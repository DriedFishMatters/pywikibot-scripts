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

# REQUIREMENTS:
# pip install pillow==2.6.1 imagehash==0.3
# https://realpython.com/fingerprinting-images-for-near-duplicate-detection/

"""docx2wiki (pywikibot script)

Uploads the content of a Word document to the wiki. Reads an input Word document (docx); uploads new images from the document to the wiki, using an image fingerprint hash algorithm to compare images in the document to those already on the wiki and detect visually similar images (e.g., cropped or resized versions of the same image); converts Zotero citations to wiki templates; then uploads the document text to the wiki. Some manual cleanup of the wiki text is generally required. Metadata for newly imported images will also need to be completed.

If using Zotero citations, the requirements are:
  1. The references must come from a group library that is accessible to
     the public
  2. The citations must be converted using the "Switch word processors"
     function in Zotero prior to processing

OPTIONS:

  -pagename:NAME (required)
        The name of the page to save the document.
  -input:DOCX (required)
        Path to the docx document to be converted to wikitext.
  -db:DATABASE
        Path to a database in which to store image hashes. Do not include
        the extension.
  -dump:true
        Dump the image database to stdout.
  -nohashes:true
        Skip retrieving image hashes
  -dry:true
        Don't upload anything to the wiki; simply process and output any
        messages as normal up to that point.

"""
import os
import sys
import shutil
import pywikibot
import json

import dateutil.parser
from datetime import datetime
import urllib.parse
import tempfile
import hashlib

import markdown
import pypandoc
import mammoth
import tempfile
import imagehash
import dbm
from PIL import Image
from bs4 import BeautifulSoup, UnicodeDammit
from pywikibot.specialbots import UploadRobot

def wrap_block(tag):
    s = tag.get_text().splitlines()
    return ' '.join([string.strip() for string in s])

def process_citations(soup):
    for link in soup.find_all('a'):
        if not 'zotero' in link.get('href', ''):
            continue
        # if not link.string:
        #     continue
        s = wrap_block(link)
        if not s.startswith('ITEM CSL_CITATION'):
            continue
        j = json.loads(s[18:]) # remove prefix 'ITEM CSL_CITATION'
        items = list()
        for c in j['citationItems']:
            uri = c['uris'][0]
            # e.g., "http://zotero.org/groups/2183860/items/UF2HZUAK"
            uri_parts = uri.split('/')
            id = uri_parts[6]
            group = uri_parts[4]
            citation = '{{{{Zotero|group={}|id={}'.format(group, id)
            for x in ('prefix', 'locator', 'suffix'):
                if c.get(x, None):
                    citation += '|{}={}'.format(x, c[x])
            citation += '}}'
            items.append(citation)
        # We use a modified Chicago note style with no final punctuation
        link.string = '<ref>' + '; '.join(items) + '</ref>'
        del link['href']
        link.name = 'span'
    return

def convert_inline_markup(soup):
    for match in soup.findAll('i'):
        match.string = "''{}''".format(match.get_text())
    for match in soup.findAll('b'):
        match.string = "'''{}'''".format(match.get_text())
    for match in soup.findAll('h1'):
        match.string = "\n\n={}=".format(wrap_block(match))
    for match in soup.findAll('h2'):
        match.string = "\n\n=={}==".format(wrap_block(match))
    for match in soup.findAll('h3'):
        match.string = "\n\n==={}===".format(wrap_block(match))
    for match in soup.findAll('h4'):
        match.string = "\n\n===={}====".format(wrap_block(match))
    for match in soup.findAll('li'):
        if match.parent.name == 'ol':
            match.string = "\n# {}".format(wrap_block(match))
        else:
            match.string = "\n* {}".format(wrap_block(match))
    return

def remove_zotero_notices(soup):
    if soup.p.get_text() == 'ZOTERO_TRANSFER_DOCUMENT':
        soup.p.decompose()
        soup.p.decompose() #second paragraph
    for p in soup.findAll('p'):
        if p.get_text().startswith('DOCUMENT_PREFERENCES'):
            p.decompose()


def parse_table(table):
    headers = table.findAll('th')
    for th in headers:
        if th.get('colspan', None):
            th.insert(0, 'colspan="{}" | '.format(th['colspan']))
    rows = [[th.text.strip(' \r\n') for th in headers]]
    trows = table.findAll('tr')
    for row in trows:
        columns = row.findAll('td')
        for td in columns:
            if td.get('colspan', None):
                td.insert(0, 'colspan="{}" | '.format(td['colspan']))
        rows.extend([[td.text.strip(' \r\n') for td in columns]])
    return rows

def format_table(data):
    t = ['\n\n{| class="wikitable"']
    t.extend(['! ' + th for th in data[0]])
    for row in data[1:]:
        t.append('|-')
        t.extend(['| ' + td for td in row])
    t.append('|}\n')
    return '\n'.join(t)

def convert_tables(soup):
    for table in soup.findAll('table'):
         # match.extract()
         data = parse_table(table)
         table.string = format_table(data)

def convert_images(soup):
    for img in soup.findAll('img'):
        img.string = '[[{}|thumb|center|600px|{}]]'.format(img['src'], img['alt'])
        img.name = 'p'

"""
We want the sha1 hashes of all thumbnail images on the wiki.
We could cache this, so that we take a generator (all the source images) and request them one at a time, only jpeg and png.

Options:
1. Incrementally update a local hash index. This would take a long time to do the first time, but would be efficient (server calculation, not bandwidth).
2. Implement a server script that hashes files on disk and that is updated with a cron job. This would take no bandwidth. It could use glob instead of the api to identify images. Requires direct server access. Would provide a lookup api.

self.site.allimages()

@cachier
get_image(hash)

- lookup fingerprint in the database (gives filename). If missing:
    - request the list of all images.
    - update the database. foreach image not in the database:
        - calculate hash (fingerprint)
        - store in database
        - return

https://realpython.com/fingerprinting-images-for-near-duplicate-detection/

"""

def get_local_image_hash(img_file):
    pil_image = Image.open(img_file)
    h = str(imagehash.dhash(pil_image))
    return h

def get_hashes(database):
    with dbm.open(database, flag='r') as db:
        hashes = {db[k].decode('utf-8'): k.decode('utf-8') for k in db.keys()}
    return hashes

_wmf_extensions = {
    "image/x-wmf": ".wmf",
    "image/x-emf": ".emf",
}


class ImageWriter(object):
    def __init__(self, base, hashes):
        self._output_dir = tempfile.gettempdir()
        self._image_number = 1
        self._base = base
        self._hashes = hashes

    def __call__(self, element):
        extension = element.content_type.partition("/")[2]
        image_filename = "{0}_{1}.{2}".format(self._base, self._image_number, extension)
        image_path = os.path.join(self._output_dir, image_filename)
        with open(image_path, "wb") as image_dest:
            with element.open() as image_source:
                shutil.copyfileobj(image_source, image_dest)

        # FIXME: Convert wmf to png
        # FIXME: Give an error if the image is not png or jpeg
        self._image_number += 1
        image_hash = get_local_image_hash(image_path)

        remote = self._hashes.get(image_hash, None)
        if remote:
            src = remote.decode('utf-8')
        else:
            if not element.alt_text:
                sys.exit("Abort: Must set ALT text for image {}.".format(self._image_number))
            bot = UploadRobot(image_path, description=element.alt_text,
                              keep_filename=True,
                              aborts=True,
                              always=True,
                              summary='Imported from docx')
            bot.run()
            src = 'File:{}'.format(image_filename)
            # FIXME: Write hash to the local database here

        return {"src": src,
                "alt": element.alt_text,
                }


def convert_docx(docx, db_file):
    style_map = """
    p[style-name='Caption'] => p.figcaption:fresh
    """
    hashes = get_hashes(db_file)
    with open(docx, "rb") as docx_fileobj:
        base = os.path.basename(docx).rpartition(".")[0]
        convert_image = mammoth.images.img_element(ImageWriter(base, hashes))
        output_filename = "{0}.html".format(base)
        result = mammoth.convert(
            docx_fileobj,
            style_map=style_map,
            convert_image=convert_image,
        )
    return result.value

def dump_database(db_file):
    with dbm.open(db_file, flag='r') as db:
        for k in db.keys():
            print(",".join([db[k].decode('utf-8'), k.decode('utf-8')]))

def get_image_hashes(db_file):
    """Look for unknown images on the wiki and generate hashes for them."""
    tmp = tempfile.gettempdir()
    with dbm.open(db_file, flag='c') as db:
        known_titles = [k.decode('utf-8') for k in db.keys()]
        for img in site.allimages():
            title = img.title()
            if not title.rpartition('.')[2].lower() in ('jpeg', 'jpg', 'png'):
                continue
            if title in known_titles:
                # print("Already in database: {}".format(title))
                continue
            print("Not in database: {}".format(title))
            img_file = os.path.join(tmp, 'mw_tmpfile')
            dl = img.download(filename=img_file)
            if not dl:
                sys.exit('Could not download {}'.format(img.title()))
            try:
                h = get_local_image_hash(img_file)
                print(h)
                db[title] = h
            except:
                sys.exit('Error processing hash for {}'.format(title))

def run(*args):
    options = {}
    local_args = pywikibot.handle_args(args)
    required = ['pagename', 'input']

    for arg in local_args:
        option, sep, value = arg.partition(':')
        options[option.strip('-')] = value
    for option in required:
        if not options.get(option, False):
            value = pywikibot.input('Please enter a value for ' + option)
            options[option] = value

    db = options.get('db', os.path.expanduser(os.path.join('~', 'DFM_images')))
    # set as a global so we can access in the Mammoth sub-functions,
    # which can't take additional parameters
    global site
    site = pywikibot.Site()

    if options.get('dump', None):
        dump_database(db)
        sys.exit()
    ## GET IMAGE HASHES
    if not options.get('nohashes', None):
        get_image_hashes(db)

    html = convert_docx(docx=options['input'], db_file=db)

    # convert to wikitext
    soup = BeautifulSoup(html, 'html.parser')
    remove_zotero_notices(soup)
    process_citations(soup)
    convert_inline_markup(soup)
    convert_images(soup)
    for match in soup.findAll('p'):
        match.string = '\n\n' + wrap_block(match)
    convert_tables(soup)
    s = soup.get_text().strip()
    mw = '\n'.join([line for line in s.split('\n')])

    # now send to mediawiki
    if not options.get('dry', None):
        target = pywikibot.Page(site, options['pagename'])
        target.text = mw
        base = os.path.basename(options['input'])
        target.save('Imported from docx file {}'.format(base))

if __name__ == '__main__':
    run()

"""
This basically works, though the formatting is a bit unreliable. Particularly if the authors have used tables for layout, or if there are no semantic headers, etc. The HTML conversion is lossy; we might actually have more success just copying and pasting into the visual editor.

We could treat this as an image export utility only for now: extract the images from the docx, see if we already have them on the wiki, and if not upload them. The main challenge is that we don't actually have access to the image descriptions unless we embed those within the alt text, and that requires manual intervention. This would mainly be useful if we have a lot of images in a Word document that all need to be uploaded, with the following conditions:

1. We don't know if the file is a cropped or scaled version of something that is already on the wiki.
2. We just want to upload the images, not the text.
3. We have too many files to upload via the upload wizard.

In fact, we can just copy and paste the images one at a time, and that will prompt for upload.

For report generation purposes, the advantage of going through the wiki is that it enforces consistent semantic formatting and enables reuse of text, citations, and images. It's difficult to do this without manual processing. If we upload these images

This actually works reasonably well, but pandoc (or mammoth?) struggles on some of the tables it seems (it renders them as text). Choosing a different table layout seems to work, but that is silly. UPDATE: It seems to be resolved by "autofit".

DOES NOT WORK. We have a gridspan=2 element in the source docx.
<table>
    <tr>
        <td><p>Dried fish supply chain stage</p></td>
        <td><p>Weights and measurements used</p></td>
        <td colspan="2"><p>Amount</p></td>
    </tr>
    <tr>
        <td><p>Purchasing the raw material (fish)</p></td>
        <td><p>20 kg basket of Lactarius×6 baskets</p></td>
        <td><p>₹600 × 6 = ₹3600</p></td>
    </tr>
    <tr>
        <td><p>Salt per basket</p></td>
        <td><p>5 kg for 20 kg fish   ×6 baskets</p></td>
        <td><p>5×20×₹4 = ₹400</p></td>
    </tr>
    <tr>
        <td><p>Transportation cost</p></td>
        <td><p>150 per basket</p></td>
        <td><p>₹150</p></td>
    </tr>
    <tr>
        <td><p>Weight reduction by 60-65%</p></td>
        <td><p>7-8 kg yield from 20 kg ×6 baskets</p></td>
        <td><p>45 kg</p></td>
    </tr>
    <tr>
        <td><p>Selling price at Karwar wholesale market</p></td>
        <td><p>A basket of 45 kg of fish</p></td>
        <td><p>₹6500-₹7000</p></td>
    </tr>
</table>

Weights, measurements and prices along the dried Lactarius supply chain at Tadadi

WORKS
<table><tr><td><p>Dried fish supply chain stage</p></td><td><p>Weights and measurements used</p></td><td><p>Amount</p></td></tr><tr><td><p>Purchasing the raw material (fish)</p></td><td><p>20 kg basket of Lactarius×6 baskets</p></td><td><p>₹600 × 6 = ₹3600</p></td></tr><tr><td><p>Salt per basket</p></td><td><p>5 kg for 20 kg fish   ×6 baskets</p></td><td><p>5×20×₹4 = ₹400</p></td></tr><tr><td><p>Transportation cost</p></td><td><p>150 per basket</p></td><td><p>₹150</p></td></tr><tr><td><p>Weight reduction by 60-65%</p></td><td><p>7-8 kg yield from 20 kg ×6 baskets</p></td><td><p>45 kg</p></td></tr><tr><td><p>Selling price at Karwar wholesale market</p></td><td><p>A basket of 45 kg of fish</p></td><td><p>₹6500-₹7000</p></td></tr></table>



For report generation:
- Create a cover page as an image (svg with text and image content) --> upload to the wiki using a tool, or else generate with a cgi script
-

"""
