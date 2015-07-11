__author__ = 'Stuart'
#!usr/bin/flask1venv python

import os
COV = None
if os.environ.get('FLASK_COVERAGE'):
    """
    branch=True tests that all conditionals in each method are tested.
    Include everything that is in the app folder, so that we aren't testing inside migrations for ex.
    """
    import coverage
    COV = coverage.coverage(branch=True, include='app/*')
    COV.start()

if os.path.exists('.env'):
    print('Importing environment from .env...')
    for line in open('.env'):
        var = line.strip().split('=')
        if len(var) == 2:
            os.environ[var[0]] = var[1]

from app import create_app, db
from app.models import User, Role, Post, Follow, Permission, Comment
from flask.ext.script import Manager,Shell
from flask.ext.migrate import Migrate, MigrateCommand

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app,db)

def make_shell_context():
    return dict(app=app,db=db, User=User, Role=Role, Post=Post, Follow=Follow, Permission=Permission, Comment=Comment)
manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)

@manager.command  # implements custom commands
def test(coverage=False):
    """
    Run the unit tests.
    To invoke: python manage.py test

    Coverage tools measure how much of app is being tested, and reports on what parts are/aren't.

    :return:
    """
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        import sys
        os.environ['FLASK_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable] + sys.argv)
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://{}/index.html'.format(covdir))
        COV.erase()

@manager.command
def profile(length=25, profile_dir=None):
    """
    start the application under teh code profiler

    Another possible source of performance problems is high CPU usage, caused by funcs that perform heavy computing.
    Source code profiles useful in finding slowest parts of an app. It watches a running app and records fns called &
    how long it takes. Then reports.

    It should do this in dev environment, since it sucks up resources itself don't do this in production

    Flask's dev webserver from Werkzeug can optionally enable python profiler for each request.
    This creates CL command for that!

    When started with this, console shows profiler stats for each request, which will include slowest 25 funcs.
    -- length option can be used to change num fns shown. --profile-dir option will save profile data for each req
    to file in given dir. Data files can be used to generate more detailed reports that include a call graph.

    https://docs.python.org/3.4/library/profile.html

    :param length:
    :param profile_dir:
    :return:
    """
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length], profile_dir=profile_dir)
    app.run()

@manager.command
def deploy():
    """
    Regardless of hosting method used, there are a series of tasks that must be carried out when an application is
    installed on a production server. Ex: Creation/update of DB tables. Having to run these tasks manually each time app
    is installed or upgraded is error prone and time consuming, so instead a command that performs all the req'd tasks
    can be added...

    These are all designed in a way that causes no problems if they are executed multiple times. Designing update funcs
    in this way makes it possible to run just this "deploy" command every time an installation or upgrade is done.
    :return:
    """
    """Run deployment tasks."""
    from flask.ext.migrate import upgrade
    from app.models import Role, User

    # migrate DB to latest revision
    upgrade()

    # create user roles
    Role.insert_roles()

    #create self-follows for all users
    User.add_self_follows()

if __name__=="__main__":
    manager.run()