# app.py
import secrets
from main import WishList
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, ValidationError
from wtforms.validators import DataRequired, Length, EqualTo
from flask_bcrypt import Bcrypt

from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from flask_caching import Cache  # Use a caching library like Flask-Caching
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wishlist.db'
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure secret key
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
kobo_wishlist = WishList()

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

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

def generate_api_key():
    return secrets.token_urlsafe(16)

def create_book(this_user, book_id):
    this_book = kobo_wishlist.add(book_id)
    if not this_book:
        return 'failed to add this book!'
    new_book = Book(
        title=this_book["title"], 
        book_id=this_book["id"], 
        price=this_book["price"], 
        timestamp=this_book["timestamp"],
        user=this_user)
    
    try:
        db.session.add(new_book)
        db.session.commit()
        flash('Book added to wishlist successfully!', 'success')
        return redirect(url_for('wishlist'))
    except Exception as e:
        db.session.rollback()
        flash('Book with this ID already exists in the wishlist.', 'danger')
        # return redirect(url_for('index'))
        return redirect(url_for('wishlist'))
    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    books = current_user.books
    # books = Book.query.all()
    # return redirect(url_for('wishlist'))
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
        return create_book(current_user, book_id)
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
    # Now you can use the user object to associate the book with the user
    # book_data = request.get_json()
    # new_book = Book(title=book_data['title'], user_id=user.id)
    # return jsonify({'message': 'Book added successfully'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
