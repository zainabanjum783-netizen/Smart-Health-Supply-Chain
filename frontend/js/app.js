// ==========================================================================
// SMART HEALTH & SUPPLY CHAIN - FRONTEND CONTROLLER (app.js)
// ==========================================================================

const AppState = {
  currentView: 'overview',
  allPhcs: [],
  allMedicines: [],
  selectedPhcId: 'PHC_VAR_01',
  selectedMedId: 'MED_AMOX',
  forecastDays: 7,
  inventoryStatusFilter: 'ALL',
  simFootfallPct: 30,
  simSupplyPct: 20
};

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  await loadOverview();
  await populateGlobalDropdowns();
}

// --- VIEW NAVIGATION ---
window.appSwitchView = function(viewName) {
  AppState.currentView = viewName;

  // Update nav tabs
  document.querySelectorAll('.nav-item').forEach(item => {
    if (item.getAttribute('data-view') === viewName) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  // Switch view section
  document.querySelectorAll('.view-section').forEach(sec => {
    sec.classList.remove('active-view');
  });
  const targetSection = document.getElementById(`view-${viewName}`);
  if (targetSection) {
    targetSection.classList.add('active-view');
  }

  // View specific loaders
  if (viewName === 'overview') {
    loadOverview();
  } else if (viewName === 'dashboard') {
    loadDashboard();
  } else if (viewName === 'inventory') {
    loadInventory();
  } else if (viewName === 'predictions') {
    loadPredictions();
  } else if (viewName === 'actions') {
    loadActions();
  } else if (viewName === 'emergency') {
    loadEmergencyDefaults();
  }
};

// ==========================================================================
// VIEW 1: OVERVIEW
// ==========================================================================
async function loadOverview() {
  try {
    const res = await fetch('/api/overview');
    const data = await res.json();

    const s = data.summary;
    document.getElementById('stat-total-phcs').textContent = s.total_phcs;
    document.getElementById('stat-critical-phcs').textContent = s.critical_phcs;
    document.getElementById('stat-active-alerts').textContent = s.active_alerts;
    document.getElementById('stat-meds-at-risk').textContent = s.medicines_at_risk;
    document.getElementById('stat-high-load-phcs').textContent = s.high_patient_load;
    document.getElementById('stat-predicted-shortages').textContent = s.predicted_shortages;

    // Render Map
    if (window.initPhcMap) {
      window.initPhcMap(data.map_phcs);
    }
  } catch (err) {
    console.error('Error loading overview:', err);
  }
}

// ==========================================================================
// VIEW 2: DASHBOARD
// ==========================================================================
let allDashboardPhcs = [];

async function loadDashboard() {
  try {
    const state = document.getElementById('dash-filter-state').value;
    const district = document.getElementById('dash-filter-district').value;
    const status = document.getElementById('dash-filter-status').value;

    const queryParams = new URLSearchParams();
    if (state) queryParams.append('state', state);
    if (district) queryParams.append('district', district);
    if (status && status !== 'ALL') queryParams.append('status', status);

    const res = await fetch(`/api/phcs?${queryParams.toString()}`);
    const data = await res.json();
    allDashboardPhcs = data.phcs;

    // Populate filter dropdowns if empty
    const stateSelect = document.getElementById('dash-filter-state');
    if (stateSelect.options.length <= 1) {
      data.states.forEach(st => {
        const opt = document.createElement('option');
        opt.value = st;
        opt.textContent = st;
        stateSelect.appendChild(opt);
      });
    }

    const distSelect = document.getElementById('dash-filter-district');
    if (distSelect.options.length <= 1) {
      data.districts.forEach(dst => {
        const opt = document.createElement('option');
        opt.value = dst;
        opt.textContent = dst;
        distSelect.appendChild(opt);
      });
    }

    renderDashboardPhcTable(allDashboardPhcs);

    // Auto-select PHC if set
    if (AppState.selectedPhcId) {
      window.appSelectPhc(AppState.selectedPhcId);
    } else if (allDashboardPhcs.length > 0) {
      window.appSelectPhc(allDashboardPhcs[0].phc_id);
    }
  } catch (err) {
    console.error('Error loading dashboard:', err);
  }
}

function renderDashboardPhcTable(phcs) {
  const tbody = document.getElementById('dash-phc-table-body');
  if (!phcs || phcs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:20px; color:#64748b;">No PHCs found matching selected filters.</td></tr>`;
    return;
  }

  tbody.innerHTML = phcs.map(p => {
    const isSelected = p.phc_id === AppState.selectedPhcId ? 'class="selected-row"' : '';
    const badgeClass = p.overall_status === 'CRITICAL' ? 'badge-critical' : (p.overall_status === 'WARNING' ? 'badge-warning' : 'badge-normal');

    return `
      <tr ${isSelected} id="dash-row-${p.phc_id}">
        <td><strong>${p.phc_name}</strong></td>
        <td>${p.district}</td>
        <td>${p.state}</td>
        <td>${p.today_footfall}/day <span style="font-size:11px; color:#64748b;">(${p.footfall_trend_symbol})</span></td>
        <td>${p.medicine_status_text}</td>
        <td>
          <span class="badge-status ${badgeClass}">
            ${p.overall_symbol} ${p.overall_label}
          </span>
        </td>
        <td>
          <button class="btn-action-sm" onclick="window.appSelectPhc('${p.phc_id}')">Select Facility</button>
        </td>
      </tr>
    `;
  }).join('');
}

window.appFilterDashboard = function() {
  loadDashboard();
};

window.appSearchDashboard = function() {
  const query = document.getElementById('dash-search-input').value.toLowerCase().trim();
  if (!query) {
    renderDashboardPhcTable(allDashboardPhcs);
    return;
  }
  const filtered = allDashboardPhcs.filter(p => 
    p.phc_name.toLowerCase().includes(query) || 
    p.district.toLowerCase().includes(query)
  );
  renderDashboardPhcTable(filtered);
};

window.appSelectPhc = async function(phcId) {
  AppState.selectedPhcId = phcId;

  // Highlight table row
  document.querySelectorAll('#dash-phc-table-body tr').forEach(r => r.classList.remove('selected-row'));
  const row = document.getElementById(`dash-row-${phcId}`);
  if (row) row.classList.add('selected-row');

  try {
    const res = await fetch(`/api/phc/${phcId}`);
    const data = await res.json();
    if (data.error) return;

    const panel = document.getElementById('phc-drilldown-panel');
    panel.style.display = 'block';

    // Header info
    document.getElementById('drill-phc-name').textContent = data.phc.phc_name;
    document.getElementById('drill-phc-district').textContent = `${data.phc.district} District`;
    document.getElementById('drill-phc-state').textContent = data.phc.state;
    document.getElementById('drill-phc-beds').textContent = `${data.phc.total_beds} Hospital Beds`;

    // Overall status badge
    const badgeEl = document.getElementById('drill-overall-badge');
    const badge = data.medicine_metrics.critical_medicines > 0 ? 
      { class: 'badge-critical', label: 'Critical Alert 🔴' } : 
      (data.medicine_metrics.warning_medicines > 0 ? { class: 'badge-warning', label: 'Warning 🟡' } : { class: 'badge-normal', label: 'Normal 🟢' });
    badgeEl.innerHTML = `<span class="badge-status ${badge.class}">${badge.label}</span>`;

    // Patient Footfall Cards
    const pm = data.patient_metrics;
    document.getElementById('drill-footfall-today').textContent = `${pm.today_patients}/day`;
    document.getElementById('drill-footfall-avg7').textContent = `${pm.avg_daily_patients}/day`;
    document.getElementById('drill-footfall-trend7').textContent = `${pm.trend_7d_pct > 0 ? '+' : ''}${pm.trend_7d_pct}%`;
    document.getElementById('drill-footfall-trend7-lbl').textContent = pm.trend_7d_symbol;
    document.getElementById('drill-footfall-trend30').textContent = `${pm.trend_30d_pct > 0 ? '+' : ''}${pm.trend_30d_pct}%`;

    // Medicine Status Cards
    const mm = data.medicine_metrics;
    document.getElementById('drill-meds-total').textContent = mm.total_medicines_in_stock;
    document.getElementById('drill-meds-warning').textContent = mm.approaching_shortage;
    document.getElementById('drill-meds-critical').textContent = mm.critical_medicines;
    document.getElementById('drill-meds-expiring').textContent = mm.medicines_nearing_expiry;

    // Render Charts
    if (window.renderDashboardFootfallChart) {
      window.renderDashboardFootfallChart('chart-drill-footfall', pm.history_30d);
    }
    if (window.renderDashboardConsumptionChart) {
      window.renderDashboardConsumptionChart('chart-drill-consumption', data.top_usage_series);
    }
    if (window.renderDashboardStockBarChart) {
      window.renderDashboardStockBarChart('chart-drill-stock', mm.inventory);
    }

    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (err) {
    console.error('Error fetching PHC detail:', err);
  }
};

window.appSelectPhcAndGoToDashboard = function(phcId) {
  AppState.selectedPhcId = phcId;
  window.appSwitchView('dashboard');
};

// ==========================================================================
// VIEW 3: INVENTORY
// ==========================================================================
let inventoryDebounceTimer = null;

window.appFilterInventory = function() {
  clearTimeout(inventoryDebounceTimer);
  inventoryDebounceTimer = setTimeout(loadInventory, 250);
};

window.appSetInventoryStatus = function(status, btnElement) {
  AppState.inventoryStatusFilter = status;
  document.querySelectorAll('#view-inventory .btn-filter-pill').forEach(b => b.classList.remove('active'));
  btnElement.classList.add('active');
  loadInventory();
};

async function loadInventory() {
  const medQuery = document.getElementById('inv-search-medicine').value.trim();
  const phcQuery = document.getElementById('inv-search-phc').value.trim();
  const status = AppState.inventoryStatusFilter;

  const params = new URLSearchParams();
  if (medQuery) params.append('search_medicine', medQuery);
  if (phcQuery) params.append('search_phc', phcQuery);
  if (status && status !== 'ALL') params.append('status', status);

  try {
    const res = await fetch(`/api/inventory?${params.toString()}`);
    const data = await res.json();
    renderInventoryTable(data.items);
  } catch (err) {
    console.error('Error loading inventory:', err);
  }
}

function renderInventoryTable(items) {
  const tbody = document.getElementById('inv-table-body');
  if (!items || items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:24px; color:#64748b;">No inventory records match your search criteria.</td></tr>`;
    return;
  }

  tbody.innerHTML = items.map(item => {
    const badgeClass = item.status.code === 'CRITICAL' ? 'badge-critical' : (item.status.code === 'WARNING' ? 'badge-warning' : 'badge-normal');
    const expiryWarning = item.is_nearing_expiry ? `<div class="badge-expiry" style="margin-top:4px;">⏳ Expiring Soon (${item.days_to_expiry}d)</div>` : '';

    return `
      <tr>
        <td><strong>${item.phc_name}</strong></td>
        <td>${item.district}</td>
        <td><strong>${item.medicine_name}</strong></td>
        <td><span style="font-size:11px; color:#64748b;">${item.category}</span></td>
        <td><strong>${item.current_stock.toLocaleString()}</strong> ${item.unit}</td>
        <td>${item.average_daily_usage} /day</td>
        <td>
          <strong style="color: ${item.status.code === 'CRITICAL' ? '#dc2626' : (item.status.code === 'WARNING' ? '#d97706' : '#16a34a')};">
            ${item.days_remaining} days
          </strong>
        </td>
        <td>
          <div>${item.expiry_date}</div>
          ${expiryWarning}
        </td>
        <td>
          <span class="badge-status ${badgeClass}">
            ${item.status.symbol} ${item.status.label}
          </span>
        </td>
      </tr>
    `;
  }).join('');
}

// ==========================================================================
// VIEW 4: PREDICTIONS
// ==========================================================================
async function populateGlobalDropdowns() {
  try {
    const resPhcs = await fetch('/api/phcs');
    const dataPhcs = await resPhcs.json();
    AppState.allPhcs = dataPhcs.phcs;

    const selectPhc = document.getElementById('pred-select-phc');
    selectPhc.innerHTML = dataPhcs.phcs.map(p => 
      `<option value="${p.phc_id}" ${p.phc_id === AppState.selectedPhcId ? 'selected' : ''}>${p.phc_name} (${p.district})</option>`
    ).join('');

    // Pre-select Varanasi Central as default demo showcase
    if (!AppState.selectedPhcId) {
      AppState.selectedPhcId = 'PHC_VAR_01';
      selectPhc.value = 'PHC_VAR_01';
    }

    // Medicine options
    const medicinesList = [
      { id: "MED_AMOX", name: "Amoxicillin 500mg" },
      { id: "MED_PARA", name: "Paracetamol 500mg" },
      { id: "MED_ORS", name: "Oral Rehydration Salts (ORS)" },
      { id: "MED_AZI", name: "Azithromycin 500mg" },
      { id: "MED_METF", name: "Metformin 500mg" },
      { id: "MED_AMLO", name: "Amlodipine 5mg" },
      { id: "MED_IBUP", name: "Ibuprofen 400mg" },
      { id: "MED_CEFT", name: "Ceftriaxone 1g Injection" },
      { id: "MED_SALB", name: "Salbutamol Inhaler 100mcg" },
      { id: "MED_IFA", name: "Iron & Folic Acid (IFA)" },
      { id: "MED_RAB", name: "Anti-Rabies Vaccine" },
      { id: "MED_ASV", name: "Polyvalent Anti-Snake Venom" }
    ];
    AppState.allMedicines = medicinesList;

    const selectMed = document.getElementById('pred-select-medicine');
    selectMed.innerHTML = medicinesList.map(m => 
      `<option value="${m.id}" ${m.id === AppState.selectedMedId ? 'selected' : ''}>${m.name}</option>`
    ).join('');
  } catch (err) {
    console.error('Error populating dropdowns:', err);
  }
}

window.appSetForecastDays = function(days, btnElement) {
  AppState.forecastDays = days;
  document.querySelectorAll('#view-predictions .btn-period').forEach(b => b.classList.remove('active'));
  btnElement.classList.add('active');
  window.appLoadPrediction();
};

async function loadPredictions() {
  const phcSelect = document.getElementById('pred-select-phc');
  const medSelect = document.getElementById('pred-select-medicine');
  if (phcSelect.value) AppState.selectedPhcId = phcSelect.value;
  if (medSelect.value) AppState.selectedMedId = medSelect.value;

  window.appLoadPrediction();
}

window.appLoadPrediction = async function() {
  const phcId = document.getElementById('pred-select-phc').value || AppState.selectedPhcId;
  const medId = document.getElementById('pred-select-medicine').value || AppState.selectedMedId;
  const forecastDays = AppState.forecastDays || 7;

  try {
    const res = await fetch(`/api/predictions?phc_id=${phcId}&medicine_id=${medId}&forecast_days=${forecastDays}`);
    const data = await res.json();
    if (data.error) return;

    const pred = data.prediction;
    const phc = data.phc;
    const med = data.medicine;

    // Shortage Status Banner
    const banner = document.getElementById('pred-status-banner');
    const statusIcon = document.getElementById('pred-status-icon');
    const statusText = document.getElementById('pred-status-text');
    
    if (pred.shortage_expected) {
      banner.className = 'shortage-banner critical-banner';
      statusIcon.textContent = '🔴';
      statusText.textContent = `CRITICAL SHORTAGE EXPECTED WITHIN ${pred.days_remaining} DAYS`;
    } else {
      banner.className = 'shortage-banner safe-banner';
      statusIcon.textContent = '🟢';
      statusText.textContent = `ADEQUATE STOCK BUFFER (${pred.days_remaining} DAYS REMAINING)`;
    }

    document.getElementById('pred-banner-stock').textContent = `${pred.current_stock.toLocaleString()} ${med.unit}`;
    document.getElementById('pred-banner-usage').textContent = `${pred.adjusted_daily_demand} ${med.unit}`;
    document.getElementById('pred-banner-days').textContent = `${pred.days_remaining} days`;
    document.getElementById('pred-banner-date').textContent = pred.shortage_date;

    // Patient Footfall Forecast metrics
    const ps = pred.patient_stats;
    document.getElementById('pred-footfall-today').textContent = `${ps.today_footfall}/day`;
    document.getElementById('pred-footfall-avg').textContent = `${ps.avg_7d}/day`;
    document.getElementById('pred-footfall-tomorrow').textContent = `${ps.expected_tomorrow}/day`;
    
    const trendBadge = document.getElementById('pred-trend-badge');
    trendBadge.textContent = ps.trend_symbol;
    trendBadge.className = ps.trend_direction === 'increasing' ? 'badge-status badge-warning' : (ps.trend_direction === 'decreasing' ? 'badge-status badge-normal' : 'badge-status');

    // Footfall to Medicine coupling card
    document.getElementById('pred-coupling-footfall-pct').textContent = `${ps.trend_pct > 0 ? '+' : ''}${ps.trend_pct}%`;
    document.getElementById('pred-coupling-demand').textContent = `${pred.adjusted_daily_demand} ${med.unit}/day`;
    
    const stepsList = document.getElementById('pred-formula-steps');
    stepsList.innerHTML = `
      <li>${pred.formula_explanation.step1}</li>
      <li>${pred.formula_explanation.step2}</li>
      <li><strong>Coupling:</strong> ${pred.formula_explanation.step3}</li>
      <li>${pred.formula_explanation.step4}</li>
      <li><strong>Stockout Horizon:</strong> ${pred.formula_explanation.step5} &rarr; Projected zero stock on <strong>${pred.shortage_date}</strong></li>
    `;

    // 7-day Historical Breakdown table
    document.getElementById('pred-base-avg-label').textContent = `Base 7-day Avg: ${pred.base_daily_consumption} ${med.unit}/day`;
    const breakdownBody = document.getElementById('pred-usage-breakdown-body');
    breakdownBody.innerHTML = data.usage_breakdown_7d.map(item => `
      <tr>
        <td><strong>${item.day}</strong></td>
        <td>${item.date}</td>
        <td><strong>${item.quantity}</strong> ${med.unit}</td>
      </tr>
    `).join('');

    // Charts
    if (window.renderPredictionFootfallChart) {
      window.renderPredictionFootfallChart('chart-pred-footfall', data.patient_timeline);
    }
    if (window.renderStockDepletionChart) {
      window.renderStockDepletionChart('chart-pred-depletion', data.depletion_series);
    }
  } catch (err) {
    console.error('Error loading prediction:', err);
  }
};

// ==========================================================================
// VIEW 5: ACTIONS
// ==========================================================================
let currentActionRecommendations = [];

async function loadActions() {
  try {
    const res = await fetch('/api/actions');
    const data = await res.json();
    currentActionRecommendations = data.redistributions;

    renderRedistributionCards(data.redistributions);
    renderPatientLoadAlerts(data.patient_load_alerts);
    renderActionHistory(data.action_history);
  } catch (err) {
    console.error('Error loading actions:', err);
  }
}

function renderRedistributionCards(items) {
  const container = document.getElementById('actions-redistribution-grid');
  if (!items || items.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:30px; text-align:center; color:#64748b;">
        🟢 No imminent medicine stockouts detected across the network. All facilities maintain adequate safe buffers.
      </div>
    `;
    return;
  }

  container.innerHTML = items.map((item, idx) => `
    <div class="action-card">
      <div>
        <div class="action-header">
          <span class="action-badge">${item.medicine.medicine_name}</span>
          <span style="font-size:12px; font-weight:600; color:#dc2626;">Urgency: ${item.urgency}</span>
        </div>

        <div class="redistribution-boxes">
          <!-- Source (Surplus) -->
          <div class="node-box source-box">
            <div class="node-type">🟢 Source (Surplus)</div>
            <div class="node-name">${item.source.phc_name}</div>
            <div class="node-meta">
              District: ${item.source.district}<br>
              Stock: <strong>${item.source.current_stock}</strong> ${item.medicine.unit}<br>
              Surplus: <strong>+${item.source.surplus}</strong>
            </div>
          </div>

          <div class="transfer-arrow">&rarr;</div>

          <!-- Destination (Shortage) -->
          <div class="node-box dest-box">
            <div class="node-type">🔴 Dest (Deficit)</div>
            <div class="node-name">${item.destination.phc_name}</div>
            <div class="node-meta">
              District: ${item.destination.district}<br>
              Stock: <strong>${item.destination.current_stock}</strong> ${item.medicine.unit}<br>
              Shortage: <strong>-${item.destination.shortage}</strong>
            </div>
          </div>
        </div>

        <div class="transfer-recommendation-box">
          Recommended Action:<br>
          <strong>Transfer ${item.recommended_quantity} ${item.medicine.unit}</strong><br>
          <span style="font-size:11px; color:#64748b;">${item.source.phc_name} &rarr; ${item.destination.phc_name} (${item.distance_km} km distance)</span>
        </div>
      </div>

      <div class="action-footer">
        <button class="btn-outline" onclick="window.appViewActionDetails(${idx})">View Details</button>
        <button class="btn-approve" onclick="window.appApproveTransfer(${idx})">✓ Approve Transfer</button>
      </div>
    </div>
  `).join('');
}

function renderPatientLoadAlerts(alerts) {
  const container = document.getElementById('actions-patient-load-list');
  if (!alerts || alerts.length === 0) {
    container.innerHTML = `
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:20px; text-align:center; color:#64748b;">
        🟢 No facility experiencing patient surges above normal capacity thresholds.
      </div>
    `;
    return;
  }

  container.innerHTML = alerts.map(a => {
    const nearbyHtml = a.nearby_phcs.length > 0 ? a.nearby_phcs.map(n => `
      <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:6px; padding:8px 12px; margin-top:6px; display:flex; justify-content:space-between; align-items:center;">
        <div>
          <strong>${n.phc_name}</strong> (${n.district}) &bull; <span style="color:#64748b;">${n.distance_km} km away</span>
        </div>
        <div>
          <span style="font-size:11px; color:#15803d; font-weight:700;">Avg Load: ${n.avg_patients}/day | ${n.total_beds} Beds Available</span>
        </div>
      </div>
    `).join('') : '<div style="color:#64748b; font-size:11px;">No nearby under-utilized PHC identified within 35km.</div>';

    return `
      <div class="patient-load-card">
        <div class="pl-header">
          <div class="pl-title">
            <span>⚠️ HIGH PATIENT LOAD SURGE &bull; ${a.phc_name} (${a.district})</span>
          </div>
          <span class="badge-status badge-warning">+${a.increase_pct}% Surge</span>
        </div>

        <div class="pl-details">
          <div>Baseline Average: <strong>${a.current_avg} patients/day</strong></div>
          <div>Today's Footfall: <strong>${a.today_footfall} patients</strong></div>
          <div>Predicted Load: <strong style="color:#c2410c;">${a.predicted_load} patients/day</strong></div>
        </div>

        <div class="pl-redirect-box">
          <strong style="color:#0f172a;">Informational Action Recommendation:</strong><br>
          ${a.recommendation_text}
          <div style="margin-top:8px;">
            <strong style="font-size:11px; text-transform:uppercase; color:#64748b;">Nearby Alternative Facilities with Available Capacity:</strong>
            ${nearbyHtml}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function renderActionHistory(history) {
  const tbody = document.getElementById('actions-history-body');
  if (!history || history.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:20px; color:#64748b;">No transfers executed yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = history.map(h => `
    <tr>
      <td><span style="font-size:12px; color:#64748b;">${h.timestamp}</span></td>
      <td><strong>${h.source_phc_name}</strong></td>
      <td><strong>${h.dest_phc_name}</strong></td>
      <td>${h.medicine_name}</td>
      <td><strong style="color:#15803d;">+${h.quantity} ${h.unit}</strong></td>
      <td><span class="badge-status badge-normal">✓ ${h.status}</span></td>
      <td style="font-size:12px; color:#475569;">${h.rationale}</td>
    </tr>
  `).join('');
}

window.appViewActionDetails = function(index) {
  const item = currentActionRecommendations[index];
  if (!item) return;

  const modal = document.getElementById('modal-details');
  document.getElementById('modal-title').textContent = `Redistribution Details: ${item.medicine.medicine_name}`;

  document.getElementById('modal-body').innerHTML = `
    <div style="font-size:13px; line-height:1.7;">
      <p style="margin-bottom:12px;"><strong>Optimization Rationale:</strong> Destination facility is facing an imminent stockout with only <strong>${item.destination.days_remaining} days</strong> of inventory remaining. The source facility holds a healthy surplus above its 10-day safety reserve.</p>
      
      <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:14px; margin-bottom:14px;">
        <div style="margin-bottom:8px;"><strong>Source Facility:</strong> ${item.source.phc_name} (${item.source.district})</div>
        <div>Current Stock: ${item.source.current_stock} ${item.medicine.unit}</div>
        <div>10-Day Reserve Buffer: ${item.source.expected_demand} ${item.medicine.unit}</div>
        <div>Surplus Available for Transfer: <span style="color:#15803d; font-weight:700;">${item.source.surplus} ${item.medicine.unit}</span></div>
      </div>

      <div style="background:#fef2f2; border:1px solid #fecaca; border-radius:8px; padding:14px; margin-bottom:14px;">
        <div style="margin-bottom:8px;"><strong>Destination Facility:</strong> ${item.destination.phc_name} (${item.destination.district})</div>
        <div>Current Stock: ${item.destination.current_stock} ${item.medicine.unit}</div>
        <div>Target 7-Day Stock Buffer: ${item.destination.expected_demand} ${item.medicine.unit}</div>
        <div>Deficit to Cover: <span style="color:#dc2626; font-weight:700;">${item.destination.shortage} ${item.medicine.unit}</span></div>
      </div>

      <div style="background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:12px; margin-bottom:16px;">
        <strong>Recommended Transfer Amount:</strong> ${item.recommended_quantity} ${item.medicine.unit}<br>
        <strong>Geographic Transit Distance:</strong> ${item.distance_km} km
      </div>

      <div style="display:flex; justify-content:flex-end; gap:10px;">
        <button class="btn-outline" onclick="window.appCloseModal()">Close</button>
        <button class="btn-approve" onclick="window.appApproveTransfer(${index}); window.appCloseModal();">Approve & Execute Now</button>
      </div>
    </div>
  `;

  modal.classList.add('active');
};

window.appCloseModal = function() {
  document.getElementById('modal-details').classList.remove('active');
};

window.appApproveTransfer = async function(index) {
  const item = currentActionRecommendations[index];
  if (!item) return;

  try {
    const res = await fetch('/api/actions/transfer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_phc_id: item.source.phc_id,
        dest_phc_id: item.destination.phc_id,
        medicine_id: item.medicine.medicine_id,
        quantity: item.recommended_quantity
      })
    });

    const data = await res.json();
    if (data.success) {
      showToast(`Transfer Approved! ${item.recommended_quantity} ${item.medicine.unit} dispatched from ${item.source.phc_name} to ${item.destination.phc_name}.`, 'success');
      // Refresh actions list and background overview data
      loadActions();
      loadOverview();
    } else {
      showToast(data.error || 'Failed to approve transfer', 'error');
    }
  } catch (err) {
    showToast('Transfer request failed: ' + err.message, 'error');
  }
};

// ==========================================================================
// VIEW 6: EMERGENCY SIMULATION CENTER
// ==========================================================================
window.appSetSimFootfall = function(pct, btnElement) {
  AppState.simFootfallPct = pct;
  document.querySelectorAll('.sim-var-box:first-child .btn-sim-option').forEach(b => b.classList.remove('active'));
  btnElement.classList.add('active');
};

window.appSetSimSupply = function(pct, btnElement) {
  AppState.simSupplyPct = pct;
  document.querySelectorAll('.sim-var-box:nth-child(2) .btn-sim-option').forEach(b => b.classList.remove('active-supply'));
  btnElement.classList.add('active-supply');
};

function loadEmergencyDefaults() {
  window.appRunEmergencySimulation();
}

window.appRunEmergencySimulation = async function() {
  const footfallPct = AppState.simFootfallPct;
  const supplyPct = AppState.simSupplyPct;

  try {
    const res = await fetch('/api/emergency/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        footfall_increase_pct: footfallPct,
        supply_reduction_pct: supplyPct
      })
    });

    const data = await res.json();
    const imp = data.impact_summary;

    // Impact Summary Numbers (Dynamic from mathematical calculations)
    document.getElementById('sim-impact-phcs').textContent = `${imp.phcs_at_risk_count} PHCs`;
    document.getElementById('sim-impact-load').textContent = `${imp.high_patient_load_count} PHCs`;
    document.getElementById('sim-impact-meds').textContent = `${imp.medicines_at_risk_count} Formularies`;

    // Example Box values demonstrating patient -> demand -> stock coupling
    const normalPatients = 300;
    const simPatients = Math.round(normalPatients * (1 + footfallPct / 100));
    const normalMedDemand = 100;
    const simMedDemand = Math.round(normalMedDemand * (1 + footfallPct / 100));
    const normalStock = 500;
    const simStock = Math.round(normalStock * (1 - supplyPct / 100));
    const simDays = (simStock / simMedDemand).toFixed(1);

    document.getElementById('sim-ex-patient').textContent = `${simPatients}/day (+${footfallPct}%)`;
    document.getElementById('sim-ex-demand').textContent = `${simMedDemand}/day`;
    document.getElementById('sim-ex-stock').textContent = `${simStock} units (-${supplyPct}%)`;
    document.getElementById('sim-ex-days').textContent = `${simDays} days (${simDays < 3 ? '🔴 Critical' : (simDays < 7 ? '🟡 Warning' : '🟢 Normal')})`;

    // Comparison Chart
    if (window.renderEmergencyComparisonChart) {
      window.renderEmergencyComparisonChart('chart-emergency-comparison', imp);
    }

    // Crisis Redistribution Recommendations
    renderEmergencyActions(data.emergency_recommendations);
    showToast(`Simulation executed: Footfall Surge +${footfallPct}%, Supply Disruption -${supplyPct}%`, 'success');
  } catch (err) {
    console.error('Error running emergency simulation:', err);
  }
};

function renderEmergencyActions(actions) {
  const container = document.getElementById('sim-emergency-actions-grid');
  if (!actions || actions.length === 0) {
    container.innerHTML = `<div style="grid-column: 1/-1; background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:20px; text-align:center; color:#64748b;">No emergency redistributions required under current parameters.</div>`;
    return;
  }

  container.innerHTML = actions.slice(0, 8).map((item) => `
    <div class="action-card" style="border-top: 4px solid #ef4444;">
      <div>
        <div class="action-header">
          <span class="action-badge" style="background:#fee2e2; color:#b91c1c;">🚨 Crisis Action: ${item.medicine.medicine_name}</span>
          <span style="font-size:11px; font-weight:700; color:#dc2626; text-transform:uppercase;">Urgency: ${item.urgency}</span>
        </div>

        <div style="font-size:13px; line-height:1.6; margin-bottom:12px;">
          <div style="margin-bottom:8px;">
            <strong>Medicine:</strong> ${item.medicine.medicine_name}<br>
            <strong>Recommended Quantity:</strong> <span style="color:#b91c1c; font-weight:800; font-size:14px;">${item.recommended_quantity} ${item.medicine.unit}</span>
          </div>

          <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:8px 10px; margin-bottom:8px;">
            <div><strong>Source PHC (Surplus):</strong> 🟢 ${item.source.phc_name} (${item.source.district}) &bull; Stock: ${item.source.current_stock}</div>
            <div><strong>Destination PHC (Deficit):</strong> 🔴 ${item.destination.phc_name} (${item.destination.district}) &bull; Stock: ${item.destination.current_stock}</div>
            <div><strong>Transit Distance:</strong> ${item.distance_km} km</div>
          </div>

          <div style="font-size:12px; color:#475569; background:#fff1f2; border:1px solid #fecdd3; border-radius:4px; padding:6px 10px;">
            <strong>Crisis Reason:</strong> ${item.reason}
          </div>
        </div>
      </div>

      <div class="action-footer">
        <button class="btn-approve" onclick="window.appApproveCrisisAction('${item.source.phc_id}', '${item.destination.phc_id}', '${item.medicine.medicine_id}', ${item.recommended_quantity})">
          ⚡ Execute Emergency Dispatch (${item.recommended_quantity} ${item.medicine.unit})
        </button>
      </div>
    </div>
  `).join('');
}

window.appApproveCrisisAction = async function(srcId, dstId, medId, qty) {
  try {
    const res = await fetch('/api/actions/transfer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_phc_id: srcId,
        dest_phc_id: dstId,
        medicine_id: medId,
        quantity: qty
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Emergency dispatch of ${qty} units completed successfully!`, 'success');
      window.appRunEmergencySimulation();
      loadOverview();
      loadActions();
    }
  } catch (err) {
    showToast('Failed to execute emergency dispatch: ' + err.message, 'error');
  }
};

// ==========================================================================
// RESET DEMO DATA
// ==========================================================================
window.appResetDatabase = async function() {
  if (!confirm('Are you sure you want to reset the database to the initial synthetic hackathon state?')) {
    return;
  }
  try {
    const res = await fetch('/api/reset', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      // Reset simulation state variables
      AppState.simFootfallPct = 30;
      AppState.simSupplyPct = 20;
      AppState.inventoryStatusFilter = 'ALL';

      // Restore active option buttons in Emergency UI
      document.querySelectorAll('.sim-var-box:first-child .btn-sim-option').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.sim-var-box:nth-child(2) .btn-sim-option').forEach(b => b.classList.remove('active-supply'));
      const defFootfall = document.querySelectorAll('.sim-var-box:first-child .btn-sim-option')[3];
      if (defFootfall) defFootfall.classList.add('active');
      const defSupply = document.querySelectorAll('.sim-var-box:nth-child(2) .btn-sim-option')[2];
      if (defSupply) defSupply.classList.add('active-supply');

      showToast('Database reset to initial demo state successfully!', 'success');
      window.appSwitchView(AppState.currentView);
    }
  } catch (err) {
  }
};

// ==========================================================================
// TOAST SYSTEM
// ==========================================================================
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✓' : '⚠️'}</span>
    <span>${message}</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
