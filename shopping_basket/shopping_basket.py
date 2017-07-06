import session, shop_data, wtforms


#----------------------------------------------------------------------------#
# Various shopping-basket related goodies
#----------------------------------------------------------------------------#


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
        if "price_adjustments" in session["basket"][item_id]:
            total_price += session["basket"][item_id]["price_adjustments"]

    return {
        "products": products,
        "total_price": total_price
    }

def get_gravity_forms_entry_storage_key(entry_id):
    return "gravity_forms_entry_"+entry_id

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
