import os, jwt
from functools import wraps
from flask import request, jsonify
from base.database.db import db
from flask_login import UserMixin
from werkzeug.security import check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from base.common.utiils import COMMON_URL
from datetime import datetime
from sqlalchemy.dialects.mysql import LONGTEXT

class User(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    fullname = db.Column('fullname', db.String(100), nullable=False)
    email = db.Column('email', db.String(100))
    phonenumber = db.Column('phonenumber', db.String(100))
    country_code = db.Column('country_code', db.String(100))
    password = db.Column('password', db.String(300))

    qr_code = db.Column(db.String(225))

    image_name = db.Column('photo_name', db.String(225), default="conprofile.png", nullable=False)
    image_path = db.Column('photo_path', db.String(225), nullable=False,
                           default="https://frienddate-app.s3.amazonaws.com/conprofile.png")
    height = db.Column('height', db.String(100), default='N/A')
    drink = db.Column('drink', db.String(100), default='No')
    smoke = db.Column('smoke', db.String(100), default='No')
    city = db.Column('city', db.String(100))
    state = db.Column('state', db.String(100))
    age = db.Column('age', db.Date)
    country = db.Column('country', db.String(100))
    hide_friends = db.Column('hide_friends', db.String(100), default='0')
    gender = db.Column('gender', db.String(100))
    sexuality = db.Column('sexuality', db.String(100), default='Straight')
    looking_for = db.Column('looking_for', db.String(100), default='Friends')
    relationship_status = db.Column('relationship_status', db.String(100), default='Single')
    profile_visible_for = db.Column('profile_visible_for', db.String(100), default='0')
    device_token = db.Column('device_token', db.String(500))
    device_type = db.Column('device_type', db.String(500))
    latitude = db.Column('latitude', db.String(100))
    longitude = db.Column('longitude', db.String(100))
    double_verification = db.Column('double_verification', db.Boolean(), default=False)
    created_time = db.Column('created_time', db.DateTime, nullable=False)
    deleted_time = db.Column('deleted_time', db.DateTime)
    heart_your_comment = db.Column('heart_your_comment', db.Boolean(), default=True)
    like_your_comment = db.Column('like_your_comment', db.Boolean(), default=True)
    messege_friends = db.Column('messege_friends', db.Boolean(), default=True)
    messege_frienddate = db.Column('messege_frienddate', db.Boolean(), default=True)
    messege_new_user = db.Column('messege_new_user', db.Boolean(), default=True)
    dislike_your_comment = db.Column('dislike_your_comment', db.Boolean(), default=True)
    tag_you = db.Column('tag_you', db.Boolean(), default=True)
    friend_request = db.Column('friend_request', db.Boolean(), default=True)
    unfriend = db.Column('unfriend', db.Boolean(), default=True)
    add_new_community = db.Column('add_new_community', db.Boolean(), default=True)
    profile_pic = db.Column('profile_pic', db.Boolean(), default=True)
    relationship_status_change = db.Column('relationship_status_change', db.Boolean(), default=True)
    is_subscription = db.Column('is_subscription', db.Boolean(), default=False)
    subscription_start_time = db.Column('subscription_start_time', db.String(225))
    subscription_end_time = db.Column('subscription_end_time', db.String(225))
    subscription_price = db.Column('subscription_price', db.String(225))
    product_id = db.Column('product_id', db.String(1000))
    description_box = db.Column('description_box', db.String(1000), default='N/A')
    transaction_id = db.Column('transaction_id', db.String(1000))
    purchase_date = db.Column('purchase_date', db.String(1000))
    about_me = db.Column('about_me', db.Text, default='N/A')
    college = db.Column('college', db.String(250))
    new_bio = db.Column('new_bio', db.String(1000))

    # this is latest bio feild
    user_bio = db.Column(db.String(1000))

    profile_link = db.Column(db.String(250))

    is_subscription_badge = db.Column('is_subscription_badge', db.Boolean(), default=False)
    subscription_start_time_badge = db.Column('subscription_start_time_badge', db.String(225))
    subscription_end_time_badge = db.Column('subscription_end_time_badge', db.String(225))
    # subscription_price_badge = db.Column('subscription_price_badge', db.String(225))
    product_id_badge = db.Column('product_id_badge', db.String(1000))
    badge_name = db.Column('badge_name', db.String(1000), default='N/A')
    transaction_id_badge = db.Column('transaction_id_badge', db.String(1000))
    purchase_date_badge = db.Column('purchase_date_badge', db.String(1000))

    is_block = db.Column('is_block', db.Boolean(), default=False)
    is_18plus = db.Column('is_18plus', db.Boolean())

    deleted = db.Column('deleted', db.Boolean(), default=False)
    otp_verify = db.Column('otp_verify', db.Boolean(), default=False)
    delete_reason = db.Column('delete_reason', db.String(1000))
    social_id = db.Column('social_id', db.String(250))
    social_type = db.Column('social_type', db.String(250))
    is_social_login = db.Column('is_social_login', db.Boolean(), default=False)

    is_featured = db.Column('is_featured', db.Boolean(), default=False)

    age_verify = db.Column(db.Boolean(), default=False)

    is_business = db.Column(db.Boolean(), default=False)
    is_completed_profile = db.Column('is_completed_profile', db.Boolean(), default=False)
    multiple_images = db.Column('multiple_images', db.String(1000))
    is_profile_private = db.Column(db.Boolean(), default=False)

    kids = db.Column(db.Boolean(), default=False)

    saved_city = db.Column(db.String(250))
    saved_state = db.Column(db.String(250))
    saved_gender = db.Column(db.String(250))
    start_age = db.Column(db.String(250))
    end_age = db.Column(db.String(250))
    saved_looking_for = db.Column(db.String(250))
    is_filter = db.Column(db.Boolean(), default=False)

    is_group_post_notification = db.Column(db.Boolean(), default=True)
    is_invite_notification = db.Column(db.Boolean(), default=True)
    is_request_notification = db.Column(db.Boolean(), default=True)

    box_1 = db.Column(db.Text)
    box_2 = db.Column(db.Text)
    box_3 = db.Column(db.Text)
    box_4 = db.Column(db.Text)
    box_5 = db.Column(db.Text)
    box_6 = db.Column(db.Text)
    box_7 = db.Column(db.Text)
    box_8 = db.Column(db.Text)
    box_9 = db.Column(db.Text)
    box_10 = db.Column(db.Text)

    user_badge = db.Column(db.String(250))
    notify_gender = db.Column(db.String(50), default='All')

    user_id = db.relationship('Block', backref='users_id')
    save_community_id = db.relationship('SavedCommunity', backref='save_community')
    save_things_community_id = db.relationship('SavedThingsCommunity', backref='save_things_community')

    community_post_id = db.relationship('CommunityPost', backref='community_post_id')
    like_id = db.relationship('PostLike', backref='like_id')
    category_id = db.relationship('SelectedCategory', backref='categorys_id')
    things_review_id = db.relationship('ThingsReview', backref='things_review_id')
    places_review_id = db.relationship('PlacesReview', backref='places_review_id')
    things_recommendation_id = db.relationship('ThingsRecommendation', backref='things_recommendation_id')
    places_recommendation_id = db.relationship('PlacesRecommendation', backref='places_recommendation_id')
    feed_id = db.relationship('Feed', backref='feed_id')
    followed_user = db.relationship('Follow', backref='followed_user',
                                foreign_keys='Follow.by_id')
    feed_comment_id = db.relationship('FeedComments', backref='feed_comment_id')
    feed_like_id = db.relationship('FeedLike', backref='feed_like_id')
    by_user_notification = db.relationship('NewNotification', backref='by_user_notification',
                                foreign_keys='NewNotification.by_id')
    by_review = db.relationship('ProfileReviewRequest', backref='by_review',
                                foreign_keys='ProfileReviewRequest.by_id')
    chat_data = db.relationship('GroupChat', backref='chat_data')
    review_comment_user = db.relationship('ProfileReviewComments', backref='review_comment_user',
                                foreign_keys='ProfileReviewComments.user_id')
    i_am_going_data = db.relationship('IamGoing', backref='i_am_going_data')
    event_comment_data = db.relationship('EventComments', backref='event_comment_data')
    event_data = db.relationship('Events', backref='event_data')
    meetup_data = db.relationship('Meetup', backref='meetup_data')
    new_user_post_comment_data = db.relationship('NewUserPostComments', backref='new_user_post_comment_data')
    user_photo_comment_data = db.relationship('UserPhotoComments', backref='user_photo_comment_data')

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def as_dict_box(self):
        return {

            "box_1": self.box_1 if self.box_1 is not None else '',
            "box_2": self.box_2 if self.box_2 is not None else '',
            "box_3": self.box_3 if self.box_3 is not None else '',
            "box_4": self.box_4 if self.box_4 is not None else '',
            "box_5": self.box_5 if self.box_5 is not None else '',
            "box_6": self.box_6 if self.box_6 is not None else '',
            "box_7": self.box_7 if self.box_7 is not None else '',
            "box_8": self.box_8 if self.box_8 is not None else '',
            "box_9": self.box_9 if self.box_9 is not None else '',
            "box_10": self.box_10 if self.box_10 is not None else ''
        }

    def as_dict(self):

        box_values = {

            "box_1": self.box_1 if self.box_1 is not None else '',
            "box_2": self.box_2 if self.box_2 is not None else '',
            "box_3": self.box_3 if self.box_3 is not None else '',
            "box_4": self.box_4 if self.box_4 is not None else '',
            "box_5": self.box_5 if self.box_5 is not None else '',
            "box_6": self.box_6 if self.box_6 is not None else '',
            "box_7": self.box_7 if self.box_7 is not None else '',
            "box_8": self.box_8 if self.box_8 is not None else '',
            "box_9": self.box_9 if self.box_9 is not None else '',
            "box_10": self.box_10 if self.box_10 is not None else ''

        }

        return {
            'id': str(self.id),
            'username': self.fullname,
            'email': self.email,
            'country_code': self.country_code,
            'phonenumber': self.phonenumber,
            'password': self.password,
            'user_image': self.image_path,
            'height': self.height if self.height is not None else '',
            'drink': self.drink if self.drink is not None else '',
            'city': self.city if self.city is not None else '',
            'smoke': self.smoke if self.smoke is not None else '',
            'state': self.state if self.state is not None else '',
            'age': self.age if self.age is not None else '',
            'country': self.country if self.country is not None else '',
            'hide_friends': self.hide_friends,
            'gender': self.gender if self.gender is not None else '',
            'sexuality': self.sexuality,
            'looking_for': self.looking_for,
            'relationship_status': self.relationship_status,
            'profile_visible_for': self.profile_visible_for,
            'created_time': self.created_time,
            'double_verification': self.double_verification,
            'is_18plus': self.is_18plus if self.is_18plus is not None else False,
            'otp_verify': self.otp_verify,
            'is_subscription': self.is_subscription,
            'about_me': self.about_me,
            'college': self.college,
             'is_social_login': self.is_social_login,
            'kids': self.kids,
            'box_values': box_values,
            'user_badge': self.user_badge if self.user_badge is not None else '',
            'user_bio': self.user_bio if self.user_bio is not None else '',
            'qr_code': self.qr_code if self.qr_code is not None else ''

        }

    def get_token(self, expiress_sec=1800):
        serial = Serializer(os.getenv('SECRET_KEY'), expiress_sec)
        return serial.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_token(token):
        serial = Serializer(os.getenv('SECRET_KEY'))
        try:
            user_id = serial.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)


def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None
        if 'authorization' in request.headers:
            token = request.headers['authorization']

        if not token:
            return jsonify({'status': 0, 'message': 'a valid token is missing'})
        try:
            data = jwt.decode(token, '192b9bdd22ab9ed4d12e236c78afcb9a393ec15f71bbf5dc987d54727823bcbf',
                              algorithms=["HS256"])
            active_user = User.query.filter_by(id=data['id']).first()

            if active_user.is_block == True:
                return jsonify({'status': 0, 'messege': 'You Are Block By Admin'})

        except:
            return jsonify({'status': 0, 'message': 'token is invalid'})

        return f(active_user, *args, **kwargs)

    return decorator

class UserVideos(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    video_path = db.Column(db.String(225), nullable=False)
    thumbnail = db.Column(db.String(225), nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

    def as_dict(self,active_user_id):
        check_like = LikeUserVideos.query.filter_by(user_id=active_user_id, video_id=self.id).first()
        is_like = False
        if check_like:
            is_like = True
        return {
            'id': str(self.id),
            'video': self.video_path,
            'is_like': is_like,
            'thumbnail': self.thumbnail
        }

class LikeUserVideos(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    video_id = db.Column('video_id', db.Integer, db.ForeignKey('user_videos.id', ondelete='CASCADE', onupdate='CASCADE'))
    main_user_id = db.Column('main_user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class UserPhotos(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    image_path = db.Column('image_path', db.String(225), nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

    def as_dict(self,active_user_id):
        check_like = LikeUserPhotos.query.filter_by(user_id=active_user_id, image_id=self.id).first()
        is_like = False
        if check_like:
            is_like = True
        return {
            'id': str(self.id),
            'image': self.image_path,
            'is_like': is_like
        }

class UserPhotoComments(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    comment = db.Column(db.Text())
    created_time = db.Column(db.DateTime)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    user_photo_id = db.Column(db.Integer, db.ForeignKey('user_photos.id', ondelete='CASCADE', onupdate='CASCADE'))

    def as_dict(self):
        input_date = datetime.strptime(str(self.created_time), "%Y-%m-%d %H:%M:%S")
        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return {
            'id': self.id,
            'comment': self.comment,
            'user_id': self.user_id,
            'username': self.user_photo_comment_data.fullname,
            'user_image': self.user_photo_comment_data.image_path,
            'created_time': output_date
        }

class LikeUserPhotos(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    image_id = db.Column('image_id', db.Integer, db.ForeignKey('user_photos.id', ondelete='CASCADE', onupdate='CASCADE'))
    main_user_id = db.Column('main_user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class LikeRecommendation(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    places_id = db.Column('places_id', db.Integer, db.ForeignKey('places_recommendation.id', ondelete='CASCADE', onupdate='CASCADE'))
    things_id = db.Column('things_id', db.Integer, db.ForeignKey('things_recommendation.id', ondelete='CASCADE', onupdate='CASCADE'))
    type = db.Column('type', db.String(50))

class RecommendationComments(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    places_id = db.Column('places_id', db.Integer, db.ForeignKey('places_recommendation.id', ondelete='CASCADE', onupdate='CASCADE'))
    things_id = db.Column('things_id', db.Integer, db.ForeignKey('things_recommendation.id', ondelete='CASCADE', onupdate='CASCADE'))
    type = db.Column( db.String(50))
    comment = db.Column(db.Text())
    created_time = db.Column(db.DateTime)

class FriendRequest(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    request_status = db.Column('request_status', db.Integer())
    by_id = db.Column('by_id', db.Integer, nullable=False)
    to_id = db.Column('to_id', db.Integer, nullable=False)
    created_time = db.Column('created_time', db.DateTime)

    def as_dict(self):
        return {'id': self.id,
                'request_status': self.request_status,
                'by_id': str(self.by_id),
                'to_id': str(self.to_id)
                }

class ProfileReviewRequest(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    request_status = db.Column('request_status', db.Integer())
    review = db.Column('review', db.Text())
    to_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'))
    by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'))
    created_time = db.Column('created_time', db.DateTime)

    def as_dict(self):
        return {'id': self.id,
                'request_status': self.request_status,
                'by_id': str(self.by_id),
                'to_id': str(self.to_id)
                }

class ProfileReviewLike(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    profile_review_id = db.Column('profile_review_id', db.Integer, db.ForeignKey('profile_review_request.id', ondelete='CASCADE', onupdate='CASCADE'))
    main_user_id = db.Column('main_user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class ProfileReviewComments(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    comment = db.Column(db.Text())
    created_time = db.Column(db.DateTime)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    profile_review_id = db.Column('profile_review_id', db.Integer, db.ForeignKey('profile_review_request.id', ondelete='CASCADE', onupdate='CASCADE'))
    main_user_id = db.Column('main_user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

    def as_dict(self):
        input_date = datetime.strptime(str(self.created_time), "%Y-%m-%d %H:%M:%S")
        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return {'id': self.id,
                'comment': self.comment,
                'user_id': str(self.user_id),
                'username': self.review_comment_user.fullname,
                'user_image': self.review_comment_user.image_path,
                'created_time': output_date
                }

class SelectedCategory(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    category_id = db.Column('category_id', db.String(500), nullable=False)

    def as_dict(self):
        return {'id': self.id,
                'user_id': str(self.user_id),
                'category_id': self.category_id
                }

class DateRequest(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    messege = db.Column('messege', db.String(300))
    request_status = db.Column('request_status', db.Boolean())
    by_id = db.Column('by_id', db.Integer, nullable=False)
    to_id = db.Column('to_id', db.Integer, nullable=False)

    def as_dict(self):
        return {'id': self.id,
                'request_status': self.request_status,
                'by_id': str(self.by_id),
                'to_id': str(self.to_id)
                }

class Block(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    is_block = db.Column('is_block', db.Boolean(), nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

    blocked_user = db.Column('blocked_user', db.Integer, nullable=False)

    def as_dict(self):
        return {'id': self.id,
                'is_block': self.is_block,
                'user_id': str(self.user_id),
                'blocked_user': self.blocked_user
                }

class Report(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    messege = db.Column('messege', db.String(500), nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

    reported_user = db.Column('reported_user', db.Integer, nullable=False)
    reported_time = db.Column('reported_time', db.DateTime, nullable=False)

    def as_dict(self):
        return {'id': self.id,
                'messege': self.messege,
                'user_id': str(self.user_id),
                'reported_user': self.reported_user,
                'reported_time': self.reported_time

                }

class TagFriends(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    users = db.Column('users', db.String(500), nullable=False)
    community_post_id = db.Column('community_post_id', db.String(100), nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

    def as_dict(self):
        return {'id': self.id,
                'user_id': str(self.user_id),
                'community_chat_id': self.community_post_id
                }

class ChatMute(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    is_chat_mute = db.Column('is_chat_mute', db.Boolean(), nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

    post_id = db.Column('post_id', db.Integer, nullable=False)

    def as_dict(self):
        return {'id': self.id,
                'is_chat_mute': self.is_chat_mute,
                'user_id': str(self.user_id),
                'post_id': self.post_id
                }

class Notification(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    title = db.Column('title', db.String(200))
    messege = db.Column('messege', db.String(500))
    page = db.Column('page', db.String(100))
    is_read = db.Column('is_read', db.Boolean(), nullable=False)
    created_time = db.Column('created_time', db.DateTime, nullable=False)
    post_id = db.Column('post_id', db.Integer)
    community_id = db.Column('community_id', db.Integer)

    by_id = db.Column('by_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                      nullable=False)
    to_id = db.Column('to_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                      nullable=False)

class NewNotification(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    title = db.Column('title', db.String(200))
    message = db.Column('message', db.String(500))
    page = db.Column('page', db.String(100))
    is_read = db.Column('is_read', db.Boolean(), nullable=False)
    created_time = db.Column('created_time', db.DateTime, nullable=False)
    feed_id = db.Column('feed_id', db.Integer)

    by_id = db.Column('by_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                      nullable=False)
    to_id = db.Column('to_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                      nullable=False)

class GroupNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    title = db.Column(db.String(200))
    message = db.Column(db.String(500))
    community_id = db.Column(db.Integer)
    community_type = db.Column(db.Integer)

    page = db.Column(db.String(100))
    is_read = db.Column(db.Boolean(), nullable=False)
    created_time = db.Column(db.DateTime, nullable=False)

    by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                      nullable=False)
    to_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                      nullable=False)

    def as_dict(self):
        user_data = User.query.get(self.by_id)

        input_date = datetime.strptime(str(self.created_time), "%Y-%m-%d %H:%M:%S")
        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return {
            'id': self.id,
            'user_id': str(user_data.id),
            'username': user_data.fullname,
            'user_image': user_data.image_path,
            'created_time': output_date,
            'title': self.title if self.title is not None else '',
            'message': self.message if self.message is not None else '',

            "address": "",
            "any_date": "",
            "any_time": "",
            "city": "",
            "description": "",
            "end_time": "14:00",
            "meetup_date": "",
            "place": "",
            "start_time": "",
            "state": "",
        }




class TblCountries(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    name = db.Column(db.String(100))

    # iso3 = db.Column(db.String(3, collation='utf8mb4_unicode_ci'), nullable=True)
    #    numeric_code = db.Column(db.String(3, collation='utf8mb4_unicode_ci'), nullable=True)
    #   iso2 = db.Column(db.String(2, collation='utf8mb4_unicode_ci'), nullable=True)
    # phonecode = db.Column(db.String(255, collation='utf8mb4_unicode_ci'), nullable=True)
    # capital = db.Column(db.String(255, collation='utf8mb4_unicode_ci'), nullable=True)
    # currency = db.Column(db.String(255, collation='utf8mb4_unicode_ci'), nullable=True)
    # currency_name = db.Column(db.String(255, collation='utf8mb4_unicode_ci'), nullable=True)
    # currency_symbol = db.Column(db.String(255, collation='utf8mb4_unicode_ci'), nullable=True)
    # tld = db.Column(db.String(255, collation='utf8mb4_unicode_ci'), nullable=True)
    # native = db.Column(db.String(255, collation='utf8mb4_unicode_ci'), nullable=True)
    # region = db.Column(db.String(255, collation='utf8mb4_unicode_ci'), nullable=True)
    # subregion = db.Column(db.String(255, collation='utf8mb4_unicode_ci'), nullable=True)
    # timezones = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    # translations = db.Column(db.Text(collation='utf8mb4_unicode_ci'), nullable=True)
    # latitude = db.Column(db.Numeric(10, 8), nullable=True)
    # longitude = db.Column(db.Numeric(11, 8), nullable=True)
    # emoji = db.Column(db.String(191, collation='utf8mb4_unicode_ci'), nullable=True)
    # emojiU = db.Column(db.String(191, collation='utf8mb4_unicode_ci'), nullable=True)
    # created_at = db.Column(db.TIMESTAMP, nullable=True)
    # updated_at = db.Column(db.TIMESTAMP, nullable=False,
    #                      server_default=db.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    # flag = db.Column(db.Boolean, nullable=False, default=True)
    # wikiDataId = db.Column(db.String(255, collation='utf8mb4_unicode_ci'), nullable=True,
    #                      comment='Rapid API GeoDB Cities')

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
        }

class TblStates(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    name = db.Column(db.String(255))
    country_id = db.Column(db.Integer, db.ForeignKey('tbl_countries.id', ondelete='CASCADE', onupdate='CASCADE'),
                           nullable=False)

    # country_code = db.Column(db.String(2, collation='utf8mb4_unicode_ci'))
    # fips_code = db.Column(db.String(255, collation='utf8mb4_unicode_ci'), nullable=True)
    # iso2 = db.Column(db.String(255, collation='utf8mb4_unicode_ci'), nullable=True)
    # type = db.Column(db.String(191, collation='utf8mb4_unicode_ci'), nullable=True)
    # latitude = db.Column(db.Numeric(10, 8), nullable=True)
    # longitude = db.Column(db.Numeric(11, 8), nullable=True)
    # created_at = db.Column(db.TIMESTAMP, nullable=True)
    # updated_at = db.Column(db.TIMESTAMP, nullable=False,
    #                      server_default=db.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    # flag = db.Column(db.Boolean, nullable=False, default=True)
    # wikiDataId = db.Column(db.String(255, collation='utf8mb4_unicode_ci'), nullable=True,
    #                      comment='Rapid API GeoDB Cities')

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
        }

class Follow(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    by_id = db.Column('by_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    to_id = db.Column('to_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

    def as_dict(self):
        return {
            'id': self.id,
            'user_id': self.followed_user.id,
            'username': self.followed_user.fullname ,
            'user_image': self.followed_user.image_path,

        }

class HideFeed(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    feed_id = db.Column('feed_id', db.Integer, db.ForeignKey('feed.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class Feed(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    text = db.Column('text', db.Text)
    created_time = db.Column('created_time', db.DateTime, nullable=False)

    community_type = db.Column(db.String(20))
    community_id = db.Column(db.String(20))
    community_name = db.Column(db.String(200))

    image_name = db.Column('image_name', db.String(225))
    image_path = db.Column('image_path', db.String(225))
    video_path = db.Column('video_path', db.String(225))
    thumbnail_path = db.Column('thumbnail_path', db.String(225))
    type = db.Column('type', db.String(225))
    link = db.Column('link', db.String(1000))
    website_link = db.Column(db.String(1000))
    # content_type = db.Column('content_type', db.String(225))
    is_review = db.Column('is_review', db.Boolean(), default=False)
    is_repost = db.Column('is_repost', db.Boolean(), default=False)
    repost_feed_id = ('repost_feed_id', db.Integer)
    review_id = db.Column('review_id', db.Integer)
    review_table = db.Column('review_table', db.String(225))

    feed_type = db.Column(db.String(225))
    address = db.Column(db.String(525))
    description = db.Column(LONGTEXT)
    event_date = db.Column(db.Date)
    event_time = db.Column(db.String(50))

    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                      nullable=False)

    def as_dict(self,user_id):
        is_my_feed = False
        if user_id == self.user_id:
            is_my_feed = True

        input_date = datetime.strptime(str(self.created_time), "%Y-%m-%d %H:%M:%S")
        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return {
            'id': self.id,
            'text': self.text if self.text is not None else '',
            'image': self.image_path if self.image_path is not None else '',
            'type': self.type,
            'link': self.link if self.link is not None else '',
            'user_id': self.user_id,
            'username': self.feed_id.fullname,
            'user_image': self.feed_id.image_path,
            'is_my_feed': is_my_feed,
            'video': self.video_path if self.video_path is not None else '',
            'thumbnail': self.thumbnail_path if self.thumbnail_path is not None else '',
            'created_time': output_date,
            'is_repost': self.is_repost,
            'website_link': self.website_link if self.website_link is not None else '',
            'community_type': self.community_type if self.community_type is not None else '',
            'community_id': self.community_id if self.community_id is not None else '',
            'community_name': self.community_name if self.community_name is not None else ''

        }

class FeedLike(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    feed_id = db.Column('feed_id', db.Integer, db.ForeignKey('feed.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class FeedComments(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    text = db.Column('text', db.String(1000), nullable=False)
    created_time = db.Column('created_time', db.DateTime, nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    feed_id = db.Column('feed_id', db.Integer, db.ForeignKey('feed.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

    def as_dict(self, active_user_id):
        is_my_comment = False
        if active_user_id == self.user_id:
            is_my_comment = True

        input_date = datetime.strptime(str(self.created_time), "%Y-%m-%d %H:%M:%S")
        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        return {

            'id': self.id,
            'text': self.text,
            'username': self.feed_comment_id.fullname,
            'user_image': self.feed_comment_id.image_path,
            'created_time': output_date,
            'user_id': self.user_id,
            'is_my_comment': is_my_comment
        }

class FeedCommentLike(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    feed_comment_id = db.Column('feed_comment_id', db.Integer, db.ForeignKey('feed_comments.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class PlacesReviewLike(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    review_id = db.Column('review_id', db.Integer, db.ForeignKey('places_review.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class PlacesReviewComments(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    text = db.Column('text', db.String(1000), nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    review_id = db.Column('review_id', db.Integer, db.ForeignKey('places_review.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class PlacesReviewCommentLike(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    places_comment_id = db.Column('places_comment_id', db.Integer, db.ForeignKey('places_review_comments.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class ThingsReviewLike(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    review_id = db.Column('review_id', db.Integer, db.ForeignKey('things_review.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class ThingsReviewComments(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    text = db.Column('text', db.String(1000), nullable=False)

    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    review_id = db.Column('review_id', db.Integer, db.ForeignKey('things_review.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class ThingsReviewCommentLike(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    things_comment_id = db.Column('things_comment_id', db.Integer, db.ForeignKey('things_review_comments.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class GroupChat(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    text = db.Column(db.Text)
    created_time = db.Column(db.DateTime, nullable=False)
    image_name = db.Column(db.String(225))
    image_path = db.Column(db.String(225))
    type = db.Column(db.String(225))
    places_created_id = db.Column(db.Integer,
                           db.ForeignKey('created_community.id', ondelete='CASCADE', onupdate='CASCADE'))
    things_created_id = db.Column(db.Integer,
                             db.ForeignKey('created_things_community.id', ondelete='CASCADE', onupdate='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class FavoriteUser(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    to_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                      nullable=False)
    created_time = db.Column(db.DateTime, nullable=False)

class FavoriteSubCategory(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    places_id = db.Column(db.Integer, db.ForeignKey('created_community.id', ondelete='CASCADE', onupdate='CASCADE'))
    things_id = db.Column(db.Integer, db.ForeignKey('created_things_community.id', ondelete='CASCADE', onupdate='CASCADE'))
    type = db.Column(db.String(50))

class NewGroup(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    group_name = db.Column(db.String(200))
    created_time = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)

class JoinedNewGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('new_group.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class NewUserPosts(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    title = db.Column(db.String(200))

    # --- new feilds---

    gender = db.Column(db.String(50))
    age_start = db.Column(db.String(50))
    age_end = db.Column(db.String(50))
    looking_for = db.Column(db.String(50))
    sexual_orientation = db.Column(db.String(50))

    # ------------------

    image_name = db.Column(db.String(225))
    image_path = db.Column(db.String(225))
    thumbnail_path = db.Column(db.String(225))
    content_type = db.Column(db.String(225), nullable=False)
    city = db.Column(db.String(200))
    state = db.Column(db.String(200))
    created_time = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

    def as_dict(self,active_user_id):
        check_like = LikeNewUserPosts.query.filter_by(user_id=active_user_id, image_id=self.id).first()
        like_counts = LikeNewUserPosts.query.filter_by(image_id=self.id).count()
        user_data = User.query.get(self.user_id)

        input_date = datetime.strptime(str(self.created_time), "%Y-%m-%d %H:%M:%S")
        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        is_like = False
        if check_like:
            is_like = True

        is_my_post = False
        if active_user_id == self.user_id:
            is_my_post = True

        is_follow = Follow.query.filter_by(by_id = active_user_id,to_id = self.user_id).first()

        return {
            'id': str(self.id),
            'title': self.title if self.title is not None else '',
            'image': self.image_path if self.content_type == 'image' else '',
            'video': self.image_path if self.content_type == 'video' else '',
            'is_like': is_like,
            'like_counts': str(like_counts),
            'user_id': user_data.id,
            'username': user_data.fullname,
            'user_image': user_data.image_path,
            'new_bio': user_data.new_bio if user_data.new_bio is not None else '',
            'created_time': output_date,
            'content_type': self.content_type,
            'is_my_post': is_my_post,
            'is_follow': bool(is_follow),
            'city': self.city if self.city is not None else '',
            'state': self.state if self.state is not None else '',
            'thumbnail': self.thumbnail_path if self.thumbnail_path is not None else '',

            #new feilds

            'gender': self.gender if self.gender is not None else '',
            'age_start': self.age_start if self.age_start is not None else '',
            'age_end': self.age_end if self.age_end is not None else '',
            'looking_for': self.looking_for if self.looking_for is not None else '',
            'sexual_orientation': self.sexual_orientation if self.sexual_orientation is not None else ''
        }

class NewUserPostComments(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    comment = db.Column(db.Text())
    created_time = db.Column(db.DateTime)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    new_user_post_id = db.Column(db.Integer, db.ForeignKey('new_user_posts.id', ondelete='CASCADE', onupdate='CASCADE'))

    def as_dict(self):
        input_date = datetime.strptime(str(self.created_time), "%Y-%m-%d %H:%M:%S")
        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return {
            'id': self.id,
            'comment': self.comment,
            'user_id': self.user_id,
            'username': self.event_comment_data.fullname,
            'user_image': self.event_comment_data.image_path,
            'created_time': output_date
        }

class LikeNewUserPosts(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    image_id = db.Column(db.Integer, db.ForeignKey('new_user_posts.id', ondelete='CASCADE', onupdate='CASCADE'))
    main_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class HideNewUserPosts(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    image_id = db.Column(db.Integer, db.ForeignKey('new_user_posts.id', ondelete='CASCADE', onupdate='CASCADE'))

class ReportNewUserPosts(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    image_id = db.Column(db.Integer, db.ForeignKey('new_user_posts.id', ondelete='CASCADE', onupdate='CASCADE'))
    created_time = db.Column(db.DateTime, nullable=False)

class HideUser(db.Model):
    id = db.Column(db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    to_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                      nullable=False)
    created_time = db.Column(db.DateTime, nullable=False)

class Events(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    name = db.Column(db.String(200))
    city = db.Column(db.String(200))
    state = db.Column(db.String(200))
    address = db.Column(db.String(500))
    description = db.Column(db.Text)
    start_time = db.Column(db.String(200))
    end_time = db.Column(db.String(200))
    event_date = db.Column(db.String(200))
    image_name = db.Column(db.String(225))
    image_path = db.Column(db.String(225))
    is_deleted = db.Column(db.Boolean(), default=False)
    created_time = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

    def as_dict(self,active_user_id):
        input_date = datetime.strptime(str(self.created_time), "%Y-%m-%d %H:%M:%S")
        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        is_my_event = False

        if self.user_id == active_user_id:
            is_my_event = True

        check_going = IamGoing.query.filter_by(event_id = self.id).count()
        check_going_confirm = IamGoing.query.filter_by(event_id=self.id,user_id = active_user_id).first()

        return {

            'id': self.id,
            'name': self.name if self.name is not None else '',
            'description': self.description if self.description is not None else '',
            'start_time': self.start_time if self.start_time is not None else '',
            'end_time': self.end_time if self.end_time is not None else '',
            'event_date': self.event_date,
            'image': self.image_path if self.image_path is not None else '',
            'is_my_event': is_my_event,
            'created_time': output_date,
            'counts': str(check_going),
            'i_am_going': bool(check_going_confirm),
            'user_id': str(self.event_data.id),
            'username': self.event_data.fullname,
            'user_image': self.event_data.image_path if self.event_data.image_path is not None else '',
            'address': self.address if self.address is not None else ''
        }

class IamGoing(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='CASCADE', onupdate='CASCADE'))
    created_time = db.Column(db.DateTime, nullable=False)

    def as_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.i_am_going_data.fullname,
            'user_image': self.i_am_going_data.image_path
        }

class EventComments(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    comment = db.Column(db.Text())
    created_time = db.Column(db.DateTime)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='CASCADE', onupdate='CASCADE'))

    def as_dict(self):
        input_date = datetime.strptime(str(self.created_time), "%Y-%m-%d %H:%M:%S")
        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return {
            'id': self.id,
            'comment': self.comment,
            'user_id': self.user_id,
            'username': self.event_comment_data.fullname,
            'user_image': self.event_comment_data.image_path,
            'created_time': output_date
        }

class Meetup(db.Model):
    id = db.Column(db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    place = db.Column(db.String(200))
    city = db.Column(db.String(200))
    state = db.Column(db.String(200))
    address = db.Column(db.String(500))
    description = db.Column(db.Text)
    start_time = db.Column(db.String(200))
    end_time = db.Column(db.String(200))
    meetup_date = db.Column(db.String(200))

    any_time = db.Column(db.String(200))
    any_date = db.Column(db.String(200))

    gender = db.Column(db.String(200),default='All')
    sexuality = db.Column(db.String(200))
    start_age = db.Column(db.String(200))
    end_age = db.Column(db.String(200))

    is_show = db.Column(db.Boolean(), default=True)
    created_time = db.Column(db.DateTime, nullable=False)

    image_name = db.Column(db.String(225))
    image_path = db.Column(db.String(225))
    video_path = db.Column(db.String(225))
    thumbnail_path = db.Column(db.String(225))
    type = db.Column(db.String(225))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    meetup_request_data = db.relationship('MeetupRequest', backref='meetup_request_data')

    def as_dict(self,active_user_id):
        input_date = datetime.strptime(str(self.created_time), "%Y-%m-%d %H:%M:%S")
        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        is_my_meetup = False

        if self.user_id == active_user_id:
            is_my_meetup = True

        check_reported = ReportMeetup.query.filter_by(user_id = active_user_id,meetup_id=self.id).first()

        # meetup_count = MeetupRequest.query.filter_by(meetup_id = self.id).count()
        is_meetup_request = MeetupRequest.query.filter_by(meetup_id=self.id,by_id = active_user_id).first()

        return {

            'id': self.id,
            'place': self.place if self.place is not None else '',
            'description': self.description if self.description is not None else '',
            'start_time': self.start_time if self.start_time is not None else '',
            'end_time': self.end_time if self.end_time is not None else '',
            'meetup_date': self.meetup_date,
            'is_my_meetup': is_my_meetup,
            'created_time': output_date,
            # 'counts': str(meetup_count),
            'is_meetup_request': bool(is_meetup_request),
            'user_id': str(self.meetup_data.id),
            'username': self.meetup_data.fullname,
            'user_image': self.meetup_data.image_path if self.meetup_data.image_path is not None else '',
            'address': self.address if self.address is not None else '',
            'city': self.city if self.city is not None else '',
            'state': self.state if self.state is not None else '',

            'gender': self.gender if self.gender is not None else '',
            'sexuality': self.sexuality if self.sexuality is not None else '',
            'start_age': self.start_age if self.start_age is not None else '',
            'end_age': self.end_age if self.end_age is not None else '',
            'any_time': self.any_time if self.any_time is not None else '',
            'any_date': self.any_date if self.any_date is not None else '',
            'type': self.type if self.type is not None else "text",
            'image': self.image_path if self.image_name is not None else "",
            'video': self.video_path if self.video_path is not None else "",
            'thumbnail': self.thumbnail_path if self.thumbnail_path is not None else "",
            "is_reported": bool(check_reported)
        }

    def as_dict_notification(self):

        return {

            'id': str(self.id),
            'place': self.place if self.place is not None else '',
            'description': self.description if self.description is not None else '',
            'start_time': self.start_time if self.start_time is not None else '',
            'end_time': self.end_time if self.end_time is not None else '',
            'meetup_date': self.meetup_date,
            'address': self.address if self.address is not None else ''
        }

class HideMeetup(db.Model):
    id = db.Column(db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    created_time = db.Column(db.DateTime, nullable=False)
    meetup_id = db.Column(db.Integer, db.ForeignKey('meetup.id', ondelete='CASCADE', onupdate='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class ReportMeetup(db.Model):
    id = db.Column(db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    created_time = db.Column(db.DateTime, nullable=False)
    meetup_id = db.Column(db.Integer, db.ForeignKey('meetup.id', ondelete='CASCADE', onupdate='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class MeetupRequest(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    title = db.Column(db.String(200))
    message = db.Column(db.String(200))
    is_read = db.Column(db.Boolean(), nullable=False)
    is_show = db.Column(db.Boolean(), default=True)
    by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    to_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                      nullable=False)
    meetup_id = db.Column(db.Integer, db.ForeignKey('meetup.id', ondelete='CASCADE', onupdate='CASCADE'))
    created_time = db.Column(db.DateTime, nullable=False)

    def as_dict(self):
        user_data = User.query.get(self.by_id)
        input_date = datetime.strptime(str(self.created_time), "%Y-%m-%d %H:%M:%S")
        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return {
            'title': self.title,
            'message': self.message,
            'created_time': output_date,
            'user_id': user_data.id,
            'username': user_data.fullname,
            'user_image': user_data.image_path if user_data.image_path is not None else '',
            'city': self.meetup_request_data.city if self.meetup_request_data.city is not None else '',
            'state': self.meetup_request_data.state if self.meetup_request_data.state is not None else ''
        }

# class MeetupNotification(db.Model):
#     id = db.Column(db.Integer, primary_key=True,
#                    autoincrement=True, nullable=False)
#     title = db.Column(db.String(200))
#     message = db.Column(db.String(200))
#     is_read = db.Column(db.Boolean(), nullable=False)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
#                         nullable=False)
#     meetup_id = db.Column(db.Integer, db.ForeignKey('meetup.id', ondelete='CASCADE', onupdate='CASCADE'))
#     created_time = db.Column(db.DateTime, nullable=False)

class GroupChatNotificationOnOff(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    type = db.Column(db.String(225))
    places_created_id = db.Column(db.Integer,
                           db.ForeignKey('created_community.id', ondelete='CASCADE', onupdate='CASCADE'))
    things_created_id = db.Column(db.Integer,
                             db.ForeignKey('created_things_community.id', ondelete='CASCADE', onupdate='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class GroupPosts(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    description = db.Column(db.Text)
    place = db.Column(db.String(250))
    address = db.Column(db.String(250))
    time = db.Column(db.String(50))
    date = db.Column(db.String(50))
    gender = db.Column(db.String(50),default="All")
    age_start = db.Column(db.String(50))
    age_end = db.Column(db.String(50))
    looking_for = db.Column(db.String(50))

    relationship_for = db.Column(db.String(50))

    sexual_orientation = db.Column(db.String(50))

    created_time = db.Column(db.DateTime, nullable=False)

    type = db.Column(db.String(225))
    places_created_id = db.Column(db.Integer,
                                  db.ForeignKey('created_community.id', ondelete='CASCADE', onupdate='CASCADE'))
    things_created_id = db.Column(db.Integer,
                                  db.ForeignKey('created_things_community.id', ondelete='CASCADE', onupdate='CASCADE'))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

    def as_dict(self,active_user_id):
        user_data = User.query.get(self.user_id)

        input_date = datetime.strptime(str(self.created_time), "%Y-%m-%d %H:%M:%S")
        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        is_my_post = False
        if active_user_id == self.user_id:
            is_my_post = True

        return {
            'id': str(self.id),
            'user_id': user_data.id,
            'username': user_data.fullname,
            'user_image': user_data.image_path,
            'created_time': output_date,
            'is_my_post': is_my_post,

            'place': self.place if self.place is not None else '',
            'address': self.address if self.address is not None else '',

            'description': self.description if self.description is not None else '',
            'time': self.time if self.time is not None else '',
            'date': self.date if self.date is not None else '',

            'gender': self.gender if self.gender is not None else '',
            'age_start': self.age_start if self.age_start is not None else '',
            'age_end': self.age_end if self.age_end is not None else '',
            'looking_for': self.looking_for if self.looking_for is not None else '',
            'sexual_orientation': self.sexual_orientation if self.sexual_orientation is not None else ''
        }

class VisitGroupComments(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    type = db.Column(db.String(225))
    visit_time = db.Column(db.DateTime, nullable=False)
    places_created_id = db.Column(db.Integer,
                           db.ForeignKey('created_community.id', ondelete='CASCADE', onupdate='CASCADE'))
    things_created_id = db.Column(db.Integer,
                             db.ForeignKey('created_things_community.id', ondelete='CASCADE', onupdate='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

class GroupComments(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    comment = db.Column(db.Text)
    type = db.Column(db.String(225))
    created_time = db.Column(db.DateTime, nullable=False)
    places_created_id = db.Column(db.Integer,
                           db.ForeignKey('created_community.id', ondelete='CASCADE', onupdate='CASCADE'))
    things_created_id = db.Column(db.Integer,
                             db.ForeignKey('created_things_community.id', ondelete='CASCADE', onupdate='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

    def as_dict(self,active_user_id):
        user_data = User.query.get(self.user_id)

        input_date = datetime.strptime(str(self.created_time), "%Y-%m-%d %H:%M:%S")
        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        is_my_comment = False
        if active_user_id == self.user_id:
            is_my_comment = True

        return {
            'id': str(self.id),
            'comment':self.comment,
            'user_id': user_data.id,
            'username': user_data.fullname,
            'user_image': user_data.image_path,
            'created_time': output_date,
            'is_my_comment': is_my_comment,
            'type': self.type
        }