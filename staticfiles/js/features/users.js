// static/js/features/users.js
// Portal Users & HR Accounts management

async function loadPortalUsers() {
    const tbody = document.getElementById('portalUsersTableBody');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px; color: var(--text-light);">Loading portal users...</td></tr>';

    try {
        const res = await apiFetch('/auth/users/');
        if (res.ok) {
            const users = await res.json();
            renderPortalUsersTable(users.results || users);
        } else {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px; color: #ef4444;">Failed to load users.</td></tr>';
        }
    } catch (e) {
        console.error(e);
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px; color: #ef4444;">Error loading portal users.</td></tr>';
    }
}

function renderPortalUsersTable(users) {
    const tbody = document.getElementById('portalUsersTableBody');
    if (!tbody) return;

    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 25px; color: var(--text-light);">No registered users found.</td></tr>';
        return;
    }

    tbody.innerHTML = users.map(u => {
        const isSelf = currentUser && currentUser.id === u.id;
        const statusBadge = u.is_active 
            ? '<span class="status-pill synced" style="background:#22c55e; color:white;">Active</span>' 
            : '<span class="status-pill action-needed" style="background:#ef4444; color:white;">Inactive</span>';
        
        const actionLabel = u.is_active ? 'Deactivate' : 'Activate';
        const actionBtnClass = u.is_active ? 'btn-secondary' : 'btn-primary';

        return `
            <tr style="border-bottom: 1px solid var(--border-color); height: 55px;">
                <td style="padding: 10px 20px; font-weight: 700; color: var(--text-main); font-family: 'Inter', sans-serif;">
                    ${u.first_name} ${u.last_name} ${isSelf ? ' <small style="color:var(--primary-color); font-weight:normal;">(You)</small>' : ''}
                </td>
                <td style="padding: 10px 20px; color: var(--text-secondary); font-family: monospace;">${u.username}</td>
                <td style="padding: 10px 20px; color: var(--text-secondary);">${u.email}</td>
                <td style="padding: 10px 20px; color: var(--text-secondary);">${u.phone || '-'}</td>
                <td style="padding: 10px 20px;">
                    <span style="font-size: 8.5pt; font-weight: bold; background: rgba(124, 58, 237, 0.1); color: var(--primary-color); padding: 4px 8px; border-radius: 6px; text-transform: uppercase;">
                        ${u.role_name || 'No Role'}
                    </span>
                </td>
                <td style="padding: 10px 20px;">${statusBadge}</td>
                <td style="padding: 10px 20px; text-align: right;">
                    ${isSelf ? '' : `
                        <button class="btn" style="padding: 5px 12px; font-size: 8.5pt; border-radius: 6px; font-weight:600; cursor:pointer;" onclick="toggleUserStatus(${u.id}, ${u.is_active})">
                            ${actionLabel}
                        </button>
                        <button class="btn" style="padding: 5px 12px; font-size: 8.5pt; border-radius: 6px; font-weight:600; cursor:pointer; background-color:#ef4444; color:white; border:none; margin-left: 5px;" onclick="deletePortalUser(${u.id})">
                            Delete
                        </button>
                    `}
                </td>
            </tr>
        `;
    }).join('');
}

async function populateRolesDropdown() {
    const select = document.getElementById('userRoleSelect');
    if (!select) return;

    select.innerHTML = '<option value="">Loading roles...</option>';

    try {
        const res = await apiFetch('/roles/');
        if (res.ok) {
            const roles = await res.json();
            const rolesList = roles.results || roles;
            const activeRoles = rolesList.filter(r => r.is_active);
            select.innerHTML = activeRoles.map(r => `<option value="${r.id}">${r.name} (${r.code})</option>`).join('');
        } else {
            select.innerHTML = '<option value="">Failed to load roles</option>';
        }
    } catch (e) {
        console.error(e);
        select.innerHTML = '<option value="">Error loading roles</option>';
    }
}

function openAddUserModal() {
    const modal = document.getElementById('addUserModal');
    if (modal) {
        modal.style.display = 'flex';
        populateRolesDropdown();
    }
}

function closeAddUserModal() {
    const modal = document.getElementById('addUserModal');
    if (modal) {
        modal.style.display = 'none';
        document.getElementById('addUserForm').reset();
        document.getElementById('manualPasswordFields').style.display = 'none';
    }
}

function toggleManualPasswordFields() {
    const autoGen = document.getElementById('userAutoPasswordInput').checked;
    const manualFields = document.getElementById('manualPasswordFields');
    const manualInput = document.getElementById('userManualPasswordInput');

    if (autoGen) {
        manualFields.style.display = 'none';
        manualInput.removeAttribute('required');
    } else {
        manualFields.style.display = 'block';
        manualInput.setAttribute('required', 'true');
    }
}

async function submitAddUser(event) {
    event.preventDefault();

    const firstName = document.getElementById('userFirstNameInput').value;
    const lastName = document.getElementById('userLastNameInput').value;
    const username = document.getElementById('userUsernameInput').value.replace(/\s+/g, '');
    const email = document.getElementById('userEmailInput').value.replace(/\s+/g, '');
    const phone = document.getElementById('userPhoneInput').value.trim();
    const roleId = document.getElementById('userRoleSelect').value;
    const autoGen = document.getElementById('userAutoPasswordInput').checked;
    const password = autoGen ? '' : document.getElementById('userManualPasswordInput').value;

    const payload = {
        first_name: firstName,
        last_name: lastName,
        username: username,
        email: email,
        phone: phone,
        role_id: roleId ? parseInt(roleId) : null,
        auto_generate_password: autoGen,
        password: password
    };

    showToast('Registering user & generating credentials...');

    try {
        const res = await apiFetch('/auth/users/', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            const data = await res.json();
            showToast('User account registered successfully.');
            closeAddUserModal();

            // Display credentials modal
            document.getElementById('credEmailText').textContent = data.email;
            document.getElementById('credUsernameText').textContent = data.username;
            document.getElementById('credPasswordText').textContent = data.password;

            const credModal = document.getElementById('userCredentialsModal');
            if (credModal) credModal.style.display = 'flex';

            loadPortalUsers();
        } else {
            const err = await res.json();
            showToast('Registration failed: ' + JSON.stringify(err), 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Error registering user.', 'error');
    }
}

function closeCredentialsModal() {
    const modal = document.getElementById('userCredentialsModal');
    if (modal) modal.style.display = 'none';
}

function copyCredentialsToClipboard() {
    const email = document.getElementById('credEmailText').textContent;
    const username = document.getElementById('credUsernameText').textContent;
    const password = document.getElementById('credPasswordText').textContent;

    const text = `HR Portal Credentials:\nEmail / Username: ${email}\nPassword: ${password}`;
    
    navigator.clipboard.writeText(text).then(() => {
        showToast('Credentials copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy text: ', err);
        showToast('Failed to copy to clipboard.', 'error');
    });
}

async function toggleUserStatus(userId, isCurrentlyActive) {
    showToast('Updating user access status...');
    try {
        const res = await apiFetch(`/auth/users/${userId}/`, {
            method: 'PATCH',
            body: JSON.stringify({ is_active: !isCurrentlyActive })
        });

        if (res.ok) {
            showToast('User status updated successfully.');
            loadPortalUsers();
        } else {
            const err = await res.json();
            showToast('Update failed: ' + JSON.stringify(err), 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Error updating user status.', 'error');
    }
}

async function deletePortalUser(userId) {
    const _userDelConf = await showDangerConfirm({
        title: 'Delete Portal User?',
        body: 'This will permanently delete this portal user account including all associated access and credentials. This action cannot be undone.',
        confirmText: 'Yes, Delete Account',
        cancelText: 'Cancel',
    });
    if (!_userDelConf || !_userDelConf.confirmed) return;

    showToast('Deleting portal user account...');
    try {
        const res = await apiFetch(`/auth/users/${userId}/`, {
            method: 'DELETE'
        });

        if (res.status === 204) {
            showToast('Portal user account deleted successfully.');
            loadPortalUsers();
        } else {
            const err = await res.json();
            showToast('Failed to delete account: ' + JSON.stringify(err), 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Error deleting account.', 'error');
    }
}
