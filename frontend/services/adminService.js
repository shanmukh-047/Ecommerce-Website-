import api from '../lib/apiClient';

/**
 * Admin / Staff Service
 * Dedicated client for administration portal and store management APIs.
 */
export const adminService = {
  // --- Dashboard Metrics ---
  async getDashboard(options = {}) {
    const res = await api.get('/staff/dashboard/', options);
    return res?.data || res;
  },

  // --- Catalog / Product Management ---
  async getProducts(params = {}, options = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.category) query.append('category', params.category);
    if (params.search) query.append('search', params.search);

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await api.get(`/staff/catalog/products/${qs}`, options);
    return res;
  },

  async getProduct(productId, options = {}) {
    const res = await api.get(`/staff/catalog/products/${productId}/`, options);
    return res?.product || res?.data?.product || res;
  },

  async createProduct(productData, options = {}) {
    const res = await api.post('/staff/catalog/products/', productData, options);
    return res?.product || res?.data?.product || res;
  },

  async updateProduct(productId, patchData, options = {}) {
    const res = await api.patch(`/staff/catalog/products/${productId}/`, patchData, options);
    return res?.product || res?.data?.product || res;
  },

  async deleteProduct(productId, options = {}) {
    const res = await api.delete(`/staff/catalog/products/${productId}/`, options);
    return res;
  },

  async uploadProductImage(productId, file, isPrimary = false, altText = '', options = {}) {
    const formData = new FormData();
    formData.append('image', file);
    if (isPrimary) formData.append('is_primary', 'true');
    if (altText) formData.append('alt_text', altText);

    const res = await api.post(`/staff/catalog/products/${productId}/images/`, formData, {
      ...options,
      headers: {
        ...(options.headers || {}),
        'Content-Type': 'multipart/form-data',
      },
    });
    return res?.image || res?.data?.image || res;
  },

  async getCategories(options = {}) {
    const res = await api.get('/staff/catalog/categories/', options);
    return res?.categories || res?.data?.categories || res;
  },

  // --- Orders Management ---
  async getOrders(params = {}, options = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.status) query.append('status', params.status);
    if (params.payment_status) query.append('payment_status', params.payment_status);
    if (params.gateway) query.append('gateway', params.gateway);
    if (params.search) query.append('search', params.search);
    if (params.is_wholesale !== undefined) query.append('is_wholesale', params.is_wholesale);

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await api.get(`/staff/orders/${qs}`, options);
    return res;
  },

  async getOrderDetail(orderId, options = {}) {
    const res = await api.get(`/staff/orders/${orderId}/`, options);
    return res?.order || res?.data?.order || res;
  },

  async updateOrderStatus(orderId, newStatus, notes = '', options = {}) {
    const res = await api.post(
      `/staff/orders/${orderId}/status/`,
      { status: newStatus, notes },
      options
    );
    return res?.order || res?.data?.order || res;
  },

  // --- Payments Verification Management ---
  async getPayments(params = {}, options = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.status) query.append('status', params.status);
    if (params.gateway) query.append('gateway', params.gateway);
    if (params.search) query.append('search', params.search);

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await api.get(`/staff/payments/${qs}`, options);
    return res;
  },

  async getPayment(paymentId, options = {}) {
    const res = await api.get(`/staff/payments/${paymentId}/`, options);
    return res?.payment || res?.data?.payment || res;
  },

  async verifyPayment(paymentId, notes = '', options = {}) {
    const res = await api.post(
      `/staff/payments/${paymentId}/verify/`,
      { notes },
      options
    );
    return res?.payment || res?.data?.payment || res;
  },

  async rejectPayment(paymentId, reason, options = {}) {
    const res = await api.post(
      `/staff/payments/${paymentId}/reject/`,
      { reason },
      options
    );
    return res?.payment || res?.data?.payment || res;
  },

  async markCODCollected(paymentId, options = {}) {
    const res = await api.post(
      `/staff/payments/${paymentId}/mark-cod-collected/`,
      {},
      options
    );
    return res?.payment || res?.data?.payment || res;
  },

  // --- Inventory Management ---
  async getInventory(params = {}, options = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.search) query.append('search', params.search);
    if (params.low_stock) query.append('low_stock', 'true');

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await api.get(`/staff/inventory/${qs}`, options);
    return res;
  },

  async getInventoryItem(stockItemId, options = {}) {
    const res = await api.get(`/staff/inventory/${stockItemId}/`, options);
    return res?.stock_item || res?.data?.stock_item || res;
  },

  async updateStock(stockItemId, quantityOnHand, reorderLevel = 10, options = {}) {
    const res = await api.patch(
      `/staff/inventory/${stockItemId}/`,
      {
        quantity_on_hand: quantityOnHand,
        reorder_level: reorderLevel,
      },
      options
    );
    return res?.stock_item || res?.data?.stock_item || res;
  },
};

export default adminService;
