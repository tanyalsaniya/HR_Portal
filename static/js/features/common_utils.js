// static/js/features/common_utils.js
// Common UI layout utilities & Role-Based Access Control filters

// Theme Toggle
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    html.style.colorScheme = next;
    localStorage.setItem('theme', next);
}

// Toggle Notifications slide-over panel
function toggleNotifPanel() {
    const panel = document.getElementById('notifPanel');
    if (panel) panel.classList.toggle('open');
}

// ---------- RBAC GATE & UI HELPERS ----------
function hasPermission(codename) {
    return currentUser && currentUser.permissions && currentUser.permissions.includes(codename);
}

function applyPermissionsToUI() {
    if (!currentUser) return;

    // Sidebar links visibility
    const dashboardLink = document.getElementById('dashboardLink');
    if (dashboardLink) dashboardLink.style.display = hasPermission('dashboard.read') ? 'block' : 'none';

    const onboardingLink = document.getElementById('onboardingLink');
    if (onboardingLink) {
        const hasOnboardingAccess = ['onboarding.read', 'onboarding.create', 'onboarding.update', 'onboarding.delete', 'onboarding.generate_letters'].some(hasPermission);
        onboardingLink.style.display = hasOnboardingAccess ? 'block' : 'none';
    }

    const salaryLink = document.getElementById('salaryLink');
    if (salaryLink) {
        const hasSalaryAccess = ['salary.read', 'salary.create_slips', 'salary.approve_increments'].some(hasPermission);
        salaryLink.style.display = hasSalaryAccess ? 'block' : 'none';
    }

    const exitLink = document.getElementById('exitLink');
    if (exitLink) {
        const hasExitAccess = ['exit.read', 'exit.create', 'exit.update', 'exit.delete', 'exit.generate_letters', 'exit.rejoin'].some(hasPermission);
        exitLink.style.display = hasExitAccess ? 'block' : 'none';
    }

    const studentLink = document.getElementById('studentLink');
    if (studentLink) {
        const hasStudentAccess = ['student.read', 'student.create', 'student.update', 'student.delete', 'student.export'].some(hasPermission);
        studentLink.style.display = hasStudentAccess ? 'block' : 'none';
    }

    const tabCertGenBtn = document.getElementById('tabCertGenBtn');
    if (tabCertGenBtn) {
        const isAdminOrHr = currentUser && (currentUser.role === 'ADMIN' || currentUser.role === 'HR');
        tabCertGenBtn.style.display = isAdminOrHr ? 'inline-block' : 'none';
    }


    const adminLogsLink = document.getElementById('adminLogsLink');
    if (adminLogsLink) adminLogsLink.style.display = hasPermission('audit.read') ? 'block' : 'none';

    const adminRolesLink = document.getElementById('adminRolesLink');
    if (adminRolesLink) {
        const isHr = currentUser && (currentUser.role === 'HR' || currentUser.role_code === 'HR');
        const hasRolesManage = hasPermission('roles.manage');
        adminRolesLink.style.display = (hasRolesManage && !isHr) ? 'block' : 'none';
    }

    // Hide settings icon for HR role
    const settingsIconBtn = document.querySelector('button[title="Settings"]');
    if (settingsIconBtn) {
        const isHr = currentUser && (currentUser.role === 'HR' || currentUser.role_code === 'HR');
        settingsIconBtn.style.display = isHr ? 'none' : 'flex';
    }

    // Hide Roles & Permissions view panel for HR role
    const rolesView = document.getElementById('rolesView');
    if (rolesView) {
        const isHr = currentUser && (currentUser.role === 'HR' || currentUser.role_code === 'HR');
        if (isHr) {
            rolesView.style.display = 'none';
        }
    }

    const probationLink = document.getElementById('probationLink');
    if (probationLink) {
        probationLink.style.display = (currentUser && (currentUser.role === 'ADMIN' || currentUser.role === 'HR')) ? 'block' : 'none';
    }


    // Dashboard items
    const incrementWidget = document.getElementById('adminWidgetIncrements');
    if (incrementWidget) {
        incrementWidget.style.display = hasPermission('salary.approve_increments') ? 'block' : 'none';
    }

    // Salaries view header & tables
    const incHeader = document.getElementById('adminIncrementsHeader');
    if (incHeader) incHeader.style.display = hasPermission('salary.approve_increments') ? 'block' : 'none';
    const incTable = document.getElementById('adminIncrementsTableContainer');
    if (incTable) incTable.style.display = hasPermission('salary.approve_increments') ? 'block' : 'none';

    // Top action buttons
    const addEmpBtn = document.getElementById('addEmployeeBtn');
    if (addEmpBtn) addEmpBtn.style.display = hasPermission('onboarding.create') ? 'block' : 'none';

    const bulkSlipsBtn = document.getElementById('bulkSlipsBtn');
    if (bulkSlipsBtn) bulkSlipsBtn.style.display = hasPermission('salary.create_slips') ? 'block' : 'none';

    const setupSalaryBtn = document.getElementById('setupSalaryBtn');
    if (setupSalaryBtn) setupSalaryBtn.style.display = hasPermission('salary.create_slips') ? 'block' : 'none';

    const addExitBtn = document.getElementById('addExitBtn');
    if (addExitBtn) addExitBtn.style.display = hasPermission('exit.create') ? 'block' : 'none';

    const exportStudBtn = document.getElementById('exportStudentBtn');
    if (exportStudBtn) exportStudBtn.style.display = hasPermission('student.export') ? 'block' : 'none';

    const addStudBtn = document.getElementById('addStudentBtn');
    if (addStudBtn) addStudBtn.style.display = hasPermission('student.create') ? 'block' : 'none';

    // Exit template management (Admin or exit.manage_templates permission)
    const manageExitTemplatesBtn = document.getElementById('manageExitTemplatesBtn');
    if (manageExitTemplatesBtn) {
        const isAdmin = currentUser.role_code === 'ADMIN' || currentUser.role === 'ADMIN' || currentUser.is_superuser;
        const hasTemplatePerm = hasPermission('exit.manage_templates');
        manageExitTemplatesBtn.style.display = (isAdmin || hasTemplatePerm) ? 'inline-block' : 'none';
    }

    // Exit email documents permission check
    const chkSendEmailOnExit = document.getElementById('chkSendEmailOnExit');
    const lblSendEmailOnExit = document.getElementById('lblSendEmailOnExit');
    if (chkSendEmailOnExit || lblSendEmailOnExit) {
        const isAdmin = currentUser.role_code === 'ADMIN' || currentUser.role === 'ADMIN' || currentUser.is_superuser;
        const hasEmailPerm = hasPermission('exit.send_email');
        const canSend = isAdmin || hasEmailPerm;
        if (lblSendEmailOnExit) {
            lblSendEmailOnExit.style.display = canSend ? 'inline-flex' : 'none';
        }
        if (chkSendEmailOnExit && !canSend) {
            chkSendEmailOnExit.checked = false;
        }
    }

    // Onboarding templates/letters tabs visibility (Admin or specific permission)
    const pTabLettersBtn = document.getElementById('pTabLettersBtn');
    const subTabGenerateBtn = document.getElementById('subTabGenerateBtn');
    const subTabTemplateBtn = document.getElementById('subTabTemplateBtn');

    if (pTabLettersBtn || subTabGenerateBtn || subTabTemplateBtn) {
        const isAdmin = currentUser.role_code === 'ADMIN' || currentUser.role === 'ADMIN' || currentUser.is_superuser;
        const hasGenPerm = hasPermission('onboarding.generate_letters');
        const hasTemplatePerm = hasPermission('onboarding.manage_templates');

        if (pTabLettersBtn) {
            pTabLettersBtn.style.display = (isAdmin || hasGenPerm || hasTemplatePerm) ? 'inline-block' : 'none';
        }
        if (subTabGenerateBtn) {
            subTabGenerateBtn.style.display = (isAdmin || hasGenPerm) ? 'inline-block' : 'none';
        }
        if (subTabTemplateBtn) {
            subTabTemplateBtn.style.display = (isAdmin || hasTemplatePerm) ? 'inline-block' : 'none';
        }
    }
}

// ---------- URL State Helpers ----------
function setUrlParam(key, value) {
    const url = new URL(window.location);
    url.searchParams.set(key, value);
    // Merge with existing history state so we don't clobber it
    const currentState = history.state || {};
    currentState[key] = value;
    history.replaceState(currentState, '', url);
}

function getUrlParam(key) {
    const url = new URL(window.location);
    return url.searchParams.get(key);
}
