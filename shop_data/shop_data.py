# To run this on the command line, use: 'python -m shop_data.download'
import storage, pprint
from woocommerce import API

wcapi = API(
    url="https://old.blueshiftcoding.com",
    consumer_key="ck_8764d7d17bbbf01c7fcfaa765721fb9ae43e0095",
    consumer_secret="cs_3970ccd6e87e3ff6327acaaf4ef342ccbdcbafe3",
    wp_api=True,
    version="wc/v2"
)

def download_data():

	# TODO:WV:20170620:Add robustness in case of bad response to wcapi.get
	# TODO:WV:20170620:Paginate properly through categories so that the case of more than 100 categories is handled.
	response = wcapi.get("products/categories?per_page=100")
	categories = response.json()
	storage.set("categories", categories)

	download_products_in_category()
	for category in categories:
		download_products_in_category(category)

def download_products_in_category(category=None):
	item_name = "products"
	if category is not None:
		category_id = str(category["id"])
		api_url = item_name+"?on_sale=1&category="+category_id
		storage_key = item_name+"-category-"+category_id
	else:
		api_url = item_name
		storage_key = item_name

	response = wcapi.get(api_url)
	products = response.json()
	storage.set(storage_key, products)

def get_categories():
	categories = get_thing("categories")
	return categories

# Finds a category based on its name, and optionally its parent category
def get_category(name, parent_id = None):
	categories = get_categories()
	parent_category_found = None
	for category in categories:
		correct_name = (name == category["name"])
		correct_parent = ((parent_id is None and category["parent"] == 0) or (parent_id is not None and category["parent"] == parent_id))
		if correct_name and correct_parent:
			return category

	return None

# TODO:WV:20170622:Add robustness here if thing not found
def get_products(categories=None):

	if categories is None:
		products = get_thing("products")

	else:
		if not isinstance(categories, list):
			categories = [categories]

		def get_filter_function(all_products_so_far):
			def fn(product):
				for existing_product in all_products_so_far:
					if product["id"] == existing_product["id"]:
						return True
				return False
			return fn

		products = []
		first_category = True
		for category in categories:
			this_category_products = get_thing("products-category-"+str(category["id"]))

			if first_category:
				products = this_category_products
				first_category = False
			else:
				products = filter(get_filter_function(products), this_category_products)

	return products

def get_thing(thingname):
	thing = storage.get(thingname)
	if thing  is None:
		raise Exception("No "+thingname+" found.  Please run the download.py script to fetch them from the API.")
	return thing