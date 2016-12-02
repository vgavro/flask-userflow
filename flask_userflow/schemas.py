import pytz
import marshmallow as ma
from marshmallow import validate
from itsdangerous import BadSignature, SignatureExpired

from . import _userflow


class BaseSchema(ma.Schema):
    pass


class TokenMixin(object):
    token = ma.fields.Str(required=True)

    def _load_token(self, name, token):
        max_age = _userflow.config['{}_AGE'.format(name.upper())]
        serializer = getattr(_userflow, '{}_serializer'.format(name))
        try:
            return serializer.loads(token, max_age=max_age)
        except SignatureExpired:
            raise ma.ValidationError('TOKEN_EXPIRED', field_names=['token'])
        except (BadSignature, TypeError, ValueError):
            raise ma.ValidationError('INVALID_TOKEN', field_names=['token'])


class UserMixin(object):
    def _get_user(self, email):
        return _userflow.datastore.find_user(email=email)


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
    password = ma.fields.Str(required=True, validate=[validate.Length(min=6, max=64)])


class ConfirmPasswordMixin(PasswordMixin):
    confirm_password = ma.fields.Str(required=True)

    @ma.validates_schema
    def validate_confirm_password(self, data):
        if 'password' in data and 'confirm_password' in data:
            if data['password'] != data['confirm_password']:
                raise ma.ValidationError('PASSWORD_MISMATCH',
                                         field_names=['confirm_password'])


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
    remember = ma.fields.Boolean(required=False)

    @ma.post_load
    def user(self, data):
        user = self._get_user(data['email'])
        if not user.verify_password(data['password']):
            raise ma.ValidationError('INVALID_PASSWORD', field_names=['password'])
        if not user.is_active:
            raise ma.ValidationError('DISABLED_ACCOUNT')

        data.setdefault('remember', False)
        return user, data


class RegisterStartSchema(UnregisteredEmailMixin, BaseSchema):
    pass


class RegisterConfirmSchema(TokenMixin, BaseSchema):
    @ma.post_load
    def data(self, data):
        data.update({'email': self._load_token('register_confirm', data['token'])})
        return data


class RegisterFinishSchema(TokenMixin, ConfirmPasswordMixin, I18nValidationMixin, BaseSchema):
    locale = ma.fields.Str(required=False)
    timezone = ma.fields.Str(required=False)

    @ma.post_load
    def data(self, data):
        data.update({'email': self._load_token('register_confirm', data['token'])})
        return data


class RestoreStartSchema(RegisteredEmailMixin, BaseSchema):
    pass


class RestoreConfirmSchema(TokenMixin, UserMixin, BaseSchema):
    @ma.post_load
    def data(self, data):
        data.update({'email': self._load_token('restore_confirm', data['token'])})
        user = self._get_user(data['email'])
        if not user:
            raise ma.ValidationError('USER_DOES_NOT_EXIST', field_names=['token'])
        return data


class RestoreFinishSchema(ConfirmPasswordMixin, TokenMixin, UserMixin, BaseSchema):
    @ma.post_load
    def data(self, data):
        data.update({'email': self._load_token('restore_confirm', data['token'])})
        user = self._get_user(data['email'])
        if not user:
            raise ma.ValidationError('USER_DOES_NOT_EXIST', field_names=['token'])
        return user, data


class UserSchema(BaseSchema):
    name = ma.fields.Str(required=True)
    id = ma.fields.Str(required=True)
    email = ma.fields.Str(required=True)


class ProviderUserSchema(BaseSchema):
    provider = ma.fields.Str(required=True)
    provider_user_id = ma.fields.Str(required=True)


schemas_map = {
    'set_i18n': SetI18nSchema(),

    'login': LoginSchema(),

    'register_start': RegisterStartSchema(),
    'register_confirm': RegisterConfirmSchema(),
    'register_finish': RegisterFinishSchema(),

    'restore_start': RestoreStartSchema(),
    'restore_confirm': RestoreConfirmSchema(),
    'restore_finish': RestoreFinishSchema(),

    'user_schema': UserSchema(),
    'provider_user_schema': ProviderUserSchema(),
}
