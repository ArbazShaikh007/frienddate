from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

def initialize_db(app):
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] ='mysql+pymysql://root:root@localhost:3306/friend_datedb?charset=utf8'
    app.config['SQLALCHEMY_PRE_PING'] = True

    db.init_app(app)
    migrate.init_app(app, db)