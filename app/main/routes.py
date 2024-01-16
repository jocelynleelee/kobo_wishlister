# app/main/routes.py
import secrets
import random
from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user, logout_user, login_user
from . import main
from .models.user import User
from .models.book import Book
from functools import wraps
from flask_mail import Message
from .models.registration_form import RegistrationForm
from .models.login_form import LoginForm
from .tasks import create_book
from app import db, bcrypt, cache, mail, celery_app
from sqlalchemy import desc, func


def generate_api_key():
    return secrets.token_urlsafe(16)

@main.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if not current_user.is_authenticated:
        return render_template('index.html')
    return redirect(url_for('main.wishlist'))

@main.route('/register', methods=['GET', 'POST'])
def register():

    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            username=form.username.data,
            password=hashed_password,
            api_key=generate_api_key(),
            email=form.email.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)

@main.route('/', methods=['GET', 'POST'])
@main.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('main.wishlist'))
        else:
            flash('Login unsuccessful. Check username and password.', 'danger')
    return render_template('login.html', form=form)

@main.route('/wishlist')
@login_required
def wishlist():
    books = Book.query.filter_by(user_id=current_user.id).all()
    grouped_data = {}
    for book in books:
        if book.title not in grouped_data:
            grouped_data[book.title] = {
                'id': book.book_id,
                'timestamps': [],
                'prices': []
            }
        grouped_data[book.title]['timestamps'].append(book.timestamp)
        grouped_data[book.title]['prices'].append(book.price)
        if not grouped_data[book.title].get("image_url"):
            grouped_data[book.title]["image_url"] = book.book_image
    return render_template('wishlist.html', grouped_data=grouped_data)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@main.route('/add_book_page')
@login_required
def add_book_page():
    return render_template('index.html')

@main.route('/add_book', methods=['POST'])
@login_required
def add_book():
    return login_required(add_book_login)()

@login_required
def add_book_login():
    if request.method == 'POST':
        book_id = request.form['book_id']
        new_book_result = create_book.apply_async(
            args=[book_id], countdown=1)
        this_book = new_book_result.get()
        if not isinstance(this_book, dict):
            flash('Book id doesn\'t seem to exist.')
            return render_template('index.html')
        new_book = Book(
            title=this_book["title"], 
            book_id=this_book["id"], 
            price=this_book["price"], 
            timestamp=this_book["timestamp"],
            book_image=this_book["image"],
            user_id=current_user.id)
        try:
            db.session.add(new_book)
            db.session.commit()
            flash('Book added to wishlist successfully!', 'success')
            return redirect(url_for('main.wishlist'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding this book to db', 'danger')
        return redirect(url_for('main.index'))
       
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
    if cache.get(api_key):
        return True
    user = User.query.filter_by(api_key=api_key).first()
    if user:
        cache.set(api_key, True)
    return user is not None

def get_user_by_api_key(api_key):
    return User.query.filter_by(api_key=api_key).first()

@main.route('/api/add_book', methods=['POST'])
@api_key_required
def add_book_api_key():
    user = request.user
    form_data = request.values
    new_book_result = create_book.apply_async(
            args=[form_data["book_id"]], countdown=1)
    new_book = new_book_result.get()
    return new_book

@main.route('/api/get_wishlist', methods=['POST'])
@api_key_required
def get_wishlist_api_key():
    this_user_id = request.user.id
    latest_prices = db.session.query(
        Book.title,
        db.func.max(Book.timestamp).label('latest_timestamp'),
        Book.price,
        Book.book_id 
    ).filter(
        Book.user_id == this_user_id
    ).group_by(
        Book.title
    ).all()
    unique_book_dict = {title: {"price": price, "book_id": book_id} \
                        for title, latest_timestamp, price, book_id in latest_prices }
    return unique_book_dict

@main.route('/api/update_wishlist', methods=['POST'])
@api_key_required
def update_wishlist_api_key():
    current_user_id = request.user.id
    books = get_wishlist_api_key()
    added_books = {}
    for book in books:
        new_book_result = create_book.apply_async(
            args=[str(books[book]["book_id"])], countdown=1)
        new_book = new_book_result.get()
        if isinstance(new_book, dict):
            new_book = Book(
            title=new_book["title"], 
            book_id=new_book["id"], 
            price=new_book["price"], 
            timestamp=new_book["timestamp"],
            book_image=new_book["image"],
            user_id=current_user_id)
            try:
                db.session.add(new_book)
                db.session.commit()
                added_books[new_book["title"]] = new_book
                
            except Exception as e:
                db.session.rollback()
                continue   
    return added_books


@main.route("/send_mail", methods=['POST'])
def send_price_drop_mail():
    # get all users from the db
    users = User.query.all()
    subject = 'Book Price Drop Notification'

    # update the wishlist first
    for user in users:
        update_wishlist(user)
        books = Book.query.filter_by(user_id=user.id).all()
        on_sale_books = []
        processed = []
        recipient = user.email
        username = user.username
        for book in books:
            if book.title in processed:
                continue
        # check the latest 2 prices to get the recipients
            processed.append(book.title)
            latest_prices = Book.query.filter_by(
                title=book.title).order_by(desc(Book.timestamp)).limit(2).all()
            if len(latest_prices) >= 2:
                latest_price = latest_prices[0].price
                second_last_price = latest_prices[1].price
                # if latest_price < second_last_price: # comment this out for testing
                on_sale_books.append((book, latest_price, second_last_price))

        if on_sale_books:
            body = render_template('price_drop_notification.html', 
                                user=username,
                                on_sale_books=on_sale_books)

            mail_message = Message(subject,
                              sender="jasmin2067@gmail.com",
                              recipients=[recipient],
                              html=body)
            mail.send(mail_message)

@main.route("/update_wishlist", methods=['POST'])
def update_wishlist(user):
    books = get_unique_books_for_user(user.id)
    for book in books:
        book_id = book[0]
        try:
            new_book_result = create_book.apply_async(
                args=[book_id], countdown=1)
            new_book = new_book_result.get()
        except Exception as e:
            print(str(e))
        if not isinstance(new_book, dict):
            continue
        new_book = Book(
        title=new_book["title"], 
        book_id=new_book["id"], 
        price=new_book["price"], 
        timestamp=new_book["timestamp"],
        book_image=new_book["image"],
        user_id=user.id)
        try:
            db.session.add(new_book)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            continue 

def get_unique_books_for_user(this_user_id):
    # Query to get unique books based on their titles for a specific user

    try:
        unique_books = (
            Book.query
            .filter_by(user_id=this_user_id)
            .with_entities(
                Book.book_id,
                Book.title,
                func.max(Book.timestamp).label('latest_timestamp'),
                func.max(Book.price).label('latest_price'),
                func.max(Book.book_image).label('latest_image_url')
            )
            .group_by(Book.title)
            .all()
        )
        return unique_books
    except Exception as e:
        print(f"Error fetching unique books: {str(e)}")
        return None
