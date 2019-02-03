# How to set up a local development copy of the OSR website
There are two ways to get the server started, but for both of them you'll start by [forking](https://help.github.com/articles/fork-a-repo/) the repository on github. Just click the fork button in the upper right when you're looking at this repository on github.

## Running via docker
If you already have [docker](https://docker.com) installed and running, simply clone the repo into the parent directory of your choice, cd into the project directory, and run the setup script:
```bash
git clone https://github.com/YOURUSERNAME/openstudyroom.git
cd openstudyroom/
./docker.sh
```

It will take a while to set up all of the dependencies, but when it finishes, you should have a copy of the OSR server running at [http://127.0.0.1:8000](http://127.0.0.1:8000). You can log in with the username `admin` and the password `admin`.

You'll find more information [here](/docs/docker.md). If you have trouble, don't hesitate to ask for help in the #dev_room channel on [discord](https://discord.gg/7sbMHyC).

## Manually
Tested on Ubuntu 14.04 with Python 3.4, Ubuntu 16.04 and Python 3.5, and Archlinux.

Updated and tested the 12 September 2017.

First you need to fork this github repository. Just click the fork buton on github.

Be sure you have git and python3-dev and libpq-dev installed. If not, run
```bash
sudo apt-get install git-core python3-dev libpq-dev
```

You also need virtualenv installed.
```bash
sudo pip3 install virtualenv
```

create a working directory: `mkdir osr`

go inside: `cd osr/`

create a virtual environment: `virtualenv -p python3 venv`

activate it: `source venv/bin/activate`

clone your git repo: `git clone https://github.com/YOURUSERNAME/openstudyroom.git`

go to project folder: `cd openstudyroom/`

change branch to dev: `git checkout dev`

install depedency: `pip install -r requirements.txt`

Rename machina local folder to fix the [url issue](https://github.com/climu/openstudyroom/issues/267). Mind the python version: `mv ../venv/lib/python3.?/site-packages/machina/locale/ ../venv/lib/python3.?/site-packages/machina/locale.back/`

run migrations and migrate:

`./manage.py makemigrations`

`./manage.py migrate`

Load initial datas:
`./manage.py loaddata fixtures/initial_data.json `

run the server:
`./manage.py runserver`

The server should now be running on your computer at [http://127.0.0.1:8000](http://127.0.0.1:8000). You can connect with user `admin` and pass `admin`