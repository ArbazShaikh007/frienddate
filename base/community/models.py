from base.database.db import db
from datetime import datetime
import pytz
from base.user.models import ThingsReviewLike,PlacesReviewLike


# def convert_tz():
#     return datetime.now(tz=pytz.timezone('Asia/Kolkata'))

# now = datetime.now(tz=pytz.timezone('Asia/Kolkata'))
# convert = datetime.now().astimezone().tzinfo

class CreatedCommunity(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    community_name = db.Column('community_name', db.String(100), nullable=False)
    community_post_id = db.relationship('CommunityPost', backref='post_id', cascade="all, delete-orphan")
    category_id = db.Column('category_id', db.Integer, db.ForeignKey('category.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
    created_time = db.Column('created_time',db.DateTime, nullable = False)
    avarage_rating = db.Column('avarage_rating', db.Float(),default=0)
    visited = db.Column('visited', db.Integer())
    state = db.Column('state', db.String(100))
    city = db.Column('city', db.String(100))
    link = db.Column('link', db.String(250))
    saved = db.relationship('SavedCommunity', backref='saved')
    places_recommendation = db.relationship('PlacesRecommendation', backref='places_recommendation')
    places_review = db.relationship('PlacesReview', backref='places_review')


    def as_dict(self):
        if not self.visited:
            self.visited=0
        return {
                'id' : self.id,
                'community_name' : self.community_name,
                'category_id': self.category_id,
            'user_id': str(self.user_id),
            'created_time': self.created_time,
            'visited': self.visited,

        }

class HideCommunity(db.Model):
    id = db.Column(db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    created_id = db.Column(db.Integer, db.ForeignKey('created_community.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)

class SavedCommunity(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    community_name = db.Column('community_name', db.String(100), nullable=False)
    created_time = db.Column('created_time',db.DateTime,nullable = False)
    visited = db.Column('visited', db.Integer())
    is_saved = db.Column('is_saved', db.Boolean(), default = False)
    state = db.Column('state', db.String(100))
    city = db.Column('city', db.String(100))
    created_id = db.Column('created_id', db.Integer, db.ForeignKey('created_community.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
    category_id = db.Column('category_id', db.Integer, db.ForeignKey('category.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)

    def as_dict(self):
        if not self.visited:
            self.visited=0
        return {
                'id' : self.id,
                'community_name' : self.community_name,
                'category_id': self.category_id,
            'user_id': str(self.user_id),
            'created_time' : self.created_time,
            'created_id': self.created_id,
            'visited': self.visited,

        }

class CreatedThingsCommunity(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                       autoincrement=True, nullable=False)
    community_name = db.Column('community_name', db.String(100), nullable=False)
    # community_post_id = db.relationship('CommunityPost', backref='post_id', cascade="all, delete-orphan")
    category_id = db.Column('category_id', db.Integer,
                                db.ForeignKey('things_category.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                            nullable=False)
    created_time = db.Column('created_time', db.DateTime, nullable=False)
    visited = db.Column('visited', db.Integer())
    state = db.Column('state', db.String(100))
    avarage_rating = db.Column('avarage_rating', db.Float(), default=0)
    city = db.Column('city', db.String(100))
    link = db.Column('link', db.String(250))
    saved = db.relationship('SavedThingsCommunity', backref='saved')
    things_recommendation = db.relationship('ThingsRecommendation', backref='things_recommendation')
    things_review = db.relationship('ThingsReview', backref='things_review')
    group_things_data = db.relationship('GroupChat', backref='group_things_data')

    def as_dict(self):
        if not self.visited:
           self.visited = 0

        return {
                'id': self.id,
                'community_name': self.community_name,
                'category_id': self.category_id,
                'user_id': str(self.user_id),
                'created_time': self.created_time,
                'visited': self.visited,
            'link': self.link if self.link is not None else 'N/A',
            'city': self.city if self.city is not None else 'N/A',
            'state': self.state if self.state is not None else 'N/A'

            }

class HideThingsCommunity(db.Model):
    id = db.Column(db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    created_id = db.Column(db.Integer,
                               db.ForeignKey('created_things_community.id', ondelete='CASCADE', onupdate='CASCADE'),
                               nullable=False)
    category_id = db.Column(db.Integer,
                                db.ForeignKey('things_category.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                            nullable=False)


class SavedThingsCommunity(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    community_name = db.Column('community_name', db.String(100), nullable=False)
    created_time = db.Column('created_time', db.DateTime, nullable=False)
    visited = db.Column('visited', db.Integer())
    is_saved = db.Column('is_saved', db.Boolean(), default=False)
    state = db.Column('state', db.String(100))
    city = db.Column('city', db.String(100))
    created_id = db.Column('created_id', db.Integer,
                               db.ForeignKey('created_things_community.id', ondelete='CASCADE', onupdate='CASCADE'),
                               nullable=False)
    category_id = db.Column('category_id', db.Integer,
                                db.ForeignKey('things_category.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                            nullable=False)

    def as_dict(self):
        if not self.visited:
            self.visited = 0
        return {
                'id': self.id,
                'community_name': self.community_name,
                'category_id': self.category_id,
                'user_id': str(self.user_id),
                'created_time': self.created_time,
                'created_id': self.created_id,
                'visited': self.visited,

            }

# class CommunityLike(db.Model):
#     id = db.Column('id', db.Integer, primary_key=True,
#                    autoincrement=True, nullable=False)
#     like_status = db.Column('like_status', db.Boolean())
#     community_id = db.Column('community_id', db.Integer, db.ForeignKey('created_community.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
#     user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
#
#
#     def as_dict(self):
#         return {
#                 'id' : self.id,
#                 'like_status' : self.like_status,
#                 'community_id': self.community_id,
#             'user_id': str(self.user_id),
#
#         }
#
# class CommunityComment(db.Model):
#     id = db.Column('id', db.Integer, primary_key=True,
#                    autoincrement=True, nullable=False)
#     comment = db.Column('comment', db.String(500), nullable=False)
#     community_id = db.Column('community_id', db.Integer, db.ForeignKey('created_community.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
#     user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
#
#
#     def as_dict(self):
#         return {
#                 'id' : self.id,
#                 'comment' : self.comment,
#                 'community_id': self.community_id,
#             'user_id': str(self.user_id),
#
#         }


class CommunityPost(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    text = db.Column('text', db.String(500), nullable=False)
    created_time = db.Column('created_time',db.DateTime,nullable=False)
    like_id = db.relationship('PostLike', backref='likes_id', cascade="all, delete-orphan")
    thusup_id = db.relationship('PostThumsup', backref='thusup_id', cascade="all, delete-orphan")
    thusdown_id = db.relationship('PostThumpdown', backref='thusdown_id', cascade="all, delete-orphan")
    comment_id = db.relationship('PostComment', backref='comment_id', cascade="all, delete-orphan")

    community_id = db.Column('community_id', db.Integer, db.ForeignKey('created_community.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)


    def as_dict(self):
        return {
                'id' : self.id,
                'text' : self.text,
                'community_id': self.community_id,
            'user_id': str(self.user_id),

        }


class ThingsReview(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    title = db.Column('title', db.String(350))
    text = db.Column('text', db.Text)
    created_time = db.Column('created_time',db.DateTime,nullable=False)
    image_name = db.Column('image_name', db.String(225))
    image_path = db.Column('image_path', db.String(225))
    rate = db.Column('rate', db.Float())

    community_id = db.Column('community_id', db.Integer, db.ForeignKey('created_things_community.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)

    def as_dict(self,active_user_id):

        is_my_review = False
        if self.user_id == active_user_id:
            is_my_review = True

        return {
                'id' : self.id,
            'title': self.things_review.community_name if self.things_review.community_name is not None else '',
                'text' : self.text if self.text is not None else '',
            'image': self.image_path if self.image_path is not None else '',
            'user_id': str(self.user_id),
            'user_image': self.things_review_id.image_path,
            'username': self.things_review_id.fullname,
            'is_my_review': is_my_review,
            'rate': str(self.rate) if self.rate is not None else '0'

        }

    def as_dict2(self, active_user_id):
        type = 'text'
        if self.image_path is not None:
            type = 'image'

        is_my_feed = False
        if self.user_id == active_user_id:
            is_my_feed = True

        is_like = False
        check_like = ThingsReviewLike.query.filter_by(user_id=active_user_id, review_id=self.id).first()
        if check_like:
            is_like = True

        input_date = datetime.strptime(str(self.created_time), "%Y-%m-%d %H:%M:%S")
        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        return {
            'id': self.id,
            'title': self.title if self.title is not None else '',
            'text': self.text if self.text is not None else '',
            'image': self.image_path if self.image_path is not None else '',
            'type': type,
            'user_id': str(self.user_id),
            'username': self.things_review_id.fullname,
            'user_image': self.things_review_id.image_path,
            'is_my_feed': is_my_feed,
            'video': '',
            'thumbnail': '',
            'created_time': output_date,
            'is_like': is_like,
            'review_type': 'things'

        }


class PlacesReview(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    title = db.Column('title', db.String(350))
    text = db.Column('text', db.Text)
    created_time = db.Column('created_time', db.DateTime, nullable=False)
    image_name = db.Column('image_name', db.String(225))
    image_path = db.Column('image_path', db.String(225))
    rate = db.Column('rate', db.Float())

    community_id = db.Column('community_id', db.Integer,
                             db.ForeignKey('created_community.id', ondelete='CASCADE', onupdate='CASCADE'),
                             nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)

    def as_dict(self,active_user_id):
        is_my_review = False
        if self.user_id == active_user_id:
            is_my_review = True
        return {
                'id' : self.id,
            'title': self.places_review.community_name if self.places_review.community_name is not None else '',
                'text' : self.text if self.text is not None else '',
            'image': self.image_path if self.image_path is not None else '',
            'user_id': str(self.user_id),
            'user_image': self.places_review_id.image_path,
            'username': self.places_review_id.fullname,
            'is_my_review': is_my_review,
            'rate': str(self.rate) if self.rate is not None else '0'
        }

    def as_dict2(self, active_user_id):
        type = 'text'
        if self.image_path is not None:
            type = 'image'

        is_my_feed = False
        if self.user_id == active_user_id:
            is_my_feed = True

        is_like = False
        check_like = PlacesReviewLike.query.filter_by(user_id=active_user_id, review_id=self.id).first()
        if check_like:
            is_like = True

        input_date = datetime.strptime(str(self.created_time), "%Y-%m-%d %H:%M:%S")
        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        return {
            'id': self.id,
            'title': self.title if self.title is not None else '',
            'text': self.text if self.text is not None else '',
            'image': self.image_path if self.image_path is not None else '',
            'type': type,
            'user_id': str(self.user_id),
            'username': self.places_review_id.fullname,
            'user_image': self.places_review_id.image_path,
            'is_my_feed': is_my_feed,
            'video': '',
            'thumbnail': '',
            'created_time': output_date,
            'is_like': is_like,
            'review_type': 'places'

        }

class ThingsRecommendation(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    image_path = db.Column('image_path', db.String(225))
    text = db.Column('text', db.Text())
    link = db.Column('link', db.String(225))
    content_type = db.Column('content_type', db.String(225))
    have_image = db.Column('have_image', db.Boolean())

    community_id = db.Column('community_id', db.Integer, db.ForeignKey('created_things_community.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
    category_id = db.Column('category_id', db.Integer,
                            db.ForeignKey('things_category.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)

class PlacesRecommendation(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)

    image_path = db.Column('image_path', db.String(225))
    text = db.Column('text', db.Text())
    link = db.Column('link', db.String(225))
    content_type = db.Column('content_type', db.String(225))
    have_image = db.Column('have_image', db.Boolean())

    community_id = db.Column('community_id', db.Integer,
                             db.ForeignKey('created_community.id', ondelete='CASCADE', onupdate='CASCADE'),
                             nullable=False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    category_id = db.Column('category_id', db.Integer,
                            db.ForeignKey('category.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)


class PostLike(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    like_status = db.Column('like_status', db.Boolean())
    post_id = db.Column('post_id', db.Integer, db.ForeignKey('community_post.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)


    def as_dict(self):
        return {
                'id' : self.id,
                'like_status' : self.like_status,
                'chat_id': self.chat_id,
            'user_id': str(self.user_id),

        }

class PostThumsup(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    thums_status = db.Column('thums_status', db.Boolean())
    post_id = db.Column('chat_id', db.Integer, db.ForeignKey('community_post.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)


    def as_dict(self):
        return {
                'id' : self.id,
                'thums_status' : self.thums_status,
                'post_id': self.post_id,
            'user_id': str(self.user_id),

        }

class PostThumpdown(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    thums_status = db.Column('thums_status', db.Boolean())
    post_id = db.Column('post_id', db.Integer, db.ForeignKey('community_post.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)


    def as_dict(self):
        return {
                'id' : self.id,
                'thums_status' : self.thums_status,
                'post_id': self.post_id,
            'user_id': str(self.user_id),

        }

class PostComment(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    comment = db.Column('comment', db.String(500), nullable=False)
    created_time = db.Column('created_time',db.DateTime,nullable=False)

    post_id = db.Column('post_id', db.Integer, db.ForeignKey('community_post.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)


    def as_dict(self):
        return {
                'id' : self.id,
                'comment' : self.comment,
                'post_id': self.post_id,
            'user_id': str(self.user_id),

        }

class UnsavedCommunity(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    unsave = db.Column('unsave', db.Boolean())
    community_id = db.Column('community_id', db.Integer, nullable = False)
    category_id = db.Column('category_id', db.Integer, nullable = False)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id',ondelete='CASCADE',onupdate = 'CASCADE'), nullable = False)


    def as_dict(self):
        return {
                'id' : self.id,
                'unsave' : self.unsave,
                'community_id': self.community_id,
            'user_id': str(self.user_id),

        }

class CategoryVisited(db.Model):
    id = db.Column(db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    visited_counts = db.Column(db.Integer)

    category_id = db.Column(db.Integer,
                            db.ForeignKey('category.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)


class ThingsCategoryVisited(db.Model):
    id = db.Column(db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    visited_counts = db.Column(db.Integer)

    category_id = db.Column(db.Integer,
                            db.ForeignKey('things_category.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
