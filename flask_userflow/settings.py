class LazyValue(object):
    def __init__(self, conf_callback):
        self.conf_callback = conf_callback

    def resolve(self, config, app_config):
        return self.conf_callback(config, app_config)


default_config = (
    ('SECRET_KEY', LazyValue(lambda c, app_c: app_c['SECRET_KEY'])),
    ('PASSWORD_ROUNDS', 12),
    ('PASSWORD_IDENT', '2b'),

    ('DKIM_KEY', LazyValue(lambda c, app_c: app_c.get('EMAIL_DKIM_KEY'))),
    ('DKIM_KEY_PATH', LazyValue(lambda c, app_c: app_c.get('EMAIL_DKIM_KEY_PATH'))),
    ('DKIM_DOMAIN', LazyValue(lambda c, app_c: app_c.get('EMAIL_DKIM_DOMAIN'))),
    ('DKIM_SELECTOR', LazyValue(lambda c, app_c: app_c.get('EMAIL_DKIM_SELECTOR'))),

    ('LOCALES', LazyValue(lambda c, app_c: app_c.get('LOCALES', ['en']))),
    ('DEFAULT_LOCALE', LazyValue(lambda c, app_c: app_c.get('DEFAULT_LOCALE', c['LOCALES'][0]))),
    ('DEFAULT_TIMEZONE', LazyValue(lambda c, app_c: app_c.get('DEFAULT_TIMEZONE', 'UTC'))),

    ('AUTHOMATIC_CONFIG', {}),
    ('AUTHOMATIC_SECRET_KEY', LazyValue(lambda c, app_c: c['SECRET_KEY'])),

    ('REGISTER_CONFIRM_URL', '/register_confirm/{}'),
    ('REGISTER_CONFIRM_AGE', 60 * 60 * 24 * 14),

    ('RESTORE_CONFIRM_URL', '/restore_confirm/{}'),
    ('RESTORE_CONFIRM_AGE', 60 * 60 * 24 * 14),

    ('URL_PREFIX', '/user'),
    ('SUBDOMAIN', None),

    ('STATUS_API_URL', '/status'),
    ('STATUS_API_METHOD', 'GET'),
    ('SET_I18N_API_URL', '/set_i18n'),
    ('SET_I18N_API_METHOD', 'POST'),
    ('TIMEZONES_API_URL', '/timezones'),
    ('TIMEZONES_API_METHOD', 'GET'),
    ('LOGIN_API_URL', '/status'),
    ('LOGIN_API_METHOD', 'POST'),
    ('LOGOUT_API_URL', '/status'),
    ('LOGOUT_API_METHOD', 'DELETE'),

    ('REGISTER_START_API_URL', '/register'),
    ('REGISTER_START_API_METHOD', 'POST'),
    ('REGISTER_CONFIRM_API_URL', '/register_confirm'),
    ('REGISTER_CONFIRM_API_METHOD', 'POST'),
    ('REGISTER_FINISH_API_URL', '/register'),
    ('REGISTER_FINISH_API_METHOD', 'PUT'),

    ('RESTORE_START_API_URL', '/restore'),
    ('RESTORE_START_API_METHOD', 'POST'),
    ('RESTORE_CONFIRM_API_URL', '/restore_confirm'),
    ('RESTORE_CONFIRM_API_METHOD', 'POST'),
    ('RESTORE_FINISH_API_URL', '/restore'),
    ('RESTORE_FINISH_API_METHOD', 'PUT'),
)


class Config(dict):
    PREFIX = 'USERFLOW_'
    UPDATE_APP_CONFIG = False

    default_config = default_config

    def __init__(self, app_config):
        super(Config, self).__init__()

        for key, value in self.default_config:
            app_key = '{}{}'.format(self.PREFIX, key)
            value = app_config.get(app_key, value)

            if isinstance(value, LazyValue):
                value = value.resolve(self, app_config)

            self[key] = value

            if self.UPDATE_APP_CONFIG:
                app_config[app_key] = value
