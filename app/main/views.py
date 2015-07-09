__author__ = 'Stuart'

from datetime import datetime
from flask import render_template, redirect, url_for, abort, flash, request, current_app, make_response
from flask.ext.login import login_required, current_user
from flask.ext.sqlalchemy import get_debug_queries
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, CommentForm
from .. import db
from ..models import User, Permission, Role, Post, Comment
from ..decorators import admin_required, permission_required

@main.route('/', methods = ['GET','POST'])
def index():
    form = PostForm()
    if current_user.can(Permission.WRITE_ARTICLES) and form.validate_on_submit():
        post = Post(body=form.body.data,
                    author=current_user._get_current_object())
        db.session.add(post)
        return redirect(url_for('.index'))  # redirs within blueprint can use this form, across needs 'bpname.index'
    page = request.args.get('page',1, type=int)  # request's query string is available as request.args. When explicit
    # page isn't given, default=1. type=int ensures will be int.
    show_followed = False
    if current_user.is_authenticated():
        show_followed = bool(request.cookies.get('show_followed',''))  # choice of showing all or none stored in cookie
            # called show_followed. When set to nonempty string means only followed posts should be shown.
            # Cookies are stored in request obj as a request.cookies dict.
            # String val of cookie converted to Boolean
    if show_followed:
        query = current_user.followed_posts  # uses user's followed posts property.
    else:
        query = Post.query
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'], error_out=False)  # paginate obj takes page num
    # as first required arg, then optional per_page defaults to 20 or whatever is config'd. Error_out: True issues 404
    # if a page outside valid range requested, error_out:Flase returns empty list. looks like ?page=2.
    #posts = Post.query.order_by(Post.timestamp.desc()).all()  # loads all posts
    posts = pagination.items
    return render_template('index.html',
                           form=form,
                           pagination=pagination,
                           posts  = posts,
                           current_time = datetime.utcnow(),
                           show_followed=show_followed)

@main.route('/admin')
@login_required
@admin_required
def for_admins_only():
    return "For admins!"

@main.route('/moderator')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def for_moderators_only():
    return "For comment moderators!"

@main.route('/edit-profile', methods=['GET','POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(user)
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)

@main.route('/edit-profile/<int:id>')
@login_required
@admin_required
def edit_profile_admin(id):
    """
    allows admin to edit attributes for user based on ID
    :param id:
    :return:
    """
    user = User.query.get_or_404(id)  # if invalid, returns 404
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)  #
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)

@main.route('/user/<username>')
def user(username):
    """
    List of posts obtained from User.posts relationshup, so gotta load user first. Then, since it's a query obj, we
    order it by timestamp.
    :param username:
    :return:
    """
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    posts = user.posts.order_by(Post.timestamp.desc()).all()
    return render_template('user.html', user=user, posts=posts)

@main.route('/edit/<int:id>', methods = ['GET','POST'])
@login_required
def edit(id):
    """
    allows only author of a blog post to edit it, except for admins, who can edit all posts
    If user tries to edit another user's post, 403's.
    PostForm is same one as used on homepage.
    :param id:
    :return:
    """
    post = Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMINISTER):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        flash('The post has been updated')
        return redirect(url_for('.post', id=post.id))
    form.body.data = post.body
    return render_template('edit_post.html', form=form)

@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    flash('You are now following {}'.format(username))
    return redirect(url_for('.user', username=username))

@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('You are not following this user.')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    flash('You are not following {} anymore'.format(username))
    return redirect(url_for('.user', username=username))

@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page',1, type=int)
    pagination = user.followers.paginate(
        page,
        per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False
    )
    follows = [{'user':item.follower, 'timestamp':item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title='Followers of',
                           endpoint = '.followers', pagination=pagination, follows=follows)

@main.route('/followed-by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page,
        per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False
    )
    follows = [{'user':item.followed, 'timestamp':item.timestamp} for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint = '.followed_by', pagination=pagination, follows=follows)

@main.route('/all')
@login_required
def show_all():
    """
    when invoked, show_followed cookie set to proper value.
    Cookies can only be set on a response obj so these routes need to create one through make_response() instead of
    letting flask do it.
    Takes cookie name, and value as first 2 args, then time in seconds for last one. 30 days here.
    :return:
    """
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60)
    return resp

@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed','1',max_age=30*24*60*60)
    return resp

@main.route('/post/<int:id>', methods = ['GET','POST'])
def post(id):
    """
    sends comment form to post.html template for rendering.
    As in the Post case, author of comment can't be directly set to current_user, since this is a context variable
    proxy object. The expression current_user._get_current_object() returns actual User obj.
    Comments sorted by timestamp, so new comments always added to bottom of list.
    When new comment entered, redir goes to same url but page at -1, for last page to see our comment.
    If page == -1 does math to see what the actual page number would be.
    Then gets list of comments associated with the post.comments 1-many relationship, sorted by timestamp, and paginated
    .
    :param id:
    :return:
    """
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body = form.body.data,
                          post = post,
                          author = current_user._get_current_object())
        db.session.add(comment)
        flash('Your comment has been published')
        return redirect(url_for('.post', id=post.id, page=1))
    page = request.args.get('page',1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) / current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page,
        per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('post.html', posts=[post], form=form,
                           comments = comments, pagination=pagination)

@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate():
    page = request.args.get('page',1,type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page,
        per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('moderate.html', comments=comments,
                           pagination=pagination, page=page)

@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_enable(id):
    """
    grabs comment by id, sets disabled to false, and returns moderate url to keep modding, and whatever page was inc'd
    in the request string.
    :param id:
    :return:
    """
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page = request.args.get('page',1,type=int)))

@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled= True
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page = request.args.get('page',1,type=int)))

@main.route('/shutdown')
def server_shutdown():
    """
    After all tests completed, flask server gracefully shut down. Since server is running in own thread, only way to
    ask that is to send a regular HTTP request.

    Only works when app is running in testing mode. Invoking in other configs will fail.

    Werk exposes a shutdown funct in the environ, then we call it and return.
    :return:
    """
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if not shutdown:
        abort(500)
    shutdown()
    return 'Shutting down'

@main.after_app_request
def after_request(response):
    """
    Doesn't modify the response, just gets query timings recorded by flask-sqla & logs slow ones.
    get_debug_queries returns q's issued during request as a list.

    Walks the list & logs any that last longer than our defined time.
    Logging is issued at the warning level. Changing level to error would cause all slow query occurrences to be emailed
    as well.

    Get debug queries enabled only in debug by default. But performance issues rare during development since small db's
    are used. So, it's usefull to have this in production.
    :param response:
    :return:
    """
    for query in get_debug_queries():
        if query.duration >= current_app.config['FLASKY_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: {}\n'
                'Parameters: {}\n'
                'Duration: {}\n,'
                'Context: {}\n'.format(query.statement, query.parameters, query.duration, query.context))
            # not included: query.start_time, query.end_time
    return response