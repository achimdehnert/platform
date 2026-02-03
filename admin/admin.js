/**
 * Platform Admin - JavaScript
 * Tenant & User Management
 */

const Admin = {
    // Storage Keys
    TENANTS_KEY: 'platform_tenants',
    USERS_KEY: 'platform_users',
    PLANS_KEY: 'platform_plans',
    ROLES_KEY: 'platform_roles',

    // Initialize
    init() {
        this.initPlans();
        this.initRoles();
        this.initTenants();
        this.initUsers();
    },

    // ==================== PLANS ====================
    initPlans() {
        if (!localStorage.getItem(this.PLANS_KEY)) {
            const defaultPlans = [
                { id: 1, code: 'free', name: 'Free', maxUsers: 2, maxStorageGb: 1, priceMonth: 0 },
                { id: 2, code: 'starter', name: 'Starter', maxUsers: 5, maxStorageGb: 10, priceMonth: 49 },
                { id: 3, code: 'professional', name: 'Professional', maxUsers: 25, maxStorageGb: 100, priceMonth: 149 },
                { id: 4, code: 'enterprise', name: 'Enterprise', maxUsers: 1000, maxStorageGb: 1000, priceMonth: 499 }
            ];
            localStorage.setItem(this.PLANS_KEY, JSON.stringify(defaultPlans));
        }
    },

    getPlans() {
        return JSON.parse(localStorage.getItem(this.PLANS_KEY) || '[]');
    },

    getPlanById(id) {
        return this.getPlans().find(p => p.id === id);
    },

    getPlanByCode(code) {
        return this.getPlans().find(p => p.code === code);
    },

    // ==================== ROLES ====================
    initRoles() {
        if (!localStorage.getItem(this.ROLES_KEY)) {
            const defaultRoles = [
                { id: 1, code: 'owner', name: 'Owner', isSystem: true },
                { id: 2, code: 'admin', name: 'Administrator', isSystem: true },
                { id: 3, code: 'member', name: 'Member', isSystem: true },
                { id: 4, code: 'viewer', name: 'Viewer', isSystem: true }
            ];
            localStorage.setItem(this.ROLES_KEY, JSON.stringify(defaultRoles));
        }
    },

    getRoles() {
        return JSON.parse(localStorage.getItem(this.ROLES_KEY) || '[]');
    },

    // ==================== TENANTS ====================
    initTenants() {
        if (!localStorage.getItem(this.TENANTS_KEY)) {
            const defaultTenants = [
                { id: 1, slug: 'techcorp', name: 'TechCorp GmbH', planId: 4, status: 'active', createdAt: '2025-01-15' },
                { id: 2, slug: 'global-solutions', name: 'Global Solutions AG', planId: 3, status: 'active', createdAt: '2025-12-22' },
                { id: 3, slug: 'marketing-ag', name: 'Marketing AG', planId: 2, status: 'active', createdAt: '2026-01-05' },
                { id: 4, slug: 'innovate-io', name: 'Innovate Ltd', planId: 3, status: 'active', createdAt: '2025-11-18' },
                { id: 5, slug: 'demo', name: 'Demo Tenant', planId: 1, status: 'active', createdAt: '2026-02-01' }
            ];
            localStorage.setItem(this.TENANTS_KEY, JSON.stringify(defaultTenants));
        }
    },

    getTenants() {
        return JSON.parse(localStorage.getItem(this.TENANTS_KEY) || '[]');
    },

    saveTenants(tenants) {
        localStorage.setItem(this.TENANTS_KEY, JSON.stringify(tenants));
    },

    getTenantById(id) {
        return this.getTenants().find(t => t.id === id);
    },

    // ==================== USERS ====================
    initUsers() {
        if (!localStorage.getItem(this.USERS_KEY)) {
            const defaultUsers = [
                { id: 1, email: 'max@techcorp.de', firstName: 'Max', lastName: 'Mustermann', tenantId: 1, roleCode: 'owner', status: 'active', lastLogin: '2026-02-02', createdAt: '2025-01-15' },
                { id: 2, email: 'anna@techcorp.de', firstName: 'Anna', lastName: 'Schmidt', tenantId: 1, roleCode: 'admin', status: 'active', lastLogin: '2026-02-01', createdAt: '2025-01-20' },
                { id: 3, email: 'peter@techcorp.de', firstName: 'Peter', lastName: 'Weber', tenantId: 1, roleCode: 'member', status: 'active', lastLogin: '2026-01-28', createdAt: '2025-02-10' },
                { id: 4, email: 'julia@global-solutions.com', firstName: 'Julia', lastName: 'Meier', tenantId: 2, roleCode: 'owner', status: 'active', lastLogin: '2026-02-02', createdAt: '2025-12-22' },
                { id: 5, email: 'tom@global-solutions.com', firstName: 'Tom', lastName: 'Braun', tenantId: 2, roleCode: 'member', status: 'active', lastLogin: '2026-01-30', createdAt: '2025-12-25' },
                { id: 6, email: 'lisa@marketing-ag.de', firstName: 'Lisa', lastName: 'Marketing', tenantId: 3, roleCode: 'owner', status: 'active', lastLogin: '2026-02-01', createdAt: '2026-01-05' },
                { id: 7, email: 'john@innovate.io', firstName: 'John', lastName: 'Innovate', tenantId: 4, roleCode: 'owner', status: 'active', lastLogin: '2026-02-02', createdAt: '2025-11-18' },
                { id: 8, email: 'sarah@innovate.io', firstName: 'Sarah', lastName: 'Tech', tenantId: 4, roleCode: 'member', status: 'pending', lastLogin: null, createdAt: '2026-01-15' },
                { id: 9, email: 'demo@platform.io', firstName: 'Demo', lastName: 'User', tenantId: 5, roleCode: 'owner', status: 'active', lastLogin: '2026-02-02', createdAt: '2026-02-01' }
            ];
            localStorage.setItem(this.USERS_KEY, JSON.stringify(defaultUsers));
        }
    },

    getUsers() {
        return JSON.parse(localStorage.getItem(this.USERS_KEY) || '[]');
    },

    saveUsers(users) {
        localStorage.setItem(this.USERS_KEY, JSON.stringify(users));
    },

    getUserById(id) {
        return this.getUsers().find(u => u.id === id);
    },

    getUsersByTenantId(tenantId) {
        return this.getUsers().filter(u => u.tenantId === tenantId);
    },

    // ==================== DASHBOARD ====================
    loadDashboard() {
        const tenants = this.getTenants().filter(t => t.status === 'active');
        const users = this.getUsers();
        const plans = this.getPlans();

        // Calculate MRR
        let mrr = 0;
        tenants.forEach(t => {
            const plan = this.getPlanById(t.planId);
            if (plan) mrr += plan.priceMonth;
        });
        document.getElementById('mrr-value').textContent = `€${mrr.toLocaleString()}`;
        document.getElementById('tenant-count').textContent = tenants.length;
        document.getElementById('user-count').textContent = users.length;

        // Plan Distribution
        const planDist = document.getElementById('plan-distribution');
        const planCounts = {};
        plans.forEach(p => planCounts[p.code] = 0);
        tenants.forEach(t => {
            const plan = this.getPlanById(t.planId);
            if (plan) planCounts[plan.code]++;
        });

        planDist.innerHTML = plans.map(p => `
            <div class="plan-stat plan-${p.code}">
                <div class="plan-stat-value">${planCounts[p.code]}</div>
                <div class="plan-stat-label">${p.name}</div>
                <div class="plan-stat-price">€${p.priceMonth}/Monat</div>
            </div>
        `).join('');

        // Add plan stat styles
        const style = document.createElement('style');
        style.textContent = `
            .plan-stat { padding: 1rem; border-radius: 8px; }
            .plan-stat-value { font-size: 2rem; font-weight: 700; }
            .plan-stat-label { font-size: 0.9rem; }
            .plan-stat-price { font-size: 0.8rem; opacity: 0.8; }
            .plan-free { background: #f5f5f5; color: #666; }
            .plan-starter { background: #e3f2fd; color: #1565c0; }
            .plan-professional { background: #e8f5e9; color: #2e7d32; }
            .plan-enterprise { background: linear-gradient(135deg, #fff3e0, #ffe0b2); color: #e65100; }
        `;
        document.head.appendChild(style);

        // Recent Tenants
        const recentTenants = document.getElementById('recent-tenants');
        recentTenants.innerHTML = tenants.slice(0, 5).map(t => {
            const plan = this.getPlanById(t.planId);
            const userCount = this.getUsersByTenantId(t.id).length;
            return `
                <tr>
                    <td><strong>${t.name}</strong><br><small>${t.slug}</small></td>
                    <td><span class="plan-badge plan-${plan?.code}">${plan?.name}</span></td>
                    <td>${userCount}</td>
                    <td><span class="status-badge status-${t.status}">${t.status}</span></td>
                    <td>${t.createdAt}</td>
                </tr>
            `;
        }).join('');

        // Activity List
        const activityList = document.getElementById('activity-list');
        activityList.innerHTML = `
            <div class="activity-item">
                <div class="activity-icon new-tenant">🆕</div>
                <div>
                    <div><strong>Demo Tenant</strong> registriert</div>
                    <div class="activity-time">vor 1 Tag</div>
                </div>
            </div>
            <div class="activity-item">
                <div class="activity-icon upgrade">⬆️</div>
                <div>
                    <div><strong>Global Solutions</strong> Upgrade auf Professional</div>
                    <div class="activity-time">vor 2 Tagen</div>
                </div>
            </div>
            <div class="activity-item">
                <div class="activity-icon user">👤</div>
                <div>
                    <div><strong>Sarah Tech</strong> eingeladen zu Innovate Ltd</div>
                    <div class="activity-time">vor 3 Tagen</div>
                </div>
            </div>
        `;

        // Add activity time style
        const actStyle = document.createElement('style');
        actStyle.textContent = `.activity-time { color: #888; font-size: 0.85rem; }`;
        document.head.appendChild(actStyle);
    },

    // ==================== TENANT LIST ====================
    loadTenants() {
        this.renderTenantTable();
    },

    filterTenants() {
        this.renderTenantTable();
    },

    renderTenantTable() {
        const planFilter = document.getElementById('planFilter')?.value || '';
        const statusFilter = document.getElementById('statusFilter')?.value || '';
        const searchInput = document.getElementById('searchInput')?.value?.toLowerCase() || '';

        let tenants = this.getTenants();

        // Apply filters
        if (planFilter) {
            const plan = this.getPlanByCode(planFilter);
            if (plan) tenants = tenants.filter(t => t.planId === plan.id);
        }
        if (statusFilter) {
            tenants = tenants.filter(t => t.status === statusFilter);
        }
        if (searchInput) {
            tenants = tenants.filter(t => 
                t.name.toLowerCase().includes(searchInput) || 
                t.slug.toLowerCase().includes(searchInput)
            );
        }

        const tbody = document.getElementById('tenant-table-body');
        if (!tbody) return;

        tbody.innerHTML = tenants.map(t => {
            const plan = this.getPlanById(t.planId);
            const userCount = this.getUsersByTenantId(t.id).length;
            return `
                <tr>
                    <td><strong>${t.name}</strong></td>
                    <td><code>${t.slug}</code></td>
                    <td><span class="plan-badge plan-${plan?.code}">${plan?.name}</span></td>
                    <td>${userCount} / ${plan?.maxUsers || '∞'}</td>
                    <td><span class="status-badge status-${t.status}">${this.getStatusLabel(t.status)}</span></td>
                    <td>${t.createdAt}</td>
                    <td>
                        <button class="btn-sm btn-view" onclick="Admin.viewTenant(${t.id})" title="Details">👁️</button>
                        <button class="btn-sm btn-edit" onclick="Admin.editTenant(${t.id})" title="Bearbeiten">✏️</button>
                        <button class="btn-sm btn-upgrade" onclick="Admin.manageUsers(${t.id})" title="Benutzer">👥</button>
                        <button class="btn-sm btn-delete" onclick="Admin.deleteTenant(${t.id})" title="Löschen">🗑️</button>
                    </td>
                </tr>
            `;
        }).join('');

        document.getElementById('pagination-info').textContent = `Zeige ${tenants.length} Tenants`;
    },

    getStatusLabel(status) {
        const labels = { active: 'Aktiv', suspended: 'Gesperrt', deleted: 'Gelöscht', pending: 'Eingeladen' };
        return labels[status] || status;
    },

    // ==================== TENANT CRUD ====================
    createTenant() {
        const plans = this.getPlans();
        const planOptions = plans.map(p => `<option value="${p.id}">${p.name} (€${p.priceMonth}/Monat)</option>`).join('');

        this.showModal('Neuen Tenant anlegen', `
            <div class="form-group">
                <label>Firmenname *</label>
                <input type="text" id="tenant-name" placeholder="z.B. Musterfirma GmbH">
            </div>
            <div class="form-group">
                <label>Slug *</label>
                <input type="text" id="tenant-slug" placeholder="z.B. musterfirma">
                <div class="form-hint">Eindeutige ID, nur Kleinbuchstaben und Bindestriche</div>
            </div>
            <div class="form-group">
                <label>Admin E-Mail *</label>
                <input type="email" id="tenant-email" placeholder="admin@firma.de">
            </div>
            <div class="form-group">
                <label>Plan</label>
                <select id="tenant-plan">${planOptions}</select>
            </div>
        `, () => {
            const name = document.getElementById('tenant-name').value;
            const slug = document.getElementById('tenant-slug').value.toLowerCase().replace(/[^a-z0-9-]/g, '-');
            const email = document.getElementById('tenant-email').value;
            const planId = parseInt(document.getElementById('tenant-plan').value);

            if (!name || !slug || !email) {
                this.showToast('Bitte alle Pflichtfelder ausfüllen!', 'error');
                return;
            }

            const tenants = this.getTenants();
            if (tenants.find(t => t.slug === slug)) {
                this.showToast('Slug existiert bereits!', 'error');
                return;
            }

            const newId = Math.max(...tenants.map(t => t.id), 0) + 1;
            const today = new Date().toISOString().split('T')[0];

            tenants.push({
                id: newId,
                slug: slug,
                name: name,
                planId: planId,
                status: 'active',
                createdAt: today
            });
            this.saveTenants(tenants);

            // Create owner user
            const users = this.getUsers();
            const newUserId = Math.max(...users.map(u => u.id), 0) + 1;
            users.push({
                id: newUserId,
                email: email,
                firstName: 'Admin',
                lastName: name.split(' ')[0],
                tenantId: newId,
                roleCode: 'owner',
                status: 'active',
                lastLogin: null,
                createdAt: today
            });
            this.saveUsers(users);

            this.showToast(`Tenant "${name}" mit Owner angelegt!`, 'success');
            this.closeModal();
            this.renderTenantTable();
        });
    },

    editTenant(id) {
        const tenant = this.getTenantById(id);
        if (!tenant) return;

        const plans = this.getPlans();
        const planOptions = plans.map(p => 
            `<option value="${p.id}" ${tenant.planId === p.id ? 'selected' : ''}>${p.name}</option>`
        ).join('');

        const statusOptions = ['active', 'suspended', 'deleted'].map(s =>
            `<option value="${s}" ${tenant.status === s ? 'selected' : ''}>${this.getStatusLabel(s)}</option>`
        ).join('');

        this.showModal('Tenant bearbeiten', `
            <div class="form-group">
                <label>Firmenname</label>
                <input type="text" id="edit-tenant-name" value="${tenant.name}">
            </div>
            <div class="form-group">
                <label>Slug</label>
                <input type="text" id="edit-tenant-slug" value="${tenant.slug}" disabled>
            </div>
            <div class="form-group">
                <label>Plan</label>
                <select id="edit-tenant-plan">${planOptions}</select>
            </div>
            <div class="form-group">
                <label>Status</label>
                <select id="edit-tenant-status">${statusOptions}</select>
            </div>
        `, () => {
            const tenants = this.getTenants();
            const idx = tenants.findIndex(t => t.id === id);
            if (idx === -1) return;

            tenants[idx].name = document.getElementById('edit-tenant-name').value;
            tenants[idx].planId = parseInt(document.getElementById('edit-tenant-plan').value);
            tenants[idx].status = document.getElementById('edit-tenant-status').value;

            this.saveTenants(tenants);
            this.showToast('Tenant aktualisiert!', 'success');
            this.closeModal();
            this.renderTenantTable();
        });
    },

    viewTenant(id) {
        const tenant = this.getTenantById(id);
        if (!tenant) return;

        const plan = this.getPlanById(tenant.planId);
        const users = this.getUsersByTenantId(id);

        this.showModal(`🏢 ${tenant.name}`, `
            <div class="tenant-details">
                <div class="detail-row"><strong>Slug:</strong> ${tenant.slug}</div>
                <div class="detail-row"><strong>Plan:</strong> ${plan?.name} (€${plan?.priceMonth}/Monat)</div>
                <div class="detail-row"><strong>Status:</strong> ${this.getStatusLabel(tenant.status)}</div>
                <div class="detail-row"><strong>Erstellt:</strong> ${tenant.createdAt}</div>
                <div class="detail-row"><strong>Benutzer:</strong> ${users.length} / ${plan?.maxUsers}</div>
            </div>
            <hr>
            <h4>Benutzer</h4>
            <ul class="user-list">
                ${users.map(u => `<li>${u.firstName} ${u.lastName} (${u.email}) - ${u.roleCode}</li>`).join('')}
            </ul>
        `, null, true);
    },

    deleteTenant(id) {
        const tenant = this.getTenantById(id);
        if (!tenant) return;

        if (!confirm(`Tenant "${tenant.name}" wirklich löschen? Alle Benutzer werden ebenfalls entfernt.`)) return;

        let tenants = this.getTenants();
        tenants = tenants.filter(t => t.id !== id);
        this.saveTenants(tenants);

        let users = this.getUsers();
        users = users.filter(u => u.tenantId !== id);
        this.saveUsers(users);

        this.showToast('Tenant gelöscht!', 'success');
        this.renderTenantTable();
    },

    manageUsers(tenantId) {
        window.location.href = `users.html?tenant=${tenantId}`;
    },

    // ==================== USER LIST ====================
    loadUsers() {
        // Populate tenant filter
        const tenantFilter = document.getElementById('tenantFilter');
        if (tenantFilter) {
            const tenants = this.getTenants();
            tenantFilter.innerHTML = '<option value="">Alle Tenants</option>' +
                tenants.map(t => `<option value="${t.id}">${t.name}</option>`).join('');

            // Check URL for tenant filter
            const urlParams = new URLSearchParams(window.location.search);
            const tenantParam = urlParams.get('tenant');
            if (tenantParam) tenantFilter.value = tenantParam;
        }
        this.renderUserTable();
    },

    filterUsers() {
        this.renderUserTable();
    },

    renderUserTable() {
        const tenantFilter = document.getElementById('tenantFilter')?.value || '';
        const roleFilter = document.getElementById('roleFilter')?.value || '';
        const statusFilter = document.getElementById('userStatusFilter')?.value || '';
        const searchInput = document.getElementById('userSearchInput')?.value?.toLowerCase() || '';

        let users = this.getUsers();

        if (tenantFilter) users = users.filter(u => u.tenantId === parseInt(tenantFilter));
        if (roleFilter) users = users.filter(u => u.roleCode === roleFilter);
        if (statusFilter) users = users.filter(u => u.status === statusFilter);
        if (searchInput) {
            users = users.filter(u =>
                u.email.toLowerCase().includes(searchInput) ||
                u.firstName.toLowerCase().includes(searchInput) ||
                u.lastName.toLowerCase().includes(searchInput)
            );
        }

        const tbody = document.getElementById('user-table-body');
        if (!tbody) return;

        tbody.innerHTML = users.map(u => {
            const tenant = this.getTenantById(u.tenantId);
            return `
                <tr>
                    <td>
                        <strong>${u.firstName} ${u.lastName}</strong><br>
                        <small>${u.email}</small>
                    </td>
                    <td>${tenant?.name || '-'}</td>
                    <td><span class="plan-badge plan-${u.roleCode === 'owner' ? 'enterprise' : u.roleCode === 'admin' ? 'professional' : 'starter'}">${u.roleCode}</span></td>
                    <td><span class="status-badge status-${u.status}">${this.getStatusLabel(u.status)}</span></td>
                    <td>${u.lastLogin || '-'}</td>
                    <td>${u.createdAt}</td>
                    <td>
                        <button class="btn-sm btn-edit" onclick="Admin.editUser(${u.id})" title="Bearbeiten">✏️</button>
                        <button class="btn-sm btn-delete" onclick="Admin.deleteUser(${u.id})" title="Löschen">🗑️</button>
                    </td>
                </tr>
            `;
        }).join('');

        document.getElementById('user-pagination-info').textContent = `Zeige ${users.length} Benutzer`;
    },

    // ==================== USER CRUD ====================
    createUser() {
        const tenants = this.getTenants();
        const tenantOptions = tenants.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
        const roles = this.getRoles();
        const roleOptions = roles.map(r => `<option value="${r.code}">${r.name}</option>`).join('');

        this.showModal('Neuen Benutzer anlegen', `
            <div class="form-group">
                <label>Vorname *</label>
                <input type="text" id="user-firstname" placeholder="Vorname">
            </div>
            <div class="form-group">
                <label>Nachname *</label>
                <input type="text" id="user-lastname" placeholder="Nachname">
            </div>
            <div class="form-group">
                <label>E-Mail *</label>
                <input type="email" id="user-email" placeholder="nutzer@firma.de">
            </div>
            <div class="form-group">
                <label>Tenant *</label>
                <select id="user-tenant">${tenantOptions}</select>
            </div>
            <div class="form-group">
                <label>Rolle</label>
                <select id="user-role">${roleOptions}</select>
            </div>
        `, () => {
            const firstName = document.getElementById('user-firstname').value;
            const lastName = document.getElementById('user-lastname').value;
            const email = document.getElementById('user-email').value;
            const tenantId = parseInt(document.getElementById('user-tenant').value);
            const roleCode = document.getElementById('user-role').value;

            if (!firstName || !lastName || !email) {
                this.showToast('Bitte alle Pflichtfelder ausfüllen!', 'error');
                return;
            }

            const users = this.getUsers();
            if (users.find(u => u.email === email)) {
                this.showToast('E-Mail existiert bereits!', 'error');
                return;
            }

            const newId = Math.max(...users.map(u => u.id), 0) + 1;
            const today = new Date().toISOString().split('T')[0];

            users.push({
                id: newId,
                email: email,
                firstName: firstName,
                lastName: lastName,
                tenantId: tenantId,
                roleCode: roleCode,
                status: 'active',
                lastLogin: null,
                createdAt: today
            });
            this.saveUsers(users);

            this.showToast(`Benutzer "${firstName} ${lastName}" angelegt!`, 'success');
            this.closeModal();
            this.renderUserTable();
        });
    },

    editUser(id) {
        const user = this.getUserById(id);
        if (!user) return;

        const roles = this.getRoles();
        const roleOptions = roles.map(r =>
            `<option value="${r.code}" ${user.roleCode === r.code ? 'selected' : ''}>${r.name}</option>`
        ).join('');

        const statusOptions = ['active', 'pending', 'suspended'].map(s =>
            `<option value="${s}" ${user.status === s ? 'selected' : ''}>${this.getStatusLabel(s)}</option>`
        ).join('');

        this.showModal('Benutzer bearbeiten', `
            <div class="form-group">
                <label>Vorname</label>
                <input type="text" id="edit-user-firstname" value="${user.firstName}">
            </div>
            <div class="form-group">
                <label>Nachname</label>
                <input type="text" id="edit-user-lastname" value="${user.lastName}">
            </div>
            <div class="form-group">
                <label>E-Mail</label>
                <input type="email" id="edit-user-email" value="${user.email}">
            </div>
            <div class="form-group">
                <label>Rolle</label>
                <select id="edit-user-role">${roleOptions}</select>
            </div>
            <div class="form-group">
                <label>Status</label>
                <select id="edit-user-status">${statusOptions}</select>
            </div>
        `, () => {
            const users = this.getUsers();
            const idx = users.findIndex(u => u.id === id);
            if (idx === -1) return;

            users[idx].firstName = document.getElementById('edit-user-firstname').value;
            users[idx].lastName = document.getElementById('edit-user-lastname').value;
            users[idx].email = document.getElementById('edit-user-email').value;
            users[idx].roleCode = document.getElementById('edit-user-role').value;
            users[idx].status = document.getElementById('edit-user-status').value;

            this.saveUsers(users);
            this.showToast('Benutzer aktualisiert!', 'success');
            this.closeModal();
            this.renderUserTable();
        });
    },

    deleteUser(id) {
        const user = this.getUserById(id);
        if (!user) return;

        if (!confirm(`Benutzer "${user.firstName} ${user.lastName}" wirklich löschen?`)) return;

        let users = this.getUsers();
        users = users.filter(u => u.id !== id);
        this.saveUsers(users);

        this.showToast('Benutzer gelöscht!', 'success');
        this.renderUserTable();
    },

    // ==================== EXPORT ====================
    exportTenants() {
        const tenants = this.getTenants();
        const csv = 'ID,Slug,Name,Plan,Status,Erstellt\n' +
            tenants.map(t => {
                const plan = this.getPlanById(t.planId);
                return `${t.id},"${t.slug}","${t.name}","${plan?.name}","${t.status}","${t.createdAt}"`;
            }).join('\n');
        this.downloadCSV(csv, 'tenants.csv');
    },

    exportUsers() {
        const users = this.getUsers();
        const csv = 'ID,Email,Vorname,Nachname,Tenant,Rolle,Status,Erstellt\n' +
            users.map(u => {
                const tenant = this.getTenantById(u.tenantId);
                return `${u.id},"${u.email}","${u.firstName}","${u.lastName}","${tenant?.name}","${u.roleCode}","${u.status}","${u.createdAt}"`;
            }).join('\n');
        this.downloadCSV(csv, 'users.csv');
    },

    downloadCSV(csv, filename) {
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
    },

    // ==================== MODAL ====================
    showModal(title, content, onConfirm, viewOnly = false) {
        const container = document.getElementById('modal-container');
        container.innerHTML = `
            <div class="modal-overlay" onclick="Admin.closeModal()">
                <div class="modal" onclick="event.stopPropagation()">
                    <div class="modal-header">
                        <h2>${title}</h2>
                        <button class="modal-close" onclick="Admin.closeModal()">×</button>
                    </div>
                    <div class="modal-body">${content}</div>
                    ${!viewOnly ? `
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="Admin.closeModal()">Abbrechen</button>
                        <button class="btn btn-primary" id="modal-confirm">Speichern</button>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;

        if (onConfirm && !viewOnly) {
            document.getElementById('modal-confirm').onclick = onConfirm;
        }
    },

    closeModal() {
        document.getElementById('modal-container').innerHTML = '';
    },

    // ==================== TOAST ====================
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
};
