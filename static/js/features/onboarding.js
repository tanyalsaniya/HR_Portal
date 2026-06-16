// static/js/features/onboarding.js
// Onboarding tracker page data loading, forms, letters, tabs, Excel import/export and secure downloads

let activeOnboardingSubTab = 'onboarding'; // 'onboarding', 'all', 'offboarding', 'dismissed'
let activeProfileTab = 'personal'; // 'personal', 'docs', 'salary', 'letters', 'audit'
let currentDetailEmployeeId = null;
let currentOnboardingData = []; // Cache list to enable client-side search/sort/filter

// Populate State dropdown lists (utility)
function populateStatesDropdown(selectId = 'empState') {
    const states = [
        ["AP", "Andhra Pradesh"], ["AR", "Arunachal Pradesh"], ["AS", "Assam"],
        ["BR", "Bihar"], ["CG", "Chhattisgarh"], ["GA", "Goa"], ["GJ", "Gujarat"],
        ["HR", "Haryana"], ["HP", "Himachal Pradesh"], ["JH", "Jharkhand"],
        ["KA", "Karnataka"], ["KL", "Kerala"], ["MP", "Madhya Pradesh"],
        ["MH", "Maharashtra"], ["MN", "Manipur"], ["ML", "Meghalaya"],
        ["MZ", "Mizoram"], ["NL", "Nagaland"], ["OD", "Odisha"], ["PB", "Punjab"],
        ["RJ", "Rajasthan"], ["SK", "Sikkim"], ["TN", "Tamil Nadu"],
        ["TG", "Telangana"], ["TR", "Tripura"], ["UP", "Uttar Pradesh"],
        ["UK", "Uttarakhand"], ["WB", "West Bengal"], ["DL", "Delhi"],
        ["JK", "Jammu & Kashmir"], ["PY", "Puducherry"]
    ];
    
    const drop = document.getElementById(selectId);
    if (drop) {
        drop.innerHTML = states.map(s => `<option value="${s[0]}">${s[1]}</option>`).join('');
    }
}

// Switch between Active, Onboarding, Offboarding, Dismissed sub-tabs
function switchOnboardingSubTab(tabId) {
    activeOnboardingSubTab = tabId;
    
    // Toggle active header tab classes
    const tabs = ['all', 'onboarding', 'offboarding', 'dismissed'];
    tabs.forEach(t => {
        const btnId = t === 'all' ? 'tabActiveBtn' : `tab${t.charAt(0).toUpperCase() + t.slice(1)}Btn`;
        const btn = document.getElementById(btnId);
        if (btn) {
            if (t === tabId) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        }
    });

    // Toggle main tables display
    document.getElementById('subTabOnboarding').style.display = tabId === 'onboarding' ? 'block' : 'none';
    document.getElementById('subTabAllEmployees').style.display = tabId !== 'onboarding' ? 'block' : 'none';
    
    // Toggle policy banner visibility (only show guidelines on onboarding tracker view)
    document.getElementById('onboardingPolicyBanner').style.display = tabId === 'onboarding' ? 'block' : 'none';

    // Fetch and load respective data
    loadFilteredEmployeeData();
}

// Global click listener to close dropdowns when clicking outside
document.addEventListener('click', (event) => {
    if (!event.target.classList.contains('btn-dot-menu')) {
        const dropdowns = document.querySelectorAll('.premium-actions-dropdown');
        dropdowns.forEach(d => d.classList.remove('show'));
    }
});

// Toggle 3-dots actions menu
function toggleRowActionMenu(event, empId) {
    event.stopPropagation();
    
    // Close other dropdowns first
    const dropdowns = document.querySelectorAll('.premium-actions-dropdown');
    dropdowns.forEach(d => {
        if (d.id !== `actionDropdown-${empId}`) {
            d.classList.remove('show');
        }
    });

    const target = document.getElementById(`actionDropdown-${empId}`);
    if (target) {
        target.classList.toggle('show');
    }
}

// Expand/Collapse filter panel drawer
function toggleFilterDrawer() {
    const drawer = document.getElementById('filterDrawerCard');
    if (drawer) {
        drawer.style.display = drawer.style.display === 'none' ? 'block' : 'none';
    }
}

// Load Onboarding directory view
async function loadOnboardingData() {
    document.getElementById('pageTitle').textContent = 'Employee Onboarding';
    
    // Load departments master lists for filters
    await loadDepartmentsSelect('empDept');
    await loadDepartmentsSelect('editEmpDept');
    await loadDepartmentsSelect('onboardingDeptFilter');
    
    // Default sub tab
    switchOnboardingSubTab(activeOnboardingSubTab);
}

// Load filtered employee datasets based on selected active tab
async function loadFilteredEmployeeData() {
    let endpoint = '/employees/';
    
    if (activeOnboardingSubTab === 'onboarding') {
        endpoint = '/employees/?type=onboarding';
    } else if (activeOnboardingSubTab === 'all') {
        endpoint = '/employees/?type=all';
    }
    
    try {
        const res = await apiFetch(endpoint);
        if (res.ok) {
            const data = await res.json();
            let rawList = data.results || data;
            
            // Local filters for other mock states (offboarding, dismissed)
            if (activeOnboardingSubTab === 'offboarding') {
                rawList = rawList.filter(e => e.status === 'Exited' || e.exit_request_id !== undefined);
            } else if (activeOnboardingSubTab === 'dismissed') {
                rawList = rawList.filter(e => e.is_deleted === true || e.status === 'Exited');
            } else if (activeOnboardingSubTab === 'all') {
                // Active directory filters out exited employees by default
                rawList = rawList.filter(e => e.status !== 'Exited');
            }
            
            currentOnboardingData = rawList;
            applySearchSortAndFilter();
        }
    } catch (e) {
        console.error(e);
        showToast('Failed to load employee list.', 'error');
    }
}

// Apply client-side search query, dropdown filters and sort orders
function filterOnboardingTables() {
    applySearchSortAndFilter();
}

function sortOnboardingTables() {
    applySearchSortAndFilter();
}

function applySearchSortAndFilter() {
    let list = [...currentOnboardingData];
    
    // 1. Search filter
    const query = document.getElementById('onboardingSearchInput').value.toLowerCase();
    if (query) {
        list = list.filter(e => 
            e.first_name.toLowerCase().includes(query) ||
            e.last_name.toLowerCase().includes(query) ||
            e.email.toLowerCase().includes(query) ||
            e.emp_id.toLowerCase().includes(query)
        );
    }
    
    // 2. Dropdown filters
    const dept = document.getElementById('onboardingDeptFilter').value;
    const type = document.getElementById('onboardingTypeFilter').value;
    const fromDate = document.getElementById('onboardingFromDateFilter').value;
    const toDate = document.getElementById('onboardingToDateFilter').value;
    
    if (dept) {
        list = list.filter(e => String(e.department) === String(dept));
    }
    if (type) {
        list = list.filter(e => e.employment_type === type);
    }
    if (fromDate) {
        list = list.filter(e => e.joining_date >= fromDate);
    }
    if (toDate) {
        list = list.filter(e => e.joining_date <= toDate);
    }
    
    // 3. Sort ordering
    const sortBy = document.getElementById('onboardingSortSelect').value;
    if (sortBy === 'name') {
        list.sort((a, b) => `${a.first_name} ${a.last_name}`.localeCompare(`${b.first_name} ${b.last_name}`));
    } else if (sortBy === 'date') {
        list.sort((a, b) => new Date(a.joining_date) - new Date(b.joining_date));
    } else if (sortBy === 'id') {
        list.sort((a, b) => a.emp_id.localeCompare(b.emp_id));
    }
    
    // Render to correct tab tbody
    if (activeOnboardingSubTab === 'onboarding') {
        renderOnboardingTrackerTable(list);
    } else {
        renderActiveDirectoryTable(list);
    }
}

// Render sub-tab 1: Onboarding Tracker
function renderOnboardingTrackerTable(list) {
    const tbody = document.getElementById('onboardingTrackerTableBody');
    if (!tbody) return;
    
    if (list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 25px; color: var(--text-light);">No employees currently under onboarding progress.</td></tr>`;
        return;
    }
    
    tbody.innerHTML = list.map(e => {
        // Initials Avatar creation
        const initials = `${e.first_name.charAt(0)}${e.last_name.charAt(0)}`.toUpperCase();
        
        // Premium initials avatar color palette picker
        const colors = [
            { bg: '#e0e7ff', text: '#4f46e5' }, // Indigo tint
            { bg: '#ffe4e6', text: '#e11d48' }, // Rose tint
            { bg: '#d1fae5', text: '#059669' }, // Emerald tint
            { bg: '#fef3c7', text: '#d97706' }, // Amber tint
            { bg: '#f3e8ff', text: '#9333ea' }, // Purple tint
            { bg: '#ecfeff', text: '#0891b2' }  // Cyan tint
        ];
        const colorIdx = e.id % colors.length;
        const pair = colors[colorIdx];
        
        const avatarCell = e.profile_photo 
            ? `<img src="${e.profile_photo}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; margin-right: 12px; display:inline-block; vertical-align: middle;">`
            : `<div style="width: 40px; height: 40px; border-radius: 50%; background-color: ${pair.bg}; color: ${pair.text}; display: inline-flex; align-items: center; justify-content: center; font-weight: 700; font-size: 10pt; margin-right: 12px; vertical-align: middle; letter-spacing: -0.02em;">${initials}</div>`;

        // Progress Calculation
        const joinDate = new Date(e.joining_date);
        const today = new Date();
        const diffTime = Math.abs(today - joinDate);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        const currentDay = diffDays > 15 ? 15 : diffDays;
        const progressPct = Math.round((currentDay / 15) * 100);

        // Calculate Action status pill
        const expectedDocs = e.bond_period_months > 0 ? 6 : 5;
        const docsCount = e.documents ? e.documents.length : 0;
        const hasSalarySet = e.salary_structures && e.salary_structures.length > 0;
        
        let statusClass = 'draft';
        let statusLabel = 'Draft';
        if (!hasSalarySet || docsCount < expectedDocs) {
            statusClass = 'action-needed';
            statusLabel = 'Action Needed';
        } else if (e.bitrix_sync_status === 'Synced') {
            statusClass = 'synced';
            statusLabel = 'Synced';
        } else if (e.bitrix_sync_status === 'Pending') {
            statusClass = 'pending';
            statusLabel = 'Pending';
        }

        return `
            <tr onclick="openEmployeeProfileDetail(${e.id})" style="border-bottom: 1px solid var(--border-color); height: 70px; cursor: pointer;">
                <td style="padding: 12px 20px; width: 40px;" onclick="event.stopPropagation()"><input type="checkbox" style="cursor:pointer; width: 16px; height: 16px; border-radius: 4px; border: 1.5px solid #cbd5e1;" onclick="event.stopPropagation()"></td>
                <td style="padding: 12px 20px; white-space: nowrap;">
                    <div style="display:flex; align-items:center;">
                        ${avatarCell}
                        <div>
                            <a href="#" onclick="openEmployeeProfileDetail(${e.id}); return false;" style="font-weight: 700; color: #0f172a; text-decoration: none; font-size: 10.5pt; font-family: 'Inter', sans-serif;">${e.first_name} ${e.last_name}</a>
                            <div style="font-size: 8.5pt; color: var(--text-muted); margin-top:2px;">${e.email}</div>
                        </div>
                    </div>
                </td>
                <td style="padding: 12px 20px; font-weight: 600; color: #1e293b; font-family: 'Inter', sans-serif;">${e.emp_id}</td>
                <td style="padding: 12px 20px; color: #475569;">${e.department_details ? e.department_details.name : e.department}</td>
                <td style="padding: 12px 20px; color: #475569;">${e.designation}</td>
                <td style="padding: 12px 20px; font-weight: 500; color: #1e293b;">${formatSimpleDate(e.joining_date)}</td>
                <td style="padding: 12px 20px;">
                    <span class="status-pill ${statusClass}">${statusLabel}</span>
                </td>
                <td style="padding: 12px 20px;">
                    <div class="progress-bar-wrapper">
                        <div class="premium-progress-track">
                            <div class="premium-progress-fill" style="width: ${progressPct}%;"></div>
                        </div>
                        <span class="progress-pct-label" style="color: #475569; font-weight: 600;">${progressPct}%</span>
                    </div>
                </td>
                <td style="padding: 12px 20px; text-align: right; position: relative;" onclick="event.stopPropagation()">
                    <div class="dropdown-menu-wrapper">
                        <button class="btn-dot-menu" onclick="toggleRowActionMenu(event, ${e.id})" style="font-size:14pt; font-weight:bold; color: #94a3b8; border: none; background: none; cursor: pointer; border-radius: 50%; width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center;">⋮</button>
                        <div class="premium-actions-dropdown" id="actionDropdown-${e.id}" style="position: absolute; right: 0; top: 35px;">
                            <button class="premium-dropdown-item" onclick="openEmployeeProfileDetail(${e.id})">View Profile</button>
                            <button class="premium-dropdown-item" onclick="openEmployeeProfileDetail(${e.id}, 'salary')">Setup Salary</button>
                            <button class="premium-dropdown-item" onclick="openEmployeeProfileDetail(${e.id}, 'letters')">Generate Letters</button>
                            <button class="premium-dropdown-item" onclick="manuallyGraduateEmployee(event, ${e.id})">Graduate Onboarding</button>
                            ${hasPermission('onboarding.delete') ? `<button class="premium-dropdown-item" onclick="softDeleteEmployee(${e.id})" style="color:#ef4444;">Delete Profile</button>` : ''}
                        </div>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// Render sub-tab 2: Active / Dismissed / Offboarding directory
function renderActiveDirectoryTable(list) {
    const tbody = document.getElementById('allEmployeesDirectoryTableBody');
    if (!tbody) return;
    
    if (list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 25px; color: var(--text-light);">No employees found in directory.</td></tr>`;
        return;
    }
    
    tbody.innerHTML = list.map(e => {
        const initials = `${e.first_name.charAt(0)}${e.last_name.charAt(0)}`.toUpperCase();
        
        const colors = [
            { bg: '#e0e7ff', text: '#4f46e5' },
            { bg: '#ffe4e6', text: '#e11d48' },
            { bg: '#d1fae5', text: '#059669' },
            { bg: '#fef3c7', text: '#d97706' },
            { bg: '#f3e8ff', text: '#9333ea' },
            { bg: '#ecfeff', text: '#0891b2' }
        ];
        const colorIdx = e.id % colors.length;
        const pair = colors[colorIdx];

        const avatarCell = e.profile_photo 
            ? `<img src="${e.profile_photo}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; margin-right: 12px; display:inline-block; vertical-align: middle;">`
            : `<div style="width: 40px; height: 40px; border-radius: 50%; background-color: ${pair.bg}; color: ${pair.text}; display: inline-flex; align-items: center; justify-content: center; font-weight: 700; font-size: 10pt; margin-right: 12px; vertical-align: middle; letter-spacing: -0.02em;">${initials}</div>`;

        let statusClass = 'synced';
        if (e.status === 'Exited') statusClass = 'action-needed';
        else if (e.status === 'Rejoined') statusClass = 'pending';

        return `
            <tr onclick="openEmployeeProfileDetail(${e.id})" style="border-bottom: 1px solid var(--border-color); height: 70px; cursor: pointer;">
                <td style="padding: 12px 20px; width: 40px;" onclick="event.stopPropagation()"><input type="checkbox" style="cursor:pointer; width: 16px; height: 16px; border-radius: 4px; border: 1.5px solid #cbd5e1;" onclick="event.stopPropagation()"></td>
                <td style="padding: 12px 20px; white-space: nowrap;">
                    <div style="display:flex; align-items:center;">
                        ${avatarCell}
                        <div>
                            <a href="#" onclick="openEmployeeProfileDetail(${e.id}); return false;" style="font-weight: 700; color: #0f172a; text-decoration: none; font-size: 10.5pt; font-family: 'Inter', sans-serif;">${e.first_name} ${e.last_name}</a>
                            <div style="font-size: 8.5pt; color: var(--text-muted); margin-top:2px;">${e.email}</div>
                        </div>
                    </div>
                </td>
                <td style="padding: 12px 20px; font-weight: 600; color: #1e293b; font-family: 'Inter', sans-serif;">${e.emp_id}</td>
                <td style="padding: 12px 20px; color: #475569;">${e.department_details ? e.department_details.name : e.department}</td>
                <td style="padding: 12px 20px; color: #475569;">${e.designation}</td>
                <td style="padding: 12px 20px; color: #475569;">${e.employment_type}</td>
                <td style="padding: 12px 20px; font-weight: 500; color: #1e293b;">${formatSimpleDate(e.joining_date)}</td>
                <td style="padding: 12px 20px;">
                    <span class="status-pill ${statusClass}">${e.status}</span>
                </td>
                <td style="padding: 12px 20px; text-align: right; position: relative;" onclick="event.stopPropagation()">
                    <div class="dropdown-menu-wrapper">
                        <button class="btn-dot-menu" onclick="toggleRowActionMenu(event, ${e.id})" style="font-size:14pt; font-weight:bold; color: #94a3b8; border: none; background: none; cursor: pointer; border-radius: 50%; width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center;">⋮</button>
                        <div class="premium-actions-dropdown" id="actionDropdown-${e.id}" style="position: absolute; right: 0; top: 35px;">
                            <button class="premium-dropdown-item" onclick="openEmployeeProfileDetail(${e.id})">View Profile</button>
                            <button class="premium-dropdown-item" onclick="openEmployeeProfileDetail(${e.id}, 'salary')">Edit Salary</button>
                            <button class="premium-dropdown-item" onclick="openEmployeeProfileDetail(${e.id}, 'letters')">Documents History</button>
                            ${e.status === 'Active' && hasPermission('exit.create') ? `
                                <button class="premium-dropdown-item" onclick="triggerExitFormality(${e.id})" style="color:#ef4444;">Initiate Exit</button>
                            ` : ''}
                        </div>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// Manual onboarding completion trigger
async function manuallyGraduateEmployee(event, empId) {
    event.stopPropagation();
    if (!confirm('Are you sure you want to graduate this employee from onboarding?')) return;
    
    showToast('Graduating employee...');
    try {
        const res = await apiFetch(`/employees/${empId}/manual-graduate/`, { method: 'POST' });
        if (res.ok) {
            showToast('Employee graduated and moved to Active Directory.');
            loadFilteredEmployeeData();
        } else {
            const err = await res.json();
            showToast(err.message || 'Graduation failed.', 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

// Trigger Excel Export for Active Directory matching filters
async function triggerExcelExport() {
    const dept = document.getElementById('onboardingDeptFilter').value;
    const type = document.getElementById('onboardingTypeFilter').value;
    const fromDate = document.getElementById('onboardingFromDateFilter').value;
    const toDate = document.getElementById('onboardingToDateFilter').value;
    
    let params = new URLSearchParams();
    params.append('type', 'all');
    if (dept) params.append('department', dept);
    if (type) params.append('employment_type', type);
    if (fromDate) params.append('from_date', fromDate);
    if (toDate) params.append('to_date', toDate);
    
    showToast('Preparing spreadsheet download...');
    try {
        const res = await apiFetch(`/employees/export-excel/?${params.toString()}`);
        if (res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `employee_directory_${new Date().toISOString().slice(0,10)}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            showToast('Download complete.');
        } else {
            showToast('Export failed.', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Export error.', 'error');
    }
}

// Onboarding Form Page Loader
async function loadOnboardingFormPage() {
    document.getElementById('pageTitle').textContent = 'Employee Onboarding';
    populateStatesDropdown('empState');
    await loadDepartmentsSelect('empDept');
}

// Load Departments select dropdown
async function loadDepartmentsSelect(selectId) {
    try {
        const res = await apiFetch('/onboarding/departments/');
        if (res.ok) {
            const depts = await res.json();
            const deptList = depts.results || depts;
            const select = document.getElementById(selectId);
            if (select) {
                const hasAll = select.firstElementChild && select.firstElementChild.value === '';
                select.innerHTML = (hasAll ? `<option value="">All Departments</option>` : '') + 
                    deptList.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
            }
        }
    } catch (e) {
        console.error(e);
    }
}

// ---------- EMPLOYEE PROFILE TABS & DETAILS ----------
// Sidebar progress helper for onboarding
function updateOnboardingProgressSidebar(emp) {
    const bondPeriod = parseInt(emp.bond_period_months || 0);
    const expectedDocs = bondPeriod > 0 ? 6 : 5;
    const docsCount = emp.documents ? emp.documents.length : 0;
    const hasSalarySet = emp.salary_structures && emp.salary_structures.length > 0;
    
    const docWeight = 60;
    const salWeight = 40;
    
    const docProgress = docsCount >= expectedDocs ? docWeight : (docsCount / expectedDocs) * docWeight;
    const salProgress = hasSalarySet ? salWeight : 0;
    
    const totalProgress = Math.round(docProgress + salProgress);
    
    const bar = document.getElementById('sidebarProgressBar');
    const text = document.getElementById('sidebarProgressText');
    const metrics = document.getElementById('sidebarChecklistMetrics');
    
    if (bar && text && metrics) {
        bar.style.width = `${totalProgress}%`;
        text.textContent = `${totalProgress}%`;
        
        let desc = `<div style="margin-top: 8px; display: flex; flex-direction: column; gap: 4px;">`;
        desc += `<div style="display: flex; align-items: center; gap: 6px;">` + 
                (docsCount >= expectedDocs ? `<span style="color:#10b981;">✓</span>` : `<span style="color:#f59e0b;">●</span>`) + 
                `<span>Documents: ${docsCount}/${expectedDocs} uploaded</span></div>`;
        desc += `<div style="display: flex; align-items: center; gap: 6px;">` + 
                (hasSalarySet ? `<span style="color:#10b981;">✓</span>` : `<span style="color:#f59e0b;">●</span>`) + 
                `<span>Salary Structure: ${hasSalarySet ? 'Configured' : 'Pending'}</span></div>`;
        desc += `</div>`;
        metrics.innerHTML = desc;
    }
}

// Interactive checklist rendering for documents tab
function renderDocumentsChecklist(docList, bondPeriod) {
    const container = document.getElementById('documentsChecklistContainer');
    if (!container) return;
    
    const requiredDocs = [
        { type: 'RESUME', name: 'Resume / CV', desc: 'Verify professional experience.' },
        { type: 'AADHAAR', name: 'Aadhaar Card', desc: 'Government identity proof.' },
        { type: 'PAN', name: 'PAN Card', desc: 'Income tax account details.' },
        { type: 'OFFER_LETTER', name: 'Signed Offer Letter', desc: 'Candidate acceptance verification.' },
        { type: 'APPOINTMENT_LETTER', name: 'Signed Appointment Contract', desc: 'Signed employment terms.' }
    ];
    
    if (bondPeriod > 0) {
        requiredDocs.push({ type: 'BOND_LETTER', name: 'Signed Bond Agreement', desc: 'Candidate training commitment bond.' });
    }
    
    container.innerHTML = requiredDocs.map(req => {
        const doc = docList.find(d => d.doc_type === req.type);
        const isUploaded = !!doc;
        
        const badgeBg = isUploaded ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)';
        const badgeTextColor = isUploaded ? '#10b981' : '#ef4444';
        const badgeBorderColor = isUploaded ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)';
        const badgeText = isUploaded ? 'Verified' : 'Missing';
        
        return `
            <div style="background-color: var(--bg-card); border: 1.5px solid ${isUploaded ? '#e2e8f0' : badgeBorderColor}; border-radius: 12px; padding: 16px; display: flex; flex-direction: column; justify-content: space-between; gap: 12px; box-shadow: var(--shadow-sm); transition: all 0.2s;" onmouseover="this.style.boxShadow='var(--shadow-md)'" onmouseout="this.style.boxShadow='var(--shadow-sm)'">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px;">
                        <span style="font-weight: 700; color: var(--text-main); font-size: 13.5px; line-height: 1.3;">${req.name}</span>
                        <span style="background-color: ${badgeBg}; color: ${badgeTextColor}; padding: 3px 8px; border-radius: 999px; font-size: 10px; font-weight: 700; border: 1px solid ${badgeBorderColor}; white-space: nowrap;">${badgeText}</span>
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px; line-height: 1.3;">${req.desc}</div>
                </div>
                ${isUploaded ? `
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 5px; border-top: 1px solid var(--border-color); padding-top: 8px;">
                        <span style="font-size: 9.5px; color: var(--text-light); font-family: monospace;">Uploaded: ${formatSimpleDate(doc.upload_date)}</span>
                        <div style="display: flex; gap: 6px;">
                            <button class="btn btn-secondary btn-sm" style="padding: 4px 6px; font-size: 10px; border-radius: 6px; font-weight:700; display: flex; align-items: center; gap: 3px;" onclick="viewSecureFile('${doc.file}', '${doc.doc_type}')">
                                👁️ View
                            </button>
                            <button class="btn btn-secondary btn-sm" style="padding: 4px 6px; font-size: 10px; border-radius: 6px; font-weight:700;" onclick="downloadSecureFile('${doc.file}', '${doc.original_filename || 'document.pdf'}')">Download</button>
                        </div>
                    </div>
                ` : `
                    <div style="margin-top: 5px; border-top: 1px dashed var(--border-color); padding-top: 8px;">
                        <button class="btn btn-primary btn-sm" style="width: 100%; font-size: 11px; padding: 6px; border-radius: 6px; background-color: var(--primary-light); color: var(--primary-color); border: 1px solid rgba(124,58,237,0.2); font-weight:700;" onclick="document.getElementById('uploadDocType').value='${req.type}'; toggleDocLabelField(); document.getElementById('uploadDocFile').focus();">Upload File</button>
                    </div>
                `}
            </div>
        `;
    }).join('');
}

async function openEmployeeProfileDetail(empId, tabToFocus = 'personal') {
    currentDetailEmployeeId = empId;
    switchView('employeeDetailView');
    
    try {
        const res = await apiFetch(`/employees/${empId}/`);
        if (res.ok) {
            const emp = await res.json();
            
            document.getElementById('detailProfileName').textContent = `${emp.first_name} ${emp.last_name}`;
            document.getElementById('detailProfileDesignation').textContent = emp.designation;
            document.getElementById('detailProfileEmpId').textContent = emp.emp_id;
            document.getElementById('detailProfileDept').textContent = emp.department_details ? emp.department_details.name : emp.department;
            
            const statusBadge = document.getElementById('detailProfileStatusBadge');
            statusBadge.textContent = emp.status;
            statusBadge.style.backgroundColor = emp.status === 'Active' ? '#22c55e' : '#ef4444';
            statusBadge.style.color = 'white';

            const bitrixBadge = document.getElementById('detailProfileBitrixBadge');
            bitrixBadge.textContent = emp.bitrix_sync_status;
            bitrixBadge.style.backgroundColor = emp.bitrix_sync_status === 'Synced' ? '#22c55e' : (emp.bitrix_sync_status === 'Pending' ? '#f59e0b' : '#ef4444');
            bitrixBadge.style.color = 'white';
            
            document.getElementById('detailBitrixActions').style.display = emp.bitrix_sync_status === 'Failed' ? 'block' : 'none';

            const img = document.getElementById('detailProfilePhoto');
            const fallback = document.getElementById('detailProfilePhotoFallback');
            if (emp.profile_photo) {
                img.src = emp.profile_photo;
                img.style.display = 'block';
                fallback.style.display = 'none';
            } else {
                img.style.display = 'none';
                fallback.style.display = 'block';
            }

            document.getElementById('editEmpFirstName').value = emp.first_name;
            document.getElementById('editEmpLastName').value = emp.last_name;
            document.getElementById('editEmpEmail').value = emp.email;
            document.getElementById('editEmpPhone').value = emp.phone;
            document.getElementById('editEmpAltPhone').value = emp.alternate_phone || '';
            document.getElementById('editEmpDob').value = emp.dob;
            document.getElementById('editEmpGender').value = emp.gender;
            
            document.getElementById('editEmpAddr1').value = emp.address_line1;
            document.getElementById('editEmpAddr2').value = emp.address_line2 || '';
            document.getElementById('editEmpCity').value = emp.city;
            
            populateStatesDropdown('editEmpState');
            document.getElementById('editEmpState').value = emp.state;
            document.getElementById('editEmpPin').value = emp.pin_code;
            
            document.getElementById('editEmpDept').value = emp.department;
            document.getElementById('editEmpDesignation').value = emp.designation;
            document.getElementById('editEmpType').value = emp.employment_type;
            document.getElementById('editEmpNotice').value = emp.notice_period_days;
            document.getElementById('editEmpBond').value = emp.bond_period_months;
            
            document.getElementById('editEmpAadhaar').value = emp.aadhaar_masked || '';
            document.getElementById('editEmpPan').value = emp.pan_masked || '';
            
            document.getElementById('editEmpEmergencyName').value = emp.emergency_contact_name;
            document.getElementById('editEmpEmergencyRel').value = emp.emergency_relationship;
            document.getElementById('editEmpEmergencyPhone').value = emp.emergency_phone;

            const joinInput = document.getElementById('editEmpJoining');
            joinInput.value = emp.joining_date;
            if (currentUser && currentUser.role === 'ADMIN') {
                joinInput.removeAttribute('disabled');
                joinInput.style.backgroundColor = 'var(--bg-color)';
                document.getElementById('joiningDateHelpText').style.display = 'none';
            } else {
                joinInput.setAttribute('disabled', 'true');
                joinInput.style.backgroundColor = 'var(--border-color)';
                document.getElementById('joiningDateHelpText').style.display = 'block';
            }
            
            // Update the sidebar progress card
            updateOnboardingProgressSidebar(emp);
            
            const deleteBtn = document.getElementById('deleteEmployeeDetailBtn');
            if (deleteBtn) {
                if (hasPermission('onboarding.delete')) {
                    deleteBtn.style.display = 'inline-block';
                } else {
                    deleteBtn.style.display = 'none';
                }
            }
            
            switchProfileTab(tabToFocus);
        }
    } catch (e) {
        console.error(e);
        showToast('Error loading profile detail.', 'error');
    }
}

// Switch Profile Detail Tab Views
function switchProfileTab(tabId) {
    activeProfileTab = tabId;
    
    const tabs = ['personal', 'docs', 'salary', 'letters', 'audit'];
    tabs.forEach(t => {
        const btn = document.getElementById(`pTab${t.charAt(0).toUpperCase() + t.slice(1)}Btn`);
        const block = document.getElementById(`profileTab${t.charAt(0).toUpperCase() + t.slice(1)}`);
        
        if (t === tabId) {
            btn.classList.add('active');
            btn.style.color = 'var(--primary-color)';
            btn.style.borderBottom = '3px solid var(--primary-color)';
            block.style.display = 'block';
        } else {
            btn.classList.remove('active');
            btn.style.color = 'var(--text-muted)';
            btn.style.borderBottom = '3px solid transparent';
            block.style.display = 'none';
        }
    });

    if (tabId === 'docs') loadProfileDocumentsList();
    else if (tabId === 'salary') loadProfileSalaryHistory();
    else if (tabId === 'letters') loadProfileLettersList();
    else if (tabId === 'audit') loadProfileAuditLog();
}

// Retrying failed Bitrix24 sync
async function triggerManualBitrixRetry() {
    if (!currentDetailEmployeeId) return;
    showToast('Queuing Bitrix24 contact sync...');
    try {
        const res = await apiFetch(`/employees/${currentDetailEmployeeId}/retry-bitrix-sync/`, { method: 'POST' });
        if (res.ok) {
            showToast('Bitrix24 sync re-queued successfully.');
            setTimeout(() => openEmployeeProfileDetail(currentDetailEmployeeId, activeProfileTab), 1500);
        }
    } catch (e) {
        console.error(e);
    }
}

// ---------- EDIT PERSONAL PROFILE SUBMIT ----------
document.addEventListener('DOMContentLoaded', () => {
    const editForm = document.getElementById('editEmployeeForm');
    if (editForm) {
        editForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!currentDetailEmployeeId) return;
            
            showToast('Saving changes...');
            
            const formData = new FormData();
            formData.append('first_name', document.getElementById('editEmpFirstName').value);
            formData.append('last_name', document.getElementById('editEmpLastName').value);
            formData.append('phone', document.getElementById('editEmpPhone').value);
            formData.append('alternate_phone', document.getElementById('editEmpAltPhone').value);
            formData.append('dob', document.getElementById('editEmpDob').value);
            formData.append('gender', document.getElementById('editEmpGender').value);
            
            formData.append('address_line1', document.getElementById('editEmpAddr1').value);
            formData.append('address_line2', document.getElementById('editEmpAddr2').value);
            formData.append('city', document.getElementById('editEmpCity').value);
            formData.append('state', document.getElementById('editEmpState').value);
            formData.append('pin_code', document.getElementById('editEmpPin').value);
            
            formData.append('department', document.getElementById('editEmpDept').value);
            formData.append('designation', document.getElementById('editEmpDesignation').value);
            formData.append('employment_type', document.getElementById('editEmpType').value);
            formData.append('notice_period_days', document.getElementById('editEmpNotice').value);
            formData.append('bond_period_months', document.getElementById('editEmpBond').value || 0);
            
            const aadhaarVal = document.getElementById('editEmpAadhaar').value;
            const panVal = document.getElementById('editEmpPan').value;
            if (aadhaarVal) formData.append('aadhaar', aadhaarVal);
            if (panVal) formData.append('pan', panVal);
            
            formData.append('emergency_contact_name', document.getElementById('editEmpEmergencyName').value);
            formData.append('emergency_relationship', document.getElementById('editEmpEmergencyRel').value);
            formData.append('emergency_phone', document.getElementById('editEmpEmergencyPhone').value);

            const joinInput = document.getElementById('editEmpJoining');
            if (joinInput && !joinInput.disabled) {
                formData.append('joining_date', joinInput.value);
            }

            const photoFile = document.getElementById('editEmpPhotoFile').files[0];
            if (photoFile) {
                formData.append('profile_photo', photoFile);
            }

            try {
                const res = await apiFetch(`/employees/${currentDetailEmployeeId}/`, {
                    method: 'PATCH',
                    body: formData
                });
                
                if (res.ok) {
                    showToast('Profile updated successfully.');
                    loadFilteredEmployeeData();
                    openEmployeeProfileDetail(currentDetailEmployeeId, 'personal');
                } else {
                    const err = await res.json();
                    showToast('Update Failed: ' + JSON.stringify(err), 'error');
                }
            } catch (ex) {
                console.error(ex);
                showToast('Network error during save.', 'error');
            }
        });
    }

    // ---------- CREATE NEW ONBOARDING PROFILE ----------
    const onboardForm = document.getElementById('onboardForm');
    if (onboardForm) {
        onboardForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            showToast('Creating employee profile...');
            
            const formData = new FormData();
            formData.append('first_name', document.getElementById('empFirstName').value);
            formData.append('last_name', document.getElementById('empLastName').value);
            formData.append('email', document.getElementById('empEmail').value);
            formData.append('phone', document.getElementById('empPhone').value);
            formData.append('dob', document.getElementById('empDob').value);
            formData.append('gender', document.getElementById('empGender').value);
            
            formData.append('address_line1', document.getElementById('empAddr1').value);
            formData.append('city', document.getElementById('empCity').value);
            formData.append('state', document.getElementById('empState').value);
            formData.append('pin_code', document.getElementById('empPin').value);
            
            formData.append('department', document.getElementById('empDept').value);
            formData.append('designation', document.getElementById('empDesignation').value);
            formData.append('employment_type', document.getElementById('empType').value);
            formData.append('joining_date', document.getElementById('empJoining').value);
            formData.append('notice_period_days', document.getElementById('empNotice').value);
            formData.append('bond_period_months', document.getElementById('empBond').value || 0);
            
            const aadhaarVal = document.getElementById('empAadhaar').value;
            const panVal = document.getElementById('empPan').value;
            if (aadhaarVal) formData.append('aadhaar', aadhaarVal);
            if (panVal) formData.append('pan', panVal);
            
            formData.append('emergency_contact_name', document.getElementById('empEmergencyName').value);
            formData.append('emergency_relationship', document.getElementById('empEmergencyRel').value);
            formData.append('emergency_phone', document.getElementById('empEmergencyPhone').value);

            try {
                const res = await apiFetch('/employees/', {
                    method: 'POST',
                    body: formData
                });
                
                if (res.status === 201 || res.ok) {
                    showToast('Employee profile created successfully.');
                    onboardForm.reset();
                    switchView('onboardingView');
                    loadFilteredEmployeeData();
                } else {
                    const err = await res.json();
                    showToast('Creation Failed: ' + JSON.stringify(err), 'error');
                }
            } catch (ex) {
                console.error(ex);
                showToast('Network error during creation.', 'error');
            }
        });
    }
});

// ---------- TAB 2: DOCUMENTS LOADING & UPLOAD ----------
async function loadProfileDocumentsList() {
    if (!currentDetailEmployeeId) return;
    try {
        const res = await apiFetch(`/onboarding/documents/?employee_id=${currentDetailEmployeeId}`);
        if (res.ok) {
            const docs = await res.json();
            const docList = docs.results || docs;
            const tbody = document.getElementById('profileDocsTableBody');
            
            // Render interactive checklist
            const bondPeriod = parseInt(document.getElementById('editEmpBond').value || 0);
            renderDocumentsChecklist(docList, bondPeriod);
            
            if (tbody) {
                if (docList.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:20px; color: var(--text-light);">No onboarding documents uploaded yet.</td></tr>`;
                    return;
                }
                
                tbody.innerHTML = docList.map(d => {
                    return `
                        <tr style="border-bottom: 1px solid var(--border-color); height: 60px;">
                            <td style="padding: 12px 20px;"><strong>${d.doc_type.replace('_', ' ')}</strong></td>
                            <td style="padding: 12px 20px;">
                                <div style="font-weight: 500; color: var(--text-main);">${d.label || '-'}</div>
                                ${d.remarks ? `<small style="color:var(--text-muted); font-size:11px;">Note: ${d.remarks}</small>` : ''}
                            </td>
                            <td style="padding: 12px 20px; color: var(--text-secondary);">${formatSimpleDate(d.upload_date)}</td>
                            <td style="padding: 12px 20px; color: var(--text-secondary);">${d.uploaded_by_username || 'System'}</td>
                            <td style="padding: 12px 20px; text-align:center;">
                                <div style="display: flex; justify-content: center; gap: 6px;">
                                    <button class="btn btn-secondary btn-sm" style="font-size:11px; padding:6px 12px; border-radius: 6px; display: flex; align-items: center; gap: 4px;" onclick="viewSecureFile('${d.file}', '${d.doc_type}')">
                                        👁️ View
                                    </button>
                                    <button class="btn btn-secondary btn-sm" style="font-size:11px; padding:6px 12px; border-radius: 6px; display: flex; align-items: center; gap: 4px;" onclick="downloadSecureFile('${d.file}', '${d.original_filename || 'document.pdf'}')">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 3v12"/></svg>Download
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
    } catch (e) {
        console.error(e);
    }
}

// Secure Document Streaming File Download helper
async function downloadSecureFile(urlPath, downloadName) {
    showToast('Downloading document...');
    try {
        const res = await apiFetch(urlPath);
        if (res.ok) {
            const blob = await res.blob();
            const blobUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = downloadName;
            document.body.appendChild(a);
            a.click();
            a.remove();
            showToast('Download complete.');
        } else {
            showToast('Access Denied or File Not Found.', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Download error.', 'error');
    }
}

async function viewSecureFile(urlPath, docType) {
    showToast('Loading document preview...');
    try {
        const res = await apiFetch(urlPath);
        if (res.ok) {
            const blob = await res.blob();
            const mimeType = blob.type;
            const blobUrl = window.URL.createObjectURL(blob);
            openDocumentViewerModal(blobUrl, mimeType, docType.replace('_', ' '));
        } else {
            showToast('Access Denied or File Not Found.', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Error loading document preview.', 'error');
    }
}

function openDocumentViewerModal(blobUrl, mimeType, title) {
    const modal = document.getElementById('documentViewerModal');
    const titleEl = document.getElementById('docViewerTitle');
    const bodyEl = document.getElementById('docViewerBody');
    
    if (!modal || !bodyEl) return;
    
    if (titleEl) {
        titleEl.textContent = title + " Preview";
    }
    
    if (mimeType.startsWith('image/')) {
        bodyEl.innerHTML = `<img src="${blobUrl}" style="max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 8px; box-shadow: var(--shadow-md);" />`;
    } else if (mimeType === 'application/pdf') {
        bodyEl.innerHTML = `<iframe src="${blobUrl}" style="width: 100%; height: 100%; border: none; border-radius: 8px;"></iframe>`;
    } else {
        bodyEl.innerHTML = `
            <div style="text-align: center; padding: 20px;">
                <p style="font-weight: 600; color: var(--text-main); margin-bottom: 15px;">Preview not supported for this file type.</p>
                <button class="btn btn-primary" onclick="window.open('${blobUrl}')">Open in New Tab</button>
            </div>
        `;
    }
    
    modal.style.display = 'flex';
}

function closeDocumentViewerModal() {
    const modal = document.getElementById('documentViewerModal');
    const bodyEl = document.getElementById('docViewerBody');
    if (modal) modal.style.display = 'none';
    if (bodyEl) bodyEl.innerHTML = '';
}

function toggleDocLabelField() {
    const type = document.getElementById('uploadDocType').value;
    document.getElementById('docLabelContainer').style.display = type === 'OTHER' ? 'block' : 'none';
}

// Upload Document Form submission
document.addEventListener('DOMContentLoaded', () => {
    const docForm = document.getElementById('docUploadForm');
    if (docForm) {
        docForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!currentDetailEmployeeId) return;

            const docType = document.getElementById('uploadDocType').value;
            const docLabel = document.getElementById('uploadDocLabel').value;
            const remarks = document.getElementById('uploadDocRemarks').value;
            const file = document.getElementById('uploadDocFile').files[0];

            if (docType === 'OTHER' && !docLabel) {
                showToast('Please specify custom label for document type Other.', 'error');
                return;
            }

            showToast('Uploading file...');
            const formData = new FormData();
            formData.append('employee', currentDetailEmployeeId);
            formData.append('doc_type', docType);
            formData.append('label', docType === 'OTHER' ? docLabel : remarks);
            formData.append('remarks', remarks);
            formData.append('file', file);

            try {
                const res = await apiFetch('/onboarding/documents/', {
                    method: 'POST',
                    body: formData
                });
                
                if (res.ok) {
                    showToast('Document uploaded successfully.');
                    docForm.reset();
                    document.getElementById('docLabelContainer').style.display = 'none';
                    loadProfileDocumentsList();
                } else {
                    const err = await res.json();
                    showToast('Upload failed: ' + JSON.stringify(err), 'error');
                }
            } catch (ex) {
                console.error(ex);
                showToast('Upload error.', 'error');
            }
        });
    }
});

// ---------- TAB 3: SALARY STRUCTURE SETUP ----------
let repeatableAllowances = [];
let repeatableDeductions = [];

function togglePfInput() {
    // Legacy stub
}

// Live calculation of Gross, Deductions, and Net salary
function calculateTakeHomeSalary() {
    const gross = parseFloat(document.getElementById('salGrossSalary').value || 0);
    const pf = parseFloat(document.getElementById('salPfContribution').value || 0);
    const esi = parseFloat(document.getElementById('salEsi').value || 0);
    const lwf = parseFloat(document.getElementById('salLabourWelfareFund').value || 0);
    const pt = parseFloat(document.getElementById('salProfessionalTax').value || 0);
    const other = parseFloat(document.getElementById('salOtherDeductions').value || 0);

    const totalDeductions = pf + esi + lwf + pt + other;
    const net = gross - totalDeductions;

    const summaryGross = document.getElementById('salSummaryGross');
    if (summaryGross) summaryGross.value = gross.toFixed(2);

    const summaryDeductions = document.getElementById('salSummaryDeductions');
    if (summaryDeductions) summaryDeductions.value = totalDeductions.toFixed(2);

    const summaryNet = document.getElementById('salSummaryNet');
    if (summaryNet) summaryNet.value = net.toFixed(2);
}

// Repeatable allowances/deductions legacy no-ops
function addAllowanceRow() {}
function removeAllowanceRow() {}
function addDeductionRow() {}
function removeDeductionRow() {}

// Submit Salary structure
document.addEventListener('DOMContentLoaded', () => {
    const salForm = document.getElementById('salarySetupForm');
    if (salForm) {
        salForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!currentDetailEmployeeId) return;

            showToast('Saving salary structure...');

            const data = {
                employee: currentDetailEmployeeId,
                effective_from: document.getElementById('salEffectiveFrom').value,
                gross_salary: parseFloat(document.getElementById('salGrossSalary').value || 0),
                pf_contribution: parseFloat(document.getElementById('salPfContribution').value || 0),
                esi: parseFloat(document.getElementById('salEsi').value || 0),
                labour_welfare_fund: parseFloat(document.getElementById('salLabourWelfareFund').value || 0),
                professional_tax: parseFloat(document.getElementById('salProfessionalTax').value || 0),
                other_deductions: parseFloat(document.getElementById('salOtherDeductions').value || 0)
            };

            try {
                const res = await apiFetch('/salaries/', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });

                if (res.ok) {
                    showToast('Salary structure defined successfully.');
                    salForm.reset();
                    loadProfileSalaryHistory();
                } else {
                    const err = await res.json();
                    showToast('Save Failed: ' + JSON.stringify(err), 'error');
                }
            } catch (ex) {
                console.error(ex);
                showToast('Save error.', 'error');
            }
        });
    }
});

// Load Employee Salary History
async function loadProfileSalaryHistory() {
    if (!currentDetailEmployeeId) return;
    try {
        const res = await apiFetch(`/salaries/?employee_id=${currentDetailEmployeeId}`);
        if (res.ok) {
            const structures = await res.json();
            const structList = structures.results || structures;
            const tbody = document.getElementById('profileSalaryHistoryTableBody');
            
            if (tbody) {
                if (structList.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:15px;">No salary structure defined yet.</td></tr>`;
                    return;
                }
                
                const latest = structList[0];
                const effFrom = document.getElementById('salEffectiveFrom');
                if (effFrom) effFrom.value = latest.effective_from || '';

                const gross = document.getElementById('salGrossSalary');
                if (gross) gross.value = latest.gross_salary || '';

                const pf = document.getElementById('salPfContribution');
                if (pf) pf.value = latest.pf_contribution || '';

                const esi = document.getElementById('salEsi');
                if (esi) esi.value = latest.esi || '';

                const lwf = document.getElementById('salLabourWelfareFund');
                if (lwf) lwf.value = latest.labour_welfare_fund || '';

                const pt = document.getElementById('salProfessionalTax');
                if (pt) pt.value = latest.professional_tax || '';

                const other = document.getElementById('salOtherDeductions');
                if (other) other.value = latest.other_deductions || '';
                
                calculateTakeHomeSalary();

                tbody.innerHTML = structList.map(s => {
                    return `
                        <tr>
                            <td><strong>${formatSimpleDate(s.effective_from)}</strong></td>
                            <td>Rs. ${parseFloat(s.gross_salary).toFixed(2)}</td>
                            <td>Rs. ${parseFloat(s.total_deductions).toFixed(2)}</td>
                            <td style="color:#22c55e; font-weight:bold;">Rs. ${parseFloat(s.net_salary).toFixed(2)}</td>
                            <td>${s.created_by_username || 'System'}</td>
                        </tr>
                    `;
                }).join('');
            }
        }
    } catch (e) {
        console.error(e);
    }
}

// ---------- TAB 4: PDF GENERATION & HISTORY ----------
let activeLetterType = null;
let previewDebounceTimer = null;
let loadedTemplates = [];

function switchLettersSubTab(tab) {
    const genBtn = document.getElementById('subTabGenerateBtn');
    const tempBtn = document.getElementById('subTabTemplateBtn');
    const genTab = document.getElementById('lettersSubTabGenerate');
    const tempTab = document.getElementById('lettersSubTabTemplate');
    
    if (!genBtn || !tempBtn || !genTab || !tempTab) return;
    
    if (tab === 'generate') {
        genBtn.classList.add('active');
        genBtn.style.color = 'var(--primary-color)';
        genBtn.style.borderBottom = '3px solid var(--primary-color)';
        tempBtn.classList.remove('active');
        tempBtn.style.color = 'var(--text-secondary)';
        tempBtn.style.borderBottom = 'none';
        genTab.style.display = 'block';
        tempTab.style.display = 'none';
    } else {
        tempBtn.classList.add('active');
        tempBtn.style.color = 'var(--primary-color)';
        tempBtn.style.borderBottom = '3px solid var(--primary-color)';
        genBtn.classList.remove('active');
        genBtn.style.color = 'var(--text-secondary)';
        genBtn.style.borderBottom = 'none';
        tempTab.style.display = 'block';
        genTab.style.display = 'none';
        loadTemplatesList();
    }
}

function closeLetterWorkspace() {
    const ws = document.getElementById('letterWorkspace');
    if (ws) ws.style.display = 'none';
    activeLetterType = null;
}

async function openLetterWorkspace(type) {
    if (!currentDetailEmployeeId) return;
    activeLetterType = type;
    
    const titleMap = {
        'offer': 'Customize Offer Letter',
        'appointment': 'Customize Appointment Letter',
        'bond': 'Customize Service Bond Agreement'
    };
    
    const titleEl = document.getElementById('workspaceTitle');
    if (titleEl) titleEl.innerText = titleMap[type] || 'Customize Letter';
    
    const bondGroup = document.getElementById('custBondPeriodGroup');
    if (bondGroup) {
        bondGroup.style.display = (type === 'bond') ? 'block' : 'none';
    }
    
    const ws = document.getElementById('letterWorkspace');
    if (ws) ws.style.display = 'flex';
    
    const spinner = document.getElementById('previewSpinner');
    if (spinner) spinner.style.display = 'flex';
    
    try {
        const res = await apiFetch(`/employees/${currentDetailEmployeeId}/`);
        if (res.ok) {
            const emp = await res.json();
            
            let latestSalary = null;
            if (emp.salary_structures && emp.salary_structures.length > 0) {
                emp.salary_structures.sort((a,b) => new Date(b.effective_from) - new Date(a.effective_from));
                latestSalary = emp.salary_structures[0];
            }
            
            const today = new Date();
            const formattedToday = today.getDate() + 'th ' + today.toLocaleString('default', { month: 'long' }) + ' ' + today.getFullYear();
            
            document.getElementById('custLetterDate').value = formattedToday;
            document.getElementById('custJoiningDate').value = emp.joining_date || '';
            document.getElementById('custFirstName').value = emp.first_name || '';
            document.getElementById('custLastName').value = emp.last_name || '';
            document.getElementById('custDesignation').value = emp.designation || '';
            document.getElementById('custAddress1').value = emp.address_line1 || '';
            document.getElementById('custCity').value = emp.city || '';
            document.getElementById('custState').value = emp.state || 'PB';
            document.getElementById('custBondPeriod').value = emp.bond_period_months || 12;
            document.getElementById('custNoticePeriod').value = emp.notice_period_days || 30;
            
            document.getElementById('custCompanyName').value = 'Devex Hub Pvt Ltd.';
            document.getElementById('custCompanyAddress').value = 'Plot No D-254, Fourth Floor, Phase 8A, Industrial Area, Mohali';
            document.getElementById('custSignatoryName').value = 'Head of HR Operations';
            document.getElementById('custSignatoryDesignation').value = 'Authorized Signatory';
            
            if (latestSalary) {
                document.getElementById('custCTC').value = parseFloat(latestSalary.gross_salary || 0);
                document.getElementById('custInHand').value = parseFloat(latestSalary.net_salary || 0);
                document.getElementById('custBasic').value = parseFloat(latestSalary.gross_salary || 0);
                document.getElementById('custHra').value = 0;
                document.getElementById('custConveyance').value = 0;
                document.getElementById('custMedical').value = 0;
                document.getElementById('custSpecial').value = 0;
                document.getElementById('custBonus').value = 0;
                
                document.getElementById('custEsiEmployer').value = 0;
                document.getElementById('custPfEmployer').value = 0;
                document.getElementById('custPfEmployee').value = parseFloat(latestSalary.pf_contribution || 0);
                document.getElementById('custEsiEmployee').value = parseFloat(latestSalary.esi || 0);
                document.getElementById('custLwf').value = parseFloat(latestSalary.labour_welfare_fund || 0);
                document.getElementById('custPT').value = parseFloat(latestSalary.professional_tax || 200);
            } else {
                const salaryFields = ['custCTC', 'custInHand', 'custBasic', 'custHra', 'custConveyance', 'custMedical', 'custSpecial', 'custBonus', 'custEsiEmployer', 'custPfEmployer', 'custPfEmployee', 'custEsiEmployee', 'custLwf', 'custPT'];
                salaryFields.forEach(f => {
                    const el = document.getElementById(f);
                    if (el) el.value = 0;
                });
                const ptEl = document.getElementById('custPT');
                if (ptEl) ptEl.value = 200;
            }
            
            await updateLetterPreview();
        }
    } catch (e) {
        console.error(e);
        showToast('Error loading employee details for letter customization.', 'error');
    }
}

function debounceLetterPreview() {
    if (previewDebounceTimer) clearTimeout(previewDebounceTimer);
    previewDebounceTimer = setTimeout(() => {
        updateLetterPreview();
    }, 800);
}

async function updateLetterPreview() {
    if (!currentDetailEmployeeId || !activeLetterType) return;
    
    const spinner = document.getElementById('previewSpinner');
    if (spinner) spinner.style.display = 'flex';
    
    const docTypeMap = {
        'offer': 'OFFER_LETTER',
        'appointment': 'APPOINTMENT_LETTER',
        'bond': 'BOND_LETTER'
    };
    const doc_type = docTypeMap[activeLetterType];
    
    const custom_context = {
        date: document.getElementById('custLetterDate').value,
        first_name: document.getElementById('custFirstName').value,
        last_name: document.getElementById('custLastName').value,
        designation: document.getElementById('custDesignation').value,
        joining_date: document.getElementById('custJoiningDate').value,
        notice_period_days: document.getElementById('custNoticePeriod').value,
        bond_period_months: document.getElementById('custBondPeriod').value,
        address_line1: document.getElementById('custAddress1').value,
        city: document.getElementById('custCity').value,
        state: document.getElementById('custState').value,
        company_name: document.getElementById('custCompanyName').value,
        company_address: document.getElementById('custCompanyAddress').value,
        signatory_name: document.getElementById('custSignatoryName').value,
        signatory_designation: document.getElementById('custSignatoryDesignation').value,
        
        ctc: document.getElementById('custCTC').value,
        in_hand: document.getElementById('custInHand').value,
        basic: document.getElementById('custBasic').value,
        hra: document.getElementById('custHra').value,
        conveyance: document.getElementById('custConveyance').value,
        medical: document.getElementById('custMedical').value,
        special: document.getElementById('custSpecial').value,
        monthly_bonus: document.getElementById('custBonus').value,
        esi_employer: document.getElementById('custEsiEmployer').value,
        pf_employer: document.getElementById('custPfEmployer').value,
        pf_employee: document.getElementById('custPfEmployee').value,
        esi_employee: document.getElementById('custEsiEmployee').value,
        lwf: document.getElementById('custLwf').value,
        professional_tax: document.getElementById('custPT').value,
    };
    
    try {
        const res = await apiFetch(`/employees/${currentDetailEmployeeId}/preview-letter/`, {
            method: 'POST',
            body: JSON.stringify({
                doc_type: doc_type,
                custom_context: custom_context
            })
        });
        
        if (res.ok) {
            const data = await res.json();
            const iframe = document.getElementById('letterPreviewIframe');
            if (iframe) {
                let html = data.html;
                
                // CSS to style the pages inside the iframe preview
                const previewStyles = `
<style id="a4-preview-styles">
    @media screen {
        html, body {
            background-color: #f1f5f9 !important;
            margin: 0 !important;
            padding: 0 !important;
            height: auto !important;
            font-family: 'Times New Roman', serif !important;
        }
        
        /* Center container for pages */
        .a4-preview-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 0 !important;
            gap: 30px !important;
            width: 100% !important;
            box-sizing: border-box !important;
            background-color: #f1f5f9 !important;
        }
        
        /* A4 Page layout matching editor visual */
        .a4-page {
            background: white !important;
            width: 210mm !important;
            min-height: 297mm !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06), 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important;
            padding: 20mm !important;
            box-sizing: border-box !important;
            position: relative !important;
            border-left: 1.5px solid #cbd5e1 !important;
            border-right: 1.5px solid #cbd5e1 !important;
            word-wrap: break-word !important;
            text-align: left !important;
            color: black !important;
            font-size: 14px !important;
            line-height: 1.6 !important;
            
            /* Guideline gradient every 297mm */
            background-image: linear-gradient(to bottom, transparent 296.5mm, #cbd5e1 296.5mm, #cbd5e1 297mm) !important;
            background-size: 100% 297mm !important;
            background-repeat: repeat-y !important;
        }
        
        /* Page tag bottom-right */
        .a4-page::after {
            content: "Page " attr(data-page-num) !important;
            position: absolute !important;
            bottom: 15px !important;
            right: 20mm !important;
            font-size: 11px !important;
            color: #94a3b8 !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 500 !important;
        }
        
        /* Page break divider line */
        .a4-page-break {
            border-top: 2px dashed #7c3aed !important;
            margin-top: 10px !important;
            margin-bottom: 10px !important;
            position: relative !important;
            height: 2px !important;
            width: 210mm !important;
            display: block !important;
            clear: both !important;
        }
        
        .a4-page-break::before {
            content: "✂--- FORCED PAGE BREAK (A4) ---" !important;
            position: absolute !important;
            top: -10px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            background: #f1f5f9 !important;
            padding: 0 12px !important;
            font-size: 9px !important;
            color: #7c3aed !important;
            font-weight: 800 !important;
            letter-spacing: 1.5px !important;
            font-family: 'Inter', sans-serif !important;
            white-space: nowrap !important;
        }
        
        /* Scope conflict override for header elements */
        .header {
            height: auto !important;
            position: static !important;
            text-align: center !important;
            border-bottom: 2px solid #0056b3 !important;
            padding-bottom: 10px !important;
            margin-bottom: 30px !important;
            background: transparent !important;
            width: auto !important;
            display: block !important;
        }
    }
</style>
`;
                
                // JavaScript to parse content and dynamically distribute to pages in the preview
                const paginationScript = `
<script>
    (function() {
        function runPagination() {
            const originalBody = document.body;
            if (!originalBody || originalBody.dataset.paginated) return;
            originalBody.dataset.paginated = "true";
            
            const container = document.createElement('div');
            container.className = 'a4-preview-container';
            
            let currentPageNum = 1;
            let pages = [];
            
            function getOrCreatePage(num) {
                if (!pages[num - 1]) {
                    const page = document.createElement('div');
                    page.className = 'a4-page';
                    page.setAttribute('data-page-num', num);
                    pages[num - 1] = page;
                }
                return pages[num - 1];
            }
            
            function getMirrorParent(originalParent, activePage) {
                if (!originalParent || originalParent === originalBody) {
                    return activePage;
                }
                
                const path = [];
                let curr = originalParent;
                while (curr && curr !== originalBody) {
                    path.unshift(curr);
                    curr = curr.parentNode;
                }
                
                let currentTarget = activePage;
                path.forEach(origNode => {
                    let mirror = null;
                    for (let child of currentTarget.children) {
                        if (child.tagName === origNode.tagName && 
                            child.className === origNode.className && 
                            !child.dataset.finalized) {
                            mirror = child;
                            break;
                        }
                    }
                    if (!mirror) {
                        mirror = origNode.cloneNode(false);
                        currentTarget.appendChild(mirror);
                    }
                    currentTarget = mirror;
                });
                
                return currentTarget;
            }
            
            function processNode(node, parentInPage) {
                if (!node) return;
                
                if (node.nodeType === Node.ELEMENT_NODE) {
                    if (node.tagName === 'SCRIPT' || node.tagName === 'STYLE' || node.id === 'a4-preview-styles') {
                        return;
                    }
                }
                
                let hasPageBreak = false;
                if (node.nodeType === Node.ELEMENT_NODE) {
                    const styleAttr = node.getAttribute('style') || '';
                    hasPageBreak = styleAttr.includes('page-break-before: always') || 
                                   styleAttr.includes('page-break-before:always') ||
                                   node.style.pageBreakBefore === 'always';
                }
                
                if (hasPageBreak) {
                    currentPageNum++;
                }
                
                if (node.nodeType === Node.TEXT_NODE) {
                    const activePage = getOrCreatePage(currentPageNum);
                    const targetParent = getMirrorParent(parentInPage, activePage);
                    targetParent.appendChild(node.cloneNode(true));
                    return;
                }
                
                if (node.nodeType === Node.ELEMENT_NODE) {
                    const isTableOrRow = ['TABLE', 'TR', 'THEAD', 'TBODY', 'TH', 'TD', 'UL', 'OL', 'LI'].includes(node.tagName);
                    const isSpecialBlock = node.classList.contains('header') || 
                                           node.classList.contains('signature-section') ||
                                           node.classList.contains('details-table');
                    const isLeaf = node.childNodes.length === 0;
                    
                    if (isLeaf || isTableOrRow || isSpecialBlock) {
                        const activePage = getOrCreatePage(currentPageNum);
                        const targetParent = getMirrorParent(parentInPage, activePage);
                        targetParent.appendChild(node.cloneNode(true));
                        return;
                    }
                    
                    Array.from(node.childNodes).forEach(child => {
                        processNode(child, node);
                    });
                }
            }
            
            Array.from(originalBody.childNodes).forEach(child => {
                processNode(child, originalBody);
            });
            
            pages.forEach((page, index) => {
                if (index > 0) {
                    const pbIndicator = document.createElement('div');
                    pbIndicator.className = 'a4-page-break';
                    container.appendChild(pbIndicator);
                }
                container.appendChild(page);
            });
            
            originalBody.innerHTML = '';
            originalBody.appendChild(container);
        }
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', runPagination);
        } else {
            runPagination();
        }
    })();
</script>
`;
                
                if (html.includes('</head>')) {
                    html = html.replace('</head>', previewStyles + '</head>');
                } else {
                    html = previewStyles + html;
                }
                
                if (html.includes('</body>')) {
                    html = html.replace('</body>', paginationScript + '</body>');
                } else {
                    html = html + paginationScript;
                }
                
                iframe.srcdoc = html;
            }
        }
    } catch (e) {
        console.error(e);
    } finally {
        if (spinner) spinner.style.display = 'none';
    }
}

async function downloadCustomizedLetter() {
    if (!currentDetailEmployeeId || !activeLetterType) return;
    
    showToast(`Generating ${activeLetterType.toUpperCase()} PDF...`);
    
    const custom_context = {
        date: document.getElementById('custLetterDate').value,
        first_name: document.getElementById('custFirstName').value,
        last_name: document.getElementById('custLastName').value,
        designation: document.getElementById('custDesignation').value,
        joining_date: document.getElementById('custJoiningDate').value,
        notice_period_days: document.getElementById('custNoticePeriod').value,
        bond_period_months: document.getElementById('custBondPeriod').value,
        address_line1: document.getElementById('custAddress1').value,
        city: document.getElementById('custCity').value,
        state: document.getElementById('custState').value,
        company_name: document.getElementById('custCompanyName').value,
        company_address: document.getElementById('custCompanyAddress').value,
        signatory_name: document.getElementById('custSignatoryName').value,
        signatory_designation: document.getElementById('custSignatoryDesignation').value,
        
        ctc: document.getElementById('custCTC').value,
        in_hand: document.getElementById('custInHand').value,
        basic: document.getElementById('custBasic').value,
        hra: document.getElementById('custHra').value,
        conveyance: document.getElementById('custConveyance').value,
        medical: document.getElementById('custMedical').value,
        special: document.getElementById('custSpecial').value,
        monthly_bonus: document.getElementById('custBonus').value,
        esi_employer: document.getElementById('custEsiEmployer').value,
        pf_employer: document.getElementById('custPfEmployer').value,
        pf_employee: document.getElementById('custPfEmployee').value,
        esi_employee: document.getElementById('custEsiEmployee').value,
        lwf: document.getElementById('custLwf').value,
        professional_tax: document.getElementById('custPT').value,
    };
    
    try {
        const res = await apiFetch(`/employees/${currentDetailEmployeeId}/generate-${activeLetterType}-letter/`, {
            method: 'POST',
            body: JSON.stringify({
                custom_context: custom_context
            })
        });
        
        if (res.ok) {
            const data = await res.json();
            showToast(`${activeLetterType.toUpperCase()} generated and saved in history.`);
            loadProfileLettersList();
            
            if (data.document && data.document.file) {
                downloadSecureFile(data.document.file, `${activeLetterType}_letter.pdf`);
            }
        } else {
            const err = await res.json();
            showToast(err.error || 'Generation failed.', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Error generating PDF.', 'error');
    }
}

async function loadTemplatesList() {
    try {
        const res = await apiFetch('/onboarding/templates/');
        if (res.ok) {
            const data = await res.json();
            loadedTemplates = data.results || data;
            
            const selector = document.getElementById('templateSelector');
            if (selector) {
                selector.innerHTML = loadedTemplates.map(t => {
                    return `<option value="${t.id}">${t.title} (${t.name.replace('_', ' ')})</option>`;
                }).join('');
            }
            
            if (loadedTemplates.length > 0) {
                loadTemplateToEditor();
            }
        }
    } catch (e) {
        console.error(e);
    }
}

function loadTemplateToEditor() {
    const selector = document.getElementById('templateSelector');
    if (!selector) return;
    const selectedId = parseInt(selector.value);
    const template = loadedTemplates.find(t => t.id === selectedId);
    if (!template) return;
    
    const visualEditor = document.getElementById('visualTemplateEditor');
    if (visualEditor) {
        // Parse database HTML to strip outer html/head/body tags for editing
        const parser = new DOMParser();
        const doc = parser.parseFromString(template.html_content, 'text/html');
        
        let styles = '';
        doc.querySelectorAll('style').forEach(s => {
            styles += s.outerHTML;
        });
        
        const bodyContent = doc.body ? doc.body.innerHTML : template.html_content;
        visualEditor.innerHTML = styles + bodyContent;
    }
    
    const is_admin = currentUser && (currentUser.role === 'ADMIN');
    
    const allowHrContainer = document.getElementById('allowHrEditContainer');
    const allowHrCheckbox = document.getElementById('allowHrEditCheckbox');
    
    if (allowHrContainer && allowHrCheckbox) {
        if (is_admin) {
            allowHrContainer.style.display = 'flex';
            allowHrCheckbox.checked = template.allow_hr_edit;
            allowHrCheckbox.disabled = false;
        } else {
            allowHrContainer.style.display = 'none';
        }
    }
    
    const saveBtn = document.getElementById('saveTemplateBtn');
    const canEdit = is_admin || hasPermission('onboarding.manage_templates') || (template.allow_hr_edit && currentUser && currentUser.role === 'HR');
    
    if (visualEditor) {
        visualEditor.contentEditable = canEdit ? "true" : "false";
    }
    if (saveBtn) {
        saveBtn.disabled = !canEdit;
        saveBtn.innerText = canEdit ? 'Save Template changes' : 'Permission Denied (Read-Only)';
    }
}

async function saveTemplateChanges() {
    const selector = document.getElementById('templateSelector');
    if (!selector) return;
    const selectedId = parseInt(selector.value);
    const template = loadedTemplates.find(t => t.id === selectedId);
    if (!template) return;
    
    const visualEditor = document.getElementById('visualTemplateEditor');
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
    
    // Reconstruct valid full-page HTML template for WeasyPrint
    const fullHtml = `<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>${template.title || 'Letter Template'}</title>
    ${styles}
</head>
<body>
    ${bodyContent}
</body>
</html>`;

    const is_admin = currentUser && (currentUser.role === 'ADMIN');
    
    const payload = {
        html_content: fullHtml
    };
    
    if (is_admin) {
        payload.allow_hr_edit = document.getElementById('allowHrEditCheckbox').checked;
    }
    
    showToast('Saving template changes...');
    try {
        const res = await apiFetch(`/onboarding/templates/${selectedId}/`, {
            method: 'PATCH',
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            showToast('Template updated successfully!');
            const updated = await res.json();
            const index = loadedTemplates.findIndex(t => t.id === selectedId);
            if (index !== -1) {
                loadedTemplates[index] = updated;
            }
            loadTemplateToEditor();
        } else {
            const err = await res.json();
            showToast(err.detail || err.error || 'Failed to update template', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Error saving template.', 'error');
    }
}

function execEditorCommand(command) {
    document.execCommand(command, false, null);
    const visualEditor = document.getElementById('visualTemplateEditor');
    if (visualEditor) {
        visualEditor.focus();
    }
}

function insertPlaceholderAtCursor(placeholder) {
    if (!placeholder) return;
    const visualEditor = document.getElementById('visualTemplateEditor');
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


async function loadProfileLettersList() {
    if (!currentDetailEmployeeId) return;
    try {
        closeLetterWorkspace();
        
        const isAdmin = currentUser && (currentUser.role_code === 'ADMIN' || currentUser.role === 'ADMIN' || currentUser.is_superuser);
        const hasGenPerm = hasPermission('onboarding.generate_letters');
        const hasTemplatePerm = hasPermission('onboarding.manage_templates');
        
        if (isAdmin || hasGenPerm) {
            switchLettersSubTab('generate');
        } else if (hasTemplatePerm) {
            switchLettersSubTab('template');
        }
        
        const res = await apiFetch(`/onboarding/documents/?employee_id=${currentDetailEmployeeId}`);
        if (res.ok) {
            const docs = await res.json();
            const docList = docs.results || docs;
            
            const letterTypes = ['OFFER_LETTER', 'APPOINTMENT_LETTER', 'BOND_LETTER'];
            const letters = docList.filter(d => letterTypes.includes(d.doc_type));
            
            document.getElementById('bondLetterCardContainer').style.display = 'block';

            const tbody = document.getElementById('profileLettersTableBody');
            if (tbody) {
                if (letters.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:15px;">No letters generated yet.</td></tr>`;
                    return;
                }
                
                tbody.innerHTML = letters.map(l => {
                    return `
                        <tr>
                            <td><strong>${l.doc_type.replace('_', ' ')}</strong></td>
                            <td>${formatSimpleDate(l.upload_date)}</td>
                            <td>${l.uploaded_by_username || 'System'}</td>
                            <td style="text-align:center;">
                                <button class="btn btn-primary" style="font-size:7.5pt; padding:4px 8px;" onclick="downloadSecureFile('${l.file}', '${l.doc_type.toLowerCase()}_${currentDetailEmployeeId}.pdf')">Download PDF</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
    } catch (e) {
        console.error(e);
    }
}

// ---------- TAB 5: AUDIT LOG LIST ----------
async function loadProfileAuditLog() {
    if (!currentDetailEmployeeId) return;
    try {
        const res = await apiFetch(`/logs/?object_id=${currentDetailEmployeeId}&model_name=Employee`);
        if (res.ok) {
            const logs = await res.json();
            const logList = logs.results || logs;
            const tbody = document.getElementById('profileAuditTableBody');
            
            if (tbody) {
                if (logList.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:15px;">No audit logs recorded for this employee profile yet.</td></tr>`;
                    return;
                }
                
                tbody.innerHTML = logList.map(l => {
                    const actorName = l.actor_username || 'System';
                    return `
                        <tr>
                            <td><span style="font-weight:bold; color:var(--primary-color);">${l.action}</span></td>
                            <td style="font-size:9pt; line-height:1.4;">${l.description}</td>
                            <td style="white-space:nowrap;">${formatDate(l.timestamp)}</td>
                            <td>${actorName}</td>
                        </tr>
                    `;
                }).join('');
            }
        }
    } catch (e) {
        console.error(e);
    }
}

// ---------- MODAL 1: EXCEL BULK IMPORT SUBMIT ----------
function openExcelImportModal() {
    document.getElementById('excelImportModal').style.display = 'flex';
}

function closeExcelImportModal() {
    document.getElementById('excelImportModal').style.display = 'none';
    document.getElementById('excelImportForm').reset();
}

document.addEventListener('DOMContentLoaded', () => {
    const importForm = document.getElementById('excelImportForm');
    if (importForm) {
        importForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('excelImportFile');
            const file = fileInput.files[0];
            if (!file) return;

            showToast('Uploading Excel and running validation...');
            const formData = new FormData();
            formData.append('file', file);

            try {
                const res = await apiFetch('/employees/import-excel/', {
                    method: 'POST',
                    body: formData
                });

                if (res.status === 201) {
                    const data = await res.json();
                    showToast(data.message || 'Import successful!');
                    closeExcelImportModal();
                    loadFilteredEmployeeData();
                } else if (res.status === 200 || res.headers.get('Content-Type') === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') {
                    showToast('Validation failed. Downloading error report...', 'error');
                    const blob = await res.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `import_validation_errors_${new Date().toISOString().slice(0,10)}.xlsx`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                } else {
                    const err = await res.json();
                    showToast('Import failed: ' + (err.error || JSON.stringify(err)), 'error');
                }
            } catch (ex) {
                console.error(ex);
                showToast('Import query error.', 'error');
            }
        });
    }
});

// ---------- HELPERS ----------
function formatSimpleDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    });
}

async function softDeleteEmployee(empId) {
    if (!confirm('Are you sure you want to soft delete this employee profile?')) return;
    try {
        const res = await apiFetch(`/employees/${empId}/`, {
            method: 'DELETE'
        });
        if (res.status === 204) {
            showToast('Employee profile deleted.');
            switchView('onboardingView');
            loadFilteredEmployeeData();
        } else {
            showToast('Failed to delete.', 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

function deleteCurrentEmployee() {
    if (currentDetailEmployeeId) {
        softDeleteEmployee(currentDetailEmployeeId);
    }
}
