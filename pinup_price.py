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
    price_bushel = fields.Float()
    bases_ton = fields.Float()
    price_min = fields.Float()
    service = fields.Float()
    tc = fields.Float()
    price_per_ton = fields.Float(compute="_compute_ton_usd", store=True)
    price_mxn = fields.Float(compute="_compute_mx", store=True)
    tons_reception = fields.Float(
        compute="_compute_tr", digits=(12, 3),  store=True)
    tons_invoiced = fields.Float(
        compute="_compute_ti", digits=(12, 3),  store=True)
    tons_priced = fields.Float(
        compute="_compute_priced", digits=(12, 3),  store=True)
    invoice_create_id = fields.Many2one('account.invoice', readonly=True)


    state = fields.Selection([
        ('draft', "Draft"),
        ('price', "Price"),
        ('invoiced', "Invoiced"),
        ('close', "Close"),
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
        self.state = 'price'

    @api.multi
    def action_invoiced(self):
        self.state = 'invoiced'

    @api.multi
    def action_create(self):
        self.state = 'close'

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
    def _compute_priced(self):
        for line in self.env['pinup.price.purchase'].search([('purchase_order_id', '=', self.purchase_order_id.name)]):
            self.tons_priced += line.pinup_tons

    @api.one
    @api.depends('price_bushel')
    def _compute_ton_usd(self):
            self.price_per_ton = self.price_bushel * 0.3936825 + self.bases_ton

    @api.one
    @api.depends('price_per_ton')
    def _compute_mx(self):
        self.price_mxn = self.price_per_ton * self.tc

    @api.multi
    def write(self, vals, recursive=None):
        if not recursive:
            if self.state == 'draft':
                self.write({'state': 'price'}, 'r')
            elif self.state == 'price':
                self.write({'state': 'invoiced'}, 'r')
        res = super(pinup_price_purchase, self).write(vals)
        return res

    @api.model
    def create(self, vals):
        vals['state'] = 'price'
        res = super(pinup_price_purchase, self).create(vals)
        return res

    @api.multi
    def action_create(self):
        invoice_id = self.env['account.invoice'].create({
            'partner_id' : self.partner_id.id,
            'account_id' : 5976,
            'journal_id' : 2,
            'currency_id' : 34,
            'type':'in_invoice',
            'origin' : self.purchase_order_id.name,
            'date_invoice':self.request_date,
            'invoice_line.product_id' : 2,
            'invoice_line.quantity' : self.pinup_tons,
            'invoice_line.price_unit' : self.price_mxn,
            'invoice_line_tax_id':3,
            'state':'draft',
            })
        self.create_move_id(invoice_id)
        self.invoice_create_id = invoice_id
        self.state = 'close'


    @api.multi
    def create_move_id(self, invoice_id):
        move_id = self.env['account.invoice.line'].create({
            'invoice_id': invoice_id.id,
            'price_unit': self.price_mxn,
            'product_id': 2,
            'quantity' : self.pinup_tons,
            'account_id':5976,
            'name':'factura desde preciar',
        })



    # @api.one
    # @api.depends('purchase_order_id')
    # def _compute_tc(self):
    #     tc = self.env['market.usd'].search([], order='date desc', limit=1)
    #     for ltc in tc:
    #         self.tc = ltc['exchange_rate']
    #
    # @api.one
    # @api.depends('purchase_order_id')
    # def _compute_tc_date(self):
    #     tc = self.env['market.usd'].search([], order='date desc', limit=1)
    #     for ltc in tc:
    #         self.tc_date = ltc['date']
    #
    # @api.one
    # @api.depends('purchase_order_id')
    # def _compute_price_date(self):
    #     tc = self.env['market.price'].search([], order='id desc', limit=1)
    #     for ltc in tc:
    #         self.price_date = ltc['date']
    #
    # @api.one
    # @api.depends('purchase_order_id')
    # def _compute_price(self):
    #     mp = self.env['market.price'].search([], order='id desc', limit=1)
    #     for lmp in mp:
    #         self.price_usd = lmp['price_ton']

    # @api.one
    # @api.depends('tc_mn')
    # def _compute_mx(self):
    #     self.price_mx = self.price_usd_mn * self.tc_mn

    # price_usd = fields.Float(compute="_compute_price", store=True)
    # tc = fields.Char(compute="_compute_tc", store=True)
    # tc_mn = fields.Float()
    # price_mx = fields.Float(compute="_compute_mx")
    # tc_date = fields.Char(compute="_compute_tc_date", store=True)
    # price_date = fields.Char(compute="_compute_price_date", store=True)
