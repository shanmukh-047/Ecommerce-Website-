import api from '../lib/apiClient';

/**
 * Payments Service
 * Communicates directly with Django payments endpoints (/api/v1/payments/).
 */
export const paymentService = {
  /**
   * Initiate payment for an order in PENDING_PAYMENT status.
   * Endpoint: POST /api/v1/payments/orders/<order_id>/initiate/
   * @param {string} orderId - UUID of the order
   * @param {object} options - Request options (signal, timeout)
   */
  async initiatePayment(orderId, options = {}) {
    const res = await api.post(`/payments/orders/${orderId}/initiate/`, {}, options);
    return res;
  },

  /**
   * Cryptographically verify HMAC-SHA256 signature returned by payment gateway.
   * Endpoint: POST /api/v1/payments/orders/<order_id>/verify/
   * @param {string} orderId - UUID of the order
   * @param {object} verifyData - { razorpay_order_id, razorpay_payment_id, razorpay_signature, payment_method }
   * @param {object} options - Request options
   */
  async verifyPayment(orderId, verifyData, options = {}) {
    const res = await api.post(`/payments/orders/${orderId}/verify/`, verifyData, options);
    return res?.payment || res;
  },

  /**
   * Retrieve payment status and attempt audit log for an order.
   * Endpoint: GET /api/v1/payments/orders/<order_id>/
   * @param {string} orderId - UUID of the order
   * @param {object} options - Request options
   */
  async getPaymentDetails(orderId, options = {}) {
    const res = await api.get(`/payments/orders/${orderId}/`, options);
    return res?.payment || res;
  },

  /**
   * Place Cash on Delivery (COD) order payment.
   * Creates payment record with status PENDING, confirms order, and reserves stock.
   * Endpoint: POST /api/v1/payments/orders/<order_id>/cod/
   * @param {string} orderId - UUID of the order
   * @param {object} options - Request options
   */
  async createCODPayment(orderId, options = {}) {
    const res = await api.post(`/payments/orders/${orderId}/cod/`, {}, options);
    return res?.payment || res;
  },

  /**
   * Staff: Mark Cash on Delivery (COD) payment as collected upon delivery.
   * Transitions payment status from PENDING to CAPTURED.
   * Endpoint: POST /api/v1/staff/payments/<payment_id>/mark-cod-collected/
   * @param {string} paymentId - UUID of the payment
   * @param {object} options - Request options
   */
  async markCODCollected(paymentId, options = {}) {
    const res = await api.post(`/staff/payments/${paymentId}/mark-cod-collected/`, {}, options);
    return res?.payment || res;
  },

  /**
   * @deprecated Historical manual UPI UTR submission. Retained for backward compatibility.
   * Endpoint: POST /api/v1/payments/orders/<order_id>/submit-utr/
   * @param {string} orderId - UUID of the order
   * @param {string} utrNumber - 12-digit bank/UPI reference
   * @param {File} screenshotFile - Optional screenshot file
   * @param {object} options - Request options
   */
  async submitUTR(orderId, utrNumber, screenshotFile = null, options = {}) {
    if (screenshotFile) {
      const formData = new FormData();
      formData.append('utr_number', utrNumber.trim());
      formData.append('screenshot', screenshotFile);
      const res = await api.post(`/payments/orders/${orderId}/submit-utr/`, formData, {
        ...options,
        headers: {
          ...(options.headers || {}),
          'Content-Type': 'multipart/form-data',
        },
      });
      return res?.payment || res;
    }

    const res = await api.post(
      `/payments/orders/${orderId}/submit-utr/`,
      { utr_number: utrNumber.trim() },
      options
    );
    return res?.payment || res;
  },

  /**
   * Staff: List payment transactions for admin dashboard.
   * Endpoint: GET /api/v1/staff/payments/
   */
  async adminListPayments(params = {}, options = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.status) query.append('status', params.status);
    if (params.gateway) query.append('gateway', params.gateway);
    if (params.search) query.append('search', params.search);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await api.get(`/staff/payments/${queryString}`, options);
    return res;
  },

  /**
   * Staff: Verify manual UPI payment after checking business bank account.
   * Endpoint: POST /api/v1/staff/payments/<payment_id>/verify/
   * @param {string} paymentId - UUID of the payment
   * @param {string} notes - Verification audit note
   */
  async adminVerifyPayment(paymentId, notes = '', options = {}) {
    const res = await api.post(
      `/staff/payments/${paymentId}/verify/`,
      { notes },
      options
    );
    return res?.payment || res;
  },

  /**
   * Staff: Reject manual UPI payment if UTR is invalid or funds not received.
   * Endpoint: POST /api/v1/staff/payments/<payment_id>/reject/
   * @param {string} paymentId - UUID of the payment
   * @param {string} reason - Rejection explanation
   */
  async adminRejectPayment(paymentId, reason, options = {}) {
    const res = await api.post(
      `/staff/payments/${paymentId}/reject/`,
      { reason },
      options
    );
    return res?.payment || res;
  },
};

export default paymentService;
