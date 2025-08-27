/**
 * Preview Section JavaScript
 * Path: results/static/results/js/preview.js
 * 
 * PREVIEW FUNCTIONALITY ONLY - Admin logic handled by lottery_admin.js
 */

// Preview state management
let previewVisible = false;
let previewData = {};
let lastDataHash = '';

/**
 * Initialize preview functionality when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    // Wait for lottery_admin.js to load first
    setTimeout(() => {
        initializePreviewSystem();
        console.log('Preview system initialized');
    }, 200);
});

/**
 * Initialize the complete preview system
 */
function initializePreviewSystem() {
    // Initialize preview content structure
    initializePreviewContent();
    
    // Set up form field listeners for real-time updates
    setupPreviewFormListeners();
    
    // Load existing data if in edit mode
    loadExistingPreviewData();
    
    // Set up periodic updates for smooth UX
    setInterval(updatePreviewIfVisible, 2000);
    
    // Check initial preview state
    checkInitialPreviewState();
}

/**
 * Initialize preview content structure
 */
function initializePreviewContent() {
    const previewContent = document.getElementById('preview-content');
    
    if (!previewContent) {
        console.log('Preview content container not found');
        return;
    }
    
    // Only initialize if empty
    if (previewContent.innerHTML.trim() === '') {
        previewContent.innerHTML = `
            <div class="preview-wrapper">
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
}

/**
 * Check initial preview state and update accordingly
 */
function checkInitialPreviewState() {
    const previewSection = document.getElementById('preview-section');
    if (previewSection) {
        previewVisible = previewSection.style.display !== 'none' && previewSection.style.display !== '';
        if (previewVisible) {
            updatePreview();
        }
    }
}

/**
 * Set up form field listeners for real-time preview updates
 */
function setupPreviewFormListeners() {
    // Basic form fields
    const basicSelectors = [
        'select[name="lottery"]',
        'input[name="date"]',
        'input[name="draw_number"]',
        'input[name="is_published"]',
        'input[name="is_bumper"]'
    ];
    
    basicSelectors.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(element => {
            element.addEventListener('change', debounce(updatePreview, 300));
            if (element.type === 'text' || element.type === 'number' || element.type === 'date') {
                element.addEventListener('input', debounce(updatePreview, 500));
            }
        });
    });
    
    // Prize entry fields - set up with observer for dynamic content
    setupPrizeFieldListeners();
    observePrizeFieldChanges();
    
    console.log('Preview form listeners setup complete');
}

/**
 * Setup listeners for existing prize entry fields
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
        input.addEventListener('change', debounce(updatePreview, 200));
        input.addEventListener('input', debounce(updatePreview, 800));
    });
    
    console.log(`Setup preview listeners for ${prizeInputs.length} prize fields`);
}

/**
 * Observe for new prize fields being added
 */
function observePrizeFieldChanges() {
    const observer = new MutationObserver(function(mutations) {
        let needsUpdate = false;
        
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                // Check if any new prize entry fields were added
                const addedNodes = Array.from(mutation.addedNodes);
                addedNodes.forEach(node => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        const prizeInputs = node.querySelectorAll(
                            'input[name*="_prize_amount"], input[name*="_ticket_number"], input[name*="_place"]'
                        );
                        if (prizeInputs.length > 0) {
                            needsUpdate = true;
                            // Set up listeners on new fields
                            prizeInputs.forEach(input => {
                                input.addEventListener('change', debounce(updatePreview, 200));
                                input.addEventListener('input', debounce(updatePreview, 800));
                            });
                        }
                    }
                });
            }
        });
        
        if (needsUpdate) {
            setTimeout(updatePreview, 100);
        }
    });
    
    // Observe all prize entry containers
    const prizeContainers = document.querySelectorAll('[id$="-entries"]');
    prizeContainers.forEach(container => {
        observer.observe(container, {
            childList: true,
            subtree: true
        });
    });
    
    console.log(`Observing ${prizeContainers.length} prize containers for changes`);
}

/**
 * Load existing data if in edit mode
 */
function loadExistingPreviewData() {
    if (window.prizeEntriesData && Object.keys(window.prizeEntriesData).length > 0) {
        console.log('Loading existing prize data for preview:', window.prizeEntriesData);
        setTimeout(updatePreview, 500);
    }
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
 * Main preview update function - called from admin system
 */
function updatePreview() {
    if (!previewVisible) return;
    
    try {
        const formData = collectFormData();
        const dataHash = generateDataHash(formData);
        
        // Only update if data has actually changed
        if (dataHash === lastDataHash) {
            return;
        }
        
        lastDataHash = dataHash;
        previewData = formData;
        updatePreviewHTML(formData);
        
        console.log('Preview updated with new data');
    } catch (error) {
        console.error('Error updating preview:', error);
        showPreviewError('Error updating preview: ' + error.message);
    }
}

/**
 * Generate a simple hash of form data for change detection
 */
function generateDataHash(data) {
    try {
        return btoa(JSON.stringify(data)).substring(0, 20);
    } catch (e) {
        return Math.random().toString(36).substring(7);
    }
}

/**
 * Collect all form data for preview generation
 */
function collectFormData() {
    const data = {
        lottery: getLotteryName(),
        date: getFormValue('input[name="date"]'),
        drawNumber: getFormValue('input[name="draw_number"]'),
        isPublished: getCheckboxValue('input[name="is_published"]'),
        isBumper: getCheckboxValue('input[name="is_bumper"]'),
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
    const lotterySelect = document.querySelector('select[name="lottery"]');
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
    
    // First, try to use existing database data if available (edit mode)
    if (window.prizeEntriesData && Object.keys(window.prizeEntriesData).length > 0) {
        prizeTypes.forEach(prizeType => {
            if (window.prizeEntriesData[prizeType] && window.prizeEntriesData[prizeType].length > 0) {
                prizes[prizeType] = window.prizeEntriesData[prizeType].map(entry => ({
                    amount: entry.prize_amount || '',
                    ticket: entry.ticket_number || '',
                    place: entry.place || ''
                }));
            }
        });
        
        // If we have existing data, return it
        if (Object.keys(prizes).length > 0) {
            return prizes;
        }
    }
    
    // Fallback to form inputs if no existing data
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
        return entries;
    }
    
    // Check if this is a special prize type that has multiple tickets per amount
    const specialPrizes = ['consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th'];
    const isSpecialPrize = specialPrizes.includes(prizeType);
    
    if (isSpecialPrize) {
        // For special prizes, collect all ticket inputs directly from container
        const ticketInputs = container.querySelectorAll(`input[name="${prizeType}_ticket_number[]"]`);
        const amountInputs = container.querySelectorAll(`input[name="${prizeType}_prize_amount[]"]`);
        
        // Group tickets by amount (every 3 tickets share an amount)
        ticketInputs.forEach((ticketInput, index) => {
            const ticket = ticketInput.value.trim();
            if (ticket) {
                // Determine which amount this ticket belongs to (3 tickets per amount)
                const amountIndex = Math.floor(index / 3);
                const amountInput = amountInputs[amountIndex];
                const amount = amountInput ? amountInput.value.trim() : '';
                
                entries.push({ amount, ticket, place: '' });
            }
        });
    } else {
        // For regular prizes (1st, 2nd, 3rd), use original logic
        const prizeEntries = container.querySelectorAll('.prize-entry');
        
        prizeEntries.forEach(entry => {
            const amountInput = entry.querySelector(`input[name="${prizeType}_prize_amount[]"]`);
            const ticketInput = entry.querySelector(`input[name="${prizeType}_ticket_number[]"]`);
            const placeInput = entry.querySelector(`input[name="${prizeType}_place[]"]`);
            
            const amount = amountInput ? amountInput.value.trim() : '';
            const ticket = ticketInput ? ticketInput.value.trim() : '';
            const place = placeInput ? placeInput.value.trim() : '';
            
            // Only include entries with at least amount or ticket
            if (amount || ticket) {
                entries.push({ amount, ticket, place });
            }
        });
    }
    
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
 * Generate complete preview HTML
 */
function generatePreviewHTML(data) {
    if (!hasValidData(data)) {
        return getPlaceholderHTML();
    }
    
    return `
        <div class="preview-result">
            ${generateResultHeader(data)}
            ${generatePrizeCards(data.prizes)}
            ${generateStatusBadge(data)}
        </div>
    `;
}

/**
 * Check if data is valid for preview
 */
function hasValidData(data) {
    return data.lottery || data.date || data.drawNumber || Object.keys(data.prizes).length > 0;
}

/**
 * Get placeholder HTML when no data
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
    const drawNumber = data.drawNumber || 'N/A';
    const formattedDate = data.formattedDate || 'Not set';
    
    return `
        <div class="result-header">
            <h2>${lotteryName}</h2>
            <div class="result-meta">
                <div class="result-date">Date: ${formattedDate}</div>
                <div class="result-draw">Draw #${drawNumber}</div>
                ${data.isBumper ? '<div class="result-bumper">🎉 Bumper Draw</div>' : ''}
            </div>
        </div>
    `;
}

/**
 * Generate prize cards HTML
 */
function generatePrizeCards(prizes) {
    if (!prizes || Object.keys(prizes).length === 0) {
        return '<div class="no-data-message">No prize data entered yet</div>';
    }
    
    const prizeOrder = ['1st', '2nd', '3rd', 'consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th'];
    const prizeNames = {
        '1st': '🥇 First Prize',
        '2nd': '🥈 Second Prize',
        '3rd': '🥉 Third Prize',
        '4th': '4️⃣ Fourth Prize',
        '5th': '5️⃣ Fifth Prize',
        '6th': '6️⃣ Sixth Prize',
        '7th': '7️⃣ Seventh Prize',
        '8th': '8️⃣ Eighth Prize',
        '9th': '9️⃣ Ninth Prize',
        '10th': '🔟 Tenth Prize',
        'consolation': '🎊 Consolation Prize'
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
    
    return `
        <div class="${cardClass}">
            <div class="prize-header">${prizeName}</div>
            <div class="prize-content">
                <div class="prize-amount">${formattedAmount}</div>
                ${generateWinningNumbers(prizeType, prizeData)}
            </div>
        </div>
    `;
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
 * Generate consolation prize numbers in grid
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
 * Generate top prize numbers (1st, 2nd, 3rd) with places
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
function generateStatusBadge(data) {
    const isPublished = data.isPublished;
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
 * Set preview visibility state
 */
function setPreviewVisible(visible) {
    previewVisible = visible;
    if (visible) {
        updatePreview();
    }
}

/**
 * Get current preview state
 */
function getPreviewState() {
    return {
        visible: previewVisible,
        data: previewData,
        lastHash: lastDataHash
    };
}

// ========== INTEGRATION WITH LOTTERY ADMIN ==========

/**
 * Function called by lottery_admin.js to update preview
 */
function updatePreviewFromLotteryAdmin() {
    updatePreview();
}

/**
 * Function to handle preview toggle from lottery_admin.js
 */
function togglePreviewFromAdmin(visible) {
    setPreviewVisible(visible);
    return visible;
}

// ========== EXPORT FUNCTIONS ==========

// Export main functions for lottery_admin.js integration
window.updatePreviewFromLotteryAdmin = updatePreviewFromLotteryAdmin;
window.togglePreviewFromAdmin = togglePreviewFromAdmin;
window.setPreviewVisible = setPreviewVisible;
window.getPreviewState = getPreviewState;

// Export for debugging
window.previewDebug = {
    collectFormData,
    updatePreview,
    generatePreviewHTML,
    previewVisible: () => previewVisible,
    previewData: () => previewData,
    lastDataHash: () => lastDataHash
};