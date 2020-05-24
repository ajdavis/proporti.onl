import os
import pickle
import random
import re
import sys
import time
import warnings
import webbrowser

import twitter  # pip install python-twitter
import gender_guesser.detector as gender  # pip install gender-guesser
from requests_oauthlib import OAuth1Session
from unidecode import unidecode  # pip install unidecode

if os.path.exists('detector.pickle'):
    detector = pickle.load(open('detector.pickle', 'rb'))
else:
    detector = gender.Detector(case_sensitive=False)
    with open('detector.pickle', 'wb+') as f:
        pickle.dump(detector, f)


def split(s):
    try:
        return s.split()[0]
    except IndexError:
        return s


def rm_punctuation(s, _pat=re.compile(r'\W+')):
    return _pat.sub(' ', s)


def make_pronoun_patterns():
    for p, g in [('non binary', 'nonbinary'),
                 ('non-binary', 'nonbinary'),
                 ('nonbinary', 'nonbinary'),
                 ('enby', 'nonbinary'),
                 ('nb', 'nonbinary'),
                 ('genderqueer', 'nonbinary'),
                 ('man', 'male'),
                 ('male', 'male'),
                 ('boy', 'male'),
                 ('guy', 'male'),
                 ('woman', 'female'),
                 ('womanist', 'female'),
                 ('female', 'female'),
                 ('girl', 'female'),
                 ('gal', 'female'),
                 ('latina', 'female'),
                 ('latino', 'male'),
                 ('dad', 'male'),
                 ('mum', 'female'),
                 ('mom', 'female'),
                 ('father', 'male'),
                 ('grandfather', 'male'),
                 ('mother', 'female'),
                 ('grandmother', 'female'),
                 ('they', 'nonbinary'),
                 ('xe', 'nonbinary'),
                 ('xi', 'nonbinary'),
                 ('xir', 'nonbinary'),
                 ('ze', 'nonbinary'),
                 ('zie', 'nonbinary'),
                 ('zir', 'nonbinary'),
                 ('hir', 'nonbinary'),
                 ('she', 'female'),
                 ('hers', 'female'),
                 ('her', 'female'),
                 ('he', 'male'),
                 ('his', 'male'),
                 ('him', 'male'),
                 # Source: http://nikkistevens.com/open-demographics/questions/gender.html
                 ('demi-?girl', 'nonbinary'),
                 ('demi-?woman', 'nonbinary'),
                 ('demi-?female', 'nonbinary'),
                 ('demi-?boy', 'nonbinary'),
                 ('demi-?man', 'nonbinary'),
                 ('demi-?male', 'nonbinary'),
                 ('gender-?flux', 'nonbinary'),
                 ('gender-?fluid', 'nonbinary'),
                 ('demi-?gender', 'nonbinary'),
                 ('bi-?gender', 'nonbinary'),
                 ('tri-?gender', 'nonbinary'),
                 ('two-?spirit', 'nonbinary'),
                 ('multi-?gender', 'nonbinary'),
                 ('poly-?gender', 'nonbinary'),
                 ('pan-?gender', 'nonbinary'),
                 ('omni-?gender', 'nonbinary'),
                 ('maxi-?gender', 'nonbinary'),
                 ('apora-?gender', 'nonbinary'),
                 ('inter-?gender', 'nonbinary'),
                 ('maverique', 'nonbinary'),
                 ('gender[ -]?confus(ion)|(ed)', 'nonbinary'),
                 ('gender[ -]?f[u\*]ck', 'nonbinary'),
                 ('gender[ -]?indifferent', 'nonbinary'),
                 ('gray-?gender', 'nonbinary'),
                 ('agender', 'nonbinary'),
                 ('demi-?agender', 'nonbinary'),
                 ('genderless', 'nonbinary'),
                 ('gender[ -]?neutral', 'nonbinary'),
                 ('neutrois', 'nonbinary'),
                 ('androgynous', 'nonbinary'),
                 ('androgyne', 'nonbinary'),
                 ]:
        for text in (r'\b' + p + r'\b',
                     r'\b' + p + r'/',
                     r'\b' + p + r' /',
                     r'pronoun\.is/' + p):
            yield re.compile(text), g


_PRONOUN_PATTERNS = list(make_pronoun_patterns())


class Cache(object):
    def __init__(self):
        self._users = {}
        self._hits = self._misses = 0

    @property
    def hit_percentage(self):
        return (100 * self._hits) / (self._hits + self._misses)

    def UsersLookup(self, user_ids):
        rv = [self._users[uid] for uid in user_ids if uid in self._users]
        self._hits += len(rv)
        self._misses += len(user_ids) - len(rv)
        return rv

    def UncachedUsers(self, user_ids):
        return list(set(user_ids) - set(self._users))

    def AddUsers(self, profiles):
        for p in profiles:
            self._users[p.id] = p


def declared_gender(description):
    dl = description.lower()
    if ('pronoun.is' in dl and
            'pronoun.is/she' not in dl and
            'pronoun.is/he' not in dl):
        return 'nonbinary'

    guesses = set()
    for p, g in _PRONOUN_PATTERNS:
        if p.search(dl):
            guesses.add(g)
            if len(guesses) > 1:
                return 'andy'  # Several guesses: don't know.

    if len(guesses) == 1:
        return next(iter(guesses))

    return 'andy'  # Zero or several guesses: don't know.


def analyze_user(user, verbose=False):
    """Get (gender, declared) tuple.

    gender is "male", "female", "nonbinary", or "andy" meaning unknown.
    declared is True or False.
    """
    with warnings.catch_warnings():
        # Suppress unidecode warning "Surrogate character will be ignored".
        warnings.filterwarnings("ignore")
        g = declared_gender(user.description)
        if g != 'andy':
            return g, True

        # We haven't found a preferred pronoun.
        for name, country in [
            (split(user.name), 'usa'),
            (user.name, 'usa'),
            (split(unidecode(user.name)), 'usa'),
            (unidecode(user.name), 'usa'),
            (split(user.name), None),
            (user.name, None),
            (unidecode(user.name), None),
            (split(unidecode(user.name)), None),
        ]:
            g = detector.get_gender(name, country)
            if g != 'andy':
                # Not androgynous.
                break

            g = detector.get_gender(rm_punctuation(name), country)
            if g != 'andy':
                # Not androgynous.
                break

        if verbose:
            print("{:20s}\t{:40s}\t{:s}".format(
                user.screen_name.encode('utf-8'),
                user.name.encode('utf-8'), g))

        if g.startswith('mostly_'):
            g = g.split('mostly_')[1]

        return g, False


def div(num, denom):
    if denom:
        return num / float(denom)

    return 0


class Stat(object):
    def __init__(self):
        self.n = 0
        self.n_declared = 0


class Analysis(object):
    def __init__(self, ids_sampled, ids_fetched):
        self.nonbinary = Stat()
        self.male = Stat()
        self.female = Stat()
        self.andy = Stat()
        self.ids_sampled = ids_sampled
        self.ids_fetched = ids_fetched

    def update(self, gender, declared):
        # Elide gender-unknown and androgynous names.
        attr = getattr(self, 'andy' if gender == 'unknown' else gender)
        attr.n += 1
        if declared:
            attr.n_declared += 1

    def guessed(self, gender=None):
        if gender:
            attr = getattr(self, gender)
            return attr.n - attr.n_declared

        return (self.guessed('nonbinary')
                + self.guessed('male')
                + self.guessed('female'))

    def declared(self, gender=None):
        if gender:
            attr = getattr(self, gender)
            return attr.n_declared

        return (self.nonbinary.n_declared
                + self.male.n_declared
                + self.female.n_declared)

    def pct(self, gender):
        attr = getattr(self, gender)
        return div(100 * attr.n, self.nonbinary.n + self.male.n + self.female.n)


def dry_run_analysis():
    friends = Analysis(250, 400)
    friends.nonbinary.n = 10
    friends.nonbinary.n_declared = 10
    friends.male.n = 200
    friends.male.n_declared = 20
    friends.female.n = 40
    friends.female.n_declared = 5
    friends.andy.n = 250

    followers = Analysis(250, 400)
    followers.nonbinary.n = 10
    followers.nonbinary.n_declared = 10
    followers.male.n = 200
    followers.male.n_declared = 20
    followers.female.n = 40
    followers.female.n_declared = 5
    followers.andy.n = 250

    timeline = Analysis(250, 400)
    timeline.nonbinary.n = 10
    timeline.nonbinary.n_declared = 10
    timeline.male.n = 200
    timeline.male.n_declared = 20
    timeline.female.n = 40
    timeline.female.n_declared = 5
    timeline.andy.n = 250

    return friends, followers, timeline


def analyze_users(users, ids_fetched=None):
    an = Analysis(ids_sampled=len(users), ids_fetched=ids_fetched)

    for user in users:
        g, declared = analyze_user(user)
        an.update(g, declared)

    return an


def batch(it, size):
    for i in range(0, len(it), size):
        yield it[i:i + size]


def get_twitter_api(consumer_key, consumer_secret,
                    oauth_token, oauth_token_secret):
    return twitter.Api(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token_key=oauth_token,
        access_token_secret=oauth_token_secret,
        sleep_on_rate_limit=True)


# 500 ids per call.
MAX_GET_FRIEND_IDS_CALLS = 10
MAX_GET_FOLLOWER_IDS_CALLS = 10

# 100 users per call.
MAX_USERS_LOOKUP_CALLS = 30


def get_friends_lists(user_id, consumer_key, consumer_secret,
                      oauth_token, oauth_token_secret):
    api = get_twitter_api(consumer_key, consumer_secret,
                          oauth_token, oauth_token_secret)

    # Only store what we need, avoid oversized session cookie.
    def process_lists():
        for l in reversed(api.GetLists()):
            as_dict = l.AsDict()
            yield {'id': as_dict.get('id'), 'name': as_dict.get('name')}

    return list(process_lists())


def analyze_self(user_id, api):
    users = api.UsersLookup(screen_name=[user_id])

    return analyze_user(users[0])


def fetch_users(user_ids, api, cache):
    users = []
    users.extend(cache.UsersLookup(user_ids))
    for ids in batch(cache.UncachedUsers(user_ids), 100):
        results = api.UsersLookup(ids)
        cache.AddUsers(results)
        users.extend(results)

    return users


def analyze_friends(user_id, list_id, api, cache):
    nxt = -1
    friend_ids = []
    for _ in range(MAX_GET_FRIEND_IDS_CALLS):
        if list_id is not None:
            nxt, prev, data = api.GetListMembersPaged(list_id=list_id,
                                                      cursor=nxt)
            friend_ids.extend([fr.id for fr in data])
        else:
            nxt, prev, data = api.GetFriendIDsPaged(screen_name=user_id,
                                                    cursor=nxt)

            friend_ids.extend(data)
        if nxt == 0 or nxt == prev:
            break

    # We can fetch users' details 100 at a time.
    if len(friend_ids) > 100 * MAX_USERS_LOOKUP_CALLS:
        friend_id_sample = random.sample(friend_ids,
                                         100 * MAX_USERS_LOOKUP_CALLS)
    else:
        friend_id_sample = friend_ids

    users = fetch_users(friend_id_sample, api, cache)
    return analyze_users(users, ids_fetched=len(friend_ids))


def analyze_followers(user_id, api, cache):
    nxt = -1
    follower_ids = []
    for _ in range(MAX_GET_FOLLOWER_IDS_CALLS):
        nxt, prev, data = api.GetFollowerIDsPaged(screen_name=user_id,
                                                  cursor=nxt)
        follower_ids.extend(data)
        if nxt == 0 or nxt == prev:
            break

    # We can fetch users' details 100 at a time.
    if len(follower_ids) > 100 * MAX_USERS_LOOKUP_CALLS:
        follower_id_sample = random.sample(follower_ids,
                                           100 * MAX_USERS_LOOKUP_CALLS)
    else:
        follower_id_sample = follower_ids

    users = fetch_users(follower_id_sample, api, cache)
    return analyze_users(users, ids_fetched=len(follower_ids))


def analyze_timeline(user_id, list_id, api, cache):
    # Timeline-functions are limited to 200 statuses
    if list_id is not None:
        statuses = api.GetListTimeline(list_id=list_id, count=200)
    else:
        statuses = api.GetHomeTimeline(count=200)

    timeline_ids = []
    for s in statuses:
        # Skip the current user's own tweets.
        if s.user.screen_name != user_id:
            timeline_ids.append(s.user.id)

    # Reduce to unique list of ids
    timeline_ids = list(set(timeline_ids))
    users = fetch_users(timeline_ids, api, cache)
    return analyze_users(users, ids_fetched=len(timeline_ids))


# From https://github.com/bear/python-twitter/blob/master/get_access_token.py
def get_access_token(consumer_key, consumer_secret):
    REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
    ACCESS_TOKEN_URL = 'https://api.twitter.com/oauth/access_token'
    AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'

    oauth_client = OAuth1Session(consumer_key, client_secret=consumer_secret,
                                 callback_uri='oob')

    print('\nRequesting temp token from Twitter...\n')

    try:
        resp = oauth_client.fetch_request_token(REQUEST_TOKEN_URL)
    except ValueError as e:
        raise ValueError(
            'Invalid response from Twitter requesting temp token: {0}'.format(
                e))

    url = oauth_client.authorization_url(AUTHORIZATION_URL)

    print('I will try to start a browser to visit the following Twitter page '
          'if a browser will not start, copy the URL to your browser '
          'and retrieve the pincode to be used '
          'in the next step to obtaining an Authentication Token: \n'
          '\n\t{0}'.format(url))

    webbrowser.open(url)
    pincode = input('\nEnter your pincode? ')

    print('\nGenerating and signing request for an access token...\n')

    oauth_client = OAuth1Session(consumer_key, client_secret=consumer_secret,
                                 resource_owner_key=resp.get('oauth_token'),
                                 resource_owner_secret=resp.get(
                                     'oauth_token_secret'),
                                 verifier=pincode)
    try:
        resp = oauth_client.fetch_access_token(ACCESS_TOKEN_URL)
    except ValueError as e:
        msg = ('Invalid response from Twitter requesting '
               'temp token: {0}').format(e)
        raise ValueError(msg)
    #
    # print('''Your tokens/keys are as follows:
    #     consumer_key         = {ck}
    #     consumer_secret      = {cs}
    #     access_token_key     = {atk}
    #     access_token_secret  = {ats}'''.format(
    #     ck=consumer_key,
    #     cs=consumer_secret,
    #     atk=resp.get('oauth_token'),
    #     ats=resp.get('oauth_token_secret')))

    return resp.get('oauth_token'), resp.get('oauth_token_secret')


if __name__ == '__main__':
    import argparse

    p = argparse.ArgumentParser(description='Estimate gender distribution of '
                                            'Twitter friends, followers and'
                                            'your timeline')
    p.add_argument('user_id', nargs=1)
    p.add_argument('--self', help="perform gender analysis on user_id itself",
                   action="store_true")
    p.add_argument('--dry-run', help="fake results", action="store_true")
    args = p.parse_args()
    [user_id] = args.user_id

    consumer_key = (os.environ.get('CONSUMER_KEY') or
                    input('Enter your consumer key: '))

    consumer_secret = (os.environ.get('CONSUMER_SECRET') or
                       input('Enter your consumer secret: '))

    if args.dry_run:
        tok, tok_secret = None, None
    else:
        tok, tok_secret = get_access_token(consumer_key, consumer_secret)

    if args.self:
        if args.dry_run:
            g, declared = 'male', True
        else:
            api = get_twitter_api(
                consumer_key, consumer_secret, tok, tok_secret)
            g, declared = analyze_self(user_id, api)

        print('{} ({})'.format(g, 'declared pronoun' if declared else 'guess'))
        sys.exit()

    print("{:>25s}\t{:>10s}\t{:>10s}\t{:>10s}\t{:>10s}".format(
        '', 'NONBINARY', 'MEN', 'WOMEN', 'UNKNOWN'))

    start = time.time()
    cache = Cache()
    if args.dry_run:
        friends, followers, timeline = dry_run_analysis()
    else:
        api = get_twitter_api(consumer_key, consumer_secret, tok, tok_secret)
        friends = analyze_friends(user_id, None, api, cache)
        followers = analyze_followers(user_id, api, cache)
        timeline = analyze_timeline(user_id, None, api, cache)

    duration = time.time() - start

    for user_type, an in [('friends', friends), ('followers', followers),
                          ('timeline', timeline)]:
        nb, men, women, andy = an.nonbinary.n, an.male.n, an.female.n, an.andy.n

        print("{:>25s}\t{:>10.2f}%\t{:10.2f}%\t{:10.2f}%".format(
            user_type, an.pct('nonbinary'), an.pct('male'), an.pct('female')))

        print("{:>25s}\t{:>10d} \t{:10d} \t{:10d} \t{:10d}".format(
            'Guessed from name:',
            an.guessed('nonbinary'),
            an.guessed('male'),
            an.guessed('female'),
            an.andy.n))

        print("{:>25s}\t{:>10d} \t{:10d} \t{:10d}".format(
            'Declared pronouns:',
            an.declared('nonbinary'),
            an.declared('male'),
            an.declared('female')))

    print("")
    print("Analysis took {:.2f} seconds, cache hit ratio {}%".format(
        duration, cache.hit_percentage))
