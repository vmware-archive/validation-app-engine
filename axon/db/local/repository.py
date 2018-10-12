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
        [self.delete(session, uuid=id) for id in ids]

    def delete_all(self, session):
        session.query(self.model_class).delete()
        session.flush()

    def get(self, session, **filters):
        model = session.query(self.model_class).filter_by(**filters).first()
        if not model:
            return
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

    def create_record(self, session, **traffi_dict):
        with session.begin(subtransactions=True):
            if not traffi_dict.get('uuid'):
                traffi_dict['uuid'] = str(uuid.uuid4())
            record = models.TrafficRecord(**traffi_dict)
            session.add(record)
            return self.record.get(session, uuid=record.uuid)

    def create_connected_state(self, session, **cs_dict):
        with session.begin(subtransactions=True):
            if not cs_dict.get('uuid'):
                cs_dict['uuid'] = str(uuid.uuid4())
            record = models.ConnectedState(**cs_dict)
            session.add(record)
            return self.connected_state.get(session, uuid=record.uuid)


class ConnectedStateRepository(BaseRepository):
    model_class = models.ConnectedState

    def get_servers(self, session, endpoint_ip):
        result = self.get(session, endpoint=endpoint_ip)
        return result.get('servers', [])

    def get_clients(self, session, endpoint_ip):
        result = self.get(session, endpoint=endpoint_ip)
        return result.get('clients', [])

    def update_servers(self, session, endpoint, servers):
        current_servers = self.get_servers(session, endpoint)
        current_servers.extend(servers)
        session.query(self.model_class).filter_by(
            endpoint=endpoint).update(
            {"servers": current_servers},
            synchronize_session=False)
        session.commit()

    def update_clients(self, session, endpoint, clients):
        current_clints = self.get_clients(session, endpoint)
        current_clints.extend(clients)
        session.query(self.model_class).filter_by(
            endpoint=endpoint).update(
            {"clients": current_clints},
            synchronize_session=False)
        session.commit()


class TrafficRecordsRepositery(BaseRepository):
    model_class = models.TrafficRecord

    def get_failure_count(self, session, start_time, end_time=None, **filters):
        if end_time:
            query = session.query(self.model_class).filter_by(
                **filters).filter(
                self.model_class.created_time.between(
                    start_time, end_time))
        else:
            query = session.query(self.model_class).filter_by(
                **filters).filter(
                self.model_class.created_time >= start_time)
        query = query.options(joinedload('*'))
        model_list = query.all()
        data_model_list = [model.to_dict() for model in model_list]
        return len(data_model_list)

    def get_success_count(self, session, start_time, end_time=None, **filters):
        if end_time:
            query = session.query(self.model_class).filter_by(
                **filters).filter(
                self.model_class.created_time.between(
                    start_time, end_time))
        else:
            query = session.query(self.model_class).filter_by(
                **filters).filter(
                self.model_class.created_time >= start_time)
        query = query.options(joinedload('*'))
        model_list = query.all()
        data_model_list = [model.to_dict() for model in model_list]
        return len(data_model_list)
