"""zotero_recently_added (pywikibot script)

Upload a list of recent items from a Zotero library to a wiki page.

OPTIONS:

  -key:KEY (required)
        API key for Zotero
  -library:TYPE (required)
        'group' or 'user'
  -user_id:ID (required)
        The ID of the Zotero user
  -collection:COLLECTION_ID (required)
        The ID of the collection to retrieve items from
  -pagename:PAGENAME (required)
        Target wiki pagename
  -preface:TEXT
        Text to insert at the top of the page
  -days:DAYS
        Return items added in the most recent DAYS

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


def _html2wiki(input):
    """Convert the html returned by Zotero to wikitext."""
    w = pypandoc.convert_text(input, 'mediawiki', format='html').strip()
    w = ' '.join(w.split()) #conflate whitespaces
    w = w.replace('<div', '<span').replace('</div>', '</span>')
    return w

def _process_zotero_item(zot, item):
    """Convert bibliography entry to a wikitext list item."""
    out = ['# ']
    out.append("'''[{}]''' ".format(item['data'].get('itemType', '')))
    out.append(_html2wiki(item['bib']))

    if item['meta'].get('numChildren', 0) > 0:
        attachments = zot.children(item['key'])

        for a in attachments:
            if a['data'].get('itemType', None) == 'note':
                continue
            if a['data'].get('url', None):
                link = a['data']['url']
            else:
                # api should give "links.enclosure.href" but this is absent?
                link = a['links']['self']['href'] + '/file/view'
            out.append('[{} {}]'.format(link, a['data']['title']))

    return ' '.join(out)


def bibliography(user_id=None, key=None, library='group', collection=None,
                days=None, **kwargs):
    """Generate a wikitext bibliography via the Zotero API."""

    out = []

    zot = zotero.Zotero(user_id, library, api_key=key)
    zot.add_parameters(
                include='bib,data',
                style='chicago-author-date',
                linkwrap='0',
                sort='dateAdded',
                direction='desc'
            )
    try:
        items = zot.everything(zot.collection_items(collection))
    except HTTPError:
        sys.exit('HTTP Error')

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    for item in items:
        if item['data'].get('itemType', '') in ('note', 'attachment'):
            continue
        if days:
            dateAdded = datetime.datetime.fromisoformat(item['data']['dateAdded'].replace("Z", "+00:00"))
            d = (now - dateAdded).total_seconds()
            delta = 86400*int(days)
            if d > delta:
                continue
        out.append(_process_zotero_item(zot, item))
    return '\n'.join(out)


def run(*args):
    options = {}
    local_args = pywikibot.handle_args(args)

    required = ['key', 'library', 'user_id', 'collection', 'pagename']

    for arg in local_args:
        option, sep, value = arg.partition(':')
        option = option.strip('-')
        options[option] = value

    for option in required:
        if not options.get(option, None):
            value = pywikibot.input('Please enter a value for ' + option)
            options[option] = value

    site = pywikibot.Site()
    mw = bibliography(**options)

    if 'preface' in options:
        mw = '\n\n'.join([options['preface'], mw])
    target = pywikibot.Page(site, options['pagename'])

    target.text = mw
    target.save('Updated from Zotero library')

if __name__ == '__main__':
    run()
