/**
 * SENTINEL WEALTH & FRAUD SHIELD
 * Complete Frontend Controller & Reactive State Manager (2026)
 * Supports Multi-Currency (INR ₹, USD $, EUR €, GBP £, JPY ¥, etc.),
 * Page-Specific Dynamic Color Theming, Privacy Mode, and Emergency Lockdown.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Supported Currencies & Baseline USD Exchange Rates
  const CURRENCIES = {
    INR: { symbol: "₹", rate: 83.5, name: "Indian Rupee", locale: "en-IN" },
    USD: { symbol: "$", rate: 1.0, name: "US Dollar", locale: "en-US" },
    EUR: { symbol: "€", rate: 0.92, name: "Euro", locale: "de-DE" },
    GBP: { symbol: "£", rate: 0.79, name: "British Pound", locale: "en-GB" },
    JPY: { symbol: "¥", rate: 155.0, name: "Japanese Yen", locale: "ja-JP" },
    AED: { symbol: "د.إ ", rate: 3.67, name: "UAE Dirham", locale: "ar-AE" },
    CAD: { symbol: "CA$", rate: 1.36, name: "Canadian Dollar", locale: "en-CA" },
    AUD: { symbol: "AU$", rate: 1.52, name: "Australian Dollar", locale: "en-AU" }
  };

  // Global State
  const state = {
    overview: null,
    accounts: [],
    transactions: [],
    budgets: [],
    subscriptions: [],
    fraudAlerts: [],
    forecast: null,
    insights: [],
    blocklist: [],
    activeTab: "dashboard",
    theme: localStorage.getItem("sentinel_theme") || "dark",
    currency: localStorage.getItem("sentinel_currency") || "INR",
    isPrivacyActive: localStorage.getItem("sentinel_privacy") === "true",
    charts: {}
  };

  // ----------------------------------------------------
  // Initialization
  // ----------------------------------------------------
  initTheme();
  initCurrency();
  initPrivacyMode();
  initNavigation();
  initModals();
  initEventListeners();
  fetchAllData();

  // ----------------------------------------------------
  // Currency Management Engine (INR ₹, USD, EUR, etc.)
  // ----------------------------------------------------
  function initCurrency() {
    const select = document.getElementById("global-currency-select");
    if (select) {
      select.value = state.currency;
      select.addEventListener("change", (e) => {
        state.currency = e.target.value;
        localStorage.setItem("sentinel_currency", state.currency);
        reRenderAllViews();
      });
    }
    updateModalCurrencyLabels();
  }

  function formatCurrency(usdVal) {
    if (usdVal === undefined || usdVal === null) return "₹0.00";
    const curr = CURRENCIES[state.currency] || CURRENCIES.INR;
    const converted = usdVal * curr.rate;

    const formattedNum = new Intl.NumberFormat(curr.locale, {
      minimumFractionDigits: state.currency === "JPY" ? 0 : 2,
      maximumFractionDigits: state.currency === "JPY" ? 0 : 2
    }).format(converted);

    return `${curr.symbol}${formattedNum}`;
  }

  function updateModalCurrencyLabels() {
    const curr = CURRENCIES[state.currency] || CURRENCIES.INR;
    
    // Update currency symbol and code spans across all modals
    document.querySelectorAll(".active-curr-sym").forEach(el => {
      el.innerText = curr.symbol;
    });
    document.querySelectorAll(".active-curr-code").forEach(el => {
      el.innerText = state.currency;
    });

    // Update input placeholders
    const txAmtInput = document.getElementById("tx-amount");
    if (txAmtInput) {
      txAmtInput.placeholder = `e.g. ${curr.symbol}150.00`;
    }

    const budgetInput = document.getElementById("budget-limit-val");
    if (budgetInput) {
      budgetInput.placeholder = `e.g. ${curr.symbol}5000`;
    }

    const nlpInput = document.getElementById("input-nlp-quick-add");
    if (nlpInput) {
      nlpInput.placeholder = `✨ NLP Smart Add: 'Paid ${curr.symbol}450 on Dominos Pizza in Mumbai' or 'Spent ${curr.symbol}1200 at Whole Foods'..."`;
    }
  }

  function reRenderAllViews() {
    renderOverview();
    renderAccounts();
    populateAccountSelects();
    updateModalCurrencyLabels();
    renderRecentTransactions();
    renderAllTransactions();
    renderBudgets();
    renderSubscriptions();
    renderFraudAlerts();
    renderForecast();
    runWhatIfCalculation();
    applyPrivacyMode();
  }

  // ----------------------------------------------------
  // Theme Switching System (Dark & Light)
  // ----------------------------------------------------
  function initTheme() {
    applyTheme(state.theme);

    const themeToggleBtn = document.getElementById("btn-theme-toggle");
    if (themeToggleBtn) {
      themeToggleBtn.addEventListener("click", () => {
        const newTheme = state.theme === "dark" ? "light" : "dark";
        state.theme = newTheme;
        localStorage.setItem("sentinel_theme", newTheme);
        applyTheme(newTheme);
        
        // Re-render charts with adapted colors
        if (state.overview) {
          renderCashflowChart(state.overview.cashflow_history);
          renderCategoryDonutChart(state.overview.category_breakdown);
        }
        if (state.forecast) {
          renderForecast();
        }
      });
    }
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    const themeIcon = document.getElementById("theme-icon");
    if (themeIcon) {
      if (theme === "light") {
        themeIcon.className = "ph-bold ph-moon";
        themeIcon.title = "Switch to Dark Mode";
      } else {
        themeIcon.className = "ph-bold ph-sun";
        themeIcon.title = "Switch to Light Mode";
      }
    }
  }

  // ----------------------------------------------------
  // Privacy Blur / Incognito Mode (Hide Balances)
  // ----------------------------------------------------
  function initPrivacyMode() {
    applyPrivacyMode();
    const btn = document.getElementById("btn-privacy-toggle");
    if (btn) {
      btn.addEventListener("click", () => {
        state.isPrivacyActive = !state.isPrivacyActive;
        localStorage.setItem("sentinel_privacy", state.isPrivacyActive);
        applyPrivacyMode();
      });
    }
  }

  function applyPrivacyMode() {
    const icon = document.getElementById("privacy-icon");
    if (icon) {
      icon.className = state.isPrivacyActive ? "ph-bold ph-eye-slash text-orange" : "ph-bold ph-eye";
    }

    const sensitiveSelectors = [
      "#net-worth-val",
      "#income-val",
      "#expense-val",
      ".acc-balance",
      ".sub-amount",
      "#mini-health-score",
      "#fc-spent",
      "#fc-projected"
    ];

    sensitiveSelectors.forEach(sel => {
      document.querySelectorAll(sel).forEach(el => {
        el.classList.toggle("privacy-blurred", state.isPrivacyActive);
      });
    });
  }

  // ----------------------------------------------------
  // Page-Specific Dynamic Color Themes & Navigation
  // ----------------------------------------------------
  function initNavigation() {
    const navItems = document.querySelectorAll(".nav-item");
    navItems.forEach(item => {
      item.addEventListener("click", () => {
        const targetTab = item.getAttribute("data-tab");
        switchTab(targetTab);
      });
    });

    // Sub-navigation triggers
    document.getElementById("btn-quick-sandbox")?.addEventListener("click", () => switchTab("simulator"));
    document.getElementById("btn-view-threats")?.addEventListener("click", () => switchTab("fraud"));
    document.getElementById("btn-view-all-tx")?.addEventListener("click", () => switchTab("transactions"));
  }

  function switchTab(tabId) {
    state.activeTab = tabId;

    // Apply Page Theme to Body
    document.body.setAttribute("data-page-theme", tabId);

    // Update Nav Buttons
    document.querySelectorAll(".nav-item").forEach(btn => {
      btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
    });

    // Update Views
    document.querySelectorAll(".tab-view").forEach(view => {
      view.classList.toggle("active", view.id === `tab-${tabId}`);
    });

    // Page Specific Theme Labels & Headers
    const pageBadgeLabel = document.getElementById("page-theme-label");
    const pageTitle = document.getElementById("page-title");
    const pageSub = document.getElementById("page-subtitle");

    const tabMeta = {
      dashboard: { badge: "Executive Wealth Matrix", title: "Financial Executive Dashboard", sub: "Real-time wealth tracking, automated categorization & multi-vector fraud interception" },
      transactions: { badge: "Transaction Intelligence Log", title: "Transaction Intelligence Log", sub: "Search, filter, auto-categorize and inspect granular transaction risk scores" },
      budgets: { badge: "Budget & Subscription Sentry", title: "Budgets, Subscriptions & Optimizer", sub: "Monitor spending caps, prune recurring leaks and simulate compound wealth growth" },
      advisor: { badge: "AI Financial Intelligence", title: "AI Financial Advisor & Assistant", sub: "Natural language financial reasoning, proactive recommendations & smart savings" },
      fraud: { badge: "Sentinel Threat Defense Matrix", title: "Fraud Security & Threat Defense Center", sub: "Multi-vector anomaly alerts, explainable AI diagnostics and dispute resolution" },
      simulator: { badge: "Attack Sandbox Engine", title: "Real-Time Attack Sandbox", sub: "Simulate advanced fraud vectors to benchmark the AI detection engine live" }
    };

    if (tabMeta[tabId]) {
      pageBadgeLabel.innerText = tabMeta[tabId].badge;
      pageTitle.innerText = tabMeta[tabId].title;
      pageSub.innerText = tabMeta[tabId].sub;
    }

    // Refresh charts if switching to dashboard
    if (tabId === "dashboard") {
      setTimeout(() => {
        if (state.charts.cashflow) state.charts.cashflow.resize();
        if (state.charts.category) state.charts.category.resize();
        if (state.charts.forecast) state.charts.forecast.resize();
      }, 100);
    }
  }

  // ----------------------------------------------------
  // API Fetch Orchestration
  // ----------------------------------------------------
  async function fetchAllData() {
    try {
      await Promise.all([
        fetchOverview(),
        fetchAccounts(),
        fetchTransactions(),
        fetchBudgets(),
        fetchSubscriptions(),
        fetchFraudAlerts(),
        fetchBlocklist(),
        fetchInsights(),
        fetchForecast()
      ]);
      applyPrivacyMode();
    } catch (err) {
      console.error("Error fetching application data:", err);
    }
  }

  async function fetchOverview() {
    const res = await fetch("/api/finance/overview");
    if (!res.ok) return;
    state.overview = await res.json();
    renderOverview();
  }

  async function fetchAccounts() {
    const res = await fetch("/api/accounts");
    if (!res.ok) return;
    state.accounts = await res.json();
    renderAccounts();
    populateAccountSelects();
  }

  async function fetchTransactions() {
    const res = await fetch("/api/transactions");
    if (!res.ok) return;
    state.transactions = await res.json();
    renderRecentTransactions();
    renderAllTransactions();
    document.getElementById("nav-tx-count").innerText = state.transactions.length;
  }

  async function fetchBudgets() {
    const res = await fetch("/api/budgets");
    if (!res.ok) return;
    state.budgets = await res.json();
    renderBudgets();
  }

  async function fetchSubscriptions() {
    const res = await fetch("/api/subscriptions");
    if (!res.ok) return;
    state.subscriptions = await res.json();
    renderSubscriptions();
    initWhatIfChecklist();
    runWhatIfCalculation();
  }

  async function fetchFraudAlerts() {
    const filter = document.getElementById("fraud-status-filter")?.value || "active";
    const res = await fetch(`/api/fraud/alerts?status_filter=${filter}`);
    if (!res.ok) return;
    state.fraudAlerts = await res.json();
    renderFraudAlerts();
  }

  async function fetchBlocklist() {
    const res = await fetch("/api/fraud/blocklist");
    if (!res.ok) return;
    state.blocklist = await res.json();
    renderBlocklist();
  }

  async function fetchInsights() {
    const res = await fetch("/api/advisor/insights");
    if (!res.ok) return;
    state.insights = await res.json();
    renderInsights();
  }

  async function fetchForecast() {
    const res = await fetch("/api/finance/forecast");
    if (!res.ok) return;
    state.forecast = await res.json();
    renderForecast();
  }

  // ----------------------------------------------------
  // Render: Overview & Charts
  // ----------------------------------------------------
  function renderOverview() {
    const ov = state.overview;
    if (!ov) return;

    // Metric Values with Currency Conversion
    document.getElementById("net-worth-val").innerText = formatCurrency(ov.net_worth);
    document.getElementById("income-val").innerText = `+${formatCurrency(ov.total_income_this_month)}`;
    document.getElementById("expense-val").innerText = `-${formatCurrency(ov.total_expense_this_month)}`;
    document.getElementById("savings-rate-val").innerText = `${ov.savings_rate_this_month}%`;

    // Health Score in Sidebar
    document.getElementById("mini-health-score").innerText = `${ov.financial_health_score}/100`;
    document.getElementById("mini-health-grade").innerText = `Grade: ${ov.health_grade}`;
    const healthBar = document.getElementById("mini-health-bar");
    healthBar.style.width = `${ov.financial_health_score}%`;
    healthBar.className = `progress-fill ${ov.financial_health_score >= 75 ? 'emerald' : ov.financial_health_score >= 50 ? 'orange' : 'danger'}`;

    // Global Threat Banner Check
    const threatBanner = document.getElementById("global-threat-banner");
    const fraudNavCount = document.getElementById("nav-fraud-count");
    const fraudThreatCount = document.getElementById("fraud-active-threats");

    if (ov.active_fraud_alerts_count > 0) {
      threatBanner.style.display = "flex";
      document.getElementById("threat-banner-text").innerText = `Sentinel Sentry intercepted ${ov.active_fraud_alerts_count} high-risk suspicious transaction(s). Review immediately.`;
      fraudNavCount.style.display = "inline-block";
      fraudNavCount.innerText = ov.active_fraud_alerts_count;
      fraudThreatCount.innerText = ov.active_fraud_alerts_count;
      document.getElementById("security-state-badge").className = "badge-status text-danger";
      document.getElementById("security-state-badge").innerText = "⚠️ Threat Detected";
    } else {
      threatBanner.style.display = "none";
      fraudNavCount.style.display = "none";
      fraudThreatCount.innerText = "0";
      document.getElementById("security-state-badge").className = "badge-status text-emerald";
      document.getElementById("security-state-badge").innerText = "🛡️ Shield Armed (Safe)";
    }

    // Subscriptions Overview
    document.getElementById("sub-monthly-total").innerText = `${formatCurrency(ov.total_subscriptions_monthly)}/mo`;

    // Render Charts
    renderCashflowChart(ov.cashflow_history);
    renderCategoryDonutChart(ov.category_breakdown);
    applyPrivacyMode();
  }

  function renderCashflowChart(history) {
    if (!history || history.length === 0) return;
    const ctx = document.getElementById("cashflowChart")?.getContext("2d");
    if (!ctx) return;

    if (state.charts.cashflow) state.charts.cashflow.destroy();

    const isDark = state.theme === "dark";
    const currRate = CURRENCIES[state.currency]?.rate || 1.0;
    const currSym = CURRENCIES[state.currency]?.symbol || "$";

    const labels = history.map(h => h.month);
    const incomeData = history.map(h => h.income * currRate);
    const expenseData = history.map(h => h.expenses * currRate);
    const savingsData = history.map(h => h.net_savings * currRate);

    state.charts.cashflow = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Monthly Inflow",
            data: incomeData,
            backgroundColor: isDark ? "rgba(16, 185, 129, 0.75)" : "rgba(16, 185, 129, 0.85)",
            borderColor: "#10b981",
            borderRadius: 6,
            barPercentage: 0.6
          },
          {
            label: "Monthly Outflow",
            data: expenseData,
            backgroundColor: isDark ? "rgba(245, 158, 11, 0.75)" : "rgba(245, 158, 11, 0.85)",
            borderColor: "#f59e0b",
            borderRadius: 6,
            barPercentage: 0.6
          },
          {
            label: "Net Savings",
            data: savingsData,
            type: "line",
            borderColor: isDark ? "#818cf8" : "#4f46e5",
            backgroundColor: isDark ? "rgba(129, 140, 248, 0.12)" : "rgba(79, 70, 229, 0.08)",
            borderWidth: 3,
            tension: 0.35,
            fill: true,
            pointBackgroundColor: isDark ? "#818cf8" : "#4f46e5",
            pointRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "top",
            labels: { color: isDark ? "#94a3b8" : "#475569", font: { family: "'Plus Jakarta Sans'", size: 12, weight: "600" } }
          },
          tooltip: {
            backgroundColor: isDark ? "#0f172a" : "#1e293b",
            borderColor: isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)",
            borderWidth: 1,
            callbacks: {
              label: (context) => `${context.dataset.label}: ${currSym}${context.raw.toLocaleString()}`
            }
          }
        },
        scales: {
          x: {
            grid: { color: isDark ? "rgba(255, 255, 255, 0.04)" : "rgba(0, 0, 0, 0.04)" },
            ticks: { color: "#64748b", font: { family: "'Plus Jakarta Sans'" } }
          },
          y: {
            grid: { color: isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.05)" },
            ticks: {
              color: "#64748b",
              font: { family: "'JetBrains Mono'" },
              callback: (val) => `${currSym}${val.toLocaleString()}`
            }
          }
        }
      }
    });
  }

  function renderCategoryDonutChart(categories) {
    if (!categories || categories.length === 0) return;
    const ctx = document.getElementById("categoryDonutChart")?.getContext("2d");
    if (!ctx) return;

    if (state.charts.category) state.charts.category.destroy();

    const isDark = state.theme === "dark";
    const currRate = CURRENCIES[state.currency]?.rate || 1.0;
    const currSym = CURRENCIES[state.currency]?.symbol || "$";

    const labels = categories.map(c => c.category);
    const data = categories.map(c => c.amount * currRate);
    const colors = categories.map(c => c.color);

    state.charts.category = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: colors,
          borderColor: isDark ? "#0e131f" : "#ffffff",
          borderWidth: 3,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "70%",
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: isDark ? "#0f172a" : "#1e293b",
            borderColor: isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)",
            borderWidth: 1,
            callbacks: {
              label: (ctx) => ` ${ctx.label}: ${currSym}${ctx.raw.toLocaleString()} (${categories[ctx.dataIndex].percentage}%)`
            }
          }
        }
      }
    });

    // Custom Legend
    const legendContainer = document.getElementById("category-legend-list");
    if (legendContainer) {
      legendContainer.innerHTML = categories.slice(0, 6).map(c => `
        <div class="legend-item">
          <span class="legend-color" style="background-color: ${c.color}"></span>
          <span>${c.category} (${c.percentage}%)</span>
        </div>
      `).join("");
    }
  }

  function renderForecast() {
    const fc = state.forecast;
    if (!fc) return;

    document.getElementById("fc-spent").innerText = formatCurrency(fc.current_spent);
    document.getElementById("fc-burn").innerText = `${formatCurrency(fc.daily_burn_rate)} / day`;
    document.getElementById("fc-projected").innerText = formatCurrency(fc.projected_total_month_expense);

    const badge = document.getElementById("forecast-status-badge");
    if (fc.status === "on_track") {
      badge.className = "badge emerald";
      badge.innerText = "On Track";
    } else if (fc.status === "warning") {
      badge.className = "badge orange";
      badge.innerText = "Near Budget Limit";
    } else {
      badge.className = "badge danger";
      badge.innerText = "Over Budget Alert";
    }

    // Trajectory Chart
    const ctx = document.getElementById("forecastTrajectoryChart")?.getContext("2d");
    if (!ctx || !fc.forecast_points) return;

    if (state.charts.forecast) state.charts.forecast.destroy();

    const isDark = state.theme === "dark";
    const currRate = CURRENCIES[state.currency]?.rate || 1.0;
    const currSym = CURRENCIES[state.currency]?.symbol || "$";

    const labels = fc.forecast_points.map(p => p.day);
    const actualData = fc.forecast_points.map(p => p.actual !== null ? p.actual * currRate : null);
    const projectedData = fc.forecast_points.map(p => p.projected !== null ? p.projected * currRate : null);

    state.charts.forecast = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Actual Spend",
            data: actualData,
            borderColor: "#10b981",
            backgroundColor: "rgba(16, 185, 129, 0.1)",
            borderWidth: 2,
            tension: 0.2,
            pointRadius: 0,
            fill: true
          },
          {
            label: "AI Burn Trajectory",
            data: projectedData,
            borderColor: "#f59e0b",
            borderDash: [5, 5],
            borderWidth: 2,
            tension: 0.2,
            pointRadius: 0
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: isDark ? "#0f172a" : "#1e293b",
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${currSym}${ctx.raw?.toLocaleString()}`
            }
          }
        },
        scales: {
          x: { display: false },
          y: {
            grid: { color: isDark ? "rgba(255, 255, 255, 0.04)" : "rgba(0, 0, 0, 0.04)" },
            ticks: { color: "#64748b", font: { family: "'JetBrains Mono'", size: 10 } }
          }
        }
      }
    });
  }

  // ----------------------------------------------------
  // Render: Accounts & Freeze Toggle
  // ----------------------------------------------------
  function renderAccounts() {
    const container = document.getElementById("accounts-container");
    if (!container) return;

    container.innerHTML = state.accounts.map(acc => {
      const isCard = acc.type === "credit_card";
      return `
        <div class="account-item">
          <div class="acc-info">
            <h4>${acc.name} ${acc.is_frozen ? '<span class="badge danger">LOCKED</span>' : ''}</h4>
            <p>${acc.type.replace('_', ' ').toUpperCase()} • ${acc.account_number_mask}</p>
          </div>
          <div class="acc-meta">
            <span class="acc-balance ${isCard ? 'text-orange' : 'text-emerald'}">
              ${isCard ? '-' : ''}${formatCurrency(acc.balance)}
            </span>
            <button class="btn-freeze ${acc.is_frozen ? 'frozen' : ''}" onclick="toggleAccountFreeze(${acc.id})">
              ${acc.is_frozen ? 'Unlock' : 'Freeze'}
            </button>
          </div>
        </div>
      `;
    }).join("");
  }

  window.toggleAccountFreeze = async function(accId) {
    try {
      const res = await fetch(`/api/accounts/${accId}/toggle-freeze`, { method: "POST" });
      if (res.ok) {
        await fetchAccounts();
        await fetchOverview();
      }
    } catch (err) {
      console.error(err);
    }
  };

  function populateAccountSelects() {
    const select = document.getElementById("tx-account-select");
    const filterSelect = document.getElementById("tx-filter-account");
    if (!select) return;

    select.innerHTML = state.accounts.map(acc => `
      <option value="${acc.id}">${acc.name} (${formatCurrency(acc.balance)})</option>
    `).join("");

    if (filterSelect) {
      filterSelect.innerHTML = '<option value="All">All Accounts</option>' + state.accounts.map(acc => `
        <option value="${acc.id}">${acc.name}</option>
      `).join("");
    }
  }

  // ----------------------------------------------------
  // Render: Transactions Table
  // ----------------------------------------------------
  function renderRecentTransactions() {
    const tbody = document.getElementById("recent-tx-tbody");
    if (!tbody) return;

    const recent = state.transactions.slice(0, 6);
    tbody.innerHTML = recent.map(tx => buildTxRowHtml(tx)).join("");
  }

  function renderAllTransactions() {
    const tbody = document.getElementById("all-tx-tbody");
    if (!tbody) return;

    const searchTerm = document.getElementById("tx-search-input")?.value.toLowerCase() || "";
    const catFilter = document.getElementById("tx-filter-category")?.value || "All";
    const riskFilter = document.getElementById("tx-filter-risk")?.value || "All";
    const accFilter = document.getElementById("tx-filter-account")?.value || "All";

    const filtered = state.transactions.filter(tx => {
      const matchSearch = tx.merchant.toLowerCase().includes(searchTerm) || tx.description.toLowerCase().includes(searchTerm);
      const matchCat = catFilter === "All" || tx.category === catFilter;
      const matchRisk = riskFilter === "All" || tx.risk_level === riskFilter;
      const matchAcc = accFilter === "All" || tx.account_id.toString() === accFilter;
      return matchSearch && matchCat && matchRisk && matchAcc;
    });

    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: #64748b; padding: 24px;">No matching transactions found.</td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map(tx => buildTxRowHtml(tx, true)).join("");
  }

  function buildTxRowHtml(tx, includeStatus = false) {
    const isIncome = tx.type === "income";
    const dateStr = new Date(tx.timestamp).toLocaleString("en-US", {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
    });

    let riskBadgeClass = "safe";
    let riskIcon = "ph-shield-check";
    if (tx.risk_level === "HIGH_RISK") {
      riskBadgeClass = "high_risk";
      riskIcon = "ph-warning-octagon";
    } else if (tx.risk_level === "SUSPICIOUS") {
      riskBadgeClass = "suspicious";
      riskIcon = "ph-warning";
    }

    return `
      <tr>
        <td style="font-family: var(--font-mono); font-size: 12px; color: var(--text-muted);">${dateStr}</td>
        <td>
          <div class="table-merchant">${tx.merchant}</div>
          <div class="table-desc">${tx.description}</div>
        </td>
        <td><span class="category-pill">${tx.category}</span></td>
        <td style="color: var(--text-secondary); font-size: 12px;">${tx.account_name}</td>
        <td style="color: var(--text-muted); font-size: 12px;"><i class="ph ph-map-pin"></i> ${tx.location_city}</td>
        <td style="font-family: var(--font-mono); font-weight: 700; color: ${isIncome ? 'var(--accent-emerald)' : 'var(--text-primary)'};">
          ${isIncome ? '+' : '-'}${formatCurrency(tx.amount)}
        </td>
        <td>
          <span class="risk-badge ${riskBadgeClass}">
            <i class="ph-bold ${riskIcon}"></i> ${tx.risk_score.toFixed(0)} (${tx.risk_level.replace('_', ' ')})
          </span>
        </td>
        ${includeStatus ? `<td><span class="tag">${tx.status.toUpperCase()}</span></td>` : ''}
        <td>
          <button class="btn-ghost-sm" onclick="inspectTransactionRisk(${tx.id})">
            AI Report
          </button>
        </td>
      </tr>
    `;
  }

  window.inspectTransactionRisk = function(txId) {
    const tx = state.transactions.find(t => t.id === txId);
    if (!tx) return;

    const modalBody = document.getElementById("risk-modal-body");
    const reasons = tx.risk_reasons || [];

    modalBody.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 16px;">
        <div>
          <h2 style="font-size: 20px; font-weight: 800; color: var(--text-primary);">${tx.merchant}</h2>
          <p style="color: var(--text-muted); font-size: 13px;">${tx.category} • ${tx.account_name} • ${tx.location_city}</p>
        </div>
        <div style="text-align: right;">
          <div style="font-family: var(--font-mono); font-size: 24px; font-weight: 700; color: var(--text-primary);">
            ${formatCurrency(tx.amount)}
          </div>
          <span class="risk-badge ${tx.risk_level.toLowerCase()}">
            Risk Score: ${tx.risk_score.toFixed(1)} / 100
          </span>
        </div>
      </div>

      <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 12px; color: var(--page-accent);">
        <i class="ph-bold ph-tree-structure"></i> Explainable AI Anomaly Vector Analysis
      </h4>

      ${reasons.length === 0 ? `
        <div style="background-color: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 16px; border-radius: var(--radius-md); color: var(--accent-emerald); font-size: 13px;">
          ✅ <strong>Zero Anomalies Detected:</strong> This transaction conforms with your historical behavioral baseline, geographic location, and usual merchant spending velocity.
        </div>
      ` : `
        <div style="display: flex; flex-direction: column; gap: 10px;">
          ${reasons.map(r => `
            <div style="background-color: rgba(239, 68, 68, 0.08); border: 1px solid var(--border-danger); border-radius: var(--radius-md); padding: 14px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <strong style="color: var(--accent-danger); font-size: 14px;">${r.factor}</strong>
                <span class="badge danger">+${r.score_impact} pts (${r.severity.toUpperCase()})</span>
              </div>
              <p style="font-size: 13px; color: var(--text-primary); line-height: 1.4;">${r.description}</p>
            </div>
          `).join("")}
        </div>
      `}

      <div style="margin-top: 20px; display: flex; justify-content: flex-end; gap: 10px;">
        <button class="btn btn-secondary" onclick="document.getElementById('modal-risk-detail').classList.remove('open')">Close</button>
      </div>
    `;

    document.getElementById("modal-risk-detail").classList.add("open");
  };

  // ----------------------------------------------------
  // Render: Budgets & Subscriptions
  // ----------------------------------------------------
  function renderBudgets() {
    const container = document.getElementById("budgets-container");
    if (!container) return;

    container.innerHTML = state.budgets.map(b => {
      let statusClass = "emerald";
      if (b.status === "warning") statusClass = "orange";
      if (b.status === "exceeded") statusClass = "danger";

      return `
        <div class="budget-item">
          <div class="budget-item-header">
            <span>${b.category}</span>
            <span class="badge ${statusClass}">${b.percentage}% spent</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill ${statusClass}" style="width: ${Math.min(100, b.percentage)}%;"></div>
          </div>
          <div class="budget-amounts">
            <span>Spent: ${formatCurrency(b.current_spent)}</span>
            <span>Limit: ${formatCurrency(b.monthly_limit)}</span>
          </div>
        </div>
      `;
    }).join("");
  }

  function renderSubscriptions() {
    const container = document.getElementById("subscriptions-container");
    if (!container) return;

    container.innerHTML = state.subscriptions.map(sub => `
      <div class="sub-item">
        <div>
          <div class="sub-name">${sub.name}</div>
          <div class="sub-cycle">Bills ${sub.billing_cycle} • Next: ${sub.next_billing_date}</div>
        </div>
        <div style="text-align: right;">
          <div class="sub-amount">${formatCurrency(sub.amount)} / mo</div>
          <button class="btn-ghost-sm" onclick="toggleSubscription(${sub.id})">
            ${sub.is_active ? 'Active (Toggle)' : 'Cancelled'}
          </button>
        </div>
      </div>
    `).join("");
  }

  window.toggleSubscription = async function(subId) {
    try {
      await fetch(`/api/subscriptions/${subId}/toggle-status`, { method: "POST" });
      await fetchSubscriptions();
      await fetchOverview();
    } catch (err) {
      console.error(err);
    }
  };

  // ----------------------------------------------------
  // What-If Wealth Optimizer Logic
  // ----------------------------------------------------
  function initWhatIfChecklist() {
    const container = document.getElementById("what-if-subs-checklist");
    if (!container) return;

    container.innerHTML = `<label style="font-weight: 600; font-size: 13px; margin-bottom: 6px; display: block;">Select Subscriptions to Simulate Cancelling:</label>` + 
      state.subscriptions.map(s => `
        <div class="checklist-item">
          <input type="checkbox" id="wif-sub-${s.id}" value="${s.id}" class="wif-sub-chk">
          <label for="wif-sub-${s.id}">${s.name} (+${formatCurrency(s.amount)}/mo)</label>
        </div>
      `).join("");

    document.querySelectorAll(".wif-sub-chk").forEach(chk => {
      chk.addEventListener("change", runWhatIfCalculation);
    });
  }

  async function runWhatIfCalculation() {
    const diningPct = parseFloat(document.getElementById("slider-dining")?.value || 0);
    const extraSave = parseFloat(document.getElementById("slider-extra")?.value || 0);

    document.getElementById("slider-dining-val").innerText = `${diningPct}%`;
    document.getElementById("slider-extra-val").innerText = `${formatCurrency(extraSave)}/mo`;

    const cancelIds = [];
    document.querySelectorAll(".wif-sub-chk:checked").forEach(chk => {
      cancelIds.push(parseInt(chk.value));
    });

    try {
      const res = await fetch("/api/advisor/what-if", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dining_reduction_pct: diningPct,
          subscriptions_to_cancel_ids: cancelIds,
          custom_monthly_savings: extraSave,
          investment_return_rate: 0.07
        })
      });

      if (!res.ok) return;
      const data = await res.json();

      document.getElementById("wif-monthly-save").innerText = `+${formatCurrency(data.monthly_savings)}/mo`;
      document.getElementById("wif-annual-save").innerText = `+${formatCurrency(data.annual_savings)}/yr`;
      document.getElementById("wif-5yr-wealth").innerText = formatCurrency(data.five_year_savings_compounded);
      document.getElementById("wif-10yr-wealth").innerText = formatCurrency(data.ten_year_savings_compounded);

      const breakdownBox = document.getElementById("wif-breakdown-list");
      breakdownBox.innerHTML = `
        <strong>Simulated Savings Impact:</strong><br>
        ${data.breakdown_details.map(d => `• ${d}`).join("<br>")}
        <br><strong>New Projected Monthly Savings Rate:</strong> ${data.new_projected_savings_rate}%
      `;
    } catch (err) {
      console.error("What-if error:", err);
    }
  }

  // ----------------------------------------------------
  // Render: AI Advisor & Chat
  // ----------------------------------------------------
  function renderInsights() {
    const container = document.getElementById("insights-container");
    if (!container) return;

    container.innerHTML = state.insights.map(ins => `
      <div class="insight-card ${ins.type}">
        <span class="insight-badge">${ins.badge}</span>
        <div class="insight-title">${ins.title}</div>
        <div class="insight-desc">${ins.description}</div>
      </div>
    `).join("");
  }

  async function handleSendChat(customQuery = null) {
    const input = document.getElementById("chat-input");
    const query = customQuery || input.value.trim();
    if (!query) return;

    if (!customQuery) input.value = "";

    const chatContainer = document.getElementById("chat-messages");

    // Append User Message
    chatContainer.innerHTML += `
      <div class="chat-bubble user">
        <p>${escapeHtml(query)}</p>
      </div>
    `;
    chatContainer.scrollTop = chatContainer.scrollHeight;

    // Call API
    try {
      const res = await fetch("/api/advisor/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      });

      if (!res.ok) return;
      const data = await res.json();

      // Format markdown-like bold
      const formattedAnswer = data.answer.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');

      chatContainer.innerHTML += `
        <div class="chat-bubble ai">
          <div class="bubble-header">
            <i class="ph-bold ph-sparkle"></i>
            <strong>Sentinel AI Assistant</strong>
          </div>
          <p>${formattedAnswer}</p>
        </div>
      `;
      chatContainer.scrollTop = chatContainer.scrollHeight;
    } catch (err) {
      console.error("Chat error:", err);
    }
  }

  // ----------------------------------------------------
  // Render: Fraud Security Center & Dispute Handling
  // ----------------------------------------------------
  function renderFraudAlerts() {
    const container = document.getElementById("fraud-alerts-container");
    if (!container) return;

    if (state.fraudAlerts.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; color: #64748b; padding: 32px;">
          <i class="ph ph-shield-check" style="font-size: 36px; color: var(--accent-emerald); margin-bottom: 8px;"></i>
          <p>Zero active security threats. Your transaction history is fully verified.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = state.fraudAlerts.map(alert => {
      const factors = alert.risk_factors || [];
      const isResolved = alert.status !== "active";

      return `
        <div class="alert-item ${isResolved ? 'resolved' : ''}">
          <div class="alert-item-top">
            <div>
              <div class="alert-merchant">${alert.merchant}</div>
              <span style="font-size: 12px; color: var(--text-muted);">${alert.location_city} • ${new Date(alert.timestamp).toLocaleString()}</span>
            </div>
            <div style="text-align: right;">
              <div class="alert-amount">${formatCurrency(alert.amount)}</div>
              <span class="badge danger">Risk: ${alert.risk_score.toFixed(0)}/100</span>
            </div>
          </div>

          <div class="alert-factors">
            ${factors.map(f => `
              <div class="factor-pill">
                <span>⚠️ ${f.factor}: ${f.description}</span>
                <strong>+${f.score_impact}</strong>
              </div>
            `).join("")}
          </div>

          ${!isResolved ? `
            <div class="alert-actions">
              <button class="btn btn-danger-sm" onclick="resolveAlert(${alert.id}, 'confirm_fraud')">
                <i class="ph-bold ph-shield-slash"></i> Confirm Fraud (Refund & Block)
              </button>
              <button class="btn btn-secondary-sm" onclick="resolveAlert(${alert.id}, 'mark_valid')">
                <i class="ph ph-check"></i> Mark Valid (False Positive)
              </button>
              <button class="btn btn-secondary-sm" onclick="resolveAlert(${alert.id}, 'freeze_account')">
                <i class="ph ph-lock"></i> Freeze Card
              </button>
            </div>
          ` : `
            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;">
              Status: <strong>${alert.status.replace('_', ' ').toUpperCase()}</strong> (${alert.notes})
            </div>
          `}
        </div>
      `;
    }).join("");
  }

  window.resolveAlert = async function(alertId, action) {
    try {
      const res = await fetch(`/api/fraud/alerts/${alertId}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, notes: "" })
      });

      if (res.ok) {
        const data = await res.json();
        alert(data.message);
        await fetchAllData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  function renderBlocklist() {
    const container = document.getElementById("blocklist-container");
    if (!container) return;

    if (state.blocklist.length === 0) {
      container.innerHTML = `<p style="color: var(--text-muted); font-size: 13px;">No merchants currently blacklisted.</p>`;
      return;
    }

    container.innerHTML = state.blocklist.map(b => `
      <div style="display: flex; justify-content: space-between; padding: 8px 12px; background-color: var(--bg-card); border-radius: var(--radius-sm); margin-bottom: 6px; font-size: 13px;">
        <strong>🚫 ${b.merchant_name}</strong>
        <span style="color: var(--text-muted);">${b.reason}</span>
      </div>
    `).join("");
  }

  // ----------------------------------------------------
  // Emergency Panic Lockdown System
  // ----------------------------------------------------
  function initPanicLock() {
    const btnPanic = document.getElementById("btn-emergency-panic");
    const modalPanic = document.getElementById("modal-panic-lock");
    const btnClose = document.getElementById("btn-close-panic-modal");
    const btnCancel = document.getElementById("btn-cancel-panic");
    const btnConfirm = document.getElementById("btn-confirm-panic-freeze");

    btnPanic?.addEventListener("click", () => modalPanic?.classList.add("open"));
    btnClose?.addEventListener("click", () => modalPanic?.classList.remove("open"));
    btnCancel?.addEventListener("click", () => modalPanic?.classList.remove("open"));

    btnConfirm?.addEventListener("click", async () => {
      // Freeze all accounts
      for (const acc of state.accounts) {
        if (!acc.is_frozen) {
          await fetch(`/api/accounts/${acc.id}/toggle-freeze`, { method: "POST" });
        }
      }
      modalPanic?.classList.remove("open");
      alert("🚨 EMERGENCY LOCKDOWN ACTIVE: All connected accounts and cards have been frozen!");
      await fetchAllData();
    });
  }

  // ----------------------------------------------------
  // Live Fraud Attack Simulator Sandbox
  // ----------------------------------------------------
  async function triggerSimulation(attackType) {
    const termOutput = document.getElementById("sim-terminal-output");
    
    // Log intent to terminal
    termOutput.innerHTML += `
      <p class="term-line alert">⚡ [ATTACK DISPATCHED] Triggering vector scenario: '${attackType}'...</p>
    `;
    termOutput.scrollTop = termOutput.scrollHeight;

    try {
      const res = await fetch(`/api/simulator/trigger-attack?attack_type=${attackType}`, { method: "POST" });
      if (!res.ok) throw new Error("Simulation failed");

      const tx = await res.json();

      termOutput.innerHTML += `
        <p class="term-line alert">🚨 [INTERCEPTED] Amount: ${formatCurrency(tx.amount)} @ ${tx.merchant}</p>
        <p class="term-line alert">📊 [RISK EVALUATION] Score: ${tx.risk_score}/100 Tier: ${tx.risk_level}</p>
        ${tx.risk_reasons.map(r => `<p class="term-line info">   ↳ Vector: ${r.factor} (${r.severity.toUpperCase()})</p>`).join("")}
        <p class="term-line success">✅ [ACTION] Security alert logged in Fraud Center & account protected.</p>
      `;
      termOutput.scrollTop = termOutput.scrollHeight;

      // Show 2FA challenge modal for high-risk attacks
      if (tx.risk_score >= 70) {
        document.getElementById("modal-2fa-challenge")?.classList.add("open");
      }

      await fetchAllData();
    } catch (err) {
      termOutput.innerHTML += `<p class="term-line alert">❌ Error executing attack simulation.</p>`;
    }
  }

  // ----------------------------------------------------
  // Modals & Forms
  // ----------------------------------------------------
  function initModals() {
    initPanicLock();

    // 2FA Modal close
    document.getElementById("btn-close-2fa-modal")?.addEventListener("click", () => {
      document.getElementById("modal-2fa-challenge")?.classList.remove("open");
    });
    document.getElementById("btn-complete-2fa")?.addEventListener("click", () => {
      document.getElementById("modal-2fa-challenge")?.classList.remove("open");
      alert("✅ 2FA Step-up verification confirmed via hardware key.");
    });

    // Record Transaction Modal
    const modalTx = document.getElementById("modal-transaction");
    document.getElementById("btn-add-transaction")?.addEventListener("click", () => modalTx.classList.add("open"));
    document.getElementById("btn-close-tx-modal")?.addEventListener("click", () => modalTx.classList.remove("open"));
    document.getElementById("btn-cancel-tx")?.addEventListener("click", () => modalTx.classList.remove("open"));

    // Risk Modal
    document.getElementById("btn-close-risk-modal")?.addEventListener("click", () => {
      document.getElementById("modal-risk-detail").classList.remove("open");
    });

    // Budget Modal
    const modalBudget = document.getElementById("modal-budget");
    document.getElementById("btn-add-budget")?.addEventListener("click", () => modalBudget.classList.add("open"));
    document.getElementById("btn-close-budget-modal")?.addEventListener("click", () => modalBudget.classList.remove("open"));
    document.getElementById("btn-cancel-budget")?.addEventListener("click", () => modalBudget.classList.remove("open"));
  }

  function initEventListeners() {
    // Search & Filter listeners
    document.getElementById("tx-search-input")?.addEventListener("input", renderAllTransactions);
    document.getElementById("tx-filter-category")?.addEventListener("change", renderAllTransactions);
    document.getElementById("tx-filter-risk")?.addEventListener("change", renderAllTransactions);
    document.getElementById("tx-filter-account")?.addEventListener("change", renderAllTransactions);
    document.getElementById("fraud-status-filter")?.addEventListener("change", fetchFraudAlerts);

    // Refresh button
    document.getElementById("btn-refresh")?.addEventListener("click", fetchAllData);
    document.getElementById("btn-refresh-insights")?.addEventListener("click", fetchInsights);

    // Simulator attack buttons
    document.querySelectorAll(".btn-simulate").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const type = e.target.getAttribute("data-type");
        triggerSimulation(type);
      });
    });

    // Chat listeners
    document.getElementById("btn-send-chat")?.addEventListener("click", () => handleSendChat());
    document.getElementById("chat-input")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") handleSendChat();
    });

    document.querySelectorAll(".chip").forEach(chip => {
      chip.addEventListener("click", (e) => {
        const query = e.target.getAttribute("data-query");
        handleSendChat(query);
      });
    });

    // Sliders for What-If
    document.getElementById("slider-dining")?.addEventListener("input", runWhatIfCalculation);
    document.getElementById("slider-extra")?.addEventListener("input", runWhatIfCalculation);

    // NLP Natural Language Quick-Add
    const btnNlp = document.getElementById("btn-nlp-submit");
    const inputNlp = document.getElementById("input-nlp-quick-add");

    async function handleNlpQuickAdd() {
      const text = inputNlp?.value.trim();
      if (!text) return;
      try {
        btnNlp.innerText = "Parsing...";
        const res = await fetch("/api/transactions/smart-parse", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text })
        });
        if (res.ok) {
          const newTx = await res.json();
          inputNlp.value = "";
          alert(`✅ NLP Auto-Logged: ${newTx.merchant} (${formatCurrency(newTx.amount)}) under ${newTx.category} • Risk Score: ${newTx.risk_score}/100 (${newTx.risk_level})`);
          await fetchAllData();
          if (newTx.is_flagged) {
            inspectTransactionRisk(newTx.id);
          }
        } else {
          alert("Failed to parse transaction text.");
        }
      } catch (err) {
        console.error(err);
      } finally {
        btnNlp.innerHTML = `<i class="ph-bold ph-plus-circle"></i> Quick Parse & Log`;
      }
    }

    btnNlp?.addEventListener("click", handleNlpQuickAdd);
    inputNlp?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") handleNlpQuickAdd();
    });

    // Form Submit: Transaction
    document.getElementById("form-transaction")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const currRate = CURRENCIES[state.currency]?.rate || 1.0;
      const rawInputAmt = parseFloat(document.getElementById("tx-amount").value);
      // Convert back to base USD for backend storage
      const usdAmount = rawInputAmt / currRate;

      const payload = {
        type: document.getElementById("tx-type").value,
        account_id: parseInt(document.getElementById("tx-account-select").value),
        merchant: document.getElementById("tx-merchant").value,
        amount: usdAmount,
        category: document.getElementById("tx-category").value,
        location_city: document.getElementById("tx-city").value,
        description: document.getElementById("tx-desc").value
      };

      try {
        const res = await fetch("/api/transactions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const err = await res.json();
          alert(`Failed: ${err.detail}`);
          return;
        }

        const newTx = await res.json();
        document.getElementById("modal-transaction").classList.remove("open");
        document.getElementById("form-transaction").reset();
        
        await fetchAllData();

        if (newTx.is_flagged) {
          alert(`⚠️ Alert: This transaction was flagged with a risk score of ${newTx.risk_score}/100.`);
          inspectTransactionRisk(newTx.id);
        }
      } catch (err) {
        console.error(err);
      }
    });

    // Form Submit: Budget
    document.getElementById("form-budget")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const currRate = CURRENCIES[state.currency]?.rate || 1.0;
      const rawLimit = parseFloat(document.getElementById("budget-limit-val").value);
      const usdLimit = rawLimit / currRate;

      const payload = {
        category: document.getElementById("budget-category-select").value,
        monthly_limit: usdLimit
      };

      try {
        const res = await fetch("/api/budgets", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          document.getElementById("modal-budget").classList.remove("open");
          await fetchBudgets();
          await fetchOverview();
        }
      } catch (err) {
        console.error(err);
      }
    });
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
  }
});
