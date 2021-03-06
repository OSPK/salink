import datetime
import random
import urllib2
from flask import redirect, url_for, render_template, flash, request, json,\
    jsonify, Response, escape, abort
from app import app, login_manager, db, limiter, mail
from flask.ext.assets import Environment, Bundle
from flask.ext.login import login_user, logout_user, current_user
from pf_oauth import OAuthSignIn
from models import User, Product, Review
# WTF FORMS
from flask_wtf import Form
from wtforms import StringField, PasswordField, HiddenField, SubmitField, SelectField, BooleanField
from wtforms.widgets import TextArea
from wtforms.validators import DataRequired, Length, ValidationError,\
    InputRequired, Email
from wtforms.fields.html5 import EmailField
from werkzeug import secure_filename, url_decode
from flask_wtf.file import FileField, FileAllowed, FileRequired
from ago import human
import opengraph
from sqlalchemy.orm import load_only
from flask.ext.mail import Message

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

# all categories
CATEGORIES = [('Architecture', 'Architecture'), ('Carpet', 'Carpet'), ('Grocery Store', 'Grocery Store'), ('Real Estate - Realtor - Mortgage', 'Real Estate - Realtor - Mortgage'), ('Printing', 'Printing'), ('Auto Mechanic - Buying - Selling', 'Auto Mechanic - Buying - Selling'), ('Woodworking', 'Woodworking'), ('School', 'School'), ('Draperies - Curtains', 'Draperies - Curtains'), ('Newspaper', 'Newspaper'), ('Insurance', 'Insurance'), ('Restaurant - Sweet Shop', 'Restaurant - Sweet Shop'), ('Bank - Money', 'Bank - Money'), ('Remittance', 'Remittance'), ('Glass', 'Glass'), ('Worship Places', 'Worship Places'), ('Accountant', 'Accountant'), ('Traveling Agency', 'Traveling Agency'), ('Construction', 'Construction'), ('Clinic - Pharmacy', 'Clinic - Pharmacy'), ('Boutique - Clothing', 'Boutique - Clothing'), ('Jewelers', 'Jewelers'), ('Painting', 'Painting'), ('Optics - Glasses', 'Optics - Glasses'), ('Electronic', 'Electronic'), ('Furniture', 'Furniture'), ('Moving Companies', 'Moving Companies'), ('Stationary', 'Stationary'), ('Others', 'Others')]

# sudo apt-get install libjpeg-dev
# thumbs

login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


# Forms
class AddProduct(Form):
    title = StringField('Business Name', validators=[DataRequired("Title is required"), Length(message="Title must be 1 to 70 characters long", min=1, max=70)])
    category = SelectField('Category', choices=CATEGORIES, validators=[DataRequired("Category is required")])
    address = StringField('Address', validators=[Length(message="address cannot be longer than 500 characters", min=0, max=500)], widget=TextArea())
    phone = StringField('Phone Number', validators=[DataRequired("Phone Numeber is required"), Length(message="Phone Number must be 5 to 70 characters long", min=5, max=70)])
    image = FileField('Featued Image', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Images only!')])
    image2 = FileField('Image 2', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Images only!')])
    image3 = FileField('Image 3', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Images only!')])
    image4 = FileField('Image 4', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Images only!')])
    video = StringField('Video URL')
    contact_name = StringField('Contact person name')
    services = StringField('Services')
    cell_number = StringField('Cell Number')
    fax_number = StringField('Fax Number')
    website = StringField('Website')
    email = StringField('Email')
    location = StringField('Location')
    featured = BooleanField('Featured Listing')


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


def is_authorised(product):
    if current_user.is_authenticated():
        if current_user.id == product.owner_id:
            return True
        if current_user.id == 1:
            return True
    else:
        return False


def is_admin():
    if current_user.id in [1]:
        return True
    else:
        return False


def ago_format(date):
    return human(date, precision=1, past_tense='{} ago', future_tense='in {}')


def top_categories():
    list = []
    for category in CATEGORIES:
        list.append(category[0])
    return sorted(list)


def site_url():
    return 'http://southasianlink.ca/'


def video_stuff(vid_data):
    video_url = vid_data

    if not video_url.startswith('http://'):
        if not video_url.startswith('https://'):
            video_url = "http://" + video_url
    sites_allowed = ['dailymotion', 'youtube', 'tune.pk', 'playit.pk', 'vine.co', 'vimeo.com', 'soundcloud.com']

    # check if from sites_allowed
    if not any(site in video_url for site in sites_allowed):
        flash("Not a valid video URL", 'danger')
        return "Invalid video"

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
            return redirect(url_for('addproduct'))

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

    v = {}
    v['vid'] = vid
    v['imagename'] = imagename
    print v
    return v


def featured():
    producs = Product.query.filter(Product.featured == True).all()
    return producs


app.jinja_env.globals.update(ago_format=ago_format, featured=featured, top_categories=top_categories, site_url=site_url, is_authorised=is_authorised, is_admin=is_admin)


# ------------------ ROUTES ---------------------------------------


@app.route('/')
def index():
    this_month = datetime.date.today() - datetime.timedelta(days=131)
    products = Product.query.filter(Product.pub_date > this_month, Product.status == 'publish').order_by(Product.views.desc()).paginate(1, 9, False)

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
    products = Product.query.filter(Product.status == 'publish').order_by(Product.pub_date.desc()).paginate(page, POSTS_PER_PAGE, False)

    if view == 'trending':
        this_week = datetime.date.today() - datetime.timedelta(days=7)
        products = Product.query.filter(Product.pub_date > this_week, Product.status == 'publish').order_by(Product.views.desc()).paginate(page, POSTS_PER_PAGE, False)
    if view == 'most-viewed':
        products = Product.query.filter(Product.status == 'publish').order_by(Product.views.desc()).paginate(page, POSTS_PER_PAGE, False)
    if view == 'most-reviewed':
        products = Product.query.filter(Product.status == 'publish').order_by(Product.review_count.desc()).paginate(page, POSTS_PER_PAGE, False)

    return render_template('products.html', products=products, view=view)


@app.route('/category/<category>/')
@app.route('/category/<category>/<view>')
@app.route('/category/<category>/<view>/<int:page>/')
def category(page=1, category=None, view='latest'):
    if category is None:
        return redirect(url_for('products'))

    products = Product.query.filter(Product.category == category, Product.status == 'publish').order_by(Product.pub_date.desc()).paginate(page, POSTS_PER_PAGE, False)

    if view == 'trending':
        this_week = datetime.date.today() - datetime.timedelta(days=7)
        products = Product.query.filter(Product.pub_date > this_week, Product.category == category, Product.status == 'publish').order_by(Product.views.desc()).paginate(page, POSTS_PER_PAGE, False)
    if view == 'most-viewed':
        products = Product.query.filter(Product.category == category, Product.status == 'publish').order_by(Product.views.desc()).paginate(page, POSTS_PER_PAGE, False)
    if view == 'most-reviewed':
        products = Product.query.filter(Product.category == category, Product.status == 'publish').order_by(Product.review_count.desc()).paginate(page, POSTS_PER_PAGE, False)

    return render_template('category.html', products=products, category=category, view=view)


@app.route('/pending/')
@app.route('/pending/<int:page>/')
def pending(page=1):
    if is_admin():
        products = Product.query.filter(Product.status == 'pending').order_by(Product.pub_date.desc()).paginate(page, POSTS_PER_PAGE, False)
        return render_template('products.html', products=products, view='pending')
    else:
        return redirect(url_for('index'))


@app.route('/approve/<int:id>/', methods=['POST'])
def approve(id):
    if is_admin:
        product = Product.query.get_or_404(id)
        product.status = "publish"
        db.session.commit()
        flash('Approved product', 'success')

    return redirect(url_for('pending'))


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
    products = Product.query.options(load_only("title", "id")).filter(Product.title.startswith(search), Product.status == 'publish').limit(5).all()
    products2 = Product.query.options(load_only("title", "id")).filter(Product.title.contains('%' + search + '%'), Product.status == 'publish').limit(5).all()
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
    form = AddProduct()

    if not current_user.is_authenticated():
        return redirect(url_for('login'))

    if request.method == 'GET':
        return render_template('new.html', form=form)

    if form.validate_on_submit() and current_user.is_authenticated():
        title = form.title.data
        address = form.address.data
        phone = form.phone.data
        category = form.category.data
        pub_date = datetime.datetime.now()
        contact_name = form.contact_name.data
        services = form.services.data
        cell_number = form.cell_number.data
        fax_number = form.fax_number.data
        website = form.website.data
        email = form.email.data
        location = form.location.data
        imagename = None
        image2name = None
        image3name = None
        image4name = None
        vid = None
        if form.image.data:
            imagename = unicode(random.randint(9000, 10000)) + '-southasianlink-' + secure_filename(form.image.data.filename)
            form.image.data.save('app/static/uploads/' + imagename)                                 # save this

        if form.image2.data:
            image2name = unicode(random.randint(9000, 10000)) + '-southasianlink-' + secure_filename(form.image2.data.filename)
            form.image2.data.save('app/static/uploads/' + image2name)                                 # save this

        if form.image3.data:
            image3name = unicode(random.randint(9000, 10000)) + '-southasianlink-' + secure_filename(form.image3.data.filename)
            form.image3.data.save('app/static/uploads/' + image3name)                                 # save this

        if form.image4.data:
            image4name = unicode(random.randint(9000, 10000)) + '-southasianlink-' + secure_filename(form.image4.data.filename)
            form.image4.data.save('app/static/uploads/' + image4name)                                 # save this

        if form.video.data:
            v = video_stuff(form.video.data)
            vid = v['vid']
            imagename = v['imagename']

        product = Product(title=title, pub_date=pub_date, contact_name=contact_name, services=services,
                          cell_number=cell_number, fax_number=fax_number, website=website, email=email,
                          location=location, category=category, owner_id=current_user.id, image=imagename,
                          image2=image2name, image3=image3name, image4=image4name, video=vid, address=address,
                          phone=phone, status='pending')

        db.session.add(product)
        db.session.commit()
        msg = Message("Product added | Pending", sender="support@southasianlink.ca", recipients=["southasianlinks@gmail.com"])
        msg.html = """
        <h1>A new product has been added</h1>
        <h2 style='color:#4070A0;'>{}</h2>
        <h3>It is pending your approval</h3>
        <p>To approve go to <a href="http://southasianlink.ca/pending">http://southasianlink.ca/pending</a></p>
        """.format(title)
        mail.send(msg)

        flash('Added successfully', 'success')

        return redirect(url_for('product', id=product.id))

    elif current_user.is_authenticated():
        flash_errors(form, 'danger')
        return render_template('new.html', form=form)


@app.route('/p/<id>', methods=['GET'])
def product(id):
    product = Product.query.get_or_404(id)
    category = product.category
    xposts = Product.query.options(load_only("id")).filter(Product.id < id, Product.category == category, Product.status == 'publish').order_by(Product.pub_date.desc()).limit(7).all()
    prod_next = Product.query.options(load_only("id")).filter(Product.id < id, Product.category == category, Product.status == 'publish').order_by(Product.pub_date.desc()).limit(1).first()  # Product.query.get(next_id)
    prod_prev = Product.query.options(load_only("id")).filter(Product.id > id, Product.category == category, Product.status == 'publish').order_by(Product.pub_date.desc()).limit(1).first()
    reviews = product.reviews.all()
    reviewform = AddReview()

    if request.method == 'GET':
        if product.views is not None:
            product.views += 1
            db.session.commit()
        else:
            product.views = 1
            db.session.commit()

    return render_template('product.html', product=product, reviewform=reviewform, reviews=reviews, prod_next=prod_next, prod_prev=prod_prev, xposts=xposts)


@app.route('/p/<id>/edit', methods=['GET', 'POST'])
def edit_product(id):
    product = Product.query.get_or_404(id)
    form = AddProduct()

    if request.method == 'POST':
        if form.validate_on_submit() and is_authorised(product):
            title = form.title.data
            address = form.address.data
            phone = form.phone.data
            category = form.category.data
            pub_date = datetime.datetime.now()
            contact_name = form.contact_name.data
            services = form.services.data
            cell_number = form.cell_number.data
            fax_number = form.fax_number.data
            website = form.website.data
            email = form.email.data
            location = form.location.data
            imagename = product.image
            image2name = product.image2
            image3name = product.image3
            image4name = product.image4
            vid = product.video
            featured = form.featured.data

            if form.image.data:
                imagename = unicode(random.randint(9000, 10000)) + '-southasianlink-' + secure_filename(form.image.data.filename)
                form.image.data.save('app/static/uploads/' + imagename)                                 # save this

            if form.image2.data:
                image2name = unicode(random.randint(9000, 10000)) + '-southasianlink-' + secure_filename(form.image2.data.filename)
                form.image2.data.save('app/static/uploads/' + image2name)                                 # save this

            if form.image3.data:
                image3name = unicode(random.randint(9000, 10000)) + '-southasianlink-' + secure_filename(form.image3.data.filename)
                form.image3.data.save('app/static/uploads/' + image3name)                                 # save this

            if form.image4.data:
                image4name = unicode(random.randint(9000, 10000)) + '-southasianlink-' + secure_filename(form.image4.data.filename)
                form.image4.data.save('app/static/uploads/' + image4name)                                 # save this

            if form.video.data:
                v = video_stuff(form.video.data)
                vid = v['vid']
                imagename = v['imagename']

            product.title = title
            product.pub_date = pub_date
            product.contact_name = contact_name
            product.services = services
            product.cell_number = cell_number
            product.fax_number = fax_number
            product.website = website
            product.email = email
            product.location = location
            product.category = category
            product.owner_id = current_user.id
            product.image = imagename
            product.image2 = image2name
            product.image3 = image3name
            product.image4 = image4name
            product.video = vid
            product.address = address
            product.phone = phone
            if is_admin():
                product.featured = featured

            db.session.commit()

            flash('Added successfully', 'success')

            return redirect(url_for('product', id=product.id))

    return render_template('edit.html', product=product, form=form)


@app.route('/p/<id>/review/', methods=['POST'])
@limiter.limit("12/minute")
@limiter.limit("1/second")
def product_post_review(id):
    product_id = id
    reviewform = AddReview()

    if not current_user.is_authenticated():
        abort(401)

    if current_user.is_authenticated():
        author_id = current_user.id
        pub_date = datetime.datetime.now()

        if reviewform.validate_on_submit():
            review_text = unicode(reviewform.review_text.data)
            review = Review(product_id=product_id, author_id=author_id, pub_date=pub_date, review_text=review_text)
            db.session.add(review)
            db.session.commit()
            if review.product.review_count is None:
                review.product.review_count = 1
            else:
                review.product.review_count += 1
            db.session.commit()
            resp = {'user': current_user.nickname, 'review': escape(review_text), 'reviewid': review.id}
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
    if is_authorised(product):
        db.session.delete(product)
        db.session.commit()
        flash(title, "danger")
    return redirect(url_for('index'))


@app.route('/r/<id>/delete', methods=['POST'])
def delete_review(id):
    review = Review.query.filter(Review.id == id).first()
    product_id = review.product_id
    if current_user.is_authenticated() and current_user.id == review.author_id:
        review.product.review_count -= 1
        db.session.delete(review)
        db.session.commit()
        resp = {}
        # flash("Review deleted", "danger")
        return jsonify(resp)

# ============================ /Deleting Stuff ===============================

# ============================ Pages ===============================


@app.route('/legal/<page>/')
def page(page):
    return render_template('legal.html', page=page)


@app.route('/about/')
def about():
    return render_template('about.html')


@app.route('/tariff/')
def tariff():
    return render_template('tariff.html')


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
