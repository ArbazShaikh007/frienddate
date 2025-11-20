from base.database.db import db
from base.admin.models import Admin, Cms
from base.user.models import User

def admin_insert_data(x):
    db.session.add(x)
    db.session.commit()

def admin_view_data():
    return Admin.query.all()

def admin_validate(x):
    return Admin.query.filter_by(email = x).first()

def admin_update_data(object):
    db.session.merge(object)
    db.session.commit()
def terms_condition(x):
    return Cms.query.filter_by(id=x).first()
def block(x):
    return User.query.filter_by(id = x).first()
