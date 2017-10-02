# coding: utf-8

#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

# Flask modules
from flask import Flask, render_template, request, redirect, Response, url_for, session, flash, jsonify
import wtforms
from forms import *

# Core modules
import os, time, copy, math, json, re, requests, collections, json, hashlib
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
mailgun_secret_key = os.environ["BLUESHIFTAPP_MAILGUN_SECRET_KEY"]
course_info_request = {
    "sender": "hello@blueshiftcoding.com",
    "recipient": "hello@blueshiftcoding.com"
}


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


@app.template_filter('strip')
def template_strip(value):
    if not isinstance(value, str):
        return value
    return value.strip()


@app.template_filter('integers')
def get_integers(value):
    if not isinstance(value, basestring):
        return value
    return re.sub("[^0-9]", "", value)

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
        page_num=page_num,
        total_pages=total_pages,
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

@app.route('/cart/coupon', methods=['POST'])
@app.route('/cart', methods=['GET', 'POST'])
def cart():

    # Extract input from post-data
    # TODO:WV:20171002:Validate coupon
    coupon = None if "coupon" not in request.form else request.form["coupon"]
    product_id = None if "product_id" not in request.form else request.form["product_id"]
    delete_item_id = None if "delete_item_id" not in request.form else request.form["delete_item_id"]

    # Initialise basket in session if necessary
    if "basket" not in session:
        session["basket"] = {}

    # If adding a coupon, add it to the basket
    # TODO:WV:20171002:For now, only allow one coupon at a time (bearing in mind space in Python session and complications that would be involved in syncing coupons from server, expiring at appropriate dates, etc.)
    if coupon is not None:

        # Decode incoming coupon
        try:
            coupon = json.loads(coupon)
        except:
            return jsonify({"status": "error"})

        # Check coupon for valid signature
        if not validate_signature(coupon):
            return jsonify({"status": "error"})

        # Check that there is not already a coupon in the basket
        for item_id in session["basket"]:
            if "coupon" in session["basket"][item_id]:
                return jsonify({"status": "error", "msg": "Only one discount code can be used at a time"})

        uniqid = blueshiftutils.uniqid()
        session["basket"][uniqid] = {
            "unique_id": uniqid,
            "coupon": {
                "id": coupon["id"],
                "discount_type": coupon["discount_type"],
                "amount": coupon["amount"],
                "code": coupon["code"]
            }
        }

        return jsonify({"status": "ok"})

    # If adding a product, either add it to the basket, or find the relevant form fields for adding to the template
    if product_id is not None:

        # Prepare data to go into the session after this process has finished (it may be added to later in this function)
        data_for_session = {
            "unique_id": blueshiftutils.uniqid(),
            "product_id": product_id
        }

        product_exists = shop_data.product_exists(id=product_id)
        if not product_exists:
            return redirect(url_for('cart'))

        product = shop_data.get_product(id=product_id)
        if product is None:

            # This redirect is probably unnecessary, but have left it in for now (2017-09-18)
            return redirect(url_for('cart'))

        # If no booking info provided, show a form requesting it
        form_id = None
        for meta_datum in product["meta_data"]:
            if "key" in meta_datum and meta_datum["key"] == "_gravity_form_data":
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
                    raise Exception("Invalid response from gravity forms")

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

    # Show an 'empty cart' message if the cart is empty
    if not "basket" in session or not session["basket"]:
        return render_template(
            "pages/empty-basket.html",
        )

    # Sort basket: coupons after products
    basket_products = collections.OrderedDict()
    basket_coupons = collections.OrderedDict()
    for item_id in session["basket"]:
        item = session["basket"][item_id]
        if "coupon" in item:
            basket_coupons[item_id] = item
        elif "product_id" in item:
            basket_products[item_id] = item
        else:
            raise Exception("Unknown basket item type")
    sorted_basket = collections.OrderedDict()
    for k, e in basket_products.items() + basket_coupons.items():
        sorted_basket[k]= e

    return render_template(
        "pages/basket.html",
        basket=sorted_basket,
        show_coupon_row=len(basket_coupons) == 0,
        **shopping_basket.get_all_basket_data()
    )

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():

    if not "basket" in session or not session["basket"]:
        return redirect(url_for("classes"))

    form = shopping_basket.CheckoutForm(request.form)
    all_basket_data = shopping_basket.get_all_basket_data()
    if request.method == 'POST' and form.validate():
        session["checkout-parent-info-ok"] = True

        if all_basket_data["total_price"] == 0:
            return redirect(url_for("processpayment"))

        return render_template(
            "pages/payment.html",
            form=form,
            stripe_publishable_key=stripe_keys["publishable"],
            basket=session["basket"],
            **all_basket_data
        )

    return render_template(
        "pages/checkout.html",
        form=form,
        basket=session["basket"],
        **all_basket_data
    )


@app.route('/requestcourseinfo', methods=['POST'])
def requestcourseinfo():

    if "email" not in request.form or not request.form["email"]:
        return Response("No email supplied")

    api_url = "https://api:"+mailgun_secret_key+"@api.mailgun.net/v2/mailgun.blueshiftcoding.com"
    r = requests.post(api_url+"/messages", data={
        "from" : course_info_request["sender"],
        "to" : course_info_request["recipient"],
        "subject" : "Course info request",
        "text" : "Email address: "+request.form["email"]+("\nCourse enquired about: "+(request.form["course"] if ("course" in request.form and request.form["course"]) else ""))
    })

    return Response("{'status': 'ok'}")

@app.route('/requestschoolsinfo', methods=['POST'])
def requestschoolsinfo():

    if "email" not in request.form or not request.form["email"]:
        return Response("No email supplied")

    api_url = "https://api:"+mailgun_secret_key+"@api.mailgun.net/v2/mailgun.blueshiftcoding.com"
    r = requests.post(api_url+"/messages", data={
        "from" : course_info_request["sender"],
        "to" : course_info_request["recipient"],
        "subject" : "Course info request",
        "text" : "Email address: "+request.form["email"] +
        "\nName: "+(request.form["first_name"] ) + "\nMessage: "+request.form["message"]
    })

    flash("Thanks for getting in touch, we'll get back to you ASAP")
    return redirect(url_for("schools"))

@app.route('/processpayment', methods=['POST'])
def processpayment():

    if not "basket" in session or not "checkout-parent-info-ok" in session:
        return redirect(url_for("classes"))

    # Build list of line items for Woocommerce order
    line_items = []
    for item_id in session["basket"]:

        # Load gravity forms entry and form
        line_item_meta_data = []
        if "gravity_forms_entry" in session["basket"][item_id]:
            gravity_forms_entry_id = session["basket"][item_id]["gravity_forms_entry"]
            gravity_forms_entry = shopping_basket.uncache_gravity_forms_entry(gravity_forms_entry_id)
            if not gravity_forms_entry:
                raise Exception("Form data could not be retrieved")
            gravity_forms_form = shop_data.get_form(gravity_forms_entry["form_id"])
            if not gravity_forms_form:
                raise Exception("Form not found")

            # Iterate through fields in the gravity form, add meta-data to the line-item for each one
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
        product = shop_data.get_product(id=session["basket"][item_id]["product_id"])
        line_item_total = (0 if "price" not in product or product["price"] is None or product["price"] == "" else float(product["price"]))

        if "price_adjustments" in session["basket"][item_id]:
            line_item_total += session["basket"][item_id]["price_adjustments"]

        line_items.append({
            "product_id": session["basket"][item_id]["product_id"],
            "quantity": 1,
            "total": line_item_total,
            "meta_data": line_item_meta_data
        })

    # Put charge through via Stripe
    # - set up basic data for Stripe charge
    # - add receipt email if available
    # - charge the card
    basket_data = shopping_basket.get_all_basket_data()
    amount = int(float(basket_data["total_price"]) * 100)
    if (amount != 0):
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
    parent_data = {
        "first_name": request.form["parents_first_name"],
        "last_name": request.form["parents_last_name"],
        "email": request.form["email"],
        "phone": request.form["contact_number"]
    }
    response = wcapi.post("orders", {
        "payment_method": "stripe",
        "payment_method_title": "Stripe",
        "set_paid": True,
        "line_items": line_items,
        "billing": parent_data
    })

    if not response or (response.status_code != 201 and response.status_code != 200):
        raise Exception("Invalid response from WooCommerce")

    # Empty the basket
    if "basket" in session:
        del session["basket"]

    return redirect(url_for("ordercomplete"))

@app.route('/ordercomplete')
def ordercomplete():
    return render_template(
        'pages/ordercomplete.html'
    )

@app.route('/class/<slug>')
def singleclass(slug):
    product = shop_data.get_product(slug=slug)

    return render_template(
        'pages/single_class.html',
        product=product
    )

    return product

@app.route('/coupons/<code>')
def coupons(code):
    coupon = shop_data.get_coupon(code=code)
    allowed_keys = [
        "id",
        "amount",
        "code",
        "discount_type",
        "exclude_sale_items",
        "excluded_product_categories",
        "excluded_product_ids",
        "free_shipping",
        "individual_use",
        "limit_usage_to_x_items",
        "maximum_amount",
        "product_categories",
        "product_ids",
        "usage_count",
        "usage_limit"
    ]

    filtered_coupon = {k: coupon[k] for k in allowed_keys if k in coupon}
    filtered_coupon = sign(filtered_coupon)

    return jsonify(filtered_coupon)

def sign(dictionary, lifespan=3600):
    working_dictionary = dictionary.copy()
    gentime = int(time.time())
    working_dictionary["gentime"] = gentime
    working_dictionary["expiry"] = gentime + lifespan
    ordered_dict = collections.OrderedDict(sorted(working_dictionary.items()))
    ordered_dict["signature"] = get_signature(ordered_dict)
    return dict(ordered_dict)

def get_signature(ordered_dict):
    return hashlib.sha256(json.dumps(ordered_dict)).hexdigest()

def validate_signature(dictionary, lifespan=3600):
    if "gentime" not in dictionary or "expiry" not in dictionary or "signature" not in dictionary:
        return False
    if int(dictionary["expiry"]) < int(time.time()):
        return False
    working_dictionary = dictionary.copy()
    signature_to_check = working_dictionary["signature"]
    del working_dictionary["signature"]
    ordered_dict = collections.OrderedDict(sorted(working_dictionary.items()))
    return (signature_to_check == get_signature(ordered_dict))


@app.route('/classes/', defaults={"url_category": None})
@app.route('/classes/<url_category>')
def classes(url_category):

    # Add filter drop-downs, with options
    filters_category = shop_data.get_category("FILTERS")
    filter_category_ids = {}
    if filters_category is None:
        filters = []
    else:
        filters = []

        categories = shop_data.get_categories()
        for category in categories:
            if "parent" in category and (category["parent"] == filters_category["id"]):
                filter_category_ids[category["name"].lower()] = category["id"]
                filters.append({"category": category, "child_categories": []})

        # Find filter options
        for class_filter in filters:
            for category in categories:
                if "parent" in category and (category["parent"] == class_filter["category"]["id"]):
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
