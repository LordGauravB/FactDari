// Enhanced FactDari Analytics JavaScript
(() => {
  'use strict';
  
  const charts = {};
  let refreshInterval = null;
  let countdownInterval = null;
  let isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
  // Store full data globally for modal expansion
  let fullMostReviewedData = [];
  let fullLeastReviewedData = [];
  // Current datasets and sort state for main tables
  let currentMostData = [];
  let currentLeastData = [];
  let mostSortState = { index: 2, dir: 'desc' }; // Reviews desc
  let leastSortState = { index: 2, dir: 'asc' }; // Reviews asc
  let sortHandlersAttached = false;

  function qs(sel) { return document.querySelector(sel); }
  function qsa(sel) { return Array.from(document.querySelectorAll(sel)); }

  async function fetchData() {
    const res = await fetch('/api/chart-data');
    if (!res.ok) throw new Error('Failed to fetch chart data');
    const data = await res.json();
    
    // Fetch ALL facts separately if not included
    if (!data.all_most_reviewed_facts || !data.all_least_reviewed_facts) {
      try {
        // Fetch all facts with a separate request
        const allFactsRes = await fetch('/api/chart-data?all=true');
        if (allFactsRes.ok) {
          const allFactsData = await allFactsRes.json();
          fullMostReviewedData = allFactsData.all_most_reviewed_facts || [];
          fullLeastReviewedData = allFactsData.all_least_reviewed_facts || [];
        } else {
          // Fallback to limited data
          fullMostReviewedData = data.most_reviewed_facts || [];
          fullLeastReviewedData = data.least_reviewed_facts || [];
        }
      } catch (e) {
        // If the endpoint doesn't support all=true, use what we have
        fullMostReviewedData = data.most_reviewed_facts || [];
        fullLeastReviewedData = data.least_reviewed_facts || [];
      }
    } else {
      fullMostReviewedData = data.all_most_reviewed_facts || [];
      fullLeastReviewedData = data.all_least_reviewed_facts || [];
    }
    
    return data;
  }

  // Enable sorting for dynamically created modal tables
  function makeModalTableSortable(table, data, tableType) {
    const thead = table.querySelector('thead');
    const tbody = table.querySelector('tbody');
    if (!thead || !tbody) return;
    let state = { index: 2, dir: tableType === 'most' ? 'desc' : 'asc' };
    const ths = Array.from(thead.querySelectorAll('th'));
    ths.forEach((th, idx) => {
      th.classList.add('sortable');
      th.addEventListener('click', () => {
        const newDir = (state.index === idx && state.dir === 'asc') ? 'desc' : 'asc';
        state = { index: idx, dir: newDir };
        const sorted = sortData(data, idx, newDir, tableType);
        // Re-render rows
        tbody.innerHTML = '';
        sorted.forEach((row, index) => {
          const tr = document.createElement('tr');
          const factContent = row.Content || '';
          let html = '';
          if (tableType === 'most') {
            let medalClass = '';
            if (state.index === 2 && state.dir === 'desc') {
              if (index === 0) medalClass = 'medal-gold';
              else if (index === 1) medalClass = 'medal-silver';
              else if (index === 2) medalClass = 'medal-bronze';
            }
            html = `
              <td><span class="fact-text">${factContent}</span></td>
              <td>${row.CategoryName || ''}</td>
              <td style="text-align: center;" class="${medalClass}">${row.ReviewCount || 0}</td>
            `;
          } else {
            let medalClass = '';
            if (state.index === 2 && state.dir === 'asc') {
              if (index === 0) medalClass = 'medal-gold';
              else if (index === 1) medalClass = 'medal-silver';
              else if (index === 2) medalClass = 'medal-bronze';
            }
            html = `
              <td><span class="fact-text">${factContent}</span></td>
              <td>${row.CategoryName || ''}</td>
              <td style="text-align: center;" class="${medalClass}">${row.ReviewCount || 0}</td>
              <td style="text-align: center;">${row.DaysSinceReview ?? 'N/A'}</td>
            `;
          }
          tr.innerHTML = html;
          tbody.appendChild(tr);
        });
        applySortIndicator(table, idx, newDir);
      });
    });
    applySortIndicator(table, state.index, state.dir);
  }

  function setText(id, text) { const el = qs(id); if (el) el.textContent = text; }

  function updateMetrics(data) {
    const totalFacts = (data.category_distribution?.data || []).reduce((a,b)=>a+b,0);
    const totalCategories = (data.category_distribution?.labels || []).length;
    const today = (()=>{
      const arr = data.reviews_per_day?.datasets?.[0]?.data || [];
      return arr.length ? arr[arr.length-1] : 0;
    })();
    const streak = data.review_streak?.current_streak || 0;
    const favoritesCount = data.favorites_count || 0;

    setText('#total-cards', totalFacts);
    setText('#due-today', today);
    setText('#mastered-cards', `${streak}d`);
    setText('#active-categories', totalCategories);
    setText('#favorites-count', favoritesCount);
  }

  function destroyChart(key) { if (charts[key]) { charts[key].destroy(); charts[key] = null; } }

  function pieChart(key, canvasId, payload) {
    const ctx = qs(`#${canvasId}`).getContext('2d');
    destroyChart(key);
    
    const colors = isDarkMode ? [
      '#60a5fa','#34d399','#fbbf24','#f87171','#a78bfa','#22d3ee','#fb923c','#94a3b8','#4ade80','#fca5a5'
    ] : [
      '#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#f97316','#1e293b','#16a34a','#dc2626'
    ];
    
    charts[key] = new Chart(ctx, {
      type: 'pie',
      data: { 
        labels: payload.labels, 
        datasets: [{ 
          data: payload.data, 
          backgroundColor: colors,
          borderWidth: 2,
          borderColor: isDarkMode ? '#1e293b' : '#ffffff',
          hoverOffset: 8
        }]
      },
      options: { 
        responsive: true,
        maintainAspectRatio: false,
        plugins: { 
          legend: { 
            position: 'bottom',
            labels: {
              padding: 15,
              font: { size: 12 },
              color: isDarkMode ? '#cbd5e1' : '#475569'
            }
          },
          tooltip: {
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            titleColor: isDarkMode ? '#f1f5f9' : '#0f172a',
            bodyColor: isDarkMode ? '#cbd5e1' : '#475569',
            borderColor: isDarkMode ? '#334155' : '#e2e8f0',
            borderWidth: 1,
            padding: 12,
            displayColors: true,
            callbacks: {
              label: function(context) {
                const label = context.label || '';
                const value = context.parsed || 0;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: ${value} (${percentage}%)`;
              }
            }
          }
        },
        animation: {
          animateRotate: true,
          animateScale: true,
          duration: 800
        }
      }
    });
  }

  function doughnutChart(key, canvasId, payload) {
    const ctx = qs(`#${canvasId}`).getContext('2d');
    destroyChart(key);
    
    const colors = isDarkMode ? [
      '#f87171','#fbbf24','#34d399','#60a5fa','#a78bfa'
    ] : [
      '#ef4444','#f59e0b','#10b981','#3b82f6','#8b5cf6'
    ];
    
    charts[key] = new Chart(ctx, {
      type: 'doughnut',
      data: { 
        labels: payload.labels, 
        datasets: [{ 
          data: payload.data, 
          backgroundColor: colors,
          borderWidth: 2,
          borderColor: isDarkMode ? '#1e293b' : '#ffffff',
          hoverOffset: 8
        }]
      },
      options: { 
        responsive: true,
        maintainAspectRatio: false,
        cutout: '60%',
        plugins: { 
          legend: { 
            position: 'bottom',
            labels: {
              padding: 15,
              font: { size: 12 },
              color: isDarkMode ? '#cbd5e1' : '#475569'
            }
          },
          tooltip: {
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            titleColor: isDarkMode ? '#f1f5f9' : '#0f172a',
            bodyColor: isDarkMode ? '#cbd5e1' : '#475569',
            borderColor: isDarkMode ? '#334155' : '#e2e8f0',
            borderWidth: 1,
            padding: 12
          }
        },
        animation: {
          animateRotate: true,
          animateScale: true,
          duration: 800
        }
      }
    });
  }

  function lineChart(key, canvasId, payload) {
    const ctx = qs(`#${canvasId}`).getContext('2d');
    destroyChart(key);
    
    // Enhanced dataset styling
    if (payload.datasets) {
      payload.datasets = payload.datasets.map(dataset => ({
        ...dataset,
        borderColor: isDarkMode ? '#60a5fa' : '#3b82f6',
        backgroundColor: isDarkMode ? 'rgba(96, 165, 250, 0.1)' : 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: isDarkMode ? '#60a5fa' : '#3b82f6',
        pointBorderColor: isDarkMode ? '#1e293b' : '#ffffff',
        pointBorderWidth: 2,
        tension: 0.3,
        fill: true
      }));
    }
    
    charts[key] = new Chart(ctx, {
      type: 'line',
      data: payload,
      options: { 
        responsive: true, 
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        scales: { 
          x: {
            grid: {
              color: isDarkMode ? '#334155' : '#e2e8f0',
              drawBorder: false
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            }
          },
          y: { 
            beginAtZero: true,
            grid: {
              color: isDarkMode ? '#334155' : '#e2e8f0',
              drawBorder: false
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            }
          }
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            titleColor: isDarkMode ? '#f1f5f9' : '#0f172a',
            bodyColor: isDarkMode ? '#cbd5e1' : '#475569',
            borderColor: isDarkMode ? '#334155' : '#e2e8f0',
            borderWidth: 1,
            padding: 12,
            displayColors: false
          }
        },
        animation: {
          duration: 1000,
          easing: 'easeInOutQuart'
        }
      }
    });
  }

  function barChart(key, canvasId, payload, horizontal=false) {
    const ctx = qs(`#${canvasId}`).getContext('2d');
    destroyChart(key);
    
    // Enhanced dataset styling
    if (payload.datasets) {
      payload.datasets = payload.datasets.map((dataset, i) => {
        const colors = isDarkMode ? 
          ['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#a78bfa'] :
          ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
        return {
          ...dataset,
          backgroundColor: colors[i % colors.length],
          borderColor: 'transparent',
          borderRadius: 6,
          barThickness: 'flex',
          maxBarThickness: 40
        };
      });
    }
    
    charts[key] = new Chart(ctx, {
      type: 'bar',
      data: payload,
      options: { 
        responsive: true, 
        maintainAspectRatio: false, 
        indexAxis: horizontal ? 'y' : 'x',
        scales: { 
          x: {
            beginAtZero: horizontal,
            grid: {
              color: isDarkMode ? '#334155' : '#e2e8f0',
              drawBorder: false
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            }
          },
          y: {
            beginAtZero: !horizontal,
            grid: {
              color: isDarkMode ? '#334155' : '#e2e8f0',
              drawBorder: false
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            }
          }
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            titleColor: isDarkMode ? '#f1f5f9' : '#0f172a',
            bodyColor: isDarkMode ? '#cbd5e1' : '#475569',
            borderColor: isDarkMode ? '#334155' : '#e2e8f0',
            borderWidth: 1,
            padding: 12
          }
        },
        animation: {
          duration: 800,
          easing: 'easeInOutQuart'
        }
      }
    });
  }

  // Sorting helpers
  function normalizeValue(val, numeric = false, nullHigh = true) {
    if (val == null) return nullHigh ? Number.POSITIVE_INFINITY : Number.NEGATIVE_INFINITY;
    if (numeric) {
      const n = Number(val);
      return Number.isNaN(n) ? 0 : n;
    }
    return String(val).toLowerCase();
  }

  function sortData(data, colIdx, dir, tableType) {
    const numericColsMost = { 2: true };
    const numericColsLeast = { 2: true, 3: true };
    const isNumeric = tableType === 'most' ? !!numericColsMost[colIdx] : !!numericColsLeast[colIdx];
    const getVal = (row) => {
      switch (colIdx) {
        case 0: return normalizeValue(row.Content, false);
        case 1: return normalizeValue(row.CategoryName, false);
        case 2: return normalizeValue(row.ReviewCount, true);
        case 3: return normalizeValue(row.DaysSinceReview, true);
        default: return 0;
      }
    };
    return [...(data || [])].sort((a, b) => {
      const va = getVal(a), vb = getVal(b);
      if (va < vb) return dir === 'asc' ? -1 : 1;
      if (va > vb) return dir === 'asc' ? 1 : -1;
      return 0;
    });
  }

  function applySortIndicator(table, colIdx, dir) {
    const ths = Array.from(table.querySelectorAll('thead th'));
    ths.forEach((th, i) => {
      th.removeAttribute('aria-sort');
      th.classList.add('sortable');
      if (i === colIdx) th.setAttribute('aria-sort', dir === 'asc' ? 'ascending' : 'descending');
    });
  }

  function renderMostTable(data) {
    const mostTbody = qs('#most-reviewed-table tbody');
    if (!mostTbody) return;
    mostTbody.innerHTML = '';
    const mostToShow = (data || []).slice(0, 10);
    const showMedals = mostSortState.index === 2 && mostSortState.dir === 'desc';
    mostToShow.forEach((row, index) => {
      const tr = document.createElement('tr');
      const factContent = row.Content || '';
      const displayText = factContent.length > 150 ?
        `<span class="fact-text" title="${factContent.replace(/"/g, '&quot;')}">${factContent.substring(0, 150)}...</span>` :
        `<span class="fact-text">${factContent}</span>`;
      let medalClass = '';
      if (showMedals) {
        if (index === 0) medalClass = 'medal-gold';
        else if (index === 1) medalClass = 'medal-silver';
        else if (index === 2) medalClass = 'medal-bronze';
      }
      tr.innerHTML = `
        <td>${displayText}</td>
        <td>${row.CategoryName || ''}</td>
        <td style="text-align: center;" class="${medalClass}">${row.ReviewCount || 0}</td>
      `;
      mostTbody.appendChild(tr);
    });
  }

  function renderLeastTable(data) {
    const leastTbody = qs('#least-reviewed-table tbody');
    if (!leastTbody) return;
    leastTbody.innerHTML = '';
    const leastToShow = (data || []).slice(0, 10);
    const showMedals = leastSortState.index === 2 && leastSortState.dir === 'asc';
    leastToShow.forEach((row, index) => {
      const tr = document.createElement('tr');
      const factContent = row.Content || '';
      const displayText = factContent.length > 150 ?
        `<span class="fact-text" title="${factContent.replace(/"/g, '&quot;')}">${factContent.substring(0, 150)}...</span>` :
        `<span class="fact-text">${factContent}</span>`;
      let medalClass = '';
      if (showMedals) {
        if (index === 0) medalClass = 'medal-gold';
        else if (index === 1) medalClass = 'medal-silver';
        else if (index === 2) medalClass = 'medal-bronze';
      }
      tr.innerHTML = `
        <td>${displayText}</td>
        <td>${row.CategoryName || ''}</td>
        <td style="text-align: center;" class="${medalClass}">${row.ReviewCount || 0}</td>
        <td style="text-align: center;">${row.DaysSinceReview ?? 'N/A'}</td>
      `;
      leastTbody.appendChild(tr);
    });
  }

  function attachTableSortHandlers() {
    const mostTable = qs('#most-reviewed-table');
    const leastTable = qs('#least-reviewed-table');
    if (mostTable && !mostTable.dataset.sortAttached) {
      const ths = Array.from(mostTable.querySelectorAll('thead th'));
      ths.forEach((th, idx) => {
        th.classList.add('sortable');
        th.addEventListener('click', () => {
          const newDir = (mostSortState.index === idx && mostSortState.dir === 'asc') ? 'desc' : 'asc';
          mostSortState = { index: idx, dir: newDir };
          const sorted = sortData(currentMostData, idx, newDir, 'most');
          renderMostTable(sorted);
          applySortIndicator(mostTable, idx, newDir);
        });
      });
      mostTable.dataset.sortAttached = '1';
      applySortIndicator(mostTable, mostSortState.index, mostSortState.dir);
    }
    if (leastTable && !leastTable.dataset.sortAttached) {
      const ths = Array.from(leastTable.querySelectorAll('thead th'));
      ths.forEach((th, idx) => {
        th.classList.add('sortable');
        th.addEventListener('click', () => {
          const newDir = (leastSortState.index === idx && leastSortState.dir === 'asc') ? 'desc' : 'asc';
          leastSortState = { index: idx, dir: newDir };
          const sorted = sortData(currentLeastData, idx, newDir, 'least');
          renderLeastTable(sorted);
          applySortIndicator(leastTable, idx, newDir);
        });
      });
      leastTable.dataset.sortAttached = '1';
      applySortIndicator(leastTable, leastSortState.index, leastSortState.dir);
    }
  }

  function populateTables(most, least) {
    currentMostData = most || [];
    currentLeastData = least || [];
    const sortedMost = sortData(currentMostData, mostSortState.index, mostSortState.dir, 'most');
    const sortedLeast = sortData(currentLeastData, leastSortState.index, leastSortState.dir, 'least');
    renderMostTable(sortedMost);
    renderLeastTable(sortedLeast);
    if (!sortHandlersAttached) {
      attachTableSortHandlers();
      sortHandlersAttached = true;
    } else {
      const mostTable = qs('#most-reviewed-table');
      const leastTable = qs('#least-reviewed-table');
      if (mostTable) applySortIndicator(mostTable, mostSortState.index, mostSortState.dir);
      if (leastTable) applySortIndicator(leastTable, leastSortState.index, leastSortState.dir);
    }
  }

  function renderHeatmap(hm) {
    const container = qs('#review-heatmap');
    if (!container || !hm) return;
    container.innerHTML = '';
    container.appendChild(el('div', { className: 'heatmap-label', text: '' }));
    (hm.hours || []).forEach(h => container.appendChild(el('div', { className: 'heatmap-label', text: String(h) })));
    (hm.days || []).forEach((day, dIdx) => {
      container.appendChild(el('div', { className: 'heatmap-label', text: day.slice(0,3) }));
      for (let h = 0; h < 24; h++) {
        const v = (hm.data?.[dIdx]?.[h]) || 0;
        const intensity = Math.min(v/10, 1);
        const cellClass = v === 0 ? 'heatmap-cell empty' : 'heatmap-cell';
        const cell = el('div', { className: cellClass });
        
        // Enhanced color gradient
        if (v === 0) {
          cell.style.background = isDarkMode ? '#1e293b' : '#f1f5f9';
        } else {
          const baseColor = isDarkMode ? '96, 165, 250' : '59, 130, 246';
          cell.style.background = `rgba(${baseColor}, ${intensity})`;
        }
        
        cell.title = `${day} ${h}:00 - ${v} reviews`;
        if (v > 0) {
          cell.textContent = v;
          cell.style.color = intensity > 0.5 ? '#ffffff' : (isDarkMode ? '#cbd5e1' : '#475569');
        }
        
        container.appendChild(cell);
      }
    });
  }

  function el(tag, { className, text }={}) {
    const e = document.createElement(tag);
    if (className) e.className = className;
    if (text != null) e.textContent = text;
    return e;
  }

  async function load() {
    try {
      showLoadingState();
      const data = await fetchData();
      
      // Update metrics with animation
      updateMetrics(data);
      animateMetrics();
      
      // Render charts with slight delay for smooth transition
      setTimeout(() => {
        pieChart('category_distribution', 'category-distribution', data.category_distribution);
        doughnutChart('review_status', 'review-status', data.review_status);
        lineChart('reviews_per_day', 'reviews-per-day', data.reviews_per_day);
        barChart('facts_timeline', 'facts-timeline', data.facts_added_timeline);
        barChart('category_reviews', 'category-reviews', data.category_reviews, true);
        populateTables(data.most_reviewed_facts, data.least_reviewed_facts);
        renderHeatmap(data.review_heatmap);
      }, 100);
      
      hideLoadingState();
      
      // Show success notification
      showNotification('Data refreshed successfully', 'success');
    } catch (e) {
      console.error('Failed to load data:', e);
      hideLoadingState();
      showNotification('Failed to load data. Please try again.', 'error');
    }
  }
  
  function animateMetrics() {
    qsa('.metric-value').forEach(el => {
      const finalText = el.textContent;
      const isNumber = /^\d+/.test(finalText);
      
      if (isNumber) {
        const finalValue = parseInt(finalText);
        let currentValue = 0;
        const increment = Math.ceil(finalValue / 20);
        const timer = setInterval(() => {
          currentValue += increment;
          if (currentValue >= finalValue) {
            currentValue = finalValue;
            clearInterval(timer);
          }
          el.textContent = finalText.replace(/\d+/, currentValue);
        }, 50);
      }
    });
  }
  
  function showNotification(message, type = 'info') {
    const notification = el('div', { className: `notification notification-${type}` });
    notification.textContent = message;
    notification.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      padding: 12px 20px;
      border-radius: 8px;
      background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
      color: white;
      font-weight: 500;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      z-index: 10000;
      animation: slideInRight 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    setTimeout(() => {
      notification.style.animation = 'slideOutRight 0.3s ease';
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  function setupTabs() {
    qsa('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        qsa('.tab-btn').forEach(b => b.classList.remove('active'));
        qsa('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        const tab = btn.getAttribute('data-tab');
        const panel = qs(`#${tab}-tab`);
        if (panel) panel.classList.add('active');
      });
    });
  }

  
  function setupExpandModal() {
    const modal = qs('#chart-modal');
    const closeBtn = modal?.querySelector('.modal-close');
    const modalCanvas = modal?.querySelector('#modal-chart');
    const modalChartContainer = modal?.querySelector('.modal-chart-container');
    
    qsa('.expand-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const key = btn.getAttribute('data-chart');
        
        // Handle tables and heatmap differently
        if (key === 'most-reviewed-table' || key === 'least-reviewed-table') {
          if (!modal || !modalChartContainer) return;
          modal.style.display = 'flex';
          
          // Create a new table with ALL facts
          const tableContainer = document.createElement('div');
          tableContainer.className = 'table-container';
          tableContainer.style.maxHeight = '65vh';
          tableContainer.style.overflow = 'auto';
          
          const table = document.createElement('table');
          table.className = 'data-table';
          table.id = key;
          
          // Create header
          const thead = document.createElement('thead');
          const headerRow = document.createElement('tr');
          
          if (key === 'most-reviewed-table') {
            headerRow.innerHTML = '<th>Fact</th><th>Category</th><th>Reviews</th>';
            thead.appendChild(headerRow);
            table.appendChild(thead);
            
            // Create body with ALL facts
            const tbody = document.createElement('tbody');
            fullMostReviewedData.forEach((row, index) => {
              const tr = document.createElement('tr');
              const factContent = row.Content || '';
              
              // Add medal class for top 3
              let medalClass = '';
              if (index === 0) medalClass = 'medal-gold';
              else if (index === 1) medalClass = 'medal-silver';
              else if (index === 2) medalClass = 'medal-bronze';
              
              tr.innerHTML = `
                <td><span class="fact-text">${factContent}</span></td>
                <td>${row.CategoryName || ''}</td>
                <td style="text-align: center;" class="${medalClass}">${row.ReviewCount || 0}</td>
              `;
              tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            // Enable sorting in modal for Most Reviewed
            makeModalTableSortable(table, fullMostReviewedData, 'most');
            
          } else {
            headerRow.innerHTML = '<th>Fact</th><th>Category</th><th>Reviews</th><th>Days Since</th>';
            thead.appendChild(headerRow);
            table.appendChild(thead);
            
            // Create body with ALL facts
            const tbody = document.createElement('tbody');
            fullLeastReviewedData.forEach((row, index) => {
              const tr = document.createElement('tr');
              const factContent = row.Content || '';
              
              // Add medal class for top 3
              let medalClass = '';
              if (index === 0) medalClass = 'medal-gold';
              else if (index === 1) medalClass = 'medal-silver';
              else if (index === 2) medalClass = 'medal-bronze';
              
              tr.innerHTML = `
                <td><span class="fact-text">${factContent}</span></td>
                <td>${row.CategoryName || ''}</td>
                <td style="text-align: center;" class="${medalClass}">${row.ReviewCount || 0}</td>
                <td style="text-align: center;">${row.DaysSinceReview ?? 'N/A'}</td>
              `;
              tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            // Enable sorting in modal for Least Reviewed
            makeModalTableSortable(table, fullLeastReviewedData, 'least');
          }
          
          tableContainer.appendChild(table);
          
          modalChartContainer.innerHTML = '';
          modalChartContainer.style.height = 'auto';
          modalChartContainer.appendChild(tableContainer);
          
          // Add a title above the table
          const title = document.createElement('h3');
          title.style.marginBottom = '16px';
          title.style.color = 'var(--text)';
          title.textContent = key === 'most-reviewed-table' 
            ? `All Most Reviewed Facts (${fullMostReviewedData.length} total)` 
            : `All Least Reviewed Facts (${fullLeastReviewedData.length} total)`;
          modalChartContainer.insertBefore(title, tableContainer);
          
        } else if (key === 'review-heatmap-chart') {
          if (!modal || !modalChartContainer) return;
          modal.style.display = 'flex';
          
          // Clone the heatmap for the modal
          const sourceHeatmap = qs('#review-heatmap')?.cloneNode(true);
          if (sourceHeatmap) {
            modalChartContainer.innerHTML = '';
            modalChartContainer.style.height = 'auto';
            modalChartContainer.style.maxHeight = '70vh';
            modalChartContainer.style.overflow = 'auto';
            sourceHeatmap.style.fontSize = '14px';
            sourceHeatmap.style.gap = '4px';
            modalChartContainer.appendChild(sourceHeatmap);
          }
          
        } else {
          // Handle regular charts
          const idMap = {
            'category-distribution': 'category_distribution',
            'review-status': 'review_status',
            'reviews-per-day': 'reviews_per_day',
            'facts-timeline': 'facts_timeline',
            'category-reviews': 'category_reviews',
          };
          const chartRef = charts[idMap[key]];
          if (!chartRef || !modal || !modalChartContainer) return;
          
          modal.style.display = 'flex';
          
          // Clear and recreate canvas
          modalChartContainer.innerHTML = '';
          modalChartContainer.style.height = '60vh';
          modalChartContainer.style.overflow = 'hidden';
          
          const newCanvas = document.createElement('canvas');
          newCanvas.id = 'modal-chart';
          modalChartContainer.appendChild(newCanvas);
          
          // Get context from the new canvas
          const ctx = newCanvas.getContext('2d');
          
          // Destroy any existing modal chart
          if (charts.modal) { 
            charts.modal.destroy(); 
            charts.modal = null; 
          }
          
          // Create the new chart with enhanced options
          const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: chartRef.config.type === 'pie' || chartRef.config.type === 'doughnut' ? 'bottom' : 'top',
                labels: {
                  padding: 15,
                  font: { size: 14 }
                }
              }
            }
          };
          
          // Copy over specific options from original chart
          if (chartRef.config.options) {
            if (chartRef.config.options.plugins) {
              chartOptions.plugins = { ...chartOptions.plugins, ...chartRef.config.options.plugins };
            }
            if (chartRef.config.options.scales) {
              chartOptions.scales = chartRef.config.options.scales;
            }
            if (chartRef.config.options.indexAxis) {
              chartOptions.indexAxis = chartRef.config.options.indexAxis;
            }
          }
          
          charts.modal = new Chart(ctx, {
            type: chartRef.config.type,
            data: JSON.parse(JSON.stringify(chartRef.config.data)), // Deep clone
            options: chartOptions
          });
        }
      });
    });
    
    closeBtn?.addEventListener('click', () => { 
      modal.style.display = 'none'; 
      if (charts.modal) { 
        charts.modal.destroy(); 
        charts.modal = null; 
      }
      // Reset modal container
      if (modalChartContainer) {
        modalChartContainer.innerHTML = '';
        modalChartContainer.style.height = '60vh';
        modalChartContainer.style.overflow = 'hidden';
      }
    });
    
    modal?.addEventListener('click', (e) => { 
      if (e.target === modal) { 
        closeBtn.click(); 
      } 
    });
  }

  function showLoadingState() { qs('#loading-screen')?.classList.remove('hidden'); }
  function hideLoadingState() { qs('#loading-screen')?.classList.add('hidden'); }

  function startCountdown(seconds = 300) {
    const el = qs('#countdown');
    if (countdownInterval) clearInterval(countdownInterval);
    if (refreshInterval) clearInterval(refreshInterval);
    const update = () => {
      const m = Math.floor(seconds/60); const s = seconds%60;
      if (el) el.textContent = `${m}m ${s}s`;
      if (seconds-- <= 0) { load(); seconds = 300; }
    };
    update();
    countdownInterval = setInterval(update, 1000);
    refreshInterval = setInterval(load, 300000);
  }

  // Add theme detection and update
  function updateTheme() {
    isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
    // Re-render charts if they exist
    Object.keys(charts).forEach(key => {
      if (charts[key] && charts[key].config) {
        charts[key].update();
      }
    });
  }
  
  // Add smooth scroll for internal links
  function setupSmoothScroll() {
    qsa('a[href^="#"]').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const target = qs(link.getAttribute('href'));
        if (target) {
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  }
  
  // Add keyboard shortcuts
  function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey || e.metaKey) {
        switch(e.key) {
          case 'r':
            e.preventDefault();
            load();
            startCountdown(300);
            break;
          case '1':
          case '2':
          case '3':
            e.preventDefault();
            const tabIndex = parseInt(e.key) - 1;
            const tabs = qsa('.tab-btn');
            if (tabs[tabIndex]) tabs[tabIndex].click();
            break;
        }
      }
    });
  }
  
  // Add CSS for animations
  function injectAnimationStyles() {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
      }
      .ripple {
        position: absolute;
        border-radius: 50%;
        width: 20px;
        height: 20px;
        background: rgba(255, 255, 255, 0.5);
        animation: rippleEffect 0.6s ease-out;
        pointer-events: none;
      }
      @keyframes rippleEffect {
        to {
          transform: scale(4);
          opacity: 0;
        }
      }
    `;
    document.head.appendChild(style);
  }
  
  document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupExpandModal();
    setupSmoothScroll();
    setupKeyboardShortcuts();
    injectAnimationStyles();
    
    // Theme change listener
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateTheme);
    
    // Refresh button with animation
    const refreshBtn = qs('#refresh-btn');
    refreshBtn?.addEventListener('click', () => {
      refreshBtn.style.animation = 'spin 0.5s ease';
      setTimeout(() => refreshBtn.style.animation = '', 500);
      load();
      startCountdown(300);
    });
    
    // Initial load
    load().then(() => startCountdown(300));
  });
})();
