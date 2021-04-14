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

This should work on any UNIX with python 3.7.

Updated and tested on April 2021.

First you need to fork this github repository. Just click the fork buton on github.

Be sure you have git and python3-dev and libpq-dev installed. If not, run
```bash
sudo apt-get install git-core python3-dev libpq-dev
```

Create a working directory: `mkdir osr`

Go inside: `cd osr/`

Create a virtual environment: `python3.7 -m venv venv`

Activate it: `source venv/bin/activate`

Clone your git repo: `git clone https://github.com/YOURUSERNAME/openstudyroom.git`

Go to project folder: `cd openstudyroom/`

Change branch to dev: `git checkout dev`

Install development dependencies: `pip install -r requirements_dev.txt`

Run migrations and migrate:

`./manage.py makemigrations`

`./manage.py migrate`

Load initial datas:
`./manage.py loaddata fixtures/initial_data.json `

Run the server:
`./manage.py runserver`

The server should now be running on your computer at [http://127.0.0.1:8000](http://127.0.0.1:8000). You can connect with user `admin` and pass `admin`
