import os
from flask import Flask
from base.database.db import initialize_db,db
from flask_login import LoginManager
from base.user.models import User
from base.admin.auth import UPLOAD_FOLDER,ADMIN_FOLDER,CATEGORY_FOLDER
from base.admin.models import Admin
from flask_moment import Moment
from base.common.schedulers import scheduler

from dotenv import load_dotenv
load_dotenv()

login_manager = LoginManager()
moment = Moment()
app = Flask(__name__)

def create_app():

    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
    app.config['TESTING'] = False
    # app.config['SQLALCHEMY_ECHO'] = True
    # app.config['SQLALCHEMY_RECORD_QUERIES'] = True
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['ADMIN_FOLDER'] = ADMIN_FOLDER
    app.config['CATEGORY_FOLDER'] = CATEGORY_FOLDER


    app.config['SQLALCHEMY_DATABASE_URI'] ='mysql+pymysql://root:root@localhost:3306/friend_datedb?charset=utf8'
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = 0
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 465
    app.config['MAIL_USE_TLS'] = False
    app.config['MAIL_USE_SSL'] = True
    app.config['MAIL_USERNAME'] = 'arbaz78673@gmail.com'
    app.config['MAIL_PASSWORD'] = 'eivfguphdyorfjuj'

    login_manager.init_app(app)
    moment.init_app(app)

    initialize_db(app)
    # mail.init_app(app)

    from base.user.auth import user_auth
    from base.user.view import user_view
    from base.admin.auth import admin_auth
    from base.admin.view import admin_views
    from base.community.create import community_create

    from base.v2.user.auth import user_auth_v2
    from base.v2.user.view import user_view_v2
    from base.v2.admin.auth import admin_auth_v2
    from base.v2.admin.view import admin_views_v2
    from base.v2.community.create import community_create_v2

    from base.v3.user.auth import user_auth_v3
    from base.v3.user.view import user_view_v3
    from base.v3.admin.auth import admin_auth_v3
    from base.v3.admin.view import admin_views_v3
    from base.v3.community.create import community_create_v3

    from base.v4.user.auth import user_auth_v4
    from base.v4.user.view import user_view_v4
    from base.v4.admin.auth import admin_auth_v4
    from base.v4.admin.view import admin_views_v4
    from base.v4.community.create import community_create_v4

    from base.v5.user.auth import user_auth_v5
    from base.v5.user.view import user_view_v5
    from base.v5.admin.auth import admin_auth_v5
    from base.v5.admin.view import admin_views_v5
    from base.v5.community.create import community_create_v5

    app.register_blueprint(user_auth, url_prefix='/')
    app.register_blueprint(user_view, url_prefix='/')
    app.register_blueprint(admin_auth, url_prefix='/')
    app.register_blueprint(admin_views, url_prefix='/')
    app.register_blueprint(community_create, url_prefix='/')

    app.register_blueprint(user_auth_v2, url_prefix='/v2')
    app.register_blueprint(user_view_v2, url_prefix='/v2')
    app.register_blueprint(admin_auth_v2, url_prefix='/v2')
    app.register_blueprint(admin_views_v2, url_prefix='/v2')
    app.register_blueprint(community_create_v2, url_prefix='/v2')

    app.register_blueprint(user_auth_v3, url_prefix='/v3')
    app.register_blueprint(user_view_v3, url_prefix='/v3')
    app.register_blueprint(admin_auth_v3, url_prefix='/v3')
    app.register_blueprint(admin_views_v3, url_prefix='/v3')
    app.register_blueprint(community_create_v3, url_prefix='/v3')

    app.register_blueprint(user_auth_v4, url_prefix='/v4')
    app.register_blueprint(user_view_v4, url_prefix='/v4')
    app.register_blueprint(admin_auth_v4, url_prefix='/v4')
    app.register_blueprint(admin_views_v4, url_prefix='/v4')
    app.register_blueprint(community_create_v4, url_prefix='/v4')

    app.register_blueprint(user_auth_v5, url_prefix='/v5')
    app.register_blueprint(user_view_v5, url_prefix='/v5')
    app.register_blueprint(admin_auth_v5, url_prefix='/v5')
    app.register_blueprint(admin_views_v5, url_prefix='/v5')
    app.register_blueprint(community_create_v5, url_prefix='/v5')

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":  # Only run in main reloaded process
        if not scheduler.running:
            scheduler.init_app(app)
            scheduler.start()
            print("Scheduler started")

    # this below is  initialize kind of model so can create tables
    @login_manager.user_loader
    def load_user(id):
        return Admin.query.get(int(id))

    return app
print("in u_controller")


