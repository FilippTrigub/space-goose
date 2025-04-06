#!/bin/sh

set -ex 
docker context use default
docker build -t olegselajev241/hani:ollama . 
