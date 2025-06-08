/**
 * Lottery Admin Enhancement Script
 * Path: results/static/results/js/lottery_admin.js
 * 
 * Clean production version - Admin functionality only
 */

// Store entry counters for each prize type
const entryCounters = {};
let isDirty = false;

/**
 * Initialize the lottery admin interface
 */
function initLotteryAdmin() {
    // Initialize prize type counters
    document.querySelectorAll('.form-section').forEach(section => {
        const prizeType = section.id.replace('-section', '');
        if (prizeType) {
            entryCounters[prizeType] = 1;
        }
    });

    // Set up form change tracking
    setupFormChangeTracking();
    
    // Set today's date as default for new entries only
    const dateInput = document.querySelector('input[name="date"]');
    if (dateInput && !dateInput.value) {
        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const dd = String(today.getDate()).padStart(2, '0');
        dateInput.value = `${yyyy}-${mm}-${dd}`;
    }

    // Check if we're in edit mode and load existing entries
    loadExistingPrizeEntries();

    // Add form submission handler
    document.getElementById('lotteryForm').addEventListener('submit', validateAndSubmit);
    
    // Add beforeunload event to warn about unsaved changes
    window.addEventListener('beforeunload', function(e) {
        if (isDirty) {
            e.preventDefault();
            e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
            return e.returnValue;
        }
    });

    // Initialize fixed bottom buttons
    initializeFixedButtons();
    initializePreviewState();
}

/**
 * Add entry to prize section
 */
function addEntry(prizeType) {
    const entriesContainer = document.getElementById(prizeType + '-entries');
    if (!entriesContainer) return;
    
    const firstEntry = entriesContainer.children[0];
    if (!firstEntry) return;
    
    const newEntry = firstEntry.cloneNode(true);
    
    // Clear input values and set up tracking
    const inputs = newEntry.querySelectorAll('input');
    inputs.forEach(input => {
        input.value = '';
        input.addEventListener('change', () => {
            isDirty = true;
            notifyPreviewUpdate();
        });
    });
    
    // Add remove button if this is not the first entry
    if (entriesContainer.children.length > 0 && !newEntry.querySelector('.remove-entry-btn')) {
        addRemoveButtonToEntry(newEntry, entriesContainer);
    }
    
    entryCounters[prizeType] = (entryCounters[prizeType] || 0) + 1;
    entriesContainer.appendChild(newEntry);
    isDirty = true;
    
    // Focus on the first input
    const firstInput = newEntry.querySelector('input');
    if (firstInput) firstInput.focus();

    notifyPreviewUpdate();
}

/**
 * Toggle between normal and bulk entry modes
 */
function toggleBulkEntry(prizeType) {
    const bulkSection = document.getElementById(prizeType + '-bulk');
    const isVisible = bulkSection.style.display !== 'none';
    bulkSection.style.display = isVisible ? 'none' : 'block';
    
    if (!isVisible) {
        setTimeout(() => {
            const specialPrizes = ['consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th'];
            if (specialPrizes.includes(prizeType)) {
                const amountInput = document.getElementById(prizeType + '-bulk-amount');
                if (amountInput) amountInput.focus();
            } else {
                const textarea = document.getElementById(prizeType + '-bulk-textarea');
                if (textarea) textarea.focus();
            }
        }, 100);
    }
}

/**
 * Process bulk entries with support for both formats - FIXED VERSION
 */
function processBulkEntries(prizeType) {
    const textarea = document.getElementById(prizeType + '-bulk-textarea');
    const entriesContainer = document.getElementById(prizeType + '-entries');
    
    if (!textarea || !entriesContainer) {
        showNotification('Error: Could not find required elements.', 'error');
        return;
    }
    
    const templateEntry = entriesContainer.children[0];
    if (!templateEntry) {
        showNotification('Error: No template entry found.', 'error');
        return;
    }
    
    // Clear existing entries
    entriesContainer.innerHTML = '';
    
    const specialPrizes = ['consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th'];
    const isSpecialPrize = specialPrizes.includes(prizeType);
    
    let errorCount = 0;
    let successCount = 0;
    
    if (isSpecialPrize) {
        // Handle special prize format
        const bulkAmountInput = document.getElementById(prizeType + '-bulk-amount');
        if (!bulkAmountInput) {
            showNotification('Error: Could not find prize amount input.', 'error');
            entriesContainer.appendChild(templateEntry);
            return;
        }
        
        const prizeAmount = bulkAmountInput.value.trim();
        if (!prizeAmount) {
            showNotification('Please enter a prize amount.', 'warning');
            entriesContainer.appendChild(templateEntry);
            return;
        }
        
        // Get the text input from the textarea
        const rawTicketNumbers = textarea.value.trim().split(/\s+/);

        // Keep only non-empty ticket entries (allowing letters, numbers, or both)
        const ticketNumbers = rawTicketNumbers.filter(ticket => ticket.length > 0);

        
        if (ticketNumbers.length === 0) {
            showNotification('No valid numeric ticket numbers found.', 'warning');
            entriesContainer.appendChild(templateEntry);
            return;
        }
        
        const invalidCount = rawTicketNumbers.length - ticketNumbers.length;
        
        // Process each ticket number
        ticketNumbers.forEach((ticketNumber, index) => {
            const cleanTicketNumber = ticketNumber.trim();
            if (cleanTicketNumber.length > 0) {
                const newEntry = templateEntry.cloneNode(true);
                
                const amountInput = newEntry.querySelector(`input[name="${prizeType}_prize_amount[]"]`);
                const ticketInput = newEntry.querySelector(`input[name="${prizeType}_ticket_number[]"]`);
                
                if (amountInput) amountInput.value = prizeAmount;
                if (ticketInput) ticketInput.value = cleanTicketNumber;
                
                if (successCount > 0) {
                    addRemoveButtonToEntry(newEntry, entriesContainer);
                }
                
                setupEntryChangeTracking(newEntry);
                entriesContainer.appendChild(newEntry);
                successCount++;
            } else {
                errorCount++;
            }
        });
        
        bulkAmountInput.value = '';
        textarea.value = '';
        
    } else {
        // Handle original format for 1st, 2nd, 3rd prizes
        const lines = textarea.value.trim().split('\n');
        if (lines.length === 0 || (lines.length === 1 && lines[0] === '')) {
            showNotification('No entries found in the bulk entry textarea.', 'warning');
            entriesContainer.appendChild(templateEntry);
            return;
        }
        
        lines.forEach((line) => {
            const values = line.split(',').map(v => v.trim());
            
            if (values.length < 2) {
                errorCount++;
                return;
            }
            
            const newEntry = templateEntry.cloneNode(true);
            
            const amountInput = newEntry.querySelector(`input[name="${prizeType}_prize_amount[]"]`);
            const ticketInput = newEntry.querySelector(`input[name="${prizeType}_ticket_number[]"]`);
            const placeInput = newEntry.querySelector(`input[name="${prizeType}_place[]"]`);
            
            if (amountInput) amountInput.value = values[0] || '';
            if (ticketInput) ticketInput.value = values[1] || '';
            if (placeInput && values[2]) placeInput.value = values[2];
            
            if (successCount > 0) {
                addRemoveButtonToEntry(newEntry, entriesContainer);
            }
            
            setupEntryChangeTracking(newEntry);
            entriesContainer.appendChild(newEntry);
            successCount++;
        });
        
        textarea.value = '';
    }
    
    // If no successful entries, add back the template
    if (successCount === 0) {
        entriesContainer.appendChild(templateEntry);
    }
    
    entryCounters[prizeType] = entriesContainer.children.length;
    isDirty = true;
    
    // FIX: Reset the toggle switch to "Normal" position and hide bulk section
    const toggleSwitch = document.querySelector(`#${prizeType}-section .toggle-switch input[type="checkbox"]`);
    if (toggleSwitch) {
        toggleSwitch.checked = false; // Reset toggle to "Normal" position
    }
    
    // Hide the bulk section
    const bulkSection = document.getElementById(prizeType + '-bulk');
    if (bulkSection) {
        bulkSection.style.display = 'none';
    }
    
    // Show summary notification
    if (errorCount > 0 || (isSpecialPrize && invalidCount > 0)) {
        const totalErrors = errorCount + (isSpecialPrize ? invalidCount : 0);
        const errorMsg = isSpecialPrize ? 
            `Processed ${successCount} entries successfully. ${totalErrors} entries were skipped.` :
            `Processed ${successCount} entries successfully. ${errorCount} lines were skipped due to incorrect format.`;
        showNotification(errorMsg, 'warning');
    } else {
        showNotification(`Successfully processed ${successCount} entries.`, 'success');
    }

    notifyPreviewUpdate();
}

/**
 * Validate form and submit if valid
 */
function validateAndSubmit(e) {
    e.preventDefault();
    
    // Basic validation
    const lottery = document.querySelector('select[name="lottery"]').value;
    const drawNumber = document.querySelector('input[name="draw_number"]').value;
    const date = document.querySelector('input[name="date"]').value;
    
    if (!lottery || !drawNumber || !date) {
        showNotification('Please fill in all required fields in the Lottery Draw Information section.', 'error');
        return;
    }
    
    // Check if at least one prize entry is filled
    let hasEntries = false;
    const prizeTypes = Object.keys(entryCounters);
    
    for (const prizeType of prizeTypes) {
        const entriesContainer = document.getElementById(prizeType + '-entries');
        if (!entriesContainer) continue;
        
        const entries = entriesContainer.querySelectorAll('.prize-entry');
        
        for (const entry of entries) {
            const inputs = entry.querySelectorAll('input[type="number"], input[type="text"]');
            const values = Array.from(inputs).map(input => input.value.trim());
            
            if (values.filter(v => v !== '').length >= 2) {
                hasEntries = true;
                break;
            }
        }
        
        if (hasEntries) break;
    }
    
    if (!hasEntries) {
        showNotification('Please add at least one prize entry.', 'error');
        return;
    }
    
    // Confirm submission
    if (confirm('Are you sure you want to save these lottery results?')) {
        isDirty = false;
        e.target.submit();
    }
}

/**
 * Set up change tracking on form elements
 */
function setupFormChangeTracking() {
    const formElements = document.querySelectorAll('#lotteryForm input, #lotteryForm select, #lotteryForm textarea');
    formElements.forEach(element => {
        element.addEventListener('change', () => {
            isDirty = true;
            notifyPreviewUpdate();
        });
        
        if (element.tagName === 'INPUT' && (element.type === 'text' || element.type === 'number') || element.tagName === 'TEXTAREA') {
            element.addEventListener('keyup', () => {
                isDirty = true;
                notifyPreviewUpdate();
            });
        }
    });
}

/**
 * Set up change tracking for a single entry
 */
function setupEntryChangeTracking(entry) {
    entry.querySelectorAll('input').forEach(input => {
        input.addEventListener('change', () => {
            isDirty = true;
            notifyPreviewUpdate();
        });
    });
}

/**
 * Load existing prize entries in edit mode
 */
function loadExistingPrizeEntries() {
    if (typeof window.prizeEntriesData === 'undefined' || !window.prizeEntriesData) {
        return;
    }
    
    Object.keys(window.prizeEntriesData).forEach(prizeType => {
        const entries = window.prizeEntriesData[prizeType];
        
        if (!entries || entries.length === 0) return;
        
        const entriesContainer = document.getElementById(prizeType + '-entries');
        if (!entriesContainer) return;
        
        const firstEntry = entriesContainer.children[0];
        if (!firstEntry) return;
        
        const templateEntry = firstEntry.cloneNode(true);
        entriesContainer.innerHTML = '';
        
        entries.forEach((entry, index) => {
            const newEntry = templateEntry.cloneNode(true);
            
            const amountInput = newEntry.querySelector(`input[name="${prizeType}_prize_amount[]"]`);
            if (amountInput) amountInput.value = entry.prize_amount || '';
            
            const ticketInput = newEntry.querySelector(`input[name="${prizeType}_ticket_number[]"]`);
            if (ticketInput) ticketInput.value = entry.ticket_number || '';
            
            if (prizeType === '1st' || prizeType === '2nd' || prizeType === '3rd') {
                const placeInput = newEntry.querySelector(`input[name="${prizeType}_place[]"]`);
                if (placeInput) placeInput.value = entry.place || '';
            }
            
            if (index > 0) {
                addRemoveButtonToEntry(newEntry, entriesContainer);
            }
            
            setupEntryChangeTracking(newEntry);
            entriesContainer.appendChild(newEntry);
        });
        
        entryCounters[prizeType] = entriesContainer.children.length;
    });
}

/**
 * Show notification to user
 */
function showNotification(message, type = 'info') {
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-message">${message}</span>
            <button class="notification-close">×</button>
        </div>
    `;
    
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '1';
    }, 10);
    
    const closeButton = notification.querySelector('.notification-close');
    closeButton.addEventListener('click', () => {
        notification.style.opacity = '0';
        setTimeout(() => {
            if (container.contains(notification)) {
                container.removeChild(notification);
            }
        }, 300);
    });
    
    setTimeout(() => {
        if (container.contains(notification)) {
            notification.style.opacity = '0';
            setTimeout(() => {
                if (container.contains(notification)) {
                    container.removeChild(notification);
                }
            }, 300);
        }
    }, 5000);
}

/**
 * Helper function to add remove button to an entry
 */
function addRemoveButtonToEntry(entryElement, container) {
    const formRow = entryElement.querySelector('.form-row');
    if (formRow && !entryElement.querySelector('.remove-entry-btn')) {
        const actionDiv = document.createElement('div');
        actionDiv.className = 'form-group';
        
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'remove-entry-btn btn btn-danger btn-small';
        removeBtn.innerHTML = '❌ Remove';
        removeBtn.onclick = function() {
            container.removeChild(entryElement);
            isDirty = true;
            notifyPreviewUpdate();
        };
        
        actionDiv.appendChild(removeBtn);
        formRow.appendChild(actionDiv);
    }
}

/**
 * Initialize fixed bottom buttons functionality
 */
function initializeFixedButtons() {
    const previewBtn = document.querySelector('.preview-toggle-btn');
    if (previewBtn) {
        previewBtn.addEventListener('click', handlePreviewToggle);
    }
    
    const saveBtn = document.querySelector('.save-btn-bottom');
    if (saveBtn) {
        enhanceFixedSaveButton(saveBtn);
    }
    
    setupKeyboardShortcuts();
    initScrollBehavior();
    initButtonInteractions();
}

/**
 * Handle preview toggle for fixed buttons
 */
/**
 * Handle preview toggle for fixed buttons - FIXED VERSION
 */
/**
 * Handle preview toggle for fixed buttons - COMPLETE FIX
 */
/**
 * Handle preview toggle for fixed buttons - FIXED VERSION
 */
function handlePreviewToggle() {
    console.log('=== Preview Toggle Called ===');
    
    // Get all required elements
    const previewSection = document.getElementById('preview-section');
    const previewBtn = document.querySelector('.preview-toggle-btn');
    const previewBtnText = document.getElementById('preview-btn-text');
    const previewContainer = document.getElementById('preview-container');
    
    // Guard clause for missing elements
    if (!previewSection || !previewBtn || !previewBtnText) {
        console.error('Critical preview elements not found!');
        showNotification('Preview elements not found', 'error');
        return;
    }
    
    // Ensure we're not in the middle of a toggle already
    if (window._previewToggleInProgress) {
        console.log('Toggle already in progress, ignoring duplicate call');
        return;
    }
    window._previewToggleInProgress = true;
    
    // Get computed style for accurate visibility check
    const computedStyle = window.getComputedStyle(previewSection);
    const isCurrentlyVisible = computedStyle.display !== 'none';
    
    console.log('Current preview state:', {
        isCurrentlyVisible,
        displayStyle: computedStyle.display,
        sectionDisplay: previewSection.style.display
    });
    
    // Execute toggle with proper locking
    try {
        if (isCurrentlyVisible) {
            // === HIDE PREVIEW ===
            console.log('Hiding preview');
            
            // Update DOM
            previewSection.style.display = 'none';
            previewBtnText.textContent = 'Show Preview';
            previewBtn.classList.remove('active');
            
            const icon = previewBtn.querySelector('span:first-child');
            if (icon) icon.textContent = '👁️';
            
            // Notify preview system about visibility change
            if (typeof window.setPreviewVisible === 'function') {
                console.log('Calling setPreviewVisible(false)');
                window.setPreviewVisible(false);
            }
            
            showNotification('Preview hidden', 'info');
            
        } else {
            // === SHOW PREVIEW ===
            console.log('Showing preview');
            
            // Update DOM first
            previewSection.style.display = 'block';
            previewBtnText.textContent = 'Hide Preview';
            previewBtn.classList.add('active');
            
            const icon = previewBtn.querySelector('span:first-child');
            if (icon) icon.textContent = '🙈';
            
            // Generate preview - use promise for better sequencing
            try {
                console.log('Generating preview content');
                
                // 1. First ensure preview is visible in DOM
                previewSection.style.display = 'block';
                
                // 2. Notify preview system with proper locking
                if (typeof window.setPreviewVisible === 'function') {
                    console.log('Calling setPreviewVisible(true)');
                    window.setPreviewVisible(true);
                } else if (typeof window.updatePreviewFromLotteryAdmin === 'function') {
                    console.log('Falling back to updatePreviewFromLotteryAdmin()');
                    window.updatePreviewFromLotteryAdmin();
                } else {
                    console.log('Falling back to generateBasicPreview()');
                    generateBasicPreview();
                }
                
                // Add debugging content for visual confirmation
                if (previewContainer) {
                    // Check if we have any content
                    if (previewContainer.children.length === 0 || 
                        (previewContainer.children.length === 1 && 
                         previewContainer.children[0].classList.contains('preview-placeholder'))) {
                        
                        console.log('No preview content found, forcing basic preview');
                        generateBasicPreview();
                    }
                }
                
                // 3. Scroll into view after a delay to ensure content is rendered
                setTimeout(() => {
                    console.log('Scrolling to preview section');
                    previewSection.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'start',
                        inline: 'nearest'
                    });
                }, 500);
                
                showNotification('Preview generated successfully', 'success');
                
            } catch (err) {
                console.error('Error generating preview:', err);
                showNotification('Error generating preview: ' + err.message, 'error');
                
                // Ensure some content is visible even on error
                if (previewContainer) {
                    previewContainer.innerHTML = `
                        <div class="preview-error">
                            <div class="error-icon">⚠️</div>
                            <h4>Preview Error</h4>
                            <p>${err.message || 'Unknown error generating preview'}</p>
                        </div>
                    `;
                }
            }
        }
    } catch (err) {
        console.error('Error in handlePreviewToggle:', err);
        showNotification('Error toggling preview: ' + err.message, 'error');
    } finally {
        // Release lock to prevent deadlocks
        setTimeout(() => {
            window._previewToggleInProgress = false;
            console.log('=== Preview Toggle Completed ===');
        }, 600);
    }
}

/**
 * ENHANCED: Better basic preview generation with more robust error handling
 */
function generateBasicPreview() {
    console.log('Generating basic preview...');
    
    const previewContainer = document.getElementById('preview-container');
    if (!previewContainer) {
        console.error('Preview container not found!');
        return;
    }
    
    try {
        const lotterySelect = document.querySelector('select[name="lottery"]');
        const drawNumber = document.querySelector('input[name="draw_number"]');
        const date = document.querySelector('input[name="date"]');
        const isPublished = document.querySelector('input[name="is_published"]');
        const isBumper = document.querySelector('input[name="is_bumper"]');
        
        // Log current form values
        console.log('Form values for preview:', {
            lottery: lotterySelect?.value,
            drawNumber: drawNumber?.value,
            date: date?.value,
            isPublished: isPublished?.checked,
            isBumper: isBumper?.checked
        });
        
        if (!lotterySelect?.value || !drawNumber?.value || !date?.value) {
            previewContainer.innerHTML = `
                <div class="preview-placeholder">
                    <div class="placeholder-icon">⚠️</div>
                    <h3>Incomplete Information</h3>
                    <p>Please fill in the lottery type, draw number, and date to generate preview</p>
                </div>
            `;
            return;
        }
        
        const lotteryName = lotterySelect.options[lotterySelect.selectedIndex].text;
        let formattedDate = 'Invalid Date';
        
        try {
            formattedDate = new Date(date.value).toLocaleDateString('en-IN', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        } catch (e) {
            console.error('Error formatting date:', e);
        }
        
        // Collect prize entries
        let prizeEntriesHtml = '';
        const prizeTypes = ['1st', '2nd', '3rd', 'consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th'];
        let hasAnyPrizes = false;
        
        prizeTypes.forEach(prizeType => {
            const entriesContainer = document.getElementById(prizeType + '-entries');
            if (!entriesContainer) return;
            
            const entries = [];
            const prizeEntries = entriesContainer.querySelectorAll('.prize-entry');
            
            prizeEntries.forEach(entry => {
                const amountInput = entry.querySelector(`input[name="${prizeType}_prize_amount[]"]`);
                const ticketInput = entry.querySelector(`input[name="${prizeType}_ticket_number[]"]`);
                const placeInput = entry.querySelector(`input[name="${prizeType}_place[]"]`);
                
                const amount = amountInput?.value?.trim();
                const ticket = ticketInput?.value?.trim();
                const place = placeInput?.value?.trim();
                
                if (amount && ticket) {
                    entries.push({ amount, ticket, place });
                }
            });
            
            if (entries.length > 0) {
                hasAnyPrizes = true;
                const prizeClass = prizeType === '1st' ? 'first-prize' : '';
                const prizeTitle = prizeType.charAt(0).toUpperCase() + prizeType.slice(1) + ' Prize';
                
                prizeEntriesHtml += `
                    <div class="prize-card ${prizeClass}">
                        <div class="prize-header">${prizeTitle}</div>
                        <div class="prize-content">
                            <div class="prize-amount">₹${entries[0].amount}</div>
                            <div class="winning-numbers">
                `;
                
                entries.forEach(entry => {
                    prizeEntriesHtml += `
                        <div class="winning-number">
                            <span class="ticket-number">${entry.ticket}</span>
                            ${entry.place ? `<span class="place-name">${entry.place}</span>` : ''}
                        </div>
                    `;
                });
                
                prizeEntriesHtml += `
                            </div>
                        </div>
                    </div>
                `;
            }
        });
        
        if (!hasAnyPrizes) {
            prizeEntriesHtml = `
                <div class="preview-no-prizes">
                    <div class="placeholder-icon">🎫</div>
                    <h3>No Prize Entries</h3>
                    <p>Add some prize entries to see them in the preview</p>
                </div>
            `;
        }
        
        previewContainer.innerHTML = `
            <div class="preview-result">
                <div class="result-header">
                    <h2>${lotteryName} - Draw #${drawNumber.value}</h2>
                    <div class="result-meta">
                        <div class="result-date">Date: ${formattedDate}</div>
                        ${isBumper?.checked ? '<div class="result-bumper">🎊 BUMPER DRAW</div>' : ''}
                    </div>
                </div>
                <div class="status-badge ${isPublished?.checked ? '' : 'unpublished'}">
                    ${isPublished?.checked ? '✅ Published' : '📝 Draft'}
                </div>
                ${prizeEntriesHtml}
                <div class="preview-footer">
                    <div class="preview-summary">
                        <span>Generated at: ${new Date().toLocaleTimeString()}</span>
                        <span>Status: ${isPublished?.checked ? 'Published' : 'Draft'}</span>
                    </div>
                </div>
            </div>
        `;
        
        console.log('Basic preview generated successfully');
    } catch (err) {
        console.error('Error generating basic preview:', err);
        previewContainer.innerHTML = `
            <div class="preview-error">
                <div class="error-icon">⚠️</div>
                <h4>Preview Generation Error</h4>
                <p>${err.message || 'Unknown error generating preview'}</p>
            </div>
        `;
    }
}

/**
 * Initialize preview synchronization with DOM state on page load
 * Call this function in the initLotteryAdmin function
 */
function initializePreviewState() {
    const previewSection = document.getElementById('preview-section');
    
    if (previewSection) {
        const computedStyle = window.getComputedStyle(previewSection);
        const isVisible = computedStyle.display !== 'none';
        
        console.log('Initializing preview state, currently visible:', isVisible);
        
        // Synchronize button state with current visibility
        if (isVisible) {
            const previewBtn = document.querySelector('.preview-toggle-btn');
            const previewBtnText = document.getElementById('preview-btn-text');
            
            if (previewBtn) previewBtn.classList.add('active');
            if (previewBtnText) previewBtnText.textContent = 'Hide Preview';
            
            // Notify preview system
            if (typeof window.setPreviewVisible === 'function') {
                window.setPreviewVisible(true);
            }
        }
    }
}

/**
 * Enhance fixed save button
 */
function enhanceFixedSaveButton(saveBtn) {
    const form = document.getElementById('lotteryForm');
    if (!form) return;
    
    form.addEventListener('submit', function() {
        saveBtn.classList.add('loading');
        saveBtn.disabled = true;
        
        const iconSpan = saveBtn.querySelector('span:first-child');
        const textSpan = saveBtn.querySelector('span:last-child');
        
        if (iconSpan) iconSpan.textContent = '⏳';
        if (textSpan) {
            const isEditMode = form.querySelector('input[name="result_id"]');
            textSpan.textContent = isEditMode ? 'Updating...' : 'Saving...';
        }
        
        showNotification('Saving lottery results...', 'info');
        
        setTimeout(() => {
            if (saveBtn.classList.contains('loading')) {
                saveBtn.classList.remove('loading');
                saveBtn.disabled = false;
                if (iconSpan) iconSpan.textContent = '💾';
                if (textSpan) {
                    const isEditMode = form.querySelector('input[name="result_id"]');
                    textSpan.textContent = isEditMode ? 'Update Lottery Results' : 'Save Lottery Results';
                }
            }
        }, 10000);
    });
}

/**
 * Setup keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            const saveBtn = document.querySelector('.save-btn-bottom');
            if (saveBtn && !saveBtn.disabled) {
                document.getElementById('lotteryForm').submit();
            }
        }
        
        if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
            e.preventDefault();
            handlePreviewToggle();
        }
        
        if (e.key === 'Escape') {
            const previewSection = document.getElementById('preview-section');
            if (previewSection && previewSection.style.display !== 'none') {
                handlePreviewToggle();
            }
        }
    });
}

/**
 * Initialize scroll behavior for fixed buttons
 */
function initScrollBehavior() {
    let isScrolling = false;
    
    window.addEventListener('scroll', function() {
        if (!isScrolling) {
            window.requestAnimationFrame(function() {
                const bottomButtons = document.querySelector('.bottom-action-buttons');
                if (!bottomButtons) return;
                
                const scrollY = window.scrollY;
                
                if (scrollY > 100) {
                    bottomButtons.style.boxShadow = '0 -4px 20px rgba(0, 0, 0, 0.15)';
                    bottomButtons.style.backdropFilter = 'blur(15px)';
                } else {
                    bottomButtons.style.boxShadow = '0 -2px 10px rgba(0, 0, 0, 0.1)';
                    bottomButtons.style.backdropFilter = 'blur(10px)';
                }
                
                isScrolling = false;
            });
        }
        isScrolling = true;
    });
}

/**
 * Initialize button interactions
 */
function initButtonInteractions() {
    const buttons = document.querySelectorAll('.bottom-action-buttons .btn');
    
    buttons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            if (!button.disabled && !button.classList.contains('loading')) {
                button.style.transform = 'translateY(-2px)';
            }
        });
        
        button.addEventListener('mouseleave', function() {
            if (!button.disabled && !button.classList.contains('loading')) {
                button.style.transform = '';
            }
        });
    });
}

/**
 * Notify preview system of form updates
 */
function notifyPreviewUpdate() {
    clearTimeout(window.previewUpdateTimeout);
    window.previewUpdateTimeout = setTimeout(() => {
        if (typeof window.updatePreviewFromLotteryAdmin === 'function') {
            window.updatePreviewFromLotteryAdmin();
        }
    }, 300);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initLotteryAdmin();
});

// Export functions for global access
window.addEntry = addEntry;
window.toggleBulkEntry = toggleBulkEntry;
window.processBulkEntries = processBulkEntries;
window.handlePreviewToggle = handlePreviewToggle;
window.showNotification = showNotification;