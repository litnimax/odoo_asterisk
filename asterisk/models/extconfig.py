from openerp import models, fields, api, _

class Conf(models.Model):
    _name = 'asterisk.conf'
    _description = 'Conf File'

    filename = fields.Char(required=True)
    category = fields.Char(required=True)
    var_name = fields.Char(required=True)
    var_val = fields.Char(required=True)
    cat_metric = fields.Integer(default=1)
    var_metric = fields.Integer(default=1)
    commented = fields.Integer(default=0)

