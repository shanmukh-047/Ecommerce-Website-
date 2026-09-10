'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import cartService from '../services/cartService';
import { useToast } from '../components/common/Toast';

const CartContext = createContext(null);

export function useCart() {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
}

export function CartProvider({ children }) {
  const [cart, setCart] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [updatingItemId, setUpdatingItemId] = useState(null);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const { success, error: showError } = useToast();

  const openCart = useCallback(() => setIsCartOpen(true), []);
  const closeCart = useCallback(() => setIsCartOpen(false), []);
  const toggleCart = useCallback(() => setIsCartOpen((prev) => !prev), []);

  // Fetch authoritative cart state from backend
  const fetchCart = useCallback(async () => {
    try {
      const data = await cartService.getCart();
      if (data) {
        setCart(data?.cart || data);
      }
    } catch {
      // Cart might not exist yet for new visitor; initialize default empty cart structure
      setCart({
        items: [],
        items_subtotal: '0.00',
        discount_amount: '0.00',
        net_subtotal: '0.00',
        applied_coupon_code: null,
        validation_issues: [],
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCart();

    const handleAuthChanged = () => {
      fetchCart();
    };

    window.addEventListener('bharat:auth-changed', handleAuthChanged);
    return () => {
      window.removeEventListener('bharat:auth-changed', handleAuthChanged);
    };
  }, [fetchCart]);

  // Derived state directly from backend response
  const items = useMemo(() => cart?.items || [], [cart]);

  const itemCount = useMemo(() => {
    return items.reduce((total, item) => total + (Number(item.quantity) || 0), 0);
  }, [items]);

  const subtotal = useMemo(() => {
    return parseFloat(cart?.items_subtotal || '0') || 0;
  }, [cart]);

  const discountAmount = useMemo(() => {
    return parseFloat(cart?.discount_amount || '0') || 0;
  }, [cart]);

  const netSubtotal = useMemo(() => {
    return parseFloat(cart?.net_subtotal || '0') || 0;
  }, [cart]);

  const appliedCouponCode = cart?.applied_coupon_code || null;
  const validationIssues = useMemo(() => cart?.validation_issues || [], [cart]);

  // Map validation issues by item_id for fast lookup in line items
  const validationIssuesMap = useMemo(() => {
    const map = {};
    validationIssues.forEach((issue) => {
      if (issue?.item_id) {
        map[issue.item_id] = issue.code || 'ISSUE';
      }
    });
    return map;
  }, [validationIssues]);

  const hasValidationIssues = validationIssues.length > 0;

  /**
   * Add item variant to cart
   */
  const addToCart = async (variantId, quantity = 1, shouldOpenDrawer = true) => {
    setIsUpdating(true);
    try {
      const res = await cartService.addItem(variantId, quantity);
      const updatedCart = res?.cart || res;
      setCart(updatedCart);
      success('Item added to your basket', 'Added to Cart');
      if (shouldOpenDrawer) {
        setIsCartOpen(true);
      }
      return updatedCart;
    } catch (err) {
      showError(err.message || 'Could not add item to cart. Please check stock.', 'Stock Notice');
      throw err;
    } finally {
      setIsUpdating(false);
    }
  };

  /**
   * Update quantity of an item line
   */
  const updateQuantity = async (itemId, newQuantity) => {
    setIsUpdating(true);
    setUpdatingItemId(itemId);
    try {
      let res;
      if (newQuantity <= 0) {
        res = await cartService.removeItem(itemId);
      } else {
        res = await cartService.updateQuantity(itemId, newQuantity);
      }
      const updatedCart = res?.cart || res;
      setCart(updatedCart);
      return updatedCart;
    } catch (err) {
      showError(err.message || 'Failed to update item quantity', 'Cart Notice');
      throw err;
    } finally {
      setIsUpdating(false);
      setUpdatingItemId(null);
    }
  };

  /**
   * Remove item line completely
   */
  const removeItem = async (itemId) => {
    setIsUpdating(true);
    setUpdatingItemId(itemId);
    try {
      const res = await cartService.removeItem(itemId);
      const updatedCart = res?.cart || res;
      setCart(updatedCart);
      success('Item removed from basket', 'Cart Updated');
      return updatedCart;
    } catch (err) {
      showError(err.message || 'Failed to remove item', 'Cart Error');
      throw err;
    } finally {
      setIsUpdating(false);
      setUpdatingItemId(null);
    }
  };

  /**
   * Apply promotional coupon
   */
  const applyCoupon = async (code) => {
    setIsUpdating(true);
    try {
      const res = await cartService.applyCoupon(code);
      const updatedCart = res?.cart || res;
      setCart(updatedCart);
      success(`Promo code "${code.toUpperCase()}" applied successfully!`, 'Discount Applied');
      return updatedCart;
    } catch (err) {
      showError(err.message || 'Invalid or expired promo code', 'Coupon Error');
      throw err;
    } finally {
      setIsUpdating(false);
    }
  };

  /**
   * Remove promotional coupon
   */
  const removeCoupon = async () => {
    setIsUpdating(true);
    try {
      const res = await cartService.removeCoupon();
      const updatedCart = res?.cart || res;
      setCart(updatedCart);
      success('Promo code removed', 'Cart Updated');
      return updatedCart;
    } catch (err) {
      showError(err.message || 'Failed to remove promo code', 'Cart Error');
      throw err;
    } finally {
      setIsUpdating(false);
    }
  };

  /**
   * Clear all items from cart
   */
  const clearCart = async () => {
    setIsUpdating(true);
    try {
      await cartService.clearCart();
      setCart({
        items: [],
        items_subtotal: '0.00',
        discount_amount: '0.00',
        net_subtotal: '0.00',
        applied_coupon_code: null,
        validation_issues: [],
      });
      success('Basket cleared', 'Cart Updated');
    } catch (err) {
      showError(err.message || 'Failed to clear cart', 'Cart Error');
    } finally {
      setIsUpdating(false);
    }
  };

  const isItemUpdating = (itemId) => updatingItemId === itemId;

  const value = {
    cart,
    items,
    itemCount,
    subtotal,
    discountAmount,
    netSubtotal,
    appliedCouponCode,
    validationIssues,
    validationIssuesMap,
    hasValidationIssues,
    isLoading,
    isUpdating,
    updatingItemId,
    isItemUpdating,
    isCartOpen,
    openCart,
    closeCart,
    toggleCart,
    fetchCart,
    addToCart,
    updateQuantity,
    removeItem,
    applyCoupon,
    removeCoupon,
    clearCart,
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export default CartContext;
