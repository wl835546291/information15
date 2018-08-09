# -*- coding: utf-8 -*-
# @File  : __init__.py.py
# @Author: willem
# @time: 18-7-27 下午4:27
import logging
from logging.handlers import RotatingFileHandler

import redis
from flask import Flask
from flask import g
from flask import render_template
from flask.ext.session import Session
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.wtf import CSRFProtect
from flask.ext.wtf.csrf import generate_csrf

from config import config_map

# 设置日志的记录等级
logging.basicConfig(level=logging.DEBUG)  # 调试debug级
# 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
# 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
# 为刚创建的日志记录器设置日志记录格式
file_log_handler.setFormatter(formatter)
# 为全局的日志工具对象（flask app使用的）添加日志记录器
logging.getLogger().addHandler(file_log_handler)

db = SQLAlchemy()
redis_store = None  # type: redis.StrictRedis


# 传过来的参数表示config的配置文件的名字
def create_app(config_name):
    app = Flask(__name__)

    # 根据字典的key， 获取到字典的value
    # config_class = config_map.get(config_name)
    config_class = config_map[config_name]

    app.config.from_object(config_class)

    db.init_app(app)

    global redis_store
    # 创建redis, 用于存储验证码(短信验证码， 图片验证码)
    redis_store = redis.StrictRedis(host=config_class.REDIS_HOST, port=config_class.REDIS_PORT, decode_responses=True)

    Session(app)  # 导入session

    CSRFProtect(app)  # 开启CSRF保护

    # 请求钩子, 对响应做进一步处理
    @app.after_request
    def after_request(resp):
        csrf_token = generate_csrf()  # 生成csrf_token
        resp.set_cookie('csrf_token', csrf_token)  # 将csrf_token添加到cookie中
        return resp

    # 404页面
    from info.utils.common import user_login_data
    @app.errorhandler(404)
    @user_login_data
    def page_not_found(error):  # 必须添加参数，接收错误信息
        user = g.user
        data = {
            'user_info': user.to_dict() if user else None
        }
        return render_template('news/404.html', data=data)

    from info.utils.common import do_index_class
    # 添加一个自定义模板过滤器indexClass
    app.add_template_filter(do_index_class, 'indexClass')

    # 注册index蓝图
    from info.index import index_blue
    app.register_blueprint(index_blue)

    # 注册登录注册蓝图
    from info.passport import passport_blue
    app.register_blueprint(passport_blue)

    # 注册新闻蓝图
    from info.news import news_blue
    app.register_blueprint(news_blue)

    # 注册个人中心蓝图
    from info.user import user_blue
    app.register_blueprint(user_blue)

    # 注册管理员蓝图
    from info.admin import admin_blue
    app.register_blueprint(admin_blue)

    return app
