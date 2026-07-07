import re

def fix_html():
    with open('templates/salary/salary_panel.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Extract the orphaned payrollGridContainer
    grid_match = re.search(r'(<!-- EDITABLE PAYROLL GRID CONTAINER -->\s*<div id="payrollGridContainer".*?</table>\n\s*</div>\n\s*</div>)', html, re.DOTALL)
    if not grid_match:
        print("Could not find orphaned payrollGridContainer")
        return
    grid_html = grid_match.group(1)
    
    # Remove it from the top
    html = html.replace(grid_html, '')
    
    # But wait, grid_html has an extra closing div at the end which originally closed payrollAdminPanel
    # Let's clean it up by removing the very last </div>
    grid_html_clean = re.sub(r'</div>\s*$', '', grid_html).strip() + '\n</div>\n'

    # 2. Insert into Active Tab
    active_insert_point = r'(<button class="btn btn-primary" onclick="openManualGenerateModal\(\)".*?</button>\n\s*</div>\n\s*</div>)'
    
    # 3. Create dismissed grid
    dismissed_grid_html = grid_html_clean.replace('payrollGridContainer', 'dismissedPayrollGridContainer')
    dismissed_grid_html = dismissed_grid_html.replace('payrollGridMonthYear', 'dismissedPayrollGridMonthYear')
    dismissed_grid_html = dismissed_grid_html.replace('cancelPayrollGrid()', 'cancelDismissedPayrollGrid()')
    dismissed_grid_html = dismissed_grid_html.replace('savePayrollGrid()', 'saveDismissedPayrollGrid()')
    dismissed_grid_html = dismissed_grid_html.replace('payrollGridTable', 'dismissedPayrollGridTable')
    dismissed_grid_html = dismissed_grid_html.replace('payrollGridBody', 'dismissedPayrollGridBody')

    # Now, find the active admin panel buttons block
    active_match = re.search(active_insert_point, html, re.DOTALL)
    if active_match:
        old_str = active_match.group(1)
        # old_str ends with </div>\n        </div>
        # replace the last </div> with the grid
        new_str = old_str.rsplit('</div>', 1)[0] + '\n' + grid_html_clean + '\n</div>'
        html = html.replace(old_str, new_str)
        print("Fixed active grid")
    else:
        print("Could not find active insert point")

    # Find the dismissed admin panel buttons block
    dismissed_insert_point = r'(<button class="btn btn-primary" onclick="openDismissedManualGenerateModal\(\)".*?</button>\n\s*</div>\n\s*</div>)'
    dismissed_match = re.search(dismissed_insert_point, html, re.DOTALL)
    if dismissed_match:
        old_str = dismissed_match.group(1)
        new_str = old_str.rsplit('</div>', 1)[0] + '\n' + dismissed_grid_html + '\n</div>'
        html = html.replace(old_str, new_str)
        print("Fixed dismissed grid")
    else:
        print("Could not find dismissed insert point")

    with open('templates/salary/salary_panel.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("salary_panel.html fixed.")

if __name__ == '__main__':
    fix_html()
