import logging
import os

from flask import Flask, flash, redirect, render_template, request, session
from flask_oauth import OAuth
from wtforms import Form, StringField, SelectField

from analyze import (analyze_followers,
                     analyze_friends,
                     analyze_timeline,
                     div,
                     dry_run_analysis,
                     get_friends_lists)

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

app = Flask('twitter-gender-proportion')
app.config['SECRET_KEY'] = os.environ['COOKIE_SECRET']
app.config['DRY_RUN'] = False

CONSUMER_KEY = os.environ.get('CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('CONSUMER_SECRET')
TRACKING_ID = os.environ.get('TRACKING_ID')

oauth = OAuth()
twitter = oauth.remote_app(
    'twitter',
    base_url='https://api.twitter.com/1/',
    request_token_url='https://api.twitter.com/oauth/request_token',
    access_token_url='https://api.twitter.com/oauth/access_token',
    authorize_url='https://api.twitter.com/oauth/authenticate',
    consumer_key=os.environ['CONSUMER_KEY'],
    consumer_secret=os.environ['CONSUMER_SECRET'])


@twitter.tokengetter
def get_twitter_token(token=None):
    return session.get('twitter_token')


@app.route('/login')
def login():
    callback = '/authorized'
    next_url = request.args.get('next') or request.referrer
    if next_url:
        callback += '?next=' + next_url

    # This has been particularly flakey.
    try:
        return twitter.authorize(callback=callback)
    except Exception:
        app.logger.exception("Error in twitter.authorize, retrying")
        return twitter.authorize(callback=callback)


@app.route('/logout')
def logout():
    session.pop('twitter_token')
    session.pop('twitter_user')
    flash(u'Logged out.')
    return redirect('/')


@app.route('/authorized')
@twitter.authorized_handler
def oauth_authorized(resp):
    next_url = request.args.get('next') or '/'
    if resp is None:
        flash(u'You denied the request to sign in.')
        return redirect(next_url)

    session['twitter_token'] = (resp['oauth_token'], resp['oauth_token_secret'])
    session['twitter_user'] = resp['screen_name']
    try:
        session['lists'] = get_friends_lists(resp['screen_name'],
                                             CONSUMER_KEY,
                                             CONSUMER_SECRET,
                                             resp['oauth_token'],
                                             resp['oauth_token_secret'])
    except Exception:
        app.logger.exception("Error in get_friends_lists, ignoring")
        session['lists'] = []

    flash(u'You were signed in as %s' % resp['screen_name'])
    return redirect(next_url)


class AnalyzeForm(Form):
    user_id = StringField('Twitter User Name')
    lst = SelectField('List')


@app.route('/', methods=['GET', 'POST'])
def index():
    oauth_token, oauth_token_secret = session.get('twitter_token', (None, None))
    form = AnalyzeForm(request.form)
    if session.get('lists'):
        form.lst.choices = [('none', 'No list')] + [
            (unicode(l['id']), l['name']) for l in session['lists']]
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
            list_name = list_id = None
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
                results = {'friends': analyze_friends(form.user_id.data,
                                                      list_id,
                                                      CONSUMER_KEY,
                                                      CONSUMER_SECRET,
                                                      oauth_token,
                                                      oauth_token_secret),
                           'followers': analyze_followers(form.user_id.data,
                                                          CONSUMER_KEY,
                                                          CONSUMER_SECRET,
                                                          oauth_token,
                                                          oauth_token_secret),
                           'timeline': analyze_timeline(list_id,
                                                        CONSUMER_KEY,
                                                        CONSUMER_SECRET,
                                                        oauth_token,
                                                        oauth_token_secret)}
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
