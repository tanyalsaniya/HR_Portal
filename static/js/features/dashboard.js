// static/js/features/dashboard.js
// Clean Professional Dashboard — metric loading, animations, breakdown bars, activity feed

// ── Animate a numeric counter from 0 to target ──
function animateCounter(el, target, duration = 850) {
    if (!el) return;
    const start = performance.now();
    const update = (now) => {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        el.textContent = Math.round(target * eased);
        if (progress < 1) requestAnimationFrame(update);
    };
    requestAnimationFrame(update);
}

// ── Animate a progress bar width ──
function animateBar(barId, pct, delay = 0) {
    setTimeout(() => {
        const el = document.getElementById(barId);
        if (el) el.style.width = Math.max(pct, pct > 0 ? 4 : 0) + '%';
    }, delay);
}

// ── Update workforce breakdown bars ──
function updateBreakdownBars(employees, students, exits) {
    const total = Math.max(employees + students + exits, 1);

    const ePct = (employees / total) * 100;
    const sPct = (students / total) * 100;
    const xPct = (exits   / total) * 100;

    const brkE = document.getElementById('brkEmployees');
    const brkS = document.getElementById('brkStudents');
    const brkX = document.getElementById('brkExits');
    if (brkE) brkE.textContent = employees;
    if (brkS) brkS.textContent = students;
    if (brkX) brkX.textContent = exits;

    animateBar('barEmployees', ePct, 300);
    animateBar('barStudents',  sPct, 420);
    animateBar('barExits',     xPct, 540);
}

// ── Render the activity feed ──
function renderActivityFeed(logs) {
    const body = document.getElementById('dashboardRecentLogsBody');
    if (!body) return;

    if (!logs || logs.length === 0) {
        body.innerHTML = `
            <div class="db-empty-state">
                <svg width="32" height="32" fill="none" stroke="#cbd5e1" stroke-width="1.5" viewBox="0 0 24 24">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                </svg>
                <div class="db-empty-text">No recent activity found.</div>
            </div>`;
        return;
    }

    const iconMap = {
        'CREATE': { cls: 'dot-create', symbol: '✦' },
        'UPDATE': { cls: 'dot-update', symbol: '✎' },
        'DELETE': { cls: 'dot-delete', symbol: '✕' },
    };

    body.innerHTML = logs.map(l => {
        const key  = (l.action || '').toUpperCase();
        const meta = iconMap[key] || { cls: 'dot-default', symbol: '·' };
        const timeStr = formatRelativeTime(l.timestamp);
        const actor   = l.actor_username || 'System';
        const model   = l.model_name || '';
        return `
        <div class="db-activity-item">
            <div class="db-activity-dot ${meta.cls}">${meta.symbol}</div>
            <div class="db-activity-content">
                <div class="db-activity-desc">${l.description || '—'}</div>
                <div class="db-activity-meta">
                    <span class="db-actor-chip">
                        <svg width="9" height="9" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                            <circle cx="12" cy="7" r="4"/>
                        </svg>
                        ${actor}
                    </span>
                    <span>${timeStr}</span>
                    ${model ? `<span style="opacity:0.5">·</span><span>${model}</span>` : ''}
                </div>
            </div>
        </div>`;
    }).join('');
}

// ── Relative time helper ──
function formatRelativeTime(iso) {
    if (!iso) return '—';
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1)  return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24)  return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
}

// ── Live clock & greeting ──
function updateDashboardClock() {
    const now  = new Date();
    const timeEl  = document.getElementById('dbCurrentTime');
    const dateEl  = document.getElementById('dbCurrentDate');
    const greetEl = document.getElementById('dbWelcomeTitle');

    if (timeEl) {
        timeEl.textContent = now.toLocaleTimeString('en-US', {
            hour: '2-digit', minute: '2-digit', hour12: true
        });
    }
    if (dateEl) {
        dateEl.textContent = now.toLocaleDateString('en-US', {
            weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'
        });
    }
    if (greetEl) {
        const h = now.getHours();
        greetEl.textContent =
            h < 12 ? 'Good morning' :
            h < 17 ? 'Good afternoon' :
                     'Good evening';
    }
}

// ── Main Load Function ──
async function loadDashboardData() {
    document.getElementById('pageTitle').textContent = 'Dashboard';

    // Start live clock
    updateDashboardClock();
    if (window._dbClockInterval) clearInterval(window._dbClockInterval);
    window._dbClockInterval = setInterval(updateDashboardClock, 1000);

    try {
        const res = await apiFetch('/dashboard/');
        if (!res.ok) {
            showToast('Failed to load dashboard data.', 'error');
            return;
        }
        const data = await res.json();

        const totalEmp    = data.total_employees    || 0;
        const activeEmp   = data.active_employees   || 0;
        const activeStud  = data.active_students    || 0;
        const pendingExit = data.pending_exits      || 0;
        const increments  = data.anniversaries_count || 0;

        // Animate stat counters
        animateCounter(document.getElementById('statTotalEmployees'),    totalEmp);
        animateCounter(document.getElementById('statActiveEmployees'),   activeEmp);
        animateCounter(document.getElementById('statActiveStudents'),    activeStud);
        animateCounter(document.getElementById('statPendingExits'),      pendingExit);
        animateCounter(document.getElementById('statAnniversaries'),     increments);

        // Pending exits tag colour
        const exitTag = document.getElementById('dbExitTag');
        if (exitTag && pendingExit === 0) {
            exitTag.textContent = 'All Clear';
            exitTag.className = 'db-stat-tag db-tag-positive';
        }

        // Breakdown bars
        setTimeout(() => updateBreakdownBars(totalEmp, activeStud, pendingExit), 250);

        // Activity feed
        const body = document.getElementById('dashboardRecentLogsBody');
        if (typeof hasPermission === 'function' && hasPermission('audit.read')) {
            renderActivityFeed(data.recent_logs || []);
        } else if (body) {
            body.innerHTML = `
                <div class="db-empty-state">
                    <svg width="32" height="32" fill="none" stroke="#cbd5e1" stroke-width="1.5" viewBox="0 0 24 24">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                        <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                    </svg>
                    <div class="db-empty-text">Audit logs are visible to administrators only.</div>
                </div>`;
        }

    } catch (e) {
        console.error('Dashboard load error:', e);
        showToast('Error loading dashboard.', 'error');
    }
}
