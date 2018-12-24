import os
import pickle
import random
import re
import string
import sys
import warnings
import webbrowser

import twitter  # pip install python-twitter
import sexmachine.detector as gender  # pip install SexMachine
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


allchars = string.maketrans('', '')
nonletter = allchars.translate(allchars, string.letters).replace(' ', '')


def rm_punctuation(s):
    return string.translate(s.encode("utf-8"), None, nonletter).strip()


def declared_gender(description):
    dl = description.lower()
    if ('pronoun.is' in dl and
        'pronoun.is/she' not in dl and
        'pronoun.is/he' not in dl):
        return 'nonbinary'

    guesses = set()
    for p, g in [('non binary', 'nonbinary'),
                 ('non-binary', 'nonbinary'),
                 ('nonbinary', 'nonbinary'),
                 ('enby', 'nonbinary'),
                 ('genderqueer', 'nonbinary'),
                 ('man', 'male'),
                 ('male', 'male'),
                 ('boy', 'male'),
                 ('guy', 'male'),
                 ('woman', 'female'),
                 ('female', 'female'),
                 ('girl', 'female'),
                 ('gal', 'female'),
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
                 ]:
        for text in (r'\b' + p + r'\b',
                     r'\b' + p + r'/',
                     r'\b' + p + r' /',
                     r'pronoun\.is/' + p):
            if re.compile(text).search(dl):
                guesses.add(g)

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
        attr = getattr(self, gender)
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

    return friends, followers


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


def analyze_self(user_id, consumer_key, consumer_secret,
                 oauth_token, oauth_token_secret):
    api = get_twitter_api(consumer_key, consumer_secret,
                          oauth_token, oauth_token_secret)

    users = api.UsersLookup(screen_name=[user_id])

    return analyze_user(users[0])


def analyze_friends(user_id, list_id, consumer_key, consumer_secret,
                    oauth_token, oauth_token_secret):
    api = get_twitter_api(consumer_key, consumer_secret,
                          oauth_token, oauth_token_secret)

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

    users = []
    for ids in batch(friend_id_sample, 100):
        users.extend(api.UsersLookup(ids))

    return analyze_users(users, ids_fetched=len(friend_ids))


def analyze_followers(user_id, consumer_key, consumer_secret,
                      oauth_token, oauth_token_secret):
    api = get_twitter_api(consumer_key, consumer_secret,
                          oauth_token, oauth_token_secret)
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

    users = []
    for ids in batch(follower_id_sample, 100):
        users.extend(api.UsersLookup(ids))

    return analyze_users(users, ids_fetched=len(follower_ids))


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
    pincode = raw_input('\nEnter your pincode? ')

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
                                            'Twitter friends and followers')
    p.add_argument('user_id', nargs=1)
    p.add_argument('--self', help="perform gender analysis on user_id itself",
                   action="store_true")
    p.add_argument('--dry-run', help="fake results", action="store_true")
    args = p.parse_args()
    [user_id] = args.user_id

    consumer_key = (os.environ.get('CONSUMER_KEY') or
                    raw_input('Enter your consumer key: '))

    consumer_secret = (os.environ.get('CONSUMER_SECRET') or
                       raw_input('Enter your consumer secret: '))

    if args.dry_run:
        tok, tok_secret = None, None
    else:
        tok, tok_secret = get_access_token(consumer_key, consumer_secret)

    if args.self:
        if args.dry_run:
            g, declared = 'male', True
        else:
            g, declared = analyze_self(user_id, consumer_key, consumer_secret,
                                       tok, tok_secret)

        print('{} ({})'.format(g, 'declared pronoun' if declared else 'guess'))
        sys.exit()

    print("{:>25s}\t{:>10s}\t{:>10s}\t{:>10s}\t{:>10s}".format(
        '', 'NONBINARY', 'MEN', 'WOMEN', 'UNKNOWN'))

    if args.dry_run:
        friends, followers = dry_run_analysis()
    else:
        friends = analyze_friends(user_id, None, consumer_key, consumer_secret,
                                  tok, tok_secret)
        followers = analyze_followers(user_id, consumer_key, consumer_secret,
                                      tok, tok_secret)

    for user_type, an in [('friends', friends), ('followers', followers)]:
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
