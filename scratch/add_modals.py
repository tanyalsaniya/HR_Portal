import re

def append_modals():
    with open('templates/salary/salary_panel.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Check if they are already added
    if 'id="dismissedSalaryImportModal"' in html:
        print("Modals already added")
        return

    # Extract salaryImportModal
    import_match = re.search(r'(<!-- MODAL: IMPORT EXCEL -->.*?</div>\n</div>)', html, re.DOTALL)
    if not import_match:
        print("Could not find import modal")
        return
    import_modal = import_match.group(1)

    # Extract manualGenerateModal
    manual_match = re.search(r'(<!-- MODAL: MANUAL GENERATE -->.*?</div>\n</div>)', html, re.DOTALL)
    if not manual_match:
        print("Could not find manual generate modal")
        return
    manual_modal = manual_match.group(1)

    # Transform for dismissed
    dismissed_import = import_modal
    dismissed_import = dismissed_import.replace('<!-- MODAL: IMPORT EXCEL -->', '<!-- MODAL: DISMISSED IMPORT EXCEL -->')
    dismissed_import = dismissed_import.replace('id="salaryImportModal"', 'id="dismissedSalaryImportModal"')
    dismissed_import = dismissed_import.replace('closeImportModal()', 'closeDismissedImportModal()')
    dismissed_import = dismissed_import.replace('id="salaryImportForm"', 'id="dismissedSalaryImportForm"')
    dismissed_import = dismissed_import.replace('id="importExcelFile"', 'id="dismissedImportExcelFile"')
    dismissed_import = dismissed_import.replace('Import Monthly Salary Excel', 'Import Dismissed Salary Excel')

    dismissed_manual = manual_modal
    dismissed_manual = dismissed_manual.replace('<!-- MODAL: MANUAL GENERATE -->', '<!-- MODAL: DISMISSED MANUAL GENERATE -->')
    dismissed_manual = dismissed_manual.replace('id="salaryManualGenerateModal"', 'id="dismissedSalaryManualGenerateModal"')
    dismissed_manual = dismissed_manual.replace('closeManualGenerateModal()', 'closeDismissedManualGenerateModal()')
    dismissed_manual = dismissed_manual.replace('id="salaryManualGenerateForm"', 'id="dismissedSalaryManualGenerateForm"')
    dismissed_manual = dismissed_manual.replace('id="manualGenerateEmployee"', 'id="dismissedManualGenerateEmployee"')
    dismissed_manual = dismissed_manual.replace('id="manualGenerateMonth"', 'id="dismissedManualGenerateMonth"')
    dismissed_manual = dismissed_manual.replace('id="manualGenerateYear"', 'id="dismissedManualGenerateYear"')
    dismissed_manual = dismissed_manual.replace('Generate Individual Payslip', 'Generate Dismissed Payslip')

    # Append to end of HTML
    html = html + '\n\n' + dismissed_import + '\n\n' + dismissed_manual + '\n'

    with open('templates/salary/salary_panel.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Modals added successfully.")

if __name__ == '__main__':
    append_modals()
