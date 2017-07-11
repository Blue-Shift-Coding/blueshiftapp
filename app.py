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
import shop_data, shopping_basket, blueshiftutils
from api.blog import fetch_posts, get_post
from woocommerceapi import wcapi
from gravityformsapi import gf

# Third party libraries
import stripe
from lib.format import post_format_date
from functools import wraps


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

@app.route('/processpayment', methods=['POST'])
def processpayment():

    if not "basket" in session:
        return redirect(url_for("classes"))

    # Build list of line items for Woocommerce order
    line_items = []
    for item_id in session["basket"]:

        # Load gravity forms entry and form
        gravity_forms_entry_id = session["basket"][item_id]["gravity_forms_entry"]
        gravity_forms_entry = shopping_basket.uncache_gravity_forms_entry(gravity_forms_entry_id)
        if not gravity_forms_entry:
            raise Exception("Form data could not be retrieved")
        gravity_forms_form = shop_data.get_form(gravity_forms_entry["form_id"])
        if not gravity_forms_form:
            raise Exception("Form not found")

        # Iterate through fields in the gravity form, add meta-data to the line-item for each one
        line_item_meta_data = []
        gravity_forms_lead = {}
        def add_field(field):
            field_key = str(field["id"])

            if field_key in gravity_forms_entry:
                gravity_forms_lead[field_key] = gravity_forms_entry[field_key]
                line_item_meta_data.append({
                    "key": field["label"],
                    "value": gravity_forms_entry[field_key]
                })
        for field in gravity_forms_form["fields"]:
            if field["type"] == "name":
                for sub_field in field["inputs"]:
                    add_field(sub_field)

            if str(field["id"]) in gravity_forms_entry:
                add_field(field)
        line_item_meta_data.append({
            "key": "_gravity_forms_history",
            "value": {
                "_gravity_form_data": {"id": gravity_forms_entry["form_id"]},
                "_gravity_form_lead": gravity_forms_lead
            },
        })

        # Add the actual line item
        line_items.append({
            "product_id": session["basket"][item_id]["product_id"],
            "quantity": 1,
            "meta_data": line_item_meta_data
        })

    # Put charge through via Stripe
    # - set up basic data for Stripe charge
    # - add receipt email if available
    # - charge the card
    basket_data = shopping_basket.get_all_basket_data()
    amount = int(float(basket_data["total_price"]) * 100)
    stripe_charge_data = {
        "source":request.form["stripeToken"],
        "amount":amount,
        "currency":"gbp",
        "description":"Flask Charge"
    }
    stripe_info = stripe.Token.retrieve(request.form["stripeToken"])
    customer_email = stripe_info["email"]
    if customer_email:
        stripe_charge_data.update({
            "receipt_email":customer_email
        })
    charge = stripe.Charge.create(**stripe_charge_data)

    # Submit order to WooCommerce API
    # TODO:WV:20170704:Could include the customers name (or other identifying data, e.g. attendee name), for the WooCommerce orders index
    response = wcapi.post("orders", {
        "payment_method": "stripe",
        "payment_method_title": "Stripe",
        "set_paid": True,
        "line_items": line_items
    })

    if not response or (response.status_code != 201 and response.status_code != 200):
        raise Exception("Invalid response from WooCommerce")

    # Empty the basket
    del session["basket"]

    # TODO:WV:20170706:Format this in the template
    flash("Order complete", "done")

    return redirect(url_for("classes"))

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
        "unique_id": blueshiftutils.uniqid(),
        "product_id": product_id
    }

    # If adding a product, either add it to the basket, or find the relevant form fields for adding to the template
    if product_id is not None:

        product = shop_data.get_product(id=product_id)
        if product is None:
            return redirect(url_for('cart'))

        # If no booking info provided, show a form requesting it
        form_id = None
        for meta_datum in product["meta_data"]:
            if meta_datum["key"] == "_gravity_form_data":
                form_id = meta_datum["value"]["id"]
                break
        if form_id is not None:

            # Load form from ID
            gravity_forms_form = shop_data.get_form(form_id)
            if gravity_forms_form is None:
                raise Exception("Form not found")

            # Build form in WTForms
            builder = shopping_basket.BookingInformationFormBuilder(gravity_forms_form)
            BookingInformationForm = builder.build_booking_form()
            form = BookingInformationForm(request.form)

            # If valid form was submitted, save the data to the server
            if len(request.form.keys()) > 1 and form.validate():

                gravity_forms_submission = {}
                price_adjustments = 0
                for field in form:
                    matches = blueshiftutils.rgx_matches("^gravity_forms_field_(?:[0-9]+_)?([0-9\.]+)$", field.name)
                    if matches:
                        field_id = matches.group(1)

                        price_adjustments += shopping_basket.get_price_adjustments(
                            gravity_forms_form,
                            field_id,
                            request.form[field.name]
                        )

                        # Add this field into the submission for gravity forms
                        gravity_forms_submission.update({field_id: request.form[field.name]})

                # Add any price adjustments into the session
                if price_adjustments != 0:
                    data_for_session["price_adjustments"] = price_adjustments

                # Add the form ID into the submission for gravity forms
                gravity_forms_submission.update({"form_id": form_id})
                result = gf.post_entry([gravity_forms_submission])
                if isinstance(result, list) and len(result) == 1 and isinstance(result[0], int):
                    gravity_forms_entry_id = result[0]
                    shopping_basket.cache_gravity_forms_entry(
                        gravity_forms_entry_id,
                        gravity_forms_submission
                    )
                    data_for_session["gravity_forms_entry"] = gravity_forms_entry_id
                else:
                    raise Exception("Invlid response from gravity forms")

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
        **shopping_basket.get_all_basket_data()
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
    # TODO:WV:20170707:Update Wordpress plugin to prevent editing the FILTERS category name or adding any others called FILTERS at the same level in the category hierarchy
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
    if "page_num" in request.args and blueshiftutils.rgx_matches("^[0-9]+$", request.args["page_num"]):
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
# Utilities
#----------------------------------------------------------------------------#


# This can be used for logging debug to Heroku logs (or to console, in dev)
def log_to_stdout(log_message):
    ch = logging.StreamHandler()
    app.logger.addHandler(ch)
    app.logger.info(log_message)



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
