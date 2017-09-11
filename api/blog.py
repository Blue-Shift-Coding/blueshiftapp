import requests
from cachetools.func import ttl_cache

# Wordpress
WORDPRESS_URL = 'https://old.blueshiftcoding.com/'

# Minutes in seconds
MINS = 60


@ttl_cache(ttl=15*MINS)
def fetch_posts(page_num=1):
    r = requests.get('{}/wp-json/wp/v2/posts?page={}'.format(WORDPRESS_URL, page_num))

    # Raise HTTPError if not 2xx
    r.raise_for_status()

    posts = r.json()
    total_pages = int(r.headers.get('X-WP-TotalPages', 1))
    return posts, total_pages


@ttl_cache(ttl=60*MINS)
def get_post(post_id):
    r = requests.get('{}/wp-json/wp/v2/posts/{}'.format(WORDPRESS_URL, post_id))

    # Raise HTTPError if not 2xx
    r.raise_for_status()

    post = r.json()
    return post
