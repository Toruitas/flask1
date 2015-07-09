__author__ = 'Stuart'

from flask import Flask
from flask.ext.bootstrap import Bootstrap
from flask.ext.mail import Mail
from flask.ext.moment import Moment
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.pagedown import PageDown
from config import config


bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()
pagedown = PageDown()

login_manager = LoginManager()
login_manager.session_protection='strong'  # can be none, basic, strong. Strong keeps track of IP & browser.
# will log out if change detected
login_manager.login_view = 'auth.login'  # sets endpoint for login page. Since this is inside a blueprint, needs to be prefixed
# by blueprint name

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])  # gets configuration from config file's object by name
    config[config_name].init_app(app)  # runs init_app

    # extension objs not initially bound to an app
    bootstrap.init_app(app)  # serve local static?
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    pagedown.init_app(app)

    # attach routes and custom error pages here


    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    # url_prefix optional. When used, all routes defined in blueprint will register with given prefix.
    # in this case: /auth. For example. /login will be /auth/login. localhost:5000/auth/login

    from .api_1_0 import api as api_1_0_blueprint
    app.register_blueprint(api_1_0_blueprint, url_prefix='/api/v1.0')

    return app

