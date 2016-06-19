import os
import pickle
import random
import string

import twitter                          # pip install python-twitter
import sexmachine.detector as gender    # pip install SexMachine
from unidecode import unidecode         # pip install unidecode


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


def analyze_users(users, verbose=False):
    men = 0
    women = 0
    andy = 0

    for user in users:
        for name, country in [
            (user.name.split()[0], 'usa'),
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

        if g == 'male':
            men += 1
        elif g == 'female':
            women += 1
        else:
            andy += 1

    return men, women, andy


def batch(it, size):
    for i in range(0, len(it), size):
        yield it[i:i + size]


def get_twitter_api(oauth_token, oauth_token_secret):
    return twitter.Api(
        consumer_key="XpukwJDDIXoF1iBcTAJMXYthg",
        consumer_secret="wVuS3bj6hHCuoTkMEqAHjl0l2bODcLRIXkvs2JzOYxfGERYskq",
        access_token_key=oauth_token,
        access_token_secret=oauth_token_secret,
        sleep_on_rate_limit=True)


MAX_GET_FRIEND_IDS_CALLS = 5
MAX_GET_FOLLOWER_IDS_CALLS = 5
MAX_USERS_LOOKUP_CALLS = 10


def analyze_friends(user_id, oauth_token, oauth_token_secret):
    result = {'ids_fetched': 0, 'ids_sampled': 0}
    api = get_twitter_api(oauth_token, oauth_token_secret)

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

    result['men'], result['women'], result['andy'] = analyze_users(users)
    return result


def analyze_followers(user_id, oauth_token, oauth_token_secret):
    result = {'ids_fetched': 0, 'ids_sampled': 0}
    api = get_twitter_api(oauth_token, oauth_token_secret)
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

    result['men'], result['women'], result['andy'] = analyze_users(users)
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Estimate gender ratio of Twitter friends and followers')
    parser.add_argument('user_id', nargs=1)
    args = parser.parse_args()
    [user_id] = args.user_id

    tok = "131044458-jjzsC9RNoWkICI2C622VFO3u2XETYRKLY4WtDSR6"
    tok_secret = "UBkM1GOxmELqKvuUa8qXQ8qQJkYcmTq3644hs3w8fKNyk"

    print('\n')
    print("{:>10s}\t{:>10s}\t{:>10s}\t{:>10s}".format(
        '', 'men', 'women', 'undetermined'))

    for user_type, users in [
        ('friends', analyze_friends(user_id, tok, tok_secret)),
        ('followers', analyze_followers(user_id, tok, tok_secret)),
    ]:
        men, women, andy = users['men'], users['women'], users['andy']
        print("{:>10s}\t{:10d}\t{:10d}\t{:10d}".format(
            user_type, men, women, andy))

        print("{:>10s}\t{:10.2f}\t{:10.2f}".format(
            '',
            100 * men / float(men + women),
            100 * women / float(men + women)))
