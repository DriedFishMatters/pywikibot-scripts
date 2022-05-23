# import datetime
import re
import os
import sys

from cachier import cachier
import pywikibot
from pyzotero import zotero
from bs4 import BeautifulSoup
import json

from datetime import datetime

REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
  <head>
    <link rel="stylesheet" href="report.css">
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <meta name="title" content="{title}"/>
    <meta name="date" content="{date}"/>
    <meta name="description" content="{abstract}"/>
    <meta name="series" content="{series}"/>
    <meta name="index" content="{number}"/>
    <meta name="publisher" content="{institution}"/>
    <meta name="author" content="{authors}"/>
  </head>
  <body class="mw-content content" style="background:white; max-width:100%">
  <section id="frontmatter">
    <p>&copy; Copyright {date} {institution}</p>
    <p>{license}</p>
    <p>{address}</p>
    <p>{acknowledgements}</p>
  </section>
  <section id="abstract" style="page-break-before:always">
    <h3>Abstract</h3>
    <p class="abstract">{abstract}</p>
  </section>
  <section id="content">
  <article>
      {source}
  </article>
  </section>
  </body>
</html>
"""

def fetch_bibliography(zotero_library, refs):
    q = 'https://api.zotero.org/groups/{}/items/{}?format=json&include=bib&style=chicago-note-bibliography&linkwrap=1'

    zot = zotero.Zotero(zotero_library, 'group')
    # zot.add_parameters(content='bib', style='mla')
    zot.add_parameters(format='json', content='bib',
        style='chicago-note-bibliography', linkwrap=1,
        itemKey=','.join(refs))
    items = zot.everything(zot.items())
    bib = '\r\n'.join(sorted(items))
    return bib

def process_metadata(wikitext):
    m = re.search('{{Report metadata(.*?)}}', wikitext,
                flags=re.MULTILINE|re.DOTALL)
    if not m:
        sys.exit("No metadata template found in the source!")
    tpl = m.group(1)
    meta = {}
    for line in tpl.strip().split('|'):
        if not '=' in line:
            continue
        k,sep,v = line.partition('=')
        meta[k.strip()] = v.strip()
    return meta

def wiki_page(pagename):
    site = pywikibot.Site()
    page = pywikibot.Page(site, pagename)

    req = site._simple_request(action='parse', page=page,
        prop="text|images",
        disableeditsection="1", disabletoc="1")
    data = req.submit()
    html = data['parse']['text']['*']
    images = data['parse']['images']
    return (html, page.text, images)

    # return (page._get_parsed_page(), page.text)

def unlink_notes(report):
    soup = BeautifulSoup(report, 'html.parser')

    for n in soup.find_all(class_='noprint'):
        n.decompose()

    for n in soup.find_all(class_='reference-text'):
        for link in n.find_all('a'):
            link.unwrap()

    for ref in soup.find_all('div', 'magnify'):
        ref.decompose()

    # calibre doesn't recognize page-break-after:avoid but it does recognize
    # page-break-inside:avoid
    for h in ('h3', 'h2'):
        for header in soup.find_all(h):
            n1 = header.next_sibling # should be whitespace
            n2 = None
            if n1:
                n2 = n1.next_sibling
            new_tag = soup.new_tag('div')
            new_tag['style'] = 'page-break-inside:avoid'
            header.wrap(new_tag)
            if n1:
                new_tag.append(n1)
            if n2:
                new_tag.append(n2)

    for ref in soup.find_all('div', 'csl-entry'):
        ref.name = 'p' # change citation container from "div" to "p"
        del ref['style'] # remove hard-coded hanging indent
    for thumb in soup.find_all('div', 'thumb'):
        name = thumb.a['href'].partition('File:')[2]
        if int(thumb.img['width']) > 528: # 5.5in @ 96 dpi
            thumb.div['class'] = 'fullwidth'
        del thumb.div['style']
        del thumb.img['height']
        del thumb.img['width']
        del thumb.a['href']
        thumb.img['src'] = name
    return str(soup)


def download_images(images, outdir):
    site = pywikibot.Site()
    # retrieve all the full-resolution images (i.e., not the thumbs)
    for image in images:
        filename = image.replace('File:', '')
        local_path = os.path.join(outdir, filename)
        if not os.path.exists(local_path):
            allimages = site.allimages(start=image, total=1)
            for i in allimages:
                print('downloading {}...'.format(local_path))
                i.download(filename=local_path)


def run(*args):
    options = {}
    local_args = pywikibot.handle_args(args)
    required = ['title', 'outdir', 'license', 'address',
                'acknowledgements']

    for arg in local_args:
        option, sep, value = arg.partition(':')
        options[option.strip('-')] = value
    for option in required:
        if not options.get(option, None):
            value = pywikibot.input('Please enter a value for ' + option)
            options[option] = value

    html, wikitext, images = wiki_page(options['title'])
    metadata = process_metadata(wikitext)
    metadata['license'] = options['license']
    metadata['date'] = datetime.now().strftime('%Y')
    metadata['title'] = options['title']
    metadata['address'] = options['address']
    metadata['acknowledgements'] = options ['acknowledgements']

    download_images(images, options['outdir'])

    if options.get('zotero_library', None):
        pagerefs = re.findall('{{Zotero.*?id=([A-Z0-9]+)', wikitext)
        refs = []
        refs.extend([ref for ref in pagerefs if not ref in refs])
        if len(refs) > 0:
            html = '\r\n\r\n'.join([html,
                '<article class="bibliography"><h2>Bibliography</h2></article>',
                fetch_bibliography(options['zotero_library'], refs)])

    html = REPORT_TEMPLATE.format( source=html, **metadata  )
    html = unlink_notes(html)

    with open(os.path.join(options['outdir'], 'index.html'), 'w') as out:
        out.write(html)

if __name__ == '__main__':
    run()
