/**
 * Visual Workflow Builder - Main Entry Point
 * Initializes the application and coordinates components
 */

(function() {
    'use strict';

    /**
     * Initialize the workflow builder application
     */
    function init() {
        console.log('Initializing Visual Workflow Builder...');

        // Initialize domain selector
        DomainSelector.init();
        
        // Initialize workflow executor
        if (window.WorkflowExecutor) {
            WorkflowExecutor.init();
        }
        
        // Initialize handler browser
        if (window.HandlerBrowser) {
            HandlerBrowser.init();
        }

        // Setup event listeners
        setupEventListeners();
        
        // Setup navigation
        setupNavigation();

        console.log('Visual Workflow Builder initialized successfully!');
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Back to domains button
        const backButton = document.getElementById('back-to-domains-btn');
        if (backButton) {
            backButton.addEventListener('click', handleBackToDomains);
        }

        // Save workflow button
        const saveButton = document.getElementById('save-workflow-btn');
        if (saveButton) {
            saveButton.addEventListener('click', handleSaveWorkflow);
        }
    }

    /**
     * Handle back to domains navigation
     */
    function handleBackToDomains() {
        // Reset canvas
        WorkflowCanvas.reset();

        // Switch back to domain selection
        DomainSelector.switchScreen('domain-selection-screen');
    }

    /**
     * Handle save workflow action
     */
    function handleSaveWorkflow() {
        const template = WorkflowCanvas.currentTemplate;

        if (!template) {
            alert('No workflow loaded to save.');
            return;
        }

        console.log('Saving workflow:', template);
        alert(`Workflow "${template.name}" would be saved here.\n\nThis feature will be implemented soon!`);
        
        // TODO: Implement save functionality
        // - Allow user to customize workflow
        // TODO: Add save workflow functionality
        console.log('Save workflow clicked');
    }

    /**
     * Setup navigation between screens
     */
    function setupNavigation() {
        // Tab navigation
        const navTabs = document.querySelectorAll('.builder-nav .nav-link');
        navTabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                const screen = tab.dataset.screen;
                switchScreen(screen);
            });
        });
    }
    
    /**
     * Switch between screens
     */
    function switchScreen(screenName) {
        // Update active tab
        const navTabs = document.querySelectorAll('.builder-nav .nav-link');
        navTabs.forEach(tab => {
            if (tab.dataset.screen === screenName) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });
        
        // Hide all screens
        const screens = document.querySelectorAll('.screen');
        screens.forEach(screen => {
            screen.style.display = 'none';
            screen.classList.remove('active');
        });
        
        // Show selected screen
        let targetScreen;
        if (screenName === 'domains') {
            targetScreen = document.getElementById('domain-screen');
        } else if (screenName === 'handlers') {
            targetScreen = document.getElementById('handler-browser-screen');
            // Load handlers when showing handler browser
            if (window.HandlerBrowser) {
                window.HandlerBrowser.show();
            }
        }
        
        if (targetScreen) {
            targetScreen.style.display = 'block';
            targetScreen.classList.add('active');
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
