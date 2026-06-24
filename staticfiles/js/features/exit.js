// static/js/features/exit.js
// Complete Exit Clearance & Workflow processing handlers

let currentExits = [];
let activeExitRequest = null;
let exitCurrentPage = 1;
let exitTotalCount = 0;
let exitFilteredList = [];

// Helper to check if current user is admin
function isAdminUser() {
    return typeof currentUser !== 'undefined' && 
           currentUser && 
           (currentUser.role === 'ADMIN' || currentUser.role_code === 'ADMIN');
}

// ---------- EXIT MANAGEMENT VIEW ----------
async function loadExitData() {
    document.getElementById('pageTitle').textContent = 'Employee exit manager';
    try {
        const res = await apiFetch('/api/exit/requests/?no_pagination=true');
        if (res.ok) {
            const exits = await res.json();
            currentExits = exits.results || exits;
            exitCurrentPage = 1;
            filterExitTable();
        } else {
            showToast('Failed to fetch exit records.', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Server error loading exit data.', 'error');
    }
}

function renderExitTable(exits) {
    const tbody = document.getElementById('exitTableBody');
    if (!tbody) return;

    if (exits.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:#64748b;">No exit records found.</td></tr>';
        return;
    }

    tbody.innerHTML = exits.map(x => {
        const empName = x.employee_details ? `${x.employee_details.first_name} ${x.employee_details.last_name}` : 'Unknown';
        const empId = x.employee_details ? x.employee_details.emp_id : x.employee;
        let statusColor = '#eab308'; // yellow default
        if (x.status === 'FULLY_EXITED') statusColor = '#16a34a'; // green
        else if (x.status === 'COMPLETED' || x.status === 'CLEARANCES_DONE' || x.status === 'FF_PROCESSED') statusColor = '#2563eb'; // blue
        else if (x.status === 'CANCELLED') statusColor = '#dc2626'; // red

        return `
            <tr style="cursor:pointer;" onclick="openExitDetailModal(${x.id})">
                <td><strong>${empId}</strong></td>
                <td>${empName}</td>
                <td>${x.exit_type}</td>
                <td>${x.resignation_date}</td>
                <td>${x.last_working_day}</td>
                <td><span style="font-weight:bold; color:${statusColor}">${x.status}</span></td>
                <td>
                    <button class="btn btn-secondary" style="font-size:8pt; padding:4px 8px;" onclick="event.stopPropagation(); openExitDetailModal(${x.id})">Manage Flow</button>
                </td>
            </tr>
        `;
    }).join('');
}

// Client side search and filters
function filterExitTable() {
    const searchVal = document.getElementById('exitSearchInput').value.toLowerCase();
    const statusVal = document.getElementById('exitStatusFilter').value;

    exitFilteredList = currentExits.filter(x => {
        const empName = x.employee_details ? `${x.employee_details.first_name} ${x.employee_details.last_name}`.toLowerCase() : '';
        const empId = x.employee_details ? x.employee_details.emp_id.toLowerCase() : '';
        const matchesSearch = empName.includes(searchVal) || empId.includes(searchVal);
        const matchesStatus = !statusVal || x.status === statusVal;
        return matchesSearch && matchesStatus;
    });

    exitTotalCount = exitFilteredList.length;
    
    // Reset page if it exceeds maximum pages
    const maxPage = Math.ceil(exitTotalCount / 10) || 1;
    if (exitCurrentPage > maxPage) {
        exitCurrentPage = maxPage;
    }

    const paginationFooter = document.getElementById('exitPaginationFooter');
    if (paginationFooter) {
        paginationFooter.style.display = 'flex';
        updateExitPaginationControls(exitCurrentPage, exitTotalCount);
    }

    const startIdx = (exitCurrentPage - 1) * 10;
    const paginatedList = exitFilteredList.slice(startIdx, startIdx + 10);
    renderExitTable(paginatedList);
}

function changeExitPage(direction) {
    const maxPage = Math.ceil(exitTotalCount / 10) || 1;
    exitCurrentPage = Math.max(1, Math.min(maxPage, exitCurrentPage + direction));
    
    const startIdx = (exitCurrentPage - 1) * 10;
    const paginatedList = exitFilteredList.slice(startIdx, startIdx + 10);
    renderExitTable(paginatedList);
    
    updateExitPaginationControls(exitCurrentPage, exitTotalCount);
}

function updateExitPaginationControls(currentPage, totalCount) {
    const pageStart = totalCount === 0 ? 0 : (currentPage - 1) * 10 + 1;
    const pageEnd = Math.min(currentPage * 10, totalCount);
    
    const startEl = document.getElementById('exitPageStart');
    const endEl = document.getElementById('exitPageEnd');
    const totalEl = document.getElementById('exitTotalCount');
    const prevBtn = document.getElementById('exitPrevBtn');
    const nextBtn = document.getElementById('exitNextBtn');
    
    if (startEl) startEl.textContent = pageStart;
    if (endEl) endEl.textContent = pageEnd;
    if (totalEl) totalEl.textContent = totalCount;
    
    if (prevBtn) prevBtn.disabled = currentPage <= 1;
    if (nextBtn) nextBtn.disabled = pageEnd >= totalCount;
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

async function loadActiveEmployeesSelect(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;
    try {
        const res = await apiFetch('/employees/?type=all&no_pagination=true');
        if (res.ok) {
            const employees = await res.json();
            const list = employees.results || employees;
            const activeList = list.filter(e => e.status === 'Active');
            select.innerHTML = '<option value="">Select Employee</option>' + activeList.map(e => `
                <option value="${e.id}">${e.first_name} ${e.last_name} (${e.emp_id})</option>
            `).join('');
        }
    } catch (e) {
        console.error(e);
    }
}

// ---------- DETAILS VIEW WORKFLOW ----------
async function openExitDetailModal(id) {
    try {
        const res = await apiFetch(`/api/exit/requests/${id}/`);
        if (res.ok) {
            activeExitRequest = await res.json();
            switchView('exitDetailView');
            populateExitDetails(activeExitRequest);
        } else {
            showToast('Failed to fetch details.', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Error loading details view.', 'error');
    }
}

function closeExitDetailModal() {
    switchView('exitView');
}

function populateExitDetails(x) {
    // Basic info
    const name = x.employee_details ? `${x.employee_details.first_name} ${x.employee_details.last_name}` : 'Unknown';
    document.getElementById('detEmpName').textContent = name;
    document.getElementById('detEmpId').textContent = x.employee_details ? x.employee_details.emp_id : x.employee;
    document.getElementById('detLwd').textContent = x.last_working_day;
    document.getElementById('detResignDate').textContent = x.resignation_date;

    // Absconding flow check
    const isAbsconding = x.exit_type === 'ABSCONDING';
    document.getElementById('abscondingBanner').style.display = isAbsconding ? 'block' : 'none';

    // RBAC protections check
    const isAdmin = isAdminUser();
    
    // Admin only actions
    document.getElementById('btnCancelExit').style.display = isAdmin ? 'inline-block' : 'none';
    document.getElementById('btnOverrideExit').style.display = isAdmin ? 'inline-block' : 'none';
    document.getElementById('btnReopenExit').style.display = isAdmin ? 'inline-block' : 'none';
    document.getElementById('btnExtendLwd').style.display = isAdmin ? 'inline-block' : 'none';
    document.getElementById('btnApproveFf').style.display = isAdmin ? 'inline-block' : 'none';
    document.getElementById('btnGenNoc').style.display = isAdmin ? 'inline-block' : 'none';

    // Resend link hide for absconding or final exit
    document.getElementById('btnResendToken').style.display = (!isAbsconding && x.status !== 'FULLY_EXITED') ? 'inline-block' : 'none';

    // Mark Fully Exited condition
    const ff = x.ff_settlement;
    document.getElementById('btnMarkExited').disabled = (!ff || !ff.approved_by || x.status === 'FULLY_EXITED');

    const chkEmail = document.getElementById('chkSendEmailOnExit');
    if (chkEmail) {
        chkEmail.disabled = (x.status === 'FULLY_EXITED');
        chkEmail.checked = (x.status === 'FULLY_EXITED') ? x.send_email_on_exit : true;
    }

    // Update Timeline status
    const steps = ['PENDING', 'IN_PROGRESS', 'COMPLETED', 'CLEARANCES_DONE', 'FF_PROCESSED', 'FULLY_EXITED'];
    
    // Map status to active step index (0 to 5, or 6 for fully completed)
    const statusToActiveIndex = {
        'PENDING': 0,
        'IN_PROGRESS': 1,
        'COMPLETED': 3,        // Questionnaire done, Clearances in progress (Step 4 is active)
        'CLEARANCES_DONE': 4,  // Clearances done, F&F in progress (Step 5 is active)
        'FF_PROCESSED': 5,     // F&F done, final exit mark in progress (Step 6 is active)
        'FULLY_EXITED': 6      // All steps completed
    };

    let activeIndex = statusToActiveIndex[x.status];
    if (x.status === 'REOPENED') {
        activeIndex = x.form_response ? 3 : 1;
    }

    // Handle CANCELLED / OVERRIDDEN timeline override
    if (x.status === 'CANCELLED' || x.status === 'OVERRIDDEN') {
        activeIndex = -1;
    }
    
    // Calculate progress line width
    let progressWidth = 0;
    if (activeIndex >= 0) {
        // Line should extend to the active step. If fully completed, extend to the end (index 5)
        const lineTargetIndex = Math.min(activeIndex, steps.length - 1);
        progressWidth = (lineTargetIndex / (steps.length - 1)) * 90; // max width 90%
    }
    document.getElementById('timelineProgress').style.width = `${progressWidth}%`;

    steps.forEach((step, idx) => {
        const stepDiv = document.getElementById(`step_${step}`);
        if (!stepDiv) return;
        const dot = stepDiv.querySelector('.step-dot');
        
        // Reset styles
        dot.style.backgroundColor = '#cbd5e1';
        dot.style.color = 'white';

        if (x.status === 'CANCELLED') {
            dot.style.backgroundColor = '#f87171'; // red
        } else if (x.status === 'OVERRIDDEN') {
            dot.style.backgroundColor = '#f59e0b'; // orange
        } else {
            if (idx < activeIndex) {
                dot.style.backgroundColor = '#22c55e'; // green (completed)
            } else if (idx === activeIndex) {
                dot.style.backgroundColor = '#3b82f6'; // active blue
            }
        }
    });

    // Populate Checklists
    document.getElementById('chkItEmail').checked = x.it_email_deactivated;
    document.getElementById('chkItAccess').checked = x.it_system_access_revoked;
    document.getElementById('chkItVpn').checked = x.it_vpn_removed;
    document.getElementById('chkItBio').checked = x.it_biometric_deactivated;
    document.getElementById('chkItBackup').checked = x.it_data_backup_completed;

    document.getElementById('selClrIt').value = x.clearance_it;
    document.getElementById('selClrFinance').value = x.clearance_finance;
    document.getElementById('selClrAdmin').value = x.clearance_admin;
    document.getElementById('selClrManager').value = x.clearance_manager;
    document.getElementById('selClrLibrary').value = x.clearance_library;

    // Populate F&F Calculator
    const salaryStructures = (x.employee_details && x.employee_details.salary_structures) || [];
    salaryStructures.sort((a, b) => new Date(b.effective_from) - new Date(a.effective_from));
    const latestSalary = salaryStructures[0];
    const basicSalary = latestSalary ? parseFloat(latestSalary.basic) : 0;

    // Setup working days default
    const lwd = new Date(x.last_working_day);
    const dayOfMonth = lwd.getDate();

    if (ff) {
        document.getElementById('ffMonthDays').value = ff.salary_month_days;
        document.getElementById('ffWorkedDays').value = ff.salary_worked_days;
        document.getElementById('ffLeaveEncashDays').value = ff.leave_encash_days;
        document.getElementById('ffBonusArrears').value = ff.bonus_arrears;
        document.getElementById('ffGratuityAmount').value = ff.gratuity_amount;
        document.getElementById('ffNoticeShortDays').value = ff.notice_shortfall_days;
        document.getElementById('ffAdvanceOutstanding').value = ff.salary_advance_outstanding;
        document.getElementById('ffBondPenalty').value = ff.bond_penalty;
        document.getElementById('ffTdsDeduction').value = ff.tds_deduction;
        
        // Load custom rows
        renderCustomRows('reimbursementsContainer', ff.reimbursements_json || [], 'reimb');
        renderCustomRows('deductionsContainer', ff.other_deductions_json || [], 'ded');
    } else {
        // defaults
        document.getElementById('ffMonthDays').value = 30;
        document.getElementById('ffWorkedDays').value = dayOfMonth;
        document.getElementById('ffLeaveEncashDays').value = x.leave_balance_days || 0;
        document.getElementById('ffBonusArrears').value = 0;
        document.getElementById('ffGratuityAmount').value = 0;
        document.getElementById('ffNoticeShortDays').value = 0;
        document.getElementById('ffAdvanceOutstanding').value = 0;
        document.getElementById('ffBondPenalty').value = 0;
        document.getElementById('ffTdsDeduction').value = 0;
        
        document.getElementById('reimbursementsContainer').innerHTML = '';
        document.getElementById('deductionsContainer').innerHTML = '';
    }

    // Save basic salary as attributes for calculations
    document.getElementById('ffPerDaySalary').dataset.basic = basicSalary;
    
    // Run initial calculations
    calculateFfTotals();

    // Populate Exit Questionnaire Data
    const fr = x.form_response;
    const noRespEl = document.getElementById('exitFormNoResponse');
    const respDetailsEl = document.getElementById('exitFormResponseDetails');
    if (fr) {
        if (noRespEl) noRespEl.style.display = 'none';
        if (respDetailsEl) {
            respDetailsEl.style.display = 'block';
            document.getElementById('qDetSubmittedAt').textContent = fr.submitted_at ? new Date(fr.submitted_at).toLocaleString() : '-';
            document.getElementById('qDetPersonalEmail').textContent = fr.personal_email || '-';
            document.getElementById('qDetPersonalPhone').textContent = fr.personal_phone || '-';
            document.getElementById('qDetPersonalAddress').textContent = fr.personal_address || '-';
            
            document.getElementById('qDetReasonDropdown').textContent = fr.reason_dropdown || '-';
            document.getElementById('qDetKtStatus').textContent = fr.kt_status || '-';
            document.getElementById('qDetKtHandover').textContent = fr.kt_handover_to || '-';
            document.getElementById('qDetKtCompletionDate').textContent = fr.kt_completion_date || '-';
            
            const getYesNoSpan = (val) => {
                if (val === true || val === 'true') {
                    return '<span style="color: #16a34a; font-weight: bold;">YES</span>';
                }
                return '<span style="color: #dc2626; font-weight: bold;">NO</span>';
            };
            
            document.getElementById('qDetKtManagerConfirmed').innerHTML = getYesNoSpan(fr.kt_manager_confirmed);
            document.getElementById('qDetKtNotes').textContent = fr.kt_remarks || '-';
            
            // Assets return clearance details
            document.getElementById('qDetAssetLaptopStatus').innerHTML = getYesNoSpan(fr.asset_laptop_returned);
            document.getElementById('qDetAssetLaptopSerial').textContent = fr.asset_laptop_serial || '-';
            document.getElementById('qDetAssetLaptopRemarks').textContent = fr.asset_laptop_remarks || '-';
            
            document.getElementById('qDetAssetIdStatus').innerHTML = getYesNoSpan(fr.asset_id_returned);
            document.getElementById('qDetAssetIdRemarks').textContent = fr.asset_id_remarks || '-';
            
            document.getElementById('qDetAssetAccessCardStatus').innerHTML = getYesNoSpan(fr.asset_access_card_returned);
            document.getElementById('qDetAssetAccessCardRemarks').textContent = fr.asset_access_card_remarks || '-';
            
            document.getElementById('qDetAssetMobileStatus').innerHTML = getYesNoSpan(fr.asset_mobile_returned);
            document.getElementById('qDetAssetMobileNumber').textContent = fr.asset_mobile_number || '-';
            document.getElementById('qDetAssetMobileRemarks').textContent = fr.asset_mobile_remarks || '-';
            
            document.getElementById('qDetAssetLockerStatus').innerHTML = getYesNoSpan(fr.asset_locker_returned);
            document.getElementById('qDetAssetLockerRemarks').textContent = fr.asset_locker_remarks || '-';
            
            document.getElementById('qDetAssetOthers').textContent = fr.asset_others_details || '-';
            document.getElementById('qDetAssetsConfirmation').innerHTML = getYesNoSpan(fr.assets_confirmation);
            
            // Feedback details
            document.getElementById('qDetRecommend').textContent = fr.recommend || '-';
            document.getElementById('qDetRatingEnv').textContent = fr.rating_env || '-';
            document.getElementById('qDetRatingMgmt').textContent = fr.rating_mgmt || '-';
            document.getElementById('qDetRatingBalance').textContent = fr.rating_balance || '-';
            document.getElementById('qDetReasonDetails').textContent = fr.reason_details || '-';
            document.getElementById('qDetLikedMost').textContent = fr.liked_most || '-';
            document.getElementById('qDetImprovedMost').textContent = fr.improved_most || '-';
            document.getElementById('qDetFeedback').textContent = fr.other_feedback || '-';
            document.getElementById('qDetDeclarationConfirmed').innerHTML = getYesNoSpan(fr.declaration_confirmed);
        }
    } else {
        if (noRespEl) noRespEl.style.display = 'block';
        if (respDetailsEl) respDetailsEl.style.display = 'none';
    }

    // Reset view to first tab
    switchExitTab('clearances');
}

// Switch Profile Detail Tab Views in Exit Panel
function switchExitTab(tabId) {
    const tabs = ['clearances', 'ff', 'docs', 'form'];
    tabs.forEach(t => {
        const btn = document.getElementById(`exitTab${t.charAt(0).toUpperCase() + t.slice(1)}Btn`);
        const content = document.getElementById(`exitTab${t.charAt(0).toUpperCase() + t.slice(1)}`);
        
        if (btn && content) {
            if (t === tabId) {
                btn.classList.add('active');
                btn.style.color = 'var(--primary-color)';
                btn.style.borderBottom = '3px solid var(--primary-color)';
                content.style.display = 'block';
            } else {
                btn.classList.remove('active');
                btn.style.color = '#64748b';
                btn.style.borderBottom = '3px solid transparent';
                content.style.display = 'none';
            }
        }
    });
}



function renderCustomRows(containerId, items, prefix) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = items.map((item, idx) => `
        <div class="${prefix}-row" style="display: flex; gap: 10px; align-items: center;">
            <input type="text" class="${prefix}-title" value="${item.title}" placeholder="Item label" style="padding: 4px; font-size: 8.5pt; flex: 2;">
            <input type="number" class="${prefix}-amount" value="${item.amount}" oninput="calculateFfTotals()" placeholder="Amount" style="padding: 4px; font-size: 8.5pt; flex: 1;">
            <button onclick="this.parentElement.remove(); calculateFfTotals();" style="border:none; background:none; color:#ef4444; font-size:12pt; cursor:pointer;">&times;</button>
        </div>
    `).join('');
}

function addReimbursementRow() {
    const container = document.getElementById('reimbursementsContainer');
    const div = document.createElement('div');
    div.className = 'reimb-row';
    div.style = 'display: flex; gap: 10px; align-items: center;';
    div.innerHTML = `
        <input type="text" class="reimb-title" placeholder="Item label" style="padding: 4px; font-size: 8.5pt; flex: 2;">
        <input type="number" class="reimb-amount" value="0" oninput="calculateFfTotals()" placeholder="Amount" style="padding: 4px; font-size: 8.5pt; flex: 1;">
        <button onclick="this.parentElement.remove(); calculateFfTotals();" style="border:none; background:none; color:#ef4444; font-size:12pt; cursor:pointer;">&times;</button>
    `;
    container.appendChild(div);
}

function addDeductionRow() {
    const container = document.getElementById('deductionsContainer');
    const div = document.createElement('div');
    div.className = 'ded-row';
    div.style = 'display: flex; gap: 10px; align-items: center;';
    div.innerHTML = `
        <input type="text" class="ded-title" placeholder="Item label" style="padding: 4px; font-size: 8.5pt; flex: 2;">
        <input type="number" class="ded-amount" value="0" oninput="calculateFfTotals()" placeholder="Amount" style="padding: 4px; font-size: 8.5pt; flex: 1;">
        <button onclick="this.parentElement.remove(); calculateFfTotals();" style="border:none; background:none; color:#ef4444; font-size:12pt; cursor:pointer;">&times;</button>
    `;
    container.appendChild(div);
}

function calculateFfTotals() {
    const basicMonthly = parseFloat(document.getElementById('ffPerDaySalary').dataset.basic) || 0;
    const monthDays = parseFloat(document.getElementById('ffMonthDays').value) || 30;
    const workedDays = parseFloat(document.getElementById('ffWorkedDays').value) || 0;
    const leaveDays = parseFloat(document.getElementById('ffLeaveEncashDays').value) || 0;
    const noticeDays = parseFloat(document.getElementById('ffNoticeShortDays').value) || 0;

    const perDay = monthDays > 0 ? basicMonthly / monthDays : 0;
    const proratedBasic = perDay * workedDays;
    const leaveEncash = perDay * leaveDays;
    const noticeShort = perDay * noticeDays;

    document.getElementById('ffPerDaySalary').value = perDay.toFixed(2);
    document.getElementById('ffProportionalSalary').value = proratedBasic.toFixed(2);
    document.getElementById('ffLeaveEncashAmount').value = leaveEncash.toFixed(2);
    document.getElementById('ffNoticeShortAmount').value = noticeShort.toFixed(2);

    // Sum earnings
    const bonus = parseFloat(document.getElementById('ffBonusArrears').value) || 0;
    const gratuity = parseFloat(document.getElementById('ffGratuityAmount').value) || 0;
    let customReimb = 0;
    document.querySelectorAll('.reimb-row').forEach(row => {
        customReimb += parseFloat(row.querySelector('.reimb-amount').value) || 0;
    });

    const totalEarnings = proratedBasic + leaveEncash + bonus + gratuity + customReimb;

    // Sum deductions
    const advance = parseFloat(document.getElementById('ffAdvanceOutstanding').value) || 0;
    const bond = parseFloat(document.getElementById('ffBondPenalty').value) || 0;
    const tds = parseFloat(document.getElementById('ffTdsDeduction').value) || 0;
    let customDeds = 0;
    document.querySelectorAll('.ded-row').forEach(row => {
        customDeds += parseFloat(row.querySelector('.ded-amount').value) || 0;
    });

    const totalDeductions = noticeShort + advance + bond + tds + customDeds;
    const netPayable = totalEarnings - totalDeductions;

    document.getElementById('lblTotalEarnings').textContent = `INR ${totalEarnings.toFixed(2)}`;
    document.getElementById('lblTotalDeductions').textContent = `INR ${totalDeductions.toFixed(2)}`;
    document.getElementById('lblNetPayable').textContent = `INR ${netPayable.toFixed(2)}`;
}

// ---------- API MUTATIONS ----------
async function saveItChecklist() {
    if (!activeExitRequest) return;
    try {
        const body = {
            it_email_deactivated: document.getElementById('chkItEmail').checked,
            it_system_access_revoked: document.getElementById('chkItAccess').checked,
            it_vpn_removed: document.getElementById('chkItVpn').checked,
            it_biometric_deactivated: document.getElementById('chkItBio').checked,
            it_data_backup_completed: document.getElementById('chkItBackup').checked
        };
        const res = await apiFetch(`/api/exit/requests/${activeExitRequest.id}/update-it-checklist/`, {
            method: 'PUT',
            body: JSON.stringify(body)
        });
        if (res.ok) {
            showToast('IT Revocation checklist saved successfully.');
            openExitDetailModal(activeExitRequest.id);
        } else {
            showToast('Failed to save IT checklist.', 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

async function saveClearances() {
    if (!activeExitRequest) return;
    try {
        const body = {
            clearance_it: document.getElementById('selClrIt').value,
            clearance_finance: document.getElementById('selClrFinance').value,
            clearance_admin: document.getElementById('selClrAdmin').value,
            clearance_manager: document.getElementById('selClrManager').value,
            clearance_library: document.getElementById('selClrLibrary').value
        };
        const res = await apiFetch(`/api/exit/requests/${activeExitRequest.id}/update-clearances/`, {
            method: 'PUT',
            body: JSON.stringify(body)
        });
        if (res.ok) {
            showToast('Department clearances checklist updated.');
            openExitDetailModal(activeExitRequest.id);
            loadExitData();
        } else {
            showToast('Failed to save clearances.', 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

async function saveFfCalculations() {
    if (!activeExitRequest) return;
    
    const reimbursements = [];
    document.querySelectorAll('.reimb-row').forEach(row => {
        const title = row.querySelector('.reimb-title').value;
        const amount = parseFloat(row.querySelector('.reimb-amount').value) || 0;
        if (title.trim()) reimbursements.push({ title, amount });
    });

    const other_deductions = [];
    document.querySelectorAll('.ded-row').forEach(row => {
        const title = row.querySelector('.ded-title').value;
        const amount = parseFloat(row.querySelector('.ded-amount').value) || 0;
        if (title.trim()) other_deductions.push({ title, amount });
    });

    const body = {
        salary_month_days: parseInt(document.getElementById('ffMonthDays').value) || 30,
        salary_worked_days: parseFloat(document.getElementById('ffWorkedDays').value) || 0,
        salary_proportional: parseFloat(document.getElementById('ffProportionalSalary').value) || 0,
        leave_encash_days: parseFloat(document.getElementById('ffLeaveEncashDays').value) || 0,
        leave_encashment_amount: parseFloat(document.getElementById('ffLeaveEncashAmount').value) || 0,
        bonus_arrears: parseFloat(document.getElementById('ffBonusArrears').value) || 0,
        gratuity_amount: parseFloat(document.getElementById('ffGratuityAmount').value) || 0,
        notice_shortfall_days: parseFloat(document.getElementById('ffNoticeShortDays').value) || 0,
        notice_shortfall_amount: parseFloat(document.getElementById('ffNoticeShortAmount').value) || 0,
        salary_advance_outstanding: parseFloat(document.getElementById('ffAdvanceOutstanding').value) || 0,
        bond_penalty: parseFloat(document.getElementById('ffBondPenalty').value) || 0,
        tds_deduction: parseFloat(document.getElementById('ffTdsDeduction').value) || 0,
        reimbursements_json: reimbursements,
        other_deductions_json: other_deductions
    };

    try {
        const res = await apiFetch(`/api/exit/requests/${activeExitRequest.id}/process-ff/`, {
            method: 'POST',
            body: JSON.stringify(body)
        });
        if (res.ok) {
            showToast('F&F draft calculations saved.');
            openExitDetailModal(activeExitRequest.id);
            loadExitData();
        } else {
            const err = await res.json();
            showToast(JSON.stringify(err), 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

async function approveFfCalculations() {
    if (!activeExitRequest) return;
    if (!confirm('Are you sure you want to approve this Full & Final Settlement? This will freeze the computations.')) return;

    try {
        const res = await apiFetch(`/api/exit/requests/${activeExitRequest.id}/approve-ff/`, {
            method: 'POST'
        });
        if (res.ok) {
            showToast('F&F Settlement calculations approved.');
            openExitDetailModal(activeExitRequest.id);
            loadExitData();
        } else {
            const err = await res.json();
            showToast(err.error || 'Failed to approve F&F.', 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

async function actionResendLink() {
    if (!activeExitRequest) return;
    try {
        const res = await apiFetch(`/api/exit/requests/${activeExitRequest.id}/resend-link/`, {
            method: 'POST'
        });
        if (res.ok) {
            showToast('New questionnaire link emailed to employee.');
        } else {
            showToast('Failed to resend link.', 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

async function actionExtendLwd() {
    if (!activeExitRequest) return;
    const newDate = prompt('Enter new Last Working Day (YYYY-MM-DD):', activeExitRequest.last_working_day);
    if (!newDate) return;

    try {
        const res = await apiFetch(`/api/exit/requests/${activeExitRequest.id}/extend-lwd/`, {
            method: 'PUT',
            body: JSON.stringify({ last_working_day: newDate })
        });
        if (res.ok) {
            showToast('Last Working Day updated successfully.');
            openExitDetailModal(activeExitRequest.id);
            loadExitData();
        } else {
            const err = await res.json();
            showToast(JSON.stringify(err), 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

async function actionReopenExit() {
    if (!activeExitRequest) return;
    if (!confirm('Are you sure you want to reopen this exit request?')) return;

    try {
        const res = await apiFetch(`/api/exit/requests/${activeExitRequest.id}/reopen/`, {
            method: 'PUT'
        });
        if (res.ok) {
            showToast('Exit request reopened successfully.');
            openExitDetailModal(activeExitRequest.id);
            loadExitData();
        } else {
            showToast('Failed to reopen exit.', 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

async function actionCancelExit() {
    if (!activeExitRequest) return;
    const reason = prompt('Please enter cancellation reason:');
    if (!reason) return;

    try {
        const res = await apiFetch(`/api/exit/requests/${activeExitRequest.id}/cancel/`, {
            method: 'PUT',
            body: JSON.stringify({ cancelled_reason: reason })
        });
        if (res.ok) {
            showToast('Exit process cancelled successfully. Employee status restored to Active.');
            closeExitDetailModal();
            loadExitData();
        } else {
            const err = await res.json();
            showToast(JSON.stringify(err), 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

async function actionOverrideExit() {
    if (!activeExitRequest) return;
    const reason = prompt('Please enter Override reason (e.g. Absconding Override):');
    if (!reason) return;

    try {
        const res = await apiFetch(`/api/exit/requests/${activeExitRequest.id}/override/`, {
            method: 'PUT',
            body: JSON.stringify({ override_reason: reason })
        });
        if (res.ok) {
            showToast('Exit status overridden successfully.');
            openExitDetailModal(activeExitRequest.id);
            loadExitData();
        } else {
            const err = await res.json();
            showToast(JSON.stringify(err), 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

let currentPreviewPdfUrl = null;
let currentPreviewPdfName = '';

async function actionSendEmailDocs() {
    if (!activeExitRequest) return;
    if (!confirm('Are you sure you want to email the selected documents to the employee now?')) return;

    const email_documents = [];
    if (document.getElementById('chkEmailRelieving') && document.getElementById('chkEmailRelieving').checked) email_documents.push('RELIEVING_LETTER');
    if (document.getElementById('chkEmailExperience') && document.getElementById('chkEmailExperience').checked) email_documents.push('EXPERIENCE_LETTER');
    if (document.getElementById('chkEmailNotice') && document.getElementById('chkEmailNotice').checked) email_documents.push('NOTICE_LETTER');
    if (document.getElementById('chkEmailNoc') && document.getElementById('chkEmailNoc').checked) email_documents.push('NOC_LETTER');
    if (document.getElementById('chkEmailFfLetter') && document.getElementById('chkEmailFfLetter').checked) email_documents.push('FF_SETTLEMENT_LETTER');
    if (document.getElementById('chkEmailFfSlip') && document.getElementById('chkEmailFfSlip').checked) email_documents.push('FF_SALARY_SLIP');

    try {
        const res = await apiFetch(`/api/exit/requests/${activeExitRequest.id}/send-documents-email/`, {
            method: 'POST',
            body: JSON.stringify({ 
                email_documents: email_documents
            })
        });
        if (res.ok) {
            showToast('Documents are being dispatched via email.');
        } else {
            const err = await res.json();
            showToast(JSON.stringify(err), 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Error dispatching emails.', 'error');
    }
}

async function actionMarkExited() {
    if (!activeExitRequest) return;
    if (!confirm('Marking this employee as fully exited will transition their profile to Exited status. Proceed?')) return;

    const chkEmail = document.getElementById('chkSendEmailOnExit');
    const sendEmail = chkEmail ? chkEmail.checked : true;

    const email_documents = [];
    if (document.getElementById('chkEmailRelieving') && document.getElementById('chkEmailRelieving').checked) email_documents.push('RELIEVING_LETTER');
    if (document.getElementById('chkEmailExperience') && document.getElementById('chkEmailExperience').checked) email_documents.push('EXPERIENCE_LETTER');
    if (document.getElementById('chkEmailNotice') && document.getElementById('chkEmailNotice').checked) email_documents.push('NOTICE_LETTER');
    if (document.getElementById('chkEmailNoc') && document.getElementById('chkEmailNoc').checked) email_documents.push('NOC_LETTER');
    if (document.getElementById('chkEmailFfLetter') && document.getElementById('chkEmailFfLetter').checked) email_documents.push('FF_SETTLEMENT_LETTER');
    if (document.getElementById('chkEmailFfSlip') && document.getElementById('chkEmailFfSlip').checked) email_documents.push('FF_SALARY_SLIP');

    try {
        const res = await apiFetch(`/api/exit/requests/${activeExitRequest.id}/mark-fully-exited/`, {
            method: 'POST',
            body: JSON.stringify({ 
                send_email: sendEmail,
                email_documents: email_documents
            })
        });
        if (res.ok) {
            showToast('Employee offboarding process completed. Status: Fully Exited.');
            openExitDetailModal(activeExitRequest.id);
            loadExitData();
        } else {
            const err = await res.json();
            showToast(err.error || 'Failed to complete exit.', 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

async function generateDocument(type) {
    if (!activeExitRequest) return;
    showToast(`Generating ${type.toUpperCase()} PDF...`);
    try {
        const res = await apiFetch(`/api/exit/requests/${activeExitRequest.id}/generate-${type}/`, {
            method: 'POST'
        });
        if (res.ok) {
            const data = await res.json();
            showToast('PDF compilation complete.');
            if (data.document && data.document.file) {
                openPdfPreview(data.document.file, `${type.toUpperCase()} Document`);
            }
        } else {
            const err = await res.json();
            showToast(err.error || 'PDF compilation failed.', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Server error generating document.', 'error');
    }
}

function openPdfPreview(url, title) {
    const accessToken = localStorage.getItem('accessToken');
    const urlWithToken = accessToken ? `${url}?token=${encodeURIComponent(accessToken)}` : url;
    
    currentPreviewPdfUrl = urlWithToken;
    currentPreviewPdfName = title.replace(/\s+/g, '_').toLowerCase() + '.pdf';
    
    const titleEl = document.getElementById('pdfPreviewTitle');
    if (titleEl) titleEl.innerText = title;
    
    const iframe = document.getElementById('pdfPreviewIframe');
    if (iframe) iframe.src = urlWithToken;
    
    const modal = document.getElementById('pdfPreviewModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}


function closePdfPreview() {
    const modal = document.getElementById('pdfPreviewModal');
    if (modal) {
        modal.style.display = 'none';
    }
    const iframe = document.getElementById('pdfPreviewIframe');
    if (iframe) iframe.src = '';
    currentPreviewPdfUrl = null;
    currentPreviewPdfName = '';
}

function downloadPdfFromPreview() {
    if (!currentPreviewPdfUrl) return;
    const link = document.createElement('a');
    link.href = currentPreviewPdfUrl;
    link.download = currentPreviewPdfName || 'document.pdf';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Bind Waiver Checkbox
document.addEventListener('DOMContentLoaded', () => {
    const waiverCb = document.getElementById('exitWaiverCheckbox');
    if (waiverCb) {
        waiverCb.addEventListener('change', (e) => {
            const container = document.getElementById('exitLwdContainer');
            if (container) container.style.display = e.target.checked ? 'block' : 'none';
        });
    }

    // Bind form submit
    const exitForm = document.getElementById('exitForm');
    if (exitForm) {
        exitForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = {
                bitrix_user_id: document.getElementById('exitEmployeeSelect').value,
                resignation_date: document.getElementById('exitResignationDate').value,
                exit_type: document.getElementById('exitTypeSelect').value,
                mode_of_resignation: document.getElementById('exitModeSelect').value,
                notice_period_waiver: document.getElementById('exitWaiverCheckbox').checked,
                notice_letter_required: document.getElementById('exitNoticeLetterCheckbox').checked,
                exit_reason: document.getElementById('exitReasonText').value
            };

            if (data.notice_period_waiver) {
                data.last_working_day = document.getElementById('exitLwdDate').value;
            }

            try {
                showToast('Initiating offboarding process...');
                const res = await apiFetch('/api/exit/requests/', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                
                if (res.ok) {
                    showToast('Exit initiated. Questionnaire link sent.');
                    closeExitModal();
                    loadExitData();
                } else {
                    const err = await res.json();
                    showToast(JSON.stringify(err), 'error');
                }
            } catch (ex) {
                console.error(ex);
                showToast('Failed to initiate exit.', 'error');
            }
        });
    }
});

// ========================================================================
// EXIT LETTER WORKSPACE - Side-by-Side Customization & Preview
// ========================================================================

let activeWorkspaceDocType = null;
let wsPreviewDebounceTimer = null;

const DOC_TYPE_LABELS = {
    'relieving': 'Relieving Letter',
    'experience': 'Experience Letter',
    'notice': 'Notice Period Letter',
    'noc': 'NOC Letter',
    'ff-letter': 'F&F Settlement Letter',
    'ff-slip': 'Final Month Payslip'
};

function openExitLetterWorkspace(docType) {
    if (!activeExitRequest) {
        showToast('No exit request selected.', 'error');
        return;
    }
    
    activeWorkspaceDocType = docType;
    
    // Set title and doc type label
    const label = DOC_TYPE_LABELS[docType] || docType;
    document.getElementById('workspaceTitle').textContent = `📄 ${label} — Customization Workspace`;
    document.getElementById('wsDocTypeLabel').textContent = label;
    
    // Populate form fields from the active exit request
    const x = activeExitRequest;
    const emp = x.employee_details || {};
    
    // Date
    document.getElementById('wsDate').value = new Date().toISOString().split('T')[0];
    
    // Employee fields
    document.getElementById('wsFirstName').value = emp.first_name || '';
    document.getElementById('wsLastName').value = emp.last_name || '';
    document.getElementById('wsEmpId').value = emp.emp_id || '';
    document.getElementById('wsDesignation').value = emp.designation || '';
    document.getElementById('wsJoiningDate').value = emp.joining_date || '';
    document.getElementById('wsLwd').value = x.last_working_day || '';
    document.getElementById('wsResignationDate').value = x.resignation_date || '';
    
    // Company / signatory defaults (will be overridden by backend defaults if left empty)
    document.getElementById('wsCompanyName').value = '';
    document.getElementById('wsCompanyAddress').value = '';
    document.getElementById('wsSignatoryName').value = '';
    document.getElementById('wsSignatoryDesignation').value = '';
    
    // Show/hide F&F fields
    const showFfFields = (docType === 'ff-letter' || docType === 'ff-slip');
    document.getElementById('wsFfFieldsSection').style.display = showFfFields ? 'block' : 'none';
    
    if (showFfFields) {
        const ff = x.ff_settlement || {};
        document.getElementById('wsSalaryMonthDays').value = ff.salary_month_days || 30;
        document.getElementById('wsSalaryWorkedDays').value = ff.salary_worked_days || 0;
        document.getElementById('wsLeaveEncashDays').value = ff.leave_encash_days || 0;
        document.getElementById('wsBonusArrears').value = ff.bonus_arrears || 0;
        document.getElementById('wsGratuity').value = ff.gratuity_amount || 0;
        document.getElementById('wsNoticeShortDays').value = ff.notice_shortfall_days || 0;
        document.getElementById('wsAdvanceRecovery').value = ff.salary_advance_outstanding || 0;
        document.getElementById('wsTdsDeduction').value = ff.tds_deduction || 0;
    }
    
    // Switch to workspace view
    switchView('exitLetterWorkspace');
    
    // Load initial preview
    updateExitLetterPreview();
}

function closeExitLetterWorkspace() {
    activeWorkspaceDocType = null;
    document.getElementById('wsPreviewIframe').srcdoc = '';
    switchView('exitDetailView');
    // Refresh detail view data
    if (activeExitRequest) {
        populateExitDetails(activeExitRequest);
    }
}

function getWorkspaceCustomContext() {
    const ctx = {};
    
    // Only include non-empty values (empty = use backend default)
    const firstName = document.getElementById('wsFirstName').value.trim();
    if (firstName) ctx.first_name = firstName;
    
    const lastName = document.getElementById('wsLastName').value.trim();
    if (lastName) ctx.last_name = lastName;

    const empId = document.getElementById('wsEmpId').value.trim();
    if (empId) ctx.emp_id = empId;
    
    const designation = document.getElementById('wsDesignation').value.trim();
    if (designation) ctx.designation = designation;
    
    const joiningDate = document.getElementById('wsJoiningDate').value;
    if (joiningDate) ctx.joining_date = joiningDate;
    
    const lwd = document.getElementById('wsLwd').value;
    if (lwd) ctx.last_working_day = lwd;
    
    const resignDate = document.getElementById('wsResignationDate').value;
    if (resignDate) ctx.resignation_date = resignDate;
    
    const wsDate = document.getElementById('wsDate').value;
    if (wsDate) {
        const d = new Date(wsDate + 'T00:00:00');
        ctx.date = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'long', year: 'numeric' });
    }
    
    const companyName = document.getElementById('wsCompanyName').value.trim();
    if (companyName) ctx.company_name = companyName;
    
    const companyAddress = document.getElementById('wsCompanyAddress').value.trim();
    if (companyAddress) ctx.company_address = companyAddress;
    
    const sigName = document.getElementById('wsSignatoryName').value.trim();
    if (sigName) ctx.signatory_name = sigName;
    
    const sigDesignation = document.getElementById('wsSignatoryDesignation').value.trim();
    if (sigDesignation) ctx.signatory_designation = sigDesignation;
    
    // F&F fields
    const ffSection = document.getElementById('wsFfFieldsSection');
    if (ffSection && ffSection.style.display !== 'none') {
        ctx.salary_month_days = parseFloat(document.getElementById('wsSalaryMonthDays').value) || 30;
        ctx.salary_worked_days = parseFloat(document.getElementById('wsSalaryWorkedDays').value) || 0;
        ctx.leave_encash_days = parseFloat(document.getElementById('wsLeaveEncashDays').value) || 0;
        ctx.bonus_arrears = parseFloat(document.getElementById('wsBonusArrears').value) || 0;
        ctx.gratuity_amount = parseFloat(document.getElementById('wsGratuity').value) || 0;
        ctx.notice_shortfall_days = parseFloat(document.getElementById('wsNoticeShortDays').value) || 0;
        ctx.salary_advance_outstanding = parseFloat(document.getElementById('wsAdvanceRecovery').value) || 0;
        ctx.tds_deduction = parseFloat(document.getElementById('wsTdsDeduction').value) || 0;
    }
    
    return ctx;
}

async function updateExitLetterPreview() {
    if (!activeExitRequest || !activeWorkspaceDocType) return;
    
    // Debounce rapid changes
    if (wsPreviewDebounceTimer) clearTimeout(wsPreviewDebounceTimer);
    
    const statusEl = document.getElementById('wsPreviewStatus');
    if (statusEl) statusEl.textContent = '⏳ Loading preview...';
    
    wsPreviewDebounceTimer = setTimeout(async () => {
        try {
            const customContext = getWorkspaceCustomContext();
            const res = await apiFetch(`/api/exit/requests/${activeExitRequest.id}/preview-letter/`, {
                method: 'POST',
                body: JSON.stringify({
                    doc_type: activeWorkspaceDocType,
                    custom_context: customContext
                })
            });
            
            if (res.ok) {
                const data = await res.json();
                const iframe = document.getElementById('wsPreviewIframe');
                if (iframe) {
                    iframe.srcdoc = data.html;
                }
                if (statusEl) statusEl.textContent = '✅ Preview updated';
            } else {
                const err = await res.json();
                if (statusEl) statusEl.textContent = '❌ Preview error';
                console.error('Preview error:', err);
            }
        } catch (e) {
            console.error('Preview fetch error:', e);
            if (statusEl) statusEl.textContent = '❌ Network error';
        }
    }, 400);
}

async function downloadCustomizedExitLetter() {
    if (!activeExitRequest || !activeWorkspaceDocType) return;
    
    const label = DOC_TYPE_LABELS[activeWorkspaceDocType] || activeWorkspaceDocType;
    showToast(`Generating customized ${label} PDF...`);
    
    try {
        const customContext = getWorkspaceCustomContext();
        const res = await apiFetch(`/api/exit/requests/${activeExitRequest.id}/generate-${activeWorkspaceDocType}/`, {
            method: 'POST',
            body: JSON.stringify({ custom_context: customContext })
        });
        
        if (res.ok) {
            const data = await res.json();
            showToast('Customized PDF generated successfully.');
            if (data.document && data.document.file) {
                openPdfPreview(data.document.file, `${label} (Customized)`);
            }
        } else {
            const err = await res.json();
            showToast(err.error || 'PDF generation failed.', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Server error generating customized document.', 'error');
    }
}

// ========================================================================
// EXIT TEMPLATE EDITOR - HTML Template Management
// ========================================================================

let exitTemplatesCache = [];
let activeEditorTemplateId = null;

const EXIT_TEMPLATE_NAMES = [
    'RELIEVING_LETTER', 'EXPERIENCE_LETTER', 'NOTICE_LETTER',
    'NOC_LETTER', 'FF_SETTLEMENT_LETTER', 'FF_SALARY_SLIP'
];

async function openExitTemplateEditor() {
    showToast('Loading template editor...');
    
    try {
        const res = await apiFetch('/api/onboarding/templates/');
        if (res.ok) {
            const data = await res.json();
            const templates = data.results || data;
            
            // Filter to exit templates only
            exitTemplatesCache = templates.filter(t => EXIT_TEMPLATE_NAMES.includes(t.name));
            
            // Populate selector
            const selector = document.getElementById('templateEditorSelector');
            selector.innerHTML = '<option value="">— Choose a template —</option>' +
                exitTemplatesCache.map(t => `<option value="${t.id}">${t.title} (${t.name})</option>`).join('');
            
            // Clear visual editor
            const visualEditor = document.getElementById('exitVisualTemplateEditor');
            if (visualEditor) visualEditor.innerHTML = '';
            document.getElementById('templateEditorStatus').textContent = `${exitTemplatesCache.length} exit templates loaded`;
            activeEditorTemplateId = null;
            
            switchView('exitTemplateEditor');
        } else {
            showToast('Failed to load templates.', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Error loading templates.', 'error');
    }
}

function closeExitTemplateEditor() {
    activeEditorTemplateId = null;
    switchView('exitView');
}

function loadExitTemplateToEditor() {
    const selector = document.getElementById('templateEditorSelector');
    const selectedId = selector.value;
    
    if (!selectedId) {
        const visualEditor = document.getElementById('exitVisualTemplateEditor');
        if (visualEditor) visualEditor.innerHTML = '';
        document.getElementById('templateEditorStatus').textContent = 'No template selected';
        activeEditorTemplateId = null;
        return;
    }
    
    const template = exitTemplatesCache.find(t => t.id == selectedId);
    if (!template) return;
    
    activeEditorTemplateId = template.id;
    
    // Populate the visual contenteditable editor (like onboarding)
    const visualEditor = document.getElementById('exitVisualTemplateEditor');
    if (visualEditor) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(template.html_content || '', 'text/html');
        
        let styles = '';
        doc.querySelectorAll('style').forEach(s => {
            styles += s.outerHTML;
        });
        
        const bodyContent = doc.body ? doc.body.innerHTML : (template.html_content || '');
        visualEditor.innerHTML = styles + bodyContent;
    }
    
    document.getElementById('templateEditorStatus').textContent = `Editing: ${template.title}`;
    document.getElementById('templateEditorLastSaved').textContent = template.updated_at
        ? `Last saved: ${new Date(template.updated_at).toLocaleString()}`
        : '-';
}

async function saveExitTemplateChanges() {
    if (!activeEditorTemplateId) {
        showToast('Please select a template first.', 'error');
        return;
    }
    
    const template = exitTemplatesCache.find(t => t.id == activeEditorTemplateId);
    if (!template) return;
    
    const visualEditor = document.getElementById('exitVisualTemplateEditor');
    if (!visualEditor) return;
    
    // Parse current content to separate styles and body content (like onboarding)
    const parser = new DOMParser();
    const doc = parser.parseFromString(visualEditor.innerHTML, 'text/html');
    
    let styles = '';
    doc.querySelectorAll('style').forEach(s => {
        styles += s.outerHTML;
        s.remove();
    });
    
    const bodyContent = doc.body ? doc.body.innerHTML : visualEditor.innerHTML;
    
    // Reconstruct valid full-page HTML for WeasyPrint
    const newContent = `<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>${template.title || 'Exit Document'}</title>
    ${styles}
</head>
<body>
    ${bodyContent}
</body>
</html>`;
    
    if (!confirm(`Save changes to "${template.title}"? This will affect all future documents generated using this template.`)) {
        return;
    }
    
    try {
        const res = await apiFetch(`/api/onboarding/templates/${activeEditorTemplateId}/`, {
            method: 'PUT',
            body: JSON.stringify({
                name: template.name,
                title: template.title,
                html_content: fullHtml,
                allow_hr_edit: template.allow_hr_edit
            })
        });
        
        if (res.ok) {
            const updatedTemplate = await res.json();
            // Update cache
            const idx = exitTemplatesCache.findIndex(t => t.id == activeEditorTemplateId);
            if (idx >= 0) exitTemplatesCache[idx] = updatedTemplate;
            
            document.getElementById('templateEditorLastSaved').textContent = `Last saved: ${new Date().toLocaleString()}`;
            document.getElementById('templateEditorStatus').textContent = `✅ "${template.title}" saved successfully`;
            showToast('Template saved successfully.');
        } else {
            const err = await res.json();
            const errMsg = err.detail || err.error || JSON.stringify(err);
            showToast(`Failed to save: ${errMsg}`, 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Server error saving template.', 'error');
    }
}

// ---- Exit visual editor toolbar helpers ----
function execExitEditorCommand(command) {
    document.execCommand(command, false, null);
    const visualEditor = document.getElementById('exitVisualTemplateEditor');
    if (visualEditor) visualEditor.focus();
}

function insertExitPlaceholderAtCursor(placeholder) {
    if (!placeholder) return;
    const visualEditor = document.getElementById('exitVisualTemplateEditor');
    if (!visualEditor) return;
    
    visualEditor.focus();
    
    const sel = window.getSelection();
    if (sel.getRangeAt && sel.rangeCount) {
        let range = sel.getRangeAt(0);
        
        if (visualEditor.contains(range.commonAncestorContainer)) {
            range.deleteContents();
            const textNode = document.createTextNode(placeholder);
            range.insertNode(textNode);
            range = range.cloneRange();
            range.setStartAfter(textNode);
            range.collapse(true);
            sel.removeAllRanges();
            sel.addRange(range);
        } else {
            visualEditor.appendChild(document.createTextNode(placeholder));
        }
    } else {
        visualEditor.appendChild(document.createTextNode(placeholder));
    }
}

async function previewExitTemplateInEditor() {
    if (!activeEditorTemplateId) {
        showToast('Please select a template first.', 'error');
        return;
    }
    
    if (!activeExitRequest) {
        showToast('Please select an exit request first to preview a template against real data.', 'error');
        return;
    }
    
    const template = exitTemplatesCache.find(t => t.id == activeEditorTemplateId);
    if (!template) return;
    
    const visualEditor = document.getElementById('visualExitTemplateEditor');
    if (!visualEditor) return;
    
    // Parse current content to separate styles and body content
    const parser = new DOMParser();
    const doc = parser.parseFromString(visualEditor.innerHTML, 'text/html');
    
    let styles = '';
    doc.querySelectorAll('style').forEach(s => {
        styles += s.outerHTML;
        s.remove();
    });
    
    const bodyContent = doc.body ? doc.body.innerHTML : visualEditor.innerHTML;
    
    const fullHtml = `<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>${template.title || 'Exit Template'}</title>
    ${styles}
</head>
<body>
    ${bodyContent}
</body>
</html>`;
    
    // Map template name to doc type slug
    const nameToSlug = {
        'RELIEVING_LETTER': 'relieving',
        'EXPERIENCE_LETTER': 'experience',
        'NOTICE_LETTER': 'notice',
        'NOC_LETTER': 'noc',
        'FF_SETTLEMENT_LETTER': 'ff-letter',
        'FF_SALARY_SLIP': 'ff-slip'
    };
    const docType = nameToSlug[template.name];
    if (!docType) {
        showToast('Cannot preview this template type.', 'error');
        return;
    }
    
    showToast('Generating preview...');
    try {
        const res = await apiFetch(`/api/exit/requests/${activeExitRequest.id}/preview-letter/`, {
            method: 'POST',
            body: JSON.stringify({ 
                doc_type: docType,
                template_html: fullHtml
            })
        });
        
        if (res.ok) {
            const data = await res.json();
            // Open preview in a new window
            const win = window.open('', '_blank', 'width=800,height=600');
            if (win) {
                win.document.write(data.html);
                win.document.close();
            }
        } else {
            const err = await res.json();
            showToast(err.error || 'Preview failed.', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Error generating preview.', 'error');
    }
}

function execExitEditorCommand(command) {
    document.execCommand(command, false, null);
    const visualEditor = document.getElementById('visualExitTemplateEditor');
    if (visualEditor) {
        visualEditor.focus();
    }
}

function insertExitPlaceholderAtCursor(placeholder) {
    if (!placeholder) return;
    const visualEditor = document.getElementById('visualExitTemplateEditor');
    if (!visualEditor) return;
    
    visualEditor.focus();
    
    const sel = window.getSelection();
    if (sel.getRangeAt && sel.rangeCount) {
        let range = sel.getRangeAt(0);
        
        if (visualEditor.contains(range.commonAncestorContainer)) {
            range.deleteContents();
            
            const textNode = document.createTextNode(placeholder);
            range.insertNode(textNode);
            
            range = range.cloneRange();
            range.setStartAfter(textNode);
            range.collapse(true);
            sel.removeAllRanges();
            sel.addRange(range);
        } else {
            visualEditor.appendChild(document.createTextNode(placeholder));
        }
    } else {
        visualEditor.appendChild(document.createTextNode(placeholder));
    }
}

