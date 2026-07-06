import re

def process_js():
    with open('static/js/features/salary.js', 'r', encoding='utf-8') as f:
        js = f.read()

    # 1. Revert exportExcelTemplate
    export_revert = """    const isDismissed = (activeSalaryTab === 'dismissed');
    const endpoint = isDismissed ? '/api/admin/salary/dismissed/export' : '/api/admin/salary/export';

    // Download directly via window open with auth token or using a fetch with header
    fetch(`${endpoint}?month=${month}&year=${year}`, {"""
    export_original = """    // Download directly via window open with auth token or using a fetch with header
    fetch(`/api/admin/salary/export?month=${month}&year=${year}`, {"""
    js = js.replace(export_revert, export_original)

    # 2. Revert publishSlipsMonth
    publish_revert = """        const isDismissed = (activeSalaryTab === 'dismissed');
        const endpoint = isDismissed ? '/admin/salary/dismissed/publish' : '/admin/salary/publish';

        const res = await apiFetch(endpoint, {"""
    publish_original = """        const res = await apiFetch('/admin/salary/publish', {"""
    js = js.replace(publish_revert, publish_original)

    # 3. Revert salaryImportForm
    import_revert = """                const isDismissed = (activeSalaryTab === 'dismissed');
                const endpoint = isDismissed ? '/api/admin/salary/dismissed/import' : '/api/admin/salary/import';

                const res = await fetch(endpoint, {"""
    import_original = """                const res = await fetch('/api/admin/salary/import', {"""
    js = js.replace(import_revert, import_original)

    # 4. Revert loadPayrollGrid
    loadgrid_revert = """        const isDismissed = (activeSalaryTab === 'dismissed');
        const endpoint = isDismissed ? '/admin/salary/dismissed/grid' : '/admin/salary/grid';
        const res = await apiFetch(`${endpoint}?month=${month}&year=${year}`);"""
    loadgrid_original = """        const res = await apiFetch(`/admin/salary/grid?month=${month}&year=${year}`);"""
    js = js.replace(loadgrid_revert, loadgrid_original)

    # 5. Revert savePayrollGrid
    savegrid_revert = """        const isDismissed = (activeSalaryTab === 'dismissed');
        const endpoint = isDismissed ? '/admin/salary/dismissed/grid' : '/admin/salary/grid';
        const res = await apiFetch(endpoint, {"""
    savegrid_original = """        const res = await apiFetch('/admin/salary/grid', {"""
    js = js.replace(savegrid_revert, savegrid_original)

    # 6. Revert manualGenerateForm
    gen_revert = """                const isDismissed = (activeSalaryTab === 'dismissed');
                const endpoint = isDismissed ? '/admin/salary/dismissed/generate-individual' : '/admin/salary/generate-individual';
                const res = await apiFetch(endpoint, {"""
    gen_original = """                const res = await apiFetch('/admin/salary/generate-individual', {"""
    js = js.replace(gen_revert, gen_original)

    # Revert the activeSalaryTab check for reload inside generateForm
    gen_reload_revert = """                    // Reload slips list or history
                    if (activeSalaryTab === 'slips') {
                        loadSlipsRegistry();
                    } else if (activeSalaryTab === 'dismissed') {
                        loadDismissedSlipsRegistry();
                    }
                    const historyView = document.getElementById('salaryHistoryView');"""
    gen_reload_original = """                    // Reload slips list or history
                    if (activeSalaryTab === 'slips') {
                        loadSlipsRegistry();
                    }
                    const historyView = document.getElementById('salaryHistoryView');"""
    js = js.replace(gen_reload_revert, gen_reload_original)

    # 7. Revert manualGenerate modal dropdown
    dropdown_revert = """            const isDismissed = (activeSalaryTab === 'dismissed');
            const url = isDismissed ? '/employees/?type=dismissed&no_pagination=true' : '/employees/?type=all&no_pagination=true';
            apiFetch(url)"""
    dropdown_original = """            apiFetch('/employees/?type=all&no_pagination=true')"""
    js = js.replace(dropdown_revert, dropdown_original)

    # NOW add the new dismissed-specific functions at the end of the file.
    dismissed_js_functions = """
// ----------------------------------------------------
// DISMISSED PAYROLL ADMIN PANEL FUNCTIONS
// ----------------------------------------------------

function exportDismissedExcelTemplate() {
    const month = document.getElementById('dismissedPayrollMonth').value;
    const year = document.getElementById('dismissedPayrollYear').value;
    const token = localStorage.getItem('accessToken');
    
    showToast('Generating Dismissed Excel Template...');
    
    fetch(`/api/admin/salary/dismissed/export?month=${month}&year=${year}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Export failed');
        return response.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dismissed_salary_sheet_${month}_${year}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('Template downloaded successfully.');
    })
    .catch(err => {
        showToast('Error exporting template: ' + err.message, 'error');
    });
}

function openDismissedImportModal() {
    const modal = document.getElementById('dismissedSalaryImportModal');
    if (modal) modal.style.display = 'flex';
}
function closeDismissedImportModal() {
    const modal = document.getElementById('dismissedSalaryImportModal');
    if (modal) modal.style.display = 'none';
}

function openDismissedManualGenerateModal() {
    const modal = document.getElementById('dismissedSalaryManualGenerateModal');
    if (modal) {
        modal.style.display = 'flex';
        
        const employeeSelect = document.getElementById('dismissedManualGenerateEmployee');
        if (employeeSelect) {
            employeeSelect.innerHTML = '<option value="">-- Choose Employee --</option>';
            apiFetch('/employees/?type=dismissed&no_pagination=true')
                .then(res => res.json())
                .then(data => {
                    const emps = data.results || data;
                    emps.forEach(emp => {
                        const opt = document.createElement('option');
                        opt.value = emp.bitrix_id || emp.id;
                        opt.textContent = `${emp.name} (${emp.emp_id || 'N/A'})`;
                        employeeSelect.appendChild(opt);
                    });
                })
                .catch(err => console.error("Error loading dismissed employees for dropdown:", err));
        }
        
        const targetMonthEl = document.getElementById('dismissedPayrollMonth');
        const targetYearEl = document.getElementById('dismissedPayrollYear');
        const defaultMonth = targetMonthEl ? targetMonthEl.value : String(new Date().getMonth() + 1);
        const defaultYear = targetYearEl ? targetYearEl.value : String(new Date().getFullYear());
        if (document.getElementById('dismissedManualGenerateMonth')) {
            document.getElementById('dismissedManualGenerateMonth').value = defaultMonth;
        }
        if (document.getElementById('dismissedManualGenerateYear')) {
            document.getElementById('dismissedManualGenerateYear').value = defaultYear;
        }
    }
}

function closeDismissedManualGenerateModal() {
    const modal = document.getElementById('dismissedSalaryManualGenerateModal');
    if (modal) modal.style.display = 'none';
}

async function loadDismissedPayrollGrid() {
    const month = document.getElementById('dismissedPayrollMonth').value;
    const year = document.getElementById('dismissedPayrollYear').value;
    if (!month || !year) {
        showToast('Please select Target Month and Year.', 'error');
        return;
    }

    try {
        const res = await apiFetch(`/admin/salary/dismissed/grid?month=${month}&year=${year}`);
        
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.error || 'Failed to fetch payroll grid.');
        }
        
        const data = await res.json();
        
        const monthText = document.getElementById('dismissedPayrollMonth').options[document.getElementById('dismissedPayrollMonth').selectedIndex].text;
        document.getElementById('dismissedPayrollGridMonthYear').textContent = `${monthText} ${year}`;
        document.getElementById('dismissedPayrollGridContainer').style.display = 'block';

        renderDismissedPayrollGrid(data);
    } catch (err) {
        showToast(err.message || 'Failed to load payroll grid.', 'error');
    }
}

function cancelDismissedPayrollGrid() {
    document.getElementById('dismissedPayrollGridContainer').style.display = 'none';
}

function renderDismissedPayrollGrid(data) {
    const tbody = document.getElementById('dismissedPayrollGridBody');
    tbody.innerHTML = '';
    
    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="13" style="text-align: center; padding: 20px;">No employees found.</td></tr>';
        return;
    }

    data.forEach((row, index) => {
        const tr = document.createElement('tr');
        tr.dataset.bitrix_id = row.bitrix_id;
        tr.dataset.id = row.id || '';
        tr.dataset.bank_account_no = row.bank_account_no || '';
        tr.dataset.bank_name = row.bank_name || '';

        const cols = [
            { key: 'name', value: row.name, readOnly: true },
            { key: 'designation', value: row.designation, readOnly: true },
            { key: 'month_days', value: row.month_days, type: 'number' },
            { key: 'worked_days', value: row.worked_days, type: 'number' },
            { key: 'weekend', value: row.weekend, type: 'number' },
            { key: 'cl', value: row.cl, type: 'number' },
            { key: 'extra', value: row.extra, type: 'number' },
            { key: 'payable_days', value: row.payable_days, type: 'number' },
            { key: 'month_salary', value: row.month_salary, type: 'number' },
            { key: 'payable_salary', value: row.payable_salary, type: 'number' },
            { key: 'extra_days_working', value: row.extra_days_working, type: 'number' },
            { key: 'fine_advance', value: row.fine_advance, type: 'number' },
            { key: 'net_payable', value: row.net_payable, type: 'number' }
        ];

        cols.forEach(c => {
            const td = document.createElement('td');
            td.style.padding = '5px';
            td.style.border = '1px solid #e5e7eb';
            
            if (c.readOnly) {
                td.textContent = c.value;
                td.style.backgroundColor = '#f9fafb';
                td.style.color = '#6b7280';
            } else {
                const input = document.createElement('input');
                input.type = 'text';
                input.value = c.value;
                input.dataset.key = c.key;
                input.className = 'grid-input';
                input.style.width = '100%';
                input.style.border = '1px solid transparent';
                input.style.padding = '5px';
                input.style.boxSizing = 'border-box';
                
                input.addEventListener('focus', function() {
                    this.style.border = '1px solid var(--primary-color)';
                    this.style.outline = 'none';
                    this.style.backgroundColor = '#f0f9ff';
                });
                input.addEventListener('blur', function() {
                    this.style.border = '1px solid transparent';
                    this.style.backgroundColor = 'transparent';
                });
                
                td.appendChild(input);
            }
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
}

async function saveDismissedPayrollGrid() {
    const month = document.getElementById('dismissedPayrollMonth').value;
    const year = document.getElementById('dismissedPayrollYear').value;
    
    const tbody = document.getElementById('dismissedPayrollGridBody');
    const rows = tbody.querySelectorAll('tr');
    
    if (rows.length === 0 || rows[0].querySelector('td[colspan]')) {
        showToast('No data to save.', 'error');
        return;
    }

    const payload = [];
    rows.forEach(tr => {
        const rowData = {
            bitrix_id: tr.dataset.bitrix_id,
            id: tr.dataset.id || null,
            bank_account_no: tr.dataset.bank_account_no,
            bank_name: tr.dataset.bank_name
        };
        
        tr.querySelectorAll('input').forEach(input => {
            rowData[input.dataset.key] = input.value;
        });
        
        payload.push(rowData);
    });

    const btn = document.querySelector('#dismissedPayrollGridContainer button.btn-primary:nth-of-type(2)');
    const originalText = btn.textContent;
    btn.textContent = 'Saving...';
    btn.disabled = true;

    try {
        const res = await apiFetch('/admin/salary/dismissed/grid', {
            method: 'POST',
            body: JSON.stringify({
                month: month,
                year: year,
                rows: payload
            })
        });
        
        if (res.ok) {
            showToast('Payroll sheet saved successfully.', 'success');
            document.getElementById('dismissedPayrollGridContainer').style.display = 'none';
            if (activeSalaryTab === 'dismissed') {
                loadDismissedSlipsRegistry();
            }
        } else {
            const err = await res.json();
            showToast(err.error || 'Failed to save payroll.', 'error');
        }
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// BIND DISMISSED EVENT LISTENERS AFTER LOAD
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        const disImportForm = document.getElementById('dismissedSalaryImportForm');
        if (disImportForm) {
            disImportForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const fileInput = document.getElementById('dismissedImportExcelFile');
                const month = document.getElementById('dismissedPayrollMonth').value;
                const year = document.getElementById('dismissedPayrollYear').value;
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                formData.append('month', month);
                formData.append('year', year);
                
                showToast('Uploading and processing excel sheet for dismissed...');
                closeDismissedImportModal();

                const token = localStorage.getItem('accessToken');
                try {
                    const res = await fetch('/api/admin/salary/dismissed/import', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${token}`
                        },
                        body: formData
                    });
                    
                    const data = await res.json();
                    if (res.ok) {
                        showToast(`Import completed. Success: ${data.success}, Failed: ${data.failed}`);
                        if (data.error_report_url) {
                            showToast('Some rows failed. Error report downloaded.', 'warning');
                            window.open(data.error_report_url, '_blank');
                        }
                        if (activeSalaryTab === 'dismissed') {
                            loadDismissedSlipsRegistry();
                        }
                    } else {
                        showToast(`Failed: ${data.detail || 'Import failed'}`, 'error');
                        if (data.error_report_url) {
                            window.open(data.error_report_url, '_blank');
                        }
                    }
                } catch (ex) {
                    showToast(ex.message, 'error');
                }
            });
        }

        const disManualGenForm = document.getElementById('dismissedSalaryManualGenerateForm');
        if (disManualGenForm) {
            disManualGenForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const employeeId = document.getElementById('dismissedManualGenerateEmployee').value;
                const month = document.getElementById('dismissedManualGenerateMonth').value;
                const year = document.getElementById('dismissedManualGenerateYear').value;
                
                if (!employeeId || !month || !year) {
                    showToast('Please fill all required fields.', 'warning');
                    return;
                }
                
                showToast('Generating individual dismissed payslip...');
                try {
                    const res = await apiFetch('/admin/salary/dismissed/generate-individual', {
                        method: 'POST',
                        body: JSON.stringify({
                            employee_id: employeeId,
                            month: parseInt(month),
                            year: parseInt(year)
                        })
                    });
                    
                    if (res.ok) {
                        const data = await res.json();
                        showToast(data.message || 'Payslip generated successfully.', 'success');
                        closeDismissedManualGenerateModal();
                        
                        if (activeSalaryTab === 'dismissed') {
                            loadDismissedSlipsRegistry();
                        }
                    } else {
                        const err = await res.json();
                        showToast(err.error || 'Failed to generate payslip.', 'error');
                    }
                } catch (e) {
                    showToast(e.message, 'error');
                }
            });
        }
    }, 1000);
});

"""

    if "function exportDismissedExcelTemplate" not in js:
        js += dismissed_js_functions

    with open('static/js/features/salary.js', 'w', encoding='utf-8') as f:
        f.write(js)
    
    print("salary.js processed successfully.")

if __name__ == '__main__':
    process_js()
