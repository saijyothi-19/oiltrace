/**
 * OILTRACE GIS Map Configuration
 * Provides configurable basemap providers with OpenStreetMap as the default
 * zero-API-key solution for Smart India Hackathon 2026.
 */

export type BasemapProviderId = 'osm' | 'ocean' | 'carto';

export interface BasemapConfig {
  id: BasemapProviderId;
  name: string;
  description: string;
  tiles: string[];
  tileSize: number;
  maxzoom: number;
  attribution: string;
  requiresKey: boolean;
  hasKey: boolean;
}

/**
 * Resolves the active basemap configuration based on environment variables
 * and optional user selection. Always falls back gracefully to OpenStreetMap.
 */
export function getBasemapConfig(selectedProvider?: BasemapProviderId): BasemapConfig {
  const envProvider = (import.meta.env.VITE_MAP_PROVIDER || 'osm').toLowerCase();
  const cartoApiKey = import.meta.env.VITE_CARTO_API_KEY;
  const hasCartoKey = Boolean(cartoApiKey && cartoApiKey.trim() !== '');

  const providerToUse = selectedProvider || envProvider;

  // 1. CARTO Dark Matter (ONLY if valid API key is configured)
  if (providerToUse === 'carto') {
    if (hasCartoKey) {
      return {
        id: 'carto',
        name: 'CARTO Dark Matter',
        description: 'Dark cartographic basemap with authenticated API key',
        tiles: [
          `https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png?api_key=${cartoApiKey}`,
          `https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png?api_key=${cartoApiKey}`,
          `https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png?api_key=${cartoApiKey}`,
        ],
        tileSize: 256,
        maxzoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank" rel="noreferrer">CARTO</a>',
        requiresKey: true,
        hasKey: true,
      };
    } else {
      console.warn(
        '[OILTRACE GIS] CARTO requested but VITE_CARTO_API_KEY is not configured. ' +
        'Automatically falling back to OpenStreetMap (no API key required) to prevent "API KEY REQUIRED" watermark.'
      );
    }
  }

  // 2. World Ocean Bathymetry (Public marine service, no API key required)
  if (providerToUse === 'ocean') {
    return {
      id: 'ocean',
      name: 'Ocean Bathymetry',
      description: 'Marine depth contours and seafloor bathymetry',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      maxzoom: 16,
      attribution: 'Esri, GEBCO, NOAA, National Geographic, DeLorme, HERE, Geonames.org, and other contributors',
      requiresKey: false,
      hasKey: true,
    };
  }

  // 3. OpenStreetMap (Standard default, completely free, no API key required)
  return {
    id: 'osm',
    name: 'OpenStreetMap',
    description: 'Global standard geographic basemap (No API key required)',
    tiles: [
      'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    ],
    tileSize: 256,
    maxzoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors',
    requiresKey: false,
    hasKey: true,
  };
}

/**
 * Returns available basemap options for UI switcher.
 */
export function getAvailableBasemaps(): BasemapConfig[] {
  const cartoApiKey = import.meta.env.VITE_CARTO_API_KEY;
  const hasCartoKey = Boolean(cartoApiKey && cartoApiKey.trim() !== '');

  const basemaps: BasemapConfig[] = [
    getBasemapConfig('osm'),
    getBasemapConfig('ocean'),
  ];

  if (hasCartoKey) {
    basemaps.push(getBasemapConfig('carto'));
  }

  return basemaps;
}
