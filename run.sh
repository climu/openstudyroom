#!/bin/bash

INITI_DATA= [ ! -f db.sqlite3 ]

./manage.py makemigrations || exit 1
./manage.py migrate || exit 1

if $INIT_DATA ; then
    ./manage.py loaddata fixtures/initial_data.json || exit 1
fi

./manage.py runserver 0.0.0.0:8000 || exit 1
