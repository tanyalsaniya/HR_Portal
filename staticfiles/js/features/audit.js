// static/js/features/audit.js
// Central controller for Admin Audit Logs & Activity Trails (Simplified V2)

let logsCurrentPage = 1;
let logsPageSize = 12;
let currentLogsList = [];

// ---------- INITIAL LOAD ----------

async function loadLogsData() {
    document.getElementById('pageTitle').textContent = 'System Audit Logs';
    logsCurrentPage = 1;
    await fetchLogsWithParams();
}

// ---------- FETCH LOGS DATA ----------

async function fetchLogsWithParams() {
    const params = new URLSearchParams({
        page: logsCurrentPage,
        page_size: logsPageSize
    });
    
    try {
        const res = await apiFetch(`/api/audit/logs/?${params.toString()}`);
        if (res.ok) {
            const data = await res.json();
            const results = data.results || data;
            currentLogsList = results;
            
            const tbody = document.getElementById('logsTableBody');
            if (tbody) {
                if (results.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:30px; color:#64748b;">No activities logged for today.</td></tr>';
                    updatePaginationUI(0, 0, 0);
                    return;
                }
                
                tbody.innerHTML = results.map((l) => {
                    return `
                        <tr>
                            <td style="padding-left: 20px;">${formatDate(l.timestamp)}</td>
                            <td><strong>${l.actor_username || l.user_name || 'System'}</strong></td>
                            <td>${l.actor_role || l.user_role || 'N/A'}</td>
                            <td><code>${l.ip_address || 'N/A'}</code></td>
                            <td><strong>${l.action}</strong></td>
                            <td style="padding-right: 20px;">${l.description}</td>
                        </tr>
                    `;
                }).join('');
            }
            
            // Calculate ranges
            const count = data.count || results.length;
            const startRange = (logsCurrentPage - 1) * logsPageSize + 1;
            const endRange = Math.min(logsCurrentPage * logsPageSize, count);
            updatePaginationUI(count, startRange, endRange);
        } else {
            showToast('Failed to fetch activity logs.', 'error');
        }
    } catch (e) {
        console.error('Error fetching activity logs:', e);
        showToast('Error connecting to audit logs API.', 'error');
    }
}

function updatePaginationUI(total, start, end) {
    const summary = document.getElementById('logsPaginationSummary');
    if (summary) {
        summary.textContent = total > 0 ? `Showing ${start} to ${end} of ${total} activities` : 'Showing 0 to 0 of 0 activities';
    }
    
    const btnPrev = document.getElementById('btnPrevLogsPage');
    const btnNext = document.getElementById('btnNextLogsPage');
    const pageNumSpan = document.getElementById('logsCurrentPageNumber');
    
    if (pageNumSpan) pageNumSpan.textContent = logsCurrentPage;
    
    if (btnPrev) btnPrev.disabled = logsCurrentPage <= 1;
    if (btnNext) btnNext.disabled = end >= total;
}

// ---------- PAGINATION ACTIONS ----------

function prevLogsPage() {
    if (logsCurrentPage > 1) {
        logsCurrentPage--;
        fetchLogsWithParams();
    }
}

function nextLogsPage() {
    logsCurrentPage++;
    fetchLogsWithParams();
}

// ---------- EXPORT LOGS ----------

function exportAuditLogs(format) {
    const params = new URLSearchParams({
        export_format: format
    });
    
    const token = localStorage.getItem('accessToken');
    if (token) {
        params.append('token', token);
    }
    
    // Redirect browser to download file
    window.open(`/api/audit/logs/export/?${params.toString()}`, '_blank');
}
