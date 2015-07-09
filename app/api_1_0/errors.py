__author__ = 'Stuart'
from flask import jsonify
from app.exceptions import ValidationError
from . import api



def bad_request(message):
    response = jsonify({'error':'bad request', 'message':message})
    response.status_code = 400
    return response

def unauthorized(message):
    """
    When login credentials invalid, server returns 401 to client. Flask-HTTPAuth does this automatically, but to
    ensure that the response is consistent with other errors returned by the API, error response can be customized here.
    :param message:
    :return:
    """
    response = jsonify({'error':'unauthorized', 'message':message})
    response.status_code = 401
    return response

def forbidden(message):
    response = jsonify({'error':'forbidden', 'message': message})
    response.status_code = 403
    return response

@api.errorhandler(ValidationError)
def validation_error(e):
    """
    Provides response to client. To avoid having to add exception catching code in view functions, a global exception
    handler can be installed. This is ValidationError's exception handler.

    Same @xxx.errorhandler used to register handlers for HTTP status codes, but in this usage takes an exception
    class as argument. Decorated funct will be invoked any time an exception of given class is raised.

    Decorator is obtained from API blueprint, so this handler only will be invoked when exception raised while on a
    route from within the blueprint is being processed.
    :param e:
    :return:
    """
    return bad_request(e.args[0])