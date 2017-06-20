
wcapi = API(
    url="https://old.blueshiftcoding.com",
    consumer_key="ck_8764d7d17bbbf01c7fcfaa765721fb9ae43e0095",
    consumer_secret="cs_3970ccd6e87e3ff6327acaaf4ef342ccbdcbafe3"
)

def get(endpoint):
	response = wcapi.get(endpoint)
	return response.json()

