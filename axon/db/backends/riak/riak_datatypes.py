#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

"""
This module contains schema objects to manipulate riak data types (sets, maps
and counters)
"""
import os.path

from axon.db.dataclass_factory import dataclass_factory
import axon.db.backends.riak.formatters as input_formatters
import axon.db.backends.riak.formatters as output_formatters

HTTP_VERBS = (GET, POST, PUT, DELETE) = ("GET", "POST", "PUT", "DELETE")

Counter = dataclass_factory(
    'Counter', ['type', 'value', 'increment', 'decrement'],
    excludes=('type', 'value'))

Flag = dataclass_factory(
    'Flag', ['flag'],
    output_formatters={'flag': output_formatters.flag_formatter})

Register = dataclass_factory('Register', ['value'])

Set = dataclass_factory(
    'Set', ['remove_all', 'add_all', 'type', 'value', 'context'],
    excludes=(
        'type',
        'value',
        'context',
    ),
    input_formatters={'value': input_formatters.type_formatter(set)})


def map_validator(self, value):
    """
    Validates all the separate datatypes

    Parameters
    ----------
    value : [Map, Counter, Set, Register, Flag]
        this constrains the update field to a understood crdt
    """
    _ = self  # ignored
    crdts = (Counter, Set, Register, Flag, Map)
    return isinstance(value, crdts)


MapEntry = dataclass_factory('MapEntry', ['name', 'value'])

Map = dataclass_factory(
    'Map',
    ['update', 'type', 'value', 'context', 'error'],
    excludes=(
        'type',
        'value',
        'context',
    ),
    input_formatters={
        'value': input_formatters.input_map_formatter,
        'update': input_formatters.reverse_update
    },
    output_formatters={'update': output_formatters.output_map_formatter},
)


CreateCounter = dataclass_factory(
    'CreateCounter', ['path', 'verb', 'headers', 'bucket', 'key',
                      'reply_headers', 'data', 'datatype'],
    required=('bucket', 'key',),
    initializers={
        'verb': lambda: POST, 'path': lambda: '/types',
        'headers': lambda: {'Content-Type': 'application/json'},
        'datatype': lambda: 'counters',
        'data': lambda: Counter(increment=0)
    },
    input_formatters={
        'data': input_formatters.json_formatter(Counter)
    },
    output_formatters={
        'path': output_formatters.append_path_elem(
            ['datatype', 'buckets', 'bucket', 'datatypes', 'key']),
        'data': output_formatters.to_json
    }
)


SetCounter = dataclass_factory(
    'SetCounter', ['path', 'verb', 'headers', 'data', 'bucket', 'key',
                   'reply_headers', 'datatype'],
    required=('bucket', 'key',),
    initializers={
        'verb': lambda: POST, 'path': lambda: '/types',
        'headers': lambda: {'Content-Type': 'application/json'},
        'datatype': lambda: 'counters',
    },
    input_formatters={
        'data': input_formatters.json_formatter(Counter)
    },
    output_formatters={
        'path': output_formatters.append_path_elem(
            ['datatype', 'buckets', 'bucket', 'datatypes', 'key']),
        'data': output_formatters.to_json
    })

GetCounter = dataclass_factory(
    'GetCounter', [
        'path', 'verb', 'headers', 'bucket', 'key', 'reply_headers',
        'response', 'datatype'
    ],
    required=(
        'bucket',
        'key',
    ),
    initializers={
        'verb': lambda: GET,
        'path': lambda: '/types',
        'datatype': lambda: 'counters',
    },
    input_formatters={'response': input_formatters.json_formatter(Counter)},
    output_formatters={
        'path':
        output_formatters.append_path_elem(
            ['datatype', 'buckets', 'bucket', 'datatypes', 'key']),
    })


UpdateSet = dataclass_factory(
    'UpdateSet', ['path', 'verb', 'headers', 'data', 'bucket', 'key',
                  'reply_headers', 'datatype'],
    required=('bucket', 'key',),
    initializers={
        'verb': lambda: POST, 'path': lambda: '/types',
        'headers': lambda: {'Content-Type': 'application/json'},
        'datatype': lambda: 'sets',
    },
    input_formatters={
        'data': input_formatters.json_formatter(Set)
    },
    output_formatters={
        'path': output_formatters.append_path_elem(
            ['datatype', 'buckets', 'bucket', 'datatypes', 'key']),
        'data': output_formatters.to_json
    })

GetSet = dataclass_factory(
    'GetSet', [
        'path', 'verb', 'headers', 'bucket', 'key', 'reply_headers',
        'response', 'datatype'
    ],
    required=(
        'bucket',
        'key',
    ),
    initializers={
        'verb': lambda: GET,
        'path': lambda: '/types',
        'datatype': lambda: 'sets',
    },
    input_formatters={'response': input_formatters.json_formatter(Set)},
    output_formatters={
        'path':
        output_formatters.append_path_elem(
            ['datatype', 'buckets', 'bucket', 'datatypes', 'key']),
    })

UpdateMap = dataclass_factory(
    'UpdateMap', ['path', 'verb', 'headers', 'data', 'bucket', 'key',
                  'reply_headers', 'datatype'],
    required=('bucket', 'key',),
    initializers={
        'verb': lambda: POST, 'path': lambda: '/types',
        'datatype': lambda: 'maps',
        'headers': lambda: {'Content-Type': 'application/json'},
    },
    input_formatters={
        'data': input_formatters.json_formatter(Map)
    },
    output_formatters={
        'path': output_formatters.append_path_elem(
            ['datatype', 'buckets', 'bucket', 'datatypes', 'key']),
        'data': output_formatters.to_json
    })

GetMap = dataclass_factory(
    'GetMap', [
        'path', 'verb', 'headers', 'bucket', 'key', 'reply_headers',
        'response', 'datatype'
    ],
    required=(
        'bucket',
        'key',
    ),
    initializers={
        'verb': lambda: GET,
        'path': lambda: '/types',
        'datatype': lambda: 'maps',
    },
    input_formatters={'response': input_formatters.json_formatter(Map)},
    output_formatters={
        'path':
        output_formatters.append_path_elem(
            ['datatype', 'buckets', 'bucket', 'datatypes', 'key']),
    })

# This covers the object crud operations for riak

Link = dataclass_factory(
    'Link', ['location', 'tag'],
    required=(
        'location',
        'tag',
    ),
    excludes=('tag', ),
    output_formatters={'location': output_formatters.link_location})

LinkRequest = dataclass_factory(
    'LinkRequest', ['bucket', 'tag', 'keep'],
    initializers={
        'bucket': lambda: '_',
        'tag': lambda: '_',
        'keep': lambda: '1'
    })

GetObjectParams = dataclass_factory(
    'GetObjectParams', ['r', 'pr', 'basic_quorum', 'notfound_ok', 'vtag'])

CreateObjectParams = dataclass_factory(
    'CreateObjectParams', ['w', 'dw', 'pw', 'returnbody'],
    initializers={'returnbody': lambda: False})

GetObject = dataclass_factory(
    'GetObject', [
        'path', 'verb', 'params', 'response', 'headers', 'bucket', 'key',
        'reply_headers'
    ],
    required=(
        'bucket',
        'key',
    ),
    initializers={
        'verb': lambda: GET,
        'path': lambda: '/buckets',
        'headers': lambda: {}
    },
    output_formatters={
        'key': lambda _, value: str(value),
        'path': output_formatters.append_path_elem(['bucket', 'keys', 'key']),
    })

GetObjectByLink = dataclass_factory(
    'GetObjectByLink', ['link_requests'],
    input_formatters={
        'link_requests': input_formatters.list_of_type_formatter(LinkRequest),
    },
    output_formatters={
        'path': output_formatters.build_link_query_path,
    },
    inheirits=GetObject)

GetObjectByIndex = dataclass_factory(
    'GetObjectByIndex', ['indexed_by'],
    required=(
        'bucket',
        'indexed_by',
        'key',
    ),
    output_formatters={
        'key':
        lambda _, value: str(value),
        'path':
        output_formatters.append_path_elem(
            ['bucket', 'index', 'indexed_by', 'key']),
    },
    inheirits=GetObject)

GetJSONObject = dataclass_factory(
    'GetJSONObject', [],
    input_formatters={'response': input_formatters.json_loader},
    inheirits=GetObject)


def get_riak_key(create_obj):
    if hasattr(create_obj, 'reply_headers'):
        if 'location' in create_obj.reply_headers:
            return create_obj.reply_headers['location'].split(os.path.sep)[-1]


CreateObject = dataclass_factory(
    'CreateObject', ['path', 'verb', 'headers', 'params', 'data',
                     'bucket', 'key', 'reply_headers', 'links'],
    required=('bucket',),
    excludes=('links',),
    initializers={
        'verb': lambda: PUT, 'path': lambda: '/buckets',
        'headers': lambda: {'Content-Type': 'application/octet-stream'},
    },
    input_formatters={
        'reply_headers': input_formatters.set_key_from_location,
    },
    output_formatters={
        'path': output_formatters.append_path_elem(['bucket', 'keys', 'key']),
        'headers': output_formatters.add_links,
    })

# this allows riak to create the key
CreateRiakObject = dataclass_factory(
    'CreateRiakObject', [],
    initializers={'verb': lambda: POST},
    output_formatters={
        'path': output_formatters.append_path_elem(['bucket', 'keys']),
    },
    inheirits=CreateObject)


CreateJSONRiakObject = dataclass_factory(
    'CreateJSONRiakObject', [],
    initializers={'headers': lambda: {'Content-Type': 'application/json'}},
    inheirits=CreateRiakObject)


CreateJSONObject = dataclass_factory(
    'CreateJSONObject', [],
    initializers={'headers': lambda: {'Content-Type': 'application/json'}},
    inheirits=CreateObject)

DeleteObject = dataclass_factory(
    'DeleteObject', ['path', 'verb', 'headers', 'bucket', 'key'],
    required=(
        'bucket',
        'key',
    ),
    initializers={
        'verb': lambda: DELETE,
        'path': lambda: '/buckets'
    },
    output_formatters={
        'path': output_formatters.append_path_elem(['bucket', 'keys', 'key']),
    })

# This contains the Riak 2.1+ Search API

SchemaType = dataclass_factory(
    'SchemaType', [
        'name', 'class', 'sortMissingLast', 'precisionStep',
        'positionIncrementGap'
    ],
    required=(
        'name',
        'class',
    ),
    initializers={
        'sortMissingLast': lambda: False,
    },
    input_formatters={
        'sortMissingLast': input_formatters.json_loader,
        'precisionStep': input_formatters.json_loader,
        'positionIncrementGap': input_formatters.json_loader,
    },
    output_formatters={'sortMissingLast': output_formatters.to_json})

SchemaField = dataclass_factory(
    'SchemaField', [
        'name', 'type', 'indexed', 'stored', 'required', 'multiValued',
        'omitNorms'
    ],
    required=('name', ),
    initializers={
        'indexed': lambda: False,
        'stored': lambda: False,
        'type': lambda: 'string',
        'required': lambda: False,
        'omitNorms': lambda: True,
        'multiValued': lambda: False
    },
    input_formatters={
        'indexed': input_formatters.json_loader,
        'stored': input_formatters.json_loader,
        'required': input_formatters.json_loader,
        'omitNorms': input_formatters.json_loader,
        'multiValued': input_formatters.json_loader
    },
    output_formatters={
        'indexed': output_formatters.to_json,
        'stored': output_formatters.to_json,
        'required': output_formatters.to_json,
        'omitNorms': output_formatters.to_json,
        'multiValued': output_formatters.to_json
    })

SearchSchema = dataclass_factory(
    'SearchSchema', ['name', 'fields', 'types', 'dynamic_fields'],
    initializers={
        'name': lambda: '_yz_default',
        'fields': lambda: [],
        'types': lambda: [],
        'dynamic_fields': lambda: []
    })

SearchIndex = dataclass_factory(
    'SearchIndex', ['schema', 'name', 'n_val'],
    required=('name', ),
    excludes=('name', ),
    initializers={'schema': lambda: SearchSchema()},
    output_formatters={'schema': output_formatters.attrgetter('schema.name')},
    input_formatters={'schema': input_formatters.type_formatter(SearchSchema)})

QuerySpec = dataclass_factory('QuerySpec', ['op', 'left', 'right'])

QueryParams = dataclass_factory(
    'QueryParams', ['wt', 'q', 'start', 'sort', 'rows', 'fq', 'fl', 'cache'],
    initializers={
        'wt': lambda: 'json',
        'cache': lambda: True
    },
    input_formatters={
        'q': input_formatters.from_solr_query,
        'cache': input_formatters.json_loader
    },
    output_formatters={
        'q': output_formatters.to_solr_query,
        'cache': output_formatters.to_json
    })

QueryResponse = dataclass_factory('QueryResponse',
                                  ['docs', 'start', 'maxScore', 'numFound'])

QueryError = dataclass_factory('QueryError', ['msg', 'code', 'trace'])

QueryResults = dataclass_factory(
    'QueryResults', ['response', 'responseHeader', 'error'],
    initializers={'error': lambda: None},
    input_formatters={
        'response': input_formatters.dict_formatter(QueryResponse),
        'error': input_formatters.dict_formatter(QueryError)
    })

QuerySearchIndex = dataclass_factory(
    'QuerySearchIndex',
    ['path', 'verb', 'headers', 'data', 'reply_headers', 'response', 'params'],
    excludes=('data', ),
    initializers={
        'verb': lambda: GET,
        'path': lambda: '/search/query',
    },
    input_formatters={
        'params':
        input_formatters.from_solr_query_params(
            QueryParams, input_formatters.dict_formatter),
        'response':
        input_formatters.json_formatter(QueryResults)
    },
    output_formatters={
        'path': output_formatters.append_path_elem(['data.name']),
        'params': output_formatters.to_solr_query_params
    })

# This adds support for Riak's HTTP Counters

IncrementCounter = dataclass_factory(
    'IncrementCounter', [],
    required=(
        'bucket',
        'key',
        'data',
    ),
    initializers={'verb': lambda: POST},
    output_formatters={
        'path':
        output_formatters.append_path_elem(['bucket', 'counters', 'key']),
        'data': output_formatters.to_type(str),
    },
    inheirits=CreateObject)

GetCounter = dataclass_factory(
    'GetCounter', [],
    input_formatters={'response': input_formatters.type_formatter(int)},
    output_formatters={
        'path':
        output_formatters.append_path_elem(['bucket', 'counters', 'key']),
    },
    inheirits=GetObject)
