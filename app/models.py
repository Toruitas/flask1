__author__ = 'Stuart'
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask.ext.login import UserMixin, AnonymousUserMixin
from flask import current_app, request, url_for
from markdown import markdown
import bleach
import datetime
import hashlib
from . import db, login_manager
from app.exceptions import ValidationError

class Follow(db.Model):
    """
    Association table that includes timestamp. The many-many relationship must be decomped into 2 1-many relats for
    L and R sides.
    """
    __tablename__='follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    body_html = db.Column(db.Text)
    comments = db.relationship('Comment', backref='post', lazy='dynamic')

    def to_json(self):
        """
        When writing a web service, frequently need to convert internal repr of resource to/from JSON.
        url, author, comments need to return URLs for their resources. The routes defined in API blueprint.
        _external = True so full URLs not partial/relative ones included.

        This shows it's possible to return 'made up' attrs in representation of a resource. Comment_count returns
        num comments that exist for post, even though that isn't a real attribute. It's conveneint for client.
        :return:
        """
        json_post = {
            'url':url_for('api.get_post', id=self.id, _external=True),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author': url_for('api.get_user', id=self.author_id, _external=True),
            'comments': url_for('api.get_post_comments', id=self.id, _external=True),
            'comment_count': self.comments.count()
        }
        return json_post

    @staticmethod
    def from_json(json_post):
        """
        Only uses body attr from JSON dict, body_html ignored since server-side Markdown rendering is auto-triggered
        by a SQLAlch event when body attr is modified. timestamp doesnt need to be given, as it defaults to now,
        author isn't used since client has no authority to select author, the only possible one is the authenticated
        user. Comments and comment_count are auto generated from DB relationship. URL field ignored since resource
        URLs are defined by server, not client.

        For error checking, if body field empty/missing, throws error. This method doesn't know enough to properly
        handle condition. Passes error up to caller, enabling higher level code to do error handling.
        ValidationError class we implemented is a simple subclass of Python's ValueError.
        :param json_post:
        :return:
        """
        body = json_post.get('body')
        if body is None or body =='':
            raise ValidationError('post does not have a body')
        return Post(body=body)

    @staticmethod
    def generate_fake(count=100):
        """
        Similar to User's fake user generator. Only use this from shell AFTER creating users. Otherwise one user
        may have a billion posts!
        """
        from random import seed, randint
        import forgery_py

        seed()
        user_count = User.query.count()
        for i in range(count):
            u = User.query.offset(randint(0, user_count - 1)).first()
            p = Post(body=forgery_py.lorem_ipsum.sentences(randint(1,3)),
                     timestamp = forgery_py.date.date(True),
                     author=u)
            db.session.add(p)
            db.session.commit()

    @staticmethod
    def on_changed_body(target,value, oldvalue, initiator):
        """
        Renders HTML vers of body and stores in body_html, making conversion automatic
        1) markdown() does initial conversion to html.
        2) result passed to clean() plus list of allowed HTML tags. Removes any tags not approved.
        3) linkify converts any URLs written in plaintext to <a> links. Automatic link generation isn't officially
        included in Markdown specs. Pagedown supportsit as an extension, so linkify() used in the server
        to match.
        4)replaces post.body with post.body_html
        """
        allowed_tags = ['a','abbr','acronym','b','blockquote','code','em',
                        'i','li','ol','pre','strong','ul','h1','h2','h3','p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value,output_format='html'),
            tags = allowed_tags, strip=True
        ))

db.event.listen(Post.body,'set',Post.on_changed_body)  # regist'd as listener of SQLAlch's 'set' event for body. It will
    # automatically be invoked whenever the body field on any instance of the class is set to a new value


class Permission:
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0x04
    MODERATE_COMMENTS = 0x08
    ADMINISTER = 0x80

class Role(db.Model):
    """
    default should be set to True for only one role, False for others. Role marked as default will be assigned upon
    registration.
    Permissions is integer used as bit flags. Each task will be assigned a bit position, and for each role the tasks
    that are allowed for that role will have their bits set to 1.
    """
    __tablename__ = 'roles'  # SQLA doesn't use the plural naming convention so, explicitly name it
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64),unique=True)
    default = db.Column(db.Boolean, default=False, index=True)  # default should be true for only one Role, false else
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')
    # lists users assoc with role. backref adds role attr to User. lazy=dynamic returns query that hasn't been exec'd
    # yet so filters can be added to is.

    def __repr__(self):
        return '<Role {}>'.format(self.name)

    @staticmethod
    def insert_roles():
        """
        Tries to find existing roles by name and update those. New role obj created only for role names not in db
        already. This done so that role list can be updated in future when changes need to be made. To add a new role or
        change the permission assignments for a role, change the roles dictionary and return the function.
        Anonymous role doesn't need to be represented in db, as it is designed for users who aren't in the db.
        To apply to db: shell, Role.insert_roles() Role.query.all()
        :return:
        """
        roles = {'User': (Permission.FOLLOW | Permission.COMMENT | Permission.WRITE_ARTICLES, True),
                 'Moderator': (Permission.FOLLOW | Permission.COMMENT |
                               Permission.WRITE_ARTICLES | Permission.MODERATE_COMMENTS, False),
                 'Administrator': ('0xff', False)}  # can change these and run it later to change permissions
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)  # create new role
            role.permissions = roles[r][0]  # set role's permissions
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64),unique=True, index=True)
    role_id = db.Column(db.Integer,db.ForeignKey('roles.id'))  # foreign key must match
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default = False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(),default=datetime.datetime.utcnow)
        # utcnow has no () bc default can take a funct as default value, so each time default needs to be gen'd, fn
        # invoked to produce it.
    last_seen = db.Column(db.DateTime(),default=datetime.datetime.utcnow)  # refresh this evrytime usr access site
    avatar_hash = db.Column(db.String(32))
    posts = db.relationship('Post', backref='author', lazy='dynamic')  # adds author attr to Posts
    followed = db.relationship('Follow',  # class relationship
                               foreign_keys = [Follow.follower_id],  # specify foreign key to use
                               backref = db.backref('follower', lazy='joined'),  # backrefs to Follow model.
                                    # joined for single query together, rather than loaded lazily when first accessed
                                    # and each attribute would require an individual query - obtaining complete list of
                                    # followed users would require 100 added db queries!
                               lazy = 'dynamic',  # dynamic returns query objects rather than items directly, so
                                    # can add fillters to query before executed.
                               cascade = 'all, delete-orphan')  # how acts performed on a parent obj propogate to
                                    # related objs. When an obj added to db session, any objs assoc'd with it thru
                                    # relationships will be auto-added too. Default cascade options usually adequate,
                                    # but change here. Default when deleting obj is to set foreign key to null, but for
                                    # assoc table we want to delete entries that point to a record that was deleted
                                    # thus destroying the link. this is delete-orphan
                                    # 'all' doesn't actually add all. Have to specifically add delete-orphan.
    followers = db.relationship('Follow',
                                foreign_keys = [Follow.followed_id],
                                backref = db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade = 'all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy = 'dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def __init__(self, **kwargs):
        super(User,self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:  # at first registration, checks to see if email is
                # the admin's email and assigns them admin powers
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
        self.followed.append(Follow(followed=self))

    def follow(self, user):
        """
        manually inserts Follow instance into the assoc table linking a follower with followed user. Giving app opport
        to set the custom field.
        users connecting are manually assigned to new Follow instance, then added to db as usual.
        No need to set timestamp since defined with default current date and time.
        :param user:
        :return:
        """
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        """
        uses followed relationship to locate Follow instance linking user to followed user to unfollow. To destroy link,
        instance is simply deleted.
        :param user:
        :return:
        """
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self,user):
        """
        searches
        :param user:
        :return:
        """
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self,user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        return True

    def gravatar(self, size=100, default='identicon', rating='g'):
        """
        Gravatar associates avatar images with email addys. Users create acct at gravatar.com and upload images. To gen
        avatar URL, it's MD5 hash is calculated.
        :param size:
        :param default:
        :param rating:
        :return:
        """
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or hashlib.md5(self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating
        )

    def ping(self):
        """
        must be called each time a request from user is rec'd. Since the before_app_request handler in auth
        blueprint runs before every request, it can do this easily.
        :return:
        """
        self.last_seen = datetime.datetime.utcnow()
        db.session.add(self)

    def can(self, permissions):
        """
        performs bitwise & operation between permissions and permissions of assigned role. Returns True if all the
        requested bits are present in the role, which means user should be allowed to perform the tasks.
        00000001 & 00000010 = 000000011
        :param permissions:
        :return:
        """
        return self.role is not None and (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    @property
    def password(self):
        """
        Trying to read password property will return this error, since original password can't be
        recovered once hashed
        :return:
        """
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        """
        When password property is set, setter method will hash it and write it to the password_hash
        field
        :param password:
        :return:
        """
        self.password_hash = generate_password_hash(password)

    def verify_password(self,password):
        """
        Takes pw and checks it for verification against hashed version stored in User model.
        If returns True, then password is corect.
        :param password:
        :return:
        """
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):  # generates token with default validity 1 hr
        """
        Generates encrypted confirmation token based on a cryptokey (SECRET_KEY here) containing confirmation ID for
        account.
        Secured cookies signed by its dangerous can be used for this token purpose.
        Dumps takes given data ({confirm:self.id}) and generates crypto token in the form of a long-ass random
        string
        :param expiration:
        :return:
        """
        s = Serializer(current_app.config['SECRET_KEY'], expiration)  # creates JSON web sign with exp time
        return s.dumps({'confirm':self.id})  #

    def confirm(self, token):
        """
        Serializer loads() method takes token
        :param token:
        :return:
        """
        s = Serializer(current_app.config['SECRET_KEY'])  # generates thingy
        try:
            data = s.loads(token)  # tries to load based off of token, checks token time too
        except:
            return False  # oh no! .loads threw an exception for invalid token or invalid time, so we return False
        if data.get('confirm') != self.id:  # if token not for current_user.id, deny access.
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    @property
    def followed_posts(self):
        """
        By issuing join op first, the q can be started from Post.query, so now only 2 filters needed are join() and
        filter(). SLQA first collects all the filters and then gens the q in most efficient way.

        Alt:
        return db.session.query(Post).select_from(Follow).\
            filter_by(follower_id=self.id).\
            join(Post, Follow.followed_id == Post.author_id)

        query that returns post objects
        select_from(Follow) begins from Follow model
        filters follows table by the following user
        joins results of filter_by() with the Post objects
        """
        return Post.query.join(Follow, Follow.followed_id == Post.author_id).filter(Follow.follower_id == self.id)

    def generate_auth_token(self, expiration):
        """
        Client must send auth credentials with every request for RESTful. To avoid constantly transferring sensitive
        info, token-based auth used.

        Client sends login credentials to special URL that gennys auth tokens. once client has token, it can be used
        instead of login credentials to authenticate requests. For security reasons, have expiration.

        Returns signed token encoding user's id field.
        :param expiration:
        :return:
        """
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id':self.id}).decode('ascii')

    @staticmethod
    def verify_auth_token(token):
        """
        Takes token and if found valid, returns user stored in it.
        Static method as user will be known only after token decoded.
        :param token:
        :return:
        """
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    @staticmethod
    def add_self_follows():
        """
        goes through all users and makes them follow selves.

        Creating funcs taht introduce updates to the db is a common technique to update deployed apps, as running
        a scripted update is less error prone than updating dbs manually.
        """
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    def to_json(self):
        """
        Omit email and role for privacy.
        """
        json_user = {
            'url':url_for('api.get_user', id=self.id, _external=True),  # may be api.get_post
            'username': self.username,
            'member_since': self.member_since,
            'last_seen': self.last_seen,
            'posts': url_for('api.get_user_posts', id=self.id, _external=True),
            'followed_posts': url_for('api.get_user_followed_posts', id=self.id, _external=True),
            'post_count': self.posts.count()
        }
        return json_user

    @staticmethod
    def generate_fake(count=100):
        """
        uses forgery.py and a random seed to create random fake users.
        """
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(email = forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(True),
                     password = forgery_py.lorem_ipsum.word(),
                     confirmed=True,
                     name=forgery_py.name.full_name(),
                     location=forgery_py.address.city(),
                     about_me=forgery_py.lorem_ipsum.sentence(),
                     member_since = forgery_py.date.date(True))
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:  # just in case there are duplicates, although very unlikely
                db.session.rollback()



class AnonymousUser(AnonymousUserMixin):
    """
    registered to anonymous users when user isn't logged in. App can thus still freely call .can() and .is_admin()
    without checking if is logged in first.
    """
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False
login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Comment(db.Model):
    """
    Nearly same as Post.
    Disabled field is boolean used by mods to suppress offensive/inappropriate comments.
    """
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index = True, default = datetime.datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    def to_json(self):
        json_comment = {
            'url': url_for('api.get_comment', id=self.id, _external=True),
            'post': url_for('api.get_post', id=self.post_id, _external=True),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author': url_for('api.get_user', id=self.author_id,
                              _external=True),
        }
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body = json_comment.get('body')
        if body is None or body == '':
            raise ValidationError('comment does not have a body')
        return Comment(body=body)

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        """
        triggers anytime body field changes with the below db.event.listen.
        Fewer tags allowed than in a Post, since they tend to be shorter.
        :return:
        """
        allowed_tags = ['a','abbr','acronym','b','code','em','i','strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value,output_format = 'html'),
            tags = allowed_tags, strip=True
        ))
db.event.listen(Comment.body, 'set', Comment.on_changed_body)