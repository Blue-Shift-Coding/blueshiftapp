import os, json, bmemcached,  glob, pprint

if 'MEMCACHEDCLOUD_SERVERS' in os.environ and os.environ['MEMCACHEDCLOUD_SERVERS'] and 'MEMCACHEDCLOUD_USERNAME' in os.environ and os.environ['MEMCACHEDCLOUD_USERNAME'] and 'MEMCACHEDCLOUD_PASSWORD' in os.environ and os.environ['MEMCACHEDCLOUD_PASSWORD']:
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

def get_storage_dir():
	return os.path.dirname(os.path.abspath(__file__))+"/data"

def get_filename(key):
	return get_storage_dir()+"/"+key+".json"

# TODO:WV:20170622:Also use the expiry time for the disk version (e.g. by wrapping the value in another layer of JSON containing the expiry time, and adding a 'remove expired' function that inspects each item and removes expired ones)
def set(key, value, memcached_expiry_time):
	if mc:
		mc.set(key, value, memcached_expiry_time)
	else:
		f = open(get_filename(key), "w")
		f.write(json.dumps(value))
		f.close()

def flush():
	if mc:
		mc.flush_all()
	else:
		files = glob.glob(get_storage_dir()+"/*.json")
		for file in files:
			os.remove(file)

def delete(key):
	if mc:
		mc.delete(key)
	else:
		filename = get_filename(key)
		if not os.path.isfile(filename):
			return
		os.remove(filename)

