// static/js/features/salary.js
// Salary, Payroll, Excel Import/Export, and ZIP downloads handlers

let activeSalaryTab = 'slips';
let salaryCurrentPage = 1;
let salaryTotalCount = 0;
let salaryFilteredList = [];

async function loadSalaryData() {
    salaryCurrentPage = 1;
    document.getElementById('pageTitle').textContent = 'Salaries & Payroll';
    
    // Adjust visual panel options based on role
    const role = currentUser.role;
    const adminPanel = document.getElementById('payrollAdminPanel');
    const bulkActions = document.getElementById('slipBulkDownloadActions');
    
    if (role !== 'ADMIN') {
        if (adminPanel) adminPanel.style.display = 'none';
        // Non-admin can only do single/range downloads
        const setupSalaryBtn = document.getElementById('setupSalaryBtn');
        if (setupSalaryBtn) setupSalaryBtn.style.display = 'none';
    }
    if (role === 'EMPLOYEE') {
        if (bulkActions) bulkActions.style.display = 'none';
        // Hide dynamic structures and batches tab for employees
        const tabStructures = document.getElementById('tabStructures');
        const tabBatches = document.getElementById('tabBatches');
        if (tabStructures) tabStructures.style.display = 'none';
        if (tabBatches) tabBatches.style.display = 'none';
    }

    // Load data based on active tab
    await loadSlipsRegistry();
    if (role !== 'EMPLOYEE') {
        await loadStructuresRegistry();
        await loadImportBatches();
    }
}

function switchSalaryTab(tab) {
    activeSalaryTab = tab;
    
    // Toggle active classes on tab headers
    const headers = ['tabSlips', 'tabStructures', 'tabBatches'];
    headers.forEach(h => {
        const el = document.getElementById(h);
        if (el) {
            if (h === 'tab' + tab.charAt(0).toUpperCase() + tab.slice(1)) {
                el.classList.add('active-tab');
            } else {
                el.classList.remove('active-tab');
            }
        }
    });

    // Toggle visibility of panels
    const panels = ['salaryTabSlips', 'salaryTabStructures', 'salaryTabBatches'];
    panels.forEach(p => {
        const el = document.getElementById(p);
        if (el) {
            if (p === 'salaryTab' + tab.charAt(0).toUpperCase() + tab.slice(1)) {
                el.style.display = 'block';
            } else {
                el.style.display = 'none';
            }
        }
    });
}

// 1. Export Excel Template
function exportExcelTemplate() {
    const month = document.getElementById('payrollMonth').value;
    const year = document.getElementById('payrollYear').value;
    const token = localStorage.getItem('accessToken');
    
    showToast('Generating Excel Template...');
    
    // Download directly via window open with auth token or using a fetch with header
    fetch(`/api/admin/salary/export?month=${month}&year=${year}`, {
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
        a.download = `salary_sheet_${month}_${year}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('Template downloaded successfully.');
    })
    .catch(err => {
        showToast('Error exporting template: ' + err.message, 'error');
    });
}

// 2. Import Excel Modals & Submit
function openImportModal() {
    const modal = document.getElementById('salaryImportModal');
    if (modal) modal.style.display = 'flex';
}
function closeImportModal() {
    const modal = document.getElementById('salaryImportModal');
    if (modal) modal.style.display = 'none';
}

// 3. Publish Month
async function publishSlipsMonth() {
    const month = document.getElementById('payrollMonth').value;
    const year = document.getElementById('payrollYear').value;
    
    if (!confirm(`Are you sure you want to publish all draft salary slips for ${month}/${year}?`)) {
        return;
    }
    
    showToast('Publishing slips...');
    try {
        const res = await apiFetch('/admin/salary/publish', {
            method: 'POST',
            body: JSON.stringify({ month, year })
        });
        if (res.ok) {
            const data = await res.json();
            showToast(data.message || 'Slips published successfully.');
            await loadSlipsRegistry();
        } else {
            const err = await res.json();
            showToast(err.error || 'Failed to publish slips.', 'error');
        }
    } catch (e) {
        showToast('Error publishing: ' + e.message, 'error');
    }
}

// 4. Load Slips Registry
async function loadSlipsRegistry() {
    const tableHeader = document.getElementById('salaryRegistryTableHeader');
    const tbody = document.getElementById('salarySlipsTableBody');
    if (!tbody) return;

    const role = currentUser.role;
    const isEmployee = role === 'EMPLOYEE';

    // 1. Rewrite Table Headers dynamically
    if (isEmployee) {
        if (tableHeader) {
            tableHeader.innerHTML = `
                <tr>
                    <th>Month/Year</th>
                    <th>Gross Salary</th>
                    <th>Total Deductions</th>
                    <th>Net Salary</th>
                    <th>Net Credited</th>
                    <th>Payment Status</th>
                    <th>Workflow Status</th>
                    <th>Actions</th>
                </tr>
            `;
        }
    } else {
        if (tableHeader) {
            tableHeader.innerHTML = `
                <tr>
                    <th>Employee ID</th>
                    <th>Name</th>
                    <th>Department</th>
                    <th>Current Salary</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            `;
        }
    }

    const paginationFooter = document.getElementById('salarySlipsPaginationFooter');

    // 2. Load and render rows based on Role
    if (isEmployee) {
        // Employee: Flat month-wise registry for themselves
        try {
            const res = await apiFetch('/salary/history?no_pagination=true');
            if (res.ok) {
                const slipsData = await res.json();
                salaryFilteredList = slipsData.results || slipsData;
                salaryTotalCount = salaryFilteredList.length;

                if (paginationFooter) {
                    paginationFooter.style.display = 'flex';
                    updateSalaryPaginationControls(salaryCurrentPage, salaryTotalCount);
                }

                if (salaryFilteredList.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: #777; padding: 20px;">No salary slips generated yet.</td></tr>`;
                    return;
                }

                const startIdx = (salaryCurrentPage - 1) * 10;
                const paginatedSlips = salaryFilteredList.slice(startIdx, startIdx + 10);

                tbody.innerHTML = paginatedSlips.map(s => {
                    const monthNames = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                    const period = `${monthNames[s.month]} ${s.year}`;
                    
                    const actions = `
                        <div style="display:flex; gap:5px;">
                            <button class="btn btn-primary" style="font-size:8pt; padding:4px 8px; background-color:#7c3aed;" onclick="downloadSlipSingle(${s.employee_id}, ${s.month}, ${s.year})">Download PDF</button>
                        </div>
                    `;

                    return `
                        <tr>
                            <td><strong>${period}</strong></td>
                            <td>Rs. ${s.gross_salary}</td>
                            <td>Rs. ${s.total_deductions}</td>
                            <td><strong>Rs. ${s.net_salary}</strong></td>
                            <td>Rs. ${s.net_credited_amount}</td>
                            <td><span style="font-weight:bold; color:${s.payment_status === 'paid' ? '#16a34a' : '#ea580c'}; text-transform: capitalize;">${s.payment_status}</span></td>
                            <td><span style="font-weight:bold; color:${s.status === 'published' ? '#2563eb' : '#eab308'}; text-transform: capitalize;">${s.status}</span></td>
                            <td>${actions}</td>
                        </tr>
                    `;
                }).join('');
            }
        } catch (e) {
            console.error(e);
        }
    } else {
        // Admin or HR: Consolidated list of employees (one row per employee)
        try {
            const res = await apiFetch('/employees/?type=all&no_pagination=true');
            if (res.ok) {
                const empsData = await res.json();
                salaryFilteredList = empsData.results || empsData;
                salaryTotalCount = salaryFilteredList.length;

                if (paginationFooter) {
                    paginationFooter.style.display = 'flex';
                    updateSalaryPaginationControls(salaryCurrentPage, salaryTotalCount);
                }

                if (salaryFilteredList.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #777; padding: 20px;">No employees found.</td></tr>`;
                    return;
                }

                const startIdx = (salaryCurrentPage - 1) * 10;
                const paginatedEmps = salaryFilteredList.slice(startIdx, startIdx + 10);

                tbody.innerHTML = paginatedEmps.map(emp => {
                    // Calculate current salary from latest structure
                    let currentSalaryHtml = '<span style="color: #999; font-style: italic;">Not Setup</span>';
                    if (emp.salary_structures && emp.salary_structures.length > 0) {
                        const sorted = emp.salary_structures.sort((a, b) => new Date(b.effective_from) - new Date(a.effective_from));
                        currentSalaryHtml = `<strong>Rs. ${sorted[0].net_salary}</strong>`;
                    }
                    
                    const statusColor = emp.status === 'Active' ? '#16a34a' : '#ef4444';
                    
                    const actions = `
                        <div style="display:flex; gap:5px;">
                            <button class="btn btn-primary" style="font-size:8pt; padding:4px 8px; background-color:#2563eb;" onclick="viewEmployeeSalaryHistory(${emp.id}, '${emp.name.replace(/'/g, "\\'")}')">View History</button>
                        </div>
                    `;

                    return `
                        <tr>
                            <td><strong>${emp.emp_id}</strong></td>
                            <td><strong>${emp.name}</strong></td>
                            <td>${emp.department_name || 'N/A'}</td>
                            <td>${currentSalaryHtml}</td>
                            <td><span style="font-weight:bold; color:${statusColor};">${emp.status}</span></td>
                            <td>${actions}</td>
                        </tr>
                    `;
                }).join('');
            }
        } catch (e) {
            console.error(e);
        }
    }
}

function changeSalaryPage(direction) {
    const maxPage = Math.ceil(salaryTotalCount / 10) || 1;
    salaryCurrentPage = Math.max(1, Math.min(maxPage, salaryCurrentPage + direction));
    loadSlipsRegistry();
}

function updateSalaryPaginationControls(currentPage, totalCount) {
    const pageStart = totalCount === 0 ? 0 : (currentPage - 1) * 10 + 1;
    const pageEnd = Math.min(currentPage * 10, totalCount);
    
    const startEl = document.getElementById('salaryPageStart');
    const endEl = document.getElementById('salaryPageEnd');
    const totalEl = document.getElementById('salaryTotalCount');
    const prevBtn = document.getElementById('salaryPrevBtn');
    const nextBtn = document.getElementById('salaryNextBtn');
    
    if (startEl) startEl.textContent = pageStart;
    if (endEl) endEl.textContent = pageEnd;
    if (totalEl) totalEl.textContent = totalCount;
    
    if (prevBtn) prevBtn.disabled = currentPage <= 1;
    if (nextBtn) nextBtn.disabled = pageEnd >= totalCount;
}

// 5. Load Structures Registry
async function loadStructuresRegistry() {
    try {
        const res = await apiFetch('/salaries/');
        if (res.ok) {
            const structsData = await res.json();
            const structs = structsData.results || structsData;
            const tbody = document.getElementById('salaryStructureTableBody');
            if (!tbody) return;

            tbody.innerHTML = structs.map(s => `
                <tr>
                    <td><strong>${s.employee_details ? s.employee_details.name + ' (' + s.employee_details.emp_id + ')' : s.employee}</strong></td>
                    <td>Rs. ${s.gross_salary}</td>
                    <td>Rs. ${s.pf_contribution}</td>
                    <td>Rs. ${s.esi}</td>
                    <td>Rs. ${s.labour_welfare_fund}</td>
                    <td>Rs. ${s.professional_tax}</td>
                    <td>Rs. ${s.other_deductions}</td>
                    <td>${s.effective_from}</td>
                </tr>
            `).join('');
        }
    } catch (e) {
        console.error(e);
    }
}

// 6. Load Import Batches Audit Log
async function loadImportBatches() {
    try {
        const res = await apiFetch('/admin/salary/import-batches');
        if (res.ok) {
            const batchesData = await res.json();
            const batches = batchesData.results || batchesData;
            const tbody = document.getElementById('salaryBatchesTableBody');
            if (!tbody) return;

            if (batches.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: #777; padding: 20px;">No import runs recorded.</td></tr>`;
                return;
            }

            tbody.innerHTML = batches.map(b => {
                const errorReport = b.error_report_path 
                    ? `<a href="${b.error_report_path}" target="_blank" style="color: #ef4444; font-weight:600; text-decoration:underline;">Download Report</a>`
                    : 'None';
                const formattedDate = new Date(b.uploaded_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });
                
                let statusColor = '#16a34a';
                if (b.status === 'partial') statusColor = '#eab308';
                if (b.status === 'failed') statusColor = '#ef4444';

                return `
                    <tr>
                        <td><strong>Batch #${b.id}</strong></td>
                        <td>Month: ${b.month}/${b.year}</td>
                        <td>${b.file_name}</td>
                        <td>${b.uploaded_by_username || 'Admin'}</td>
                        <td>${formattedDate}</td>
                        <td>Total: ${b.total_records} | Success: ${b.success_count} | Failed: ${b.failed_count}</td>
                        <td><span style="font-weight:bold; color:${statusColor}; text-transform:uppercase;">${b.status}</span></td>
                        <td>${errorReport}</td>
                    </tr>
                `;
            }).join('');
        }
    } catch (e) {
        console.error(e);
    }
}

// 7. Single Download Helper
function downloadSlipSingle(employeeId, month, year) {
    const token = localStorage.getItem('accessToken');
    showToast('Downloading PDF Slip...');
    
    fetch(`/api/salary/slip/download?type=single&employee_id=${employeeId}&month=${month}&year=${year}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(res => {
        if (!res.ok) throw new Error('Slip download failed');
        return res.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `payslip_${month}_${year}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
    })
    .catch(err => showToast(err.message, 'error'));
}

// 8. Bulk Download Helper (ZIP)
function downloadSlipBulk() {
    const month = document.getElementById('payrollMonth').value;
    const year = document.getElementById('payrollYear').value;
    const token = localStorage.getItem('accessToken');
    
    showToast('Preparing ZIP archive...');
    fetch(`/api/salary/slip/download?type=bulk_month&month=${month}&year=${year}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(res => {
        if (!res.ok) throw new Error('Bulk download failed. Check if slips exist for this period.');
        return res.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `payslips_bulk_${month}_${year}.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('ZIP downloaded successfully.');
    })
    .catch(err => showToast(err.message, 'error'));
}

// 9. Range Download Modals & Handlers
function openRangeDownloadModal() {
    const modal = document.getElementById('rangeDownloadModal');
    if (modal) modal.style.display = 'flex';
}
function closeRangeDownloadModal() {
    const modal = document.getElementById('rangeDownloadModal');
    if (modal) modal.style.display = 'none';
}

// 10. Manual Edit Modals & Handlers
function recalculateEditSlipNetSalary(shouldUpdateInputField = true) {
    const monthDays = parseFloat(document.getElementById('editMonthDays').value) || 0;
    const workedDays = parseFloat(document.getElementById('editWorkedDays').value) || 0;
    const weekend = parseFloat(document.getElementById('editWeekend').value) || 0;
    const cl = parseFloat(document.getElementById('editCl').value) || 0;
    const extra = parseFloat(document.getElementById('editExtra').value) || 0;

    const monthSalary = parseFloat(document.getElementById('editMonthSalary').value) || 0;
    const extraDaysWorking = parseFloat(document.getElementById('editExtraDaysWorking').value) || 0;
    const fineAdvance = parseFloat(document.getElementById('editFineAdvance').value) || 0;

    const payableDays = workedDays + weekend + cl + extra;
    let payableSalary = 0;
    if (monthDays > 0) {
        payableSalary = (monthSalary / monthDays) * payableDays;
    } else {
        payableSalary = monthSalary;
    }
    const netPayable = payableSalary + extraDaysWorking - fineAdvance;

    document.getElementById('editPayableDays').value = payableDays.toFixed(2);
    document.getElementById('editPayableSalary').value = payableSalary.toFixed(2);
    document.getElementById('editNetPayable').value = netPayable.toFixed(2);

    if (shouldUpdateInputField) {
        document.getElementById('editNetCredited').value = netPayable.toFixed(2);
    }

    // Update Summary card
    const sg = document.getElementById('summaryGross');
    const sd = document.getElementById('summaryDeductions');
    const sn = document.getElementById('summaryNet');
    const sc = document.getElementById('summaryNetCredited');

    if (sg) sg.textContent = `Rs. ${monthSalary.toFixed(2)}`;
    if (sd) sd.textContent = `Rs. ${fineAdvance.toFixed(2)}`;
    if (sn) sn.textContent = `Rs. ${netPayable.toFixed(2)}`;
    if (sc) {
        const creditedVal = parseFloat(document.getElementById('editNetCredited').value) || netPayable;
        sc.textContent = `Rs. ${creditedVal.toFixed(2)}`;
    }
}

function openEditSlipModal(slip) {
    const modal = document.getElementById('editSalarySlipModal');
    if (!modal) return;
    
    modal.style.display = 'flex';
    document.getElementById('editSlipId').value = slip.id;

    // Fill current inputs
    document.getElementById('editMonthDays').value = parseFloat(slip.month_days || 0).toFixed(2);
    document.getElementById('editWorkedDays').value = parseFloat(slip.worked_days || 0).toFixed(2);
    document.getElementById('editWeekend').value = parseFloat(slip.weekend || 0).toFixed(2);
    document.getElementById('editCl').value = parseFloat(slip.cl || 0).toFixed(2);
    document.getElementById('editExtra').value = parseFloat(slip.extra || 0).toFixed(2);
    document.getElementById('editPayableDays').value = parseFloat(slip.payable_days || 0).toFixed(2);
    
    document.getElementById('editMonthSalary').value = parseFloat(slip.month_salary || 0).toFixed(2);
    document.getElementById('editPayableSalary').value = parseFloat(slip.payable_salary || 0).toFixed(2);
    document.getElementById('editExtraDaysWorking').value = parseFloat(slip.extra_days_working || 0).toFixed(2);
    
    document.getElementById('editFineAdvance').value = parseFloat(slip.fine_advance || 0).toFixed(2);
    document.getElementById('editNetPayable').value = parseFloat(slip.net_payable || 0).toFixed(2);
    
    document.getElementById('editBankAccountNo').value = slip.bank_account_no || '';
    document.getElementById('editBankName').value = slip.bank_name || '';

    document.getElementById('editLocation').value = slip.location || 'Mohali';
    document.getElementById('editNetCredited').value = parseFloat(slip.net_credited_amount || slip.net_payable || 0).toFixed(2);
    document.getElementById('editPaymentStatus').value = slip.payment_status || 'pending';
    document.getElementById('editPaymentDate').value = slip.payment_date || '';
    document.getElementById('editTransactionRef').value = slip.transaction_ref || '';

    // Populate previous values helper spans
    document.getElementById('prevMonthDays').textContent = `Was: ${parseFloat(slip.month_days || 0).toFixed(2)} days`;
    document.getElementById('prevWorkedDays').textContent = `Was: ${parseFloat(slip.worked_days || 0).toFixed(2)} days`;
    document.getElementById('prevWeekend').textContent = `Was: ${parseFloat(slip.weekend || 0).toFixed(2)} days`;
    document.getElementById('prevCl').textContent = `Was: ${parseFloat(slip.cl || 0).toFixed(2)} days`;
    document.getElementById('prevExtra').textContent = `Was: ${parseFloat(slip.extra || 0).toFixed(2)} days`;
    document.getElementById('prevPayableDays').textContent = `Was: ${parseFloat(slip.payable_days || 0).toFixed(2)} days`;
    
    document.getElementById('prevMonthSalary').textContent = `Was: Rs. ${parseFloat(slip.month_salary || 0).toFixed(2)}`;
    document.getElementById('prevPayableSalary').textContent = `Was: Rs. ${parseFloat(slip.payable_salary || 0).toFixed(2)}`;
    document.getElementById('prevExtraDaysWorking').textContent = `Was: Rs. ${parseFloat(slip.extra_days_working || 0).toFixed(2)}`;
    
    document.getElementById('prevFineAdvance').textContent = `Was: Rs. ${parseFloat(slip.fine_advance || 0).toFixed(2)}`;
    document.getElementById('prevNetPayable').textContent = `Was: Rs. ${parseFloat(slip.net_payable || 0).toFixed(2)}`;
    
    document.getElementById('prevBankAccountNo').textContent = `Was: ${slip.bank_account_no || 'None'}`;
    document.getElementById('prevBankName').textContent = `Was: ${slip.bank_name || 'None'}`;

    document.getElementById('prevLocation').textContent = `Was: ${slip.location || 'Mohali'}`;
    document.getElementById('prevNetCredited').textContent = `Was: Rs. ${parseFloat(slip.net_credited_amount || 0).toFixed(2)}`;
    document.getElementById('prevPaymentStatus').textContent = `Was: ${slip.payment_status}`;
    document.getElementById('prevPaymentDate').textContent = `Was: ${slip.payment_date || 'None'}`;
    document.getElementById('prevTransactionRef').textContent = `Was: ${slip.transaction_ref || 'None'}`;

    // Initialize summary card numbers
    recalculateEditSlipNetSalary(false);
}

function closeEditSlipModal() {
    const modal = document.getElementById('editSalarySlipModal');
    if (modal) modal.style.display = 'none';
}

// 11. Legacy Structure Modals
function openSalaryStructureModal() {
    const modal = document.getElementById('salaryStructureModal');
    if (modal) {
        modal.style.display = 'flex';
        loadActiveEmployeesSelect('structEmployeeSelect');
    }
}
function closeSalaryStructureModal() {
    const modal = document.getElementById('salaryStructureModal');
    if (modal) modal.style.display = 'none';
}

async function loadActiveEmployeesSelect(selectId) {
    try {
        const res = await apiFetch('/employees/?type=all&no_pagination=true');
        if (res.ok) {
            const emps = await res.json();
            const empList = emps.results || emps;
            const select = document.getElementById(selectId);
            if (select) {
                select.innerHTML = empList.filter(e => e.status === 'Active').map(e => `<option value="${e.id}">${e.name} (${e.emp_id})</option>`).join('');
            }
        }
    } catch (e) {
        console.error(e);
    }
}

// Event Listeners for Forms
document.addEventListener('DOMContentLoaded', () => {
    // Structure Form
    const structureForm = document.getElementById('salaryStructureForm');
    if (structureForm) {
        structureForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = {
                employee: document.getElementById('structEmployeeSelect').value,
                effective_from: document.getElementById('structEffectiveFrom').value,
                gross_salary: document.getElementById('structGrossSalary').value,
                pf_contribution: document.getElementById('structPfContribution').value,
                esi: document.getElementById('structEsi').value,
                labour_welfare_fund: document.getElementById('structLabourWelfareFund').value,
                professional_tax: document.getElementById('structProfessionalTax').value,
                other_deductions: document.getElementById('structOtherDeductions').value
            };
            
            try {
                const res = await apiFetch('/salaries/', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                if (res.ok) {
                    showToast('Salary structure setup successfully.');
                    closeSalaryStructureModal();
                    await loadSalaryData();
                } else {
                    const err = await res.json();
                    showToast(JSON.stringify(err), 'error');
                }
            } catch (ex) {
                showToast(ex.message, 'error');
            }
        });
    }

    // Import Excel Form
    const importForm = document.getElementById('salaryImportForm');
    if (importForm) {
        importForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('importExcelFile');
            const month = document.getElementById('payrollMonth').value;
            const year = document.getElementById('payrollYear').value;
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('month', month);
            formData.append('year', year);
            
            showToast('Uploading and processing excel sheet...');
            closeImportModal();

            const token = localStorage.getItem('accessToken');
            try {
                const res = await fetch('/api/admin/salary/import', {
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
                        // Notify error report
                        showToast('Some rows failed. Error report downloaded.', 'warning');
                        window.open(data.error_report_url, '_blank');
                    }
                    await loadSalaryData();
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

    // Range Download Form
    const rangeForm = document.getElementById('rangeDownloadForm');
    if (rangeForm) {
        rangeForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const fromMonth = document.getElementById('rangeFromMonth').value;
            const fromYear = document.getElementById('rangeFromYear').value;
            const toMonth = document.getElementById('rangeToMonth').value;
            const toYear = document.getElementById('rangeToYear').value;
            const token = localStorage.getItem('accessToken');
            
            closeRangeDownloadModal();
            showToast('Generating ZIP file...');
            
            fetch(`/api/salary/slip/download?type=range&from_month=${fromMonth}&from_year=${fromYear}&to_month=${toMonth}&to_year=${toYear}&employee_id=${currentUser.employee_id || ''}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })
            .then(res => {
                if (!res.ok) throw new Error('Range download failed.');
                return res.blob();
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `payslips_range_${fromMonth}_${fromYear}_to_${toMonth}_${toYear}.zip`;
                document.body.appendChild(a);
                a.click();
                a.remove();
            })
            .catch(err => showToast(err.message, 'error'));
        });
    }

    // Manual Edit Form
    const editForm = document.getElementById('editSalarySlipForm');
    if (editForm) {
        editForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const slipId = document.getElementById('editSlipId').value;
            
            const data = {
                month_days: document.getElementById('editMonthDays').value,
                worked_days: document.getElementById('editWorkedDays').value,
                weekend: document.getElementById('editWeekend').value,
                cl: document.getElementById('editCl').value,
                extra: document.getElementById('editExtra').value,
                payable_days: document.getElementById('editPayableDays').value,
                month_salary: document.getElementById('editMonthSalary').value,
                payable_salary: document.getElementById('editPayableSalary').value,
                extra_days_working: document.getElementById('editExtraDaysWorking').value,
                fine_advance: document.getElementById('editFineAdvance').value,
                net_payable: document.getElementById('editNetPayable').value,
                bank_account_no: document.getElementById('editBankAccountNo').value,
                bank_name: document.getElementById('editBankName').value,
                location: document.getElementById('editLocation').value,
                net_credited_amount: document.getElementById('editNetCredited').value,
                payment_status: document.getElementById('editPaymentStatus').value,
                payment_date: document.getElementById('editPaymentDate').value,
                transaction_ref: document.getElementById('editTransactionRef').value
            };

            showToast('Saving corrections...');
            closeEditSlipModal();
            
            try {
                const res = await apiFetch(`/admin/salary/edit/${slipId}/`, {
                    method: 'PUT',
                    body: JSON.stringify(data)
                });
                if (res.ok) {
                    showToast('Salary slip updated successfully.');
                    await loadSalaryData();
                    const urlEmpId = getEmployeeIdFromUrl();
                    if (urlEmpId) {
                        await loadDedicatedEmployeeSalaryHistory(urlEmpId);
                    }
                } else {
                    const err = await res.json();
                    showToast(JSON.stringify(err), 'error');
                }
            } catch (ex) {
                showToast(ex.message, 'error');
            }
        });
    }

    // Add change listeners to edit inputs for auto recalculation
    const inputIds = [
        'editMonthDays', 'editWorkedDays', 'editWeekend', 'editCl', 'editExtra',
        'editMonthSalary', 'editExtraDaysWorking', 'editFineAdvance'
    ];
    inputIds.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener('input', recalculateEditSlipNetSalary);
        }
    });

    const netInput = document.getElementById('editNetCredited');
    if (netInput) {
        netInput.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value) || 0;
            const el = document.getElementById('summaryNetCredited');
            if (el) el.textContent = `Rs. ${val.toFixed(2)}`;
        });
    }
});

// Dedicated Salary History Page Logic
let currentHistoryEmployeeId = null;
let currentHistoryEmployeeName = "";

function viewEmployeeSalaryHistory(employeeId, employeeName) {
    currentHistoryEmployeeId = employeeId;
    currentHistoryEmployeeName = employeeName;
    switchView('salaryHistoryView', true, { employeeId: employeeId });
}

async function loadDedicatedEmployeeSalaryHistory(employeeId) {
    try {
        currentHistoryEmployeeId = employeeId;

        // Explicitly update the page title in the navbar
        const pageTitleEl = document.getElementById('pageTitle');
        if (pageTitleEl) {
            pageTitleEl.textContent = 'Employee Salary History';
        }

        // Fetch employee details
        try {
            const empRes = await apiFetch(`/employees/${employeeId}/`);
            if (empRes.ok) {
                const emp = await empRes.json();
                currentHistoryEmployeeName = emp.name || "";
                
                const nameEl = document.getElementById('historyEmployeeName');
                if (nameEl) nameEl.textContent = emp.name || "--";
                
                const idEl = document.getElementById('historyEmployeeId');
                if (idEl) idEl.textContent = emp.emp_id || "--";
                
                const deptEl = document.getElementById('historyEmployeeDept');
                if (deptEl) {
                    deptEl.textContent = emp.department_details ? emp.department_details.name : (emp.department_name || emp.department || 'N/A');
                }
                
                const desgEl = document.getElementById('historyEmployeeDesg');
                if (desgEl) desgEl.textContent = emp.designation || 'N/A';
                
                const statusEl = document.getElementById('historyEmployeeStatus');
                if (statusEl) {
                    statusEl.textContent = emp.status || "--";
                    statusEl.className = `status-pill ${emp.status === 'Active' ? 'synced' : 'action-needed'}`;
                }

                // Avatar Initials
                const initialsEl = document.getElementById('historyEmployeeAvatar');
                if (initialsEl) {
                    const initials = emp.name ? emp.name.split(' ').map(n => n.charAt(0)).join('').toUpperCase().substring(0, 2) : '--';
                    initialsEl.textContent = initials || '--';
                }

                // Current Salary
                let currentSalaryStr = "Not Setup";
                if (emp.salary_structures && emp.salary_structures.length > 0) {
                    const sorted = emp.salary_structures.sort((a, b) => new Date(b.effective_from) - new Date(a.effective_from));
                    currentSalaryStr = `Rs. ${sorted[0].net_salary}`;
                }
                const salaryEl = document.getElementById('historyEmployeeSalary');
                if (salaryEl) salaryEl.textContent = currentSalaryStr;
            }
        } catch (e) {
            console.error("Error loading employee details for history view:", e);
        }

        // Fetch employee summary statistics
        try {
            const sumRes = await apiFetch(`/salary/employee/${employeeId}/summary`);
            if (sumRes.ok) {
                const sumData = await sumRes.json();
                const credEl = document.getElementById('historyCardCredited');
                if (credEl) credEl.textContent = `Rs. ${sumData.total_salary_credited || '0.00'}`;
                
                const dedEl = document.getElementById('historyCardDeductions');
                if (dedEl) dedEl.textContent = `Rs. ${sumData.total_deductions || '0.00'}`;
                
                const paysEl = document.getElementById('historyCardPayslips');
                if (paysEl) paysEl.textContent = sumData.total_payslips ?? 0;
                
                const lastPayEl = document.getElementById('historyCardLastPayment');
                if (lastPayEl) lastPayEl.textContent = sumData.last_payment_date || '-';
            }
        } catch (e) {
            console.error("Error loading employee salary summary statistics:", e);
        }

        // Set default filter values
        const today = new Date();
        const fromMonthEl = document.getElementById('historyPageFromMonth');
        if (fromMonthEl) fromMonthEl.value = "1";
        
        const fromYearEl = document.getElementById('historyPageFromYear');
        if (fromYearEl) fromYearEl.value = today.getFullYear();
        
        const toMonthEl = document.getElementById('historyPageToMonth');
        if (toMonthEl) toMonthEl.value = today.getMonth() + 1;
        
        const toYearEl = document.getElementById('historyPageToYear');
        if (toYearEl) toYearEl.value = today.getFullYear();
        
        const payStatEl = document.getElementById('historyPagePaymentStatus');
        if (payStatEl) payStatEl.value = "";

        // Clear select all checkbox
        const selectAllBox = document.getElementById('selectAllHistorySlips');
        if (selectAllBox) selectAllBox.checked = false;

        // Load dynamic list data
        await loadDedicatedEmployeeSalaryHistoryData();
    } catch (e) {
        console.error("Fatal error in loadDedicatedEmployeeSalaryHistory:", e);
    }
}

async function loadDedicatedEmployeeSalaryHistoryData() {
    try {
        if (!currentHistoryEmployeeId) return;

        const fromMonthEl = document.getElementById('historyPageFromMonth');
        const fromYearEl = document.getElementById('historyPageFromYear');
        const toMonthEl = document.getElementById('historyPageToMonth');
        const toYearEl = document.getElementById('historyPageToYear');
        const paymentStatusEl = document.getElementById('historyPagePaymentStatus');

        const fromMonth = fromMonthEl ? fromMonthEl.value : "1";
        const fromYear = fromYearEl ? fromYearEl.value : new Date().getFullYear();
        const toMonth = toMonthEl ? toMonthEl.value : new Date().getMonth() + 1;
        const toYear = toYearEl ? toYearEl.value : new Date().getFullYear();
        const paymentStatus = paymentStatusEl ? paymentStatusEl.value : "";

        const tbody = document.getElementById('historyPageTableBody');
        if (!tbody) return;

        tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: #777; padding: 20px;">Loading history records...</td></tr>`;

        let url = `/salary/history?employee_id=${currentHistoryEmployeeId}&from=${fromYear}-${fromMonth}&to=${toYear}-${toMonth}`;
        if (paymentStatus) {
            url += `&payment_status=${paymentStatus}`;
        }

        try {
            const res = await apiFetch(url);
            if (res.ok) {
                const slipsData = await res.json();
                const slips = slipsData.results || slipsData;

                if (!Array.isArray(slips) || slips.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: #777; padding: 20px;">No salary slips found for this selection.</td></tr>`;
                    return;
                }

                const isAdmin = currentUser && currentUser.role === 'ADMIN';

                tbody.innerHTML = slips.map(s => {
                    const monthNames = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                    const period = `${monthNames[s.month]} ${s.year}`;
                    
                    const actions = `
                        <div style="display:flex; gap:5px; justify-content: flex-end;">
                            <button class="btn btn-primary" style="font-size:8pt; padding:4px 8px; background-color:#7c3aed; border-radius: 4px;" onclick="viewPayslipSingle(${s.employee_id}, ${s.month}, ${s.year})">View Payslip</button>
                            <button class="btn btn-primary" style="font-size:8pt; padding:4px 8px; background-color:#10b981; border-radius: 4px;" onclick="downloadSlipSingle(${s.employee_id}, ${s.month}, ${s.year})">Download PDF</button>
                            ${isAdmin ? `<button class="btn btn-primary" style="font-size:8pt; padding:4px 8px; background-color:#475569; border-radius: 4px;" onclick="openEditSlipModal(${JSON.stringify(s).replace(/"/g, '&quot;')})">Edit</button>` : ''}
                        </div>
                    `;

                    return `
                        <tr style="border-bottom: 1px solid var(--border-color); height: 50px;">
                            <td style="padding: 12px 20px;"><input type="checkbox" class="history-slip-checkbox" data-id="${s.id}" style="cursor: pointer; width: 16px; height: 16px;"></td>
                            <td style="padding: 12px 20px;"><strong>${period}</strong></td>
                            <td style="padding: 12px 20px;">Rs. ${s.gross_salary}</td>
                            <td style="padding: 12px 20px;">Rs. ${s.total_deductions}</td>
                            <td style="padding: 12px 20px;"><strong>Rs. ${s.net_salary}</strong></td>
                            <td style="padding: 12px 20px;">Rs. ${s.net_credited_amount}</td>
                            <td style="padding: 12px 20px;"><span style="font-weight:bold; color:${s.payment_status === 'paid' ? '#16a34a' : '#ea580c'}; text-transform: capitalize;">${s.payment_status}</span></td>
                            <td style="padding: 12px 20px;"><span style="font-weight:bold; color:${s.status === 'published' ? '#2563eb' : '#eab308'}; text-transform: capitalize;">${s.status}</span></td>
                            <td style="padding: 12px 20px; text-align: right;">${actions}</td>
                        </tr>
                    `;
                }).join('');
            }
        } catch (e) {
            console.error("Error loading slips data:", e);
            tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: #ef4444; padding: 20px;">Error loading history data.</td></tr>`;
        }
    } catch (e) {
        console.error("Fatal error in loadDedicatedEmployeeSalaryHistoryData:", e);
    }
}

function toggleSelectAllHistorySlips(source) {
    const checkboxes = document.querySelectorAll('.history-slip-checkbox');
    checkboxes.forEach(cb => cb.checked = source.checked);
}

function downloadSelectedPayslips() {
    const checkboxes = document.querySelectorAll('.history-slip-checkbox:checked');
    if (checkboxes.length === 0) {
        showToast('Please select at least one payslip to download.', 'warning');
        return;
    }
    const ids = Array.from(checkboxes).map(cb => cb.getAttribute('data-id')).join(',');
    const token = localStorage.getItem('accessToken');
    
    showToast('Generating ZIP for selected payslips...');
    fetch(`/api/salary/slip/download?type=selected&slip_ids=${ids}&employee_id=${currentHistoryEmployeeId}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(res => {
        if (!res.ok) throw new Error('Selected download failed.');
        return res.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `payslips_selected_${Date.now()}.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('ZIP downloaded successfully.');
    })
    .catch(err => showToast(err.message, 'error'));
}

function downloadHistoryZIPRange() {
    if (!currentHistoryEmployeeId) return;

    const fromMonth = document.getElementById('historyPageFromMonth').value;
    const fromYear = document.getElementById('historyPageFromYear').value;
    const toMonth = document.getElementById('historyPageToMonth').value;
    const toYear = document.getElementById('historyPageToYear').value;
    const token = localStorage.getItem('accessToken');

    showToast('Generating ZIP file...');
    
    fetch(`/api/salary/slip/download?type=range&from_month=${fromMonth}&from_year=${fromYear}&to_month=${toMonth}&to_year=${toYear}&employee_id=${currentHistoryEmployeeId}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(res => {
        if (!res.ok) throw new Error('Range ZIP download failed.');
        return res.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `payslips_${currentHistoryEmployeeName.replace(/\s+/g, '_')}_${fromMonth}_${fromYear}_to_${toMonth}_${toYear}.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('ZIP downloaded successfully.');
    })
    .catch(err => showToast(err.message, 'error'));
}

function exportHistoryExcel() {
    if (!currentHistoryEmployeeId) return;
    const fromMonth = document.getElementById('historyPageFromMonth').value;
    const fromYear = document.getElementById('historyPageFromYear').value;
    const toMonth = document.getElementById('historyPageToMonth').value;
    const toYear = document.getElementById('historyPageToYear').value;
    const paymentStatus = document.getElementById('historyPagePaymentStatus').value;
    const token = localStorage.getItem('accessToken');

    showToast('Generating Excel report...');
    
    let url = `/api/salary/employee/${currentHistoryEmployeeId}/export?from=${fromYear}-${fromMonth}&to=${toYear}-${toMonth}`;
    if (paymentStatus) {
        url += `&payment_status=${paymentStatus}`;
    }

    fetch(url, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(res => {
        if (!res.ok) throw new Error('Excel export failed.');
        return res.blob();
    })
    .then(blob => {
        const urlObj = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = urlObj;
        a.download = `salary_history_${currentHistoryEmployeeName.replace(/\s+/g, '_')}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('Excel downloaded successfully.');
    })
    .catch(err => showToast(err.message, 'error'));
}

async function viewPayslipSingle(employeeId, month, year) {
    const token = localStorage.getItem('accessToken');
    showToast('Loading payslip PDF preview...');
    try {
        const res = await fetch(`/api/salary/slip/download?type=single&employee_id=${employeeId}&month=${month}&year=${year}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (res.ok) {
            const blob = await res.blob();
            const blobUrl = window.URL.createObjectURL(blob);
            if (typeof openDocumentViewerModal === 'function') {
                openDocumentViewerModal(blobUrl, 'application/pdf', `Payslip ${month}/${year}`);
            } else {
                window.open(blobUrl, '_blank');
            }
        } else {
            showToast('Failed to load payslip preview.', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Preview error.', 'error');
    }
}
