#!/usr/bin/env python
# coding: utf-8

import argparse
from datetime import datetime
import logging
from logging import debug, info, error, exception
import os
import sys
import urllib

import asyncore_patch

asyncore_patch.patch_all()
import asyncore
import asynchat
import socket
import errno

OK = 200
FORBIDDEN = 403
NOT_FOUND = 404
NOT_ALLOWED = 405
CODE_DESCR = {
    OK: "OK",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not found",
    NOT_ALLOWED: "Method not allowed",
}

CRLF = "\r\n"


def filepath(relpath, docroot):
    # abspath is to resolve "../../../"-like paths
    # to not allow getting out of docroot
    normpath = os.path.abspath(relpath)
    normpath = normpath.lstrip("/")
    fullpath = os.path.join(docroot, normpath)
    if os.path.isdir(fullpath):
        fullpath = os.path.join(fullpath, "index.html")
    elif os.path.isfile(fullpath):
        if relpath.endswith("/"):
            return None
    return fullpath


def read_content(filepath):
    pass


def guess_content_type(fpath):
    suffix2mime = {
        '.html': 'text/html',
        '.txt': 'text/plain',
        '.css': 'text/css',
        '.js': 'text/javascript',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.swf': 'application/x-shockwave-flash',
    }
    _, suffix = os.path.splitext(fpath)
    return suffix2mime.get(suffix)


class HttpResponse(object):
    def __init__(self, code, content, content_type=None, content_len=0):
        self.code = code
        self.content = content
        self.content_type = content_type
        self.content_len = content_len
        self.utcnow = datetime.utcnow()

    def __str__(self):
        lines = []
        lines.append("HTTP/1.1 %d %s" % (self.code, CODE_DESCR[self.code]))
        lines.append(self.utcnow.strftime("Date: %a, %d %b %Y %H:%M:%S GMT"))
        lines.append("Server: OTUServer/1.0")
        if self.content_type:
            lines.append("Content-Type: %s" % self.content_type)
        if self.content_len is not None:
            lines.append("Content-Length: %d" % self.content_len)
        lines.append("")
        lines.append(self.content or "")
        return CRLF.join(lines)


def serve_one(req, docroot):
    fpath = filepath(req.relpath, docroot)
    debug("check local file %s", fpath)

    if not fpath:
        debug("... path is not defined")
        return HttpResponse(NOT_FOUND, None)
    if not fpath.startswith(docroot):
        debug("... escaped from docroot.")
        return HttpResponse(FORBIDDEN, None)

    try:
        fp = open(fpath)
    except IOError as e:
        if e.errno == errno.EACCES:
            debug("... access denied")
            return HttpResponse(FORBIDDEN, None)
        if e.errno == errno.ENOENT:
            debug("... Not exists")
            return HttpResponse(NOT_FOUND, None)
        raise
    else:
        debug("... File exists")
        with fp:
            content = fp.read()

    content_type = guess_content_type(fpath)
    if req.method == "GET":
        return HttpResponse(OK, content, content_type, len(content))
    elif req.method == "HEAD":
        return HttpResponse(OK, None, content_type, len(content))
    else:
        return HttpResponse(NOT_ALLOWED, None)


class HttpRequest(object):
    def __init__(self, method, relpath, version, headers):
        self.method = method
        self.relpath = relpath
        self.version = version
        self.headers = headers
        info("Created %s", self)

    def __str__(self):
        return ("HttpRequest(method=%s, relpath=%s, version=%s, headers=%r)" %
                (self.method, self.relpath, self.version, self.headers))

    @staticmethod
    def _url2relpath(url_path):
        res = urllib.unquote_plus(url_path).decode("utf-8")
        # strip off url arguments part
        return res.split("?", 1)[0]

    @classmethod
    def from_data(cls, data):
        lines = data.split(CRLF)
        method, location, version = lines[0].split()
        headers = {}
        for s in lines[1:]:
            if not s:
                continue
            header, value = s.split(None, 1)
            header = header.rstrip(":")
            headers[header] = value
        return HttpRequest(
            method,
            cls._url2relpath(location),
            version,
            headers
        )


class HttpHandler(asynchat.async_chat):

    def __init__(self, sock, addr, docroot):
        asynchat.async_chat.__init__(self, sock=sock)
        self.docroot = docroot
        self.ibuffer = []
        self.set_terminator(CRLF + CRLF)
        self.logger = logging.getLogger("handler_%s" % (addr,))

    def collect_incoming_data(self, data):
        """Buffer the data"""
        self.logger.debug("< %s", data)
        self.ibuffer.append(data)

    def found_terminator(self):
        req = HttpRequest.from_data("".join(self.ibuffer))
        resp = serve_one(req, self.docroot)
        self.push(str(resp))
        #self.logger.debug("> %s" % resp)
        if req.headers.get("Connection") != "keep-alive":
            self.logger.debug("close_when_done")
            self.close_when_done()
        else:
            self.logger.debug("re-using connection")
            self.ibuffer = []


class HttpServer(asyncore.dispatcher):

    def __init__(self, host, port, docroot, nworkers):
        self.docroot = docroot
        self.nworkers = nworkers

        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(100)

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            info('Incoming connection from %s' % repr(addr))
            HttpHandler(sock, addr, self.docroot)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", dest="document_root",
                        default=".",
                        help="Document root path ('.' by default).")
    parser.add_argument("-w", dest="nworkers",
                        default=10,
                        help="Number of workers (default 10).")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(name)s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')

    os.chdir(args.document_root)
    server = HttpServer(
        'localhost',
        8080,
        docroot=args.document_root,
        nworkers=args.nworkers
    )
    asyncore.loop()  # using select.epoll on Linux 2.5.44+


if __name__ == '__main__':
    main()
