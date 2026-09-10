'use client';

import React from 'react';
import { ToastProvider } from '../common/Toast';
import { AuthProvider } from '../../context/AuthContext';
import { CartProvider } from '../../context/CartContext';
import CartDrawer from '../cart/CartDrawer';

/**
 * Global Context Providers wrapper for Next.js App Router.
 * Supplies Toast, Auth, and Cart context across the application.
 */
export default function Providers({ children }) {
  return (
    <ToastProvider>
      <AuthProvider>
        <CartProvider>
          {children}
          <CartDrawer />
        </CartProvider>
      </AuthProvider>
    </ToastProvider>
  );
}
