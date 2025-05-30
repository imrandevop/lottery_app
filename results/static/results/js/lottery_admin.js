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
    
    // Set today's date as default
    const dateInput = document.querySelector('input[name="date"]');
    if (dateInput && !dateInput.value) {
        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const dd = String(today.getDate()).padStart(2, '0');
        dateInput.value = `${yyyy}-${mm}-${dd}`;
    }

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
 * Add a new entry for a specific prize type
 * @param {string} prizeType - The type of prize (e.g., '1st', '2nd', etc.)
 */
function addEntry(prizeType) {
    const entriesContainer = document.getElementById(prizeType + '-entries');
    const firstEntry = entriesContainer.children[0];
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
    
    // Add remove button if not the first entry
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
    
    entryCounters[prizeType]++;
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
        // Focus on the textarea when switching to bulk mode
        setTimeout(() => {
            const textarea = document.getElementById(prizeType + '-bulk-textarea');
            if (textarea) {
                textarea.focus();
            }
        }, 100);
    }
}

/**
 * Process bulk entries for a specific prize type
 * @param {string} prizeType - The type of prize
 */
function processBulkEntries(prizeType) {
    const textarea = document.getElementById(prizeType + '-bulk-textarea');
    const entriesContainer = document.getElementById(prizeType + '-entries');
    
    // Clear existing entries except the first one
    while (entriesContainer.children.length > 1) {
        entriesContainer.removeChild(entriesContainer.lastChild);
    }
    
    // Reset the first entry
    const firstEntry = entriesContainer.children[0];
    const firstEntryInputs = firstEntry.querySelectorAll('input');
    firstEntryInputs.forEach(input => {
        input.value = '';
    });
    
    // Process each line from the textarea
    const lines = textarea.value.trim().split('\n');
    if (lines.length === 0 || (lines.length === 1 && lines[0] === '')) {
        showNotification('No entries found in the bulk entry textarea.', 'warning');
        return;
    }
    
    let errorCount = 0;
    
    lines.forEach((line, index) => {
        const values = line.split(',');
        
        if (prizeType === '1st' || prizeType === '2nd' || prizeType === '3rd') {
            // Format: amount,ticket_number,place
            if (values.length < 3) {
                errorCount++;
                if (errorCount <= 3) { // Limit error messages
                    showNotification(`Line ${index + 1} does not have the correct format. Expected: amount,ticket_number,place`, 'error');
                }
                return;
            }
            
            if (index === 0) {
                // Update the first entry
                firstEntryInputs[0].value = values[0].trim(); // amount
                firstEntryInputs[1].value = values[1].trim(); // ticket
                firstEntryInputs[2].value = values[2].trim(); // place
            } else {
                // Add new entry
                const entry = firstEntry.cloneNode(true);
                const entryInputs = entry.querySelectorAll('input');
                entryInputs[0].value = values[0].trim(); // amount
                entryInputs[1].value = values[1].trim(); // ticket
                entryInputs[2].value = values[2].trim(); // place
                
                // Add remove button
                const actionDiv = document.createElement('div');
                actionDiv.className = 'entry-actions';
                
                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.className = 'remove-entry-btn';
                removeBtn.innerHTML = '❌ Remove';
                removeBtn.onclick = function() {
                    entriesContainer.removeChild(entry);
                    isDirty = true;
                };
                
                actionDiv.appendChild(removeBtn);
                entry.appendChild(actionDiv);
                
                entriesContainer.appendChild(entry);
            }
        } else {
            // Format: amount,ticket_number
            if (values.length < 2) {
                errorCount++;
                if (errorCount <= 3) { // Limit error messages
                    showNotification(`Line ${index + 1} does not have the correct format. Expected: amount,ticket_number`, 'error');
                }
                return;
            }
            
            if (index === 0) {
                // Update the first entry
                firstEntryInputs[0].value = values[0].trim(); // amount
                firstEntryInputs[1].value = values[1].trim(); // ticket
            } else {
                // Add new entry
                const entry = firstEntry.cloneNode(true);
                const entryInputs = entry.querySelectorAll('input');
                entryInputs[0].value = values[0].trim(); // amount
                entryInputs[1].value = values[1].trim(); // ticket
                
                // Add remove button
                const actionDiv = document.createElement('div');
                actionDiv.className = 'entry-actions';
                
                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.className = 'remove-entry-btn';
                removeBtn.innerHTML = '❌ Remove';
                removeBtn.onclick = function() {
                    entriesContainer.removeChild(entry);
                    isDirty = true;
                };
                
                actionDiv.appendChild(removeBtn);
                entry.appendChild(actionDiv);
                
                entriesContainer.appendChild(entry);
            }
        }
    });
    
    // Show summary notification
    if (errorCount > 3) {
        showNotification(`${errorCount} total lines with incorrect format were skipped.`, 'warning');
    }
    
    // Update entry counter
    entryCounters[prizeType] = entriesContainer.children.length;
    isDirty = true;
    
    // Toggle back to normal view
    toggleBulkEntry(prizeType);
    
    showNotification(`Successfully processed ${lines.length - errorCount} entries.`, 'success');
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