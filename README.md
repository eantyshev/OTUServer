## OTUServer 1.0

Simple HTTP server, uses asyncore/asynchat with epoll support from patch https://github.com/shuge/asyncore_patch

### Usage
Since server is single-threaded, no workers argument supported.
```
$ python httpd.py -r <docroot path>
```

### High-load testing results

```
$ ab -n 50000 -c 100 -r http://127.0.0.1:8080/
This is ApacheBench, Version 2.3 <$Revision: 1706008 $>
Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
Licensed to The Apache Software Foundation, http://www.apache.org/

Benchmarking 127.0.0.1 (be patient)
Completed 5000 requests
Completed 10000 requests
Completed 15000 requests
Completed 20000 requests
Completed 25000 requests
Completed 30000 requests
Completed 35000 requests
Completed 40000 requests
Completed 45000 requests
Completed 50000 requests
Finished 50000 requests


Server Software:        OTUServer/1.0
Server Hostname:        127.0.0.1
Server Port:            8080

Document Path:          /
Document Length:        0 bytes

Concurrency Level:      100
Time taken for tests:   17.168 seconds
Complete requests:      50000
Failed requests:        0
Non-2xx responses:      50000
Total transferred:      5250000 bytes
HTML transferred:       0 bytes
Requests per second:    2912.46 [#/sec] (mean)
Time per request:       34.335 [ms] (mean)
Time per request:       0.343 [ms] (mean, across all concurrent requests)
Transfer rate:          298.64 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.1      0       2
Processing:     3   34   1.9     34      50
Waiting:        1   34   1.9     34      50
Total:          5   34   1.9     34      50

Percentage of the requests served within a certain time (ms)
  50%     34
  66%     35
  75%     35
  80%     36
  90%     36
  95%     37
  98%     38
  99%     40
 100%     50 (longest request)
 ```
