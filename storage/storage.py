import os, json, bmemcached

if os.environ['MEMCACHEDCLOUD_SERVERS'] and os.environ['MEMCACHEDCLOUD_USERNAME'] and os.environ['MEMCACHEDCLOUD_PASSWORD']:
	mc = bmemcached.Client(os.environ['MEMCACHEDCLOUD_SERVERS'].split(','), os.environ['MEMCACHEDCLOUD_USERNAME'], os.environ['MEMCACHEDCLOUD_PASSWORD'])
else:
	mc = None

def get(key):
	if mc:
		return mc.get(key)
	else:
		filename = get_filename(key)
		if not os.path.isfile(filename):
			return None
		file_contents = open(filename).read()
		return json.loads(file_contents)

def get_filename(key):
	return os.path.dirname(os.path.abspath(__file__))+"/data-"+key+".json"

def set(key, value):
	if mc:
		return mc.set(key, value)
	else:
		f = open(get_filename(key), "w")
		f.write(json.dumps(value))
		f.close()

