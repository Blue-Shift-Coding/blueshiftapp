# coding: utf-8

#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

# Flask modules
from flask import Flask, render_template, request, redirect, Response, url_for, session, flash
import wtforms
from forms import *

# Core modules
import os, time, copy, math, json, re
import logging, pprint
from logging import Formatter, FileHandler

# Internal modules
from api.blog import fetch_posts, get_post
import shop_data, storage
from functools import wraps
from woocommerceapi import wcapi
from gravityformsapi import gf

# Third party libraries
# TODO:WV:20170706:Confirm where lib.format came from
import stripe
from lib.format import post_format_date


#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
app.config.from_object('config')
app.secret_key = os.environ["BLUESHIFTAPP_SESSION_SIGNING_KEY"]
stripe_keys = {
    "secret": os.environ["BLUESHIFTAPP_STRIPE_SECRET_KEY"],
    "publishable": os.environ["BLUESHIFTAPP_STRIPE_PUBLISHABLE_KEY"]
}
stripe.api_key = stripe_keys["secret"]

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

@app.context_processor
def inject_shopping_basket_item_count():
    return dict(shopping_basket_item_count=0 if "basket" not in session else len(session["basket"]))


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


# TODO:WV:20170704:Could set up an unpaid order before payment
@app.route('/processpayment', methods=['POST'])
def processpayment():

    if not "basket" in session:
        return redirect(url_for("classes"))

    # Build list of line items for Woocommerce order
    line_items = []
    for item_id in session["basket"]:

        # TODO:WV:20170704:Handle bad response
        gravity_forms_entry = gf.get_entry(session["basket"][item_id]["gravity_forms_entry"])

        # TODO:WV:20170704:Handle form not found (for some reason), by downloading from the API, and handle any subsequent bad response
        gravity_forms_form = shop_data.get_form(gravity_forms_entry["form_id"])

        list_item_meta_data = []
        gravity_forms_lead = {}
        def add_field(field):
            field_key = str(field["id"])
            gravity_forms_lead[field_key] = gravity_forms_entry[field_key]
            list_item_meta_data.append({
                "key": field["label"],
                "value": gravity_forms_entry[field_key]
            })
        for field in gravity_forms_form["fields"]:
            if field["type"] == "name":
                for sub_field in field["inputs"]:
                    add_field(sub_field)

            if str(field["id"]) in gravity_forms_entry:
                add_field(field)

        list_item_meta_data.append({
            "key": "_gravity_forms_history",
            "value": {
                "_gravity_form_data": {"id": gravity_forms_entry["form_id"]},
                "_gravity_form_lead": gravity_forms_lead
            },
        })

        line_items.append({
            "product_id": session["basket"][item_id]["product_id"],
            "quantity": 1,
            "meta_data": list_item_meta_data
        })

    # Put charge through via Stripe
    basket_data = get_all_basket_data()
    amount = int(float(basket_data["total_price"]) * 100)

    # Set up basic data for Stripe charge
    stripe_charge_data = {
        "source":request.form["stripeToken"],
        "amount":amount,
        "currency":"gbp",
        "description":"Flask Charge"
    }

    # If customer email was provided, add a receipt email to the order
    stripe_info = stripe.Token.retrieve(request.form["stripeToken"])
    customer_email = stripe_info["email"]
    if customer_email:
        stripe_charge_data.update({
            "receipt_email":customer_email
        })

    charge = stripe.Charge.create(**stripe_charge_data)

    # Submit order to WooCommerce API
    # TODO:WV:20170704:Can include shipping data, etc. from stripe if available
    # TODO:WV:20170704:Handle bad response
    response = wcapi.post("orders", {
        "payment_method": "stripe",
        "payment_method_title": "Stripe",
        "set_paid": True,
        "line_items": line_items
    })

    # Empty the basket
    del session["basket"]

    # TODO:WV:20170706:Format this in the template
    flash("Order complete", "done")

    return redirect(url_for("classes"))

def get_all_basket_data():
    if "basket" not in session:
        return {}

    # Get full data on all products in the basket
    # TODO:WV:20170706:Add prices onto each item based on form options
    products = {}
    total_price = 0;
    for item_id in session["basket"]:
        product = shop_data.get_product(id=session["basket"][item_id]["product_id"])
        products[session["basket"][item_id]["product_id"]] = product
        total_price += float(product["price"])

    return {
        "products": products,
        "total_price": total_price
    }

@app.route('/cart', methods=['GET', 'POST'])
def cart():

    # Extract input from post-data
    product_id = None if "product_id" not in request.form else request.form["product_id"]
    delete_item_id = None if "delete_item_id" not in request.form else request.form["delete_item_id"]

    # Initialise basket in session if necessary
    if "basket" not in session:
        session["basket"] = {}

    # Prepare data to go into the session after this process has finished (it may be added to later in this function)
    data_for_session = {
        "unique_id": uniqid(),
        "product_id": product_id
    }

    # If adding a product, either add it to the basket, or find the relevant form fields for adding to the template
    # TODO:WV:20170630:Session size of ~4k might be too small.  Consider saving the form data to the server, perhaps via the GravityForms API,
    # to keep session size down.
    if product_id is not None:

        product = shop_data.get_product(id=product_id)
        if product is None:
            return redirect(url_for('cart'))

        # If no booking info provided, show a form requesting it
        # TODO:WV:20170630:Add "attendee's name" field by default, for inclusion in the basket row
        form_id = None
        for meta_datum in product["meta_data"]:
            if meta_datum["key"] == "_gravity_form_data":
                form_id = meta_datum["value"]["id"]
                break
        if form_id is not None:

            # TODO:WV:20170630:Handle form not found, here
            builder = BookingInformationFormBuilder(shop_data.get_form(form_id))
            BookingInformationForm = builder.build_booking_form()
            form = BookingInformationForm(request.form)

            # If valid form was submitted, save the data to the server
            # TODO:WV:20170706:Could make this all faster by storing the form responses in memcached rather than gravityforms
            if len(request.form.keys()) > 1 and form.validate():

                gravity_forms_form = shop_data.get_form(form_id)
                if not gravity_forms_form:
                    raise Exception("Form not found")

                gravity_forms_submission = {}
                price_adjustments = 0
                for field in form:
                    matches = rgx_matches("^gravity_forms_field_(?:[0-9]+_)?([0-9\.]+)$", field.name)
                    if matches:
                        field_id = matches.group(1)

                        # If there are any price adjustments associated with this field, add them in
                        # TODO:WV:20170706:Some of the fields feature a 'base price'.  What is this?
                        for gravity_forms_field in gravity_forms_form["fields"]:
                            if "id" in gravity_forms_field and (str(gravity_forms_field["id"]) == field_id) and "choices" in gravity_forms_field:
                                for choice in gravity_forms_field["choices"]:
                                    if "price" in choice and (choice["value"] == request.form[field.name]):
                                        price_parts = rgx_matches("^([^0-9\.]*)([0-9.]+)$", choice["price"])
                                        choice_price = price_parts.group(2)
                                        price_adjustments += float(choice_price)

                        # Add this field into the submission for gravity forms
                        gravity_forms_submission.update({field_id: request.form[field.name]})

                # Add any price adjustments into the session
                if price_adjustments != 0:
                    data_for_session["price_adjustments"] = price_adjustments

                # Add the form ID into the submission for gravity forms
                # TODO:WV:20170706:Handle invalid response from gravity forms, and a response from gravity forms that says the data is invalid
                gravity_forms_submission.update({"form_id": form_id})
                entry = [gravity_forms_submission]
                result = gf.post_entry(entry)
                if isinstance(result, list) and len(result) == 1 and isinstance(result[0], int):
                    data_for_session["gravity_forms_entry"] = result[0]

            # If no valid form was submitted, display the form
            else:
                return render_template(
                    "pages/add-to-basket.html",
                    product=product,
                    form=form
                )

        # Add product and booking information to the basket
        session["basket"][data_for_session["unique_id"]] = data_for_session

    # If removing an item, do so
    if delete_item_id is not None:
        if delete_item_id in session["basket"]:
            del session["basket"][delete_item_id]

    # Prevent form re-submit issue
    if product_id is not None or delete_item_id is not None:
        return redirect(url_for('cart'))

    return render_template(
        "pages/basket.html",
        stripe_publishable_key=stripe_keys["publishable"],
        basket=session["basket"],
        **get_all_basket_data()
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




#----------------------------------------------------------------------------#
# General utilities
#----------------------------------------------------------------------------#


def rgx_matches(rgx, string):
    matches = re.search(rgx, string)
    if matches is None:
        return False
    return matches

# This can be used for logging debug to Heroku logs (or to console, in dev)
def log_to_stdout(log_message):
    ch = logging.StreamHandler()
    app.logger.addHandler(ch)
    app.logger.info(log_message)

def uniqid(prefix = ''):
    current_time = time.time() * 1000
    output = prefix + hex(int(current_time))[2:10] + hex(int(current_time*1000000) % 0x100000)[2:7]
    return output


#----------------------------------------------------------------------------#
# App-specific utilities
#----------------------------------------------------------------------------#

class BookingInformationFormBuilder():

    def __init__(self, gravity_forms_data):
        self.gravity_forms_data = gravity_forms_data
        class BookingInformationForm(wtforms.Form):
            pass
        self.form_class = BookingInformationForm

    def add_field(self, name, field):
        setattr(self.form_class, name, field)

    def add_heading(self, text, heading_level="2"):
        self.add_field("heading-"+uniqid(), wtforms.StringField("", widget=self.get_heading_widget(text, heading_level)))

    def get_heading_widget(self, text, heading_level="2"):
        def heading_widget(field, **kwargs):
            return u"<h"+heading_level+">"+text+"</h"+heading_level+">";
        return heading_widget

    def get_option_field(self, field_type, gf_field, validators):
        choices = []
        for gf_choice in gf_field["choices"]:
            choices.append((gf_choice["value"], gf_choice["text"]+(" ("+gf_choice["price"]+")" if "price" in gf_choice and gf_choice["price"] != "" else "")))

        if field_type == "radio":
            return wtforms.RadioField(gf_field["label"], choices=choices, validators=validators)
        else:
            return wtforms.SelectField(gf_field["label"], choices=choices, validators=validators)

    def get_radio_field(self, gf_field, validators=[]):
        return self.get_option_field("radio", gf_field, validators)

    def get_select_field(self, gf_field, validators=[]):
        return self.get_option_field("select", gf_field, validators)

    def build_booking_form(self):
        for gf_field in self.gravity_forms_data["fields"]:
            field_name = "gravity_forms_field_"+str(gf_field["id"])

            validators = []
            is_required = "isRequired" in gf_field and gf_field["isRequired"]
            if is_required:
                validators.append(wtforms.validators.Required())

            if gf_field["type"] == "section":
                if "label" in gf_field and gf_field["label"] != "":
                    self.add_heading(gf_field["label"])
                if "description" in gf_field and gf_field["description"] != "":
                    self.add_heading(gf_field["description"], "3")

            elif gf_field["type"] == "name":
                self.add_heading(gf_field["label"], "4")
                for sub_field in gf_field["inputs"]:
                    sub_field_name = field_name+"_"+str(sub_field["id"])

                    if "inputType"in sub_field and sub_field["inputType"] == "radio":
                        self.add_field(sub_field_name, self.get_radio_field(sub_field))
                    else:
                        self.add_field(sub_field_name, wtforms.StringField(sub_field["label"]))

            elif gf_field["type"] == "select":
                self.add_field(field_name, self.get_select_field(gf_field, validators))

            elif "inputType" in gf_field and gf_field["inputType"] == "radio":
                self.add_field(field_name, self.get_radio_field(gf_field, validators))

            else:
                self.add_field(field_name, wtforms.StringField(gf_field["label"], validators=validators))

        return self.form_class



#----------------------------------------------------------------------------#
# Error handlers
#----------------------------------------------------------------------------#


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
