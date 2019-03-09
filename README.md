Gender Distribution of Twitter Friends and Followers
====================================================

[Twitter analytics](https://analytics.twitter.com) estimates the gender ratio of
your followers, but it doesn't tell you about those you follow--your
Twitter "friends"--and it doesn't let you analyze other people's friends and
followers. Neither does it notice gender-nonbinary users. This tool attempts to
fill the gap. It guesses the gender of your friends and followers by looking in
their Twitter bios for pronoun announcements like "she/her", or else guessing
based on first name.

I've deployed it for public use since June 2016 at
[proporti.onl](https://www.proporti.onl).

Read my article about this code: **["72% Of The People I Follow On Twitter Are
Men."](https://emptysqua.re/blog/gender-of-twitter-users-i-follow/)**

[Tweet me your thoughts](https://twitter.com/jessejiryudavis).

Install
-------

This script requires Python 2.7, and the packages listed in `requirements.txt`.

```
python2.7 -m pip install -r requirements.txt
```

Command-line Use
----------------

Pass a Twitter username to analyze the user's friends and followers:

```
python2.7 analyze.py jessejiryudavis
```

Test
----

From the repository root directory:

```
python2.7 -m unittest discover -v
```

Website
-------

Start a Flask server for testing:

```
CONSUMER_KEY=foo CONSUMER_SECRET=bar COOKIE_SECRET=baz python2.7 server.py 8000
```
