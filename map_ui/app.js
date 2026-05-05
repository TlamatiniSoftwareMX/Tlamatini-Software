const state = {
  map: null,
  config: null,
  currentMapId: "",
  lastUpdatedAt: "",
  protocolRegistered: false,
  baseLayerGroups: {},
  overlayLayerGroups: {},
  popup: null,
  persistTimer: null,
  measurePoints: [],
  boundOverlayHandlers: new Set(),
  drawMode: null,
  emojiMarkers: [],
  selectedFeature: null,
  telemetry: {
    altitude: null,
    heading: null,
    speed: null,
    gpsStatus: "No disponible",
  },
  satellite: {
    availability: null,
    task: null,
  },
  satelliteWarningShown: false,
};

const THEMES = {
  standard: {
    background: "#dce7f4",
    ocean: "#93bddc",
    water: "#82b6d9",
    land: "#eef3e5",
    parks: "#d7ebcb",
    roadsMinor: "#f8fafc",
    roadsMajor: "#d7b38c",
    bridges: "#f59e0b",
    buildings: "#d7cab8",
    boundaries: "#7c8aa0",
    labels: "#0f172a",
    labelsHalo: "#f8fafc",
  },
  dark: {
    background: "#08111d",
    ocean: "#0f2740",
    water: "#123a63",
    land: "#101b2a",
    parks: "#103224",
    roadsMinor: "#4b5563",
    roadsMajor: "#f59e0b",
    bridges: "#f97316",
    buildings: "#293548",
    boundaries: "#7dd3fc",
    labels: "#e2e8f0",
    labelsHalo: "#0b1220",
  },
  tactical: {
    background: "#10150f",
    ocean: "#14263c",
    water: "#1e4a64",
    land: "#1d2a1d",
    parks: "#375d30",
    roadsMinor: "#7c6f48",
    roadsMajor: "#facc15",
    bridges: "#f97316",
    buildings: "#475569",
    boundaries: "#ef4444",
    labels: "#f8fafc",
    labelsHalo: "#17201a",
  },
  paper: {
    background: "#f3ecd9",
    ocean: "#b7d1d6",
    water: "#8bb8c4",
    land: "#f7f1e2",
    parks: "#ccd8aa",
    roadsMinor: "#d8cdb8",
    roadsMajor: "#9f7b57",
    bridges: "#b45309",
    buildings: "#c5b59f",
    boundaries: "#8b5e3c",
    labels: "#2b2118",
    labelsHalo: "#fffaf0",
  },
  desert: {
    background: "#261c12",
    ocean: "#354f68",
    water: "#5b8aa8",
    land: "#c8a46a",
    parks: "#8fa36a",
    roadsMinor: "#e3c48a",
    roadsMajor: "#fff0b3",
    bridges: "#fb923c",
    buildings: "#8f6b4a",
    boundaries: "#7f1d1d",
    labels: "#fff7ed",
    labelsHalo: "#3b2a1b",
  },
  nightwatch: {
    background: "#05070d",
    ocean: "#0b1d33",
    water: "#11436d",
    land: "#0d1522",
    parks: "#0d3a2f",
    roadsMinor: "#334155",
    roadsMajor: "#22d3ee",
    bridges: "#f59e0b",
    buildings: "#1f2937",
    boundaries: "#f43f5e",
    labels: "#e0f2fe",
    labelsHalo: "#020617",
  },
  high_contrast: {
    background: "#000000",
    ocean: "#001a33",
    water: "#00b7ff",
    land: "#111111",
    parks: "#1f7a1f",
    roadsMinor: "#888888",
    roadsMajor: "#ffff00",
    bridges: "#ff7a00",
    buildings: "#ffffff",
    boundaries: "#ff0033",
    labels: "#ffffff",
    labelsHalo: "#000000",
  },
};

const OVERLAY_STYLE = {
  puntos: { color: "#ef4444", label: "Puntos guardados" },
  rutas: { color: "#22c55e", label: "Rutas" },
  poligonos: { color: "#f97316", label: "Zonas de riesgo" },
  refugios: { color: "#38bdf8", label: "Refugios" },
  recursos: { color: "#eab308", label: "Recursos" },
  nodos: { color: "#8b5cf6", label: "Nodos" },
  sensores: { color: "#06b6d4", label: "Sensores" },
  comunicaciones: { color: "#facc15", label: "Comunicaciones" },
  observacion: { color: "#fb7185", label: "Observación" },
  control: { color: "#a78bfa", label: "Control y checkpoints" },
  rutas_evacuacion: { color: "#22c55e", label: "Rutas de evacuación" },
  rutas_logisticas: { color: "#f59e0b", label: "Rutas logísticas" },
  rutas_patrullaje: { color: "#60a5fa", label: "Rutas de patrullaje" },
  zonas_seguras: { color: "#10b981", label: "Zonas seguras" },
  perimetros: { color: "#f97316", label: "Perímetros" },
  amenazas: { color: "#ef4444", label: "Amenazas" },
  imported: { color: "#f472b6", label: "GeoJSON importado" },
};

const mapNameEl = document.getElementById("mapName");
const mapMetaEl = document.getElementById("mapMeta");
const viewerModeEl = document.getElementById("viewerMode");
const statusEl = document.getElementById("status");
const featureInfoEl = document.getElementById("featureInfo");
const featureActionsEl = document.getElementById("featureActions");
const featureEditBtnEl = document.getElementById("featureEditBtn");
const featureDeleteBtnEl = document.getElementById("featureDeleteBtn");
const viewerInfoEl = document.getElementById("viewerInfo");
const emptyStateEl = document.getElementById("emptyState");
const styleSelectEl = document.getElementById("styleSelect");
const mapBaseListEl = document.getElementById("mapBaseList");
const baseLayersListEl = document.getElementById("baseLayersList");
const overlayLayersListEl = document.getElementById("overlayLayersList");
const coordCursorEl = document.getElementById("coordCursor");
const coordCenterEl = document.getElementById("coordCenter");
const measureInfoEl = document.getElementById("measureInfo");
const telemetryPanelEl = document.getElementById("telemetryPanel");
const telemetryContentEl = document.getElementById("telemetryContent");
const recenterBtn = document.getElementById("recenterBtn");
const measureToggleBtn = document.getElementById("measureToggleBtn");
const clearMeasureBtn = document.getElementById("clearMeasureBtn");
const refreshBtn = document.getElementById("refreshBtn");
const telemetryToggleBtn = document.getElementById("telemetryToggleBtn");
const downloadSatelliteBtn = document.getElementById("downloadSatelliteBtn");
const cancelSatelliteBtn = document.getElementById("cancelSatelliteBtn");
const satelliteStatusEl = document.getElementById("satelliteStatus");
const contextMenuEl = document.getElementById("contextMenu");
const featureModalEl = document.getElementById("featureModal");
const modalTitleEl = document.getElementById("modalTitle");
const modalCloseBtn = document.getElementById("modalCloseBtn");
const featureFormEl = document.getElementById("featureForm");
const deleteBtnEl = document.getElementById("deleteBtn");
const fieldNombreEl = document.getElementById("fieldNombre");
const fieldCategoriaEl = document.getElementById("fieldCategoria");
const fieldRiesgoEl = document.getElementById("fieldRiesgo");
const fieldLayerIdEl = document.getElementById("fieldLayerId");
const fieldLatitudEl = document.getElementById("fieldLatitud");
const fieldLongitudEl = document.getElementById("fieldLongitud");
const fieldDescripcionEl = document.getElementById("fieldDescripcion");
const fieldCoordinatesEl = document.getElementById("fieldCoordinates");
const coordsFieldWrapEl = document.getElementById("coordsFieldWrap");
const latitudFieldWrapEl = fieldLatitudEl.closest("label");
const longitudFieldWrapEl = fieldLongitudEl.closest("label");
const fieldCategoriaWrapEl = document.getElementById("fieldCategoriaWrap");
const fieldLayerWrapEl = document.getElementById("fieldLayerWrap");
const emojiFieldWrapEl = document.getElementById("emojiFieldWrap");
const emojiPickerBtnEl = document.getElementById("emojiPickerBtn");
const emojiModalEl = document.getElementById("emojiModal");
const emojiModalCloseBtnEl = document.getElementById("emojiModalCloseBtn");
const emojiPickerGridEl = document.getElementById("emojiPickerGrid");
const categoryAddBtn = document.getElementById("categoryAddBtn");
const categoryEditBtn = document.getElementById("categoryEditBtn");
const categoryDeleteBtn = document.getElementById("categoryDeleteBtn");
const layerAddBtn = document.getElementById("layerAddBtn");
const layerEditBtn = document.getElementById("layerEditBtn");
const layerDeleteBtn = document.getElementById("layerDeleteBtn");
const collapseToggleEls = Array.from(document.querySelectorAll(".collapse-toggle"));

const MAP_BASE_OPTIONS = [
  { id: "mapa", label: "Mapa actual", meta: "Mapa vectorial offline de TLAMATINI" },
  { id: "satellite", label: "Satélite", meta: "Imagen aérea como base cuando haya conexión" },
];

const EXTRA_OVERLAY_OPTIONS = [
  { id: "curvas_nivel", label: "Curvas de nivel", meta: "Overlay de relieve sobre el mapa base" },
  { id: "areas_verdes", label: "Áreas verdes", meta: "Cobertura verde semitransparente" },
  { id: "areas_urbanas", label: "Áreas urbanas", meta: "Cobertura urbana semitransparente" },
  { id: "telemetry_panel", label: "Mostrar telemetría", meta: "Panel flotante inferior derecho" },
];

const SATELLITE_DOWNLOAD_EXTRA_ZOOMS = 2;
const SATELLITE_DOWNLOAD_MAX_ZOOM = 18;

const IDENTIFIER_EMOJIS = [
  { emoji: "🏠", label: "Casa" },
  { emoji: "🏘️", label: "Vecindario" },
  { emoji: "⛽", label: "Gasolinera" },
  { emoji: "🏪", label: "Tienda" },
  { emoji: "🏬", label: "Comercio" },
  { emoji: "🚗", label: "Carro" },
  { emoji: "🚚", label: "Camión" },
  { emoji: "🚌", label: "Transporte" },
  { emoji: "🍔", label: "Comida" },
  { emoji: "🌮", label: "Puesto" },
  { emoji: "🍞", label: "Pan" },
  { emoji: "💧", label: "Agua" },
  { emoji: "🛠️", label: "Herramientas" },
  { emoji: "🔧", label: "Taller" },
  { emoji: "⚙️", label: "Equipo" },
  { emoji: "💀", label: "Craneo" },
  { emoji: "🦴", label: "Hueso" },
  { emoji: "⚠️", label: "Peligro" },
  { emoji: "☢️", label: "Riesgo" },
  { emoji: "🔥", label: "Fuego" },
  { emoji: "🚧", label: "Bloqueo" },
  { emoji: "🧯", label: "Extintor" },
  { emoji: "🏥", label: "Hospital" },
  { emoji: "⛑️", label: "Emergencia" },
  { emoji: "🚑", label: "Ambulancia" },
  { emoji: "🚓", label: "Patrulla" },
  { emoji: "🏫", label: "Escuela" },
  { emoji: "🏢", label: "Edificio" },
  { emoji: "🌉", label: "Puente" },
  { emoji: "🌲", label: "Bosque" },
  { emoji: "⛺", label: "Campamento" },
  { emoji: "📡", label: "Antena" },
];

const CATEGORY_OPTIONS = {
  point: [
    { value: "refugio", label: "Refugio" },
    { value: "recurso", label: "Recurso" },
    { value: "zona_riesgo", label: "Zona de riesgo" },
    { value: "nodo", label: "Nodo" },
    { value: "sensor", label: "Sensor" },
    { value: "punto_interes", label: "Punto de interés" },
    { value: "comunicaciones", label: "Comunicaciones" },
    { value: "observacion", label: "Observación" },
    { value: "checkpoint", label: "Checkpoint" },
  ],
  route: [
    { value: "ruta", label: "Ruta" },
    { value: "evacuacion", label: "Evacuación" },
    { value: "abastecimiento", label: "Abastecimiento" },
    { value: "patrullaje", label: "Patrullaje" },
    { value: "escape", label: "Escape" },
    { value: "enlace", label: "Enlace" },
  ],
  polygon: [
    { value: "zona_riesgo", label: "Zona de riesgo" },
    { value: "perimetro", label: "Perímetro" },
    { value: "operacion", label: "Operación" },
    { value: "zona_segura", label: "Zona segura" },
    { value: "amenaza", label: "Amenaza" },
    { value: "resguardo", label: "Resguardo" },
  ],
};

function normalizeCategoryValue(text) {
  return String(text || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function categoryOptionsForKind(kind) {
  const defaults = CATEGORY_OPTIONS[kind] || [];
  const custom = state.config?.preferences?.category_options?.[kind] || [];
  const hidden = new Set((state.config?.preferences?.category_hidden?.[kind] || []).map((item) => String(item || "").trim()));
  const merged = [];
  const seen = new Set();
  for (const option of [...defaults, ...custom]) {
    const normalized = typeof option === "string"
      ? { value: normalizeCategoryValue(option), label: String(option).trim() }
      : { value: String(option?.value || "").trim(), label: String(option?.label || "").trim() };
    if (!normalized.value || !normalized.label || hidden.has(normalized.value) || seen.has(normalized.value)) {
      continue;
    }
    seen.add(normalized.value);
    merged.push(normalized);
  }
  return merged;
}

async function saveCategoryOptions(kind, options) {
  if (!state.config?.preferences) {
    return;
  }
  state.config.preferences.category_options = {
    ...(state.config.preferences.category_options || {}),
    [kind]: options,
  };
  await postJson("/runtime/preferences", {
    category_options: {
      [kind]: options,
    },
  });
}

async function saveHiddenCategories(kind, values) {
  if (!state.config?.preferences) {
    return;
  }
  state.config.preferences.category_hidden = {
    ...(state.config.preferences.category_hidden || {}),
    [kind]: values,
  };
  await postJson("/runtime/preferences", {
    category_hidden: {
      [kind]: values,
    },
  });
}

function refreshCategorySelect(selected) {
  const kind = state.formState?.kind;
  if (!kind) {
    return;
  }
  populateSelect(fieldCategoriaEl, categoryOptionsForKind(kind), selected || fieldCategoriaEl.value);
}

const LAYER_OPTIONS = {
  point: [
    { value: "puntos", label: "Puntos guardados" },
    { value: "refugios", label: "Refugios" },
    { value: "recursos", label: "Recursos" },
    { value: "nodos", label: "Nodos" },
    { value: "sensores", label: "Sensores" },
    { value: "comunicaciones", label: "Comunicaciones" },
    { value: "observacion", label: "Observación" },
    { value: "control", label: "Control y checkpoints" },
  ],
  route: [
    { value: "rutas", label: "Rutas" },
    { value: "rutas_evacuacion", label: "Rutas de evacuación" },
    { value: "rutas_logisticas", label: "Rutas logísticas" },
    { value: "rutas_patrullaje", label: "Rutas de patrullaje" },
  ],
  polygon: [
    { value: "poligonos", label: "Zonas de riesgo" },
    { value: "zonas_seguras", label: "Zonas seguras" },
    { value: "perimetros", label: "Perímetros" },
    { value: "amenazas", label: "Amenazas" },
  ],
};

function geometryForKind(kind) {
  if (kind === "point") return ["Point"];
  if (kind === "route") return ["LineString", "MultiLineString"];
  return ["Polygon", "MultiPolygon"];
}

function colorForKind(kind) {
  if (kind === "point") return "#ef4444";
  if (kind === "route") return "#22c55e";
  return "#f97316";
}

function layerOptionsForKind(kind) {
  const defaults = LAYER_OPTIONS[kind] || [];
  const custom = (state.config?.preferences?.custom_layers || [])
    .filter((item) => Array.isArray(item?.geometry) && item.geometry.some((value) => geometryForKind(kind).includes(value)))
    .map((item) => ({ value: String(item.id || "").trim(), label: String(item.label || "").trim() }));
  const hidden = new Set((state.config?.preferences?.layer_hidden?.[kind] || []).map((item) => String(item || "").trim()));
  const labels = state.config?.preferences?.layer_option_labels || {};
  const merged = [];
  const seen = new Set();
  for (const option of [...defaults, ...custom]) {
    const normalized = typeof option === "string"
      ? { value: option, label: option }
      : { value: String(option?.value || "").trim(), label: String(option?.label || "").trim() };
    if (!normalized.value || hidden.has(normalized.value) || seen.has(normalized.value)) {
      continue;
    }
    seen.add(normalized.value);
    merged.push({ value: normalized.value, label: String(labels[normalized.value] || normalized.label || normalized.value).trim() });
  }
  return merged;
}

function refreshLayerSelect(selected) {
  const kind = state.formState?.kind;
  if (!kind) {
    return;
  }
  populateSelect(fieldLayerIdEl, layerOptionsForKind(kind), selected || fieldLayerIdEl.value);
}

async function saveCustomLayers(layers) {
  if (!state.config?.preferences) {
    return;
  }
  state.config.preferences.custom_layers = layers;
  await postJson("/runtime/preferences", { custom_layers: layers });
}

async function saveLayerLabels(labels) {
  if (!state.config?.preferences) {
    return;
  }
  state.config.preferences.layer_option_labels = {
    ...(state.config.preferences.layer_option_labels || {}),
    ...labels,
  };
  await postJson("/runtime/preferences", { layer_option_labels: labels });
}

async function saveHiddenLayers(kind, values) {
  if (!state.config?.preferences) {
    return;
  }
  state.config.preferences.layer_hidden = {
    ...(state.config.preferences.layer_hidden || {}),
    [kind]: values,
  };
  await postJson("/runtime/preferences", {
    layer_hidden: {
      [kind]: values,
    },
  });
}

state.contextTarget = null;
state.formState = null;

function cacheBust(url) {
  return `${url}${url.includes("?") ? "&" : "?"}t=${Date.now()}`;
}

async function fetchJson(url) {
  const response = await fetch(cacheBust(url), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`No se pudo cargar ${url}`);
  }
  return await response.json();
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `No se pudo completar ${url}`);
  }
  return data;
}

function ensureProtocol() {
  if (state.protocolRegistered) {
    return;
  }
  const protocol = new pmtiles.Protocol();
  maplibregl.addProtocol("pmtiles", protocol.tile);
  state.protocolRegistered = true;
}

const SHORTBREAD_FALLBACK_LAYERS = [
  "ocean",
  "land",
  "water_polygons",
  "water_lines",
  "water_lines_labels",
  "sites",
  "landcover",
  "landuse",
  "landuse_polygons",
  "boundaries",
  "street_polygons",
  "streets",
  "bridges",
  "railways",
  "rail",
  "rail_lines",
  "aeroways",
  "runways",
  "airports",
  "buildings",
  "contours",
  "terrain",
  "hillshade",
  "place_labels",
  "street_labels",
  "boundary_labels",
];

function availableSourceLayers(config) {
  const vectorLayers = (((config || {}).mapa || {}).pmtilesMetadata || {}).vector_layers || [];
  if (Array.isArray(vectorLayers) && vectorLayers.length) {
    return new Set(vectorLayers.map((item) => item.id).filter(Boolean));
  }
  const schema = String((((config || {}).mapa || {}).schema || "")).toLowerCase();
  if (schema === "shortbread") {
    return new Set(SHORTBREAD_FALLBACK_LAYERS);
  }
  return new Set();
}

function layerExists(available, name) {
  return available.has(name);
}

function glyphsUrl(config) {
  return `${config.viewer_url}fonts/{fontstack}/{range}.pbf`;
}

function buildLabelLayer(id, sourceLayer, color, haloColor, minzoom = 10, textSize = 12) {
  return {
    id,
    type: "symbol",
    source: "basemap",
    "source-layer": sourceLayer,
    minzoom,
    layout: {
      "text-field": ["coalesce", ["get", "name"], ["get", "name_en"], ["get", "name_de"]],
      "text-font": ["Noto Sans Regular"],
      "text-size": textSize,
      "symbol-placement": sourceLayer.includes("street") || sourceLayer.includes("water_lines") ? "line" : "point",
    },
    paint: {
      "text-color": color,
      "text-halo-color": haloColor,
      "text-halo-width": 1.4,
    },
  };
}

function hasVectorLayerMetadata(config) {
  const vectorLayers = (((config || {}).mapa || {}).pmtilesMetadata || {}).vector_layers || [];
  return Array.isArray(vectorLayers) && vectorLayers.length > 0;
}

function overlaySource(config, layerId) {
  return {
    type: "geojson",
    data: cacheBust(config.capas[layerId].url),
  };
}

function classifyPropertyExpression() {
  return [
    "downcase",
    [
      "to-string",
      ["coalesce", ["get", "class"], ["get", "kind"], ["get", "type"], ["get", "landuse"], ["get", "category"], ""],
    ],
  ];
}

function greenAreaFilter() {
  return [
    "in",
    classifyPropertyExpression(),
    [
      "literal",
      [
        "park",
        "forest",
        "wood",
        "grass",
        "grassland",
        "meadow",
        "scrub",
        "farmland",
        "farm",
        "orchard",
        "vineyard",
        "cemetery",
        "village_green",
        "nature_reserve",
        "recreation_ground",
        "allotments",
        "garden",
      ],
    ],
  ];
}

function urbanAreaFilter() {
  return [
    "in",
    classifyPropertyExpression(),
    [
      "literal",
      [
        "residential",
        "commercial",
        "industrial",
        "retail",
        "construction",
        "brownfield",
        "garages",
        "military",
        "port",
        "quarry",
        "education",
        "hospital",
        "railway",
      ],
    ],
  ];
}

function buildStyle(config) {
  const prefs = config.preferences || {};
  const themeId = prefs.style_id || "standard";
  const theme = THEMES[themeId] || THEMES.standard;
  const available = availableSourceLayers(config);
  const mapData = config.mapa;
  const layers = [
    {
      id: "background",
      type: "background",
      paint: { "background-color": theme.background },
    },
    {
      id: "base-satellite",
      type: "raster",
      source: "satellite",
      layout: { visibility: prefs.map_base === "satellite" ? "visible" : "none" },
      paint: { "raster-opacity": 1 },
    },
  ];

  const add = (layer) => layers.push(layer);
  const ifLayer = (name, builder) => {
    if (layerExists(available, name)) {
      add(builder(name));
    }
  };
  const ifAnyLayer = (names, builder) => {
    for (const name of names) {
      if (layerExists(available, name)) {
        add(builder(name));
        return;
      }
    }
  };

  ifLayer("ocean", (name) => ({
    id: "base-ocean",
    type: "fill",
    source: "basemap",
    "source-layer": name,
    paint: { "fill-color": theme.ocean },
  }));
  ifLayer("land", (name) => ({
    id: "base-land",
    type: "fill",
    source: "basemap",
    "source-layer": name,
    paint: { "fill-color": theme.land },
  }));
  ifLayer("water_polygons", (name) => ({
    id: "base-water-polygons",
    type: "fill",
    source: "basemap",
    "source-layer": name,
    paint: { "fill-color": theme.water },
  }));
  ifLayer("water_lines", (name) => ({
    id: "base-water-lines",
    type: "line",
    source: "basemap",
    "source-layer": name,
    paint: { "line-color": theme.water, "line-width": 1.3 },
  }));
  ifLayer("sites", (name) => ({
    id: "base-sites",
    type: "fill",
    source: "basemap",
    "source-layer": name,
    paint: { "fill-color": theme.parks, "fill-opacity": 0.7 },
  }));
  ifAnyLayer(["landcover", "landuse", "landuse_polygons"], (name) => ({
    id: "base-landuse",
    type: "fill",
    source: "basemap",
    "source-layer": name,
    paint: { "fill-color": theme.parks, "fill-opacity": 0.3 },
  }));
  ifLayer("boundaries", (name) => ({
    id: "base-boundaries",
    type: "line",
    source: "basemap",
    "source-layer": name,
    paint: { "line-color": theme.boundaries, "line-width": 1.1, "line-opacity": 0.75 },
  }));
  ifLayer("street_polygons", (name) => ({
    id: "base-street-polygons",
    type: "fill",
    source: "basemap",
    "source-layer": name,
    paint: { "fill-color": theme.roadsMinor, "fill-opacity": 0.95 },
  }));
  ifLayer("streets", (name) => ({
    id: "base-streets",
    type: "line",
    source: "basemap",
    "source-layer": name,
    paint: {
      "line-color": theme.roadsMajor,
      "line-width": ["interpolate", ["linear"], ["zoom"], 10, 0.8, 12, 1.8, 14, 3.2],
    },
  }));
  ifLayer("bridges", (name) => ({
    id: "base-bridges",
    type: "line",
    source: "basemap",
    "source-layer": name,
    paint: { "line-color": theme.bridges, "line-width": ["interpolate", ["linear"], ["zoom"], 12, 1.2, 14, 3.6] },
  }));
  ifAnyLayer(["railways", "rail", "rail_lines"], (name) => ({
    id: "base-railways",
    type: "line",
    source: "basemap",
    "source-layer": name,
    paint: { "line-color": theme.boundaries, "line-width": ["interpolate", ["linear"], ["zoom"], 10, 0.7, 13, 2.1], "line-dasharray": [1.5, 1.2] },
  }));
  ifAnyLayer(["aeroways", "runways", "airports"], (name) => ({
    id: "base-air",
    type: "line",
    source: "basemap",
    "source-layer": name,
    paint: { "line-color": theme.bridges, "line-width": ["interpolate", ["linear"], ["zoom"], 9, 0.8, 13, 2.8], "line-opacity": 0.9 },
  }));
  ifLayer("buildings", (name) => ({
    id: "base-buildings",
    type: "fill",
    source: "basemap",
    "source-layer": name,
    paint: { "fill-color": theme.buildings, "fill-opacity": ["interpolate", ["linear"], ["zoom"], 12, 0.15, 14, 0.65] },
  }));
  ifAnyLayer(["contours", "terrain", "hillshade"], (name) => ({
    id: "base-terrain",
    type: "line",
    source: "basemap",
    "source-layer": name,
    paint: { "line-color": theme.labels, "line-width": 0.7, "line-opacity": 0.22 },
  }));

  if (hasVectorLayerMetadata(config) || String(mapData.schema || "").toLowerCase() === "shortbread") {
    ifLayer("place_labels", (name) => buildLabelLayer("base-place-labels", name, theme.labels, theme.labelsHalo, 7, 12));
    ifLayer("street_labels", (name) => buildLabelLayer("base-street-labels", name, theme.labels, theme.labelsHalo, 10, 11));
    ifLayer("boundary_labels", (name) => buildLabelLayer("base-boundary-labels", name, theme.labels, theme.labelsHalo, 4, 11));
    ifLayer("water_lines_labels", (name) => buildLabelLayer("base-water-labels", name, theme.labels, theme.labelsHalo, 10, 11));
  }

  for (const layerId of Object.keys(config.capas || {})) {
    const style = OVERLAY_STYLE[layerId] || { color: "#f43f5e", label: layerId };
    add({
      id: `ov-${layerId}-fill`,
      type: "fill",
      source: layerId,
      filter: ["in", ["geometry-type"], ["literal", ["Polygon", "MultiPolygon"]]],
      paint: {
        "fill-color": ["coalesce", ["get", "color"], style.color],
        "fill-opacity": 0.18,
      },
    });
    add({
      id: `ov-${layerId}-line`,
      type: "line",
      source: layerId,
      filter: ["in", ["geometry-type"], ["literal", ["LineString", "MultiLineString", "Polygon", "MultiPolygon"]]],
      paint: {
        "line-color": ["coalesce", ["get", "color"], style.color],
        "line-width": ["case", ["in", ["geometry-type"], ["literal", ["LineString", "MultiLineString"]]], 3, 2],
      },
    });
    add({
      id: `ov-${layerId}-circle`,
      type: "circle",
      source: layerId,
      filter: ["all", ["==", ["geometry-type"], "Point"], ["==", ["coalesce", ["get", "emoji"], ""], ""]],
      paint: {
        "circle-radius": ["case", ["==", layerId, "sensores"], 5, ["==", layerId, "nodos"], 7, 6],
        "circle-color": ["coalesce", ["get", "color"], style.color],
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1.2,
      },
    });
    add({
      id: `ov-${layerId}-emoji`,
      type: "symbol",
      source: layerId,
      filter: ["all", ["==", ["geometry-type"], "Point"], ["!=", ["coalesce", ["get", "emoji"], ""], ""]],
      layout: {
        "text-field": ["get", "emoji"],
        "text-size": 20,
        "text-allow-overlap": true,
        "text-ignore-placement": true,
      },
      paint: {
        "text-color": "#ffffff",
        "text-halo-color": ["coalesce", ["get", "color"], style.color],
        "text-halo-width": 1.8,
      },
    });
  }

  ifAnyLayer(["contours", "terrain", "hillshade"], (name) => ({
    id: "ov-curvas-nivel",
    type: "line",
    source: "basemap",
    "source-layer": name,
    paint: {
      "line-color": "#f8fafc",
      "line-width": 0.9,
      "line-opacity": 0.55,
    },
  }));

  ifLayer("sites", (name) => ({
    id: "ov-areas-verdes-sites",
    type: "fill",
    source: "basemap",
    "source-layer": name,
    paint: {
      "fill-color": "#22c55e",
      "fill-opacity": 0.22,
    },
  }));
  ifAnyLayer(["landcover", "landuse", "landuse_polygons"], (name) => ({
    id: "ov-areas-verdes-landuse",
    type: "fill",
    source: "basemap",
    "source-layer": name,
    filter: greenAreaFilter(),
    paint: {
      "fill-color": "#22c55e",
      "fill-opacity": 0.2,
    },
  }));
  ifAnyLayer(["landuse", "landuse_polygons"], (name) => ({
    id: "ov-areas-urbanas-landuse",
    type: "fill",
    source: "basemap",
    "source-layer": name,
    filter: urbanAreaFilter(),
    paint: {
      "fill-color": "#d6b38a",
      "fill-opacity": 0.18,
    },
  }));
  ifLayer("buildings", (name) => ({
    id: "ov-areas-urbanas-buildings",
    type: "fill",
    source: "basemap",
    "source-layer": name,
    paint: {
      "fill-color": "#a8a29e",
      "fill-opacity": ["interpolate", ["linear"], ["zoom"], 11, 0.06, 14, 0.26],
    },
  }));

  return {
    version: 8,
    glyphs: glyphsUrl(config),
    sources: {
      satellite: {
        type: "raster",
        tiles: [
          `${config.viewer_url}runtime/satellite_tile/{z}/{x}/{y}.jpg`,
        ],
        tileSize: 256,
        attribution: "Satélite configurable",
      },
      basemap: {
        type: "vector",
        url: `pmtiles://${mapData.pmtilesUrl}`,
      },
      ...Object.fromEntries(Object.keys(config.capas || {}).map((layerId) => [layerId, overlaySource(config, layerId)])),
      measure: {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      },
      sketch: {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      },
    },
    layers: [
      ...layers,
      {
        id: "measure-line",
        type: "line",
        source: "measure",
        filter: ["in", ["geometry-type"], ["literal", ["LineString", "MultiLineString"]]],
        paint: { "line-color": "#f43f5e", "line-width": 3, "line-dasharray": [2, 1] },
      },
      {
        id: "measure-points",
        type: "circle",
        source: "measure",
        filter: ["==", ["geometry-type"], "Point"],
        paint: { "circle-radius": 5, "circle-color": "#f43f5e", "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.2 },
      },
      {
        id: "sketch-fill",
        type: "fill",
        source: "sketch",
        filter: ["in", ["geometry-type"], ["literal", ["Polygon", "MultiPolygon"]]],
        paint: { "fill-color": "#38bdf8", "fill-opacity": 0.16 },
      },
      {
        id: "sketch-line",
        type: "line",
        source: "sketch",
        filter: ["in", ["geometry-type"], ["literal", ["LineString", "Polygon", "MultiPolygon"]]],
        paint: { "line-color": "#38bdf8", "line-width": 3, "line-dasharray": [1.2, 1.1] },
      },
      {
        id: "sketch-points",
        type: "circle",
        source: "sketch",
        filter: ["==", ["geometry-type"], "Point"],
        paint: { "circle-radius": 5, "circle-color": "#38bdf8", "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.2 },
      },
    ],
  };
}

function baseLayerGroups(available) {
  return {
    land: ["base-land"],
    satellite: ["base-satellite"],
    water: ["base-ocean", "base-water-polygons", "base-water-lines"],
    roads: ["base-street-polygons", "base-streets", "base-bridges"],
    rails: ["base-railways"],
    air: ["base-air"],
    buildings: ["base-buildings"],
    parks: ["base-sites"],
    terrain: ["base-terrain"],
    landuse: ["base-landuse"],
    boundaries: ["base-boundaries"],
    labels: ["base-place-labels", "base-street-labels", "base-boundary-labels", "base-water-labels"],
    place_labels: ["base-place-labels", "base-street-labels"],
    water_labels: ["base-water-labels"],
    boundary_labels: ["base-boundary-labels"],
  };
}

function overlayLayerGroups(config) {
  const groups = {};
  for (const layerId of Object.keys(config.capas || {})) {
    groups[layerId] = [`ov-${layerId}-fill`, `ov-${layerId}-line`, `ov-${layerId}-circle`, `ov-${layerId}-emoji`];
  }
  groups.curvas_nivel = ["ov-curvas-nivel"];
  groups.areas_verdes = ["ov-areas-verdes-sites", "ov-areas-verdes-landuse"];
  groups.areas_urbanas = ["ov-areas-urbanas-landuse", "ov-areas-urbanas-buildings"];
  groups.telemetry_panel = [];
  return groups;
}

function setLayerGroupVisibility(group, visible) {
  if (!state.map) {
    return;
  }
  for (const layerId of group) {
    if (state.map.getLayer(layerId)) {
      state.map.setLayoutProperty(layerId, "visibility", visible ? "visible" : "none");
    }
  }
}

function applyVisibilityFromPreferences() {
  const prefs = state.config.preferences || {};
  for (const [key, group] of Object.entries(state.baseLayerGroups)) {
    const visible = key === "satellite"
      ? prefs.map_base === "satellite"
      : baseLayerVisibleForCurrentMapBase(key, prefs);
    setLayerGroupVisibility(group, visible);
  }
  for (const [key, group] of Object.entries(state.overlayLayerGroups)) {
    setLayerGroupVisibility(group, prefs.overlay_layers?.[key] !== false);
  }
  updateTelemetryPanelVisibility();
  updateTelemetryPanel();
}

function currentMapBaseLabel() {
  return state.config?.preferences?.map_base === "satellite" ? "Satélite" : "Mapa";
}

function baseLayerVisibleForCurrentMapBase(key, prefs) {
  const activeBase = prefs.map_base || "mapa";
  if (activeBase !== "satellite") {
    return prefs.base_layers?.[key] !== false;
  }
  const satelliteCompatible = new Set(["roads", "rails", "air", "boundaries", "labels", "place_labels", "water_labels", "boundary_labels"]);
  return satelliteCompatible.has(key) && prefs.base_layers?.[key] !== false;
}

function updateTelemetryPanelVisibility() {
  const visible = !!state.config?.preferences?.telemetry_visible;
  telemetryPanelEl.classList.toggle("hidden", !visible);
  if (telemetryToggleBtn) {
    telemetryToggleBtn.classList.toggle("active", visible);
    telemetryToggleBtn.textContent = visible ? "Ocultar telemetría" : "Mostrar telemetría";
  }
}

function formatTelemetryValue(value, suffix = "") {
  if (value === null || value === undefined || value === "" || Number.isNaN(value)) {
    return "N/D";
  }
  return `${value}${suffix}`;
}

function updateTelemetryPanel() {
  if (!telemetryContentEl) {
    return;
  }
  const center = state.map ? state.map.getCenter() : null;
  const zoom = state.map ? state.map.getZoom().toFixed(2) : "N/D";
  const altitude = state.telemetry.altitude === null ? "N/D" : `${Number(state.telemetry.altitude).toFixed(1)} m`;
  const heading = state.telemetry.heading === null ? "N/D" : `${Number(state.telemetry.heading).toFixed(0)}°`;
  const speed = state.telemetry.speed === null ? "N/D" : `${(Number(state.telemetry.speed) * 3.6).toFixed(1)} km/h`;
  const connection = typeof navigator.onLine === "boolean" ? (navigator.onLine ? "En línea" : "Sin conexión") : "N/D";
  telemetryContentEl.innerHTML = `
    <div>Latitud: ${center ? center.lat.toFixed(5) : "N/D"}</div>
    <div>Longitud: ${center ? center.lng.toFixed(5) : "N/D"}</div>
    <div>Altitud: ${altitude}</div>
    <div>Rumbo: ${heading}</div>
    <div>Velocidad: ${speed}</div>
    <div>Zoom: ${zoom}</div>
    <div>Mapa: ${currentMapBaseLabel()}</div>
    <div>Modo: ${state.satellite.availability?.mode === "offline" ? "Offline" : state.satellite.availability?.mode === "partial" ? "Offline parcial" : state.satellite.availability?.mode === "online" ? "Online" : "N/D"}</div>
    <div>Tiles offline: ${state.satellite.availability?.coverage?.complete ? "Disponible" : state.satellite.availability?.coverage?.partial ? "Parcial" : "No disponible"}</div>
    <div>Conexión: ${connection}</div>
    <div>GPS: ${state.telemetry.gpsStatus || "N/D"}</div>
  `;
}

function currentMapBoundsPayload() {
  if (!state.map) {
    return null;
  }
  const bounds = state.map.getBounds();
  return {
    west: bounds.getWest(),
    south: bounds.getSouth(),
    east: bounds.getEast(),
    north: bounds.getNorth(),
  };
}

function currentSatelliteZoomRange() {
  const zoom = Math.max(0, Math.floor(state.map ? state.map.getZoom() : 0));
  return {
    min_zoom: zoom,
    max_zoom: Math.min(zoom + SATELLITE_DOWNLOAD_EXTRA_ZOOMS, SATELLITE_DOWNLOAD_MAX_ZOOM),
  };
}

async function refreshSatelliteState() {
  if (!state.map) {
    return;
  }
  try {
    const payload = {
      bounds: currentMapBoundsPayload(),
      zoom: Math.max(0, Math.floor(state.map.getZoom())),
    };
    const response = await postJson("/runtime/satellite/status", payload);
    state.satellite.availability = response.availability || null;
    state.satellite.task = response.task || null;
    updateSatelliteStatusUi();
    updateTelemetryPanel();
  } catch (_error) {
    // Mantener la UI operativa aunque falle el estado satelital.
  }
}

function updateSatelliteStatusUi() {
  const availability = state.satellite.availability || {};
  const task = state.satellite.task || {};
  const taskActive = ["queued", "downloading"].includes(task.status);
  if (taskActive) {
    satelliteStatusEl.textContent = task.message || `Descargando satélite offline: ${task.current || 0} / ${task.total || 0} tiles`;
  } else if (availability.message) {
    satelliteStatusEl.textContent = `Satélite: ${availability.message}`;
  } else if (!availability.configured) {
    satelliteStatusEl.textContent = "Satélite: proveedor no configurado.";
  } else {
    satelliteStatusEl.textContent = "Satélite: pendiente";
  }
  cancelSatelliteBtn.classList.toggle("hidden", !taskActive);
  downloadSatelliteBtn.disabled = taskActive || !state.map;
}

async function requestSatelliteEstimate() {
  const zoomRange = currentSatelliteZoomRange();
  return await postJson("/runtime/satellite/estimate", {
    bounds: currentMapBoundsPayload(),
    min_zoom: zoomRange.min_zoom,
    max_zoom: zoomRange.max_zoom,
  });
}

function formatHumanBytes(size) {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = Number(size || 0);
  let idx = 0;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return idx === 0 ? `${Math.round(value)} ${units[idx]}` : `${value.toFixed(1)} ${units[idx]}`;
}

async function startSatelliteDownloadFlow() {
  if (!state.map) {
    return;
  }
  try {
    const result = await requestSatelliteEstimate();
    const estimate = result.estimate || {};
    const availability = result.availability || {};
    if (estimate.total_tiles > estimate.limit) {
      window.alert("La zona seleccionada es demasiado grande. Acerca el mapa o reduce el rango de zoom.");
      satelliteStatusEl.textContent = "Satélite: la zona visible supera el límite de descarga.";
      return;
    }
    const confirmed = window.confirm(
      "Se descargarán imágenes satelitales de la zona visible para uso offline. Esto puede consumir espacio en disco y tardar varios minutos.\n\n"
      + `Zoom inicial: ${estimate.min_zoom}\n`
      + `Zoom final: ${estimate.max_zoom}\n`
      + `Tiles estimados: ${estimate.total_tiles}\n`
      + `Tamaño estimado: ${formatHumanBytes(estimate.estimated_bytes)}\n`
      + `Estado actual: ${availability.message || "Sin datos"}`
    );
    if (!confirmed) {
      return;
    }
    const zoomRange = currentSatelliteZoomRange();
    const response = await postJson("/runtime/satellite/download", {
      bounds: currentMapBoundsPayload(),
      min_zoom: zoomRange.min_zoom,
      max_zoom: zoomRange.max_zoom,
    });
    state.satellite.task = response.task || null;
    updateSatelliteStatusUi();
    await refreshSatelliteState();
  } catch (error) {
    satelliteStatusEl.textContent = `Satélite: ${String(error.message || error)}`;
  }
}

function formatCoords(lngLat) {
  return `${lngLat.lat.toFixed(5)}, ${lngLat.lng.toFixed(5)}`;
}

function updateCenterHud() {
  if (!state.map) {
    return;
  }
  const center = state.map.getCenter();
  coordCenterEl.textContent = `Centro: ${formatCoords(center)} | z ${state.map.getZoom().toFixed(2)}`;
  updateTelemetryPanel();
}

function describeFeature(feature) {
  const props = feature.properties || {};
  const coords = (feature.geometry || {}).coordinates;
  return [
    props.nombre || "Elemento",
    `Identificador: ${props.emoji ? `${props.emoji} ${props.icon_label || ""}`.trim() : "Sin identificador"}`,
    `Tipo: ${props.tipo || "n/d"}`,
    `Categoría: ${props.categoria || props.riesgo || "n/d"}`,
    `Estado: ${props.estado || "n/d"}`,
    `Coordenadas: ${JSON.stringify(coords || [])}`,
    `Notas: ${props.notas || props.descripcion || "Sin notas"}`,
    `Fuente: ${props.fuente_datos || "local"}`,
  ].join("\n");
}

function updateSelectedFeatureActions() {
  const feature = state.selectedFeature;
  const enabled = !!feature;
  if (featureActionsEl) {
    featureActionsEl.style.display = "flex";
  }
  featureEditBtnEl.disabled = !enabled;
  featureDeleteBtnEl.disabled = !enabled;
}

function showFeature(feature, lngLat) {
  state.selectedFeature = feature;
  featureInfoEl.textContent = describeFeature(feature);
  updateSelectedFeatureActions();
  if (state.popup) {
    state.popup.remove();
  }
  state.popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false })
    .setLngLat(lngLat)
    .setHTML(`<strong>${feature.properties?.emoji ? `${feature.properties.emoji} ` : ""}${feature.properties?.nombre || "Elemento"}</strong><br>${feature.properties?.categoria || feature.properties?.tipo || "n/d"}`)
    .addTo(state.map);
}

function clearFeatureSelection() {
  state.selectedFeature = null;
  featureInfoEl.textContent = "Selecciona un elemento del mapa para ver su información útil.";
  updateSelectedFeatureActions();
  if (state.popup) {
    state.popup.remove();
    state.popup = null;
  }
}

function hideContextMenu() {
  contextMenuEl.classList.add("hidden");
  contextMenuEl.innerHTML = "";
}

function showContextMenu(items, point, title = "Mapa") {
  contextMenuEl.innerHTML = `<div class="menu-title">${title}</div>`;
  for (const item of items) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "menu-item";
    btn.textContent = item.label;
    btn.onclick = () => {
      hideContextMenu();
      item.onClick();
    };
    contextMenuEl.appendChild(btn);
  }
  contextMenuEl.style.left = `${point.x}px`;
  contextMenuEl.style.top = `${point.y}px`;
  contextMenuEl.classList.remove("hidden");
}

function menuScreenPoint(mapPoint) {
  const rect = state.map.getCanvas().getBoundingClientRect();
  return {
    x: rect.left + mapPoint.x,
    y: rect.top + mapPoint.y,
  };
}

function populateSelect(selectEl, options, selected) {
  selectEl.innerHTML = "";
  for (const option of options) {
    const normalized = typeof option === "string" ? { value: option, label: option } : option;
    const el = document.createElement("option");
    el.value = normalized.value;
    el.textContent = normalized.label;
    if ((selected || "") === normalized.value) {
      el.selected = true;
    }
    selectEl.appendChild(el);
  }
}

function geometryToCoordinateText(feature) {
  const geometry = feature?.geometry || {};
  if (geometry.type === "LineString") {
    return (geometry.coordinates || []).map(([lon, lat]) => `${lat},${lon}`).join("\n");
  }
  if (geometry.type === "Polygon") {
    const ring = (geometry.coordinates || [])[0] || [];
    const trimmed = ring.length > 1 && ring[0][0] === ring[ring.length - 1][0] && ring[0][1] === ring[ring.length - 1][1] ? ring.slice(0, -1) : ring;
    return trimmed.map(([lon, lat]) => `${lat},${lon}`).join("\n");
  }
  return "";
}

function openFeatureModal(config) {
  state.formState = config;
  modalTitleEl.textContent = config.title;
  refreshCategorySelect(config.values.categoria);
  refreshLayerSelect(config.values.layer_id);
  fieldNombreEl.value = config.values.nombre || "";
  fieldDescripcionEl.value = config.values.descripcion || "";
  fieldRiesgoEl.value = config.values.riesgo || "medio";
  fieldLatitudEl.value = config.values.latitud ?? "";
  fieldLongitudEl.value = config.values.longitud ?? "";
  fieldCoordinatesEl.value = config.values.coordinates || "";
  const isPoint = config.kind === "point";
  latitudFieldWrapEl.classList.toggle("hidden", !isPoint);
  longitudFieldWrapEl.classList.toggle("hidden", !isPoint);
  emojiFieldWrapEl.classList.toggle("hidden", !isPoint);
  coordsFieldWrapEl.classList.toggle("hidden", isPoint || config.showCoordinateEditor !== true);
  fieldRiesgoEl.closest("label").classList.toggle("hidden", config.kind === "route");
  state.formState.emoji = config.values.emoji || "";
  state.formState.icon_label = config.values.icon_label || "";
  updateEmojiPickerButton();
  if (!isPoint) {
    fieldLatitudEl.value = "";
    fieldLongitudEl.value = "";
  }
  fieldDescripcionEl.required = false;
  deleteBtnEl.classList.toggle("hidden", !config.editing);
  featureModalEl.classList.remove("hidden");
}

function closeFeatureModal() {
  featureModalEl.classList.add("hidden");
  state.formState = null;
}

function selectedEmojiMeta() {
  return IDENTIFIER_EMOJIS.find((item) => item.emoji === state.formState?.emoji) || null;
}

function updateEmojiPickerButton() {
  const meta = selectedEmojiMeta();
  emojiPickerBtnEl.textContent = meta ? `${meta.emoji} ${meta.label}` : "Sin identificador";
}

function renderEmojiPicker() {
  emojiPickerGridEl.innerHTML = "";
  for (const item of IDENTIFIER_EMOJIS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `emoji-option${state.formState?.emoji === item.emoji ? " selected" : ""}`;
    btn.innerHTML = `<span class="emoji-symbol">${item.emoji}</span><span class="emoji-label">${item.label}</span>`;
    btn.onclick = () => {
      if (!state.formState) {
        return;
      }
      state.formState.emoji = item.emoji;
      state.formState.icon_label = item.label;
      updateEmojiPickerButton();
      renderEmojiPicker();
      closeEmojiModal();
    };
    emojiPickerGridEl.appendChild(btn);
  }
}

function openEmojiModal() {
  if (state.formState?.kind !== "point") {
    return;
  }
  renderEmojiPicker();
  emojiModalEl.classList.remove("hidden");
}

function closeEmojiModal() {
  emojiModalEl.classList.add("hidden");
}

function clearEmojiMarkers() {
  for (const marker of state.emojiMarkers) {
    marker.remove();
  }
  state.emojiMarkers = [];
}

async function syncEmojiMarkers() {
  clearEmojiMarkers();
  if (!state.map || !state.config?.capas) {
    return;
  }
  const overlayPrefs = state.config.preferences?.overlay_layers || {};
  for (const [layerId, meta] of Object.entries(state.config.capas)) {
    if (overlayPrefs[layerId] === false) {
      continue;
    }
    try {
      const fc = await fetchJson(meta.url);
      for (const feature of fc.features || []) {
        const props = feature.properties || {};
        const geometry = feature.geometry || {};
        if (geometry.type !== "Point" || !props.emoji) {
          continue;
        }
        const coordinates = geometry.coordinates || [];
        if (!Array.isArray(coordinates) || coordinates.length < 2) {
          continue;
        }
        const el = document.createElement("button");
        el.type = "button";
        el.className = "emoji-map-marker";
        el.textContent = props.emoji;
        el.title = props.nombre || props.icon_label || "Identificador";
        el.onclick = (event) => {
          event.stopPropagation();
          showFeature(feature, { lng: coordinates[0], lat: coordinates[1] });
        };
        el.oncontextmenu = (event) => {
          event.preventDefault();
          event.stopPropagation();
          showFeature(feature, { lng: coordinates[0], lat: coordinates[1] });
          const kind = featureKind(feature);
          showContextMenu(
            [
              { label: kind === "point" ? "Editar punto" : kind === "route" ? "Editar ruta" : "Editar polígono", onClick: () => openEditFeatureModal(feature) },
              { label: "Eliminar", onClick: () => deleteFeatureFromContext(feature) },
            ],
            { x: event.clientX, y: event.clientY },
            feature.properties?.nombre || "Elemento",
          );
        };
        const marker = new maplibregl.Marker({ element: el, anchor: "center" })
          .setLngLat([coordinates[0], coordinates[1]])
          .addTo(state.map);
        state.emojiMarkers.push(marker);
      }
    } catch (_error) {
      // Ignorar fallos transitorios de una capa individual.
    }
  }
}

function bindOverlayClicks() {
  if (!state.map || !state.config) {
    return;
  }
  for (const layerId of Object.keys(state.config.capas || {})) {
    for (const suffix of ["fill", "line", "circle", "emoji"]) {
      const styleLayerId = `ov-${layerId}-${suffix}`;
      if (!state.map.getLayer(styleLayerId)) {
        continue;
      }
      state.map.on("click", styleLayerId, (event) => {
        const feature = event.features && event.features[0];
        if (!feature) {
          return;
        }
        showFeature(feature, event.lngLat);
      });
      state.map.on("mouseenter", styleLayerId, () => {
        state.map.getCanvas().style.cursor = "pointer";
      });
      state.map.on("mouseleave", styleLayerId, () => {
        state.map.getCanvas().style.cursor = "";
      });
      state.boundOverlayHandlers.add(styleLayerId);
    }
  }
}

function showMapContextMenu(lngLat, point) {
  state.contextTarget = { lngLat, point };
  showContextMenu(
    [
      { label: "Agregar punto", onClick: () => openCreatePointModal(lngLat) },
      { label: "Agregar identificador", onClick: () => openCreateIdentifierModal(lngLat) },
      { label: "Agregar ruta", onClick: () => beginRouteDrawing(lngLat) },
      { label: "Agregar polígono", onClick: () => beginPolygonDrawing(lngLat) },
    ],
    menuScreenPoint(point),
    "Crear elemento",
  );
}

function showFeatureContextMenu(feature, point) {
  const kind = featureKind(feature);
  showContextMenu(
    [
      { label: kind === "point" ? "Editar punto" : kind === "route" ? "Editar ruta" : "Editar polígono", onClick: () => openEditFeatureModal(feature) },
      { label: "Eliminar", onClick: () => deleteFeatureFromContext(feature) },
    ],
    menuScreenPoint(point),
    feature.properties?.nombre || "Elemento",
  );
}

function featureKind(feature) {
  const type = feature?.geometry?.type || "";
  if (type === "Point") return "point";
  if (type === "LineString" || type === "MultiLineString") return "route";
  return "polygon";
}

function openCreatePointModal(lngLat) {
  openFeatureModal({
    editing: false,
    kind: "point",
    title: "Agregar punto",
    showCoordinateEditor: false,
    values: {
      nombre: "",
      categoria: "refugio",
      descripcion: "",
      riesgo: "medio",
      layer_id: "puntos",
      latitud: Number(lngLat.lat.toFixed(6)),
      longitud: Number(lngLat.lng.toFixed(6)),
      emoji: "",
      icon_label: "",
    },
  });
}

function openCreateIdentifierModal(lngLat) {
  openFeatureModal({
    editing: false,
    kind: "point",
    title: "Agregar identificador",
    showCoordinateEditor: false,
    values: {
      nombre: "",
      categoria: "punto_interes",
      descripcion: "Identificador visual en el mapa",
      riesgo: "medio",
      layer_id: "puntos",
      latitud: Number(lngLat.lat.toFixed(6)),
      longitud: Number(lngLat.lng.toFixed(6)),
      emoji: "",
      icon_label: "",
    },
  });
  openEmojiModal();
}

function openCreateGeometryModal(kind, lngLat) {
  const sample = `${lngLat.lat.toFixed(6)},${lngLat.lng.toFixed(6)}`;
  openFeatureModal({
    editing: false,
    kind,
    title: kind === "route" ? "Agregar ruta" : "Agregar polígono",
    showCoordinateEditor: true,
    values: {
      nombre: "",
      categoria: kind === "route" ? "ruta" : "zona_riesgo",
      descripcion: "",
      riesgo: kind === "route" ? "medio" : "alto",
      layer_id: kind === "route" ? "rutas" : "poligonos",
      coordinates: sample,
    },
  });
}

function beginPolygonDrawing(lngLat) {
  state.drawMode = {
    kind: "polygon",
    points: [[Number(lngLat.lng.toFixed(6)), Number(lngLat.lat.toFixed(6))]],
  };
  closeFeatureModal();
  hideContextMenu();
  updateSketch();
  statusEl.textContent = "Dibujo de polígono activo: clic izquierdo para añadir vértices y clic derecho para finalizar.";
}

function beginRouteDrawing(lngLat) {
  state.drawMode = {
    kind: "route",
    points: [[Number(lngLat.lng.toFixed(6)), Number(lngLat.lat.toFixed(6))]],
  };
  closeFeatureModal();
  hideContextMenu();
  updateSketch();
  statusEl.textContent = "Dibujo de ruta activo: clic izquierdo para añadir puntos en orden y clic derecho para finalizar.";
}

function addRouteVertex(lngLat) {
  if (!state.drawMode || state.drawMode.kind !== "route") {
    return;
  }
  state.drawMode.points.push([Number(lngLat.lng.toFixed(6)), Number(lngLat.lat.toFixed(6))]);
  updateSketch();
  statusEl.textContent = `Puntos de la ruta: ${state.drawMode.points.length}. Clic derecho para finalizar.`;
}

function cancelRouteDrawing() {
  state.drawMode = null;
  updateSketch();
  statusEl.textContent = "Dibujo de ruta cancelado.";
}

function finishRouteDrawing() {
  if (!state.drawMode || state.drawMode.kind !== "route") {
    return;
  }
  if (state.drawMode.points.length < 2) {
    statusEl.textContent = "La ruta necesita al menos 2 puntos.";
    return;
  }
  const coordinates = state.drawMode.points.map(([lng, lat]) => [lng, lat]);
  state.drawMode = null;
  updateSketch();
  openFeatureModal({
    editing: false,
    kind: "route",
    title: "Agregar ruta",
    showCoordinateEditor: false,
    values: {
      nombre: "",
      categoria: "ruta",
      descripcion: "",
      riesgo: "medio",
      layer_id: "rutas",
      coordinates: coordinates.map(([lng, lat]) => `${lat},${lng}`).join("\n"),
    },
  });
  statusEl.textContent = "Ruta capturada. Completa el formulario y guarda.";
}

function addPolygonVertex(lngLat) {
  if (!state.drawMode || state.drawMode.kind !== "polygon") {
    return;
  }
  state.drawMode.points.push([Number(lngLat.lng.toFixed(6)), Number(lngLat.lat.toFixed(6))]);
  updateSketch();
  statusEl.textContent = `Vértices del polígono: ${state.drawMode.points.length}. Clic derecho para finalizar.`;
}

function cancelPolygonDrawing() {
  state.drawMode = null;
  updateSketch();
  statusEl.textContent = "Dibujo de polígono cancelado.";
}

function finishPolygonDrawing(point) {
  if (!state.drawMode || state.drawMode.kind !== "polygon") {
    return;
  }
  if (state.drawMode.points.length < 3) {
    showContextMenu([{ label: "Cancelar dibujo", onClick: () => cancelPolygonDrawing() }], menuScreenPoint(point), "Faltan vértices");
    statusEl.textContent = "El polígono necesita al menos 3 vértices.";
    return;
  }
  const coordinates = state.drawMode.points.map(([lng, lat]) => [lng, lat]);
  state.drawMode = null;
  updateSketch();
  openFeatureModal({
    editing: false,
    kind: "polygon",
    title: "Agregar polígono",
    showCoordinateEditor: false,
    values: {
      nombre: "",
      categoria: "zona_riesgo",
      descripcion: "",
      riesgo: "alto",
      layer_id: "poligonos",
      coordinates: coordinates.map(([lng, lat]) => `${lat},${lng}`).join("\n"),
    },
  });
  statusEl.textContent = "Polígono capturado. Completa el formulario y guarda.";
}

function openEditFeatureModal(feature) {
  const kind = featureKind(feature);
  const coords = feature?.geometry?.coordinates || [];
  openFeatureModal({
    editing: true,
    kind,
    title: kind === "point" ? "Editar punto" : kind === "route" ? "Editar ruta" : "Editar polígono",
    values: {
      feature_id: feature.properties?.id || "",
      nombre: feature.properties?.nombre || "",
      categoria: feature.properties?.categoria || "",
      descripcion: feature.properties?.descripcion || "",
      riesgo: feature.properties?.riesgo || "medio",
      layer_id: feature.properties?.tipo || (kind === "point" ? "puntos" : kind === "route" ? "rutas" : "poligonos"),
      latitud: kind === "point" ? Number((coords[1] || 0).toFixed(6)) : "",
      longitud: kind === "point" ? Number((coords[0] || 0).toFixed(6)) : "",
      coordinates: geometryToCoordinateText(feature),
      emoji: feature.properties?.emoji || "",
      icon_label: feature.properties?.icon_label || "",
    },
  });
}

function formPayloadFromModal() {
  const base = {
    nombre: fieldNombreEl.value.trim(),
    categoria: fieldCategoriaEl.value,
    descripcion: fieldDescripcionEl.value.trim(),
    riesgo: fieldRiesgoEl.value,
    layer_id: fieldLayerIdEl.value,
  };
  if (state.formState.kind === "point") {
    return {
      ...base,
      coordinates: {
        lat: Number(fieldLatitudEl.value),
        lon: Number(fieldLongitudEl.value),
      },
      emoji: state.formState.emoji || "",
      icon_label: state.formState.icon_label || "",
    };
  }
  return {
    ...base,
    coordinates: parseCoordinateLines(fieldCoordinatesEl.value),
  };
}

async function saveFeatureFromModal() {
  if (!state.formState) {
    return;
  }
  const payload = formPayloadFromModal();
  if (!payload.nombre) {
    throw new Error("El nombre es obligatorio.");
  }
  if (state.formState.editing) {
    await postJson("/runtime/feature/update", {
      kind: state.formState.kind,
      feature_id: state.formState.values.feature_id,
      ...payload,
    });
    statusEl.textContent = `Elemento "${payload.nombre}" actualizado`;
  } else {
    await postJson("/runtime/feature", {
      kind: state.formState.kind,
      ...payload,
    });
    statusEl.textContent = `Elemento "${payload.nombre}" guardado`;
  }
  closeFeatureModal();
  await loadRuntime(true);
}

async function deleteFeatureFromContext(feature) {
  const name = feature?.properties?.nombre || "elemento";
  if (!window.confirm(`¿Eliminar "${name}"?`)) {
    return;
  }
  await postJson("/runtime/feature/delete", {
    feature_id: feature.properties?.id || "",
    layer_id: feature.properties?.tipo || "",
  });
  statusEl.textContent = `Elemento "${name}" eliminado`;
  closeFeatureModal();
  await loadRuntime(true);
}

async function handleCategoryAdd() {
  const kind = state.formState?.kind;
  if (!kind) return;
  const nombre = window.prompt("Nueva categoría:", "");
  if (!nombre || !nombre.trim()) return;
  const label = nombre.trim();
  const value = normalizeCategoryValue(label);
  if (!value) return;
  const opciones = categoryOptionsForKind(kind);
  if (opciones.some((item) => item.value === value)) {
    statusEl.textContent = `La categoría "${label}" ya existe`;
    refreshCategorySelect(value);
    return;
  }
  const custom = (state.config.preferences.category_options?.[kind] || []).slice();
  custom.push({ value, label });
  await saveCategoryOptions(kind, custom);
  const hidden = (state.config.preferences.category_hidden?.[kind] || []).filter((item) => item !== value);
  await saveHiddenCategories(kind, hidden);
  refreshCategorySelect(value);
  statusEl.textContent = `Categoría "${label}" agregada`;
}

async function handleCategoryEdit() {
  const kind = state.formState?.kind;
  const actual = fieldCategoriaEl.value;
  if (!kind || !actual) return;
  const opciones = categoryOptionsForKind(kind);
  const encontrada = opciones.find((item) => item.value === actual);
  if (!encontrada) return;
  const nuevoNombre = window.prompt("Editar categoría:", encontrada.label);
  if (!nuevoNombre || !nuevoNombre.trim()) return;
  const label = nuevoNombre.trim();
  const value = normalizeCategoryValue(label);
  if (!value) return;
  const defaults = (CATEGORY_OPTIONS[kind] || []).map((item) => (typeof item === "string" ? normalizeCategoryValue(item) : item.value));
  const custom = (state.config.preferences.category_options?.[kind] || []).slice();
  const customIndex = custom.findIndex((item) => String(item.value) === actual);
  if (customIndex >= 0) {
    custom[customIndex] = { value, label };
  } else if (defaults.includes(actual)) {
    custom.push({ value, label });
  }
  await saveCategoryOptions(kind, custom);
  const hidden = (state.config.preferences.category_hidden?.[kind] || []).filter((item) => item !== value);
  if (defaults.includes(actual) && actual !== value && !hidden.includes(actual)) {
    hidden.push(actual);
  }
  await saveHiddenCategories(kind, hidden);
  refreshCategorySelect(value);
  statusEl.textContent = `Categoría actualizada a "${label}"`;
}

async function handleCategoryDelete() {
  const kind = state.formState?.kind;
  const actual = fieldCategoriaEl.value;
  if (!kind || !actual) return;
  const opciones = categoryOptionsForKind(kind);
  const encontrada = opciones.find((item) => item.value === actual);
  if (!encontrada) return;
  if (!window.confirm(`¿Eliminar la categoría "${encontrada.label}"?`)) {
    return;
  }
  const defaults = (CATEGORY_OPTIONS[kind] || []).map((item) => (typeof item === "string" ? normalizeCategoryValue(item) : item.value));
  const custom = (state.config.preferences.category_options?.[kind] || []).slice().filter((item) => String(item.value) !== actual);
  const hidden = (state.config.preferences.category_hidden?.[kind] || []).slice();
  if (defaults.includes(actual) && !hidden.includes(actual)) {
    hidden.push(actual);
  }
  await saveCategoryOptions(kind, custom);
  await saveHiddenCategories(kind, hidden);
  const restantes = categoryOptionsForKind(kind);
  refreshCategorySelect(restantes[0]?.value || "");
  statusEl.textContent = `Categoría "${encontrada.label}" eliminada`;
}

async function handleLayerAdd() {
  const kind = state.formState?.kind;
  if (!kind) return;
  const nombre = window.prompt("Nuevo tipo de capa:", "");
  if (!nombre || !nombre.trim()) return;
  const label = nombre.trim();
  const value = normalizeCategoryValue(label);
  if (!value) return;
  const existentes = [
    ...(LAYER_OPTIONS[kind] || []).map((item) => String(item.value || item).trim()),
    ...(state.config.preferences.custom_layers || []).map((item) => String(item.id || "").trim()),
  ];
  if (existentes.includes(value)) {
    statusEl.textContent = `La capa "${label}" ya existe`;
    refreshLayerSelect(value);
    return;
  }
  const custom = (state.config.preferences.custom_layers || []).slice();
  custom.push({
    id: value,
    label,
    geometry: geometryForKind(kind),
    color: colorForKind(kind),
  });
  await saveCustomLayers(custom);
  const hidden = (state.config.preferences.layer_hidden?.[kind] || []).filter((item) => item !== value);
  await saveHiddenLayers(kind, hidden);
  await saveLayerLabels({ [value]: label });
  refreshLayerSelect(value);
  statusEl.textContent = `Tipo de capa "${label}" agregado`;
}

async function handleLayerEdit() {
  const kind = state.formState?.kind;
  const actual = fieldLayerIdEl.value;
  if (!kind || !actual) return;
  const opciones = layerOptionsForKind(kind);
  const encontrada = opciones.find((item) => item.value === actual);
  if (!encontrada) return;
  const nuevoNombre = window.prompt("Editar tipo de capa:", encontrada.label);
  if (!nuevoNombre || !nuevoNombre.trim()) return;
  const label = nuevoNombre.trim();
  const custom = (state.config.preferences.custom_layers || []).slice();
  const customIndex = custom.findIndex((item) => String(item.id) === actual);
  if (customIndex >= 0) {
    custom[customIndex] = { ...custom[customIndex], label };
    await saveCustomLayers(custom);
  }
  await saveLayerLabels({ [actual]: label });
  refreshLayerSelect(actual);
  statusEl.textContent = `Tipo de capa actualizado a "${label}"`;
}

async function handleLayerDelete() {
  const kind = state.formState?.kind;
  const actual = fieldLayerIdEl.value;
  if (!kind || !actual) return;
  const opciones = layerOptionsForKind(kind);
  const encontrada = opciones.find((item) => item.value === actual);
  if (!encontrada) return;
  if (!window.confirm(`¿Ocultar el tipo de capa "${encontrada.label}"?`)) {
    return;
  }
  const hidden = (state.config.preferences.layer_hidden?.[kind] || []).slice();
  if (!hidden.includes(actual)) {
    hidden.push(actual);
  }
  await saveHiddenLayers(kind, hidden);
  const restantes = layerOptionsForKind(kind);
  refreshLayerSelect(restantes[0]?.value || "");
  statusEl.textContent = `Tipo de capa "${encontrada.label}" ocultado`;
}

function showCategoryFieldContextMenu(event) {
  event.preventDefault();
  event.stopPropagation();
  showContextMenu(
    [
      { label: "Agregar categoría", onClick: () => void handleCategoryAdd() },
      { label: "Editar categoría", onClick: () => void handleCategoryEdit() },
      { label: "Eliminar categoría", onClick: () => void handleCategoryDelete() },
    ],
    { x: event.clientX, y: event.clientY },
    "Categoría",
  );
}

function showLayerFieldContextMenu(event) {
  event.preventDefault();
  event.stopPropagation();
  showContextMenu(
    [
      { label: "Agregar tipo de capa", onClick: () => void handleLayerAdd() },
      { label: "Editar tipo de capa", onClick: () => void handleLayerEdit() },
      { label: "Ocultar tipo de capa", onClick: () => void handleLayerDelete() },
    ],
    { x: event.clientX, y: event.clientY },
    "Tipo de capa",
  );
}

function bindRightClickMenu(target, handler) {
  if (!target) {
    return;
  }
  target.oncontextmenu = handler;
  target.onmousedown = (event) => {
    if (event.button === 2) {
      handler(event);
    }
  };
}

function buildToggle(container, key, label, checked, meta, onChange) {
  const row = document.createElement("label");
  row.className = "layer-toggle";
  row.innerHTML = `
    <input type="checkbox" ${checked ? "checked" : ""}>
    <div>
      <div>${label}</div>
      <div class="layer-meta">${meta || ""}</div>
    </div>
    <span>${checked ? "on" : "off"}</span>
  `;
  const input = row.querySelector("input");
  const badge = row.querySelector("span");
  input.addEventListener("change", () => {
    badge.textContent = input.checked ? "on" : "off";
    onChange(key, input.checked);
  });
  container.appendChild(row);
}

function buildChoiceToggle(container, key, label, checked, meta, onChange) {
  const row = document.createElement("label");
  row.className = "layer-toggle";
  row.innerHTML = `
    <input type="radio" name="map-base-choice" ${checked ? "checked" : ""}>
    <div>
      <div>${label}</div>
      <div class="layer-meta">${meta || ""}</div>
    </div>
    <span>${checked ? "activo" : ""}</span>
  `;
  const input = row.querySelector("input");
  const badge = row.querySelector("span");
  input.addEventListener("change", () => {
    if (!input.checked) {
      return;
    }
    for (const item of container.querySelectorAll(".layer-toggle span")) {
      item.textContent = "";
    }
    badge.textContent = "activo";
    onChange(key);
  });
  container.appendChild(row);
}

function renderControls() {
  const config = state.config;
  const prefs = config.preferences || {};

  styleSelectEl.innerHTML = "";
  for (const item of config.styles || []) {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.label;
    if ((prefs.style_id || "standard") === item.id) {
      option.selected = true;
    }
    styleSelectEl.appendChild(option);
  }

  mapBaseListEl.innerHTML = "";
  for (const item of MAP_BASE_OPTIONS) {
    buildChoiceToggle(
      mapBaseListEl,
      item.id,
      item.label,
      (prefs.map_base || "mapa") === item.id,
      item.meta,
      (id) => {
        state.config.preferences.map_base = id;
        applyVisibilityFromPreferences();
        updateTelemetryPanel();
        persistPreferences({ map_base: id });
      },
    );
  }

  baseLayersListEl.innerHTML = "";
  const baseLabels = {
    land: "Suelo / terreno",
    satellite: "Satélite",
    water: "Agua",
    roads: "Calles y carreteras",
    rails: "Vías férreas",
    air: "Pistas / aerovías",
    buildings: "Edificios",
    parks: "Parques / vegetación",
    terrain: "Curvas / relieve",
    landuse: "Uso de suelo",
    boundaries: "Límites administrativos",
    labels: "Etiquetas / nombres",
    place_labels: "Nombres de lugares",
    water_labels: "Etiquetas de agua",
    boundary_labels: "Etiquetas de límites",
  };
  for (const key of Object.keys(state.baseLayerGroups)) {
    if (key === "satellite") {
      continue;
    }
    buildToggle(
      baseLayersListEl,
      key,
      baseLabels[key] || key,
      prefs.base_layers?.[key] !== false,
      state.baseLayerGroups[key].length ? `${state.baseLayerGroups[key].length} subcapas` : "No disponible en este tileset",
      (id, checked) => {
        state.config.preferences.base_layers[id] = checked;
        setLayerGroupVisibility(state.baseLayerGroups[id], checked);
        persistPreferences({ base_layers: { [id]: checked } });
      },
    );
  }

  overlayLayersListEl.innerHTML = "";
  for (const meta of config.layer_meta || []) {
    buildToggle(
      overlayLayersListEl,
      meta.id,
      meta.label,
      prefs.overlay_layers?.[meta.id] !== false,
      `${meta.feature_count} elementos | ${meta.geometry_types.join(", ") || "sin geometría"}`,
      (id, checked) => {
        state.config.preferences.overlay_layers[id] = checked;
        setLayerGroupVisibility(state.overlayLayerGroups[id], checked);
        persistPreferences({ overlay_layers: { [id]: checked } });
        syncEmojiMarkers();
      },
    );
  }
  for (const meta of EXTRA_OVERLAY_OPTIONS) {
    const checked = meta.id === "telemetry_panel"
      ? !!prefs.telemetry_visible
      : prefs.overlay_layers?.[meta.id] !== false;
    buildToggle(
      overlayLayersListEl,
      meta.id,
      meta.label,
      checked,
      meta.meta,
      (id, enabled) => {
        if (id === "telemetry_panel") {
          state.config.preferences.telemetry_visible = enabled;
          updateTelemetryPanelVisibility();
          updateTelemetryPanel();
          persistPreferences({ telemetry_visible: enabled });
          return;
        }
        state.config.preferences.overlay_layers[id] = enabled;
        setLayerGroupVisibility(state.overlayLayerGroups[id] || [], enabled);
        persistPreferences({ overlay_layers: { [id]: enabled } });
      },
    );
  }
}

function haversine(a, b) {
  const toRad = (n) => (n * Math.PI) / 180;
  const R = 6371000;
  const dLat = toRad(b.lat - a.lat);
  const dLon = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const q = Math.sin(dLat / 2) ** 2 + Math.sin(dLon / 2) ** 2 * Math.cos(lat1) * Math.cos(lat2);
  return 2 * R * Math.atan2(Math.sqrt(q), Math.sqrt(1 - q));
}

function measurementGeoJSON() {
  const features = state.measurePoints.map((p, idx) => ({
    type: "Feature",
    properties: { idx },
    geometry: { type: "Point", coordinates: [p.lng, p.lat] },
  }));
  if (state.measurePoints.length >= 2) {
    features.push({
      type: "Feature",
      properties: {},
      geometry: {
        type: "LineString",
        coordinates: state.measurePoints.map((p) => [p.lng, p.lat]),
      },
    });
  }
  return { type: "FeatureCollection", features };
}

function sketchGeoJSON() {
  const mode = state.drawMode;
  if (!mode || !Array.isArray(mode.points) || mode.points.length === 0) {
    return { type: "FeatureCollection", features: [] };
  }
  const features = mode.points.map(([lng, lat], idx) => ({
    type: "Feature",
    properties: { idx },
    geometry: { type: "Point", coordinates: [lng, lat] },
  }));
  const coordinates = mode.points.map(([lng, lat]) => [lng, lat]);
  if (coordinates.length >= 2) {
    features.push({
      type: "Feature",
      properties: {},
      geometry: { type: "LineString", coordinates },
    });
  }
  if (mode.kind === "polygon" && coordinates.length >= 3) {
    const ring = [...coordinates];
    if (ring[0][0] !== ring[ring.length - 1][0] || ring[0][1] !== ring[ring.length - 1][1]) {
      ring.push(ring[0]);
    }
    features.push({
      type: "Feature",
      properties: {},
      geometry: { type: "Polygon", coordinates: [ring] },
    });
  }
  return { type: "FeatureCollection", features };
}

function updateMeasurement() {
  if (!state.map) {
    return;
  }
  const source = state.map.getSource("measure");
  if (source && source.setData) {
    source.setData(measurementGeoJSON());
  }
  if (state.measurePoints.length < 2) {
    measureInfoEl.textContent = state.config.preferences.measurement_enabled ? "Medición: marca puntos sobre el mapa" : "Medición: inactiva";
    return;
  }
  let total = 0;
  for (let i = 1; i < state.measurePoints.length; i++) {
    total += haversine(state.measurePoints[i - 1], state.measurePoints[i]);
  }
  measureInfoEl.textContent = total >= 1000 ? `Medición: ${(total / 1000).toFixed(2)} km` : `Medición: ${Math.round(total)} m`;
}

function updateSketch() {
  if (!state.map) {
    return;
  }
  const source = state.map.getSource("sketch");
  if (source && source.setData) {
    source.setData(sketchGeoJSON());
  }
}

function clearMeasurement() {
  state.measurePoints = [];
  updateMeasurement();
}

function initTelemetrySensors() {
  if (navigator.geolocation) {
    state.telemetry.gpsStatus = "Disponible";
    navigator.geolocation.watchPosition(
      (position) => {
        const coords = position.coords || {};
        state.telemetry.altitude = Number.isFinite(coords.altitude) ? coords.altitude : null;
        state.telemetry.heading = Number.isFinite(coords.heading) ? coords.heading : null;
        state.telemetry.speed = Number.isFinite(coords.speed) ? coords.speed : null;
        state.telemetry.gpsStatus = "Activo";
        updateTelemetryPanel();
      },
      (_error) => {
        state.telemetry.gpsStatus = "No disponible";
        updateTelemetryPanel();
      },
      { enableHighAccuracy: false, maximumAge: 15000, timeout: 10000 },
    );
  } else {
    state.telemetry.gpsStatus = "No disponible";
  }
  window.addEventListener("online", () => updateTelemetryPanel());
  window.addEventListener("offline", () => updateTelemetryPanel());
}

async function persistPreferences(delta) {
  if (state.persistTimer) {
    clearTimeout(state.persistTimer);
  }
  state.persistTimer = setTimeout(async () => {
    try {
      await fetch("/runtime/preferences", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(delta),
      });
    } catch (_error) {
      // Runtime persistence can fail transiently; UI state remains local.
    }
  }, 350);
}

function bindUI() {
  for (const toggle of collapseToggleEls) {
    toggle.onclick = () => {
      const targetId = toggle.getAttribute("data-target");
      const body = document.getElementById(targetId);
      if (!body) {
        return;
      }
      const hidden = body.classList.toggle("hidden");
      const icon = toggle.querySelector(".collapse-icon");
      if (icon) {
        icon.textContent = hidden ? "+" : "−";
      }
    };
  }
  styleSelectEl.onchange = () => {
    state.config.preferences.style_id = styleSelectEl.value;
    persistPreferences({ style_id: styleSelectEl.value });
    reloadMapStyle();
  };
  recenterBtn.onclick = () => {
    if (!state.map || !state.config?.mapa) {
      return;
    }
    state.map.flyTo({
      center: [state.config.mapa.centerLon, state.config.mapa.centerLat],
      zoom: state.config.preferences.last_zoom || state.config.mapa.zoomInicial,
      speed: 0.8,
    });
  };
  measureToggleBtn.onclick = () => {
    const enabled = !state.config.preferences.measurement_enabled;
    state.config.preferences.measurement_enabled = enabled;
    measureToggleBtn.classList.toggle("active", enabled);
    persistPreferences({ measurement_enabled: enabled });
    updateMeasurement();
  };
  clearMeasureBtn.onclick = () => clearMeasurement();
  refreshBtn.onclick = () => loadRuntime(true);
  downloadSatelliteBtn.onclick = () => void startSatelliteDownloadFlow();
  cancelSatelliteBtn.onclick = async () => {
    try {
      await postJson("/runtime/satellite/cancel", {});
      await refreshSatelliteState();
    } catch (error) {
      satelliteStatusEl.textContent = `Satélite: ${String(error.message || error)}`;
    }
  };
  telemetryToggleBtn.onclick = () => {
    const enabled = !state.config.preferences.telemetry_visible;
    state.config.preferences.telemetry_visible = enabled;
    updateTelemetryPanelVisibility();
    updateTelemetryPanel();
    persistPreferences({ telemetry_visible: enabled });
  };
  categoryAddBtn.onclick = () => void handleCategoryAdd();
  categoryEditBtn.onclick = () => void handleCategoryEdit();
  categoryDeleteBtn.onclick = () => void handleCategoryDelete();
  layerAddBtn.onclick = () => void handleLayerAdd();
  layerEditBtn.onclick = () => void handleLayerEdit();
  layerDeleteBtn.onclick = () => void handleLayerDelete();
  bindRightClickMenu(fieldCategoriaEl, showCategoryFieldContextMenu);
  bindRightClickMenu(fieldCategoriaWrapEl, showCategoryFieldContextMenu);
  bindRightClickMenu(fieldLayerIdEl, showLayerFieldContextMenu);
  bindRightClickMenu(fieldLayerWrapEl, showLayerFieldContextMenu);
  modalCloseBtn.onclick = () => closeFeatureModal();
  emojiPickerBtnEl.onclick = () => openEmojiModal();
  emojiModalCloseBtnEl.onclick = () => closeEmojiModal();
  featureModalEl.addEventListener("click", (event) => {
    if (event.target === featureModalEl) {
      closeFeatureModal();
    }
  });
  emojiModalEl.addEventListener("click", (event) => {
    if (event.target === emojiModalEl) {
      closeEmojiModal();
    }
  });
  featureFormEl.onsubmit = async (event) => {
    event.preventDefault();
    try {
      await saveFeatureFromModal();
    } catch (error) {
      statusEl.textContent = String(error.message || error);
    }
  };
  deleteBtnEl.onclick = async () => {
    try {
      await postJson("/runtime/feature/delete", {
        feature_id: state.formState?.values?.feature_id || "",
        layer_id: fieldLayerIdEl.value,
      });
      statusEl.textContent = `Elemento eliminado`;
      closeFeatureModal();
      await loadRuntime(true);
    } catch (error) {
      statusEl.textContent = String(error.message || error);
    }
  };
  featureEditBtnEl.onclick = () => {
    if (!state.selectedFeature) {
      return;
    }
    openEditFeatureModal(state.selectedFeature);
  };
  featureDeleteBtnEl.onclick = async () => {
    if (!state.selectedFeature) {
      return;
    }
    try {
      await deleteFeatureFromContext(state.selectedFeature);
      clearFeatureSelection();
    } catch (error) {
      statusEl.textContent = String(error.message || error);
    }
  };
  document.addEventListener("click", () => hideContextMenu());
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      hideContextMenu();
      if (state.drawMode?.kind === "polygon") {
        cancelPolygonDrawing();
      } else if (state.drawMode?.kind === "route") {
        cancelRouteDrawing();
      } else if (!emojiModalEl.classList.contains("hidden")) {
        closeEmojiModal();
      } else {
        closeFeatureModal();
      }
    }
  });
}

function parseCoordinateLines(text) {
  return String(text || "")
    .split(/[\n;]+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [latRaw, lonRaw] = line.split(",").map((value) => value.trim());
      if (!latRaw || !lonRaw) {
        throw new Error(`Coordenada inválida: ${line}`);
      }
      return [Number(lonRaw), Number(latRaw)];
    });
}

function reloadMapStyle() {
  if (!state.map || !state.config?.mapa?.hasPmtiles) {
    return;
  }
  const center = state.map.getCenter();
  const zoom = state.map.getZoom();
  state.map.setStyle(buildStyle(state.config));
  state.map.once("styledata", () => {
    state.map.jumpTo({ center, zoom });
    state.baseLayerGroups = baseLayerGroups(availableSourceLayers(state.config));
    state.overlayLayerGroups = overlayLayerGroups(state.config);
    applyVisibilityFromPreferences();
    bindOverlayClicks();
    updateMeasurement();
    syncEmojiMarkers();
  });
}

function updateOverlaySources(config) {
  if (!state.map) {
    return;
  }
  for (const layerId of Object.keys(config.capas || {})) {
    const source = state.map.getSource(layerId);
    if (source && source.setData) {
      source.setData(cacheBust(config.capas[layerId].url));
    }
  }
  updateMeasurement();
}

function showEmpty(message, detail) {
  clearEmojiMarkers();
  emptyStateEl.classList.remove("hidden");
  emptyStateEl.querySelector("h2").textContent = message;
  emptyStateEl.querySelector("p").textContent = detail;
  mapNameEl.textContent = message;
  mapMetaEl.textContent = "";
  statusEl.textContent = detail;
}

function hideEmpty() {
  emptyStateEl.classList.add("hidden");
}

async function loadRuntime(force = false) {
  try {
    const config = await fetchJson("/runtime/runtime_config.json");
    const changedMap = (config.mapa && config.mapa.id) !== state.currentMapId;
    const changedUpdate = (config.updated_at || "") !== state.lastUpdatedAt;
    if (changedMap) {
      clearFeatureSelection();
    }
    state.config = config;
    state.lastUpdatedAt = config.updated_at || "";
    viewerModeEl.textContent = config.mapa ? `Modo ${config.mapa.viewer_mode}` : "Sin mapa activo";
    viewerInfoEl.textContent = config.mapa
      ? `Mapa: ${config.mapa.name}\nFormato: ${config.mapa.format}\nEsquema: ${config.mapa.schema || "offline"}\nCentro base: ${config.mapa.centerLat.toFixed(5)}, ${config.mapa.centerLon.toFixed(5)}`
      : "Selecciona y activa un mapa desde TLAMATINI.";

    if (!config.mapa) {
      showEmpty("Sin mapa activo", "No hay un mapa offline activado en este momento.");
      return;
    }

    mapNameEl.textContent = config.mapa.name;
    mapMetaEl.textContent = `${config.mapa.format} | zoom ${config.mapa.minZoom}-${config.mapa.maxZoom}`;
    measureToggleBtn.classList.toggle("active", !!config.preferences.measurement_enabled);

    if (!config.mapa.hasPmtiles) {
      showEmpty("Mapa legacy", "El mapa activo no usa PMTiles. El visor avanzado queda listo cuando actives uno del catálogo.");
      return;
    }

    hideEmpty();
    ensureProtocol();
    state.baseLayerGroups = baseLayerGroups(availableSourceLayers(config));
    state.overlayLayerGroups = overlayLayerGroups(config);
    renderControls();

    if (!state.map) {
      state.map = new maplibregl.Map({
        container: "mapCanvas",
        style: buildStyle(config),
        center: [config.preferences.last_center?.lon || config.mapa.centerLon, config.preferences.last_center?.lat || config.mapa.centerLat],
        zoom: config.preferences.last_zoom || config.mapa.zoomInicial,
        minZoom: config.mapa.minZoom,
        maxZoom: config.mapa.maxZoom + 2,
      });
      state.map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), "top-right");
      state.map.on("load", () => {
        applyVisibilityFromPreferences();
        bindOverlayClicks();
        updateMeasurement();
        syncEmojiMarkers();
        updateSketch();
        updateTelemetryPanel();
        refreshSatelliteState();
        statusEl.textContent = `Mapa ${config.mapa.name} listo`;
      });
      state.map.on("error", (event) => {
        const sourceId = event?.sourceId || event?.source?.id || "";
        if ((sourceId === "satellite" || String(event?.error?.message || "").toLowerCase().includes("satellite")) && !state.satelliteWarningShown) {
          state.satelliteWarningShown = true;
          statusEl.textContent = "La capa satelital no está disponible en este momento.";
        }
      });
      state.map.on("mousemove", (event) => {
        coordCursorEl.textContent = `Cursor: ${formatCoords(event.lngLat)}`;
      });
      state.map.on("moveend", () => {
        updateCenterHud();
        refreshSatelliteState();
        const center = state.map.getCenter();
        state.config.preferences.last_center = { lat: center.lat, lon: center.lng };
        state.config.preferences.last_zoom = state.map.getZoom();
        persistPreferences({ last_center: state.config.preferences.last_center, last_zoom: state.config.preferences.last_zoom });
      });
      state.map.on("click", (event) => {
        hideContextMenu();
        if (state.drawMode?.kind === "route") {
          addRouteVertex(event.lngLat);
          return;
        }
        if (state.drawMode?.kind === "polygon") {
          addPolygonVertex(event.lngLat);
          return;
        }
        const interactiveLayers = Object.values(state.overlayLayerGroups || {}).flat().filter((layerId) => state.map.getLayer(layerId));
        const features = interactiveLayers.length ? state.map.queryRenderedFeatures(event.point, { layers: interactiveLayers }) : [];
        if (!features.length) {
          clearFeatureSelection();
        }
        if (!state.config.preferences.measurement_enabled) {
          return;
        }
        state.measurePoints.push({ lng: event.lngLat.lng, lat: event.lngLat.lat });
        updateMeasurement();
      });
      state.map.on("contextmenu", (event) => {
        event.preventDefault();
        if (!state.config?.mapa) {
          return;
        }
        if (state.drawMode?.kind === "route") {
          showContextMenu(
            [
              { label: "Finalizar ruta", onClick: () => finishRouteDrawing() },
              { label: "Cancelar dibujo", onClick: () => cancelRouteDrawing() },
            ],
            menuScreenPoint(event.point),
            "Ruta en curso",
          );
          return;
        }
        if (state.drawMode?.kind === "polygon") {
          showContextMenu(
            [
              { label: "Finalizar polígono", onClick: () => finishPolygonDrawing(event.point) },
              { label: "Cancelar dibujo", onClick: () => cancelPolygonDrawing() },
            ],
            menuScreenPoint(event.point),
            "Polígono en curso",
          );
          return;
        }
        const interactiveLayers = Object.values(state.overlayLayerGroups || {}).flat();
        const features = interactiveLayers.length ? state.map.queryRenderedFeatures(event.point, { layers: interactiveLayers }) : [];
        const feature = features && features[0];
        if (feature) {
          showFeature(feature, event.lngLat);
          showFeatureContextMenu(feature, event.point);
          return;
        }
        showMapContextMenu(event.lngLat, event.point);
      });
    } else if (changedMap || force) {
      state.map.setStyle(buildStyle(config));
      state.map.once("styledata", () => {
        if (changedMap) {
          state.map.jumpTo({
            center: [config.mapa.centerLon, config.mapa.centerLat],
            zoom: config.mapa.zoomInicial,
          });
        }
        applyVisibilityFromPreferences();
        bindOverlayClicks();
        updateMeasurement();
        syncEmojiMarkers();
        updateSketch();
        refreshSatelliteState();
      });
    } else if (changedUpdate) {
      updateOverlaySources(config);
      syncEmojiMarkers();
      updateSketch();
      refreshSatelliteState();
    }

    state.currentMapId = config.mapa.id;
    updateCenterHud();
  } catch (error) {
    viewerModeEl.textContent = "Error";
    statusEl.textContent = String(error.message || error);
    showEmpty("Error de visor", "No se pudo cargar la configuración local del visor.");
  }
}

async function pollRuntime() {
  try {
    const config = await fetchJson("/runtime/runtime_config.json");
    const changedMap = (config.mapa && config.mapa.id) !== state.currentMapId;
    const changedUpdate = (config.updated_at || "") !== state.lastUpdatedAt;
    if (changedMap || changedUpdate) {
      await loadRuntime();
      return;
    }
    if (state.map && config.capas) {
      updateOverlaySources(config);
    }
    if (state.map) {
      refreshSatelliteState();
    }
  } catch (_error) {
    // ignore transient errors
  }
}

bindUI();
initTelemetrySensors();
updateSelectedFeatureActions();
loadRuntime();
window.setInterval(pollRuntime, 3000);
