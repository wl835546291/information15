# -*- coding: utf-8 -*-
# @File  : __init__.py.py
# @Author: willem
# @time: 18-7-29 下午5:22
from flask import Blueprint
# 初始化登录注册蓝图
passport_blue = Blueprint('passport', __name__, url_prefix='/passport')

from . import views