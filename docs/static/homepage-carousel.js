/**
 * Quote Carousel - Netflix Style
 * Animated carousel with navigation buttons, indicators, and touch swipe support
 */

document.addEventListener('DOMContentLoaded', function() {
    initQuoteCarousel();
});

function initQuoteCarousel() {
    const wrapper = document.querySelector('.quote-carousel-wrapper');
    const carousel = document.getElementById('quoteCarousel');
    const prevBtn = document.getElementById('quote-prev-btn');
    const nextBtn = document.getElementById('quote-next-btn');
    const indicators = document.querySelectorAll('.carousel-indicators .indicator');
    const cards = document.querySelectorAll('.quote-card-carousel');

    if (!carousel || cards.length === 0) return;

    let currentIndex = 0;
    let touchStartX = 0;
    let touchEndX = 0;
    let isDragging = false;

    // Calculate gap from CSS (15px from .quote-carousel gap: 15px)
    const GAP = 15;

    function calculateOffset() {
        // Each card is 100% width + gap, so offset accounts for both
        // Formula: -(currentIndex * (100% + gap))
        // We convert gap to percentage based on wrapper width
        const gapPercentage = (GAP / wrapper.offsetWidth) * 100;
        return -(currentIndex * (100 + gapPercentage));
    }

    function updateCarousel(smooth = true) {
        // Move carousel with offset that includes gap
        if (smooth) {
            carousel.style.transition = 'transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
        } else {
            carousel.style.transition = 'none';
        }

        carousel.style.transform = `translateX(${calculateOffset()}%)`;

        // Update indicators
        indicators.forEach((ind, idx) => {
            ind.classList.toggle('active', idx === currentIndex);
        });
    }

    function goToSlide(index) {
        currentIndex = (index + cards.length) % cards.length;
        updateCarousel(true);
    }

    // Navigation buttons
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            goToSlide(currentIndex + 1);
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            goToSlide(currentIndex - 1);
        });
    }

    // Indicators
    indicators.forEach((ind, idx) => {
        ind.addEventListener('click', () => {
            goToSlide(idx);
        });
    });

    // Touch/Swipe support
    wrapper.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
        isDragging = true;
        carousel.style.transition = 'none';
    });

    wrapper.addEventListener('touchmove', (e) => {
        if (!isDragging) return;
        touchEndX = e.changedTouches[0].screenX;
    });

    wrapper.addEventListener('touchend', (e) => {
        if (!isDragging) return;
        isDragging = false;

        const diff = touchStartX - touchEndX;
        const threshold = 50; // Minimum pixels to trigger slide change

        if (Math.abs(diff) > threshold) {
            if (diff > 0) {
                // Swiped left, go to next
                goToSlide(currentIndex + 1);
            } else {
                // Swiped right, go to previous
                goToSlide(currentIndex - 1);
            }
        } else {
            // Small swipe or no swipe, stay on current slide
            updateCarousel(true);
        }
    });

    // Prevent scrolling while touching carousel
    wrapper.addEventListener('touchmove', function(e) {
        if (isDragging) {
            e.preventDefault();
        }
    }, { passive: false });

    // Initialize
    updateCarousel(false);
}
