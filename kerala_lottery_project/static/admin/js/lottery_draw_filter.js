(function($) {
    $(document).ready(function() {
        // Get the lottery type select and winning ticket formset
        var lotteryTypeSelect = $('#id_lottery_type');
        var winningTicketFormset = $('.winning-ticket-formset');
        
        // Function to update prize categories in all inline forms
        function updateAllPrizeCategories(lotteryTypeId) {
            if (!lotteryTypeId) return;
            
            // For each inline form
            $('.dynamic-winningticket_set').each(function() {
                var prizeCategorySelect = $(this).find('select[id$="-prize_category"]');
                
                // Clear current options
                prizeCategorySelect.empty();
                
                // Add loading option
                prizeCategorySelect.append('<option value="">Loading...</option>');
            });
            
            // Fetch prize categories for the selected lottery type
            $.getJSON('/admin/lottery/prizecategory/by-lottery-type/' + lotteryTypeId + '/', function(data) {
                // For each inline form
                $('.dynamic-winningticket_set').each(function() {
                    var prizeCategorySelect = $(this).find('select[id$="-prize_category"]');
                    
                    // Clear current options
                    prizeCategorySelect.empty();
                    
                    // Add empty option
                    prizeCategorySelect.append('<option value="">---------</option>');
                    
                    // Add options for each prize category
                    $.each(data, function(index, category) {
                        prizeCategorySelect.append(
                            $('<option></option>').val(category.id).text(category.display_name || category.name)
                        );
                    });
                });
            });
        }
        
        // Update prize categories when lottery type changes
        lotteryTypeSelect.on('change', function() {
            updateAllPrizeCategories($(this).val());
        });
        
        // Initial update if lottery type is already selected
        if (lotteryTypeSelect.val()) {
            updateAllPrizeCategories(lotteryTypeSelect.val());
        }
        
        // When a new inline form is added, update its prize categories
        $(document).on('formset:added', function(event, $row, formsetName) {
            if (formsetName === 'winningticket_set' && lotteryTypeSelect.val()) {
                var prizeCategorySelect = $row.find('select[id$="-prize_category"]');
                
                // Clear current options
                prizeCategorySelect.empty();
                
                // Add loading option
                prizeCategorySelect.append('<option value="">Loading...</option>');
                
                // Fetch prize categories for the selected lottery type
                $.getJSON('/admin/lottery/prizecategory/by-lottery-type/' + lotteryTypeSelect.val() + '/', function(data) {
                    // Clear current options
                    prizeCategorySelect.empty();
                    
                    // Add empty option
                    prizeCategorySelect.append('<option value="">---------</option>');
                    
                    // Add options for each prize category
                    $.each(data, function(index, category) {
                        prizeCategorySelect.append(
                            $('<option></option>').val(category.id).text(category.display_name || category.name)
                        );
                    });
                });
            }
        });
    });
})(django.jQuery);