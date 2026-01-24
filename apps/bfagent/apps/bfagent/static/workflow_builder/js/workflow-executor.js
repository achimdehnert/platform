/**
 * Workflow Executor Component
 * Handles workflow execution with modal UI
 */

const WorkflowExecutor = {
    currentTemplate: null,
    executionModal: null,
    
    /**
     * Initialize executor
     */
    init() {
        // Setup modal
        const modalElement = document.getElementById('executionModal');
        this.executionModal = new bootstrap.Modal(modalElement);
        
        // Setup event listeners
        this.setupEventListeners();
    },
    
    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Execute button
        const executeBtn = document.getElementById('execute-workflow-btn');
        if (executeBtn) {
            executeBtn.addEventListener('click', () => this.showExecutionModal());
        }
        
        // Start execution button
        const startBtn = document.getElementById('start-execution-btn');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.executeWorkflow());
        }
    },
    
    /**
     * Show execution button
     */
    showExecuteButton(template) {
        this.currentTemplate = template;
        const section = document.getElementById('execute-workflow-section');
        section.style.display = 'block';
    },
    
    /**
     * Hide execution button
     */
    hideExecuteButton() {
        const section = document.getElementById('execute-workflow-section');
        section.style.display = 'none';
        this.currentTemplate = null;
    },
    
    /**
     * Show execution modal
     */
    showExecutionModal() {
        if (!this.currentTemplate) return;
        
        // Reset modal
        this.resetModal();
        
        // Build variables form
        this.buildVariablesForm();
        
        // Show modal
        this.executionModal.show();
    },
    
    /**
     * Build variables input form with smart dropdowns
     */
    async buildVariablesForm() {
        const form = document.getElementById('variables-form');
        const variables = this.currentTemplate.variables?.required || [];
        
        if (variables.length === 0) {
            form.innerHTML = '<p class="text-muted">No variables required for this workflow.</p>';
            return;
        }
        
        let formHTML = '';
        
        for (const varName of variables) {
            formHTML += await this.buildFieldForVariable(varName);
        }
        
        form.innerHTML = formHTML;
    },
    
    /**
     * Build appropriate field type based on variable name
     */
    async buildFieldForVariable(varName) {
        const fieldConfig = this.getFieldConfig(varName);
        
        // For dropdowns, load options
        if (fieldConfig.type === 'select') {
            const options = await this.loadOptionsFor(varName);
            return this.buildSelectField(varName, fieldConfig, options);
        }
        
        // For regular inputs
        return this.buildInputField(varName, fieldConfig);
    },
    
    /**
     * Get field configuration based on variable name
     */
    getFieldConfig(varName) {
        const configs = {
            'project_id': {
                type: 'select',
                label: 'Select Project',
                placeholder: 'Choose a project'
            },
            'plot_type': {
                type: 'select',
                label: 'Plot Type',
                placeholder: 'Choose plot structure'
            },
            'character_id': {
                type: 'select',
                label: 'Select Character',
                placeholder: 'Choose a character'
            },
            'chapter_number': {
                type: 'number',
                label: 'Chapter Number',
                placeholder: 'Enter chapter number'
            }
        };
        
        return configs[varName] || {
            type: 'text',
            label: this.formatLabel(varName),
            placeholder: `Enter ${varName}`
        };
    },
    
    /**
     * Load options for dropdown fields
     */
    async loadOptionsFor(varName) {
        try {
            if (varName === 'project_id') {
                const projects = await WorkflowAPI.getProjects();
                return projects.map(p => ({ value: p.id, label: p.title }));
            }
            
            if (varName === 'plot_type') {
                return [
                    { value: 'three_act', label: 'Three Act Structure' },
                    { value: 'heroes_journey', label: "Hero's Journey" },
                    { value: 'freytag', label: "Freytag's Pyramid" },
                    { value: 'save_the_cat', label: 'Save The Cat' },
                    { value: 'custom', label: 'Custom Structure' }
                ];
            }
            
            if (varName === 'character_id') {
                // Mock data - replace with real API call
                return [
                    { value: 1, label: 'John Smith (Protagonist)' },
                    { value: 2, label: 'Sarah Connor (Antagonist)' },
                    { value: 3, label: 'Dr. Watson (Supporting)' }
                ];
            }
            
            return [];
        } catch (error) {
            console.error(`Failed to load options for ${varName}:`, error);
            return [];
        }
    },
    
    /**
     * Build select field HTML
     */
    buildSelectField(varName, config, options) {
        let optionsHTML = `<option value="">-- ${config.placeholder} --</option>`;
        options.forEach(opt => {
            optionsHTML += `<option value="${opt.value}">${opt.label}</option>`;
        });
        
        return `
            <div class="mb-3">
                <label for="var-${varName}" class="form-label">
                    <i class="bi bi-list"></i> ${config.label}
                </label>
                <select class="form-select" id="var-${varName}" name="${varName}" required>
                    ${optionsHTML}
                </select>
            </div>
        `;
    },
    
    /**
     * Build regular input field HTML
     */
    buildInputField(varName, config) {
        return `
            <div class="mb-3">
                <label for="var-${varName}" class="form-label">${config.label}</label>
                <input type="${config.type}" class="form-control" id="var-${varName}" 
                       name="${varName}" placeholder="${config.placeholder}" required>
            </div>
        `;
    },
    
    /**
     * Format variable name as label
     */
    formatLabel(varName) {
        return varName
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    },
    
    /**
     * Execute workflow
     */
    async executeWorkflow() {
        try {
            // Gather variables
            const variables = this.gatherVariables();
            
            // Hide form, show progress
            document.getElementById('variables-form-section').style.display = 'none';
            document.getElementById('start-execution-btn').style.display = 'none';
            document.getElementById('execution-progress-section').style.display = 'block';
            
            // Update progress
            this.updateProgress(25, 'Starting workflow...');
            
            await this.simulateExecution();
            
            // Show success
            this.showSuccess('Workflow executed successfully! (Demo mode)');
            
        } catch (error) {
            this.showError(error.message);
        }
    },
    
    /**
     * Gather variables from form (inputs and selects)
     */
    gatherVariables() {
        const variables = {};
        const fields = document.querySelectorAll('#variables-form input, #variables-form select');
        
        fields.forEach(field => {
            if (field.value.trim() === '' && field.required) {
                const label = this.formatLabel(field.name);
                throw new Error(`Please select/fill in: ${label}`);
            }
            variables[field.name] = field.value;
        });
        
        return variables;
    },
    
    /**
     * Simulate execution (replace with real API call)
     */
    async simulateExecution() {
        this.updateProgress(50, 'Processing inputs...');
        await this.sleep(1000);
        
        this.updateProgress(75, 'Running AI generation...');
        await this.sleep(1500);
        
        this.updateProgress(100, 'Finalizing output...');
        await this.sleep(800);
    },
    
    /**
     * Update progress bar
     */
    updateProgress(percent, message) {
        const bar = document.getElementById('execution-progress-bar');
        const status = document.getElementById('execution-status');
        
        bar.style.width = percent + '%';
        bar.setAttribute('aria-valuenow', percent);
        status.textContent = message;
    },
    
    /**
     * Show success message
     */
    showSuccess(message) {
        document.getElementById('execution-progress-section').style.display = 'none';
        document.getElementById('execution-results-section').style.display = 'block';
        document.getElementById('execution-results').innerHTML = `
            <strong>Success!</strong><br>
            ${message}<br><br>
            <em>Note: Full execution will be integrated in next phase.</em>
        `;
    },
    
    /**
     * Show error message
     */
    showError(message) {
        document.getElementById('execution-progress-section').style.display = 'none';
        document.getElementById('execution-error-section').style.display = 'block';
        document.getElementById('execution-error').innerHTML = `
            <strong>Error:</strong> ${message}
        `;
    },
    
    /**
     * Reset modal to initial state
     */
    resetModal() {
        document.getElementById('variables-form-section').style.display = 'block';
        document.getElementById('start-execution-btn').style.display = 'block';
        document.getElementById('execution-progress-section').style.display = 'none';
        document.getElementById('execution-results-section').style.display = 'none';
        document.getElementById('execution-error-section').style.display = 'none';
        
        this.updateProgress(0, '');
    },
    
    /**
     * Sleep helper
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
};

// Export
window.WorkflowExecutor = WorkflowExecutor;
