/**
 * Workflow Canvas Component
 * Displays and manages workflow templates and phases
 */

const WorkflowCanvas = {
    currentTemplate: null,
    currentDomainId: null,

    /**
     * Load templates for selected domain
     */
    async loadTemplates(domainId) {
        this.currentDomainId = domainId;
        
        try {
            DomainSelector.showLoading(true);
            const data = await WorkflowAPI.getTemplates(domainId);
            this.renderTemplateList(data.templates);
        } catch (error) {
            console.error('Failed to load templates:', error);
            DomainSelector.showError('Failed to load templates.');
        } finally {
            DomainSelector.showLoading(false);
        }
    },

    /**
     * Render template selection list
     */
    renderTemplateList(templates) {
        const list = document.getElementById('template-list');
        list.innerHTML = '';

        if (templates.length === 0) {
            list.innerHTML = '<p class="text-muted">No templates available for this domain.</p>';
            return;
        }

        templates.forEach(template => {
            const card = this.createTemplateCard(template);
            list.appendChild(card);
        });

        // Show template selection, hide canvas
        document.getElementById('template-selection').style.display = 'block';
        document.getElementById('workflow-canvas').style.display = 'none';
    },

    /**
     * Create template card element
     */
    createTemplateCard(template) {
        const card = document.createElement('div');
        card.className = 'template-card';
        card.onclick = () => this.selectTemplate(template.template_id);

        card.innerHTML = `
            <h4>${template.name}</h4>
            <p>${template.description}</p>
            <div class="template-meta">
                <span>
                    <i class="bi bi-layers"></i> ${template.phase_count} phases
                </span>
                <span>
                    <i class="bi bi-gear"></i> ${template.handler_count} handlers
                </span>
            </div>
        `;

        return card;
    },

    /**
     * Select and load a template
     */
    async selectTemplate(templateId) {
        try {
            DomainSelector.showLoading(true);
            const template = await WorkflowAPI.getTemplateDetail(templateId);
            this.currentTemplate = template;
            
            // Update UI
            document.getElementById('current-template-name').textContent = template.name;
            
            // Render workflow canvas
            this.renderWorkflowCanvas(template);
        } catch (error) {
            console.error('Failed to load template:', error);
            DomainSelector.showError('Failed to load template details.');
        } finally {
            DomainSelector.showLoading(false);
        }
    },

    /**
     * Render workflow canvas with phases
     */
    renderWorkflowCanvas(template) {
        const canvas = document.getElementById('workflow-canvas');
        canvas.innerHTML = '';

        // Hide template selection, show canvas
        document.getElementById('template-selection').style.display = 'none';
        canvas.style.display = 'block';

        // Create phase container
        const container = document.createElement('div');
        container.className = 'phase-container';

        // Render each phase
        template.phases.forEach(phase => {
            const phaseNode = this.createPhaseNode(phase);
            container.appendChild(phaseNode);
        });

        canvas.appendChild(container);
        
        // Show execute button
        if (window.WorkflowExecutor) {
            WorkflowExecutor.showExecuteButton(template);
        }
    },

    /**
     * Create phase node element
     */
    createPhaseNode(phase) {
        const node = document.createElement('div');
        node.className = 'phase-node';
        node.style.borderLeftColor = phase.color;

        const handlersHTML = phase.handlers.map(handler => `
            <div class="handler-node">
                <div class="handler-name">${handler.handler || handler.name || 'Unknown Handler'}</div>
                <div class="handler-config">${this.formatHandlerConfig(handler.config)}</div>
            </div>
        `).join('');

        node.innerHTML = `
            <div class="phase-header">
                <span class="phase-icon">${phase.icon}</span>
                <h3 style="color: ${phase.color};">${phase.name}</h3>
            </div>
            <div class="handler-list">
                ${handlersHTML}
            </div>
        `;

        return node;
    },

    /**
     * Format handler configuration for display
     */
    formatHandlerConfig(config) {
        if (!config || Object.keys(config).length === 0) {
            return '<span class="text-muted">No configuration</span>';
        }

        const entries = Object.entries(config)
            .slice(0, 3)  // Show max 3 config items
            .map(([key, value]) => `${key}: ${JSON.stringify(value)}`)
            .join(', ');

        return entries;
    },

    /**
     * Reset canvas
     */
    reset() {
        this.currentTemplate = null;
        document.getElementById('workflow-canvas').innerHTML = '';
        document.getElementById('template-selection').style.display = 'block';
        document.getElementById('workflow-canvas').style.display = 'none';
    }
};

// Export
window.WorkflowCanvas = WorkflowCanvas;
