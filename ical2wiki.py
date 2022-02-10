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

"""ical2wiki (pywikibot script)

Script to read an iCalendar file, accessible from a public URL, and update a
wiki page containing a listing of upcoming events from the calendar file.

OPTIONS:

  -calendar:CALENDAR (required)
        URL of the input iCalendar file
  -pagename:PAGENAME (required)
        Target wiki pagename
"""

import sys
import requests
import dateutil.parser
from datetime import datetime, date
import urllib.parse

from icalendar import Calendar, __version__
import pypandoc
import pywikibot

def html2wiki(input):
    w = pypandoc.convert_text(input, 'plain', format='html').strip()
    w = ' '.join(w.split()) #conflate whitespaces
    return w

def get_calendar(calendar=None, **kwargs):
    """Read an iCalendar file from the URL at `calendar`.
    Return formatted wikitext version of the events listing.
    """

    if not calendar:
        return ''
    tpl = "=== {time}. {summary}===\n{description}"
    r = requests.request('GET', calendar)
    cal = Calendar.from_ical(r.text)
    out = []

    events = {datetime.strftime(event.get('dtstart').dt, "%Y-%m-%d"):
                event for event in cal.walk('vevent')}

    for t, event in sorted(events.items()):
        end = str(event.get('dtend').dt)
        today = str(date.today())
        if end < today:
            continue
        time = datetime.strftime(event.get('dtstart').dt, '%Y-%m-%d')

        summary = event.get('summary', ' ')
        description = event.get('description', ' ')

        out.append( tpl.format(
            summary=html2wiki(summary),
            time=time,
            description=html2wiki(description) ) )
    return '\n\n'.join(out)

def run(*args):
    options = {}
    local_args = pywikibot.handle_args(args)

    required = ['calendar', 'pagename']

    for arg in local_args:
        option, sep, value = arg.partition(':')
        option = option.strip('-')
        options[option] = value

    for option in required:
        if not options.get(option, None):
            value = pywikibot.input('Please enter a value for ' + option)
            options[option] = value

    site = pywikibot.Site()
    mw = get_calendar(**options)
    if 'preface' in options:
        mw = '\n\n'.join([options['preface'], mw])
    target = pywikibot.Page(site, options['pagename'])
    target.text = mw
    target.save('Updated from iCal file')

if __name__ == '__main__':
    run()
