// Update the AJAX call in your JavaScript file (winningticket_filter.js)
function updatePrizeCategories(lotteryTypeId) {
    if (!lotteryTypeId) return;
    
    // Clear current options
    prizeCategorySelect.empty();
    
    // Add loading option
    prizeCategorySelect.append('<option value="">Loading...</option>');
    
    // Debug: Log the URL we're calling
    var apiUrl = '/api/prize-categories/' + lotteryTypeId + '/';
    console.log('Calling API:', apiUrl);

    function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');
    
    // Fetch prize categories with error handling
    $.ajax({
        url: apiUrl,
        type: 'GET',
        dataType: 'json',
        headers: {
        'X-CSRFToken': csrftoken
        },
        success: function(data) {
            console.log('API response:', data);
            prizeCategorySelect.empty();
            
            // Add empty option
            prizeCategorySelect.append('<option value="">---------</option>');
            
            // Add options for each prize category
            $.each(data, function(index, category) {
                prizeCategorySelect.append(
                    $('<option></option>').val(category.id).text(category.display_name || category.name)
                );
            });
        },
        error: function(xhr, status, error) {
            console.error('API error:', status, error);
            console.log('Response text:', xhr.responseText.substring(0, 500)); // Show first 500 chars
            
            prizeCategorySelect.empty();
            prizeCategorySelect.append('<option value="">Error loading data</option>');
        }
    });
}