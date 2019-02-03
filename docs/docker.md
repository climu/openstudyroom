# Running a local docker instance

**DISCLAIMER: this is still experimental and not recommended for production. Use at your own risk.**


## Preparation

Install docker for your operating system.

Note: You may need to take steps to tell your system to run the dockerd service and add your username to the `docker` group:
```bash
sudo systemctl start docker
sudo usermod -a -G docker <username>
```

The system will not see changes to your groups until your next login, but you can update that manually within a shell with `exec su <username>`


Clone this repository and cd into it.

## Starting the docker service

**NOTE**: Building the docker image after any major change will take a lot of time. 

Run the `docker.sh` file **or** run these commands.

First stop any running instance:

```
docker stop osr_django 
```

Delete the image so it can be recreated.

```
docker rm osr_django
```

Build the docker image

```
docker build -t osr/osr_django .
```

and finally run it.

```
docker run --restart=always --name=osr_django -p 8000:8000 -v $(pwd):/app -d osr/osr_django
```

A running instance should be available at http://localhost:8000 you can connect with user `admin` and password `admin`.

## Shell access for the docker
in order to gain shell access to run any command you want, run the following commands.

```
docker exec -it osr_django /bin/bash
```

The files are stored in /app directory.

## Database madness

Since the database will be created inside docker image, its user will be root. You can safely reown it.

```
sudo chown $(whoami) db.sqlite3
```

**NOTE** If this file is not available when the `run.sh` file is running (on every start and restart of the docker image) then the default files will be loaded. Otherwise the database will be intact (except for any migration). You can restart the docker image by running:

```
docker restart osr_django
```

## When do I need to rebuild the docker Image?

You only need to rebuild the docker image if you want to upgrade python or any of pypi packages. If you need to re-run makemigrations and migrate, you can get shell access on the docker image and go from there.

## How can I read the logs?

```
docker logs -f osr_django
```
