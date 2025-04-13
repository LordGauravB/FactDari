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

// Initialize charts when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Fetch all chart data at once for efficiency
    fetch('/api/chart-data')
        .then(response => response.json())
        .then(data => {
            initializeCategoryDistributionChart(data.categoryDistribution);
            initializeCardsPerCategoryChart(data.categoryDistribution);
            initializeViewMasteryChart(data.viewMasteryCorrelation);
            initializeIntervalGrowthChart(data.intervalGrowth);
            initializeReviewScheduleChart(data.reviewSchedule);
            initializeCardsAddedChart(data.cardsAddedOverTime);
            initializeLearningEfficiencyChart(data.learningEfficiency);
            initializeLearningCurveChart(data.learningCurve);
        })
        .catch(error => console.error('Error fetching chart data:', error));
});

// 1. Category Distribution Pie Chart
function initializeCategoryDistributionChart(data) {
    const ctx = document.getElementById('categoryDistributionChart').getContext('2d');
    
    const labels = data.map(item => item.CategoryName);
    const values = data.map(item => item.CardCount);
    
    new Chart(ctx, {
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

// 2. Cards per Category Bar Chart
function initializeCardsPerCategoryChart(data) {
    const ctx = document.getElementById('cardsPerCategoryChart').getContext('2d');
    
    const labels = data.map(item => item.CategoryName);
    const values = data.map(item => item.CardCount);
    
    new Chart(ctx, {
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
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
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

// 3. View Count vs. Mastery Scatter Plot
function initializeViewMasteryChart(data) {
    const ctx = document.getElementById('viewMasteryChart').getContext('2d');
    
    const scatterData = data.map(item => ({
        x: item.ViewCount,
        y: item.MasteryPercentage,
        label: item.Question
    }));
    
    new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Cards',
                data: scatterData,
                backgroundColor: chartColors[2],
                borderColor: 'rgba(0, 0, 0, 0.1)',
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Mastery Level (%)',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'View Count',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const item = context.raw;
                            let label = item.label || '';
                            if (label.length > 30) {
                                label = label.substr(0, 30) + '...';
                            }
                            return `${label} (Views: ${item.x}, Mastery: ${Math.round(item.y)}%)`;
                        }
                    }
                }
            }
        }
    });
}

// 4. Interval Growth Line Chart
function initializeIntervalGrowthChart(data) {
    const ctx = document.getElementById('intervalGrowthChart').getContext('2d');
    
    const labels = data.map(item => `${item.CurrentInterval} days`);
    const values = data.map(item => item.CardCount);
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Number of Cards',
                data: values,
                fill: false,
                borderColor: chartColors[3],
                tension: 0.1,
                pointBackgroundColor: chartColors[3],
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
                    title: {
                        display: true,
                        text: 'Number of Cards',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
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
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    });
}

// 5. Review Schedule Timeline
function initializeReviewScheduleChart(data) {
    const ctx = document.getElementById('reviewScheduleChart').getContext('2d');
    
    const labels = data.map(item => item.ReviewDate);
    const values = data.map(item => item.CardCount);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Cards Due',
                data: values,
                backgroundColor: chartColors[4],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Cards',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        },
                        maxRotation: 45,
                        minRotation: 45
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// 6. Cards Added Over Time
function initializeCardsAddedChart(data) {
    const ctx = document.getElementById('cardsAddedChart').getContext('2d');
    
    const labels = data.map(item => item.Date);
    const values = data.map(item => item.CardsAdded);
    
    // Calculate cumulative values
    const cumulativeValues = [];
    let sum = 0;
    for (const val of values) {
        sum += val;
        cumulativeValues.push(sum);
    }
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Cards Added',
                    data: values,
                    backgroundColor: chartColors[5],
                    borderColor: chartColors[5],
                    type: 'bar'
                },
                {
                    label: 'Cumulative Total',
                    data: cumulativeValues,
                    borderColor: chartColors[0],
                    backgroundColor: 'transparent',
                    type: 'line',
                    tension: 0.1,
                    pointRadius: 3
                }
            ]
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
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        },
                        maxRotation: 45,
                        minRotation: 45
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// 7. Learning Efficiency Chart
function initializeLearningEfficiencyChart(data) {
    const ctx = document.getElementById('learningEfficiencyChart').getContext('2d');
    
    const scatterData = data.map(item => ({
        x: item.ViewCount,
        y: item.EfficiencyScore,
        label: item.Question
    }));
    
    new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Efficiency Score',
                data: scatterData,
                backgroundColor: chartColors[6],
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Efficiency Score (Mastery % per View)',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'View Count',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const item = context.raw;
                            let label = item.label || '';
                            if (label.length > 30) {
                                label = label.substr(0, 30) + '...';
                            }
                            return `${label} (Views: ${item.x}, Efficiency: ${Math.round(item.y * 100) / 100})`;
                        }
                    }
                }
            }
        }
    });
}

// 8. Learning Curve Line Chart
function initializeLearningCurveChart(data) {
    const ctx = document.getElementById('learningCurveChart').getContext('2d');
    
    const labels = data.map(item => item.Date);
    const values = data.map(item => item.AverageMastery);
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Mastery Level',
                data: values,
                borderColor: chartColors[7],
                backgroundColor: 'rgba(121, 85, 72, 0.1)',
                fill: true,
                tension: 0.3,
                pointBackgroundColor: chartColors[7],
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
                    title: {
                        display: true,
                        text: 'Average Mastery Level (%)',
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    ticks: {
                        color: 'white',
                        font: {
                            family: 'Trebuchet MS'
                        },
                        maxRotation: 45,
                        minRotation: 45
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    });
}