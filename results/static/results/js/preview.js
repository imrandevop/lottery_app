/**
 * Preview Section JavaScript
 * Path: results/static/results/js/preview.js
 * 
 * Handles lottery result preview functionality with simple responsive design
 */

// Preview state management
let previewVisible = false;
let previewData = {};

/**
 * Initialize preview functionality when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    initializePreview();
    console.log('Preview functionality initialized');
});

/**
 * Initialize all preview functionality
 */
function initializePreview() {
    setupFormListeners();
    loadExistingData();
    
    // Override existing button handlers to include preview updates
    overrideFormHandlers();
    
    // Set up periodic preview updates for better UX
    setInterval(updatePreviewIfVisible, 2000);
}

/**
 * Toggle preview visibility
 */
function togglePreview() {
    const previewSection = document.getElementById('preview-section');
    const previewBtn = document.querySelector('.preview-toggle-btn');
    const btnText = document.getElementById('preview-btn-text');
    const statusText = document.getElementById('preview-status');
    
    if (!previewSection) {
        console.error('Preview section not found');
        return;
    }
    
    previewVisible = !previewVisible;
    
    if (previewVisible) {
        previewSection.style.display = 'block';
        previewBtn.classList.add('active');
        btnText.textContent = 'Hide Preview';
        statusText.textContent = 'Preview visible';
        
        // Initialize preview content if not already done
        initializePreviewContent();
        updatePreview();
        
        // Simple scroll to preview without animation
        previewSection.scrollIntoView({ block: 'start' });
    } else {
        previewSection.style.display = 'none';
        previewBtn.classList.remove('active');
        btnText.textContent = 'Show Preview';
        statusText.textContent = 'Preview hidden';
    }
    
    console.log(`Preview ${previewVisible ? 'shown' : 'hidden'}`);
}

/**
 * Initialize preview content structure
 */
function initializePreviewContent() {
    const previewContent = document.getElementById('preview-content');
    
    if (!previewContent || previewContent.innerHTML.trim() !== '') {
        return; // Already initialized or content exists
    }
    
    previewContent.innerHTML = `
        <div class="preview-wrapper">
            <!-- Desktop Preview -->
            <div class="preview-container" id="preview-container">
                <div class="preview-placeholder">
                    <div class="placeholder-icon">📋</div>
                    <h3>Lottery Result Preview</h3>
                    <p>Fill in the form data to see the live preview</p>
                </div>
            </div>
        </div>
    `;
    
    console.log('Preview content structure initialized');
}

/**
 * Update preview if currently visible
 */
function updatePreviewIfVisible() {
    if (previewVisible) {
        updatePreview();
    }
}

/**
 * Main preview update function
 */
function updatePreview() {
    if (!previewVisible) return;
    
    try {
        // Collect current form data
        const formData = collectFormData();
        
        // Check if data has changed significantly
        if (!hasDataChanged(formData)) {
            return;
        }
        
        // Update preview data
        previewData = formData;
        
        // Generate and update preview HTML
        updatePreviewHTML(formData);
        
        console.log('Preview updated:', formData);
    } catch (error) {
        console.error('Error updating preview:', error);
        showPreviewError('Error updating preview');
    }
}

/**
 * Check if form data has changed significantly
 */
function hasDataChanged(newData) {
    // Simple comparison - you might want to make this more sophisticated
    return JSON.stringify(newData) !== JSON.stringify(previewData);
}

/**
 * Collect all form data for preview
 */
function collectFormData() {
    const data = {
        lottery: getLotteryName(),
        date: getFormValue('#date, input[name="date"]'),
        drawNumber: getFormValue('#draw_number, input[name="draw_number"]'),
        isPublished: getCheckboxValue('#published, input[name="is_published"]'),
        prizes: collectPrizeData()
    };
    
    // Format date for display
    if (data.date) {
        data.formattedDate = formatDateForDisplay(data.date);
    }
    
    return data;
}

/**
 * Get lottery name from select element
 */
function getLotteryName() {
    const lotterySelect = document.querySelector('#lottery, select[name="lottery"]');
    if (lotterySelect && lotterySelect.selectedIndex > 0) {
        return lotterySelect.options[lotterySelect.selectedIndex].text;
    }
    return '';
}

/**
 * Get form field value safely
 */
function getFormValue(selector) {
    const element = document.querySelector(selector);
    return element ? element.value.trim() : '';
}

/**
 * Get checkbox value safely
 */
function getCheckboxValue(selector) {
    const element = document.querySelector(selector);
    return element ? element.checked : false;
}

/**
 * Format date for display
 */
function formatDateForDisplay(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-GB', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    } catch (e) {
        return dateString;
    }
}

/**
 * Collect prize data from all prize sections
 */
function collectPrizeData() {
    const prizes = {};
    const prizeTypes = ['1st', '2nd', '3rd', 'consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th'];
    
    prizeTypes.forEach(prizeType => {
        const entries = collectPrizeEntriesForType(prizeType);
        if (entries.length > 0) {
            prizes[prizeType] = entries;
        }
    });
    
    return prizes;
}

/**
 * Collect prize entries for a specific prize type
 */
function collectPrizeEntriesForType(prizeType) {
    const entries = [];
    const container = document.getElementById(`${prizeType}-entries`);
    
    if (!container) {
        console.log(`Container not found: ${prizeType}-entries`);
        return entries;
    }
    
    const prizeEntries = container.querySelectorAll('.prize-entry');
    
    prizeEntries.forEach(entry => {
        const amountInput = entry.querySelector(`input[name="${prizeType}_prize_amount[]"]`);
        const ticketInput = entry.querySelector(`input[name="${prizeType}_ticket_number[]"]`);
        const placeInput = entry.querySelector(`input[name="${prizeType}_place[]"]`);
        
        const amount = amountInput ? amountInput.value.trim() : '';
        const ticket = ticketInput ? ticketInput.value.trim() : '';
        const place = placeInput ? placeInput.value.trim() : '';
        
        if (amount || ticket) {
            entries.push({ amount, ticket, place });
        }
    });
    
    return entries;
}

/**
 * Update preview HTML with new data
 */
function updatePreviewHTML(data) {
    const container = document.getElementById('preview-container');
    
    if (!container) {
        console.error('Preview container not found');
        return;
    }
    
    const html = generatePreviewHTML(data);
    container.innerHTML = html;
}

/**
 * Generate desktop preview HTML
 */
function generatePreviewHTML(data) {
    if (!hasValidData(data)) {
        return getPlaceholderHTML();
    }
    
    let html = `
        <div class="preview-result">
            ${generateResultHeader(data)}
            ${generatePrizeCards(data.prizes)}
            ${generateStatusBadge(data.isPublished)}
        </div>
    `;
    
    return html;
}

/**
 * Check if data is valid for preview
 */
function hasValidData(data) {
    return data.date || data.drawNumber || Object.keys(data.prizes).length > 0;
}

/**
 * Get placeholder HTML
 */
function getPlaceholderHTML() {
    return `
        <div class="preview-placeholder">
            <div class="placeholder-icon">📋</div>
            <h3>Lottery Result Preview</h3>
            <p>Fill in the form data to see the live preview</p>
        </div>
    `;
}

/**
 * Generate result header HTML
 */
function generateResultHeader(data) {
    const lotteryName = data.lottery || 'Lottery Name';
    
    return `
        <div class="result-header">
            <h2>${lotteryName}</h2>
            <div class="result-meta">
                <div class="result-date">Date: ${data.formattedDate || 'Not set'}</div>
                <div class="result-draw">Draw #${data.drawNumber || 'N/A'}</div>
            </div>
        </div>
    `;
}

/**
 * Generate prize cards HTML
 */
function generatePrizeCards(prizes) {
    if (!prizes || Object.keys(prizes).length === 0) {
        return '<div class="no-data-message">No prize data entered</div>';
    }
    
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
    
    let html = '';
    
    prizeOrder.forEach(prizeType => {
        if (prizes[prizeType] && prizes[prizeType].length > 0) {
            html += generateSinglePrizeCard(
                prizeType, 
                prizeNames[prizeType], 
                prizes[prizeType]
            );
        }
    });
    
    return html;
}

/**
 * Generate single prize card HTML
 */
function generateSinglePrizeCard(prizeType, prizeName, prizeData) {
    const firstEntry = prizeData[0];
    const amount = firstEntry.amount || '0';
    const formattedAmount = formatCurrency(amount);
    
    const cardClass = prizeType === '1st' ? 'prize-card first-prize' : 'prize-card';
    
    let html = `
        <div class="${cardClass}">
            <div class="prize-header">${prizeName}</div>
            <div class="prize-content">
                <div class="prize-amount">${formattedAmount}</div>
                ${generateWinningNumbers(prizeType, prizeData)}
            </div>
        </div>
    `;
    
    return html;
}

/**
 * Generate winning numbers HTML based on prize type
 */
function generateWinningNumbers(prizeType, prizeData) {
    if (prizeType === 'consolation') {
        return generateConsolationNumbers(prizeData);
    } else if (['1st', '2nd', '3rd'].includes(prizeType)) {
        return generateTopPrizeNumbers(prizeData);
    } else {
        return generateRegularPrizeNumbers(prizeData);
    }
}

/**
 * Generate consolation prize numbers
 */
function generateConsolationNumbers(prizeData) {
    let html = '<div class="consolation-grid">';
    
    prizeData.forEach(data => {
        if (data.ticket) {
            html += `<div class="consolation-number">${data.ticket}</div>`;
        }
    });
    
    html += '</div>';
    return html;
}

/**
 * Generate top prize numbers (1st, 2nd, 3rd)
 */
function generateTopPrizeNumbers(prizeData) {
    let html = '<div class="winning-numbers">';
    
    prizeData.forEach(data => {
        if (data.ticket) {
            html += `
                <div class="winning-number">
                    <span class="ticket-number">${data.ticket}</span>
                    ${data.place ? `<span class="place-name">${data.place}</span>` : ''}
                </div>
            `;
        }
    });
    
    html += '</div>';
    return html;
}

/**
 * Generate regular prize numbers (4th-10th)
 */
function generateRegularPrizeNumbers(prizeData) {
    let html = '<div class="winning-numbers">';
    
    if (prizeData.length > 4) {
        // Use grid layout for many numbers
        html += '<div class="multiple-numbers-grid">';
        prizeData.forEach(data => {
            if (data.ticket) {
                html += `<div class="number-item">${data.ticket}</div>`;
            }
        });
        html += '</div>';
    } else {
        // Use regular layout for few numbers
        prizeData.forEach(data => {
            if (data.ticket) {
                html += `
                    <div class="winning-number">
                        <span class="ticket-number">${data.ticket}</span>
                    </div>
                `;
            }
        });
    }
    
    html += '</div>';
    return html;
}

/**
 * Generate status badge
 */
function generateStatusBadge(isPublished) {
    const status = isPublished ? 'published' : 'unpublished';
    const statusText = isPublished ? 'Published' : 'Draft';
    const statusClass = isPublished ? 'status-badge' : 'status-badge unpublished';
    
    return `<div class="${statusClass}">${statusText}</div>`;
}

/**
 * Format currency in Indian format
 */
function formatCurrency(amount) {
    if (!amount || isNaN(amount)) return '₹0/-';
    
    const numAmount = parseFloat(amount);
    return `₹${numAmount.toLocaleString('en-IN')}/-`;
}

/**
 * Setup form field listeners
 */
function setupFormListeners() {
    // Basic form fields
    const basicSelectors = [
        '#lottery, select[name="lottery"]',
        '#date, input[name="date"]',
        '#draw_number, input[name="draw_number"]',
        '#published, input[name="is_published"]'
    ];
    
    basicSelectors.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(element => {
            element.addEventListener('change', updatePreview);
            element.addEventListener('input', debounce(updatePreview, 300));
        });
    });
    
    // Prize entry fields
    setupPrizeFieldListeners();
    
    console.log('Form listeners setup complete');
}

/**
 * Setup listeners for prize entry fields
 */
function setupPrizeFieldListeners() {
    const prizeInputs = document.querySelectorAll(
        'input[name*="_prize_amount"], input[name*="_ticket_number"], input[name*="_place"]'
    );
    
    prizeInputs.forEach(input => {
        // Remove existing listeners to avoid duplicates
        input.removeEventListener('change', updatePreview);
        input.removeEventListener('input', updatePreview);
        
        // Add new listeners
        input.addEventListener('change', updatePreview);
        input.addEventListener('input', debounce(updatePreview, 500));
    });
    
    console.log(`Setup listeners for ${prizeInputs.length} prize fields`);
}

/**
 * Load existing data if in edit mode
 */
function loadExistingData() {
    // Check if we're in edit mode and have existing data
    if (window.prizeEntriesData && Object.keys(window.prizeEntriesData).length > 0) {
        console.log('Loading existing prize data:', window.prizeEntriesData);
        
        // If preview is visible, update it
        if (previewVisible) {
            updatePreview();
        }
    }
}

/**
 * Override existing form handlers to include preview updates
 */
function overrideFormHandlers() {
    // Override add entry buttons
    overrideAddEntryButtons();
    
    // Override bulk process buttons
    overrideBulkProcessButtons();
    
    // Override toggle bulk entry
    overrideToggleBulkEntry();
}

/**
 * Override add entry button handlers
 */
function overrideAddEntryButtons() {
    const addButtons = document.querySelectorAll('button[onclick*="addEntry"]');
    
    addButtons.forEach(button => {
        const originalOnclick = button.getAttribute('onclick');
        const prizeType = originalOnclick.match(/addEntry\('([^']+)'\)/)?.[1];
        
        if (prizeType) {
            button.setAttribute('onclick', `addEntryWithPreview('${prizeType}')`);
        }
    });
    
    console.log(`Override ${addButtons.length} add entry buttons`);
}

/**
 * Override bulk process button handlers
 */
function overrideBulkProcessButtons() {
    const bulkButtons = document.querySelectorAll('button[onclick*="processBulkEntries"]');
    
    bulkButtons.forEach(button => {
        const originalOnclick = button.getAttribute('onclick');
        const prizeType = originalOnclick.match(/processBulkEntries\('([^']+)'\)/)?.[1];
        
        if (prizeType) {
            button.setAttribute('onclick', `processBulkEntriesWithPreview('${prizeType}')`);
        }
    });
    
    console.log(`Override ${bulkButtons.length} bulk process buttons`);
}

/**
 * Override toggle bulk entry handlers
 */
function overrideToggleBulkEntry() {
    const toggleInputs = document.querySelectorAll('input[onchange*="toggleBulkEntry"]');
    
    toggleInputs.forEach(input => {
        const originalOnchange = input.getAttribute('onchange');
        const prizeType = originalOnchange.match(/toggleBulkEntry\('([^']+)'\)/)?.[1];
        
        if (prizeType) {
            input.setAttribute('onchange', `toggleBulkEntryWithPreview('${prizeType}')`);
        }
    });
    
    console.log(`Override ${toggleInputs.length} toggle bulk entry handlers`);
}

/**
 * Enhanced addEntry function with preview update
 */
function addEntryWithPreview(prizeType) {
    // Call original addEntry function if it exists
    if (typeof window.addEntry === 'function') {
        window.addEntry(prizeType);
    } else {
        console.error('Original addEntry function not found');
        return;
    }
    
    // Setup listeners on new fields and update preview
    setTimeout(() => {
        setupPrizeFieldListeners();
        updatePreview();
    }, 100);
}

/**
 * Enhanced bulk processing with preview update
 */
function processBulkEntriesWithPreview(prizeType) {
    // Call original processBulkEntries function
    if (typeof window.processBulkEntries === 'function') {
        window.processBulkEntries(prizeType);
    } else {
        console.error('Original processBulkEntries function not found');
        return;
    }
    
    // Setup listeners and update preview after bulk processing
    setTimeout(() => {
        setupPrizeFieldListeners();
        updatePreview();
    }, 200);
}

/**
 * Enhanced toggle bulk entry with preview update
 */
function toggleBulkEntryWithPreview(prizeType) {
    // Call original toggleBulkEntry function
    if (typeof window.toggleBulkEntry === 'function') {
        window.toggleBulkEntry(prizeType);
    } else {
        console.error('Original toggleBulkEntry function not found');
        return;
    }
    
    // Update preview after toggle
    setTimeout(updatePreview, 100);
}

/**
 * Show preview error message
 */
function showPreviewError(message) {
    const container = document.getElementById('preview-container');
    
    if (container) {
        container.innerHTML = `
            <div class="preview-error">
                <div class="error-icon">⚠️</div>
                <h4>Preview Error</h4>
                <p>${message}</p>
            </div>
        `;
    }
}

/**
 * Debounce function to limit frequent calls
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
 * Utility function to safely get element
 */
function safeGetElement(selector) {
    try {
        return document.querySelector(selector);
    } catch (e) {
        console.error(`Error selecting element: ${selector}`, e);
        return null;
    }
}

/**
 * Export functions for global access
 */
window.togglePreview = togglePreview;
window.addEntryWithPreview = addEntryWithPreview;
window.processBulkEntriesWithPreview = processBulkEntriesWithPreview;
window.toggleBulkEntryWithPreview = toggleBulkEntryWithPreview;
window.updatePreview = updatePreview;

// Export for debugging
window.previewDebug = {
    collectFormData,
    updatePreview,
    previewVisible: () => previewVisible,
    previewData: () => previewData
};