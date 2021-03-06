# !/usr/bin/env python
#  encoding: utf-8


from functools import wraps
from flask import abort
from flask.ext.login import current_user
from .models import Permission


def permission_required(permission):
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			if not current_user.can(permission):
				abort(403)
			'''
			要return，否则会出现View function did not return a response错误
			'''
			return func(*args, **kwargs)
		return wrapper
	return decorator
	

def admin_required(func):
	return permission_required(Permission.ADMINISTER)(func)
	'''
	@wraps(func)
	def wrapper(*args, **kwargs):
		if not current_user.can(Permission.ADMINISTER):
			abort(403)
		func(*args, **kwargs)
	return wrapper
	'''  