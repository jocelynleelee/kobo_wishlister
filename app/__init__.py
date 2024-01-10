# app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from wishlister import WishList
from flask_caching import Cache
from celery import Celery

def create_app() -> Flask:
    app = Flask(__name__, template_folder='main/templates')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wishlist.db'
    app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure secret key
    app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
    app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
    return app

app = create_app()

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
