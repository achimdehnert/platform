/**
 * Handler Browser Component
 * Manages handler library display, search, details, and testing
 */

const HandlerBrowser = {
    handlers: [],
    filteredHandlers: [],
    currentHandler: null,
    detailsModal: null,
    testerModal: null,
    
    /**
     * Initialize Handler Browser
     */
    async init() {
        // Setup modals
        const detailsModalEl = document.getElementById('handlerDetailsModal');
        const testerModalEl = document.getElementById('handlerTesterModal');
        
        if (detailsModalEl) this.detailsModal = new bootstrap.Modal(detailsModalEl);
        if (testerModalEl) this.testerModal = new bootstrap.Modal(testerModalEl);
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Don't load handlers yet - wait until screen is shown
        console.log('Handler Browser initialized');
    },
    
    /**
     * Show handler browser screen (called when tab is clicked)
     */
    async show() {
        console.log('Showing Handler Browser...');
        // Load handlers if not loaded yet
        if (this.handlers.length === 0) {
            await this.loadHandlers();
        }
    },
    
    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Search
        const searchInput = document.getElementById('handler-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterHandlers(e.target.value, document.getElementById('handler-filter').value);
            });
        }
        
        // Filter
        const filterSelect = document.getElementById('handler-filter');
        if (filterSelect) {
            filterSelect.addEventListener('change', (e) => {
                this.filterHandlers(document.getElementById('handler-search').value, e.target.value);
            });
        }
        
        // Test handler button
        const testBtn = document.getElementById('test-handler-btn');
        if (testBtn) {
            testBtn.addEventListener('click', () => this.showHandlerTester());
        }
        
        // Run test button
        const runTestBtn = document.getElementById('run-handler-test-btn');
        if (runTestBtn) {
            runTestBtn.addEventListener('click', () => this.runHandlerTest());
        }
    },
    
    /**
     * Load handlers from API
     */
    async loadHandlers() {
        try {
            const data = await WorkflowAPI.getHandlers();
            this.handlers = data.handlers || [];
            this.filteredHandlers = [...this.handlers];
            
            this.updateStatistics();
            this.renderHandlerList();
        } catch (error) {
            console.error('Failed to load handlers:', error);
            this.showError('Failed to load handlers');
        }
    },
    
    /**
     * Update handler statistics with real data from DB
     */
    updateStatistics() {
        const stats = {
            input: 0,
            processing: 0,
            output: 0
        };
        
        this.handlers.forEach(handler => {
            if (handler.category) {
                stats[handler.category] = (stats[handler.category] || 0) + 1;
            }
        });
        
        // Update with real counts from DB
        document.getElementById('input-handler-count').textContent = stats.input || 0;
        document.getElementById('processing-handler-count').textContent = stats.processing || 0;
        document.getElementById('output-handler-count').textContent = stats.output || 0;
    },
    
    /**
     * Filter handlers
     */
    filterHandlers(searchTerm, category) {
        this.filteredHandlers = this.handlers.filter(handler => {
            // Category filter
            if (category !== 'all' && handler.category !== category) {
                return false;
            }
            
            // Search filter
            if (searchTerm) {
                const term = searchTerm.toLowerCase();
                return handler.handler_id.toLowerCase().includes(term) ||
                       handler.display_name.toLowerCase().includes(term) ||
                       handler.description.toLowerCase().includes(term);
            }
            
            return true;
        });
        
        this.renderHandlerList();
    },
    
    /**
     * Render handler list
     */
    renderHandlerList() {
        const container = document.getElementById('handler-list');
        
        if (this.filteredHandlers.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="bi bi-inbox" style="font-size: 3rem;"></i>
                    <p class="mt-3">No handlers found</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.filteredHandlers.map(handler => 
            this.createHandlerCard(handler)
        ).join('');
        
        // Add click listeners
        container.querySelectorAll('.handler-card').forEach((card, index) => {
            card.addEventListener('click', () => {
                this.showHandlerDetails(this.filteredHandlers[index]);
            });
        });
    },
    
    /**
     * Create handler card HTML with real DB metrics
     */
    createHandlerCard(handler) {
        const icon = this.getHandlerIcon(handler.category);
        const usageCount = handler.used_in_workflows || 0;
        const executions = handler.total_executions || 0;
        const successRate = handler.success_rate || 100;
        const avgTime = handler.avg_execution_time_ms || 0;
        
        // Format metrics
        const timeDisplay = avgTime > 0 ? `${avgTime}ms` : 'N/A';
        const successDisplay = executions > 0 ? `${successRate.toFixed(1)}%` : 'N/A';
        
        // Experimental or deprecated badge
        let statusBadge = '';
        if (handler.is_experimental) {
            statusBadge = '<span class="badge bg-warning text-dark ms-2">Experimental</span>';
        } else if (handler.is_deprecated) {
            statusBadge = '<span class="badge bg-danger ms-2">Deprecated</span>';
        }
        
        return `
            <div class="handler-card">
                <div class="handler-card-header">
                    <div class="handler-card-title">
                        <span class="handler-icon">${icon}</span>
                        <h4>${handler.display_name || handler.handler_id}${statusBadge}</h4>
                    </div>
                    <span class="handler-category-badge ${handler.category}">
                        ${handler.category}
                    </span>
                </div>
                <div class="handler-card-description">
                    ${handler.description || 'No description available'}
                </div>
                <div class="handler-card-meta">
                    <span><i class="bi bi-tag"></i> v${handler.version || '1.0'}</span>
                    <span><i class="bi bi-diagram-3"></i> Used in ${usageCount} actions</span>
                    <span><i class="bi bi-lightning-charge"></i> ${executions} executions</span>
                    <span><i class="bi bi-speedometer"></i> ${timeDisplay}</span>
                    <span><i class="bi bi-check-circle"></i> ${successDisplay}</span>
                </div>
            </div>
        `;
    },
    
    /**
     * Get handler icon by category
     */
    getHandlerIcon(category) {
        const icons = {
            input: '📥',
            processing: '⚙️',
            output: '📤'
        };
        return icons[category] || '📦';
    },
    
    /**
     * Show handler details modal
     */
    async showHandlerDetails(handler) {
        this.currentHandler = handler;
        
        // Set title
        document.getElementById('handler-detail-name').textContent = 
            handler.display_name || handler.handler_id;
        
        // Load detailed info
        try {
            const details = await WorkflowAPI.getHandlerDetail(handler.handler_id);
            this.renderHandlerDetails(details);
            this.detailsModal.show();
        } catch (error) {
            console.error('Failed to load handler details:', error);
            this.showError('Failed to load handler details');
        }
    },
    
    /**
     * Render handler details
     */
    renderHandlerDetails(handler) {
        const container = document.getElementById('handler-details-content');
        
        container.innerHTML = `
            <div class="handler-detail-section">
                <h6><i class="bi bi-info-circle"></i> Description</h6>
                <p>${handler.description || 'No description available'}</p>
            </div>
            
            <div class="handler-detail-section">
                <h6><i class="bi bi-tag"></i> Details</h6>
                <ul class="list-unstyled">
                    <li><strong>Category:</strong> ${handler.category}</li>
                    <li><strong>Version:</strong> ${handler.version || '1.0.0'}</li>
                    <li><strong>Handler ID:</strong> <code>${handler.handler_id}</code></li>
                </ul>
            </div>
            
            <div class="handler-detail-section">
                <h6><i class="bi bi-gear"></i> Configuration Schema</h6>
                <pre class="handler-detail-code">${this.formatJSON(handler.config_schema || {})}</pre>
            </div>
            
            <div class="handler-detail-section">
                <h6><i class="bi bi-arrow-right-circle"></i> Input/Output</h6>
                <p><strong>Input:</strong> ${handler.input_type || 'context (Dict)'}</p>
                <p><strong>Output:</strong> ${handler.output_type || 'Dict'}</p>
            </div>
            
            ${handler.used_in_templates && handler.used_in_templates.length > 0 ? `
                <div class="handler-detail-section">
                    <h6><i class="bi bi-diagram-3"></i> Used In</h6>
                    <ul class="handler-usage-list">
                        ${handler.used_in_templates.map(t => `<li>${t}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
        `;
    },
    
    /**
     * Show handler tester
     */
    showHandlerTester() {
        if (!this.currentHandler) return;
        
        // Hide details modal
        this.detailsModal.hide();
        
        // Set handler name
        document.getElementById('tester-handler-name').textContent = 
            this.currentHandler.display_name || this.currentHandler.handler_id;
        
        // Reset inputs
        document.getElementById('test-context-input').value = '{\n  "project_id": 1\n}';
        document.getElementById('test-config-input').value = '{}';
        document.getElementById('test-results-section').style.display = 'none';
        
        // Show tester modal
        this.testerModal.show();
    },
    
    /**
     * Run handler test
     */
    async runHandlerTest() {
        if (!this.currentHandler) return;
        
        try {
            // Get inputs
            const contextStr = document.getElementById('test-context-input').value;
            const configStr = document.getElementById('test-config-input').value;
            
            // Parse JSON
            const context = JSON.parse(contextStr);
            const config = JSON.parse(configStr);
            
            // Show loading
            const resultsSection = document.getElementById('test-results-section');
            const resultsOutput = document.getElementById('test-results-output');
            const statusIcon = document.getElementById('test-status-icon');
            
            resultsSection.style.display = 'block';
            statusIcon.innerHTML = '<i class="bi bi-hourglass-split text-warning"></i>';
            resultsOutput.textContent = 'Running test...';
            
            // Call API (mock for now)
            await this.sleep(1000);
            
            // Mock success result
            const result = {
                success: true,
                execution_time: '123ms',
                output: {
                    title: 'My Fantasy Novel',
                    genre: 'Fantasy',
                    ...context
                }
            };
            
            // Display results
            statusIcon.innerHTML = '<i class="bi bi-check-circle text-success"></i>';
            resultsOutput.textContent = this.formatJSON(result);
            
        } catch (error) {
            // Display error
            const resultsSection = document.getElementById('test-results-section');
            const resultsOutput = document.getElementById('test-results-output');
            const statusIcon = document.getElementById('test-status-icon');
            
            resultsSection.style.display = 'block';
            statusIcon.innerHTML = '<i class="bi bi-x-circle text-danger"></i>';
            resultsOutput.textContent = `Error: ${error.message}`;
        }
    },
    
    /**
     * Format JSON for display
     */
    formatJSON(obj) {
        return JSON.stringify(obj, null, 2);
    },
    
    /**
     * Sleep helper
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },
    
    /**
     * Show error message
     */
    showError(message) {
        // Could use toast or alert
        console.error(message);
    }
};

// Export
window.HandlerBrowser = HandlerBrowser;
