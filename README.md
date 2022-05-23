# DFM pywikibot scripts

Collection of pywikibot scripts for managing data in a MediaWiki-powered wiki
and synchronizing with other platforms.

## Installation

Checkout or download to the `myscripts` directory inside `pywikibot2/scripts/userscripts`. Then add to your user-config.py:

```
user_script_paths = ['scripts.userscripts.myscripts']
```

## Scripts

### blog2wiki

This script retrieves an RSS feed and posts it to a specified page on the wiki.
The feed can then be embedded on other wiki pages as needed.

#### Usage

```
  python pwb.py blog2wiki [options]
```

#### Options

```
-pagename:PAGENAME (required)
    Page on the wiki where the feed data will be posted.
-blog_url:URL (required)
    URL for the blog feed
-days:DAYS (optional; default: 45)
    Blog posts published within this past number of days will be
    posted to the wiki
```

### compile_tables

This script reads tables from the pages in a category on the wiki,
then creates a combined table using fields that are in common to those
tables.


#### Usage

```
  python pwb.py compile_tables [options]
```

#### Options

```
-fieldnames:FIELDNAMES (required)
    List of table headers to use. Separate multiple values with semicolons.
-target:PAGENAME (required)
    Target wiki pagename
-category:CATEGORY (required)
    The wiki category containing the pages with tables.
```

### docx2wiki

Uploads the content of a Word document to the wiki. Reads an input Word document (docx); uploads new images from the document to the wiki, using an image fingerprint hash algorithm to compare images in the document to those already on the wiki and detect visually similar images (e.g., cropped or resized versions of the same image); converts Zotero citations to wiki templates; then uploads the document text to the wiki. Some manual cleanup of the wiki text is generally required. Metadata for newly imported images will also need to be completed.

If using Zotero citations, the requirements are:
  1. The references must come from a group library that is accessible to
     the public
  2. The citations must be converted using the "Switch word processors"
     function in Zotero prior to processing

For image processing to work, the ALT text for each image MUST be set in
Word.

#### Usage

```
  python pwb.py docx2wiki [options]
```

#### Options

```
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
```

### featured_pages

Locate the most recently added items in a featured category, and post a page
to the wiki listing those pages with their summaries. Pages are linked using
the canonical URL, so the generated wiki page can be redistributed outside the
wiki. Requires [Extension:TextExtracts](https://www.mediawiki.org/wiki/Extension:TextExtracts).

The use case scenario motivating this tool is the generation of a "featured
pages" section for an email newsletter. Existing tools are too verbose
(Special:RecentChanges) or provide only page titles with no summary ("Dynamic
page list"). Summaries are available through Extension:TextExtracts, which is
required for this script to work properly, but can only be accessed from the
MediaWiki API. Generating the page content as a bot is more flexible than
creating a new MediaWiki extension with the same functionality, and it can be
managed by a user who does not have administrative permissions over the wiki
installation.

#### Usage

```
    python pywikibot.py featured_pages [options]
```

#### Options

```
  -category:CATEGORY (required)
        The name of the category to list pages from
  -pagename:PAGENAME (required)
        Target wiki pagename
  -preface:TEXT
        Text to insert at the top of the page
  -limit:LIMIT
        Number of pages to return.
```

### ical2wiki

Script to read an iCalendar file, accessible from a public URL, and update a
wiki page containing a listing of upcoming events from the calendar file.

#### Usage

```
    python pywikibot.py ical2wiki [options]
```

#### Options

```
  -calendar:CALENDAR (required)
        URL of the input iCalendar file
  -pagename:PAGENAME (required)
        Target wiki pagename
```

### report

Downloads a page from the wiki along with high-resolution versions of all the images embedded in that page, retrieves data for any citations on that page that are linked to the Zotero group library, then saves the page as an html document containing front matter, standalone content, notes and bibliography, and table of contents. The resulting document can be used as input for generation of any of the output formats supported by Calibre, including EPUB and PDF.

#### Usage

```
  python pwb.py report [options]
```

#### Options

```
-title:TITLE (required)
    The title of the wiki page containing the report
-outdir:DIR (required)
    The path on disk to a directory in which the output should be saved.
-license:LICENSE (required)
    Copyright/license text, in html format.
-address:ADDRESS (required)
    Address of the publisher, in html format.
-acknowledgements:ACKNOWLEDGEMENTS (required)
    Acknowledgements text for the frontmatter, in html format.
-zotero_library:LIBRARY_ID (optional)
    The ID for a Zotero group library from which citations will be retrieved.
```

### trello2wiki

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

#### Usage

```
    python pywikibot.py trello2wiki [options]
```

#### Options

```
-key:KEY (required)
    API key for Trello
-token:TOKEN (reuiqred)
    API token for Trello
-board:BOARD (required)
    The ID of the Trello board from which to retrieve data
-category:CATEGORY
    Wikitext string containing the category or categories for the pages,
    e.g., '[[Category:Foo]]'
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
```

### trelloattachments

This script reads data from a Trello board and downloads attachments, one per folder.

#### Usage

```
  python pwb.py trelloattachments [options]
```

#### Options

```
-key:KEY (required)
    API key for Trello
-token:TOKEN (required)
    API token for Trello
-board:BOARD (required)
    The ID of the Trello board from which to retrieve data
-category:CATEGORY
    Wikitext string containing the category or categories for the pages,
    e.g., [[Category:Foo]]
```

### wiki2html

Script for exporting wiki pages in a given category to static html pages
for public distribution.

#### Usage

```
  python pwb.py wiki2html [options]
```

#### Options

```
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
```

### zotero_bibliography

Upload a list of recent items from a Zotero library to a wiki page.

#### Usage

```
  python pwb.py zotero_bibliography [options]
```

#### Options

```
-key:KEY (required)
    API key for Zotero
-library_type:TYPE (required)
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
```

### zotero_recently_added

Upload a list of recent items from a Zotero library to a wiki page.

#### Usage

```
  python pwb.py zotero-recently-added [options]
```

#### Options

```
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
```

### zotero2wiki

Upload a formatted list of items from a Zotero collection to a wiki page.

#### Usage

```
  python pwb.py zotero2wiki [options]
```

#### Options

```
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
```

## Copying

Copyright 2022, Eric Thrift

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

## Credits

This script was originally written for the
[Dried Fish Matters](https://driedfishmatters.org) project, supported
by the [Social Sciences and Humanities Research Council of
Canada](http://sshrc-crsh.gc.ca).
