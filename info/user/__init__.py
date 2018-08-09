# -*- coding: utf-8 -*-
# @File  : __init__.py.py
# @Author: willem
# @time: 18-8-4 上午9:09
from flask import Blueprint

user_blue = Blueprint('user', __name__, url_prefix='/user')

from . import views
