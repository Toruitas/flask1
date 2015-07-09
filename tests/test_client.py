__author__ = 'Stuart'

from flask import url_for
import unittest, re
from app import create_app, db
from app.models import User, Role

class FlaskClientTestCase(unittest.TestCase):
    def setUp(self):
        """
        self.client instance is flask test client obj. This exposes methods that issue requests into app. When created
        with use_cookies=True, will accept and send cookies in same way as browser, so can use cookies and create
        user sessions. Can/must log in and out.
        :return:
        """
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_home_page(self):
        """
        Searches for stranger in the response.
        get_data returns data as byte array by default, so as_test=True returns it in unicode string instead.
        :return:
        """
        response = self.client.get(url_for('main.index'))
        self.assertTrue('Stranger' in response.get_data(as_text=True))

    def test_register_and_login(self):
        # register a new account  -  fields must exactly match field names in form
        response = self.client.post(url_for('auth.register'), data = {
            'email':'john@example.com',
            'username': 'john',
            'password': 'cat',
            'password2':'cat'
        })
        # auth/register can respond in 2 ways: valid gets redirect to login. Invalid gets presented with form again plus
        # error messages.
        # 302 is redirect code
        self.assertTrue(response.status_code == 302)

        #log in with same new account
        response = self.client.post(url_for('auth.login'), data={
            'email' : 'john@example.com',
            'password':'cat'
        }, follow_redirects=True)  # makes test client act like browser and autoissue GET for redir URL.
        data = response.get_data(as_text=True)  # with this, 302 won't return, will get response from redir'd URL
        self.assertTrue(re.search('Hello,\s+john!', data))  # have to use regex since string is assembled from static &
                                                            # dynamic portions
        self.assertTrue('You have not confirmed your account yet' in data)

        # send a confirmation token
        # since usually this is emailed to a user, we can't access that. Solution here bypasses that and generates one
        # directly from User. Then we pass that directly to the auth.confirm url.
        # could also have extracted token by parsing email body, which Flask-Mail saves when running in a testing config
        # - find out how???
        user = User.query.filter_by(email='john@example.com').first()
        token = user.generate_confirmation_token()
        response = self.client.get(url_for('auth.confirm', token=token), follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertTrue('You have confirmed your account' in data)

        # logout
        response = self.client.get(url_for('auth.logout'), follow_redirects = True)
        data = response.get_data(as_text=True)
        self.assertTrue('You have been logged out' in data)
