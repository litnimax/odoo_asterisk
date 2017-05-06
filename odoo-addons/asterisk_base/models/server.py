from odoo import api, models, fields, _


class AsteriskServer(models.Model):
    _name = 'asterisk.server'

    name = fields.Char(required=True)
    host = fields.Char(required=True)
    note = fields.Text()
    ami_port = fields.Integer(required=True, default=5038, string='AMI Port')
    http_port = fields.Integer(required=True, default=8088, string='HTTP Port')
    https_port = fields.Integer(required=True, default=8089, string='HTTPS Port')
    use_https = fields.Boolean(string='Use HTTPS')
    certificate = fields.Text(string='TLS Certificate')
    key = fields.Text(string='TLS Private Key')
