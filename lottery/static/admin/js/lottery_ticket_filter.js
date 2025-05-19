(function($) {
    $(document).ready(function() {
        // Function to update prize categories based on selected draw
        function updatePrizeCategories() {
            var drawId = $('#id_draw').val();
            if (!drawId) return;
            
            // Get the prize category select element
            var prizeCategorySelect = $('#id_prize_category');
            if (!prizeCategorySelect.length) return;
            
            // Save current value
            var currentValue = prizeCategorySelect.val();
            
            // Fetch prize categories for this draw via AJAX
            $.getJSON('/admin/lottery/winningticket/get-prize-categories-for-draw/', {draw_id: drawId}, function(data) {
                // Clear existing options
                prizeCategorySelect.empty();
                // Add an empty option
                prizeCategorySelect.append($('<option value="">---------</option>'));
                // Add new options
                $.each(data, function(index, item) {
                    prizeCategorySelect.append(
                        $('<option></option>').val(item.id).text(item.name)
                    );
                });
                // Try to restore the previous value if it still exists
                prizeCategorySelect.val(currentValue);
            });
        }
        
        // Bind to draw change event
        $('#id_draw').change(updatePrizeCategories);
        
        // Also run on page load
        if ($('#id_draw').length) {
            updatePrizeCategories();
        }
    });
})(django.jQuery);