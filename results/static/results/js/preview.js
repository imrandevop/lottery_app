/**
 * Preview Functionality JavaScript
 * Path: results/static/results/js/preview.js
 * 
 * This file handles all preview-related functionality for the lottery admin panel.
 * Separated for better code organization and maintainability.
 */

// Preview state
let previewVisible = false;

/**
 * Initialize preview functionality
 */
function initPreview() {
    // Set up form change listeners for preview updates
    setupPreviewListeners();
    
    console.log('Preview functionality initialized');
}

/**
 * Toggle preview visibility
 */
function togglePreview() {
    const previewSection = document.getElementById('preview-section');
    const previewBtn = document.querySelector('.preview-toggle-btn');
    const btnText = document.getElementById('preview-btn-text');
    
    previewVisible = !previewVisible;
    
    if (previewVisible) {
        previewSection.classList.add('visible');
        previewBtn.classList.add('active');
        btnText.innerHTML = '🙈 Hide Preview';
        updatePreview();
        
        // Scroll to preview with smooth animation
        setTimeout(() => {
            previewSection.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center' 
            });
        }, 300);
    } else {
        previewSection.classList.remove('visible');
        previewBtn.classList.remove('active');
        btnText.innerHTML = '👁️ Show Preview';
    }
}

/**
 * Update the preview with current form data
 */
function updatePreview() {
    if (!previewVisible) return;
    
    const container = document.getElementById('mobile-preview-container');
    if (!container) return;
    
    // Get form data
    const formData = collectFormData();
    
    // Generate preview HTML
    const previewHTML = generatePreviewHTML(formData);
    
    // Update container
    container.innerHTML = previewHTML;
}

/**
 * Collect all form data for preview
 * @returns {Object} Collected form data
 */
function collectFormData() {
    const data = {
        lottery: document.querySelector('#lottery option:checked')?.text || '',
        date: document.getElementById('date')?.value || '',
        drawNumber: document.getElementById('draw_number')?.value || '',
        isPublished: document.getElementById('published')?.checked || false,
        prizes: {}
    };
    
    // Format date
    if (data.date) {
        const dateObj = new Date(data.date);
        data.formattedDate = dateObj.toLocaleDateString('en-GB', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    }
    
    // Collect prize data
    const prizeTypes = ['1st', '2nd', '3rd', 'consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th'];
    
    prizeTypes.forEach(prizeType => {
        const entriesContainer = document.getElementById(prizeType + '-entries');
        if (!entriesContainer) return;
        
        const entries = entriesContainer.querySelectorAll('.prize-entry');
        const prizeData = [];
        
        entries.forEach(entry => {
            const inputs = entry.querySelectorAll('input');
            const amount = inputs[0]?.value?.trim();
            const ticket = inputs[1]?.value?.trim();
            const place = inputs[2]?.value?.trim();
            
            if (amount || ticket) {
                prizeData.push({ amount, ticket, place });
            }
        });
        
        if (prizeData.length > 0) {
            data.prizes[prizeType] = prizeData;
        }
    });
    
    return data;
}

/**
 * Generate preview HTML from form data
 * @param {Object} data - Form data
 * @returns {string} Generated HTML
 */
function generatePreviewHTML(data) {
    let html = '';
    
    // Generate header if we have basic data
    if (data.date || data.drawNumber) {
        html += `
            <div class="mobile-header">
                <div class="date">${data.formattedDate || 'No Date'}</div>
                <div class="draw-number"># ${data.drawNumber || 'No Draw Number'}</div>
            </div>
        `;
    }
    
    // Generate prize cards
    const prizeOrder = ['1st', '2nd', '3rd', 'consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th'];
    const prizeNames = {
        '1st': '1st Prize',
        '2nd': '2nd Prize', 
        '3rd': '3rd Prize',
        '4th': '4th Prize',
        '5th': '5th Prize',
        '6th': '6th Prize',
        '7th': '7th Prize',
        '8th': '8th Prize',
        '9th': '9th Prize',
        '10th': '10th Prize',
        'consolation': 'Consolation Prize'
    };
    
    let hasAnyData = false;
    
    prizeOrder.forEach(prizeType => {
        if (data.prizes[prizeType]) {
            html += generatePrizeCard(prizeType, prizeNames[prizeType], data.prizes[prizeType]);
            hasAnyData = true;
        }
    });
    
    // Show no data message if needed
    if (!hasAnyData) {
        html = '<div class="no-data-message">Fill in the form data to see the preview</div>';
    }
    
    return html;
}

/**
 * Generate HTML for a single prize card
 * @param {string} prizeType - Type of prize
 * @param {string} prizeName - Display name of prize
 * @param {Array} prizeData - Array of prize entries
 * @returns {string} Generated HTML
 */
function generatePrizeCard(prizeType, prizeName, prizeData) {
    const amount = prizeData[0]?.amount || '';
    const formattedAmount = amount ? formatCurrency(parseInt(amount)) : '₹0/-';
    
    let numbersHTML = '';
    
    if (prizeType === 'consolation') {
        // Consolation prizes in grid format
        numbersHTML = '<div class="consolation-grid">';
        prizeData.forEach(data => {
            if (data.ticket) {
                numbersHTML += `<div class="consolation-number">${data.ticket}</div>`;
            }
        });
        numbersHTML += '</div>';
    } else if (prizeType === '1st' || prizeType === '2nd' || prizeType === '3rd') {
        // Top prizes with places
        prizeData.forEach(data => {
            if (data.ticket) {
                numbersHTML += `
                    <div class="winning-number with-place">
                        <span class="ticket-number">${data.ticket}</span>
                        ${data.place ? `<span class="place-name">${data.place}</span>` : ''}
                    </div>
                `;
            }
        });
    } else {
        // Other prizes - use grid if many numbers
        if (prizeData.length > 4) {
            numbersHTML = '<div class="multiple-numbers-grid">';
            prizeData.forEach(data => {
                if (data.ticket) {
                    numbersHTML += `<div class="number-item">${data.ticket}</div>`;
                }
            });
            numbersHTML += '</div>';
        } else {
            prizeData.forEach(data => {
                if (data.ticket) {
                    numbersHTML += `<div class="winning-number"><span class="ticket-number">${data.ticket}</span></div>`;
                }
            });
        }
    }
    
    return `
        <div class="prize-card">
            <div class="prize-header">${prizeName}</div>
            <div class="prize-content">
                <div class="prize-amount">${formattedAmount}</div>
                <div class="winning-numbers">${numbersHTML}</div>
            </div>
        </div>
    `;
}

/**
 * Format currency in Indian format
 * @param {number} amount - Amount to format
 * @returns {string} Formatted currency string
 */
function formatCurrency(amount) {
    if (isNaN(amount)) return '₹0/-';
    return `₹${amount.toLocaleString('en-IN')}/-`;
}

/**
 * Set up event listeners for form elements to update preview
 */
function setupPreviewListeners() {
    // Basic form fields
    const basicFields = ['#lottery', '#date', '#draw_number', '#published'];
    basicFields.forEach(selector => {
        const element = document.querySelector(selector);
        if (element) {
            element.addEventListener('change', updatePreview);
            element.addEventListener('input', updatePreview);
        }
    });
    
    // Prize entry fields (setup on existing entries)
    setupPrizeFieldListeners();
}

/**
 * Set up listeners on prize entry fields
 */
function setupPrizeFieldListeners() {
    const prizeInputs = document.querySelectorAll('[id*="_prize_amount"], [id*="_ticket_number"], [id*="_place"]');
    prizeInputs.forEach(input => {
        input.addEventListener('change', updatePreview);
        input.addEventListener('input', debounce(updatePreview, 300)); // Debounced for typing
    });
}

/**
 * Enhanced addEntry function that includes preview listeners
 * This extends the original addEntry function
 */
function addEntryWithPreview(prizeType) {
    // Call the original addEntry function if it exists
    if (typeof window.originalAddEntry === 'function') {
        window.originalAddEntry(prizeType);
    } else if (typeof window.addEntry === 'function') {
        window.addEntry(prizeType);
    }
    
    // Set up listeners on the new entry
    setTimeout(() => {
        setupPrizeFieldListeners();
        updatePreview();
    }, 100);
}

/**
 * Enhanced bulk processing with preview update
 */
function processBulkEntriesWithPreview(prizeType) {
    // Call the original processBulkEntries function
    if (typeof window.processBulkEntries === 'function') {
        window.processBulkEntries(prizeType);
    }
    
    // Update preview after bulk processing
    setTimeout(() => {
        setupPrizeFieldListeners();
        updatePreview();
    }, 200);
}

/**
 * Debounce function to limit frequent updates
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Initialize preview when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize preview functionality
    initPreview();
    
    // Override addEntry calls to include preview updates
    const addEntryBtns = document.querySelectorAll('button[onclick*="addEntry"]');
    addEntryBtns.forEach(btn => {
        const onclick = btn.getAttribute('onclick');
        const prizeType = onclick.match(/addEntry\('([^']+)'\)/)?.[1];
        if (prizeType) {
            btn.setAttribute('onclick', `addEntryWithPreview('${prizeType}')`);
        }
    });
    
    // Override bulk processing calls
    const bulkBtns = document.querySelectorAll('button[onclick*="processBulkEntries"]');
    bulkBtns.forEach(btn => {
        const onclick = btn.getAttribute('onclick');
        const prizeType = onclick.match(/processBulkEntries\('([^']+)'\)/)?.[1];
        if (prizeType) {
            btn.setAttribute('onclick', `processBulkEntriesWithPreview('${prizeType}')`);
        }
    });
    
    console.log('Preview event listeners setup complete');
});