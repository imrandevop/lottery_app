(function($) {
    $(document).ready(function() {
        // Get the lottery type select and prize category select elements
        var lotteryTypeSelect = $('#id_lottery_type');
        var drawSelect = $('#id_draw');
        var prizeCategorySelect = $('#id_prize_category');
        
        // Function to update prize categories based on lottery type
        function updatePrizeCategories(lotteryTypeId) {
            if (!lotteryTypeId) return;
            
            // Clear current options
            prizeCategorySelect.empty();
            
            // Add loading option
            prizeCategorySelect.append('<option value="">Loading...</option>');
            
            // Fetch prize categories for the selected lottery type
            $.getJSON('/admin/lottery/prizecategory/by-lottery-type/' + lotteryTypeId + '/', function(data) {
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
        
        // Function to update prize categories based on draw
        function updatePrizeCategoriesFromDraw(drawId) {
            if (!drawId) return;
            
            // Clear current options
            prizeCategorySelect.empty();
            
            // Add loading option
            prizeCategorySelect.append('<option value="">Loading...</option>');
            
            // Fetch draw details to get lottery type
            $.getJSON('/admin/api/lottery/lotterydraw/' + drawId + '/', function(data) {
                if (data && data.lottery_type) {
                    updatePrizeCategories(data.lottery_type);
                }
            });
        }
        
        // Update prize categories when lottery type changes
        lotteryTypeSelect.on('change', function() {
            updatePrizeCategories($(this).val());
        });
        
        // Update prize categories when draw changes
        drawSelect.on('change', function() {
            updatePrizeCategoriesFromDraw($(this).val());
        });
        
        // Initial update if lottery type is already selected
        if (lotteryTypeSelect.val()) {
            updatePrizeCategories(lotteryTypeSelect.val());
        }
        
        // Initial update if draw is already selected
        if (drawSelect.val()) {
            updatePrizeCategoriesFromDraw(drawSelect.val());
        }
    });
})(django.jQuery);