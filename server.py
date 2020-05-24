import logging
import os

from authlib.integrations.flask_client import OAuth, OAuthError
from flask import (Flask,
                   flash,
                   redirect,
                   render_template,
                   request,
                   session,
                   url_for)
from wtforms import Form, StringField, SelectField

from analyze import (analyze_followers,
                     analyze_friends,
                     analyze_timeline,
                     Cache,
                     div,
                     dry_run_analysis,
                     get_friends_lists,
                     get_twitter_api)

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

CONSUMER_KEY = os.environ.get('CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('CONSUMER_SECRET')
TRACKING_ID = os.environ.get('TRACKING_ID')

if not (CONSUMER_KEY and CONSUMER_SECRET):
    raise ValueError(
        "Must set CONSUMER_KEY and CONSUMER_SECRET environment variables")

app = Flask('twitter-gender-proportion')
app.config['SECRET_KEY'] = os.environ['COOKIE_SECRET']
app.config['DRY_RUN'] = False
app.config['TWITTER_CLIENT_ID'] = CONSUMER_KEY
app.config['TWITTER_CLIENT_SECRET'] = CONSUMER_SECRET

oauth = OAuth(app)
oauth.register(
    name='twitter',
    api_base_url='https://api.twitter.com/1.1/',
    request_token_url='https://api.twitter.com/oauth/request_token',
    access_token_url='https://api.twitter.com/oauth/access_token',
    authorize_url='https://api.twitter.com/oauth/authenticate',
    fetch_token=lambda: session.get('token'),  # DON'T DO IT IN PRODUCTION
    consumer_key=CONSUMER_KEY,
    consumer_secret=CONSUMER_SECRET)

twitter = oauth.twitter


@app.route('/login')
def login():
    redirect_uri = url_for('oauth_authorized', _external=True)
    return oauth.twitter.authorize_redirect(redirect_uri)


@app.route('/logout')
def logout():
    session.pop('twitter_token')
    session.pop('twitter_user')
    flash('Logged out.')
    return redirect('/')


@app.errorhandler(OAuthError)
def handle_error(error):
    flash('You denied the request to sign in.')
    return redirect('/')


@app.route('/authorized')
def oauth_authorized():
    token = oauth.twitter.authorize_access_token()
    resp = oauth.twitter.get('account/verify_credentials.json')
    profile = resp.json()
    session['twitter_token'] = (token['oauth_token'], token['oauth_token_secret'])
    session['twitter_user'] = profile['screen_name']
    try:
        session['lists'] = get_friends_lists(profile['screen_name'],
                                             CONSUMER_KEY,
                                             CONSUMER_SECRET,
                                             token['oauth_token'],
                                             token['oauth_token_secret'])
    except Exception:
        app.logger.exception("Error in get_friends_lists, ignoring")
        session['lists'] = []

    flash('You were signed in as %s' % profile['screen_name'])
    return redirect('/')


class AnalyzeForm(Form):
    user_id = StringField('Twitter User Name')
    lst = SelectField('List')


@app.route('/', methods=['GET', 'POST'])
def index():
    oauth_token, oauth_token_secret = session.get('twitter_token', (None, None))
    form = AnalyzeForm(request.form)
    if session.get('lists'):
        form.lst.choices = (
            [('none', 'No list')]
            + [(str(l['id']), l['name']) for l in session['lists']]
        )
    else:
        del form.lst

    results = {}
    list_name = list_id = error = None
    if request.method == 'POST' and form.validate() and form.user_id.data:
        # Don't show auth'ed user's lists in results for another user.
        if (hasattr(form, 'lst')
            and form.user_id.data != session.get('twitter_user')):
            del form.lst

        if app.config['DRY_RUN']:
            list_name = None
            friends, followers, timeline = dry_run_analysis()
            results = {'friends': friends,
                       'followers': followers,
                       'timeline': timeline}
        else:
            if session.get('lists') and form.lst and form.lst.data != 'none':
                list_id = int(form.lst.data)
                list_name = [l['name'] for l in session['lists'] if
                             int(l['id']) == list_id][0]

            try:
                api = get_twitter_api(CONSUMER_KEY, CONSUMER_SECRET,
                                      oauth_token, oauth_token_secret)
                cache = Cache()
                results = {
                    'friends': analyze_friends(
                        form.user_id.data, list_id, api, cache),
                    'followers': analyze_followers(
                        form.user_id.data, api, cache),
                    'timeline': analyze_timeline(
                        form.user_id.data, list_id, api, cache)}
            except Exception as exc:
                import traceback
                traceback.print_exc()
                error = exc

    return render_template('index.html',
                           form=form, results=results, error=error, div=div,
                           list_name=list_name, TRACKING_ID=TRACKING_ID)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('port', nargs=1, type=int)
    args = parser.parse_args()
    [port] = args.port

    app.config['DRY_RUN'] = args.dry_run
    app.run(port=port, debug=args.debug)
