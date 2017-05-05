import requests, urllib, os.path, json, time

# TODO:WV:20170504:I think this library may be out of date (XMLRPC only; not REST)  Check and remove if so.
from infusionsoft.library import Infusionsoft

access_token_file = os.path.dirname(os.path.abspath(__file__))+"/access_token_data.json"
if not os.path.isfile(access_token_file):
	print "Access token not found.  Please visit /api-authenticate to regenerate it."

file_contents = open(access_token_file).read(1000)
access_token_data = json.loads(file_contents)



# TODO:WV:20170504:Refresh access token if necessary, using refresh_token.  Then use the new access token to make API calls.
# See https://developer.infusionsoft.com/docs/rest/#!/Authentication/permission

