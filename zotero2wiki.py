"""zotero2wiki (pywikibot script)

Upload a formatted list of items from a Zotero collection to a wiki page.

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
"""

import sys
import pywikibot
from pyzotero import zotero

TEMPLATE = """{{{{report
| cover = {cover}
| title = {title}
| authors = {authors}
| series title = {seriesTitle}
| report type = {reportType}
| report number = {reportNumber}
| abstract = {abstractNote}
| attachments = {attachments}
| zotero = {zotero_url}
| url = {url}
| DOI = {DOI}
}}}}"""


def zotero_request(user_id=None, key=None, library_type='group',
        collection=None, **kwargs):
    """Retrieve data from the Zotero API."""

    zot = zotero.Zotero(user_id, library_type, api_key=key)
    zot.add_parameters(
                sort='dateAdded',
                direction='desc'
            )
    try:
        items = zot.everything(zot.collection_items(collection))
    except HTTPError:
        sys.exit('HTTP Error')
    return zot, items

def process_item(zot, i):
    if i['data']['itemType'] in ['note', 'attachment']:
        return None
    data = {}
    fields = ['title', 'seriesTitle', 'reportType', 'reportNumber',
            'abstractNote', 'url', 'cover', 'DOI', 'attachments']
    for f in fields:
        data[f] = i['data'].get(f, '')
    authors_list = []
    for c in i['data']['creators']:
        if c.get('name', None):
            authors_list.append(c['name'])
        else:
            authors_list.append(' '.join([c.get('firstName', ''),  c.get('lastName', '')]))
    data['zotero_url'] = i['links']['alternate']['href']
    data['authors'] = ', '.join(authors_list)
    extra_fields = i['data']['extra'].splitlines()
    for e in extra_fields:
        k, sep, v = e.partition(':')
        data[k.lower()] = v.strip()

    if i['meta'].get('numChildren', 0) > 0:
        attachments = zot.children(i['key'])
        attachments_list = []
        for a in attachments:
            if a['data'].get('itemType', None) == 'note':
                continue
            if a['data'].get('url', None):
                link = a['data']['url']
            else:
                link = a['links']['self']['href'] + '/file/view'
            attachments_list.append('[{} {}]'.format(link, a['data']['title']))
        data['attachments'] = ' | '.join(attachments_list)

    return data


def run(*args):
    local_args = pywikibot.handle_args(args)
    required = ['key', 'library_type', 'user_id', 'collection', 'pagename']
    options = {}

    for arg in local_args:
        option, sep, value = arg.partition(':')
        options[option.strip('-')] = value
    for option in required:
        if not options.get(option, False):
            value = pywikibot.input('Please enter a value for ' + option)
            options[option] = value

    site = pywikibot.Site()
    mw = []

    tpl = options.get('template', TEMPLATE)

    zot, items = zotero_request(**options)
    for i in items:
        data = process_item(zot, i)
        if data:
            mw.append(tpl.format(**data))

    if options.get('preface', None):
        mw = [options['preface']] + mw

    if options.get('dry-run', None):
        print('\n\n'.join(mw))
    else:
        target = pywikibot.Page(site, options['pagename'])
        target.text = '\n\n'.join(mw)
        target.save('Updated from Zotero collection {collection}'.format(**options))

if __name__ == '__main__':
    run()
