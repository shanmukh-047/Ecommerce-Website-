import api from '../lib/apiClient';

/**
 * Shipping & Shipment Tracking Service
 * Communicates directly with Django shipping endpoints (/api/v1/shipping/).
 */
export const shippingService = {
  /**
   * Retrieve all shipments and tracking milestones for an authenticated customer's order.
   * Endpoint: GET /api/v1/shipping/orders/<order_id>/tracking/
   * @param {string} orderId - UUID of the order
   * @param {object} options - Request options (signal, timeout, etc.)
   */
  async getOrderTracking(orderId, options = {}) {
    const res = await api.get(`/shipping/orders/${orderId}/tracking/`, options);
    return res;
  },

  /**
   * Retrieve full details of a specific consignment belonging to the authenticated customer.
   * Endpoint: GET /api/v1/shipping/<shipment_number>/
   * @param {string} shipmentNumber - Unique shipment reference (e.g. SHP-20260908-XXXX)
   * @param {object} options - Request options
   */
  async getShipmentDetail(shipmentNumber, options = {}) {
    const res = await api.get(`/shipping/${shipmentNumber}/`, options);
    return res?.shipment || res;
  },

  /**
   * Public milestone tracking endpoint for carrier tracking (SMS/Email/Guest).
   * Unauthenticated, strictly redacts customer PII and financials.
   * Endpoint: GET /api/v1/shipping/track/?awb=... or ?shipment=...
   * @param {string} query - AWB number or Shipment number
   * @param {object} options - Request options
   */
  async trackPublic(query, options = {}) {
    const trimmed = (query || '').trim();
    if (!trimmed) {
      throw new Error('Tracking number or AWB is required.');
    }

    // Attempt tracking by AWB first, fallback to shipment number
    const isAwbFormat = trimmed.toUpperCase().startsWith('BMP-AWB-') || trimmed.length > 8;
    const queryParam = isAwbFormat ? `awb=${encodeURIComponent(trimmed)}` : `shipment=${encodeURIComponent(trimmed)}`;

    try {
      const res = await api.get(`/shipping/track/?${queryParam}`, options);
      return res?.tracking || res;
    } catch {
      // If failed with one param, try the alternative
      const altParam = isAwbFormat ? `shipment=${encodeURIComponent(trimmed)}` : `awb=${encodeURIComponent(trimmed)}`;
      const fallbackRes = await api.get(`/shipping/track/?${altParam}`, options);
      return fallbackRes?.tracking || fallbackRes;
    }
  },
};

export default shippingService;
