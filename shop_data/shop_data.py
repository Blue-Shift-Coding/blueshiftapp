# To run this on the command line, use: 'python -m shop_data.download'
import storage, pprint, os, time
from woocommerce import API

#### Config
data_lifetime_in_seconds = 14400
#### /Config


wcapi = API(
    url=os.environ["BLUESHIFTAPP_WOOCOMMERCE_BASE_URL"],
    consumer_key=os.environ["BLUESHIFTAPP_WOOCOMMERCE_CONSUMER_KEY"],
    consumer_secret=os.environ["BLUESHIFTAPP_WOOCOMMERCE_CONSUMER_SECRET"],
    wp_api=True,
    version="wc/v2"
)

def download_data():
	expiry_time = time.time() + data_lifetime_in_seconds

	# Download all raw data
	# TODO:WV:20170624:Delete items that have been removed since last download
	download_paginated_set("categories", "products/categories?", expiry_time)
	download_paginated_set("products", "products?on_sale=1&", expiry_time)

	# Save category-specific lists of categories
	category_ids = storage.get("categories")
	product_ids = storage.get("products")
	for category_id in category_ids:
		product_ids_this_category = []
		for product_id in product_ids:
			product = storage.get(get_single_item_storage_key("products", product_id))
			for product_category in product["categories"]:
				if product_category["id"] == category_id:
					product_ids_this_category.append(product_id)
		storage.set(
			get_products_category_item_name(category_id),
			product_ids_this_category,
			expiry_time
		)

def get_products_category_item_name(category_id):
	return "products_category_"+str(category_id)

def get_single_item_storage_key(item_name, item_id):
	return item_name+"_"+str(item_id)

def download_paginated_set(item_name, base_query, expiry_time):
	page_num = 1
	per_page = 10
	item_ids = []
	num_pages = None
	while True:

		# TODO:WV:20170620:Add robustness in case of bad response to wcapi.get.  I.e. dont assume response.json() will be sensible.  Also handle HTTPs timeout.
		url = base_query+"page="+str(page_num)+"&per_page="+str(per_page)
		response = wcapi.get(url)
		items = response.json()

		# Save single items and collate IDs
		for item in items:
			item_ids.append(item["id"])
			storage.set(
				get_single_item_storage_key(item_name, item["id"]),
				item,
				expiry_time
			)

		if num_pages is None:
			num_pages = int(response.headers.get("X-WP-TotalPages"))

		# Stop looping if this is the end of the paginated set
		page_num += 1
		if page_num > num_pages:
			break

	# Save record of all ids
	storage.set(
		item_name,
		item_ids,
		expiry_time
	)

	return num_pages

def ids_to_items(item_name, ids):
	items = []
	for item_id in ids:
		items.append(storage.get(get_single_item_storage_key(item_name, item_id)))
	return items

# Finds a category based on its name, and optionally its parent category
def get_category(name, parent_id = None):
	category_ids = storage.get("categories")
	for category_id in category_ids:
		category = storage.get(get_single_item_storage_key("categories", category_id))
		correct_name = (name == category["name"])
		correct_parent = ((parent_id is None and category["parent"] == 0) or (parent_id is not None and category["parent"] == parent_id))
		if correct_name and correct_parent:
			return category

# TODO:WV:20170622:Add robustness here if thing not found
def get_products(categories=None, page_num=1, per_page=10):
	product_ids = storage.get("products")

	offset_first_product = page_num - 1 * per_page
	offset_last_product = page_num * per_page

	products_found = []

	if categories is None:
		return ids_to_items("products", product_ids[offset_first_product:offset_last_product])

	else:

		if not isinstance(categories, list):
			categories = [categories]

		for product_id in product_ids:
			product = storage.get(get_single_item_storage_key("products", product_id))
			num_categories_product_found_in = 0
			for category in categories:
				for product_category in product["categories"]:
					if product_category["id"] == category["id"]:
						num_categories_product_found_in += 1
						break
			if num_categories_product_found_in == len(categories):
				products_found.append(product)

		return products_found[offset_first_product:offset_last_product]

def get_categories():
	category_ids = storage.get("categories")
	return ids_to_items("categories", category_ids)