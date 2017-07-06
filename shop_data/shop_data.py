# To run this on the command line, use: 'python -m shop_data.download'
import storage, pprint, os, time, sys
from woocommerceapi import wcapi
from gravityformsapi import gf

#### Config
data_lifetime_in_seconds = 14400
#### /Config


#### Not-config (things that look like config but which actually cannot be changed, or the script will break)
items_apis = {
	"products": "woocommerce",
	"categories": "woocommerce",
	"forms": "gravityforms"
}
#### /Not-config

wcapi = woocommerceapi.wcapi
gf = wooco


def download_data():
	expiry_time = time.time() + data_lifetime_in_seconds

	# Get all forms from
	# TODO:WV:20170629:Handle any error in 'get_forms'
	forms = gf.get_forms().values()
	update_set("forms", expiry_time=expiry_time, item_ids=map(lambda x: x["id"], forms), get_item_method=gf.get_form)
	update_set("categories", expiry_time=expiry_time, base_query="products/categories?")
	update_set("products", expiry_time=expiry_time, base_query="products?")

def update_set(item_name, expiry_time, base_query=None, item_ids=None, get_item_method=None):

	# Find item_type
	if item_name in items_apis:
		api_to_use = items_apis[item_name]
	else:
		raise Exception("Unknown item name")

	# Validate input to this function
	if api_to_use == "woocommerce":
		if base_query is None:
			raise Exception("Please supply a base query")
	elif api_to_use == "gravityforms":
		if item_ids is None:
			raise Exception("Please supply all current item IDs")
		if get_item_method is None:
			raise Exception("Please supply a method that retrieves a single item based on its ID")
	else:
		raise Exception("Unknown API")

	# Save new data and remove data that is no longer present
	# TODO:WV:20170629:Re-test this, especially for gravityforms
	ids_before = get_item_ids(item_name)
	if api_to_use == "woocommerce":
		download_paginated_set(item_name, base_query, expiry_time)
	elif api_to_use == "gravityforms":
		download_items_from_ids(item_name, expiry_time, item_ids, get_item_method)
	else:
		raise Exception("Unknown API")
	ids_after = get_item_ids(item_name)
	deleted_ids = list_diff(ids_before, ids_after)
	for item_id in deleted_ids:
		storage.delete(get_single_item_storage_key(item_name, item_id))

def list_diff(list1, list2):
	return list(set(list1).difference(list2))

def get_item_ids(item_name):
	ids = storage.get(item_name)
	if ids is None:
		ids = []
	return ids

def get_single_item_storage_key(item_name, item_id=None, item_slug=None):
	if item_id is None:
		if item_slug is None:
			raise Exception("Please provide either an item ID or a slug")
		slugs = storage.get(get_slugs_storage_key(item_name))
		if slugs[item_slug]:
			item_id = slugs[item_slug]

	return item_name+"_"+str(item_id)

def get_slugs_storage_key(item_name):
	return item_name+"_slugs"

def download_items_from_ids(item_name, expiry_time, item_ids, get_item_method):
	for item_id in item_ids:

		# TODO:WV:20170630:Handle failure here
		item = get_item_method(item_id)
		storage.set(
			get_single_item_storage_key(item_name, item_id),
			item,
			expiry_time
		)

	storage.set(
		item_name,
		item_ids,
		expiry_time
	)

def download_paginated_set(item_name, base_query, expiry_time):
	page_num = 1
	per_page = 100
	item_ids = []
	item_slugs = {}
	num_pages = None
	while True:
		url = base_query+"page="+str(page_num)+"&per_page="+str(per_page)
		try:
			response = wcapi.get(url)
			items = response.json()
		except:
			print "Invalid response downloading "+item_name+" - leaving them as-is "
			return

		items_data = save_items(item_name, items, expiry_time)
		item_ids.extend(items_data["item_ids"])
		item_slugs.update(items_data["item_slugs"])

		if num_pages is None:
			num_pages = int(response.headers.get("X-WP-TotalPages"))

		# Stop looping if this is the end of the paginated set
		page_num += 1
		if page_num > num_pages:
			break

	# Save indexing data
	storage.set(
		item_name,
		item_ids,
		expiry_time
	)
	storage.set(
		get_slugs_storage_key(item_name),
		item_slugs,
		expiry_time
	)

	return num_pages

def save_items(item_name, items, expiry_time):
	item_ids = []
	item_slugs = {}
	for item in items:
		item_ids.append(item["id"])
		if "slug" in item:
			item_slugs.update({item["slug"]: item["id"]})
		storage.set(
			get_single_item_storage_key(item_name, item["id"]),
			item,
			expiry_time
		)
	return {"item_ids":item_ids, "item_slugs": item_slugs}

def ids_to_items(item_name, ids):
	items = []
	for item_id in ids:
		items.append(storage.get(get_single_item_storage_key(item_name, item_id)))
	return items

# Finds a category based on its name, and optionally its parent category
def get_category(name, parent_id = None):
	category_ids = get_item_ids("categories")

	for category_id in category_ids:
		category = storage.get(get_single_item_storage_key("categories", category_id))
		correct_name = (name == category["name"])
		correct_parent = ((parent_id is None and category["parent"] == 0) or (parent_id is not None and category["parent"] == parent_id))
		if correct_name and correct_parent:
			return category

def get_product(id=None, slug=None):
	storage_key = get_single_item_storage_key("products", item_id=id, item_slug=slug)
	return storage.get(storage_key)

def get_form(id):
	storage_key = get_single_item_storage_key("forms", item_id=id)
	return storage.get(storage_key)

def get_products(categories=None, page_num=1, per_page=10):
	product_ids = get_item_ids("products")

	offset_first_product = (page_num - 1) * per_page
	offset_last_product = page_num * per_page

	if categories is None:
		return {
			"num_total": len(product_ids),
			"products": ids_to_items("products", product_ids[offset_first_product:offset_last_product])
		}

	else:

		products_skipped = 0
		products_added = 0
		total_matching_products_found = 0

		products_found = []

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
				total_matching_products_found += 1

				if products_added == per_page:
					continue

				if products_skipped == offset_first_product:
					products_found.append(product)
					products_added += 1
				else:
					products_skipped += 1

		return {
			"num_total": total_matching_products_found,
			"products": products_found
		}

def get_categories():
	category_ids = get_item_ids("categories")
	return ids_to_items("categories", category_ids)