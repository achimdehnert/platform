/**
 * MCP Dashboard JavaScript
 * ========================
 * 
 * HTMX-native interactions - no fetch() calls needed.
 * 
 * This file handles:
 * - SSE event processing
 * - Toast notifications
 * - Modal management
 * - Keyboard shortcuts
 */

(function() {
    'use strict';
    
    // =========================================================================
    // INITIALIZATION
    // =========================================================================
    
    document.addEventListener('DOMContentLoaded', function() {
        initializeKeyboardShortcuts();
        initializeTooltips();
        setupSSEHandlers();
    });
    
    // =========================================================================
    // SSE (Server-Sent Events) HANDLERS
    // =========================================================================
    
    function setupSSEHandlers() {
        // Session updates from SSE
        document.body.addEventListener('session-update', function(evt) {
            try {
                const data = JSON.parse(evt.detail.data);
                const row = document.getElementById(`session-row-${data.session_id}`);
                if (row) {
                    row.innerHTML = data.html;
                    // Highlight updated row briefly
                    row.classList.add('table-warning');
                    setTimeout(() => row.classList.remove('table-warning'), 2000);
                }
            } catch (e) {
                console.error('Failed to process session update:', e);
            }
        });
        
        // Stats updates from SSE
        document.body.addEventListener('stats-update', function(evt) {
            try {
                const data = JSON.parse(evt.detail.data);
                const container = document.getElementById('stats-container');
                if (container && data.html) {
                    container.innerHTML = data.html;
                }
            } catch (e) {
                console.error('Failed to process stats update:', e);
            }
        });
    }
    
    // =========================================================================
    // TOAST NOTIFICATIONS
    // =========================================================================
    
    window.showToast = function(message, level = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        
        const bgClasses = {
            success: 'text-bg-success',
            error: 'text-bg-danger',
            warning: 'text-bg-warning',
            info: 'text-bg-info'
        };
        
        const toastId = 'toast-' + Date.now();
        
        const toastHtml = `
            <div id="${toastId}" class="toast show align-items-center ${bgClasses[level] || bgClasses.info} border-0" 
                 role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        <span class="me-2">${icons[level] || icons.info}</span>
                        ${escapeHtml(message)}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                            data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', toastHtml);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            const toast = document.getElementById(toastId);
            if (toast) {
                toast.classList.add('hiding');
                setTimeout(() => toast.remove(), 300);
            }
        }, 5000);
    };
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // =========================================================================
    // HTMX EVENT HANDLERS
    // =========================================================================
    
    // Show toast on HTMX trigger
    document.body.addEventListener('htmx:trigger', function(evt) {
        if (evt.detail.name === 'showToast') {
            const { message, level } = evt.detail.value;
            showToast(message, level);
        }
    });
    
    // Handle HTMX errors
    document.body.addEventListener('htmx:responseError', function(evt) {
        console.error('HTMX Response Error:', evt.detail);
        showToast('Request failed. Please try again.', 'error');
    });
    
    // Handle HTMX timeout
    document.body.addEventListener('htmx:timeout', function(evt) {
        console.error('HTMX Timeout:', evt.detail);
        showToast('Request timed out. Please try again.', 'warning');
    });
    
    // Before request - add loading state
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        const target = evt.detail.elt;
        if (target.tagName === 'BUTTON') {
            target.dataset.originalText = target.innerHTML;
            target.disabled = true;
        }
    });
    
    // After request - remove loading state
    document.body.addEventListener('htmx:afterRequest', function(evt) {
        const target = evt.detail.elt;
        if (target.tagName === 'BUTTON' && target.dataset.originalText) {
            target.disabled = false;
            // Keep disabled if response indicated to stay disabled
            if (!evt.detail.xhr.getResponseHeader('X-Keep-Disabled')) {
                target.innerHTML = target.dataset.originalText;
            }
        }
    });
    
    // =========================================================================
    // MODALS
    // =========================================================================
    
    window.openModal = function(url) {
        const container = document.getElementById('modal-container');
        if (!container) return;
        
        htmx.ajax('GET', url, {
            target: '#modal-container',
            swap: 'innerHTML'
        }).then(() => {
            const modal = new bootstrap.Modal(container);
            modal.show();
        });
    };
    
    window.closeModal = function() {
        const container = document.getElementById('modal-container');
        if (container) {
            const modal = bootstrap.Modal.getInstance(container);
            if (modal) modal.hide();
        }
    };
    
    // Close modal on successful form submission
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        if (evt.detail.xhr.getResponseHeader('X-Close-Modal') === 'true') {
            closeModal();
        }
    });
    
    // =========================================================================
    // KEYBOARD SHORTCUTS
    // =========================================================================
    
    function initializeKeyboardShortcuts() {
        document.addEventListener('keydown', function(evt) {
            // Only when not in input fields
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
                return;
            }
            
            // Escape - close modal
            if (evt.key === 'Escape') {
                closeModal();
            }
            
            // Ctrl/Cmd + S - sync data
            if ((evt.ctrlKey || evt.metaKey) && evt.key === 's') {
                evt.preventDefault();
                const syncBtn = document.querySelector('[hx-post*="sync"]');
                if (syncBtn) syncBtn.click();
            }
            
            // R - refresh stats
            if (evt.key === 'r' && !evt.ctrlKey && !evt.metaKey) {
                const statsContainer = document.getElementById('stats-container');
                if (statsContainer) {
                    htmx.trigger(statsContainer, 'refresh');
                }
            }
        });
    }
    
    // =========================================================================
    // TOOLTIPS
    // =========================================================================
    
    function initializeTooltips() {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltipTriggerList.forEach(function(tooltipTriggerEl) {
            new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Reinitialize tooltips after HTMX swap
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        initializeTooltips();
    });
    
    // =========================================================================
    // UTILITY FUNCTIONS
    // =========================================================================
    
    // Format duration
    window.formatDuration = function(seconds) {
        if (seconds < 60) return `${seconds}s`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
        const hours = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${mins}m`;
    };
    
    // Format file size
    window.formatFileSize = function(bytes) {
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        return `${size.toFixed(1)} ${units[unitIndex]}`;
    };
    
    // =========================================================================
    // CONFIRM DIALOGS (Enhanced)
    // =========================================================================
    
    // Override default confirm for HTMX
    document.body.addEventListener('htmx:confirm', function(evt) {
        const message = evt.detail.question;
        
        // Use custom confirm dialog if available
        if (typeof Swal !== 'undefined') {
            evt.preventDefault();
            
            Swal.fire({
                title: 'Confirm',
                text: message,
                icon: 'question',
                showCancelButton: true,
                confirmButtonColor: '#4f46e5',
                cancelButtonColor: '#6b7280',
                confirmButtonText: 'Yes, proceed',
                cancelButtonText: 'Cancel'
            }).then((result) => {
                if (result.isConfirmed) {
                    evt.detail.issueRequest();
                }
            });
        }
    });
    
})();
