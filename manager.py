# -*- coding: utf-8 -*-
# @File  : manager.py
# @Author: willem
# @time: 18-7-27 下午2:51
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script import Manager

from info import create_app, db
from info.models import User

app = create_app('develop')

# 脚本管理器
manager = Manager(app)
# 数据库迁移
migrate = Migrate(app, db)
# 向脚本管理器中添加一条命令
manager.add_command('mysql', MigrateCommand)


# 创建管理员用户， 装饰器中参数： key  value  函数参数
@manager.option('-n', '--name', dest='name')
@manager.option('-p', '--password', dest='password')
def create_super_user(name, password):
    user = User()
    user.nick_name = name  # 昵称
    user.password = password
    user.mobile = name
    user.is_admin = True  # 是否是管理员权限

    db.session.add(user)
    db.session.commit()


if __name__ == '__main__':
    # app.run()
    manager.run()   # 启动服务器
