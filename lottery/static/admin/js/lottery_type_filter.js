(function($) {
    $(document).ready(function() {
        // Function to update prize categories based on lottery type
        function updatePrizeCategories() {
            var lotteryTypeId = $('#id_lottery_type').val();
            if (!lotteryTypeId) return;
            
            // For each prize category dropdown in inline formsets
            $('select[id$=prize_category]').each(function() {
                var select = $(this);
                // Save current value
                var currentValue = select.val();
                
                // Fetch appropriate prize categories via AJAX
                $.getJSON('/admin/lottery/lotterydraw/get-prize-categories/', {lottery_type_id: lotteryTypeId}, function(data) {
                    // Clear existing options
                    select.empty();
                    // Add an empty option
                    select.append($('<option value="">---------</option>'));
                    // Add new options
                    $.each(data, function(index, item) {
                        select.append(
                            $('<option></option>').val(item.id).text(item.name)
                        );
                    });
                    // Try to restore the previous value if it still exists
                    select.val(currentValue);
                });
            });
        }
        
        // Bind to lottery type change event
        $('#id_lottery_type').change(updatePrizeCategories);
        
        // Also run on page load
        if ($('#id_lottery_type').length) {
            updatePrizeCategories();
        }
        
        // When new inline forms are added, update their prize category dropdowns
        $(document).on('formset:added', function() {
            updatePrizeCategories();
        });
    });
})(django.jQuery);