document.addEventListener('DOMContentLoaded', function () {
    const urlInput = document.getElementById('url-input');
    const scrapeBtn = document.getElementById('scrape-btn');
    const loadingDiv = document.getElementById('loading');
    const resultsDiv = document.getElementById('results');
    const errorDiv = document.getElementById('error-message');

    scrapeBtn.addEventListener('click', async function () {
        const url = urlInput.value.trim();

        if (!url) {
            showError('Please enter an Amazon TV URL');
            return;
        }

        // Show loading state
        loadingDiv.classList.remove('d-none');
        resultsDiv.classList.add('d-none');
        errorDiv.classList.add('d-none');
        scrapeBtn.disabled = true;

        try {
            const response = await fetch('/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to scrape TV details');
            }

            displayResults(data);
        } catch (error) {
            showError(error.message);
        } finally {
            loadingDiv.classList.add('d-none');
            scrapeBtn.disabled = false;
        }
    });

    function showError(message) {
        errorDiv.textContent = message;
        errorDiv.classList.remove('d-none');
        resultsDiv.classList.add('d-none');
    }

    function displayResults(data) {
        // Show results container
        resultsDiv.classList.remove('d-none');

        // Display product images
        const carouselInner = document.querySelector('#product-images .carousel-inner');
        carouselInner.innerHTML = '';
        data.product_images.forEach((image, index) => {
            const div = document.createElement('div');
            div.className = `carousel-item ${index === 0 ? 'active' : ''}`;
            div.innerHTML = `<img src="${image}" class="d-block w-100" alt="Product Image ${index + 1}">`;
            carouselInner.appendChild(div);
        });

        // Display manufacturer images
        const manufacturerCarousel = document.querySelector('#manufacturer-images .carousel-inner');
        manufacturerCarousel.innerHTML = '';
        if (data.manufacturer_images && data.manufacturer_images.length > 0) {
            data.manufacturer_images.forEach((image, index) => {
                const div = document.createElement('div');
                div.className = `carousel-item ${index === 0 ? 'active' : ''}`;
                div.innerHTML = `<img src="${image}" class="d-block w-100" alt="Manufacturer Image ${index + 1}">`;
                manufacturerCarousel.appendChild(div);
            });
            document.querySelector('#manufacturer-images').closest('.card').classList.remove('d-none');
        } else {
            document.querySelector('#manufacturer-images').closest('.card').classList.add('d-none');
        }

        // Display product details
        document.getElementById('product-name').textContent = data.product_name;

        // Display rating and review count
        const ratingSection = document.querySelector('.rating-section');
        if (data.rating) {
            const stars = '⭐'.repeat(Math.round(parseFloat(data.rating)));
            ratingSection.innerHTML = `
                ${stars} ${data.rating} 
                <span class="text-muted">(${data.number_of_ratings} ratings)</span>
            `;
        }

        // Display price information
        const currentPrice = document.querySelector('.current-price');
        const originalPrice = document.querySelector('.original-price');
        const discount = document.querySelector('.discount');

        currentPrice.textContent = `₹${data.selling_price.toLocaleString()}`;
        originalPrice.textContent = `₹${data.mrp.toLocaleString()}`;
        discount.textContent = data.discount_percentage;

        // Display features
        const aboutList = document.getElementById('about-items');
        aboutList.innerHTML = data.about_this_item.map(item => `<li>${item}</li>`).join('');

        // Display bank offers
        const bankOffersCarousel = document.querySelector('#bank-offers-carousel .carousel-inner');
        const offerCounter = document.getElementById('offer-counter');

        if (data.bank_offers && data.bank_offers.length > 0) {
            // Filter out invalid offers and offers without meaningful content
            const validOffers = data.bank_offers
                .filter(offer => offer && typeof offer === 'object' && offer.offer_text)
                .filter(offer => {
                    // Filter out generic messages and disclaimers
                    const text = offer.offer_text.toLowerCase();
                    return !text.includes('payment security system') &&
                        !text.includes('reserves the right') &&
                        !text.includes('will not be liable');
                });

            if (validOffers.length > 0) {
                // Update the counter
                offerCounter.textContent = `Offer ${1} of ${validOffers.length}`;

                // Create carousel indicators
                const indicators = document.querySelector('#bank-offers-carousel .carousel-indicators');
                indicators.innerHTML = validOffers.map((_, index) => `
                    <button type="button" 
                            data-bs-target="#bank-offers-carousel" 
                            data-bs-slide-to="${index}"
                            ${index === 0 ? 'class="active" aria-current="true"' : ''}
                            aria-label="Offer ${index + 1}">
                    </button>
                `).join('');

                // Create carousel items
                bankOffersCarousel.innerHTML = validOffers.map((offer, index) => {
                    let offerHtml = `<div class="carousel-item${index === 0 ? ' active' : ''}" data-bs-interval="3000">`;
                    offerHtml += '<div class="bank-offer-card">';

                    // Add bank name if available
                    if (offer.bank_name) {
                        offerHtml += `<div class="bank-name">${offer.bank_name} Bank Offer</div>`;
                    }

                    // Add offer text
                    offerHtml += `<div class="offer-text">${offer.offer_text}</div>`;

                    // Add discount amount if available
                    if (offer.discount_amount) {
                        offerHtml += `<div class="discount-amount">Discount Amount: ₹${offer.discount_amount.toLocaleString()}</div>`;
                    }

                    // Add minimum purchase if available
                    if (offer.min_purchase) {
                        offerHtml += `<div class="min-purchase">Minimum Purchase: ₹${offer.min_purchase.toLocaleString()}</div>`;
                    }

                    // Add EMI information if available
                    if (offer.emi_available) {
                        offerHtml += '<div class="emi-info">EMI Available';
                        if (offer.emi_duration) {
                            offerHtml += ` for ${offer.emi_duration} months`;
                        }
                        offerHtml += '</div>';
                    }

                    offerHtml += '</div></div>';
                    return offerHtml;
                }).join('');

                // Show the carousel
                bankOffersCarousel.closest('.card').classList.remove('d-none');

                // Initialize the carousel with options
                const carousel = new bootstrap.Carousel(document.getElementById('bank-offers-carousel'), {
                    interval: 3000,
                    ride: 'carousel',
                    wrap: true
                });

                // Add carousel event listener to update counter
                document.getElementById('bank-offers-carousel').addEventListener('slid.bs.carousel', function (event) {
                    const activeIndex = event.to + 1;
                    offerCounter.textContent = `Offer ${activeIndex} of ${validOffers.length}`;
                });
            } else {
                bankOffersCarousel.closest('.card').classList.add('d-none');
            }
        } else {
            bankOffersCarousel.closest('.card').classList.add('d-none');
        }

        // Display specifications
        const specsTable = document.getElementById('specs-table').querySelector('tbody');
        specsTable.innerHTML = '';
        for (const [key, value] of Object.entries(data.product_information)) {
            specsTable.innerHTML += `
                <tr>
                    <th scope="row">${key}</th>
                    <td>${value}</td>
                </tr>
            `;
        }

        // Display AI summary
        document.getElementById('ai-summary').textContent = data.ai_review_summary;
    }
}); 