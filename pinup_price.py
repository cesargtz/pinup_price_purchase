# -*- coding: utf-8 -*-

from openerp import models, fields, api, exceptions
import psycopg2


class pinup_price_purchase(models.Model):
    _inherit = ['mail.thread']
    _name = 'pinup.price.purchase'

    _defaults = {'name': lambda obj, cr, uid, context: obj.pool.get(
        'ir.sequence').get(cr, uid, 'reg_code_price'), }
    name = fields.Char('Set Price Reference', required=True, select=True, copy=False,
                       help="Unique number of the set prices")

    purchase_order_id = fields.Many2one('purchase.order')
    partner_id = fields.Many2one(
        'res.partner', readonly=True, related="purchase_order_id.partner_id", store=True)
    tons_contract = fields.Float(compute="_compute_tons")
    request_date = fields.Date(required=True, default=fields.Date.today)
    pinup_tons = fields.Float(required=True, eval="False")
    price_usd = fields.Float(compute="_compute_price", store=True)
    price_usd_mn = fields.Float()
    tc = fields.Char(compute="_compute_tc", store=True)
    tc_mn = fields.Float()
    price_mx = fields.Float(compute="_compute_mx")
    tc_date = fields.Char(compute="_compute_tc_date", store=True)
    price_date = fields.Char(compute="_compute_price_date", store=True)
    tons_reception = fields.Float(
        compute="_compute_tr", digits=(12, 3),  store=True)
    tons_invoiced = fields.Float(
        compute="_compute_ti", digits=(12, 3),  store=True)
    tons_priced = fields.Float(
        compute="_compute_priced", digits=(12, 3),  store=True)



    state = fields.Selection([
        ('draft', "Draft"),
        ('confirmed', "Confirmed"),
    ], default='draft')

    @api.one
    @api.depends("purchase_order_id")
    def _compute_tons(self):
        self.tons_contract = self.purchase_order_id.tons_hired

    @api.multi
    def action_draft(self):
        self.state = 'draft'

    @api.multi
    def action_confirmed(self):
        self.state = 'confirmed'

    @api.constrains('pinup_tons')
    def _check_tons(self):
        tons_available = self.tons_reception + self.pinup_tons - self.tons_priced
        if self.pinup_tons > tons_available:
            raise exceptions.ValidationError(
                "No tienes las suficientes toneladas para preciar.")

    @api.multi
    @api.depends('purchase_order_id')
    def _compute_ti(self):
        cr = self.env.cr
        cr.execute("""SELECT invoice_id FROM purchase_invoice_rel WHERE purchase_id = %d """ % (
            self.purchase_order_id.id))
        invoice_ids = cr.fetchall()
        tons_billing = 0
        if invoice_ids:
            for invoice_id in invoice_ids:
                for only_id in invoice_id:
                    data = self.env['account.invoice'].search(
                        [('id', '=', only_id), ('state', 'in', ['open', 'paid'])])
                    for line in data:
                        tons_billing += line['tons']

            self.tons_invoiced = tons_billing
        else:
            self.tons_invoiced = 0

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

    @api.one
    @api.depends('purchase_order_id')
    def _compute_priced(self):
        for line in self.env['pinup.price.purchase'].search([('purchase_order_id', '=', self.purchase_order_id.name)]):
            self.tons_priced += line.pinup_tons

    @api.one
    @api.depends('tc_mn')
    def _compute_mx(self):
        self.price_mx = self.price_usd_mn * self.tc_mn
