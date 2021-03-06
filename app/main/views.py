# !/usr/bin/env python
#  encoding: utf-8

from flask import render_template, abort, redirect, url_for, flash, request, current_app, make_response
from ..models import User, Role, Permission, Post, Permission, Comment
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, CommentForm
from .. import db
from flask.ext.login import current_user, login_required
from ..decorators import admin_required, permission_required

from . import main


@main.route("/", methods=['GET', 'POST'])
def index():
	#return render_template('index.html')
	form = PostForm()
	if current_user.can(Permission.WRITE_ARTICLES) and form.validate_on_submit():
		post = Post(body=form.body.data, author=current_user._get_current_object())
		db.session.add(post)
		return redirect(url_for('.index'))
	page = request.args.get('page', 1, type=int)
	show_followed = False
	if current_user.is_authenticated:
		show_followed = bool(request.cookies.get('show_followed',''))
	if show_followed:
		query = current_user.followed_posts
	else:
		query = Post.query
	pagination = query.order_by(Post.timestamp.desc()).paginate(page, 
		per_page=current_app.config.get('FLASK_POSTS_PER_PAGE', 10), error_out=False)
	#posts = Post.query.order_by(Post.timestamp.desc()).all()
	posts = pagination.items
	return render_template('index.html', form=form, 
		posts=posts, Permission=Permission, pagination=pagination, show_followed=show_followed)


@main.route("/user/<username>")
def user(username):
	user = User.query.filter_by(username=username).first()
	if not user:
		abort(404)
	posts = user.posts.order_by(Post.timestamp.desc()).all()
	return render_template("user.html", user=user, posts=posts, Permission=Permission)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
	form = EditProfileForm()
	if form.validate_on_submit():
		current_user.name = form.name.data
		current_user.location = form.location.data
		current_user.about_me = form.about_me.data
		db.session.add(current_user)
		flash('Your profile has been updated.')
		return redirect(url_for('.user', username=current_user.username))
	form.name.data = current_user.name
	form.location.data = current_user.location
	form.about_me.data = current_user.about_me
	return render_template("edit_profile.html", form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
	user = User.query.get_or_404(id)
	form = EditProfileAdminForm(user=user)
	if form.validate_on_submit():
		user.email = form.email.data
		user.username = form.username.data
		user.confirmed = form.confirmed.data
		user.role = Role.query.get(form.role.data)
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


@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
	'''
		current_user是上下文代理对象
		真正的User对象要使用current_user._get_current_object()获取
	'''
	post = Post.query.get_or_404(id)
	form = CommentForm()
	if form.validate_on_submit():
		comment = Comment(body=form.body.data, post=post, author=current_user._get_current_object())
		db.session.add(comment)
		flash('Your comment has been published.')
		return redirect(url_for('.post', id=post.id, page=-1))
	page = request.args.get('page', 1, type=int)
	if page == -1:
		page = (post.comments.count() - 1) / current_app.config.get('FLASK_COMMENTS_PER_PAGE', 10) + 1
	pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
		page, per_page=current_app.config.get('FLASK_COMMENTS_PER_PAGE', 10), error_out=False)
	comments = pagination.items
	return render_template('post.html', posts=[post], form=form, 
		comments=comments, pagination=pagination, Permission=Permission)


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
	post = Post.query.get_or_404(id)
	if current_user != post.author and not current_user.is_administrator:
		abort(403)
	form = PostForm()
	if form.validate_on_submit():
		post.body = form.body.data
		db.session.add(post)
		flash('The post has been updated.')
		return redirect(url_for('.post', id=post.id))
	form.body.data = post.body
	return render_template('edit_post.html', form=form)


@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
	u = User.query.filter_by(username=username).first()
	if u is None:
		flash('Invalid user.')
		return redirect(url_for('.index'))
	if current_user.is_following(u):
		flash('You are already following this user.')
		return redirect(url_for('.user', username=username))
	current_user.follow(u)
	db.session.add(current_user)
	flash('You are now following %s.' % username)
	return redirect(url_for('.user', username=username))


@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
	u = User.query.filter_by(username=username).first()
	if u is None:
		flash('Invalid user.')
		return redirect(url_for('.index'))
	if not current_user.is_following(u):
		flash('You have not following this user.')
		return redirect(url_for('.user', username=username))
	current_user.unfollow(u)
	db.session.add(current_user)
	flash('You are now unfollowing %s.' % username)
	return redirect(url_for('.user', username=username))


@main.route('/followers/<username>')
@login_required
def followers(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('Invalid user.')
		return redirect(url_for('.index'))
	page = request.args.get('page', 1, type=int)
	pagination = user.followers.paginate(
		page, per_page=current_app.config.get('FLASK_FOLLOWERS_PER_PAGE',10),error_out=False)
	follows = [{'user': item.follower, 'timestamp': item.timestamp} for item in pagination.items]
	return render_template('followers.html', user=user, title='Followers of', endpoint='.followers',
		pagination=pagination, follows=follows)



@main.route('/followed_by/<username>')
@login_required
def followed_by(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('Invalid user.')
		return redirect(url_for('.index'))	
	page = request.args.get('page', 1, type=int)
	pagination = user.followed.paginate(
		page, per_page=current_app.config.get('FLASK_FOLLOWERS_PER_PAGE', 10), error_out=False)
	follows = [{'user': item.followed, 'timestamp': item.timestamp} for item in pagination.items]
	return render_template('followers.html', user=user, title='Followed of', endpoint='.followed_by',
		pagination=pagination, follows=follows)


@main.route('/all')
@login_required
def show_all():
	# cookie只能在响应对象中设置， 因此要用make_response方法创建响应对象
	resp = make_response(redirect(url_for('.index')))
	resp.set_cookie('show_followed', '', max_age=30*24*60*60)
	return resp


@main.route('/followed')
@login_required
def show_followed():
	resp = make_response(redirect(url_for('.index')))
	resp.set_cookie('show_followed', '1', max_age=30*24*60*60)
	return resp


@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate():
	page = request.args.get('page', 1, type=int)
	pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
		page, per_page=current_app.config.get('FLASK_COMMENTS_PER_PAGE', 10), error_out=False)
	comments = pagination.items
	return render_template('moderate.html', comments=comments, pagination=pagination, page=page)


@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_enable(id):
	comment = Comment.query.get_or_404(id)
	comment.disabled = False
	db.session.add(comment)
	return redirect(url_for('.moderate', page=request.args.get('page', 1, type=int)))


@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_disable(id):
	comment = Comment.query.get_or_404(id)
	comment.disabled = True
	db.session.add(comment)
	return redirect(url_for('.moderate', page=request.args.get('page', 1, type=int)))