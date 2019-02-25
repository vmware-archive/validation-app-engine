#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import uuid

from sqlalchemy.orm import joinedload

from axon.db.local import models


class BaseRepository(object):
    model_class = None

    def count(self, session, **filters):
        return session.query(self.model_class).filter_by(**filters).count()

    def create(self, session, **model_kwargs):
        with session.begin(subtransactions=True):
            model = self.model_class(**model_kwargs)
            session.add(model)
        return model.to_dict()

    def delete(self, session, **filters):
        model = session.query(self.model_class).filter_by(**filters).one()
        with session.begin(subtransactions=True):
            session.delete(model)
            session.flush()

    def delete_batch(self, session, ids=None):
        ids = ids or []
        [self.delete(session, id=id) for id in ids]

    def delete_all(self, session):
        session.query(self.model_class).delete()
        session.flush()

    def get(self, session, **filters):
        model = session.query(self.model_class).filter_by(**filters).first()
        if not model:
            return {}
        return model.to_dict()

    def get_all(self, session, **filters):
        query = session.query(self.model_class).filter_by(**filters)
        # Only make one trip to the database
        query = query.options(joinedload('*'))

        model_list = query.all()

        data_model_list = [model.to_dict() for model in model_list]
        return data_model_list

    def exists(self, session, id):
        return bool(session.query(self.model_class).filter_by(id=id).first())


class Repositories(object):

    def __init__(self):
        self.record = TrafficRecordsRepositery()
        self.connected_state = ConnectedStateRepository()

    def create_record(self, session, **traffic_dict):
        if not traffic_dict.get('id'):
            traffic_dict['id'] = str(uuid.uuid4())
        record = models.TrafficRecord(**traffic_dict)
        session.add(record)

    def create_connected_state(self, session, **cs_dict):
        if not cs_dict.get('id'):
            cs_dict['id'] = str(uuid.uuid4())
        record = models.ConnectedState(**cs_dict)
        session.add(record)


class ConnectedStateRepository(BaseRepository):
    model_class = models.ConnectedState

    def get_servers(self, session, endpoint_ip):
        result = self.get(session, endpoint=endpoint_ip)
        return result.get('servers', [])

    def get_clients(self, session, endpoint_ip):
        result = self.get(session, endpoint=endpoint_ip)
        return result.get('clients', [])

    def update(self, session, endpoint, **model_kwargs):
        with session.begin(subtransactions=True):
            session.query(self.model_class).filter_by(
                endpoint=endpoint).update(model_kwargs)


class TrafficRecordsRepositery(BaseRepository):
    model_class = models.TrafficRecord

    def get_record_count(self, session, start_time, end_time, **filters):
        return session.query(self.model_class).filter_by(
            **filters).filter(
            self.model_class.created.between(start_time, end_time)).count()

    def get_records(self, session, start_time, end_time, **filters):
        query = session.query(self.model_class).filter_by(
            **filters).filter(
            self.model_class.created.between(start_time, end_time))
        model_list = query.all()
        data_model_list = [model.to_dict() for model in model_list]
        return data_model_list
