__author__ = 'Stuart'

"""
Template stuff
"""

from flask import Flask, render_template, url_for, redirect, session,flash
from flask.ext.bootstrap import Bootstrap
from flask.ext.moment import Moment
from flask.ext.wtf import Form
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.script import Manager, Shell
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.mail import Mail, Message
from wtforms import StringField, SubmitField
from wtforms.validators import Required, DataRequired, InputRequired  # look up difference between these
from datetime import datetime
import os
from threading import Thread  # cPython C extension modules that properly release the GIL will run in parallel


basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess string'  # saved in a no-shared github in a true version! diff each app!
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///' + os.path.join(basedir,'data.sqlite')
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True  # auto commits to DB at end of each request.
bootstrap = Bootstrap(app)
moment = Moment(app)
db = SQLAlchemy(app)
manager = Manager(app)
migrate = Migrate(app, db)
manager.add_command('db',MigrateCommand)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')  # xxxx@gmail.com
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')  # $env:MAIL_PASSWORD = "xxx343"
app.config['FLASKY_MAIL_SUBJECT_PREFIX'] = '[Flasky]'  # prefix string for subject
app.config['FLASKY_MAIL_SENDER'] = 'Flasky Admin <flasky@example.com>'  # sender
app.config['FLASKY_ADMIN'] = os.environ.get('FLASKY_ADMIN')  # xxxx@gmail.com
mail = Mail(app)


########## Models
class Role(db.Model):
    __tablename__ = 'roles'  # SQLA doesn't use the plural naming convention so, explicitly name it
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64),unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')
    # lists users assoc with role. backref adds role attr to User. lazy=dynamic returns query that hasn't been exec'd
    # yet so filters can be added to is.

    def __repr__(self):
        return '<Role {}>'.format(self.name)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64),unique=True,index=True)
    role_id = db.Column(db.Integer,db.ForeignKey('roles.id'))  # foreign key must match

    def __repr__(self):
        return '<User {}>'.format(self.username)

###############Shell context creation
def _make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role)
manager.add_command('shell', Shell(make_context=_make_shell_context))

########## Email
def send_email(to,subject, template, **kwargs):
    """
    After creating this we modify index.
    :param to:
    :param subject:
    :param template:
    :param kwargs:
    :return:
    """
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + subject,
                  sender = app.config['FLASKY_MAIL_SENDER'],
                  recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)  # plain text
    msg.html = render_template(template + '.html', **kwargs)  # html
    thr = Thread(target=send_async_email,args=[app,msg])
    thr.start()
    return thr

def send_async_email(app,msg):
    with app.app_context():
        mail.send(msg)

########## Forms
class NameForm(Form):
    name = StringField('What is your name?', validators=[DataRequired()])  # Required()
    submit = SubmitField('Submit')  # first arg is label used to render to HTML

########## Routes
@app.route('/', methods=['GET','POST'])
def index():
    #name = None
    form = NameForm()
    if form.validate_on_submit():
        #name = form.name.data
        #form.name.data = ''
        #old_name = session.get('name')
        # if old_name is not None and old_name != form.name.data:
        #     flash('Looks like you have changed your name!')
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            user = User(username = form.name.data)
            db.session.add(user)
            session['known'] = False
            if app.config['FLASKY_ADMIN']:
                send_email(app.config['FLASKY_ADMIN'],
                           'New User',
                           'mail/new_user',  # template argument
                           user=user)
        else:
            session['known'] = True
        session['name'] = form.name.data
        form.name.data = ''
        return redirect(url_for('index'))
    return render_template('index.html',
                           form = form,
                           name = session.get('name'),  # like with all dictionaries, using .get(key) avoids exception,
                           known = session.get('known',False),
                           current_time = datetime.utcnow())  # and would return None for a missing key

@app.route('/user/<name>')
def user(name):
    return render_template('user.html',name=name)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'),404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'),500



if __name__=="__main__":
    manager.run()
