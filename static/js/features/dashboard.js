// static/js/features/dashboard.js
// Dashboard metric loading operations

// Load Dashboard details
async function loadDashboardData() {
    document.getElementById('pageTitle').textContent = 'Dashboard Overview';
    try {
        const res = await apiFetch('/dashboard/');
        if (res.ok) {
            const data = await res.json();
            
            // Update stats counters
            document.getElementById('statTotalEmployees').textContent = data.total_employees;
            document.getElementById('statActiveEmployees').textContent = data.active_employees;
            document.getElementById('statActiveStudents').textContent = data.active_students;
            document.getElementById('statPendingExits').textContent = data.pending_exits;
            document.getElementById('statAnniversaries').textContent = data.anniversaries_count;

            // Update recent logs feed
            const body = document.getElementById('dashboardRecentLogsBody');
            if (body) {
                if (hasPermission('audit.read')) {
                    const logsList = data.recent_logs;
                    if (logsList && logsList.length > 0) {
                        body.innerHTML = logsList.map(l => `
                            <tr>
                                <td>${formatDate(l.timestamp)}</td>
                                <td>${l.actor_username || 'System'}</td>
                                <td>${l.action}</td>
                                <td>${l.model_name}</td>
                                <td>${l.description}</td>
                            </tr>
                        `).join('');
                    } else {
                        body.innerHTML = `<tr><td colspan="5" style="text-align: center;">No operational logs found.</td></tr>`;
                    }
                } else {
                    body.innerHTML = `<tr><td colspan="5" style="text-align: center;">Recent operational logs are only visible to authorized administrators.</td></tr>`;
                }
            }
        } else {
            showToast('Failed to load dashboard data.', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Failed to load dashboard data.', 'error');
    }
}
