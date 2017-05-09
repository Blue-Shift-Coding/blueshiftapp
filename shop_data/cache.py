# To run this on the command line, use: 'python -m shop-data.download'
import storage

def get_all():
	products = storage.get("products")
	if not products:
		raise Exception("No products found.  Please run the download.py script to generate it from the API.")
	return products["products"]



