#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import pickle

from sqlalchemy.types import TypeDecorator, TEXT
from sqlalchemy.ext.declarative import declared_attr


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
