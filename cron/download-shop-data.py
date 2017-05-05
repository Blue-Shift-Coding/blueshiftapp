import requests, os.path, json, time, base64, sys

# TODO:WV:20170504:I think this library may be out of date (XMLRPC only; not REST)  Check and remove if so.
from infusionsoft.library import Infusionsoft

access_token_file = os.path.dirname(os.path.abspath(__file__))+"/access_token_data.json"
if not os.path.isfile(access_token_file):
	print "Access token not found.  Please visit /api-authenticate to regenerate it."

file_contents = open(access_token_file).read(1000)
access_token_data = json.loads(file_contents)

if (not ("access_token" in access_token_data and "time_saved_unix" in access_token_data and "access_token_lifespan_in_seconds" in access_token_data and "refresh_token" in access_token_data)):
	print "Not all necessary access token data found"

buffertime = 300
access_token_expiry_time = ((int(access_token_data["time_saved_unix"]) + int(access_token_data["access_token_lifespan_in_seconds"])) - buffertime)
current_time = int(time.time())

if (access_token_expiry_time < int(current_time)):
	payload = {
		"grant_type": "refresh_token",
		"refresh_token": access_token_data["refresh_token"]
	}
	credentials = {
	}
	headers = {
		"Authorization": "Basic "+base64.b64encode(credentials["client_id"]+":"+credentials["client_secret"])
	}
	print (credentials["client_id"]+":"+credentials["client_secret"])
	r = requests.post("https://api.infusionsoft.com/token", data=payload, headers=headers)

	# Save access token and associated data for later use
	# TOOD:WV:20170505:De-dup between here and the controller
	response_data = r.json()

	if ("error" in response_data):
		print "Could not authenticate (error from server)"
		print r.content
		sys.exit(1)

	# TODO:WV:20170505:De-deup between here and the cron job
	if (not ("access_token" in response_data and "expires_in" in response_data and "refresh_token" in response_data)):
		print "Some expected data was missing from API response"
		print response_data
		sys.exit(1)

	# TODO:WV:20170504:Dont repeat this file-name in the cron job

	f = open(os.path.dirname(os.path.abspath(__file__))+"/access_token_data.json", "w")
	f.write(json.dumps({
		"access_token": response_data["access_token"],
		"time_saved_unix": int(time.time()),
		"access_token_lifespan_in_seconds": response_data["expires_in"],
		"refresh_token": response_data["refresh_token"],
	}))
	f.close()


# TODO:WV:20170504:Refresh access token if necessary, using refresh_token.  Then use the new access token to make API calls.
# See https://developer.infusionsoft.com/docs/rest/#!/Authentication/permission

