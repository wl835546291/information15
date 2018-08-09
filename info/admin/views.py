# -*- coding: utf-8 -*-
# @File  : views.py
# @Author: willem
# @time: 18-8-5 下午2:42
import time
from datetime import datetime, timedelta

from flask import current_app, jsonify
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for

from info import constants
from info import db
from info.models import User, News, Category
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import admin_blue


# 登录视图
@admin_blue.route('/login', methods=['post', 'get'])
def admin_login():
    # get请求， 获取信息
    if request.method == 'GET':
        # 判断用户是否登录， 且是否是管理员权限
        user_id = session.get('user_id', None)
        is_admin = session.get('is_admin', False)
        if user_id and is_admin:
            # 重定向到后台首页
            return redirect(url_for('admin.admin_index'))  # 前缀.方法名
        # 返回登录界面
        return render_template('admin/login.html')

    # 获取参数
    username = request.form.get('username')
    password = request.form.get('password')
    # 查询当前用户， 并判断
    user = User.query.filter(User.mobile == username, User.is_admin == True).first()
    if not user:
        return render_template('admin/login.html', errmsg='没有这个用户')
    # 校验密码
    if not user.check_password(password):
        return render_template('admin/login.html', errmsg='密码错误')

    # 将登录信息保存到session中
    session['user_id'] = user.id
    session['nick_name'] = user.nick_name
    session['mobile'] = user.mobile
    session['is_admin'] = user.is_admin
    # 重定向到后台首页, 参数为 路径/前缀.函数名
    return redirect(url_for('admin.admin_index'))


# 后台首页用户信息
@admin_blue.route('/index')
@user_login_data
def admin_index():
    # 获取登录用户信息
    user = g.user
    data = {
        'user_info': user.to_dict()
    }
    return render_template('admin/index.html', data=data)


# 用户统计数据展示
@admin_blue.route('/user_count')
def user_count():
    total_count = 0  # 总人数
    mon_count = 0  # 本月人数
    day_mount = 0  # 当天人数

    # 获取总人数， 不包括管理员用户
    total_count = User.query.filter(User.is_admin == False).count()
    # 获取当前时间, time.struct_time(tm_year=2018, tm_mon=8, tm_mday=5, tm_hour=17, tm_min=34, tm_sec=13, tm_wday=6, tm_yday=217, tm_isdst=0)
    now_time = time.localtime()

    # 本月开始时间， 年-月-01
    mon_begin = '%d-%02d-01' % (now_time.tm_year, now_time.tm_mon)
    # 格式化开始时间， 年-月-日 00:00:00       strptime(): 字符串转时间对象
    mon_begin_date = datetime.strptime(mon_begin, '%Y-%m-%d')
    # 本月新增人数
    mon_count = User.query.filter(User.is_admin == False, User.create_time >= mon_begin_date).count()

    # 当天开始时间， 年-月-日
    today_begin = '%d-%02d-%02d' % (now_time.tm_year, now_time.tm_mon, now_time.tm_mday)
    # 格式化当天开始时间， 年-月-日 00:00:00
    today_begin_date = datetime.strptime(today_begin, '%Y-%m-%d')
    # 当天新增人数
    day_mount = User.query.filter(User.is_admin == False, User.create_time >= today_begin_date).count()

    # 曲线图数据信息
    active_count = []  # 活跃人数列表
    active_time = []  # 活跃时间列表
    # 一月数据循环遍历得到
    for i in range(0, 30):
        # 每天开始时间，timedelta()计算时间差的函数，参数为距离当前时间之前的值
        begin_date = today_begin_date - timedelta(days=i)
        # 每天结束时间
        end_date = today_begin_date - timedelta(days=(i - 1))
        # 每天用户活跃数
        count = User.query.filter(User.is_admin == False, User.last_login >= begin_date,
                                  User.last_login <= end_date).count()
        active_count.append(count)  # 将人数添加到列表中
        # 将时间添加到列表中       strftime(): 时间对象转字符串
        active_time.append(begin_date.strftime('%Y-%m-%d'))

    # 列表反转，因为时间数量都是倒序的
    active_count.reverse()
    active_time.reverse()

    data = {
        'total_count': total_count,
        'mon_count': mon_count,
        'day_count': day_mount,
        'active_count': active_count,
        'active_time': active_time
    }
    return render_template('admin/user_count.html', data=data)


# 用户列表数据展示
@admin_blue.route('/user_list')
def user_list():
    # 获取参数，并校验转int
    page = request.args.get('p')
    try:
        page = int(page)
    except Exception as e:
        page = 1
    # 查询普通用户并分页，创建时间降序
    paginate = User.query.filter(User.is_admin == False).order_by(User.create_time.desc()).paginate(page, 10, False)
    items = paginate.items  # 每页的用户对象
    current_page = paginate.page
    total_page = paginate.pages
    # 将当前页的用户添加到列表中
    user_list = []
    for user in items:
        user_list.append(user.to_admin_dict())

    data = {
        'users': user_list,
        'current_page': current_page,
        'total_page': total_page
    }
    return render_template('admin/user_list.html', data=data)


# 新闻审核数据展示
@admin_blue.route('/news_review')
def news_review():
    # 获取参数页数
    page = request.args.get('p', 1)
    # 获取关键字, 表单提交没有action默认为当前路径， get请求会把表单name属性添加到url参数上
    keywords = request.args.get('keywords')
    try:
        page = int(page)
    except Exception as e:
        page = 1

    # 添加查询条件列表， 状态和关键字
    filter = [News.status != 0]
    if keywords:
        filter.append(News.title.contains(keywords))
    # 查询并分页
    paginate = News.query.filter(*filter).order_by(News.create_time.desc()).paginate(page, 10, False)
    items = paginate.items  # 每页的新闻对象
    current_page = paginate.page
    total_page = paginate.pages

    # 将当前页的新闻添加到列表中
    news_list = []
    for news in items:
        news_list.append(news.to_review_dict())

    data = {
        'news_list': news_list,
        'current_page': current_page,
        'total_page': total_page
    }
    return render_template('admin/news_review.html', data=data)


# 新闻审核详情：   页面加载    修改提交
@admin_blue.route('/news_review_detail', methods=['post', 'get'])
def news_review_detail():
    # get请求， 获取数据加载页面
    if request.method == 'GET':
        news_id = request.args.get('news_id')
        news = News.query.get(news_id)
        data = {
            'news': news.to_dict()
        }
        return render_template('admin/news_review_detail.html', data=data)

    # post请求， 获取参数
    action = request.json.get('action')
    news_id = request.json.get('news_id')
    # 根基新闻id查询该新闻
    news = News.query.get(news_id)

    if action == 'accept':  # 通过行为
        news.status = 0
    else:
        # 未通过原因
        reason = request.json.get('reason')
        if not reason:
            return jsonify(errno=RET.PARAMERR, errmsg="请说明没有通过的原因")
        news.status = -1
        news.reason = reason
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg='审核完成')


# 新闻编辑
@admin_blue.route('/news_edit')
def news_edit():
    page = request.args.get('p')
    try:
        page = int(page)
    except Exception as e:
        page = 1

    paginate = News.query.order_by(News.create_time.desc()).paginate(page, 10, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    news_list = []
    for news in items:
        news_list.append(news.to_review_dict())

    data = {
        'news_list': news_list,
        'current_page': current_page,
        'total_page': total_page
    }
    return render_template('admin/news_edit.html', data=data)


# 新闻编辑详情
@admin_blue.route('/news_edit_detail', methods=['post', 'get'])
def news_edit_detail():
    # get请求， 获取数据， 展示页面
    if request.method == 'GET':
        news_id = request.args.get('news_id')
        news = News.query.get(news_id)  # 新闻
        categorys = Category.query.all()  # 分类

        category_list = []
        for category in categorys:
            category_list.append(category.to_dict())
        category_list.pop(0)  # 排除最新分类

        data = {
            'news': news.to_dict(),
            'categories': category_list
        }
        return render_template('admin/news_edit_detail.html', data=data)

    # post请示， 修改数据后提交
    news_id = request.form.get('news_id')
    title = request.form.get('title')
    digest = request.form.get('digest')
    content = request.form.get('content')
    index_image = request.files.get('index_image').read()  # 文件获取用files
    category_id = request.form.get('category_id')
    # 判断是否为空
    if not all([title, digest, content, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数有误')

    key = storage(index_image)  # 七牛云返回的key

    news = News.query.get(news_id)
    news.title = title
    news.digest = digest
    news.content = content
    # 七牛云图片路径：  前缀 + key
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.category_id = category_id
    db.session.commit()

    return jsonify(errno=RET.OK, errmsg='新闻编辑成功')


# 新闻分类管理界面展示
@admin_blue.route('/news_type')
def news_type():
    categories = Category.query.all()
    category_list = []
    for category in categories:
        category_list.append(category.to_dict())
    category_list.pop(0)

    data = {
        'categories': category_list
    }
    return render_template('admin/news_type.html', data=data)


# 添加/修改新闻分类
@admin_blue.route('/add_category', methods=['post'])
def add_category():
    # 获取参数分类id和名字
    cid = request.json.get('id')
    name = request.json.get('name')
    if cid:
        # 编辑分类， 改名字
        category = Category.query.get(cid)
        category.name = name
    else:
        # 增加分类
        category = Category()
        category.name = name
        db.session.add(category)

    db.session.commit()
    return jsonify(errno=RET.OK, errmsg='新闻分类管理成功')


@admin_blue.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.admin_login'))
