/**
 * AgriSure - Main JavaScript
 * Contract Farming Marketplace
 */

'use strict';

// =============================================================================
// HTMX Configuration
// =============================================================================

document.addEventListener('DOMContentLoaded', function () {
    // Configure HTMX to include CSRF token in all requests
    document.body.addEventListener('htmx:configRequest', function (event) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
            event.detail.headers['X-CSRFToken'] = csrfToken.value;
        }
    });

    // Initialize toast auto-dismiss
    initToasts();

    // Initialize mobile menu
    initMobileMenu();
});

// =============================================================================
// Toast Notifications
// =============================================================================

function initToasts() {
    const toasts = document.querySelectorAll('[data-toast]');
    toasts.forEach(function (toast) {
        const duration = parseInt(toast.dataset.duration) || 5000;
        setTimeout(function () {
            dismissToast(toast);
        }, duration);
    });
}

function dismissToast(toast) {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease-in-out';
    setTimeout(function () {
        toast.remove();
    }, 300);
}

// =============================================================================
// Mobile Menu
// =============================================================================

function initMobileMenu() {
    const menuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');

    if (menuButton && mobileMenu) {
        menuButton.addEventListener('click', function () {
            mobileMenu.classList.toggle('hidden');
        });
    }
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Format currency in Indian Rupees
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(amount);
}

/**
 * Format date in readable format
 */
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-IN', options);
}

/**
 * Debounce function for search inputs
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = function () {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Show loading spinner on a button
 */
function setButtonLoading(button, loading) {
    if (loading) {
        button.disabled = true;
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = `
            <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            Processing...
        `;
    } else {
        button.disabled = false;
        button.innerHTML = button.dataset.originalText;
    }
}
