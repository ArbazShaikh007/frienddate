from base.database.db import db
from base.user.models import User,FriendRequest,SelectedCategory

def insert_data(x):
    db.session.add(x)
    db.session.commit()

def view_data():
    return User.query.filter_by(deleted = False).all()

def validate(x):
    return User.query.filter_by(email = x).first()

def update_data(object):
    db.session.merge(object)
    db.session.commit()

def sent_frnd_req(x,y):
    return FriendRequest.query.filter(FriendRequest.by_id == x,FriendRequest.to_id==y).count() > 0

def delete_frnd_req(x,y):
    FriendRequest.query.filter_by(by_id = x,to_id=y).delete()
    db.session.commit()
def check_cat_id(x,y):
    return SelectedCategory.query.filter(SelectedCategory.user_id == x, SelectedCategory.category_id == y).count() > 0

def delete_cat(x,y):
    SelectedCategory.query.filter_by(user_id= x, category_id= y).delete()
    db.session.commit()


# check = FriendRequest.query.filter_by(to_id=active_user.id,by_id = user_id, request_status=True).first()
#
#     print('chekkkkkkkkkkkkkkkkkkkkkkk11111111111',check)
#
#     checked = FriendRequest.query.filter_by(by_id=active_user.id,to_id = user_id, request_status=True).first()
#     print('checkedddddddddddddddddddd222222222222222222',checked)
#
# if check is None and checked is None:
