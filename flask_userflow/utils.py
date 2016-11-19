import base64
import hashlib
import hmac


def md5(data):
    return hashlib.md5(data).hexdigest()


def get_hmac(password, salt):
    h = hmac.new(salt, password, hashlib.sha512)
    return base64.b64encode(h.digest())


def set_attrs_from_dict(obj, dict_, attrs, pop=False):
    for attr in attrs:
        if attr in dict_:
            setattr(obj, attr, dict_[attr])
            if pop:
                del dict_[attr]
