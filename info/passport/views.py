# -*- coding: utf-8 -*-
# @File  : views.py
# @Author: willem
# @time: 18-7-29 下午5:22
import random
import re
from datetime import datetime

from flask import current_app
from flask import make_response, jsonify
from flask import request
from flask import session

from info import constants, db
from info import redis_store
from info.models import User
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET
from . import passport_blue


# 图片验证码
@passport_blue.route('/image_code')
def image_code():
    # 获取前端传递过来的随机的一个验证码编号
    code_id = request.args.get('code_id')
    # 生成图片验证码 `name：名字  text： 图片上的内容   image： 图片
    name, text, image = captcha.generate_captcha()
    print('图片验证码为： ', text)
    # 将图片验证码保存到redis中， 参数： key， value， 过期时间
    redis_store.set('image_code_' + code_id, text, 300)

    # make_response: 响应体对象，  参数为图片验证码
    resp = make_response(image)
    # 响应头类型： image/jpg
    resp.headers['Content-Type'] = 'image/jpg'
    return resp


# 短信验证码
@passport_blue.route('/sms_code', methods=['get', 'post'])
def sms_code():
    # 1. 接收参数并判断是否有值
    mobile = request.json.get('mobile')  # 获取手机号
    image_code = request.json.get('image_code')  # 获取图片验证码
    image_code_id = request.json.get('image_code_id')  # 获取的图片验证码编号， 用于获取redis中的真实图片验证码
    # 验证前端传过来的参数是否为空
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg='请输入参数')  # errno为错误码   errmsg为错误信息

    # 2.校验手机号是否正确, 正则匹配
    if not re.match(r'1[345678]\d{9}', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='请输入正确的手机号')

    # 3.获取redis中的真实图片验证码,并验证是否过期
    real_image_code = redis_store.get('image_code_' + image_code_id)
    # 判断redis是否过期
    if not real_image_code:
        return jsonify(errno=RET.NODATA, errmsg='图片验证码已经过期')

    # 4.判断用户输入的图片验证码， 转为小写再判断
    print('是否一样： ', image_code.lower(),real_image_code.lower())
    if image_code.lower() != real_image_code.lower():
        return jsonify(errno=RET.PARAMERR, errmsg='请输入正确的图片验证码')

    # 5.随机生成一个6位数的短信验证码， 不足补0   000006
    random_sms_code = '%06d' % random.randint(0, 999999)
    print('短信验证码为：', random_sms_code)
    # 将验证码保存到redis中， 参数： key, 短信验证码， 过期时间
    redis_store.set('sms_code_' + mobile, random_sms_code, constants.SMS_CODE_REDIS_EXPIRES)

    # 6.发送短信: 参数： 手机号   列表：短信验证码/有效分钟数   模板id(默认为1)
    # status_code = CCP().send_template_sms('15213012374', [random_sms_code, constants.SMS_CODE_REDIS_EXPIRES/60], 1)
    # 7.返回发送状态： 0表示发送短信成功
    # if status_code !=0:
    #     return jsonify(errno = RET.THIRDERR, errmsg = '短信发送失败')
    return jsonify(errno = RET.OK, errmsg = '短信发送成功')

# 注册
@passport_blue.route('/register', methods = ['get', 'post'])
def register():
    # 1.获取前端传过来的参数：   mobile  smscode password
    mobile = request.json.get('mobile')
    sms_code = request.json.get('smscode')
    password = request.json.get('password')

    # 2.获取redis中保存的短信验证码，判断是否过期
    real_sms_code = redis_store.get('sms_code_' + mobile)
    if not real_sms_code:
        return jsonify(errno = RET.NODATA, errmsg = '短信验证码已过期')

    # 3.判断输入的和redis中的短信验证码是否一致
    print('短信码是否一致： ', sms_code, real_sms_code)
    if sms_code != real_sms_code:
        return jsonify(errno = RET.PARAMERR, errmsg = '请输入正确的短信验证码')

    # 4.创建一个用户， 来保存注册信息,持久化到数据库
    user = User()
    user.mobile = mobile
    user.password = password
    user.nick_name = mobile     # 昵称
    user.last_login = datetime.now()    # 获取当前时间
    db.session.add(user)
    db.session.commit()
    print('持久化成功')

    # 5.返回注册成功
    return jsonify(errno = RET.OK, errmsg = '注册成功')

@passport_blue.route('/login', methods = ['get', 'post'])
def login():
    # 1.获取参数信息
    mobile = request.json.get('mobile')
    password = request.json.get('password')

    # 2.通过手机号查询当前用户,并判断是否注册
    user = None
    try:
        # user = User.query.filter(User.mobile == mobile).first()
        user = User.query.filter_by(mobile = mobile).first()
    except Exception as e:
        # 把错误信息存储到log日志中
        current_app.logger.error(e)
    # 判断用户是否注册
    if not user:
        return jsonify(errno = RET.NODATA, errmsg = '请注册')

    # 3.通过系统的源码方法帮我们检查用户的密码是否正确
    if not user.check_password(password):
        return jsonify(errno = RET.PWDERR, errmsg = '请输入正确的密码')

    # 4.将用户登录状态保存， 保存用户信息到session中
    session['user_id'] = user.id
    session['nick_name'] = user.nick_name
    session['mobile'] = user.mobile

    # 5.更新最后登录时间
    user.last_login = datetime.now()
    db.session.commit()

    return jsonify(errno = RET.OK, errmsg = '登录成功')


@passport_blue.route('/logout')
def logout():
    # 清空session, 当没元素时返回None
    session.pop('user_id', None)
    session.pop('nick_name', None)
    session.pop('mobile', None)
    session.pop('is_admin', None)   # 管理员不会在前台页面登录

    # 返回结果
    return jsonify(errno = RET.OK, errmsg = '退出成功')
