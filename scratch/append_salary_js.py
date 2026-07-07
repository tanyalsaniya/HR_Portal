import os

code = """
// -- DISMISSED EMPLOYEES TAB LOGIC --
let dismissedCurrentPage = 1;
let dismissedTotalCount = 0;
let dismissedFilteredList = [];

async function loadDismissedSlipsRegistry() {
    const tbody = document.getElementById('dismissedSlipsTableBody');
    if (!tbody) return;

    const role = currentUser.role;
    if (role === 'EMPLOYEE') return; // Employees don't see this

    const paginationFooter = document.getElementById('dismissedSlipsPaginationFooter');

    try {
        const res = await apiFetch('/salary/dismissed/history?no_pagination=true');
        if (res.ok) {
            const slipsData = await res.json();
            dismissedFilteredList = slipsData.results || slipsData;
            dismissedTotalCount = dismissedFilteredList.length;

            if (paginationFooter) {
                paginationFooter.style.display = 'flex';
                updateDismissedPaginationControls(dismissedCurrentPage, dismissedTotalCount);
            }

            if (dismissedFilteredList.length === 0) {
                tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: #777; padding: 20px;">No dismissed employee salary slips generated yet.</td></tr>`;
                return;
            }

            const startIdx = (dismissedCurrentPage - 1) * 10;
            const paginatedSlips = dismissedFilteredList.slice(startIdx, startIdx + 10);

            tbody.innerHTML = paginatedSlips.map(s => {
                const monthNames = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                const period = `${monthNames[s.month]} ${s.year}`;
                
                const actions = `
                    <div style="display:flex; gap:5px;">
                        <button class="btn btn-primary" style="font-size:8pt; padding:4px 8px; background-color:#7c3aed;" onclick="downloadDismissedSlipSingle(${s.employee_id}, ${s.month}, ${s.year})">Download PDF</button>
                    </div>
                `;

                return `
                    <tr>
                        <td><strong>${s.employee_name || 'Ex-Employee'}</strong></td>
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
}

function changeDismissedPage(dir) {
    const totalPages = Math.ceil(dismissedTotalCount / 10);
    const newPage = dismissedCurrentPage + dir;
    if (newPage >= 1 && newPage <= totalPages) {
        dismissedCurrentPage = newPage;
        loadDismissedSlipsRegistry(); // Re-render with new slice
    }
}

function updateDismissedPaginationControls(currentPage, totalCount) {
    const prevBtn = document.getElementById('dismissedPrevBtn');
    const nextBtn = document.getElementById('dismissedNextBtn');
    const pageStart = document.getElementById('dismissedPageStart');
    const pageEnd = document.getElementById('dismissedPageEnd');
    const countEl = document.getElementById('dismissedTotalCount');

    if (!prevBtn || !nextBtn) return;

    const totalPages = Math.ceil(totalCount / 10);
    
    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages || totalPages === 0;

    const start = totalCount === 0 ? 0 : ((currentPage - 1) * 10) + 1;
    let end = currentPage * 10;
    if (end > totalCount) end = totalCount;

    if (pageStart) pageStart.textContent = start;
    if (pageEnd) pageEnd.textContent = end;
    if (countEl) countEl.textContent = totalCount;
}

function downloadDismissedSlipSingle(employeeId, month, year) {
    const token = localStorage.getItem('accessToken');
    fetch(`/api/salary/dismissed/slip/download?type=single&employee_id=${employeeId}&month=${month}&year=${year}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Download failed');
        return response.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `payslip_dismissed_${month}_${year}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
    })
    .catch(err => {
        showToast('Error downloading slip: ' + err.message, 'error');
    });
}

function downloadDismissedSlipBulk() {
    const month = document.getElementById('payrollMonth').value;
    const year = document.getElementById('payrollYear').value;
    const token = localStorage.getItem('accessToken');
    
    showToast('Preparing ZIP download...');
    
    fetch(`/api/salary/dismissed/slip/download?type=bulk_month&month=${month}&year=${year}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Download failed');
        return response.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dismissed_payslips_bulk_${month}_${year}.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('ZIP downloaded successfully.');
    })
    .catch(err => {
        showToast('Error downloading ZIP: ' + err.message, 'error');
    });
}
"""

with open('static/js/features/salary.js', 'a', encoding='utf-8') as f:
    f.write(code)
