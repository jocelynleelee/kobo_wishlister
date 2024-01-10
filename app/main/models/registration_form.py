from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length, EqualTo
from wtforms import StringField, PasswordField, SubmitField, ValidationError
# from main.routes import db
from app import db
from ..models.user import User

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