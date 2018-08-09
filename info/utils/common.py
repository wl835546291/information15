# -*- coding: utf-8 -*-
# @File  : common.py
# @Author: willem
# @time: 18-8-1 下午5:12
import functools

from flask import g
from flask import session

from info.models import User


def do_index_class(index):
    """点击排行编号的样式过滤器"""
    if index == 0:
        return 'first'
    elif index == 1:
        return 'second'
    elif index == 2:
        return 'third'
    else:
        return ''


def user_login_data(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 从session中获取当前登录的用户
        user_id = session.get('user_id')
        user = None
        # 判断当前用户是否登录
        if user_id:
            # 通过id获取用户信息
            user = User.query.get(user_id)
        g.user = user
        return func(*args, **kwargs)

    return wrapper
