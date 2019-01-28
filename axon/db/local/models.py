#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import pickle

from sqlalchemy.types import TypeDecorator, TEXT
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, String, Boolean, Float, Integer


def passby(data):
    return data


class PickelEncodedType(TypeDecorator):
    """Abstract base type serialized as json-encoded string in db."""
    type = None
    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is None:
            # Save default value according to current type to keep the
            # interface the consistent.
            value = self.type()
        elif not isinstance(value, self.type):
            raise TypeError("%s supposes to store %s objects, but %s given"
                            % (self.__class__.__name__,
                               self.type.__name__,
                               type(value).__name__))
        serialized_value = pickle.dumps(value)
        return serialized_value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = pickle.loads(value)
        return value


class PickleEncodedList(PickelEncodedType):
    """Represents list serialized as pickle-encoded string in db."""
    type = list


class BaseModel(object):

    @declared_attr
    def __tablename__(self):
        return self.__name__.lower()

    @classmethod
    def find_one(cls, session, id):
        return session.query(cls).filter(cls.get_id() == id).one()

    @classmethod
    def find_update(cls, session, id, args):
        return session.query(cls).filter(cls.get_id() == id).update(
            args, synchronize_session=False)

    @classmethod
    def get_id(cls):
        pass

    def to_dict(self):
        intersection = set(self.__table__.columns.keys()) & set(self.FIELDS)
        return dict(map(
            lambda key:
                (key,
                    (lambda value: self.FIELDS[key](value) if value is not
                     None else None)
                    (getattr(self, key))),
                intersection))

    FIELDS = {}


Base = declarative_base(cls=BaseModel)


class TrafficRecord(Base):
    __tablename__ = 'trafficrecord'

    id = Column(String(36), primary_key=True)
    src = Column(String(36))
    dst = Column(String(36))
    port = Column(Integer())
    latency = Column(Float())
    error = Column(String(100))
    success = Column(Boolean(), default=True)
    type = Column(String(10))
    created = Column(Float())
    connected = Column(Boolean())

    FIELDS = {
        'id': str,
        'src': str,
        'dst': str,
        'port': int,
        'latency': float,
        'error': str,
        'type': str,
        'created': int,
    }

    FIELDS.update(Base.FIELDS)


class ConnectedState(Base):
    __tablename__ = 'connectedstate'

    id = Column(String(36))
    endpoint = Column(String(36), primary_key=True)
    servers = Column(PickleEncodedList)
    clients = Column(PickleEncodedList)

    FIELDS = {
        'id': str,
        'endpoint': str,
        'servers': passby,
        'clients': passby
    }

    FIELDS.update(Base.FIELDS)
