import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


def get_engine(uri):
    return create_engine(uri)


DATABASE_URL = os.getenv('DATABASE_URL', "sqlite:////tmp/traffic.db")
db_session = scoped_session(sessionmaker())
engine = get_engine(DATABASE_URL)


def init_session():
    db_session.configure(bind=engine)
    from axon.db.local.models import Base
    Base.metadata.create_all(engine)


def get_session():
    return db_session