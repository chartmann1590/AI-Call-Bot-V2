/**
 * CallBot Application JavaScript
 * Common functionality and utilities
 */

// Global variables
let currentAudio = null;
let autoRefreshInterval = null;

// Initialize application
$(document).ready(function() {
    initializeApp();
});

function initializeApp() {
    // Add fade-in animation to cards
    $('.card').addClass('fade-in');
    
    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Initialize popovers
    $('[data-bs-toggle="popover"]').popover();
    
    // Setup form validation
    setupFormValidation();
    
    // Setup auto-refresh for active calls
    setupAutoRefresh();
    
    // Setup keyboard shortcuts
    setupKeyboardShortcuts();
}

/**
 * Form validation setup
 */
function setupFormValidation() {
    // Add custom validation for required fields
    $('form').on('submit', function(e) {
        const requiredFields = $(this).find('[required]');
        let isValid = true;
        
        requiredFields.each(function() {
            if (!$(this).val()) {
                $(this).addClass('is-invalid');
                isValid = false;
            } else {
                $(this).removeClass('is-invalid');
            }
        });
        
        if (!isValid) {
            e.preventDefault();
            showAlert('Please fill in all required fields.', 'danger');
        }
    });
    
    // Remove invalid class on input
    $('input, select, textarea').on('input change', function() {
        if ($(this).val()) {
            $(this).removeClass('is-invalid');
        }
    });
}

/**
 * Setup auto-refresh functionality
 */
function setupAutoRefresh() {
    // Auto-refresh active calls every 10 seconds
    if ($('#active-calls').length) {
        autoRefreshInterval = setInterval(function() {
            updateActiveCalls();
        }, 10000);
    }
}

/**
 * Setup keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    $(document).keydown(function(e) {
        // Ctrl/Cmd + R to refresh
        if ((e.ctrlKey || e.metaKey) && e.keyCode === 82) {
            e.preventDefault();
            location.reload();
        }
        
        // Ctrl/Cmd + S to save (on settings page)
        if ((e.ctrlKey || e.metaKey) && e.keyCode === 83) {
            e.preventDefault();
            $('form').submit();
        }
        
        // Escape to close modals
        if (e.keyCode === 27) {
            $('.modal').modal('hide');
        }
    });
}

/**
 * Update active calls count
 */
function updateActiveCalls() {
    $.get('/api/active_calls')
        .done(function(data) {
            const activeCount = Object.keys(data).length;
            $('#active-calls').text(activeCount);
            
            // Update status indicator
            if (activeCount > 0) {
                $('#active-calls').addClass('text-warning');
            } else {
                $('#active-calls').removeClass('text-warning');
            }
        })
        .fail(function() {
            console.error('Failed to update active calls');
        });
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info', duration = 5000) {
    const alertId = 'alert-' + Date.now();
    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Add alert to page
    $('.container').first().prepend(alertHtml);
    
    // Auto-dismiss after duration
    if (duration > 0) {
        setTimeout(function() {
            $(`#${alertId}`).fadeOut(function() {
                $(this).remove();
            });
        }, duration);
    }
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
            showAlert('Copied to clipboard!', 'success', 2000);
        }).catch(function() {
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

/**
 * Fallback copy to clipboard for older browsers
 */
function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showAlert('Copied to clipboard!', 'success', 2000);
    } catch (err) {
        showAlert('Failed to copy to clipboard', 'danger', 3000);
    }
    
    document.body.removeChild(textArea);
}

/**
 * Play audio file
 */
function playAudio(audioUrl, callId = null) {
    // Stop any currently playing audio
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }
    
    // Create new audio element
    currentAudio = new Audio(audioUrl);
    
    // Add event listeners
    currentAudio.addEventListener('loadstart', function() {
        showAlert('Loading audio...', 'info', 2000);
    });
    
    currentAudio.addEventListener('canplay', function() {
        showAlert('Audio loaded successfully', 'success', 2000);
    });
    
    currentAudio.addEventListener('error', function() {
        showAlert('Failed to load audio', 'danger', 3000);
    });
    
    currentAudio.addEventListener('ended', function() {
        currentAudio = null;
    });
    
    // Play audio
    currentAudio.play().catch(function(error) {
        console.error('Audio playback failed:', error);
        showAlert('Failed to play audio', 'danger', 3000);
    });
}

/**
 * Format duration in MM:SS format
 */
function formatDuration(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

/**
 * Format timestamp
 */
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
}

/**
 * Debounce function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Search functionality with debouncing
 */
const debouncedSearch = debounce(function(searchTerm) {
    // Implement search functionality here
    console.log('Searching for:', searchTerm);
}, 300);

/**
 * Export data to CSV
 */
function exportToCSV(data, filename) {
    const csvContent = convertToCSV(data);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

/**
 * Convert data to CSV format
 */
function convertToCSV(data) {
    if (!data || data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const csvRows = [];
    
    // Add headers
    csvRows.push(headers.join(','));
    
    // Add data rows
    for (const row of data) {
        const values = headers.map(header => {
            const value = row[header];
            // Escape commas and quotes
            return `"${String(value).replace(/"/g, '""')}"`;
        });
        csvRows.push(values.join(','));
    }
    
    return csvRows.join('\n');
}

/**
 * Loading state management
 */
function setLoadingState(element, isLoading) {
    if (isLoading) {
        $(element).addClass('loading');
        $(element).prop('disabled', true);
    } else {
        $(element).removeClass('loading');
        $(element).prop('disabled', false);
    }
}

/**
 * API request wrapper with error handling
 */
function apiRequest(url, options = {}) {
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
        ...options
    };
    
    return fetch(url, defaultOptions)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .catch(error => {
            console.error('API request failed:', error);
            showAlert('Request failed: ' + error.message, 'danger', 5000);
            throw error;
        });
}

/**
 * Cleanup function
 */
function cleanup() {
    // Stop auto-refresh
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    // Stop audio
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }
    
    // Remove event listeners
    $(document).off('keydown');
}

// Cleanup on page unload
$(window).on('beforeunload', cleanup);

// Export functions for global use
window.CallBot = {
    showAlert,
    copyToClipboard,
    playAudio,
    formatDuration,
    formatTimestamp,
    exportToCSV,
    setLoadingState,
    apiRequest,
    cleanup
}; 