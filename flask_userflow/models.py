from datetime import datetime

from werkzeug.datastructures import ImmutableList
from werkzeug.utils import cached_property
from flask_login import AnonymousUserMixin, UserMixin

from .utils import md5
from . import _userflow


class I18NMixin(object):
    @cached_property
    def _i18n_info(self):
        return _userflow.request_utils.get_i18n_info()

    @property
    def timezone(self):
        return getattr(self, '_timezone', self._i18n_info['timezone'])

    @timezone.setter
    def timezone(self, value):
        self._timezone = value
        _userflow.request_utils.set_i18n_info(timezone=value)

    @property
    def locale(self):
        return getattr(self, '_locale', self._i18n_info['locale'])

    @locale.setter
    def locale(self, value):
        self._locale = value
        _userflow.request_utils.set_i18n_info(locale=value)


class AnonymousUser(I18NMixin, AnonymousUserMixin):
    def __init__(self):
        self.roles = ImmutableList()

    def has_role(self, *args):
        return False


class UserMixin(I18NMixin, UserMixin):
    @property
    def id(self):
        """Used for relations with other models"""
        raise NotImplementedError()

    @property
    def auth_id(self):
        """Used for authentication"""
        raise NotImplementedError()

    @property
    def is_active(self):
        return True

    def get_auth_token(self):
        """Returns the user's authentication token."""
        return _userflow.auth_token_serializer.dumps(self.auth_id)

    def set_password(self, password):
        self.password = _userflow.encrypt_password(password)

    def verify_password(self, password):
        return _userflow.verify_password(password, self.password)

    def get_id(self):
        return self.auth_id

    def generate_auth_id(self):
        """This also may be used to invalidate all current sessions"""
        assert self.password
        self.auth_id = md5('%s%s%s' % (str(self.id), self.password,
                                       datetime.utcnow().isoformat()))

    @property
    def roles(self):
        if not _userflow.datastore.role_model:
            raise NotImplementedError('Implement this or add role_model to datastore')
        roles = _userflow._datastore.find_roles(user_id=self.id)
        return [role.name for role in roles]

    def add_role(self, name):
        if not _userflow.datastore.role_model:
            raise NotImplementedError('Implement this or add role_model to datastore')
        role = _userflow.datastore.create_role(name=name, user_id=self.id)
        _userflow.datastore.put(role)
        _userflow.datastore.commit()

    def delete_role(self, name):
        if not _userflow.datastore.role_model:
            raise NotImplementedError('Implement this or add role_model to datastore')
        roles = _userflow.datastore.find_roles(user_id=self.id)
        roles = filter(lambda r: r.name == name, roles)
        for role in roles:
            _userflow.datastore.delete(role)
        _userflow.datastore.commit()

    def has_role(self, *args):
        roles = self.roles
        return all(r in roles for r in args)
