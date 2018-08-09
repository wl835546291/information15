# -*- coding: utf-8 -*-
# @File  : config.py
# @Author: willem
# @time: 18-7-27 下午4:23
import redis


class Config(object):
    SQLALCHEMY_DATABASE_URI = 'mysql://root:mysql@localhost:3306/information15'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_HOST = 'localhost'    # 常量， 主机
    REDIS_PORT = 6379       # 常量， 端口

    SESSION_TYPE = 'redis'      # 设置session的存储数据类型
    # 创建一个session_redis, 用来存储session
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT)
    SESSION_USE_SIGNER = True   # 使用session签名
    PERMANENT_SESSION_LIFETIME = 86400 * 3  # 设置session的有效期， 单位为s， 86400表示一条

    SECRET_KEY = 'DAGDGRFDFEDS'

# 项目开发阶段， 测试模式
class DevelopmentConfig(Config):
    DEBUG = True

# 项目上线，  上线模式
class ProductionConfig(Config):
    DEBUG = False

config_map = {
    'develop': DevelopmentConfig,
    'production': ProductionConfig
}
