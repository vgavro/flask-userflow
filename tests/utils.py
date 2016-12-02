from flask import json, Response as BaseResponse
from flask.testing import FlaskClient
from werkzeug.utils import cached_property


class Response(BaseResponse):
    @cached_property
    def json(self):
        return json.loads(self.data)


class TestClient(FlaskClient):
    def open(self, *args, **kwargs):
        if 'json' in kwargs:
            kwargs['data'] = json.dumps(kwargs.pop('json'))
            kwargs['content_type'] = 'application/json'
        return super(TestClient, self).open(*args, **kwargs)


def populate_datastore(userflow):
    users = [
        ('vgavro@gmail.com', 'Victor Gavro', 'password', ['admin'], True),
    ]

    for u in users:
        # password = userflow.encrypt_password(u[2])
        user = userflow.datastore.create_user(email=u[0], name=u[1], is_active=u[4])
        user.set_password(u[2])
        user.generate_auth_id()
        userflow.datastore.put(user)
    userflow.datastore.commit()
