// ==========================================================================
// SMART HEALTH & SUPPLY CHAIN - LEAFLET MAP VISUALIZATION (Overview)
// ==========================================================================

let phcMapInstance = null;
let phcMarkersLayer = null;
let locationControlAdded = false;
let userLocationMarker = null;

function initPhcMap(phcList) {
  const mapElement = document.getElementById('phc-network-map');
  if (!mapElement) return;

  // Initialize map if not yet done
  if (!phcMapInstance) {
    // Center of Uttar Pradesh
    phcMapInstance = L.map('phc-network-map', {
      center: [26.8467, 80.9462],
      zoom: 7,
      scrollWheelZoom: false
    });

    // OpenStreetMap standard tiles (100% free, no API key required, no watermark)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
      maxZoom: 19
    }).addTo(phcMapInstance);

    phcMarkersLayer = L.layerGroup().addTo(phcMapInstance);

    // ======================================================================
    // MY LOCATION BUTTON
    // ======================================================================

    if (!locationControlAdded) {
      const locationControl = L.control({ position: 'topleft' });

      locationControl.onAdd = function () {
        const button = L.DomUtil.create('button', 'my-location-button');

        button.innerHTML = '📍';
        button.title = 'My Location';
        button.type = 'button';

        button.style.width = '34px';
        button.style.height = '34px';
        button.style.backgroundColor = '#ffffff';
        button.style.border = '2px solid rgba(0,0,0,0.2)';
        button.style.borderRadius = '4px';
        button.style.cursor = 'pointer';
        button.style.fontSize = '18px';
        button.style.display = 'flex';
        button.style.alignItems = 'center';
        button.style.justifyContent = 'center';

        L.DomEvent.disableClickPropagation(button);

        button.onclick = function () {

          if (!navigator.geolocation) {
            alert('Geolocation is not supported by your browser.');
            return;
          }

          button.innerHTML = '⏳';

          navigator.geolocation.getCurrentPosition(
            function (position) {

              const latitude = position.coords.latitude;
              const longitude = position.coords.longitude;

              // Move map to user's current location
              phcMapInstance.setView(
                [latitude, longitude],
                15
              );

              // Remove previous user location marker
              if (userLocationMarker) {
                phcMapInstance.removeLayer(userLocationMarker);
              }

              // Add current location marker
              userLocationMarker = L.marker(
                [latitude, longitude]
              )
                .addTo(phcMapInstance)
                .bindPopup('📍 You are here')
                .openPopup();

              button.innerHTML = '📍';
            },

            function () {

              button.innerHTML = '📍';

              alert(
                'Unable to get your location. Please allow location access in your browser.'
              );

            }
          );
        };

        return button;
      };

      locationControl.addTo(phcMapInstance);

      locationControlAdded = true;
    }
  }

  // Clear existing markers
  phcMarkersLayer.clearLayers();

  const colorMap = {
    'CRITICAL': '#dc2626',
    'WARNING': '#d97706',
    'NORMAL': '#16a34a'
  };

  phcList.forEach(phc => {
    const color = colorMap[phc.overall_status] || '#16a34a';

    const marker = L.circleMarker([phc.latitude, phc.longitude], {
      radius: phc.overall_status === 'CRITICAL' ? 10 : 8,
      fillColor: color,
      color: '#ffffff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.9
    });

    const popupHtml = `
      <div style="font-family: inherit; min-width: 220px; padding: 4px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
          <span style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: #64748b;">${phc.district} District</span>
          <span style="font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: ${color}22; color: ${color};">${phc.overall_symbol} ${phc.overall_label}</span>
        </div>
        <div style="font-size: 14px; font-weight: 700; color: #0f172a; margin-bottom: 8px;">${phc.phc_name}</div>
        <div style="font-size: 12px; color: #334155; line-height: 1.6; margin-bottom: 10px;">
          <div><strong>Today's Footfall:</strong> ${phc.today_footfall} patients/day (${phc.footfall_trend_symbol})</div>
          <div><strong>Medicine Status:</strong> ${phc.medicine_status_text}</div>
          <div><strong>Critical Medicines:</strong> ${phc.critical_med_count}</div>
          <div><strong>Total Beds:</strong> ${phc.total_beds} beds</div>
        </div>
        <button onclick="window.appSelectPhcAndGoToDashboard('${phc.phc_id}')" 
          style="width: 100%; padding: 6px 10px; background: #1d4ed8; color: #fff; border: none; border-radius: 4px; font-size: 12px; font-weight: 600; cursor: pointer;">
          View in Dashboard →
        </button>
      </div>
    `;

    marker.bindPopup(popupHtml);
    phcMarkersLayer.addLayer(marker);
  });

  // Fit bounds if markers exist
  if (phcList.length > 0) {
    setTimeout(() => {
      phcMapInstance.invalidateSize();
    }, 200);
  }
}