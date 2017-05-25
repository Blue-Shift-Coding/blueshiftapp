# To run this on the command line, use: 'python -m shop_data.download'
import infusionsoftapi, pprint, storage

infusionsoftapi.refresh_access_token_data_if_necessary()

products = infusionsoftapi.get_all_products()
storage.set("products", products)

categories = infusionsoftapi.get_category_tree()
storage.set("categories", categories)