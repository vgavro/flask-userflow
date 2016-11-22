from datetime import datetime

import bcrypt
import pytz
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import safe_str_cmp
from flask import Blueprint
from flask_login import LoginManager, current_user, AnonymousUserMixin
from flask_principal import Principal, Identity, UserNeed, RoleNeed, identity_loaded
from authomatic import Authomatic

from .settings import Config
from .request_utils import RequestUtils
from .emails import Emails
from .schemas import schemas_map
from .models import AnonymousUser
from .views import views_map, add_api_routes as _add_api_routes


class UserflowExtension(object):
    anonymous_user_cls = AnonymousUser

    config_cls = Config
    request_utils_cls = RequestUtils
    emails_cls = Emails
    schemas = schemas_map
    views = views_map

    def __init__(self, app, datastore, geoip=None, celery=None, message_cls=None,
                 jinja_env=None, authomatic=None, views=None, schemas=None,
                 add_api_routes=True):
        self.app = app
        self.datastore = datastore

        config = self.config_cls(app.config)
        self.config = config
        self.request_utils = self.request_utils_cls(config, geoip)
        self.emails = self.emails_cls(config, message_cls, celery, jinja_env or app.jinja_env)
        self.authomatic = authomatic or Authomatic(config['AUTHOMATIC_CONFIG'],
                                                   config['AUTHOMATIC_SECRET_KEY'])

        self.schemas = schemas or self.schemas
        self.views = views or self.views

        self.blueprint = Blueprint('userflow', 'flask_userflow',
                                   url_prefix=config['URL_PREFIX'],
                                   subdomain=config['SUBDOMAIN'],
                                   template_folder='templates')
        if add_api_routes:
            _add_api_routes(config, self.views, self.blueprint)
        app.register_blueprint(self.blueprint)

        self._init_login_manager()
        self._init_principal()

        self.auth_token_serializer = self._create_serializer('auth_token')
        self.register_confirm_serializer = self._create_serializer('register_confirm')
        self.restore_confirm_serializer = \
            self._create_serializer('restore_confirm')

    def _init_login_manager(self):
        self.login_manager = LoginManager(self.app)
        self.login_manager.user_loader(self._user_loader)
        self.login_manager.anonymous_user = self.anonymous_user_cls

    def _user_loader(self, auth_id):
        return self.datastore.find_user(auth_id=auth_id)

    def _init_principal(self):
        self.principal = Principal(self.app, use_sessions=False)
        self.principal.identity_loader = self._identity_loader
        identity_loaded.connect_via(self.app)(self._on_identity_loaded)

    @staticmethod
    def _identity_loader():
        if not isinstance(current_user._get_current_object(), AnonymousUserMixin):
            identity = Identity(current_user.id)
            return identity

    @staticmethod
    def _on_identity_loaded(sender, identity):
        if hasattr(current_user, 'id'):
            identity.provides.add(UserNeed(current_user.id))

        for role in current_user.roles:
            identity.provides.add(RoleNeed(role.name))

        identity.user = current_user

    def _create_serializer(self, name):
        salt = self.config.get('%s_SALT' % name.upper())
        return URLSafeTimedSerializer(secret_key=self.config['SECRET_KEY'], salt=salt)

    def encrypt_password(self, password):
        if isinstance(password, unicode):
            password = password.encode('utf8')
        salt = bcrypt.gensalt(rounds=self.config['PASSWORD_ROUNDS'],
                              prefix=self.config['PASSWORD_IDENT'])
        return bcrypt.hashpw(password, salt)

    def verify_password(self, password, password_hash):
        if isinstance(password, unicode):
            password = password.encode('utf8')
        if isinstance(password_hash, unicode):
            password_hash = password_hash.encode('utf8')
        return safe_str_cmp(bcrypt.hashpw(password, password_hash), password_hash)

    def get_timezone_choices(self, locale=None):
        # l18n may be used for timezone names localization,
        # but it has some issues to workaround
        result = []
        for tz in pytz.common_timezones:
            now = datetime.now(pytz.timezone(tz))
            ofs = now.strftime("%z")
            result.append((int(ofs), tz, "(GMT%s) %s" % (ofs, tz)))

        result.sort()

        for i in xrange(len(result)):
            result[i] = result[i][1:]

        return result
