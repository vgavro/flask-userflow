class Datastore(object):
    def __init__(self, db, user_model, role_model=None, provider_user_model=None,
                 track_login_model=None):
        self.db = db
        self.user_model = user_model
        self.role_model = role_model
        self.provider_user_model = provider_user_model
        self.track_login_model = track_login_model

    def commit(self):
        raise NotImplementedError()

    def put(self, model):
        raise NotImplementedError()

    def delete(self, model):
        raise NotImplementedError()

    def _find_models(self, model, **kwargs):
        raise NotImplementedError()

    def _find_model(self, model, **kwargs):
        try:
            return self._find_models(**kwargs)[0]
        except IndexError:
            return None

    def find_users(self, **kwargs):
        return self._find_models(self.user_model, **kwargs)

    def find_roles(self, **kwargs):
        assert self.role_model
        return self._find_models(self.role_model, **kwargs)

    def find_provider_users(self, **kwargs):
        assert self.provider_user_model
        return self._find_models(self.provider_user_model, **kwargs)

    def find_track_login(self, **kwargs):
        assert self.track_login_model
        return self._find_models(self.track_login_model, **kwargs)


class SQLAlchemyDatastore(Datastore):
    def commit(self):
        self.db.session.commit()

    def put(self, model):
        self.db.session.add(model)

    def delete(self, model):
        self.db.session.delete(model)

    def _find_model(self, model, **kwargs):
        return model.query.filter_by(**kwargs).first()

    def _find_models(self, model, **kwargs):
        return model.query.filter_by(**kwargs)
