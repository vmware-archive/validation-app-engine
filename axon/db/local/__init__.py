import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


def get_engine(uri):
    return create_engine(uri)


if os.name == "posix":
   DB_URL = "sqlite:////opt/axon/traffic.db"
else:
   DB_URL = "sqlite:///C:\axon\\traffic.db"


DATABASE_URL = os.getenv('DATABASE_URL', DB_URL)
db_session = scoped_session(sessionmaker(
    autoflush=True,
    autocommit=False))
engine = get_engine(DATABASE_URL)


def init_session():
    db_session.configure(bind=engine)
    from axon.db.local.models import Base
    Base.metadata.create_all(engine)


def get_session():
    return db_session()

