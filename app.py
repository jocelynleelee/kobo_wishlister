# app.py
from main import WishList
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, ValidationError
from wtforms.validators import DataRequired, Length, EqualTo
from flask_bcrypt import Bcrypt
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wishlist.db'
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure secret key
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
kobo_wishlist = WishList()

# Database model for User
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    books = current_user.books
    # books = Book.query.all()
    return render_template('index.html', books=books)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, password=hashed_password)
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
            return redirect(url_for('index'))
        else:
            flash('Login unsuccessful. Check username and password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/add_book', methods=['POST'])
@login_required
def add_book():
    if request.method == 'POST':
        # Your route logic here
        book_id = request.form['book_id']
        this_book = kobo_wishlist.add(book_id)
        if not this_book:
            return 'failed to add this book!'
        new_book = Book(
            title=this_book["title"], 
            book_id=this_book["id"], 
            price=this_book["price"], 
            timestamp=this_book["timestamp"],
            user=current_user)
        
        try:
            db.session.add(new_book)
            db.session.commit()
            flash('Book added to wishlist successfully!', 'success')
            return redirect(url_for('wishlist'))
        except Exception as e:
            db.session.rollback()
            flash('Book with this ID already exists in the wishlist.', 'danger')
            return redirect(url_for('index'))
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
            grouped_data[book.title] = {'timestamps': [], 'prices': []}
        grouped_data[book.title]['timestamps'].append(book.timestamp)
        grouped_data[book.title]['prices'].append(book.price)

    return render_template('wishlist.html', grouped_data=grouped_data)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
