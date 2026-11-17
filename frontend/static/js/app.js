import {createApi} from './api.js';
import {createAlertsView} from './alerts.js';
import {createDashboardController, createDashboardView} from './dashboard.js';
import {createLocationView} from './location.js';
import {createMapView} from './map.js';
import {createTracking} from './tracking.js';

export function mountDashboard({root = globalThis.document, api = createApi(), leaflet = globalThis.L, clipboard = globalThis.navigator?.clipboard, timers = globalThis} = {}) {
  const map = createMapView(root, leaflet);
  const controller = createDashboardController({
    api,
    view: createDashboardView(root),
    alerts: createAlertsView(root),
    location: createLocationView(root, map, {clipboard, timers}),
    tracking: createTracking(root, api, map),
    timers,
  });
  controller.start();
  return controller;
}

if (typeof document !== 'undefined') mountDashboard();
