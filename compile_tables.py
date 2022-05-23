"""compile_tables

This pywikibot script reads tables from the pages in a category on the wiki,
then creates a combined table using fields that are in common to those
tables.

OPTIONS:

  -fieldnames:FIELDNAMES (required)
    List of table headers to use. Separate multiple values with semicolons.
  -target:PAGENAME (required)
    Target wiki pagename
  -category:CATEGORY (required)
    The wiki category containing the pages with tables.

"""

import pywikibot
from pywikibot import pagegenerators
from bs4 import BeautifulSoup

def parse_table(html):
    soup = BeautifulSoup(html, 'html.parser')
    data = []
    for table in soup.findAll('table', {'class': 'wikitable'}):
        for row in table.findAll('tr'):
            k = row.th.string or None
            if not k:
                continue
            v = ''.join([s for s in row.td.stripped_strings])
            k = k.lower().strip()
            if k == 'title':
                v = '[[{}]]'.format(v.strip())
            data.append((k, v))
    return dict(data)

def run():
    local_args = pywikibot.handle_args(args)
    required = ['fieldnames', 'category', 'target']
    options = {}

    for arg in local_args:
        option, sep, value = arg.partition(':')
        options[option.strip('-')] = value
    for option in required:
        if not options.get(option, False):
            value = pywikibot.input('Please enter a value for ' + option)
            options[option] = value

    site = pywikibot.Site()
    category = pywikibot.Category(site, options['category'])
    pages = pagegenerators.CategorizedPageGenerator(category)
    rows = []
    rows.append('{| class="wikitable sortable"')
    fieldnames = [f.strip() for f in options['fieldnames'].split(';')]
    rows.append('! ' + ' !! '.join(fieldnames))

    for page in pages:
        html=page._get_parsed_page()
        data = parse_table(html)
        rows.append('|-')
        rows.append('| ' + ' || '.join([data[f] or '' for f in fieldnames]))

    rows.append('|}')
    wikitext = '\r\n'.join(rows)

    target = pywikibot.Page(site, options['target'])
    target.text = wikitext
    target.save('Updated table based on contents of {}'.format(
            options['category']))

if __name__ == '__main__':
    run()
