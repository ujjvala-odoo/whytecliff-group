# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015-2016 Whytecliff Group Pvt. Ltd.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time

from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import osv

import sys
sys.path.insert(0, 'addons/account/report')

from common_report_header import common_report_header


class report_profit_loss(report_sxw.rml_parse, common_report_header):
    def __init__(self, cr, uid, name, context=None):
        super(report_profit_loss, self).__init__(cr, uid, name, context=context)
        self.localcontext.update( {
            'get_lines': self.get_lines,
            'time': time,
            'get_fiscalyear': self._get_fiscalyear,
            'get_account': self._get_account,
            'get_start_period': self.get_start_period,
            'get_end_period': self.get_end_period,
            'get_filter': self._get_filter,
            'get_target_move': self._get_target_move,
            'get_columns': self._get_columns,
            'get_columns_data': self._get_columns_data,
        })
        self.context = context

    def set_context(self, objects, data, ids, report_type=None):
        new_ids = self.pool.get('account.account').search(self.cr, self.uid, [('parent_id', '=', False)])
        self.context['landscape'] = True
        if (data['model'] == 'ir.ui.menu'):
            objects = self.pool.get('account.account').browse(self.cr, self.uid, new_ids)
        return super(report_profit_loss, self).set_context(objects, data, new_ids, report_type=report_type)

    def _get_columns(self, data):
        period_obj = self.pool.get('account.period')
        res = []
        period_from = period_to = False
        if data['form'].get('period_from', False):
            period_from = data['form']['period_from']
        if data['form'].get('period_to', False):
            period_to = data['form']['period_to']
        pids = period_obj.search(self.cr, self.uid, [('id','>=',period_from), ('id','<=',period_to)])
        for period in period_obj.browse(self.cr, self.uid, pids):
            res.append(period)
        return res

    def _get_columns_data(self, account_id, data):
        obj_move = self.pool.get('account.move.line')
        periods = self._get_columns(data)
        result = []
        context = data['form'].get('used_context',{})
        move_state = ['draft','posted']
        if context.get('target_move') == 'posted':
            move_state = ['posted','']

        if account_id:
            for period in periods:
                context.update({'date_from': period.date_start, 'date_to': period.date_stop})
                query = obj_move._query_get(self.cr, self.uid, obj='l', context=context)
                self.cr.execute('SELECT (sum(debit) - sum(credit)) as tot_balance \
                        FROM account_move_line l \
                        JOIN account_move am ON (am.id = l.move_id) \
                        WHERE (l.account_id = %s) \
                        AND (am.state IN %s) \
                        AND '+ query +' '
                        ,(account_id, tuple(move_state)))
                sum_balance = self.cr.fetchone()[0] or 0.0
                result.append(sum_balance)
        return result

    def get_lines(self, data):
        lines = []
        account_obj = self.pool.get('account.account')
        ids2 = self.pool.get('account.financial.report')._get_children_by_order(self.cr, self.uid, [data['form']['account_report_id'][0]], context=data['form']['used_context'])
        for report in self.pool.get('account.financial.report').browse(self.cr, self.uid, ids2, context=self.context):
            vals = {
                'name': report.name,
                'balance': report.balance * report.sign or 0.0,
                'type': 'report',
                'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
                'account_type': report.type =='sum' and 'view' or False, #used to underline the financial report balances
                'account_id': False,
            }
            lines.append(vals)
            account_ids = []
            if report.display_detail == 'no_detail':
                #the rest of the loop is used to display the details of the financial report, so it's not needed here.
                continue
            if report.type == 'accounts' and report.account_ids:
                account_ids = account_obj._get_children_and_consol(self.cr, self.uid, [x.id for x in report.account_ids])
            elif report.type == 'account_type' and report.account_type_ids:
                account_ids = account_obj.search(self.cr, self.uid, [('user_type','in', [x.id for x in report.account_type_ids])])
            if account_ids:
                for account in account_obj.browse(self.cr, self.uid, account_ids, context=self.context):
                    #if there are accounts to display, we add them to the lines with a level equals to their level in
                    #the COA + 1 (to avoid having them with a too low level that would conflicts with the level of data
                    #financial reports for Assets, liabilities...)
                    if report.display_detail == 'detail_flat' and account.type == 'view':
                        continue
                    vals = {
                        'name': account.code + ' ' + account.name,
                        'balance':  account.balance != 0 and account.balance * report.sign or account.balance,
                        'type': 'account',
                        'level': report.display_detail == 'detail_with_hierarchy' and min(account.level + 1,6) or 6, #account.level + 1
                        'account_type': account.type,
                        'account_id': account.id,
                    }
                    lines.append(vals)
        return lines

class report_profitloss(osv.AbstractModel):
    _name = 'report.whytecliff_report.report_profitloss'
    _inherit = 'report.abstract_report'
    _template = 'whytecliff_report.report_profitloss'
    _wrapped_report_class = report_profit_loss

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: