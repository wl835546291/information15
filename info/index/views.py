# -*- coding: utf-8 -*-
# @File  : views.py
# @Author: willem
# @time: 18-7-27 下午4:34
from flask import current_app, jsonify
from flask import g
from flask import render_template
from flask import request
from flask import session

from info.models import User, News, Category
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import index_blue


@index_blue.route('/')
@user_login_data
def index():
    # 获取点击排行的前10条数据， 根据浏览量降序排序
    news = News.query.order_by(News.clicks.desc()).limit(10)
    news_lsit = []
    # 循环获取新闻排行信息， 并添加到列表中
    for new_mode in news:
        news_lsit.append(new_mode.to_dict())

    # 获取新闻分类的数据
    categorys = Category.query.all()
    category_list = []
    for category in categorys:
        category_list.append(category.to_dict())

    data = {
        'user_info': g.user.to_dict() if g.user else None,
        'click_news_list': news_lsit,
        'categorys': category_list
    }
    # 展示首页相关信息
    return render_template('news/index.html', data=data)


# 更新小图标icon
@index_blue.route('/favicon.ico')
def favicon():
    # current_app代理对象， 代理的是app对象
    # send_static_file 发送静态文件到浏览器
    return current_app.send_static_file('news/favicon.ico')


@index_blue.route('/news_list')
def news_list():
    # 1.获取参数
    # 获取新闻类型id， 默认为1
    cid = request.args.get('cid', 1)
    # 获取页数，默认为1
    page = request.args.get('page', 1)
    # 获取每页新闻个数， 默认10个
    per_page = request.args.get('per_page', 10)

    # 2.校验参数
    try:
        # 前端传过来的参数为str， 需要转为整型
        cid = int(cid)
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        cid = 1
        page = 1
        per_page = 10

    # 3.查询数据, 只查询审核通过的新闻
    filter = [News.status == 0]
    # 将新闻类别不是1(最新)的模糊查询添加到列表中
    # 等于1时数据库中没数据， 是查询所有新闻来加载
    if cid != 1:
        filter.append(News.category_id == cid)
    # 实例化paginate分页对象， 参数：页数， 每页新闻数， 没有对应页时是否报错；  *filter拆包
    paginate = News.query.filter(*filter).order_by(News.create_time.desc()).paginate(page, per_page, False)

    # if cid == 1:
    #     paginate = News.query.order_by(News.create_time.desc()).paginate(page, per_page, False)
    # else:
    #     paginate = News.query.filter(Category.id == cid).order_by(News.create_time.desc()).paginate(page, per_page, False)

    # 获取到当前页面需要展示的数据
    items = paginate.items
    # 当前页
    current_page = paginate.page
    # 总页数
    total_page = paginate.pages

    # 当前页中的新闻
    news_list = []
    for item in items:
        news_list.append(item.to_dict())

    # 4.返回数据
    data = {
        'current_page': current_page,
        'total_page': total_page,
        'news_dict_li': news_list
    }
    return jsonify(errno=RET.OK, errmsg='ok', data=data)
