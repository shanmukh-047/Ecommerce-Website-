import api, { setAccessToken, clearAccessToken } from '../lib/apiClient';

/**
 * Authentication & Customer Service
 */
export const authService = {
  /**
   * Log in retail or wholesale customer
   */
  async login(email, password, options = {}) {
    const data = await api.post('/auth/login/', { email, password }, options);
    if (data?.access_token) {
      setAccessToken(data.access_token);
    }
    return data;
  },

  /**
   * Register retail customer
   */
  async register(payload, options = {}) {
    const data = await api.post('/auth/register/', payload, options);
    if (data?.access_token) {
      setAccessToken(data.access_token);
    }
    return data;
  },

  /**
   * Register B2B Wholesale buyer
   */
  async registerWholesale(payload, options = {}) {
    const data = await api.post('/auth/register/wholesale/', payload, options);
    if (data?.access_token) {
      setAccessToken(data.access_token);
    }
    return data;
  },

  /**
   * Get current authenticated user profile
   */
  async getMe(options = {}) {
    return api.get('/auth/me/', options);
  },

  /**
   * Update profile (first_name, last_name, phone_number)
   */
  async updateMe(payload, options = {}) {
    return api.patch('/auth/me/', payload, options);
  },

  /**
   * Log out and invalidate session cookies
   */
  async logout(options = {}) {
    try {
      await api.post('/auth/logout/', {}, options);
    } catch {
      // Ignore network errors on logout
    } finally {
      clearAccessToken();
    }
  },

  /**
   * Customer saved addresses
   */
  async getAddresses(options = {}) {
    return api.get('/auth/addresses/', options);
  },

  async addAddress(addressData, options = {}) {
    return api.post('/auth/addresses/', addressData, options);
  },

  async updateAddress(addressId, addressData, options = {}) {
    return api.patch(`/auth/addresses/${addressId}/`, addressData, options);
  },

  async deleteAddress(addressId, options = {}) {
    return api.delete(`/auth/addresses/${addressId}/`, options);
  },

  /**
   * Request password reset email (forgot password)
   */
  async requestPasswordReset(email, options = {}) {
    return api.post('/auth/password-reset/', { email }, options);
  },

  /**
   * Confirm password reset with one-time token
   */
  async confirmPasswordReset(payload, options = {}) {
    return api.post('/auth/password-reset/confirm/', payload, options);
  },

  /**
   * Change password for authenticated user
   */
  async changePassword(payload, options = {}) {
    return api.post('/auth/change-password/', payload, options);
  },
};

export default authService;
