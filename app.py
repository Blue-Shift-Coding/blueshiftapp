1#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from flask import Flask, render_template, request, redirect, Response, url_for
# from flask.ext.sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from forms import *
import os, time, copy, math, json
from api.blog import fetch_posts, get_post
from lib.format import post_format_date
import infusionsoftapi, shop_data, storage
from functools import wraps


#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
app.config.from_object('config')
#db = SQLAlchemy(app)

# Automatically tear down SQLAlchemy.
'''
@app.teardown_request
def shutdown_session(exception=None):
    db_session.remove()
'''

# Login required decorator.
'''
def login_required(test):
    @wraps(test)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return test(*args, **kwargs)
        else:
            flash('You need to login first.')
            return redirect(url_for('login'))
    return wrap
'''

#----------------------------------------------------------------------------#
# Basic Auth decorator
#----------------------------------------------------------------------------#

def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """

    if not ('BLUESHIFTAPP_ADMIN_USER' in os.environ and 'BLUESHIFTAPP_ADMIN_PASSWORD' in os.environ):
        raise LookupError("Admin credentials not found in environment")

    return username == os.environ['BLUESHIFTAPP_ADMIN_USER'] and password == os.environ['BLUESHIFTAPP_ADMIN_PASSWORD']

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


#----------------------------------------------------------------------------#
# Context Processors (for setting global template variables)
#----------------------------------------------------------------------------#

@app.context_processor
def inject_class_categories():

    # Add categories to the page, for the main nav menu
    categories = shop_data.cache.get_categories()
    class_categories = []
    for category_index in categories:
        category = categories[category_index]
        if category["category"]["name"] not in infusionsoftapi.categories_for_filtering and category["category"]["name"] not in infusionsoftapi.categories_for_metadata:
            class_categories.append({"name": category["category"]["name"], "url": "/classes/"+category["category"]["name"]})
    class_categories.append({"name": "Browse all", "url": "/classes"})

    return dict(class_categories=class_categories)

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def home():
    return render_template('pages/home.html')


@app.route('/about/')
def about():
    return render_template('pages/about.html')

@app.route('/mission')
def mission():
    return render_template('pages/mission.html')

@app.route('/story/')
def story():
    return render_template('pages/story.html')

@app.route('/team')
def team():
    return render_template('pages/team.html')

@app.route('/teachers/')
def teachers():
    return render_template('pages/teachers.html')

@app.route('/testimonials')
def testimonials():
    return render_template('pages/testimonials.html')

@app.route('/curriculum/')
def curriculum():
    return render_template('pages/curriculum.html')

@app.route('/faq/')
def faq():
    return render_template('pages/faq.html')

@app.route('/news/')
@app.route('/news/<int:page_num>/')
def news(page_num=1):
    posts, total_pages = fetch_posts(page_num)

    if page_num < 1:
        return abort(404)

    if page_num > total_pages:
        return abort(404)

    return render_template(
        'pages/news.html',
        data=posts,
        pagination_data={
            "page_num":page_num,
            "total_pages":total_pages,
            "route_function":{
                "name":"news"
            }
        },
        format_date=post_format_date
    )

@app.route('/post/<int:post_id>/<slug>/')
def post(post_id, slug):
    post = get_post(post_id)

    return render_template(
        'pages/post.html', post=post, post_id=post_id, format_date=post_format_date)


@app.route('/login/')
def login():
    form = LoginForm(request.form)
    return render_template('forms/login.html', form=form)


@app.route('/register/')
def register():
    form = RegisterForm(request.form)
    return render_template('forms/register.html', form=form)


@app.route('/forgot/')
def forgot():
    form = ForgotForm(request.form)
    return render_template('forms/forgot.html', form=form)

# TODO:WV:20170526:How to prevent third parties maliciously requesting this.  Can we restrict to Infusionsoft IPs?
@app.route('/re-sync')
def re_sync():

    log_to_stdout("Headers")
    log_to_stdout(request.headers)

    # If this request is Infusionsoft checking that the URL works, just ping back their hook-secret in a header
    header_name = "X-Hook-Secret"
    secret = request.headers.get(header_name)
    if secret:
        resp = flask.Response("")
        resp.headers[header_name] = secret
        return resp

    # Otherwise, queue a re-sync
    storage.set(shop_data.cache.queue_key, 1)
    return "Done"

def log_to_stdout(log_message):
    ch = logging.StreamHandler()
    app.logger.addHandler(ch)
    app.logger.info("Request Headers")
    app.logger.info(request.headers)

@app.route('/set-up-infusionsoft-callback-hooks')
@requires_auth
def set_up_infusionsoft_callback_hooks():
    log_to_stdout("Test")
    infusionsoftapi.refresh_access_token_data_if_necessary()
    if not infusionsoftapi.have_access_token():
        return "No access token - please visit /api-authenciate to enable the Infusionsoft API"

    callback_url = url_for("re_sync", _external=True, _scheme='https')
    event_keys = ["product.add", "product.delete", "product.edit"]
    for event_key in event_keys:
        infusionsoftapi.update_hook(event_key, callback_url)

    return "Done"

@app.route('/api-authenticate/')
@requires_auth
def api_authenticate():

    # If at stage 2, there should be a 'code' in the URL.  Extract it here; if absent, assume at stage 1.
    code = request.args.get("code")

    # Stage 1 - get permission to get an access token
    if not code:
        url = infusionsoftapi.get_authorization_url(request.base_url)
        return redirect(url, code=302)

    # Stage 2 - get and save the access token
    infusionsoftapi.download_initial_access_token_data(code=code, redirect_uri=request.base_url)
    return redirect("/api-authenticate-done", code=302)

@app.route('/api-authenticate-done/')
def api_authenticate_done():
    return "Done"

# TODO:WV:20170515:Refactorthe produts storage mechanism so that it could cope with a large database
# TODO:WV:20170515:(Perhaps - in memcached, one document per product, and one document with all the searching data in, or one document with a list of product IDs for every possible search)
@app.route('/classes/', defaults={"url_category": None, "dates": None, "ages": None, "page_num": 1})
@app.route('/classes/<int:page_num>', defaults={"url_category": None, "dates": None, "ages": None})
@app.route('/classes/<url_category>', defaults={"dates": None, "ages": None, "page_num": 1})
@app.route('/classes/<url_category>/<page_num>', defaults={"dates": None, "ages": None})
@app.route('/classes/<url_category>/<dates>', defaults={"ages": None, "page_num": 1})
@app.route('/classes/<url_category>/<dates>/<page_num>', defaults={"ages": None})
@app.route('/classes/<url_category>//<ages>', defaults={"dates": None, "page_num": 1})
@app.route('/classes/<url_category>//<ages>/<page_num>', defaults={"dates": None})
@app.route('/classes/<url_category>/<dates>/<ages>', defaults={"page_num": 1})
@app.route('/classes/<url_category>/<dates>/<ages>/<page_num>', defaults={})
@app.route('/classes//<dates>', defaults={"url_category": None, "ages": None, "page_num": 1})
@app.route('/classes//<dates>/<page_num>', defaults={"url_category": None, "ages": None})
@app.route('/classes///<ages>', defaults={"url_category": None, "dates": None, "page_num": 1})
@app.route('/classes///<ages>/<page_num>', defaults={"url_category": None, "dates": None})
@app.route('/classes//<dates>/<ages>', defaults={"url_category": None, "page_num": 1})
@app.route('/classes//<dates>/<ages>/<page_num>', defaults={"url_category": None})
def classes(url_category, dates, ages, page_num):
    products = shop_data.cache.get_products()

    # Get options for the filter-drop-downs
    categories = shop_data.cache.get_categories()
    filters = copy.deepcopy(infusionsoftapi.categories_for_filtering)
    for filter_category_name in filters:
        for category_index in categories:
            category = categories[category_index]
            if category["category"]["name"] == filter_category_name and len(category["children"]) != 0:
                for child_category in category["children"]:
                    filters[filter_category_name].append(child_category["name"])

    # Finds a category based on its name, and optionally its parent category
    def get_category(category_parent, category_child=None):
        for category_index in categories:
            category = categories[category_index]
            if category["category"]["name"] == category_parent:
                if category_child is None:
                    return category["category"]
                else:
                    for child_category in category["children"]:
                        if child_category["name"] == category_child:
                            return child_category
        return None

    # Returns a function to filter products by any category
    def get_filter_function(filter_category_parent, filter_category=None):

        # Find category id to filter by
        # NB not passed in URL for SEO reasons
        category = get_category(filter_category_parent, filter_category)
        category_id = None if category is None else category["id"]

        def filter_function(product):
            return category_id is not None and category_id in product["categories"]

        return filter_function

    # Filter products by category if a category was provided in the URL
    if url_category is not None and url_category not in infusionsoftapi.categories_for_filtering:
        products = filter(get_filter_function(url_category), products)

    # Filter products by date if a date was provided in the URL
    if dates is not None:
        products = filter(get_filter_function("Dates", dates), products)

    # Filter products by age if an age range was provided in the URL
    if ages is not None:
        products = filter(get_filter_function("Age range", ages), products)

    # Get pagination data for template
    per_page = 10
    total_pages = int(math.ceil(float(len(products)) / float(per_page)))

    # Filter products to the current page
    # NB has to happen AFTER working out total_pages, because it changes 'products', which is also used to calculate total_pages
    offset = per_page * (page_num - 1)
    products = products[offset:offset + per_page]

    return render_template(
        'pages/classes.html',
        products=products,
        dates=filters["Dates"],
        ages=filters["Age range"],
        pagination_data={
            "page_num":page_num,
            "total_pages":total_pages,
            "route_function": {
                "name": "classes",
                "arguments": {
                    "url_category":url_category,
                    "dates":dates,
                    "ages":ages
                }
            }
        },
    )


# Error handlers.


@app.errorhandler(500)
def internal_error(error):
    #db_session.rollback()
    return render_template('errors/500.html'), 500


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
