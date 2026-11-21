
/**
 * LiveAuction — polished frontend interactions.
 * Keeps bidding logic server-authoritative while adding lightweight UI feedback.
 */
document.addEventListener('DOMContentLoaded', function () {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Mobile navigation.
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', function () {
            navLinks.classList.toggle('open');
            const spans = navToggle.querySelectorAll('span');
            const open = navLinks.classList.contains('open');
            if (open) {
                spans[0].style.transform = 'rotate(45deg) translate(4px, 5px)';
                spans[1].style.opacity = '0';
                spans[2].style.transform = 'rotate(-45deg) translate(4px, -5px)';
            } else {
                spans[0].style.transform = 'none';
                spans[1].style.opacity = '1';
                spans[2].style.transform = 'none';
            }
        });
    }

    // Sticky header state.
    const navbar = document.querySelector('.navbar');
    const updateNav = function () {
        if (navbar) navbar.classList.toggle('scrolled', window.scrollY > 8);
    };
    updateNav();
    window.addEventListener('scroll', updateNav, { passive: true });

    // Auto-dismiss flash alerts.
    document.querySelectorAll('.alert').forEach(function (alert) {
        setTimeout(function () {
            alert.style.transition = 'opacity .4s ease, transform .4s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(function () { alert.remove(); }, 400);
        }, 4500);
    });

    // Scroll reveal for page sections and content cards.
    const revealTargets = document.querySelectorAll('.section, .stats-section, .page-header, .auction-card, .stat-card, .detail-left, .detail-right, .form-card, .dashboard-section');
    revealTargets.forEach(function (element, index) {
        element.classList.add('reveal');
        if (index % 4 === 1) element.classList.add('reveal-delay-1');
        if (index % 4 === 2) element.classList.add('reveal-delay-2');
        if (index % 4 === 3) element.classList.add('reveal-delay-3');
    });
    if (!prefersReducedMotion && 'IntersectionObserver' in window) {
        const revealObserver = new IntersectionObserver(function (entries, observer) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -30px' });
        revealTargets.forEach(function (element) { revealObserver.observe(element); });
    } else {
        revealTargets.forEach(function (element) { element.classList.add('is-visible'); });
    }

    // Subtle desktop card tilt; disabled on touch/reduced-motion devices.
    if (!prefersReducedMotion && window.matchMedia('(pointer: fine)').matches) {
        document.querySelectorAll('.auction-card').forEach(function (card) {
            card.addEventListener('pointermove', function (event) {
                const rect = card.getBoundingClientRect();
                const x = (event.clientX - rect.left) / rect.width - 0.5;
                const y = (event.clientY - rect.top) / rect.height - 0.5;
                card.style.transform = 'perspective(900px) rotateX(' + (-y * 2.3) + 'deg) rotateY(' + (x * 2.8) + 'deg) translateY(-8px)';
            });
            card.addEventListener('pointerleave', function () {
                card.style.transform = '';
            });
        });
    }

    // Button ripple feedback.
    document.querySelectorAll('.btn').forEach(function (button) {
        button.addEventListener('click', function (event) {
            if (prefersReducedMotion) return;
            const rect = button.getBoundingClientRect();
            button.style.setProperty('--ripple-x', (event.clientX - rect.left) + 'px');
            button.style.setProperty('--ripple-y', (event.clientY - rect.top) + 'px');
            button.classList.remove('ripple');
            void button.offsetWidth;
            button.classList.add('ripple');
        });
    });

    // Hero pointer depth effect.
    const hero = document.querySelector('.hero');
    if (hero && !prefersReducedMotion && window.matchMedia('(pointer: fine)').matches) {
        hero.addEventListener('pointermove', function (event) {
            const rect = hero.getBoundingClientRect();
            const x = (event.clientX - rect.left) / rect.width - 0.5;
            const y = (event.clientY - rect.top) / rect.height - 0.5;
            hero.style.backgroundPosition = (50 + x * 2) + '% ' + (50 + y * 2) + '%';
        });
        hero.addEventListener('pointerleave', function () {
            hero.style.backgroundPosition = '';
        });
    }

    // Dynamic countdown timers.
    const timerElements = document.querySelectorAll('[data-countdown]');
    function updateAllTimers() {
        const now = Date.now();
        timerElements.forEach(function (el) {
            const targetTime = new Date(el.getAttribute('data-countdown')).getTime();
            const diff = targetTime - now;
            if (!Number.isFinite(targetTime)) return;
            if (diff <= 0) {
                const statusBadge = el.closest('.detail-container, .auction-card')?.querySelector('.badge-live');
                if (statusBadge) {
                    statusBadge.className = 'badge badge-closed';
                    statusBadge.textContent = 'CLOSED';
                }
                el.innerHTML = '<span class="countdown-ended">Auction Ended</span>';
                return;
            }
            const days = Math.floor(diff / 86400000);
            const hours = Math.floor((diff % 86400000) / 3600000);
            const minutes = Math.floor((diff % 3600000) / 60000);
            const seconds = Math.floor((diff % 60000) / 1000);
            const daysEl = el.querySelector('.cd-days');
            const hoursEl = el.querySelector('.cd-hours');
            const minsEl = el.querySelector('.cd-mins');
            const secsEl = el.querySelector('.cd-secs');
            if (daysEl && hoursEl && minsEl && secsEl) {
                daysEl.textContent = String(days).padStart(2, '0');
                hoursEl.textContent = String(hours).padStart(2, '0');
                minsEl.textContent = String(minutes).padStart(2, '0');
                secsEl.textContent = String(seconds).padStart(2, '0');
            } else {
                el.textContent = (days > 0 ? days + 'd ' : '') + String(hours).padStart(2, '0') + 'h ' + String(minutes).padStart(2, '0') + 'm ' + String(seconds).padStart(2, '0') + 's';
            }
        });
    }
    if (timerElements.length) {
        updateAllTimers();
        setInterval(updateAllTimers, 1000);
    }

    // Client-side bid validation; final validation remains on the server.
    const bidForm = document.getElementById('bid-form');
    if (bidForm) {
        bidForm.addEventListener('submit', function (event) {
            const amountInput = bidForm.querySelector('input[name="amount"]');
            const nameInput = bidForm.querySelector('input[name="bidder_name"]');
            if (nameInput && !nameInput.value.trim()) {
                event.preventDefault(); nameInput.focus(); alert('Please enter your name.'); return;
            }
            if (!amountInput || !amountInput.value) {
                event.preventDefault(); amountInput?.focus(); alert('Please enter a bid amount.'); return;
            }
            const amount = parseFloat(amountInput.value);
            if (isNaN(amount) || amount <= 0) {
                event.preventDefault(); amountInput.focus(); alert('Please enter a valid bid amount greater than zero.'); return;
            }
            const currentPriceEl = document.getElementById('current-price-val') || document.querySelector('.price-box-value');
            if (currentPriceEl) {
                const currentPrice = parseFloat(currentPriceEl.textContent.replace(/[^0-9.]/g, ''));
                if (!isNaN(currentPrice) && amount <= currentPrice) {
                    event.preventDefault(); amountInput.focus();
                    alert('Your bid (₹' + amount.toFixed(2) + ') must be greater than current price (₹' + currentPrice.toFixed(2) + ').');
                }
            }
        });
    }
});
