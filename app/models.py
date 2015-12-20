import datetime
from app import db
from flask.ext.login import UserMixin
from werkzeug import generate_password_hash, check_password_hash
from sqlalchemy.orm import load_only


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    social_id = db.Column(db.String(64), nullable=True, unique=True)
    join_date = db.Column(db.DateTime, nullable=False)
    nickname = db.Column(db.String(64), nullable=False, unique=True)
    email = db.Column(db.String(64), nullable=True)
    password = db.Column(db.String(66), nullable=True)
    user_fullname = db.Column(db.String(64), nullable=True)
    products = db.relationship('Product', backref='user', lazy='dynamic')
    reviews = db.relationship('Review', backref='user', lazy='dynamic')

    def __init__(self, social_id=None, nickname=None, email=None, password=None, user_fullname=None):
        if social_id is not None:
            self.social_id = social_id
        if email is not None:
            self.email = email
        if user_fullname is not None:
            self.user_fullname = user_fullname
        self.nickname = nickname
        if password is not None:
            self.set_password(password)
        self.join_date = datetime.datetime.now()

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        if self.password is None:
            return check_password_hash('', password)    # need to improve this
        return check_password_hash(self.password, password)

    def __repr__(self):
        return str(self.nickname)


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    pub_date = db.Column(db.DateTime, nullable=False)
    category = db.Column(db.String(70), nullable=True)
    phone = db.Column(db.String(70), nullable=True)
    contact_name = db.Column(db.String(70), nullable=True)
    services = db.Column(db.String(70), nullable=True)
    cell_number = db.Column(db.String(70), nullable=True)
    fax_number = db.Column(db.String(70), nullable=True)
    website = db.Column(db.String(70), nullable=True)
    email = db.Column(db.String(70), nullable=True)
    location = db.Column(db.String(70), nullable=True)
    address = db.Column(db.String(500), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    review_count = db.Column(db.Integer, nullable=True)
    image = db.Column(db.String(300), nullable=True)
    image2 = db.Column(db.String(300), nullable=True)
    image3 = db.Column(db.String(300), nullable=True)
    image4 = db.Column(db.String(300), nullable=True)
    status = db.Column(db.String(70), nullable=True)
    video = db.Column(db.String(300), nullable=True)
    reviews = db.relationship('Review', cascade="all,delete", backref='product', lazy='dynamic')
    views = db.Column(db.Integer, nullable=True)
    featured = db.Column(db.Boolean, nullable=True)

    def __init__(self, **kwargs):
        super(Product, self).__init__(**kwargs)
        self.category = self.category.lower()

    def owner_(self):
        return User.query.options(load_only("id")).get(self.owner_id)

    def reviews_(self):
        return Review.query.options(load_only("id")).filter(Review.product_id == self.id).all

    def __repr__(self):              # __unicode__ on Python 2
        return self.title.encode("utf-8")


class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    review_text = db.Column(db.String(500), nullable=False)
    pub_date = db.Column(db.DateTime, nullable=False)

    def product_(self):
        return Product.query.options(load_only("id")).get(self.product_id)

    def author_(self):
        return User.query.options(load_only("id")).get(self.author_id)

    def __init__(self, **kwargs):
        super(Review, self).__init__(**kwargs)

        return self.id

    def __repr__(self):              # __unicode__ on Python 2
        return str(self.review_text) + ' by ' + str(self.author_().nickname)
