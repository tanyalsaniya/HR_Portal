import re

def isolate_ui():
    with open('templates/salary/salary_panel.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Extract the whole payrollAdminPanel
    admin_panel_match = re.search(r'(<!-- PAYROLL CONTROL PANEL CARD -->.*?<div class="table-responsive">)', html, re.DOTALL)
    if not admin_panel_match:
        print("Could not find payrollAdminPanel")
        return
    admin_panel_html = admin_panel_match.group(1)
    
    grid_match = re.search(r'(<!-- EDITABLE PAYROLL GRID CONTAINER -->.*?</table>\n\s*</div>\n\s*</div>)', html, re.DOTALL)
    if grid_match:
        grid_html = grid_match.group(1)
        html = html.replace(grid_html, '')
    else:
        grid_html = ""

    # Remove admin panel from global area
    html = html.replace(admin_panel_html, '')

    # Combine into active admin block
    active_admin_block = admin_panel_html + "\n" + grid_html
    
    # Create dismissed admin block
    dismissed_admin_block = active_admin_block
    dismissed_admin_block = dismissed_admin_block.replace('payrollAdminPanel', 'dismissedPayrollAdminPanel')
    dismissed_admin_block = dismissed_admin_block.replace('payrollMonth', 'dismissedPayrollMonth')
    dismissed_admin_block = dismissed_admin_block.replace('payrollYear', 'dismissedPayrollYear')
    dismissed_admin_block = dismissed_admin_block.replace('loadPayrollGrid()', 'loadDismissedPayrollGrid()')
    dismissed_admin_block = dismissed_admin_block.replace('exportExcelTemplate()', 'exportDismissedExcelTemplate()')
    dismissed_admin_block = dismissed_admin_block.replace('openImportModal()', 'openDismissedImportModal()')
    dismissed_admin_block = dismissed_admin_block.replace('publishSlipsMonth()', 'publishDismissedSlipsMonth()')
    dismissed_admin_block = dismissed_admin_block.replace('openManualGenerateModal()', 'openDismissedManualGenerateModal()')
    dismissed_admin_block = dismissed_admin_block.replace('slipBulkDownloadActions', 'dismissedBulkDownloadActions')
    dismissed_admin_block = dismissed_admin_block.replace('downloadSlipBulk()', 'downloadDismissedSlipBulk()')
    dismissed_admin_block = dismissed_admin_block.replace('<button class="btn btn-primary" style="font-size: 9pt; padding: 6px 12px; background-color: #475569;" onclick="openRangeDownloadModal()">Download Date Range</button>', '')
    dismissed_admin_block = dismissed_admin_block.replace('Payslips List', 'Dismissed Employees Payslips')
    
    dismissed_admin_block = dismissed_admin_block.replace('payrollGridContainer', 'dismissedPayrollGridContainer')
    dismissed_admin_block = dismissed_admin_block.replace('payrollGridMonthYear', 'dismissedPayrollGridMonthYear')
    dismissed_admin_block = dismissed_admin_block.replace('cancelPayrollGrid()', 'cancelDismissedPayrollGrid()')
    dismissed_admin_block = dismissed_admin_block.replace('savePayrollGrid()', 'saveDismissedPayrollGrid()')
    dismissed_admin_block = dismissed_admin_block.replace('payrollGridTable', 'dismissedPayrollGridTable')
    dismissed_admin_block = dismissed_admin_block.replace('payrollGridBody', 'dismissedPayrollGridBody')
    
    # Insert active block into TAB 1
    insert_point_1 = r'(<!-- TAB 1: SALARY SLIPS REGISTRY -->\n\s*<div id="salaryTabSlips" class="salary-tab-content">)'
    html = re.sub(insert_point_1, r'\1\n' + active_admin_block, html)

    # Insert dismissed block into TAB 4
    insert_point_4 = r'(<!-- TAB 4: DISMISSED EMPLOYEES -->\n\s*<div id="salaryTabDismissed" class="salary-tab-content" style="display: none;">)'
    html = re.sub(insert_point_4, r'\1\n' + dismissed_admin_block, html)
    
    with open('templates/salary/salary_panel.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("salary_panel.html updated successfully.")

if __name__ == '__main__':
    isolate_ui()
