__author__ = 'Stuart'
"""
API 1.0.
Backwards incompatible version of API would be own folder. For a mobile app for ex. Can't force upgrade everything.


"""

from flask import Blueprint

api = Blueprint('api', __name__)

from . import authentication, posts, users, comments, errors
