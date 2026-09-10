import api from '../lib/apiClient';

/**
 * Cart & Promotions Service
 * Interacts directly with Django cart endpoints.
 * Automatically handles guest cart cookies, JWT auth, and cart unwrapping.
 */
export const cartService = {
  /**
   * Fetch current active cart
   */
  async getCart(options = {}) {
    const res = await api.get('/cart/', options);
    return res?.cart || res;
  },

  /**
   * Add item variant to cart
   */
  async addItem(variantId, quantity = 1, options = {}) {
    const res = await api.post(
      '/cart/items/',
      {
        variant_id: variantId,
        quantity,
      },
      options
    );
    return res?.cart || res;
  },

  /**
   * Update item line quantity
   */
  async updateQuantity(itemId, quantity, options = {}) {
    const res = await api.patch(
      `/cart/items/${itemId}/`,
      {
        quantity,
      },
      options
    );
    return res?.cart || res;
  },

  /**
   * Remove item line from cart
   */
  async removeItem(itemId, options = {}) {
    const res = await api.delete(`/cart/items/${itemId}/`, options);
    return res?.cart || res;
  },

  /**
   * Clear all items from cart
   */
  async clearCart(options = {}) {
    const res = await api.delete('/cart/', options);
    return res?.cart || res;
  },

  /**
   * Apply promotional coupon code
   */
  async applyCoupon(code, options = {}) {
    const res = await api.post(
      '/cart/coupon/',
      {
        code,
      },
      options
    );
    return res?.cart || res;
  },

  /**
   * Remove active promotional coupon
   */
  async removeCoupon(options = {}) {
    const res = await api.delete('/cart/coupon/', options);
    return res?.cart || res;
  },
};

export default cartService;
