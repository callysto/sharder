FROM python:3.9-slim

MAINTAINER Ian Allison <iana@pims.math.ca>

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libcurl4-openssl-dev \
      libssl-dev \
      build-essential \
      && \
    apt-get purge && apt-get clean

RUN pip3 install --no-cache-dir tornado ruamel.yaml oauthlib psycopg2-binary pycurl "sqlalchemy<2" pyyaml pymysql cryptography

RUN mkdir -p /srv/sharder
ADD sharder.py /srv/sharder/sharder.py
ADD daemon.py /srv/sharder/daemon.py
ADD utils.py /srv/sharder/utils.py
ADD admin.py /srv/sharder/admin.py
ADD templates /srv/sharder/templates

WORKDIR /srv/sharder

ENTRYPOINT ["python3", "/srv/sharder/daemon.py", "--config-file", "/srv/sharder/sharder.yml"]
