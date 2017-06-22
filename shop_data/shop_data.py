# To run this on the command line, use: 'python -m shop-data.download'
import storage
from woocommerce import API

wcapi = API(
    url="https://old.blueshiftcoding.com",
    consumer_key="ck_8764d7d17bbbf01c7fcfaa765721fb9ae43e0095",
    consumer_secret="cs_3970ccd6e87e3ff6327acaaf4ef342ccbdcbafe3"
)

def download_data():
	response = wcapi.get("products")
	products = response.json()
	storage.set("products", products)

	# TODO:WV:20170620:Add robustness in case of bad response
	response = wcapi.get("products/categories")
	categories = response.json()
	storage.set("categories", categories["product_categories"])

# TODO:WV:20170622:Handle pagination if there are more than 10 categories
def get_categories():
	categories = get_thing("categories")
	return categories

# Finds a category based on its name, and optionally its parent category
def get_category(name, parent_name = None):
	categories = get_categories()
	parent_category_found = None
	for category in categories:
		if (parent_name is None and category["name"] == name) or (parent_name is not None and category["name"] == parent_name):
			parent_category_found = category
			break

	if parent_category_found is None:
		return None

	if parent_name is None:
		return parent_category_found

	for category in categories:
		if category["parent"] == parent_category_found["id"] and category["name"] == name:
			return category

	return None


def get_products(category=None):
	products = get_thing("products")
	return products["products"]

def get_thing(thingname):
	thing = storage.get(thingname)
	if not thing:
		raise Exception("No "+thingname+" found.  Please run the download.py script to fetch them from the API.")
	return thing