from random import randint
from sqlalchemy.exc import IntegrityError
from faker import Faker
from . import db
from .models import User, Post, Group, Join
from flask import current_app
from app import search
from datetime import datetime

def _get_key (dict , value):
    return str([k for k, v in dict.items() if v == value][0])

def test_user():
    if User.query.filter_by(email='skylty01@gmail.com').first():
        return None
    u = User(email='skylty01@gmail.com',
             username='Sky',
             password='123',
             confirmed=True,
             is_admin=True)
    db.session.add(u)
    db.session.commit()

def users(count=100):
    fake = Faker('en_US')
    i = 0
    while i < count:
        u = User(email=fake.email(),
                 username=fake.user_name(),
                 password='password',
                 confirmed=True,
                 name=fake.name(),
                 location=fake.city())
        db.session.add(u)
        try:
            db.session.commit()
            i += 1
        except IntegrityError:
            db.session.rollback()

def groups():
    fake = Faker('en_US')
    user_count = User.query.count()
    for i in range(user_count):
        u = User.query.offset(i).first()
        if u.my_group is not None:
            continue
        g = Group(groupname=fake.name(),
                  about_us=fake.text(),
                  is_approved=1)
        u.my_group = g
        j = Join(group=g, member=u, is_approved=1)
        db.session.add(j)
        db.session.add(u)
        db.session.add(g)
    db.session.commit()

def followers(post, count=10):
    fake = Faker('en_US')
    i=0
    for user in User.query.all():
        if i >= count:
            break
        if user.is_following(post):
            continue
        post.followers.append(user)
        i += 1
    db.session.commit()

def posts(count=100):
    fake = Faker('en_US')
    group = Group.query.filter_by(is_approved=1)
    group_count = group.count()

    for i in range(count):
        datetime_from = datetime(2019, 7, randint(14, 20))
        datetime_to = datetime(2019, 7, randint(14, 20))
        g = group.offset(randint(0, group_count - 1)).first()
        p = Post(title='Activity %d' % i,
                 location=fake.city(),
                 tag=_get_key(current_app.config['TAGS'], randint(0, 5)),
                 datetime_from = datetime_from,
                 datetime_to = datetime_to,
                 post_html=fake.text(),
                 author=g)
        db.session.add(p)
    db.session.commit()
    search.update_index(Post)
