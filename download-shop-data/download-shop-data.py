# To run this on the command line, use: 'python -m download-shop-data.download-shop-data'
import infusionsoftapi, pprint, json, os.path

products_file = os.path.dirname(os.path.abspath(__file__))+"/products.json"

infusionsoftapi.refresh_access_token_data_if_necessary()

products = infusionsoftapi.get_all_products()

f = open(products_file, "w")
f.write(json.dumps(products))
f.close()


pprint.pprint(products)



