import datetime
import random
import urllib2
from flask import redirect, url_for, render_template, flash, request, json,\
    jsonify, Response, escape, abort
from app import app, login_manager, db, limiter
from flask.ext.assets import Environment, Bundle
from flask.ext.login import login_user, logout_user, current_user
from pf_oauth import OAuthSignIn
from models import User, Product, Review, Vote
# WTF FORMS
from flask_wtf import Form
from wtforms import StringField, PasswordField, HiddenField, SubmitField, SelectField
from wtforms.widgets import TextArea
from wtforms.validators import DataRequired, Length, ValidationError,\
    InputRequired, Email
from wtforms.fields.html5 import EmailField
from werkzeug import secure_filename, url_decode
from flask_wtf.file import FileField, FileAllowed, FileRequired
from ago import human
import opengraph
from sqlalchemy.orm import load_only

# Compile Sass using Flask-assets
assets = Environment(app)
assets.url = app.static_url_path
# Bootstrap Sass
bootstrap = Bundle(
    'sass/bootstrap/bootstrap.scss',
    filters='pyscss, cssmin',
    output='css/bootstrap.min.css')
# Custom Sass
custom_sass = Bundle(
    'sass/style.scss',
    filters='pyscss, cssmin',
    output='css/style.min.css')
assets.register('bootstrap', bootstrap)
assets.register('custom_sass', custom_sass)
# /Compile Sass using Flask-assets

# pagination
POSTS_PER_PAGE = 9

#all categories
CATEGORIES = [('Architecture', 'Architecture'), ('Carpet', 'Carpet'), ('Grocery Store', 'Grocery Store'), ('Real Estate/Realtor/Mortgage', 'Real Estate/Realtor/Mortgage'), ('Printing', 'Printing'), ('Auto Mechanic/Buying/Selling', 'Auto Mechanic/Buying/Selling'), ('Woodworking', 'Woodworking'), ('School', 'School'), ('Draperies/Curtains', 'Draperies/Curtains'), ('Newspaper', 'Newspaper'), ('Insurance', 'Insurance'), ('Restaurant/Sweet Shop', 'Restaurant/Sweet Shop'), ('Bank/Money', 'Bank/Money'), ('Remittance', 'Remittance'), ('Glass', 'Glass'), ('Worship Places', 'Worship Places'), ('Accountant', 'Accountant'), ('Traveling Agency', 'Traveling Agency'), ('Construction', 'Construction'), ('Clinic/Pharmacy', 'Clinic/Pharmacy'), ('Boutique/Clothing', 'Boutique/Clothing'), ('Jewelers', 'Jewelers'), ('Painting', 'Painting'), ('Optics/Glasses', 'Optics/Glasses'), ('Electronic', 'Electronic'), ('Furniture', 'Furniture'), ('Moving Companies', 'Moving Companies'), ('Stationary', 'Stationary'), ('Others', 'Others')]

# sudo apt-get install libjpeg-dev
# thumbs

login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


# Forms
class AddProduct(Form):
    title = StringField('Name', validators=[DataRequired("Title is required"), Length(message="Title must be 1 to 70 characters long", min=1, max=70)])
    category = SelectField('Category', choices=CATEGORIES, validators=[DataRequired("Category is required")])
    address = StringField('Address', validators=[Length(message="address cannot be longer than 500 characters", min=0, max=500)], widget=TextArea())
    phone = StringField('Phone Number', validators=[DataRequired("Phone Numeber is required"), Length(message="Phone Number must be 5 to 70 characters long", min=5, max=70)])
    image = FileField('Image', validators=[FileRequired(), FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Images only!')])


class AddProductVid(Form):
    title = StringField('Title', validators=[DataRequired("Title is required"), Length(message="Title must be 1 to 70 characters long", min=1, max=70)])
    category = SelectField('Category', choices=CATEGORIES, validators=[DataRequired("Category is required")])
    address = StringField('Address', validators=[Length(message="address cannot be longer than 500 characters", min=0, max=500)], widget=TextArea())
    phone = StringField('Phone Number', validators=[DataRequired("Phone Numeber is required"), Length(message="Phone Number must be 5 to 70 characters long", min=5, max=70)])
    video = StringField('URL', validators=[DataRequired("URL is required"), Length(min=5)])


class AddReview(Form):
    review_text = StringField('review_text', validators=[DataRequired("Review with 1-140 words is required"), Length(min=1, max=500)], widget=TextArea())


class SignupForm(Form):
    nickname = StringField("Username", validators=[DataRequired("Please enter your username."), Length(message="Username must be 3 to 14 characters long", min=3, max=14)])
    email = EmailField("Email Address", validators=[DataRequired("Please enter your email."), Email("Email is required")])
    password = PasswordField('Password', validators=[DataRequired("Please enter a password."), Length(message="Password must be 6 to 14 characters long", min=6, max=14)])
    submit = SubmitField("Create account")

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def validate(self):
        if not Form.validate(self):
            return False

        user = User.query.filter_by(nickname=self.nickname.data.lower()).first()
        email = User.query.filter_by(email=self.email.data.lower()).first()
        if user:
            self.nickname.errors.append("That Username is already taken")
            return False
        if email:
            self.email.errors.append("That Email is already registered")
            return False
        else:
            return True


class LoginForm(Form):
    nickname = StringField("Username", validators=[DataRequired("Please enter your username."), Length(min=3, max=14)])
    password = PasswordField('Password', validators=[DataRequired("Please enter a password."), Length(min=6, max=14, message="Password must be at least 6 characters")])
    submit = SubmitField("Sign In")

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def validate(self):
        if not Form.validate(self):
            return False

        user = User.query.filter_by(nickname=self.nickname.data.lower()).first()
        if user and user.check_password(self.password.data):
            login_user(user, True)
            return True
        else:
            self.nickname.errors.append("Invalid username or password")
            return False


def flash_errors(form, category):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ), category)


def product_review_count(products):
    r = {}
    for product in products:
        reviews = len(Review.query.options(load_only("product_id")).filter(Review.product_id == product.id).all())
        r[product.id] = reviews
    return r


def ago_format(date):
    return human(date, precision=1, past_tense='{} ago', future_tense='in {}')


def top_categories():
    this_month = datetime.date.today() - datetime.timedelta(days=60)
    p = Product.query.options(load_only("category")).filter(Product.pub_date > this_month).order_by(Product.views.desc()).limit(10).all()
    c = []
    for product in p:
        cat = [product.category]
        c.extend(cat)
    return set(c)

def site_url():
    return 'http://southasianlink.ca/'

app.jinja_env.globals.update(ago_format=ago_format, top_categories=top_categories, site_url=site_url)


# ------------------ ROUTES ---------------------------------------


@app.route('/')
def index():
    this_month = datetime.date.today() - datetime.timedelta(days=131)
    products = Product.query.filter(Product.pub_date > this_month).order_by(Product.views.desc()).paginate(1, 9, False)
    if current_user.is_authenticated() is True:
        return redirect(url_for('products'))

    return render_template('index.html', title='Home', products=products)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if request.method == 'POST':
        if not form.validate_on_submit():
            return render_template('signup.html', form=form)
        else:
            newuser = User(nickname=form.nickname.data, password=form.password.data, email=form.email.data)
            db.session.add(newuser)
            db.session.commit()
            login_user(newuser, True)
            return redirect(url_for('index'))

    elif request.method == 'GET':
        return render_template('signup.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        if form.validate() is False:
            return render_template('login.html', form=form)
        else:
            return redirect(url_for('index'))

    elif request.method == 'GET' and current_user.is_authenticated() is True:
        return redirect(url_for('index'))

    elif request.method == 'GET' and current_user.is_authenticated() is False:
        return render_template('login.html', form=form)


@app.route('/profile/<user>')
@app.route('/profile/<user>/<view>/')
@app.route('/profile/<user>/<view>/<int:page>')
def profile(user, view='p', page=1):
    if current_user.is_authenticated() and user == current_user.nickname:
        user = current_user
    else:
        user = User.query.filter(User.nickname == user).first_or_404()
    reviews = user.reviews.order_by(Review.pub_date.desc()).all()
    products = user.products.paginate(page, POSTS_PER_PAGE, False)
    return render_template('profile.html', user=user, reviews=reviews, products=products)


@app.route('/listing/')
@app.route('/listing/<view>/')
@app.route('/listing/<view>/<int:page>/')
def products(page=1, view='latest'):
    products = Product.query.order_by(Product.pub_date.desc()).paginate(page, POSTS_PER_PAGE, False)

    if view == 'trending':
        this_week = datetime.date.today() - datetime.timedelta(days=7)
        products = Product.query.filter(Product.pub_date > this_week).order_by(Product.views.desc()).paginate(page, POSTS_PER_PAGE, False)
    if view == 'most-viewed':
        products = Product.query.order_by(Product.views.desc()).paginate(page, POSTS_PER_PAGE, False)
    if view == 'passing':
        products = Product.query.filter(Product.passes > Product.fails).order_by(Product.passes.desc()).paginate(page, POSTS_PER_PAGE, False)
    if view == 'failing':
        products = Product.query.filter(Product.fails > Product.passes).order_by(Product.fails.desc()).paginate(page, POSTS_PER_PAGE, False)
    if view == 'most-reviewed':
        products = Product.query.order_by(Product.review_count.desc()).paginate(page, POSTS_PER_PAGE, False)
    if view == 'tied':
        products = Product.query.filter((Product.fails == Product.passes) >= 1).order_by(Product.fails.desc()).paginate(page, POSTS_PER_PAGE, False)

    return render_template('products.html', products=products, view=view)


@app.route('/category/<category>/')
@app.route('/category/<category>/<view>')
@app.route('/category/<category>/<view>/<int:page>/')
def category(page=1, category=None, view='latest'):
    if category is None:
        return redirect(url_for('products'))

    products = Product.query.filter(Product.category == category).order_by(Product.pub_date.desc()).paginate(page, POSTS_PER_PAGE, False)

    if view == 'trending':
        this_week = datetime.date.today() - datetime.timedelta(days=7)
        products = Product.query.filter(Product.pub_date > this_week, Product.category == category).order_by(Product.views.desc()).paginate(page, POSTS_PER_PAGE, False)
    if view == 'most-viewed':
        products = Product.query.filter(Product.category == category).order_by(Product.views.desc()).paginate(page, POSTS_PER_PAGE, False)
    if view == 'passing':
        products = Product.query.filter(Product.passes > Product.fails, Product.category == category).order_by(Product.passes.desc()).paginate(page, POSTS_PER_PAGE, False)
    if view == 'failing':
        products = Product.query.filter(Product.fails > Product.passes, Product.category == category).order_by(Product.fails.desc()).paginate(page, POSTS_PER_PAGE, False)
    if view == 'most-reviewed':
        products = Product.query.filter(Product.category == category).order_by(Product.review_count.desc()).paginate(page, POSTS_PER_PAGE, False)
    if view == 'tied':
        products = Product.query.filter((Product.fails == Product.passes) >= 1, Product.category == category).order_by(Product.fails.desc()).paginate(page, POSTS_PER_PAGE, False)

    return render_template('category.html', products=products, category=category, view=view)


@app.route('/s/', methods=['GET'])
@app.route('/s/<int:page>', methods=['GET'])
def search(page=1):
    search = request.args.get('s')
    products = Product.query.options(load_only("id")).filter(Product.title.like('%' + search + '%')).paginate(page, POSTS_PER_PAGE, False)
    results = 1
    if len(products.items) == 0:
        results = 0

    return render_template('products.html', search=search, results=results, products=products)


@app.route('/listing/autocomplete', methods=['GET', 'POST'])
def autocomplete():
    search = unicode(request.args.get('q'))
    products = Product.query.options(load_only("title", "id")).filter(Product.title.startswith(search)).limit(5).all()
    products2 = Product.query.options(load_only("title", "id")).filter(Product.title.contains('%' + search + '%')).limit(5).all()
    p = {}
    q = []
    for product in products:
        # p.extend(['{ title:'+product.title+', image: '+product.image+'}'])
        p = {"label": product.title, "url": "/p/" + str(product.id)}
        q.extend([p])
    for product in products2:
        r = {"label": product.title, "url": "/p/" + str(product.id)}
        q.extend([r])

    seen = set()  # http://stackoverflow.com/questions/9427163/remove-duplicate-dict-in-list-in-python
    l = []
    for d in q:
        t = tuple(d.items())
        if t not in seen:
            seen.add(t)
            l.append(d)

    products = json.dumps(l)
    response = Response(products, mimetype='application/json')
    return response


@app.route('/listing/add', methods=['GET', 'POST'])
@limiter.limit("1/second")
def addproduct():
    imgform = AddProduct()
    vidform = AddProductVid()

    if not current_user.is_authenticated():
        return redirect(url_for('login'))

    if request.method == 'GET':
        return render_template('new.html', imgform=imgform, vidform=vidform)

    if imgform.validate_on_submit() and request.form.get('formtype') == 'image' and current_user.is_authenticated():
        title = imgform.title.data
        address = imgform.address.data
        category = imgform.category.data
        imagename = unicode(random.randint(9000, 10000)) + '-southasianlink-' + secure_filename(imgform.image.data.filename)
        imgform.image.data.save('app/static/uploads/' + imagename)                                 # save this
        pub_date = datetime.datetime.now()
        product = Product(title=title, pub_date=pub_date, category=category, owner_id=current_user.id, image=imagename, address=address, passes=0, fails=0)

        db.session.add(product)
        db.session.commit()

        flash('Added successfully', 'success')

        return redirect(url_for('product', id=product.id))
    elif request.form.get('formtype') == 'image' and current_user.is_authenticated():
        flash_errors(imgform, 'danger')
        return render_template('new.html', imgform=imgform, vidform=vidform)

    if vidform.validate_on_submit() and request.form.get('formtype') == 'video' and current_user.is_authenticated():
        title = vidform.title.data
        address = vidform.address.data
        category = vidform.category.data
        video_url = vidform.video.data
        if not video_url.startswith('http://'):
            if not video_url.startswith('https://'):
                video_url = "http://" + video_url
        pub_date = datetime.datetime.now()
        sites_allowed = ['dailymotion', 'youtube', 'tune.pk', 'playit.pk', 'vine.co', 'vimeo.com', 'soundcloud.com']

        # check if from sites_allowed
        if not any(site in video_url for site in sites_allowed):
            flash("Not a valid video URL", 'danger')
            return render_template('new.html', imgform=imgform, vidform=vidform)

        # proceed if not
        try:
            video = opengraph.OpenGraph(url=video_url)
        except:
            video = None

        if "playit.pk" in video_url:
            vid_id = video.url.split('?v=')[1]
            vid = "https://playit.pk/embed-t?v=" + vid_id
            # image = "http://img.playit.pk/vi/{0}/hqdefault.jpg".format(vid_id)
            if video.get('image'):
                image = video.image
                imagename = unicode(random.randint(9000, 10000)) + '-southasianlink-' + secure_filename(title) + ".jpg"
                with open('app/static/uploads/' + imagename, 'w') as f:
                    req = urllib2.Request(image, headers={'User-Agent': "Mozilla"})
                    f.write(urllib2.urlopen(req, timeout=15).read())
            else:
                imagename = "placeholder-video.png"

        elif "tune.pk" in video_url:
            vid_id = video.video.split('?videoid=')[1]
            vid = "http://tune.pk/player/embed_player.php?vid={0}&autoplay=no".format(vid_id)
            if video.get('image'):
                image = video.get('image')
                imagename = unicode(random.randint(9000, 10000)) + '-southasianlink-' + secure_filename(video.get('title')) + ".jpg"
                with open('app/static/uploads/' + imagename, 'w') as f:
                    f.write(urllib2.urlopen(image, timeout=15).read())
            else:
                imagename = "placeholder-video.png"

        elif "soundcloud.com" in video_url:
            vid = video.get('player')
            if video.get('image'):
                image = video.get('image:src').replace("https://", "http://")
                imagename = unicode(random.randint(9000, 10000)) + '-southasianlink-' + secure_filename(video.get('title')) + ".jpg"
                with open('app/static/uploads/' + imagename, 'w') as f:
                    req = urllib2.Request(image, headers={'User-Agent': "Mozilla"})
                    f.write(urllib2.urlopen(req, timeout=15).read())
            else:
                imagename = "placeholder-video.png"

        else:
            if video is None or not video.is_valid():
                flash("Not a valid video URL", 'danger')
                return render_template('new.html', imgform=imgform, vidform=vidform)

            if video.get('video'):
                vid = video.get('video')
            if video.get('video:url'):
                vid = video.get('video:url')
            if "vimeo.com/" in video_url:
                vid_id = video.get("video:url").split('clip_id=')[1].split('&')[0]
                vid = "https://player.vimeo.com/video/{0}".format(vid_id)

            if video.get('image'):
                image = video.get('image')
                imagename = unicode(random.randint(9000, 10000)) + '-southasianlink-' + secure_filename(video.get('title')) + ".jpg"
                with open('app/static/uploads/' + imagename, 'w') as f:
                    f.write(urllib2.urlopen(image, timeout=15).read())
            else:
                imagename = "placeholder-video.png"

        product = Product(title=title, pub_date=pub_date, owner_id=current_user.id, category=category, video=vid, image=imagename, address=address, passes=0, fails=0)

        db.session.add(product)
        db.session.commit()

        return redirect(url_for('product', id=product.id))

    elif request.form.get('formtype') == 'video' and current_user.is_authenticated():
        flash_errors(vidform, 'danger')
        return render_template('new.html', imgform=imgform, vidform=vidform)


@app.route('/p/<id>', methods=['GET'])
def product(id):
    product = Product.query.get_or_404(id)
    xposts = Product.query.options(load_only("id")).filter(Product.id < id).order_by(Product.pub_date.desc()).limit(7).all()

    prod_next = Product.query.options(load_only("id")).filter(Product.id < id).order_by(Product.pub_date.desc()).limit(1).first()  # Product.query.get(next_id)
    prod_prev = Product.query.options(load_only("id")).filter(Product.id > id).order_by(Product.pub_date.desc()).limit(1).first()
    reviews = product.reviews.all()
    reviewform = AddReview()
    already_voted = False
    myvote = None
    my_vote = None
    review_exists = False

    for review in reviews:
        if review.review_text is not None:
            review_exists = True

    if current_user.is_authenticated():
        myvote = Vote.query.options(load_only("id")).filter(Vote.author_id == current_user.id, Vote.product_id == id).order_by(Vote.pub_date.desc()).first()

        if myvote:
            already_voted = True
            if myvote.vote is True:
                my_vote = "pass"
            if myvote.vote is False:
                my_vote = "fail"

    if request.method == 'GET':
        if product.views is not None:
            product.views += 1
            db.session.commit()
        else:
            product.views = 1
            db.session.commit()

    return render_template('product.html', review_exists=review_exists, my_vote=my_vote, product=product, reviewform=reviewform, reviews=reviews, already_voted=already_voted, prod_next=prod_next, prod_prev=prod_prev, xposts=xposts)


@app.route('/p/<id>/vote/', methods=['POST'])
@limiter.limit("15/minute")
@limiter.limit("2/second")
def product_post_vote(id):
    product = Product.query.options(load_only("id")).get_or_404(id)
    already_voted = False
    myvote = None
    my_vote = None

    if not current_user.is_authenticated():
        abort(401)

    if current_user.is_authenticated():
        myvote = Vote.query.options(load_only("vote")).filter(Vote.author_id == current_user.id, Vote.product_id == id).order_by(Vote.pub_date.desc()).first()

        if myvote:
            already_voted = True
            if myvote.vote is True:
                my_vote = "pass"
            if myvote.vote is False:
                my_vote = "fail"

    if current_user.is_authenticated() and already_voted is False:
        product_id = product.id
        author_id = current_user.id
        pub_date = datetime.datetime.now()
        vote = request.form.get('vote')

        if vote == 'pass':
            voted = Vote(product_id=product_id, author_id=author_id, vote=True, pub_date=pub_date)

        elif vote == 'fail':
            voted = Vote(product_id=product_id, author_id=author_id, vote=False, pub_date=pub_date)
        # product.image = request.form['image']
        if vote is not None:
            db.session.add(voted)
            db.session.commit()

            # flash('Updated successfully', 'success')
            
            resp = {'points': current_user.points, 'passes': product.passes, 'fails': product.fails}

            return Response(json.dumps(resp), mimetype='application/json')
            # redirect(url_for('product', id=product_id))

        if vote is None:
            flash('You forgot to vote', 'danger')

            return redirect(url_for('product', id=product_id))

    if current_user.is_authenticated() and already_voted is True:

        if request.form.get('votechange'):
            vote = request.form.get('votechange')
            if vote == "pass" and myvote.vote is False:
                product.pass_it()
                product.fails -= 1
                myvote.vote = not myvote.vote
            if vote == "fail" and myvote.vote is True:
                product.fail_it()
                product.passes -= 1
                myvote.vote = not myvote.vote
            myvote.pub_date = datetime.datetime.now()

            db.session.commit()
            # flash("Vote changed", 'success')

            resp = {'points': current_user.points, 'passes': product.passes, 'fails': product.fails}

            return jsonify(resp)
            # redirect(url_for('product', id=product_id))


@app.route('/p/<id>/review/', methods=['POST'])
@limiter.limit("12/minute")
@limiter.limit("1/second")
def product_post_review(id):
    product_id = id
    reviewform = AddReview()
    already_voted = False
    myvote = None
    my_vote = None

    if not current_user.is_authenticated():
        abort(401)

    if current_user.is_authenticated():
        myvote = Vote.query.options(load_only("id")).filter(Vote.author_id == current_user.id, Vote.product_id == id).order_by(Vote.pub_date.desc()).first()

        if myvote:
            already_voted = True

    if current_user.is_authenticated():
        author_id = current_user.id
        pub_date = datetime.datetime.now()

        if reviewform.validate_on_submit():
            review_text = unicode(reviewform.review_text.data)
            review = Review(product_id=product_id, author_id=author_id, pub_date=pub_date, review_text=review_text)
            db.session.add(review)
            db.session.commit()
            resp = {'user': current_user.nickname, 'points': current_user.points, 'review': escape(review_text), 'reviewid': review.id}
            return jsonify(resp)
            # return redirect(url_for('product', id=product_id)) #            +'#'+unicode(review.id))
        else:
            return "Something went wrong", 406


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous():
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()


@app.route('/callback/<provider>')
def oauth_callback(provider):
    if not current_user.is_anonymous():
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    social_id, username, user_fullname = oauth.callback()
    if social_id is None:
        flash('Authentication failed.', 'danger')
        return redirect(url_for('index'))
    user = User.query.filter_by(social_id=social_id).first()
    if not user:
        user = User(social_id=social_id, nickname=username, user_fullname=user_fullname)
        db.session.add(user)
        db.session.commit()
    login_user(user, True)
    return redirect(url_for('index'))

# ============================ Deleting Stuff ===============================


@app.route('/p/<id>/delete', methods=['POST'])
def delete_product(id):
    product = Product.query.options(load_only("id")).get_or_404(id)
    title = "'" + product.title + "' deleted"
    if current_user.is_authenticated() and current_user.id == product.owner_id:
        points = product.passes
        current_user.points -= (10 + points)
        db.session.delete(product)
        db.session.commit()
        flash(title, "danger")
    return redirect(url_for('index'))


@app.route('/r/<id>/delete', methods=['POST'])
def delete_review(id):
    review = Review.query.filter(Review.id == id).first()
    product_id = review.product_id
    if current_user.is_authenticated() and current_user.id == review.author_id:
        current_user.points -= 2
        review.product.review_count -= 1
        db.session.delete(review)
        db.session.commit()
        # flash("Review deleted", "danger")
        resp = {'points': current_user.points}
        return jsonify(resp)

# ============================ /Deleting Stuff ===============================

# ============================ Pages ===============================

@app.route('/legal/<page>/')
def page(page):
    return render_template('legal.html', page=page)

# ============================ /Pages ===============================

@app.errorhandler(401)
def custom_401(error):
    return Response('Please Sign up or Log in', 401, {'WWWAuthenticate': 'Basic realm="Login Required"'})

@app.errorhandler(413)
def custom_413(e):
    return render_template('404.html', e=413), 413


@app.errorhandler(404)
def custom_404(e):
    return render_template('404.html', e=404), 404


@app.errorhandler(429)
def custom_429(e):
    return "You're doing that too much", 429


@app.errorhandler(500)
def custom_500(e):
    return render_template('404.html', e=500), 500


@app.route('/dbup')
def dbup():
    return ''

'''
THE API BEGINS here
=========================================================
=========================================================
=========================================================
'''


@app.route('/api/p/<id>', methods=['GET', 'POST'])
def product_api(id):
    product = Product.query.get_or_404(id)
    p = {"id": product.id, "title": product.title, "category": product.category, "passes": product.passes, "fails": product.fails,
         "review_count": product.review_count, "pub_date": product.pub_date, "added_by": product.owner_id, "image": "static/uploads/" + product.image,
         "video": product.video, "views": product.views, "address": product.address}
    r = [{"review": review.review_text,
          "author_id": review.user.id,
          "author_username": review.user.nickname,
          "pud_date": review.pub_date,
          "id": review.id}
         for review in product.reviews.all()]
    return jsonify(p, reviews=r)


@app.route('/api/listing/', methods=['GET'])
def products_api():
    products = Product.query.order_by(Product.pub_date.desc()).all()
    resp = []
    for product in products:
        p = {"id": product.id, "title": product.title, "category": product.category, "passes": product.passes, "fails": product.fails,
             "review_count": product.review_count, "pub_date": product.pub_date, "added_by": product.owner_id, "image": product.image,
             "video": product.video, "views": product.views}
        resp.append(p)

    return jsonify(products=resp)
