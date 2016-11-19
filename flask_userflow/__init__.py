from werkzeug.local import LocalProxy
from flask import current_app

_userflow = LocalProxy(lambda: current_app.extensions['userflow'])  # noqa

from .core import UserflowExtension
from .datastore import SQLAlchemyDatastore
from .models import UserMixin


class Userflow(object):
    extension_cls = UserflowExtension

    def __init__(self, app, datastore, **kwargs):
        self.app = app
        self.datastore = datastore

        if app is not None and datastore is not None:
            extension = self.init_app(app, datastore, **kwargs)
            self.__dict__.update(extension.__dict__)

    def init_app(self, app, datastore, **kwargs):
        extension_cls = kwargs.pop('extension_cls', self.extension_cls)
        extension = extension_cls(app, datastore, **kwargs)
        app.extensions['userflow'] = extension
        return extension
