from openerp import fields, models

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def pinup_price(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'pinup_price_purchase', 'pinup_price_purchase_list_action'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
        res = mod_obj.get_object_reference(cr, uid, 'pinup_price_purchase', 'pinup_price_purchase_form_view')
        action['views'] = [(res and res[1] or False, 'form')]
        action['context'] = {'default_purchase_order_id': ids[0]}
        return action
