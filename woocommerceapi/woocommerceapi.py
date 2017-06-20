import os

required_environment_variables = ["BLUESHIFTAPP_WOOCOMMERCE_BASE_URL", "BLUESHIFTAPP_WOOCOMMERCE_CONSUMER_KEY", "BLUESHIFTAPP_WOOCOMMERCE_CONSUMER_SECRET"]

for key in required_environment_variables:
	required_environment_variable = required_environment_variables[key]
	if not required_environment_variable in os.environ:
		raise Exception("Environment variable '"+required_environment_variable+"' not found")

wcapi = API(
    url=os.environ["BLUESHIFTAPP_WOOCOMMERCE_BASE_URL"],
    consumer_key=os.environ["BLUESHIFTAPP_WOOCOMMERCE_CONSUMER_KEY"],
    consumer_secret=os.environ["BLUESHIFTAPP_WOOCOMMERCE_CONSUMER_SECRET"]
)

def get(endpoint):
	response = wcapi.get(endpoint)
	return response.json()

