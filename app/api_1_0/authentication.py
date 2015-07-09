__author__ = 'Stuart'
from flask import g, jsonify
from flask.ext.httpauth import HTTPBasicAuth
from ..models import User, AnonymousUser
from . import api
from .errors import unauthorized, forbidden

auth = HTTPBasicAuth()  # auth obj created

@auth.verify_password
def verify_password(email_or_token, password):
    """
    Email and password verified using existing support in User model. Verification returns True when login valid,
    else False. Anonymous logins are supported for which client must send a blank email field.
    Authentication callback saves the authenticated user in Flask's g global obj so that view function can access it
    later.
    When anon login rec'd, funct returns True and saves instance of AnonUser class into g.current_user.

    If email_or_token is blank, is anon user
    if pw blank, assume token validation
    if both not blank, assume email/pw validation

    With this, token validation is optional and up to client to use or not.

    To give view functions ability to distinguish between the 2 auth methods, a g.token_used variable is added.
    :param email:
    :param password:
    :return:
    """
    if email_or_token == '':
        g.current_user = AnonymousUser()
        return True
    if password == '':  # if pw blank, assumed to be a token and validated as such
        g.current_user = User.verify_auth_token(email_or_token)
        g.token_used = True
        return g.current_user is not None
    user = User.query.filter_by(email = email_or_token).first()  # if both email and pw not blank, assume email/pw auth
    if not user:
        return False
    g.current_user = user
    g.token_used = False
    return user.verify_password(password)

@auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')

@api.before_request
@auth.login_required
def before_request():
    if not g.current_user.is_anonymous() and not g.current_user.confirmed:
        return forbidden('Unconfirmed account')

@api.route('/token/')
def get_token():
    """
    Returns auth tokens to clients.
    Since is in blueprint, auth mechanisms added to before_request handler also apply to it.
    To prevent clients from using an old token to request a new one, the g.token_used variable is checked, and
    in that way requests authenticated with a toekn can be rejected.

    Returns token in JSON response with validity 1 hour. Period also included in JSON response.
    :return:
    """
    if g.current_user.is_anonymous() or g.token_used:
        return unauthorized('Invalid credentials')
    return jsonify({'token':g.current_user.generate_auth_token(expiration=3600),
                    'expiration':3600})