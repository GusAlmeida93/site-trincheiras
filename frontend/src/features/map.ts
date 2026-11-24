import * as L from 'leaflet';

import type { MapFeatureRead, MapRegionRead } from '../api/types';
import { byId } from '../lib/dom';

// The generated API type for coordinates is unknown[]; narrow at the boundary.
function asLatLng(value: unknown): L.LatLngTuple {
  if (
    Array.isArray(value) &&
    value.length === 2 &&
    typeof value[0] === 'number' &&
    typeof value[1] === 'number'
  ) {
    return [value[0], value[1]];
  }
  throw new Error('invalid [lat, lng] coordinate in map data');
}

function asLatLngList(value: unknown[]): L.LatLngTuple[] {
  return value.map(asLatLng);
}

export interface MapSection {
  setRegions(regions: MapRegionRead[]): void;
  onPanelShown(): void;
  showFallback(): void;
}

export function createMapSection(): MapSection {
  const container = byId('strategic-map');
  const legendContainer = byId('map-legend');
  const noteEl = byId('map-region-note');
  const regionButtons = document.querySelectorAll<HTMLElement>('.map-region-btn');

  let regions: MapRegionRead[] = [];
  let map: L.Map | null = null;
  let layerGroup: L.LayerGroup | null = null;
  let featureLayers: Record<string, L.Layer> = {};
  let activeRegionSlug = '';
  let panelVisible = false;

  function createFeatureLayer(feature: MapFeatureRead): L.Path {
    const baseStyle: L.PathOptions = {
      color: 'rgba(255,255,255,0.45)',
      weight: 2,
      fillColor: feature.fill_color || '#d8b5a5',
      fillOpacity: 0.5,
      className: 'map-feature-layer',
    };
    const highlightStyle: L.PathOptions = {
      weight: 3,
      color: '#f0d8a0',
      fillOpacity: 0.72,
    };

    const layer: L.Path =
      feature.shape === 'circle'
        ? L.circle(asLatLng(feature.coordinates), {
            ...baseStyle,
            radius: feature.radius_m ?? 180000,
          })
        : L.polygon(asLatLngList(feature.coordinates), baseStyle);

    layer.on('mouseover', () => {
      layer.setStyle(highlightStyle);
      if ('bringToFront' in layer && typeof layer.bringToFront === 'function') {
        layer.bringToFront();
      }
    });
    layer.on('mouseout', () => {
      layer.setStyle(baseStyle);
    });

    if (feature.name || feature.description) {
      const pinSvg =
        '<svg class="map-info-pin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>';
      const popupHtml = `
        <div class="map-info-card">
          <div class="map-info-accent" style="background:${feature.fill_color || '#d8b5a5'}"></div>
          <div class="map-info-body">
            <h4>${pinSvg}${feature.name || ''}</h4>
            <p>${feature.description || ''}</p>
            <hr class="map-info-divider">
            <div class="map-info-detail">
              <span class="map-info-detail-icon">⛏</span>
              <span><strong>Produz:</strong> ${feature.producer || 'informação em revisão.'}</span>
            </div>
            <div class="map-info-detail">
              <span class="map-info-detail-icon">🏳</span>
              <span><strong>Cedida a:</strong> ${feature.ceded_to || 'informação em revisão.'}</span>
            </div>
          </div>
        </div>
      `;
      layer.bindPopup(popupHtml, { maxWidth: 320, className: 'map-enhanced-popup' });
    }

    return layer;
  }

  function renderLegend(region: MapRegionRead): void {
    if (!legendContainer) return;
    legendContainer.innerHTML = '';

    region.features.forEach((feature, index) => {
      const btn = document.createElement('button');
      btn.className = 'map-legend-item';
      btn.type = 'button';
      btn.innerHTML = `<span class="map-legend-swatch" style="background:${feature.fill_color || '#d8b5a5'}"></span>${feature.name}`;

      btn.addEventListener('click', () => {
        legendContainer
          .querySelectorAll('.map-legend-item')
          .forEach((el) => el.classList.remove('is-active'));
        btn.classList.add('is-active');

        const targetLayer = featureLayers[`${region.slug}-${index}`];
        if (targetLayer && map) {
          if (feature.shape === 'circle') {
            map.setView(
              asLatLng(feature.coordinates),
              Math.min(map.getZoom() + 1, 6),
              { animate: true }
            );
          } else if (targetLayer instanceof L.Polygon) {
            map.fitBounds(targetLayer.getBounds(), {
              padding: [40, 40],
              animate: true,
              maxZoom: 7,
            });
          }
          if ('openPopup' in targetLayer) {
            (targetLayer as L.Path).openPopup();
          }
        }
      });

      legendContainer.appendChild(btn);
    });
  }

  function renderRegion(regionSlug: string): void {
    const region = regions.find((r) => r.slug === regionSlug);
    if (!map || !layerGroup || !region) return;

    activeRegionSlug = regionSlug;
    layerGroup.clearLayers();
    featureLayers = {};

    region.features.forEach((feature, index) => {
      const layer = createFeatureLayer(feature);
      layer.addTo(layerGroup!);
      featureLayers[`${region.slug}-${index}`] = layer;
    });

    map.setView([region.center_lat, region.center_lng], region.zoom, {
      animate: true,
    });
    if (noteEl) {
      noteEl.textContent = region.note;
    }

    renderLegend(region);

    regionButtons.forEach((button) => {
      const isActive = button.dataset.mapRegion === regionSlug;
      button.classList.toggle('active', isActive);
      button.setAttribute('aria-selected', String(isActive));
    });
  }

  function tryInit(): void {
    // Leaflet must not initialise inside a hidden panel: tile/viewport maths
    // need real dimensions, hence the activate → init → invalidateSize dance.
    if (map || !container || !panelVisible || !regions.length) return;

    map = L.map(container, {
      zoomControl: true,
      minZoom: 2,
      maxZoom: 8,
      worldCopyJump: true,
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    }).addTo(map);

    layerGroup = L.layerGroup().addTo(map);
    renderRegion(activeRegionSlug || regions[0]!.slug);

    setTimeout(() => {
      map?.invalidateSize();
    }, 80);
  }

  regionButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const regionSlug = button.dataset.mapRegion;
      if (!regionSlug) return;
      if (!map) {
        tryInit();
      }
      renderRegion(regionSlug);
    });
  });

  return {
    setRegions(newRegions: MapRegionRead[]): void {
      regions = newRegions;
      tryInit();
    },
    onPanelShown(): void {
      panelVisible = true;
      tryInit();
      if (map) {
        setTimeout(() => {
          map?.invalidateSize();
        }, 80);
      }
    },
    showFallback(): void {
      if (container) {
        container.innerHTML =
          "<p class='map-fallback'>Não foi possível carregar o mapa interativo.</p>";
      }
    },
  };
}
