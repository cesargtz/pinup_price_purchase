# -*- coding: utf-8 -*-

from openerp import models, fields, api

class pinup_price_purchase(models.Model):
    _name = 'pinup.price.purchase'

    purchase_order_id = fields.Many2one('purchase.order')
    request_date = fields.Date(required=True, default=fields.Date.today)
    pinup_tons = fields.Float()
    price = fields.Float()
    tc = fields.Char(compute="_compute_tc")
    tc_date = fields.Char()



    @api.one
    @api.onchange('price','purchase_order_id')
    def _compute_tc(self):
        tc = self.env['market.usd'].search([], order='date desc', limit=1)
        for ltc in tc:
            self.tc = ltc['exchange_rate']


class pinup_price_purchase_inherit(models.Model):
    _inherit = 'purchase.order'

    pinup_price_purchase = fields.Many2one('pinup.price.purchase','purchase_order_id')
