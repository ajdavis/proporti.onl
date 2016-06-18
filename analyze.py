import os
import pickle
import string

import twitter                          # pip install python-twitter
import sexmachine.detector as gender    # pip install SexMachine
from unidecode import unidecode         # pip install unidecode


api = twitter.Api(
    consumer_key="XpukwJDDIXoF1iBcTAJMXYthg",
    consumer_secret="wVuS3bj6hHCuoTkMEqAHjl0l2bODcLRIXkvs2JzOYxfGERYskq",
    access_token_key="131044458-jjzsC9RNoWkICI2C622VFO3u2XETYRKLY4WtDSR6",
    access_token_secret="UBkM1GOxmELqKvuUa8qXQ8qQJkYcmTq3644hs3w8fKNyk")

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


def analyze_friends(user_id):
    return analyze_users(api.GetFriends(user_id))


def analyze_followers(user_id):
    return analyze_users(api.GetFollowers(user_id))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Estimate gender ratio of Twitter friends and followers')
    parser.add_argument('user_id', nargs=1)
    args = parser.parse_args()
    [user_id] = args.user_id

    print('\n')
    print("{:>10s}\t{:>10s}\t{:>10s}\t{:>10s}".format(
        '', 'men', 'women', 'undetermined'))

    for user_type, users in [
        ('friends', analyze_friends(user_id)),
        ('followers', analyze_followers(user_id)),
    ]:
        men, women, andy = users
        print("{:>10s}\t{:10d}\t{:10d}\t{:10d}".format(
            user_type, men, women, andy))

        print("{:>10s}\t{:10.2f}\t{:10.2f}".format(
            '',
            100 * men / float(men + women),
            100 * women / float(men + women)))
