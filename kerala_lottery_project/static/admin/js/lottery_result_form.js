// Save this to static/admin/js/lottery_result_form.js
(function($) {
    $(document).ready(function() {
        // Helper function to create input fields for 4-digit numbers
        function createNumberGrid(container, numbers) {
            const grid = $('<div class="number-grid"></div>');
            
            if (numbers && numbers.length > 0) {
                numbers.forEach(function(number) {
                    const cell = $('<div class="number-cell"></div>');
                    const input = $('<input type="text" maxlength="4" class="number-input" value="' + number + '">');
                    
                    cell.append(input);
                    grid.append(cell);
                });
            } else {
                // Create empty grid with 40 cells (10 rows x 4 columns)
                for (let i = 0; i < 40; i++) {
                    const cell = $('<div class="number-cell"></div>');
                    const input = $('<input type="text" maxlength="4" class="number-input">');
                    
                    cell.append(input);
                    grid.append(cell);
                }
            }
            
            container.append(grid);
        }
        
        // Initialize any existing grids
        $('.number-grid-container').each(function() {
            const container = $(this);
            const numbersText = container.data('numbers') || '';
            const numbers = numbersText.split(/\s+/).filter(n => n.trim());
            
            createNumberGrid(container, numbers);
        });
        
        // When form submits, collect grid values into hidden fields
        $('#lottery-result-form').on('submit', function() {
            $('.number-grid-container').each(function() {
                const container = $(this);
                const hiddenField = container.find('input[type="hidden"]');
                const numbers = [];
                
                container.find('.number-input').each(function() {
                    const value = $(this).val().trim();
                    if (value) {
                        numbers.push(value);
                    }
                });
                
                hiddenField.val(numbers.join(' '));
            });
        });
    });
})(django.jQuery);