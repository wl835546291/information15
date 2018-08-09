# -*- coding: utf-8 -*-
# @File  : __init__.py.py
# @Author: willem
# @time: 18-8-5 下午2:42
from flask import Blueprint
from flask import redirect
from flask import request
from flask import session

admin_blue = Blueprint('admin', __name__, url_prefix='/admin')

from . import views


# 添加请求钩子， 用户权限校验
@admin_blue.before_request
def check_admin():
    # 判断当前登录后台的用户是不是管理员
    is_admin = session.get('is_admin', None)
    # 如果不是管理员，就不能访问后台管理员界面
    if not is_admin and not request.url.endswith('/admin/login'):
        return redirect('/')
