from flask import session
import shop_data, wtforms, blueshiftutils, time, datetime, storage, re, cgi
from gravityformsapi import gf


#----------------------------------------------------------------------------#
# Various shopping-basket related goodies
#----------------------------------------------------------------------------#

def uncache_gravity_forms_entry(gravity_forms_entry_id):
    gravity_forms_entry = storage.get(get_gravity_forms_entry_storage_key(gravity_forms_entry_id))
    if not gravity_forms_entry:
        gravity_forms_entry = gf.get_entry(gravity_forms_entry_id)
    if not gravity_forms_entry:
        cache_gravity_forms_entry(
            gravity_forms_entry_id,
            gravity_forms_entry
        )

    return gravity_forms_entry

def cache_gravity_forms_entry(gravity_forms_entry_id, gravity_forms_submission):
    one_day_in_seconds = 86400
    expiry_time = time.time() + one_day_in_seconds
    storage.set(
        get_gravity_forms_entry_storage_key(gravity_forms_entry_id),
        gravity_forms_submission,
        expiry_time
    )

def get_all_basket_data():
    if "basket" not in session:
        return {}

    # Get full data on all products in the basket
    # Including total price
    products = {}
    names = {}
    coupons = {}
    total_price = 0;
    for item_id in session["basket"]:
        basket_item = session["basket"][item_id]
        if not isinstance(basket_item, dict):
            continue

        if "coupon" in basket_item:
            if basket_item["coupon"]["discount_type"] == "fixed_cart":
                total_price -= float(basket_item["coupon"]["amount"])
            elif basket_item["coupon"]["discount_type"] == "percent":
                total_price *= (float(basket_item["coupon"]["amount"]) / 100)
            elif basket_item["coupon"]["discount_type"] == "fixed_product":
                # TODO:WV:20171002:Implement this
                pass
            else:
                raise Exception("Unknown coupon type")
            coupons[basket_item["coupon"]["id"]] = basket_item["coupon"]

        elif "product_id" in basket_item:
            product_exists = shop_data.product_exists(id=basket_item["product_id"])
            if not product_exists:
                continue
            product = shop_data.get_product(id=basket_item["product_id"])
            products[session["basket"][item_id]["product_id"]] = product
            total_price += (0 if "price" not in product or product["price"] is None or product["price"] == "" else float(product["price"]))
            if "price_adjustments" in session["basket"][item_id]:
                total_price += session["basket"][item_id]["price_adjustments"]

            if "gravity_forms_entry" in session["basket"][item_id]:
                gravity_forms_entry_id = session["basket"][item_id]["gravity_forms_entry"]
                gravity_forms_entry = uncache_gravity_forms_entry(gravity_forms_entry_id)
                gravity_forms_form = shop_data.get_form(gravity_forms_entry["form_id"])

                this_item_name = None
                for field in gravity_forms_form["fields"]:
                    name_labels = [
                        "childsname",
                        "nameofchild",
                        "studentsname",
                        "nameofstudent",
                        "attendeesname",
                        "nameofattendee"
                    ]
                    if re.sub("[^a-zA-Z]", "", field["label"]).lower() in name_labels:

                        # Concatenate all sub-fields of name-fields
                        if field["type"] == "name" and "inputs" in field:
                            this_item_name = ""
                            for sub_field in field["inputs"]:
                                for field_id in gravity_forms_entry:
                                    if str(field_id) == str(sub_field["id"]):
                                        this_item_name += gravity_forms_entry[field_id]+" "
                            this_item_name = this_item_name.strip()

                        # Use the value of other fields, as-is
                        elif str(field["id"]) in gravity_forms_entry and gravity_forms_entry[str(field["id"])] != "":
                            this_item_name = gravity_forms_entry[str(field["id"])]

                        # Stop looking for name-fields
                        break

                if this_item_name:
                    names[item_id] = this_item_name
        else:
            raise Exception("Unknown basket item type")


    return {
        "products": products,
        "coupons": coupons,
        "total_price": total_price,
        "names": names
    }


def get_price_adjustments(gravity_forms_form, field_id, field_value):
    for gravity_forms_field in gravity_forms_form["fields"]:
        if "id" in gravity_forms_field and (str(gravity_forms_field["id"]) == field_id) and "choices" in gravity_forms_field:
            for choice in gravity_forms_field["choices"]:
                if "price" in choice and (choice["value"] == field_value):
                    price_parts = blueshiftutils.rgx_matches("([0-9.]+)$", choice["price"])
                    if price_parts:
                        choice_price = price_parts.group(1)
                        return float(choice_price)
    return 0

def get_gravity_forms_entry_storage_key(entry_id):
    return "gravity_forms_entry_"+str(entry_id)

class CheckoutForm(wtforms.Form):
    parents_first_name = wtforms.StringField("Parent's First Name", [wtforms.validators.Length(min=3)])
    parents_last_name = wtforms.StringField("Parent's Last Name", [wtforms.validators.Length(min=3)])
    contact_number = wtforms.StringField("Contact Number", [wtforms.validators.Length(min=8)])
    email = wtforms.StringField("Email", [wtforms.validators.Email()])


class BookingInformationFormBuilder():

    def __init__(self, gravity_forms_data):
        self.gravity_forms_data = gravity_forms_data
        class BookingInformationForm(wtforms.Form):
            pass
        self.form_class = BookingInformationForm

    def add_field(self, name, field):
        setattr(self.form_class, name, field)

    def add_heading(self, text, heading_level="3", color_number = "1"):
        self.add_field("heading-"+blueshiftutils.uniqid(), wtforms.StringField("", widget=self.get_heading_widget(text, heading_level)))

    def get_heading_widget(self, text, heading_level="2", color_number = "1"):
        def heading_widget(field, **kwargs):
            return u"<h"+heading_level+" class='color-"+color_number+"'>"+text+"</h"+heading_level+">";
        return heading_widget

    def listToOptions(self, list_of_options):
        output = ""
        for option_in_list in list_of_options:
            option_value = cgi.escape(str(option_in_list).zfill(2))
            output += "<option value='"+option_value+"'>"+option_value+"</option>"
        return output

    def get_date_widget(self):
        def date_widget(field, **kwargs):
            days = range(1, 31)
            months = range(1, 12)
            years = range(2000, datetime.datetime.now().year + 10)

            if 'value' not in kwargs:
                kwargs['value'] = field._value()

            return """
                <div class='blueshift-date-dropdowns'>
                    <input type='hidden' name='"""+cgi.escape(field.name)+"""' value='"""+cgi.escape(kwargs['value'])+"""' />
                    <select class='blueshift-date-day'><option>day</option>"""+self.listToOptions(days)+"""</select>
                    <select class='blueshift-date-month'><option>month</option>"""+self.listToOptions(months)+"""</select>
                    <select class='blueshift-date-year'><option>year</option>"""+self.listToOptions(years)+"""</select>
                </div>
            """
        return date_widget

    def get_option_field(self, field_type, gf_field, validators):
        choices = []
        for gf_choice in gf_field["choices"]:
            choices.append((gf_choice["value"], gf_choice["text"]))

        if field_type == "radio":
            return wtforms.RadioField(gf_field["label"], choices=choices, validators=validators)
        else:
            choices.insert(0, ('', ''))
            is_required = "isRequired" in gf_field and gf_field["isRequired"]
            if is_required:
                validators.append(wtforms.validators.NoneOf([''], message=u"This field is required"))
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

            if "isHidden" in gf_field and gf_field["ishidden"]:
                continue

            elif gf_field["type"] == "section":
                if "label" in gf_field and gf_field["label"] != "":
                    self.add_heading(gf_field["label"])
                if "description" in gf_field and gf_field["description"] != "":
                    self.add_heading(gf_field["description"], "4")

            elif gf_field["type"] == "name":

                # Don't output the main field label - instead just output the sub-fields and require their labels to be adequately clear on their own
                for sub_field in gf_field["inputs"]:
                    sub_field_name = field_name+"_"+str(sub_field["id"])

                    sub_field_validators = []
                    if is_required:
                        sub_field_validators.append(wtforms.validators.Required())

                    if "isHidden" in sub_field and sub_field["isHidden"]:
                        continue

                    elif "inputType"in sub_field and sub_field["inputType"] == "radio":
                        self.add_field(sub_field_name, self.get_radio_field(sub_field, validators=sub_field_validators))

                    else:
                        self.add_field(sub_field_name, wtforms.StringField(
                            sub_field["label"] if "customLabel" not in sub_field else sub_field["customLabel"],
                            validators=sub_field_validators
                        ))

            elif gf_field["type"] == "select":
                self.add_field(field_name, self.get_select_field(gf_field, validators))

            elif "inputType" in gf_field and gf_field["inputType"] == "radio":
                self.add_field(field_name, self.get_radio_field(gf_field, validators))

            elif gf_field["type"] == "date":
                self.add_field(field_name, wtforms.DateField(gf_field["label"], validators=validators, widget=self.get_date_widget(), format="%d/%m/%Y"))

            else:
                self.add_field(field_name, wtforms.StringField(gf_field["label"], validators=validators))

        return self.form_class
