# -*- coding: utf-8 -*-
# @File  : views.py
# @Author: willem
# @time: 18-8-4 上午9:09
from flask import g, jsonify
from flask import redirect
from flask import render_template
from flask import request

from info import constants
from info import db
from info.models import Category, News, User
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import user_blue


# 主视图函数， 数据展示
@user_blue.route('/info')
@user_login_data
def get_user_info():
    # 获取用户信息
    user = g.user
    if not user:  # 用户未登录则重定向到首页
        return redirect('/')

    data = {
        'user_info': user.to_dict()
    }

    return render_template('news/user.html', data=data)


# 基本资料设置
@user_blue.route('/base_info', methods=['post', 'get'])
@user_login_data
def base_info():
    # 1.获取用户登录信息,用于显示修改前的值
    user = g.user
    if request.method == 'GET':
        data = {
            'user_info': user.to_dict()
        }
        return render_template('news/user_base_info.html', data=data)
    # 2.获取参数并判断是否为空
    nick_name = request.json.get('nick_name')
    gender = request.json.get('gender')
    print(gender)
    signature = request.json.get('signature')
    if not all([nick_name, gender, signature]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不能为空')
    # 3.设置基本信息并提交数据库
    user.nick_name = nick_name
    user.gender = gender
    user.signature = signature
    db.session.commit()
    # 4.返回结果
    return jsonify(errno=RET.OK, errmsg='修改成功')


# 头像设置
@user_blue.route('/pic_info', methods=['get', 'post'])
@user_login_data
def pic_info():
    # 获取用户登录信息， 用户显示头像
    user = g.user
    if request.method == 'GET':
        data = {
            'user_info': user.to_dict()
        }
        return render_template('news/user_pic_info.html', data=data)
    # 获取到用户上传的图片
    avatar = request.files.get('avatar').read()
    key = storage(avatar)  # 获取返回的key

    # 更新用户头像并提交到数据库
    user.avatar_url = key
    db.session.commit()

    data = {
        # 七牛云上的图片地址   七牛云 + key
        'avatar_url': constants.QINIU_DOMIN_PREFIX + key
    }
    return jsonify(errno=RET.OK, errmsg='上传成功', data=data)


# 密码修改
@user_blue.route('/pass_info', methods=['get', 'post'])
@user_login_data
def pass_info():
    # 获取用户信息， 用户后面设置密码
    user = g.user
    if request.method == 'GET':
        return render_template('news/user_pass_info.html')
    # 获取参数， 检验旧密码
    old_password = request.json.get('old_password')
    new_password = request.json.get('new_password')
    if not user.check_password(old_password):
        return jsonify(errno=RET.PWDERR, errmsg='密码错误')
    # 跟新密码
    user.password = new_password
    db.session.commit()

    return jsonify(errno=RET.OK, errmsg='密码修改成功')


# 我的收藏
@user_blue.route('/collection')
@user_login_data
def collection():
    user = g.user
    # 获取参数， 并转为整型， get请求取到的数据为str
    page = request.args.get('p')
    try:
        page = int(page)
    except Exception as e:
        page = 1

    # 获取用户新闻列表并分页
    paginate = user.collection_news.paginate(page, 3, False)
    items = paginate.items  # 当前页的新闻个数
    current_page = paginate.page  # 当前页
    total_page = paginate.pages  # 总页数

    # 将新闻转为字典添加到列表中
    collection_list = []
    for news in items:
        collection_list.append(news.to_dict())

    # 返回模板和数据
    data = {
        'collections': collection_list,
        'current_page': current_page,
        'total_page': total_page
    }
    return render_template('news/user_collection.html', data=data)


# 新闻发布
@user_blue.route('/news_release', methods=['get', 'post'])
@user_login_data
def news_release():
    user = g.user
    # 获取所有新闻分类, 用于更新新闻分类
    if request.method == 'GET':
        categorys = Category.query.all()
        category_list = []
        for category in categorys:
            category_list.append(category.to_dict())

        # 删除最新
        category_list.pop(0)
        data = {
            'categories': category_list
        }
        return render_template('news/user_news_release.html', data=data)

    # 获取前端传过来的参数,并判断是否为空
    title = request.form.get('title')
    category_id = request.form.get('category_id')
    digest = request.form.get('digest')
    index_image = request.files.get('index_image').read()
    content = request.form.get('content')
    if not all([title, category_id, digest, index_image, content]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不能为空')

    # 将图片传给七牛云， 返回key
    key = storage(index_image)

    # 设置数据， 提交数据库
    news = News()
    news.title = title
    news.category_id = category_id
    news.digest = digest
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.content = content
    news.source = '个人发布'
    news.user_id = user.id
    news.status = 1
    db.session.add(news)
    db.session.commit()

    return jsonify(errno=RET.OK, errmsg='发布成功')


# 新闻列表
@user_blue.route('/news_list')
@user_login_data
def news_list():
    user = g.user
    # 获取参数并转换类型
    page = request.args.get('p')
    try:
        page = int(page)
    except Exception as e:
        page = 1
    # 获取个人发布的新闻并分页
    paginate = News.query.filter(News.user_id == user.id).paginate(page, 10, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    # 当前页面的新闻
    news_list = []
    for news in items:
        news_list.append(news.to_review_dict())
    # 返回模板+数据
    data = {
        'news_list': news_list,
        'current_page': current_page,
        'total_page': total_page
    }
    return render_template('news/user_news_list.html', data=data)


# 我的关注
@user_blue.route('/user_follow')
@user_login_data
def user_follow():
    user = g.user
    # 获取页数
    page = request.args.get('p')
    try:
        page = int(page)
    except Exception as e:
        page = 1

    # 分页处理
    paginate = user.followed.paginate(page, 3, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    # 将当前页用户关注的粉丝添加到列表中
    followed_list = []
    for follow in items:
        followed_list.append(follow.to_dict())

    data = {
        'followeds': followed_list,
        'current_page': current_page,
        'total_page': total_page
    }
    return render_template('news/user_follow.html', data=data)


# 作者用户概况
@user_blue.route('/other_info')
@user_login_data
def other_info():
    # 用户必须登录
    user = g.user
    if not user:
        # return jsonify(errno=RET.SESSIONERR, errmsg="请登陆")
        return redirect('/')
    # 作者id
    author_id = request.args.get('id')
    # 作者信息
    author = User.query.get(author_id)

    # 该作者是否被关注了
    is_followed = False
    if author and author in user.followed:
        is_followed = True

    data = {
        'user_info': user.to_dict(),
        'author_info': author.to_dict(),
        'is_followed': is_followed
    }
    return render_template('news/other.html', data=data)


# 作者用户的新闻列表
@user_blue.route('/other_news_list')
def other_news_list():
    # 获取参数并校验
    page = request.args.get('p')
    author_id = request.args.get('user_id')
    try:
        page = int(page)
    except Exception as e:
        page =1
    # 分页处理
    paginate = News.query.filter(News.user_id == author_id).paginate(page, 2, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    news_list = []
    for news in items:
        news_list.append(news.to_dict())

    data = {
        'news_list': news_list,
        'current_page': current_page,
        'total_page': total_page
    }
    return jsonify(errno=RET.OK, errmsg="OK", data=data)
