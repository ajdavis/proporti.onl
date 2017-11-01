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
                return g

    return 'andy'  # Don't know.


def analyze_user(user, verbose=False):
    with warnings.catch_warnings():
        # Suppress unidecode warning "Surrogate character will be ignored".
        warnings.filterwarnings("ignore")
        g = declared_gender(user.description)
        if g == 'andy':
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

        return g


def analyze_users(users, verbose=False):
    result = {'nonbinary': 0,
              'men': 0,
              'women': 0,
              'andy': 0}

    for user in users:
        g = analyze_user(user, verbose)

        if g == 'nonbinary':
            result['nonbinary'] += 1
        elif g in ('male', 'mostly_male'):
            result['men'] += 1
        elif g in ('female', 'mostly_female'):
            result['women'] += 1
        else:
            result['andy'] += 1

    return result


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


def analyze_self(user_id, consumer_key, consumer_secret,
                 oauth_token, oauth_token_secret):
    api = get_twitter_api(consumer_key, consumer_secret,
                          oauth_token, oauth_token_secret)

    users = api.UsersLookup(screen_name=[user_id])

    return analyze_user(users[0])


def analyze_friends(user_id, consumer_key, consumer_secret,
                    oauth_token, oauth_token_secret, verbose):
    if verbose:
      print "\nAnalyzing friends."

    result = {'ids_fetched': 0, 'ids_sampled': 0}
    api = get_twitter_api(consumer_key, consumer_secret,
                          oauth_token, oauth_token_secret)

    nxt = -1
    friend_ids = []
    for _ in range(MAX_GET_FRIEND_IDS_CALLS):
        nxt, prev, data = api.GetFriendIDsPaged(screen_name=user_id,
                                                cursor=nxt)
        friend_ids.extend(data)
        if nxt == 0 or nxt == prev:
            break

    result['ids_fetched'] = len(friend_ids)

    # We can fetch users' details 100 at a time.
    if len(friend_ids) > 100 * MAX_USERS_LOOKUP_CALLS:
        friend_id_sample = random.sample(friend_ids,
                                         100 * MAX_USERS_LOOKUP_CALLS)
    else:
        friend_id_sample = friend_ids

    result['ids_sampled'] = len(friend_id_sample)
    users = []
    for ids in batch(friend_id_sample, 100):
        users.extend(api.UsersLookup(ids))

    result.update(analyze_users(users, verbose))
    return result


def analyze_followers(user_id, consumer_key, consumer_secret,
                      oauth_token, oauth_token_secret, verbose):
    if verbose:
      print "\nAnalyzing followers."

    result = {'ids_fetched': 0, 'ids_sampled': 0}
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

    result['ids_fetched'] = len(follower_ids)

    # We can fetch users' details 100 at a time.
    if len(follower_ids) > 100 * MAX_USERS_LOOKUP_CALLS:
        follower_id_sample = random.sample(follower_ids,
                                           100 * MAX_USERS_LOOKUP_CALLS)
    else:
        follower_id_sample = follower_ids

    result['ids_sampled'] = len(follower_id_sample)
    users = []
    for ids in batch(follower_id_sample, 100):
        users.extend(api.UsersLookup(ids))

    result.update(analyze_users(users, verbose))
    return result


def div(num, denom):
    if denom:
        return num / float(denom)

    return 0


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
    p.add_argument('--verbose', help="print user analysis",
                   action="store_true")
    p.add_argument('--self', help="perform gender analysis on user_id itself",
                   action="store_true")
    args = p.parse_args()
    [user_id] = args.user_id

    consumer_key = (os.environ.get('CONSUMER_KEY') or
                    raw_input('Enter your consumer key: '))

    consumer_secret = (os.environ.get('CONSUMER_SECRET') or
                       raw_input('Enter your consumer secret: '))

    tok, tok_secret = get_access_token(consumer_key, consumer_secret)

    if args.self:
        print(analyze_self(user_id, consumer_key, consumer_secret,
                           tok, tok_secret))
        sys.exit()

    data = [
        ('friends', analyze_friends(user_id, consumer_key, consumer_secret,
                                    tok, tok_secret, args.verbose)),
        ('followers', analyze_followers(user_id, consumer_key, consumer_secret,
                                        tok, tok_secret, args.verbose)),
    ]

    print("{:>10s}\t{:>10s}\t{:>10s}\t{:>10s}\t{:>10s}".format(
        '', 'nonbinary', 'men', 'women', 'unknown'))

    for user_type, users in data:
        nonbinary, men, women, andy = (
            users['nonbinary'], users['men'], users['women'], users['andy'])

        print("{:>10s}\t{:>10d}\t{:10d}\t{:10d}\t{:10d}".format(
            user_type, nonbinary, men, women, andy))

        print("{:>10s}\t{:>10.2f}\t{:10.2f}\t{:10.2f}".format(
            '',
            div(100 * nonbinary, nonbinary + men + women),
            div(100 * men, nonbinary + men + women),
            div(100 * women, nonbinary + men + women)))
