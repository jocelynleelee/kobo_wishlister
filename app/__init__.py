# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_caching import Cache
from wishlister import WishList
from celery import Celery

def create_app() -> Flask:
    app = Flask(__name__, template_folder='main/templates')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wishlist.db'
    app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure secret key
    app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
    app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 465
    app.config['MAIL_USE_TLS'] = False
    app.config['MAIL_USE_SSL'] = True
    app.config['MAIL_USERNAME'] = 'jasmin2067@gmail.com'
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    return app

app = create_app()
mail = Mail(app)
celery_app = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery_app.conf.update(app.config)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
login_manager.login_view = 'main.login'
kobo_wishlist = WishList()
from .main import main as main_blueprint

app.register_blueprint(main_blueprint)


from app.main.models.user import User
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))






# Import your routes and other components
from .main import routes, tasks, models
