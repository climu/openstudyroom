FROM python:3.7-stretch as base_build
# Do not buffer python's stdout or stderr
ENV PYTHONUNBUFFERED 1
# Create the app directory
RUN mkdir /app
WORKDIR /app
ADD requirements.txt /app/
RUN pip install -r requirements.txt

FROM base_build as webserver
EXPOSE 8000
# https://github.com/climu/openstudyroom/issues/267
RUN rm -r /usr/local/lib/python3.7/site-packages/machina/locale
ADD run.sh /app/
CMD ["./run.sh"]

FROM base_build as pylint
ADD requirements_dev.txt /app/
RUN pip install -r requirements_dev.txt
# https://github.com/climu/openstudyroom/issues/267
RUN rm -r /usr/local/lib/python3.7/site-packages/machina/locale

CMD ["/usr/local/bin/pylint community fixtures fullcalendar home league openstudyroom search wgo manage.py"]