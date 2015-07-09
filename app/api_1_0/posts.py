__author__ = 'Stuart'

from flask import jsonify, request, g, abort, url_for, current_app
from .. import db
from ..models import Post, Permission
from . import api
from .decorators import permission_required
from .errors import forbidden

@api.route('/posts/')
def get_posts():
    """
    Contains data items in a page, yay.
    :return:
    """
    page = request.args.get('page',1,type=int)
    pagination = Post.query.paginate(
        page,
        per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_posts', page=page-1, _external=True)
    next_posts = None
    if pagination.has_next:
        next_posts = url_for('api.get_posts', page=page+1, _external=True)
    return jsonify({
        'posts':[post.to_json() for post in posts],
        'prev': prev,
        'next': next_posts,
        'count': pagination.total
    })


@api.route('/posts/<int:id>')
def get_post(id):
    """
    404 error handler is at app level but will provide JSON if client requests that format
    If response customized to web service desired, 404 error handler can be overridden in blueprint
    :param id:
    :return:
    """
    post = Post.query.get_or_404(id)
    return jsonify(post.to_json())

@api.route('/posts/', methods=['POST'])
@permission_required(Permission.WRITE_ARTICLES)
def new_post():
    """
    Post handler for blog post resources inserts a new blog post into db.

    Wrapped in permission required that ensures authenticated user has permission to write.
    Creation of post is straightforward due to error handling we implemented earlier. A blog post is created from JSON
    data and author explicitly assigned as authenticated user.
    After model written to DB, 201 status code returned and Location header added with URL of new resource.

    Body of response includes new resource in JSON, so client doesn't have to issue another GET right after creation.
    :return:
    """
    post = Post.from_json(request.json)
    post.author = g.current_user
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_json()), 201, {'Location': url_for('api.get_post', id=post.id, _external=True)}

@api.route('/posts/<int:id>', methods=['PUT'])
@permission_required(Permission.WRITE_ARTICLES)
def edit_post(id):
    """
    permission checks a bit more complex. Check for permission to write is with decorator, but to allow user to edit
    a blog post, func must also check for user is author or admin. If this check had to be done a lot, a decorator could
    be created to do that.

    Since application doesn't allow deletion of posts, handler for DELETE request doesn't need to be implemented.
    :param id:
    :return:
    """
    post = Post.query.get_or_404(id)
    if g.current_user != post.author and not g.current_user.can(Permission.ADMINISTER):
        return forbidden("Not permitted")
    post.body = request.json.get('body', post.body)
    db.session.add(post)
    return jsonify(post.to_json())
