/**
 * Quote Carousel - Netflix Style
 * Animated carousel with navigation buttons and indicators
 */

document.addEventListener('DOMContentLoaded', function() {
    initQuoteCarousel();
});

function initQuoteCarousel() {
    const carousel = document.getElementById('quoteCarousel');
    const prevBtn = document.getElementById('quote-prev-btn');
    const nextBtn = document.getElementById('quote-next-btn');
    const indicators = document.querySelectorAll('.carousel-indicators .indicator');
    const cards = document.querySelectorAll('.quote-card-carousel');

    if (!carousel || cards.length === 0) return;

    let currentIndex = 0;

    function updateCarousel() {
        // Move carousel
        carousel.style.transform = `translateX(-${currentIndex * 100}%)`;

        // Update indicators
        indicators.forEach((ind, idx) => {
            ind.classList.toggle('active', idx === currentIndex);
        });
    }

    // Next button
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            currentIndex = (currentIndex + 1) % cards.length;
            updateCarousel();
        });
    }

    // Previous button
    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            currentIndex = (currentIndex - 1 + cards.length) % cards.length;
            updateCarousel();
        });
    }

    // Indicators
    indicators.forEach((ind, idx) => {
        ind.addEventListener('click', () => {
            currentIndex = idx;
            updateCarousel();
        });
    });

    // Initialize
    updateCarousel();
}
