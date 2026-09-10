import api from '../lib/apiClient';

/**
 * Orders & Checkout Service
 * Communicates directly with Django orders endpoints (/api/v1/orders/).
 */
export const orderService = {
  /**
   * Execute atomic checkout from active cart
   * @param {string} shippingAddressId - UUID of customer's saved address
   * @param {string} customerNotes - Optional special instructions
   * @param {object} options - Request options (signal, timeout, etc.)
   */
  async checkout(shippingAddressId, customerNotes = '', options = {}) {
    const res = await api.post(
      '/orders/checkout/',
      {
        shipping_address_id: shippingAddressId,
        customer_notes: customerNotes,
      },
      options
    );
    return res?.order || res;
  },

  /**
   * Fetch authenticated customer's order history
   * @param {number} page - Page number for pagination
   * @param {object} options - Request options (signal, timeout, etc.)
   */
  async getOrders(page = 1, options = {}) {
    const res = await api.get(`/orders/?page=${page}`, options);
    return res;
  },

  /**
   * Retrieve full details of an order by ID
   * @param {string} orderId - UUID of the order
   * @param {object} options - Request options (signal, timeout, etc.)
   */
  async getOrderById(orderId, options = {}) {
    const res = await api.get(`/orders/${orderId}/`, options);
    return res?.order || res;
  },

  /**
   * Cancel an order in PENDING_PAYMENT status
   * @param {string} orderId - UUID of the order
   * @param {string} reason - Cancellation reason
   * @param {object} options - Request options (signal, timeout, etc.)
   */
  async cancelOrder(orderId, reason = 'Cancelled by customer.', options = {}) {
    const res = await api.post(`/orders/${orderId}/cancel/`, { reason }, options);
    return res?.order || res;
  },
};

export default orderService;
