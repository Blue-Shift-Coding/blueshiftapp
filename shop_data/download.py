# To run this on the command line, use: 'python -m shop_data.download'
import infusionsoftapi, pprint, storage

infusionsoftapi.refresh_access_token_data_if_necessary()

products = infusionsoftapi.get_all_products()

# Add dummy age range data and date range data until we have a solution to where it is coming from
# TODO:WV:20170515:Multiple date ranges per class
# TODO:WV:20170515:Add actual data when  available
dummy_data = {
	1:{"start_date": None, "end_date": None, "min_age": None, "max_age": None, "is_ongoing_weekly": False},
	3:{"start_date": 1496098800, "end_date": 1501714800, "min_age": 5, "max_age": 6, "is_ongoing_weekly": False},
	5:{"start_date": 1496098800, "end_date": 1501714800, "min_age": 6, "max_age": 8, "is_ongoing_weekly": False},
	7:{"start_date": 1496703600, "end_date": 1499382000, "min_age": None, "max_age": None, "is_ongoing_weekly": False}
}
def add_missing_data(product):
	if product["id"] in dummy_data:
		product.update(dummy_data[product["id"]])
	return product
products["products"] = map(add_missing_data, products["products"])

# TODO:WV:20170505:No categories in this data at the moment (although, there are subcategories, by ID only).  See if this can be fixed as the categories will be important for the website.
storage.set("products", products)
