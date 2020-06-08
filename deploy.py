#!/usr/bin/env python
import argparse
import os

import requests

my_domain = "www.proporti.onl"
username = "emptysquare"

parser = argparse.ArgumentParser()
parser.add_argument(
    "token",
    metavar="PYTHON_ANYWHERE_TOKEN",
    help="A Python Anywhere API token for your account",
)

args = parser.parse_args()

print("Rsync files....")
os.system(
    "rsync -rv --exclude '*.pyc' *"
    " emptysquare@ssh.pythonanywhere.com:www.proporti.onl/"
)

print("Reinstall dependencies....")
os.system(
    "ssh emptysquare@ssh.pythonanywhere.com"
    " '~/my-venv3/bin/pip install -U -r ~/www.proporti.onl/requirements.txt'"
)

print("Restarting....")
uri = "https://www.pythonanywhere.com/api/v0/user/{uname}/webapps/{dom}/reload/"
response = requests.post(
    uri.format(uname=username, dom=my_domain),
    headers={"Authorization": "Token {token}".format(token=args.token)},
)

if response.status_code == 200:
    print("All OK")
else:
    print(
        "Got unexpected status code {}: {!r}".format(
            response.status_code, response.content
        )
    )
