#!/bin/bash

set -uvo pipefail

NAME=osr_django_dev
VOLUME="-v $(pwd):/app"

docker stop $NAME
docker rm $NAME
set -e
docker build -t osr/$NAME -f Dockerfile.dev .
docker run --restart=always --name=$NAME $VOLUME -it osr/$NAME /usr/local/bin/pylint community fixtures fullcalendar home league openstudyroom search wgo manage.py