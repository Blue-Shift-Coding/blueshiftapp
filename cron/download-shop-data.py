import requests, urllib, os.path, json, time

# TODO:WV:20170504:I think this library may be out of date (XMLRPC only; not REST)  Check and remove if so.
from infusionsoft.library import Infusionsoft

if not os.path.isfile(os.path.dirname(__file__)+"/access_token_data.json"):
	print "Access token not found.  Please visit /api-authenticate to regenerate it."

