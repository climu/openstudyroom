FROM python:3.5-stretch

# Do not buffer python's stdout or stderr
ENV PYTHONUNBUFFERED 1

# Create the app directory
RUN mkdir /app
WORKDIR /app

ADD requirements.txt /app/

RUN pip install -r requirements.txt

# ADD . /app/

EXPOSE 8000

# https://github.com/climu/openstudyroom/issues/267
RUN rm /usr/lib/python3.5/site-packages/machina/locale/ -rf

ADD run.sh /app/

CMD ["./run.sh"]
