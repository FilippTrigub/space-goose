#!/bin/sh

docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock -p 7681:7681 olegselajev241/hani:latest
