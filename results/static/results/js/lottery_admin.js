/**
 * Lottery Admin Enhancement Script
 * Path: results/static/results/js/lottery_admin.js
 * 
 * This script provides additional functionality for the lottery result entry form,
 * including dynamic form handling, validation, preview capabilities, and more.
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
}

/**
 * FIXED VERSION - Replace the addEntry function in your existing JS file
 */
function addEntry(prizeType) {
    const entriesContainer = document.getElementById(prizeType + '-entries');
    if (!entriesContainer) {
        console.log(`Container for ${prizeType} not found`);
        return;
    }
    
    const firstEntry = entriesContainer.children[0];
    if (!firstEntry) {
        console.log(`No template entry found for ${prizeType}`);
        return;
    }
    
    const newEntry = firstEntry.cloneNode(true);
    
    // Clear input values
    const inputs = newEntry.querySelectorAll('input');
    inputs.forEach(input => {
        input.value = '';
        
        // Set up change tracking
        input.addEventListener('change', () => {
            isDirty = true;
        });
    });
    
    // Add remove button if this is not the first entry
    if (entriesContainer.children.length > 0 && !newEntry.querySelector('.remove-entry-btn')) {
        const formRow = newEntry.querySelector('.form-row');
        if (formRow) {
            const actionDiv = document.createElement('div');
            actionDiv.className = 'form-group';
            
            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'remove-entry-btn btn btn-danger btn-small';
            removeBtn.innerHTML = '❌ Remove';
            removeBtn.onclick = function() {
                entriesContainer.removeChild(newEntry);
                isDirty = true;
            };
            
            actionDiv.appendChild(removeBtn);
            formRow.appendChild(actionDiv);
        }
    }
    
    entryCounters[prizeType] = (entryCounters[prizeType] || 0) + 1;
    entriesContainer.appendChild(newEntry);
    isDirty = true;
    
    // Focus on the first input of the new entry
    const firstInput = newEntry.querySelector('input');
    if (firstInput) {
        firstInput.focus();
    }
}

/**
 * Toggle between normal and bulk entry modes
 * @param {string} prizeType - The type of prize
 */
function toggleBulkEntry(prizeType) {
    const bulkSection = document.getElementById(prizeType + '-bulk');
    const isVisible = bulkSection.style.display !== 'none';
    bulkSection.style.display = isVisible ? 'none' : 'block';
    
    if (!isVisible) {
        // Focus on the appropriate input when switching to bulk mode
        setTimeout(() => {
            // Check if this is a special prize type
            const specialPrizes = ['consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th'];
            if (specialPrizes.includes(prizeType)) {
                const amountInput = document.getElementById(prizeType + '-bulk-amount');
                if (amountInput) {
                    amountInput.focus();
                }
            } else {
                const textarea = document.getElementById(prizeType + '-bulk-textarea');
                if (textarea) {
                    textarea.focus();
                }
            }
        }, 100);
    }
}

/**
 * UPDATED VERSION - Process bulk entries with support for both formats
 */
function processBulkEntries(prizeType) {
    const textarea = document.getElementById(prizeType + '-bulk-textarea');
    const entriesContainer = document.getElementById(prizeType + '-entries');
    
    if (!textarea || !entriesContainer) {
        showNotification('Error: Could not find required elements.', 'error');
        return;
    }
    
    // Get the template entry
    const templateEntry = entriesContainer.children[0];
    if (!templateEntry) {
        showNotification('Error: No template entry found.', 'error');
        return;
    }
    
    // Clear existing entries
    entriesContainer.innerHTML = '';
    
    // Check if this is a special prize type (consolation, 4th-10th)
    const specialPrizes = ['consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th'];
    const isSpecialPrize = specialPrizes.includes(prizeType);
    
    let errorCount = 0;
    let successCount = 0;
    
    if (isSpecialPrize) {
        // Handle special prize format: amount from input field + space-separated ticket numbers
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
        
        // Get ticket numbers from textarea (space-separated, numbers only)
        const rawTicketNumbers = textarea.value.trim().split(/\s+/).filter(ticket => ticket.length > 0);
        
        // Validate and filter to only numeric values (any length)
        const ticketNumbers = rawTicketNumbers.filter(ticket => {
            const numericTicket = ticket.replace(/\D/g, ''); // Remove non-digits
            return numericTicket.length > 0; // Keep if there are any digits (no minimum length)
        });
        
        if (ticketNumbers.length === 0) {
            showNotification('No valid numeric ticket numbers found. Please enter numbers only.', 'warning');
            entriesContainer.appendChild(templateEntry);
            return;
        }
        
        // Track invalid entries
        const invalidCount = rawTicketNumbers.length - ticketNumbers.length;
        
        // Process each ticket number (accept any digit length)
        ticketNumbers.forEach((ticketNumber, index) => {
            const cleanTicketNumber = ticketNumber.replace(/\D/g, ''); // Clean to numbers only
            if (cleanTicketNumber.length > 0) { // Accept any length > 0
                const newEntry = templateEntry.cloneNode(true);
                
                // Set values using proper selectors
                const amountInput = newEntry.querySelector(`input[name="${prizeType}_prize_amount[]"]`);
                const ticketInput = newEntry.querySelector(`input[name="${prizeType}_ticket_number[]"]`);
                
                if (amountInput) amountInput.value = prizeAmount;
                if (ticketInput) ticketInput.value = cleanTicketNumber;
                
                // Add remove button for all except first entry
                if (successCount > 0) {
                    addRemoveButtonToEntry(newEntry, entriesContainer);
                }
                
                // Set up change tracking
                newEntry.querySelectorAll('input').forEach(input => {
                    input.addEventListener('change', () => {
                        isDirty = true;
                    });
                });
                
                entriesContainer.appendChild(newEntry);
                successCount++;
            } else {
                errorCount++;
            }
        });
        
        // Clear the inputs after processing
        bulkAmountInput.value = '';
        textarea.value = '';
        
    } else {
        // Handle original format for 1st, 2nd, 3rd prizes: amount,ticket_number,place per line
        const lines = textarea.value.trim().split('\n');
        if (lines.length === 0 || (lines.length === 1 && lines[0] === '')) {
            showNotification('No entries found in the bulk entry textarea.', 'warning');
            entriesContainer.appendChild(templateEntry);
            return;
        }
        
        lines.forEach((line, index) => {
            const values = line.split(',').map(v => v.trim());
            
            // Format: amount,ticket_number,place
            if (values.length < 2) {
                errorCount++;
                return;
            }
            
            const newEntry = templateEntry.cloneNode(true);
            
            // Set values using proper selectors
            const amountInput = newEntry.querySelector(`input[name="${prizeType}_prize_amount[]"]`);
            const ticketInput = newEntry.querySelector(`input[name="${prizeType}_ticket_number[]"]`);
            const placeInput = newEntry.querySelector(`input[name="${prizeType}_place[]"]`);
            
            if (amountInput) amountInput.value = values[0] || '';
            if (ticketInput) ticketInput.value = values[1] || '';
            if (placeInput && values[2]) placeInput.value = values[2];
            
            // Add remove button for all except first entry
            if (successCount > 0) {
                addRemoveButtonToEntry(newEntry, entriesContainer);
            }
            
            // Set up change tracking
            newEntry.querySelectorAll('input').forEach(input => {
                input.addEventListener('change', () => {
                    isDirty = true;
                });
            });
            
            entriesContainer.appendChild(newEntry);
            successCount++;
        });
        
        // Clear the textarea after processing
        textarea.value = '';
    }
    
    // If no successful entries, add back the template
    if (successCount === 0) {
        entriesContainer.appendChild(templateEntry);
    }
    
    // Update entry counter
    entryCounters[prizeType] = entriesContainer.children.length;
    isDirty = true;
    
    // Toggle back to normal view
    toggleBulkEntry(prizeType);
    
    // Show summary notification
    if (errorCount > 0 || (isSpecialPrize && invalidCount > 0)) {
        const totalErrors = errorCount + (isSpecialPrize ? invalidCount : 0);
        const errorMsg = isSpecialPrize ? 
            `Processed ${successCount} entries successfully. ${totalErrors} entries were skipped (${invalidCount} non-numeric, ${errorCount} empty).` :
            `Processed ${successCount} entries successfully. ${errorCount} lines were skipped due to incorrect format.`;
        showNotification(errorMsg, 'warning');
    } else {
        showNotification(`Successfully processed ${successCount} entries.`, 'success');
    }
}

/**
 * Validate form and submit if valid
 * @param {Event} e - Form submission event
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
            
            // Check if all required fields in this entry are filled
            if (values.filter(v => v !== '').length >= 2) { // At least amount and ticket number
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
        isDirty = false; // Reset dirty flag before submitting
        e.target.submit();
    }
}

/**
 * Set up change tracking on form elements
 */
function setupFormChangeTracking() {
    // Track changes on all inputs, selects, and textareas
    const formElements = document.querySelectorAll('#lotteryForm input, #lotteryForm select, #lotteryForm textarea');
    formElements.forEach(element => {
        element.addEventListener('change', () => {
            isDirty = true;
        });
        
        if (element.tagName === 'INPUT' && (element.type === 'text' || element.type === 'number') || element.tagName === 'TEXTAREA') {
            element.addEventListener('keyup', () => {
                isDirty = true;
            });
        }
    });
}

/**
 * Show a notification to the user
 * @param {string} message - The message to display
 * @param {string} type - The type of notification (success, error, warning, info)
 */
function showNotification(message, type = 'info') {
    // Check if notification container exists, create if not
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
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-message">${message}</span>
            <button class="notification-close">×</button>
        </div>
    `;
    
    // Add notification to container
    container.appendChild(notification);
    
    // Fade in
    setTimeout(() => {
        notification.style.opacity = '1';
    }, 10);
    
    // Close button functionality
    const closeButton = notification.querySelector('.notification-close');
    closeButton.addEventListener('click', () => {
        notification.style.opacity = '0';
        setTimeout(() => {
            container.removeChild(notification);
        }, 300);
    });
    
    // Auto close after 5 seconds
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
 * Generate a preview of the lottery results
 */
function previewResults() {
    // Create preview container if it doesn't exist
    let previewSection = document.getElementById('preview-section');
    if (!previewSection) {
        previewSection = document.createElement('div');
        previewSection.id = 'preview-section';
        previewSection.className = 'preview-section';
        previewSection.innerHTML = '<h4>Result Preview</h4>';
        
        // Find a good place to insert the preview
        const formContainer = document.querySelector('.lottery-form-container');
        formContainer.appendChild(previewSection);
    } else {
        // Clear existing preview
        while (previewSection.childNodes.length > 1) {
            previewSection.removeChild(previewSection.lastChild);
        }
    }
    
    // Collect basic information
    const lottery = document.querySelector('select[name="lottery"] option:checked');
    const drawNumber = document.querySelector('input[name="draw_number"]');
    const date = document.querySelector('input[name="date"]');
    const isPublished = document.querySelector('input[name="is_published"]');
    
    // Create basic info table
    const basicInfoTable = document.createElement('table');
    basicInfoTable.className = 'preview-table';
    basicInfoTable.innerHTML = `
        <tr>
            <th>Lottery</th>
            <td>${lottery ? lottery.text : 'Not selected'}</td>
        </tr>
        <tr>
            <th>Draw Number</th>
            <td>${drawNumber ? drawNumber.value : 'Not entered'}</td>
        </tr>
        <tr>
            <th>Date</th>
            <td>${date ? date.value : 'Not entered'}</td>
        </tr>
        <tr>
            <th>Published</th>
            <td>${isPublished && isPublished.checked ? 'Yes' : 'No'}</td>
        </tr>
    `;
    
    previewSection.appendChild(basicInfoTable);
    
    // Collect and display prize entries
    const prizeTypes = Object.keys(entryCounters);
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
    
    // Process each prize type
    for (const prizeType of prizeTypes) {
        const entriesContainer = document.getElementById(prizeType + '-entries');
        if (!entriesContainer) continue;
        
        const entries = entriesContainer.querySelectorAll('.prize-entry');
        if (entries.length === 0) continue;
        
        // Check if any entries have data
        let hasData = false;
        for (const entry of entries) {
            const inputs = entry.querySelectorAll('input[type="number"], input[type="text"]');
            const values = Array.from(inputs).map(input => input.value.trim());
            
            if (values.filter(v => v !== '').length > 0) {
                hasData = true;
                break;
            }
        }
        
        if (!hasData) continue;
        
        // Create heading for this prize type
        const heading = document.createElement('h5');
        heading.textContent = prizeNames[prizeType] || prizeType;
        heading.style.marginTop = '20px';
        heading.style.borderBottom = '1px solid #dee2e6';
        heading.style.paddingBottom = '8px';
        previewSection.appendChild(heading);
        
        // Create table for entries
        const entriesTable = document.createElement('table');
        entriesTable.className = 'preview-table';
        
        // Create table header
        let tableHead = '<thead><tr>';
        tableHead += '<th>Prize Amount</th>';
        tableHead += '<th>Ticket Number</th>';
        
        if (prizeType === '1st' || prizeType === '2nd' || prizeType === '3rd') {
            tableHead += '<th>Place</th>';
        }
        
        tableHead += '</tr></thead>';
        entriesTable.innerHTML = tableHead;
        
        // Create table body
        const tableBody = document.createElement('tbody');
        
        for (const entry of entries) {
            const inputs = entry.querySelectorAll('input');
            if (inputs.length < 2) continue;
            
            const amount = inputs[0].value.trim();
            const ticket = inputs[1].value.trim();
            
            if (!amount && !ticket) continue;
            
            const row = document.createElement('tr');
            
            // Add amount cell
            const amountCell = document.createElement('td');
            amountCell.textContent = amount ? `₹${amount}` : '-';
            row.appendChild(amountCell);
            
            // Add ticket cell
            const ticketCell = document.createElement('td');
            ticketCell.textContent = ticket || '-';
            row.appendChild(ticketCell);
            
            // Add place cell if applicable
            if (prizeType === '1st' || prizeType === '2nd' || prizeType === '3rd') {
                const place = inputs[2].value.trim();
                const placeCell = document.createElement('td');
                placeCell.textContent = place || '-';
                row.appendChild(placeCell);
            }
            
            tableBody.appendChild(row);
        }
        
        entriesTable.appendChild(tableBody);
        previewSection.appendChild(entriesTable);
    }
    
    // Scroll to preview
    previewSection.scrollIntoView({ behavior: 'smooth' });
}

// Initialize the lottery admin when the DOM is loaded
document.addEventListener('DOMContentLoaded', initLotteryAdmin);

 /** FIXED VERSION - Replace the loadExistingPrizeEntries function in your existing JS file
 */
function loadExistingPrizeEntries() {
    // Check if we have prize entries data in the page
    if (typeof window.prizeEntriesData === 'undefined' || !window.prizeEntriesData) {
        console.log('No prize entries data found - not in edit mode');
        return; // Not in edit mode or no data
    }
    
    console.log('Loading prize entries data:', window.prizeEntriesData);
    
    // For each prize type
    Object.keys(window.prizeEntriesData).forEach(prizeType => {
        const entries = window.prizeEntriesData[prizeType];
        console.log(`Processing ${entries.length} entries for ${prizeType}`);
        
        if (!entries || entries.length === 0) return;
        
        const entriesContainer = document.getElementById(prizeType + '-entries');
        if (!entriesContainer) {
            console.log(`Container for ${prizeType} not found`);
            return;
        }
        
        // Clear existing entries but keep the first one as template
        const firstEntry = entriesContainer.children[0];
        if (!firstEntry) {
            console.log(`No template entry found for ${prizeType}`);
            return;
        }
        
        // Save the template
        const templateEntry = firstEntry.cloneNode(true);
        
        // Clear the container
        entriesContainer.innerHTML = '';
        
        // Add each entry from the data
        entries.forEach((entry, index) => {
            console.log(`Adding entry ${index} for ${prizeType}:`, entry);
            const newEntry = templateEntry.cloneNode(true);
            
            // Set values - match the input names from your template
            const inputs = newEntry.querySelectorAll('input');
            if (inputs.length >= 2) {
                // Prize amount input
                const amountInput = newEntry.querySelector(`input[name="${prizeType}_prize_amount[]"]`);
                if (amountInput) {
                    amountInput.value = entry.prize_amount || '';
                }
                
                // Ticket number input
                const ticketInput = newEntry.querySelector(`input[name="${prizeType}_ticket_number[]"]`);
                if (ticketInput) {
                    ticketInput.value = entry.ticket_number || '';
                }
                
                // Place input (only for 1st, 2nd, 3rd)
                if (prizeType === '1st' || prizeType === '2nd' || prizeType === '3rd') {
                    const placeInput = newEntry.querySelector(`input[name="${prizeType}_place[]"]`);
                    if (placeInput) {
                        placeInput.value = entry.place || '';
                    }
                }
            }
            
            // Add remove button (except for the first entry)
            if (index > 0 && !newEntry.querySelector('.remove-entry-btn')) {
                const formRow = newEntry.querySelector('.form-row');
                if (formRow) {
                    const actionDiv = document.createElement('div');
                    actionDiv.className = 'form-group';
                    
                    const removeBtn = document.createElement('button');
                    removeBtn.type = 'button';
                    removeBtn.className = 'remove-entry-btn btn btn-danger btn-small';
                    removeBtn.innerHTML = '❌ Remove';
                    removeBtn.onclick = function() {
                        entriesContainer.removeChild(newEntry);
                        isDirty = true;
                    };
                    
                    actionDiv.appendChild(removeBtn);
                    formRow.appendChild(actionDiv);
                }
            }
            
            // Set up change tracking
            newEntry.querySelectorAll('input').forEach(input => {
                input.addEventListener('change', () => {
                    isDirty = true;
                });
            });
            
            entriesContainer.appendChild(newEntry);
        });
        
        // Update counter
        entryCounters[prizeType] = entriesContainer.children.length;
    });
    
    console.log('Prize entries loading completed');
}

/**
 * Add an entry with existing data
 * @param {string} prizeType - The type of prize
 * @param {object} entryData - The existing entry data
 */
function addEntryWithData(prizeType, entryData) {
    console.log(`Adding entry with data for ${prizeType}:`, entryData);
    
    const entriesContainer = document.getElementById(prizeType + '-entries');
    if (!entriesContainer) {
        console.log(`Container for ${prizeType} not found`);
        return;
    }
    
    // Find a template entry to clone
    let templateEntry;
    if (entriesContainer.children.length > 0) {
        templateEntry = entriesContainer.children[0];
    } else {
        // Try to find a template from another prize type
        const anyPrizeEntry = document.querySelector('.prize-entry');
        if (!anyPrizeEntry) {
            console.log('No template entry found');
            return;
        }
        templateEntry = anyPrizeEntry;
    }
    
    const newEntry = templateEntry.cloneNode(true);
    
    // Set values
    const inputs = newEntry.querySelectorAll('input');
    if (inputs.length >= 2) {
        inputs[0].value = entryData.prize_amount || '';
        inputs[1].value = entryData.ticket_number || '';
        
        if (inputs.length >= 3 && (prizeType === '1st' || prizeType === '2nd' || prizeType === '3rd')) {
            inputs[2].value = entryData.place || '';
        }
    }
    
    // Add remove button if needed
    if (!newEntry.querySelector('.remove-entry-btn')) {
        const actionDiv = document.createElement('div');
        actionDiv.className = 'entry-actions';
        
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'remove-entry-btn';
        removeBtn.innerHTML = '❌ Remove';
        removeBtn.onclick = function() {
            entriesContainer.removeChild(newEntry);
            isDirty = true;
        };
        
        actionDiv.appendChild(removeBtn);
        newEntry.appendChild(actionDiv);
    }
    
    // Set up change tracking
    newEntry.querySelectorAll('input').forEach(input => {
        input.addEventListener('change', () => {
            isDirty = true;
        });
    });
    
    entriesContainer.appendChild(newEntry);
    console.log(`Added entry to ${prizeType} container`);
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
        };
        
        actionDiv.appendChild(removeBtn);
        formRow.appendChild(actionDiv);
    }
}