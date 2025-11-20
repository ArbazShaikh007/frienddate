import os, jwt
from functools import wraps
from flask import request, jsonify
from base.database.db import db
from flask_login import UserMixin
from werkzeug.security import check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from base.common.utiils import COMMON_URL


class Admin(UserMixin, db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    fullname = db.Column('fullname', db.String(100), nullable=False)
    email = db.Column('email', db.String(100), nullable=False)
    phonenumber = db.Column('phonenumber', db.String(100), nullable=False)
    password = db.Column('password', db.String(300),
                         nullable=False)
    image_name = db.Column('image_name', db.String(225), default='conprofile.png')
    image_path = db.Column('image_path', db.String(225),
                           default="https://frienddate-app.s3.amazonaws.com/conprofile.png")
    otp = db.Column(db.Integer)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def as_dict(self):
        return {
            'id': self.id,
            'username': self.fullname,
            # 'lastname' : self.lastname,
            'email': self.email,
            'phonenumber': self.phonenumber,
            'password': self.password,
        }

    def get_token(self, expiress_sec=1800):
        serial = Serializer('192b9bdd22ab9ed4d12e236c78afcb9a393ec15f71bbf5dc987d54727823bcbf', expiress_sec)
        return serial.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_token(token):
        serial = Serializer('192b9bdd22ab9ed4d12e236c78afcb9a393ec15f71bbf5dc987d54727823bcbf')
        try:
            user_id = serial.loads(token)['user_id']
        except:
            return None
        return Admin.query.get(user_id)


class Category(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    category_name = db.Column('category_name', db.String(100), nullable=False)
    image_name = db.Column('image_name', db.String(225), nullable=False)
    image_path = db.Column('image_path', db.String(225), nullable=False)
    community_id = db.relationship('CreatedCommunity', backref='community_id')
    save_community_id = db.relationship('SavedCommunity', backref='saved_community')
    community_places_id = db.relationship('CreatedCommunity', backref='community_places_id')

    def as_dict(self, count=None):
        category_dict = {
                'id': self.id,
                'category_name': self.category_name,
                'image_name': self.image_path,
            }
        if count is not None:
            category_dict['count'] = count
        return category_dict

    def as_dict_merge(self, count=None):
        category_dict = {
                'id': self.id,
                'category_name': self.category_name,
                'image_name': self.image_path,
            'type': 'places'
            }
        if count is not None:
            category_dict['count'] = count
        return category_dict


class ThingsCategory(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    category_name = db.Column('category_name', db.String(100), nullable=False)
    image_name = db.Column('image_name', db.String(225), nullable=False)
    image_path = db.Column('image_path', db.String(225), nullable=False)
    # category_que = db.relationship('CategoryQue', backref='category_que')

    community_things_id = db.relationship('CreatedThingsCommunity', backref='community_things_id')
    saved_things_community_id = db.relationship('SavedThingsCommunity', backref='saved_things_community_id')



    # def as_dict(self, count=None):
    #     category_dict = {
    #             'id': self.id,
    #             'category_name': self.category_name,
    #             'image_name': self.image_path,
    #         }
    #     if count is not None:
    #         category_dict['words_count'] = count
    #     return category_dict

    def as_dict(self, count=None):
        category_dict = {
                'id': self.id,
                'category_name': self.category_name,
                'image_name': self.image_path,
            }
        if count is not None:
            category_dict['count'] = count
        return category_dict

    def as_dict_merge(self, count=None):
        category_dict = {
                'id': self.id,
                'category_name': self.category_name,
                'image_name': self.image_path,
            'type': 'things'
            }
        if count is not None:
            category_dict['count'] = count
        return category_dict


class QuestionsCategory(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    category_name = db.Column('category_name', db.String(100), nullable=False)
    image_name = db.Column('image_name', db.String(225), nullable=False)
    image_path = db.Column('image_path', db.String(225), nullable=False)
    category_que = db.relationship('CategoryQue', backref='category_que')

    def as_dict(self):
        return {
            'id': self.id,
            'category_name': self.category_name,
            'image_name': self.image_path
        }


class Cms(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    title = db.Column('title', db.String(100), nullable=False)

    content = db.Column('content', db.Text, nullable=False)
    youtube_link = db.Column('youtube_link', db.Text, nullable=False)

    def as_dict(self):
        return {'title': self.title,
                'content': self.content,
                }


class Faqs(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    question = db.Column('question', db.Text,
                         nullable=False)
    answer = db.Column('answer', db.Text,
                         nullable=False)

    def as_dict(self):
        return {'id': self.id,
                'question': self.question
                }

class CategoryQue(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    question = db.Column('question', db.Text,
                         nullable=False)
    questions_category_id = db.Column('questions_category_id', db.Integer, db.ForeignKey('questions_category.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    ans = db.relationship('CategoryAns', backref='category_ans')

    def as_dict(self):
        return {'id': self.id,
                'question': self.question,
                }

class CategoryAns(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)

    answer = db.Column('answer', db.Text,
                       nullable=False)
    question_id = db.Column('question_id', db.Integer, db.ForeignKey('category_que.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

    # def as_dict(self):
    #     return {'id': self.id,
    #             'question': self.question,
    #             'answer': self.answer,
    #             }

class LikeUserAnswer(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    answer_id = db.Column('answer_id', db.Integer, db.ForeignKey('category_ans.id', ondelete='CASCADE', onupdate='CASCADE'))
    main_user_id = db.Column('main_user_id', db.Integer,
                             db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                             nullable=False)

class CommentsUserAnswer(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    answer_id = db.Column('answer_id', db.Integer, db.ForeignKey('category_ans.id', ondelete='CASCADE', onupdate='CASCADE'))
    main_user_id = db.Column('main_user_id', db.Integer,
                             db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                             nullable=False)
    comment = db.Column(db.Text())
    created_time = db.Column(db.DateTime)

class BlockedWords(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    blocked_word = db.Column('blocked_word', db.String(100), nullable=False)


class Badges(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    deleted = db.Column('deleted', db.Boolean(), default=False)
    badge_name = db.Column('badge_name', db.String(100), nullable=False)


class Buddys(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    deleted = db.Column('deleted', db.Boolean(), default=False)
    type = db.Column('type', db.String(100), nullable=False)


class Buttons(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    button_original_name = db.Column('button_original_name', db.String(100), nullable=False)
    button_name = db.Column('button_name', db.String(100), nullable=False)
    image_name = db.Column('image_name', db.String(225), nullable=False)
    image_path = db.Column('image_path', db.String(225), nullable=False)

    def as_dict(self):
        return {
            'id': self.id,
            'button_original_name': self.button_original_name,
            'button_name': self.button_name,
            'image_name': self.image_path
        }