// static/js/features/exit.js
// Exit Clearance data loading and processing handlers

// ---------- EXIT MANAGEMENT VIEW ----------
async function loadExitData() {
    document.getElementById('pageTitle').textContent = 'Employee exit manager';
    try {
        const res = await apiFetch('/exits/');
        if (res.ok) {
            const exits = await res.json();
            const exitList = exits.results || exits;
            const tbody = document.getElementById('exitTableBody');
            
            if (tbody) {
                tbody.innerHTML = exitList.map(x => `
                    <tr>
                        <td>${x.employee_details ? x.employee_details.emp_id : x.employee}</td>
                        <td>${x.employee_details ? x.employee_details.first_name + ' ' + x.employee_details.last_name : ''}</td>
                        <td>${x.resignation_date}</td>
                        <td>${x.last_working_day}</td>
                        <td><span style="font-weight:bold; color:${x.status === 'COMPLETED' ? '#22c55e' : '#eab308'}">${x.status}</span></td>
                        <td>
                            ${x.status === 'COMPLETED' ? `
                                <button class="btn" style="font-size:8pt; padding:4px 8px;" onclick="triggerGenerateExitLetter(${x.id}, 'relieving')">Relieving Letter</button>
                                <button class="btn" style="font-size:8pt; padding:4px 8px;" onclick="triggerGenerateExitLetter(${x.id}, 'experience')">Experience Letter</button>
                            ` : `
                                <button class="btn" style="font-size:8pt; padding:4px 8px;" onclick="triggerResendExitLink(${x.id})">Resend Form Link</button>
                            `}
                            ${x.notice_letter_required ? `<button class="btn" style="font-size:8pt; padding:4px 8px;" onclick="triggerGenerateExitLetter(${x.id}, 'notice')">Notice Letter</button>` : ''}
                        </td>
                    </tr>
                `).join('');
            }
        }
    } catch (e) {
        console.error(e);
    }
}

// Initiate Exit modal
function openInitiateExitModal() {
    const modal = document.getElementById('initiateExitModal');
    if (modal) {
        modal.style.display = 'flex';
        loadActiveEmployeesSelect('exitEmployeeSelect');
    }
}
function closeExitModal() {
    const modal = document.getElementById('initiateExitModal');
    if (modal) modal.style.display = 'none';
}

document.addEventListener('DOMContentLoaded', () => {
    // Waiver LWD toggle
    const waiverCb = document.getElementById('exitWaiverCheckbox');
    if (waiverCb) {
        waiverCb.addEventListener('change', (e) => {
            const container = document.getElementById('exitLwdContainer');
            if (container) container.style.display = e.target.checked ? 'block' : 'none';
        });
    }

    // Submit exit form
    const exitForm = document.getElementById('exitForm');
    if (exitForm) {
        exitForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = {
                employee: document.getElementById('exitEmployeeSelect').value,
                resignation_date: document.getElementById('exitResignationDate').value,
                exit_type: document.getElementById('exitTypeSelect').value,
                notice_waiver: document.getElementById('exitWaiverCheckbox').checked,
                notice_letter_required: document.getElementById('exitNoticeLetterCheckbox').checked,
                exit_reason: document.getElementById('exitReasonText').value
            };

            if (data.notice_waiver) {
                data.last_working_day = document.getElementById('exitLwdDate').value;
            }

            try {
                showToast('Initiating exit process and email tokens...');
                const res = await apiFetch('/exits/', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                
                if (res.ok) {
                    showToast('Exit clearance initiated. Email token sent to employee.');
                    closeExitModal();
                    loadExitData();
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

async function triggerResendExitLink(id) {
    try {
        const res = await apiFetch(`/exits/${id}/send-link/`, { method: 'POST' });
        if (res.ok) showToast('Exit link emailed successfully.');
        else showToast('Failed to send link.', 'error');
    } catch (e) { console.error(e); }
}

async function triggerGenerateExitLetter(exitId, type) {
    showToast(`Generating ${type} PDF...`);
    try {
        const res = await apiFetch(`/exits/${exitId}/generate-${type}/`, { method: 'POST' });
        if (res.ok) {
            const data = await res.json();
            showToast(`${type.toUpperCase()} PDF created.`);
            if (data.document && data.document.file) {
                window.open(data.document.file, '_blank');
            }
            loadExitData();
        } else {
            const err = await res.json();
            showToast(err.error || 'Generation failed.', 'error');
        }
    } catch (e) { console.error(e); }
}
