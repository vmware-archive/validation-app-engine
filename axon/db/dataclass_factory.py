#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

"""
The base schema object and a class factory creator.
"""
import collections
import datetime
import inspect
import json
import re
import six
import sys
import time
import uuid

COLLECTION_MARKER = "[]"


def _return_schema(cls, kwargs):
    """
    Higher protcol pickles need instructions on the values to set

    Parameters
    ----------
    cls : SchemaBase
        The schema class being unpickled
    kwargs : {schema_field: value, ...}
        The values the schema class was created with
    """
    return cls(**kwargs)


def convert(name):
    """
    convert CamelCase to snake_case

    >>> convert('CamelCase')
    'camel_case'
    >>> convert('CamelCamelCase')
    'camel_camel_case'
    >>> convert('Camel2Camel2Case')
    'camel2_camel2_case'
    >>> convert('getHTTPResponseCode')
    'get_http_response_code'
    >>> convert('get2HTTPResponseCode')
    'get2_http_response_code'
    >>> convert('HTTPResponseCode')
    'http_response_code'
    >>> convert('HTTPResponseCodeXYZ')
    'http_response_code_xyz'
    """
    first_cap_re = re.compile('(.)([A-Z][a-z]+)')
    all_cap_re = re.compile('([a-z0-9])([A-Z])')
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


class SchemaJsonEncoder(json.JSONEncoder):
    """
    handles various encoding quirks when turning a schema object
    into valid json.
    """

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return int(time.mktime(obj.timetuple()))
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, SchemaBase):
            return obj.as_json()
        if inspect.isclass(obj):
            return str(obj.__name__)
        if inspect.isfunction(obj):
            return str(obj.__name__)
        # if all else fails, or at least for debugging
        try:
            json.dumps(obj)
        except TypeError:
            return "TypeError: %s" % str(obj)
        return json.JSONEncoder.default(self, obj)


class SchemaMeta(type):
    def __new__(cls, name, bases, dct):
        # This ensures that inheiritance is aggregating _fields,
        # _validators and what not
        for attrname in ['_fields', '_excludes', '_required']:
            new_attrvals = list(dct[attrname])
            dct[attrname] = []
            for base in bases:
                dct[attrname].extend(list(getattr(base, attrname, ())))
            dct[attrname].extend(new_attrvals)
            # ensures each attribute only shows up once
            # esx schemas don't use kwargs, we have to preserve ordering
            # python 2.6 on vyatta doesn't have OrderedDict, but the schemas
            # used there shouldn't be impacted too much by duplicate fields.
            if (2, 7) < sys.version_info:
                dct[attrname] = list(
                    collections.OrderedDict.fromkeys(dct[attrname]))
            dct[attrname] = tuple(dct[attrname])

        dict_attrs = [
            '_validators', '_initializers', '_in_formatters',
            '_out_formatters', '_references'
        ]
        if bases:
            last_base = bases[-1]
            for attrname in dict_attrs:
                last_attrs = getattr(last_base, attrname, {})
                if dct.get(attrname) is None:
                    dct[attrname] = last_attrs
                else:
                    new_attrs = dct[attrname]
                    for aname, aval in last_attrs.items():
                        if aname not in new_attrs:
                            dct[attrname][aname] = aval
        fields = list(dct['_fields'])
        fields.append('__weakref__')
        dct['__slots__'] = tuple(fields)
        # So it is possible that we will try and assign a __weakref__
        # twice via inheiritance.  This catches that.
        try:
            return type.__new__(cls, name, bases, dct)
        except TypeError:
            dct['__slots__'] = tuple(dct['_fields'])
            return type.__new__(cls, name, bases, dct)


@six.add_metaclass(SchemaMeta)
class SchemaBase(object):
    """
    This is the base class for the schemas created by the schema factory
    below.

    Attributes
    ----------
    _fields : ['attr1', 'attr2',....]
        The names of the attributes of the schema child class.
    _validators : {'attr': validator_func(instance_obj, value), ...}
        A mapping of attribute names to validator functions
    _initializers : {'attr': initializer_func(),...}
        A mapping of attribute names to initializer functions
    _in_formatters : {'attr': input_fomatter(value),...}
        A mapping of attribute names to input formatters
    _out_formatters : {'attr': output_formatter(instance_obj, value),...}
        A mapping of attribute names to output formatters
    _excludes : ('attr1', 'attr2',...)
        A tuple of attribute names to exclude
    _required : ('attr1', 'attr2', ...)
        A tuple of attribute names that must be defined
    """

    _fields = ()
    _validators = None
    _initializers = None
    _in_formatters = None
    _out_formatters = None
    _references = None
    _excludes = ()
    _required = ()

    def __new__(cls, *args, **kwargs):
        """
        This function is where the newly created object has its
        initializers called and validators called after attribute
        assignation has happened
        """
        new_inst = super(SchemaBase, cls).__new__(cls)
        val_dict = dict(list(zip(cls._fields, args)))
        val_dict.update(kwargs)
        for field, initializer in cls._initializers.items():
            if field not in val_dict:
                val_dict[field] = initializer()
        for attrname, attrval in val_dict.items():
            if attrname in cls._references:
                # if we are initializing a schema with the reference target
                # instead of the reference source, we bypass reference
                # resolution for that attribute. Main use
                # case is deserialization via cls._from_dict()
                object.__setattr__(new_inst, attrname, attrval)
            else:
                setattr(new_inst, attrname, attrval)
        for attr in cls._required:
            try:
                _ = getattr(new_inst, attr)
            except AttributeError:
                raise ValueError('%s is required' % attr)
        return new_inst

    def __reduce__(self):
        """
        Hinting for higher protocol pickles
        """
        kwargs = {}
        for field in self._fields:
            if hasattr(self, field):
                if field not in self._references:
                    kwargs[field] = getattr(self, field)
        return _return_schema, (self.__class__, kwargs), None

    def __setattr__(self, name, value):
        """
        When we set attributes the validators are invoked here.
        """
        if name in self._validators:
            validators = self._validators[name]
            if callable(validators):
                validators = (validators, )
            for validator in validators:
                if not validator(self, value):
                    if inspect.isfunction(validator):
                        msg = ("Validator (%s) failed: %s => %r not valid "
                               "value" % (inspect.getsource(validator), name,
                                          value))
                    else:
                        # The istype() validator is an object, not a function
                        msg = ("Validator (%s) failed: %s => %r not valid "
                               "value" % (validator.__class__.__name__, name,
                                          value))
                    raise ValueError(msg)
        if name in self._references:
            reference_target = self._references[name]
            ref_targets = reference_target.split(".")
            ref_base = ref_targets[0]
            ref_terminal = ref_targets[-1]
            ref_targets = ref_targets[1:-1]
            ref_attr = getattr(self, ref_base, None)
            if not ref_attr:
                raise RuntimeError(
                    "The reference target object \"%s\" has not been assigned "
                    "to this schema object (%s). It must be assigned before "
                    "accessing the reference \"%s\"." %
                    (ref_base, type(self).__name__, name))
            for ref_subattr in ref_targets:
                ref_attr = getattr(ref_attr, ref_subattr)
            setattr(ref_attr, ref_terminal, value)
            return
        super(SchemaBase, self).__setattr__(name, value)

    @classmethod
    def _as_dict_parse(cls, attr):
        if hasattr(attr, '_as_dict'):
            return attr._as_dict()
        elif isinstance(attr, (list, tuple)):
            return [cls._as_dict_parse(subattr) for subattr in attr]
        elif isinstance(attr, dict):
            dtuple = iter(attr.items())
            return {key: cls._as_dict_parse(sattr) for key, sattr in dtuple}
        else:
            return attr

    def _as_dict(self):
        """
        transforms the schema object into a dictionary.  Any attributes with
        a _as_dict method (like schema objects for example) will have their
        _as_dict methods called
        """
        ret_val = {}
        for fname in self._fields:
            if fname in self._excludes:
                continue
            try:
                parsed = self._as_dict_parse(getattr(self, fname, None))
                formatted = self._out_formatters[fname](self, parsed)
                # TODO: This if statement prevents intentionally using None
                # values for attribute values
                if formatted is not None:
                    ret_val[fname] = formatted
            except AttributeError:
                pass
        return ret_val

    def __getattr__(self, attrname):
        if attrname in self._references:
            reference_target = self._references[attrname]
            attrlist = reference_target.split(".")
            ref_attr = attrlist[0]
            ref_target = attrlist[1]
            if COLLECTION_MARKER in ref_attr:
                # only supports one level of reference collection currently
                ref_attr = ref_attr.strip(COLLECTION_MARKER)
                ref_collection = getattr(self, ref_attr, set())
                target_set = set()
                for elem in ref_collection:
                    target_set.add(getattr(elem, ref_target, None))
                return target_set
            subattr = self
            for attr in attrlist:
                subattr = getattr(subattr, attr, None)
                if not subattr:
                    # usually if no reference object was set on this instance
                    return object.__getattribute__(self, attrname)
            return subattr
        return object.__getattribute__(self, attrname)

    @classmethod
    def _as_json_helper(cls, attr):
        if hasattr(attr, 'as_json'):
            return attr.as_json()
        elif isinstance(attr, (list, tuple)):
            recursed_formatted = [
                cls._as_json_helper(subattr) for subattr in attr
            ]
            return recursed_formatted
        elif isinstance(attr, dict):
            dtuple = iter(attr.items())
            return {key: cls._as_json_helper(sattr) for key, sattr in dtuple}
        else:
            return attr

    def as_json(self, include_empty=False):
        """
        recursively serializes the schema object to pretty json.

        mainly meant for debugging/readability of the graph.
        output formatters can do a lot of things like make api calls/riak
        calls, so we don't run them by default

        Parameters
        ----------
        include_empty: bool
            whether to include empty schema fields. defaults to false since
            many fields are unused by us
        """
        self_dict = {}
        for fname in self._fields:
            fval = getattr(self, fname, None)
            if fval is None and not include_empty:
                continue
            fval = self._as_json_helper(fval)
            self_dict[fname] = fval
        return self_dict

    def __getitem__(self, name):
        try:
            return getattr(self, name)
        except AttributeError:
            raise KeyError

    def get(self, name, default=None):
        return getattr(self, name, default)

    @classmethod
    def _from_dict(cls, input_dict):
        kwargs = {}
        for fname, value in input_dict.items():
            if value is None:
                continue
            kwargs[fname] = cls._in_formatters[fname](value)
        return cls(**kwargs)

    def __getstate__(self):
        """
        A bunch of problems in serialization stem from calling
        the output formatters as _as_dict does.
        """
        ret_val = {}
        for fname in self._fields:
            if fname in self._excludes:
                continue
            if fname in self._references:
                continue
            try:
                ret_val[fname] = getattr(self, fname)
            except AttributeError:
                pass
        return ret_val

    def __setstate__(self, state):
        """
        There really isn't a need to call the input formatters here either.

        Parameters
        ----------
        state : dict
            The dictionary of non-None attributes
        """
        for fname, value in state.items():
            if fname in self._references:
                continue
            setattr(self, fname, value)

    def __repr__(self):
        vals = [
            '%s=%r' % (fname, getattr(self, fname)) for fname in self._fields
            if hasattr(self, fname)
        ]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(vals))


def _check_func(fmap, argcount, func_type):
    """
    This is a little helper function to check the argument
    counts on a mapping of functions
    """
    for funcs in fmap.values():
        if callable(funcs):
            funcs = (funcs, )
        for func in funcs:
            # func might be a callable object; if so make the necessary tweaks
            if inspect.isfunction(func):
                _argcount = argcount
            else:
                func = func.__call__
                _argcount = argcount + 1
            if len(inspect.getargspec(func).args) != _argcount:
                raise TypeError(
                    '%s functions take %d arguments' % (func_type, argcount))


def dataclass_factory(clsname,
                      attrlist,
                      validators=None,
                      initializers=None,
                      input_formatters=None,
                      output_formatters=None,
                      excludes=None,
                      required=None,
                      inheirits=None,
                      references=None):
    """
    This is a class factory for NSX logical schema objects. LSwitches,
    LRouters and so forth.  Transport specific implmentations of actions
    on these schema values are located in subpackages of this package.  So
    ./http/lswitch.py for example would hold http specific schema objects
    while ./lswitch.py would look something like:

    from axon.utils.dataclass_factory import dataclass_factory


    LSwitch = dataclass_factory(
        'LSwitch', ['attr1', 'attr2',...], initializers={'attr1': lambda: 0},
        validators={'attr2': lambda x, y: y is not None})

    Parameters
    ----------
    clsname : string
        The name of the class type being returned
    attrlist : [string1, string2,...]
        A list of the attribute names for this class object being built
    validators : {'attribute1': 2 arg function or tuple of 2 arg functions,
                  ....}, optional
        This is a map of the above attribute names to a function taking 2
        arguments (the instance value and the value to validate) or a tuple of
        functions taking 2 arguments. This validates the attibute
        initialization as well as the attribute setting
    initializers: {'attribute1': 0 arg function,....}, optional
        This is a map of the above attribute names to a function
        taking 0 args.  This initializes the attribute to a specific
        value.
    input_formatters: {'attribute1': 1 arg function,....}, optional
        This is a 1 arg function (the value being formatted) that formats a
        given attribute for something more amenable to loading a schema object.
    output_formatters: {'attribute1': 2 arg function,....}, optional
        This is a 2 arg function (the instance object and the value being
        formatted) that formats a given attribute for something maybe more
        amenable to parsing.
    excludes : list, optional
        A set of attributes to be excluded in the _as_dict call. This is used,
        for example, in the graph code to prevent multiple definitions of the
        same objects.
    required : list, optional
        The list of attributes that must be set on the instance.
    inherits : SchemaBase class
        A different base class.  All _fields, validators etc will be aggregated
    references: dict, optional
        A mapping of attributes on this schema object that refer to attributes
        on a different schema object. the target attr is in the form of
        a string of attrs (i.e. attr.subattr.subattr) where the first
        part of the target must be an attribute on the same schema, and
        subsequent subattrs allow references to arbitrarily nested
        attributes. This allows get/set actions on the attribute to be passed
        to the target, so that updates to the target object will be reflected
        in all referring schemas automatically.
    """
    validators = {} if not validators else validators
    _check_func(validators, 2, 'Validator')

    initializers = {} if not initializers else initializers
    _check_func(initializers, 0, 'Initializer')

    input_formatters = {} if not input_formatters else input_formatters
    _check_func(input_formatters, 1, 'Input Formatter')

    output_formatters = {} if not output_formatters else output_formatters
    _check_func(output_formatters, 2, 'Output Formatter')

    references = {} if not references else references

    excludes = () if not excludes else excludes
    required = () if not required else required
    bases = (SchemaBase, )

    if inheirits is not None:
        if not issubclass(inheirits, SchemaBase):
            raise ValueError('Any base class must be a SchemaBase child')
        bases = (inheirits, )

    result = type(
        clsname, bases, {
            '_fields':
            tuple(attrlist),
            '_in_formatters':
            collections.defaultdict(lambda: lambda x: x, input_formatters),
            '_out_formatters':
            collections.defaultdict(lambda: lambda _, x: x, output_formatters),
            '_references':
            references,
            '_validators':
            validators,
            '_initializers':
            initializers,
            '_excludes':
            excludes,
            '_required':
            required
        })
    # caught this in namedtuple we need to line the module up to the
    # stack frame globals otherwise pickling doesn't work since the
    # module of the created type will be this module
    try:
        result.__module__ = sys._getframe(1).f_globals.get(
            '__name__', '__main__')
    except (AttributeError, ValueError):
        pass
    return result
