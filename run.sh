#!/bin/bash

set -eu

# This is ugly but it works.
if [ ! -f db.sqlite3 ]; then
    INIT_DATA=true
else
    INIT_DATA=false
fi

./manage.py makemigrations
./manage.py migrate

if $INIT_DATA ; then
    ./manage.py loaddata fixtures/initial_data.json
fi

./manage.py runserver 0.0.0.0:8000
