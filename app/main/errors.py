__author__ = 'Stuart'

# pg 80

from flask import render_template, request, jsonify
from . import main

@main.app_errorhandler(403)
def forbidden(e):
    """
    New version of error handler checks Accept request header, which werkzeug decodes into request.accept_mimetypes,
    to determine what format client wants response in. Browsers generally don't specify restrictions on
    response formats, so JSON response only gen'd for clients that accept JSON not HTML.
    """
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response = jsonify({'error':'forbidden'})
        response.status_code = 403
        return response
    return render_template('403.html'), 403

@main.app_errorhandler(404)
def page_not_found(e):
    """
    A difference when writing error handlers inside a blueprint is that if the errorhandler
decorator is used, the handler will only be invoked for errors that originate in the blueprint.
To install application-wide error handlers, the app_errorhandler must be used
instead.

For API, we need to adjust it to respond based on format requested by client, this is called content negotiation.
    :param e:
    :return:
    """
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response = jsonify({'error':'not found'})
        response.status_code = 404
        return response
    return render_template('404.html'), 404

@main.app_errorhandler(500)
def internal_server_error(e):
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response = jsonify({'error':'internal server error'})
        response.status_code = 500
        return response
    return render_template('500.html'), 500

