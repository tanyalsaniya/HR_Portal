import re

def migrate():
    with open('templates/salary/salary_panel.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Extract active admin block
    # It starts at <!-- PAYROLL CONTROL PANEL CARD --> and ends right before <!-- DYNAMIC TABS FOR DATA VIEWS -->
    match = re.search(r'(<!-- PAYROLL CONTROL PANEL CARD -->.*?)\n\s*<!-- DYNAMIC TABS FOR DATA VIEWS -->', html, re.DOTALL)
    if not match:
        print("Could not find admin block")
        return
    active_admin_block = match.group(1)

    # Remove it from global scope
    html = html.replace(active_admin_block, '')

    # 2. Add 'Dismissed Employees' tab to tabs
    tabs_match = re.search(r'(<span id="tabBatches".*?</span>)', html, re.DOTALL)
    if tabs_match:
        dismissed_tab = '\n        <span id="tabDismissed" onclick="switchSalaryTab(\'dismissed\')" style="padding: 10px 5px; font-weight: 600; cursor: pointer; color: var(--text-color); border-bottom: 2px solid transparent;">Dismissed Employees</span>'
        html = html.replace(tabs_match.group(1), tabs_match.group(1) + dismissed_tab)

    # 3. Create dismissed admin block
    dismissed_admin_block = active_admin_block
    dismissed_admin_block = dismissed_admin_block.replace('payrollAdminPanel', 'dismissedPayrollAdminPanel')
    dismissed_admin_block = dismissed_admin_block.replace('payrollMonth', 'dismissedPayrollMonth')
    dismissed_admin_block = dismissed_admin_block.replace('payrollYear', 'dismissedPayrollYear')
    dismissed_admin_block = dismissed_admin_block.replace('loadPayrollGrid()', 'loadDismissedPayrollGrid()')
    dismissed_admin_block = dismissed_admin_block.replace('exportExcelTemplate()', 'exportDismissedExcelTemplate()')
    dismissed_admin_block = dismissed_admin_block.replace('openImportModal()', 'openDismissedImportModal()')
    dismissed_admin_block = dismissed_admin_block.replace('publishSlipsMonth()', 'publishDismissedSlipsMonth()')
    dismissed_admin_block = dismissed_admin_block.replace('openManualGenerateModal()', 'openDismissedManualGenerateModal()')
    
    dismissed_admin_block = dismissed_admin_block.replace('payrollGridContainer', 'dismissedPayrollGridContainer')
    dismissed_admin_block = dismissed_admin_block.replace('payrollGridMonthYear', 'dismissedPayrollGridMonthYear')
    dismissed_admin_block = dismissed_admin_block.replace('cancelPayrollGrid()', 'cancelDismissedPayrollGrid()')
    dismissed_admin_block = dismissed_admin_block.replace('savePayrollGrid()', 'saveDismissedPayrollGrid()')
    dismissed_admin_block = dismissed_admin_block.replace('payrollGridTable', 'dismissedPayrollGridTable')
    dismissed_admin_block = dismissed_admin_block.replace('payrollGridBody', 'dismissedPayrollGridBody')

    # 4. Insert active_admin_block into TAB 1
    insert_point_1 = r'(<!-- TAB 1: SALARY SLIPS REGISTRY -->\n\s*<div id="salaryTabSlips" class="salary-tab-content">)'
    html = re.sub(insert_point_1, r'\1\n' + active_admin_block + '\n', html)

    # 5. Extract Payslips List block to duplicate it for Dismissed
    # It starts at <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">\n            <h3 style="margin: 0;">Payslips List</h3>
    # and ends at the end of salaryTabSlips (i.e. before <!-- TAB 2: STRUCTURES -->)
    slips_list_match = re.search(r'(<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">\n\s*<h3 style="margin: 0;">Payslips List</h3>.*?</div>\n\s*</div>)\n\s*<!-- TAB 2: STRUCTURES -->', html, re.DOTALL)
    if slips_list_match:
        slips_list = slips_list_match.group(1)
        # However, the match includes the closing </div> of salaryTabSlips! 
        # Let's fix the match to not include the closing div of salaryTabSlips.
        slips_list = re.sub(r'\n\s*</div>$', '', slips_list)

        dismissed_slips = slips_list
        dismissed_slips = dismissed_slips.replace('Payslips List', 'Dismissed Employees Payslips')
        dismissed_slips = dismissed_slips.replace('slipBulkDownloadActions', 'dismissedBulkDownloadActions')
        dismissed_slips = dismissed_slips.replace('downloadSlipBulk()', 'downloadDismissedSlipBulk()')
        dismissed_slips = re.sub(r'<button class="btn btn-primary" style="font-size: 9pt; padding: 6px 12px; background-color: #475569;" onclick="openRangeDownloadModal\(\)">Download Date Range</button>', '', dismissed_slips)
        dismissed_slips = dismissed_slips.replace('salaryRegistryTableHeader', 'dismissedRegistryTableHeader')
        dismissed_slips = dismissed_slips.replace('salarySlipsTableBody', 'dismissedSlipsTableBody')
        dismissed_slips = dismissed_slips.replace('salarySlipsPaginationFooter', 'dismissedSlipsPaginationFooter')
        dismissed_slips = dismissed_slips.replace('salaryPageStart', 'dismissedPageStart')
        dismissed_slips = dismissed_slips.replace('salaryPageEnd', 'dismissedPageEnd')
        dismissed_slips = dismissed_slips.replace('salaryTotalCount', 'dismissedTotalCount')
        dismissed_slips = dismissed_slips.replace('salaryPrevBtn', 'dismissedPrevBtn')
        dismissed_slips = dismissed_slips.replace('salaryNextBtn', 'dismissedNextBtn')
        dismissed_slips = dismissed_slips.replace('changeSalaryPage(-1)', 'changeDismissedPage(-1)')
        dismissed_slips = dismissed_slips.replace('changeSalaryPage(1)', 'changeDismissedPage(1)')

        # In Dismissed Employee Payslips table, we need different headers.
        # Original: Employee, Month/Year, Gross Salary, Total Deductions, Net Salary, Net Credited, Payment Status, Workflow Status, Actions
        # In dismissed: Employee ID, Name, Department, Status, Actions
        old_headers = r'<tr>\s*<th>Employee</th>\s*<th>Month/Year</th>\s*<th>Gross Salary</th>\s*<th>Total Deductions</th>\s*<th>Net Salary</th>\s*<th>Net Credited</th>\s*<th>Payment Status</th>\s*<th>Workflow Status</th>\s*<th>Actions</th>\s*</tr>'
        new_headers = '<tr>\n                        <th>Employee ID</th>\n                        <th>Name</th>\n                        <th>Department</th>\n                        <th>Status</th>\n                        <th>Actions</th>\n                    </tr>'
        dismissed_slips = re.sub(old_headers, new_headers, dismissed_slips)

        # 6. Create TAB 4
        tab4 = f"""
    <!-- TAB 4: DISMISSED EMPLOYEES -->
    <div id="salaryTabDismissed" class="salary-tab-content" style="display: none;">
{dismissed_admin_block}
{dismissed_slips}
    </div>
"""
        # Insert TAB 4 right before the first Modal (<!-- MODAL 5: DEFINE SALARY STRUCTURE -->)
        html = html.replace('<!-- MODAL 5: DEFINE SALARY STRUCTURE -->', tab4 + '\n<!-- MODAL 5: DEFINE SALARY STRUCTURE -->')

    with open('templates/salary/salary_panel.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("salary_panel.html fixed perfectly.")

if __name__ == '__main__':
    migrate()
