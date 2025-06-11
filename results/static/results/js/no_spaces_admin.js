/**
 * No Spaces Admin Script
 * Path: results/static/results/js/no_spaces_admin.js
 * 
 * Prevents spaces in admin form fields
 */

(function() {
    'use strict';
    
    /**
     * Remove spaces from input value
     */
    function removeSpaces(input) {
        if (input && input.value) {
            const cursorPosition = input.selectionStart;
            const originalLength = input.value.length;
            input.value = input.value.replace(/\s/g, '');
            const newLength = input.value.length;
            const spacesRemoved = originalLength - newLength;
            
            // Adjust cursor position if spaces were removed before cursor
            if (spacesRemoved > 0) {
                const newCursorPosition = Math.max(0, cursorPosition - spacesRemoved);
                input.setSelectionRange(newCursorPosition, newCursorPosition);
            }
        }
    }
    
    /**
     * Add no-space functionality to an input element
     */
    function makeInputNoSpaces(input) {
        if (!input) return;
        
        // Add visual indicator
        input.style.borderLeft = '3px solid #28a745';
        input.title = 'Spaces are not allowed in this field';
        
        // Handle input event (real-time removal)
        input.addEventListener('input', function(e) {
            removeSpaces(e.target);
        });
        
        // Handle paste event
        input.addEventListener('paste', function(e) {
            setTimeout(() => {
                removeSpaces(e.target);
            }, 10);
        });
        
        // Handle keydown to prevent space key
        input.addEventListener('keydown', function(e) {
            if (e.code === 'Space' || e.key === ' ') {
                e.preventDefault();
                return false;
            }
        });
        
        // Handle blur to clean up any remaining spaces
        input.addEventListener('blur', function(e) {
            removeSpaces(e.target);
        });
    }
    
    /**
     * Initialize no-spaces functionality for all relevant fields
     */
    function initializeNoSpaces() {
        // Target fields that should not have spaces
        const noSpaceSelectors = [
            // General admin fields
            'input[data-no-spaces="true"]',
            'input.no-spaces',
            
            // Specific field names that should never have spaces
            'input[name*="code"]',
            'input[name*="ticket_number"]',
            'input[name*="draw_number"]',
            'input[name*="place"]',
            
            // Inline formset fields
            'input[name*="ticket_number"]',
            'input[name*="place"]',
            
            // Custom admin view fields
            'input[name$="_ticket_number[]"]',
            'input[name$="_place[]"]',
            'input[name="draw_number"]',
            
            // Any text input that has "number" in its name
            'input[type="text"][name*="number"]'
        ];
        
        noSpaceSelectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(input => {
                makeInputNoSpaces(input);
            });
        });
        
        // Also handle dynamically added inline forms
        const inlineGroups = document.querySelectorAll('.inline-group');
        inlineGroups.forEach(group => {
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) { // Element node
                            const inputs = node.querySelectorAll('input[type="text"], input[name*="ticket_number"], input[name*="place"]');
                            inputs.forEach(input => {
                                makeInputNoSpaces(input);
                            });
                        }
                    });
                });
            });
            
            observer.observe(group, {
                childList: true,
                subtree: true
            });
        });
    }
    
    /**
     * Add no-spaces functionality to lottery admin custom views
     */
    function initializeLotteryAdminNoSpaces() {
        // Handle custom lottery admin form
        const lotteryForm = document.getElementById('lotteryForm');
        if (lotteryForm) {
            const fieldsToRestrict = [
                'input[name="draw_number"]',
                'input[name$="_ticket_number[]"]',
                'input[name$="_place[]"]'
            ];
            
            fieldsToRestrict.forEach(selector => {
                lotteryForm.querySelectorAll(selector).forEach(input => {
                    makeInputNoSpaces(input);
                });
            });
            
            // Monitor for dynamically added entries
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) {
                            fieldsToRestrict.forEach(selector => {
                                const inputs = node.querySelectorAll ? node.querySelectorAll(selector) : [];
                                inputs.forEach(input => {
                                    makeInputNoSpaces(input);
                                });
                            });
                        }
                    });
                });
            });
            
            observer.observe(lotteryForm, {
                childList: true,
                subtree: true
            });
        }
    }
    
    /**
     * Show notification when spaces are prevented
     */
    function showSpacePreventedNotification() {
        let notification = document.getElementById('space-prevented-notification');
        
        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'space-prevented-notification';
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #ffc107;
                color: #856404;
                padding: 10px 15px;
                border-radius: 4px;
                font-size: 13px;
                z-index: 9999;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                opacity: 0;
                transition: opacity 0.3s ease;
            `;
            notification.innerHTML = '⚠️ Spaces are not allowed in this field';
            document.body.appendChild(notification);
        }
        
        notification.style.opacity = '1';
        
        setTimeout(() => {
            notification.style.opacity = '0';
        }, 2000);
    }
    
    /**
     * Initialize everything when DOM is ready
     */
    function initialize() {
        initializeNoSpaces();
        initializeLotteryAdminNoSpaces();
        
        // Add global event listener for space key prevention feedback
        document.addEventListener('keydown', function(e) {
            if ((e.code === 'Space' || e.key === ' ') && 
                e.target.matches('input[data-no-spaces="true"], input.no-spaces, input[name*="ticket_number"], input[name*="place"], input[name*="code"], input[name*="draw_number"]')) {
                showSpacePreventedNotification();
            }
        });
        
        console.log('No-spaces admin functionality initialized');
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
    
    // Also initialize when page is fully loaded (for dynamic content)
    window.addEventListener('load', initialize);
    
})();