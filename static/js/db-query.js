async function queryDatabase() {
  const queryPanel = document.createElement('div');
  queryPanel.innerHTML = `
    <div class="query-modal">
      <h6>Requête SQL directe</h6>
      <textarea id="sql-query" rows="4" placeholder="SELECT * FROM operations_sar WHERE statut = 'En cours'">SELECT * FROM operations_sar WHERE statut = 'En cours' LIMIT 100</textarea>
      <div class="d-flex gap-2 mt-2">
        <button class="btn btn-primary btn-sm" onclick="executeDbQuery()">Exécuter</button>
        <button class="btn btn-secondary btn-sm" onclick="this.parentElement.parentElement.remove()">Annuler</button>
      </div>
    </div>
  `;
  
  document.getElementById('layers-panel').appendChild(queryPanel);
}

async function executeDbQuery() {
  const sql = document.getElementById('sql-query').value;
  
  try {
    const response = await fetch('/api/db/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: sql })
    });
    
    const data = await response.json();
    addVectorLayerFromData(data.features);
  } catch (error) {
    alert('Erreur requête: ' + error.message);
  }
}

function addVectorLayerFromData(features) {
  const vectorSource = new ol.source.Vector({
    features: new ol.format.GeoJSON().readFeatures(features)
  });
  
  const vectorLayer = new ol.layer.Vector({
    source: vectorSource,
    style: new ol.style.Style({
      stroke: new ol.style.Stroke({ color: '#001F4D', width: 2 }),
      fill: new ol.style.Fill({ color: 'rgba(201,169,74,0.3)' })
    })
  });
  
  map.addLayer(vectorLayer);
}