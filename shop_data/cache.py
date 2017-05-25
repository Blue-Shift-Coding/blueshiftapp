# To run this on the command line, use: 'python -m shop-data.download'
import storage

def get_products():
	products = get_thing("products")
	return products["products"]

def get_categories():
	categories = get_thing("categories")
	return categories

def get_thing(thingname):
	thing = storage.get(thingname)
	if not thing:
		raise Exception("No "+thingname+" found.  Please run the download.py script to fetch them from the API.")
	return thing