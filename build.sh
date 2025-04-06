#!/bin/sh

set -ex 

docker buildx build --builder cloud-docker-devrel --platform linux/amd64 --build-arg SETUP=cloud-run --tag olegselajev241/hani:cloud-run --push .
docker buildx build --builder cloud-docker-devrel --platform linux/amd64 --build-arg SETUP=compose --tag olegselajev241/hani:compose --push .
docker buildx build --builder cloud-docker-devrel --platform linux/amd64,linux/arm64 --tag olegselajev241/hani:local --push .

# build ollama image with qwen2.5:7b
# don't need to do this many times, once is enough 
#docker buildx build --builder cloud-docker-devrel --platform linux/amd64,linux/arm64 --tag olegselajev241/oqwen2.5:7b --push -f ollama.Dockerfile .
