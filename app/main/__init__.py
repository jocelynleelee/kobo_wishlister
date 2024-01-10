# app/__init__.py

from flask import Blueprint

main = Blueprint('main', __name__, template_folder='templates')

# Import routes here
from . import routes

