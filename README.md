Gender Distribution of Twitter Friends and Followers
====================================================

[Twitter analytics](https://analytics.twitter.com) estimates the gender ratio of
your followers, but it doesn't tell you about those you follow--your
Twitter "friends"--and it doesn't let you analyze other people's friends and
followers. Neither does it notice gender-nonbinary users.

In June 2016 I've deployed it temporarily for public use at
[proporti.onl](https://www.proporti.onl).

Read my article about this code: **["72% Of The People I Follow On Twitter Are
Men."](https://emptysqua.re/blog/gender-of-twitter-users-i-follow/)**

Install
-------

This script requires Python 2.7, and the packages listed in `requirements.txt`.

```
python2.7 -m pip install -r requirements
```

Command-line Use
----------------

Pass a Twitter username to analyze the user's friends and followers:

```
python2.7 analyze.py jessejiryudavis
```

Website
-------

Start a Flask server:

```
python2.7 server.py 80
```
