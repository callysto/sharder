#!/usr/bin/env python3

import argparse
import sys
import yaml

from sqlalchemy import func
from tornado import log

from sharder import Shard
from utils import default_config, configure_database, create_sharder


def list_users():
    q = sharder.session.query(Shard).filter(Shard.kind == "hub")
    print("{: <45} {: <30}".format("Username", "Hub"))
    for user in q:
        if "dummy-" in user.name:
            continue
        print("{: <45} {: <30}".format(user.name, user.bucket))


def find_user():
    q = sharder.session.query(Shard).filter(
        Shard.kind == "hub", Shard.name == args.find_user
    )
    print("{: <45} {: <30}".format("Username", "Hub"))
    for user in q:
        print("{: <45} {: <30}".format(user.name, user.bucket))


def delete_user():
    q = sharder.session.query(Shard).filter(
        Shard.kind == "hub", Shard.name == args.delete_user
    )

    if q.count() != 1:
        print(f"Could not find user {args.delete_user}")
        sys.exit(1)

    user = q[0]
    sharder.session.delete(user)
    sharder.session.commit()


def list_users_on_hub():
    q = sharder.session.query(Shard).filter(
        Shard.kind == "hub", Shard.bucket == args.list_users_on_hub
    )
    print("{: <45} {: <30}".format("Username", "Hub"))
    for user in q:
        if "dummy-" in user.name:
            continue
        print("{: <45} {: <30}".format(user.name, user.bucket))


def list_hubs():
    q = (
        sharder.session.query(Shard.bucket, func.count(Shard.bucket).label("total"))
        .filter(Shard.kind == "hub")
        .group_by(Shard.bucket)
        .order_by("bucket")
    )

    hub_counts = {}
    for hub in sharder.hubs:
        hub_counts[hub["name"]] = {"extra_shards": hub.get("extra_shards", 0)}

    for hub in q:
        hub_counts[hub.bucket]["raw"] = hub.total

    print(
        "{: <35} {: <10} {: <10} {: <20}".format(
            "Hub", "Raw", "Extra", "Effective Total Users"
        )
    )
    for hub, hubinfo in hub_counts.items():
        print(
            "{: <35} {: <10} {: < 10} {: <10}".format(
                hub,
                hubinfo["raw"],
                hubinfo["extra_shards"],
                hubinfo["raw"] + hubinfo["extra_shards"],
            )
        )


def move_user():
    q = sharder.session.query(Shard).filter(
        Shard.kind == "hub", Shard.name == args.move_user
    )

    if q.count() != 1:
        print(f"Could not find user {args.move_user}")
        sys.exit(1)

    user = q[0]

    if args.to_hub not in config["hubs"]:
        print(f"Could not find hub {args.to_hub}")
        sys.exit(1)

    user.bucket = args.to_hub
    sharder.session.commit()


def add_user():
    if args.to_hub not in config["hubs"]:
        print(f"Count not find hub {args.to_hub}")
        sys.exit(1)

    sharder.session.add(Shard(kind="hub", bucket=args.to_hub, name=args.add_user))
    sharder.session.commit()


def migrate_hub():
    if args.migrate_hub not in config["hubs"]:
        print(f"Could not find hub {args.migrate_hub}")
        sys.exit(1)

    if args.to_hub not in config["hubs"]:
        print(f"Could not find hub {args.to_hub}")
        sys.exit(1)

    q = sharder.session.query(Shard).filter(
        Shard.kind == "hub", Shard.bucket == args.migrate_hub
    )

    for user in q:
        user.bucket = args.to_hub
        sharder.session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JupyterHub Sharder Admin Utility")
    parser.add_argument(
        "--config-file",
        help="The sharder config file",
        default="/srv/sharder/sharder.yml",
    )
    parser.add_argument("--find-user", help="Find a user by <user>")
    parser.add_argument("--add-user", help="Add <user>")
    parser.add_argument("--delete-user", help="Delete <user>")
    parser.add_argument("--list-users-on-hub", help="List all users on <hub>")
    parser.add_argument("--list-hubs", action="store_true", help="List all hubs")
    parser.add_argument("--list-users", action="store_true", help="List all users")
    parser.add_argument("--move-user", help="Move <user>")
    parser.add_argument("--migrate-hub", help="Move all users on <hub>")
    parser.add_argument("--to-hub", help="Destination <hub> for adds and moves")
    args = parser.parse_args()

    l = log.app_log
    config = default_config()
    if args.config_file is not None:
        with open(args.config_file) as f:
            c = yaml.load(f, Loader=yaml.FullLoader)
            config.update(c)

    db = configure_database(config, l)
    sharder = create_sharder(config, db, l)

    if args.find_user:
        find_user()

    if args.list_users:
        list_users()

    if args.list_users_on_hub:
        list_users_on_hub()

    if args.list_hubs:
        list_hubs()

    if args.delete_user:
        delete_user()

    if args.add_user:
        add_user()

    if args.move_user:
        if args.to_hub is None:
            print("--move-user requires --to-hub")
            sys.exit(1)
        move_user()

    if args.migrate_hub:
        if args.to_hub is None:
            print("--move-all-users-on requires --to-hub")
            sys.exit(1)
        migrate_hub()
