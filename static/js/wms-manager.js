class WmsManager {
  constructor() {
    this.servers = [];
    this.layers = new Map();
    this.loadServers();
  }

  async loadServers() {
    const response = await fetch('/config/servers.json');
    this.servers = await response.json().wms_servers;
    
    const select = document.getElementById('wms-server-select');
    select.innerHTML = '<option value="">Choisir serveur...</option>';
    
    this.servers.forEach((server, index) => {
      const option = new Option(server.name, index);
      select.appendChild(option);
    });
  }

  async loadWmsLayers(serverIndex) {
    if (serverIndex === '') return;
    
    const server = this.servers[serverIndex];
    const capabilitiesUrl = `${server.url}?service=WMS&request=GetCapabilities&version=1.3.0`;
    
    try {
      const response = await fetch(capabilitiesUrl);
      const xml = await response.text();
      const layers = this.parseCapabilities(xml);
      
      this.populateLayersPanel(layers, server);
    } catch (error) {
      console.error('Erreur WMS:', error);
    }
  }

  parseCapabilities(xml) {
    // Parser XML GetCapabilities pour lister les layers
    const parser = new DOMParser();
    const doc = parser.parseFromString(xml, 'text/xml');
    const layers = [];
    
    const layerNodes = doc.querySelectorAll('Layer Layer');
    layerNodes.forEach(node => {
      const name = node.querySelector('Name')?.textContent;
      const title = node.querySelector('Title')?.textContent;
      if (name && title) {
        layers.push({ name, title, server: this.currentServer });
      }
    });
    
    return layers;
  }

  populateLayersPanel(layers, server) {
    const panel = document.getElementById('layers-panel');
    panel.innerHTML = '';
    
    layers.forEach(layer => {
      const div = document.createElement('div');
      div.className = 'layer-item';
      div.innerHTML = `
        <input type="checkbox" id="chk-${layer.name}">
        <label for="chk-${layer.name}">${layer.title}</label>
        <small class="text-muted">${server.name}</small>
      `;
      div.onclick = () => this.toggleLayer(layer);
      panel.appendChild(div);
    });
  }

  toggleLayer(layer) {
    const layerId = `${layer.server.name}_${layer.name}`;
    
    if (layers[layerId]) {
      // Retirer la couche
      map.removeLayer(layers[layerId]);
      delete layers[layerId];
    } else {
      // Ajouter la couche WMS
      const wmsSource = new ol.source.TileWMS({
        url: layer.server.url,
        params: {
          'LAYERS': layer.name,
          'FORMAT': 'image/png',
          'TRANSPARENT': true,
          'VERSION': '1.3.0'
        },
        serverType: 'geoserver'
      });
      
      const wmsLayer = new ol.layer.Tile({
        source: wmsSource,
        opacity: 0.8
      });
      
      map.addLayer(wmsLayer);
      layers[layerId] = wmsLayer;
    }
  }

  addCustomWms() {
    const url = document.getElementById('custom-wms-url').value;
    if (url) {
      this.loadWmsLayersCustom(url);
    }
  }
}

// Initialisation
const wmsManager = new WmsManager();