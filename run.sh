#!/bin/sh

docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock -p 7681:7681 hani:0.0.1
