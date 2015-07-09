__author__ = 'Stuart'

from functools import wraps
from flask import g
from .errors import forbidden

def permission_required(permission):
    """
    makes custom decorator preventing unauth'd users from creating new blog posts
    :param permission:
    :return:
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.current_user.can(permission):
                return forbidden('Not permitted')
            return f(*args, **kwargs)
        return decorated_function
    return decorator
