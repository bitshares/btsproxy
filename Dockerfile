FROM python:3.5

COPY setup.py /
COPY btsproxy /btsproxy
WORKDIR /

RUN python setup.py install

STOPSIGNAL SIGINT

CMD ["btsproxy"]
