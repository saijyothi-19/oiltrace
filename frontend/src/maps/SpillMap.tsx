import React, { useEffect, useRef, useState, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { 
  Layers, 
  Eye, 
  EyeOff, 
  Navigation, 
  Maximize2, 
  ShieldAlert, 
  MapPin, 
  Compass, 
  Ship, 
  Flame,
  Radio,
  AlertTriangle,
  Globe
} from 'lucide-react';
import type { 
  SpillEvent, 
  DriftSimulation, 
  Vessel, 
  VesselCandidate 
} from '../types';
import { 
  getBasemapConfig, 
  getAvailableBasemaps, 
  type BasemapProviderId 
} from './mapConfig';

interface SpillMapProps {
  selectedSpill?: SpillEvent | null;
  driftSimulation?: DriftSimulation | null;
  vessels?: Vessel[];
  candidates?: VesselCandidate[];
  selectedVesselMmsi?: string | null;
  onSelectVessel?: (mmsi: string) => void;
  onSelectSpill?: (spillId: number) => void;
  className?: string;
}

export const SpillMap: React.FC<SpillMapProps> = ({
  selectedSpill,
  driftSimulation,
  vessels = [],
  candidates = [],
  selectedVesselMmsi,
  onSelectVessel,
  onSelectSpill,
  className = 'w-full h-full',
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);

  // Active Basemap State (default: OpenStreetMap, zero API key)
  const [activeBasemap, setActiveBasemap] = useState<BasemapProviderId>('osm');
  const availableBasemaps = getAvailableBasemaps();

  // Map Status / Error State
  const [mapWarning, setMapWarning] = useState<string | null>(null);

  // Layer Visibility States
  const [layers, setLayers] = useState({
    satellite: true,
    spill: true,
    origin: true,
    drift: true,
    aisTracks: true,
    candidates: true,
    centroid: true,
  });
  const [showLayerPanel, setShowLayerPanel] = useState(false);

  // Initialize MapLibre GL
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    // Load initial basemap config (OpenStreetMap by default)
    const basemapConfig = getBasemapConfig(activeBasemap);

    // Initial center: Offshore Mumbai incident area or Arabian Sea corridor
    const initialCenter: [number, number] = selectedSpill?.centroid?.coordinates
      ? [selectedSpill.centroid.coordinates[0], selectedSpill.centroid.coordinates[1]]
      : [72.4, 18.9];

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          'basemap-source': {
            type: 'raster',
            tiles: basemapConfig.tiles,
            tileSize: basemapConfig.tileSize,
            attribution: basemapConfig.attribution,
            maxzoom: basemapConfig.maxzoom,
          },
        },
        layers: [
          {
            id: 'background',
            type: 'background',
            paint: {
              'background-color': '#0a1128', // Deep oceanic dark backdrop
            },
          },
          {
            id: 'basemap-layer',
            type: 'raster',
            source: 'basemap-source',
            minzoom: 0,
            maxzoom: basemapConfig.maxzoom,
            paint: {
              'raster-opacity': 0.88,
            },
          },
        ],
      },
      center: initialCenter,
      zoom: 8.5,
      pitch: 0,
      attributionControl: false, // Custom attribution control added below
    });

    // Add Navigation and Custom Attribution Controls
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ unit: 'nautical' }), 'bottom-left');
    map.addControl(
      new maplibregl.AttributionControl({
        compact: false,
        customAttribution: 'OILTRACE Marine Decision Support &bull; SIH 2026',
      }),
      'bottom-right'
    );

    // Graceful error listener for tile resilience
    map.on('error', (e) => {
      // Catch tile loading errors gracefully without crashing the UI
      if (e?.error && (e.error as any)?.status === 401) {
        setMapWarning('Basemap tile authentication error. Falling back to OpenStreetMap.');
        switchBasemap('osm');
      }
    });

    map.on('load', () => {
      mapRef.current = map;
      setupMapLayers(map);
    });

    return () => {
      if (popupRef.current) popupRef.current.remove();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Switch Basemap dynamically
  const switchBasemap = useCallback((providerId: BasemapProviderId) => {
    const map = mapRef.current;
    if (!map) return;

    const newConfig = getBasemapConfig(providerId);
    setActiveBasemap(providerId);

    const source = map.getSource('basemap-source') as maplibregl.RasterTileSource | undefined;
    if (source && typeof (source as any).setTiles === 'function') {
      (source as any).setTiles(newConfig.tiles);
    } else {
      // Recreate raster source and layer if setTiles is unsupported
      if (map.getLayer('basemap-layer')) map.removeLayer('basemap-layer');
      if (map.getSource('basemap-source')) map.removeSource('basemap-source');

      map.addSource('basemap-source', {
        type: 'raster',
        tiles: newConfig.tiles,
        tileSize: newConfig.tileSize,
        attribution: newConfig.attribution,
        maxzoom: newConfig.maxzoom,
      });

      map.addLayer(
        {
          id: 'basemap-layer',
          type: 'raster',
          source: 'basemap-source',
          minzoom: 0,
          maxzoom: newConfig.maxzoom,
          paint: {
            'raster-opacity': 0.88,
          },
        },
        'satellite-bounds-layer' // Place under analytical vector layers
      );
    }
  }, []);

  // Setup GeoJSON Sources & Layers
  const setupMapLayers = (map: maplibregl.Map) => {
    // 1. Satellite Scene Bounds
    map.addSource('satellite-bounds-source', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });
    map.addLayer({
      id: 'satellite-bounds-layer',
      type: 'line',
      source: 'satellite-bounds-source',
      paint: {
        'line-color': '#06b6d4',
        'line-width': 1.5,
        'line-dasharray': [2, 2],
      },
    });

    // 2. Spill Polygons (SAR Extent Slick)
    map.addSource('spill-source', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });
    map.addLayer({
      id: 'spill-fill',
      type: 'fill',
      source: 'spill-source',
      paint: {
        'fill-color': '#991b1b', // Deep crimson oil slick
        'fill-opacity': 0.70,
      },
    });
    map.addLayer({
      id: 'spill-outline',
      type: 'line',
      source: 'spill-source',
      paint: {
        'line-color': '#ef4444', // Bright red boundary
        'line-width': 2.5,
      },
    });

    // 3. Spill Centroid Marker
    map.addSource('spill-centroid-source', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });
    map.addLayer({
      id: 'spill-centroid-halo',
      type: 'circle',
      source: 'spill-centroid-source',
      paint: {
        'circle-radius': 12,
        'circle-color': '#ef4444',
        'circle-opacity': 0.25,
      },
    });
    map.addLayer({
      id: 'spill-centroid-circle',
      type: 'circle',
      source: 'spill-centroid-source',
      paint: {
        'circle-radius': 5,
        'circle-color': '#ef4444',
        'circle-stroke-color': '#ffffff',
        'circle-stroke-width': 2,
      },
    });

    // 4. Probable Origin Uncertainty Region
    map.addSource('origin-source', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });
    map.addLayer({
      id: 'origin-fill',
      type: 'fill',
      source: 'origin-source',
      paint: {
        'fill-color': '#f59e0b',
        'fill-opacity': 0.30,
      },
    });
    map.addLayer({
      id: 'origin-line',
      type: 'line',
      source: 'origin-source',
      paint: {
        'line-color': '#fbbf24',
        'line-width': 2,
        'line-dasharray': [3, 2],
      },
    });

    // 5. Drift Simulation Trajectories
    map.addSource('drift-source', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });
    map.addLayer({
      id: 'drift-lines',
      type: 'line',
      source: 'drift-source',
      paint: {
        'line-color': ['get', 'color'],
        'line-width': 2.0,
        'line-opacity': 0.85,
      },
    });

    // 6. AIS Vessel Tracks
    map.addSource('ais-tracks-source', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });
    map.addLayer({
      id: 'ais-tracks-line',
      type: 'line',
      source: 'ais-tracks-source',
      paint: {
        'line-color': ['get', 'strokeColor'],
        'line-width': ['get', 'lineWidth'],
        'line-opacity': 0.85,
      },
    });

    // 7. Vessel Positions & Candidate Markers
    map.addSource('vessel-points-source', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });
    map.addLayer({
      id: 'vessel-points-circle',
      type: 'circle',
      source: 'vessel-points-source',
      paint: {
        'circle-radius': ['get', 'radius'],
        'circle-color': ['get', 'color'],
        'circle-stroke-color': '#ffffff',
        'circle-stroke-width': 1.8,
      },
    });

    // Interactive Click Events
    map.on('click', 'spill-fill', (e) => {
      if (!e.features || !e.features[0]) return;
      const props = e.features[0].properties;
      if (props) {
        if (onSelectSpill) onSelectSpill(props.spill_id);
        const coordinates = e.lngLat;
        new maplibregl.Popup({ closeButton: true, offset: 12 })
          .setLngLat(coordinates)
          .setHTML(`
            <div style="font-family: monospace; font-size: 11px; color: #0f172a; padding: 4px;">
              <div style="font-weight: bold; color: #dc2626; margin-bottom: 4px;">OIL SPILL INCIDENT #${props.spill_id}</div>
              <div>Area: <strong>${Number(props.area_km2).toFixed(2)} km²</strong></div>
              <div>Perimeter: <strong>${Number(props.perimeter_km || 0).toFixed(2)} km</strong></div>
              <div>Confidence: <strong>${(Number(props.confidence) * 100).toFixed(1)}%</strong></div>
            </div>
          `)
          .addTo(map);
      }
    });

    map.on('click', 'vessel-points-circle', (e) => {
      if (!e.features || !e.features[0]) return;
      const props = e.features[0].properties;
      if (props && props.mmsi) {
        if (onSelectVessel) onSelectVessel(props.mmsi);
        const coords = (e.features[0].geometry as any).coordinates;
        new maplibregl.Popup({ closeButton: true, offset: 14 })
          .setLngLat(coords)
          .setHTML(`
            <div style="font-family: monospace; font-size: 11px; color: #0f172a; padding: 4px;">
              <div style="font-weight: bold; color: #0284c7; margin-bottom: 2px;">${props.name || 'VESSEL'}</div>
              <div>MMSI: <strong>${props.mmsi}</strong></div>
              <div>Type: <strong>${props.ship_type || 'Commercial'}</strong></div>
              <div>Speed: <strong>${Number(props.speed || 0).toFixed(1)} kts</strong></div>
              <div style="margin-top: 4px;"><span style="background: ${props.color}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: bold;">${props.priority || 'TRACKED'}</span></div>
            </div>
          `)
          .addTo(map);
      }
    });

    map.on('click', 'origin-fill', (e) => {
      if (!e.features || !e.features[0]) return;
      const props = e.features[0].properties;
      new maplibregl.Popup({ closeButton: true, offset: 10 })
        .setLngLat(e.lngLat)
        .setHTML(`
          <div style="font-family: monospace; font-size: 11px; color: #0f172a; padding: 4px;">
            <div style="font-weight: bold; color: #d97706; margin-bottom: 4px;">RECONSTRUCTED ORIGIN ZONE</div>
            <div>Hindcast Origin: <strong>95% Confidence Ellipse</strong></div>
            <div>Simulation ID: <strong>#${props?.simulation_id || 'N/A'}</strong></div>
          </div>
        `)
        .addTo(map);
    });

    // Cursor pointer triggers
    map.on('mouseenter', 'spill-fill', () => { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'spill-fill', () => { map.getCanvas().style.cursor = ''; });
    map.on('mouseenter', 'vessel-points-circle', () => { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'vessel-points-circle', () => { map.getCanvas().style.cursor = ''; });
    map.on('mouseenter', 'origin-fill', () => { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'origin-fill', () => { map.getCanvas().style.cursor = ''; });
  };

  // Update Data Sources when Props Change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    // 1. Update Spill Polygon
    const spillSource = map.getSource('spill-source') as maplibregl.GeoJSONSource | undefined;
    if (spillSource && selectedSpill && selectedSpill.spill_geometry) {
      spillSource.setData({
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            geometry: selectedSpill.spill_geometry,
            properties: {
              spill_id: selectedSpill.id,
              confidence: selectedSpill.confidence,
              area_km2: selectedSpill.area_km2,
              perimeter_km: selectedSpill.perimeter_km,
            },
          },
        ],
      });
    } else if (spillSource) {
      spillSource.setData({ type: 'FeatureCollection', features: [] });
    }

    // 2. Update Spill Centroid
    const centroidSource = map.getSource('spill-centroid-source') as maplibregl.GeoJSONSource | undefined;
    if (centroidSource && selectedSpill && selectedSpill.centroid?.coordinates) {
      centroidSource.setData({
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            geometry: {
              type: 'Point',
              coordinates: selectedSpill.centroid.coordinates,
            },
            properties: {
              spill_id: selectedSpill.id,
            },
          },
        ],
      });
    } else if (centroidSource) {
      centroidSource.setData({ type: 'FeatureCollection', features: [] });
    }

    // 3. Update Satellite Scene Bounding Box
    const satSource = map.getSource('satellite-bounds-source') as maplibregl.GeoJSONSource | undefined;
    if (satSource && selectedSpill && selectedSpill.satellite_image?.bounding_geometry) {
      satSource.setData({
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            geometry: selectedSpill.satellite_image.bounding_geometry,
            properties: {
              satellite: selectedSpill.satellite_image.satellite,
            },
          },
        ],
      });
    } else if (satSource) {
      satSource.setData({ type: 'FeatureCollection', features: [] });
    }

    // 4. Update Origin Geometry
    const originSource = map.getSource('origin-source') as maplibregl.GeoJSONSource | undefined;
    if (originSource && driftSimulation && driftSimulation.origin_probability_geometry) {
      originSource.setData({
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            geometry: driftSimulation.origin_probability_geometry,
            properties: {
              simulation_id: driftSimulation.id,
              confidence: driftSimulation.confidence,
            },
          },
        ],
      });
    } else if (originSource) {
      originSource.setData({ type: 'FeatureCollection', features: [] });
    }

    // 5. Update Drift Trajectories
    const driftSource = map.getSource('drift-source') as maplibregl.GeoJSONSource | undefined;
    if (driftSource && driftSimulation && driftSimulation.particles && driftSimulation.particles.length > 0) {
      const grouped: Record<number, [number, number][]> = {};
      driftSimulation.particles.forEach((p) => {
        if (!grouped[p.particle_id]) grouped[p.particle_id] = [];
        grouped[p.particle_id].push(p.position.coordinates);
      });

      const features = Object.entries(grouped).map(([pId, coords]) => ({
        type: 'Feature' as const,
        geometry: {
          type: 'LineString' as const,
          coordinates: coords,
        },
        properties: {
          particle_id: Number(pId),
          color: driftSimulation.simulation_type === 'BACKWARD' ? '#fb923c' : '#38bdf8',
        },
      }));

      driftSource.setData({ type: 'FeatureCollection', features });
    } else if (driftSource) {
      driftSource.setData({ type: 'FeatureCollection', features: [] });
    }

    // 6. Update AIS Vessel Tracks & Candidate Markers
    const tracksSource = map.getSource('ais-tracks-source') as maplibregl.GeoJSONSource | undefined;
    const pointsSource = map.getSource('vessel-points-source') as maplibregl.GeoJSONSource | undefined;

    if (tracksSource && pointsSource) {
      const trackFeatures: any[] = [];
      const pointFeatures: any[] = [];

      vessels.forEach((vessel) => {
        const isSelected = selectedVesselMmsi === vessel.mmsi;
        const candidate = candidates.find((c) => c.vessel?.mmsi === vessel.mmsi || c.vessel_id === vessel.id);

        let priorityColor = '#94a3b8'; // default low/normal slate
        let markerRadius = 5.5;
        let lineWidth = isSelected ? 3.5 : 1.8;
        let priorityLabel = 'TRACKED';

        if (candidate) {
          priorityLabel = candidate.priority;
          if (candidate.priority === 'HIGH') {
            priorityColor = '#ef4444'; // Red for high priority candidate
            markerRadius = 7.5;
          } else if (candidate.priority === 'MEDIUM') {
            priorityColor = '#f59e0b'; // Amber
            markerRadius = 6.5;
          } else {
            priorityColor = '#38bdf8'; // Sky blue
            markerRadius = 5.5;
          }
        }

        if (isSelected) {
          priorityColor = '#22d3ee'; // Highlight cyan
          markerRadius = 9.0;
        }

        // Add trajectory LineString if positions exist
        if (vessel.positions && vessel.positions.length > 1) {
          const coords = vessel.positions.map((p) => p.position.coordinates);
          trackFeatures.push({
            type: 'Feature',
            geometry: { type: 'LineString', coordinates: coords },
            properties: {
              mmsi: vessel.mmsi,
              name: vessel.name,
              strokeColor: priorityColor,
              lineWidth: lineWidth,
            },
          });
        }

        // Add current/last known point
        if (vessel.positions && vessel.positions.length > 0) {
          const lastPos = vessel.positions[vessel.positions.length - 1];
          pointFeatures.push({
            type: 'Feature',
            geometry: lastPos.position,
            properties: {
              mmsi: vessel.mmsi,
              name: vessel.name,
              ship_type: vessel.ship_type,
              speed: lastPos.speed,
              color: priorityColor,
              radius: markerRadius,
              priority: priorityLabel,
            },
          });
        }
      });

      tracksSource.setData({ type: 'FeatureCollection', features: trackFeatures });
      pointsSource.setData({ type: 'FeatureCollection', features: pointFeatures });
    }

    // Auto-fit to spill bounds when selected
    if (selectedSpill?.centroid?.coordinates) {
      const [lon, lat] = selectedSpill.centroid.coordinates;
      map.flyTo({
        center: [lon, lat],
        zoom: 9.2,
        speed: 1.2,
      });
    }
  }, [selectedSpill, driftSimulation, vessels, candidates, selectedVesselMmsi]);

  // Update Layer Visibility Toggles
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    if (map.getLayer('spill-fill')) {
      map.setLayoutProperty('spill-fill', 'visibility', layers.spill ? 'visible' : 'none');
      map.setLayoutProperty('spill-outline', 'visibility', layers.spill ? 'visible' : 'none');
    }
    if (map.getLayer('spill-centroid-circle')) {
      map.setLayoutProperty('spill-centroid-circle', 'visibility', layers.centroid ? 'visible' : 'none');
      map.setLayoutProperty('spill-centroid-halo', 'visibility', layers.centroid ? 'visible' : 'none');
    }
    if (map.getLayer('satellite-bounds-layer')) {
      map.setLayoutProperty('satellite-bounds-layer', 'visibility', layers.satellite ? 'visible' : 'none');
    }
    if (map.getLayer('origin-fill')) {
      map.setLayoutProperty('origin-fill', 'visibility', layers.origin ? 'visible' : 'none');
      map.setLayoutProperty('origin-line', 'visibility', layers.origin ? 'visible' : 'none');
    }
    if (map.getLayer('drift-lines')) {
      map.setLayoutProperty('drift-lines', 'visibility', layers.drift ? 'visible' : 'none');
    }
    if (map.getLayer('ais-tracks-line')) {
      map.setLayoutProperty('ais-tracks-line', 'visibility', layers.aisTracks ? 'visible' : 'none');
    }
    if (map.getLayer('vessel-points-circle')) {
      map.setLayoutProperty('vessel-points-circle', 'visibility', layers.candidates ? 'visible' : 'none');
    }
  }, [layers]);

  const toggleLayer = (layerKey: keyof typeof layers) => {
    setLayers((prev) => ({ ...prev, [layerKey]: !prev[layerKey] }));
  };

  const resetView = () => {
    const map = mapRef.current;
    if (!map) return;
    if (selectedSpill?.centroid?.coordinates) {
      map.flyTo({
        center: selectedSpill.centroid.coordinates,
        zoom: 9.2,
        speed: 1.5,
      });
    } else {
      map.flyTo({
        center: [72.4, 18.9],
        zoom: 8.5,
        speed: 1.5,
      });
    }
  };

  return (
    <div className={`relative ${className}`}>
      {/* Map Container */}
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Map Warning Banner (if offline or tile warning) */}
      {mapWarning && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-950/90 border border-amber-600 text-amber-200 text-xs shadow-xl backdrop-blur">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          <span>{mapWarning}</span>
          <button 
            onClick={() => setMapWarning(null)} 
            className="ml-2 text-amber-400 hover:text-white font-bold"
          >
            &times;
          </button>
        </div>
      )}

      {/* Layer Toggle Floating Button (Top Left) */}
      <div className="absolute top-4 left-4 z-20 flex flex-col gap-2">
        <button
          onClick={() => setShowLayerPanel(!showLayerPanel)}
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-navy-900/95 border border-slate-700/80 text-slate-200 text-xs shadow-xl backdrop-blur hover:bg-slate-800 transition-colors"
        >
          <Layers className="w-4 h-4 text-cyan-400" />
          <span className="font-semibold font-mono">GIS Controls</span>
        </button>

        {/* Layer Controls Panel */}
        {showLayerPanel && (
          <div className="w-64 p-3.5 rounded-lg bg-navy-900/95 border border-slate-700/80 shadow-2xl backdrop-blur text-xs space-y-3">
            {/* Basemap Selection */}
            <div>
              <div className="text-[10px] font-mono font-semibold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <Globe className="w-3 h-3 text-indigo-400" />
                <span>Geographic Basemap</span>
              </div>
              <div className="grid grid-cols-2 gap-1.5 bg-slate-950/80 p-1 rounded-lg border border-slate-800">
                {availableBasemaps.map((b) => (
                  <button
                    key={b.id}
                    onClick={() => switchBasemap(b.id)}
                    className={`px-2 py-1.5 text-[11px] rounded font-medium transition text-center ${
                      activeBasemap === b.id
                        ? 'bg-indigo-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    }`}
                    title={b.description}
                  >
                    {b.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Analytical Vector Overlays */}
            <div>
              <div className="text-[10px] font-mono font-semibold text-slate-400 uppercase tracking-wider mb-2 border-b border-slate-800 pb-1 flex justify-between items-center">
                <span>Analytical Overlays</span>
                <button 
                  onClick={resetView}
                  className="text-[10px] text-cyan-400 hover:underline flex items-center gap-0.5"
                  title="Recenter Map on Incident"
                >
                  <Maximize2 className="w-3 h-3" /> Fit
                </button>
              </div>

              <div className="space-y-1.5 font-mono text-[11px]">
                <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer select-none">
                  <span className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
                    Oil Spill Slick
                  </span>
                  <input
                    type="checkbox"
                    checked={layers.spill}
                    onChange={() => toggleLayer('spill')}
                    className="rounded border-slate-700 text-cyan-500 focus:ring-0 bg-slate-800"
                  />
                </label>

                <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer select-none">
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full border border-white bg-red-500"></span>
                    Spill Centroid
                  </span>
                  <input
                    type="checkbox"
                    checked={layers.centroid}
                    onChange={() => toggleLayer('centroid')}
                    className="rounded border-slate-700 text-cyan-500 focus:ring-0 bg-slate-800"
                  />
                </label>

                <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer select-none">
                  <span className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                    Probable Origin
                  </span>
                  <input
                    type="checkbox"
                    checked={layers.origin}
                    onChange={() => toggleLayer('origin')}
                    className="rounded border-slate-700 text-cyan-500 focus:ring-0 bg-slate-800"
                  />
                </label>

                <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer select-none">
                  <span className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-orange-400"></span>
                    Drift Hindcasting
                  </span>
                  <input
                    type="checkbox"
                    checked={layers.drift}
                    onChange={() => toggleLayer('drift')}
                    className="rounded border-slate-700 text-cyan-500 focus:ring-0 bg-slate-800"
                  />
                </label>

                <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer select-none">
                  <span className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span>
                    AIS Vessel Tracks
                  </span>
                  <input
                    type="checkbox"
                    checked={layers.aisTracks}
                    onChange={() => toggleLayer('aisTracks')}
                    className="rounded border-slate-700 text-cyan-500 focus:ring-0 bg-slate-800"
                  />
                </label>

                <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer select-none">
                  <span className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-400"></span>
                    Candidate Vessels
                  </span>
                  <input
                    type="checkbox"
                    checked={layers.candidates}
                    onChange={() => toggleLayer('candidates')}
                    className="rounded border-slate-700 text-cyan-500 focus:ring-0 bg-slate-800"
                  />
                </label>

                <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer select-none">
                  <span className="flex items-center gap-2">
                    <span className="w-2.5 h-1 border-t border-dashed border-cyan-400"></span>
                    SAR Scene Bounds
                  </span>
                  <input
                    type="checkbox"
                    checked={layers.satellite}
                    onChange={() => toggleLayer('satellite')}
                    className="rounded border-slate-700 text-cyan-500 focus:ring-0 bg-slate-800"
                  />
                </label>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Map Legend Overlay (Bottom Right, above attribution) */}
      <div className="absolute bottom-9 right-3 z-10 p-2.5 rounded-lg bg-navy-900/90 border border-slate-800 shadow-xl backdrop-blur text-[11px] font-mono space-y-1.5 hidden md:block select-none pointer-events-none">
        <div className="text-slate-400 font-semibold text-[10px] uppercase tracking-wider mb-1">
          Symbology / GIS
        </div>
        <div className="flex items-center gap-2 text-slate-300">
          <span className="w-3 h-3 bg-red-600/70 border border-red-500 rounded-sm"></span>
          <span>Spill Slick (SAR Extent)</span>
        </div>
        <div className="flex items-center gap-2 text-slate-300">
          <span className="w-3 h-3 bg-amber-500/30 border border-dashed border-amber-400 rounded-sm"></span>
          <span>Origin Uncertainty Ellipse</span>
        </div>
        <div className="flex items-center gap-2 text-slate-300">
          <span className="w-3 h-1 bg-orange-400"></span>
          <span>Backward Hindcast Drift</span>
        </div>
        <div className="flex items-center gap-2 text-slate-300">
          <span className="w-3 h-1 bg-cyan-400"></span>
          <span>AIS Vessel Trajectory</span>
        </div>
        <div className="flex items-center gap-2 text-slate-300">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500 border border-white"></span>
          <span>HIGH Priority Candidate</span>
        </div>
      </div>
    </div>
  );
};
