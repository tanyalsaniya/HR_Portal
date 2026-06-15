// static/js/features/student.js
// Students and Interns registry, installments, certificate generation handlers

let studentInstallmentRows = [];

// ---------- STUDENTS & INTERNS VIEW ----------
async function loadStudentData() {
    document.getElementById('pageTitle').textContent = 'Student / Intern Module';
    try {
        const res = await apiFetch('/students/');
        if (res.ok) {
            const studs = await res.json();
            const studList = studs.results || studs;
            const tbody = document.getElementById('studentTableBody');
            
            if (tbody) {
                tbody.innerHTML = studList.map(s => `
                    <tr>
                        <td>${s.cert_no}</td>
                        <td>${s.name}</td>
                        <td>${s.email}</td>
                        <td>${s.student_type}</td>
                        <td>${s.joining_date}</td>
                        <td>${s.completion_date}</td>
                        <td>Rs. ${s.total_fees}</td>
                        <td><span style="font-weight:bold; color:${s.status === 'ACTIVE' ? '#eab308' : '#22c55e'}">${s.status}</span></td>
                        <td>
                            <button class="btn" style="font-size:8pt; padding:4px 8px;" onclick="generateStudentCertificate(${s.id})">Generate Cert</button>
                            ${s.cert_pdf ? `<button class="btn" style="font-size:8pt; padding:4px 8px;" onclick="window.open('${s.cert_pdf}', '_blank')">View Cert</button>` : ''}
                            <button class="btn" style="font-size:8pt; padding:4px 8px;" onclick="viewInstallmentsModal(${s.id}, '${s.name}')">Fee Schedule</button>
                        </td>
                    </tr>
                `).join('');
            }
        }
    } catch (e) {
        console.error(e);
    }
}

function openStudentModal() {
    const modal = document.getElementById('studentModal');
    if (modal) {
        modal.style.display = 'flex';
        loadDepartmentsSelect('studDept');
        // reset installments rows
        studentInstallmentRows = [];
        const container = document.getElementById('installmentsWrapper');
        if (container) container.innerHTML = '';
    }
}
function closeStudentModal() {
    const modal = document.getElementById('studentModal');
    if (modal) modal.style.display = 'none';
}

function addInstallmentRow() {
    const index = studentInstallmentRows.length + 1;
    const div = document.createElement('div');
    div.className = 'form-grid';
    div.style.marginBottom = '5px';
    div.innerHTML = `
        <div>
            <label>Installment ${index} Amount (Rs.)</label>
            <input type="number" class="inst-amount" required>
        </div>
        <div>
            <label>Due Date</label>
            <input type="date" class="inst-due" required>
        </div>
    `;
    const container = document.getElementById('installmentsWrapper');
    if (container) {
        container.appendChild(div);
        studentInstallmentRows.push(div);
    }
}

async function generateStudentCertificate(studentId, override = false) {
    showToast('Generating training certificate...');
    try {
        const res = await apiFetch(`/students/${studentId}/generate-certificate/`, {
            method: 'POST',
            body: JSON.stringify({ confirm_override: override })
        });
        
        if (res.ok) {
            const result = await res.json();
            if (result.requires_override) {
                if (confirm(result.warning)) {
                    generateStudentCertificate(studentId, true); // re-call with override
                }
            } else {
                showToast('Certificate generated successfully!');
                if (result.cert_pdf) {
                    window.open(result.cert_pdf, '_blank');
                }
                loadStudentData();
            }
        } else {
            showToast('Certificate generation failed.', 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

// Installments viewer overlay/list
async function viewInstallmentsModal(studentId, name) {
    try {
        const res = await apiFetch(`/student/installments/?student_id=${studentId}`);
        if (res.ok) {
            const installments = await res.json();
            const list = installments.results || installments;
            
            // Open warning toast/alert showing details or build inline popup
            let htmlList = list.map(inst => `
                <div style="border-bottom:1px solid var(--border-color); padding:10px 0; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong>Installment ${inst.installment_number}</strong><br>
                        Amount: Rs. ${inst.amount} | Due: ${inst.due_date}<br>
                        Paid: Rs. ${inst.paid_amount} | Date: ${inst.paid_date || 'N/A'}<br>
                        Status: <span style="font-weight:bold; color:${inst.status === 'PAID' ? '#22c55e' : '#ef4444'}">${inst.status}</span>
                    </div>
                    <div>
                        ${inst.status !== 'PAID' ? `
                            <button class="btn btn-primary" style="font-size:7.5pt; padding:3px 6px;" onclick="openRecordPaymentModal(${inst.id})">Pay</button>
                            <button class="btn" style="font-size:7.5pt; padding:3px 6px; background-color:#eab308; color:white;" onclick="triggerWarningEmail(${inst.id})">Email Warn</button>
                        ` : ''}
                    </div>
                </div>
            `).join('');

            if (list.length === 0) {
                htmlList = '<div>No fee installments defined for this student.</div>';
            }

            // Build standard inline alert dialog or dynamic popup
            alertModalHTML(`Fee installments for ${name}`, htmlList);
        }
    } catch (e) {
        console.error(e);
    }
}

function alertModalHTML(title, content) {
    // Remove previous if exists
    const old = document.getElementById('alertDynamicModal');
    if (old) old.remove();

    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'alertDynamicModal';
    modal.style.display = 'flex';
    modal.innerHTML = `
        <div class="modal-content" style="max-height:80%; overflow-y:auto;">
            <div class="flex-row-header">
                <h3 style="margin:0;">${title}</h3>
                <button onclick="document.getElementById('alertDynamicModal').remove()" style="background:none; border:none; font-size:16pt; cursor:pointer;">&times;</button>
            </div>
            <div>${content}</div>
        </div>
    `;
    document.body.appendChild(modal);
}

// Record installment payment
function openRecordPaymentModal(instId) {
    // Close dynamic installment viewer
    const dynamic = document.getElementById('alertDynamicModal');
    if (dynamic) dynamic.style.display = 'none';

    const modal = document.getElementById('recordPaymentModal');
    if (modal) {
        modal.style.display = 'flex';
        document.getElementById('paymentInstallmentId').value = instId;
    }
}
function closeRecordPaymentModal() {
    const modal = document.getElementById('recordPaymentModal');
    if (modal) modal.style.display = 'none';
}

async function triggerWarningEmail(instId) {
    try {
        showToast('Sending overdue alert email...');
        const res = await apiFetch(`/student/installments/${instId}/send-warning/`, { method: 'POST' });
        if (res.ok) {
            showToast('Warning email sent successfully to student.');
        } else {
            showToast('Failed to send warning email.', 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Register student submit
    const studentForm = document.getElementById('studentForm');
    if (studentForm) {
        studentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Build installments schedule
            const schedule = [];
            const amounts = document.querySelectorAll('.inst-amount');
            const dues = document.querySelectorAll('.inst-due');
            for (let i = 0; i < amounts.length; i++) {
                schedule.push({
                    amount: amounts[i].value,
                    due_date: dues[i].value
                });
            }

            const data = {
                name: document.getElementById('studName').value,
                email: document.getElementById('studEmail').value,
                phone: document.getElementById('studPhone').value,
                institute: document.getElementById('studInstitute').value,
                course_at_institute: document.getElementById('studCourse').value,
                student_type: document.getElementById('studType').value,
                program_name: document.getElementById('studProgram').value,
                department: document.getElementById('studDept').value,
                mentor: document.getElementById('studMentor').value,
                joining_date: document.getElementById('studJoining').value,
                completion_date: document.getElementById('studCompletion').value,
                cert_type: document.getElementById('studCertType').value,
                total_fees: document.getElementById('studFees').value,
                installments_schedule: schedule
            };

            try {
                const res = await apiFetch('/students/', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                if (res.ok) {
                    showToast('Student registered and installment plans generated!');
                    closeStudentModal();
                    loadStudentData();
                } else {
                    const err = await res.json();
                    showToast(JSON.stringify(err), 'error');
                }
            } catch (ex) {
                console.error(ex);
            }
        });
    }

    // Submit payment recording
    const paymentForm = document.getElementById('recordPaymentForm');
    if (paymentForm) {
        paymentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const instId = document.getElementById('paymentInstallmentId').value;
            const data = {
                amount_paid: document.getElementById('paymentAmountPaid').value,
                remarks: document.getElementById('paymentRemarks').value
            };

            try {
                const res = await apiFetch(`/student/installments/${instId}/record-payment/`, {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                if (res.ok) {
                    showToast('Payment recorded successfully.');
                    closeRecordPaymentModal();
                    loadStudentData();
                } else {
                    showToast('Failed to record payment.', 'error');
                }
            } catch (ex) {
                console.error(ex);
            }
        });
    }
});
