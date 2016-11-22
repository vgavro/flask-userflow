class Emails(object):
    message_cls = None
    jinja_env = None

    names = ['register_start', 'register_finish', 'restore_start']

    def __init__(self, config, message_cls, celery, jinja_env):
        if message_cls:
            self.message_cls = message_cls
        if not self.message_cls:
            try:
                from flask_emails import Message
                self.message_cls = Message
            except ImportError:
                pass

        if not self.message_cls:
            def send(*args, **kwargs):
                raise RuntimeError('No flask_emails, and message_cls is not configured')
            self.send = send
        elif celery:
            def send(self, to, name, context, locale=None):
                return self.send_task.delay(to, name, context, locale)
            self.send_task = self.celery.task(self._send)
            self.send = send
        else:
            self.send = self._send

        self.dkim_key = config.get('DKIM_KEY')
        if not self.dkim_key and config.get('DKIM_KEY_PATH'):
            self.dkim_key = open(config['DKIM_KEY_PATH']).read()
        self.dkim_domain = config.get('DKIM_DOMAIN')
        self.dkim_selector = config.get('DKIM_SELECTOR')

        if jinja_env:
            self.jinja_env = jinja_env

        self.messages = {}

    def _create(self, name):
        subject_template = 'userflow/emails/{}_subject.txt'.format(name)
        html_template = 'userflow/emails/{}.html'.format(name)
        subject = self.jinja_env.get_template(subject_template)
        html = self.jinja_env.get_template(html_template)

        message = self.message_cls(subject=subject, html=html)
        if self.dkim_key:
            message.dkim(key=self.dkim_key, domain=self.dkim_domain,
                         selector=self.dkim_selector)
        return message

    def _send(self, name, to, context, locale=None):
        if name not in self.names:
            raise ValueError('No email with name {} registered'.format(name))
        if name not in self.messages:
            self.messages[name] = self._create(name)
        self.messages[name].send(to=to, render=context)
