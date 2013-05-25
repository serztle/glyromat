#!/usr/bin/env python
# encoding: utf-8

"""Glyromat

Usage:
    glyromat [options]
    glyromat --help|-h

Options:
    --force-utf8            BLA [default: No]
    --language LANG         BLA [default: en]
    --language-aware-only   BLA [default: No]
    --min-size SIZE         BLA [default: -1]
    --max-size SIZE         BLA [default: -1]
    --qsratio QSRATIO       BLA [default: 0.9]
    --max-per-plugins NUM   BLA [default: -1]
    --image-viewer VIEWER   BLA [default: sxiv %s]
    --preset_artist ARTIST      [default: DevilDriver]
    --preset_album ALBUM        [default: Beast]
    --preset_title TITLE        [default: Beast]
    --preset_database PATH      [default: ]
    --redirects NUM             [default: 3]
    --timeout SECONDS           [default: 20]
    --parallel NUM              [default: 0]
    --verbosity NUM             [default: 0]
    --fuzzyness NUM             [default: 4]
    --proxy PROXY               [default: ]
    --lang_aware_only           [default: No]
    --normalization NORM        [default: artist,album,title,moderate]
"""

from docopt import docopt
from glyromat import Glyromat
from gi.repository import Gtk

arguments = docopt(__doc__, version='Glyromat 0.1')

arguments['--img-size'] = [int(arguments['--min-size']), int(arguments['--max-size'])]
arguments['--qsratio'] = float(arguments['--qsratio'])

for option in ['max-per-plugins', 'redirects', 'timeout', 'parallel', 'verbosity', 'fuzzyness']:
    option = '--' + option
    arguments[option] = int(arguments[option])

arguments['--normalization'] = arguments['--normalization'].split(',')

settings = {
    'preset_artist': 'DevilDriver',
    'preset_album': 'Beast',
    'preset_title': 'Beast'
}
for key, value in arguments.items():
    settings[key[2:].replace('-', '_')] = value

main = Glyromat(settings)
main.show_all()
main.connect('destroy', Gtk.main_quit)
Gtk.main()
