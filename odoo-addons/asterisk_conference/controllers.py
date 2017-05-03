# -*- coding: utf-8 -*-
from openerp import http

# class AsteriskConference(http.Controller):
#     @http.route('/asterisk_conference/asterisk_conference/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/asterisk_conference/asterisk_conference/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('asterisk_conference.listing', {
#             'root': '/asterisk_conference/asterisk_conference',
#             'objects': http.request.env['asterisk_conference.asterisk_conference'].search([]),
#         })

#     @http.route('/asterisk_conference/asterisk_conference/objects/<model("asterisk_conference.asterisk_conference"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('asterisk_conference.object', {
#             'object': obj
#         })