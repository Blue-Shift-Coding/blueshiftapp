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

def ids_to_items(item_name, ids):
	items = []
	for item_id in ids:
		items.append(storage.get(get_single_item_storage_key(item_name, item_id)))
	return items

def iterate_paginated_set(item_name, callback):
	summary = get_summary(item_name)
	for i in range(0, int(summary["num_pages"])):
		page_of_ids = storage.get(get_item_page_storage_key(item_name, i + 1))
		page_of_items = ids_to_items(item_name, page_of_ids)
		result = callback(page_of_items)

		# If the callback returned a value, stop iterating here and pass it on
		if result is not None:
			return result

# The following two variables need to be variables to get around the fact that Python doesn't allow
# Them to by declared in categories_iterator and then referenced from withint products_iterator.
# There will be a pythonic way of doing this.  What is it?
# TODO:WV:20170623:Find and implement the proper way of doing it
product_ids_this_category = None
product_category_page_num = None
def download_data():
	expiry_time = time.time() + data_lifetime_in_seconds

	# Download all raw data
	download_paginated_set("categories", "products/categories?", expiry_time)
	download_paginated_set("products", "products?on_sale=1&", expiry_time)

	# Save category-specific lists of products
	def get_filter_products_in_category(category):
		def fn(product):
			for product_category in product["categories"]:
				if product_category["id"] == category["id"]:
					return True
			return False
		return fn

	def categories_iterator(page_of_categories):
		global product_ids_this_category, product_category_page_num

		for category in page_of_categories:
			product_ids_this_category = []
			product_category_page_num = 1
			def products_iterator(page_of_products):
				global product_ids_this_category, product_category_page_num

				products_in_category_this_page = filter(get_filter_products_in_category(category), page_of_products)
				for product in products_in_category_this_page:
					product_ids_this_category.append(product["id"])
					if len(product_ids_this_category) == per_page:
						storage.set(
							get_products_category_storage_key(category["id"], product_category_page_num),
							product_ids_this_category,
							expiry_time
						)
						product_ids_this_category = []
						product_category_page_num += 1
			iterate_paginated_set("products", products_iterator)

			# Save final page of this category, if there is one
			if len(product_ids_this_category) != 0:
				storage.set(
					get_products_category_storage_key(category["id"], product_category_page_num),
					product_ids_this_category,
					expiry_time
				)

	iterate_paginated_set("categories", categories_iterator)

def get_products_category_item_name(category_id):
	return "products_category_"+str(category_id)

def get_products_category_storage_key(category_id, page_number):
	return get_item_page_storage_key(get_products_category_item_name(category_id), page_number)

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
		products = ids_to_items(storage.get(get_item_page_storage_key("products", page_num)))

	elif not isinstance(categories, list):

		# TODO:WV:20170623:Test for expired categories (not included in the last data download) and ignore them - find an appropriate place to do this
		products = ids_to_items(storage.get(get_products_category_storage_key(categories["id"], page_num)))

	else:
		# Find the correct page of appropriately categorised products
		num_products_to_skip = (page_num - 1) * per_page
		num_products_skipped = 0
		num_categories = len(categories)
		products = []
		def products_iterator(page_of_products):

			for product in page_of_products:

				# Count how many of the specified categories the product was found in
				num_categories_product_found_in = 0
				for category in categories:
					def product_category_iterator(page_of_products_in_this_category):
						if product in page_of_products_in_this_category:
							num_categories_product_found_in += 1
							return True
					iterate_paginated_set(get_products_category_item_name(category["id"]), product_category_iterator)

				# If the product was in all of the specified categories, and it is in the correct page of results, add it to the output
				if num_categories_product_found_in == num_categories:
					num_products_still_to_skip = num_products_to_skip - num_products_skipped
					if num_products_still_to_skip < 1:
						products.append(product)

						# Can stop iterating if we now have enough products
						if len(products) == per_page:
							return True
					else:
						num_products_skipped += 1

		iterate_paginated_set("products", products_iterator)

	return products

def get_thing(thingname):
	thing = storage.get(thingname)
	if thing  is None:
		raise Exception("No "+thingname+" found.  Please run the download.py script to fetch them from the API.")
	return thing