from base.database.db import db
from base.community.models import PostLike,PostThumsup,CommunityPost,PostThumpdown,CreatedCommunity
from base.user.models import User

def community_insert_data(x):
    db.session.add(x)
    db.session.commit()
# def community_comments(x):
#     return CommunityComment.query.filter_by(community_id=x).all()

def get_user_data(x):
    return User.query.filter_by(id=x).first()

# def liked_community(x,y):
#     return CommunityLike.query.filter(CommunityLike.user_id == x, CommunityLike.community_id == y).count() > 0

# def add_community_like(x,y):
#     like_add = CommunityLike(user_id= x, community_id= y, like_status=True)
#     db.session.add(like_add)
#     db.session.commit()
#
# def delete_community_like(x,y):
#     CommunityLike.query.filter_by(user_id= x, community_id= y).delete()
#     db.session.commit()

def get_community_chat(x):
    return CommunityPost.query.filter_by(id=x).first()

def liked_chats(x,y):
    return PostLike.query.filter(PostLike.user_id == x, PostLike.post_id == y).count() > 0

def add_like(x,y):
    like_add = PostLike(user_id= x, post_id= y, like_status=True)
    db.session.add(like_add)
    db.session.commit()

def delete_like(x,y):
    PostLike.query.filter_by(user_id= x, post_id= y).delete()
    db.session.commit()

def thumpsup_chats(x,y):
    return PostThumsup.query.filter(PostThumsup.user_id == x, PostThumsup.post_id == y).count() > 0

def thumsup(x,y):
    like_add = PostThumsup(user_id= x, post_id= y, thums_status=True)
    db.session.add(like_add)
    db.session.commit()

def delete_thumsup(x,y):
    PostThumsup.query.filter_by(user_id= x, post_id= y).delete()
    db.session.commit()

def thumpsdown_chats(x,y):
    return PostThumpdown.query.filter(PostThumpdown.user_id == x, PostThumpdown.post_id == y).count() > 0

def thumsdown(x,y):
    like_add = PostThumpdown(user_id= x, post_id= y, thums_status=True)
    db.session.add(like_add)
    db.session.commit()

def delete_thumsdown(x,y):
    PostThumpdown.query.filter_by(user_id= x, post_id= y).delete()
    db.session.commit()
def get_community(x):
    return CreatedCommunity.query.filter_by(id=x).first()