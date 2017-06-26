1#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from flask import Flask, render_template, request, redirect, Response, url_for, session
# from flask.ext.sqlalchemy import SQLAlchemy
import logging, pprint
from logging import Formatter, FileHandler
from forms import *
import os, time, copy, math, json, re
from api.blog import fetch_posts, get_post
from lib.format import post_format_date
import shop_data
from functools import wraps


#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
app.config.from_object('config')
app.secret_key = os.environ["BLUESHIFTAPP_SESSION_SIGNING_KEY"]

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
# Context Processors (for setting global template variables)
#----------------------------------------------------------------------------#

@app.context_processor
def inject_class_categories():
    class_categories = []
    categories = shop_data.get_categories()
    for category in categories:
        if (category["parent"] == 0 or category["parent"] is None) and (category["name"].lower() != "filters"):
            class_categories.append({"name": category["name"], "url": "/classes/"+category["name"]})
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

@app.route('/who_we_are')
def testimonials():
    return render_template('pages/who_we_are.html')

@app.route('/schools')
def schools():
    return render_template('pages/schools.html')

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

# This can be used for logging debug to Heroku logs (or to console, in dev)
def log_to_stdout(log_message):
    ch = logging.StreamHandler()
    app.logger.addHandler(ch)
    app.logger.info(log_message)

@app.route('/cart', methods=['GET', 'POST'])
def cart():

    # Extract input from post-data
    product_id = None if "product_id" not in request.form else request.form["product_id"]
    quantity = None if "quantity" not in request.form else request.form["quantity"]

    # Update basket if necessary
    if product_id is not None:

        product = shop_data.get_product(id=product_id)
        if product is None:

            # TODO:WV:20170626:User-friendly error here
            raise Exception("Product not found")

        if quantity is None or not rgx_matches("^[+\-]?[0-9]+$", quantity):

            # TODO:WV:20170626:User-friendly error here
            raise Exception("Invalid quantity")

        # Upadte basket in the session
        if "basket" not in session:
            session["basket"] = {}
        old_quantity = 0 if product_id not in session["basket"] else session["basket"][product_id]
        operator = quantity[0:1]
        if operator == "+":
            new_quantity = old_quantity + int(quantity[1])
        elif operator == "-":
            new_quantity = old_quantity - int(quantity[1])
        else:
            new_quantity = int(quantity)
        if new_quantity <= 0:
            session["basket"].pop(product_id, None)
        else:
            session["basket"][product_id] = new_quantity

    # Generate full basket, with product data etc, and output to the user
    full_basket = {}
    if "basket" in session:
        for item in session["basket"]:
            full_basket[item] = {
                "product": shop_data.get_product(id=product_id),
                "quantity": session["basket"][product_id]
            }

    return render_template(
        "pages/basket.html",
        basket=full_basket
    )

@app.route('/class/<slug>')
def singleclass(slug):
    product = shop_data.get_product(slug=slug)

    return render_template(
        'pages/single_class.html',
        product=product
    )

    return product


@app.route('/classes/', defaults={"url_category": None})
@app.route('/classes/<url_category>')
def classes(url_category):

    # Add filter drop-downs, with options
    # TODO:WV:20170626:Add Wordpress plugin to prevent editing the FILTERS category name or adding any others called FILTERS at the same level in the category hierarchy
    filters_category = shop_data.get_category("FILTERS")
    filter_category_ids = {}
    if filters_category is None:
        filters = []
    else:
        filters = []

        categories = shop_data.get_categories()
        for category in categories:
            if category["parent"] == filters_category["id"]:
                filter_category_ids[category["name"].lower()] = category["id"]
                filters.append({"category": category, "child_categories": []})

        # Find filter options
        for class_filter in filters:
            for category in categories:
                if category["parent"] == class_filter["category"]["id"]:
                    class_filter["child_categories"].append(category)

    # Compile list of categories to restrict products by
    active_categories = []
    if url_category is not None:
        active_categories.append(shop_data.get_category(url_category))
    for arg in request.args:
        if request.args[arg] and arg in filter_category_ids:
            filter_category = shop_data.get_category(request.args[arg], parent_id=filter_category_ids[arg])
            if filter_category is not None:
                active_categories.append(filter_category)

    # Find page number from query string - default to 1
    if "page_num" in request.args and rgx_matches("^[0-9]+$", request.args["page_num"]):
        page_num = int(request.args["page_num"])
    else:
        page_num = 1

    # Fetch list of products and generate page
    per_page = 10
    products = shop_data.get_products(active_categories, page_num, per_page)

    return render_template(
        'pages/classes.html',
        products=products["products"],
        class_filters=filters,
        dates=filters["Dates"] if "Dates" in filters else [],
        ages=filters["Age range"] if "Age range" in filters else [],
        pagination_data={
            "page_num":page_num,
            "total_pages":int(math.ceil(products["num_total"] / float(per_page))),
            "route_function": {
                "name": "classes",
                "arguments": {
                    "url_category":url_category,
                    "dates":None if "dates" not in request.args else request.args["dates"],
                    "ages":None if "ages" not in request.args else request.args["ages"]
                }
            }
        },
    )


# Error handlers.

def rgx_matches(rgx, string):
    matches = re.search(rgx, string)
    return matches is not None

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
