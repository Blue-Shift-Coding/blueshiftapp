# See https://developer.infusionsoft.com/docs/rest
import requests, os.path, json, time, base64, urllib

credentials_file = os.path.dirname(os.path.abspath(__file__))+"/credentials.json"
access_token_file = os.path.dirname(os.path.abspath(__file__))+"/access_token_data.json"
authorization_url = "https://signin.infusionsoft.com/app/oauth/authorize"
token_url = "https://api.infusionsoft.com/token"
api_url = "https://api.infusionsoft.com/crm/rest/v1"

if not os.path.isfile(credentials_file):
	raise Exception("Credentials file not found.  Please place a file called 'credentials.json' in this module's directory containing your client_id and client_secret.")
file_contents = open(credentials_file).read(1000)
credentials = json.loads(file_contents)
if (not ("client_id" in credentials and "client_secret" in credentials)):
	raise ValueError("Not all necessary credentials pdata found")


def get_access_token_data():
	if not os.path.isfile(access_token_file):
		raise Exception("Access token not found.  Please visit /api-authenticate to regenerate it.")
	file_contents = open(access_token_file).read(1000)
	access_token_data = json.loads(file_contents)

	if (not ("access_token" in access_token_data and "time_saved_unix" in access_token_data and "access_token_lifespan_in_seconds" in access_token_data and "refresh_token" in access_token_data)):
		raise ValueError("Not all necessary access token data found")

	return access_token_data


def get_authorization_url(redirect_uri):
	params = {
		"response_type": "code",
		"scope": "full",
		"client_id": credentials["client_id"],
		"redirect_uri": redirect_uri
	}
	url = authorization_url+"?"+urllib.urlencode(params);
	return url


def download_initial_access_token_data(code, redirect_uri):
	payload = {
		"client_id": credentials["client_id"],
		"client_secret": credentials["client_secret"],
		"code": code,
		"grant_type": "authorization_code",
		"redirect_uri": redirect_uri
	}
	headers = {}
	update_access_token_data(payload=payload, headers=headers)


def refresh_access_token_data_if_necessary():
	buffertime = 300

	access_token_data = get_access_token_data()
	access_token_expiry_time = ((int(access_token_data["time_saved_unix"]) + int(access_token_data["access_token_lifespan_in_seconds"])) - buffertime)
	current_time = int(time.time())

	if (access_token_expiry_time < int(current_time)):
		refresh_access_token_data()


def refresh_access_token_data(refresh_token = None):
	access_token_data = get_access_token_data
	if (not "refresh_token" in access_token_data):
		raise ValueError("No refresh token found in existing access token data")

	payload = {
		"grant_type": "refresh_token",
		"refresh_token": access_token_data["refresh_token"]
	}
	headers = {
		"Authorization": "Basic "+base64.b64encode(credentials["client_id"]+":"+credentials["client_secret"])
	}
	update_access_token_data(payload=payload, headers=headers)


def update_access_token_data(payload, headers={}):
	r = requests.post(token_url, data=payload, headers=headers)
	response_data = r.json()

	if ("error" in response_data):
		raise ValueError("Could not authenticate (error from server)")

	if (not ("access_token" in response_data and "expires_in" in response_data and "refresh_token" in response_data)):
		raise ValueError("Some expected data was missing from API response")

	f = open(access_token_file, "w")
	f.write(json.dumps({
		"access_token": response_data["access_token"],
		"time_saved_unix": int(time.time()),
		"access_token_lifespan_in_seconds": response_data["expires_in"],
		"refresh_token": response_data["refresh_token"],
	}))
	f.close()

def get_all_products():
	return get("/products/search")

def get(url, params = {}):
	access_token_data = get_access_token_data()
	params["access_token"] = access_token_data["access_token"]
	url = api_url + url + "?" + urllib.urlencode(params)
	r = requests.get(url)
	return r.json()