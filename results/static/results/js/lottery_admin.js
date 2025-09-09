/**
 * Lottery Admin Enhancement Script
 * Path: results/static/results/js/lottery_admin.js
 * 
 * Enhanced version only - Single initialization
 */

// Store entry counters for each prize type
const entryCounters = {};
let isDirty = false;

/**
 * Get the next ticket number for a specific prize type (4th-10th only)
 */
function getNextTicketNumber(prizeType) {
    const numberedPrizes = ['4th', '5th', '6th', '7th', '8th', '9th', '10th'];
    if (!numberedPrizes.includes(prizeType)) {
        return null;
    }
    
    const entriesContainer = document.getElementById(prizeType + '-entries');
    if (!entriesContainer) {
        return 1;
    }
    
    const existingTickets = entriesContainer.querySelectorAll('.ticket-field-group');
    return existingTickets.length + 1;
}

/**
 * Renumber all existing ticket fields for a prize type (4th-10th only)
 */
function renumberTicketFields(prizeType) {
    const numberedPrizes = ['4th', '5th', '6th', '7th', '8th', '9th', '10th'];
    if (!numberedPrizes.includes(prizeType)) {
        return;
    }
    
    const entriesContainer = document.getElementById(prizeType + '-entries');
    if (!entriesContainer) {
        return;
    }
    
    const ticketGroups = entriesContainer.querySelectorAll('.ticket-field-group');
    ticketGroups.forEach((ticketGroup, index) => {
        // Remove existing number label if present
        const existingLabel = ticketGroup.querySelector('.ticket-number-label');
        if (existingLabel) {
            existingLabel.remove();
        }
        
        // Add new number label
        const numberLabel = document.createElement('span');
        numberLabel.textContent = index + 1;
        numberLabel.className = 'ticket-number-label';
        // Simple white text in black circle - works for both light and dark modes
                    numberLabel.style.cssText = 'position: absolute; left: 5px; top: 50%; transform: translateY(-50%); font-size: 11px; color: white; font-weight: bold; z-index: 1; background: #000; border-radius: 50%; width: 18px; height: 18px; display: flex; align-items: center; justify-content: center;';
        
        ticketGroup.style.position = 'relative';
        const ticketInput = ticketGroup.querySelector('input');
        if (ticketInput) {
            ticketInput.style.paddingLeft = '25px';
        }
        
        ticketGroup.insertBefore(numberLabel, ticketGroup.firstChild);
    });
}

/**
 * Initialize the lottery admin interface - ENHANCED VERSION ONLY
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
    
    // Add numbering to existing ticket fields for 4th-10th prizes
    const numberedPrizes = ['4th', '5th', '6th', '7th', '8th', '9th', '10th'];
    numberedPrizes.forEach(prizeType => {
        renumberTicketFields(prizeType);
    });
    
    // Set default prize amounts for 1st, 2nd, 3rd prizes (only for new entries, not edit mode)
    setDefaultPrizeAmounts();
    
    // Set up auto-save for ticket number inputs (4th-10th prizes only)
    setupAutoSaveForTicketInputs();

    // Add ENHANCED form submission handler (only one)
    const form = document.getElementById('lotteryForm');
    if (form) {
        form.addEventListener('submit', validateAndSubmitWithNotification);
    }
    
    // Initialize notification checkbox behavior
    initializeNotificationCheckbox();
    
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
 * Enhanced form validation with notification support
 */
function validateAndSubmitWithNotification(e) {
    e.preventDefault();
    
    // Basic validation
    const lottery = document.querySelector('select[name="lottery"]').value;
    const drawNumber = document.querySelector('input[name="draw_number"]').value;
    const date = document.querySelector('input[name="date"]').value;
    
    if (!lottery || !drawNumber || !date) {
        showNotification('Please fill in all required fields in the Lottery Draw Information section.', 'error');
        return;
    }
    
    // Check if at least one prize entry is filled and validate special prize first entries
    let hasEntries = false;
    const prizeTypes = Object.keys(entryCounters);
    const specialPrizes = ['consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th'];
    
    for (const prizeType of prizeTypes) {
        const entriesContainer = document.getElementById(prizeType + '-entries');
        if (!entriesContainer) continue;
        
        const entries = entriesContainer.querySelectorAll('.prize-entry');
        
        // Special validation for consolation and 4th-10th prizes
        if (specialPrizes.includes(prizeType) && entries.length > 0) {
            const firstEntry = entries[0];
            const firstEntryAmountInput = firstEntry.querySelector('.first-entry-amount') || 
                                        firstEntry.querySelector(`input[name="${prizeType}_prize_amount[]"]:not([type="hidden"])`);
            
            const hasTicketEntries = Array.from(entries).some(entry => {
                const ticketInput = entry.querySelector(`input[name="${prizeType}_ticket_number[]"]`);
                return ticketInput && ticketInput.value.trim() !== '';
            });
            
            // If there are ticket entries but no first entry amount, show error
            if (hasTicketEntries && (!firstEntryAmountInput || !firstEntryAmountInput.value.trim() || firstEntryAmountInput.value.trim() === '0')) {
                const prizeTypeName = prizeType === 'consolation' ? 'Consolation' : prizeType.charAt(0).toUpperCase() + prizeType.slice(1);
                showNotification(`⚠️ No prize amount entered! Please enter the prize amount for ${prizeTypeName} prize before saving.`, 'error');
                if (firstEntryAmountInput) {
                    firstEntryAmountInput.focus();
                    firstEntryAmountInput.style.borderColor = '#dc3545';  // Red border to highlight
                    setTimeout(() => {
                        firstEntryAmountInput.style.borderColor = '';  // Reset after 3 seconds
                    }, 3000);
                }
                return;
            }
        }
        
        // Check for regular prizes (1st, 2nd, 3rd) - each entry must have both amount and ticket
        if (!specialPrizes.includes(prizeType) && entries.length > 0) {
            for (const entry of entries) {
                const amountInput = entry.querySelector(`input[name="${prizeType}_prize_amount[]"]`);
                const ticketInput = entry.querySelector(`input[name="${prizeType}_ticket_number[]"]`);
                
                const hasTicket = ticketInput && ticketInput.value.trim() !== '';
                const hasAmount = amountInput && amountInput.value.trim() !== '' && amountInput.value.trim() !== '0';
                
                // If has ticket but no amount, show error
                if (hasTicket && !hasAmount) {
                    const prizeTypeName = prizeType.charAt(0).toUpperCase() + prizeType.slice(1);
                    showNotification(`⚠️ No prize amount entered! Please enter the prize amount for ${prizeTypeName} prize before saving.`, 'error');
                    if (amountInput) {
                        amountInput.focus();
                        amountInput.style.borderColor = '#dc3545';  // Red border to highlight
                        setTimeout(() => {
                            amountInput.style.borderColor = '';  // Reset after 3 seconds
                        }, 3000);
                    }
                    return;
                }
            }
        }
        
        for (const entry of entries) {
            const inputs = entry.querySelectorAll('input[type="number"], input[type="text"]:not([type="hidden"])');
            const values = Array.from(inputs).map(input => input.value.trim());
            
            if (values.filter(v => v !== '').length >= 2) {
                hasEntries = true;
                break;
            }
        }
        
        if (hasEntries) break;
    }
    
    // Enhanced 4-digit validation for 7th-10th prizes during form submission
    let validationFailed = false;
    const fourDigitPrizes = ['7th', '8th', '9th', '10th'];
    for (const prizeType of fourDigitPrizes) {
        const entriesContainer = document.getElementById(prizeType + '-entries');
        if (!entriesContainer) continue;
        
        const ticketInputs = entriesContainer.querySelectorAll(`input[name="${prizeType}_ticket_number[]"]`);
        for (const ticketInput of ticketInputs) {
            const value = ticketInput.value.trim();
            if (value !== '') {
                // Check for non-numeric characters
                if (!/^\d+$/.test(value)) {
                    const prizeTypeName = prizeType.charAt(0).toUpperCase() + prizeType.slice(1);
                    showNotification(`❌ FORM BLOCKED: ${prizeTypeName} prize ticket "${value}" contains invalid characters. Only numbers (0-9) are allowed.`, 'error');
                    ticketInput.focus();
                    validationFailed = true;
                    break;
                }
                
                // Check if it's exactly 4 digits
                if (value.length !== 4) {
                    const prizeTypeName = prizeType.charAt(0).toUpperCase() + prizeType.slice(1);
                    let errorMessage = '';
                    let detailMessage = '';
                    
                    if (value.length < 4) {
                        errorMessage = `❌ FORM BLOCKED: ${prizeTypeName} prize requires exactly 4 digits. "${value}" has only ${value.length} digit${value.length === 1 ? '' : 's'}.`;
                        detailMessage = `${prizeType} prize requires exactly 4 digits. You entered ${value.length} digit${value.length === 1 ? '' : 's'}. Please add ${4 - value.length} more digit${4 - value.length === 1 ? '' : 's'}.`;
                    } else {
                        errorMessage = `❌ FORM BLOCKED: ${prizeTypeName} prize requires exactly 4 digits. "${value}" has ${value.length} digits.`;
                        detailMessage = `${prizeType} prize requires exactly 4 digits. You entered ${value.length} digits. Please remove ${value.length - 4} digit${value.length - 4 === 1 ? '' : 's'}.`;
                    }
                    
                    showNotification(errorMessage, 'error');
                    ticketInput.focus();
                    validationFailed = true;
                    break;
                }
            }
        }
        if (validationFailed) break;
    }
    
    // If validation failed, stop here and don't submit
    if (validationFailed) {
        console.log('FORM SUBMISSION BLOCKED DUE TO VALIDATION FAILURE');
        return false;
    }
    
    if (!hasEntries) {
        showNotification('Please add at least one prize entry.', 'error');
        return;
    }
    
    // Check if notification checkbox is checked
    const notifyCheckbox = document.querySelector('input[name="results_ready_notification"]');
    const isPublishedCheckbox = document.querySelector('input[name="is_published"]');
    const willSendNotification = notifyCheckbox && notifyCheckbox.checked;
    
    // Auto-check published if notification is being sent
    if (willSendNotification && isPublishedCheckbox && !isPublishedCheckbox.checked) {
        isPublishedCheckbox.checked = true;
        showNotification('Auto-enabled "Mark as declared" since notification is being sent.', 'info');
    }
    
    // Show appropriate saving message
    if (willSendNotification) {
        showNotification('Saving results and sending notification to users...', 'info');
    } else {
        showNotification('Saving lottery results...', 'info');
    }
    
    // Get the form and create FormData object
    const form = document.getElementById('lotteryForm');
    const formData = new FormData(form);
    
    // Debug: Log all form data being submitted
    console.log('=== FORM DATA BEING SUBMITTED ===');
    for (let [key, value] of formData.entries()) {
        if (key.includes('_ticket_number') || key.includes('_prize_amount')) {
            console.log(`${key}: "${value}"`);
        }
    }
    console.log('=== END FORM DATA ===');
    
    // Get UI elements for status updates
    const saveBtn = document.querySelector('.save-btn-bottom');
    let iconSpan = null;
    let textSpan = null;
    
    // Update UI to show loading state
    if (saveBtn) {
        iconSpan = saveBtn.querySelector('span:first-child');
        textSpan = saveBtn.querySelector('span:last-child');
        
        saveBtn.classList.add('loading');
        saveBtn.disabled = true;
        
        if (iconSpan) iconSpan.textContent = willSendNotification ? '📱' : '⏳';
        if (textSpan) {
            const isEditMode = form.querySelector('input[name="result_id"]');
            if (willSendNotification) {
                textSpan.textContent = isEditMode ? 'Updating & Notifying...' : 'Saving & Notifying...';
            } else {
                textSpan.textContent = isEditMode ? 'Updating...' : 'Saving...';
            }
        }
    }
    
    // Perform AJAX submission
    fetch(form.action || window.location.href, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Server returned an error response: ' + response.status);
        }
        return response.text();
    })
    .then(html => {
        // Success handling
        isDirty = false;
        
        // Look for success messages in the response
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const successMsg = doc.querySelector('.messagelist .success');
        const errorMsg = doc.querySelector('.messagelist .error');
        
        if (errorMsg) {
            showNotification(errorMsg.textContent.trim(), 'error');
        } else if (successMsg) {
            let message = successMsg.textContent.trim();
            
            // Enhance message if notification was sent
            if (willSendNotification) {
                message = message + ' 📱 Users have been notified!';
            }
            
            showNotification(message, 'success');
        } else {
            // Default success message
            const defaultMsg = willSendNotification ? 
                'Results saved and users notified! 📱' : 
                'Lottery results saved successfully!';
            showNotification(defaultMsg, 'success');
        }
        
        // Update any necessary parts of the page
        const resultId = doc.querySelector('input[name="result_id"]');
        if (resultId && !form.querySelector('input[name="result_id"]')) {
            // If this was a new entry that now has an ID, update the form
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'result_id';
            hiddenInput.value = resultId.value;
            form.appendChild(hiddenInput);
            
            // 🔥 UPDATE FORM ACTION URL TO EDIT ENDPOINT
            form.action = `/api/results/admin/edit-result/${resultId.value}/`;
            console.log('Form action updated to:', form.action);
            
            // Update page title to show we're in edit mode
            const title = document.querySelector('.form-header');
            if (title) {
                title.textContent = 'Lottery Result Edit System';
            }
            
            // Update browser URL without reload (optional - keeps URL in sync)
            window.history.replaceState({}, '', `/api/results/admin/edit-result/${resultId.value}/`);
            console.log('Browser URL updated to edit mode');
        }
        
        // Reset UI loading state
        if (saveBtn) {
            saveBtn.classList.remove('loading');
            saveBtn.disabled = false;
            
            if (iconSpan) iconSpan.textContent = '💾';
            if (textSpan) {
                textSpan.textContent = form.querySelector('input[name="result_id"]') ? 
                    'Update Lottery Results' : 'Save Lottery Results';
            }
        }
    })
    .catch(error => {
        console.error('Error submitting form:', error);
        const errorMsg = willSendNotification ? 
            'Error saving results and sending notification. Please try again.' :
            'Error saving lottery results. Please try again.';
        showNotification(errorMsg, 'error');
        
        // Reset UI loading state
        if (saveBtn) {
            saveBtn.classList.remove('loading');
            saveBtn.disabled = false;
            
            if (iconSpan) iconSpan.textContent = '💾';
            if (textSpan) {
                textSpan.textContent = form.querySelector('input[name="result_id"]') ? 
                    'Update Lottery Results' : 'Save Lottery Results';
            }
        }
    });
}

/**
 * Enhanced notification checkbox behavior
 */
function initializeNotificationCheckbox() {
    const notifyCheckbox = document.querySelector('input[name="results_ready_notification"]');
    const isPublishedCheckbox = document.querySelector('input[name="is_published"]');
    
    if (notifyCheckbox) {
        // Add change event listener
        notifyCheckbox.addEventListener('change', function() {
            if (this.checked) {
                // Show confirmation when checking
                showNotification('Notification will be sent when you save the results.', 'info');
                
                // Auto-check published (but don't force it)
                if (isPublishedCheckbox && !isPublishedCheckbox.checked) {
                    isPublishedCheckbox.checked = true;
                    showNotification('Auto-enabled "Mark as declared" for notification.', 'info');
                }
            } else {
                showNotification('Notification will not be sent.', 'info');
            }
            
            isDirty = true;
            notifyPreviewUpdate();
        });
        
        // Add visual feedback
        notifyCheckbox.addEventListener('mouseenter', function() {
            if (!this.checked) {
                this.style.transform = 'scale(1.2)';
                this.style.transition = 'transform 0.2s ease';
            }
        });
        
        notifyCheckbox.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1.1)';
        });
    }
}

/**
 * Add multiple individual ticket fields to prize section
 * SMART APPEND: Adds fields to the end of existing fields, filling incomplete rows first
 * @param {string} prizeType - The type of prize (e.g., '1st', 'consolation', etc.)
 * @param {number} numFields - Number of fields to add (optional, will prompt if not provided)
 */
function addMultipleFields(prizeType, numFields) {
    // If numFields is not provided, prompt user
    if (typeof numFields === 'undefined') {
        numFields = prompt('How many fields do you need?', '3');
        
        // Validate input
        if (numFields === null) return; // User cancelled
        
        numFields = parseInt(numFields);
        if (isNaN(numFields) || numFields < 1 || numFields > 100) {
            alert('Please enter a valid number between 1 and 100');
            return;
        }
    }
    
    const entriesContainer = document.getElementById(prizeType + '-entries');
    if (!entriesContainer) return;
    
    const fieldsPerRow = 3;
    let fieldsToAdd = numFields;
    
    // Find ALL existing entries and determine the absolute last one to append to
    const allExistingEntries = entriesContainer.querySelectorAll('.prize-entry');
    let targetEntry;
    
    console.log(`[DEBUG] Found ${allExistingEntries.length} existing entries for ${prizeType}`);
    
    if (allExistingEntries.length > 0) {
        // Use the last existing entry
        targetEntry = allExistingEntries[allExistingEntries.length - 1];
        console.log(`[DEBUG] Using existing entry:`, targetEntry);
    } else {
        // Create the first entry if none exists
        targetEntry = document.createElement('div');
        targetEntry.className = 'prize-entry';
        targetEntry.setAttribute('data-entry-index', 0);
        entriesContainer.appendChild(targetEntry);
        console.log(`[DEBUG] Created new entry:`, targetEntry);
    }
    
    // Find the very last ticket row across ALL entries
    const allExistingRows = entriesContainer.querySelectorAll('.form-row.ticket-row');
    let lastRow = allExistingRows[allExistingRows.length - 1];
    
    console.log(`[DEBUG] Found ${allExistingRows.length} existing ticket rows, last row:`, lastRow);
    
    if (lastRow) {
        // Make sure we're adding to the entry that contains the last row
        const lastRowEntry = lastRow.closest('.prize-entry');
        if (lastRowEntry) {
            targetEntry = lastRowEntry;
        }
        
        const fieldsInLastRow = lastRow.querySelectorAll('.ticket-field-group').length;
        const spaceInLastRow = fieldsPerRow - fieldsInLastRow;
        
        if (spaceInLastRow > 0) {
            // Fill the remaining space in the last row first
            const fieldsToAddToLastRow = Math.min(spaceInLastRow, fieldsToAdd);
            
            for (let i = 0; i < fieldsToAddToLastRow; i++) {
                const ticketGroup = document.createElement('div');
                ticketGroup.className = 'form-group ticket-field-group';
                ticketGroup.style.flex = '1 1 33.333% !important';
                ticketGroup.style.minWidth = '0 !important';
                ticketGroup.style.maxWidth = '33.333% !important';
                ticketGroup.style.boxSizing = 'border-box !important';
                
                const ticketInput = document.createElement('input');
                // Use text input with numeric inputmode for 7th-10th prizes to show number pad on mobile
                const numberPadPrizes = ['7th', '8th', '9th', '10th'];
                ticketInput.type = 'text';
                
                // Add inputmode for number pad on mobile
                if (numberPadPrizes.includes(prizeType)) {
                    ticketInput.setAttribute('inputmode', 'numeric');
                }
                ticketInput.name = `${prizeType}_ticket_number[]`;
                ticketInput.id = `${prizeType}_ticket_${Date.now()}_lastrow_${i}`;
                ticketInput.className = 'form-control';
                
                // Add 4-digit validation for 7th-10th prizes
                if (numberPadPrizes.includes(prizeType)) {
                    ticketInput.setAttribute('maxlength', '4');
                    ticketInput.setAttribute('placeholder', '4 digits');
                    ticketInput.setAttribute('title', 'Enter exactly 4 digits');
                    ticketInput.setAttribute('pattern', '[0-9]{4}');
                    
                    // Add input filtering to allow only digits and limit to 4 characters
                    ticketInput.addEventListener('input', function(e) {
                        // Remove any non-digit characters
                        let value = this.value.replace(/\D/g, '');
                        // Limit to 4 digits
                        if (value.length > 4) {
                            value = value.slice(0, 4);
                        }
                        this.value = value;
                    });
                }
                
                // Add event listeners
                ticketInput.addEventListener('input', () => {
                    isDirty = true;
                    notifyPreviewUpdate();
                });
                
                // Add 4-digit validation for 7th-10th prizes
                if (numberPadPrizes.includes(prizeType)) {
                    ticketInput.addEventListener('input', function() {
                        // Clear error on input
                        clearInputError(this);
                    });
                    
                    // Validate on blur (when moving to next field)
                    ticketInput.addEventListener('blur', function(e) {
                        // Only validate if moving to another element, not if clicking outside the form area
                        setTimeout(() => {
                            const activeElement = document.activeElement;
                            // Only validate if focus moved to another input field or form element
                            if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'BUTTON' || activeElement.tagName === 'SELECT' || activeElement.tagName === 'TEXTAREA')) {
                                validateFourDigitInput(this, prizeType);
                            }
                        }, 10);
                    });
                }
                
                // Apply no spaces functionality
                applyNoSpacesToInput(ticketInput);
                
                // Set up auto-save for 4th-10th prizes
                const autoSavePrizes = ['4th', '5th', '6th', '7th', '8th', '9th', '10th'];
                if (autoSavePrizes.includes(prizeType)) {
                    setupAutoSaveForInput(ticketInput, prizeType);
                }
                
                // Add numbering for 4th-10th prizes
                const ticketNumber = getNextTicketNumber(prizeType);
                if (ticketNumber !== null) {
                    const numberLabel = document.createElement('span');
                    numberLabel.textContent = ticketNumber;
                    numberLabel.className = 'ticket-number-label';
                    // Simple white text in black circle - works for both light and dark modes
                    numberLabel.style.cssText = 'position: absolute; left: 5px; top: 50%; transform: translateY(-50%); font-size: 11px; color: white; font-weight: bold; z-index: 1; background: #000; border-radius: 50%; width: 18px; height: 18px; display: flex; align-items: center; justify-content: center;';
                    
                    ticketGroup.style.position = 'relative';
                    ticketInput.style.paddingLeft = '25px';
                    
                    ticketGroup.appendChild(numberLabel);
                }
                
                ticketGroup.appendChild(ticketInput);
                lastRow.appendChild(ticketGroup);
            }
            
            fieldsToAdd -= fieldsToAddToLastRow;
        }
    }
    
    // Now create new rows for any remaining fields
    if (fieldsToAdd > 0) {
        const numNewRows = Math.ceil(fieldsToAdd / fieldsPerRow);
        
        for (let rowIdx = 0; rowIdx < numNewRows; rowIdx++) {
            // Create new row
            const newRow = document.createElement('div');
            newRow.className = 'form-row ticket-row';
            newRow.style.display = 'flex !important';
            newRow.style.flexWrap = 'nowrap !important';
            newRow.style.maxWidth = '100% !important';
            
            // Determine how many fields in this row
            const remainingFields = fieldsToAdd - (rowIdx * fieldsPerRow);
            const fieldsInThisRow = Math.min(fieldsPerRow, remainingFields);
            
            // Create fields for this row
            for (let fieldIdx = 0; fieldIdx < fieldsInThisRow; fieldIdx++) {
                const ticketGroup = document.createElement('div');
                ticketGroup.className = 'form-group ticket-field-group';
                ticketGroup.style.flex = '1 1 33.333% !important';
                ticketGroup.style.minWidth = '0 !important';
                ticketGroup.style.maxWidth = '33.333% !important';
                ticketGroup.style.boxSizing = 'border-box !important';
                
                const ticketInput = document.createElement('input');
                // Use text input with numeric inputmode for 7th-10th prizes to show number pad on mobile
                const numberPadPrizes = ['7th', '8th', '9th', '10th'];
                ticketInput.type = 'text';
                
                // Add inputmode for number pad on mobile
                if (numberPadPrizes.includes(prizeType)) {
                    ticketInput.setAttribute('inputmode', 'numeric');
                }
                ticketInput.name = `${prizeType}_ticket_number[]`;
                ticketInput.id = `${prizeType}_ticket_${Date.now()}_${rowIdx}_${fieldIdx}`;
                ticketInput.className = 'form-control';
                
                // Add 4-digit validation for 7th-10th prizes
                if (numberPadPrizes.includes(prizeType)) {
                    ticketInput.setAttribute('maxlength', '4');
                    ticketInput.setAttribute('placeholder', '4 digits');
                    ticketInput.setAttribute('title', 'Enter exactly 4 digits');
                    ticketInput.setAttribute('pattern', '[0-9]{4}');
                    
                    // Add input filtering to allow only digits and limit to 4 characters
                    ticketInput.addEventListener('input', function(e) {
                        // Remove any non-digit characters
                        let value = this.value.replace(/\D/g, '');
                        // Limit to 4 digits
                        if (value.length > 4) {
                            value = value.slice(0, 4);
                        }
                        this.value = value;
                    });
                }
                
                // Add event listeners
                ticketInput.addEventListener('input', () => {
                    isDirty = true;
                    notifyPreviewUpdate();
                });
                
                // Add 4-digit validation for 7th-10th prizes
                if (numberPadPrizes.includes(prizeType)) {
                    ticketInput.addEventListener('input', function() {
                        // Clear error on input
                        clearInputError(this);
                    });
                    
                    // Validate on blur (when moving to next field)
                    ticketInput.addEventListener('blur', function(e) {
                        // Only validate if moving to another element, not if clicking outside the form area
                        setTimeout(() => {
                            const activeElement = document.activeElement;
                            // Only validate if focus moved to another input field or form element
                            if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'BUTTON' || activeElement.tagName === 'SELECT' || activeElement.tagName === 'TEXTAREA')) {
                                validateFourDigitInput(this, prizeType);
                            }
                        }, 10);
                    });
                }
                
                // Apply no spaces functionality
                applyNoSpacesToInput(ticketInput);
                
                // Set up auto-save for 4th-10th prizes
                const autoSavePrizes = ['4th', '5th', '6th', '7th', '8th', '9th', '10th'];
                if (autoSavePrizes.includes(prizeType)) {
                    setupAutoSaveForInput(ticketInput, prizeType);
                }
                
                // Add numbering for 4th-10th prizes
                const ticketNumber = getNextTicketNumber(prizeType);
                if (ticketNumber !== null) {
                    const numberLabel = document.createElement('span');
                    numberLabel.textContent = ticketNumber;
                    numberLabel.className = 'ticket-number-label';
                    // Simple white text in black circle - works for both light and dark modes
                    numberLabel.style.cssText = 'position: absolute; left: 5px; top: 50%; transform: translateY(-50%); font-size: 11px; color: white; font-weight: bold; z-index: 1; background: #000; border-radius: 50%; width: 18px; height: 18px; display: flex; align-items: center; justify-content: center;';
                    
                    ticketGroup.style.position = 'relative';
                    ticketInput.style.paddingLeft = '25px';
                    
                    ticketGroup.appendChild(numberLabel);
                }
                
                ticketGroup.appendChild(ticketInput);
                newRow.appendChild(ticketGroup);
            }
            
            // Add the completed row to the target entry (where the last row was found)
            targetEntry.appendChild(newRow);
        }
    }
    
    // Mark form as dirty and update preview
    isDirty = true;
    notifyPreviewUpdate();
    
    // Renumber all ticket fields for 4th-10th prizes after adding new fields
    renumberTicketFields(prizeType);
}

/**
 * Add entry to prize section (simplified - adds exactly 3 fields per call)
 */
function addEntry(prizeType) {
    // Always add exactly 3 fields to maintain consistent 3-per-row layout
    // This ensures perfect responsive behavior across all devices
    addMultipleFields(prizeType, 3);
}

/**
 * Clear all ticket fields and remove dynamically generated fields (4th-10th only)
 */
function clearAllFields(prizeType) {
    const entriesContainer = document.getElementById(prizeType + '-entries');
    if (!entriesContainer) return;
    
    // Get all ticket input fields
    const ticketInputs = entriesContainer.querySelectorAll('input[name$="_ticket_number[]"]');
    
    if (ticketInputs.length === 0) {
        showNotification('No ticket fields to clear.', 'info');
        return;
    }
    
    // Check if there are any values to clear or extra fields to remove
    const hasValues = Array.from(ticketInputs).some(input => input.value.trim() !== '');
    const hasExtraFields = ticketInputs.length > 3;
    
    if (!hasValues && !hasExtraFields) {
        showNotification('All ticket fields are already empty and at minimum count.', 'info');
        return;
    }
    
    // Confirm before clearing
    const fieldCount = ticketInputs.length;
    let confirmMessage = `This will:\n`;
    if (hasValues) {
        confirmMessage += `• Clear all ${fieldCount} ticket field values\n`;
    }
    if (hasExtraFields) {
        confirmMessage += `• Remove ${fieldCount - 3} extra fields (keeping only 3)\n`;
    }
    confirmMessage += `\nThis cannot be undone. Continue?`;
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    // First, clear all values
    ticketInputs.forEach(input => {
        input.value = '';
    });
    
    // Complete DOM cleanup - remove ALL dynamically generated content
    const allTicketRows = entriesContainer.querySelectorAll('.form-row.ticket-row');
    const allPrizeEntries = entriesContainer.querySelectorAll('.prize-entry');
    
    // Remove all prize entries except the first one (which is from the template)
    for (let i = allPrizeEntries.length - 1; i > 0; i--) {
        allPrizeEntries[i].remove();
    }
    
    // In the first (template) entry, remove all ticket rows except the first one
    const firstEntry = allPrizeEntries[0];
    if (firstEntry) {
        const ticketRowsInFirstEntry = firstEntry.querySelectorAll('.form-row.ticket-row');
        
        // Remove all ticket rows except the first one
        for (let i = ticketRowsInFirstEntry.length - 1; i > 0; i--) {
            ticketRowsInFirstEntry[i].remove();
        }
        
        // Ensure the first row has exactly 3 fields
        const firstRow = ticketRowsInFirstEntry[0];
        if (firstRow) {
            const fieldsInFirstRow = firstRow.querySelectorAll('.form-group.ticket-field-group');
            // Remove extra fields beyond 3 in the first row
            for (let i = fieldsInFirstRow.length - 1; i >= 3; i--) {
                fieldsInFirstRow[i].remove();
            }
            
            // Force layout refresh to remove any phantom spacing
            firstRow.style.display = 'none';
            setTimeout(() => {
                firstRow.style.display = '';
            }, 10);
        }
    }
    
    // Clean up any orphaned elements
    entriesContainer.querySelectorAll('.form-row.ticket-row').forEach((row, index) => {
        if (index > 0) {
            row.remove();
        }
    });
    
    // Mark form as dirty and update preview
    isDirty = true;
    notifyPreviewUpdate();
    
    const clearedActions = [];
    if (hasValues) clearedActions.push('values cleared');
    if (hasExtraFields) clearedActions.push(`${fieldCount - 3} extra fields removed`);
    
    showNotification(`${prizeType} prize: ${clearedActions.join(', ')}. Reset to 3 fields.`, 'success');
    
    // Renumber remaining ticket fields for 4th-10th prizes
    renumberTicketFields(prizeType);
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
 * Process bulk entries with support for both formats
 */
function processBulkEntries(prizeType) {
    const textarea = document.getElementById(prizeType + '-bulk-textarea');
    const entriesContainer = document.getElementById(prizeType + '-entries');
    const bulkSection = document.getElementById(prizeType + '-bulk');
    
    if (!textarea || !entriesContainer) {
        showNotification('Error: Could not find required elements.', 'error');
        return;
    }
    
    // Check if bulk section is visible
    if (!bulkSection || bulkSection.style.display === 'none') {
        showNotification('Please switch to Bulk mode first.', 'warning');
        return;
    }
    
    const templateEntry = entriesContainer.children[0];
    if (!templateEntry) {
        showNotification('Error: No template entry found.', 'error');
        return;
    }
    
    // Don't clear existing entries - we want to append to them
    const specialPrizes = ['consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th'];
    const isSpecialPrize = specialPrizes.includes(prizeType);
    
    // Get current entry count to continue numbering
    const currentEntryCount = entriesContainer.children.length;
    
    // Check if the first entry is empty (template entry)
    let hasEmptyFirstEntry = false;
    if (currentEntryCount === 1) {
        const firstEntry = entriesContainer.children[0];
        const firstAmountInput = firstEntry.querySelector('input[name$="_prize_amount[]"]');
        const firstTicketInputs = firstEntry.querySelectorAll('input[name$="_ticket_number[]"]');
        
        const hasAmount = firstAmountInput && firstAmountInput.value.trim();
        const hasTickets = Array.from(firstTicketInputs).some(input => input.value.trim());
        
        if (!hasAmount && !hasTickets) {
            hasEmptyFirstEntry = true;
        }
    }
    
    
    let errorCount = 0;
    let successCount = 0;
    
    if (isSpecialPrize) {
        // Handle special prize format
        const bulkAmountInput = document.getElementById(prizeType + '-bulk-amount');
        if (!bulkAmountInput) {
            showNotification('Error: Could not find prize amount input.', 'error');
            return;
        }
        
        let prizeAmount = bulkAmountInput.value.trim();
        
        // If no prize amount entered but there are existing entries, inherit from first entry
        if ((!prizeAmount || prizeAmount === '0') && currentEntryCount > 0) {
            const firstExistingEntry = entriesContainer.children[0];
            const firstAmountInput = firstExistingEntry.querySelector('input[name$="_prize_amount[]"]');
            if (firstAmountInput && firstAmountInput.value.trim()) {
                prizeAmount = firstAmountInput.value.trim();
                showNotification(`Using existing prize amount: ₹${prizeAmount}`, 'info');
            }
        }
        
        // Always require prize amount for bulk entry processing
        if (!prizeAmount || prizeAmount === '0') {
            showNotification('⚠️ Prize amount is required! Please enter a prize amount before processing bulk entries.', 'error');
            bulkAmountInput.focus();
            bulkAmountInput.style.borderColor = '#dc3545';  // Red border to highlight
            setTimeout(() => {
                bulkAmountInput.style.borderColor = '';  // Reset after 3 seconds
            }, 3000);
            return;
        }
        
        // Validate that prize amount is a positive number
        const prizeAmountNum = parseFloat(prizeAmount);
        if (isNaN(prizeAmountNum) || prizeAmountNum <= 0) {
            showNotification('Prize amount must be a positive number.', 'error');
            bulkAmountInput.focus();
            return;
        }
        
        // Get the text input from the textarea
        const rawTicketNumbers = textarea.value.trim().split(/\s+/);

        // Keep only non-empty ticket entries (allowing letters, numbers, or both)
        const ticketNumbers = rawTicketNumbers.filter(ticket => ticket.length > 0);

        
        if (ticketNumbers.length === 0) {
            showNotification('No valid ticket numbers found.', 'warning');
            return;
        }
        
        const invalidCount = rawTicketNumbers.length - ticketNumbers.length;
        
        // Strategy: First fill existing empty ticket fields, then create new entries as needed
        let ticketIndex = 0; // Track position in ticketNumbers array
        let currentEntryIdx = hasEmptyFirstEntry ? -1 : 0; // Start from first existing entry
        
        // If we have an empty first entry, we'll replace it instead of appending
        if (hasEmptyFirstEntry) {
            entriesContainer.removeChild(entriesContainer.children[0]);
            currentEntryIdx = -1; // Signal that we need to create the first entry
        }
        
        // First, fill existing entries' empty ticket fields
        if (!hasEmptyFirstEntry && currentEntryCount > 0) {
            for (let entryIdx = 0; entryIdx < currentEntryCount && ticketIndex < ticketNumbers.length; entryIdx++) {
                const existingEntry = entriesContainer.children[entryIdx];
                const ticketInputs = existingEntry.querySelectorAll(`input[name="${prizeType}_ticket_number[]"]`);
                
                // Fill empty ticket fields in this existing entry
                for (let fieldIdx = 0; fieldIdx < ticketInputs.length && ticketIndex < ticketNumbers.length; fieldIdx++) {
                    if (!ticketInputs[fieldIdx].value.trim()) {
                        ticketInputs[fieldIdx].value = ticketNumbers[ticketIndex];
                        ticketIndex++;
                        successCount++;
                        
                        // Set up event listeners for the newly filled field
                        applyNoSpacesToInput(ticketInputs[fieldIdx]);
                        ticketInputs[fieldIdx].addEventListener('change', () => {
                            isDirty = true;
                            notifyPreviewUpdate();
                        });
                        
                        // Set up auto-save for 4th-10th prizes
                        const autoSavePrizes = ['4th', '5th', '6th', '7th', '8th', '9th', '10th'];
                        if (autoSavePrizes.includes(prizeType)) {
                            setupAutoSaveForInput(ticketInputs[fieldIdx], prizeType);
                        }
                    }
                }
            }
        }
        
        // Now create new entries for remaining tickets
        let newEntryIndex = 0;
        while (ticketIndex < ticketNumbers.length) {
            // All prize types now get 3 tickets per row (simplified approach)
            const ticketsPerEntry = 3;
            
            // Get up to ticketsPerEntry tickets for this entry
            const remainingTickets = ticketNumbers.length - ticketIndex;
            const ticketsForThisEntry = Math.min(ticketsPerEntry, remainingTickets);
            const entryTickets = ticketNumbers.slice(ticketIndex, ticketIndex + ticketsForThisEntry);
            
            if (entryTickets.length === 0) break;
            
            // Create new entry
            const entry = document.createElement('div');
            entry.className = 'prize-entry';
            entry.setAttribute('data-entry-index', (hasEmptyFirstEntry ? 0 : currentEntryCount) + newEntryIndex);
            
            const formRow = document.createElement('div');
            formRow.className = 'form-row ticket-row';
            formRow.style.display = 'flex !important';
            formRow.style.flexWrap = 'nowrap !important';
            formRow.style.maxWidth = '100% !important';
            
            // Add amount field logic:
            // - Only add visible amount field if this is the very first entry in the entire container
            const isVeryFirstEntry = (hasEmptyFirstEntry && newEntryIndex === 0) || (currentEntryCount === 0 && newEntryIndex === 0);
            
            if (isVeryFirstEntry) {
                const prizeGroup = document.createElement('div');
                prizeGroup.className = 'form-group prize-amount-field';
                
                const prizeLabel = document.createElement('label');
                prizeLabel.textContent = 'Prize Amount (₹)';
                prizeLabel.setAttribute('for', `${prizeType}_bulk_amount_0`);
                
                const prizeInput = document.createElement('input');
                prizeInput.type = 'number';
                prizeInput.name = `${prizeType}_prize_amount[]`;
                prizeInput.id = `${prizeType}_bulk_amount_0`;
                prizeInput.className = 'form-control first-entry-amount';
                prizeInput.value = prizeAmount;
                prizeInput.onwheel = function() { this.blur(); };  // Prevent scroll wheel changes
                
                // Set up event listener for amount changes to update inherited amounts
                prizeInput.addEventListener('input', () => {
                    const allEntries = entriesContainer.querySelectorAll('.prize-entry');
                    allEntries.forEach((entryEl, entryIdx) => {
                        if (entryIdx > 0) { // Skip the first entry
                            const inheritedInput = entryEl.querySelector('.inherited-amount');
                            if (inheritedInput) {
                                inheritedInput.value = prizeInput.value;
                            }
                        }
                    });
                    isDirty = true;
                    notifyPreviewUpdate();
                });
                
                prizeGroup.appendChild(prizeLabel);
                prizeGroup.appendChild(prizeInput);
                formRow.appendChild(prizeGroup);
            } else {
                // Hidden amount input for additional entries
                const hiddenAmountInput = document.createElement('input');
                hiddenAmountInput.type = 'hidden';
                hiddenAmountInput.name = `${prizeType}_prize_amount[]`;
                hiddenAmountInput.value = prizeAmount;
                hiddenAmountInput.classList.add('inherited-amount');
                formRow.appendChild(hiddenAmountInput);
            }
            
            // All prize types now use 1 row (simplified approach)
            const totalRows = 1;
            
            // Create rows of 3 ticket fields each
            for (let rowIndex = 0; rowIndex < totalRows; rowIndex++) {
                // Create a new form row for each row (except the first one which uses existing formRow)
                let currentFormRow = formRow;
                if (rowIndex > 0) {
                    currentFormRow = document.createElement('div');
                    currentFormRow.className = 'form-row ticket-row';
                    currentFormRow.style.display = 'flex !important';
                    currentFormRow.style.flexWrap = 'nowrap !important';
                    currentFormRow.style.maxWidth = '100% !important';
                    entry.appendChild(currentFormRow);
                }
                
                // Create 3 ticket fields for this row
                for (let fieldIndex = 0; fieldIndex < 3; fieldIndex++) {
                    const ticketGroup = document.createElement('div');
                    ticketGroup.className = 'form-group ticket-field-group';
                    ticketGroup.style.flex = '1 1 33.333% !important';
                    ticketGroup.style.minWidth = '0 !important';
                    ticketGroup.style.maxWidth = '33.333% !important';
                    ticketGroup.style.boxSizing = 'border-box !important';
                    
                    const ticketInput = document.createElement('input');
                    // Use text input with numeric inputmode for 7th-10th prizes to show number pad on mobile
                    const numberPadPrizes = ['7th', '8th', '9th', '10th'];
                    ticketInput.type = 'text';
                    
                    // Add inputmode for number pad on mobile
                    if (numberPadPrizes.includes(prizeType)) {
                        ticketInput.setAttribute('inputmode', 'numeric');
                    }
                    ticketInput.name = `${prizeType}_ticket_number[]`;
                    ticketInput.id = `${prizeType}_ticket_bulk_${(hasEmptyFirstEntry ? 0 : currentEntryCount) + newEntryIndex}_${rowIndex}_${fieldIndex}`;
                    ticketInput.className = 'form-control';
                    
                    // Add 4-digit validation for 7th-10th prizes
                    if (numberPadPrizes.includes(prizeType)) {
                        ticketInput.setAttribute('maxlength', '4');
                        ticketInput.setAttribute('placeholder', '4 digits');
                        ticketInput.setAttribute('title', 'Enter exactly 4 digits');
                        ticketInput.setAttribute('pattern', '[0-9]{4}');
                        
                        // Add input filtering to allow only digits and limit to 4 characters
                        ticketInput.addEventListener('input', function(e) {
                            // Remove any non-digit characters
                            let value = this.value.replace(/\D/g, '');
                            // Limit to 4 digits
                            if (value.length > 4) {
                                value = value.slice(0, 4);
                            }
                            this.value = value;
                        });
                    }
                    
                    // Calculate ticket index for this field
                    const ticketIndex = (rowIndex * 3) + fieldIndex;
                    const ticketValue = ticketIndex < entryTickets.length ? entryTickets[ticketIndex].trim() : '';
                    ticketInput.value = ticketValue;
                    
                    // Add numbering for 4th-10th prizes
                    const ticketNumber = getNextTicketNumber(prizeType);
                    if (ticketNumber !== null) {
                        const numberLabel = document.createElement('span');
                        numberLabel.textContent = ticketNumber;
                        numberLabel.className = 'ticket-number-label';
                        // Simple white text in black circle - works for both light and dark modes
                    numberLabel.style.cssText = 'position: absolute; left: 5px; top: 50%; transform: translateY(-50%); font-size: 11px; color: white; font-weight: bold; z-index: 1; background: #000; border-radius: 50%; width: 18px; height: 18px; display: flex; align-items: center; justify-content: center;';
                        
                        ticketGroup.style.position = 'relative';
                        ticketInput.style.paddingLeft = '25px';
                        
                        ticketGroup.appendChild(numberLabel);
                    }
                    
                    ticketGroup.appendChild(ticketInput);
                    currentFormRow.appendChild(ticketGroup);
                    
                    applyNoSpacesToInput(ticketInput);
                    ticketInput.setAttribute('data-bulk-field', 'true');
                    
                    // Add 4-digit validation for 7th-10th prizes in bulk entry
                    if (numberPadPrizes.includes(prizeType)) {
                        ticketInput.addEventListener('input', function() {
                            // Clear error on input
                            clearInputError(this);
                        });
                        
                        // Validate on blur (when moving to next field)
                        ticketInput.addEventListener('blur', function(e) {
                            // Only validate if moving to another element, not if clicking outside the form area
                            setTimeout(() => {
                                const activeElement = document.activeElement;
                                // Only validate if focus moved to another input field or form element
                                if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'BUTTON' || activeElement.tagName === 'SELECT' || activeElement.tagName === 'TEXTAREA')) {
                                    validateFourDigitInput(this, prizeType);
                                }
                            }, 10);
                        });
                    }
                    
                    // Set up event listeners for form changes
                    ticketInput.addEventListener('change', () => {
                        isDirty = true;
                        notifyPreviewUpdate();
                    });
                    
                    // Set up auto-save for 4th-10th prizes
                    const autoSavePrizes = ['4th', '5th', '6th', '7th', '8th', '9th', '10th'];
                    if (autoSavePrizes.includes(prizeType)) {
                        setupAutoSaveForInput(ticketInput, prizeType);
                    }
                }
            }
            
            entry.appendChild(formRow);
            
            
            setupEntryChangeTracking(entry);
            entriesContainer.appendChild(entry);
            newEntryIndex++;
            
            // Update success count and ticket index
            successCount += entryTickets.length;
            ticketIndex += entryTickets.length;
        }
        
        
        // Clear bulk inputs after successful processing
        if (bulkAmountInput) bulkAmountInput.value = '';
        if (textarea) textarea.value = '';
        
    } else {
        // Handle original format for 1st, 2nd, 3rd prizes
        const lines = textarea.value.trim().split('\n');
        if (lines.length === 0 || (lines.length === 1 && lines[0] === '')) {
            showNotification('No entries found in the bulk entry textarea.', 'warning');
            return;
        }
        
        lines.forEach((line, lineIndex) => {
            const values = line.split(',').map(v => v.trim());
            
            if (values.length < 2) {
                errorCount++;
                return;
            }
            
            const newEntry = templateEntry.cloneNode(true);
            newEntry.setAttribute('data-entry-index', currentEntryCount + successCount);
            
            const amountInput = newEntry.querySelector(`input[name="${prizeType}_prize_amount[]"]`);
            const ticketInput = newEntry.querySelector(`input[name="${prizeType}_ticket_number[]"]`);
            const placeInput = newEntry.querySelector(`input[name="${prizeType}_place[]"]`);
            
            if (amountInput) amountInput.value = values[0] || '';
            if (ticketInput) ticketInput.value = values[1] || '';
            if (placeInput && values[2]) placeInput.value = values[2];
            
            
            setupEntryChangeTracking(newEntry);
            entriesContainer.appendChild(newEntry);
            successCount++;
        });
        
        textarea.value = '';
    }
    
    // No need to add template entry back - we preserve existing entries
    
    // Ensure the first entry has the correct structure after bulk processing
    if (isSpecialPrize && entriesContainer.children.length > 0) {
        const firstEntry = entriesContainer.children[0];
        let firstEntryAmountInput = firstEntry.querySelector('.first-entry-amount');
        
        // If first entry doesn't have visible amount input, we need to fix this
        if (!firstEntryAmountInput) {
            // Look for hidden amount input and convert it to visible
            const hiddenAmountInput = firstEntry.querySelector(`input[name="${prizeType}_prize_amount[]"][type="hidden"]`);
            
            if (hiddenAmountInput) {
                // Create visible amount field structure
                const prizeGroup = document.createElement('div');
                prizeGroup.className = 'form-group prize-amount-field';
                
                const prizeLabel = document.createElement('label');
                prizeLabel.textContent = 'Prize Amount (₹)';
                prizeLabel.setAttribute('for', `${prizeType}_amount`);
                
                const prizeInput = document.createElement('input');
                prizeInput.type = 'number';
                prizeInput.name = `${prizeType}_prize_amount[]`;
                prizeInput.id = `${prizeType}_amount`;
                prizeInput.className = 'form-control first-entry-amount';
                prizeInput.value = hiddenAmountInput.value;
                prizeInput.onwheel = function() { this.blur(); };
                
                // Set up event listener for amount changes to update inherited amounts
                prizeInput.addEventListener('input', () => {
                    const allEntries = entriesContainer.querySelectorAll('.prize-entry');
                    allEntries.forEach((entryEl, entryIdx) => {
                        if (entryIdx > 0) { // Skip the first entry
                            const inheritedInput = entryEl.querySelector('.inherited-amount');
                            if (inheritedInput) {
                                inheritedInput.value = prizeInput.value;
                            }
                        }
                    });
                    isDirty = true;
                    notifyPreviewUpdate();
                });
                
                prizeGroup.appendChild(prizeLabel);
                prizeGroup.appendChild(prizeInput);
                
                // Replace hidden input with visible one
                const formRow = firstEntry.querySelector('.form-row');
                formRow.removeChild(hiddenAmountInput);
                formRow.insertBefore(prizeGroup, formRow.firstChild);
            }
        }
        
        // Ensure all ticket inputs in the first entry are properly set up
        const ticketInputs = firstEntry.querySelectorAll(`input[name="${prizeType}_ticket_number[]"]`);
        ticketInputs.forEach((ticketInput, index) => {
            // Apply event listeners and no-spaces functionality
            applyNoSpacesToInput(ticketInput);
            ticketInput.addEventListener('change', () => {
                isDirty = true;
                notifyPreviewUpdate();
            });
            
            // Set up auto-save for 4th-10th prizes
            const autoSavePrizes = ['4th', '5th', '6th', '7th', '8th', '9th', '10th'];
            if (autoSavePrizes.includes(prizeType)) {
                setupAutoSaveForInput(ticketInput, prizeType);
            }
        });
    }
    
    // Update the entry counter based on final count
    entryCounters[prizeType] = entriesContainer.children.length;
    isDirty = true;
    
    // Reset the toggle switch to "Normal" position and hide bulk section
    const toggleSwitch = document.querySelector(`#${prizeType}-section .toggle-switch input[type="checkbox"]`);
    if (toggleSwitch) {
        toggleSwitch.checked = false;
    }
    
    // Hide the bulk section
    const bulkSectionElement = document.getElementById(prizeType + '-bulk');
    if (bulkSectionElement) {
        bulkSectionElement.style.display = 'none';
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
    
    // Renumber all ticket fields for 4th-10th prizes after bulk processing
    renumberTicketFields(prizeType);
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
 * Set default prize amounts for 1st, 2nd, 3rd prizes
 */
function setDefaultPrizeAmounts() {
    // Only set defaults if we're not in edit mode (no existing data)
    const isEditMode = document.querySelector('input[name="result_id"]') !== null;
    if (isEditMode) {
        return; // Don't set defaults in edit mode
    }
    
    // Default amounts
    const defaultAmounts = {
        '1st': '10000000',    // 1 crore
        '2nd': '3000000',     // 30 lakh  
        '3rd': '500000'       // 5 lakh
    };
    
    // Set default amounts for 1st, 2nd, 3rd prize first entries
    Object.keys(defaultAmounts).forEach(prizeType => {
        const amountInput = document.querySelector(`input[name="${prizeType}_prize_amount[]"]`);
        if (amountInput && !amountInput.value.trim()) {
            amountInput.value = defaultAmounts[prizeType];
            
            // Mark form as clean initially since these are defaults
            setTimeout(() => {
                // Only mark clean if user hasn't made other changes
                if (amountInput.value === defaultAmounts[prizeType]) {
                    // Don't mark as dirty for default values
                }
            }, 100);
        }
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
        
        const specialPrizes = ['consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th'];
        const isSpecialPrize = specialPrizes.includes(prizeType);
        
        if (isSpecialPrize) {
            // For special prizes, group tickets by 3 per entry
            const groupedEntries = [];
            for (let i = 0; i < entries.length; i += 3) {
                const entryGroup = entries.slice(i, i + 3);
                if (entryGroup.length > 0) {
                    groupedEntries.push({
                        prize_amount: entryGroup[0].prize_amount,
                        tickets: entryGroup.map(e => e.ticket_number)
                    });
                }
            }
            
            groupedEntries.forEach((group, groupIndex) => {
                const newEntry = templateEntry.cloneNode(true);
                newEntry.setAttribute('data-entry-index', groupIndex);
                
                const amountInput = newEntry.querySelector(`input[name="${prizeType}_prize_amount[]"]`);
                
                // Set amount for the entry
                if (groupIndex === 0) {
                    // First entry keeps visible amount field
                    if (amountInput) amountInput.value = group.prize_amount || '';
                } else {
                    // Additional entries get hidden amount field
                    const formRow = newEntry.querySelector('.form-row');
                    const prizeAmountField = newEntry.querySelector('.prize-amount-field');
                    
                    if (prizeAmountField && formRow) {
                        prizeAmountField.remove();
                        
                        const hiddenAmountInput = document.createElement('input');
                        hiddenAmountInput.type = 'hidden';
                        hiddenAmountInput.name = `${prizeType}_prize_amount[]`;
                        hiddenAmountInput.value = group.prize_amount || '';
                        hiddenAmountInput.classList.add('inherited-amount');
                        
                        formRow.appendChild(hiddenAmountInput);
                    }
                }
                
                // Set ticket values in the 3 available fields
                const ticketFields = newEntry.querySelectorAll(`input[name="${prizeType}_ticket_number[]"]`);
                group.tickets.forEach((ticket, ticketIndex) => {
                    if (ticketFields[ticketIndex]) {
                        ticketFields[ticketIndex].value = ticket || '';
                        // Initialize _originalValue for auto-save tracking
                        ticketFields[ticketIndex]._originalValue = ticket || '';
                    }
                });
                
                
                setupEntryChangeTracking(newEntry);
                entriesContainer.appendChild(newEntry);
            });
            
            entryCounters[prizeType] = groupedEntries.length;
        } else {
            // Regular prizes - original logic
            entries.forEach((entry, index) => {
                const newEntry = templateEntry.cloneNode(true);
                newEntry.setAttribute('data-entry-index', index);
                
                const amountInput = newEntry.querySelector(`input[name="${prizeType}_prize_amount[]"]`);
                const ticketInput = newEntry.querySelector(`input[name="${prizeType}_ticket_number[]"]`);
                
                if (amountInput) amountInput.value = entry.prize_amount || '';
                if (ticketInput) {
                    ticketInput.value = entry.ticket_number || '';
                    // Initialize _originalValue for auto-save tracking
                    ticketInput._originalValue = entry.ticket_number || '';
                }
                
                if (prizeType === '1st' || prizeType === '2nd' || prizeType === '3rd') {
                    const placeInput = newEntry.querySelector(`input[name="${prizeType}_place[]"]`);
                    if (placeInput) placeInput.value = entry.place || '';
                }
                
                
                setupEntryChangeTracking(newEntry);
                entriesContainer.appendChild(newEntry);
            });
            
            entryCounters[prizeType] = entries.length;
        }
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
 * Initialize fixed bottom buttons functionality
 */
function initializeFixedButtons() {
    const previewBtn = document.querySelector('.preview-toggle-btn');
    if (previewBtn) {
        previewBtn.addEventListener('click', handlePreviewToggle);
    }
    
    // REMOVED: enhanceFixedSaveButton() call to prevent duplicate listeners
    
    setupKeyboardShortcuts();
    initScrollBehavior();
    initButtonInteractions();
}

/**
 * Handle preview toggle for fixed buttons
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
 * Better basic preview generation with more robust error handling
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
 * Setup keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            const saveBtn = document.querySelector('.save-btn-bottom');
            if (saveBtn && !saveBtn.disabled) {
                document.getElementById('lotteryForm').dispatchEvent(new Event('submit'));
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

/**
 * Apply no-spaces functionality to inputs
 */
function applyNoSpacesToInput(input) {
    if (!input) return;
    
    // Check if this input should not have spaces
    const noSpaceFields = ['ticket_number', 'place', 'draw_number'];
    const shouldApplyNoSpaces = noSpaceFields.some(field => 
        input.name && input.name.includes(field)
    );
    
    if (shouldApplyNoSpaces) {
        // Add visual indicator
        input.style.borderLeft = '3px solid #28a745';
        input.title = 'Spaces are not allowed in this field';
        
        // Remove spaces function
        function removeSpaces() {
            if (input.value) {
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
        
        // Handle input event (real-time removal)
        input.addEventListener('input', removeSpaces);
        
        // Handle paste event
        input.addEventListener('paste', function() {
            setTimeout(removeSpaces, 10);
        });
        
        // Handle keydown to prevent space key
        input.addEventListener('keydown', function(e) {
            if (e.code === 'Space' || e.key === ' ') {
                e.preventDefault();
                showSpaceNotification();
                return false;
            }
        });
        
        // Handle blur to clean up any remaining spaces
        input.addEventListener('blur', removeSpaces);
    }
}

/**
 * Validate 4-digit input for 7th-10th prizes with enhanced error messaging
 */
function validateFourDigitInput(input, prizeType) {
    const value = input.value.trim();
    
    // Clear any existing error styling
    clearInputError(input);
    
    // If empty, just show default placeholder
    if (value === '') {
        input.title = 'Enter exactly 4 digits';
        return;
    }
    
    // Check for non-numeric characters  
    if (!/^\d+$/.test(value)) {
        // Just clear any existing errors, don't show new inline errors
        return;
    }
    
    // Check length - must be exactly 4 digits
    if (value.length !== 4) {
        // Just clear any existing errors, don't show new inline errors
        return;
    }
    
    // If we reach here, validation passed
    input.title = `${prizeType} prize ticket number: ${value} ✓`;
}

/**
 * Show error styling and message for input validation
 */
function showInputError(input, message) {
    // Apply error styling
    input.style.borderColor = '#dc3545';
    input.style.backgroundColor = '#fff5f5';
    input.style.boxShadow = '0 0 0 0.2rem rgba(220, 53, 69, 0.25)';
    input.title = message;
    
    // Show inline error message
    showInlineErrorMessage(input, message);
}

/**
 * Clear error styling from input
 */
function clearInputError(input) {
    input.style.borderColor = '';
    input.style.backgroundColor = '';
    input.style.boxShadow = '';
    
    // Clear inline error message
    clearInlineErrorMessage(input);
}

/**
 * Show inline error message below input
 */
function showInlineErrorMessage(input, message) {
    // Remove existing error message
    clearInlineErrorMessage(input);
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'inline-error-message';
    errorDiv.innerHTML = `<span class="error-icon">❌</span> ${message}`;
    errorDiv.style.cssText = `
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
        border-radius: 0 0 4px 4px;
        padding: 8px 12px;
        font-size: 12px;
        line-height: 1.4;
        z-index: 1000;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        animation: slideDown 0.2s ease-out;
        word-wrap: break-word;
    `;
    
    // Add animation keyframes if not already added
    if (!document.getElementById('validation-animations')) {
        const style = document.createElement('style');
        style.id = 'validation-animations';
        style.textContent = `
            @keyframes slideDown {
                from { opacity: 0; transform: translateY(-5px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @keyframes fadeOut {
                from { opacity: 1; }
                to { opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Make parent position relative to position error message
    const parent = input.parentElement;
    if (parent && window.getComputedStyle(parent).position === 'static') {
        parent.style.position = 'relative';
    }
    
    parent.appendChild(errorDiv);
}

/**
 * Clear inline error message
 */
function clearInlineErrorMessage(input) {
    const parent = input.parentElement;
    if (parent) {
        const existingError = parent.querySelector('.inline-error-message');
        if (existingError) {
            existingError.style.animation = 'fadeOut 0.2s ease-out';
            setTimeout(() => {
                if (existingError.parentNode) {
                    existingError.parentNode.removeChild(existingError);
                }
            }, 200);
        }
    }
}

/**
 * Show notification when spaces are prevented
 */
function showSpaceNotification() {
    let notification = document.getElementById('space-prevented-notification');
    
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'space-prevented-notification';
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: #ffc107;
            color: #856404;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 9999;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            opacity: 0;
            transition: opacity 0.3s ease;
            font-weight: 500;
        `;
        notification.innerHTML = '⚠️ Spaces not allowed';
        document.body.appendChild(notification);
    }
    
    notification.style.opacity = '1';
    
    setTimeout(() => {
        notification.style.opacity = '0';
    }, 1500);
}

// Initialize when DOM is loaded - SINGLE INITIALIZATION
document.addEventListener('DOMContentLoaded', function() {
    initLotteryAdmin();
});


/**
 * Auto-save ticket number when user moves to next field
 */
function autoSaveTicket(ticketInput, prizeType) {
    const ticketNumber = ticketInput.value.trim();
    
    // Only auto-save for 4th-10th prizes
    const autoSavePrizes = ['4th', '5th', '6th', '7th', '8th', '9th', '10th'];
    if (!autoSavePrizes.includes(prizeType)) {
        return;
    }
    
    // Don't save empty ticket numbers
    if (!ticketNumber) {
        return;
    }
    
    // Validate 4-digit requirement for 7th-10th prizes before auto-saving
    const fourDigitPrizes = ['7th', '8th', '9th', '10th'];
    if (fourDigitPrizes.includes(prizeType)) {
        // Check for non-numeric characters
        if (!/^\d+$/.test(ticketNumber)) {
            showAutoSaveError(ticketInput, `${prizeType} prize ticket must contain only numbers (0-9). Auto-save cancelled.`);
            return;
        }
        
        // Check length - must be exactly 4 digits
        if (ticketNumber.length !== 4) {
            if (ticketNumber.length < 4) {
                showAutoSaveError(ticketInput, `${prizeType} prize requires exactly 4 digits. You entered ${ticketNumber.length} digit${ticketNumber.length === 1 ? '' : 's'}. Auto-save cancelled.`);
            } else {
                showAutoSaveError(ticketInput, `${prizeType} prize requires exactly 4 digits. You entered ${ticketNumber.length} digits. Auto-save cancelled.`);
            }
            return;
        }
    }
    
    // Get result ID (required for auto-save)
    const resultIdInput = document.querySelector('input[name="result_id"]');
    if (!resultIdInput || !resultIdInput.value) {
        showAutoSaveError(ticketInput, 'Please save the form first before auto-saving tickets');
        return;
    }
    
    // Get prize amount for validation
    const prizeAmountInput = getPrizeAmountForType(prizeType);
    if (!prizeAmountInput || !prizeAmountInput.value.trim() || prizeAmountInput.value.trim() === '0') {
        showAutoSaveError(ticketInput, 'Please enter prize amount first');
        return;
    }
    
    // Show saving indicator
    showAutoSavingIndicator(ticketInput);
    
    // Prepare data for auto-save
    const saveData = {
        result_id: resultIdInput.value,
        prize_type: prizeType,
        ticket_number: ticketNumber,
        prize_amount: prizeAmountInput.value.trim(),
        original_ticket_number: ticketInput._originalValue || ''  // Include original ticket number for edit tracking
    };
    
    // Make AJAX call to auto-save
    fetch('/api/results/admin/auto-save-ticket/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(saveData)
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 403) {
                throw new Error('CSRF verification failed. Please refresh the page.');
            } else if (response.status === 404) {
                throw new Error('Auto-save endpoint not found. Please contact support.');
            } else {
                throw new Error(`Server error (${response.status}). Please try again.`);
            }
        }
        
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showAutoSaveSuccess(ticketInput, data.message);
            console.log(`Auto-saved ticket: ${ticketNumber} for ${prizeType} prize`);
        } else {
            showAutoSaveError(ticketInput, data.error || 'Failed to auto-save');
        }
    })
    .catch(error => {
        console.error('Auto-save error:', error);
        showAutoSaveError(ticketInput, error.message);
    });
}

/**
 * Get prize amount input for a specific prize type
 */
function getPrizeAmountForType(prizeType) {
    // Look for the first entry's amount input for this prize type
    const entriesContainer = document.getElementById(prizeType + '-entries');
    if (!entriesContainer) return null;
    
    const firstEntry = entriesContainer.children[0];
    if (!firstEntry) return null;
    
    // Look for visible amount input first (first-entry-amount)
    let amountInput = firstEntry.querySelector('.first-entry-amount');
    if (!amountInput) {
        // Fall back to any amount input
        amountInput = firstEntry.querySelector(`input[name="${prizeType}_prize_amount[]"]`);
    }
    
    return amountInput;
}

/**
 * Show auto-saving indicator
 */
function showAutoSavingIndicator(ticketInput) {
    clearAutoSaveIndicators(ticketInput);
    
    const indicator = document.createElement('div');
    indicator.className = 'auto-save-indicator saving';
    indicator.innerHTML = '💾 Saving...';
    indicator.style.cssText = `
        position: absolute;
        bottom: -25px;
        left: 0;
        font-size: 11px;
        color: #007bff;
        background: rgba(255, 255, 255, 0.95);
        padding: 2px 8px;
        border-radius: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.15);
        z-index: 100;
        white-space: nowrap;
        border: 1px solid #007bff;
    `;
    
    // Add to the form row container to avoid blocking fields
    const formRow = ticketInput.closest('.form-row');
    if (formRow) {
        formRow.style.position = 'relative';
        formRow.appendChild(indicator);
    }
}

/**
 * Show auto-save success indicator
 */
function showAutoSaveSuccess(ticketInput, message) {
    clearAutoSaveIndicators(ticketInput);
    
    const indicator = document.createElement('div');
    indicator.className = 'auto-save-indicator success';
    indicator.innerHTML = '✅ Saved';
    indicator.style.cssText = `
        position: absolute;
        bottom: -25px;
        left: 0;
        font-size: 11px;
        color: #28a745;
        background: rgba(255, 255, 255, 0.95);
        padding: 2px 8px;
        border-radius: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.15);
        z-index: 100;
        white-space: nowrap;
        border: 1px solid #28a745;
    `;
    
    // Add to the form row container to avoid blocking fields
    const formRow = ticketInput.closest('.form-row');
    if (formRow) {
        formRow.style.position = 'relative';
        formRow.appendChild(indicator);
    }
    
    // Remove success indicator after 3 seconds
    setTimeout(() => {
        clearAutoSaveIndicators(ticketInput);
    }, 3000);
}

/**
 * Show auto-save error indicator
 */
function showAutoSaveError(ticketInput, errorMessage) {
    clearAutoSaveIndicators(ticketInput);
    
    const indicator = document.createElement('div');
    indicator.className = 'auto-save-indicator error';
    indicator.innerHTML = '❌ Failed';
    indicator.title = errorMessage;
    indicator.style.cssText = `
        position: absolute;
        bottom: -25px;
        left: 0;
        font-size: 11px;
        color: #dc3545;
        background: rgba(255, 255, 255, 0.95);
        padding: 2px 8px;
        border-radius: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.15);
        z-index: 100;
        cursor: help;
        white-space: nowrap;
        border: 1px solid #dc3545;
    `;
    
    // Add to the form row container to avoid blocking fields
    const formRow = ticketInput.closest('.form-row');
    if (formRow) {
        formRow.style.position = 'relative';
        formRow.appendChild(indicator);
    }
    
    // Remove error indicator after 5 seconds
    setTimeout(() => {
        clearAutoSaveIndicators(ticketInput);
    }, 5000);
    
    // Also show notification for more detail
    showNotification(errorMessage, 'error');
}

/**
 * Clear auto-save indicators
 */
function clearAutoSaveIndicators(ticketInput) {
    const formRow = ticketInput.closest('.form-row');
    if (formRow) {
        const indicators = formRow.querySelectorAll('.auto-save-indicator');
        indicators.forEach(indicator => indicator.remove());
    }
}

/**
 * Get CSRF token for AJAX requests
 */
function getCsrfToken() {
    // Try multiple ways to get CSRF token
    let token = '';
    
    // Method 1: Hidden input field (most reliable in Django forms)
    const tokenInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (tokenInput && tokenInput.value) {
        return tokenInput.value;
    }
    
    // Method 2: Meta tag
    const tokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (tokenMeta && tokenMeta.content) {
        return tokenMeta.content;
    }
    
    // Method 3: Cookie (if available)
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }
    
    console.warn('No CSRF token found for auto-save!');
    return '';
}

/**
 * Set up auto-save for ticket number inputs
 */
function setupAutoSaveForTicketInputs() {
    // Only set up for 4th-10th prizes
    const autoSavePrizes = ['4th', '5th', '6th', '7th', '8th', '9th', '10th'];
    
    autoSavePrizes.forEach(prizeType => {
        const entriesContainer = document.getElementById(prizeType + '-entries');
        if (!entriesContainer) return;
        
        // Set up auto-save for existing ticket inputs
        const ticketInputs = entriesContainer.querySelectorAll(`input[name="${prizeType}_ticket_number[]"]`);
        ticketInputs.forEach(ticketInput => {
            setupAutoSaveForInput(ticketInput, prizeType);
        });
    });
}

/**
 * Set up auto-save for a single input
 */
function setupAutoSaveForInput(ticketInput, prizeType) {
    // Remove existing auto-save listeners to avoid duplicates
    if (ticketInput._autoSaveHandler) {
        ticketInput.removeEventListener('blur', ticketInput._autoSaveHandler);
    }
    if (ticketInput._focusHandler) {
        ticketInput.removeEventListener('focus', ticketInput._focusHandler);
    }
    
    // Create focus handler to store original value
    ticketInput._focusHandler = function() {
        // Store the original value when focus is gained
        ticketInput._originalValue = ticketInput.value.trim();
    };
    
    // Create auto-save handler
    ticketInput._autoSaveHandler = function() {
        // Small delay to ensure the input value is finalized
        setTimeout(() => {
            autoSaveTicket(ticketInput, prizeType);
        }, 100);
    };
    
    // Add focus event listener to track original value
    ticketInput.addEventListener('focus', ticketInput._focusHandler);
    
    // Add blur event listener for auto-save
    ticketInput.addEventListener('blur', ticketInput._autoSaveHandler);
    
    // Add visual indicator that this field has auto-save
    ticketInput.title = (ticketInput.title || '') + ' (Auto-saves when you move to next field)';
    ticketInput.style.borderLeft = '3px solid #007bff'; // Blue border to indicate auto-save
}

/**
 * Delete individual ticket from database for 4th-10th prizes
 */

// Export functions for global access
window.addEntry = addEntry;
window.addMultipleFields = addMultipleFields;
window.clearAllFields = clearAllFields;
window.toggleBulkEntry = toggleBulkEntry;
window.processBulkEntries = processBulkEntries;
window.handlePreviewToggle = handlePreviewToggle;
window.showNotification = showNotification;
window.setupAutoSaveForInput = setupAutoSaveForInput;