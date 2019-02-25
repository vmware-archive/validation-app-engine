#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

"""
This handles a great deal of the complexity embodied in writing queriable data
to riak.  The interface defined here combines some aspects of sqlalchemy's
interface to give an ORM type feel to interacting with data in riak.

The primary goal for this interface is to encapsulate things like placing test
ids on records and data serialization format so users just need to create,
read, write, and delete records without necessarily worrying about the
mechanics of interacting with riak
"""
import json
import six
import time
import uuid

import axon.db.backends.riak.riak_datatypes as riak_datatypes
from axon.db.dataclass_factory import dataclass_factory


def get_test_id():
    from axon.common import config as conf
    return conf.TEST_ID


Column = dataclass_factory(
    'Column', [
        'name', 'column_type', 'indexed', 'stored', 'default', 'schema_name',
        'transform', 'key_col'
    ],
    initializers={
        'name': lambda: None,
        'column_type': lambda: str,
        'indexed': lambda: False,
        'stored': lambda: True,
        'default': lambda: None,
        'schema_name': lambda: None,
        'transform': lambda: None,
        'key_col': lambda: False
    })


class RecordMeta(type):
    """
    This metaclass controls the creation of record classes.
    """

    def __new__(mcs, name, bases, dct):
        columns, notestid = {}, dct.get('notestid', False)
        for base in bases:
            columns.update(getattr(base, '_columns', {}))
        if notestid:
            del columns['testid']
            _ = dct.pop('testid', None)
        _keys = list(dct.keys())
        for attrname in _keys:
            if isinstance(dct[attrname], Column):
                if attrname == 'key':
                    raise TypeError('Key is a reserved name for '
                                    'record attributes')
                col_def = dct.pop(attrname)
                if col_def.name is not None:
                    attrname = col_def.name
                columns[attrname] = col_def
        dct['_columns'] = columns
        if dct.get('bucketname') is None:
            dct['bucketname'] = name.lower()
        if dct.get('indexname') is None:
            dct['indexname'] = name.lower()
        newcls = super(RecordMeta, mcs).__new__(mcs, name, bases, dct)
        return newcls


@six.add_metaclass(RecordMeta)
class Record(object):
    """
    A record object contains all the data necessary to manage a specific
    object in riak

    Attributes
    ----------
    index : boolean
        This record type should be indexed
    readonly : boolean
        This record can only be read but never created via the
        buffer interface directly
    indexname : string
        The name of the index. Defaults to the bucketname
    bucketname : string
        The name of the bucket defaults to the lower cased class name
    usetype : boolean
        When this is set then use the properties of the bucket type named
        after this bucketname
    prop_dict : dictionary
        These are bucket properties to set

    Parameters
    ----------
    kwargs : dict
        This is a mapping of column names to column values
    """

    index = False
    indexname = None
    bucketname = None
    usetype = False
    _columns = {}
    # default number of search replicas
    create_cls = riak_datatypes.CreateJSONRiakObject
    update_cls = riak_datatypes.CreateJSONObject
    delete_cls = riak_datatypes.DeleteObject

    testid = Column(
        indexed=True, stored=True, default=lambda: get_test_id(), key_col=True)

    def __new__(cls, *args, **kwargs):
        _ = (args, kwargs)  # pylint
        newinst = super(Record, cls).__new__(cls)
        for col_name, col_def in newinst._columns.items():
            col_val = None
            if callable(col_def.default):
                col_val = col_def.default()
            elif col_def.default is not None:
                col_val = col_def.default
            setattr(newinst, col_name, getattr(newinst, col_name, col_val))
        return newinst

    def __init__(self, **kwargs):
        for col_name, col_value in kwargs.items():
            if col_name not in self._columns:
                raise TypeError('%s is an invalid keyword argument for this '
                                'class' % col_name)
            col_type = self._columns[col_name].column_type
            col_transform = self._columns[col_name].transform
            if col_value is None:
                result = [] if col_type in (list, set) else None
            elif col_transform is not None:
                result = col_transform(col_value)
            else:
                result = col_type(col_value)
            setattr(self, col_name, result)
        if not isinstance(getattr(type(self), 'key', None), property):
            self.key = str(uuid.uuid4())
        # if self.index:
        #     self.__props['search_index'] = self.bucketname
        super(Record, self).__init__()

    def _as_dict(self):
        """
        Serializes the object to a regular python dictionary
        """
        return {
            col_name: getattr(self, col_name)
            for col_name in self._columns if hasattr(self, col_name)
        }

    @classmethod
    def from_json(cls, json_str):
        """
        This deserializes a json blib to a record object
        """
        return cls(**json.loads(json_str))

    @property
    def printable(self):
        """
        This iterator yields the printable set of column names/values
        """
        for col_name in self._columns:
            col_val = getattr(self, col_name)
            if isinstance(col_val, set):
                col_val = list(col_val)
            yield (col_name, col_val)

    @property
    def create_request(self):
        """
        This allows for simple class level read requests on the
        buffer object
        """
        path = '/buckets'
        if self.usetype:
            path = '/'.join(['/types', self.bucketname, 'buckets'])
        if self.key is None:
            return self.create_cls(
                bucket=self.bucketname,
                path=path,
                headers={
                    'Content-Type': 'application/json'
                },
                data=repr(self))
        else:
            return self.update_cls(
                bucket=self.bucketname,
                key=self.key,
                path=path,
                headers={
                    'Content-Type': 'application/json'
                },
                data=repr(self))

    @property
    def delete_request(self):
        """
        This returns a delete request object
        """
        path = '/buckets'
        if self.usetype:
            path = '/'.join(['/types', self.bucketname, 'buckets'])
        return self.delete_cls(bucket=self.bucketname, key=self.key, path=path)

    @classmethod
    def transform_read_request(cls, rest_obj):
        """
        This transforms the read request response to something
        that can be sent to the record class as kwargs
        """
        if cls.index and isinstance(rest_obj, dict):
            # this is a solr document
            doc = rest_obj
            return {
                cname: doc[cname]
                for cname in cls._columns if cname in doc
            }
        return rest_obj.response

    @property
    def read_request(self):
        """
        The default for reading is to segment records by testid (or key if it
        is set). For more complex cases the query interface should be used
        instead.
        """
        path = '/buckets'
        if self.usetype:
            path = '/'.join(['/types', self.bucketname, 'buckets'])
        return riak_datatypes.GetJSONObject(
            bucket=self.bucketname, key=self.key, path=path)

    def __repr__(self):
        return json.dumps({cname: cval for cname, cval in self.printable})

    __str__ = __unicode__ = __repr__


class TimestampedRecord(Record):
    """
    Frequently we are saving timestamped data (connectivity, core files and
    what not). This allows us to ensure that a timestamp is applied
    to record instance
    """
    created = Column(
        'created',
        column_type=float,
        indexed=True,
        stored=True,
        default=time.time)


class SearchRecord(Record):
    """
    This is a record type that contains searchable data. Mostly this contains
    logic for constructing simple fielded queries
    """
    index = True
    usetype = True
    filter_by_testid = True
    testid = Column(
        indexed=True,
        stored=True,
        schema_name='testid_register',
        default=lambda: get_test_id(),
        key_col=True)


class MapRecord(Record):
    """
    Some records are crdt map types.  These records must be indexed and all
    the fields in them must correspond to a specific data type
    """
    usetype = True
    testid = Column(
        indexed=True,
        stored=True,
        schema_name='testid_register',
        default=lambda: get_test_id(),
        key_col=True)

    @property
    def map_create_request(self):
        """
        This randomly keys each entry since reads will go against the search
        engine
        """
        map_entries = []
        for col_name, col_def in self._columns.items():
            map_entry = riak_datatypes.MapEntry()
            if col_def.schema_name is None:
                raise RuntimeError('All map records must have a schema_name '
                                   'defined')
            if col_def.schema_name.endswith('_counter'):
                name = 'increment'
                value = 0
                if col_def.column_type == bool:
                    if getattr(self, col_name, False):
                        value = 1
                elif col_def.column_type == int:
                    value = getattr(self, col_name, 0)
                    if value < 0:
                        value, name = abs(value), 'decrement'
                map_entry.name = col_name
                map_entry.value = riak_datatypes.Counter(**{name: value})
            elif col_def.schema_name.endswith('_flag'):
                if col_def.column_type == bool:
                    value = getattr(self, col_name, False)
                    map_entry.name = col_name
                    map_entry.value = riak_datatypes.Flag(bool(value))
            elif col_def.schema_name.endswith('_register'):
                if getattr(self, col_name, None) is not None:
                    map_entry.name = col_name
                    map_entry.value = riak_datatypes.Register(
                        value=str(getattr(self, col_name)))
            elif col_def.schema_name.endswith('_set'):
                if getattr(self, col_name, None) is not None:
                    map_entry.name = col_name
                    map_entry.value = riak_datatypes.Set(
                        add_all=list(set(getattr(self, col_name))))
            map_entries.append(map_entry)
        map_value = riak_datatypes.Map(update=map_entries)
        return riak_datatypes.UpdateMap(
            bucket=self.bucketname,
            datatype=self.indexname,
            key=str(uuid.uuid4()),
            data=map_value)

    @classmethod
    def transform_read_request(cls, doc):
        """
        This breaks the map up into it individual components

        Parameters
        ----------
        doc : dict, GetMap
            This is the json record from search
        """
        if isinstance(doc, riak_datatypes.GetMap):
            map_obj = getattr(doc, 'response', None)
            map_value = getattr(map_obj, 'value', None)
            if map_value is not None:
                map_obj.update = map_value
                doc = map_obj._as_dict().get('update', {})
        kwargs = {}
        for col_name, col_def in cls._columns.items():
            if col_def.schema_name is None:
                raise RuntimeError('All map records must have a schema_name '
                                   'defined')
            if col_def.schema_name in doc:
                if col_def.schema_name.endswith('_flag') and \
                   col_def.column_type == bool:
                    kwargs[col_name] = doc[col_def.schema_name] is True or \
                        doc[col_def.schema_name] == 'enable'
                else:
                    kwargs[col_name] = doc[col_def.schema_name]
        return kwargs

    @property
    def read_request(self):
        """
        Just a normal datatools read
        """
        return riak_datatypes.GetMap(
            bucket=self.bucketname, datatype=self.indexname, key=self.key)

    @property
    def create_request(self):
        """
        This just ensures on the outgoing write the keys are properly updated.
        """
        map_create_request = self.map_create_request
        map_create_request.key = self.key
        return map_create_request


class Sets(MapRecord):
    """
    Simple set CRDT record to hold a set of ips.
    TODO: clean this up into a proper base record
    """
    usetype = True

    vif_ips = Column(column_type=set, default=set())

    def add(self, vif_ip):
        """
        Parameters
        ----------
        vif_ip: str
            The ip to add to this set
        """
        self.vif_ips.add([vif_ip])

    @property
    def key(self):
        """
        Keyed by testid and a static string '_vifips', to differentiate
        from other general sets we might store in the future.
        """
        return '%s_vifips' % (self.testid)

    @property
    def create_request(self):
        """
        Overriden for riak set CRDT.
        """
        obj_value = riak_datatypes.Set(add_all=list(self.vif_ips))
        return riak_datatypes.UpdateSet(
            bucket=self.bucketname, datatype=self.bucketname,
            key=self.key, data=obj_value)

    @property
    def read_request(self):
        """
        Set lookup
        """
        return riak_datatypes.GetSet(
            bucket=self.bucketname, datatype=self.bucketname, key=self.key)

    @classmethod
    def transform_read_request(cls, doc):
        """
        This breaks the set up into its individual components

        Parameters
        ----------
        doc : dict, GetMap
            This is the json record from search
        """
        set_obj = getattr(doc, 'response', None)
        set_value = getattr(set_obj, 'value', None)
        if set_value is not None:
            set_obj.add_all = set_value
            doc = set_obj._as_dict().get('add_all', {})

        kwargs = {'vif_ips': set_value}
        return kwargs

    def _handle_set_request(self, col_name, new_val):
        """
        _handle_set_request
        """
        old_val = set()
        # get the current value for this object from riak
        # try:
        #     rr = []
        #     old_val = set()
        #     client = riak_client.RiakClient()
        #     rr.append(client.read(self))
        #     if rr:
        #         rec = self.transform_read_request(rr[0])
        #         old_val = rec.get(col_name, set())
        # except Exception as err:
        #     _ = err
        #     # When writing data for the first time there will be no records.
        #     pass

        # just in case set was converted to list on response handling, make
        # sure both vals are of type 'set'
        new_val = set(new_val)
        old_val = set(old_val)
        # remove everything that was there previously but is not now
        remove_set = old_val - new_val
        add_set = new_val - old_val
        # cast them to a list for the riak_datatypes schema
        set_val = riak_datatypes.Set(
            add_all=list(add_set), remove_all=list(remove_set))
        return set_val

    @property
    def map_create_request(self):
        """
        map_create_request
        """
        map_entries = []
        for col_name, col_def in self._columns.iteritems():
            map_entry = riak_datatypes.MapEntry()
            if col_def.schema_name is None:
                raise RuntimeError('All map records must have a schema_name '
                                   'defined')
            if col_def.schema_name.endswith('_counter'):
                name = 'increment'
                value = 0
                if col_def.column_type == bool:
                    if getattr(self, col_name, False):
                        value = 1
                elif col_def.column_type == int:
                    value = getattr(self, col_name, 0)
                    if value < 0:
                        value, name = abs(value), 'decrement'
                map_entry.name = col_name
                map_entry.value = riak_datatypes.Counter(**{name: value})
            elif col_def.schema_name.endswith('_flag'):
                if col_def.column_type == bool:
                    value = getattr(self, col_name, False)
                    map_entry.name = col_name
                    map_entry.value = riak_datatypes.Flag(bool(value))
            elif col_def.schema_name.endswith('_register'):
                if getattr(self, col_name, None) is not None:
                    map_entry.name = col_name
                    map_entry.value = riak_datatypes.Register(
                        value=str(getattr(self, col_name)))
            elif col_def.schema_name.endswith('_set'):
                if getattr(self, col_name, None) is not None:
                    map_entry.name = col_name
                    new_val = getattr(self, col_name)
                    map_entry.value = self._handle_set_request(
                        col_name, new_val)
            map_entries.append(map_entry)
        map_value = riak_datatypes.Map(update=map_entries)
        return riak_datatypes.UpdateMap(
            bucket=self.bucketname,
            datatype=self.indexname,
            key=str(uuid.uuid4()),
            data=map_value)
