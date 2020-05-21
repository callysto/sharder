# Sharder

This is another implementation of the sharder from the
[data8xhub](https://github.com/berkeley-dsep-infra/data8xhub) repository. A
sharder is an application which assigns objects to bins (e.g. users to
JupyterHub instances) by applying some assignment policy.

This sharder is a python program which maintains a database of object-bin
assignments. When a request for an object-bin paring is made, if the pairing
already exists, the bin name is returned. If it does not exist, sharder.py
implements the sharder policy, assign the object to a bin (forever), and returns
the bin name.

The current sharder policy is "emptiest bin" and the logic is mostly implemented
in SQL. When a new object of a given kind is added, the database is queried to
see how many of that kind are assigned to each bin, and a new record is added to
the bin with the fewest assignments.


## Implementation

The sharder is meant to run as a service, whether using Docker or systemd.
It's designed as a REST-based web application and expects a REMOTE_USER
header to be already set when it receives requests. This means that you need
to put the service behind a web server like Apache or nginx.

The sharder will then take the value of REMOTE_USER and see if the user has
already been assigned a bucket. If so, the name of the bucket will be returned.
If not, a bucket will be assigned. Either way, a cookie called "hub" will
be set with the determined value.

## Running the Sharder

A docker-compose file is provided to spin up nginx, postgresql and tornado,
implementing the full sharder application stack, buy you can also run the
sharder as a standalone application.

### As a Standalone Application

You can use systemd with a unit file such as:

```
[root@sharder-profound-moose sharder]# cat /etc/systemd/system/sharder.service
[Unit]
Description=JupyterHub Sharder

[Service]
ExecStart=/bin/python3.6 /srv/sharder/request-sharder.py --config-file /srv/sharder/sharder.yml
Restart=on-failure

[Install]
WantedBy=ulti-user.target
```

This will initialize a database (with the right behaviour for multiple
connections) and setup a tornado webserver. You can make requests against the
webserver with the REMOTE_USER header set, e.g.

```
  curl -H 'REMOTE_USER: iana 127.0.0.1:8888/shard
```

The output of the request-sharder application should let you know the result of
the assignment. This assignment should be stable across subsequent requests.

### As a multi-part application

A docker-compose file is provided which will create a database, the sharder and
and an nginx "edge" server. The database must be configured as part of the build
process by setting the environment variables POSTGRES_USER, POSTGRES_PASSSWORD
and POSTGRES_DB, e.g.

```
  $ vi sharding.env  # This name is already part of the .gitignore
POSTGRES_USER="shard_user"
POSTGRES_PASSWORD="some long random password here"
POSTGRES_DB="hubshards"
export POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB

MYSQL_USER="shard_user"
MYSQL_PASSWORD="some long random password here"
MYSQL_ROOT_PASSWORD="some long random password here"
MYSQL_DATABASE="hubshards"
export MYSQL_ROOT_PASSWORD MYSQL_USER MYSQL_PASSWORD MYSQL_DATABASE

  $ source sharding.env
```

A new directory called db will be created in this directory and will be used to
store the hub database files persistently. If you want do reset the system it is
safe to delete this directory.

```
  $ docker-compose build
  $ docker-compuse up -d
```

The sharder has a dependency on the database so it is launched by wait-for-it.sh
to give the database time to be prepared, once it is ready the sharder will
apply the schema and wait to service requests.

You can use an extensions such as
[ModHeader](https://chrome.google.com/webstore/detail/modheader/idgpnmonknjnojddfkpgkljpfnnfcklj/related?hl=en)
to set the REMOTE_USER header and the Chrome developer tools to check the value
of the `hub` cookie. Try visiting 127.0.0.1:8080/shard (remember to delete the
hub cookie if you update the REMOTE_USER header). To see the logs on the sharder
you can run

```
  $ docker-compose logs sharder
```

If you want to inspect the database you can use psql in the db container, e.g.

```
  $ docker-compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB
psql (10.5 (Debian 10.5-1.pgdg90+1))
Type "help" for help.

hubshards=# \c hubshards
You are now connected to database "hubshards" as user "shard_user".
hubshards=# \dt
          List of relations
 Schema | Name  | Type  |   Owner
--------+-------+-------+------------
 public | shard | table | shard_user
(1 row)

hubshards=# SELECT * from shard;
 id | kind | bucket |    name
----+------+--------+-------------
  1 | hub  | hub-0  | dummy-hub-0
  2 | hub  | hub-1  | dummy-hub-1
  3 | hub  | hub-2  | dummy-hub-2
  4 | hub  | hub-3  | dummy-hub-3
  5 | hub  | hub-4  | dummy-hub-4
  6 | hub  | hub-0  | iana
  7 | hub  | hub-1  | brian
(7 rows)

hubshards=# \q
```

### Administration

There is an `admin.py` script included which can assist in performing various
administration actions:

```
python3.6 admin.py --config-file /path/to/sharder.yml --help
```

### pytest

test_sharder.py defines an in-memory sqlite database to test the sharder
application. The tests demonstrate how to add new rows to the database and check
that they are "fairly" assigned according to the sharder policy.

```
 $ pytest
 ...
test_sharder.py ...                                              [100%]

======================= 3 passed in 0.76 seconds =======================
```
