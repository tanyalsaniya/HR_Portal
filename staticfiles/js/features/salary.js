// static/js/features/salary.js
// Salary, Payroll, Bulk slips generation, and increment approval handlers

// ---------- PAYROLL / SALARIES VIEW ----------
async function loadSalaryData() {
    document.getElementById('pageTitle').textContent = 'Salaries & Payroll';
    try {
        // Load Salary structures
        const structRes = await apiFetch('/salaries/');
        if (structRes.ok) {
            const structs = await structRes.json();
            const structList = structs.results || structs;
            const tbody = document.getElementById('salaryStructureTableBody');
            
            if (tbody) {
                tbody.innerHTML = structList.map(s => `
                    <tr>
                        <td>${s.employee_details ? s.employee_details.first_name + ' ' + s.employee_details.last_name + ' (' + s.employee_details.emp_id + ')' : s.employee}</td>
                        <td>Rs. ${s.basic}</td>
                        <td>Rs. ${s.hra}</td>
                        <td>Rs. ${s.gross_salary}</td>
                        <td>Rs. ${s.total_deductions}</td>
                        <td><strong>Rs. ${s.net_salary}</strong></td>
                        <td>${s.effective_from}</td>
                    </tr>
                `).join('');
            }
        }

        // If user has permission, load Raise approvals reminders
        if (hasPermission('salary.approve_increments')) {
            const remRes = await apiFetch('/salary/increments/');
            if (remRes.ok) {
                const rems = await remRes.json();
                const remList = rems.results || rems;
                const tbody = document.getElementById('salaryIncrementsReminderBody');
                
                if (tbody) {
                    tbody.innerHTML = remList.map(r => `
                        <tr>
                            <td>${r.employee_details ? r.employee_details.first_name + ' ' + r.employee_details.last_name + ' (' + r.employee_details.emp_id + ')' : r.employee}</td>
                            <td>${r.anniversary_date}</td>
                            <td><span style="font-weight:bold; color:${r.status === 'Pending' ? '#eab308' : '#22c55e'}">${r.status}</span></td>
                            <td>
                                ${r.status === 'Pending' ? `<button class="btn btn-primary" style="font-size:8pt; padding:4px 8px;" onclick="openRaiseApprovalModal(${r.id}, ${r.employee}, '${r.employee_details.first_name} ${r.employee_details.last_name}')">Review & Approve</button>` : 'Actioned'}
                            </td>
                        </tr>
                    `).join('');
                }
            }
        }
    } catch (e) {
        console.error(e);
    }
}

// Define Salary structure modal
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
        const res = await apiFetch('/employees/');
        if (res.ok) {
            const emps = await res.json();
            const empList = emps.results || emps;
            const select = document.getElementById(selectId);
            if (select) {
                select.innerHTML = empList.filter(e => e.status === 'Active').map(e => `<option value="${e.id}">${e.first_name} ${e.last_name} (${e.emp_id})</option>`).join('');
            }
        }
    } catch (e) {
        console.error(e);
    }
}

// Bulk payslip modal
function openBulkSlipModal() {
    const modal = document.getElementById('bulkSlipModal');
    if (modal) modal.style.display = 'flex';
}
function closeBulkSlipModal() {
    const modal = document.getElementById('bulkSlipModal');
    if (modal) modal.style.display = 'none';
}

// Raise approval modal
async function openRaiseApprovalModal(reminderId, employeeId, nameStr) {
    const modal = document.getElementById('approveIncrementModal');
    if (!modal) return;
    
    modal.style.display = 'flex';
    document.getElementById('incReminderId').value = reminderId;
    document.getElementById('incEmployeeId').value = employeeId;
    document.getElementById('incEmployeeName').value = nameStr;
    
    // Set effective date anniversary default
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('incEffectiveDate').value = today;

    // Fetch current salary details to print old net
    try {
        const res = await apiFetch(`/salaries/?employee_id=${employeeId}`);
        if (res.ok) {
            const data = await res.json();
            const list = data.results || data;
            if (list.length > 0) {
                const current = list[0];
                document.getElementById('incCurrentNet').value = `Gross: Rs. ${current.gross_salary} | Net: Rs. ${current.net_salary}`;
                document.getElementById('incNewBasic').value = current.basic;
                document.getElementById('incNewHra').value = current.hra;
                document.getElementById('incNewAllowances').value = current.special;
            }
        }
    } catch (e) {
        console.error(e);
    }
}

function closeApproveIncrementModal() {
    const modal = document.getElementById('approveIncrementModal');
    if (modal) modal.style.display = 'none';
}

// Register form submit event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Salary structure form submit
    const salaryForm = document.getElementById('salaryStructureForm');
    if (salaryForm) {
        salaryForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = {
                employee: document.getElementById('structEmployeeSelect').value,
                effective_from: document.getElementById('structEffectiveFrom').value,
                basic: document.getElementById('structBasic').value,
                hra: document.getElementById('structHra').value,
                conveyance: document.getElementById('structConveyance').value,
                medical: document.getElementById('structMedical').value,
                special: document.getElementById('structSpecial').value,
                monthly_bonus: document.getElementById('structBonus').value,
                pf: document.getElementById('structPf').value,
                tds: document.getElementById('structTds').value,
            };

            try {
                const res = await apiFetch('/salaries/', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                if (res.ok) {
                    showToast('Salary structure saved successfully.');
                    closeSalaryStructureModal();
                    loadSalaryData();
                } else {
                    const err = await res.json();
                    showToast(JSON.stringify(err), 'error');
                }
            } catch (ex) {
                console.error(ex);
            }
        });
    }

    // Bulk payslip form submit
    const bulkForm = document.getElementById('bulkSlipForm');
    if (bulkForm) {
        bulkForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = {
                month: document.getElementById('bulkSlipMonth').value,
                year: document.getElementById('bulkSlipYear').value,
                working_days: document.getElementById('bulkSlipWorkingDays').value,
                payment_date: document.getElementById('bulkSlipPaymentDate').value,
                payment_mode: document.getElementById('bulkSlipPaymentMode').value,
            };

            try {
                showToast('Running bulk payslips creation...');
                const res = await apiFetch('/salary/slips/bulk-generate/', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                if (res.ok) {
                    const summary = await res.json();
                    showToast(`Bulk payroll run completed. Slips Generated: ${summary.generated}, Skipped: ${summary.skipped}`);
                    closeBulkSlipModal();
                } else {
                    showToast('Failed to run bulk payroll.', 'error');
                }
            } catch (ex) {
                console.error(ex);
            }
        });
    }

    // Raise approval form submit
    const incForm = document.getElementById('approveIncrementForm');
    if (incForm) {
        incForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const reminderId = document.getElementById('incReminderId').value;
            const data = {
                employee: document.getElementById('incEmployeeId').value,
                new_basic: document.getElementById('incNewBasic').value,
                new_hra: document.getElementById('incNewHra').value,
                new_allowances: document.getElementById('incNewAllowances').value,
                effective_date: document.getElementById('incEffectiveDate').value,
                reason: document.getElementById('incReasonText').value
            };

            try {
                showToast('Approving raises and compiling letter...');
                const res = await apiFetch(`/salary/increments/${reminderId}/approve/`, {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                
                if (res.ok) {
                    showToast('Salary revision approved and letters sent!');
                    closeApproveIncrementModal();
                    loadSalaryData();
                } else {
                    const err = await res.json();
                    showToast(JSON.stringify(err), 'error');
                }
            } catch (ex) {
                console.error(ex);
            }
        });
    }
});
