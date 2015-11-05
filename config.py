import os

basedir = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db') #'mysql://root:1234@localhost/salink'  # 
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')

WTF_CSRF_ENABLED = True
MAX_CONTENT_LENGTH = 12 * 1024 * 1024

MEDIA_FOLDER = os.path.join(basedir, 'app/static/uploads/')  # https://pypi.python.org/pypi/Flask-thumbnails
MEDIA_URL = '/static/uploads/'

SECRET_KEY = 'you-will-never-guess'

# OAUTH_CREDENTIALS = {
#     'facebook': {
#         'id': '',
#         'secret': ''
#     },
#     'twitter': {
#         'id': '',
#         'secret': ''
#     }
# }
