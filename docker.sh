#!/bin/bash

export NAME=osr_django
export PORTS="-p 8000:8000"
export VOLUME="-v $(pwd):/app"

docker stop $NAME
docker rm $NAME
docker build -t osr/$NAME . || exit 1
docker run --restart=always --name=$NAME $PORTS $VOLUME -d osr/$NAME

