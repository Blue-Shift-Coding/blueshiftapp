# To run this on the command line, use: 'python -m shop_data.download'
import infusionsoftapi, pprint, storage

infusionsoftapi.refresh_access_token_data_if_necessary()

products = infusionsoftapi.get_all_products()

# TODO:WV:20170505:No categories in this data at the moment (although, there are subcategories, by ID only).  See if this can be fixed as the categories will be important for the website.
storage.set("products", products)

pprint.pprint(products)



