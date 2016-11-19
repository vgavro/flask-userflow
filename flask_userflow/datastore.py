class Datastore(object):
    pass


class SQLAlchemyDatastore(Datastore):
    def __init__(self, db, user_model, provider_user_model=None,
                 track_login_model=None):
        self.db = db
        self.user_model = user_model
        self.provider_user_model = provider_user_model
        self.track_login_model = track_login_model

    def commit(self):
        self.db.session.commit()

    def put(self, model):
        self.db.session.add(model)
        return model

    def delete(self, model):
        self.db.session.delete(model)

    def find_user(self, **kwargs):
        return self.user_model.query.filter_by(**kwargs).first()

    def find_provider_user(self, **kwargs):
        if not self.provider_user_model:
            raise RuntimeError()
        #return self.user_model.query.filter_by(**kwargs).first()
