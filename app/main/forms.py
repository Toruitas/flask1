__author__ = 'Stuart'
from flask.ext.wtf import Form
from flask.ext.pagedown.fields import PageDownField
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField, ValidationError
from wtforms.validators import Required, DataRequired, InputRequired, Length, Email, Regexp
from ..models import Role, User

class NameForm(Form):
    name = StringField('What is your name?', validators=[DataRequired()])  # Required()
    submit = SubmitField('Submit')  # first arg is label used to render to HTML

class EditProfileForm(Form):
    name = StringField('Real name', validators=[Length(0,64)])  # can be 0 length, so show optional
    location = StringField('Location', validators=[Length(0,64)])
    about_me = TextAreaField('About Me')
    submit = SubmitField('Submit')

class EditProfileAdminForm(Form):
    email = StringField('Email', validators=[DataRequired(),Length(1,64),Email()])
    username = StringField('Username', validators=[
        DataRequired(), Length(1,64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                             'Usernames must have only letters, numbers, dots or underscores')
    ])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce = int)  # select field for drop-down field.
    name = StringField('Real name', validators=[Length(0,64)])
    location = StringField('Location', validators=[Length(0,64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        """
        roles aren't hardcoded above, but get info from a query. A SelectField's .choices attrib must be given as
        list of tuples, with each tuple consisting of 2 values: an identifier for item, and text to show in the control
        as a string. Coerce = int forces the identifier to be an int, rather than default string.
        :param user:
        :param args:
        :param kwargs:
        :return:
        """
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name) for role in Role.qeuery.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        """
        first check if changes were made, and if yes, ensures that new value doesn't duplicate another value.
        To do this, form receives user obj as arg and saves as self.user (in __init__).
        :param field:
        :return:
        """
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered')

    def validate_username(self, field):
        """
        WTForms inline validators: validate_field(form, field)
        :param field:
        :return:
        """
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use')

class PostForm(Form):
    body = PageDownField("What's on your mind?", validators = [DataRequired()])
    submit = SubmitField("Submit")

class CommentForm(Form):
    body = StringField('',validators = [DataRequired()])
    submit = SubmitField('Submit')

