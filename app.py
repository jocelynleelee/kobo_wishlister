# app.py
from flask import Flask
from celery import Celery, Task
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_caching import Cache
from main import WishList
import secrets
from functools import wraps
from flask import render_template, Blueprint, redirect, url_for, flash, request, jsonify
from flask_login import login_user, login_required, logout_user, current_user
# from models.models import *
# from models.config import db
# from tasks import create_book
from flask_sqlalchemy import SQLAlchemy


def create_app() -> Flask:
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wishlist.db'
    app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure secret key
    app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
    app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
    return app

kobo_wishlist = WishList()
app = create_app()
celery_app = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery_app.conf.update(app.config)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# route_bp = Blueprint("routes", __name__, template_folder="templates")

@celery_app.task
def create_book(current_user_id, book_id):
    this_book = kobo_wishlist.add(book_id)
    if not this_book:
        return 'failed to add this book!'
    
    return this_book

from datetime import datetime
from flask_login import UserMixin
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length, EqualTo
from wtforms import StringField, PasswordField, SubmitField, ValidationError
# from app import db


# Database model for User
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    api_key = db.Column(db.String(16), unique=True)
    books = db.relationship('Book', backref='user', lazy=True)
    
# Database model for Book
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    book_id = db.Column(db.String(20), nullable=False, unique=False)
    price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Registration form
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username is already taken. Please choose a different one.')

# Login form
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# route_bp = Blueprint("routes", __name__, template_folder="templates")

def generate_api_key():
    return secrets.token_urlsafe(16)

def update_db(current_user_id, this_book):
    new_book = Book(
        title=this_book["title"], 
        book_id=this_book["id"], 
        price=this_book["price"], 
        timestamp=this_book["timestamp"],
        user_id=current_user_id)
    
    try:
        db.session.add(new_book)
        db.session.commit()
        flash('Book added to wishlist successfully!', 'success')
        return redirect(url_for('wishlist'))
    except Exception as e:
        db.session.rollback()
        # flash(str(e))
        flash('Book with this ID already exists in the wishlist.', 'danger')
        # return redirect(url_for('index'))
        return redirect(url_for('wishlist'))
    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# @celery_app.route('/')
@app.route('/', methods=['GET'])
@login_required
def index():
    books = current_user.books
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            username=form.username.data,
            password=hashed_password,
            api_key=generate_api_key())
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('wishlist'))
        else:
            flash('Login unsuccessful. Check username and password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/', methods=['POST'])
@login_required
def add_book():    
    return login_required(add_book_login)()
        
@login_required
def add_book_login():
    if request.method == 'POST':
        # Your route logic here
        book_id = request.form['book_id']
        # Call the Celery task asynchronously using delay()
        new_book_object = create_book.apply_async(args=[current_user.id, book_id], countdown=1)
        new_book_dict = new_book_object.get()
        new_book = Book(
            title=new_book_dict["title"], 
            book_id=new_book_dict["id"], 
            price=new_book_dict["price"], 
            timestamp=new_book_dict["timestamp"],
            user_id=current_user.id)
        
        try:
            db.session.add(new_book)
            db.session.commit()
            flash('Book added to wishlist successfully!', 'success')
            return redirect(url_for('wishlist'))
        except Exception as e:
            db.session.rollback()
            # flash(str(e))
            flash('Book with this ID already exists in the wishlist.', 'danger')
            return redirect(url_for('wishlist'))
    else:
        return 'Invalid request method'

@app.route('/wishlist')
@login_required
def wishlist():
    # get the books for the current user
    books = Book.query.filter_by(user_id=current_user.id).all()

    grouped_data = {}
    for book in books:
        if book.title not in grouped_data:
            grouped_data[book.title] = {
                'id': book.book_id,
                'timestamps': [], 'prices': []}
        grouped_data[book.title]['timestamps'].append(book.timestamp)
        grouped_data[book.title]['prices'].append(book.price)

    return render_template('wishlist.html', grouped_data=grouped_data)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

def api_key_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('API-Key')

        # Validate the API key (you may need to query your user database)
        if not is_valid_api_key(api_key):
            return jsonify({'error': 'Invalid API key'}), 401
        # If the API key is valid, get the user
        user = get_user_by_api_key(api_key)

        # Attach the user to the request context for later use
        request.user = user
        return func(*args, **kwargs)

    return decorated_function

###############################
#             API             #
###############################

def is_valid_api_key(api_key):
    # Implement your API key validation logic (query your user database, etc.)
    # Return True if the API key is valid, False otherwise
    if cache.get(api_key):
        return True
    user = User.query.filter_by(api_key=api_key).first()
    if user:
        cache.set(api_key, True)
    return user is not None

def get_user_by_api_key(api_key):
    # Implement your logic to retrieve the user based on the API key
    # This might involve querying your user database
    # Return the user object or None if not found
    return User.query.filter_by(api_key=api_key).first()

@app.route('/api/add_book', methods=['POST'])
@api_key_required
def add_book_api_key():
    # Check if the provided API key matches the user's API key
    user = request.user  # Access the user from the request context
    form_data = request.values
    return create_book(user, form_data["book_id"])


    
if __name__ == '__main__':
    # app.run(debug=True)
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
    
