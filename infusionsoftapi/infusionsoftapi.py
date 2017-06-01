# See https://developer.infusionsoft.com/docs/rest
import requests, time, base64, urllib, os, json, storage, pprint, re, imghdr
from infusionsoft.library import InfusionsoftOAuth

access_token_file = os.path.dirname(os.path.abspath(__file__))+"/access_token_data.json"
authorization_url = "https://signin.infusionsoft.com/app/oauth/authorize"
token_url = "https://api.infusionsoft.com/token"
api_url = "https://api.infusionsoft.com/crm/rest/v1"

credentials = {}
for credential in [{"var": "BLUESHIFTAPP_INFUSIONSOFT_CLIENT_ID", "name":"client_id"}, {"var": "BLUESHIFTAPP_INFUSIONSOFT_CLIENT_SECRET", "name":"client_secret"}]:
	if not os.environ[credential["var"]]:
		raise Exception("Missing credential "+credential["name"])
	credentials[credential["name"]] = os.environ[credential["var"]]

# These are also used outside the module
categories_for_filtering = {"Age range": [], "Dates": []}
categories_for_metadata = ["Times"]

def have_access_token():
	access_token_data = get_access_token_data()
	return access_token_data is not None

def get_access_token_data():
	access_token_data = storage.get("access_token_data")

	if not access_token_data:
		return None

	if (not access_token_data or not ("access_token" in access_token_data and "time_saved_unix" in access_token_data and "access_token_lifespan_in_seconds" in access_token_data and "refresh_token" in access_token_data)):
		raise ValueError("Not all necessary access token data found")

	return access_token_data


def get_authorization_url(redirect_uri):
	params = {
		"response_type": "code",
		"scope": "full",
		"client_id": credentials["client_id"],
		"redirect_uri": redirect_uri
	}
	url = authorization_url+"?"+urllib.urlencode(params);
	return url


def download_initial_access_token_data(code, redirect_uri):
	payload = {
		"client_id": credentials["client_id"],
		"client_secret": credentials["client_secret"],
		"code": code,
		"grant_type": "authorization_code",
		"redirect_uri": redirect_uri
	}
	headers = {}
	update_access_token_data(payload=payload, headers=headers)


def refresh_access_token_data_if_necessary():
	buffertime = 300
	access_token_data = get_access_token_data()

	if not access_token_data:
		refresh_access_token_data()
		return

	access_token_expiry_time = ((int(access_token_data["time_saved_unix"]) + int(access_token_data["access_token_lifespan_in_seconds"])) - buffertime)
	current_time = int(time.time())

	if (access_token_expiry_time < int(current_time)):
		refresh_access_token_data()


def refresh_access_token_data():
	access_token_data = get_access_token_data()

	if not access_token_data:
		raise ValueError("No access token to refresh - please authorize the app by starting the app and visiting /api-authenticate")

	if (not "refresh_token" in access_token_data):
		raise ValueError("No refresh token found in existing access token data")

	payload = {
		"grant_type": "refresh_token",
		"refresh_token": access_token_data["refresh_token"]
	}
	headers = {
		"Authorization": "Basic "+base64.b64encode(credentials["client_id"]+":"+credentials["client_secret"])
	}
	update_access_token_data(payload=payload, headers=headers)


def update_access_token_data(payload, headers={}):
	r = requests.post(token_url, data=payload, headers=headers)
	response_data = r.json()

	if ("error" in response_data):
		raise ValueError("Could not authenticate (error from server)")

	if (not ("access_token" in response_data and "expires_in" in response_data and "refresh_token" in response_data)):
		raise ValueError("Some expected data was missing from API response")

	access_token_data = storage.set("access_token_data", {
		"access_token": response_data["access_token"],
		"time_saved_unix": int(time.time()),
		"access_token_lifespan_in_seconds": response_data["expires_in"],
		"refresh_token": response_data["refresh_token"],
	})

def get_all_products():
	products = get("/products/search")

	# Add categories to products
	# Also add maximum and minimum age, for colour coding on the website
	categories = get_category_tree()
	product_categories = query_product_category_assign_table()
	for product in products["products"]:
		product.update({"categories": [], "min_age": None, "max_age": None});
		for product_category in product_categories:
			if product["id"] == product_category["ProductId"]:
				for category_id in categories:
					category = categories[category_id]
					if category["category"]["id"] == product_category["ProductCategoryId"]:
						product["categories"].append(category["category"]["id"])
					else:
						for child_category in category["children"]:
							if child_category["id"] == product_category["ProductCategoryId"]:
								product["categories"].append(child_category["id"])
								if category["category"]["name"] == "Age range":
									matches = re.search("^([0-9]+)\-([0-9]+)$", child_category["name"])
									if matches is not None:
										min_age = int(matches.group(1))
										max_age = int(matches.group(2))
										product["min_age"] = min_age if product["min_age"] is None else min(product["min_age"], min_age)
										product["max_age"] = max_age if product["max_age"] is None else max(product["max_age"], max_age)
								if category["category"]["name"] == "Times":
									if "times" not in product:
										product["times"] = []
									product["times"].append(child_category["name"])

	# Add images to products
	extra_product_data = query_product_table()
	for extra_product_datum in extra_product_data:
		for product in products["products"]:
			if (extra_product_datum["Id"] == product["id"]):
				if ("LargeImage" in extra_product_datum and extra_product_datum["LargeImage"] is not None):
					image_type = imghdr.what('', extra_product_datum["LargeImage"].data)
					if image_type:
						product.update({"image": "data:image/"+image_type+";base64,"+extra_product_datum["LargeImage"].data.encode("base64")})
				break

	# Add extra data to product options, as required
	for product in products["products"]:
		for option in product["product_options"]:
			format_rgx = "\s*\(format:([^)]+)\)\s*$"
			matches = re.search(format_rgx, option["label"])
			if matches is not None:
				match_parts = re.split("\s*;\s*", matches.group(1))
				if (match_parts[0].lower() == "date"):
					option.update({"type": "Date", "restrictions": [match_parts[1]], "label": re.sub(format_rgx, "", option["label"])})


	# Add extra product options, as required
	# TODO:WV:20170601:Restrict which fields show up on which products, using the category system
	for product in products["products"]:
		product.update({"extra_options": [
			{"label": "Test extra option 1", "type": "Variable", "required": True, "id": "test1"},
			{"label": "Test extra option 2", "type": "Variable", "required": True, "id": "test2"}]
		})

	return products

def get_category_tree():
	categoryTree = {}
	categories = query_category_table()

	def add_category(id, category=None):
		if not id in categoryTree:
			categoryTree[id] = {"category": None, "children": []}
		if category is not None:
			categoryTree[id]["category"] = category

	for category in categories:
		category_for_storage = {"id": category["Id"], "name": category["CategoryDisplayName"]}
		if "ParentId" in category and category["ParentId"] is not None and category["ParentId"] != 0:
			add_category(category["ParentId"])
			categoryTree[category["ParentId"]]["children"].append(category_for_storage)
		else:
			add_category(category["Id"], category_for_storage)

	return categoryTree

def get_product(id):
	return get("/products/"+str(id))

def get_event_keys():
	return get("/hooks/event_keys")

def update_hook(event_key, hook_url):
	return post("/hooks", {"eventKey":event_key, "hookUrl": hook_url})

def delete_hook(id):
	return delete("/hooks/"+str(id))

def get_available_hooks():
	return get("/hooks")

def get(url, params = {}):
	r = requests.get(completeUrl(url, params))
	return r.json()

def put(url, params = {}):
	r = requests.put(completeUrl(url), json=params)
	return r.json()

def post(url, params = {}):
	r = requests.post(completeUrl(url), json=params)
	return r.json()

def delete(url, params={}):
	requests.delete(completeUrl(url), json=params)

# Example XMLAPI request using their legacy API (neccessary using product images and categories)
def query_product_table():
	return xmlrpc_query_table("Product", ["Id", "ProductName", "LargeImage"], {"ProductName": "%"})

def query_category_table():
	return xmlrpc_query_table("ProductCategory", ["Id", "CategoryDisplayName", "ParentId"], {"Id": "%"})

def query_product_category_assign_table():
	return xmlrpc_query_table("ProductCategoryAssign", ["Id", "ProductCategoryId", "ProductId"], {"Id": "%"})

def completeUrl(url, params={}):
	access_token_data = get_access_token_data()
	params["access_token"] = access_token_data["access_token"]
	url = api_url + url + "?" + urllib.urlencode(params)
	return url

def xmlrpc_query_table(table, return_fields, query_data, page=0, limit=10000):
	access_token_data = get_access_token_data()
	Infusionsoft = InfusionsoftOAuth(access_token_data["access_token"])
	data = Infusionsoft.DataService('query', table, limit, page, query_data, return_fields)
	return data