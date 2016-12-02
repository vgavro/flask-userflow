from datetime import datetime
from functools import wraps

from werkzeug.local import LocalProxy
from flask import request, Response, after_this_request, make_response, session, redirect, jsonify
from flask_login import login_user as _login_user, logout_user, current_user
from authomatic.adapters import WerkzeugAdapter

from . import _userflow


_datastore = LocalProxy(lambda: _userflow.datastore)


def schema_errors_processor(errors):
    response = jsonify({'errors': errors})
    response.status_code = 422
    return response


def load_schema(schema_name):
    # using schema_name for lazy getting schema, in case of override
    def decorator(func):
        @wraps(func)
        def wrapper(payload, *args, **kwargs):
            schema = _userflow.schemas[schema_name]
            data, errors = schema.load(payload or {})
            if errors:
                return _userflow.views['_schema_errors_processor'](errors)
            else:
                return func(data, *args, **kwargs)
        wrapper.load_schema_decorated = True
        return wrapper
    return decorator


def request_json(func):
    @wraps(func)
    def wrapper():
        return func(request.json)
    return wrapper


def response_json(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        if not isinstance(response, Response):
            return jsonify(response)
        return response
    return wrapper


def login_user(user, remember=False, provider=None):
    assert user.is_active
    logged_in = _login_user(user, remember)
    assert logged_in, 'Not logged in for unknown reason'

    session.pop('auth_provider', None)

    if _datastore.track_login_model:
        track_login = _datastore.track_login_model()
        track_login.populate(
            time=datetime.utcnow(),
            remote_addr=_userflow.request_utils.get_remote_addr(),
            geoip_info=_userflow.request_utils.get_geoip_info(),
            ua_info=_userflow.request_utils.get_ua_info(),
        )
        _datastore.put(track_login)
        after_this_request(lambda r: _datastore.commit())
    return user.get_auth_token()


@load_schema('login')
def login(data):
    user, data = data
    auth_token = login_user(user, data['remember'])
    data = status()
    data['auth_token'] = auth_token
    return data


def logout():
    logout_user()
    return status()


def status():
    if not current_user.is_anonymous:
        user, errors = _userflow.schemas['user_schema'].dump(current_user)
        assert not errors
    else:
        user = None

    result = {
        'user': user,
        'locale': current_user.locale,
        'timezone': current_user.timezone,
    }

    if 'auth_provider' in session:
        auth_provider = {}
        for provider, provider_user_id in session['auth_provider'].items():
            provider_user = _datastore.find_provider_user(provider=provider,
                                                          provider_user_id=provider_user_id)
            if provider_user:
                schema = _userflow.schemas['ProviderUserSchema']
                auth_provider[provider] = schema.dump(provider_user)
            else:
                session['auth_provider'].pop(provider)
        if not session['auth_provider']:
            session.pop('auth_provider')
        if auth_provider:
            result['auth_provider'] = auth_provider

    if _userflow.request_utils.geoip:
        result['geoip'] = _userflow.request_utils.get_geoip_info()

    return result


@load_schema('set_i18n')
def set_i18n(data):
    if 'timezone' in data:
        current_user.timezone = data['timezone']
    if 'locale' in data:
        current_user.locale = data['locale']
    if not current_user.is_anonymous:
        _datastore.commit()


def timezones():
    return {'timezones': _userflow.get_timezone_choices()}


def provider_login(provider, goal):
    if goal not in ('LOGIN', 'REGISTER', 'ASSOCIATE'):
        raise ValueError('Unknown goal: {}'.format(goal))

    response = make_response()
    result = _userflow.authomatic.login(WerkzeugAdapter(request, response), provider)
    if result:
        if result.error:
            # log result.to_json() if needed, but authomatic logs it anyway
            return redirect(_userflow.config['PROVIDER_{}_ERROR_URL'.format(goal)])

        # OAuth 2.0 and OAuth 1.0a provide only limited user data on login,
        # We need to update the user to get more info.
        result.user.update()

        provider_user = _datastore.find_provider_user(provider=provider,
                                                      provider_user_id=result.user.id)
        if provider_user:
            provider_user.populate(result.user)
        else:
            provider_user = _datastore.provider_user_model()
            provider_user.provider = provider
            provider_user.populate(result.user)
            _datastore.put(provider_user)

        after_this_request(lambda r: _datastore.commit())

        if goal == 'ASSOCIATE':
            provider_user.user_id == current_user.id
            return redirect(_userflow.config['PROVIDER_ASSOCIATE_SUCCEED_URL'])

        if provider_user.user_id:
            user = _datastore.find_user(id=provider_user.user_id)
            if not user.is_active:
                return redirect(_userflow.config['PROVIDER_LOGIN_INACTIVE_URL'])
            login_user(user, False, provider)
            return redirect(_userflow.config['PROVIDER_LOGIN_SUCCEED_URL'])

        if result.user.email:
            user = _datastore.find_user(email=result.user.email)
            if user:
                provider_user.user_id = user.id
                if not user.is_active:
                    return redirect(_userflow.config['PROVIDER_LOGIN_INACTIVE_URL'])
                login_user(user, False, provider)
                return redirect(_userflow.config['PROVIDER_LOGIN_SUCCEED_URL'])

        if goal == 'LOGIN':
            return redirect(_userflow.config['PROVIDER_LOGIN_NOT_EXIST_URL'])

        assert goal == 'REGISTER'

        session.setdefault('auth_provider', {})
        session['auth_provider'][provider] = result.user.id

        if result.user.email:
            token = _userflow.register_confirm_serializer.dumps(result.user.email)
            confirm_url = _userflow.config['REGISTER_CONFIRM_URL'].format(token)
            return redirect(confirm_url)
        else:
            return redirect(_userflow.config['REGISTER_START_URL'])


@load_schema('register_start')
def register_start(data):
    token = _userflow.register_confirm_serializer.dumps(data['email'])
    confirm_url = _userflow.config['REGISTER_CONFIRM_URL'].format(token)
    _userflow.emails.send('register_start', data['email'], {'confirm_url': confirm_url})


@load_schema('register_confirm')
def register_confirm(data):
    return data


@load_schema('register_finish')
def register_finish(data, login=True, login_remember=False):
    locale = data.get('locale', current_user.locale)
    timezone = data.get('timezone', current_user.timezone)
    user = _datastore.user_model(email=data['email'], locale=locale,
                                 timezone=timezone)
    user.active = True
    user.set_password(data['password'])
    user.generate_auth_id()
    _datastore.put(user)
    if login:
        auth_token = login_user(user, login_remember)
    else:
        auth_token = None

    _datastore.commit()  # TODO: to get user_id

    provider_associated = False

    for provider, provider_user_id in session.get('auth_provider', {}).items():
        provider_user = _datastore.find_provider_user(provider=provider,
                                                      provider_user_id=provider_user_id)
        if provider_user:
            provider_associated = True
            provider_user.user_id = user.id
    session.pop('auth_provider', None)

    if provider_associated:
        _datastore.commit()

    return {
        'auth_token': auth_token
    }


@load_schema('restore_start')
def restore_start(data):
    token = _userflow.restore_confirm_serializer.dumps(data['email'])
    confirm_url = _userflow.config['RESTORE_CONFIRM_URL'].format(token)
    _userflow.emails.send('restore_start',
                          data['email'], {'confirm_url': confirm_url})


@load_schema('restore_confirm')
def restore_confirm(data):
    return data


@load_schema('restore_finish')
def restore_finish(data, login=True, login_remember=False):
    user, data = data
    user.set_password(data['password'])
    _datastore.commit()


views_map = {
    '_schema_errors_processor': schema_errors_processor,

    'login': login,
    'logout': logout,
    'status': status,
    'set_i18n': set_i18n,
    'timezones': timezones,

    'register_start': register_start,
    'register_confirm': register_confirm,
    'register_finish': register_finish,
    'restore_start': restore_start,
    'restore_confirm': restore_confirm,
    'restore_finish': restore_finish,
}


def add_api_routes(config, views_map, blueprint):
    for name, view in views_map.items():
        if name.startswith('_'):
            continue

        def _conf(key):
            return config[key.format(name.upper())]

        if _conf('{}_API_URL'):
            if hasattr(view, 'load_schema_decorated'):
                view = request_json(view)
            view = response_json(view)
            blueprint.route(_conf('{}_API_URL'), methods=[_conf('{}_API_METHOD')],
                            endpoint=name)(view)
