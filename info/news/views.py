# -*- coding: utf-8 -*-
# @File  : views.py
# @Author: willem
# @time: 18-8-1 下午8:57
from flask import g, jsonify
from flask import render_template
from flask import request

from info import db
from info.models import News, Comment, CommentLike, User
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import news_blue


# 新闻详情页面数据
@news_blue.route('/<int:news_id>')
@user_login_data
def news_detail(news_id):
    # 获取点击排行的前10条数据， 根据浏览量降序排序
    news_model = News.query.order_by(News.clicks.desc()).limit(10)
    news_lsit = []
    # 循环获取新闻排行信息， 并添加到列表中
    for new_mode in news_model:
        news_lsit.append(new_mode.to_dict())

    # 新闻详情内容： 根据id获取
    news = News.query.get(news_id)

    # 判断是否收藏该新闻， 默认为false
    is_collected = False
    # 判断用户是否收藏过该新闻
    user = g.user
    if user and news in user.collection_news:
        is_collected = True

    # 判断是否关注了该作者， 默认为false
    is_followed = False
    # 用户必须登录才能关注新闻作者， followed表示用户关注的人
    if user and news.user in user.followed:
        is_followed = True

    # 获取新闻评论列表
    comments = Comment.query.filter_by(news_id=news_id).order_by(Comment.create_time.desc()).all()
    # 转化为json格式添加到列表中
    comment_list = []

    comment_like_ids = []   # 该用户所有的点赞id
    if user:    # 用户必须登录才能查出该用户哪些评论点赞了
        # 该用户所有的点赞
        comment_like_list = CommentLike.query.filter(CommentLike.user_id == user.id).all()
        comment_like_ids = [comment_like.comment_id for comment_like in comment_like_list]
    for comment in comments:    # 遍历所有评论
        comment_dict = comment.to_dict()
        comment_dict['is_like'] = False     # 给评论字典添加一个属性, 记录该评论是否被该用户点赞
        if comment.id in comment_like_ids:  # 如果评论id在用户的评论点赞id中， 则用户已经点过赞了
            comment_dict['is_like'] = True
        comment_list.append(comment_dict)

    data = {
        'user_info': user.to_dict() if user else None,  # 用户
        'click_news_list': news_lsit,  # 排行
        'news': news.to_dict(),  # 新闻
        'is_collected': is_collected,  # 是否收藏过
        'is_followed': is_followed, # 是否关注过
        'comments': comment_list  # 评论
    }
    # 展示新闻详细信息
    return render_template('news/detail.html', data=data)


# 新闻收藏功能
@news_blue.route('/news_collect', methods=['post'])
@user_login_data
def news_collect():
    user = g.user
    if not user:  # 判断用户是否登录， 必须登录后才能收藏
        return jsonify(errno=RET.SESSIONERR, errmsg='用户未登录')

    # 获取参数
    news_id = request.json.get('news_id')
    action = request.json.get('action')  # 收藏/取消收藏

    # 根据新闻id获取该新闻
    news = News.query.get(news_id)

    if action == 'collect':
        user.collection_news.append(news)  # 收藏新闻
    else:
        user.collection_news.remove(news)  # 取消收藏
    # 持久化到数据库
    db.session.commit()

    return jsonify(errno=RET.OK, errmsg='收藏成功')


# 评论新闻功能
@news_blue.route('/news_comment', methods=['post'])
@user_login_data
def news_comment():
    user = g.user
    if not user:  # 必须登录后才能评论
        return jsonify(errno=RET.SESSIONERR, errmsg='用户未登录')

    # 获取参数
    news_id = request.json.get('news_id')
    content = request.json.get('comment')
    parent_id = request.json.get('parent_id')  # 父评论id（回复的评论的id）

    comment = Comment()  # 实例化评论对象
    comment.user_id = user.id
    comment.news_id = news_id
    comment.content = content  # 评论内容
    if parent_id:  # 不是所有的评论都有回复
        comment.parent_id = parent_id
    # 将评论保存到数据库中
    db.session.add(comment)
    db.session.commit()

    # 前端需要comment对象数据， 所以响应中要添加data
    return jsonify(errno=RET.OK, errmsg='评论成功', data=comment.to_dict())


@news_blue.route('/comment_like', methods=['post'])
@user_login_data
def comment_like():
    user = g.user
    if not user:  # 点赞用户必须登录
        return jsonify(errno=RET.SESSIONERR, errmsg='用户未登录')

    comment_id = request.json.get('comment_id')  # 评论id
    news_id = request.json.get('news_id')  # 新闻id
    action = request.json.get('action')  # 点赞/取消点赞

    # 根据评论id获取要点赞的评论
    comment = Comment.query.get(comment_id)

    # 查询当前评论的点赞信息， 根据评论id和用户id查询
    comment_like = CommentLike.query.filter(CommentLike.comment_id == comment_id,
                                            CommentLike.user_id == user.id).first()
    if action == 'add':     # 点赞操作
        if not comment_like:
            comment_like = CommentLike()    # 实例化点赞对象
            comment_like.comment_id = comment_id    # 评论id
            comment_like.user_id = user.id  # 用户id
            db.session.add(comment_like)    # 添加到会话
            comment.like_count += 1     # 点赞数 + 1
    else:   # 取消点赞操作
        if comment_like:
            db.session.delete(comment_like)     # 删除点赞
            comment.like_count -= 1     # 点赞数 - 1
    db.session.commit()

    return jsonify(errno=RET.OK, errmsg='操作成功')


# 关注/取消关注
@news_blue.route('/followed_user', methods=['post'])
@user_login_data
def followed_user():
    user = g.user
    if not user:
        return jsonify(errno = RET.SESSIONERR,errmsg = "请登陆")

    # 被关注新闻作者的id
    author_id = request.json.get('user_id')
    action = request.json.get('action')     # 关注/取消关注

    # 新闻作者的信息
    author = User.query.get(author_id)

    # 关注
    if action == 'follow':
        # 判断作者是否在用户关注的粉丝中
        if author not in user.followed:
            user.followed.append(author)
        else:
            return jsonify(errno = RET.NODATA, errmsg = '已经关注过了')
    else:
        # 取消关注
        if author in user.followed:
            user.followed.remove(author)
        else:
            return jsonify(errno = RET.NODATA, errmsg='没有相应关注')

    db.session.commit()
    return jsonify(errno = RET.OK, errmsg = 'ok')
