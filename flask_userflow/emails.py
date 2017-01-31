from flask import render_template


class Emails(object):
    message_cls = None

    def __init__(self, config, message_cls, celery):
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
            def send(*args, **kwargs):
                return self._send(*args, **kwargs)
            self.send_task = celery.task(send)

            def send_delay(name, to, context, locale=None):
                return self.send_task.delay(name, to, context, locale)
            self.send = send_delay

        else:
            self.send = self._send

        self.dkim_key = config.get('DKIM_KEY')
        if not self.dkim_key and config.get('DKIM_KEY_PATH'):
            self.dkim_key = open(config['DKIM_KEY_PATH']).read()
        self.dkim_domain = config.get('DKIM_DOMAIN')
        self.dkim_selector = config.get('DKIM_SELECTOR')

    def create(self, name, context, locale):
        subject_template = 'userflow/emails/{}_subject.txt'.format(name)
        html_template = 'userflow/emails/{}.html'.format(name)
        subject = render_template(subject_template, **context)
        html = render_template(html_template, **context)
        message = self.message_cls(subject=subject, html=html)
        if self.dkim_key:
            message.dkim(key=self.dkim_key, domain=self.dkim_domain,
                         selector=self.dkim_selector)
        return message

    def _send(self, name, to, context, locale=None):
        message = self.create(name, context, locale)
        message.send(to=to)
