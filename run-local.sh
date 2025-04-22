#!/bin/sh

# docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock -p 7681:7681 -e GOOSE_MODEL=ai/gemma3-qat:12B-Q4_K_M olegselajev241/hani:local


# OLEG!! Log out of the docker desktop for this to work!!!!
docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock -p 7681:7681 olegselajev241/hani:local
#docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock -p 7681:7681 -e GOOSE_PROVIDER=google -e GOOSE_MODEL=gemini-2.5-pro-exp-03-25 --env-file .env olegselajev241/hani:local