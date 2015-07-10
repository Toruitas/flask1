__author__ = 'Stuart'

import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    FLASKY_MAIL_SUBJECT_PREFIX = '[Flasky]'
    FLASKY_MAIL_SENDER = 'Flasky Admin <flasky@example.com>'
    FLASKY_ADMIN = os.environ.get('FLASKY_ADMIN')  # email addy that when recognized is auto-promoted to admin
    FLASKY_POSTS_PER_PAGE = 20
    FLASKY_COMMENTS_PER_PAGE = 30
    FLASKY_FOLLOWERS_PER_PAGE = 50
    SQlALCHEMY_RECORD_QUERIES = True  # enable recording of q stats
    FLASKY_SLOW_DB_QUERY_TIME= 0.5  # timeout of half sec
    SSL_DISABLE = True

    @staticmethod
    def init_app(app):
        """
        Takes app instance as arg.
        Here, config specific initialization can be performed.
        """
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir,'data-test.sqlite')
    WTF_CSRF_ENABLED = False  # since extracting and parsing the CSRF token in tests is a bitch, easier to disable

class ProductionConfig(Config):
    """
    When app in debug mode, Werk's interactive debugger appears on webpage to look at source. But in Production,
    this is silenced. Flask on stuartup creates instance of logging.Logger and attaches to app as app.logger. In
    debug mode, the logger writes to console, but in production mode there are no handlers configd for it by default,
    so unless a handler is added, logs aren't stored. This here config's a logging handler that sends errors while
    running in production mode to the list of admin's emails config'd in the FLASKY_ADMIN setting.

    Class methods are bound to classes not objs, so since we don't instantiate any Production config, it's what we use.
    Maybe.
    Good for factory methods, like this.
    https://julien.danjou.info/blog/2013/guide-python-static-class-abstract-methods
    """
    import psycopg2
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir,'data.sqlite')

    @classmethod
    def init_app(cls, app):  # cls has to be 1st arg for class methods
        Config.init_app(app)

        # email errors to admins
        import logging
        from logging.handlers import SMTPHandler
        credentials = None
        secure = None
        if getattr(cls, 'MAIL_USERNAME', None) is not None:
            credentials = (cls.MAIL_USERNAME, cls.MAIL_PASSWORD)
            if getattr(cls, 'MAIL_USE_TLS', None):
                secure = ()
        mail_handler = SMTPHandler(
            mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT),
            fromaddr=cls.FLASKY_MAIL_SENDER,
            toaddrs=[cls.FLASKY_ADMIN],
            subject=cls.FLASKY_MAIL_SUBJECT_PREFIX + ' Application Error',
            credentials=credentials,
            secure=secure)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

class HerokuConfig(ProductionConfig):
    SSL_DISABLE = bool(os.environ.get('SSL_DISABLE'))

    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)  # first this so we get the email logging

        # handle proxy server headers
        # Heroku passes everything internally with HTTP, so if a request started with HTTPS and then got changed to
        # HTTP inside, browser would give warning.
        # All components of a page must have matching security.
        # Werk has a middleware that checks custom headers ad updates the request obj accordingly, so that
        # request.is_secure for example reflects security of the req the client sent to reverse proxy server of Heroku
        # and not that the proxy server sent to app. Pg225
        # WSGI middlewares such as ProxyFix are added by wrapping the WSGI app.
        # When reqcomes, middlewares get chance to inspect the environ and make changes before req is processed.
        # Necessary for any reverse proxy server deployment.
        from werkzeug.contrib.fixers import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)

        # log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)

config = {
    'development' : DevelopmentConfig,
    'testing' : TestingConfig,
    'production' : ProductionConfig,
    'heroku': HerokuConfig,
    'default': DevelopmentConfig,
}