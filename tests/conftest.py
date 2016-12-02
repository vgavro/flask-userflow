import tempfile
import os

import pytest
from flask import Flask

from flask_userflow import Userflow, SQLAlchemyDatastore, UserMixin
from utils import Response, TestClient, populate_datastore


@pytest.fixture()
def app():
    app = Flask(__name__)
    app.response_class = Response
    app.test_client_class = TestClient
    app.testing = True
    app.debug = True
    app.config['SECRET_KEY'] = 'secret'
    app.config['LOCALES'] = ['en', 'ru']
    app.config['EMAIL_BACKEND'] = 'flask_emails.backends.DummyBackend'
    app.config['EMAIL_DEFAULT_FROM'] = 'py@test'
    app.config['USERFLOW_PASSWORD_ROUNDS'] = 4
    return app


@pytest.fixture()
def sqlalchemy_datastore(request, tmpdir, app):
    from flask_sqlalchemy import SQLAlchemy

    f, path = tempfile.mkstemp(prefix='flask-userflow-', suffix='.db',
                               dir=str(tmpdir))

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + path
    # turn fucking boring warning off
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)

    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(255), unique=True)
        name = db.Column(db.String(255))
        auth_id = db.Column(db.String(255), unique=True)
        password = db.Column(db.String(255))
        is_active = db.Column(db.Boolean())

        locale = db.Column(db.String(255))
        timezone = db.Column(db.String(255))

    with app.app_context():
        db.create_all()

    request.addfinalizer(lambda: os.remove(path))

    return SQLAlchemyDatastore(db, User)


@pytest.fixture()
def sqlalchemy_app(app, sqlalchemy_datastore):
    app.userflow = Userflow(app, datastore=sqlalchemy_datastore)
    with app.app_context():
        populate_datastore(app.userflow)
    return app


@pytest.fixture()
def client(request, sqlalchemy_app):
    return sqlalchemy_app.test_client()
