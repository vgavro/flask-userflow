from functools import partial


class Datastore(object):
    def __init__(self, db, user_model, role_model=None, provider_user_model=None,
                 track_login_model=None):
        self.db = db
        self.user_model = user_model
        self.role_model = role_model
        self.provider_user_model = provider_user_model
        self.track_login_model = track_login_model
        self._bind_methods()

    def commit(self):
        raise NotImplementedError()

    def put(self, obj):
        raise NotImplementedError()

    def delete(self, obj):
        raise NotImplementedError()

    def _find_models(self, model, **kwargs):
        raise NotImplementedError()

    def _find_model(self, model, **kwargs):
        try:
            return self._find_models(**kwargs)[0]
        except IndexError:
            return None

    def _create_model(self, model, **kwargs):
        obj = model(**kwargs)
        return obj

    def _bind_methods(self):
        for model_name in 'user', 'role', 'provider_user', 'track_login':
            model = getattr(self, '{}_model'.format(model_name))
            if model:
                find_models = 'find_{}s'.format(model_name)
                find_model = 'find_{}'.format(model_name)
                create_model = 'create_{}'.format(model_name)
                if not hasattr(self, find_models):
                    setattr(self, find_models, partial(self._find_models, model))
                if not hasattr(self, find_model):
                    setattr(self, find_model, partial(self._find_model, model))
                if not hasattr(self, create_model):
                    setattr(self, create_model, partial(self._create_model, model))


class SQLAlchemyDatastore(Datastore):
    def commit(self):
        self.db.session.commit()

    def put(self, obj):
        self.db.session.add(obj)

    def delete(self, obj):
        self.db.session.delete(obj)

    def _find_model(self, model, **kwargs):
        return model.query.filter_by(**kwargs).first()

    def _find_models(self, model, **kwargs):
        return model.query.filter_by(**kwargs)
