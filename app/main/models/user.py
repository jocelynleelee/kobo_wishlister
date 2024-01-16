from app import db
from flask_login import UserMixin

# Database model for User
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(320), unique=True, nullable=False)
    api_key = db.Column(db.String(16), unique=True)
    books = db.relationship('Book', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'