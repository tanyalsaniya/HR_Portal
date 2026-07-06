with open('templates/salary/salary_panel.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '<!-- PAYROLL CONTROL PANEL CARD -->' in line or 'id="payrollAdminPanel"' in line or '<!-- DYNAMIC TABS FOR DATA VIEWS -->' in line or '<!-- EDITABLE PAYROLL GRID CONTAINER -->' in line or 'id="payrollGridContainer"' in line or 'TAB 1: SALARY SLIPS REGISTRY' in line or 'TAB 4: DISMISSED EMPLOYEES' in line:
        print(f'{i+1}: {line.strip()}')
