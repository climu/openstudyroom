#!/bin/bash

set -eu

INITI_DATA= [ ! -f db.sqlite3 ]

./manage.py makemigrations
./manage.py migrate

if $INIT_DATA ; then
    ./manage.py loaddata fixtures/initial_data.json
fi

./manage.py runserver 0.0.0.0:8000
