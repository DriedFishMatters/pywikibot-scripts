# DFM pywikibot scripts

Collection of pywikibot scripts for managing data in a MediaWiki-powered wiki
and synchronizing with other platforms.

## Installation

Checkout or download to the `myscripts` directory inside `pywikibot2/scripts/userscripts`. Then add to your user-config.py:

```
user_script_paths = ['scripts.userscripts.myscripts']
```

## Scripts

### `zotero_recently_added`

Upload a list of recent items from a Zotero library to a wiki page.

USAGE:

```
  python pwb.py zotero-recently-added [options]
```

OPTIONS:

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

## `featured_pages`

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

USAGE:

```
    python pywikibot.py featured_pages [options]
```

OPTIONS:

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
