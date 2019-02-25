#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

"""
This contains output formatters specific to the riak http protocol
"""
import collections
import inspect
import json
import operator
import os
import os.path
import struct
# python 2 and 3 compatibility
import six.moves.urllib as urllib


def build_cls_hierarchy(cls, cls_hierarchy):
    cls_hierarchy.add(cls)
    for sub_cls in cls.__subclasses__():
        build_cls_hierarchy(sub_cls, cls_hierarchy)


def json_loader(value):
    """
    Passthrough for json.loads
    """
    return json.loads(value)


def json_list_formatter(cls):
    """
    This returns a function to map a given list of dictionaries
    to a list of class instances via a _from_dict class method.
    This input value is a json string.

    Parameters
    ----------
    cls : class with a _from_dict method
        The class instance to cast the dict to
    """
    return lambda value: [
        dict_formatter(cls)(obj_dict) for obj_dict in json.loads(value)]


def type_formatter(cls):
    """
    This casts the value to the type specified above

    Parameters
    ----------
    cls : type class
        The type to cast to
    """
    return lambda value: cls(value)


def list_of_type_formatter(cls):
    """
    This casts the value to a list type specified above

    Parameters
    ----------
    cls : type class
        The type to cast to
    """
    return lambda value: [cls(val) for val in value]


def json_formatter(cls):
    """
    This returns a function to map a json dictionary to a
    class instance of the passed in class via its _from_dict
    method.

    Parameters
    ----------
    cls : class with a _from_dict method
        The class instance to cast the dict to
    """
    return lambda value: dict_formatter(cls)(json.loads(value))


def dict_formatter(cls):
    """
    This returns a function to map a dictionary to a class instance via
    a _from_dict method if it exists otherwise it just returns the value

    Parameters
    ----------
    cls : class with a _from_dict method
        The class instance to cast the dict to
    """

    def _dict_formatter(value):
        if hasattr(cls, '_from_dict'):
            try:
                # rabbitmq for one can have attributes with a '.'
                return cls._from_dict({
                    key.replace('.', '_'): val
                    for key, val in value.items()
                })
            except (AttributeError, ValueError) as e:
                cls_set = set()
                if cls is object or not inspect.isclass(cls):
                    cls_set = set([cls])
                else:
                    build_cls_hierarchy(cls, cls_set)
                for derived_cls in cls_set:
                    if not hasattr(derived_cls, '_from_dict'):
                        continue
                    try:
                        return derived_cls._from_dict(value)
                    except (AttributeError, ValueError):
                        pass
                raise e
        else:
            return value

    return _dict_formatter


def list_formatter(cls):
    """
    This returns a function to map a given list of dictionaries
    to a list of class instances via a _from_dict class method.
    There is a corner case in which a passed in class might be a
    primative like a string.  This also handles that case by skipping
    the _from_dict call.

    Parameters
    ----------
    cls : class with a _from_dict method
        The class instance to cast the dict to
    """

    def _lformatter(value):
        cls_hierarchy = set()
        if cls is object or not inspect.isclass(cls):
            cls_hierarchy = set([cls])
        else:
            build_cls_hierarchy(cls, cls_hierarchy)
        if not isinstance(value, (list, tuple)):
            value = [
                value,
            ]
        res = []
        for obj_dict in value:
            for i, _cls in enumerate(cls_hierarchy):
                # Test all classes in class hierarchy
                if hasattr(_cls, '_from_dict'):
                    try:
                        res.append(_cls._from_dict(obj_dict))
                        break
                    except (AttributeError, ValueError):
                        # Try next class in class hierarchy if the response
                        # object cannot be used to instatiante an object of
                        # the current class
                        if i == len(cls_hierarchy) - 1:
                            # This means none of the classes in the hierarchy
                            # are compatible for at least one of the items in
                            # the input list
                            raise
                else:
                    if not isinstance(obj_dict, _cls):
                        try:
                            res.append(_cls(obj_dict))
                            break
                        except (AttributeError, ValueError):
                            # Try next class in class hierarchy if the
                            # response object cannot be used to instatiante
                            # an object of the current class
                            if i == len(cls_hierarchy) - 1:
                                # This means none of the classes in the
                                # hierarchy are compatible for at least
                                # one of the items in the input list
                                raise
                    else:
                        res.append(obj_dict)
                        break
        return res

    return _lformatter


def link_location(self, value):
    """
    formats link headers according to the riak docs

    Parameters
    ----------
    self : lib.schema.riak.objects.Link
        The Link schema object
    value : string
        The location url of the link.
    """
    return '<%s>; riaktag="%s"' % (value, self.tag)


def add_links(self, value):
    """
    This creates a Link header from the links

    Parameters
    ----------
    self : lib.schema.riak.objects.Link
        The Link schema object
    value : dict
        The headers of the request to add the links to
    """
    links = getattr(self, 'links', [])
    if links:
        value['Link'] = ', '.join(
            link._as_dict()['location'] for link in links)
    return value


def build_link_query_path(self, value):
    """
    Building a query path with links requires a bit beyond the
    regular path appender. This handles that extra

    Parameters
    ----------
    self : lib.schema.riak.GetObjectByLink
        The schema element we are building out
    value : string
        The base path to build out of.
    """
    base_path = append_path_elem(['bucket', 'keys', 'key'])(self, value)
    link_paths = [
        ','.join((lreq.bucket, lreq.tag, lreq.keep))
        for lreq in self.link_requests
    ]
    full_path = [base_path] + link_paths
    return '/'.join(full_path)


def to_solr_query(self, value):
    """
    This turns a list of query spec items into a complete urlsafe
    query string

    Parameters
    ----------
    value : dict
        The query parameters
    """
    _ = self  # pylint
    if hasattr(value, '_as_dict'):
        value = value._as_dict()
    stack, root = [(None, value)], value
    while stack:
        parent, value = stack.pop()
        right_str = isinstance(value['right'], str)
        left_str = isinstance(value['left'], str)
        if not left_str and value['left']['op'] == ':':
            value['left'] = '%s:%s' % (value['left']['left'],
                                       value['left']['right'])
        if not right_str and value['right']['op'] == ':':
            value['right'] = '%s:%s' % (value['right']['left'],
                                        value['right']['right'])
        right_str = isinstance(value['right'], str)
        left_str = isinstance(value['left'], str)
        if parent is not None:
            attrname = 'right' if parent['right'] == value else 'left'
            if right_str and left_str:
                logic = '%s %s %s' % (value['left'], value['op'].upper(),
                                      value['right'])
                if parent['op'] != value['op']:
                    logic = '( %s %s %s )' % (
                        value['left'], value['op'].upper(), value['right'])
                parent[attrname] = logic
            else:
                stack.append((parent, value))
                if not right_str:
                    stack.append((value, value['right']))
                if not left_str:
                    stack.append((value, value['left']))
        else:
            if not left_str or not right_str:
                stack.append((parent, value))
            if not right_str:
                stack.append((value, value['right']))
            if not left_str:
                stack.append((value, value['left']))
    return '%s %s %s' % (root['left'], root['op'].upper(), root['right'])


def flag_formatter(self, value):
    """
    This formats the flag data type into a correct value for riak

    Parameters
    ----------
    value : boolean
        enable if true else disable
    """
    _ = self  # ignored
    return 'enable' if value else 'disable'


def output_map_formatter(self, value):
    """
    This handles formatting the update command for maps in a way
    that makes sense for the http api

    Parameters
    ----------
    value : ignored
        we need the untransformed value
    """
    if not getattr(self, 'update', None):
        return {}
    _ = value  # ignored
    ret_val = {}
    attr_map = collections.defaultdict(
        lambda: lambda x, attr: getattr(x, attr))
    attr_map['decrement'] = lambda x, attr: -1 * x.decrement
    attr_map['flag'] = lambda x, attr: x._as_dict()['flag']
    attr_map['add_all'] = attr_map['remove'] = lambda x, attr: x._as_dict()
    attr_map['update'] = lambda x, attr: x._as_dict()
    attrs = ('increment', 'value', 'add_all', 'remove', 'flag', 'update',
             'decrement')
    for map_entry in self.update:
        if not getattr(map_entry, 'name', None) or \
           not getattr(map_entry, 'value', None):
            continue
        key = '%s_%s' % (map_entry.name,
                         map_entry.value.__class__.__name__.lower())
        for attr in attrs:
            if hasattr(map_entry.value, attr):
                key_val = attr_map[attr](map_entry.value, attr)
                if isinstance(key_val, set):
                    key_val = list(key_val)
                ret_val[key] = key_val
                break
    return ret_val


def to_solr_query_params(self, value):
    """
    This turns a QueryParams dict into a flat list of tuples

    Parameters
    ----------
    value : dict
        The query parameters
    """
    _ = self  # pylint
    params = []
    if 'fq' in value:
        fqry = value.pop('fq')
        for fieldname, fieldvalue in fqry:
            params.append(('fq', '%s:%s' % (fieldname, fieldvalue)))
    params.extend(value.items())
    return params


"""
These input formatters are specific to the riak http api
"""


def set_key_from_location(value):
    """
    This is maybe a little bit magical but basically when
    the headers are being handled we look back in the stack and
    set the key as well since that is contained in the reply_headers

    Parameters
    ----------
    value : dict
        The current reply headers
    """
    curr_frame = inspect.currentframe()
    try:
        if curr_frame.f_back:
            kwargs = curr_frame.f_back.f_locals['kwargs']
            location = value.get('location')
            if location:
                kwargs['key'] = location.split(os.path.sep)[-1]
    finally:
        del curr_frame
    return value


def from_solr_query(value):
    """
    This takes a solr query back to the query spect from whence it came

    Parameters
    ----------
    value : string
        The query string
    """
    # avoid circular imports
    import axon.db.backends.riak.riak_datatypes as riak_datatypes
    tokens = collections.deque(value.split(' '))
    qdef = root = riak_datatypes.QuerySpec(left=None, right=None)
    while tokens:
        token = tokens.popleft()
        if ':' in token:
            left, right = token.split(':')
            local_qdef = riak_datatypes.QuerySpec(
                op=':', left=left, right=right)
            if isinstance(qdef.left, riak_datatypes.QuerySpec):
                qdef.right = local_qdef
            else:
                qdef.left = local_qdef
        elif token in '()':
            local_qdef = riak_datatypes.QuerySpec(left=None, right=None)
            if tokens:
                if isinstance(qdef.left, riak_datatypes.QuerySpec):
                    qdef.right = local_qdef
                else:
                    qdef.left = local_qdef
            qdef = local_qdef
        elif token.upper() in ('AND', 'OR'):
            if not hasattr(qdef, 'op'):
                qdef.op = token.lower()
            else:
                local_qdef = riak_datatypes.QuerySpec(
                    op=token.lower(), left=None, right=None)
                if qdef.op in ('or', 'and'):
                    if isinstance(qdef.left, riak_datatypes.QuerySpec):
                        local_qdef.left = qdef.right
                        qdef.right = local_qdef
                    else:
                        qdef.left = local_qdef
                qdef = local_qdef
    return root


def input_map_formatter(value):
    """
    This transforms the incoming map value into a list of map entries

    Parameters
    ----------
    value : dict
        The map value
    """
    ret_val = []
    import axon.db.backends.riak.riak_datatypes as riak_datatypes
    type_cls_set = set([
        (riak_datatypes.Counter,
            lambda inst, v: setattr(
                inst, 'decrement' if v < 0 else 'increment', abs(v))),
        (riak_datatypes.Register,
            lambda inst, v: setattr(inst, 'value', v)),
        (riak_datatypes.Flag,
            lambda inst, v: setattr(inst, 'flag', v is True or v == 'enable')),
        (riak_datatypes.Set,
            lambda inst, v: setattr(inst, 'value', set(v))),
        (riak_datatypes.Map,
            lambda inst, v: setattr(inst, 'value', input_map_formatter(v))),
    ])
    for key, value in value.items():
        typename, key = key.split('_')[-1], '_'.join(key.split('_')[:-1])
        type_cls = getattr(riak_datatypes, typename.capitalize())
        inst = type_cls()
        for tcls, map_func in type_cls_set:
            if tcls == type_cls:
                map_func(inst, value)
                break
        ret_val.append(riak_datatypes.MapEntry(name=key, value=inst))
    return ret_val


def reverse_update(value):
    """
    This transforms the incoming map value into a list of map entries

    Parameters
    ----------
    value : dict
        The map value
    """
    ret_val = []
    import axon.db.backends.riak.riak_datatypes as riak_datatypes
    type_cls_set = set([
        (riak_datatypes.Counter,
            lambda inst, v: setattr(
                inst, 'decrement' if v < 0 else 'increment', abs(v))),
        (riak_datatypes.Register,
            lambda inst, v: setattr(inst, 'value', v)),
        (riak_datatypes.Flag,
            lambda inst, v: setattr(inst, 'flag', v == 'enable')),
        (riak_datatypes.Set,
            lambda inst, v: [setattr(inst, attr, v[attr]) for attr in v]),
    ])
    for key, value in value.items():
        typename, key = key.split('_')[-1], '_'.join(key.split('_')[:-1])
        type_cls = getattr(riak_datatypes, typename.capitalize())
        inst = type_cls()
        for tcls, map_func in type_cls_set:
            if tcls == type_cls:
                map_func(inst, value)
                break
        ret_val.append(riak_datatypes.MapEntry(name=key, value=inst))
    return ret_val


def from_solr_query_params(cls, iformatter):
    """
    Turns the QueryParams dict back to a dict

    Parameters
    ----------
    cls : QueryParams,
        The qp class specification
    iformatter: dict_formatter
        The formatter to apply to this data
    """

    def _iformatter(value):
        val_dict = {'fq': []}
        for key, value in value:
            if key == 'fq':
                val_dict['fq'].append(tuple(value.split(':')))
            else:
                val_dict[key] = value
        return iformatter(cls)(val_dict)

    return _iformatter


# These are output formatters for schema objects


def to_json(self, value):
    """
    A small output formatter to dump a parameter to json
    """
    _ = self
    if hasattr(value, '_as_dict'):
        return json.dumps(value._as_dict())
    else:
        return json.dumps(value)


def attrgetter_as_json(attr):
    """
    Output formatter to get an attribute in json
    """

    def _attrgetter_as_json(self, value):
        value = operator.attrgetter(attr)(self)
        if hasattr(value, '_as_dict'):
            return json.dumps(value._as_dict())
        else:
            return json.dumps(value)

    return _attrgetter_as_json


def _append_path_elem_to_instance(path_attrs, self, value):
    """
    This descends to the attribute and joins it with the passed in value.
    """
    path_components = [value]
    for path_attr in path_attrs:
        attr = self
        for attrname in path_attr.split('.'):
            attr = getattr(attr, attrname, None)
            if attr is None:
                break
        if attr is None:
            attr = path_attr
        path_components.append(urllib.parse.quote(attr, safe='?='))
    return '/'.join(path_components)


def append_path_elem(attrs):
    """
    This does an os.path.join on a specific attribute from the schema object.
    To get subattributes of a schema object dot separate as you would for
    regular access to attributes.  So the value foo.bar on the attribute baz
    would return os.path.join(schema_obj.baz, schema_obj.foo.bar)

    Parameters
    ----------
    attrs : [list of strings]
        The attribute whose value is to be concatenated with the key
    """
    return lambda self, value: _append_path_elem_to_instance(
        attrs, self, value)


def attrgetter(attrname):
    """
    This gets one attribute as a substitute for another. An example of
    This is the attributes like: transport_zone_id which we want the value
    in transportzone.id
    """
    return lambda self, value: operator.attrgetter(attrname)(self)


def uuids_as_list(attrname):
    """
    Returns the UUIDs of objects in attrname
    """
    return (lambda self, value: [operator.attrgetter('id')(obj)
                                 for obj in operator.attrgetter(
            attrname)(self)])


def attrs_as_dict(attrs):
    """
    Given a list off attributes this returns a dictionary of those attributes
    on output

    Parameters
    ----------
    attrs : [strings]
        The attributes to get
    """

    def _attrs_as_dict(self, value):
        _ = value
        return {
            attr: getattr(self, attr)
            for attr in attrs if hasattr(self, attr)
        }

    return _attrs_as_dict


def _is_complex_type(value):
    """
    Could just as easily be called is_either_etree_node_list_or_dict

    Parameters
    ----------
    value : bytes
        The value to test.
    """
    return isinstance(value, (list, dict)) or hasattr(value, 'getchildren')


def to_bytes(struct_fmt):
    """
    Given a struct format we transform it to bytes on output

    Parameters
    ----------
    struct_fmt : string
        A format string suitable for struct.pack
    """

    def _pack(self, value):
        if isinstance(value, (tuple, list)):
            return struct.pack(struct_fmt, *value)
        else:
            return struct.pack(struct_fmt, value)

    return _pack


def to_type(cls):
    """
    Cast the data to a specific type

    Parameters
    ----------
    cls : class object
        The class to cast the object to
    """
    return lambda _, value: cls(value)


def extract_if_proxy_object(attr, proxy_obj_name, id_name):
    """
    In many scenarios we need id of parent object. We get parent_id from
    parent object stored as proxy object in object itself. While this mechanism
    works for POST, under certain circumstances it might fail. If GET of child
    object returns only parent_id and not parent object further PUT requests
    fail to generate parent_id from output formatter.

    Example:
    test_class = dataclass_factory(
        'test_class', ['p_id', p],
        output_formatters={
            'p_id': output_formatters.attrgetter('p.id'),
        })
    test_class(p=parent(id='XYZ'))._as_dict() ==> {'p_id': 'XYZ'}
    test_class(p_id='ABC')._as_dict() ==> {} should be {'p_id': 'ABC'}

    Parameters
    ----------
    attr: str
        Attribute which needs to be populated
    proxy_obj_name: str
        Attribute name where proxy object is stored
    id_name: str
        Attribute of proxy object which maps to attr

    Returns extracted value if proxy object is populated else attribute value
    """

    def __extract_if_proxy_object(self, value):
        if getattr(self, proxy_obj_name, None):
            id_obj = getattr(getattr(self, proxy_obj_name), id_name, None)
        else:
            id_obj = getattr(self, attr, None)
        if hasattr(id_obj, '_as_dict'):
            id_obj = id_obj._as_dict()
        return id_obj

    return __extract_if_proxy_object
