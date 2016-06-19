from flask import Flask, request, render_template
from wtforms import Form, StringField

from analyze import analyze_followers
from analyze import analyze_friends

app = Flask('twitter-gender-ratio')


class AnalyzeForm(Form):
    user_id = StringField('Twitter User Name')


@app.route('/', methods=['GET', 'POST'])
def index():
    form = AnalyzeForm(request.form)
    results = {}
    error = None
        try:
            results = {'friends': analyze_friends(form.user_id),
                       'followers': analyze_followers(form.user_id)}
        except Exception as exc:
            error = exc
    if request.method == 'POST' and form.validate() and form.user_id.data:

    return render_template('index.html',
                           form=form, results=results, error=error)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('port', nargs=1, type=int)
    args = parser.parse_args()
    [port] = args.port

    app.run(port=port, debug=args.debug)
