// Chart color palette
const chartColors = [
    '#4CAF50', '#2196F3', '#FFC107', '#F44336', '#9C27B0', 
    '#00BCD4', '#FF9800', '#795548', '#607D8B', '#E91E63'
];

// Get lighter version of each color for hover effects
const getHoverColor = (color) => {
    // Convert to RGB, make it lighter, convert back
    const r = parseInt(color.slice(1, 3), 16);
    const g = parseInt(color.slice(3, 5), 16);
    const b = parseInt(color.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, 0.7)`;
};

// Store chart references globally so we can update them
const charts = {};
let modalChart = null;

// Initialize charts when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initial data load
    fetchAndUpdateCharts();
    
    // Set up automatic refresh every 5 minutes
    setInterval(fetchAndUpdateCharts, 300000); // 300000 ms = 5 minutes
    
    // Set up refresh indicator and manual refresh button
    setupRefreshIndicator(300);
    
    // Attach event listener to manual refresh button
    document.getElementById('manual-refresh-btn').addEventListener('click', fetchAndUpdateCharts);
    
    // Set up the expand button click handlers
    setupExpandButtons();
    
    // Set up modal close button
    document.querySelector('.close-modal-btn').addEventListener('click', closeModal);
    
    // Close modal when clicking outside the modal content
    document.getElementById('chart-modal').addEventListener('click', function(event) {
        if (event.target === this) {
            closeModal();
        }
    });
    
    // Close modal with Escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeModal();
        }
    });
});

// Set up expand buttons for each chart
function setupExpandButtons() {
    const expandButtons = document.querySelectorAll('.expand-btn');
    
    expandButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            // Prevent default behavior and stop event propagation
            event.preventDefault();
            event.stopPropagation();
            
            const chartContainer = this.closest('.chart-container');
            const chartId = chartContainer.dataset.chartId;
            const chartTitle = chartContainer.querySelector('.chart-header h2').textContent;
            const chartDescription = chartContainer.querySelector('.chart-description').textContent;
            
            // Open the modal with chart data
            openChartModal(chartId, chartTitle, chartDescription);
        });
    });
}

// Open the modal with an expanded chart
function openChartModal(chartId, title, description) {
    // Set modal title and description
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-description').textContent = description;
    
    // Show the modal
    const modal = document.getElementById('chart-modal');
    
    // Reset any scrolling position
    window.scrollTo(0, 0);
    document.body.style.overflow = 'hidden';
    
    // Add the active class after a small delay to ensure proper positioning
    setTimeout(() => {
        modal.classList.add('active');
        
        // Create a new chart in the modal
        createModalChart(chartId);
    }, 50);
}

// Close the modal
function closeModal() {
    const modal = document.getElementById('chart-modal');
    
    // First remove active class (for animation)
    modal.classList.remove('active');
    
    // Wait for animation to complete before hiding
    setTimeout(() => {
        // Re-enable body scrolling
        document.body.style.overflow = '';
        
        // Destroy the modal chart to prevent memory leaks
        if (modalChart) {
            modalChart.destroy();
            modalChart = null;
        }
    }, 300);
}

// Create a new chart in the modal based on the original chart
function createModalChart(chartId) {
    // Destroy previous modal chart if it exists
    if (modalChart) {
        modalChart.destroy();
    }
    
    // Get the canvas context for the modal chart
    const modalCanvas = document.getElementById('modal-chart');
    const ctx = modalCanvas.getContext('2d');
    
    // Get the original chart configuration
    const originalChart = charts[chartId];
    
    if (!originalChart) {
        console.error(`Chart with ID ${chartId} not found`);
        return;
    }
    
    // Create a deep copy of the chart data and options to avoid reference issues
    const chartData = JSON.parse(JSON.stringify(originalChart.data));
    
    // Get the chart options and modify for the modal
    const chartOptions = getOptionsForModalChart(originalChart, chartId);
    
    // Create the new chart in the modal
    modalChart = new Chart(ctx, {
        type: originalChart.config.type,
        data: chartData,
        options: chartOptions
    });
}

// Get modified options for the modal chart
function getOptionsForModalChart(originalChart, chartId) {
    // Start with the original options
    const options = JSON.parse(JSON.stringify(originalChart.options));
    
    // Increase font sizes for the larger chart
    if (options.plugins && options.plugins.legend && options.plugins.legend.labels) {
        options.plugins.legend.labels.font = {
            ...options.plugins.legend.labels.font,
            size: 14
        };
    }
    
    if (options.scales) {
        // Increase axis label font sizes
        Object.keys(options.scales).forEach(axisKey => {
            const axis = options.scales[axisKey];
            
            if (axis.title) {
                axis.title.font = {
                    ...axis.title.font,
                    size: 16
                };
            }
            
            if (axis.ticks) {
                axis.ticks.font = {
                    ...axis.ticks.font,
                    size: 12
                };
            }
        });
    }
    
    // Increase tooltip font size
    if (!options.plugins) options.plugins = {};
    if (!options.plugins.tooltip) options.plugins.tooltip = {};
    options.plugins.tooltip.bodyFont = {
        family: 'Trebuchet MS',
        size: 14
    };
    options.plugins.tooltip.titleFont = {
        family: 'Trebuchet MS',
        size: 14,
        weight: 'bold'
    };
    
    // For scatter plots, increase point radius
    if (chartId === 'viewMasteryChart' || chartId === 'learningEfficiencyChart') {
        options.elements = {
            point: {
                radius: 7,
                hoverRadius: 9
            }
        };
    }
    
    return options;
}

// Centralized function to fetch data and update all charts
function fetchAndUpdateCharts() {
    fetch('/api/chart-data')
        .then(response => response.json())
        .then(data => {
            // Update all charts with the received data
            updateCategoryDistributionChart(data.categoryDistribution);
            updateCardsPerCategoryChart(data.categoryDistribution);
            updateReviewScheduleChart(data.reviewSchedule);
            updateLearningCurveChart(data.learningCurve);
            updateCardsAddedChart(data.cardsAddedOverTime);
            updateViewMasteryChart(data.viewMasteryCorrelation);
            updateIntervalGrowthChart(data.intervalGrowth);
            updateLearningEfficiencyChart(data.learningEfficiency);
            updateStabilityDistributionChart(data.stabilityDistribution);
            
            // Update last refresh time indicator
            const now = new Date();
            document.getElementById('last-refresh-time').textContent = `Last updated: ${now.toLocaleTimeString()}`;
            
            // Reset the countdown timer
            if (window.refreshTimer) {
                window.refreshTimer.reset();
            }
            
            // If a modal chart is open, update it too
            if (modalChart) {
                const chartId = document.querySelector('.modal.active') ? 
                    document.getElementById('modal-title').textContent : null;
                if (chartId) {
                    createModalChart(chartId);
                }
            }
        })
        .catch(error => console.error('Error fetching chart data:', error));
}

// Function to create a visual countdown indicator
function setupRefreshIndicator(seconds) {
    // Create a countdown timer
    window.refreshTimer = {
        totalSeconds: seconds,
        intervalId: null,
        element: document.getElementById('next-refresh'),
        
        start: function() {
            this.intervalId = setInterval(() => {
                this.totalSeconds--;
                const minutes = Math.floor(this.totalSeconds / 60);
                const seconds = this.totalSeconds % 60;
                this.element.textContent = `Next refresh in: ${minutes}:${seconds.toString().padStart(2, '0')}`;
                
                if (this.totalSeconds <= 0) {
                    clearInterval(this.intervalId);
                }
            }, 1000);
        },
        
        reset: function() {
            clearInterval(this.intervalId);
            this.totalSeconds = seconds;
            this.start();
        }
    };
    
    window.refreshTimer.start();
}

// 1. Category Distribution Pie Chart
function initializeCategoryDistributionChart(data) {
    const ctx = document.getElementById('categoryDistributionChart').getContext('2d');
    
    const labels = data.map(item => item.CategoryName);
    const values = data.map(item => Math.round(item.CardCount)); // Ensure integer
    
    charts.categoryDistributionChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: chartColors.slice(0, labels.length),
                hoverBackgroundColor: chartColors.slice(0, labels.length).map(getHoverColor),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            // Ensure card count is an integer
                            const value = Math.round(context.raw) || 0;
                            const total = context.dataset.data.reduce((acc, cur) => acc + cur, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} cards (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Function to update category distribution chart with new data
function updateCategoryDistributionChart(data) {
    if (!charts.categoryDistributionChart) {
        initializeCategoryDistributionChart(data);
        return;
    }
    
    const labels = data.map(item => item.CategoryName);
    const values = data.map(item => Math.round(item.CardCount)); // Ensure integer
    
    charts.categoryDistributionChart.data.labels = labels;
    charts.categoryDistributionChart.data.datasets[0].data = values;
    charts.categoryDistributionChart.data.datasets[0].backgroundColor = chartColors.slice(0, labels.length);
    charts.categoryDistributionChart.data.datasets[0].hoverBackgroundColor = chartColors.slice(0, labels.length).map(getHoverColor);
    
    charts.categoryDistributionChart.update();
}

// 2. Cards per Category Bar Chart
function initializeCardsPerCategoryChart(data) {
    const ctx = document.getElementById('cardsPerCategoryChart').getContext('2d');
    
    const labels = data.map(item => item.CategoryName);
    const values = data.map(item => Math.round(item.CardCount)); // Ensure integer
    
    charts.cardsPerCategoryChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Number of Cards',
                data: values,
                backgroundColor: chartColors[1],
                hoverBackgroundColor: getHoverColor(chartColors[1]),
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        },
                        stepSize: 1,
                        precision: 0
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    title: {
                        display: true,
                        text: 'Number of Cards',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS',
                            size: 12
                        }
                    }
                },
                x: {
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            // Ensure card count is an integer
                            return `${context.label}: ${Math.round(context.raw)} cards`;
                        }
                    }
                }
            }
        }
    });
}

// Update function for cards per category chart
function updateCardsPerCategoryChart(data) {
    if (!charts.cardsPerCategoryChart) {
        initializeCardsPerCategoryChart(data);
        return;
    }
    
    const labels = data.map(item => item.CategoryName);
    const values = data.map(item => Math.round(item.CardCount)); // Ensure integer
    
    charts.cardsPerCategoryChart.data.labels = labels;
    charts.cardsPerCategoryChart.data.datasets[0].data = values;
    
    charts.cardsPerCategoryChart.update();
}

// 3. Review Schedule Timeline
function initializeReviewScheduleChart(data) {
    const ctx = document.getElementById('reviewScheduleChart').getContext('2d');
    
    const labels = data.map(item => item.ReviewDate);
    const values = data.map(item => Math.round(item.CardCount)); // Ensure integer
    
    charts.reviewScheduleChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Cards Due',
                data: values,
                backgroundColor: chartColors[2],
                hoverBackgroundColor: getHoverColor(chartColors[2]),
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        },
                        stepSize: 1,
                        precision: 0
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    title: {
                        display: true,
                        text: 'Cards Due',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS',
                            size: 12
                        }
                    }
                },
                x: {
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        },
                        maxRotation: 90,
                        minRotation: 45
                    },
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(tooltipItems) {
                            const date = new Date(tooltipItems[0].label);
                            return date.toLocaleDateString();
                        },
                        label: function(context) {
                            // Ensure card count is an integer
                            return `Cards due: ${Math.round(context.raw)}`;
                        }
                    }
                }
            }
        }
    });
}

function updateReviewScheduleChart(data) {
    if (!charts.reviewScheduleChart) {
        initializeReviewScheduleChart(data);
        return;
    }
    
    const labels = data.map(item => item.ReviewDate);
    const values = data.map(item => Math.round(item.CardCount)); // Ensure integer
    
    charts.reviewScheduleChart.data.labels = labels;
    charts.reviewScheduleChart.data.datasets[0].data = values;
    
    charts.reviewScheduleChart.update();
}

// 4. Learning Curve
function initializeLearningCurveChart(data) {
    const ctx = document.getElementById('learningCurveChart').getContext('2d');
    
    const labels = data.map(item => item.Date);
    const values = data.map(item => item.AverageMastery);
    
    charts.learningCurveChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Mastery %',
                data: values,
                backgroundColor: 'rgba(156, 39, 176, 0.2)', // Purple
                borderColor: chartColors[4], // Purple border
                borderWidth: 2,
                tension: 0.3,
                pointRadius: 3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    title: {
                        display: true,
                        text: 'Average Mastery %',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS',
                            size: 12
                        }
                    }
                },
                x: {
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        },
                        maxRotation: 90,
                        minRotation: 45
                    },
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(tooltipItems) {
                            return tooltipItems[0].label;
                        },
                        label: function(context) {
                            return `Average Mastery: ${context.raw.toFixed(1)}%`;
                        }
                    }
                }
            }
        }
    });
}

function updateLearningCurveChart(data) {
    if (!charts.learningCurveChart) {
        initializeLearningCurveChart(data);
        return;
    }
    
    const labels = data.map(item => item.Date);
    const values = data.map(item => item.AverageMastery);
    
    charts.learningCurveChart.data.labels = labels;
    charts.learningCurveChart.data.datasets[0].data = values;
    
    charts.learningCurveChart.update();
}

// 5. Cards Added Over Time
function initializeCardsAddedChart(data) {
    const ctx = document.getElementById('cardsAddedChart').getContext('2d');
    
    const labels = data.map(item => item.Date);
    const values = data.map(item => Math.round(item.CardsAdded)); // Ensure integer
    
    // Calculate cumulative values
    const cumulativeValues = [];
    let runningTotal = 0;
    values.forEach(val => {
        runningTotal += val;
        cumulativeValues.push(runningTotal);
    });
    
    charts.cardsAddedChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Cards Added',
                    data: values,
                    backgroundColor: chartColors[5],
                    borderColor: chartColors[5],
                    borderWidth: 2,
                    tension: 0.1,
                    pointRadius: 3,
                    yAxisID: 'y'
                },
                {
                    label: 'Total Cards',
                    data: cumulativeValues,
                    backgroundColor: 'rgba(0, 188, 212, 0.2)', // Cyan
                    borderColor: getHoverColor(chartColors[5]),
                    borderWidth: 2,
                    tension: 0.1,
                    pointRadius: 0,
                    fill: true,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    position: 'left',
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        },
                        stepSize: 1,
                        precision: 0
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    title: {
                        display: true,
                        text: 'Daily Cards Added',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS',
                            size: 12
                        }
                    }
                },
                y1: {
                    beginAtZero: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false
                    },
                    ticks: {
                        color: getHoverColor(chartColors[5]),
                        font: {
                            family: 'Trebuchet MS'
                        },
                        stepSize: 1,
                        precision: 0
                    },
                    title: {
                        display: true,
                        text: 'Total Cards',
                        color: getHoverColor(chartColors[5]),
                        font: {
                            family: 'Trebuchet MS',
                            size: 12
                        }
                    }
                },
                x: {
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        },
                        maxRotation: 90,
                        minRotation: 45
                    },
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            // Ensure card counts are integers
                            const value = Math.round(context.raw);
                            if (context.dataset.label === 'Cards Added') {
                                return `Cards Added: ${value}`;
                            } else {
                                return `Total Cards: ${value}`;
                            }
                        }
                    }
                }
            }
        }
    });
}

function updateCardsAddedChart(data) {
    if (!charts.cardsAddedChart) {
        initializeCardsAddedChart(data);
        return;
    }
    
    const labels = data.map(item => item.Date);
    const values = data.map(item => Math.round(item.CardsAdded)); // Ensure integer
    
    // Calculate cumulative values
    const cumulativeValues = [];
    let runningTotal = 0;
    values.forEach(val => {
        runningTotal += val;
        cumulativeValues.push(runningTotal);
    });
    
    charts.cardsAddedChart.data.labels = labels;
    charts.cardsAddedChart.data.datasets[0].data = values;
    charts.cardsAddedChart.data.datasets[1].data = cumulativeValues;
    
    charts.cardsAddedChart.update();
}

// 6. View vs Mastery Correlation
function initializeViewMasteryChart(data) {
    const ctx = document.getElementById('viewMasteryChart').getContext('2d');
    
    // Ensure view count is an integer for each point
    const values = data.map(item => ({
        x: Math.round(item.ViewCount), // Ensure integer view count
        y: item.MasteryPercentage, 
        question: item.Question
    }));
    
    charts.viewMasteryChart = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Cards',
                data: values,
                backgroundColor: chartColors[3],
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    title: {
                        display: true,
                        text: 'Mastery %',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS',
                            size: 12
                        }
                    }
                },
                x: {
                    beginAtZero: true,
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        },
                        stepSize: 1,
                        precision: 0
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    title: {
                        display: true,
                        text: 'View Count',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS',
                            size: 12
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const data = context.dataset.data[context.dataIndex];
                            return [
                                `Views: ${Math.round(data.x)}, Mastery: ${data.y.toFixed(1)}%`,
                                `Q: ${data.question.substring(0, 30)}${data.question.length > 30 ? '...' : ''}`
                            ];
                        }
                    }
                }
            }
        }
    });
}

function updateViewMasteryChart(data) {
    if (!charts.viewMasteryChart) {
        initializeViewMasteryChart(data);
        return;
    }
    
    // Ensure view count is an integer for each point
    const values = data.map(item => ({
        x: Math.round(item.ViewCount), // Ensure integer view count
        y: item.MasteryPercentage,
        question: item.Question
    }));
    
    charts.viewMasteryChart.data.datasets[0].data = values;
    
    charts.viewMasteryChart.update();
}

// 7. Interval Growth Distribution
function initializeIntervalGrowthChart(data) {
    const ctx = document.getElementById('intervalGrowthChart').getContext('2d');
    
    // Sort data by interval
    data.sort((a, b) => a.CurrentInterval - b.CurrentInterval);
    
    const labels = data.map(item => item.CurrentInterval + ' days');
    const values = data.map(item => Math.round(item.CardCount)); // Ensure integer
    
    charts.intervalGrowthChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Number of Cards',
                data: values,
                backgroundColor: chartColors[6],
                hoverBackgroundColor: getHoverColor(chartColors[6]),
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        },
                        stepSize: 1,
                        precision: 0
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    title: {
                        display: true,
                        text: 'Number of Cards',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS',
                            size: 12
                        }
                    }
                },
                x: {
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    grid: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Interval Length',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS',
                            size: 12
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            // Ensure card count is an integer
                            return `Cards: ${Math.round(context.raw)}`;
                        }
                    }
                }
            }
        }
    });
}

function updateIntervalGrowthChart(data) {
    if (!charts.intervalGrowthChart) {
        initializeIntervalGrowthChart(data);
        return;
    }
    
    // Sort data by interval
    data.sort((a, b) => a.CurrentInterval - b.CurrentInterval);
    
    const labels = data.map(item => item.CurrentInterval + ' days');
    const values = data.map(item => Math.round(item.CardCount)); // Ensure integer
    
    charts.intervalGrowthChart.data.labels = labels;
    charts.intervalGrowthChart.data.datasets[0].data = values;
    
    charts.intervalGrowthChart.update();
}

// 8. Learning Efficiency
function initializeLearningEfficiencyChart(data) {
    const ctx = document.getElementById('learningEfficiencyChart').getContext('2d');
    
    // Ensure view count is an integer for each point
    const values = data.map(item => ({
        x: Math.round(item.ViewCount), // Ensure integer view count
        y: item.EfficiencyScore,
        question: item.Question
    }));
    
    charts.learningEfficiencyChart = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Cards',
                data: values,
                backgroundColor: chartColors[7],
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    title: {
                        display: true,
                        text: 'Efficiency Score (Mastery/Views)',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS',
                            size: 12
                        }
                    }
                },
                x: {
                    beginAtZero: true,
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        },
                        stepSize: 1,
                        precision: 0
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    title: {
                        display: true,
                        text: 'View Count',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS',
                            size: 12
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const data = context.dataset.data[context.dataIndex];
                            return [
                                `Views: ${Math.round(data.x)}, Efficiency: ${data.y.toFixed(1)}%`,
                                `Q: ${data.question.substring(0, 30)}${data.question.length > 30 ? '...' : ''}`
                            ];
                        }
                    }
                }
            }
        }
    });
}

function updateLearningEfficiencyChart(data) {
    if (!charts.learningEfficiencyChart) {
        initializeLearningEfficiencyChart(data);
        return;
    }
    
    // Ensure view count is an integer for each point
    const values = data.map(item => ({
        x: Math.round(item.ViewCount), // Ensure integer view count
        y: item.EfficiencyScore,
        question: item.Question
    }));
    
    charts.learningEfficiencyChart.data.datasets[0].data = values;
    
    charts.learningEfficiencyChart.update();
}

// 9. FSRS Stability Distribution
function initializeStabilityDistributionChart(data) {
    const ctx = document.getElementById('stabilityDistributionChart').getContext('2d');
    
    const labels = data.map(item => item.StabilityRange);
    const values = data.map(item => Math.round(item.CardCount)); // Ensure integer
    
    charts.stabilityDistributionChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Number of Cards',
                data: values,
                backgroundColor: chartColors[8],
                hoverBackgroundColor: getHoverColor(chartColors[8]),
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        },
                        stepSize: 1,
                        precision: 0
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    title: {
                        display: true,
                        text: 'Number of Cards',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS',
                            size: 12
                        }
                    }
                },
                x: {
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    grid: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Memory Stability Range',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS',
                            size: 12
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            // Ensure card count is an integer
                            return `Cards: ${Math.round(context.raw)}`;
                        }
                    }
                }
            }
        }
    });
}

function updateStabilityDistributionChart(data) {
    if (!charts.stabilityDistributionChart) {
        initializeStabilityDistributionChart(data);
        return;
    }
    
    const labels = data.map(item => item.StabilityRange);
    const values = data.map(item => Math.round(item.CardCount)); // Ensure integer
    
    charts.stabilityDistributionChart.data.labels = labels;
    charts.stabilityDistributionChart.data.datasets[0].data = values;
    
    charts.stabilityDistributionChart.update();
}