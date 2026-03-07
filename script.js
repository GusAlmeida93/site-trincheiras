// ====== API CONFIG ======
let currentJogadorId = localStorage.getItem('trincheiras_jogador_id') || null;

async function apiPost(endpoint, body) {
  try {
    const res = await fetch(`/api/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`API error (${endpoint}):`, err);
    return null;
  }
}
// =========================

const blockTabs = document.querySelectorAll(".block-tab");
const blockPanels = document.querySelectorAll(".block-panel");
const mapContainer = document.getElementById("strategic-map");
const mapRegionButtons = document.querySelectorAll(".map-region-btn");
const mapRegionNote = document.getElementById("map-region-note");
const mapLegendContainer = document.getElementById("map-legend");
let strategicMap = null;
let strategicLayerGroup = null;
let activeMapRegion = "europa";
let featureLayersMap = {};

const mapRegionConfig = {
  europa: {
    center: [50.8, 9.2],
    zoom: 4,
    note: "Europa: áreas destacadas representam regiões retiradas da Alemanha pelo Tratado de Versalhes."
  },
  africa: {
    center: [0.7, 22.0],
    zoom: 3,
    note: "África: ex-colônias alemãs foram redistribuídas entre potências vencedoras sob mandato internacional."
  },
  asia: {
    center: [14.0, 143.0],
    zoom: 3,
    note: "Ásia e Pacífico: territórios e concessões alemãs foram transferidos para Japão e outras administrações."
  }
};

const mapRegionFeatures = {
  europa: [
    {
      name: "Alsácia-Lorena",
      description: "Devolvida à França.",
      producer: "minério de ferro, carvão e indústria siderúrgica.",
      cededTo: "França (devolução confirmada pelo Tratado de Versalhes).",
      shape: "polygon",
      fill: "#e3a8a8",
      coords: [
        [49.35, 7.15],
        [49.68, 7.9],
        [48.58, 8.2],
        [48.2, 7.45]
      ]
    },
    {
      name: "Eupen-Malmedy",
      description: "Transferida para a Bélgica.",
      producer: "carvão, zinco e atividades industriais locais.",
      cededTo: "Bélgica (plebiscito supervisionado pelos vencedores).",
      shape: "polygon",
      fill: "#f5d39c",
      coords: [
        [50.9, 5.85],
        [51.1, 6.35],
        [50.74, 6.62],
        [50.54, 6.06]
      ]
    },
    {
      name: "Corredor Polonês",
      description: "Área cedida para garantir saída da Polônia ao mar.",
      producer: "grãos, madeira e acesso estratégico ao Mar Báltico.",
      cededTo: "Polônia reconstituída pelos acordos de paz pós-guerra.",
      shape: "polygon",
      fill: "#c7b3e8",
      coords: [
        [54.0, 16.9],
        [54.05, 19.45],
        [52.1, 19.2],
        [52.45, 16.35]
      ]
    },
    {
      name: "Schleswig do Norte",
      description: "Integrado à Dinamarca após plebiscito.",
      producer: "pecuária leiteira, cereais e comércio regional.",
      cededTo: "Dinamarca (resultado de plebiscito em 1920).",
      shape: "polygon",
      fill: "#9dc8e6",
      coords: [
        [55.65, 8.05],
        [55.38, 9.65],
        [54.78, 9.45],
        [54.95, 8.0]
      ]
    },
    {
      name: "Sarre",
      description: "Administração internacional temporária (Liga das Nações).",
      producer: "carvão mineral e base para indústria pesada.",
      cededTo: "Administração da Liga das Nações; exploração econômica francesa.",
      shape: "circle",
      fill: "#e7c8a0",
      coords: [49.32, 6.9],
      radius: 80000
    }
  ],
  africa: [
    {
      name: "Camarões Alemães",
      description: "Divididos entre França e Reino Unido.",
      producer: "cacau, borracha, óleo de palma e madeira tropical.",
      cededTo: "Mandatos da França e do Reino Unido.",
      shape: "polygon",
      fill: "#e2b0b0",
      coords: [
        [13.1, 8.0],
        [12.9, 15.1],
        [2.0, 15.5],
        [2.4, 8.1]
      ]
    },
    {
      name: "Sudoeste Africano Alemão",
      description: "Passou para mandato da África do Sul.",
      producer: "diamantes, cobre e criação de gado.",
      cededTo: "União Sul-Africana (mandato aprovado pela Liga das Nações).",
      shape: "polygon",
      fill: "#b4d4ea",
      coords: [
        [-17.2, 11.3],
        [-17.4, 19.5],
        [-28.9, 20.0],
        [-28.7, 12.0]
      ]
    },
    {
      name: "África Oriental Alemã",
      description: "Principal parte virou Tanganica (mandato britânico).",
      producer: "algodão, sisal, café e rotas comerciais do Índico.",
      cededTo: "Reino Unido (Tanganica), Bélgica (Ruanda-Urundi) e Portugal em faixas de fronteira.",
      shape: "polygon",
      fill: "#c9dba8",
      coords: [
        [-0.4, 29.0],
        [-0.4, 39.4],
        [-11.9, 40.0],
        [-11.8, 29.0]
      ]
    },
    {
      name: "Togo Alemão",
      description: "Dividido entre França e Reino Unido.",
      producer: "cacau, algodão, fosfato e comércio atlântico.",
      cededTo: "Mandatos francês e britânico.",
      shape: "polygon",
      fill: "#f2cf97",
      coords: [
        [11.0, 0.45],
        [11.0, 1.82],
        [6.0, 1.82],
        [6.0, 0.45]
      ]
    }
  ],
  asia: [
    {
      name: "Concessão de Kiautschou (Shandong)",
      description: "Transferida ao Japão.",
      producer: "porto estratégico, ferrovias e comércio marítimo regional.",
      cededTo: "Japão (posteriormente renegociada com a China).",
      shape: "polygon",
      fill: "#e9b4b2",
      coords: [
        [37.9, 120.0],
        [37.3, 121.7],
        [35.8, 121.8],
        [35.7, 120.2]
      ]
    },
    {
      name: "Ilhas Marianas",
      description: "Mandato japonês no Pacífico.",
      producer: "copra, fosfato e pontos de apoio naval.",
      cededTo: "Japão (mandato do Pacífico Norte).",
      shape: "circle",
      fill: "#a9cce9",
      coords: [15.2, 145.5],
      radius: 230000
    },
    {
      name: "Carolinas e Marshall",
      description: "Administração japonesa após a guerra.",
      producer: "copra, pesca oceânica e rotas marítimas estratégicas.",
      cededTo: "Japão por mandato internacional da Liga das Nações.",
      shape: "circle",
      fill: "#d7c0e6",
      coords: [7.6, 164.2],
      radius: 260000
    },
    {
      name: "Nordeste da Nova Guiné",
      description: "Mandato australiano.",
      producer: "copra, fosfato e matérias-primas tropicais.",
      cededTo: "Austrália (mandato da Liga das Nações).",
      shape: "circle",
      fill: "#f1d79f",
      coords: [-4.3, 147.4],
      radius: 270000
    }
  ]
};

function createFeatureLayer(feature) {
  const baseStyle = {
    color: "rgba(255,255,255,0.45)",
    weight: 2,
    fillColor: feature.fill || "#d8b5a5",
    fillOpacity: 0.5,
    className: "map-feature-layer"
  };

  const highlightStyle = {
    weight: 3,
    color: "#f0d8a0",
    fillOpacity: 0.72
  };

  const resetStyle = { ...baseStyle };

  let layer = null;
  if (feature.shape === "circle") {
    layer = L.circle(feature.coords, { ...baseStyle, radius: feature.radius || 180000 });
  } else {
    layer = L.polygon(feature.coords, baseStyle);
  }

  layer.on("mouseover", function () {
    this.setStyle(highlightStyle);
    if (typeof this.bringToFront === "function") this.bringToFront();
  });
  layer.on("mouseout", function () {
    this.setStyle(resetStyle);
  });

  if (feature.name || feature.description) {
    const pinSvg = '<svg class="map-info-pin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>';
    const popupHtml = `
      <div class="map-info-card">
        <div class="map-info-accent" style="background:${feature.fill || '#d8b5a5'}"></div>
        <div class="map-info-body">
          <h4>${pinSvg}${feature.name || ""}</h4>
          <p>${feature.description || ""}</p>
          <hr class="map-info-divider">
          <div class="map-info-detail">
            <span class="map-info-detail-icon">⛏</span>
            <span><strong>Produz:</strong> ${feature.producer || "informação em revisão."}</span>
          </div>
          <div class="map-info-detail">
            <span class="map-info-detail-icon">🏳</span>
            <span><strong>Cedida a:</strong> ${feature.cededTo || "informação em revisão."}</span>
          </div>
        </div>
      </div>
    `;
    layer.bindPopup(popupHtml, { maxWidth: 320, className: "map-enhanced-popup" });
  }

  return layer;
}

function renderMapLegend(regionId) {
  if (!mapLegendContainer) return;
  const features = mapRegionFeatures[regionId] || [];
  mapLegendContainer.innerHTML = "";

  features.forEach((feature, index) => {
    const btn = document.createElement("button");
    btn.className = "map-legend-item";
    btn.type = "button";
    btn.innerHTML = `<span class="map-legend-swatch" style="background:${feature.fill || '#d8b5a5'}"></span>${feature.name}`;

    btn.addEventListener("click", () => {
      // Remove all active states
      mapLegendContainer.querySelectorAll(".map-legend-item").forEach(el => el.classList.remove("is-active"));
      btn.classList.add("is-active");

      // Find the corresponding layer and zoom/open popup
      const layerKey = `${regionId}-${index}`;
      const targetLayer = featureLayersMap[layerKey];
      if (targetLayer && strategicMap) {
        if (feature.shape === "circle") {
          strategicMap.setView(feature.coords, Math.min(strategicMap.getZoom() + 1, 6), { animate: true });
        } else {
          strategicMap.fitBounds(targetLayer.getBounds(), { padding: [40, 40], animate: true, maxZoom: 7 });
        }
        targetLayer.openPopup();
      }
    });

    mapLegendContainer.appendChild(btn);
  });
}

function renderMapRegion(regionId) {
  const region = mapRegionConfig[regionId];
  if (!strategicMap || !strategicLayerGroup || !region) return;

  activeMapRegion = regionId;
  strategicLayerGroup.clearLayers();
  featureLayersMap = {};

  (mapRegionFeatures[regionId] || []).forEach((feature, index) => {
    const layer = createFeatureLayer(feature);
    layer.addTo(strategicLayerGroup);
    featureLayersMap[`${regionId}-${index}`] = layer;
  });

  strategicMap.setView(region.center, region.zoom, { animate: true });
  if (mapRegionNote) {
    mapRegionNote.textContent = region.note;
  }

  renderMapLegend(regionId);

  mapRegionButtons.forEach((button) => {
    const isActive = button.dataset.mapRegion === regionId;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
}

function initStrategicMap() {
  if (strategicMap || !mapContainer) return;

  if (typeof window.L === "undefined") {
    mapContainer.innerHTML = "<p class='map-fallback'>Não foi possível carregar o mapa interativo.</p>";
    return;
  }

  strategicMap = L.map(mapContainer, {
    zoomControl: true,
    minZoom: 2,
    maxZoom: 8,
    worldCopyJump: true
  });

  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: "&copy; OpenStreetMap contributors &copy; CARTO"
  }).addTo(strategicMap);

  strategicLayerGroup = L.layerGroup().addTo(strategicMap);
  renderMapRegion(activeMapRegion);

  setTimeout(() => {
    strategicMap.invalidateSize();
  }, 80);
}

// typeContextTitle was removed — the #contexto panel it powered was orphaned (no tab targeted it).

function activateBlock(targetId) {
  blockTabs.forEach((tab) => {
    const isActive = tab.dataset.target === targetId;
    tab.classList.toggle("active", isActive);
    tab.setAttribute("aria-selected", String(isActive));
  });

  blockPanels.forEach((panel) => {
    const isActive = panel.id === targetId;
    panel.classList.toggle("active", isActive);
    panel.hidden = !isActive;
  });

  // (The old #contexto typing animation was removed along with the orphaned panel.)

  if (targetId === "mapa") {
    initStrategicMap();
    if (strategicMap) {
      setTimeout(() => {
        strategicMap.invalidateSize();
      }, 80);
    }
  }
}

if (blockTabs.length && blockPanels.length) {
  blockTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      activateBlock(tab.dataset.target);
    });
  });

  const initialTab = document.querySelector(".block-tab.active") || blockTabs[0];
  if (initialTab) {
    activateBlock(initialTab.dataset.target);
  }
}

if (mapRegionButtons.length) {
  mapRegionButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const regionId = button.dataset.mapRegion;
      if (!regionId) return;
      if (!strategicMap) {
        initStrategicMap();
      }
      renderMapRegion(regionId);
    });
  });
}

const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let blastAudioContext = null;
let blastNoiseBuffer = null;

function getBlastAudioContext() {
  const ContextClass = window.AudioContext || window.webkitAudioContext;
  if (!ContextClass) return null;

  if (!blastAudioContext) {
    blastAudioContext = new ContextClass();
  }

  return blastAudioContext;
}

function getBlastNoiseBuffer(context) {
  if (
    blastNoiseBuffer &&
    blastNoiseBuffer.sampleRate === context.sampleRate
  ) {
    return blastNoiseBuffer;
  }

  const length = Math.floor(context.sampleRate * 1.8);
  const buffer = context.createBuffer(1, length, context.sampleRate);
  const channel = buffer.getChannelData(0);

  for (let i = 0; i < length; i += 1) {
    const decay = 1 - i / length;
    channel[i] = (Math.random() * 2 - 1) * Math.pow(decay, 1.35);
  }

  blastNoiseBuffer = buffer;
  return blastNoiseBuffer;
}

function playExplosionSound() {
  const context = getBlastAudioContext();
  if (!context) return;

  if (context.state === "suspended") {
    context.resume().catch(() => { });
  }

  const now = context.currentTime;
  const compressor = context.createDynamicsCompressor();
  compressor.threshold.setValueAtTime(-18, now);
  compressor.knee.setValueAtTime(14, now);
  compressor.ratio.setValueAtTime(6, now);
  compressor.attack.setValueAtTime(0.002, now);
  compressor.release.setValueAtTime(0.42, now);
  compressor.connect(context.destination);

  const master = context.createGain();
  master.gain.setValueAtTime(0.0001, now);
  master.gain.exponentialRampToValueAtTime(0.68, now + 0.01);
  master.gain.exponentialRampToValueAtTime(0.36, now + 0.48);
  master.gain.exponentialRampToValueAtTime(0.0001, now + 1.9);
  master.connect(compressor);

  const noiseSource = context.createBufferSource();
  noiseSource.buffer = getBlastNoiseBuffer(context);
  const noiseFilter = context.createBiquadFilter();
  noiseFilter.type = "lowpass";
  noiseFilter.frequency.setValueAtTime(820, now);
  noiseFilter.frequency.exponentialRampToValueAtTime(62, now + 1.35);
  const noiseGain = context.createGain();
  noiseGain.gain.setValueAtTime(0.0001, now);
  noiseGain.gain.exponentialRampToValueAtTime(1.42, now + 0.012);
  noiseGain.gain.exponentialRampToValueAtTime(0.58, now + 0.46);
  noiseGain.gain.exponentialRampToValueAtTime(0.0001, now + 1.52);

  noiseSource.connect(noiseFilter);
  noiseFilter.connect(noiseGain);
  noiseGain.connect(master);
  noiseSource.start(now);
  noiseSource.stop(now + 1.62);

  const thump = context.createOscillator();
  thump.type = "triangle";
  thump.frequency.setValueAtTime(178, now);
  thump.frequency.exponentialRampToValueAtTime(28, now + 0.98);
  const thumpGain = context.createGain();
  thumpGain.gain.setValueAtTime(0.0001, now);
  thumpGain.gain.exponentialRampToValueAtTime(1.28, now + 0.025);
  thumpGain.gain.exponentialRampToValueAtTime(0.18, now + 0.55);
  thumpGain.gain.exponentialRampToValueAtTime(0.0001, now + 1.15);
  thump.connect(thumpGain);
  thumpGain.connect(master);
  thump.start(now);
  thump.stop(now + 1.2);

  const rumble = context.createOscillator();
  rumble.type = "sine";
  rumble.frequency.setValueAtTime(56, now + 0.08);
  rumble.frequency.exponentialRampToValueAtTime(22, now + 1.55);
  const rumbleGain = context.createGain();
  rumbleGain.gain.setValueAtTime(0.0001, now);
  rumbleGain.gain.exponentialRampToValueAtTime(0.34, now + 0.12);
  rumbleGain.gain.exponentialRampToValueAtTime(0.0001, now + 1.62);
  rumble.connect(rumbleGain);
  rumbleGain.connect(master);
  rumble.start(now + 0.05);
  rumble.stop(now + 1.64);

  const crack = context.createOscillator();
  crack.type = "square";
  crack.frequency.setValueAtTime(980, now);
  crack.frequency.exponentialRampToValueAtTime(220, now + 0.16);
  const crackGain = context.createGain();
  crackGain.gain.setValueAtTime(0.0001, now);
  crackGain.gain.exponentialRampToValueAtTime(0.24, now + 0.003);
  crackGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.18);
  crack.connect(crackGain);
  crackGain.connect(master);
  crack.start(now);
  crack.stop(now + 0.2);
}

function pulseHit(element) {
  if (!element || prefersReducedMotion) return;
  element.classList.remove("is-hit");
  void element.offsetWidth;
  element.classList.add("is-hit");
  setTimeout(() => {
    element.classList.remove("is-hit");
  }, 320);
}

function triggerBombExplosion(targetElement) {
  playExplosionSound();
  if (!targetElement || prefersReducedMotion) return;

  const rect = targetElement.getBoundingClientRect();
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 2;

  // ── Screen flash overlay ──
  const screenFlash = document.createElement("div");
  screenFlash.className = "bomb-screen-flash";
  screenFlash.style.setProperty("--flash-x", `${(cx / window.innerWidth) * 100}%`);
  screenFlash.style.setProperty("--flash-y", `${(cy / window.innerHeight) * 100}%`);
  document.body.appendChild(screenFlash);
  setTimeout(() => screenFlash.remove(), 320);

  // ── Main blast container ──
  const blast = document.createElement("span");
  blast.className = "bomb-blast";
  blast.style.left = `${cx}px`;
  blast.style.top = `${cy}px`;

  // ── Smoke (main) ──
  const smoke = document.createElement("span");
  smoke.className = "bomb-smoke";
  blast.appendChild(smoke);

  // ── Afterglow ──
  const afterglow = document.createElement("span");
  afterglow.className = "bomb-afterglow";
  blast.appendChild(afterglow);

  // ── Secondary shockwave ring ──
  const ring2 = document.createElement("span");
  ring2.className = "bomb-ring-secondary";
  blast.appendChild(ring2);

  // ── Additional smoke puffs (3) ──
  const smokePuffs = [
    { size: 50, x: -15, y: -35, delay: 60, dur: 1100 },
    { size: 40, x: 18, y: -28, delay: 140, dur: 1300 },
    { size: 55, x: -5, y: -42, delay: 200, dur: 1400 }
  ];
  smokePuffs.forEach((puff) => {
    const s = document.createElement("span");
    s.className = "bomb-smoke-large";
    s.style.left = `${-puff.size / 2}px`;
    s.style.top = `${-puff.size / 2}px`;
    s.style.width = `${puff.size}px`;
    s.style.height = `${puff.size}px`;
    s.style.setProperty("--smoke-x", `${puff.x}px`);
    s.style.setProperty("--smoke-y", `${puff.y}px`);
    s.style.setProperty("--smoke-delay", `${puff.delay}ms`);
    s.style.setProperty("--smoke-dur", `${puff.dur}ms`);
    blast.appendChild(s);
  });

  // ── Sparks (20) — varied size, color, speed ──
  const sparkColors = [
    { color: "#fff8e0", glow: "rgba(255,248,200,0.9)" },
    { color: "#ffd6a6", glow: "rgba(255,209,122,0.8)" },
    { color: "#ffb060", glow: "rgba(255,176,96,0.8)" },
    { color: "#ff8c3a", glow: "rgba(255,140,58,0.7)" },
    { color: "#ffe8c0", glow: "rgba(255,232,192,0.85)" }
  ];
  const sparksCount = 20;
  for (let i = 0; i < sparksCount; i += 1) {
    const spark = document.createElement("span");
    spark.className = "bomb-spark";

    const angle = (Math.PI * 2 * i) / sparksCount + (Math.random() - 0.5) * 0.5;
    const distance = 45 + Math.random() * 75;
    const sc = sparkColors[i % sparkColors.length];
    const size = 3 + Math.random() * 5;
    const dur = 450 + Math.random() * 350;

    spark.style.setProperty("--dx", `${Math.cos(angle) * distance}px`);
    spark.style.setProperty("--dy", `${Math.sin(angle) * distance}px`);
    spark.style.setProperty("--spark-color", sc.color);
    spark.style.setProperty("--spark-glow", sc.glow);
    spark.style.setProperty("--spark-size", `${size}px`);
    spark.style.setProperty("--spark-dur", `${dur}ms`);
    spark.style.setProperty("--spark-delay", `${Math.random() * 80}ms`);

    blast.appendChild(spark);
  }

  // ── Debris / shrapnel (10) ──
  const debrisColors = ["#8b7355", "#6b5640", "#a39070", "#5c4a35", "#7a6348", "#9c8560"];
  const debrisCount = 10;
  for (let i = 0; i < debrisCount; i += 1) {
    const debris = document.createElement("span");
    debris.className = "bomb-debris";

    const angle = (Math.PI * 2 * i) / debrisCount + (Math.random() - 0.5) * 0.6;
    const distance = 40 + Math.random() * 80;
    const dx = Math.cos(angle) * distance;
    const dy = Math.sin(angle) * distance + Math.random() * 30;
    const rotation = (Math.random() > 0.5 ? 1 : -1) * (180 + Math.random() * 540);
    const w = 4 + Math.random() * 6;
    const h = 3 + Math.random() * 4;
    const dur = 550 + Math.random() * 350;

    debris.style.setProperty("--debris-dx", `${dx}px`);
    debris.style.setProperty("--debris-dy", `${dy}px`);
    debris.style.setProperty("--debris-rot", `${rotation}deg`);
    debris.style.setProperty("--debris-w", `${w}px`);
    debris.style.setProperty("--debris-h", `${h}px`);
    debris.style.setProperty("--debris-color", debrisColors[i % debrisColors.length]);
    debris.style.setProperty("--debris-dur", `${dur}ms`);
    debris.style.setProperty("--debris-delay", `${Math.random() * 60}ms`);

    blast.appendChild(debris);
  }

  document.body.appendChild(blast);
  setTimeout(() => {
    blast.remove();
  }, 1600);
}

const warDrawers = document.querySelectorAll(".war-drawer");
const warIntelCards = document.querySelectorAll(".war-intel-card");
const warStatus = document.getElementById("war-status");
const warRoomGrid = document.querySelector(".war-room-grid");

const warScoreEl = document.getElementById("war-score");
let warScore = 0;
let warDrawerErrors = {};

function updateWarScore() {
  if (warScoreEl) {
    warScoreEl.textContent = warScore;
  }
}

const warMatchByDoc = {
  "1": "1",
  "2": "2",
  "3": "3",
  "4": "4",
  "5": "5"
};

let selectedWarCard = null;

function updateWarStatus(message) {
  if (warStatus) {
    warStatus.textContent = message;
  }
}

function getWarCardText(card) {
  if (!card) return "";
  const textBlocks = card.querySelectorAll("p");
  if (textBlocks.length < 2) return "";
  return textBlocks[1].textContent.trim();
}

function finalizeWarCard(card) {
  if (!card) return;
  card.classList.remove("is-selected");
  card.classList.add("is-used");
  card.setAttribute("aria-hidden", "true");
  card.setAttribute("draggable", "false");
}

function resetWarCardSelection() {
  warIntelCards.forEach((card) => card.classList.remove("is-selected"));
  selectedWarCard = null;
}

function completeWarArchive(docId, drawerId) {
  const card = document.querySelector(`.war-intel-card[data-doc="${docId}"]`);
  const drawer = document.querySelector(`.war-drawer[data-drawer="${drawerId}"]`);
  if (!card || !drawer) return;
  if (card.classList.contains("is-used") || drawer.dataset.filled === "true") return;

  const expectedDrawer = warMatchByDoc[docId];
  const isCorrect = expectedDrawer === drawerId;
  const answerBox = drawer.querySelector(".war-drawer-answer");
  let pointsVariation = 0;

  if (!isCorrect) {
    if (!warDrawerErrors[drawerId]) {
      warDrawerErrors[drawerId] = 0;
    }

    if (warDrawerErrors[drawerId] < 2) {
      warScore -= 5;
      pointsVariation = -5;
      updateWarScore();
    }
    warDrawerErrors[drawerId]++;

    drawer.classList.add("is-wrong");
    card.classList.add("is-selected");
    triggerBombExplosion(drawer);
    pulseHit(warRoomGrid);
    setTimeout(() => drawer.classList.remove("is-wrong"), 420);
    updateWarStatus("Documento incorreto para essa gaveta. Tente novamente.");

    // Save incorrect attempt to API
    if (currentJogadorId) {
      apiPost('respostas', {
        jogador_id: currentJogadorId,
        modulo: 'war_room',
        pergunta_id: `gaveta_${drawerId}`,
        resposta_escolhida: `doc_${docId}`,
        correto: false,
        variacao_pontos: pointsVariation
      });
    }
    return;
  }

  pointsVariation = 10;
  drawer.dataset.filled = "true";
  drawer.classList.add("is-correct");
  if (answerBox) {
    answerBox.textContent = getWarCardText(card);
  }
  warScore += pointsVariation;
  updateWarScore();
  finalizeWarCard(card);
  resetWarCardSelection();

  // Save correct attempt to API
  if (currentJogadorId) {
    apiPost('respostas', {
      jogador_id: currentJogadorId,
      modulo: 'war_room',
      pergunta_id: `gaveta_${drawerId}`,
      resposta_escolhida: `doc_${docId}`,
      correto: true,
      variacao_pontos: pointsVariation
    });
  }

  const completed = document.querySelectorAll('.war-drawer[data-filled="true"]').length;
  const total = warDrawers.length;
  if (completed === total) {
    updateWarStatus("Excelente. Todos os relatórios foram arquivados corretamente.");
  } else {
    updateWarStatus(`Relatório arquivado com sucesso. ${completed}/${total} gavetas concluídas.`);
  }
}

if (warIntelCards.length && warDrawers.length) {
  warIntelCards.forEach((card) => {
    card.addEventListener("click", () => {
      if (card.classList.contains("is-used")) return;

      const wasSelected = card.classList.contains("is-selected");
      resetWarCardSelection();
      if (!wasSelected) {
        card.classList.add("is-selected");
        selectedWarCard = card;
        updateWarStatus("Documento selecionado. Clique em uma gaveta para arquivar.");
      } else {
        updateWarStatus("Selecione um documento para iniciar o arquivamento.");
      }
    });

    card.addEventListener("dragstart", (event) => {
      if (card.classList.contains("is-used")) {
        event.preventDefault();
        return;
      }
      resetWarCardSelection();
      selectedWarCard = card;
      card.classList.add("is-selected");
      event.dataTransfer.setData("text/plain", card.dataset.doc || "");
      event.dataTransfer.effectAllowed = "move";
      updateWarStatus("Arraste o documento até a gaveta correspondente.");
    });

    card.addEventListener("dragend", () => {
      warDrawers.forEach((drawer) => drawer.classList.remove("is-hover"));
    });
  });

  warDrawers.forEach((drawer) => {
    drawer.addEventListener("click", () => {
      if (!selectedWarCard) return;
      completeWarArchive(selectedWarCard.dataset.doc, drawer.dataset.drawer);
    });

    drawer.addEventListener("dragover", (event) => {
      event.preventDefault();
      drawer.classList.add("is-hover");
    });

    drawer.addEventListener("dragleave", () => {
      drawer.classList.remove("is-hover");
    });

    drawer.addEventListener("drop", (event) => {
      event.preventDefault();
      drawer.classList.remove("is-hover");
      const docId = event.dataTransfer.getData("text/plain");
      if (!docId) return;
      completeWarArchive(docId, drawer.dataset.drawer);
    });
  });
}

const dossiers = document.querySelectorAll(".dossier");
const dossierTabs = document.querySelectorAll(".dossier-tab");
let activeDossier = null;
let dossierSwapTimer = null;
const DOSSIER_ANIMATION_MS = 320;

function setDossierOpenHeight(dossier) {
  if (!dossier) return;
  const tab = dossier.querySelector(".dossier-tab");
  const paper = dossier.querySelector(".dossier-paper");
  if (!tab || !paper) return;

  const tabHeight = tab.offsetHeight;
  const paperHeight = paper.scrollHeight;
  const bottomGap = 34;
  dossier.style.setProperty("--dossier-open-height", `${tabHeight + paperHeight + bottomGap}px`);
}

function setDossierSelected(dossier, isSelected) {
  const tab = dossier?.querySelector(".dossier-tab");
  if (tab) {
    tab.setAttribute("aria-selected", String(isSelected));
  }
}

function openDossier(dossier) {
  if (!dossier) return;
  const paper = dossier.querySelector(".dossier-paper");
  if (!paper) return;

  paper.hidden = false;
  setDossierOpenHeight(dossier);
  void dossier.offsetWidth;
  dossier.classList.add("is-open");
  setTimeout(() => {
    if (dossier.classList.contains("is-open")) {
      setDossierOpenHeight(dossier);
    }
  }, DOSSIER_ANIMATION_MS + 40);
  setDossierSelected(dossier, true);
  activeDossier = dossier;
}

function closeDossier(dossier) {
  if (!dossier) return;
  const paper = dossier.querySelector(".dossier-paper");

  dossier.classList.remove("is-open");
  setDossierSelected(dossier, false);

  if (!paper) {
    return;
  }

  setTimeout(() => {
    if (!dossier.classList.contains("is-open")) {
      paper.hidden = true;
    }
  }, DOSSIER_ANIMATION_MS);
}

if (dossierTabs.length && dossiers.length) {
  dossiers.forEach((dossier) => {
    dossier.classList.remove("is-open");
    setDossierSelected(dossier, false);
    const paper = dossier.querySelector(".dossier-paper");
    if (paper) {
      paper.hidden = true;
    }
  });

  dossierTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const dossier = tab.closest(".dossier");
      if (!dossier) return;

      if (dossierSwapTimer) {
        clearTimeout(dossierSwapTimer);
        dossierSwapTimer = null;
      }

      if (activeDossier === dossier) {
        closeDossier(dossier);
        activeDossier = null;
        return;
      }

      if (activeDossier && activeDossier !== dossier) {
        const previous = activeDossier;
        closeDossier(previous);
        activeDossier = null;

        dossierSwapTimer = setTimeout(() => {
          openDossier(dossier);
          dossierSwapTimer = null;
        }, DOSSIER_ANIMATION_MS);
        return;
      }

      openDossier(dossier);
    });
  });

  window.addEventListener("resize", () => {
    if (activeDossier) {
      setDossierOpenHeight(activeDossier);
    }
  });
}

const clauseArticles = {
  "51": {
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5h2l1 10h12l1-10h2"/><path d="M6 5v14h12V5"/><path d="M9 8v3m0 0l3-2m-3 2l3 2"/><path d="M6 19l-2 2m14-2l2 2"/><rect x="8" y="3" width="8" height="2" rx="1"/><path d="M10 12h4m-2-2v4" opacity="0.5"/></svg>',
    number: "Artigo 51",
    title: "Devolução da Alsácia-Lorena",
    quote:
      "\u201cOs territórios cedidos à Alemanha em virtude dos preliminares de paz de 1871 são reintegrados à soberania francesa.\u201d",
    impact:
      "A Alemanha perdeu uma região estratégica e simbolicamente importante, fortalecendo sentimentos de revanche e ressentimento nacional."
  },
  "119": {
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M3.5 9h17M3.5 15h17"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M7 5l1.5 1M17 5l-1.5 1M7 19l1.5-1M17 19l-1.5-1" opacity="0.6"/><circle cx="8" cy="10" r="0.8" fill="currentColor" stroke="none"/><circle cx="16" cy="13" r="0.8" fill="currentColor" stroke="none"/><circle cx="11" cy="15" r="0.8" fill="currentColor" stroke="none"/></svg>',
    number: "Artigo 119",
    title: "Renúncia do Império Colonial",
    quote:
      "\u201cA Alemanha renuncia, em favor das potências aliadas e associadas, todos os seus direitos e títulos sobre suas possessões ultramarinas.\u201d",
    impact:
      "O país perdeu colônias, acesso direto a matérias-primas e parte de sua projeção internacional."
  },
  "160": {
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3L4 7v5c0 5 3.5 9.5 8 11 4.5-1.5 8-6 8-11V7l-8-4z"/><path d="M8.5 9l7 7M15.5 9l-7 7" stroke-width="2" opacity="0.7"/></svg>',
    number: "Artigo 160",
    title: "Desmilitarização",
    quote:
      "\u201cAs forças armadas alemãs não deverão ultrapassar 100 mil homens, destinadas exclusivamente à manutenção da ordem interna.\u201d",
    impact:
      "A capacidade militar alemã foi reduzida, diminuindo seu poder de reação e sua influência estratégica no curto prazo."
  },
  "231": {
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v4"/><path d="M12 7l-7 3"/><path d="M12 7l7 3"/><path d="M5 10v1a3 3 0 003 3h0"/><path d="M19 10v1a3 3 0 01-3 3h0"/><rect x="3" y="13" width="6" height="3" rx="1"/><rect x="15" y="13" width="6" height="3" rx="1"/><path d="M12 7v14"/><path d="M9 21h6" stroke-width="2"/><circle cx="6" cy="14.5" r="0.5" fill="currentColor" stroke="none"/><circle cx="18" cy="14.5" r="0.5" fill="currentColor" stroke="none"/></svg>',
    number: "Artigo 231",
    title: "A Cláusula de Culpa",
    quote:
      "\u201cA Alemanha e seus aliados aceitam a responsabilidade por todas as perdas e danos sofridos pelos governos aliados e associados.\u201d",
    impact:
      "Essa cláusula criou base política e jurídica para punições mais duras e alimentou forte sensação de humilhação nacional."
  },
  "232": {
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="8" width="16" height="12" rx="2"/><path d="M4 12h16"/><circle cx="12" cy="16" r="2"/><path d="M8 8V6a4 4 0 018 0v2"/><path d="M9 12v-1m6 1v-1" opacity="0.5"/><path d="M7 20l-1 1m11-1l1 1" opacity="0.4"/></svg>',
    number: "Artigo 232",
    title: "Reparações Financeiras",
    quote:
      "\u201cA Alemanha compromete-se a reparar os danos causados à população civil e aos bens dos países aliados e associados.\u201d",
    impact:
      "As reparações pesaram sobre a economia, contribuindo para inflação, desemprego e instabilidade política."
  },
  "42": {
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 13c0-2 1-4 3-5l2-4h6l2 4c2 1 3 3 3 5"/><path d="M4 13h16v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2z"/><path d="M8 17v2m8-2v2"/><path d="M10 4h4v1h-4z" opacity="0.5"/><circle cx="12" cy="12" r="5" stroke-dasharray="2 2" opacity="0.4"/><path d="M3 3l18 18" stroke-width="2.2" stroke="#b04a49"/></svg>',
    number: "Artigo 42",
    title: "Desmilitarização da Renânia",
    quote:
      "\u201cÉ proibido à Alemanha manter ou construir fortificações na margem esquerda do Reno e em zonas determinadas na margem direita.\u201d",
    impact:
      "A Renânia virou uma zona de segurança para a França, mas muitos alemães viram isso como perda de soberania."
  },
  "87": {
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/><path d="M12 3v4m0 10v4M3 12h4m10 0h4"/><path d="M12 9l0-2" stroke-width="2.5"/><path d="M14.5 11l1.7-1" stroke-width="1" opacity="0.5"/><path d="M14.5 13l1.7 1" stroke-width="1" opacity="0.5"/><path d="M9.5 11l-1.7-1" stroke-width="1" opacity="0.5"/><path d="M9.5 13l-1.7 1" stroke-width="1" opacity="0.5"/><path d="M5.5 5.5l2.1 2.1m8.8 8.8l2.1 2.1M5.5 18.5l2.1-2.1m8.8-8.8l2.1-2.1" stroke-dasharray="1 2" opacity="0.3"/></svg>',
    number: "Artigo 87",
    title: "O Corredor Polonês",
    quote:
      "\u201cA Alemanha reconhece a independência da Polônia e renuncia aos territórios definidos pelas potências aliadas.\u201d",
    impact:
      "A redefinição territorial separou áreas alemãs e ampliou tensões fronteiriças que continuaram no período entre guerras."
  }
};

const clauseItems = document.querySelectorAll(".clause-item");
const clauseDocIcon = document.getElementById("clause-doc-icon");
const clauseDocNumber = document.getElementById("clause-doc-number");
const clauseDocTitle = document.getElementById("clause-doc-title");
const clauseDocQuote = document.getElementById("clause-doc-quote");
const clauseDocImpact = document.getElementById("clause-doc-impact");

function renderClauseArticle(articleId) {
  const article = clauseArticles[articleId];
  if (!article) return;

  if (clauseDocIcon) clauseDocIcon.innerHTML = article.icon;
  if (clauseDocNumber) clauseDocNumber.textContent = article.number;
  if (clauseDocTitle) clauseDocTitle.textContent = article.title;
  if (clauseDocQuote) clauseDocQuote.textContent = article.quote;
  if (clauseDocImpact) clauseDocImpact.textContent = article.impact;
}

if (clauseItems.length) {
  const initialClause = document.querySelector(".clause-item.active");
  if (initialClause) {
    renderClauseArticle(initialClause.dataset.article);
  }

  clauseItems.forEach((item) => {
    item.addEventListener("click", () => {
      const articleId = item.dataset.article;
      clauseItems.forEach((btn) => {
        const isActive = btn === item;
        btn.classList.toggle("active", isActive);
        btn.setAttribute("aria-selected", String(isActive));
      });
      renderClauseArticle(articleId);
    });
  });
}

const participantInterests = {
  franca: {
    title: "França",
    leader: "Georges Clemenceau",
    role: "O Tigre",
    text:
      "Defendia punições severas para enfraquecer a Alemanha, recuperar regiões perdidas e garantir segurança para que a França não sofresse nova invasão. A França havia sofrido enormes perdas humanas e materiais durante a guerra, com combates travados em seu próprio território.",
    objectives: [
      "Recuperar a Alsácia-Lorena, perdida em 1871",
      "Exigir reparações financeiras pesadas para reconstruir o país",
      "Desmilitarizar a Renânia como zona de segurança",
      "Enfraquecer permanentemente o poderio militar alemão"
    ],
    quote: "\"A Alemanha pagará por tudo!\" — Posição firme de Clemenceau durante as negociações."
  },
  reino: {
    title: "Reino Unido",
    leader: "David Lloyd George",
    role: "O Mediador Pragmático",
    text:
      "Queria punir a Alemanha, mas sem destruí-la totalmente, para preservar o comércio europeu e evitar um colapso econômico no continente. O Reino Unido dependia do equilíbrio de poder europeu e temia que uma Alemanha humilhada gerasse instabilidade.",
    objectives: [
      "Manter o equilíbrio de poder na Europa continental",
      "Preservar relações comerciais com a Alemanha",
      "Expandir o domínio colonial britânico com mandatos",
      "Garantir a supremacia naval britânica"
    ],
    quote: "\"Podemos arrancar da Alemanha tudo o que ela tem, mas não podemos impedi-la de se levantar novamente.\" — Lloyd George sobre os riscos de punições excessivas."
  },
  eua: {
    title: "Estados Unidos",
    leader: "Woodrow Wilson",
    role: "O Idealista",
    text:
      "Propunha uma paz negociada, com menos vingança e mais cooperação, defendendo princípios dos 14 Pontos e a criação da Liga das Nações. Wilson acreditava que a paz duradoura dependia de justiça e autodeterminação dos povos, não de punição.",
    objectives: [
      "Implementar os 14 Pontos como base para a paz",
      "Criar a Liga das Nações para resolver conflitos futuros",
      "Defender a autodeterminação dos povos europeus",
      "Promover o livre comércio e a democracia no mundo"
    ],
    quote: "\"Devemos tornar o mundo seguro para a democracia.\" — Woodrow Wilson, ao justificar a entrada dos EUA na guerra."
  },
  alemanha: {
    title: "Alemanha",
    leader: "Delegação alemã",
    role: "A Nação Derrotada",
    text:
      "Buscava reduzir perdas territoriais, militares e financeiras, mas teve pouca influência nas decisões centrais da Conferência de Paz. A delegação alemã não participou das negociações e recebeu as condições prontas, sendo pressionada a assinar sob ameaça de invasão.",
    objectives: [
      "Negociar termos menos severos para o tratado",
      "Preservar a integridade territorial do país",
      "Manter capacidade econômica de recuperação",
      "Rejeitar a cláusula de culpa exclusiva pela guerra"
    ],
    quote: "\"Este tratado é uma sentença de morte para a Alemanha.\" — Reação da imprensa alemã ao conhecer os termos do acordo."
  }
};

const participantFlags = document.querySelectorAll(".flag-card");
const interestResult = document.getElementById("interest-result");
const interestTitle = document.getElementById("interest-title");
const interestText = document.getElementById("interest-text");
const interestLeader = document.getElementById("interest-leader");
const interestRole = document.getElementById("interest-role");
const interestObjectivesList = document.getElementById("interest-objectives-list");
const interestQuote = document.getElementById("interest-quote");

function renderParticipantInterest(participantId) {
  const content = participantInterests[participantId];
  if (!content) return;

  if (interestTitle) interestTitle.textContent = content.title;
  if (interestLeader) interestLeader.textContent = content.leader;
  if (interestRole) interestRole.textContent = content.role;
  if (interestText) interestText.textContent = content.text;

  if (interestObjectivesList) {
    interestObjectivesList.innerHTML = "";
    (content.objectives || []).forEach((obj) => {
      const li = document.createElement("li");
      li.textContent = obj;
      interestObjectivesList.appendChild(li);
    });
  }

  if (interestQuote) interestQuote.textContent = content.quote || "";
  if (interestResult) interestResult.hidden = false;
}

if (participantFlags.length) {
  participantFlags.forEach((flag) => {
    flag.addEventListener("click", () => {
      const participantId = flag.dataset.participant;
      participantFlags.forEach((btn) => {
        const isActive = btn === flag;
        btn.classList.toggle("active", isActive);
        btn.setAttribute("aria-selected", String(isActive));
      });
      renderParticipantInterest(participantId);
    });
  });
}

const intelPhotoCards = document.querySelectorAll(".intel-photo-card");
if (intelPhotoCards.length) {
  intelPhotoCards.forEach((card) => {
    card.classList.remove("is-flipped");
    card.setAttribute("aria-pressed", "false");
  });

  intelPhotoCards.forEach((card) => {
    card.addEventListener("click", () => {
      const isAlreadyFlipped = card.classList.contains("is-flipped");
      intelPhotoCards.forEach((item) => {
        item.classList.remove("is-flipped");
        item.setAttribute("aria-pressed", "false");
      });

      if (!isAlreadyFlipped) {
        card.classList.add("is-flipped");
        card.setAttribute("aria-pressed", "true");
      }
    });
  });
}

const enlistForm = document.getElementById("enlist-form");
const enlistName = document.getElementById("enlist-name");
const enlistClass = document.getElementById("enlist-class");
const enlistAvatarToggle = document.getElementById("enlist-avatar-toggle");
const enlistAvatarPanel = document.getElementById("enlist-avatar-panel");
const enlistAvatarGrid = document.getElementById("enlist-avatar-grid");
const enlistFeedback = document.getElementById("enlist-feedback");
const enlistCard = document.getElementById("enlist-card");
const enlistCardAvatar = document.getElementById("enlist-card-avatar");
const enlistCardName = document.getElementById("enlist-card-name");
const enlistCardClass = document.getElementById("enlist-card-class");
const enlistCardId = document.getElementById("enlist-card-id");
const enlistCardIssued = document.getElementById("enlist-card-issued");
const heroBanner = document.getElementById("hero-banner");
const heroRecruit = document.getElementById("hero-recruit");
const heroRecruitAvatar = document.getElementById("hero-recruit-avatar");
const heroRecruitName = document.getElementById("hero-recruit-name");
const heroRecruitClass = document.getElementById("hero-recruit-class");
let selectedAvatarUrl = "";
let selectedAvatarLabel = "";
let isAvatarPanelOpen = true;

function normalizeInput(value) {
  return String(value || "").trim().replace(/\s+/g, " ");
}

function setEnlistFeedback(message, status) {
  if (!enlistFeedback) return;
  enlistFeedback.textContent = message || "";
  enlistFeedback.classList.remove("is-error", "is-success");
  if (status) {
    enlistFeedback.classList.add(status);
  }
}

function setAvatarGuideOpen(isOpen) {
  if (!enlistAvatarToggle || !enlistAvatarPanel) return;
  isAvatarPanelOpen = Boolean(isOpen);
  enlistAvatarToggle.setAttribute("aria-expanded", String(isAvatarPanelOpen));
  enlistAvatarPanel.classList.toggle("is-collapsed", !isAvatarPanelOpen);
}

function generateRecruitNumber(issueDate) {
  const yearShort = String(issueDate.getFullYear()).slice(-2);
  const month = String(issueDate.getMonth() + 1).padStart(2, "0");
  const day = String(issueDate.getDate()).padStart(2, "0");
  const randomSuffix = String(Math.floor(Math.random() * 10000)).padStart(4, "0");
  return `TRN-${yearShort}${month}${day}-${randomSuffix}`;
}

function formatIssueDate(issueDate) {
  return issueDate.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  });
}

function svgToDataUri(svgMarkup) {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgMarkup)}`;
}

function createMilitaryStickerAvatar(sex, seed) {
  const framePairs = [
    ["#efe2cc", "#c7b596"],
    ["#e9dcc5", "#c1af90"],
    ["#f1e4cd", "#c9b89b"],
    ["#ece0ca", "#c6b294"]
  ];
  const backgrounds = [
    ["#7d6f5e", "#453d35"],
    ["#887665", "#4b4138"],
    ["#71695f", "#3f3b36"],
    ["#8d7b67", "#4e453b"],
    ["#6f6a64", "#3f3d3a"],
    ["#7a736a", "#46433f"]
  ];
  const skinTones = [
    { hi: "#f6decb", mid: "#ecc7aa", low: "#cea986", blush: "#be816f" }, // Pale
    { hi: "#f2d1b6", mid: "#e3b590", low: "#bf8f69", blush: "#ac725f" }, // Fair
    { hi: "#e6b78f", mid: "#d29a74", low: "#ae7656", blush: "#9b644f" }, // Medium Light
    { hi: "#cf9d77", mid: "#b77f5d", low: "#986649", blush: "#885847" }, // Medium
    { hi: "#ad7b5b", mid: "#916044", low: "#774d37", blush: "#6c4638" }, // Medium Dark
    { hi: "#8d6046", mid: "#744b36", low: "#5e3a2a", blush: "#523328" }, // Dark
    { hi: "#714a33", mid: "#5b3724", low: "#462718", blush: "#3d2216" }, // Deep Dark
    { hi: "#513222", mid: "#3d2215", low: "#28140a", blush: "#200e05" }, // Very Deep Dark
    { hi: "#e3b680", mid: "#cc9c60", low: "#a87840", blush: "#966235" }, // Golden Medium
    { hi: "#915037", mid: "#763c26", low: "#5d2a17", blush: "#502010" }  // Rich Red-Brown
  ];
  const eyeColors = [
    { iris: "#2b2319", ring: "#120e0a" },
    { iris: "#3e4d31", ring: "#202818" },
    { iris: "#4b6172", ring: "#2a3a45" },
    { iris: "#5f442d", ring: "#372516" },
    { iris: "#697945", ring: "#3c4628" },
    { iris: "#54697a", ring: "#32414e" }
  ];
  const hairPalettes = [
    { base: "#161311", shadow: "#0c0a09", shine: "#332b27" },
    { base: "#201b18", shadow: "#110e0c", shine: "#3e3530" },
    { base: "#32261e", shadow: "#1b1410", shine: "#544337" },
    { base: "#423126", shadow: "#261b14", shine: "#65503f" },
    { base: "#553d2e", shadow: "#33251c", shine: "#785e49" },
    { base: "#684934", shadow: "#423025", shine: "#8b6a52" },
    { base: "#7b5132", shadow: "#53351f", shine: "#9c6a47" },
    { base: "#8e5c33", shadow: "#624025", shine: "#ad7650" },
    { base: "#9e6734", shadow: "#704926", shine: "#be8454" },
    { base: "#b07e45", shadow: "#845f34", shine: "#c99a64" },
    { base: "#bd9457", shadow: "#94703f", shine: "#d6b176" },
    { base: "#cfaf75", shadow: "#a48857", shine: "#e1c591" },
    { base: "#d9bf8a", shadow: "#b49c71", shine: "#e8d3a7" },
    { base: "#7a797d", shadow: "#565559", shine: "#a3a2a6" },
    { base: "#989694", shadow: "#72706f", shine: "#c0bebc" },
    { base: "#b8b5b3", shadow: "#92908e", shine: "#d8d6d4" },
    { base: "#cbc8c4", shadow: "#a8a5a1", shine: "#ece9e5" }
  ];
  const uniformMain = ["#596145", "#4c553e", "#656b4d", "#576247", "#60644a"];
  const uniformShade = ["#3d4533", "#343d2d", "#474c39", "#394533", "#42462f"];
  const capMain = ["#5a6348", "#4b563d", "#676f51", "#556146", "#60664a"];
  const capBrim = ["#3c4632", "#333d2c", "#434d36", "#36402f", "#3e422e"];
  const badgeColor = ["#ccb679", "#bda367", "#d6c593", "#b89960"];
  const accentColors = ["#6d2926", "#2b4562", "#2c4d38", "#704425"];
  const femaleMouths = [
    "M52 74 Q60 77 68 74",
    "M52 74 Q60 76.3 68 74",
    "M52 74 Q60 75.5 68 74",
    "M52 74 Q60 76.8 68 74"
  ];
  const maleMouths = [
    "M53 74 Q60 76.4 67 74",
    "M53 74 Q60 75.8 67 74",
    "M53 74 Q60 75.2 67 74",
    "M53 74 Q60 76 67 74"
  ];

  const id = `${sex}-${seed}`;
  const frame = framePairs[(seed * 5) % framePairs.length];
  const bgPair = backgrounds[seed % backgrounds.length];
  const skin = skinTones[(seed * 3) % skinTones.length];
  const eye = eyeColors[(seed * 7) % eyeColors.length];
  const hair = hairPalettes[(seed * 11) % hairPalettes.length];
  const uniform = uniformMain[(seed * 13) % uniformMain.length];
  const uniformDark = uniformShade[(seed * 17) % uniformShade.length];
  const cap = capMain[(seed * 19) % capMain.length];
  const capBand = capBrim[(seed * 23) % capBrim.length];
  const badge = badgeColor[(seed * 29) % badgeColor.length];
  const accent = accentColors[(seed * 31) % accentColors.length];

  const femaleProfiles = [
    { rx: 19.8, ry: 22.8, mouthY: 74.1, browWeight: 1.4, lip: "#8a5a4b" },
    { rx: 20.4, ry: 22.2, mouthY: 74.4, browWeight: 1.35, lip: "#855447" },
    { rx: 19.4, ry: 23.2, mouthY: 74.2, browWeight: 1.3, lip: "#7e4f43" },
    { rx: 20.2, ry: 22.6, mouthY: 74.5, browWeight: 1.35, lip: "#8d5d4e" }
  ];
  const maleProfiles = [
    { rx: 21.8, ry: 22.1, mouthY: 74.1, browWeight: 1.9, lip: "#6f4a3a" },
    { rx: 22.2, ry: 21.7, mouthY: 74.3, browWeight: 2.0, lip: "#684334" },
    { rx: 21.4, ry: 22.5, mouthY: 74.2, browWeight: 1.85, lip: "#744d3c" },
    { rx: 22.4, ry: 21.5, mouthY: 74.3, browWeight: 2.0, lip: "#6a4637" }
  ];
  const profile = sex === "f"
    ? femaleProfiles[(seed * 2) % femaleProfiles.length]
    : maleProfiles[(seed * 2) % maleProfiles.length];

  const mouthShape = sex === "f"
    ? femaleMouths[(seed * 3) % femaleMouths.length]
    : maleMouths[(seed * 3) % maleMouths.length];

  const eyebrowTilt = (seed % 5) - 2;
  const moustache = sex === "m" && seed % 5 === 0;
  const beardShadow = sex === "m" && seed % 4 === 0;
  const freckles = seed % 13 === 0;
  const glasses = seed % 8 === 0;
  const femaleStyle = seed % 8;
  const maleStyle = seed % 8;

  const scratches = Array.from({ length: 4 }, (_, i) => {
    const y = 16 + ((seed * 11 + i * 13) % 88);
    const x1 = 14 + ((seed * 7 + i * 19) % 20);
    const x2 = 88 + ((seed * 3 + i * 17) % 18);
    return `<line x1="${x1}" y1="${y}" x2="${x2}" y2="${y + ((i % 2) * 1.1)}" stroke="rgba(255,255,255,0.028)" stroke-width="0.6"/>`;
  }).join("");

  const grainDots = Array.from({ length: 12 }, (_, i) => {
    const gx = 14 + ((seed * 17 + i * 11) % 92);
    const gy = 14 + ((seed * 13 + i * 7) % 92);
    const gr = 0.3 + ((seed + i * 2) % 4) * 0.18;
    return `<circle cx="${gx}" cy="${gy}" r="${gr}" fill="rgba(32,24,18,0.08)"/>`;
  }).join("");

  const stains = Array.from({ length: 2 }, (_, i) => {
    const sx = 16 + ((seed * 23 + i * 29) % 88);
    const sy = 16 + ((seed * 31 + i * 17) % 88);
    const sr = 5 + ((seed + i * 3) % 5);
    return `<circle cx="${sx}" cy="${sy}" r="${sr}" fill="rgba(90,70,52,0.03)"/>`;
  }).join("");

  let hairLayer = "";
  if (sex === "f") {
    if (femaleStyle === 0) {
      hairLayer = `
        <path d="M34 58 Q34 29 60 29 Q86 29 86 58 L86 76 Q86 93 72 98 L69 82 Q76 77 76 66 L76 57 Q76 42 60 42 Q44 42 44 57 L44 66 Q44 77 51 82 L48 98 Q34 93 34 76 Z" fill="${hair.base}" opacity="0.98"/>
        <path d="M42 45 Q60 36 78 45 Q70 38 60 38 Q50 38 42 45 Z" fill="${hair.shine}" opacity="0.28"/>
        <path d="M39 67 Q35 76 38 86 Q41 82 42 74 Z" fill="${hair.shadow}" opacity="0.38"/>
        <path d="M81 67 Q85 76 82 86 Q79 82 78 74 Z" fill="${hair.shadow}" opacity="0.38"/>
      `;
    } else if (femaleStyle === 1) {
      hairLayer = `
        <path d="M36 58 Q37 31 60 31 Q83 31 84 58 L84 73 Q84 86 75 92 L45 92 Q36 86 36 73 Z" fill="${hair.base}" opacity="0.98"/>
        <path d="M44 47 Q61 40 76 47 Q69 41 60 41 Q52 41 44 47 Z" fill="${hair.shine}" opacity="0.25"/>
        <path d="M46 92 Q60 88 74 92 Q60 96 46 92 Z" fill="${hair.shadow}" opacity="0.35"/>
      `;
    } else if (femaleStyle === 2) {
      hairLayer = `
        <path d="M34 57 Q36 30 60 30 Q84 30 86 57 L84 68 Q82 83 69 91 L67 80 Q74 74 74 64 L74 56 Q74 43 60 43 Q46 43 46 56 L46 64 Q46 74 53 80 L51 91 Q38 83 36 68 Z" fill="${hair.base}" opacity="0.98"/>
        <path d="M41 45 Q60 37 79 45 Q71 39 60 39 Q49 39 41 45 Z" fill="${hair.shine}" opacity="0.25"/>
      `;
    } else if (femaleStyle === 3) {
      hairLayer = `
        <path d="M35 58 Q35 32 60 32 Q85 32 85 58 L85 71 Q85 89 71 96 L49 96 Q35 89 35 71 Z" fill="${hair.base}" opacity="0.98"/>
        <path d="M43 48 Q60 41 77 48 Q69 42 60 42 Q51 42 43 48 Z" fill="${hair.shine}" opacity="0.24"/>
        <path d="M49 96 Q60 90 71 96 Q60 99 49 96 Z" fill="${hair.shadow}" opacity="0.33"/>
      `;
    } else if (femaleStyle === 4) {
      hairLayer = `
        <path d="M33 58 Q34 30 60 30 Q86 30 87 58 L87 78 Q87 95 73 100 L70 84 Q77 78 77 67 L77 57 Q77 42 60 42 Q43 42 43 57 L43 67 Q43 78 50 84 L47 100 Q33 95 33 78 Z" fill="${hair.base}" opacity="0.98"/>
        <path d="M41 45 Q60 36 79 45 Q70 37 60 37 Q50 37 41 45 Z" fill="${hair.shine}" opacity="0.27"/>
      `;
    } else if (femaleStyle === 5) {
      hairLayer = `
        <path d="M28 58 Q28 25 60 25 Q92 25 92 58 Q92 78 80 88 Q70 80 60 90 Q45 80 40 88 Q28 78 28 58 Z" fill="${hair.base}" opacity="0.98"/>
        <path d="M38 42 Q60 32 82 42 Q70 36 60 36 Q50 36 38 42 Z" fill="${hair.shine}" opacity="0.25"/>
      `;
    } else if (femaleStyle === 6) {
      hairLayer = `
        <path d="M32 58 Q34 30 60 30 Q86 30 88 58 L85 92 Q80 100 78 90 L75 95 Q70 98 70 85 L65 92 L60 85 Q50 80 44 85 L40 92 Q35 98 35 90 L32 92 Z" fill="${hair.base}" opacity="0.98"/>
        <path d="M40 46 Q60 38 78 46 Q70 42 60 42 Q50 42 40 46 Z" fill="${hair.shine}" opacity="0.25"/>
      `;
    } else {
      hairLayer = `
        <path d="M36 55 Q32 35 60 30 Q88 35 84 55 Q80 70 75 75 Q60 65 45 75 Q40 70 36 55 Z" fill="${hair.base}" opacity="0.98"/>
        <path d="M42 46 Q60 39 78 46 Q70 43 60 43 Q50 43 42 46 Z" fill="${hair.shine}" opacity="0.25"/>
      `;
    }
  } else if (maleStyle === 0) {
    hairLayer = `
      <path d="M39 51 Q44 34 60 34 Q76 34 81 51 L77 52 Q73 43 60 43 Q47 43 43 52 Z" fill="${hair.base}" opacity="0.98"/>
      <path d="M45 46 Q60 40 75 46 Q68 41 60 41 Q52 41 45 46 Z" fill="${hair.shine}" opacity="0.24"/>
    `;
  } else if (maleStyle === 1) {
    hairLayer = `
      <path d="M37 53 Q40 35 60 35 Q80 35 83 53 L78 53 Q75 45 60 45 Q45 45 42 53 Z" fill="${hair.base}" opacity="0.98"/>
      <path d="M43 48 Q60 42 77 48 Q69 43 60 43 Q51 43 43 48 Z" fill="${hair.shine}" opacity="0.24"/>
    `;
  } else if (maleStyle === 2) {
    hairLayer = `
      <path d="M40 51 Q45 36 60 36 Q75 36 80 51 L76 52 Q72 45 60 45 Q48 45 44 52 Z" fill="${hair.base}" opacity="0.98"/>
      <path d="M46 47 Q60 42 74 47 Q67 43 60 43 Q53 43 46 47 Z" fill="${hair.shine}" opacity="0.25"/>
    `;
  } else if (maleStyle === 3) {
    hairLayer = `
      <path d="M38 52 Q42 35 60 35 Q78 35 82 52 L77 53 Q73 45 60 45 Q47 45 43 53 Z" fill="${hair.base}" opacity="0.98"/>
      <path d="M44 47 Q60 41 76 47 Q68 42 60 42 Q52 42 44 47 Z" fill="${hair.shine}" opacity="0.24"/>
      <path d="M39 52 Q38 58 41 64 Q44 60 44 53 Z" fill="${hair.shadow}" opacity="0.35"/>
      <path d="M81 52 Q82 58 79 64 Q76 60 76 53 Z" fill="${hair.shadow}" opacity="0.35"/>
    `;
  } else if (maleStyle === 4) {
    hairLayer = `
      <path d="M37 51 Q42 33 60 33 Q78 33 83 51 L78 52 Q74 43 60 43 Q46 43 42 52 Z" fill="${hair.base}" opacity="0.98"/>
      <path d="M43 46 Q60 39 77 46 Q69 40 60 40 Q51 40 43 46 Z" fill="${hair.shine}" opacity="0.25"/>
    `;
  } else if (maleStyle === 5) {
    hairLayer = `
      <path d="M37 53 Q35 34 60 30 Q85 34 83 53 L78 52 Q75 42 60 42 Q45 42 42 52 Z" fill="${hair.base}" opacity="0.98"/>
      <path d="M42 47 Q60 39 78 47 Q70 43 60 43 Q50 43 42 47 Z" fill="${hair.shine}" opacity="0.24"/>
    `;
  } else if (maleStyle === 6) {
    hairLayer = `
      <path d="M38 52 Q40 38 60 38 Q80 38 82 52 L78 51 Q75 44 60 44 Q45 44 42 51 Z" fill="${hair.base}" opacity="0.98"/>
      <path d="M42 46 Q60 40 78 46 Q70 43 60 43 Q50 43 42 46 Z" fill="${hair.shine}" opacity="0.24"/>
    `;
  } else {
    hairLayer = `
      <path d="M39 52 Q42 38 60 38 Q78 38 81 52 L77 51 Q74 44 60 44 Q46 44 43 51 Z" fill="${hair.base}" opacity="0.3"/>
    `;
  }

  const blushLayer = sex === "f"
    ? `<ellipse cx="49" cy="68" rx="4" ry="2.4" fill="${skin.blush}" opacity="0.25"/><ellipse cx="71" cy="68" rx="4" ry="2.4" fill="${skin.blush}" opacity="0.25"/>`
    : "";

  const lashLayer = sex === "f"
    ? `<path d="M48.4 60.1 L49.2 58.7 M52 59.8 L52.1 58.3 M54.6 60.1 L53.8 58.7 M65.4 60.1 L66.2 58.7 M68 59.8 L68.1 58.3 M70.6 60.1 L69.8 58.7" stroke="rgba(55,38,27,0.48)" stroke-width="0.6" stroke-linecap="round"/>`
    : "";

  const glassesLayer = glasses
    ? `<rect x="46" y="59" width="9.4" height="6.6" rx="1.8" fill="none" stroke="#4b3a2f" stroke-width="1.2"/><rect x="64.6" y="59" width="9.4" height="6.6" rx="1.8" fill="none" stroke="#4b3a2f" stroke-width="1.2"/><path d="M55.4 62.2 H64.6" stroke="#4b3a2f" stroke-width="1.1" fill="none"/>`
    : "";

  const insigniaLayer = `
    <circle cx="60" cy="47.5" r="3.5" fill="${badge}"/>
    <path d="M60 44.4 L61 46.5 L63.4 46.7 L61.6 48.2 L62.1 50.5 L60 49.2 L57.9 50.5 L58.4 48.2 L56.6 46.7 L59 46.5 Z" fill="#f2dfb0"/>
  `;

  const tieLayer = seed % 4 === 0
    ? `<path d="M58.4 86 H61.6 L60.9 95 H59.1 Z" fill="${accent}" opacity="0.88"/>`
    : `<path d="M56 86 Q60 89 64 86" stroke="${accent}" stroke-width="1.6" fill="none" opacity="0.76"/>`;

  const cornerFolds = `
    <path d="M4 4 L20 4 L12 12 L4 20 Z" fill="rgba(90,74,56,0.12)"/>
    <path d="M116 4 L100 4 L108 12 L116 20 Z" fill="rgba(90,74,56,0.12)"/>
    <path d="M4 116 L20 116 L12 108 L4 100 Z" fill="rgba(90,74,56,0.1)"/>
    <path d="M116 116 L100 116 L108 108 L116 100 Z" fill="rgba(90,74,56,0.1)"/>
  `;

  const svgMarkup = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">
      <defs>
        <linearGradient id="paper-${id}" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="${frame[0]}"/>
          <stop offset="100%" stop-color="${frame[1]}"/>
        </linearGradient>
        <linearGradient id="bgGrad-${id}" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="${bgPair[0]}"/>
          <stop offset="100%" stop-color="${bgPair[1]}"/>
        </linearGradient>
        <radialGradient id="vignette-${id}" cx="50%" cy="46%" r="77%">
          <stop offset="46%" stop-color="rgba(0,0,0,0)"/>
          <stop offset="100%" stop-color="rgba(0,0,0,0.34)"/>
        </radialGradient>
        <radialGradient id="skinGrad-${id}" cx="46%" cy="33%" r="67%">
          <stop offset="0%" stop-color="${skin.hi}"/>
          <stop offset="62%" stop-color="${skin.mid}"/>
          <stop offset="100%" stop-color="${skin.low}"/>
        </radialGradient>
        <linearGradient id="uniformGrad-${id}" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="${uniform}"/>
          <stop offset="100%" stop-color="${uniformDark}"/>
        </linearGradient>
        <linearGradient id="capGrad-${id}" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="${cap}"/>
          <stop offset="100%" stop-color="${capBand}"/>
        </linearGradient>
      </defs>

      <rect x="4" y="4" width="112" height="112" rx="10" fill="url(#paper-${id})"/>
      ${cornerFolds}
      <rect x="9" y="9" width="102" height="102" rx="8" fill="#27221d"/>
      <rect x="12" y="12" width="96" height="96" rx="7" fill="url(#bgGrad-${id})"/>
      <rect x="12" y="12" width="96" height="96" rx="7" fill="url(#vignette-${id})"/>
      <rect x="12" y="12" width="96" height="96" rx="7" fill="rgba(102,72,45,0.04)"/>

      <path d="M26 108 L26 94 Q60 72 94 94 L94 108 Z" fill="url(#uniformGrad-${id})"/>
      <path d="M43 92 L60 79 L77 92 L77 108 L43 108 Z" fill="${uniformDark}" opacity="0.36"/>
      <path d="M37 95 Q49 87 60 95 Q71 87 83 95" stroke="rgba(0,0,0,0.24)" stroke-width="1.3" fill="none"/>
      <rect x="40" y="95" width="10.6" height="4.2" rx="2" fill="${badge}" opacity="0.76"/>
      <rect x="69.4" y="95" width="10.6" height="4.2" rx="2" fill="${badge}" opacity="0.76"/>
      <rect x="57" y="80.4" width="6" height="9.6" rx="2.6" fill="${skin.low}"/>
      ${tieLayer}

      <ellipse cx="60" cy="58" rx="${profile.rx}" ry="${profile.ry}" fill="url(#skinGrad-${id})"/>
      <ellipse cx="60" cy="85.2" rx="17" ry="8" fill="rgba(0,0,0,0.08)"/>
      <circle cx="39.5" cy="60" r="3.7" fill="${skin.mid}" opacity="0.95"/>
      <circle cx="80.5" cy="60" r="3.7" fill="${skin.mid}" opacity="0.95"/>
      <ellipse cx="52.2" cy="51.2" rx="8.2" ry="5.1" fill="rgba(255,255,255,0.14)"/>
      <path d="M47 70 Q60 76 73 70" fill="none" stroke="rgba(90,59,44,0.22)" stroke-width="0.9"/>

      ${hairLayer}
      <path d="M33 46 Q60 27 87 46 L87 50 L33 50 Z" fill="url(#capGrad-${id})"/>
      <rect x="31" y="49" width="58" height="7" rx="3.5" fill="${capBand}"/>
      ${insigniaLayer}

      <path d="M45 ${56 + eyebrowTilt} Q52 ${54 + eyebrowTilt} 56 ${56 + eyebrowTilt}" stroke="${hair.shadow}" stroke-width="${profile.browWeight}" fill="none" stroke-linecap="round" opacity="0.84"/>
      <path d="M64 ${56 - eyebrowTilt} Q68 ${54 - eyebrowTilt} 75 ${56 - eyebrowTilt}" stroke="${hair.shadow}" stroke-width="${profile.browWeight}" fill="none" stroke-linecap="round" opacity="0.84"/>

      <ellipse cx="52" cy="62" rx="2.3" ry="2.05" fill="#efe9df"/>
      <ellipse cx="68" cy="62" rx="2.3" ry="2.05" fill="#efe9df"/>
      <circle cx="52" cy="62" r="1.5" fill="${eye.iris}"/>
      <circle cx="68" cy="62" r="1.5" fill="${eye.iris}"/>
      <circle cx="52.4" cy="61.5" r="0.43" fill="#ffffff" opacity="0.87"/>
      <circle cx="68.4" cy="61.5" r="0.43" fill="#ffffff" opacity="0.87"/>
      <circle cx="52" cy="62" r="0.63" fill="${eye.ring}"/>
      <circle cx="68" cy="62" r="0.63" fill="${eye.ring}"/>
      ${lashLayer}

      ${glassesLayer}
      <path d="M57 66.4 Q60 69 63 71.2" stroke="#7f5d47" stroke-width="1.05" fill="none" stroke-linecap="round" opacity="0.7"/>
      <path d="${mouthShape}" transform="translate(0 ${profile.mouthY - 74})" stroke="${profile.lip}" stroke-width="1.55" fill="none" stroke-linecap="round" opacity="0.92"/>
      ${moustache ? `<path d="M51 73.6 Q56 71.7 60 73.8 Q64 71.7 69 73.6" stroke="${hair.shadow}" stroke-width="1.6" fill="none" stroke-linecap="round" opacity="0.74"/>` : ""}
      ${beardShadow ? `<path d="M48 75 Q60 82 72 75 Q70 86 60 88 Q50 86 48 75 Z" fill="${hair.shadow}" opacity="0.24"/>` : ""}
      ${freckles ? `<circle cx="47.2" cy="68.4" r="0.5" fill="${skin.low}" opacity="0.35"/><circle cx="49.7" cy="69.2" r="0.45" fill="${skin.low}" opacity="0.35"/><circle cx="70.3" cy="68.8" r="0.5" fill="${skin.low}" opacity="0.35"/><circle cx="72.7" cy="69.5" r="0.45" fill="${skin.low}" opacity="0.35"/>` : ""}
      ${blushLayer}

      <g>${stains}</g>
      <g>${grainDots}</g>
      <g>${scratches}</g>
      <rect x="12" y="12" width="96" height="96" rx="7" fill="none" stroke="rgba(255,255,255,0.17)" stroke-width="1"/>
      <rect x="4" y="4" width="112" height="112" rx="10" fill="none" stroke="rgba(40,30,22,0.38)" stroke-width="1.6"/>
    </svg>
  `;

  return svgToDataUri(svgMarkup);
}

function createEnlistAvatars() {
  const maleLabels = [
    "Soldado britânico", "Soldado europeu", "Soldado americano",
    "Soldado asiático", "Soldado indiano", "Soldado irlandês",
    "Soldado otomano", "Soldado francês", "Soldado brasileiro",
    "Soldado colonial"
  ];
  const femaleLabels = [
    "Enfermeira militar", "Auxiliar do exército", "Soldada latina",
    "Enfermeira asiática", "Auxiliar indiana", "Oficial loira",
    "Enfermeira indígena", "Enfermeira Cruz Vermelha", "Telegrafista militar",
    "Enfermeira mestiça"
  ];
  const avatars = [];
  for (let i = 1; i <= 10; i += 1) {
    avatars.push({
      id: `m-${i}`,
      label: maleLabels[i - 1],
      url: `public/avatars/avatar_m${i}.png`
    });
  }
  for (let i = 1; i <= 10; i += 1) {
    avatars.push({
      id: `f-${i}`,
      label: femaleLabels[i - 1],
      url: `public/avatars/avatar_f${i}.png`
    });
  }
  return avatars;
}

function selectEnlistAvatar(optionButton) {
  if (!optionButton || !enlistAvatarGrid) return;

  const optionButtons = enlistAvatarGrid.querySelectorAll(".enlist-avatar-option");
  optionButtons.forEach((button) => {
    const isSelected = button === optionButton;
    button.classList.toggle("is-selected", isSelected);
    button.setAttribute("aria-pressed", String(isSelected));
  });

  selectedAvatarUrl = optionButton.dataset.avatarUrl || "";
  selectedAvatarLabel = optionButton.dataset.avatarLabel || "";
}

function renderEnlistAvatarOptions() {
  if (!enlistAvatarGrid) return;

  enlistAvatarGrid.innerHTML = "";
  const avatarList = createEnlistAvatars();

  avatarList.forEach((avatar) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "enlist-avatar-option";
    button.dataset.avatarUrl = avatar.url;
    button.dataset.avatarLabel = avatar.label;
    button.setAttribute("aria-pressed", "false");
    button.setAttribute("title", avatar.label);

    const image = document.createElement("img");
    image.src = avatar.url;
    image.alt = avatar.label;
    image.loading = "lazy";

    button.appendChild(image);
    button.addEventListener("click", () => {
      selectEnlistAvatar(button);
      if (enlistFeedback?.classList.contains("is-error")) {
        setEnlistFeedback("", "");
      }
    });

    enlistAvatarGrid.appendChild(button);
  });
}

function renderEnlistCard(fullName, classroom, avatarUrl, avatarLabel) {
  if (!enlistCard || !enlistCardAvatar || !enlistCardName || !enlistCardClass) return;
  const issueDate = new Date();
  const recruitNumber = generateRecruitNumber(issueDate);

  enlistCardAvatar.src = avatarUrl;
  enlistCardAvatar.alt = avatarLabel || "Avatar selecionado";
  enlistCardName.textContent = fullName;
  enlistCardClass.textContent = classroom;
  if (enlistCardId) {
    enlistCardId.textContent = recruitNumber;
  }
  if (enlistCardIssued) {
    enlistCardIssued.textContent = formatIssueDate(issueDate);
  }
  enlistCard.hidden = false;
}

function renderHeroRecruitBadge(fullName, classroom, avatarUrl, avatarLabel) {
  if (!heroBanner || !heroRecruit || !heroRecruitAvatar || !heroRecruitName || !heroRecruitClass) return;

  heroRecruitAvatar.src = avatarUrl;
  heroRecruitAvatar.alt = avatarLabel || "Avatar do aluno";
  heroRecruitName.textContent = fullName;
  heroRecruitClass.textContent = classroom;
  heroRecruit.hidden = false;
  heroBanner.classList.add("has-recruit");
}

if (enlistAvatarGrid) {
  renderEnlistAvatarOptions();
}

if (enlistAvatarToggle && enlistAvatarPanel) {
  setAvatarGuideOpen(true);
  enlistAvatarToggle.addEventListener("click", () => {
    setAvatarGuideOpen(!isAvatarPanelOpen);
  });
}

if (enlistForm && enlistName && enlistClass) {
  enlistForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const fullName = normalizeInput(enlistName.value);
    const classroom = normalizeInput(enlistClass.value);

    if (fullName.split(" ").length < 2) {
      setEnlistFeedback("Informe o nome completo (nome e sobrenome).", "is-error");
      enlistName.focus();
      return;
    }

    if (classroom.length < 2) {
      setEnlistFeedback("Informe a turma corretamente (ex.: 9º A).", "is-error");
      enlistClass.focus();
      return;
    }

    if (!selectedAvatarUrl) {
      setAvatarGuideOpen(true);
      setEnlistFeedback("Selecione um avatar para concluir o alistamento.", "is-error");
      return;
    }

    enlistName.value = fullName;
    enlistClass.value = classroom;
    renderEnlistCard(fullName, classroom, selectedAvatarUrl, selectedAvatarLabel);
    renderHeroRecruitBadge(fullName, classroom, selectedAvatarUrl, selectedAvatarLabel);

    try {
      const numeroRecruta = enlistCardId ? enlistCardId.textContent : "Desconhecido";
      const data = await apiPost('jogadores', {
        nome: fullName,
        turma: classroom,
        numero_recruta: numeroRecruta
      });

      if (data && data.id) {
        currentJogadorId = data.id;
        localStorage.setItem('trincheiras_jogador_id', currentJogadorId);
      }
    } catch (err) {
      console.error("Exceção ao salvar jogador:", err);
    }

    setEnlistFeedback("Credencial emitida com sucesso.", "is-success");
  });
}

const delegationContent = {
  franca: {
    titulo: "Delegação da França",
    texto:
      "Meta central: impedir nova invasão alemã. Defenda indenizações altas, controle militar rígido e garantias de segurança na fronteira.",
    argumentos: [
      "A França sofreu destruição direta no território.",
      "Sem restrições militares, a Alemanha pode se reorganizar rapidamente.",
      "Indenizações ajudariam na reconstrução francesa."
    ]
  },
  reino: {
    titulo: "Delegação do Reino Unido",
    texto:
      "Meta central: manter equilíbrio europeu sem destruir totalmente a economia alemã. Tente um acordo firme, mas viável.",
    argumentos: [
      "Uma Alemanha economicamente quebrada pode gerar instabilidade no continente.",
      "É necessário punir, mas sem criar revolta permanente.",
      "Comércio europeu depende de recuperação econômica."
    ]
  },
  eua: {
    titulo: "Delegação dos Estados Unidos",
    texto:
      "Meta central: aproximar a paz dos 14 Pontos de Wilson. Defenda cooperação internacional e punições menos vingativas.",
    argumentos: [
      "Paz duradoura exige acordos equilibrados.",
      "A Liga das Nações pode mediar conflitos.",
      "Humilhação extrema tende a alimentar novos conflitos."
    ]
  },
  alemanha: {
    titulo: "Delegação da Alemanha",
    texto:
      "Meta central: reduzir punições para preservar o país. Questione a cláusula de culpa total e peça revisão de indenizações.",
    argumentos: [
      "As condições propostas afetam toda a população, não só líderes de guerra.",
      "Reparações excessivas podem colapsar a economia.",
      "Um tratado negociado pode trazer mais estabilidade que um tratado imposto."
    ]
  }
};

const delegationCards = document.querySelectorAll(".delegation-card");
const detailsBox = document.getElementById("delegation-details");

delegationCards.forEach((card) => {
  card.addEventListener("click", () => {
    delegationCards.forEach((item) => item.classList.remove("active"));
    card.classList.add("active");

    const role = card.dataset.role;
    const content = delegationContent[role];

    if (!content || !detailsBox) return;

    const listItems = content.argumentos
      .map((argumento) => `<li>${argumento}</li>`)
      .join("");

    detailsBox.innerHTML = `
      <h3>${content.titulo}</h3>
      <p>${content.texto}</p>
      <ul>${listItems}</ul>
    `;
  });
});

const trenchOrder = document.getElementById("trench-order");
const trenchTitle = document.getElementById("trench-title");
const trenchQuestion = document.getElementById("trench-question");
const trenchOptions = document.getElementById("trench-options");
const trenchFeedback = document.getElementById("trench-feedback");
const trenchReset = document.getElementById("trench-reset");
const trenchProgressFill = document.getElementById("trench-progress-fill");
const trenchSteps = document.querySelectorAll(".trench-step");
const trenchCard = document.querySelector(".trench-card");

const trenchMission = [
  {
    title: "Trincheira 1: A Nova Fronteira",
    question:
      "A Alsácia-Lorena, rica em minérios e indústria siderúrgica, foi retirada da Alemanha. Para qual país ela foi devolvida?",
    options: ["Polônia", "França", "Áustria"],
    correct: 1,
    feedback: "Correto. A Alsácia-Lorena voltou para a França pelo Tratado de Versalhes."
  },
  {
    title: "Trincheira 2: O Peso da Culpa",
    question:
      "Qual artigo declarou que a Alemanha e seus aliados eram responsáveis pelos danos da guerra?",
    options: ["Artigo 231", "Artigo 14", "Artigo 51"],
    correct: 0,
    feedback: "Certo. O Artigo 231 ficou conhecido como a Cláusula de Culpa."
  },
  {
    title: "Trincheira 3: Exército Reduzido",
    question:
      "Após o tratado, qual limite foi imposto ao exército alemão?",
    options: ["500 mil soldados", "250 mil soldados", "100 mil soldados"],
    correct: 2,
    feedback: "Exato. A Alemanha ficou limitada a 100 mil soldados."
  },
  {
    title: "Trincheira 4: Reparações",
    question:
      "As reparações exigidas da Alemanha tinham qual objetivo principal para os vencedores?",
    options: [
      "Financiar reconstrução dos países atingidos",
      "Criar uma aliança militar entre Alemanha e França",
      "Expandir o território alemão na Europa Central"
    ],
    correct: 0,
    feedback: "Isso mesmo. As reparações foram apresentadas como compensação pelos danos da guerra."
  },
  {
    title: "Trincheira 5: Paris 1919",
    question:
      "Por que muitos historiadores afirmam que a Alemanha assinou um 'Diktat'?",
    options: [
      "Porque a Alemanha escreveu as cláusulas junto com os vencedores",
      "Porque recebeu as condições quase prontas, com pouca negociação real",
      "Porque escolheu voluntariamente aumentar as punições"
    ],
    correct: 1,
    feedback: "Perfeito. O tratado foi imposto sem participação equilibrada da Alemanha."
  },
  {
    title: "Trincheira 6: Wilson e os 14 Pontos",
    question:
      "Qual era a linha geral defendida por Woodrow Wilson na Conferência de Paz?",
    options: [
      "Punições máximas e ocupação militar permanente",
      "Paz negociada, cooperação internacional e menos vingança",
      "Anexar a Alemanha em partes aos países vizinhos"
    ],
    correct: 1,
    feedback: "Correto. Wilson propôs uma paz mais negociada, com base nos 14 Pontos."
  },
  {
    title: "Trincheira 7: Consequências Políticas",
    question:
      "Como o Tratado de Versalhes se relaciona com a ascensão do nazismo?",
    options: [
      "Reduziu crises econômicas e fortaleceu a democracia alemã",
      "Eliminou o ressentimento nacional e estabilizou totalmente a política",
      "Aprofundou crise e humilhação, favorecendo discursos radicais"
    ],
    correct: 2,
    feedback: "Exato. Crise social e ressentimento foram explorados pelo nazismo nos anos seguintes."
  }
];

let trenchStepIndex = 0;
let trenchLocked = false;
let trenchScore = 0;
let trenchErrors = {};
const trenchScoreEl = document.getElementById("trench-score");

function updateTrenchScore() {
  if (trenchScoreEl) {
    trenchScoreEl.textContent = trenchScore;
  }
}

function setTrenchFeedback(message, status) {
  if (!trenchFeedback) return;
  trenchFeedback.textContent = message || "";
  trenchFeedback.classList.remove("is-error", "is-success");
  if (status) {
    trenchFeedback.classList.add(status);
  }
}

function updateTrenchProgress() {
  if (!trenchSteps.length) return;

  const total = trenchMission.length;
  const progressIndex = Math.min(trenchStepIndex, total - 1);
  const percentage = trenchStepIndex >= total
    ? 100
    : total <= 1
      ? 100
      : (progressIndex / (total - 1)) * 100;

  if (trenchProgressFill) {
    trenchProgressFill.style.width = `${percentage}%`;
  }

  trenchSteps.forEach((step, index) => {
    const isComplete = index < trenchStepIndex;
    const isActive = trenchStepIndex < total && index === trenchStepIndex;
    step.classList.toggle("is-complete", isComplete);
    step.classList.toggle("is-active", isActive);
  });
}

function disableTrenchButtons() {
  if (!trenchOptions) return;
  trenchOptions.querySelectorAll("button").forEach((button) => {
    button.disabled = true;
  });
}

function renderTrenchCompletion() {
  if (!trenchOrder || !trenchTitle || !trenchQuestion || !trenchOptions) return;

  trenchOrder.textContent = "MISSÃO CONCLUÍDA";
  trenchTitle.textContent = "Operação Encerrada";
  trenchQuestion.textContent =
    "Você sobreviveu ao campo de batalha diplomático e concluiu todas as trincheiras! Sua pontuação final foi de " + trenchScore + " pontos.";

  trenchOptions.innerHTML = "";

  if (trenchReset) {
    trenchReset.hidden = false;
  }
  setTrenchFeedback("Missão concluída com sucesso.", "is-success");
  updateTrenchProgress();
}

function advanceTrenchMission() {
  trenchStepIndex += 1;
  trenchLocked = false;
  if (trenchStepIndex >= trenchMission.length) {
    renderTrenchCompletion();
    return;
  }
  renderTrenchQuestion();
}

function handleTrenchOptionClick(button, optionIndex) {
  if (trenchLocked) return;

  const missionStep = trenchMission[trenchStepIndex];
  if (!missionStep) return;

  const optionLabel = missionStep.options[optionIndex];
  let pointsVariation = 0;

  if (optionIndex === missionStep.correct) {
    trenchLocked = true;
    disableTrenchButtons();
    pointsVariation = 10;
    trenchScore += pointsVariation;
    updateTrenchScore();
    button.classList.add("is-correct");
    setTrenchFeedback(missionStep.feedback, "is-success");

    if (currentJogadorId) {
      apiPost('respostas', {
        jogador_id: currentJogadorId,
        modulo: 'trincheiras',
        pergunta_id: `trincheira_${trenchStepIndex + 1}`,
        resposta_escolhida: optionLabel,
        correto: true,
        variacao_pontos: pointsVariation
      });
    }

    setTimeout(advanceTrenchMission, 900);
    return;
  }

  if (!trenchErrors[trenchStepIndex]) {
    trenchErrors[trenchStepIndex] = 0;
  }
  if (trenchErrors[trenchStepIndex] < 2) {
    pointsVariation = -5;
    trenchScore += pointsVariation;
    updateTrenchScore();
  }
  trenchErrors[trenchStepIndex]++;

  button.classList.add("is-wrong");
  triggerBombExplosion(button);
  pulseHit(trenchCard);
  setTrenchFeedback("Resposta incorreta. Reavalie os documentos e tente novamente.", "is-error");

  if (currentJogadorId) {
    apiPost('respostas', {
      jogador_id: currentJogadorId,
      modulo: 'trincheiras',
      pergunta_id: `trincheira_${trenchStepIndex + 1}`,
      resposta_escolhida: optionLabel,
      correto: false,
      variacao_pontos: pointsVariation
    });
  }

  setTimeout(() => {
    button.classList.remove("is-wrong");
  }, 420);
}

function renderTrenchQuestion() {
  if (!trenchOrder || !trenchTitle || !trenchQuestion || !trenchOptions) return;

  const missionStep = trenchMission[trenchStepIndex];
  if (!missionStep) {
    renderTrenchCompletion();
    return;
  }

  trenchOrder.textContent = `ORDEM ${trenchStepIndex + 1}/${trenchMission.length}`;
  trenchTitle.textContent = missionStep.title;
  trenchQuestion.textContent = missionStep.question;
  trenchOptions.innerHTML = "";

  missionStep.options.forEach((optionLabel, optionIndex) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "trench-option-btn";
    button.textContent = optionLabel;
    button.addEventListener("click", () => {
      handleTrenchOptionClick(button, optionIndex);
    });
    trenchOptions.appendChild(button);
  });

  if (trenchReset) {
    trenchReset.hidden = true;
  }

  setTrenchFeedback("", "");
  updateTrenchProgress();
}

function resetTrenchMission() {
  trenchStepIndex = 0;
  trenchLocked = false;
  trenchScore = 0;
  trenchErrors = {};
  updateTrenchScore();
  renderTrenchQuestion();
}

if (trenchOrder && trenchTitle && trenchQuestion && trenchOptions) {
  resetTrenchMission();
}

if (trenchReset) {
  trenchReset.addEventListener("click", resetTrenchMission);
}
