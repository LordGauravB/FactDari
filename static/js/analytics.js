// Analytics Dashboard JavaScript

// Global variables
let charts = {};
let chartData = null;
let refreshInterval = null;
let countdownInterval = null;
let currentTheme = 'dark';

// Chart.js default configuration
Chart.defaults.color = '#b0b0b0';
Chart.defaults.borderColor = '#333333';
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';

// Color palette
const colors = {
    primary: '#4CAF50',
    primaryLight: '#81C784',
    primaryDark: '#388E3C',
    secondary: '#2196F3',
    accent: '#FFC107',
    danger: '#F44336',
    warning: '#FF9800',
    info: '#00BCD4',
    purple: '#9C27B0',
    pink: '#E91E63',
    chartColors: [
        '#4CAF50', '#2196F3', '#FFC107', '#FF5722', '#9C27B0',
        '#00BCD4', '#FF9800', '#795548', '#607D8B', '#E91E63'
    ]
};

// Get theme-aware colors
function getThemeColors() {
    return {
        grid: currentTheme === 'light' ? '#e0e0e0' : '#333333',
        text: currentTheme === 'light' ? '#555555' : '#b0b0b0',
        border: currentTheme === 'light' ? '#e0e0e0' : '#333333',
        background: currentTheme === 'light' ? '#ffffff' : '#1e1e1e'
    };
}

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeTheme();
    initializeTabs();
    initializeEventListeners();
    fetchData();
    startAutoRefresh();
});

// Tab functionality
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.getAttribute('data-tab');
            
            // Update active states
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            button.classList.add('active');
            document.getElementById(`${targetTab}-tab`).classList.add('active');
            
            // Resize charts in the active tab
            setTimeout(() => {
                Object.values(charts).forEach(chart => chart.resize());
            }, 100);
        });
    });
}

// Event listeners
function initializeEventListeners() {
    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', () => {
        fetchData();
        resetCountdown();
    });
    
    // Expand buttons
    document.querySelectorAll('.expand-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const chartId = btn.getAttribute('data-chart');
            showModal(chartId);
        });
    });
    
    // Modal close
    document.querySelector('.modal-close').addEventListener('click', closeModal);
    document.getElementById('chart-modal').addEventListener('click', (e) => {
        if (e.target.id === 'chart-modal') closeModal();
    });
}

// Fetch data from API
async function fetchData() {
    try {
        // Show loading state
        showLoadingState();
        
        const response = await fetch('/api/chart-data');
        if (!response.ok) throw new Error('Failed to fetch data');
        
        chartData = await response.json();
        console.log('Received chart data:', chartData); // Debug log
        
        // Update metrics
        updateMetrics();
        
        // Create/update charts
        createCharts();
        
        // Hide loading state
        hideLoadingState();
        
    } catch (error) {
        console.error('Error fetching data:', error);
        showErrorState();
    }
}

// Update key metrics
function updateMetrics() {
    if (!chartData) return;
    
    // Calculate metrics from data
    const totalCards = chartData.category_distribution.labels.reduce((sum, _, i) => 
        sum + chartData.category_distribution.data[i], 0);
    
    const dueToday = chartData.review_schedule_timeline.datasets[0].data[0] || 0;
    
    const masteredCards = chartData.cards_per_category.datasets
        .find(ds => ds.label === 'Mastered')?.data.reduce((a, b) => a + b, 0) || 0;
    
    const activeCategories = chartData.category_distribution.labels.length;
    
    // Update DOM with animations
    animateValue('total-cards', totalCards);
    animateValue('due-today', dueToday);
    animateValue('mastered-cards', masteredCards);
    animateValue('active-categories', activeCategories);
}

// Animate number changes
function animateValue(elementId, endValue) {
    const element = document.getElementById(elementId);
    const startValue = parseInt(element.textContent) || 0;
    const duration = 1000;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const currentValue = Math.floor(startValue + (endValue - startValue) * progress);
        
        element.textContent = currentValue.toLocaleString();
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

// Create all charts
function createCharts() {
    if (!chartData) return;
    
    // Category Distribution (Pie Chart)
    createOrUpdateChart('category-distribution', {
        type: 'doughnut',
        data: {
            labels: chartData.category_distribution.labels,
            datasets: [{
                data: chartData.category_distribution.data,
                backgroundColor: colors.chartColors,
                borderWidth: 2,
                borderColor: getThemeColors().background
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        padding: 15,
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
    
    // Cards per Category (Stacked Bar Chart)
    createOrUpdateChart('cards-per-category', {
        type: 'bar',
        data: chartData.cards_per_category,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { 
                    stacked: true,
                    grid: { display: false }
                },
                y: { 
                    stacked: true,
                    grid: { color: getThemeColors().grid },
                    ticks: { stepSize: 1 }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: { padding: 15 }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            }
        }
    });
    
    // Review Schedule Timeline
    createOrUpdateChart('review-schedule', {
        type: 'bar',
        data: chartData.review_schedule_timeline,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { 
                    grid: { display: false }
                },
                y: { 
                    grid: { color: getThemeColors().grid },
                    ticks: { stepSize: 1 }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: function(tooltipItems) {
                            const date = new Date();
                            date.setDate(date.getDate() + tooltipItems[0].dataIndex);
                            return date.toLocaleDateString('en-US', { 
                                weekday: 'short', 
                                month: 'short', 
                                day: 'numeric' 
                            });
                        }
                    }
                }
            }
        }
    });
    
    // Learning Curve
    createOrUpdateChart('learning-curve', {
        type: 'line',
        data: chartData.learning_curve,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { 
                    grid: { display: false }
                },
                y: { 
                    grid: { color: getThemeColors().grid },
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Retention: ${context.parsed.y.toFixed(1)}%`;
                        }
                    }
                }
            },
            elements: {
                line: {
                    tension: 0.4,
                    borderWidth: 3,
                    borderColor: colors.primary,
                    backgroundColor: `${colors.primary}20`
                },
                point: {
                    radius: 4,
                    backgroundColor: colors.primary,
                    borderColor: getThemeColors().background,
                    borderWidth: 2,
                    hoverRadius: 6
                }
            }
        }
    });
    
    // Cards Added Over Time
    createOrUpdateChart('cards-added-over-time', {
        type: 'line',
        data: chartData.cards_added_over_time,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { 
                    grid: { display: false }
                },
                y: { 
                    grid: { color: getThemeColors().grid }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: { padding: 15 }
                }
            },
            elements: {
                line: {
                    tension: 0.4,
                    borderWidth: 2
                },
                point: {
                    radius: 3,
                    hoverRadius: 5
                }
            }
        }
    });
    
    // View vs Mastery Correlation
    createOrUpdateChart('view-mastery-correlation', {
        type: 'scatter',
        data: chartData.view_mastery_correlation,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'View Count'
                    },
                    grid: { color: getThemeColors().grid }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Average Easiness'
                    },
                    grid: { color: getThemeColors().grid }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Views: ${context.parsed.x}, Easiness: ${context.parsed.y.toFixed(2)}`;
                        }
                    }
                }
            },
            elements: {
                point: {
                    radius: 5,
                    backgroundColor: `${colors.secondary}80`,
                    borderColor: colors.secondary,
                    borderWidth: 2,
                    hoverRadius: 7
                }
            }
        }
    });
    
    // Interval Growth Distribution
    createOrUpdateChart('interval-growth', {
        type: 'bar',
        data: chartData.interval_growth_distribution,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { 
                    grid: { display: false }
                },
                y: { 
                    grid: { color: getThemeColors().grid },
                    ticks: { stepSize: 1 }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
    
    // Learning Efficiency
    createOrUpdateChart('learning-efficiency', {
        type: 'scatter',
        data: chartData.learning_efficiency,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Review Count'
                    },
                    grid: { color: getThemeColors().grid }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Days to Master'
                    },
                    grid: { color: getThemeColors().grid }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Reviews: ${context.parsed.x}, Days: ${context.parsed.y}`;
                        }
                    }
                }
            },
            elements: {
                point: {
                    radius: 5,
                    backgroundColor: `${colors.accent}80`,
                    borderColor: colors.accent,
                    borderWidth: 2,
                    hoverRadius: 7
                }
            }
        }
    });
    
    // FSRS Stability Distribution
    createOrUpdateChart('fsrs-stability', {
        type: 'bar',
        data: chartData.fsrs_stability_distribution,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { 
                    grid: { display: false }
                },
                y: { 
                    grid: { color: getThemeColors().grid },
                    ticks: { stepSize: 1 }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

// Create or update a chart
function createOrUpdateChart(id, config) {
    const ctx = document.getElementById(id);
    if (!ctx) return;
    
    if (charts[id]) {
        // Update existing chart
        charts[id].data = config.data;
        charts[id].update('resize');
    } else {
        // Create new chart
        charts[id] = new Chart(ctx.getContext('2d'), config);
    }
}

// Modal functionality
function showModal(chartId) {
    const modal = document.getElementById('chart-modal');
    const modalCanvas = document.getElementById('modal-chart');
    const originalChart = charts[chartId];
    
    if (!originalChart) return;
    
    // Clone the chart configuration
    const config = {
        type: originalChart.config.type,
        data: JSON.parse(JSON.stringify(originalChart.config.data)),
        options: JSON.parse(JSON.stringify(originalChart.config.options))
    };
    
    // Adjust options for modal view
    config.options.maintainAspectRatio = false;
    
    // Destroy existing modal chart if any
    if (charts['modal']) {
        charts['modal'].destroy();
    }
    
    // Create new chart in modal
    charts['modal'] = new Chart(modalCanvas.getContext('2d'), config);
    
    // Show modal
    modal.classList.add('show');
}

function closeModal() {
    const modal = document.getElementById('chart-modal');
    modal.classList.remove('show');
    
    // Destroy modal chart
    if (charts['modal']) {
        charts['modal'].destroy();
        delete charts['modal'];
    }
}

// Auto-refresh functionality
function startAutoRefresh() {
    resetCountdown();
    
    refreshInterval = setInterval(() => {
        fetchData();
        resetCountdown();
    }, 120000); // 2 minutes
}

function resetCountdown() {
    let seconds = 120;
    const countdownElement = document.getElementById('countdown');
    
    // Clear existing countdown
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
    
    // Display initial time
    updateCountdownDisplay(seconds, countdownElement);
    
    countdownInterval = setInterval(() => {
        seconds--;
        updateCountdownDisplay(seconds, countdownElement);
        
        if (seconds <= 0) {
            clearInterval(countdownInterval);
        }
    }, 1000);
}

function updateCountdownDisplay(seconds, element) {
    if (seconds > 60) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        element.textContent = `${minutes}m ${remainingSeconds}s`;
    } else {
        element.textContent = `${seconds}s`;
    }
}

// Loading states
function showLoadingState() {
    document.getElementById('loading-screen').classList.remove('hidden');
}

function hideLoadingState() {
    setTimeout(() => {
        document.getElementById('loading-screen').classList.add('hidden');
    }, 300);
}

function showErrorState() {
    hideLoadingState();
    // You can add error handling UI here
    console.error('Failed to load analytics data');
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (refreshInterval) clearInterval(refreshInterval);
    if (countdownInterval) clearInterval(countdownInterval);
});

// Theme Management
function initializeTheme() {
    // Load theme from localStorage
    const savedTheme = localStorage.getItem('memodari-theme') || 'dark';
    currentTheme = savedTheme;
    applyTheme(savedTheme);
    
    // Add theme toggle listener
    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
}

function toggleTheme() {
    currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
    applyTheme(currentTheme);
    localStorage.setItem('memodari-theme', currentTheme);
    
    // Update all charts with new theme
    updateChartsTheme();
}

function applyTheme(theme) {
    const body = document.body;
    const darkIcon = document.getElementById('theme-icon-dark');
    const lightIcon = document.getElementById('theme-icon-light');
    
    if (theme === 'light') {
        body.classList.add('light-theme');
        darkIcon.style.display = 'none';
        lightIcon.style.display = 'block';
        
        // Update Chart.js defaults for light theme
        Chart.defaults.color = '#555555';
        Chart.defaults.borderColor = '#e0e0e0';
    } else {
        body.classList.remove('light-theme');
        darkIcon.style.display = 'block';
        lightIcon.style.display = 'none';
        
        // Update Chart.js defaults for dark theme
        Chart.defaults.color = '#b0b0b0';
        Chart.defaults.borderColor = '#333333';
    }
}

function updateChartsTheme() {
    // Re-create all charts with new theme
    if (chartData) {
        createCharts();
    }
}