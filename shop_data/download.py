# To run this on the command line, use: 'python -m shop_data.download'
import cache, storage, sys, pprint

checking_queue = len(sys.argv) > 1 and sys.argv[1] == "check_queue"

if checking_queue:
	is_queued = storage.get(cache.queue_key)
	if !is_queued:
		sys.exit()

cache.download_data()

if checking_queue:
	storage.set(cache.queue_key, 0)
