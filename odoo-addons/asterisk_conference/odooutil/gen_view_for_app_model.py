#!/usr/bin/env python2.7

from os import path
from sys import argv
from jinja2 import Environment, FileSystemLoader

APP_VIEWS_FOLDER = '/Users/max/Dev/odoo/myaddons/asterisk_conference/views/'
THIS_DIR = path.dirname(path.abspath(__file__))


if __name__ == '__main__':
    app = argv[1]
    model = argv[2]
    model_name = argv[2].replace('_', ' ')
    xml = Environment(loader=FileSystemLoader(THIS_DIR)).get_template(
        'views.xml').render(**locals())
    xml_result_file = path.join(APP_VIEWS_FOLDER, '%s.xml' % argv[2])
    if path.exists(xml_result_file):
        raise Exception('File already exists. Refusing.')
    open(xml_result_file, 'w').write(
        """<?xml version="1.0" encoding="utf-8"?>
<openerp><data>

%s

</data></openerp>""" % xml)

