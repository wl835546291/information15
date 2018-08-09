# -*- coding: utf-8 -*-
# @File  : __init__.py.py
# @Author: willem
# @time: 18-7-27 下午4:33
from flask import Blueprint

index_blue = Blueprint('index', __name__, url_prefix='')

from . import views