// static/js/features/audit.js
// Audit logs loading

// ---------- AUDIT LOGS VIEW ----------
async function loadLogsData() {
    document.getElementById('pageTitle').textContent = 'System Audit Logs';
    try {
        const res = await apiFetch('/logs/');
        if (res.ok) {
            const logs = await res.json();
            const logsList = logs.results || logs;
            const tbody = document.getElementById('logsTableBody');
            
            if (tbody) {
                tbody.innerHTML = logsList.map(l => `
                    <tr>
                        <td>${formatDate(l.timestamp)}</td>
                        <td>${l.actor_username || 'System'}</td>
                        <td>${l.action}</td>
                        <td>${l.model_name}</td>
                        <td>${l.object_id || 'N/A'}</td>
                        <td>${l.description}</td>
                    </tr>
                `).join('');
            }
        }
    } catch (e) {
        console.error(e);
    }
}
