from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.thumbnails import Thumbnail
from flask_limiter import Limiter

app = Flask(__name__)

app.config.from_object('config')

db = SQLAlchemy(app)

# THUMBNAILS#
# https://pypi.python.org/pypi/Flask-thumbnails
thumb = Thumbnail(app)

limiter = Limiter(app)

login_manager = LoginManager(app)

from app import views, models