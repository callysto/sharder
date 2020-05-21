FROM python:3.6-slim-stretch

MAINTAINER Ian Allison <iana@pims.math.ca>

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libcurl4-openssl-dev \
      libssl-dev \
      build-essential \
      && \
    apt-get purge && apt-get clean

RUN pip3 install --no-cache-dir tornado ruamel.yaml oauthlib psycopg2-binary pycurl sqlalchemy pyyaml pymysql cryptography

RUN mkdir -p /srv/sharder
ADD db.py /srv/sharder/db.py
ADD sharder.py /srv/sharder/sharder.py
ADD daemon.py /srv/sharder/daemon.py
ADD wait-for-it.sh /srv/sharder/wait-for-it.sh
RUN chmod +x /srv/sharder/wait-for-it.sh
ADD templates /srv/sharder/templates

WORKDIR /srv/sharder

ENTRYPOINT ["/srv/sharder/wait-for-it.sh", "-t", "60", "mysql:3306", "--", "python3.6", "/srv/sharder/daemon.py"]
