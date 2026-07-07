import re

with open('static/js/features/salary.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Add viewDismissedEmployeeSalaryHistory
dismissed_view_fn = """
function viewDismissedEmployeeSalaryHistory(employeeId, employeeName) {
    currentHistoryEmployeeId = employeeId;
    currentHistoryEmployeeName = employeeName;
    
    // Set URL flag before switching view
    const url = new URL(window.location);
    url.searchParams.set('type', 'dismissed');
    window.history.replaceState(null, '', url.toString());
    
    switchView('salaryHistoryView', true, { employeeId: employeeId, isDismissed: true });
}
"""

if "function viewDismissedEmployeeSalaryHistory" not in content:
    content = content.replace("let currentHistoryEmployeeName = \"\";", "let currentHistoryEmployeeName = \"\";\n" + dismissed_view_fn)

# Replace summary url
sum_target = "let sumUrl = `/salary/employee/${currentHistoryEmployeeId}/summary?from=${fromYear}-${fromMonth}&to=${toYear}-${toMonth}`;"
sum_replacement = """const isDismissed = new URLSearchParams(window.location.search).get('type') === 'dismissed';
            let sumUrl = isDismissed 
                ? `/salary/dismissed/employee/${currentHistoryEmployeeId}/summary?from=${fromYear}-${fromMonth}&to=${toYear}-${toMonth}`
                : `/salary/employee/${currentHistoryEmployeeId}/summary?from=${fromYear}-${fromMonth}&to=${toYear}-${toMonth}`;"""
content = content.replace(sum_target, sum_replacement)

# Replace history fetch url
hist_target = "let url = `/salary/history?employee_id=${currentHistoryEmployeeId}&from=${fromYear}-${fromMonth}&to=${toYear}-${toMonth}`;"
hist_replacement = """let url = isDismissed
            ? `/salary/dismissed/history?employee_id=${currentHistoryEmployeeId}&from=${fromYear}-${fromMonth}&to=${toYear}-${toMonth}`
            : `/salary/history?employee_id=${currentHistoryEmployeeId}&from=${fromYear}-${fromMonth}&to=${toYear}-${toMonth}`;"""
content = content.replace(hist_target, hist_replacement)

# Replace download URLs in loadDedicatedEmployeeSalaryHistoryData
dl_single_target = "downloadSlipSingle(${s.employee_id}, ${s.month}, ${s.year})"
dl_single_replacement = "${isDismissed ? 'downloadDismissedSlipSingle' : 'downloadSlipSingle'}(${s.employee_id}, ${s.month}, ${s.year})"
content = content.replace(dl_single_target, dl_single_replacement)

with open('static/js/features/salary.js', 'w', encoding='utf-8') as f:
    f.write(content)
