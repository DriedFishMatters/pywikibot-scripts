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
  -lists:true
        Create a page for each list on the board.
  -outline:true
        Output a definition list with lists and cards for the entire board,
        and save to a single page.
  -labels:true
        Create a page for each label on the board.

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

html_footer = '</table>'
# <a href="{}">View on Trello</a></p></html>

# We use Markdown on the comments, so table cell contents are wrapped in <p>s
# Do the same for other cells to get matching margins
row = ( '<tr><td><p><a href="https://trello.com/c/{id}">{name}</a></p></td>'
        '<td>{description}</td><td>{comments}</td><td><p>{due}</p></td></tr>' )

def _get_lists(key='', token='', lists_url='', headers='', query='', **kwargs):
    query = {
       'key': key,
       'token': token,
    }

    response = requests.request(
       "GET",
       lists_url,
       headers=headers,
       params=query
    )

    lists = json.loads(response.text)
    return {l['id']: l['name'] for l in lists}


def _read_board(key='', token='', board_url='', headers='', query='', **kwargs):

    query = {
       'key': key,
       'token': token,
       'actions': 'commentCard',
       'fields': ['id', 'name', 'labels', 'desc', 'due', 'idList']
    }

    response = requests.request(
       "GET",
       board_url,
       headers=headers,
       params=query
    )

    cards = json.loads(response.text)
    labels = {}
    lists = {}

    for c in cards:
        data = {}
        data['labels'] = [l['name'] for l in c['labels']]
        comments_list = [markdown.markdown(a['data']['text']) for a in
            c['actions']]
        data['comments'] = '<HR>'.join(comments_list) # separate paragraphs
        data['name'] = c.get('name')
        data['id'] = c.get('id')
        data['description'] = markdown.markdown(c.get('desc'))
        data['due'] = c.get('due')
        if data['due']:
            d = dateutil.parser.isoparse(data['due'])
            data['due'] = d.strftime("%Y-%m-%d")
        else:
            data['due'] = '--' # allow sorting by date

        listname = c['idList']
        if not listname in lists.keys():
            lists[listname] = []
        lists[listname].append(data)

        for name in data['labels']:
            if not name in labels.keys():
                labels[name] = []
            labels[name].append(data)
    return labels, lists


def _generate(target, cards, header, footer, options):
    out = [header] + [row.format(**card) for card in cards] + [footer]
    mw = pypandoc.convert_text(' '.join(out), 'mediawiki', format='html')
    mw = mw.replace('{|', '{| class="wikitable sortable"')
    mw = mw.replace('|-', '|- style="vertical-align: top;"')
    # optional hack to remove pandoc-applied column widths
    mw = mw.replace('!width="25%"|', '!')
    mw = mw.replace('\n\n\n', '\n\n')

    target.text = '\n\n'.join([options['preface'], mw, options['category']])
    target.save('Updated from {}'.format(options['trello_url']))

def run(*args):
    print("running...")
    options = {}
    local_args = pywikibot.handle_args(args)

    site = pywikibot.Site()

    required = ['key', 'token', 'board']
    optional = ['category', 'pagename_prefix', 'preface', 'lists', 'labels']

    for option in optional:
        options[option] = ''

    for arg in local_args:
        option, sep, value = arg.partition(':')
        option = option.strip('-')
        options[option] = value

    for option in required:
        if not options.get(option, False):
            value = pywikibot.input('Please enter a value for ' + option)
            options[option] = value

    print(options)
    board_url = 'https://api.trello.com/1/boards/{}/cards/open'
    lists_url = 'https://api.trello.com/1/boards/{}/lists/open'
    filter_url = 'https://trello.com/b/{}?filter=label:'
    trello_url = 'https://trello.com/b/{}'
    options['board_url'] = board_url.format(options['board'])
    options['filter_url'] = filter_url.format(options['board'])
    options['trello_url'] = trello_url.format(options['board'])
    options['lists_url'] = lists_url.format(options['board'])

    labels, lists = _read_board(**options)

    header = (  '<table><tr><th>Name</th><th>Description</th>'
                '<th>Comments</th><th>Due</th></tr>')

    if options.get('lists', None):
        print('processing lists...')
        listnames = _get_lists(**options)
        for (list, cards) in lists.items():
            if not listnames.get(list, None): # hidden, etc.
                continue
            trello_link = board_url
            pagename = ' '.join([options['pagename_prefix'], listnames[list]])
            footer = html_footer.format(trello_link)
            target = pywikibot.Page(site, pagename)
            _generate(target, cards, header, footer, options)

    if options.get('outline', None):
        listnames = _get_lists(**options)
        pagename = ' '.join([options['pagename_prefix'], 'outline'])
        target = pywikibot.Page(site, pagename)
        dl = ['<dl>']
        for (list, cards) in lists.items():
            if not listnames.get(list, None): # hidden, etc.
                continue
            dl.append('<dt>{}</dt>'.format(listnames[list]))
            dl.extend(['<dd>{}</dd>'.format(c['name']) for c in cards])
        dl.append('</dl>')
        mw = pypandoc.convert_text(' '.join(dl), 'mediawiki', format='html')
        target.text = '\n\n'.join([options['preface'], mw, options['category']])
        target.save('Updated from {}'.format(options['trello_url']))

    if options.get('labels', None):
        for (label, cards) in labels.items():
            cards = sorted(cards, key=lambda d: d['due'])
            trello_link = options['filter_url'] + urllib.parse.quote(label)
            footer = html_footer.format(trello_link)
            pagename = ' '.join([options['pagename_prefix'], label])
            target = pywikibot.Page(site, pagename)
            _generate(target, cards, header, footer, options)

if __name__ == '__main__':
    run()
