import sqlalchemy
import pytest

from tornado import log

from sharder import Sharder

@pytest.fixture
def engine():
  engine = sqlalchemy.create_engine('sqlite:///:memory:')
  return engine

def test_single_shard(engine):
    s = Sharder(engine, 'hub', [{'name': 'hub-1'}], log=log.app_log)
    assert s.shard('user') == 'hub-1'

def test_multiple_equal_shards(engine):
    """
    Check that we shard entries equally across buckets. If we have 10 buckets
    and 100 entries, each buckets should see 10 shards
    """
    buckets = [{'name': str(i)} for i in range(10)]
    entries = [str(i) for i in range(100)]

    s = Sharder(engine, 'hub', buckets, log=log.app_log)
    [s.shard(e) for e in entries]

    shards = {}
    for e in entries:
        shard = s.shard(e)
        if shard in shards:
            shards[shard] += 1
        else:
            shards[shard]  = 1

    assert len(shards) == 10
    assert sum(shards.values()) == 100

    for shard, count in shards.items():
        assert count == 10

def test_multiple_unequal_shards(engine):
    """
    Check that when the number of entries isn't divisible by the number of
    buckets we still shard as fairly as possible.
    """
    buckets = [{'name': str(i)} for i in range(10)]
    entries = [str(i) for i in range(99)]

    s = Sharder(engine, 'hub', buckets, log=log.app_log)
    [s.shard(e) for e in entries]

    shards = {}
    for e in entries:
        shard = s.shard(e)
        if shard in shards:
            shards[shard] += 1
        else:
            shards[shard] = 1

    assert len(shards) == 10
    assert sum(shards.values()) == 99
    assert sorted(shards.values()) == [9, 10, 10, 10, 10, 10, 10, 10, 10, 10]

def test_shard_with_offset(engine):
    """
    Check that our sharding policy respects offsets. If a hub has N existing
    entries in the database and an offset of M, it should behave as is there
    are N - M users.
    """
    buckets = [{'name': str(i)} for i in range(10)]
    entries = [str(i) for i in range(100)]

    s = Sharder(engine, 'hub', buckets, log=log.app_log)
    [s.shard(e) for e in entries]

    shards = {}
    for e in entries:
        shard = s.shard(e)
        if shard in shards:
            shards[shard] += 1
        else:
            shards[shard]  = 1

    # Add 2 extra_shards to the first bucket.
    # The next 18 assignments should be spread evenly among the remaining hubs
    s.hubs[0]['extra_shards'] = 2
    extra_entries = [str(i) for i in range(100,118)]

    for e in extra_entries:
        shard = s.shard(e)
        print(f"Sharded {e} as {shard}")
        if shard in shards:
            shards[shard] += 1
        else:
            shards[shard]  = 1

    assert len(shards) == 10
    assert sum(shards.values()) == 118
    print(shards)
    for shard, count in shards.items():
        if shard == buckets[0]['name']:
            assert count == 10
        else:
            assert count == 12
   
    # If we assign 10 more, 1 should go to each bucket
    extra_entries = [str(i) for i in range(118, 128)]

    for e in extra_entries:
        shard = s.shard(e)
        print(f"Sharded {e} as {shard}")
        if shard in shards:
            shards[shard] += 1
        else:
            shards[shard]  = 1

    assert len(shards) == 10
    assert sum(shards.values()) == 128
    print(shards)
    for shard, count in shards.items():
        if shard == buckets[0]['name']:
            assert count == 11
        else:
            assert count == 13
