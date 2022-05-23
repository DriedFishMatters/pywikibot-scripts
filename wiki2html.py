"""wiki2html (pywikibot script)

Script for exporting wiki pages in a given category to static html pages
for public distribution

USAGE:

    python pwb.py wiki2html [options]

OPTIONS:

  -category:CATEGORY (required)
    The name of the category to list pages from
  -out:PATH (required)
    The path on disk to the directory for output
  -base:BASENAME (required)
    The base path for urls in HTML output
  -sitename:SITENAME (required)
    The name of the site, to be included in the html header
  -template:TEMPLATE (required)
    HTML template with python template fields, to be used in generating
    the output. See wiki2html_sample-web-template.txt. The required variables
    are sitename, title, and content (i.e., page body text).

"""

import os
import pywikibot
from slugify import slugify
from bs4 import BeautifulSoup
import requests
import urllib


INDEX_TEMPLATE = """<dt><a href="{url}">{title}</a></dt>
<dd class="extract">{extract}</dd>
"""

# use these to avoid being blocked by mod_security
# we download images directly instead of via the API
HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:55.0) Gecko/20100101 Firefox/55.0',
}

def index(site, titles):
    out = []
    titles = [title for title in titles if not title.startswith('File:')]
    extracts = pywikibot.data.api.PropertyGenerator(
            site=site,
            prop='extracts|info',
            titles=titles,
            exsentences=5,
            exintro=1,
            exsectionformat='plain',
            explaintext=1)

    for e in extracts:
        e['url'] = slugify(e['title']) + '.html'
        out.append(INDEX_TEMPLATE.format(**e))

    return ' '.join(out)

def postprocess(html, titles, out, basename):
    soup = BeautifulSoup(html, 'html.parser')
    for elem, attr in [('div', 'magnify'), ('span', 'mw-editsection')]:
        for e in soup.find_all(elem, attr):
            e.decompose()
    # remove internal links if not in list
    for a in soup.find_all('a'):
        if a['href'].startswith('#'):
            continue
        if 'external' in a.get('class', ''):
            continue
        if 'homepage' in a.get('class', ''):
            continue
        title = a.get('title', None)
        if title and title in titles:
            a['href'] = slugify(a['title']) + '.html'
        else:
            a.unwrap()
    for img in soup.find_all('img'):
        src = img.get('src', None)
        if not src:
            continue
        filename = os.path.basename(urllib.parse.unquote(src))
        local_filename = os.path.join(out, filename)
        if not os.path.exists(local_filename):
            remote_url = urllib.parse.urljoin(basename, src)
            print("Retrieving {}...".format(remote_url))
            data = requests.get(remote_url, headers=HTTP_HEADERS)
            with open(local_filename, 'wb') as img_file:
                img_file.write(data.content)
        img['src'] = urllib.parse.quote(filename)
    return str(soup)


def run(*args):
    required = ['category', 'out', 'base', 'sitename', 'template']
    options = {}

    local_args = pywikibot.handle_args(args)
    for arg in local_args:
        option, sep, value = arg.partition(':')
        options[option.strip('-')] = value
    for option in required:
        if not options.get(option, False):
            value = pywikibot.input('Please enter a value for ' + option)
            options[option] = value
    with open(options['template'], 'r') as template_file:
        tpl = template_file.read()
    site = pywikibot.Site()
    cat = pywikibot.page.Category(site, options['category'])
    pages = cat.articles()
    titles = [page.title() for page in pages]
    # reset the generator
    pages = cat.articles()

    with open(os.path.join(options['out'], 'index.html'), 'w',
                encoding='utf-8') as h:
        h.write(tpl.format(title=options['sitename'],
                content=index(site, titles), **options ))

    for page in pages:
        print('Processing {}...'.format(page.title()))
        html = tpl.format( title=page.title(),
                content=page._get_parsed_page(),
                **options )
        html = postprocess(html, titles, options['out'], options['base'])
        pagename = slugify(page.title()) + '.html'
        with open(os.path.join(options['out'], pagename), 'w', encoding='utf-8') as h:
            h.write(html)


if __name__ == '__main__':
    run()
