import pytz
import marshmallow as ma
from itsdangerous import BadSignature, SignatureExpired

from . import _userflow


class BaseSchema(ma.Schema):
    pass


class TokenMixin(object):
    token = ma.fields.Str(required=True)

    def _load_token(self, name, token):
        max_age = _userflow.config['{}_AGE'.format(name.upper())]
        serializer = getattr(_userflow, '{}_serializer')
        try:
            return serializer.loads(token, max_age=max_age)
        except SignatureExpired:
            raise ma.ValidationError('TOKEN_EXPIRED', fields=[self.token])
        except (BadSignature, TypeError, ValueError):
            raise ma.ValidationError('INVALID_TOKEN', fields=[self.token])


class UserMixin(object):
    def _get_user(self, email):
        if not hasattr(self, '_user'):
            self._user = _userflow.datastore.find_user(email=email)
        return self._user


class UnregisteredEmailMixin(UserMixin):
    email = ma.fields.Email(required=True)

    @ma.validates('email')
    def validate_email(self, email):
        user = self._get_user(email)
        if user:
            raise ma.ValidationError('USER_ALREADY_EXIST')


class RegisteredEmailMixin(UserMixin):
    email = ma.fields.Email(required=True)

    @ma.validates('email')
    def validate_email(self, email):
        user = self._get_user(email)
        if not user:
            raise ma.ValidationError('USER_DOES_NOT_EXIST')


class PasswordMixin(object):
    password = ma.fields.Str(required=True)


class ConfirmPasswordMixin(PasswordMixin):
    confirm_password = ma.fields.Str(required=True)

    @ma.validates_schema
    def validate_confirm_password(self, data):
        if 'password' in data and 'confirm_password' in data:
            if data['password'] != data['confirm_password']:
                raise ma.ValidationError('PASSWORD_MISMATCH',
                                         fields=[self.confirm_password])


class I18nValidationMixin(object):
    @ma.validates('timezone')
    def validate_timezone(self, timezone):
        if timezone not in pytz.common_timezones:
            raise ma.ValidationError('TIMEZONE_NOT_VALID')

    @ma.validates('locale')
    def validate_locale(self, locale):
        if locale not in _userflow.config['LOCALES']:
            raise ma.ValidationError('LOCALE_NOT_VALID')


class SetI18nSchema(I18nValidationMixin, BaseSchema):
    locale = ma.fields.Str(required=False)
    timezone = ma.fields.Str(required=False)

    @ma.validates_schema
    def any(self, data):
        if 'locale' not in data and 'timezone' not in data:
            raise ma.ValidationError('INSUFFICIENT_DATA')


class LoginSchema(RegisteredEmailMixin, PasswordMixin, BaseSchema):
    remember = ma.fields.Boolean(required=True)

    @ma.post_load
    def user(self, data):
        user = self._get_user(data['email'])
        if not user.validate_password(data['password']):
            raise ma.ValidationError('INVALID_PASSWORD', fields=[self.email])
        if not user.is_active:
            raise ma.ValidationError('DISABLED_ACCOUNT')
        return user, data


class RegisterStartSchema(UnregisteredEmailMixin, BaseSchema):
    pass


class RegisterConfirmSchema(TokenMixin, BaseSchema):
    @ma.post_load
    def data(self, data):
        data.update(self._load_token('register_confirm', data['token']))
        return data


class RegisterFinishSchema(TokenMixin, ConfirmPasswordMixin, I18nValidationMixin, BaseSchema):
    locale = ma.fields.Str(required=True)
    timezone = ma.fields.Str(required=True)

    @ma.post_load
    def data(self, data):
        data.update(self._load_token('register_confirm', data.pop('token')))
        return data


class PasswordRestoreStartSchema(RegisteredEmailMixin, BaseSchema):
    pass


class PasswordRestoreConfirmSchema(TokenMixin, UserMixin, BaseSchema):
    @ma.post_load
    def data(self, data):
        data.update('password_restore', self._load_token(data['token']))
        user = self._get_user(data['email'])
        if not user:
            raise ma.ValidationError('USER_DOES_NOT_EXIST')
        return user, data


class PasswordRestoreFinishSchema(BaseSchema):
    token = ma.fields.Str(required=True)

    @ma.post_load
    def data(self, data):
        data.update('password_restore', self._load_token(data['token']))
        return data


class UserSchema(BaseSchema):
    pass


class ProviderUserSchema(BaseSchema):
    pass


class Schemas(object):
    set_i18n = SetI18nSchema()

    login = LoginSchema()

    register_start = RegisterStartSchema()
    register_confirm = RegisterConfirmSchema()
    register_finish = RegisterFinishSchema()

    password_restore_start = PasswordRestoreStartSchema()
    password_restore_confirm = PasswordRestoreConfirmSchema()
    password_restore_finish = PasswordRestoreFinishSchema()

    user_schema = UserSchema()
    provider_user_schema = ProviderUserSchema()

    def __init__(self, config):
        self.config = config

    def errors_processor(self, errors):
        return errors
