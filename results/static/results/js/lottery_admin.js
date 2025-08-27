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
 * Add entry to prize section
 */
function addEntry(prizeType) {
    const entriesContainer = document.getElementById(prizeType + '-entries');
    if (!entriesContainer) return;
    
    const firstEntry = entriesContainer.children[0];
    if (!firstEntry) return;
    
    const entryIndex = entriesContainer.children.length;
    const specialPrizes = ['consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th'];
    const isSpecialPrize = specialPrizes.includes(prizeType);
    
    // Create new entry element from scratch
    const newEntry = document.createElement('div');
    newEntry.className = 'prize-entry';
    newEntry.setAttribute('data-entry-index', entryIndex);
    
    // Create form row
    const formRow = document.createElement('div');
    formRow.className = 'form-row';
    
    // For special prizes (consolation, 4th-10th), additional entries don't get prize amount field
    if (isSpecialPrize && entryIndex >= 1) {
        // Get first entry amount for inheritance
        const firstEntryAmountInput = firstEntry.querySelector('input[type="number"]') || 
                                    firstEntry.querySelector('.first-entry-amount') ||
                                    firstEntry.querySelector(`input[name="${prizeType}_prize_amount[]"]`);
        const inheritedAmount = firstEntryAmountInput ? firstEntryAmountInput.value : '';
        
        // Create hidden input for prize amount
        const hiddenAmountInput = document.createElement('input');
        hiddenAmountInput.type = 'hidden';
        hiddenAmountInput.name = `${prizeType}_prize_amount[]`;
        hiddenAmountInput.value = inheritedAmount;
        hiddenAmountInput.classList.add('inherited-amount');
        formRow.appendChild(hiddenAmountInput);
        
        // Set up listener to update inherited value when first entry changes
        if (firstEntryAmountInput) {
            firstEntryAmountInput.addEventListener('input', () => {
                hiddenAmountInput.value = firstEntryAmountInput.value;
            });
        }
        
        // Determine number of rows based on prize type
        // 6th-10th prizes get 6 rows, others get 1 row
        const expandedPrizes = ['6th', '7th', '8th', '9th', '10th'];
        const totalRows = expandedPrizes.includes(prizeType) ? 6 : 1;
        
        // Create rows of 3 ticket fields each
        for (let rowIndex = 0; rowIndex < totalRows; rowIndex++) {
            // Create a new form row for each row (except the first one which uses existing formRow)
            let currentFormRow = formRow;
            if (rowIndex > 0) {
                currentFormRow = document.createElement('div');
                currentFormRow.className = 'form-row';
                newEntry.appendChild(currentFormRow);
            }
            
            // Create 3 ticket fields for this row
            for (let fieldIndex = 0; fieldIndex < 3; fieldIndex++) {
                const ticketGroup = document.createElement('div');
                ticketGroup.className = 'form-group ticket-field-group';
                
                const ticketLabel = document.createElement('label');
                ticketLabel.setAttribute('for', `${prizeType}_ticket_${entryIndex}_${rowIndex}_${fieldIndex}`);
                // Only label the first field of each row
                ticketLabel.textContent = fieldIndex === 0 ? 'Ticket Numbers' : '';
                
                const inputContainer = document.createElement('div');
                inputContainer.className = 'input-with-remove';
                
                const ticketInput = document.createElement('input');
                ticketInput.type = 'text';
                ticketInput.name = `${prizeType}_ticket_number[]`;
                ticketInput.id = `${prizeType}_ticket_${entryIndex}_${rowIndex}_${fieldIndex}`;
                ticketInput.className = 'form-control';
                
                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.className = 'remove-ticket-btn';
                removeBtn.innerHTML = '×';
                removeBtn.title = 'Clear this ticket number';
                removeBtn.onclick = function() {
                    ticketInput.value = '';
                    ticketInput.focus();
                    isDirty = true;
                    notifyPreviewUpdate();
                };
                
                inputContainer.appendChild(ticketInput);
                inputContainer.appendChild(removeBtn);
                
                ticketGroup.appendChild(ticketLabel);
                ticketGroup.appendChild(inputContainer);
                currentFormRow.appendChild(ticketGroup);
                
                // Set up event listeners
                ticketInput.addEventListener('change', () => {
                    isDirty = true;
                    notifyPreviewUpdate();
                });
                applyNoSpacesToInput(ticketInput);
                
                // Set up auto-save for 4th-10th prizes
                const autoSavePrizes = ['4th', '5th', '6th', '7th', '8th', '9th', '10th'];
                if (autoSavePrizes.includes(prizeType)) {
                    setupAutoSaveForInput(ticketInput, prizeType);
                }
                
                // Focus on first ticket input
                if (rowIndex === 0 && fieldIndex === 0) {
                    setTimeout(() => ticketInput.focus(), 100);
                }
            }
        }
        
    } else {
        // Regular entry (first entry for special prizes, or any entry for 1st/2nd/3rd prizes)
        // Clone from first entry and modify
        const clonedEntry = firstEntry.cloneNode(true);
        newEntry.innerHTML = clonedEntry.innerHTML;
        
        // Fix duplicate IDs
        const inputs = newEntry.querySelectorAll('input');
        inputs.forEach((input, inputIndex) => {
            if (input.id) {
                input.id = `${input.id}_${entryIndex}_${inputIndex}`;
            }
            input.value = '';
            
            // Set default amount for 1st, 2nd, 3rd prize amount fields
            if (input.name && input.name.includes('_prize_amount[]')) {
                const defaultAmounts = {
                    '1st': '10000000',    // 1 crore
                    '2nd': '3000000',     // 30 lakh  
                    '3rd': '500000'       // 5 lakh
                };
                
                if (prizeType in defaultAmounts) {
                    input.value = defaultAmounts[prizeType];
                }
            }
            
            input.addEventListener('change', () => {
                isDirty = true;
                notifyPreviewUpdate();
            });
            applyNoSpacesToInput(input);
        });
        
        // Fix label for attributes
        const labels = newEntry.querySelectorAll('label[for]');
        labels.forEach((label, labelIndex) => {
            if (label.getAttribute('for')) {
                label.setAttribute('for', `${label.getAttribute('for')}_${entryIndex}_${labelIndex}`);
            }
        });
        
        // Focus on first input
        const firstInput = newEntry.querySelector('input');
        if (firstInput) setTimeout(() => firstInput.focus(), 100);
    }
    
    // Add form row to entry (always add the first form row)
    if (!newEntry.querySelector('.form-row')) {
        newEntry.appendChild(formRow);
    }
    
    // Add remove button for additional entries
    if (entryIndex > 0) {
        addRemoveButtonToEntry(newEntry, entriesContainer);
    }
    
    entryCounters[prizeType] = (entryCounters[prizeType] || 0) + 1;
    entriesContainer.appendChild(newEntry);
    isDirty = true;
    notifyPreviewUpdate();
}

/**
 * Delete all additional entries and clear all ticket numbers and prize amount
 */
function deleteAllAdditionalEntries(prizeType) {
    const entriesContainer = document.getElementById(prizeType + '-entries');
    if (!entriesContainer) return;
    
    const entries = Array.from(entriesContainer.children);
    const firstEntry = entries[0];
    
    // Check if there's anything to clear
    const hasAdditionalEntries = entries.length > 1;
    let hasTicketNumbers = false;
    let hasPrizeAmount = false;
    
    if (firstEntry) {
        // Check for ticket numbers
        const ticketInputs = firstEntry.querySelectorAll('input[name$="_ticket_number[]"]');
        hasTicketNumbers = Array.from(ticketInputs).some(input => input.value.trim() !== '');
        
        // Check for prize amount
        const prizeInput = firstEntry.querySelector('input[name$="_prize_amount[]"]');
        hasPrizeAmount = prizeInput && prizeInput.value.trim() !== '';
    }
    
    if (!hasAdditionalEntries && !hasTicketNumbers && !hasPrizeAmount) {
        showNotification('No entries or data to clear.', 'info');
        return;
    }
    
    // Build confirmation message based on what will be cleared
    let confirmMessage = 'Are you sure you want to clear:\n';
    if (hasAdditionalEntries) {
        const additionalCount = entries.length - 1;
        confirmMessage += `• ${additionalCount} additional entries\n`;
    }
    if (hasTicketNumbers) {
        confirmMessage += '• All ticket numbers\n';
    }
    if (hasPrizeAmount) {
        confirmMessage += '• Prize amount\n';
    }
    confirmMessage += '\nThis cannot be undone.';
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    // Remove all additional entries (keep only the first entry)
    for (let i = entries.length - 1; i >= 1; i--) {
        console.log(`Removing entry ${i}:`, entries[i]);
        entriesContainer.removeChild(entries[i]);
    }
    
    // Clear all ticket numbers and prize amount from the first entry
    if (firstEntry) {
        // Clear all ticket number inputs
        const ticketInputs = firstEntry.querySelectorAll('input[name$="_ticket_number[]"]');
        console.log(`Found ${ticketInputs.length} ticket inputs to clear`);
        ticketInputs.forEach((input, index) => {
            console.log(`Clearing ticket input ${index}: ${input.name} = "${input.value}"`);
            input.value = '';
        });
        
        // Clear prize amount input
        const prizeInput = firstEntry.querySelector('input[name$="_prize_amount[]"]');
        if (prizeInput) {
            console.log(`Clearing prize input: ${prizeInput.name} = "${prizeInput.value}"`);
            prizeInput.value = '';
        }
        
        // Force DOM update
        firstEntry.style.display = 'none';
        setTimeout(() => {
            firstEntry.style.display = '';
        }, 10);
    }
    
    // Update counter
    entryCounters[prizeType] = 1;
    isDirty = true;
    notifyPreviewUpdate();
    
    // Build success message
    let successMessage = 'Cleared: ';
    const clearedItems = [];
    if (hasAdditionalEntries) {
        const additionalCount = entries.length - 1;
        clearedItems.push(`${additionalCount} additional entries`);
    }
    if (hasTicketNumbers) {
        clearedItems.push('all ticket numbers');
    }
    if (hasPrizeAmount) {
        clearedItems.push('prize amount');
    }
    successMessage += clearedItems.join(', ');
    
    showNotification(successMessage, 'success');
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
            // Determine tickets per entry based on prize type
            // 6th-10th prizes get 18 tickets per entry (6 rows), others get 3 tickets (1 row)
            const expandedPrizes = ['6th', '7th', '8th', '9th', '10th'];
            const ticketsPerEntry = expandedPrizes.includes(prizeType) ? 18 : 3;
            
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
            formRow.className = 'form-row';
            
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
            
            // Determine number of rows and create ticket fields
            const totalRows = expandedPrizes.includes(prizeType) ? 6 : 1;
            
            // Create rows of 3 ticket fields each
            for (let rowIndex = 0; rowIndex < totalRows; rowIndex++) {
                // Create a new form row for each row (except the first one which uses existing formRow)
                let currentFormRow = formRow;
                if (rowIndex > 0) {
                    currentFormRow = document.createElement('div');
                    currentFormRow.className = 'form-row';
                    entry.appendChild(currentFormRow);
                }
                
                // Create 3 ticket fields for this row
                for (let fieldIndex = 0; fieldIndex < 3; fieldIndex++) {
                    const ticketGroup = document.createElement('div');
                    ticketGroup.className = 'form-group ticket-field-group';
                    
                    const ticketLabel = document.createElement('label');
                    // Only label the first field of each row
                    ticketLabel.textContent = fieldIndex === 0 ? 'Ticket Numbers' : '';
                    
                    const inputContainer = document.createElement('div');
                    inputContainer.className = 'input-with-remove';
                    
                    const ticketInput = document.createElement('input');
                    ticketInput.type = 'text';
                    ticketInput.name = `${prizeType}_ticket_number[]`;
                    ticketInput.id = `${prizeType}_ticket_bulk_${(hasEmptyFirstEntry ? 0 : currentEntryCount) + newEntryIndex}_${rowIndex}_${fieldIndex}`;
                    ticketInput.className = 'form-control';
                    
                    // Calculate ticket index for this field
                    const ticketIndex = (rowIndex * 3) + fieldIndex;
                    const ticketValue = ticketIndex < entryTickets.length ? entryTickets[ticketIndex].trim() : '';
                    ticketInput.value = ticketValue;
                    
                    const removeBtn = document.createElement('button');
                    removeBtn.type = 'button';
                    removeBtn.className = 'remove-ticket-btn';
                    removeBtn.innerHTML = '×';
                    removeBtn.title = 'Clear this ticket number';
                    removeBtn.onclick = function() {
                        ticketInput.value = '';
                        ticketInput.focus();
                        isDirty = true;
                        notifyPreviewUpdate();
                    };
                    
                    inputContainer.appendChild(ticketInput);
                    inputContainer.appendChild(removeBtn);
                    
                    ticketGroup.appendChild(ticketLabel);
                    ticketGroup.appendChild(inputContainer);
                    currentFormRow.appendChild(ticketGroup);
                    
                    applyNoSpacesToInput(ticketInput);
                    ticketInput.setAttribute('data-bulk-field', 'true');
                    
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
            
            // Add remove button for additional entries (any entry that's not the very first one in the entire container)
            if (!isVeryFirstEntry) {
                addRemoveButtonToEntry(entry, entriesContainer);
            }
            
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
            
            // Add remove button for additional entries (not the first entry in container)
            const isFirstInContainer = (currentEntryCount === 0 && successCount === 0);
            if (!isFirstInContainer) {
                addRemoveButtonToEntry(newEntry, entriesContainer);
            }
            
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
                    }
                });
                
                if (groupIndex > 0) {
                    addRemoveButtonToEntry(newEntry, entriesContainer);
                }
                
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
 * Helper function to add remove button to an entry
 */
function addRemoveButtonToEntry(entryElement, container) {
    // Don't add remove button if it already exists
    if (entryElement.querySelector('.remove-entry-btn')) {
        return;
    }
    
    // Get all form rows in this entry
    const formRows = entryElement.querySelectorAll('.form-row');
    if (formRows.length === 0) return;
    
    // For entries with multiple rows (6th-10th prizes), add button to the last row
    // For single row entries, add to the first (and only) row
    const targetRow = formRows[formRows.length - 1];
    
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
    targetRow.appendChild(actionDiv);
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
        prize_amount: prizeAmountInput.value.trim()
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
    // Remove existing auto-save listener to avoid duplicates
    ticketInput.removeEventListener('blur', ticketInput._autoSaveHandler);
    
    // Create auto-save handler
    ticketInput._autoSaveHandler = function() {
        // Small delay to ensure the input value is finalized
        setTimeout(() => {
            autoSaveTicket(ticketInput, prizeType);
        }, 100);
    };
    
    // Add blur event listener for auto-save
    ticketInput.addEventListener('blur', ticketInput._autoSaveHandler);
    
    // Add visual indicator that this field has auto-save
    ticketInput.title = (ticketInput.title || '') + ' (Auto-saves when you move to next field)';
    ticketInput.style.borderLeft = '3px solid #007bff'; // Blue border to indicate auto-save
}

// Export functions for global access
window.addEntry = addEntry;
window.deleteAllAdditionalEntries = deleteAllAdditionalEntries;
window.toggleBulkEntry = toggleBulkEntry;
window.processBulkEntries = processBulkEntries;
window.handlePreviewToggle = handlePreviewToggle;
window.showNotification = showNotification;
window.setupAutoSaveForInput = setupAutoSaveForInput;