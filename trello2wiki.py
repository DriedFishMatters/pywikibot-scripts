# Copyright 2022 Eric Thrift
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""trello2wiki (pywikibot script)

This script reads data from a Trello board and constructs a wiki page for each
label on the board, listing the cards sharing that label and the status of each
(taken from the card comments).

The goal of this script is to produce a "status updates" overview, which allows
all items for a given label to be viewed along with their comments, without
having to open individual cards. It also allows users to track changes to the
project using Special:RecentChanges in the wiki.

Card data are presented as a table with three columns: name, comments, and due
date. The Name field is linked to the matching Trello card, which will contain
full information including the task description.

OPTIONS:

  -key:KEY (required)
        API key for Trello
  -token:TOKEN (reuiqred)
        API token for Trello
  -board:BOARD (required)
        The ID of the Trello board from which to retrieve data
  -category:CATEGORY
        Wikitext string containing the category or categories for the pages,
        e.g., [[Category:Foo]]
  -pagename_prefix:PREFIX
        Prefix to be added to each pagename. You may wish to use a space,
        hyphen, or other separator, e.g., 'Trello '. A page will be generated
        for each label found on the Trello board.
  -preface:PREFACE
        Comment for editors, to be included at the top of each page. This might
        be a warning that the page is generated automatically, e.g.,
        '<!-- DO NOT EDIT! This file is updated by a bot. -->'.
"""

import pywikibot
import requests
import json

import dateutil.parser
from datetime import datetime
import urllib.parse

import markdown
import pypandoc


headers = {
   "Accept": "application/json"
}

header = ('<table><tr><th>Name</th><th>Description</th><th>Comments</th>'
          '<th>Due</th></tr>')

html_footer = '</table><p><a href="{}">View on Trello</a></p>'

# We use Markdown on the comments, so table cell contents are wrapped in <p>s
# Do the same for other cells to get matching margins
row = ( '<tr><td><p><a href="https://trello.com/c/{id}">{name}</a></p></td>'
        '<td>{description}</td><td>{comments}</td><td><p>{due}</p></td>' )

def _read_board(key='', token='', board_url='', headers='', query='', **kwargs):
    query = {
       'key': key,
       'token': token,
       'actions': 'commentCard',
       'fields': ['id', 'name', 'labels', 'desc', 'due']
    }

    response = requests.request(
       "GET",
       board_url,
       headers=headers,
       params=query
    )

    cards = json.loads(response.text)
    labels = {}

    for c in cards:
        data = {}
        data['labels'] = [l['name'] for l in c['labels']]
        comments_list = [markdown.markdown(a['data']['text'])
                for a in c['actions']]
        data['comments'] = ''.join(comments_list) # separate paragraphs
        data['name'] = c.get('name')
        data['id'] = c.get('id')
        data['description'] = markdown.markdown(c.get('desc'))
        data['due'] = c.get('due')
        if data['due']:
            d = dateutil.parser.isoparse(data['due'])
            data['due'] = d.strftime("%Y-%m-%d")
        else:
            data['due'] = '--' # allow sorting by date
        for name in data['labels']:
            if not name in labels.keys():
                labels[name] = []
            labels[name].append(data)
    return labels

def run(*args):
    options = {}
    local_args = pywikibot.handle_args(args)

    site = pywikibot.Site()

    required = ['key', 'token', 'board']
    optional = ['category', 'pagename_prefix', 'preface']

    for option in required:
        options[option] = False
    for option in optional:
        options[option] = ''

    for arg in local_args:
        option, sep, value = arg.partition(':')
        option = option.strip('-')

        if option in optional + required:
            options[option] = value
        else:
            options[option] = True

    for option in required:
        if not options[option]:
            value = pywikibot.input('Please enter a value for ' + option)
            options[option] = value

    board_url = 'https://api.trello.com/1/boards/{}/cards/all'
    filter_url = 'https://trello.com/b/{}?filter=label:'
    trello_url = 'https://trello.com/b/{}'
    options['board_url'] = board_url.format(options['board'])
    options['filter_url'] = filter_url.format(options['board'])
    options['trello_url'] = trello_url.format(options['board'])

    labels = _read_board(**options)

    for (label, cards) in labels.items():
        cards = sorted(cards, key=lambda d: d['due'])
        trello_link = options['filter_url'] + urllib.parse.quote(label)
        out = [header] + [row.format(**card) for card in cards] + [html_footer.format(trello_link)]

        mw = pypandoc.convert_text(''.join(out), 'mediawiki', format='html')
        mw = mw.replace('{|', '{| class="wikitable sortable"')
        mw = mw.replace('|-', '|- style="vertical-align: top;"')
        # optional hack to remove pandoc-applied column widths
        # mw = mw.replace('!width="25%"|', '!')
        pagename = options['pagename_prefix'] + label
        target = pywikibot.Page(site, pagename)
        target.text = '\n\n'.join([options['preface'], mw, options['category']])
        target.save('Updated from {}'.format(options['trello_url']))

if __name__ == '__main__':
    run()
