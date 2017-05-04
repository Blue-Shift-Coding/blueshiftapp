import requests, urllib
from infusionsoft.library import Infusionsoft


# TODO:WV:20170503:These should not be in version control
params = {
	"response_type": "code",
	"scope": "full",
	"client_id": "",
	"redirect_uri": "https://blueshift-app.willv.net/"
}


url = "https://signin.infusionsoft.com/app/oauth/authorize?"+urllib.urlencode(params);

print "Visit the following URL in your browser: \n"
print url
print "\n"

#print requests.get(url).content;
