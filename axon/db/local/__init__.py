#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

from contextlib import contextmanager
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


def get_engine(uri):
    return create_engine(uri)


if os.name == "posix":
   DB_URL = "sqlite:////opt/axon/traffic.db"
else:
   DB_URL = "sqlite:///C:\\axon\\traffic.db"


DATABASE_URL = os.getenv('DATABASE_URL', DB_URL)
db_session = scoped_session(sessionmaker(
    autoflush=True,
    autocommit=False))
engine = get_engine(DATABASE_URL)


def init_session():
    db_session.configure(bind=engine)
    from axon.db.local.models import Base
    Base.metadata.create_all(engine)


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = db_session
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()