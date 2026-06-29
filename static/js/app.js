// static/js/app.js
// Central client-side logic for the MTVL HR Portal V2.0
console.log('HR Portal V2.0 - app.js loaded');
const API_BASE = '/api';
let currentUser = null;

// ---------- GLOBAL LOADER SYSTEM ----------
let activeRequestsCount = 0;
let loaderTimeout = null;

function showGlobalLoader(isBlocking = false) {
    const bar = document.getElementById('globalLoadingBar');
    const overlay = document.getElementById('globalLoaderOverlay');
    
    if (bar) {
        bar.classList.remove('finished');
        bar.classList.add('loading');
        bar.style.width = '15%';
        setTimeout(() => {
            if (bar.classList.contains('loading')) {
                bar.style.width = '80%';
            }
        }, 50);
    }
    
    if (isBlocking && overlay) {
        if (loaderTimeout) clearTimeout(loaderTimeout);
        loaderTimeout = setTimeout(() => {
            overlay.classList.add('show');
        }, 150);
    }
}

function hideGlobalLoader() {
    const bar = document.getElementById('globalLoadingBar');
    const overlay = document.getElementById('globalLoaderOverlay');
    
    if (loaderTimeout) clearTimeout(loaderTimeout);
    
    if (bar) {
        bar.classList.remove('loading');
        bar.classList.add('finished');
    }
    
    if (overlay) {
        overlay.classList.remove('show');
    }
}

// ---------- JWT & API HELPER ----------
async function apiFetch(endpoint, options = {}) {
    let accessToken = localStorage.getItem('accessToken');
    
    // Determine if request is silent (notifications check)
    const isSilent = endpoint.includes('/notifications/feed/');
    if (!isSilent) {
        activeRequestsCount++;
        // If it's a write action, make it blocking
        const isWrite = options.method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method.toUpperCase());
        showGlobalLoader(isWrite);
    }
    
    // Set default headers
    options.headers = options.headers || {};
    options.headers['Accept'] = 'application/json';
    options.headers['X-Requested-With'] = 'XMLHttpRequest';
    options.headers['ngrok-skip-browser-warning'] = '69420';
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
        endpoint.startsWith('/api') ||
        endpoint.startsWith('/dashboard') ||
        endpoint.startsWith('/employees') ||
        endpoint.startsWith('/salaries') ||
        endpoint.startsWith('/exits') ||
        endpoint.startsWith('/students') ||
        endpoint.startsWith('/logs') ||
        endpoint.startsWith('/roles') ||
        endpoint.startsWith('/media') ||
        endpoint.startsWith('/static')
    ) {
        url = endpoint;
    } else {
        url = `${API_BASE}${endpoint}`;
    }

    try {
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
    } finally {
        if (!isSilent) {
            activeRequestsCount--;
            if (activeRequestsCount <= 0) {
                activeRequestsCount = 0;
                hideGlobalLoader();
            }
        }
    }
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

async function logout() {
    try {
        await apiFetch('/auth/logout/', { method: 'POST' });
    } catch (e) {
        console.error('Logout error:', e);
    }
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
// NOTE: showToast is fully defined by alerts.js (loaded before app.js).
// This stub provides a safe fallback in case alerts.js hasn't executed yet.
if (typeof window.showToast !== 'function') {
    window.showToast = function (message, type = 'success') {
        console.warn('[HR Portal] alerts.js not loaded yet — fallback toast:', type, message);
        // Minimal fallback: log only. alerts.js will override this.
    };
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
    'exitDetailView': '/exits/detail/',
    'studentView': '/students/',
    'studentDetailView': '/students/detail/',
    'logsView': '/logs/',
    'rolesView': '/roles/',
    'probationView': '/probation/'
};

const pathToView = {
    '/': 'dashboardView',
    '/dashboard/': 'dashboardView',
    '/employees/': 'onboardingView',
    '/employees/onboarding/': 'onboardingView',
    '/employees/active/': 'onboardingView',
    '/employees/offboarding/': 'onboardingView',
    '/employees/dismissed/': 'onboardingView',
    '/employees/onboard/': 'onboardingFormView',
    '/employees/detail/': 'employeeDetailView',
    '/salaries/': 'salaryView',
    '/exits/': 'exitView',
    '/exits/detail/': 'exitDetailView',
    '/exits/clearances/': 'exitDetailView',
    '/exits/documents/': 'exitDetailView',
    '/exits/form/': 'exitDetailView',
    '/students/': 'studentView',
    '/students/detail/': 'studentDetailView',
    '/logs/': 'logsView',
    '/roles/': 'rolesView',
    '/probation/': 'probationView'
};

const views = [
    'dashboardView',
    'onboardingView',
    'onboardingFormView',
    'employeeDetailView',
    'salaryView',
    'salaryHistoryView',
    'exitView',
    'exitDetailView',
    'studentView',
    'studentDetailView',
    'logsView',
    'rolesView',
    'exitLetterWorkspace',
    'exitTemplateEditor',
    'probationView'
];

function getEmployeeIdFromUrl() {
    const match = window.location.pathname.match(/\/salaries\/employee\/(\d+)\/?/);
    return match ? parseInt(match[1]) : null;
}

function getEmployeeDetailIdFromUrl() {
    const match = window.location.pathname.match(/^\/employees\/([A-Za-z0-9\-]+)\/?$/);
    if (match && ['onboard', 'onboarding', 'active', 'offboarding', 'dismissed', 'detail'].includes(match[1])) {
        return null;
    }
    return match ? match[1] : null;
}

function getExitIdFromUrl() {
    // Matches /exits/123/ or /exits/123/clearances/ or /exits/123/documents/ or /exits/123/form/
    const match = window.location.pathname.match(/^\/exits\/(\d+)(\/|\/(clearances|documents|form)\/)?$/);
    return match ? parseInt(match[1]) : null;
}

function getStudentIdFromUrl() {
    const match = window.location.pathname.match(/^\/students\/([A-Za-z0-9\-]+)\/?$/);
    return match ? match[1] : null;
}

function switchView(viewId, pushState = true, extraParams = {}) {
    showGlobalLoader(false);

    const targetView = document.getElementById(viewId);
    if (!targetView) {
        console.warn(`View "${viewId}" was not found in the page.`);
        showToast('This page section is not loaded. Please refresh the page.', 'error');
        hideGlobalLoader();
        return;
    }

    views.forEach(v => {
        const el = document.getElementById(v);
        if (el) el.style.display = v === viewId ? 'block' : 'none';
    });

    // Update sidebar active classes
    const links = document.querySelectorAll('.sidebar-link');
    // Sub-views should highlight the parent sidebar item
    const salarySubViews = ['salaryHistoryView'];
    const onboardingSubViews = ['employeeDetailView', 'onboardingFormView'];
    const studentSubViews = ['studentDetailView'];
    
    let effectiveSidebarView = viewId;
    if (salarySubViews.includes(viewId)) effectiveSidebarView = 'salaryView';
    if (onboardingSubViews.includes(viewId)) effectiveSidebarView = 'onboardingView';
    if (studentSubViews.includes(viewId)) effectiveSidebarView = 'studentView';
    // Exit detail is a sub-view of Exit Tracker — keep sidebar item highlighted
    const exitSubViews = ['exitDetailView', 'exitLetterWorkspace', 'exitTemplateEditor'];
    if (exitSubViews.includes(viewId)) effectiveSidebarView = 'exitView';
    links.forEach(l => {
        l.classList.remove('active');
        if (l.getAttribute('data-view') === effectiveSidebarView) {
            l.classList.add('active');
        }
    });

    // Load dynamic data based on view
    try {
        if (viewId === 'dashboardView') loadDashboardData();
        else if (viewId === 'onboardingView') loadOnboardingData();
        else if (viewId === 'onboardingFormView') loadOnboardingFormPage();
        else if (viewId === 'employeeDetailView' && typeof openEmployeeProfileDetail === 'function') {
            const empId = extraParams.employeeId || getEmployeeDetailIdFromUrl();
            if (empId) {
                openEmployeeProfileDetail(empId, extraParams.employeeTab || 'personal', false);
            }
        }
        else if (viewId === 'salaryView') loadSalaryData();
        else if (viewId === 'salaryHistoryView') {
            const empId = extraParams.employeeId || getEmployeeIdFromUrl();
            if (empId) {
                loadDedicatedEmployeeSalaryHistory(empId);
            }
        }
        else if (viewId === 'exitView') loadExitData();
        else if (viewId === 'exitDetailView' && extraParams.exitId && !extraParams.skipDataLoad && typeof openExitDetailModal === 'function') {
            // Only load data when arriving via refresh/popstate — NOT when called from within openExitDetailModal
            openExitDetailModal(extraParams.exitId, true);
        }
        else if (viewId === 'studentView') loadStudentData();
        else if (viewId === 'studentDetailView' && extraParams.studentId && !extraParams.skipStudentDetailLoad && typeof openStudentProfileDetail === 'function') {
            openStudentProfileDetail(extraParams.studentId, extraParams.studentTab || 'personal', false);
        }
        else if (viewId === 'logsView') loadLogsData();
        else if (viewId === 'rolesView') loadRolesData();
        else if (viewId === 'probationView') {
            if (typeof loadProbationData === 'function') loadProbationData();
        }
    } catch (e) {
        console.error(`Error loading view "${viewId}":`, e);
        showToast('Unable to load this page section. Please refresh and try again.', 'error');
    }

    // Update URL without page reload
    if (pushState) {
        let path = viewToPath[viewId] || '/';
        if (viewId === 'salaryHistoryView' && extraParams.employeeId) {
            path = `/salaries/employee/${extraParams.employeeId}/`;
        } else if (viewId === 'employeeDetailView' && extraParams.employeeId) {
            path = `/employees/${extraParams.employeeId}/`;
        } else if (viewId === 'studentDetailView' && extraParams.studentId) {
            path = `/students/${extraParams.studentId}/`;
        } else if (viewId === 'exitDetailView' && extraParams.exitId) {
            path = `/exits/${extraParams.exitId}/clearances/`;
        }
        history.pushState({
            viewId: viewId,
            employeeId: extraParams.employeeId || null,
            employeeTab: extraParams.employeeTab || null,
            studentId: extraParams.studentId || null,
            studentTab: extraParams.studentTab || null,
            exitId: extraParams.exitId || null,
        }, '', path);
    }

    setTimeout(() => {
        if (activeRequestsCount === 0) {
            hideGlobalLoader();
        }
    }, 300);
}

// Handle browser Back/Forward navigation
window.addEventListener('popstate', (event) => {
    if (event.state && event.state.viewId) {
        switchView(event.state.viewId, false, {
            employeeId: event.state.employeeId,
            employeeTab: event.state.employeeTab,
            studentId: event.state.studentId,
            studentTab: event.state.studentTab,
            exitId: event.state.exitId,
        });
    } else {
        let currentPath = window.location.pathname;
        if (!currentPath.endsWith('/')) {
            currentPath += '/';
        }
        let viewId = 'dashboardView';
        const exitId = getExitIdFromUrl();
        if (currentPath.match(/\/salaries\/employee\/(\d+)\//)) {
            viewId = 'salaryHistoryView';
        } else if (exitId) {
            viewId = 'exitDetailView';
        } else if (getEmployeeDetailIdFromUrl()) {
            viewId = 'employeeDetailView';
        } else if (getStudentIdFromUrl()) {
            viewId = 'studentDetailView';
        } else {
            viewId = pathToView[currentPath] || 'dashboardView';
        }
        switchView(viewId, false, {
            employeeId: getEmployeeDetailIdFromUrl(),
            studentId: getStudentIdFromUrl(),
            exitId: exitId,
        });
    }
});

// ---------- NOTIFICATIONS FEED ----------
async function checkNotifications() {
    if (!localStorage.getItem('accessToken')) return;

    // Type → icon emoji map
    const typeIcons = {
        info:    '💬',
        success: '✅',
        warning: '⚠️',
        urgent:  '🔴',
        error:   '❌',
    };

    try {
        const res = await apiFetch('/notifications/feed/');
        if (res.ok) {
            const data = await res.json();
            const notifications = (Array.isArray(data) ? data : (data.results || [])).slice(0, 5);
            const unreadCount = data.unread_count !== undefined ? data.unread_count : notifications.filter(n => !n.is_read).length;

            // Update Bell Badge
            const badge = document.getElementById('notifBadge');
            if (badge) {
                if (unreadCount > 0) {
                    badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
                    badge.style.display = 'block';
                } else {
                    badge.style.display = 'none';
                }
            }

            // Update subtitle
            const subtitle = document.getElementById('notifSubtitle');
            if (subtitle) {
                subtitle.textContent = unreadCount > 0
                    ? `${unreadCount} unread notification${unreadCount > 1 ? 's' : ''}`
                    : 'You\'re all caught up!';
            }

            // Populate Panel
            const listContainer = document.getElementById('notifList');
            if (listContainer) {
                if (notifications.length === 0) {
                    listContainer.innerHTML = `
                        <div class="notif-empty">
                            <div class="notif-empty-icon">🔔</div>
                            <h4>All caught up!</h4>
                            <p>No new notifications right now.<br>Check back later.</p>
                        </div>`;
                    return;
                }

                listContainer.innerHTML = notifications.map(n => {
                    const typeKey = (n.notif_type || 'info').toLowerCase();
                    const typeClass = 'notif-' + typeKey;
                    const icon = typeIcons[typeKey] || '🔔';
                    return `
                        <div class="notif-item unread ${typeClass}" onclick="markNotifRead(${n.id}, '${n.link || '#'}')">
                            <div class="notif-icon-wrap">${icon}</div>
                            <div class="notif-content">
                                <div class="notif-text">${n.message}</div>
                                <div class="notif-time">
                                    <span>🕐</span>
                                    ${formatDate(n.created_at)}
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
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
