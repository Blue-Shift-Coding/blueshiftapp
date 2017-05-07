1#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from flask import Flask, render_template, request, redirect
# from flask.ext.sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from forms import *
import os
from api.blog import fetch_posts, get_post
from lib.format import post_format_date
import infusionsoftapi, shop_data


#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
app.config.from_object('config')
#db = SQLAlchemy(app)

# Automatically tear down SQLAlchemy.
'''
@app.teardown_request
def shutdown_session(exception=None):
    db_session.remove()
'''

# Login required decorator.
'''
def login_required(test):
    @wraps(test)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return test(*args, **kwargs)
        else:
            flash('You need to login first.')
            return redirect(url_for('login'))
    return wrap
'''
#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def home():

    # TODO:WV:20170503:Send categories from Infusionsoft when they change?  Fetch from Infusionsoft every X minutes?
    categories = []

    return render_template('pages/home.html')


@app.route('/about')
def about():
    return render_template('pages/about.html')

@app.route('/news')
@app.route('/news/<int:page_num>')
def news(page_num=1):
    posts, total_pages = fetch_posts(page_num)

    if page_num < 1:
        return abort(404)

    if page_num > total_pages:
        return abort(404)

    return render_template(
        'pages/news.html', data=posts, page_num=page_num,
        total_pages=total_pages, format_date=post_format_date)

@app.route('/post/<int:post_id>/<slug>')
def post(post_id, slug):
    post = get_post(post_id)

    return render_template(
        'pages/post.html', post=post, post_id=post_id, format_date=post_format_date)


@app.route('/login')
def login():
    form = LoginForm(request.form)
    return render_template('forms/login.html', form=form)


@app.route('/register')
def register():
    form = RegisterForm(request.form)
    return render_template('forms/register.html', form=form)


@app.route('/forgot')
def forgot():
    form = ForgotForm(request.form)
    return render_template('forms/forgot.html', form=form)


@app.route('/api-authenticate')
def api_authenticate():

    # If at stage 2, there should be a 'code' in the URL.  Extract it here; if absent, assume at stage 1.
    code = request.args.get("code")

    # Stage 1 - get permission to get an access token
    # TODO:WV:20170504:Password- or IP- restrict this (may be able to set up IP restriction in the Infusionsoft developer console)
    if not code:
        url = infusionsoftapi.get_authorization_url(request.base_url)
        return redirect(url, code=302)

    infusionsoftapi.download_initial_access_token_data(code=code, redirect_uri=request.base_url)
    return redirect("/api-authenticate-done", code=302)

@app.route('/api-authenticate-done')
def api_authenticate_done():
    return "Done"

@app.route('/classes')
def classes():
    products = shop_data.cache.get_all()
    return render_template('pages/classes.html', products=products)

# Error handlers.


@app.errorhandler(500)
def internal_error(error):
    #db_session.rollback()
    return render_template('errors/500.html'), 500


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
