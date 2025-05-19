(function($) {
    $(document).ready(function() {
        var drawSelect = $('#id_draw');
        var prizeCategorySelect = $('#id_prize_category');
        
        function updatePrizeCategories() {
            var drawId = drawSelect.val();
            if (!drawId) {
                return;  // No draw selected
            }
            
            // Show loading indicator
            prizeCategorySelect.html('<option value="">Loading...</option>');
            
            // Make AJAX request to get filtered prize categories
            $.ajax({
                url: '/admin/filter-prizes-by-draw/',
                data: { 'draw_id': drawId },
                dataType: 'json',
                success: function(data) {
                    // Clear existing options
                    prizeCategorySelect.empty();
                    
                    // Add empty option
                    prizeCategorySelect.append($('<option value="">---------</option>'));
                    
                    // Add each prize category
                    $.each(data.prizes, function(i, prize) {
                        prizeCategorySelect.append(
                            $('<option></option>')
                                .attr('value', prize.id)
                                .text(prize.name)
                        );
                    });
                },
                error: function() {
                    alert('Failed to load prize categories. Please refresh the page and try again.');
                }
            });
        }
        
        // Update categories when draw changes
        drawSelect.on('change', updatePrizeCategories);
        
        // Initial update if draw is already selected
        if (drawSelect.val()) {
            updatePrizeCategories();
        }
    });
})(django.jQuery); 