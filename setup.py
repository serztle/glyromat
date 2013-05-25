#!/usr/bin/env python

from distutils.core import setup

setup(name='Glyromat',
      version='0.1',
      description='Metadata chooser for music',
      author='serztle',
      author_email='serztle@googlemail.com',
      url='https://github.com/serztle/glyromat',
      package_data={'glyromat': ['*.glade']},
      packages=['glyromat']
)
