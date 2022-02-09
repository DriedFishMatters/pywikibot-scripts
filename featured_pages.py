"""featured_pages (pywikibot script)

Locate the most recently added items in a featured category, and post a page
to the wiki listing those pages with their summaries. Pages are linked using
the canonical URL, so the generated wiki page can be redistributed outside the
wiki. Requires Extension:TextExtracts.

The use case scenario motivating this tool is the generation of a "featured
pages" section for an email newsletter. Existing tools are too verbose
(Special:RecentChanges) or provide only page titles with no summary ("Dynamic
page list"). Summaries are available through Extension:TextExtracts, which is
required for this script to work properly, but can only be accessed from the
MediaWiki API. Generating the page content as a bot is more flexible than
creating a new MediaWiki extension with the same functionality, and it can be
managed by a user who does not have administrative permissions over the wiki
installation.

USAGE:

    python pywikibot.py featured_pages [options]

OPTIONS:

  -category:CATEGORY (required)
        The name of the category to list pages from
  -pagename:PAGENAME (required)
        Target wiki pagename
  -preface:TEXT
        Text to insert at the top of the page
  -limit:LIMIT
        Number of pages to return.

LICENSE:

    Copyright 2022 Eric Thrift

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import sys
import requests
import datetime

from pyzotero import zotero
import pypandoc
import pywikibot

def html2wiki(input):
    w = pypandoc.convert_text(input, 'mediawiki', format='html').strip()
    w = ' '.join(w.split()) #conflate whitespaces
    w = w.replace('<div', '<span').replace('</div>', '</span>')
    return w

def featured(category='', limit=None, **kwargs):
    site = pywikibot.Site()
    tpl = "===[{canonicalurl} {title}]===\n{extract}"
    cat = pywikibot.page.Category(site, category)
    if limit:
        limit = int(limit)
    else:
        limit = 30
    pages = cat.newest_pages(total=limit) # gives recent edits, not creation
    out = []
    titles = [page.title() for page in pages]

    extracts = pywikibot.data.api.PropertyGenerator(site=site, prop='extracts|info', titles=titles, exsentences=5, exintro=1, exsectionformat='plain', explaintext=1, inprop='url')

    for e in extracts:
        out.append(tpl.format(**e))

    return '\n'.join(out)

def run(*args):
    options = {}
    local_args = pywikibot.handle_args(args)

    required = ['category', 'pagename']

    for arg in local_args:
        option, sep, value = arg.partition(':')
        option = option.strip('-')
        options[option] = value

    for option in required:
        if not options.get(option, None):
            value = pywikibot.input('Please enter a value for ' + option)
            options[option] = value

    site = pywikibot.Site()
    mw = featured(**options)

    if 'preface' in options:
        mw = '\n\n'.join([options['preface'], mw])
    target = pywikibot.Page(site, options['pagename'])

    target.text = mw
    target.save('Updated by featuredpages bot')

if __name__ == '__main__':
    run()
