document.addEventListener('DOMContentLoaded', function () {
    const lotterySelect = document.querySelector('#id_lottery');
    const priceSelect = document.querySelector('#id_price');

    function filterPrices() {
        const selectedLotteryId = lotterySelect.value;

        if (!selectedLotteryId) return;

        fetch(`/admin/get_prices/${selectedLotteryId}/`)
            .then(response => response.json())
            .then(data => {
                priceSelect.innerHTML = ''; // Clear old options
                data.forEach(price => {
                    const option = document.createElement('option');
                    option.value = price.id;
                    option.text = price.label;
                    priceSelect.appendChild(option);
                });
            });
    }

    lotterySelect.addEventListener('change', filterPrices);

    // Load prices initially if lottery is pre-selected
    if (lotterySelect.value) {
        filterPrices();
    }
});
