"""Blog2wiki (pywikibot script)

This script retrieves an RSS feed and posts it to a specified page on the wiki.
The feed can then be embedded on other wiki pages as needed.

"""

import pywikibot
import datetime
import feedparser
from email.utils import parsedate
import time

def blog_feed(blog_url, max_age):
    tpl = '===[{link} {title}]===\n{summary}'

    start_time = datetime.datetime.now() - datetime.timedelta(seconds=max_age)
    start_time = start_time.replace(microsecond=0).isoformat()

    now = datetime.datetime.now(tz=datetime.timezone.utc)

    feed = feedparser.parse(blog_url)
    print(feed.status)
    posts = feed['entries']
    out = []

    for post in posts:
        pub_date = parsedate(post['published']) # Wed, 16 Dec 2020 19:20:03 +0000
        pub_date_ts = datetime.datetime.fromtimestamp(time.mktime(pub_date), tz=datetime.timezone.utc)
        delta = (now-pub_date_ts).total_seconds()
        if delta > max_age:
            break
        out.append(tpl.format(**post))
    return '\n\n'.join(out)

def run(*args):
    local_args = pywikibot.handle_args(args)
    required = ['pagename', 'blog_url']
    options = {}

    for arg in local_args:
        option, sep, value = arg.partition(':')
        options[option.strip('-')] = value
    for option in required:
        if not options.get(option, False):
            value = pywikibot.input('Please enter a value for ' + option)
            options[option] = value

    max_age = 86400*(int(options.get('days', '45')))
    site = pywikibot.Site()
    target = pywikibot.Page(site, options['pagename'])
    target.text = blog_feed(options['blog_url'], max_age) + '\n\n__NOTOC__'
    target.save('Imported from blog feed at {}'.format(options['blog_url']))

if __name__ == '__main__':
    run()
