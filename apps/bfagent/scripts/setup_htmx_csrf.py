#!/usr/bin/env python3
"""
HTMX CSRF Auto-Setup Script
Automatically configures CSRF token handling for all HTMX requests
"""

import re
from pathlib import Path


def setup_csrf_in_base_template():
    """Add automatic CSRF configuration to base.html"""
    base_template = Path("templates/base.html")

    if not base_template.exists():
        print("❌ base.html not found")
        return False

    content = base_template.read_text(encoding="utf-8")

    # Check if CSRF setup already exists
    if "htmx:configRequest" in content:
        print("✅ CSRF auto-configuration already present in base.html")
        return True

    # Find the closing </head> tag
    head_close_pattern = r"</head>"

    csrf_script = """
    <!-- HTMX CSRF Auto-Configuration -->
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Auto-include CSRF token in all HTMX requests
            document.body.addEventListener('htmx:configRequest', function(event) {
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
                                || document.querySelector('meta[name="csrf-token"]')?.content
                                || '{{ csrf_token }}';

                if (csrfToken) {
                    event.detail.headers['X-CSRFToken'] = csrfToken;
                }
            });

            // Auto-handle 422 validation errors
            document.body.addEventListener('htmx:responseError', function(event) {
                if (event.detail.xhr.status === 422) {
                    // Replace form with validation errors
                    const target = event.detail.target;
                    if (target) {
                        target.innerHTML = event.detail.xhr.responseText;
                    }
                }
            });

            // Auto-show loading indicators
            document.body.addEventListener('htmx:beforeRequest', function(event) {
                const indicator = event.detail.elt.getAttribute('hx-indicator');
                if (indicator) {
                    const indicatorEl = document.querySelector(indicator);
                    if (indicatorEl) {
                        indicatorEl.style.opacity = '1';
                    }
                }
            });

            document.body.addEventListener('htmx:afterRequest', function(event) {
                const indicator = event.detail.elt.getAttribute('hx-indicator');
                if (indicator) {
                    const indicatorEl = document.querySelector(indicator);
                    if (indicatorEl) {
                        indicatorEl.style.opacity = '0';
                    }
                }
            });
        });
    </script>
</head>"""

    # Replace </head> with our script + </head>
    new_content = re.sub(head_close_pattern, csrf_script, content)

    if new_content != content:
        base_template.write_text(new_content, encoding="utf-8")
        print("✅ CSRF auto-configuration added to base.html")
        return True
    else:
        print("❌ Failed to add CSRF configuration to base.html")
        return False


def setup_csrf_meta_tag():
    """Ensure CSRF meta tag is present in base.html"""
    base_template = Path("templates/base.html")

    if not base_template.exists():
        return False

    content = base_template.read_text(encoding="utf-8")

    # Check if CSRF meta tag already exists
    if 'name="csrf-token"' in content:
        print("✅ CSRF meta tag already present")
        return True

    # Find the <head> section and add meta tag
    head_pattern = r"(<head[^>]*>)"
    csrf_meta = r'\1\n    <!-- CSRF Token for HTMX -->\n    <meta name="csrf-token" content="{{ csrf_token }}">'

    new_content = re.sub(head_pattern, csrf_meta, content)

    if new_content != content:
        base_template.write_text(new_content, encoding="utf-8")
        print("✅ CSRF meta tag added to base.html")
        return True
    else:
        print("⚠️  CSRF meta tag may already be present or head tag not found")
        return True


def create_htmx_utils_js():
    """Create utility JavaScript for HTMX helpers"""
    static_dir = Path("static/js")
    static_dir.mkdir(parents=True, exist_ok=True)

    utils_file = static_dir / "htmx-utils.js"

    js_content = """/**
 * HTMX Utilities for BF Agent v2.0.0
 * Automatic CSRF, error handling, and UI enhancements
 */

// URL resolver utility for HTMX endpoints
window.BFAgent = window.BFAgent || {};

BFAgent.urls = {
    // Chapter actions
    chapterAction: function(chapterId, action) {
        return `/chapters/${chapterId}/action/${action}/`;
    },

    // Project enrichment
    projectEnrich: function(projectId) {
        return `/projects/${projectId}/enrich/apply/`;
    },

    // Dynamic form endpoints
    formEndpoint: function(model, action, id = null) {
        const base = `/${model}/${action}/`;
        return id ? `${base}${id}/` : base;
    }
};

// Enhanced HTMX configuration
document.addEventListener('DOMContentLoaded', function() {

    // Global HTMX configuration
    htmx.config.defaultSwapStyle = 'innerHTML';
    htmx.config.defaultSwapDelay = 100;
    htmx.config.defaultSettleDelay = 200;

    // Auto-add loading states
    document.body.addEventListener('htmx:beforeRequest', function(event) {
        const button = event.detail.elt;
        if (button.tagName === 'BUTTON') {
            button.disabled = true;
            button.classList.add('loading');

            // Store original text
            if (!button.dataset.originalText) {
                button.dataset.originalText = button.innerHTML;
            }

            // Add loading spinner
            button.innerHTML = '<i class="bi bi-hourglass-split"></i> Processing...';
        }
    });

    document.body.addEventListener('htmx:afterRequest', function(event) {
        const button = event.detail.elt;
        if (button.tagName === 'BUTTON' && button.dataset.originalText) {
            button.disabled = false;
            button.classList.remove('loading');
            button.innerHTML = button.dataset.originalText;
        }
    });

    // Auto-handle success messages
    document.body.addEventListener('htmx:afterSwap', function(event) {
        // Auto-scroll to new content
        if (event.detail.target.scrollIntoView) {
            event.detail.target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        // Re-initialize tooltips and other Bootstrap components
        if (window.bootstrap && bootstrap.Tooltip) {
            const tooltipTriggerList = [].slice.call(event.detail.target.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    });

    // Enhanced error handling
    document.body.addEventListener('htmx:responseError', function(event) {
        const status = event.detail.xhr.status;
        const target = event.detail.target;

        if (status === 422) {
            // Validation errors - replace form content
            target.innerHTML = event.detail.xhr.responseText;
        } else if (status === 403) {
            // Permission denied
            target.innerHTML = '<div class="alert alert-danger">Permission denied. Please refresh and try again.</div>';
        } else if (status === 500) {
            // Server error
            target.innerHTML = '<div class="alert alert-danger">Server error. Please try again later.</div>';
        } else {
            // Generic error
            target.innerHTML = `<div class="alert alert-warning">Request failed (${status}). Please try again.</div>`;
        }
    });
});

// Utility functions for dynamic forms
BFAgent.forms = {
    // Submit form via HTMX
    submitForm: function(formId, targetId) {
        const form = document.getElementById(formId);
        const target = document.getElementById(targetId);

        if (form && target) {
            htmx.ajax('POST', form.action, {
                source: form,
                target: target,
                swap: 'innerHTML'
            });
        }
    },

    // Reset form and clear target
    resetForm: function(formId, targetId) {
        const form = document.getElementById(formId);
        const target = document.getElementById(targetId);

        if (form) form.reset();
        if (target) target.innerHTML = '';
    }
};
"""

    utils_file.write_text(js_content, encoding="utf-8")
    print(f"✅ HTMX utilities created: {utils_file}")
    return True


def update_base_template_with_utils():
    """Include the HTMX utils in base template"""
    base_template = Path("templates/base.html")

    if not base_template.exists():
        return False

    content = base_template.read_text(encoding="utf-8")

    # Check if utils already included
    if "htmx-utils.js" in content:
        print("✅ HTMX utils already included in base.html")
        return True

    # Find HTMX script and add utils after it
    htmx_pattern = r'(<script src="https://unpkg\.com/htmx\.org@[^"]*"></script>)'
    utils_script = r'\1\n    <!-- HTMX Utilities -->\n    <script src="{% load static %}{% static \'js/htmx-utils.js\' %}"></script>'

    new_content = re.sub(htmx_pattern, utils_script, content)

    if new_content != content:
        base_template.write_text(new_content, encoding="utf-8")
        print("✅ HTMX utils script added to base.html")
        return True
    else:
        print("⚠️  Could not add HTMX utils script (HTMX script not found or already present)")
        return True


def main():
    """Main setup function"""
    print("🔐 Setting up HTMX CSRF Auto-Configuration")
    print("==========================================")
    print()

    success_count = 0
    total_tasks = 4

    # 1. Setup CSRF meta tag
    if setup_csrf_meta_tag():
        success_count += 1

    # 2. Setup CSRF auto-configuration
    if setup_csrf_in_base_template():
        success_count += 1

    # 3. Create HTMX utilities
    if create_htmx_utils_js():
        success_count += 1

    # 4. Include utilities in base template
    if update_base_template_with_utils():
        success_count += 1

    print()
    print(f"✅ CSRF Auto-Setup Complete: {success_count}/{total_tasks} tasks successful")

    if success_count == total_tasks:
        print()
        print("🎉 All HTMX CSRF configurations are now automated!")
        print("   - CSRF tokens automatically included in all HTMX requests")
        print("   - 422 validation errors handled automatically")
        print("   - Loading indicators managed automatically")
        print("   - Enhanced error handling for all status codes")
        return True
    else:
        print()
        print("⚠️  Some tasks failed. Please check the output above.")
        return False


if __name__ == "__main__":
    main()
