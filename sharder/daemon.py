#!/usr/bin/env python3

import argparse
import os
import sqlite3
import tornado.ioloop
import yaml

from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine
from tornado import concurrent, gen, log, web

from sharder import Sharder
from utils import default_config, configure_database, create_sharder

class ShardHandler(tornado.web.RequestHandler):
    _sharder_thread_pool = ThreadPoolExecutor(max_workers=1)

    @concurrent.run_on_executor(executor='_sharder_thread_pool')
    def shard(self, username):
        config = self.settings['config']
        log = self.settings['log']
        db = configure_database(config, log)
        sharder = create_sharder(config, db, log)
        return sharder.shard(username)

    # I can *almost* convince myself that this is OK to be a GET
    @gen.coroutine
    def get(self):
        # This resource is protected so we should see the REMOTE_USER header
        header_name = self.settings['header']
        remote_user = self.request.headers.get(header_name, "")

        log = self.settings['log']
        if remote_user == "":
            log.info(f'Failed to find REMOTE_USER')
            raise web.HTTPError(401, "Hub sharder unable to find auth headers")

        hub = yield self.shard(remote_user)

        self.set_cookie('hub', hub)
        #self.request.headers['Cookie'] = f'hub={hub}'
        self.redirect(f'https://{hub}/jupyter/hub')

class HubHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self, hub):
        log.app_log.info('Hub Handler')
        self.render('templates/page.html')

if __name__ == "__main__":
  # Configure comment-line argument parsing.
  parser = argparse.ArgumentParser(description='JupyterHub Sharder')
  parser.add_argument('--config-file')
  args = parser.parse_args()

  # Configure logger.
  log.enable_pretty_logging()

  # Read the configuration file.
  config = default_config()
  if args.config_file is not None:
    with open(args.config_file) as f:
      c = yaml.load(f)
      config.update(c)

  cookie_secret = os.environ.get('COOKIE_SECRET')
  if cookie_secret is None and 'cookie_secret' in config:
    cookie_secret = config['cookie_secret']

  # Create the web application and set up the routes.
  app = web.Application([
      (r"/shard", ShardHandler),
      (r"/hubs/(hub-[0-9]+)", HubHandler),
    ],
    log=log.app_log,
    config=config,
    header='REMOTE_USER',
    cookie_secret=cookie_secret,
  )

  # Set up the listening service which will
  # accept and process incoming requests.
  if 'sharder_port' in config:
    sharder_port = config['sharder_port']

  if 'sharder_listen' in config:
    sharder_listen = config['sharder_listen']

  app.listen(sharder_port, sharder_listen)
  tornado.ioloop.IOLoop.current().start()
