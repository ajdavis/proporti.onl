Gender Ratio of Twitter Friends and Followers
=============================================

[Twitter analytics](https://analytics.twitter.com) estimates the gender ratio of
your followers, but it doesn't tell you the ratio of those you follow--your
Twitter "friends"--and it doesn't let you analyze other people's friends and
followers.

In June 2016 I've deployed it temporarily for public use at
[emptysquare.pythonanywhere.com](http://emptysquare.pythonanywhere.com).

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

TODO: This deployment is very prone to Twitter rate-limiting.
