#!/bin/bash

set -eux

# This is ugly but it works.
if [ ! -f db.sqlite3 ]; then
	wget --quiet https://cdn.discordapp.com/attachments/287520917255356416/1066436504597053570/db.sqlite3
fi

./manage.py makemigrations
./manage.py migrate
./manage.py runserver 0.0.0.0:8000
