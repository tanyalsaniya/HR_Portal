import re

def process_html():
    with open('templates/salary/salary_panel.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Extract payrollAdminPanel
    admin_panel_match = re.search(r'(<!-- PAYROLL CONTROL PANEL CARD -->\s*<div.*?id="payrollAdminPanel">.*?</div>\n\s*</div>)', html, re.DOTALL)
    if not admin_panel_match:
        print("Could not find payrollAdminPanel")
        return
    admin_panel = admin_panel_match.group(1)
    
    # Remove from original location
    html = html.replace(admin_panel, '')

    # 2. Extract dynamicTabs
    tabs_match = re.search(r'(<!-- DYNAMIC TABS FOR DATA VIEWS -->\s*<div[^>]*>.*?</div>)', html, re.DOTALL)
    if not tabs_match:
        print("Could not find dynamicTabs")
        return
    tabs = tabs_match.group(1)
    
    # Remove tabs from original location
    html = html.replace(tabs, '')

    # 3. Create Dismissed Admin Panel
    dismissed_admin_panel = admin_panel.replace('payrollAdminPanel', 'dismissedPayrollAdminPanel')
    dismissed_admin_panel = dismissed_admin_panel.replace('payrollMonth', 'dismissedPayrollMonth')
    dismissed_admin_panel = dismissed_admin_panel.replace('payrollYear', 'dismissedPayrollYear')
    dismissed_admin_panel = dismissed_admin_panel.replace('loadPayrollGrid()', 'loadDismissedPayrollGrid()')
    dismissed_admin_panel = dismissed_admin_panel.replace('exportExcelTemplate()', 'exportDismissedExcelTemplate()')
    dismissed_admin_panel = dismissed_admin_panel.replace('openImportModal()', 'openDismissedImportModal()')
    dismissed_admin_panel = dismissed_admin_panel.replace('openManualGenerateModal()', 'openDismissedManualGenerateModal()')
    dismissed_admin_panel = dismissed_admin_panel.replace('payrollGridContainer', 'dismissedPayrollGridContainer')
    dismissed_admin_panel = dismissed_admin_panel.replace('payrollGridMonthYear', 'dismissedPayrollGridMonthYear')
    dismissed_admin_panel = dismissed_admin_panel.replace('cancelPayrollGrid()', 'cancelDismissedPayrollGrid()')
    dismissed_admin_panel = dismissed_admin_panel.replace('savePayrollGrid()', 'saveDismissedPayrollGrid()')
    dismissed_admin_panel = dismissed_admin_panel.replace('payrollGridTable', 'dismissedPayrollGridTable')
    dismissed_admin_panel = dismissed_admin_panel.replace('payrollGridBody', 'dismissedPayrollGridBody')

    # 4. Insert tabs at the top, just below flex-row-header
    # The header looks like: <div class="flex-row-header">...</div>\n
    html = re.sub(r'(<div class="flex-row-header">.*?</div>)', r'\1\n\n' + tabs, html, flags=re.DOTALL)

    # 5. Insert admin panels inside their respective tabs
    # Active
    html = html.replace('<!-- TAB 1: SALARY SLIPS REGISTRY -->\n    <div id="salaryTabSlips" class="salary-tab-content">', '<!-- TAB 1: SALARY SLIPS REGISTRY -->\n    <div id="salaryTabSlips" class="salary-tab-content">\n' + admin_panel)
    
    # Dismissed
    html = html.replace('<!-- TAB 4: DISMISSED EMPLOYEES -->\n    <div id="salaryTabDismissed" class="salary-tab-content" style="display: none;">', '<!-- TAB 4: DISMISSED EMPLOYEES -->\n    <div id="salaryTabDismissed" class="salary-tab-content" style="display: none;">\n' + dismissed_admin_panel)

    # 6. Duplicate Import Modal
    import_modal_match = re.search(r'(<!-- MODAL 6: IMPORT EXCEL -->\s*<div class="modal" id="salaryImportModal">.*?</div>\n\s*</div>)', html, re.DOTALL)
    if import_modal_match:
        import_modal = import_modal_match.group(1)
        dismissed_import_modal = import_modal.replace('MODAL 6', 'MODAL 6 DISMISSED')
        dismissed_import_modal = dismissed_import_modal.replace('salaryImportModal', 'dismissedSalaryImportModal')
        dismissed_import_modal = dismissed_import_modal.replace('closeImportModal()', 'closeDismissedImportModal()')
        dismissed_import_modal = dismissed_import_modal.replace('salaryImportForm', 'dismissedSalaryImportForm')
        dismissed_import_modal = dismissed_import_modal.replace('importExcelFile', 'dismissedImportExcelFile')
        
        # Append dismissed import modal after original import modal
        html = html.replace(import_modal, import_modal + '\n\n' + dismissed_import_modal)

    # 7. Duplicate Manual Generate Modal
    manual_modal_match = re.search(r'(<!-- MODAL 8: MANUAL GENERATE PAYSLIP -->\s*<div class="modal" id="salaryManualGenerateModal">.*?</div>\n\s*</div>)', html, re.DOTALL)
    if manual_modal_match:
        manual_modal = manual_modal_match.group(1)
        dismissed_manual_modal = manual_modal.replace('MODAL 8', 'MODAL 8 DISMISSED')
        dismissed_manual_modal = dismissed_manual_modal.replace('salaryManualGenerateModal', 'dismissedSalaryManualGenerateModal')
        dismissed_manual_modal = dismissed_manual_modal.replace('closeManualGenerateModal()', 'closeDismissedManualGenerateModal()')
        dismissed_manual_modal = dismissed_manual_modal.replace('salaryManualGenerateForm', 'dismissedSalaryManualGenerateForm')
        dismissed_manual_modal = dismissed_manual_modal.replace('manualGenerateEmployee', 'dismissedManualGenerateEmployee')
        dismissed_manual_modal = dismissed_manual_modal.replace('manualGenerateMonth', 'dismissedManualGenerateMonth')
        dismissed_manual_modal = dismissed_manual_modal.replace('manualGenerateYear', 'dismissedManualGenerateYear')
        
        html = html.replace(manual_modal, manual_modal + '\n\n' + dismissed_manual_modal)


    with open('templates/salary/salary_panel.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("salary_panel.html processed successfully.")

if __name__ == '__main__':
    process_html()
