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
});

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
            // Removed: updateLapsesByCategoryChart(data.lapsesByCategory);
            
            // Update last refresh time indicator
            const now = new Date();
            document.getElementById('last-refresh-time').textContent = `Last updated: ${now.toLocaleTimeString()}`;
            
            // Reset the countdown timer
            if (window.refreshTimer) {
                window.refreshTimer.reset();
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
    const values = data.map(item => item.CardCount);
    
    charts.categoryDistribution = new Chart(ctx, {
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
                            const value = context.raw || 0;
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
    if (!charts.categoryDistribution) {
        initializeCategoryDistributionChart(data);
        return;
    }
    
    const labels = data.map(item => item.CategoryName);
    const values = data.map(item => item.CardCount);
    
    charts.categoryDistribution.data.labels = labels;
    charts.categoryDistribution.data.datasets[0].data = values;
    charts.categoryDistribution.data.datasets[0].backgroundColor = chartColors.slice(0, labels.length);
    charts.categoryDistribution.data.datasets[0].hoverBackgroundColor = chartColors.slice(0, labels.length).map(getHoverColor);
    
    charts.categoryDistribution.update();
}

// 2. Cards per Category Bar Chart
function initializeCardsPerCategoryChart(data) {
    const ctx = document.getElementById('cardsPerCategoryChart').getContext('2d');
    
    const labels = data.map(item => item.CategoryName);
    const values = data.map(item => item.CardCount);
    
    charts.cardsPerCategory = new Chart(ctx, {
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
                }
            }
        }
    });
}

// Update function for cards per category chart
function updateCardsPerCategoryChart(data) {
    if (!charts.cardsPerCategory) {
        initializeCardsPerCategoryChart(data);
        return;
    }
    
    const labels = data.map(item => item.CategoryName);
    const values = data.map(item => item.CardCount);
    
    charts.cardsPerCategory.data.labels = labels;
    charts.cardsPerCategory.data.datasets[0].data = values;
    
    charts.cardsPerCategory.update();
}

// 3. Review Schedule Timeline
function initializeReviewScheduleChart(data) {
    const ctx = document.getElementById('reviewScheduleChart').getContext('2d');
    
    const labels = data.map(item => item.ReviewDate);
    const values = data.map(item => item.CardCount);
    
    charts.reviewSchedule = new Chart(ctx, {
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
                        }
                    }
                }
            }
        }
    });
}

function updateReviewScheduleChart(data) {
    if (!charts.reviewSchedule) {
        initializeReviewScheduleChart(data);
        return;
    }
    
    const labels = data.map(item => item.ReviewDate);
    const values = data.map(item => item.CardCount);
    
    charts.reviewSchedule.data.labels = labels;
    charts.reviewSchedule.data.datasets[0].data = values;
    
    charts.reviewSchedule.update();
}

// 4. Learning Curve
function initializeLearningCurveChart(data) {
    const ctx = document.getElementById('learningCurveChart').getContext('2d');
    
    const labels = data.map(item => item.Date);
    const values = data.map(item => item.AverageMastery);
    
    charts.learningCurve = new Chart(ctx, {
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
    if (!charts.learningCurve) {
        initializeLearningCurveChart(data);
        return;
    }
    
    const labels = data.map(item => item.Date);
    const values = data.map(item => item.AverageMastery);
    
    charts.learningCurve.data.labels = labels;
    charts.learningCurve.data.datasets[0].data = values;
    
    charts.learningCurve.update();
}

// 5. Cards Added Over Time
function initializeCardsAddedChart(data) {
    const ctx = document.getElementById('cardsAddedChart').getContext('2d');
    
    const labels = data.map(item => item.Date);
    const values = data.map(item => item.CardsAdded);
    
    // Calculate cumulative values
    const cumulativeValues = [];
    let runningTotal = 0;
    values.forEach(val => {
        runningTotal += val;
        cumulativeValues.push(runningTotal);
    });
    
    charts.cardsAdded = new Chart(ctx, {
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
                        }
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
                        }
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
                }
            }
        }
    });
}

function updateCardsAddedChart(data) {
    if (!charts.cardsAdded) {
        initializeCardsAddedChart(data);
        return;
    }
    
    const labels = data.map(item => item.Date);
    const values = data.map(item => item.CardsAdded);
    
    // Calculate cumulative values
    const cumulativeValues = [];
    let runningTotal = 0;
    values.forEach(val => {
        runningTotal += val;
        cumulativeValues.push(runningTotal);
    });
    
    charts.cardsAdded.data.labels = labels;
    charts.cardsAdded.data.datasets[0].data = values;
    charts.cardsAdded.data.datasets[1].data = cumulativeValues;
    
    charts.cardsAdded.update();
}

// 6. View vs Mastery Correlation
function initializeViewMasteryChart(data) {
    const ctx = document.getElementById('viewMasteryChart').getContext('2d');
    
    const values = data.map(item => ({
        x: item.ViewCount,
        y: item.MasteryPercentage,
        question: item.Question
    }));
    
    charts.viewMastery = new Chart(ctx, {
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
                        }
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
                                `Views: ${data.x}, Mastery: ${data.y.toFixed(1)}%`,
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
    if (!charts.viewMastery) {
        initializeViewMasteryChart(data);
        return;
    }
    
    const values = data.map(item => ({
        x: item.ViewCount,
        y: item.MasteryPercentage,
        question: item.Question
    }));
    
    charts.viewMastery.data.datasets[0].data = values;
    
    charts.viewMastery.update();
}

// 7. Interval Growth Distribution
function initializeIntervalGrowthChart(data) {
    const ctx = document.getElementById('intervalGrowthChart').getContext('2d');
    
    // Sort data by interval
    data.sort((a, b) => a.CurrentInterval - b.CurrentInterval);
    
    const labels = data.map(item => item.CurrentInterval + ' days');
    const values = data.map(item => item.CardCount);
    
    charts.intervalGrowth = new Chart(ctx, {
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
                }
            }
        }
    });
}

function updateIntervalGrowthChart(data) {
    if (!charts.intervalGrowth) {
        initializeIntervalGrowthChart(data);
        return;
    }
    
    // Sort data by interval
    data.sort((a, b) => a.CurrentInterval - b.CurrentInterval);
    
    const labels = data.map(item => item.CurrentInterval + ' days');
    const values = data.map(item => item.CardCount);
    
    charts.intervalGrowth.data.labels = labels;
    charts.intervalGrowth.data.datasets[0].data = values;
    
    charts.intervalGrowth.update();
}

// 8. Learning Efficiency
function initializeLearningEfficiencyChart(data) {
    const ctx = document.getElementById('learningEfficiencyChart').getContext('2d');
    
    const values = data.map(item => ({
        x: item.ViewCount,
        y: item.EfficiencyScore,
        question: item.Question
    }));
    
    charts.learningEfficiency = new Chart(ctx, {
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
                        }
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
                                `Views: ${data.x}, Efficiency: ${data.y.toFixed(1)}%`,
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
    if (!charts.learningEfficiency) {
        initializeLearningEfficiencyChart(data);
        return;
    }
    
    const values = data.map(item => ({
        x: item.ViewCount,
        y: item.EfficiencyScore,
        question: item.Question
    }));
    
    charts.learningEfficiency.data.datasets[0].data = values;
    
    charts.learningEfficiency.update();
}

// 9. FSRS Stability Distribution
function initializeStabilityDistributionChart(data) {
    const ctx = document.getElementById('stabilityDistributionChart').getContext('2d');
    
    const labels = data.map(item => item.StabilityRange);
    const values = data.map(item => item.CardCount);
    
    charts.stabilityDistribution = new Chart(ctx, {
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
                            return `Cards: ${context.raw}`;
                        }
                    }
                }
            }
        }
    });
}

function updateStabilityDistributionChart(data) {
    if (!charts.stabilityDistribution) {
        initializeStabilityDistributionChart(data);
        return;
    }
    
    const labels = data.map(item => item.StabilityRange);
    const values = data.map(item => item.CardCount);
    
    charts.stabilityDistribution.data.labels = labels;
    charts.stabilityDistribution.data.datasets[0].data = values;
    
    charts.stabilityDistribution.update();
}