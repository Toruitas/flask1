from flask import Flask, request, make_response, redirect, abort
from flask.ext.script import Manager


app = Flask(__name__)
manager = Manager(app)


@app.route('/')
def index():
    user_agent = request.headers.get('User-Agent')
    return '<p>Your browser is {}</p>'.format(user_agent)

@app.route('/user/<name>')
def user(name):
    return '<h1>Hello, {}!</h1>'.format(name)

@app.route('/article/<int:pagenum>')
def article(pagenum):
    return "<span>You're on page {}</span>".format(pagenum)

@app.route('/badrequest')
def badrequest():
    return "<h1>Bad Request</h1>", 400

@app.route('/makeresponse')
def makeresponse():
    response = make_response('<h1>This document carries a cookie!</h1>')
    response.set_cookie('answer','42')
    return response

@app.route("/redirect")
def redirect():
    return redirect('http://www.example.com')

@app.route('/user/<id>')
def get_user(id):
    """
    Abort doesn't return control back to the function athat calls it but gives control
    back to the web server by raising an exception.
    :param id:
    :return:
    """
    user = load_user(id)
    if not user:
        abort(404)
    return '<h1>Hello, {}</h1>'.format(user.name)

if __name__ == '__main__':
    #app.run(debug=True)
    manager.run()  # flask-script gives us a way to pass config argvs. Kind of like the Django manage.py
                    # will run it in debug mode. Many options available with --help
                    # --host will defaults listen on localhost. --host 0.0.0.0 makes it available to networked cpus
