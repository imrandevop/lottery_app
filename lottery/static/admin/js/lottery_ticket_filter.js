(function($) {
    $(document).ready(function() {
        // Function to update prize categories based on draw's lottery type
        function updatePrizeCategories() {
            var drawId = $('#id_draw').val();
            if (drawId) {
                // Get the lottery type for this draw via AJAX
                $.getJSON('/admin/api/draw-lottery-type/', {draw_id: drawId}, function(data) {
                    if (data.lottery_type_id) {
                        // Update prize category dropdown
                        var select = $('#id_prize_category');
                        var currentValue = select.val();
                        
                        // Fetch appropriate prize categories
                        $.getJSON('/admin/api/prize-categories/', {lottery_type_id: data.lottery_type_id}, function(categories) {
                            // Clear existing options
                            select.empty();
                            // Add an empty option
                            select.append($('<option value="">---------</option>'));
                            // Add new options
                            $.each(categories, function(index, item) {
                                select.append(
                                    $('<option></option>').val(item.id).text(item.name)
                                );
                            });
                            // Try to restore the previous value if it still exists
                            select.val(currentValue);
                        });
                    }
                });
            }
        }
        
        // Bind to draw change event
        $('#id_draw').change(updatePrizeCategories);
        
        // Also run on page load
        updatePrizeCategories();
    });
})(django.jQuery);