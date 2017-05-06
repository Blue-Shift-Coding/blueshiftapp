# To run this on the command line, use: 'python -m shop-data.download'
import json, os.path

products_file = os.path.dirname(os.path.abspath(__file__))+"/products.json"

def get_all():
	if not os.path.isfile(products_file):
		raise Exception("Products file not found.  Please run the download.py script to generate it from the API.")

	# TODO:WV:20170506:I saw someone on the internet saying that it is a good idea always to supply an integer argument to read() below, to give the max. bytes to read.  Not sure why - look into it.
	file_contents = open(products_file).read()

	filedata = json.loads(file_contents)
	return filedata["products"]



