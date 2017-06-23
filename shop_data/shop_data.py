# To run this on the command line, use: 'python -m shop_data.download'
import storage, pprint, os, time
from woocommerce import API

#### Config
# - NB this per_page value is also used to determine the number of items on each page of the actual shop, for performance reasons
per_page = 10
data_lifetime_in_seconds = 14400
#### /Config


wcapi = API(
    url=os.environ["BLUESHIFTAPP_WOOCOMMERCE_BASE_URL"],
    consumer_key=os.environ["BLUESHIFTAPP_WOOCOMMERCE_CONSUMER_KEY"],
    consumer_secret=os.environ["BLUESHIFTAPP_WOOCOMMERCE_CONSUMER_SECRET"],
    wp_api=True,
    version="wc/v2"
)

def iterate_paginated_set(item_name, callback):
	summary = get_summary(item_name)
	for i in range(0, int(summary["num_pages"])):
		page_of_ids = storage.get(get_item_page_storage_key(item_name, i + 1))
		page_of_items = []
		for item_id in page_of_ids:
			page_of_items.append(storage.get(get_single_item_storage_key(item_name, item_id)))
		result = callback(page_of_items)

		# If the callback returned a value, stop iterating here and pass it on
		if result is not None:
			return result

def download_data():
	expiry_time = time.time() + data_lifetime_in_seconds

	download_paginated_set("categories", "products/categories?", expiry_time)
	download_paginated_set("products", "products?on_sale=1&", expiry_time)

	def get_filter_products_in_category(category):
		def fn(product):
			for product_category in product["categories"]:
				if product_category["id"] == category["id"]:
					return True
			return False
		return fn

	def categories_iterator(page_of_categories):
		for category in page_of_categories:
			product_ids_this_category = []
			def products_iterator(page_of_products):
				products_in_category_this_page = filter(get_filter_products_in_category(category), page_of_products)
				for product in products_in_category_this_page:
					product_ids_this_category.append(product["id"])
			iterate_paginated_set("products", products_iterator)
			storage.set("products-category-"+str(category["id"]), product_ids_this_category, expiry_time)

	iterate_paginated_set("categories", categories_iterator)

def get_item_page_storage_key(item_name, page_number):
	return item_name+"_page_"+str(page_number)

def get_single_item_storage_key(item_name, item_id):
	return item_name+"_"+str(item_id)

def get_item_summary_storage_key(item_name):
	return item_name+"_summary"

def download_paginated_set(item_name, base_query, expiry_time):
	page_num = 1

	summary = None
	while True:

		# TODO:WV:20170620:Add robustness in case of bad response to wcapi.get.  I.e. dont assume response.json() will be sensible.  Also handle HTTPs timeout.
		url = base_query+"page="+str(page_num)+"&per_page="+str(per_page)
		response = wcapi.get(url)
		items = response.json()

		# Save single items and collate IDs
		item_ids = []
		for item in items:
			item_ids.append(item["id"])
			storage.set(
				get_single_item_storage_key(item_name, item["id"]),
				item,
				expiry_time
			)

		# Save record of all ids in this page
		storage.set(
			get_item_page_storage_key(item_name, page_num),
			item_ids,
			expiry_time
		)

		# Create and save summary
		if summary is None:
			summary = {
				"num_total": response.headers.get("X-WP-Total"),
				"num_pages": response.headers.get("X-WP-TotalPages"),
				"per_page": per_page
			}
			storage.set(
				get_item_summary_storage_key(item_name),
				summary,
				expiry_time
			)

		# Stop looping if this is the end of the paginated set
		page_num += 1
		if page_num > int(summary["num_pages"]):
			break

	return summary

def get_summary(item_name):
	return storage.get(get_item_summary_storage_key(item_name))

# Finds a category based on its name, and optionally its parent category
def get_category(name, parent_id = None):

	def categories_iterator(page_of_categories):
		for category in categories:
			correct_name = (name == category["name"])
			correct_parent = ((parent_id is None and category["parent"] == 0) or (parent_id is not None and category["parent"] == parent_id))
			if correct_name and correct_parent:
				return category
	category = iterate_paginated_set("categories", categories_iterator)
	return category

# TODO:WV:20170622:Add robustness here if thing not found
def get_products(categories=None, page_num=1):

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