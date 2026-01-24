/**
 * API Client for Workflow Builder
 * Handles all communication with backend API
 */

const WorkflowAPI = {
    baseURL: '/api/workflow',

    /**
     * Fetch all available domains
     */
    async getDomains() {
        const response = await fetch(`${this.baseURL}/domains/`);
        if (!response.ok) throw new Error('Failed to fetch domains');
        return response.json();
    },

    /**
     * Fetch all workflow templates (optionally filtered by domain)
     */
    async getTemplates(domainId = null) {
        const url = domainId 
            ? `${this.baseURL}/workflows/templates/?domain=${domainId}`
            : `${this.baseURL}/workflows/templates/`;
        
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch templates');
        return response.json();
    },

    /**
     * Fetch detailed template information
     */
    async getTemplateDetail(templateId) {
        const response = await fetch(`${this.baseURL}/workflows/templates/${templateId}/`);
        if (!response.ok) throw new Error('Failed to fetch template details');
        return response.json();
    },

    /**
     * Fetch all available handlers
     */
    async getHandlers() {
        const response = await fetch(`${this.baseURL}/handlers/`);
        if (!response.ok) throw new Error('Failed to fetch handlers');
        return response.json();
    },
    
    /**
     * Get detailed information about a specific handler
     */
    async getHandlerDetail(handlerId) {
        const response = await fetch(`${this.baseURL}/handlers/${handlerId}/`);
        if (!response.ok) throw new Error('Failed to fetch handler details');
        return response.json();
    },

    /**
     * Execute a workflow
     */
    async executeWorkflow(workflowId, variables, context = {}) {
        const response = await fetch(`${this.baseURL}/workflows/execute/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                workflow_id: workflowId,
                variables,
                context
            })
        });
        
        if (!response.ok) throw new Error('Failed to execute workflow');
        return response.json();
    },

    /**
     * Get list of projects for dropdown (Real API)
     */
    async getProjects() {
        const response = await fetch(`${this.baseURL}/projects/list/`);
        if (!response.ok) throw new Error('Failed to fetch projects');
        const data = await response.json();
        return data.projects || [];
    },

    /**
     * Get CSRF token from cookies
     */
    getCSRFToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                return cookie.substring(name.length + 1);
            }
        }
        return '';
    }
};

// Export for use in other scripts
window.WorkflowAPI = WorkflowAPI;
