from woocommerce import API

wcapi = API(
    url=os.environ["BLUESHIFTAPP_WOOCOMMERCE_BASE_URL"],
    consumer_key=os.environ["BLUESHIFTAPP_WOOCOMMERCE_CONSUMER_KEY"],
    consumer_secret=os.environ["BLUESHIFTAPP_WOOCOMMERCE_CONSUMER_SECRET"],
    wp_api=True,
    version="wc/v2"
)

