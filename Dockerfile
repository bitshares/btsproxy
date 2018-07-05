FROM python:3.5

COPY . /

RUN python setup.py install

STOPSIGNAL SIGINT

CMD ["btsproxy"]
