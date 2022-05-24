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

"""
trelloattachments (pywikibot script)

This script reads data from a Trello board and downloads attachments, one per folder.

OPTIONS:

  -key:KEY (required)
        API key for Trello
  -token:TOKEN (required)
        API token for Trello
  -board:BOARD (required)
        The ID of the Trello board from which to retrieve data
  -category:CATEGORY
        Wikitext string containing the category or categories for the pages,
        e.g., [[Category:Foo]]
"""
import os

import pywikibot
import requests
import json

from slugify import slugify

def download_attachment(headers, url, name, basedir):
    dirname = os.path.join(basedir, name.strip())
    filename = os.path.join(dirname, os.path.basename(url))
    if os.path.exists(filename):
        print('EXISTS: {}'.format(filename))
        return
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    if url.startswith('https://trello.com/1/cards/'):
        r = requests.request("GET", url, headers=headers)
        with open(filename, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=128):
                fd.write(chunk)
    else:
        with open(filename + '.html', 'w') as fd:
            fd.write('<a href="{}">{}</a>'.format(url, name))

def read_board(
    key='', token='', board_url='', dry_run=False,
    headers='', query='', basedir='.',
    **kwargs):

    query = {
       'actions': 'commentCard',
       'fields': ['id', 'name', 'labels', 'desc', 'due'],
       'attachments': 'true'
    }
    headers = {
       "Accept": "application/json",
       "Authorization": 'OAuth oauth_consumer_key="{}", oauth_token="{}"'.format(key, token)
    }

    response = requests.request(
       "GET",
       board_url,
       headers=headers,
       params=query
    )
    try:
        cards = json.loads(response.text)
    except json.decoder.JSONDecodeError:
        print('Error loading data')
        return

    for c in cards:
        name = slugify(c['name'], max_length=80)
        for a in c['attachments']:
            url = a['url']
            if dry_run:
                print(url)
            else:
                download_attachment(headers, url, name, basedir)


def run(*args):
    options = {}
    local_args = pywikibot.handle_args(args)

    required = ['key', 'token', 'board']

    for arg in local_args:
        option, sep, value = arg.partition(':')
        option = option.strip('-')
        options[option] = value

    for option in required:
        if not options.get(option, None):
            value = pywikibot.input('Please enter a value for ' + option)
            options[option] = value

    # use cards/all if we want to include archived items
    options['board_url'] = 'https://api.trello.com/1/boards/{}/cards/all'.format(options['board'])

    read_board(**options)


if __name__ == '__main__':
    run()
