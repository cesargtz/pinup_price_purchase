# -*- coding: utf-8 -*-

from openerp import models, fields, api
import psycopg2

class pinup_price_purchase(models.Model):
    _name = 'pinup.price.purchase'


    _defaults = {'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'reg_code_price'), }
    name = fields.Char('Set Price Reference', required=True, select=True, copy=False,
                            help="Unique number of the set prices")

    purchase_order_id = fields.Many2one('purchase.order')
    partner_id = fields.Many2one('res.partner', readonly=True, related="purchase_order_id.partner_id")
    request_date = fields.Date(required=True, default=fields.Date.today)
    pinup_tons = fields.Float(required=True, eval="False")
    price_usd = fields.Float(compute="_compute_price", store=True)
    tc = fields.Char(compute="_compute_tc", store=True)
    tc_date = fields.Char(compute="_compute_tc_date", store=True)
    price_date = fields.Char(compute="_compute_price_date", store=True)
    tons_reception = fields.Float(compute="_compute_tr", digits=(12,4) ,  store=True)
    tons_invoiced = fields.Float(compute="_compute_ti", digits=(12,4) ,  store=True)
    # tons_invoiced = fields.Many2one('account.invoice','purchase_invoice_rel','purchase_id','invoice_id',)



    @api.multi
    @api.depends('purchase_order_id')
    def _compute_ti(self):
        cr = self.env.cr
        cr.execute("""SELECT invoice_id FROM purchase_invoice_rel WHERE purchase_id = %s """ % (self.purchase_order_id.id))
        x = cr.fetchall()
        print(x)

    @api.one
    @api.depends('purchase_order_id')
    def _compute_tr(self):
        for line in self.env['truck.reception'].search([('contract_id', '=', self.purchase_order_id.name), ('state', '=', 'done')], order='date'):
            self.tons_reception += line['clean_kilos'] / 1000

    @api.one
    @api.depends('purchase_order_id')
    def _compute_tc(self):
        tc = self.env['market.usd'].search([], order='date desc', limit=1)
        for ltc in tc:
            self.tc = ltc['exchange_rate']

    @api.one
    @api.depends('purchase_order_id')
    def _compute_tc_date(self):
        tc = self.env['market.usd'].search([], order='date desc', limit=1)
        for ltc in tc:
            self.tc_date = ltc['date']

    @api.one
    @api.depends('purchase_order_id')
    def _compute_price_date(self):
        tc = self.env['market.price'].search([], order='id desc', limit=1)
        for ltc in tc:
            self.price_date = ltc['date']

    @api.one
    @api.depends('purchase_order_id')
    def _compute_price(self):
        mp = self.env['market.price'].search([], order='id desc', limit=1)
        for lmp in mp:
            self.price_usd = lmp['price_ton']
