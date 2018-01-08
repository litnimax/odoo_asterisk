from openerp import models, fields, api, _

class ExtensionsConf(models.Model):
    _name = 'asterisk.conf.extensions'
    _Description = 'Context Name'
    _inherit = 'asterisk.conf'

    items = fields.One2many(comodel_name='asterisk.context',
                            inverse_name='context_id')
    name = fields.Char(compute='_get_name')


    @api.multi
    def _get_name(self):
        for rec in self:
            rec.name = rec.category

    @api.model
    def create(self, vals):
        vals.update({
            'filename': 'extensions.conf',
            'category': vals.get('category'),
            'var_name': 'switch',
            'var_val': 'realtime',
            'cat_metric': 1,
            'var_metric': 1,
        })
        created = super(ExtensionsConf, self).create(vals)
        return created




class Context(models.Model):
    _name = 'asterisk.context'
    _Description = 'Context'
    _rec_name = 'context'
    _order = 'exten,priority'

    context_id = fields.Many2one('asterisk.conf.extensions', ondelete='cascade')
    context = fields.Char(related='context_id.category', store=True, index=True,
                          size=40, readonly=True)
    exten = fields.Char(required=True, size=40)
    priority = fields.Integer(required=True,
                              default=lambda self: self._get_next_priority())
    app = fields.Char(required=True, size=40)
    appdata = fields.Char(size=256)


    #_sql_constraints = [
    #    ('context_exten_prio_uniq', 'UNIQUE(context,exten,priority)',
    #            _('This priority already exists in this exten and context!')),
    #]


    def _get_next_priority(self):
        last = self.env['asterisk.context'].search([
            ('context', '=', self.context),
            ('exten', '=', self.exten)
        ], order='priority', limit=1)
        if last:
            return last.priority + 1
        else:
            return 1
