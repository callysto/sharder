import tornado.web

from sqlalchemy import func
from sqlalchemy import Column, Integer, String, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


DBBase = declarative_base()

class Shard(DBBase):
    """
    Sharding table
    """
    __tablename__ = "shard"
    id     = Column(Integer, autoincrement=True, primary_key=True)
    kind   = Column(String(256))
    bucket = Column(String(256))
    name   = Column(String(256))
    UniqueConstraint(kind, name)
    Index('shard_kind_name_index', kind, name)

    def __repr__(self):
        return f'<User(id={self.id}, kind={self.kind}, bucket={self.bucket}, name={self.name})>'


class Sharder:
    """
    Simple db based sharder.
    Does least-loaded balancing of a given kind of object (homedirectory, running user, etc)
    across multiple buckets, ensuring that once an object is assigned to a bucket it always
    is assigned to the same bucket.
    """
    def __init__(self, engine, kind, buckets, log):
        self.engine  = engine
        self.kind    = kind
        self.buckets = buckets
        self.log     = log

        DBBase.metadata.create_all(engine, checkfirst=True)

        Session = sessionmaker()
        Session.configure(bind=engine)
        self.session = Session()

        # Make sure that we have at least one dummy entry for each bucket
        # NOTE: This is rather poor SQL design, but we'll defer that until later.
        for bucket in buckets:
            if self.session.query(Shard.bucket).filter_by(bucket=bucket, name=f'dummy-{bucket}').scalar() is None:
                self.session.add(Shard(kind=self.kind, bucket=bucket, name=f'dummy-{bucket}'))
                self.session.commit()

    def shard(self, name):
        """
        Return the bucket where name should be placed.
        If it isn't already in the database, a new entry will be created in the
        least populated bucket.
        """
        q = self.session.query(Shard).filter(Shard.kind == self.kind, Shard.name == name).first()
        if q:
            bucket = q.bucket
            self.log.info(f'Found {name} sharded into bucket {bucket}')
            return bucket

        # name isn't assigned to a bucket yet, add an entry
        q = (self.session.query(Shard.bucket, func.count(Shard.bucket)
            .label('total'))
            .filter(Shard.kind == self.kind)
            .group_by(Shard.bucket)
            .order_by('total').first()
        )
        if q:
            bucket = q.bucket
        self.session.add(Shard(kind=self.kind, bucket=bucket, name=name))
        self.log.info(f'Assigned {name} to bucket {bucket}')
        self.session.commit()

        return bucket
