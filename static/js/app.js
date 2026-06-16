// static/js/app.js
// Central client-side logic for the MTVL HR Portal V2.0

const API_BASE = '/api';
let currentUser = null;

// ---------- JWT & API HELPER ----------
async function apiFetch(endpoint, options = {}) {
    let accessToken = localStorage.getItem('accessToken');
    
    // Set default headers
    options.headers = options.headers || {};
    options.headers['Accept'] = 'application/json';
    options.headers['X-Requested-With'] = 'XMLHttpRequest';
    if (accessToken) {
        options.headers['Authorization'] = `Bearer ${accessToken}`;
    }
    
    // Add CSRF Token if post/put/delete
    const csrfToken = getCookie('csrftoken');
    if (csrfToken && options.method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method.toUpperCase())) {
        options.headers['X-CSRFToken'] = csrfToken;
    }

    if (!(options.body instanceof FormData)) {
        options.headers['Content-Type'] = options.headers['Content-Type'] || 'application/json';
    }

    let url;
    if (endpoint.startsWith('http')) {
        url = endpoint;
    } else if (
        endpoint.startsWith('/dashboard') ||
        endpoint.startsWith('/employees') ||
        endpoint.startsWith('/salaries') ||
        endpoint.startsWith('/exits') ||
        endpoint.startsWith('/students') ||
        endpoint.startsWith('/logs') ||
        endpoint.startsWith('/roles')
    ) {
        url = endpoint;
    } else {
        url = `${API_BASE}${endpoint}`;
    }
    let response = await fetch(url, options);

    // Handle token expiration (401 Unauthorized)
    if (response.status === 401) {
        const refreshToken = localStorage.getItem('refreshToken');
        if (refreshToken) {
            console.log('Access token expired. Attempting token refresh...');
            const refreshSuccess = await attemptTokenRefresh(refreshToken);
            if (refreshSuccess) {
                // Retry request with new token
                accessToken = localStorage.getItem('accessToken');
                options.headers['Authorization'] = `Bearer ${accessToken}`;
                response = await fetch(url, options);
            } else {
                logout();
                return response;
            }
        } else {
            logout();
            return response;
        }
    }

    return response;
}

async function attemptTokenRefresh(refreshToken) {
    try {
        const response = await fetch(`${API_BASE}/auth/refresh/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh: refreshToken })
        });
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('accessToken', data.access);
            if (data.refresh) {
                localStorage.setItem('refreshToken', data.refresh);
            }
            return true;
        }
    } catch (e) {
        console.error('Token refresh failed:', e);
    }
    return false;
}

function logout() {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    window.location.href = '/login/';
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ---------- UI TOAST NOTIFICATION ----------
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type} show`;
    toast.innerHTML = `
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ---------- SPA ROUTER ----------
const viewToPath = {
    'dashboardView': '/dashboard/',
    'onboardingView': '/employees/',
    'onboardingFormView': '/employees/onboard/',
    'employeeDetailView': '/employees/detail/',
    'salaryView': '/salaries/',
    'salaryHistoryView': '/salaries/employee/',
    'exitView': '/exits/',
    'studentView': '/students/',
    'logsView': '/logs/',
    'rolesView': '/roles/'
};

const pathToView = {
    '/': 'dashboardView',
    '/dashboard/': 'dashboardView',
    '/employees/': 'onboardingView',
    '/employees/onboard/': 'onboardingFormView',
    '/employees/detail/': 'employeeDetailView',
    '/salaries/': 'salaryView',
    '/exits/': 'exitView',
    '/students/': 'studentView',
    '/logs/': 'logsView',
    '/roles/': 'rolesView'
};

const views = [
    'dashboardView',
    'onboardingView',
    'onboardingFormView',
    'employeeDetailView',
    'salaryView',
    'salaryHistoryView',
    'exitView',
    'studentView',
    'logsView',
    'rolesView'
];

function getEmployeeIdFromUrl() {
    const match = window.location.pathname.match(/\/salaries\/employee\/(\d+)\/?/);
    return match ? parseInt(match[1]) : null;
}

function switchView(viewId, pushState = true, extraParams = {}) {
    views.forEach(v => {
        const el = document.getElementById(v);
        if (el) el.style.display = v === viewId ? 'block' : 'none';
    });

    // Update sidebar active classes
    const links = document.querySelectorAll('.sidebar-link');
    links.forEach(l => {
        l.classList.remove('active');
        if (l.getAttribute('data-view') === viewId) {
            l.classList.add('active');
        }
    });

    // Load dynamic data based on view
    if (viewId === 'dashboardView') loadDashboardData();
    else if (viewId === 'onboardingView') loadOnboardingData();
    else if (viewId === 'onboardingFormView') loadOnboardingFormPage();
    else if (viewId === 'salaryView') loadSalaryData();
    else if (viewId === 'salaryHistoryView') {
        const empId = extraParams.employeeId || getEmployeeIdFromUrl();
        if (empId) {
            loadDedicatedEmployeeSalaryHistory(empId);
        }
    }
    else if (viewId === 'exitView') loadExitData();
    else if (viewId === 'studentView') loadStudentData();
    else if (viewId === 'logsView') loadLogsData();
    else if (viewId === 'rolesView') loadRolesData();

    // Update URL without page reload
    if (pushState) {
        let path = viewToPath[viewId] || '/';
        if (viewId === 'salaryHistoryView' && extraParams.employeeId) {
            path = `/salaries/employee/${extraParams.employeeId}/`;
        }
        history.pushState({ viewId: viewId, employeeId: extraParams.employeeId || null }, '', path);
    }
}

// Handle browser Back/Forward navigation
window.addEventListener('popstate', (event) => {
    if (event.state && event.state.viewId) {
        switchView(event.state.viewId, false, { employeeId: event.state.employeeId });
    } else {
        let viewId = 'dashboardView';
        if (window.location.pathname.match(/\/salaries\/employee\/(\d+)\/?/)) {
            viewId = 'salaryHistoryView';
        } else {
            viewId = pathToView[window.location.pathname] || 'dashboardView';
        }
        switchView(viewId, false);
    }
});

// ---------- NOTIFICATIONS FEED ----------
async function checkNotifications() {
    if (!localStorage.getItem('accessToken')) return;

    try {
        const res = await apiFetch('/notifications/feed/');
        if (res.ok) {
            const data = await res.json();
            const notifications = data.results || data;
            const unread = notifications.filter(n => !n.is_read);
            
            // Update Bell Badge
            const badge = document.getElementById('notifBadge');
            if (badge) {
                if (unread.length > 0) {
                    badge.textContent = unread.length;
                    badge.style.display = 'block';
                } else {
                    badge.style.display = 'none';
                }
            }

            // Populate Panel
            const listContainer = document.getElementById('notifList');
            if (listContainer) {
                if (notifications.length === 0) {
                    listContainer.innerHTML = '<div class="notif-empty">No notifications yet</div>';
                    return;
                }

                listContainer.innerHTML = notifications.map(n => `
                    <div class="notif-item ${n.is_read ? '' : 'unread'}" onclick="markNotifRead(${n.id}, '${n.link || '#'}')">
                        <div class="notif-text">${n.message}</div>
                        <div class="notif-time">${formatDate(n.created_at)}</div>
                    </div>
                `).join('');
            }
        }
    } catch (e) {
        console.error('Error fetching notifications:', e);
    }
}

async function markNotifRead(id, redirectUrl) {
    try {
        await apiFetch(`/notifications/feed/${id}/mark-read/`, { method: 'POST' });
        checkNotifications();
        if (redirectUrl && redirectUrl !== '#') {
            // If SPA link
            if (redirectUrl.startsWith('/')) {
                // Determine view
                if (redirectUrl.includes('students')) switchView('studentView');
                else if (redirectUrl.includes('salary')) switchView('salaryView');
                else if (redirectUrl.includes('exit')) switchView('exitView');
            } else {
                window.location.href = redirectUrl;
            }
        }
    } catch (e) {
        console.error(e);
    }
}

async function markAllNotifsRead() {
    try {
        const res = await apiFetch('/notifications/feed/mark-all-read/', { method: 'POST' });
        if (res.ok) {
            showToast('All notifications marked as read.');
            checkNotifications();
        }
    } catch (e) {
        console.error(e);
    }
}

// ---------- HELPERS ----------
function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}
