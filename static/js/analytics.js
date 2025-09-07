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
    // Update navbar gamification stats
    setText('#nav-level-value', `Lv ${level}`);
    const gated = (level < 100) && (xpToNext <= 0);
    const xpText = gated ? `${xp} (achievements required)` : (xpToNext > 0 ? `${xp} (${xpToNext}\u2192)` : `${xp} (MAX)`);
    setText('#nav-xp-value', xpText);
    setText('#nav-achievements-count', `${ach.unlocked || 0}/${ach.total || 0}`);
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
        <td><span class="fact-text">${factContent}</span></td>
        <td>${row.CategoryName || ''}</td>
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
        <td>${when}</td>
        <td>${row.Name || ''}</td>
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
        `<span class="fact-text" title="${factContent.replace(/"/g, '&quot;')}">${factContent.substring(0, 150)}...</span>` :
        `<span class="fact-text">${factContent}</span>`;
      tr.innerHTML = `
        <td>${sessionStart}</td>
        <td>${reviewTime}</td>
        <td>${row.CategoryName || ''}</td>
        <td>${displayText}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderAllAchievementsTable(rows) {
    const table = qs('#all-achievements-table');
    const tbody = qs('#all-achievements-table tbody');
    if (!table || !tbody) return;
    const data = Array.isArray(rows) ? rows.slice() : [];

    // Sorting helper
    const sortBy = (idx, dir) => {
      const asc = dir === 'asc';
      const getVal = (r) => {
        switch(idx) {
          case 0: return r.Unlocked ? 1 : 0; // status
          case 1: return (r.Name || '').toLowerCase();
          case 2: return (r.Category || '').toLowerCase();
          case 3: return (r.ProgressCurrent || 0) / Math.max(1, r.Threshold || 1); // ratio
          case 4: return r.RewardXP || 0;
          case 5: return r.UnlockDate ? new Date(r.UnlockDate).getTime() : 0;
          default: return 0;
        }
      };
      data.sort((a, b) => {
        // Always show unlocked achievements first
        if (a.Unlocked !== b.Unlocked) {
          return a.Unlocked ? -1 : 1;
        }
        // Then apply the selected sorting
        const va = getVal(a), vb = getVal(b);
        if (typeof va === 'string' && typeof vb === 'string') return asc ? va.localeCompare(vb) : vb.localeCompare(va);
        return asc ? (va - vb) : (vb - va);
      });
    };
    sortBy(achievementsSortState.index, achievementsSortState.dir);

    tbody.innerHTML = '';
    data.forEach(r => {
      const tr = document.createElement('tr');
      const status = r.Unlocked ? 'Unlocked' : 'Locked';
      const progress = `${Math.min(r.ProgressCurrent || 0, r.Threshold || 0)}/${r.Threshold || 0}`;
      const when = r.UnlockDate ? new Date(r.UnlockDate).toLocaleString() : '';
      tr.innerHTML = `
        <td>${status}</td>
        <td>${r.Name || ''}</td>
        <td>${r.Category || ''}</td>
        <td style="text-align:center;">${progress}</td>
        <td style="text-align:center;">${r.RewardXP || 0} XP</td>
        <td>${when}</td>
      `;
      if (r.Unlocked) tr.classList.add('row-unlocked');
      tbody.appendChild(tr);
    });

    if (!table.dataset.sortAttached) {
      const ths = Array.from(table.querySelectorAll('thead th'));
      ths.forEach((th, idx) => {
        th.classList.add('sortable');
        th.addEventListener('click', () => {
          const newDir = (achievementsSortState.index === idx && achievementsSortState.dir === 'asc') ? 'desc' : 'asc';
          achievementsSortState = { index: idx, dir: newDir };
          renderAllAchievementsTable(rows || []);
          applySortIndicator(table, idx, newDir);
        });
      });
      table.dataset.sortAttached = '1';
      applySortIndicator(table, achievementsSortState.index, achievementsSortState.dir);
    }
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
        <td><span class="fact-text">${factContent}</span></td>
        <td>${row.CategoryName || ''}</td>
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
            key === 'favorite-facts-table' || key === 'known-facts-table') {
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
                <td><span class="fact-text">${factContent}</span></td>
                <td>${row.CategoryName || ''}</td>
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
                <td><span class="fact-text">${factContent}</span></td>
                <td>${row.CategoryName || ''}</td>
                <td style="text-align: center;" class="${medalClass}">${row.ReviewCount || 0}</td>
                <td style="text-align: center;">${row.DaysSinceReview ?? 'N/A'}</td>
              `;
              tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            // Enable sorting in modal for Known Facts
            makeModalTableSortable(table, fullKnownData, 'known');
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
            'session-actions-chart': 'session_actions'
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
              `<span class="fact-text" title="${factContent.replace(/"/g, '&quot;')}">${factContent.substring(0, 200)}...</span>` :
              `<span class="fact-text">${factContent}</span>`;
            tr.innerHTML = `
              <td>${sessionStart}</td>
              <td>${reviewTime}</td>
              <td>${row.CategoryName || ''}</td>
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
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: 'Duration (minutes)',
              color: isDarkMode ? '#94a3b8' : '#64748b'
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
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: 'Timeout Count',
              color: isDarkMode ? '#94a3b8' : '#64748b'
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
            }
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
            }
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
            }
          },
          y: {
            beginAtZero: true,
            grid: {
              color: isDarkMode ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
              color: isDarkMode ? '#94a3b8' : '#64748b'
            }
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
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: 'Reviews / Facts',
              color: isDarkMode ? '#94a3b8' : '#64748b'
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
