/**
 * Domain Selector Component
 * Displays available domains and handles selection
 */

const DomainSelector = {
    currentDomainId: null,

    /**
     * Initialize domain selector
     */
    async init() {
        try {
            this.showLoading(true);
            const data = await WorkflowAPI.getDomains();
            this.renderDomains(data.domains);
        } catch (error) {
            console.error('Failed to load domains:', error);
            this.showError('Failed to load domains. Please try again.');
        } finally {
            this.showLoading(false);
        }
    },

    /**
     * Render domains grid
     */
    renderDomains(domains) {
        const grid = document.getElementById('domain-grid');
        grid.innerHTML = '';

        domains.forEach(domain => {
            const card = this.createDomainCard(domain);
            grid.appendChild(card);
        });
    },

    /**
     * Create domain card element
     */
    createDomainCard(domain) {
        const card = document.createElement('div');
        card.className = 'domain-card';
        card.onclick = () => this.selectDomain(domain);

        card.innerHTML = `
            <div class="domain-icon" style="background-color: ${domain.color}20; color: ${domain.color};">
                ${domain.icon}
            </div>
            <h3>${domain.display_name}</h3>
            <p>${domain.description || 'No description available'}</p>
            <div class="domain-meta">
                <i class="bi bi-file-text"></i>
                <span>${domain.template_count} template${domain.template_count !== 1 ? 's' : ''}</span>
            </div>
        `;

        return card;
    },

    /**
     * Handle domain selection
     */
    async selectDomain(domain) {
        this.currentDomainId = domain.domain_id;
        
        // Update UI badge for selected domain
        const badge = document.getElementById('current-domain-name');
        badge.textContent = `${domain.icon} ${domain.display_name}`;
        badge.style.backgroundColor = `${domain.color}20`;
        badge.style.color = domain.color;

        // Switch to canvas screen and load templates
        this.switchScreen('workflow-canvas-screen');
        await WorkflowCanvas.loadTemplates(domain.domain_id);
    },

    /**
     * Switch between screens
     */
    switchScreen(screenId) {
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });
        document.getElementById(screenId).classList.add('active');
    },

    /**
     * Show/hide loading overlay
     */
    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        overlay.style.display = show ? 'flex' : 'none';
    },

    /**
     * Show error message
     */
    showError(message) {
        alert(message); // TODO: Replace with better UI
    }
};

// Export
window.DomainSelector = DomainSelector;
