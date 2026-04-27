import axios from 'axios'

const API_BASE = 'http://localhost:8000'

const api = axios.create({ baseURL: API_BASE, timeout: 15000 })

export const shipmentService = {
  getAll:   () => api.get('/shipments/').then(r => r.data),
  getById:  (id) => api.get(`/shipments/${id}`).then(r => r.data),
  getStats: () => api.get('/shipments/stats/summary').then(r => r.data),
}

export const routingService = {
  getRoute:       (id, opt = 'balanced') => api.get(`/routes/${id}?optimize_for=${opt}`).then(r => r.data),
  optimizeRoute:  (sid, opt = 'balanced') => api.post('/routes/optimize', { shipment_id: sid, optimize_for: opt }).then(r => r.data),
  triggerReroute: (sid, opt = 'balanced') => api.post('/decision/reroute', { shipment_id: sid, optimize_for: opt }).then(r => r.data),
  explainRoute:   (sid, opt = 'balanced') => api.post('/ai/explain-route', { shipment_id: sid, optimize_for: opt }).then(r => r.data),
  getLiveConditions: () => api.get('/routes/conditions/live').then(r => r.data),
}

// Phase 4
export const phase4Service = {
  getEvents:          () => api.get('/simulate/events').then(r => r.data),
  simulate:           (payload) => api.post('/simulate', payload).then(r => r.data),
  analyzeCascade:     (payload) => api.post('/cascade/analyze', payload).then(r => r.data),
  getDependencyGraph: () => api.get('/cascade/dependency-graph').then(r => r.data),
  explainImpact:      (simResult) => api.post('/ai/explain-impact', { simulation_result: simResult }).then(r => r.data),
  ask:                (question, context = null) => api.post('/ai/ask', { question, context }).then(r => r.data),
}

export default api
