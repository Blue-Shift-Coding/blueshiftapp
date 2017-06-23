# To run this on the command line, use: 'python -m shop_data.download'
import storage, pprint, os, time
from woocommerce import API

wcapi = API(
    url=os.environ["BLUESHIFTAPP_WOOCOMMERCE_BASE_URL"],
    consumer_key=os.environ["BLUESHIFTAPP_WOOCOMMERCE_CONSUMER_KEY"],
    consumer_secret=os.environ["BLUESHIFTAPP_WOOCOMMERCE_CONSUMER_SECRET"],
    wp_api=True,
    version="wc/v2"
)

data_lifetime_in_seconds = 7200
per_page = 10

def download_data():
	expiry_time = time.time() + data_lifetime_in_seconds

	categories_summary = download_paginated_set("categories", "products/categories?", expiry_time)
	products_summary = download_paginated_set("products", "products?on_sale=1&", expiry_time)

	def get_filter_products_in_category(category):
		def fn(product):
			for product_category in product["categories"]:
				if product_category["id"] == category["id"]:
					return True
			return False
		return fn

	# Generate category-specific product lists in storage, for faster searching later
	for i in range(0, int(categories_summary["num_pages"])):
		page_of_categories = storage.get(get_item_page_storage_key("categories", i + 1))
		for category in page_of_categories:
			products_this_category = []
			for j in range(0, int(products_summary["num_pages"])):
				page_of_products = storage.get(get_item_page_storage_key("products", j + 1))
				products_this_category.extend(filter(get_filter_products_in_category(category), page_of_products))
			storage.set("products-category-"+str(category["id"]), products_this_category, expiry_time)

def get_item_page_storage_key(item_name, page_number):
	return item_name+"_page_"+str(page_number)

def download_paginated_set(item_name, base_query, expiry_time):
	page_num = 1

	summary = None
	while True:

		# TODO:WV:20170620:Add robustness in case of bad response to wcapi.get.  I.e. dont assume response.json() will be sensible.  Also handle HTTPs timeout.
		url = base_query+"page="+str(page_num)+"&per_page="+str(per_page)
		response = wcapi.get(url)

		storage.set(
			get_item_page_storage_key(item_name, page_num),
			response.json(),
			expiry_time
		)

		if summary is None:
			summary = {
				"num_total": response.headers.get("X-WP-Total"),
				"num_pages": response.headers.get("X-WP-TotalPages"),
				"per_page": per_page
			}
			storage.set(
				item_name+"_summary",
				summary,
				expiry_time
			)

		page_num += 1
		if page_num > int(summary["num_pages"]):
			break

	return summary

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

		def get_filter_function(allowed_items):
			def fn(item):
				for allowed_item in allowed_items:
					if item["id"] == allowed_item["id"]:
						return True
				return False
			return fn

		# Skip categories that were not included in the last download of data (to avoid providing data from dead categories)
		all_categories = get_categories()
		categories = filter(get_filter_function(all_categories), categories)

		# Filter products to only those included in all provided categories
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