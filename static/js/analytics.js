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
  let fullFavoriteData = [];
  let fullKnownData = [];
  let sessionsData = [];
  // Recent reviews datasets
  let recentReviewsData50 = [];
  let recentReviewsData500 = [];
  // AI usage datasets
  let aiMostExplainedData = [];
  let aiRecentUsageData = [];
  // Currency settings
  let currentCurrency = 'USD';
  const USD_TO_GBP_RATE = 0.79; // Approximate conversion rate
  let cachedAIData = null; // Store AI data for currency conversion
  // Current datasets and sort state for main tables
  let currentMostData = [];
  let currentLeastData = [];
  let currentFavoriteData = [];
  let currentKnownData = [];
  let mostSortState = { index: 2, dir: 'desc' }; // Reviews desc
  let leastSortState = { index: 2, dir: 'asc' }; // Reviews asc
  let favoriteSortState = { index: 2, dir: 'desc' }; // Reviews desc
  let knownSortState = { index: 2, dir: 'desc' }; // Reviews desc
  let achievementsSortState = { index: 0, dir: 'desc' }; // Status desc (Unlocked first)
  let sortHandlersAttached = false;

  function qs(sel) { return document.querySelector(sel); }
  function qsa(sel) { return Array.from(document.querySelectorAll(sel)); }

  // HTML escape function to prevent XSS attacks
  function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
  }

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
          fullFavoriteData = allFactsData.allFavoriteFacts || [];
          fullKnownData = allFactsData.allKnownFacts || [];
          // Also grab the expanded recent reviews list
          recentReviewsData500 = allFactsData.all_recent_card_reviews || [];
        } else {
          // Fallback to limited data
          fullMostReviewedData = data.most_reviewed_facts || [];
          fullLeastReviewedData = data.least_reviewed_facts || [];
          fullFavoriteData = data.allFavoriteFacts || [];
          fullKnownData = data.allKnownFacts || [];
          recentReviewsData500 = recentReviewsData50 || [];
        }
      } catch (e) {
        // If the endpoint doesn't support all=true, use what we have
        fullMostReviewedData = data.most_reviewed_facts || [];
        fullLeastReviewedData = data.least_reviewed_facts || [];
        fullFavoriteData = data.allFavoriteFacts || [];
        fullKnownData = data.allKnownFacts || [];
        recentReviewsData500 = recentReviewsData50 || [];
      }
    } else {
      fullMostReviewedData = data.all_most_reviewed_facts || [];
      fullLeastReviewedData = data.all_least_reviewed_facts || [];
      fullFavoriteData = data.allFavoriteFacts || [];
      fullKnownData = data.allKnownFacts || [];
      recentReviewsData500 = data.all_recent_card_reviews || [];
    }
    
    // Sessions data for table/modal
    sessionsData = data.recent_sessions || [];
    // Recent reviews data
    recentReviewsData50 = data.recent_card_reviews || [];
    // Populate achievements
    renderAchievementsTable(data.recent_achievements || []);
    renderAllAchievementsTable(data.achievements || []);
    
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
              <td><span class="fact-text">${escapeHtml(factContent)}</span></td>
              <td>${escapeHtml(row.CategoryName || '')}</td>
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
              <td><span class="fact-text">${escapeHtml(factContent)}</span></td>
              <td>${escapeHtml(row.CategoryName || '')}</td>
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
    const knownFactsCount = data.known_facts_count || 0;
    const gamify = data.gamification || {};
    const level = gamify.level || 1;
    const xp = gamify.xp || 0;
    const xpToNext = (gamify.xp_to_next ?? 0);
    const ach = data.achievements_summary || { unlocked: 0, total: 0 };

    setText('#total-cards', totalFacts);
    setText('#due-today', today);
    setText('#mastered-cards', `${streak}d`);
    setText('#active-categories', totalCategories);
    setText('#favorites-count', favoritesCount);
    setText('#known-facts-count', knownFactsCount);

    // Update Lifetime Stats Grid
    const lifetimeStats = data.lifetime_stats || {};
    setText('#lifetime-adds', lifetimeStats.total_adds || 0);
    setText('#lifetime-edits', lifetimeStats.total_edits || 0);
    setText('#lifetime-deletes', lifetimeStats.total_deletes || 0);
    setText('#lifetime-reviews', lifetimeStats.total_reviews || 0);
    setText('#current-streak-value', lifetimeStats.current_streak || 0);
    setText('#longest-streak-value', lifetimeStats.longest_streak || 0);
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
    const showCenterTotal = ['favorite_categories', 'known_categories', 'categories_viewed_today'].includes(key);
    
    const colors = isDarkMode ? [
      '#f87171','#fbbf24','#34d399','#60a5fa','#a78bfa'
    ] : [
      '#ef4444','#f59e0b','#10b981','#3b82f6','#8b5cf6'
    ];

    const centerTotalPlugin = {
      id: `centerTotal-${key}`,
      beforeDraw(chart) {
        if (!showCenterTotal) return;
        const meta = chart.getDatasetMeta(0);
        if (!meta || !meta.data || !meta.data.length) return;
        const total = chart.data.datasets?.[0]?.data?.reduce((a, b) => a + (Number(b) || 0), 0) || 0;
        const { ctx } = chart;
        const { x, y } = meta.data[0];
        ctx.save();
        const fontSize = Math.max(14, Math.min(chart.width, chart.height) / 10);
        ctx.font = `600 ${fontSize}px "Inter", sans-serif`;
        ctx.fillStyle = isDarkMode ? '#e2e8f0' : '#0f172a';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(total, x, y);
        ctx.restore();
      }
    };
    
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
      },
      plugins: [centerTotalPlugin]
    });
  }

  function lineChart(key, canvasId, payload) {
    const ctx = qs(`#${canvasId}`).getContext('2d');
    destroyChart(key);

    const axisTitles = {
      reviews_per_day: { x: 'Date', y: 'Reviews' }
    };
    const titles = axisTitles[key] || {};
    
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
            },
            title: titles.x ? {
              display: true,
              text: titles.x,
              color: isDarkMode ? '#e2e8f0' : '#0f172a',
              padding: { top: 8 }
            } : undefined
          },
          y: { 
            beginAtZero: true,
            grid: {
              color: isDarkMode ? '#334155' : '#e2e8f0',
              drawBorder: false
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            title: titles.y ? {
              display: true,
              text: titles.y,
              color: isDarkMode ? '#e2e8f0' : '#0f172a',
              padding: { bottom: 8 }
            } : undefined
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

    const axisTitles = {
      facts_timeline: { x: 'Date Added', y: 'Facts Added' },
      category_reviews: { x: 'Total Reviews', y: 'Category' },
      category_review_time: { x: 'Avg Review Time (seconds)', y: 'Category' }
    };
    const titles = axisTitles[key] || {};
    
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
            },
            title: titles.x ? {
              display: true,
              text: titles.x,
              color: isDarkMode ? '#e2e8f0' : '#0f172a',
              padding: { top: 8 }
            } : undefined
          },
          y: {
            beginAtZero: !horizontal,
            grid: {
              color: isDarkMode ? '#334155' : '#e2e8f0',
              drawBorder: false
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            title: titles.y ? {
              display: true,
              text: titles.y,
              color: isDarkMode ? '#e2e8f0' : '#0f172a',
              padding: { bottom: 8 }
            } : undefined
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
      const escapedContent = escapeHtml(factContent);
      const displayText = factContent.length > 150 ?
        `<span class="fact-text" title="${escapeHtml(factContent)}">${escapeHtml(factContent.substring(0, 150))}...</span>` :
        `<span class="fact-text">${escapedContent}</span>`;
      let medalClass = '';
      if (showMedals) {
        if (index === 0) medalClass = 'medal-gold';
        else if (index === 1) medalClass = 'medal-silver';
        else if (index === 2) medalClass = 'medal-bronze';
      }
      tr.innerHTML = `
        <td>${displayText}</td>
        <td>${escapeHtml(row.CategoryName || '')}</td>
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
      const escapedContent = escapeHtml(factContent);
      const displayText = factContent.length > 150 ?
        `<span class="fact-text" title="${escapeHtml(factContent)}">${escapeHtml(factContent.substring(0, 150))}...</span>` :
        `<span class="fact-text">${escapedContent}</span>`;
      let medalClass = '';
      if (showMedals) {
        if (index === 0) medalClass = 'medal-gold';
        else if (index === 1) medalClass = 'medal-silver';
        else if (index === 2) medalClass = 'medal-bronze';
      }
      tr.innerHTML = `
        <td>${displayText}</td>
        <td>${escapeHtml(row.CategoryName || '')}</td>
        <td style="text-align: center;" class="${medalClass}">${row.ReviewCount || 0}</td>
        <td style="text-align: center;">${row.DaysSinceReview ?? 'N/A'}</td>
      `;
      leastTbody.appendChild(tr);
    });
  }

  function renderFavoriteTable(data) {
    const favTbody = qs('#favorite-facts-table tbody');
    if (!favTbody) return;
    favTbody.innerHTML = '';
    data.forEach((row, index) => {
      const tr = document.createElement('tr');
      // Show full fact content and allow wrapping
      const factContent = row.Content || '';
      let medalClass = '';
      if (favoriteSortState.index === 2 && favoriteSortState.dir === 'desc') {
        if (index === 0) medalClass = 'medal-gold';
        else if (index === 1) medalClass = 'medal-silver';
        else if (index === 2) medalClass = 'medal-bronze';
      }
      tr.innerHTML = `
        <td><span class="fact-text">${escapeHtml(factContent)}</span></td>
        <td>${escapeHtml(row.CategoryName || '')}</td>
        <td style="text-align: center;" class="${medalClass}">${row.ReviewCount || 0}</td>
        <td style="text-align: center;">${row.DaysSinceReview ?? 'N/A'}</td>
      `;
      favTbody.appendChild(tr);
    });
  }

  function renderSessionsTable(rows) {
    const tbody = qs('#sessions-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    (rows || []).forEach(row => {
      const tr = document.createElement('tr');
      const start = row.StartTime ? new Date(row.StartTime).toLocaleString() : '';
      const duration = row.DurationSeconds ?? '';
      const views = row.Views ?? 0;
      const distinct = row.DistinctFacts ?? 0;
      tr.innerHTML = `
        <td>${start}</td>
        <td style="text-align:center;">${duration}</td>
        <td style="text-align:center;">${views}</td>
        <td style="text-align:center;">${distinct}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderAchievementsTable(rows) {
    const tbody = qs('#achievements-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    (rows || []).forEach(row => {
      const tr = document.createElement('tr');
      const when = row.UnlockDate ? new Date(row.UnlockDate).toLocaleString() : '';
      tr.innerHTML = `
        <td>${escapeHtml(when)}</td>
        <td>${escapeHtml(row.Name || '')}</td>
        <td style="text-align:center;">${row.RewardXP || 0} XP</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderSessionActionsTable(rows) {
    const tbody = qs('#session-actions-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    (rows || []).forEach(r => {
      const tr = document.createElement('tr');
      const start = r.StartTime ? new Date(r.StartTime).toLocaleString() : '';
      tr.innerHTML = `
        <td>${start}</td>
        <td style="text-align:center;">${r.FactsAdded ?? 0}</td>
        <td style="text-align:center;">${r.FactsEdited ?? 0}</td>
        <td style="text-align:center;">${r.FactsDeleted ?? 0}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderRecentReviewsTable(rows) {
    const tbody = qs('#recent-reviews-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    (rows || []).forEach(row => {
      const tr = document.createElement('tr');
      const sessionStart = row.StartTime ? new Date(row.StartTime).toLocaleString() : '';
      const reviewTime = row.ReviewDate ? new Date(row.ReviewDate).toLocaleString() : '';
      const factContent = row.Content || '';
      const displayText = factContent.length > 150 ?
        `<span class="fact-text" title="${escapeHtml(factContent)}">${escapeHtml(factContent.substring(0, 150))}...</span>` :
        `<span class="fact-text">${escapeHtml(factContent)}</span>`;
      tr.innerHTML = `
        <td>${escapeHtml(sessionStart)}</td>
        <td>${escapeHtml(reviewTime)}</td>
        <td>${escapeHtml(row.CategoryName || '')}</td>
        <td>${displayText}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // Store achievements data globally for filtering
  let allAchievementsData = [];
  let currentAchievementFilter = 'all';

  // Category to icon mapping for achievements
  const achievementIcons = {
    'streak': '🔥',
    'review': '📖',
    'favorite': '⭐',
    'known': '✅',
    'category': '📊',
    'session': '⏱️',
    'time': '🕐',
    'milestone': '🏆',
    'explorer': '🧭',
    'master': '🎓',
    'dedication': '💪',
    'speed': '⚡',
    'consistency': '📅',
    'collector': '📚',
    'default': '🏅'
  };

  function getAchievementIcon(category, name) {
    const catLower = (category || '').toLowerCase();
    const nameLower = (name || '').toLowerCase();

    // Check category first
    for (const [key, icon] of Object.entries(achievementIcons)) {
      if (catLower.includes(key)) return icon;
    }

    // Check name as fallback
    for (const [key, icon] of Object.entries(achievementIcons)) {
      if (nameLower.includes(key)) return icon;
    }

    return achievementIcons.default;
  }

  function renderAllAchievementsBadges(rows, filter = 'all') {
    const container = qs('#achievements-badges-container');
    if (!container) return;

    allAchievementsData = Array.isArray(rows) ? rows.slice() : [];
    currentAchievementFilter = filter;

    // Calculate unlocked/locked counts
    const unlockedCount = allAchievementsData.filter(r => r.Unlocked).length;
    const lockedCount = allAchievementsData.filter(r => !r.Unlocked).length;
    const totalCount = allAchievementsData.length;

    // Update the count display
    const countEl = qs('#achievements-count');
    if (countEl) {
      countEl.textContent = `(${unlockedCount}/${totalCount} Unlocked)`;
    }

    // Sort: unlocked first, then by name
    allAchievementsData.sort((a, b) => {
      if (a.Unlocked !== b.Unlocked) {
        return a.Unlocked ? -1 : 1;
      }
      return (a.Name || '').localeCompare(b.Name || '');
    });

    // Filter based on current selection
    let filteredData = allAchievementsData;
    if (filter === 'unlocked') {
      filteredData = allAchievementsData.filter(r => r.Unlocked);
    } else if (filter === 'locked') {
      filteredData = allAchievementsData.filter(r => !r.Unlocked);
    }

    container.innerHTML = '';

    if (filteredData.length === 0) {
      container.innerHTML = `<div style="text-align: center; color: var(--muted); padding: 40px;">
        No ${filter === 'all' ? '' : filter} achievements found
      </div>`;
      return;
    }

    filteredData.forEach(r => {
      const badge = document.createElement('div');
      badge.className = `achievement-badge ${r.Unlocked ? 'unlocked' : 'locked'}`;

      const icon = getAchievementIcon(r.Category, r.Name);
      const progressCurrent = Math.min(r.ProgressCurrent || 0, r.Threshold || 0);
      const threshold = r.Threshold || 0;
      const progressPercent = threshold > 0 ? Math.round((progressCurrent / threshold) * 100) : 0;
      const unlockDate = r.UnlockDate ? new Date(r.UnlockDate).toLocaleDateString() : '';

      let progressBar = '';
      if (!r.Unlocked && threshold > 0) {
        progressBar = `
          <div class="badge-progress">
            <div class="badge-progress-fill" style="width: ${progressPercent}%"></div>
          </div>
        `;
      }

      let dateDisplay = '';
      if (r.Unlocked && unlockDate) {
        dateDisplay = `<div class="badge-date">${unlockDate}</div>`;
      }

      badge.innerHTML = `
        <span class="badge-xp">${r.RewardXP || 0} XP</span>
        <div class="badge-icon">${icon}</div>
        <div class="badge-name">${r.Name || 'Achievement'}</div>
        <div class="badge-category">${r.Category || ''}</div>
        ${progressBar}
        ${dateDisplay}
        <div class="badge-tooltip">
          <div class="badge-tooltip-title">${r.Name || 'Achievement'}</div>
          <div class="badge-tooltip-desc">${r.Description || 'Complete this achievement to earn XP!'}</div>
          <div class="badge-tooltip-meta">
            <span>${r.Category || 'General'}</span>
            <span>${r.RewardXP || 0} XP</span>
          </div>
          ${!r.Unlocked ? `<div class="badge-tooltip-progress">Progress: ${progressCurrent}/${threshold} (${progressPercent}%)</div>` : ''}
          ${r.Unlocked ? `<div class="badge-tooltip-progress" style="color: var(--success);">Unlocked: ${unlockDate}</div>` : ''}
        </div>
      `;

      container.appendChild(badge);
    });

    // Setup filter buttons if not already done
    setupAchievementFilters();
  }

  function setupAchievementFilters() {
    const filterBtns = qsa('.achievement-filter-tabs .filter-btn');
    if (!filterBtns.length) return;

    filterBtns.forEach(btn => {
      if (btn.dataset.filterAttached) return;
      btn.dataset.filterAttached = '1';

      btn.addEventListener('click', () => {
        // Update active state
        filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Re-render with new filter
        const filter = btn.dataset.filter || 'all';
        renderAllAchievementsBadges(allAchievementsData, filter);
      });
    });
  }

  // Keep old function name for backward compatibility
  function renderAllAchievementsTable(rows) {
    renderAllAchievementsBadges(rows, currentAchievementFilter);
  }

  function renderKnownTable(data) {
    const knownTbody = qs('#known-facts-table tbody');
    if (!knownTbody) return;
    knownTbody.innerHTML = '';
    data.forEach((row, index) => {
      const tr = document.createElement('tr');
      // Show full fact content and allow wrapping
      const factContent = row.Content || '';
      let medalClass = '';
      if (knownSortState.index === 2 && knownSortState.dir === 'desc') {
        if (index === 0) medalClass = 'medal-gold';
        else if (index === 1) medalClass = 'medal-silver';
        else if (index === 2) medalClass = 'medal-bronze';
      }
      tr.innerHTML = `
        <td><span class="fact-text">${escapeHtml(factContent)}</span></td>
        <td>${escapeHtml(row.CategoryName || '')}</td>
        <td style="text-align: center;" class="${medalClass}">${row.ReviewCount || 0}</td>
        <td style="text-align: center;">${row.DaysSinceReview ?? 'N/A'}</td>
      `;
      knownTbody.appendChild(tr);
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
    
    // Add sort handlers for favorite facts table
    const favoriteTable = qs('#favorite-facts-table');
    if (favoriteTable && !favoriteTable.dataset.sortAttached) {
      const ths = Array.from(favoriteTable.querySelectorAll('thead th'));
      ths.forEach((th, idx) => {
        th.classList.add('sortable');
        th.addEventListener('click', () => {
          const newDir = (favoriteSortState.index === idx && favoriteSortState.dir === 'asc') ? 'desc' : 'asc';
          favoriteSortState = { index: idx, dir: newDir };
          const sorted = sortData(currentFavoriteData, idx, newDir, 'favorite');
          renderFavoriteTable(sorted);
          applySortIndicator(favoriteTable, idx, newDir);
        });
      });
      favoriteTable.dataset.sortAttached = '1';
      applySortIndicator(favoriteTable, favoriteSortState.index, favoriteSortState.dir);
    }
    
    // Add sort handlers for known facts table
    const knownTable = qs('#known-facts-table');
    if (knownTable && !knownTable.dataset.sortAttached) {
      const ths = Array.from(knownTable.querySelectorAll('thead th'));
      ths.forEach((th, idx) => {
        th.classList.add('sortable');
        th.addEventListener('click', () => {
          const newDir = (knownSortState.index === idx && knownSortState.dir === 'asc') ? 'desc' : 'asc';
          knownSortState = { index: idx, dir: newDir };
          const sorted = sortData(currentKnownData, idx, newDir, 'known');
          renderKnownTable(sorted);
          applySortIndicator(knownTable, idx, newDir);
        });
      });
      knownTable.dataset.sortAttached = '1';
      applySortIndicator(knownTable, knownSortState.index, knownSortState.dir);
    }
  }

  function populateTables(most, least, favorite, known) {
    currentMostData = most || [];
    currentLeastData = least || [];
    currentFavoriteData = favorite || [];
    currentKnownData = known || [];
    
    const sortedMost = sortData(currentMostData, mostSortState.index, mostSortState.dir, 'most');
    const sortedLeast = sortData(currentLeastData, leastSortState.index, leastSortState.dir, 'least');
    const sortedFavorite = sortData(currentFavoriteData, favoriteSortState.index, favoriteSortState.dir, 'favorite');
    const sortedKnown = sortData(currentKnownData, knownSortState.index, knownSortState.dir, 'known');
    
    renderMostTable(sortedMost);
    renderLeastTable(sortedLeast);
    renderFavoriteTable(sortedFavorite);
    renderKnownTable(sortedKnown);
    
    if (!sortHandlersAttached) {
      attachTableSortHandlers();
      sortHandlersAttached = true;
    } else {
      const mostTable = qs('#most-reviewed-table');
      const leastTable = qs('#least-reviewed-table');
      const favoriteTable = qs('#favorite-facts-table');
      const knownTable = qs('#known-facts-table');
      if (mostTable) applySortIndicator(mostTable, mostSortState.index, mostSortState.dir);
      if (leastTable) applySortIndicator(leastTable, leastSortState.index, leastSortState.dir);
      if (favoriteTable) applySortIndicator(favoriteTable, favoriteSortState.index, favoriteSortState.dir);
      if (knownTable) applySortIndicator(knownTable, knownSortState.index, knownSortState.dir);
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
        doughnutChart('favorite_categories', 'favorite-categories', data.favorite_category_distribution);
        doughnutChart('known_categories', 'known-categories', data.known_category_distribution);
        doughnutChart('categories_viewed_today', 'categories-viewed-today', data.categories_viewed_today);
        
        // New Overview charts
        doughnutChart('known_vs_unknown', 'known-vs-unknown', data.known_vs_unknown);
        renderRadarChart('weekly_pattern', 'weekly-pattern', data.weekly_review_pattern);
        renderHorizontalBarChart('top_hours', 'top-hours', data.top_review_hours);
        renderGroupedBarChart('growth_trend', 'growth-trend', data.category_growth_trend);
        
        lineChart('reviews_per_day', 'reviews-per-day', data.reviews_per_day);
        // removed avg view duration chart
        barChart('facts_timeline', 'facts-timeline', data.facts_added_timeline);
        barChart('category_reviews', 'category-reviews', data.category_reviews, true);
        
        // New Progress chart
        renderMonthlyProgress('monthly_progress', 'monthly-progress', data.monthly_progress);
        
        // Duration analytics charts
        renderDurationStats(data.session_duration_stats, data.avg_review_time_per_fact, data.avg_facts_per_session, data.best_efficiency);
        pieChart('session_duration_distribution', 'session-duration-distribution', data.session_duration_distribution);
        renderDurationLineChart('daily_session_duration', 'daily-session-duration', data.daily_session_duration);
        barChart('category_review_time', 'category-review-time', data.category_review_time, true);
        renderSessionEfficiencyTable(data.session_efficiency);
        renderTimeoutChart('timeout_analysis', 'timeout-analysis', data.timeout_analysis);
        // Session actions (Add/Edit/Delete)
        renderGroupedBarChart('session_actions', 'session-actions-chart', data.session_actions_chart);
        
        populateTables(data.most_reviewed_facts, data.least_reviewed_facts, data.allFavoriteFacts, data.allKnownFacts);
        renderHeatmap(data.review_heatmap);
        renderSessionsTable(sessionsData);
        renderRecentReviewsTable(recentReviewsData50);
        renderSessionActionsTable(data.session_actions_table || []);

        // AI Usage Analytics
        renderAIUsageMetrics(data.ai_usage_summary);
        renderAICostTimeline('ai_cost_timeline', 'ai-cost-timeline', data.ai_cost_timeline);
        doughnutChart('ai_token_distribution', 'ai-token-distribution', data.ai_token_distribution);
        pieChart('ai_usage_by_category', 'ai-usage-by-category', data.ai_usage_by_category);
        pieChart('ai_latency_distribution', 'ai-latency-distribution', data.ai_latency_distribution);
        renderAIUsageTrend('ai_usage_trend', 'ai-usage-trend', data.ai_cost_timeline);
        renderAIMostExplainedTable(data.ai_most_explained_facts);
        renderAIRecentUsageTable(data.ai_recent_usage);
        renderAIProviderComparisonTable(data.ai_provider_comparison);

        // New analytics charts
        renderCategoryCompletionRate('category_completion_rate', 'category-completion-rate', data.category_completion_rate);
        renderLearningVelocity('learning_velocity', 'learning-velocity', data.learning_velocity);
        renderPeakProductivity('peak_productivity', 'peak-productivity', data.peak_productivity_times);
        pieChart('action_breakdown', 'action-breakdown', data.action_breakdown);

        // Update XP progress bar
        updateXPProgressBar(data.gamification);
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
        if (key === 'most-reviewed-table' || key === 'least-reviewed-table' ||
            key === 'favorite-facts-table' || key === 'known-facts-table' ||
            key === 'ai-most-explained-table' || key === 'ai-usage-log-table' ||
            key === 'ai-provider-comparison' || key === 'session-actions-table' ||
            key === 'achievements-table') {
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
                <td><span class="fact-text">${escapeHtml(factContent)}</span></td>
                <td>${escapeHtml(row.CategoryName || '')}</td>
                <td style="text-align: center;" class="${medalClass}">${row.ReviewCount || 0}</td>
              `;
              tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            // Enable sorting in modal for Most Reviewed
            makeModalTableSortable(table, fullMostReviewedData, 'most');

          } else if (key === 'least-reviewed-table') {
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
                <td><span class="fact-text">${escapeHtml(factContent)}</span></td>
                <td>${escapeHtml(row.CategoryName || '')}</td>
                <td style="text-align: center;" class="${medalClass}">${row.ReviewCount || 0}</td>
                <td style="text-align: center;">${row.DaysSinceReview ?? 'N/A'}</td>
              `;
              tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            // Enable sorting in modal for Least Reviewed
            makeModalTableSortable(table, fullLeastReviewedData, 'least');

          } else if (key === 'favorite-facts-table') {
            headerRow.innerHTML = '<th>Fact</th><th>Category</th><th>Reviews</th><th>Days Since</th>';
            thead.appendChild(headerRow);
            table.appendChild(thead);

            // Create body with ALL favorite facts
            const tbody = document.createElement('tbody');
            fullFavoriteData.forEach((row, index) => {
              const tr = document.createElement('tr');
              const factContent = row.Content || '';

              // Add medal class for top 3
              let medalClass = '';
              if (index === 0) medalClass = 'medal-gold';
              else if (index === 1) medalClass = 'medal-silver';
              else if (index === 2) medalClass = 'medal-bronze';

              tr.innerHTML = `
                <td><span class="fact-text">${escapeHtml(factContent)}</span></td>
                <td>${escapeHtml(row.CategoryName || '')}</td>
                <td style="text-align: center;" class="${medalClass}">${row.ReviewCount || 0}</td>
                <td style="text-align: center;">${row.DaysSinceReview ?? 'N/A'}</td>
              `;
              tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            // Enable sorting in modal for Favorite Facts
            makeModalTableSortable(table, fullFavoriteData, 'favorite');

          } else if (key === 'known-facts-table') {
            headerRow.innerHTML = '<th>Fact</th><th>Category</th><th>Reviews</th><th>Days Since</th>';
            thead.appendChild(headerRow);
            table.appendChild(thead);

            // Create body with ALL known facts
            const tbody = document.createElement('tbody');
            fullKnownData.forEach((row, index) => {
              const tr = document.createElement('tr');
              const factContent = row.Content || '';

              // Add medal class for top 3
              let medalClass = '';
              if (index === 0) medalClass = 'medal-gold';
              else if (index === 1) medalClass = 'medal-silver';
              else if (index === 2) medalClass = 'medal-bronze';

              tr.innerHTML = `
                <td><span class="fact-text">${escapeHtml(factContent)}</span></td>
                <td>${escapeHtml(row.CategoryName || '')}</td>
                <td style="text-align: center;" class="${medalClass}">${row.ReviewCount || 0}</td>
                <td style="text-align: center;">${row.DaysSinceReview ?? 'N/A'}</td>
              `;
              tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            // Enable sorting in modal for Known Facts
            makeModalTableSortable(table, fullKnownData, 'known');

          } else if (key === 'ai-most-explained-table') {
            headerRow.innerHTML = '<th>Fact</th><th>Category</th><th>AI Calls</th><th>Total Cost</th>';
            thead.appendChild(headerRow);
            table.appendChild(thead);

            const tbody = document.createElement('tbody');
            aiMostExplainedData.forEach((row, index) => {
              const tr = document.createElement('tr');
              const factContent = row.Content || '';
              const cost = parseFloat(row.TotalCost || 0);

              let medalClass = '';
              if (index === 0) medalClass = 'medal-gold';
              else if (index === 1) medalClass = 'medal-silver';
              else if (index === 2) medalClass = 'medal-bronze';

              tr.innerHTML = `
                <td><span class="fact-text">${escapeHtml(factContent)}</span></td>
                <td>${escapeHtml(row.CategoryName || '')}</td>
                <td style="text-align: center;" class="${medalClass}">${row.CallCount || 0}</td>
                <td style="text-align: center;">$${cost.toFixed(4)}</td>
              `;
              tbody.appendChild(tr);
            });
            table.appendChild(tbody);

          } else if (key === 'ai-usage-log-table') {
            headerRow.innerHTML = '<th>Time</th><th>Fact</th><th>Tokens</th><th>Cost</th><th>Latency</th><th>Status</th><th>Model</th>';
            thead.appendChild(headerRow);
            table.appendChild(thead);

            const tbody = document.createElement('tbody');
            aiRecentUsageData.forEach(row => {
              const tr = document.createElement('tr');
              const time = row.CreatedAt ? new Date(row.CreatedAt).toLocaleString() : '';
              const factContent = row.FactContent || '';
              const cost = parseFloat(row.Cost || 0);
              const latency = row.LatencyMs || 0;
              const status = row.Status || 'UNKNOWN';
              const statusClass = status === 'SUCCESS' ? 'status-success' : 'status-failed';
              const model = row.Model || '--';

              tr.innerHTML = `
                <td>${escapeHtml(time)}</td>
                <td><span class="fact-text">${escapeHtml(factContent)}</span></td>
                <td style="text-align: center;">${row.TotalTokens || 0}</td>
                <td style="text-align: center;">$${cost.toFixed(7)}</td>
                <td style="text-align: center;">${latency}ms</td>
                <td style="text-align: center;"><span class="${statusClass}">${escapeHtml(status)}</span></td>
                <td style="text-align: center;">${escapeHtml(model)}</td>
              `;
              tbody.appendChild(tr);
            });
            table.appendChild(tbody);

          } else if (key === 'ai-provider-comparison') {
            headerRow.innerHTML = '<th>Provider</th><th>Calls</th><th>Total Cost</th><th>Avg Cost</th><th>Avg Latency</th><th>Success Rate</th>';
            thead.appendChild(headerRow);
            table.appendChild(thead);

            const tbody = document.createElement('tbody');
            const providerData = qs('#ai-provider-comparison-table tbody');
            if (providerData) {
              tbody.innerHTML = providerData.innerHTML;
            }
            table.appendChild(tbody);

          } else if (key === 'session-actions-table') {
            headerRow.innerHTML = '<th>Time</th><th>Fact</th><th>Action</th><th>Category</th>';
            thead.appendChild(headerRow);
            table.appendChild(thead);

            const tbody = document.createElement('tbody');
            const actionsData = qs('#session-actions-table tbody');
            if (actionsData) {
              tbody.innerHTML = actionsData.innerHTML;
            }
            table.appendChild(tbody);

          } else if (key === 'achievements-table') {
            headerRow.innerHTML = '<th>When</th><th>Achievement</th><th>Reward</th>';
            thead.appendChild(headerRow);
            table.appendChild(thead);

            const tbody = document.createElement('tbody');
            const achievementsData = qs('#achievements-table tbody');
            if (achievementsData) {
              tbody.innerHTML = achievementsData.innerHTML;
            }
            table.appendChild(tbody);
          }

          tableContainer.appendChild(table);
          
          modalChartContainer.innerHTML = '';
          modalChartContainer.style.height = 'auto';
          modalChartContainer.appendChild(tableContainer);
          
          // Add a title above the table
          const title = document.createElement('h3');
          title.style.marginBottom = '16px';
          title.style.color = 'var(--text)';
          if (key === 'most-reviewed-table') {
            title.textContent = `All Most Reviewed Facts (${fullMostReviewedData.length} total)`;
          } else if (key === 'least-reviewed-table') {
            title.textContent = `All Least Reviewed Facts (${fullLeastReviewedData.length} total)`;
          } else if (key === 'favorite-facts-table') {
            title.textContent = `All Favorite Facts (${fullFavoriteData.length} total)`;
          } else if (key === 'known-facts-table') {
            title.textContent = `All Known Facts (${fullKnownData.length} total)`;
          } else if (key === 'ai-most-explained-table') {
            title.textContent = `Most Explained Facts by AI (${aiMostExplainedData.length} total)`;
          } else if (key === 'ai-usage-log-table') {
            title.textContent = `Recent AI Usage Log (${aiRecentUsageData.length} entries)`;
          } else if (key === 'ai-provider-comparison') {
            title.textContent = 'AI Provider Comparison';
          } else if (key === 'session-actions-table') {
            title.textContent = 'Recent Session Actions';
          } else if (key === 'achievements-table') {
            title.textContent = 'Recent Achievements';
          }
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
          
        } else if (key === 'sessions-table') {
          if (!modal || !modalChartContainer) return;
          modal.style.display = 'flex';
          modalChartContainer.innerHTML = '';
          modalChartContainer.style.height = 'auto';
          
          const tableContainer = document.createElement('div');
          tableContainer.className = 'table-container';
          const table = document.createElement('table');
          table.className = 'data-table';
          const thead = document.createElement('thead');
          thead.innerHTML = `
            <tr>
              <th>Start Time</th>
              <th>Duration (s)</th>
              <th>Views</th>
              <th>Distinct Facts</th>
            </tr>
          `;
          table.appendChild(thead);
          const tbody = document.createElement('tbody');
          (sessionsData || []).forEach(row => {
            const tr = document.createElement('tr');
            const start = row.StartTime ? new Date(row.StartTime).toLocaleString() : '';
            tr.innerHTML = `
              <td>${start}</td>
              <td style="text-align:center;">${row.DurationSeconds ?? ''}</td>
              <td style="text-align:center;">${row.Views ?? 0}</td>
              <td style="text-align:center;">${row.DistinctFacts ?? 0}</td>
            `;
            tbody.appendChild(tr);
          });
          table.appendChild(tbody);
          tableContainer.appendChild(table);
          modalChartContainer.appendChild(tableContainer);
        } else {
          // Handle regular charts (only when a valid chart id is mapped)
          const idMap = {
            'category-distribution': 'category_distribution',
            'favorite-categories': 'favorite_categories',
            'known-categories': 'known_categories',
            'categories-viewed-today': 'categories_viewed_today',
            'reviews-per-day': 'reviews_per_day',
            'facts-timeline': 'facts_timeline',
            'category-reviews': 'category_reviews',
            'session-duration-distribution': 'session_duration_distribution',
            'daily-session-duration': 'daily_session_duration',
            'category-review-time': 'category_review_time',
            'timeout-analysis': 'timeout_analysis',
            'known-vs-unknown': 'known_vs_unknown',
            'weekly-pattern': 'weekly_pattern',
            'top-hours': 'top_hours',
            'growth-trend': 'growth_trend',
            'monthly-progress': 'monthly_progress',
            'session-actions-chart': 'session_actions',
            'ai-cost-timeline': 'ai_cost_timeline',
            'ai-token-distribution': 'ai_token_distribution',
            'ai-usage-by-category': 'ai_usage_by_category',
            'ai-latency-distribution': 'ai_latency_distribution',
            'ai-usage-trend': 'ai_usage_trend',
            'category-completion-rate': 'category_completion_rate',
            'learning-velocity': 'learning_velocity',
            'peak-productivity': 'peak_productivity',
            'action-breakdown': 'action_breakdown'
          };
          const chartKey = idMap[key];
          if (chartKey) {
            const chartRef = charts[chartKey];
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
        }
        
        // Session efficiency table expansion
        if (key === 'session-efficiency-table') {
          if (!modal || !modalChartContainer) return;
          modal.style.display = 'flex';
          modalChartContainer.innerHTML = '';
          modalChartContainer.style.height = 'auto';
          
          const tableContainer = document.createElement('div');
          tableContainer.className = 'table-container';
          const table = document.createElement('table');
          table.className = 'data-table';
          const thead = document.createElement('thead');
          thead.innerHTML = `
            <tr>
              <th>Start Time</th>
              <th>Duration (min)</th>
              <th>Unique Facts</th>
              <th>Total Reviews</th>
              <th>Facts/min</th>
              <th>Reviews/min</th>
            </tr>
          `;
          table.appendChild(thead);
          const tbody = document.createElement('tbody');
          
          // Get session efficiency data from the page
          const existingRows = document.querySelectorAll('#session-efficiency-table tbody tr');
          existingRows.forEach(row => {
            tbody.appendChild(row.cloneNode(true));
          });
          
          table.appendChild(tbody);
          tableContainer.appendChild(table);
          modalChartContainer.appendChild(tableContainer);
        }
        
        // Sessions table expansion
        if (key === 'sessions-table') {
          if (!modal || !modalChartContainer) return;
          modal.style.display = 'flex';
          modalChartContainer.innerHTML = '';
          modalChartContainer.style.height = 'auto';
          
          const tableContainer = document.createElement('div');
          tableContainer.className = 'table-container';
          const table = document.createElement('table');
          table.className = 'data-table';
          const thead = document.createElement('thead');
          thead.innerHTML = `
            <tr>
              <th>Start Time</th>
              <th>Duration (s)</th>
              <th>Views</th>
              <th>Distinct Facts</th>
            </tr>
          `;
          table.appendChild(thead);
          const tbody = document.createElement('tbody');
          (sessionsData || []).forEach(row => {
            const tr = document.createElement('tr');
            const start = row.StartTime ? new Date(row.StartTime).toLocaleString() : '';
            tr.innerHTML = `
              <td>${start}</td>
              <td style="text-align:center;">${row.DurationSeconds ?? ''}</td>
              <td style="text-align:center;">${row.Views ?? 0}</td>
              <td style="text-align:center;">${row.DistinctFacts ?? 0}</td>
            `;
            tbody.appendChild(tr);
          });
          table.appendChild(tbody);
          tableContainer.appendChild(table);
          modalChartContainer.appendChild(tableContainer);
        }

        // Recent Reviews table expansion (show last 500)
        if (key === 'recent-reviews-table') {
          if (!modal || !modalChartContainer) return;
          modal.style.display = 'flex';
          modalChartContainer.innerHTML = '';
          modalChartContainer.style.height = 'auto';

          const tableContainer = document.createElement('div');
          tableContainer.className = 'table-container';
          const table = document.createElement('table');
          table.className = 'data-table';
          const thead = document.createElement('thead');
          thead.innerHTML = `
            <tr>
              <th>Session Start</th>
              <th>Review Time</th>
              <th>Category</th>
              <th>Fact</th>
            </tr>
          `;
          table.appendChild(thead);
          const tbody = document.createElement('tbody');
          const rows = (recentReviewsData500 && recentReviewsData500.length) ? recentReviewsData500 : recentReviewsData50;
          (rows || []).forEach(row => {
            const tr = document.createElement('tr');
            const sessionStart = row.StartTime ? new Date(row.StartTime).toLocaleString() : '';
            const reviewTime = row.ReviewDate ? new Date(row.ReviewDate).toLocaleString() : '';
            const factContent = row.Content || '';
            const displayText = factContent.length > 200 ?
              `<span class="fact-text" title="${escapeHtml(factContent)}">${escapeHtml(factContent.substring(0, 200))}...</span>` :
              `<span class="fact-text">${escapeHtml(factContent)}</span>`;
            tr.innerHTML = `
              <td>${escapeHtml(sessionStart)}</td>
              <td>${escapeHtml(reviewTime)}</td>
              <td>${escapeHtml(row.CategoryName || '')}</td>
              <td>${displayText}</td>
            `;
            tbody.appendChild(tr);
          });
          table.appendChild(tbody);
          tableContainer.appendChild(table);
          modalChartContainer.appendChild(tableContainer);
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
          case '4':
          case '5':
          case '6':
            e.preventDefault();
            const tabIndex = parseInt(e.key) - 1;
            const tabs = qsa('.tab-btn');
            if (tabs[tabIndex]) tabs[tabIndex].click();
            break;
        }
      }
    });
  }
  
  // Render duration statistics
  function renderDurationStats(sessionStats, reviewTimeStats, avgFactsPerSession, bestEfficiency) {
    if (sessionStats) {
      const avgSession = sessionStats.AvgDuration ? Math.round(sessionStats.AvgDuration / 60) : 0;
      const totalTime = sessionStats.TotalDuration ? Math.round(sessionStats.TotalDuration / 3600) : 0;
      const maxSession = sessionStats.MaxDuration ? Math.round(sessionStats.MaxDuration / 60) : 0;
      const totalSessions = sessionStats.SessionCount || 0;
      
      const avgEl = qs('#avg-session-duration');
      const totalEl = qs('#total-session-time');
      const maxEl = qs('#max-session-duration');
      const sessionsEl = qs('#total-sessions');
      
      if (avgEl) avgEl.textContent = `${avgSession} min`;
      if (totalEl) totalEl.textContent = `${totalTime} hrs`;
      if (maxEl) maxEl.textContent = `${maxSession} min`;
      if (sessionsEl) sessionsEl.textContent = totalSessions;
    }
    
    // Add new metrics
    if (avgFactsPerSession && avgFactsPerSession.AvgFactsPerSession !== undefined) {
      const avgFactsEl = qs('#avg-facts-per-session');
      if (avgFactsEl) {
        avgFactsEl.textContent = Math.round(avgFactsPerSession.AvgFactsPerSession);
      }
    }
    
    if (bestEfficiency && bestEfficiency.BestFactsPerMinute !== undefined) {
      const bestEffEl = qs('#best-efficiency');
      if (bestEffEl) {
        bestEffEl.textContent = `${bestEfficiency.BestFactsPerMinute}/min`;
      }
    }
    
    if (reviewTimeStats) {
      const avgTime = reviewTimeStats.AvgTimePerReview || 0;
      const minTime = reviewTimeStats.MinTimePerReview || 0;
      const maxTime = reviewTimeStats.MaxTimePerReview || 0;
      
      const avgReviewEl = qs('#avg-review-time');
      const minReviewEl = qs('#min-review-time');
      const maxReviewEl = qs('#max-review-time');
      
      if (avgReviewEl) avgReviewEl.textContent = `${avgTime}s`;
      if (minReviewEl) minReviewEl.textContent = `${minTime}s`;
      if (maxReviewEl) maxReviewEl.textContent = `${maxTime}s`;
    }
  }
  
  // Render duration line chart with multiple Y axes
  function renderDurationLineChart(key, elementId, payload) {
    const canvas = qs(`#${elementId}`);
    if (!canvas || !payload) return;
    const ctx = canvas.getContext('2d');
    
    if (charts[key]) {
      charts[key].destroy();
    }
    
    charts[key] = new Chart(ctx, {
      type: 'line',
      data: payload,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        scales: {
          x: {
            display: true,
            grid: {
              color: isDarkMode ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            title: {
              display: true,
              text: 'Date',
              color: isDarkMode ? '#e2e8f0' : '#0f172a',
              padding: { top: 8 }
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: 'Duration (minutes)',
              color: isDarkMode ? '#e2e8f0' : '#0f172a'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            grid: {
              color: isDarkMode ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            title: {
              display: true,
              text: 'Session Count',
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            grid: {
              drawOnChartArea: false,
            }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              color: isDarkMode ? '#f1f5f9' : '#0f172a',
              usePointStyle: true
            }
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            titleColor: isDarkMode ? '#f1f5f9' : '#0f172a',
            bodyColor: isDarkMode ? '#cbd5e1' : '#475569',
            borderColor: isDarkMode ? '#334155' : '#e2e8f0',
            borderWidth: 1
          }
        }
      }
    });
  }
  
  // Render session efficiency table
  function renderSessionEfficiencyTable(sessions) {
    const tbody = qs('#session-efficiency-table tbody');
    if (!tbody || !sessions) return;
    
    tbody.innerHTML = '';
    sessions.forEach(session => {
      const tr = document.createElement('tr');
      const startTime = session.StartTime ? new Date(session.StartTime).toLocaleString() : '';
      const duration = session.DurationSeconds ? Math.round(session.DurationSeconds / 60) : 0;
      
      tr.innerHTML = `
        <td>${startTime}</td>
        <td>${duration}</td>
        <td>${session.UniqueFactsReviewed || 0}</td>
        <td>${session.TotalReviews || 0}</td>
        <td>${session.FactsPerMinute || 0}</td>
        <td>${session.ReviewsPerMinute || 0}</td>
      `;
      tbody.appendChild(tr);
    });
  }
  
  // Render timeout analysis chart
  function renderTimeoutChart(key, elementId, payload) {
    const canvas = qs(`#${elementId}`);
    if (!canvas || !payload) return;
    const ctx = canvas.getContext('2d');
    
    if (charts[key]) {
      charts[key].destroy();
    }
    
    charts[key] = new Chart(ctx, {
      type: 'bar',
      data: payload,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        scales: {
          x: {
            display: true,
            grid: {
              color: isDarkMode ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            title: {
              display: true,
              text: 'Date',
              color: isDarkMode ? '#e2e8f0' : '#0f172a',
              padding: { top: 8 }
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: 'Timeout Count',
              color: isDarkMode ? '#e2e8f0' : '#0f172a'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            grid: {
              color: isDarkMode ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            title: {
              display: true,
              text: 'Timeout Percentage (%)',
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            grid: {
              drawOnChartArea: false,
            }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              color: isDarkMode ? '#f1f5f9' : '#0f172a',
              usePointStyle: true
            }
          },
          tooltip: {
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            titleColor: isDarkMode ? '#f1f5f9' : '#0f172a',
            bodyColor: isDarkMode ? '#cbd5e1' : '#475569',
            borderColor: isDarkMode ? '#334155' : '#e2e8f0',
            borderWidth: 1
          }
        }
      }
    });
  }
  
  // Render Radar Chart
  function renderRadarChart(key, elementId, payload) {
    const canvas = qs(`#${elementId}`);
    if (!canvas || !payload) return;
    const ctx = canvas.getContext('2d');
    
    if (charts[key]) {
      charts[key].destroy();
    }
    
    charts[key] = new Chart(ctx, {
      type: 'radar',
      data: payload,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            beginAtZero: true,
            grid: {
              color: isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            pointLabels: {
              color: isDarkMode ? '#f1f5f9' : '#0f172a',
              font: {
                size: 11
              }
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
            borderWidth: 1
          }
        }
      }
    });
  }
  
  // Render Horizontal Bar Chart
  function renderHorizontalBarChart(key, elementId, payload) {
    const canvas = qs(`#${elementId}`);
    if (!canvas || !payload) return;
    const ctx = canvas.getContext('2d');

    const axisTitles = {
      top_hours: { x: 'Review Count', y: 'Hour of Day' }
    };
    const titles = axisTitles[key] || {};
    
    if (charts[key]) {
      charts[key].destroy();
    }
    
    charts[key] = new Chart(ctx, {
      type: 'bar',
      data: payload,
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            titleColor: isDarkMode ? '#f1f5f9' : '#0f172a',
            bodyColor: isDarkMode ? '#cbd5e1' : '#475569',
            borderColor: isDarkMode ? '#334155' : '#e2e8f0',
            borderWidth: 1
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            grid: {
              color: isDarkMode ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            title: titles.x ? {
              display: true,
              text: titles.x,
              color: isDarkMode ? '#e2e8f0' : '#0f172a',
              padding: { top: 8 }
            } : undefined
          },
          y: {
            grid: {
              display: false
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b',
              font: {
                size: 11
              }
            },
            title: titles.y ? {
              display: true,
              text: titles.y,
              color: isDarkMode ? '#e2e8f0' : '#0f172a',
              padding: { bottom: 8 }
            } : undefined
          }
        }
      }
    });
  }
  
  // Render Grouped Bar Chart
  function renderGroupedBarChart(key, elementId, payload) {
    const canvas = qs(`#${elementId}`);
    if (!canvas || !payload) return;
    const ctx = canvas.getContext('2d');

    const axisTitles = {
      session_actions: { x: 'Session (oldest → newest)', y: 'Count' },
      growth_trend: { x: 'Category', y: 'Total Facts (Lifetime)' }
    };
    const titles = axisTitles[key] || {};
    
    if (charts[key]) {
      charts[key].destroy();
    }
    
    charts[key] = new Chart(ctx, {
      type: 'bar',
      data: payload,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              color: isDarkMode ? '#f1f5f9' : '#0f172a',
              usePointStyle: true
            }
          },
          tooltip: {
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            titleColor: isDarkMode ? '#f1f5f9' : '#0f172a',
            bodyColor: isDarkMode ? '#cbd5e1' : '#475569',
            borderColor: isDarkMode ? '#334155' : '#e2e8f0',
            borderWidth: 1
          }
        },
        scales: {
          x: {
            grid: {
              color: isDarkMode ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b',
              maxRotation: 45,
              minRotation: 45
            },
            title: titles.x ? {
              display: true,
              text: titles.x,
              color: isDarkMode ? '#e2e8f0' : '#0f172a',
              padding: { top: 8 }
            } : undefined
          },
          y: {
            beginAtZero: true,
            grid: {
              color: isDarkMode ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            title: titles.y ? {
              display: true,
              text: titles.y,
              color: isDarkMode ? '#e2e8f0' : '#0f172a',
              padding: { bottom: 8 }
            } : undefined
          }
        }
      }
    });
  }
  
  // Render Monthly Progress Chart
  function renderMonthlyProgress(key, elementId, payload) {
    const canvas = qs(`#${elementId}`);
    if (!canvas || !payload) return;
    const ctx = canvas.getContext('2d');
    
    if (charts[key]) {
      charts[key].destroy();
    }
    
    charts[key] = new Chart(ctx, {
      type: 'bar',
      data: payload,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        scales: {
          x: {
            grid: {
              color: isDarkMode ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            title: {
              display: true,
              text: 'Month (last 6 months)',
              color: isDarkMode ? '#e2e8f0' : '#0f172a',
              padding: { top: 8 }
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: 'Reviews / Facts',
              color: isDarkMode ? '#e2e8f0' : '#0f172a'
            },
            grid: {
              color: isDarkMode ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            title: {
              display: true,
              text: 'Active Days',
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            grid: {
              drawOnChartArea: false,
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              color: isDarkMode ? '#f1f5f9' : '#0f172a',
              usePointStyle: true
            }
          },
          tooltip: {
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            titleColor: isDarkMode ? '#f1f5f9' : '#0f172a',
            bodyColor: isDarkMode ? '#cbd5e1' : '#475569',
            borderColor: isDarkMode ? '#334155' : '#e2e8f0',
            borderWidth: 1
          }
        }
      }
    });
  }
  
  // Currency conversion helper
  function convertCurrency(amountUSD, toCurrency) {
    if (toCurrency === 'GBP') {
      return amountUSD * USD_TO_GBP_RATE;
    }
    return amountUSD;
  }

  function formatCurrency(amount, currency) {
    const symbol = currency === 'GBP' ? '£' : '$';
    return `${symbol}${amount.toFixed(4)}`;
  }

  // AI Usage Analytics Functions
  function renderAIUsageMetrics(summary) {
    if (!summary) return;

    // Cache the summary for currency conversion
    cachedAIData = { ...cachedAIData, summary };

    const totalCalls = summary.TotalCalls || 0;
    const totalTokens = summary.TotalTokens || 0;
    const totalCostUSD = parseFloat(summary.TotalCost || 0);
    const avgCostUSD = parseFloat(summary.AvgCost || 0);
    const avgLatency = summary.AvgLatency || 0;
    const successCount = summary.SuccessCount || 0;
    const failedCount = summary.FailedCount || 0;
    const successRate = totalCalls > 0 ? ((successCount / totalCalls) * 100).toFixed(1) : 0;
    const avgReadingTime = summary.AvgReadingTime || 0;
    const minReadingTime = summary.MinReadingTime || 0;
    const maxReadingTime = summary.MaxReadingTime || 0;

    // Convert costs based on current currency
    const totalCost = convertCurrency(totalCostUSD, currentCurrency);
    const avgCost = convertCurrency(avgCostUSD, currentCurrency);

    setText('#total-ai-calls', totalCalls.toLocaleString());
    setText('#total-ai-tokens', totalTokens.toLocaleString());
    setText('#total-ai-cost', formatCurrency(totalCost, currentCurrency));
    setText('#avg-ai-cost', formatCurrency(avgCost, currentCurrency));
    setText('#avg-ai-latency', avgLatency > 0 ? `${Math.round(avgLatency)}ms` : '--');
    setText('#ai-success-rate', `${successRate}%`);

    // Reading time stats
    setText('#avg-ai-reading-time', avgReadingTime > 0 ? `${Math.round(avgReadingTime)}s` : '--');
    setText('#min-ai-reading-time', minReadingTime > 0 ? `${Math.round(minReadingTime)}s` : '--');
    setText('#max-ai-reading-time', maxReadingTime > 0 ? `${Math.round(maxReadingTime)}s` : '--');
  }

  function renderAICostTimeline(key, elementId, payload) {
    const canvas = qs(`#${elementId}`);
    if (!canvas || !payload) return;
    const ctx = canvas.getContext('2d');

    // Cache payload for currency re-render
    cachedAIData = { ...cachedAIData, costTimeline: payload };

    if (charts[key]) {
      charts[key].destroy();
    }

    // Convert data based on current currency
    const currencySymbol = currentCurrency === 'GBP' ? '£' : '$';
    const convertedPayload = {
      ...payload,
      datasets: payload.datasets.map(ds => ({
        ...ds,
        data: ds.data.map(v => convertCurrency(v, currentCurrency)),
        label: ds.label.replace(/\$|£/, currencySymbol)
      }))
    };

    charts[key] = new Chart(ctx, {
      type: 'bar',
      data: convertedPayload,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        scales: {
          x: {
            display: true,
            grid: {
              color: isDarkMode ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            title: {
              display: true,
              text: 'Date',
              color: isDarkMode ? '#e2e8f0' : '#0f172a',
              padding: { top: 8 }
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: `Cost (${currencySymbol})`,
              color: isDarkMode ? '#e2e8f0' : '#0f172a'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b',
              callback: function(value) {
                return currencySymbol + value.toFixed(4);
              }
            },
            grid: {
              color: isDarkMode ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
            }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              color: isDarkMode ? '#f1f5f9' : '#0f172a',
              usePointStyle: true
            }
          },
          tooltip: {
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            titleColor: isDarkMode ? '#f1f5f9' : '#0f172a',
            bodyColor: isDarkMode ? '#cbd5e1' : '#475569',
            borderColor: isDarkMode ? '#334155' : '#e2e8f0',
            borderWidth: 1,
            callbacks: {
              label: function(context) {
                return context.dataset.label + ': ' + currencySymbol + context.parsed.y.toFixed(4);
              }
            }
          }
        }
      }
    });
  }

  function renderAIUsageTrend(key, elementId, payload) {
    const canvas = qs(`#${elementId}`);
    if (!canvas || !payload) return;
    const ctx = canvas.getContext('2d');

    // Cache payload for currency re-render
    cachedAIData = { ...cachedAIData, usageTrend: payload };

    if (charts[key]) {
      charts[key].destroy();
    }

    const currencySymbol = currentCurrency === 'GBP' ? '£' : '$';

    // Add calls data as a line with currency conversion
    const trendPayload = {
      labels: payload.labels,
      datasets: [
        {
          label: `Daily Cost (${currencySymbol})`,
          data: (payload.datasets[0]?.data || []).map(v => convertCurrency(v, currentCurrency)),
          type: 'bar',
          backgroundColor: '#10b981',
          yAxisID: 'y'
        },
        {
          label: `Cumulative Cost (${currencySymbol})`,
          data: (payload.datasets[1]?.data || []).map(v => convertCurrency(v, currentCurrency)),
          type: 'line',
          borderColor: '#3b82f6',
          backgroundColor: 'transparent',
          borderWidth: 2,
          tension: 0.4,
          yAxisID: 'y'
        }
      ]
    };

    charts[key] = new Chart(ctx, {
      type: 'bar',
      data: trendPayload,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        scales: {
          x: {
            display: true,
            grid: {
              color: isDarkMode ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            },
            title: {
              display: true,
              text: 'Date',
              color: isDarkMode ? '#e2e8f0' : '#0f172a',
              padding: { top: 8 }
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: `Cost (${currencySymbol})`,
              color: isDarkMode ? '#e2e8f0' : '#0f172a'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b',
              callback: function(value) {
                return currencySymbol + value.toFixed(4);
              }
            },
            grid: {
              color: isDarkMode ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
            }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              color: isDarkMode ? '#f1f5f9' : '#0f172a',
              usePointStyle: true
            }
          },
          tooltip: {
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            titleColor: isDarkMode ? '#f1f5f9' : '#0f172a',
            bodyColor: isDarkMode ? '#cbd5e1' : '#475569',
            borderColor: isDarkMode ? '#334155' : '#e2e8f0',
            borderWidth: 1,
            callbacks: {
              label: function(context) {
                return context.dataset.label + ': ' + currencySymbol + context.parsed.y.toFixed(4);
              }
            }
          }
        }
      }
    });
  }

  function renderAIMostExplainedTable(data) {
    const tbody = qs('#ai-most-explained-table tbody');
    if (!tbody) return;

    aiMostExplainedData = data || [];
    // Cache for currency re-render
    cachedAIData = { ...cachedAIData, mostExplained: data };
    tbody.innerHTML = '';

    const currencySymbol = currentCurrency === 'GBP' ? '£' : '$';

    (data || []).forEach((row, index) => {
      const tr = document.createElement('tr');
      const factContent = row.Content || '';
      const displayText = factContent.length > 100
        ? `<span class="fact-text" title="${escapeHtml(factContent)}">${escapeHtml(factContent.substring(0, 100))}...</span>`
        : `<span class="fact-text">${escapeHtml(factContent)}</span>`;
      const costUSD = parseFloat(row.TotalCost || 0);
      const cost = convertCurrency(costUSD, currentCurrency);

      let medalClass = '';
      if (index === 0) medalClass = 'medal-gold';
      else if (index === 1) medalClass = 'medal-silver';
      else if (index === 2) medalClass = 'medal-bronze';

      tr.innerHTML = `
        <td>${displayText}</td>
        <td>${escapeHtml(row.CategoryName || '')}</td>
        <td style="text-align: center;" class="${medalClass}">${row.CallCount || 0}</td>
        <td style="text-align: center;">${currencySymbol}${cost.toFixed(4)}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderAIRecentUsageTable(data) {
    const tbody = qs('#ai-usage-log-table tbody');
    if (!tbody) return;

    aiRecentUsageData = data || [];
    // Cache for currency re-render
    cachedAIData = { ...cachedAIData, recentUsage: data };
    tbody.innerHTML = '';

    const currencySymbol = currentCurrency === 'GBP' ? '£' : '$';

    (data || []).forEach(row => {
      const tr = document.createElement('tr');
      const time = row.CreatedAt ? new Date(row.CreatedAt).toLocaleString() : '';
      const factContent = row.FactContent || '';
      const displayText = factContent.length > 60
        ? `<span class="fact-text" title="${escapeHtml(factContent)}">${escapeHtml(factContent.substring(0, 60))}...</span>`
        : `<span class="fact-text">${escapeHtml(factContent)}</span>`;
      const costUSD = parseFloat(row.Cost || 0);
      const cost = convertCurrency(costUSD, currentCurrency);
      const latency = row.LatencyMs || 0;
      const status = row.Status || 'UNKNOWN';
      const statusClass = status === 'SUCCESS' ? 'status-success' : 'status-failed';

      const model = row.Model || '--';

      tr.innerHTML = `
        <td>${escapeHtml(time)}</td>
        <td>${displayText}</td>
        <td style="text-align: center;">${row.TotalTokens || 0}</td>
        <td style="text-align: center;">${currencySymbol}${cost.toFixed(7)}</td>
        <td style="text-align: center;">${latency}ms</td>
        <td style="text-align: center;"><span class="${statusClass}">${escapeHtml(status)}</span></td>
        <td style="text-align: center;">${escapeHtml(model)}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // AI Provider Comparison Table
  function renderAIProviderComparisonTable(data) {
    const tbody = qs('#ai-provider-comparison-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const currencySymbol = currentCurrency === 'GBP' ? '£' : '$';

    (data || []).forEach(row => {
      const tr = document.createElement('tr');
      const totalCostUSD = parseFloat(row.TotalCost || 0);
      const avgCostUSD = parseFloat(row.AvgCost || 0);
      const totalCost = convertCurrency(totalCostUSD, currentCurrency);
      const avgCost = convertCurrency(avgCostUSD, currentCurrency);
      const successCount = parseInt(row.SuccessCount || 0);
      const failedCount = parseInt(row.FailedCount || 0);
      const totalCalls = successCount + failedCount;
      const successRate = totalCalls > 0 ? ((successCount / totalCalls) * 100).toFixed(1) : '0.0';

      tr.innerHTML = `
        <td><strong>${escapeHtml(row.Provider || 'Unknown')}</strong></td>
        <td style="text-align: center;">${row.CallCount || 0}</td>
        <td style="text-align: center;">${currencySymbol}${totalCost.toFixed(4)}</td>
        <td style="text-align: center;">${currencySymbol}${avgCost.toFixed(6)}</td>
        <td style="text-align: center;">${Math.round(row.AvgLatency || 0)}ms</td>
        <td style="text-align: center;"><span class="${parseFloat(successRate) >= 95 ? 'status-success' : 'status-failed'}">${successRate}%</span></td>
      `;
      tbody.appendChild(tr);
    });
  }

  // Category Completion Rate Chart
  function renderCategoryCompletionRate(key, canvasId, data) {
    const ctx = qs(`#${canvasId}`)?.getContext('2d');
    if (!ctx || !data || data.length === 0) return;
    destroyChart(key);

    const labels = data.map(d => d.CategoryName || 'Unknown');
    const completionRates = data.map(d => parseFloat(d.CompletionRate || 0));
    const knownCounts = data.map(d => parseInt(d.KnownFacts || 0));
    const totalCounts = data.map(d => parseInt(d.TotalFacts || 0));

    charts[key] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Completion Rate (%)',
          data: completionRates,
          backgroundColor: completionRates.map(rate => {
            if (rate >= 75) return isDarkMode ? '#34d399' : '#10b981';
            if (rate >= 50) return isDarkMode ? '#fbbf24' : '#f59e0b';
            if (rate >= 25) return isDarkMode ? '#fb923c' : '#f97316';
            return isDarkMode ? '#f87171' : '#ef4444';
          }),
          borderRadius: 6,
          borderSkipped: false,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            beginAtZero: true,
            max: 100,
            grid: { color: isDarkMode ? 'rgba(148, 163, 184, 0.1)' : 'rgba(0, 0, 0, 0.05)' },
            ticks: { color: isDarkMode ? '#94a3b8' : '#64748b', callback: v => v + '%' },
            title: { display: true, text: 'Completion %', color: isDarkMode ? '#e2e8f0' : '#0f172a' }
          },
          y: {
            grid: { display: false },
            ticks: { color: isDarkMode ? '#94a3b8' : '#64748b' },
            title: { display: true, text: 'Category', color: isDarkMode ? '#e2e8f0' : '#0f172a' }
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            titleColor: isDarkMode ? '#f1f5f9' : '#0f172a',
            bodyColor: isDarkMode ? '#cbd5e1' : '#475569',
            borderColor: isDarkMode ? '#334155' : '#e2e8f0',
            borderWidth: 1,
            callbacks: {
              label: function(context) {
                const idx = context.dataIndex;
                return `${completionRates[idx].toFixed(1)}% (${knownCounts[idx]}/${totalCounts[idx]} facts)`;
              }
            }
          }
        }
      }
    });
  }

  // Learning Velocity Chart
  function renderLearningVelocity(key, canvasId, data) {
    const ctx = qs(`#${canvasId}`)?.getContext('2d');
    if (!ctx || !data || data.length === 0) return;
    destroyChart(key);

    const labels = data.map(d => d.CategoryName || 'Unknown');
    const avgDays = data.map(d => parseInt(d.AvgDaysToKnow || 0));
    const minDays = data.map(d => parseInt(d.MinDaysToKnow || 0));
    const maxDays = data.map(d => parseInt(d.MaxDaysToKnow || 0));

    charts[key] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Avg Days',
            data: avgDays,
            backgroundColor: isDarkMode ? '#60a5fa' : '#3b82f6',
            borderRadius: 6,
          },
          {
            label: 'Min Days',
            data: minDays,
            backgroundColor: isDarkMode ? '#34d399' : '#10b981',
            borderRadius: 6,
          },
          {
            label: 'Max Days',
            data: maxDays,
            backgroundColor: isDarkMode ? '#f87171' : '#ef4444',
            borderRadius: 6,
          }
        ]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            beginAtZero: true,
            grid: { color: isDarkMode ? 'rgba(148, 163, 184, 0.1)' : 'rgba(0, 0, 0, 0.05)' },
            ticks: { color: isDarkMode ? '#94a3b8' : '#64748b' },
            title: { display: true, text: 'Days', color: isDarkMode ? '#e2e8f0' : '#0f172a' }
          },
          y: {
            grid: { display: false },
            ticks: { color: isDarkMode ? '#94a3b8' : '#64748b' },
            title: { display: true, text: 'Category', color: isDarkMode ? '#e2e8f0' : '#0f172a' }
          }
        },
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: isDarkMode ? '#cbd5e1' : '#475569', padding: 15 }
          },
          tooltip: {
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            titleColor: isDarkMode ? '#f1f5f9' : '#0f172a',
            bodyColor: isDarkMode ? '#cbd5e1' : '#475569',
            borderColor: isDarkMode ? '#334155' : '#e2e8f0',
            borderWidth: 1,
          }
        }
      }
    });
  }

  // Peak Productivity Chart
  function renderPeakProductivity(key, canvasId, data) {
    const ctx = qs(`#${canvasId}`)?.getContext('2d');
    if (!ctx || !data || data.length === 0) return;
    destroyChart(key);

    // Create full 24-hour array
    const hourlyData = new Array(24).fill(0);
    data.forEach(d => {
      const hour = parseInt(d.Hour || 0);
      hourlyData[hour] = parseFloat(d.AvgEfficiency || 0);
    });

    const labels = Array.from({length: 24}, (_, i) => {
      const h = i % 12 || 12;
      const ampm = i < 12 ? 'AM' : 'PM';
      return `${h}${ampm}`;
    });

    // Find peak hours
    const maxEfficiency = Math.max(...hourlyData);

    charts[key] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Facts/Minute',
          data: hourlyData,
          backgroundColor: hourlyData.map(v => {
            if (v === maxEfficiency && v > 0) return isDarkMode ? '#34d399' : '#10b981';
            if (v >= maxEfficiency * 0.75) return isDarkMode ? '#60a5fa' : '#3b82f6';
            if (v > 0) return isDarkMode ? '#94a3b8' : '#cbd5e1';
            return isDarkMode ? '#374151' : '#e5e7eb';
          }),
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: isDarkMode ? '#94a3b8' : '#64748b', maxRotation: 45, minRotation: 45 },
            title: { display: true, text: 'Hour of Day', color: isDarkMode ? '#e2e8f0' : '#0f172a' }
          },
          y: {
            beginAtZero: true,
            grid: { color: isDarkMode ? 'rgba(148, 163, 184, 0.1)' : 'rgba(0, 0, 0, 0.05)' },
            ticks: { color: isDarkMode ? '#94a3b8' : '#64748b' },
            title: { display: true, text: 'Facts/Min', color: isDarkMode ? '#e2e8f0' : '#0f172a' }
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
            titleColor: isDarkMode ? '#f1f5f9' : '#0f172a',
            bodyColor: isDarkMode ? '#cbd5e1' : '#475569',
            borderColor: isDarkMode ? '#334155' : '#e2e8f0',
            borderWidth: 1,
            callbacks: {
              label: function(context) {
                return `Efficiency: ${context.parsed.y.toFixed(2)} facts/min`;
              }
            }
          }
        }
      }
    });
  }

  // Update XP Progress Bar
  function updateXPProgressBar(gamification) {
    if (!gamification) return;

    const level = gamification.level || 1;
    const xp = gamification.xp || 0;
    const xpIntoLevel = gamification.xp_into_level || 0;
    const xpToNext = gamification.xp_to_next || 0;
    const nextLevelReq = gamification.next_level_requirement || 100;
    const maxXP = 1000000;

    const progressPercent = nextLevelReq > 0 ? Math.min(100, (xpIntoLevel / nextLevelReq) * 100) : 100;

    setText('#xp-level-badge', `Lv ${level}`);
    setText('#xp-current', xpIntoLevel.toLocaleString());
    setText('#xp-required', nextLevelReq.toLocaleString());
    setText('#xp-total', `${xp.toLocaleString()} / ${maxXP.toLocaleString()}`);

    const progressBar = qs('#xp-progress-bar');
    if (progressBar) {
      progressBar.style.width = `${progressPercent}%`;
    }

    if (level >= 100) {
      setText('#xp-to-next', 'MAX LEVEL!');
    } else if (xpToNext <= 0) {
      setText('#xp-to-next', 'Unlock more achievements to level up');
    } else {
      setText('#xp-to-next', `${xpToNext.toLocaleString()} XP to next level`);
    }
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
  
  // Function to re-render AI data with new currency
  function updateAICurrency() {
    if (!cachedAIData) return;

    // Re-render metrics
    if (cachedAIData.summary) {
      renderAIUsageMetrics(cachedAIData.summary);
    }

    // Re-render charts
    if (cachedAIData.costTimeline) {
      renderAICostTimeline('ai_cost_timeline', 'ai-cost-timeline', cachedAIData.costTimeline);
    }
    if (cachedAIData.usageTrend) {
      renderAIUsageTrend('ai_usage_trend', 'ai-usage-trend', cachedAIData.usageTrend);
    }

    // Re-render tables
    if (cachedAIData.mostExplained) {
      renderAIMostExplainedTable(cachedAIData.mostExplained);
    }
    if (cachedAIData.recentUsage) {
      renderAIRecentUsageTable(cachedAIData.recentUsage);
    }
  }

  // Setup currency toggle
  function setupCurrencyToggle() {
    const toggle = qs('#currency-toggle');
    if (!toggle) return;

    // Set initial state
    toggle.setAttribute('data-currency', currentCurrency);

    toggle.addEventListener('click', () => {
      // Toggle currency
      currentCurrency = currentCurrency === 'USD' ? 'GBP' : 'USD';
      toggle.setAttribute('data-currency', currentCurrency);

      // Add a subtle animation
      toggle.style.transform = 'scale(0.98)';
      setTimeout(() => {
        toggle.style.transform = '';
      }, 100);

      // Update all AI data displays
      updateAICurrency();
    });
  }

  // Metric info data definitions
  const metricInfoData = {
    'total-facts': {
      icon: '📚',
      title: 'Total Facts',
      description: 'The total number of facts currently stored in your collection. This represents all unique pieces of knowledge you\'ve added.',
      formula: 'SELECT COUNT(*) FROM Facts'
    },
    'viewed-today': {
      icon: '👁️',
      title: 'Viewed Today',
      description: 'The total number of distinct facts you have reviewed today. Each fact is only counted once, even if you\'ve viewed it multiple times today.',
      formula: 'SELECT COUNT(DISTINCT FactID) FROM ReviewLogs WHERE ReviewDate = TODAY AND Action = \'view\''
    },
    'review-streak': {
      icon: '🔥',
      title: 'Review Streak',
      description: 'The number of consecutive days you have reviewed at least one fact. Your streak resets to 0 if you miss a day without any reviews.',
      formula: 'Count consecutive days (including today) where ReviewLogs has at least 1 view entry, going backwards until a gap is found.'
    },
    'categories': {
      icon: '📊',
      title: 'Categories',
      description: 'The number of fact categories in your collection. Categories help organize your facts into meaningful groups.',
      formula: 'SELECT COUNT(*) FROM Categories'
    },
    'favorites': {
      icon: '⭐',
      title: 'Favorites',
      description: 'The number of facts you\'ve marked as favorites. Favorite facts can be easily accessed and reviewed separately.',
      formula: 'SELECT COUNT(*) FROM ProfileFacts WHERE IsFavorite = 1'
    },
    'known-facts': {
      icon: '✅',
      title: 'Known Facts',
      description: 'The number of facts you\'ve marked as "known". These are facts you\'ve mastered and feel confident about.',
      formula: 'SELECT COUNT(*) FROM ProfileFacts WHERE IsEasy = 1'
    },
    'lifetime-adds': {
      icon: '➕',
      title: 'Facts Added',
      description: 'The total number of facts you\'ve added to your collection since you started using FactDari. This counter increments each time you create a new fact.',
      formula: 'SELECT TotalAdds FROM GamificationProfile'
    },
    'lifetime-edits': {
      icon: '✏️',
      title: 'Facts Edited',
      description: 'The total number of times you\'ve edited existing facts. Each edit to a fact\'s content increments this counter.',
      formula: 'SELECT TotalEdits FROM GamificationProfile'
    },
    'lifetime-deletes': {
      icon: '🗑️',
      title: 'Facts Deleted',
      description: 'The total number of facts you\'ve deleted from your collection. Deleted facts are removed but this counter preserves your activity history.',
      formula: 'SELECT TotalDeletes FROM GamificationProfile'
    },
    'lifetime-reviews': {
      icon: '📖',
      title: 'Total Reviews',
      description: 'The total number of fact reviews you\'ve completed. Each time you view a fact for at least 2 seconds, it counts as one review.',
      formula: 'SELECT TotalReviews FROM GamificationProfile'
    },
    'lifetime-streak': {
      icon: '🔥',
      title: 'Day Streak',
      description: 'Your current streak shows consecutive days with at least one review. Your best streak is the longest consecutive run you\'ve achieved. Missing a day resets your current streak to 0.',
      formula: 'SELECT CurrentStreak, LongestStreak FROM GamificationProfile'
    },
    'avg-session': {
      icon: '⏱️',
      title: 'Average Session',
      description: 'The average duration of your review sessions in minutes. Only sessions with recorded duration greater than 0 are included in this calculation.',
      formula: 'SELECT AVG(DurationSeconds) / 60 FROM ReviewSessions WHERE DurationSeconds > 0'
    },
    'total-time': {
      icon: '⏳',
      title: 'Total Time',
      description: 'The cumulative time you\'ve spent reviewing facts across all sessions, displayed in hours. This represents your total learning investment.',
      formula: 'SELECT SUM(DurationSeconds) / 3600 FROM ReviewSessions WHERE DurationSeconds > 0'
    },
    'longest-session': {
      icon: '🏁',
      title: 'Longest Session',
      description: 'The duration of your longest single review session in minutes. This is your personal best for sustained focus.',
      formula: 'SELECT MAX(DurationSeconds) / 60 FROM ReviewSessions WHERE DurationSeconds > 0'
    },
    'total-sessions': {
      icon: '📈',
      title: 'Total Sessions',
      description: 'The total number of review sessions you\'ve completed. A session starts when you begin reviewing and ends when you press Home, the app times out due to inactivity, or the app closes.',
      formula: 'SELECT COUNT(*) FROM ReviewSessions WHERE DurationSeconds > 0'
    },
    'avg-facts-session': {
      icon: '📊',
      title: 'Avg Facts/Session',
      description: 'The average number of unique facts you review per session. Higher values indicate more productive sessions.',
      formula: 'SELECT AVG(FactCount) FROM (SELECT COUNT(DISTINCT FactID) as FactCount FROM ReviewLogs GROUP BY SessionID)'
    },
    'best-efficiency': {
      icon: '⚡',
      title: 'Best Efficiency',
      description: 'Your highest review efficiency measured in facts per minute. This is calculated as (unique facts reviewed × 60) / session duration in seconds.',
      formula: 'SELECT MAX(COUNT(DISTINCT FactID) * 60.0 / DurationSeconds) FROM ReviewLogs JOIN ReviewSessions'
    },
    'total-ai-calls': {
      icon: '🤖',
      title: 'Total AI Calls',
      description: 'The total number of AI API calls made to generate explanations for your facts. Each time you request an AI explanation, it counts as one call.',
      formula: 'SELECT COUNT(*) FROM AIUsageLogs'
    },
    'total-ai-tokens': {
      icon: '🔢',
      title: 'Total Tokens',
      description: 'The total number of tokens consumed across all AI calls. Tokens are the basic units of text processing - both your input (the fact) and the AI\'s output (the explanation) consume tokens.',
      formula: 'SELECT SUM(TotalTokens) FROM AIUsageLogs'
    },
    'total-ai-cost': {
      icon: '💰',
      title: 'Total Cost',
      description: 'The cumulative cost of all AI API calls. Cost is calculated based on the number of input and output tokens used, with rates varying by AI provider and model.',
      formula: 'SELECT SUM(Cost) FROM AIUsageLogs'
    },
    'avg-ai-cost': {
      icon: '📊',
      title: 'Avg Cost/Call',
      description: 'The average cost per AI API call. This helps you understand your typical spending per explanation request.',
      formula: 'SELECT AVG(Cost) FROM AIUsageLogs'
    },
    'avg-ai-latency': {
      icon: '⚡',
      title: 'Avg Latency',
      description: 'The average response time for AI API calls in milliseconds. Lower latency means faster explanations. This depends on the AI provider, model, and network conditions.',
      formula: 'SELECT AVG(LatencyMs) FROM AIUsageLogs'
    },
    'ai-success-rate': {
      icon: '✅',
      title: 'Success Rate',
      description: 'The percentage of AI API calls that completed successfully. Failed calls may be due to network issues, API errors, or rate limiting.',
      formula: 'SELECT (SUM(CASE WHEN Status = \'SUCCESS\' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) FROM AIUsageLogs'
    }
  };

  function setupMetricInfoModal() {
    const modal = qs('#metric-info-modal');
    const closeBtn = modal?.querySelector('.modal-close');
    const iconEl = modal?.querySelector('.metric-info-icon');
    const titleEl = modal?.querySelector('.metric-info-title');
    const descEl = modal?.querySelector('.metric-info-description');
    const formulaEl = modal?.querySelector('.metric-info-formula');

    if (!modal) return;

    // Handle info button clicks
    qsa('.metric-info-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const metricKey = btn.dataset.metric;
        const info = metricInfoData[metricKey];

        if (info) {
          if (iconEl) iconEl.textContent = info.icon;
          if (titleEl) titleEl.textContent = info.title;
          if (descEl) descEl.textContent = info.description;
          if (formulaEl) formulaEl.textContent = info.formula;
          modal.style.display = 'flex';
        }
      });
    });

    // Close modal handlers
    const closeModal = () => {
      modal.style.display = 'none';
    };

    closeBtn?.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });

    // ESC key to close
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modal.style.display === 'flex') {
        closeModal();
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupExpandModal();
    setupMetricInfoModal();
    setupSmoothScroll();
    setupKeyboardShortcuts();
    setupCurrencyToggle();
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
