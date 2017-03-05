#!/bin/sh

rsync -rv --exclude '*.pyc' * emptysquare@ssh.pythonanywhere.com:www.proporti.onl/
open https://www.pythonanywhere.com/user/emptysquare/webapps/#tab_id_www_proporti_onl
