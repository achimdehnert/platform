/**
 * BF Agent Error Interceptor
 * Catches Django debug errors and shows a bug report button overlay
 * Works in DEBUG=True mode where Django shows its error pages
 */

(function() {
    'use strict';
    
    // Check if we're on a Django debug error page
    function isDjangoErrorPage() {
        return document.querySelector('#summary h1, .exception_value, #traceback') !== null;
    }
    
    // Extract error info from Django debug page
    function extractErrorInfo() {
        const exceptionValue = document.querySelector('.exception_value')?.textContent?.trim() || '';
        const exceptionType = document.querySelector('#summary h1')?.textContent?.trim() || 'Unknown Error';
        const requestUrl = document.querySelector('#requestinfo td')?.textContent?.trim() || window.location.href;
        const traceback = document.querySelector('#traceback_area, .traceback')?.textContent?.trim()?.substring(0, 2000) || '';
        
        return {
            type: exceptionType,
            value: exceptionValue,
            url: requestUrl,
            traceback: traceback
        };
    }
    
    // Create and inject the bug report overlay
    function injectBugReportOverlay() {
        const errorInfo = extractErrorInfo();
        
        // Create overlay container
        const overlay = document.createElement('div');
        overlay.id = 'bfagent-error-overlay';
        overlay.innerHTML = `
            <style>
                #bfagent-error-overlay {
                    position: fixed;
                    top: 10px;
                    right: 10px;
                    z-index: 99999;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                #bfagent-error-overlay .bug-btn {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 12px 20px;
                    background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
                    color: white;
                    border: none;
                    border-radius: 50px;
                    font-size: 14px;
                    font-weight: 600;
                    cursor: pointer;
                    box-shadow: 0 4px 15px rgba(220, 53, 69, 0.4);
                    transition: all 0.2s ease;
                    text-decoration: none;
                }
                #bfagent-error-overlay .bug-btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(220, 53, 69, 0.5);
                }
                #bfagent-error-overlay .bug-btn svg {
                    width: 18px;
                    height: 18px;
                }
                #bfagent-error-overlay .shortcut {
                    font-size: 11px;
                    opacity: 0.8;
                    margin-left: 4px;
                }
            </style>
            <a href="#" class="bug-btn" id="bfagent-report-bug">
                <svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M4.355.522a.5.5 0 0 1 .623.333l.291.956A4.979 4.979 0 0 1 8 1c1.007 0 1.946.298 2.731.811l.29-.956a.5.5 0 1 1 .957.29l-.41 1.352A4.985 4.985 0 0 1 13 6h.5a.5.5 0 0 0 .5-.5V5a.5.5 0 0 1 1 0v.5A1.5 1.5 0 0 1 13.5 7H13v1h1.5a.5.5 0 0 1 0 1H13v1h.5a1.5 1.5 0 0 1 1.5 1.5v.5a.5.5 0 1 1-1 0v-.5a.5.5 0 0 0-.5-.5H13a5 5 0 0 1-10 0h-.5a.5.5 0 0 0-.5.5v.5a.5.5 0 1 1-1 0v-.5A1.5 1.5 0 0 1 2.5 10H3V9H1.5a.5.5 0 0 1 0-1H3V7h-.5A1.5 1.5 0 0 1 1 5.5V5a.5.5 0 0 1 1 0v.5a.5.5 0 0 0 .5.5H3a5 5 0 0 1 1.568-3.644l-.41-1.352a.5.5 0 0 1 .333-.623zM9 12.5a1.5 1.5 0 1 0-3 0 1.5 1.5 0 0 0 3 0zm-.5-8a.5.5 0 0 0-1 0V8a.5.5 0 0 0 1 0V4.5z"/>
                </svg>
                Bug melden
                <span class="shortcut">(Ctrl+B)</span>
            </a>
        `;
        
        document.body.appendChild(overlay);
        
        // Click handler
        document.getElementById('bfagent-report-bug').addEventListener('click', function(e) {
            e.preventDefault();
            openBugReport(errorInfo);
        });
        
        // Keyboard shortcut: Ctrl+B
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'b') {
                e.preventDefault();
                openBugReport(errorInfo);
            }
        });
    }
    
    // Open bug report page with pre-filled data
    function openBugReport(errorInfo) {
        const params = new URLSearchParams({
            source_url: window.location.href,
            name: (errorInfo.type + ': ' + errorInfo.value).substring(0, 200),
            category: 'bug',
            priority: 'high',
            error_message: errorInfo.traceback.substring(0, 1000)
        });
        
        window.location.href = '/bfagent/test-studio/requirements/create/?' + params.toString();
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            if (isDjangoErrorPage()) {
                injectBugReportOverlay();
            }
        });
    } else {
        if (isDjangoErrorPage()) {
            injectBugReportOverlay();
        }
    }
    
    // Also handle window errors for JS errors
    window.addEventListener('error', function(e) {
        console.log('[BF Agent] JavaScript Error captured:', e.message);
    });
    
})();
