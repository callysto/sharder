#!/usr/bin/env python3

import os
import sqlite3

from sqlalchemy import create_engine

from sharder import Sharder

# default_config returns a dict with the default
# configuration values.
def default_config():
  c = {
    'cookie_secret': 'THIS_IS_ONLY_FOR_TESTING',
    'db_type': 'sqlite',
    'sharder_port': 8888,
    'sharder_listen': '0.0.0.0',
  }

  return c


# configure_database takes a yaml "config" data set
# and determines the type of database for the sharder
# to use.
#
# Currently PostgreSQL and SQLite are supported.
# For SQLite, it's possible to use a sqlite db file
# or an in-memory database (used only for testing).
def configure_database(config, log):
    # Determine the database engine.
    db_type = os.environ.get('DB_TYPE')
    if db_type is None and 'db_type' in config:
      db_type = config['db_type']

    # PostgreSQL and MySQL support
    if db_type == 'postgresql' or db_type == 'mysql+pymysql':
        # Support credentials both in the config file and in the environment.
        username = os.environ.get('DB_USER')
        if username is None and 'db_user' in config:
          username = config['db_user']

        password = os.environ.get('DB_PASSWORD')
        if password is None and 'db_password' in config:
          password = config['db_password']

        db_host = os.environ.get('DB_HOST')
        if db_host is None and 'db_name' in config:
          db_host = config['db_host']

        db_name = os.environ.get('DB_NAME')
        if db_name is None and 'db_name' in config:
          db_name = config['db_name']

        engine = create_engine(f'{db_type}://{username}:{password}@{db_host}/{db_name}', connect_args={'connect_timeout': 10})
        log.info(f'{db_type} DB init')

        return engine

    # SQLite
    db_file = os.environ.get('DB_FILE')
    if db_file is None and 'db_file' in config:
      db_file = config['db_file']

    if db_file is not None:
      engine = create_engine(f'sqlite:///{db_file}')
    else:
      # in-memory sqlite db for testing.
      creator = lambda: sqlite3.connect('file::memory:?cache=shared', uri=True)
      engine = create_engine('sqlite://', creator=creator, echo=True)

    log.info(f'Sqlite3 DB init')

    return engine


# create_sharder will instantiate a sharder and
# load it with known hubs.
def create_sharder(config, engine, log):
    # Get the list of hubs in the cluster.
    hubs = []
    if 'hubs' in config:
      hubs = config['hubs']

    log.info(f'Loading hubs {hubs}')
    sharder = Sharder(engine, 'hub', hubs, log)

    return sharder
