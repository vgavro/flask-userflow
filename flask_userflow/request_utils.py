from datetime import datetime, timedelta

import pytz
from ua_parser import user_agent_parser
from flask import request, session, _app_ctx_stack as stack


class RequestUtils(object):
    geoip = None  # https://github.com/vgavro/flask-geoip2/
    # TODO: support for https://pypi.python.org/pypi/Flask-GeoIP/0.1.3

    def __init__(self, config, geoip):
        self.config = config
        if geoip:
            self.geoip = geoip

    def get_remote_addr(self):
        address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if address is not None:
            # An 'X-Forwarded-For' header includes a comma separated list of the
            # addresses, the first address being the actual remote address.
            address = address.encode('utf-8').split(b',')[0].strip()
        return address

    def guess_timezone(self, geoip_info=None, browser_tz_offset=None):
        """Note: you may reimplement this using tzwhere or your methods"""

        if geoip_info:
            if geoip_info['timezone']:
                return geoip_info['timezone']
            elif geoip_info['country']:
                try:
                    return pytz.country_timezones[geoip_info['country']][0]
                except (KeyError, IndexError):
                    pass

        elif browser_tz_offset:
            offset = timedelta(minutes=browser_tz_offset)
            now = datetime.now(pytz.utc)
            timezones = {now.astimezone(tz).tzname()
                         for tz in map(pytz.timezone, pytz.all_timezones_set)
                         if now.astimezone(tz).utcoffset() == offset}
            if timezones:
                return timezones[0]

        return self.config['DEFAULT_TIMEZONE']

    def guess_locale(self, geoip_info=None, browser_locales=None):
        if self.config['LOCALES']:
            locale = request.accept_languages.best_match(self.config['LOCALES'])
            if locale:
                return locale
        return self.config['DEFAULT_LOCALE']

    def set_i18n_guess(self, browser_locales=[], browser_tz_offset=None,
                       skip_if_set=False):

        if skip_if_set and all(self.get_i18n_info(guess_if_unset=False)):
            return

        if self.geoip:
            geoip_info = self.get_geoip_info()
        else:
            geoip_info = None

        session['_locale'] = self.guess_locale(geoip_info, browser_locales)
        session['_tz'] = self.guess_timezone(geoip_info, browser_tz_offset)

    def set_i18n_info(self, locale=None, timezone=None):
        if locale:
            session['locale'] = locale
            session.pop('_locale', None)
        if timezone:
            session['tz'] = timezone
            session.pop('_tz', None)

    def get_i18n_info(self, guess_if_unset=True, raise_if_unset=False):
        result = {
            'locale': session.get('locale', session.get('_locale')),
            'timezone': session.get('tz', session.get('_tz')),
        }
        if not all(result.values()):
            if guess_if_unset:
                self.set_i18n_guess(skip_if_set=False)
                return self.get_i18n_info(guess_if_unset=False, raise_if_unset=True)
            if raise_if_unset:
                raise ValueError('no i18n info in session')
        return result

    def get_geoip_info(self):
        ctx = stack.top
        empty = {'country': None, 'city': None, 'lat': None, 'lng': None, 'timezone': None}
        if ctx is not None:
            if not hasattr(ctx, '_geoip_info'):
                remote_addr = self.get_remote_addr()
                if not self.geoip:
                    raise RuntimeError('Override this method or configure it '
                                       'with flask_geoip2 instance')
                try:
                    r = self.geoip.city(remote_addr)
                    ctx._geoip_info = {
                        'country': r.country.iso_code,
                        'city': r.city.name,
                        'lat': r.location.latitude,
                        'lng': r.location.longitude,
                        'timezone': r.location.time_zone,
                    }
                except r.AddressNotFoundError:
                    ctx._geoip_info = empty
            return ctx._geoip_info
        return empty

    def get_ua_info(self):
        return user_agent_parser.Parse(request.headers.get('User-Agent'))
