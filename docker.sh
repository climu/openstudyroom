#!/bin/bash

set -uvo pipefail

NAME=osr_django
PORTS='-p 8000:8000'
VOLUME="-v $(pwd):/app"

docker stop $NAME
docker rm $NAME
set -e
docker build -t osr/$NAME .
docker run --restart=always --name=$NAME $PORTS $VOLUME -d osr/$NAME
