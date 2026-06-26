// static/js/features/roles.js
// Roles & Permissions management handlers

// ---------- ROLES & PERMISSIONS DATA MANAGEMENT ----------
let allPermissions = [];
let allRoles = [];

async function loadRolesData() {
    document.getElementById('pageTitle').textContent = 'Roles & Permissions Control';
    
    const urlTab = getUrlParam('tab');
    if (urlTab) switchRolesTab(urlTab, false);

    try {
        // Fetch Permissions
        const permRes = await apiFetch('/roles/permissions/');
        if (permRes.ok) {
            const data = await permRes.json();
            allPermissions = data.results || data;
        }

        // Fetch Roles
        const roleRes = await apiFetch('/roles/');
        if (roleRes.ok) {
            const data = await roleRes.json();
            allRoles = data.results || data;
        }

        renderCategoryRoles(allRoles, allPermissions);
        renderGlobalPermissions(allPermissions);
    } catch (e) {
        console.error('Error loading roles data:', e);
        showToast('Failed to load roles/permissions data.', 'error');
    }
}

function switchRolesTab(tabId, updateUrl = true) {
    if (updateUrl) setUrlParam('tab', tabId);
    const categoriesTab = document.getElementById('rolesCategoriesTab');
    const permissionsTab = document.getElementById('rolesPermissionsTab');
    const usersTab = document.getElementById('rolesPortalUsersTab');
    
    const catBtn = document.getElementById('tabCategoryRoles');
    const permBtn = document.getElementById('tabGlobalPermissions');
    const usersBtn = document.getElementById('tabPortalUsers');

    if (!categoriesTab || !permissionsTab || !catBtn || !permBtn) return;

    // Reset styles
    [catBtn, permBtn, usersBtn].forEach(btn => {
        if (btn) {
            btn.className = '';
            btn.style.color = 'var(--text-color)';
            btn.style.borderBottom = 'none';
        }
    });
    if (categoriesTab) categoriesTab.style.display = 'none';
    if (permissionsTab) permissionsTab.style.display = 'none';
    if (usersTab) usersTab.style.display = 'none';

    if (tabId === 'roles-categories') {
        if (categoriesTab) categoriesTab.style.display = 'block';
        catBtn.className = 'active-tab';
        catBtn.style.color = 'var(--primary-color)';
        catBtn.style.borderBottom = '2px solid var(--primary-color)';
    } else if (tabId === 'roles-permissions') {
        if (permissionsTab) permissionsTab.style.display = 'block';
        permBtn.className = 'active-tab';
        permBtn.style.color = 'var(--primary-color)';
        permBtn.style.borderBottom = '2px solid var(--primary-color)';
    } else if (tabId === 'portal-users') {
        if (usersTab) usersTab.style.display = 'block';
        if (usersBtn) {
            usersBtn.className = 'active-tab';
            usersBtn.style.color = 'var(--primary-color)';
            usersBtn.style.borderBottom = '2px solid var(--primary-color)';
        }
        if (typeof loadPortalUsers === 'function') {
            loadPortalUsers();
        }
    }
}

function renderCategoryRoles(roles, permissions) {
    const container = document.getElementById('rolesGridContainer');
    if (!container) return;

    if (roles.length === 0) {
        container.innerHTML = '<div style="grid-column: span 3; text-align: center; padding: 40px; color: #777;">No roles defined.</div>';
        return;
    }

    // Group permissions by module for easier rendering inside cards
    const groupedPerms = {};
    permissions.forEach(p => {
        if (!groupedPerms[p.module]) {
            groupedPerms[p.module] = [];
        }
        groupedPerms[p.module].push(p);
    });

    container.innerHTML = roles.map(role => {
        const assignedPermIds = role.permissions_details ? role.permissions_details.map(p => p.id) : [];

        // Render group boxes per module
        const modulesHtml = Object.keys(groupedPerms).map(module => {
            const modulePerms = groupedPerms[module];
            const permsHtml = modulePerms.map(p => {
                const checked = assignedPermIds.includes(p.id) ? 'checked' : '';
                return `
                    <label class="perm-checkbox-item">
                        <input type="checkbox" data-role-id="${role.id}" data-perm-id="${p.id}" ${checked}>
                        <span>${p.name}</span>
                    </label>
                `;
            }).join('');

            return `
                <div class="module-perms-group">
                    <div class="module-perms-title">${module}</div>
                    ${permsHtml}
                </div>
            `;
        }).join('');

        const isSystem = role.is_system;
        const statusChecked = role.is_active ? 'checked' : '';

        return `
            <div class="role-card" id="role-card-${role.id}">
                <div class="role-card-header">
                    <div>
                        <h4 class="role-card-title">${role.name}</h4>
                        <span class="role-code-badge">${role.code}</span>
                    </div>
                    <div>
                        <label class="toggle-switch" title="Toggle active status">
                            <input type="checkbox" id="role-status-${role.id}" ${statusChecked}>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
                <div class="role-card-body">
                    <div style="font-size: 8.5pt; color: #777; margin-bottom: 5px;">
                        ${isSystem ? '🔒 System Critical Role (Name/Code Locked)' : '🛠️ Custom Role'}
                    </div>
                    <div style="max-height: 250px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; padding-right: 5px;">
                        ${modulesHtml}
                    </div>
                </div>
                <div class="role-card-footer">
                    <button class="btn btn-primary" style="font-size: 9pt; padding: 8px 16px;" onclick="saveRoleChanges(${role.id}, ${isSystem})">Save Changes</button>
                    ${isSystem ? '' : `<button class="btn" style="font-size: 9pt; padding: 8px 16px; background-color:#ef4444; color:white;" onclick="deleteRole(${role.id})">Delete</button>`}
                </div>
            </div>
        `;
    }).join('');
}

function renderGlobalPermissions(permissions) {
    const container = document.getElementById('permissionsGridContainer');
    if (!container) return;

    if (permissions.length === 0) {
        container.innerHTML = '<div style="grid-column: span 3; text-align: center; padding: 40px; color: #777;">No permissions registered.</div>';
        return;
    }

    // Group by module
    const grouped = {};
    permissions.forEach(p => {
        if (!grouped[p.module]) grouped[p.module] = [];
        grouped[p.module].push(p);
    });

    container.innerHTML = Object.keys(grouped).map(moduleName => {
        const perms = grouped[moduleName];
        const rows = perms.map(p => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border-color);">
                <div>
                    <div style="font-weight: 600; font-size: 9.5pt;">${p.name}</div>
                    <code style="font-size: 8pt; color: var(--primary-color);">${p.codename}</code>
                </div>
            </div>
        `).join('');

        return `
            <div class="role-card" style="min-height: auto;">
                <div class="role-card-header" style="border-bottom: 2px solid var(--primary-color);">
                    <h4 class="role-card-title" style="text-transform: uppercase; color: var(--primary-color);">${moduleName} Module</h4>
                </div>
                <div style="display: flex; flex-direction: column; padding: 10px 0;">
                    ${rows}
                </div>
            </div>
        `;
    }).join('');
}

async function saveRoleChanges(roleId, isSystem) {
    // Find card inputs
    const card = document.getElementById(`role-card-${roleId}`);
    if (!card) return;

    const checkboxes = card.querySelectorAll('input[type="checkbox"][data-perm-id]');
    const checkedPermIds = [];
    checkboxes.forEach(cb => {
        if (cb.checked) {
            checkedPermIds.push(parseInt(cb.getAttribute('data-perm-id')));
        }
    });

    const isActive = document.getElementById(`role-status-${roleId}`).checked;

    const payload = {
        is_active: isActive,
        permissions: checkedPermIds
    };

    showToast('Saving role access configuration...');
    try {
        const res = await apiFetch(`/roles/${roleId}/`, {
            method: 'PATCH',
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            showToast('Role permissions updated successfully!');
            
            // If current user modified their own role, refresh their credentials
            const updatedRole = await res.json();
            if (currentUser && currentUser.role === updatedRole.code) {
                const meRes = await apiFetch('/auth/me/');
                if (meRes.ok) {
                    currentUser = await meRes.json();
                    applyPermissionsToUI();
                }
            }

            loadRolesData();
        } else {
            const errors = await res.json();
            showToast('Failed to save changes: ' + JSON.stringify(errors), 'error');
        }
    } catch (err) {
        console.error(err);
        showToast('Failed to communicate with API.', 'error');
    }
}

async function deleteRole(roleId) {
    const _roleDelConf = await showDangerConfirm({
        title: 'Delete Custom Role?',
        body: 'All users currently assigned to this role will be unassigned. This action is permanent and cannot be reversed.',
        confirmText: 'Yes, Delete Role',
        cancelText: 'Cancel',
    });
    if (!_roleDelConf || !_roleDelConf.confirmed) return;

    showToast('Deleting custom role...');
    try {
        const res = await apiFetch(`/roles/${roleId}/`, {
            method: 'DELETE'
        });

        if (res.status === 204) {
            showToast('Custom role deleted successfully.');
            loadRolesData();
        } else {
            const err = await res.json();
            showToast('Failed to delete role: ' + (err.detail || JSON.stringify(err)), 'error');
        }
    } catch (err) {
        console.error(err);
        showToast('Failed to communicate with API.', 'error');
    }
}

// Add Role Modal Handlers
function openAddRoleModal() {
    const modal = document.getElementById('addRoleModal');
    if (modal) modal.style.display = 'flex';
}

function closeAddRoleModal() {
    const modal = document.getElementById('addRoleModal');
    if (modal) {
        modal.style.display = 'none';
        document.getElementById('addRoleForm').reset();
    }
}

async function submitAddRole(event) {
    event.preventDefault();
    const name = document.getElementById('roleNameInput').value;
    const code = document.getElementById('roleCodeInput').value.trim().toUpperCase();
    const isActive = document.getElementById('roleActiveInput').checked;

    const payload = {
        name: name,
        code: code,
        is_active: isActive,
        permissions: [] // New role starts with empty permissions
    };

    showToast('Creating custom role...');
    try {
        const res = await apiFetch('/roles/', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            showToast(`Role ${name} created successfully!`);
            closeAddRoleModal();
            loadRolesData();
        } else {
            const err = await res.json();
            showToast('Failed to create role: ' + JSON.stringify(err), 'error');
        }
    } catch (err) {
        console.error(err);
        showToast('Error sending API request.', 'error');
    }
}

// Add Permission Modal Handlers
function openAddPermissionModal() {
    const modal = document.getElementById('addPermissionModal');
    if (modal) modal.style.display = 'flex';
}

function closeAddPermissionModal() {
    const modal = document.getElementById('addPermissionModal');
    if (modal) {
        modal.style.display = 'none';
        document.getElementById('addPermissionForm').reset();
    }
}

async function submitAddPermission(event) {
    event.preventDefault();
    const name = document.getElementById('permNameInput').value;
    const codename = document.getElementById('permCodenameInput').value.trim().toLowerCase();
    const module = document.getElementById('permModuleSelect').value;

    const payload = {
        name: name,
        codename: codename,
        module: module
    };

    showToast('Creating database permission...');
    try {
        const res = await apiFetch('/roles/permissions/', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            showToast(`Permission created successfully!`);
            closeAddPermissionModal();
            loadRolesData();
        } else {
            const err = await res.json();
            showToast('Failed to create permission: ' + JSON.stringify(err), 'error');
        }
    } catch (err) {
        console.error(err);
        showToast('Error sending API request.', 'error');
    }
}
