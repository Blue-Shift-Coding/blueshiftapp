# To run this on the command line, use: 'python -m download-shop-data.download-shop-data.py'
import infusionsoftapi

infusionsoftapi.refresh_access_token_data_if_necessary()

products = infusionsoftapi.get_all_products()

print products



