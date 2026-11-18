import {createApi} from './api.js';
import {createAlertsView} from './alerts.js';
import {createDashboardController, createDashboardView} from './dashboard.js';
import {createLocationView} from './location.js';
import {createMapView} from './map.js';
import {createTracking} from './tracking.js';
import {createEventLocation} from './event-location.js';

export function mountDashboard({root = globalThis.document, api = createApi(), leaflet = globalThis.L, clipboard = globalThis.navigator?.clipboard, timers = globalThis, search = globalThis.location?.search || ''} = {}) {
  const map = createMapView(root, leaflet);
  const eventLocation = createEventLocation({root, api, map, search});
  const controller = createDashboardController({
    api,
    view: createDashboardView(root),
    alerts: createAlertsView(root, {onSelect: item => eventLocation.select(item)}),
    location: createLocationView(root, map, {clipboard, timers}),
    tracking: createTracking(root, api, map),
    timers,
  });
  controller.start();
  void eventLocation.openLinked();
  return controller;
}

if (typeof document !== 'undefined') mountDashboard();
