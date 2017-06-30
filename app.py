# coding: utf-8

#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from flask import Flask, render_template, request, redirect, Response, url_for, session
import wtforms
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
# Custom template filters.
#----------------------------------------------------------------------------#

@app.template_filter('currency')
def format_currency(value):
    return u"£{:,.2f}".format(value)


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

def uniqid(prefix = ''):
    return prefix + hex(int(time()))[2:10] + hex(int(time()*1000000) % 0x100000)[2:7]

# TODO:WV:20170630:Should be in a separate file?
class BookingInformationForm(wtforms.Form):
    def __init__(self, gravity_forms_data):
        self.fields = []
        for gf_field in gravity_forms_data["fields"]:
            if not "inputType" in gf_field:

                # TODO:WV:20170630:This could be a 'section' in which case a gravity-forms fieldList or other fieldEnclosure may be appropriaite
                # TODO:WV:20170630:See http://wtforms.simplecodes.com/docs/0.6/fields.html.  Otherwise find (or create) a field type that simply outputs the label and description.
                continue
            if gf_field["inputType"] == "radio":
                choices = []
                for gf_choice in gf_field["choices"]:
                    choices.append((gf_choice["value"], gf_choice["text"]+(" ("+gf_choice["price"]+")" if "price" in gf_choice else "")))
                self.fields.append(wtforms.RadioField(gf_field["label"]), choices=choices)

            # Assume text field if no 'inputType' (a lot of the text fields seem to have an empty string in the inputType)
            else:
                self.fields.append(wtforms.StringField())


@app.route('/cart', methods=['GET', 'POST'])
def cart():

    # Extract input from post-data
    product_id = None if "product_id" not in request.form else request.form["product_id"]
    delete_item_id = None if "delete_item_id" not in request.form else request.form["delete_item_id"]

    # Initialise basket in session if necessary
    if "basket" not in session:
        session["basket"] = {}

    # If adding a product, either add it to the basket, or find the relevant form fields for adding to the template
    # TODO:WV:20170630:Session size of ~4k might be too small.  Consider saving the form data to the server, perhaps via the GravityForms API,
    # to keep session size down.
    form = None
    did_change_session = False
    if product_id is not None:

        product = shop_data.get_product(id=product_id)
        if product is None:
            return redirect(url_for('cart'))

        booking_information = None if "booking_information" not in request.form else request.form["booking_information"]

        # If no booking info provided, get form for inclusion in the page
        # TODO:WV:20170630:Add "attendee's name" field by default, for inclusion in the basket row
        if booking_information is None:
            form_id = None
            for meta_datum in product["meta_data"]:
                if meta_datum["key"] == "_gravity_form_data":
                    form_id = meta_datum["value"]["id"]
                    break
            if form_id is not None:
                form = BookingInformationForm(shop_data.get_form(form_id))
        else:
            # TODO:WV:20170630:Validate booking information

            # Update basket in the session
            session["basket"][uniqid()] = {
                "product_id": product_id,
                "booking_information": booking_information
            }
            did_change_session = True

    # If removing an item, do so
    if delete_item_id is not None:
        if delete_item_id in session["basket"]:
            del session["basket"][delete_item_id]
        did_change_session = True

    # Prevent form re-submit issue
    if did_change_session:
        return redirect(url_for('cart'))

    # Get full data on all products in the basket
    products = {}
    for uniqid in session["basket"]:
        products[session["basket"]["product_id"]] = shop_data.get_product(id=session["basket"]["product_id"])

    return render_template(
        "pages/basket.html",
        basket=session["basket"],
        products=products,
        form=form
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
