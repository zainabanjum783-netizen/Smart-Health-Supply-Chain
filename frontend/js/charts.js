// ==========================================================================
// SMART HEALTH & SUPPLY CHAIN - CHART RENDERING HELPERS (Chart.js)
// ==========================================================================

const chartInstances = {};

function destroyChart(canvasId) {
  if (chartInstances[canvasId]) {
    chartInstances[canvasId].destroy();
    delete chartInstances[canvasId];
  }
}

/**
 * Renders historical patient footfall with moving average on Dashboard
 */
function renderDashboardFootfallChart(canvasId, historyData) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const labels = historyData.map(d => {
    const parts = d.date.split("-");
    return `${parts[2]}/${parts[1]}`;
  });
  const opdValues = historyData.map(d => d.opd);
  const ipdValues = historyData.map(d => d.ipd);
  const movingAvg = historyData.map(d => d.moving_avg);

  chartInstances[canvasId] = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "7-Day Moving Average",
          data: movingAvg,
          borderColor: "#0d9488",
          backgroundColor: "transparent",
          borderWidth: 3,
          tension: 0.3,
          pointRadius: 0
        },
        {
          label: "OPD Patients",
          data: opdValues,
          borderColor: "#3b82f6",
          backgroundColor: "rgba(59, 130, 246, 0.1)",
          borderWidth: 1.5,
          fill: true,
          tension: 0.2,
          pointRadius: 2
        },
        {
          label: "IPD Patients",
          data: ipdValues,
          borderColor: "#8b5cf6",
          backgroundColor: "transparent",
          borderWidth: 1.5,
          borderDash: [4, 4],
          tension: 0.2,
          pointRadius: 1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "top", labels: { font: { size: 11 } } },
        tooltip: { padding: 10 }
      },
      scales: {
        y: { beginAtZero: false, grid: { color: "#f1f5f9" } },
        x: { grid: { display: false } }
      }
    }
  });
}

/**
 * Renders multi-line medicine consumption trend on Dashboard
 */
function renderDashboardConsumptionChart(canvasId, usageSeries) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const colors = ["#2563eb", "#dc2626", "#16a34a", "#d97706", "#9333ea"];
  const datasets = [];
  let labels = [];

  const medKeys = Object.keys(usageSeries);
  medKeys.slice(0, 4).forEach((medId, idx) => {
    const list = usageSeries[medId];
    if (labels.length === 0) {
      labels = list.map(item => {
        const parts = item.date.split("-");
        return `${parts[2]}/${parts[1]}`;
      });
    }
    datasets.push({
      label: medId.replace("MED_", ""),
      data: list.map(item => item.quantity),
      borderColor: colors[idx % colors.length],
      backgroundColor: "transparent",
      borderWidth: 2,
      tension: 0.3,
      pointRadius: 1
    });
  });

  chartInstances[canvasId] = new Chart(ctx, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "top", labels: { font: { size: 11 } } }
      },
      scales: {
        y: { beginAtZero: true, grid: { color: "#f1f5f9" } },
        x: { grid: { display: false } }
      }
    }
  });
}

/**
 * Renders Horizontal Bar Chart of medicine stock on Dashboard
 */
function renderDashboardStockBarChart(canvasId, inventoryItems) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const topItems = inventoryItems.slice(0, 8);
  const labels = topItems.map(i => i.medicine_name.length > 20 ? i.medicine_name.slice(0, 18) + '…' : i.medicine_name);
  const stockData = topItems.map(i => i.current_stock);
  const bgColors = topItems.map(i => {
    if (i.days_remaining < 3) return "rgba(220, 38, 38, 0.85)";
    if (i.days_remaining < 7) return "rgba(217, 119, 6, 0.85)";
    return "rgba(22, 163, 74, 0.85)";
  });

  chartInstances[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Current Stock Units",
        data: stockData,
        backgroundColor: bgColors,
        borderRadius: 4
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            afterLabel: function(context) {
              const item = topItems[context.dataIndex];
              return `Days Remaining: ${item.days_remaining}d (${item.status.label})`;
            }
          }
        }
      },
      scales: {
        x: { grid: { color: "#f1f5f9" } },
        y: { grid: { display: false } }
      }
    }
  });
}

/**
 * Predictions: Historical Patient Footfall -> Tomorrow Forecast
 */
function renderPredictionFootfallChart(canvasId, timeline) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const labels = timeline.map(t => {
    const p = t.date.split("-");
    return t.type === "forecast" ? `Tomorrow (${p[2]}/${p[1]})` : `${p[2]}/${p[1]}`;
  });

  const historicalValues = timeline.map(t => t.type === "historical" ? t.value : null);
  const forecastValues = timeline.map((t, idx) => {
    if (t.type === "forecast") return t.value;
    if (idx === timeline.length - 2) return t.value; // connect line
    return null;
  });

  chartInstances[canvasId] = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Historical Footfall",
          data: historicalValues,
          borderColor: "#2563eb",
          backgroundColor: "rgba(37, 99, 235, 0.08)",
          borderWidth: 2.5,
          fill: true,
          tension: 0.2,
          pointRadius: 3
        },
        {
          label: "Statistical Forecast Tomorrow",
          data: forecastValues,
          borderColor: "#f59e0b",
          borderDash: [5, 5],
          backgroundColor: "transparent",
          borderWidth: 2.5,
          pointRadius: 5,
          pointBackgroundColor: "#f59e0b"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "top", labels: { font: { size: 11 } } }
      },
      scales: {
        y: { beginAtZero: false, grid: { color: "#f1f5f9" } },
        x: { grid: { display: false } }
      }
    }
  });
}

/**
 * Predictions: Projected Stock Depletion Timeline
 */
function renderStockDepletionChart(canvasId, depletionSeries) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const labels = depletionSeries.map(d => d.day_label);
  const data = depletionSeries.map(d => d.projected_stock);

  chartInstances[canvasId] = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "Projected Remaining Stock",
        data: data,
        borderColor: "#e11d48",
        backgroundColor: "rgba(225, 29, 72, 0.1)",
        borderWidth: 2.5,
        fill: true,
        tension: 0.1,
        pointRadius: 4,
        pointBackgroundColor: "#e11d48"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top", labels: { font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: function(context) {
              return `Projected Stock: ${context.raw} units`;
            }
          }
        }
      },
      scales: {
        y: { beginAtZero: true, grid: { color: "#f1f5f9" } },
        x: { grid: { display: false } }
      }
    }
  });
}

/**
 * Emergency Simulation: Impact Comparison Chart
 */
function renderEmergencyComparisonChart(canvasId, impactData) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  chartInstances[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Critical Shortages (<3d)", "Warning Shortages (<7d)"],
      datasets: [
        {
          label: "Normal Conditions",
          data: [impactData.critical_stockouts_before, impactData.warning_stockouts_before],
          backgroundColor: "#94a3b8",
          borderRadius: 4
        },
        {
          label: "Crisis Simulation",
          data: [impactData.critical_stockouts_after, impactData.warning_stockouts_after],
          backgroundColor: "#ef4444",
          borderRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top", labels: { font: { size: 12 } } }
      },
      scales: {
        y: { beginAtZero: true, grid: { color: "#f1f5f9" } },
        x: { grid: { display: false } }
      }
    }
  });
}
