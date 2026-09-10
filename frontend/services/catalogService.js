import api from '../lib/apiClient';

/**
 * Catalog & Products Service
 */
export const catalogService = {
  /**
   * Fetch spice categories list
   */
  async getCategories(options = {}) {
    return api.get('/catalog/categories/', options);
  },

  /**
   * Fetch products list with optional filters and request options
   */
  async getProducts(params = {}, options = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.append(key, val);
      }
    });
    const queryString = query.toString();
    const endpoint = `/catalog/products/${queryString ? `?${queryString}` : ''}`;
    return api.get(endpoint, options);
  },

  /**
   * Search products by keyword with optional abort signal
   */
  async searchProducts(query, limit = 6, options = {}) {
    if (!query || !query.trim()) return { results: [] };
    return api.get(
      `/catalog/products/?search=${encodeURIComponent(query.trim())}&page_size=${limit}`,
      options
    );
  },

  /**
   * Fetch product detail by slug
   */
  async getProductBySlug(slug, options = {}) {
    return api.get(`/catalog/products/${slug}/`, options);
  },

  /**
   * Fetch featured products for homepage showcase
   */
  async getFeaturedProducts(params = {}, options = {}) {
    return this.getProducts({ featured: 'true', ...params }, options);
  },

  /**
   * Fetch bestseller products
   */
  async getBestsellerProducts(params = {}, options = {}) {
    return this.getProducts({ bestseller: 'true', ...params }, options);
  },
};

export default catalogService;
