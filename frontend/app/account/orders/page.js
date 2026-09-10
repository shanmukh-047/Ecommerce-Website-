'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  Package,
  Calendar,
  Clock,
  ArrowRight,
  ShieldCheck,
  ChevronRight,
  AlertCircle,
  Truck,
  RotateCcw,
} from 'lucide-react';
import RouteGuard from '../../../components/common/RouteGuard';
import orderService from '../../../services/orderService';
import Button from '../../../components/common/Button';
import Badge from '../../../components/common/Badge';
import Skeleton from '../../../components/common/Skeleton';
import EmptyState from '../../../components/common/EmptyState';
import ErrorState from '../../../components/common/ErrorState';

const STATUS_CONFIG = {
  PENDING_PAYMENT: {
    label: 'Payment Pending',
    variant: 'warning',
    bg: 'bg-amber-50 text-amber-800 border-amber-200',
  },
  CONFIRMED: {
    label: 'Confirmed',
    variant: 'saffron',
    bg: 'bg-saffron-50 text-saffron-800 border-saffron-200',
  },
  PROCESSING: {
    label: 'Milling & Processing',
    variant: 'saffron',
    bg: 'bg-blue-50 text-blue-800 border-blue-200',
  },
  SHIPPED: {
    label: 'Dispatched in Transit',
    variant: 'primary',
    bg: 'bg-purple-50 text-purple-800 border-purple-200',
  },
  DELIVERED: {
    label: 'Delivered',
    variant: 'success',
    bg: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  },
  CANCELLED: {
    label: 'Cancelled',
    variant: 'error',
    bg: 'bg-red-50 text-red-700 border-red-200',
  },
  FAILED: {
    label: 'Payment Failed',
    variant: 'error',
    bg: 'bg-red-50 text-red-700 border-red-200',
  },
  REFUNDED: {
    label: 'Refunded',
    variant: 'stone',
    bg: 'bg-stone-100 text-stone-700 border-stone-200',
  },
};

function OrdersContent() {
  const [orders, setOrders] = useState([]);
  const [pagination, setPagination] = useState({ count: 0, total_pages: 1, current_page: 1 });
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchOrders = useCallback(async (page = 1) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await orderService.getOrders(page);
      const list = res?.results || (Array.isArray(res) ? res : []);
      setOrders(list);
      setPagination({
        count: res?.count || list.length,
        total_pages: res?.total_pages || 1,
        current_page: page,
      });
    } catch (err) {
      console.error('Failed to load orders:', err);
      setError(err.message || 'Unable to retrieve your order history from the server.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders(currentPage);
  }, [fetchOrders, currentPage]);

  return (
    <div className="min-h-screen bg-spice-canvas pb-20 pt-4 sm:pt-6">
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="mb-4 flex items-center text-xs text-spice-stone">
          <Link href="/" className="hover:text-saffron-700 transition-colors">
            Home
          </Link>
          <ChevronRight className="mx-1.5 h-3.5 w-3.5 text-spice-muted" />
          <Link href="/account" className="hover:text-saffron-700 transition-colors">
            My Account
          </Link>
          <ChevronRight className="mx-1.5 h-3.5 w-3.5 text-spice-muted" />
          <span className="font-semibold text-spice-black">Order History</span>
        </nav>

        {/* Page Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-spice-borderSubtle pb-4 gap-2">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold font-display text-spice-black tracking-tight">
              My Orders &amp; Receipts
            </h1>
            <p className="mt-1 text-xs text-spice-stone">
              Track fulfillment, invoices, and delivery milestones from our Western Ghats facilities
            </p>
          </div>

          <Link href="/products">
            <Button variant="outline" size="sm" className="text-xs font-semibold self-start">
              Shop More Spices
            </Button>
          </Link>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, idx) => (
              <div key={idx} className="rounded-2xl border border-spice-border bg-white p-5 space-y-3">
                <div className="flex justify-between">
                  <Skeleton height="20px" width="160px" />
                  <Skeleton height="20px" width="90px" className="rounded-full" />
                </div>
                <Skeleton height="40px" className="w-full rounded-lg" />
                <div className="flex justify-between pt-2">
                  <Skeleton height="16px" width="100px" />
                  <Skeleton height="28px" width="120px" className="rounded-lg" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error State */}
        {!isLoading && error && (
          <ErrorState
            title="Could not load your orders"
            message={error}
            onRetry={() => fetchOrders(currentPage)}
            className="py-16"
          />
        )}

        {/* Empty Orders State */}
        {!isLoading && !error && orders.length === 0 && (
          <EmptyState
            icon={<Package className="h-10 w-10 stroke-[1.5] text-saffron-700" />}
            title="You have not placed any orders yet"
            description="Experience single-origin, stone-ground authentic spices harvested fresh from Kerala and Karnataka estates."
            action={
              <Link href="/products">
                <Button variant="primary" size="md" rightIcon={<ArrowRight className="h-4 w-4" />}>
                  Explore Spice Pantry
                </Button>
              </Link>
            }
            className="py-16 bg-white shadow-subtle border-spice-border"
          />
        )}

        {/* Orders List */}
        {!isLoading && !error && orders.length > 0 && (
          <div className="space-y-4">
            {orders.map((order) => {
              const statusCfg = STATUS_CONFIG[order.order_status] || {
                label: order.order_status,
                variant: 'stone',
                bg: 'bg-stone-100 text-stone-800 border-stone-200',
              };

              const formattedDate = order.created_at
                ? new Date(order.created_at).toLocaleDateString('en-IN', {
                    day: 'numeric',
                    month: 'short',
                    year: 'numeric',
                  })
                : 'Recent';

              const lines = order.lines || [];

              return (
                <div
                  key={order.id}
                  className="rounded-2xl border border-spice-border bg-white p-5 sm:p-6 shadow-subtle hover:border-saffron-500/40 transition-colors"
                >
                  {/* Order Top Bar */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-spice-borderSubtle pb-4 gap-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-sm sm:text-base font-bold text-spice-black tracking-wide">
                          #{order.order_number}
                        </span>
                        <span
                          className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${statusCfg.bg}`}
                        >
                          <span className="h-1.5 w-1.5 rounded-full bg-current" />
                          {statusCfg.label}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 text-xs text-spice-muted">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3.5 w-3.5" />
                          {formattedDate}
                        </span>
                        <span>•</span>
                        <span>
                          {order.total_quantity || lines.length} {order.total_quantity === 1 ? 'pack' : 'packs'}
                        </span>
                      </div>
                    </div>

                    <div className="text-left sm:text-right">
                      <span className="text-xs text-spice-muted block leading-none mb-1">Grand Total</span>
                      <span className="text-lg font-extrabold text-spice-black tabular-nums">
                        ₹{parseFloat(order.grand_total || 0).toFixed(2)}
                      </span>
                    </div>
                  </div>

                  {/* Order Items Preview */}
                  <div className="py-4 space-y-2">
                    {lines.slice(0, 3).map((line) => (
                      <div key={line.id} className="flex items-center justify-between text-xs text-spice-stone">
                        <div className="flex items-center gap-2 truncate min-w-0 pr-2">
                          <span className="h-1.5 w-1.5 rounded-full bg-saffron-600 shrink-0" />
                          <span className="font-medium text-spice-black truncate">{line.product_name}</span>
                          <span className="text-spice-muted shrink-0">
                            ({line.variant_name || `${line.weight_in_grams}g`}) × {line.quantity}
                          </span>
                        </div>
                        <span className="font-bold text-spice-black tabular-nums shrink-0">
                          ₹{parseFloat(line.line_subtotal || 0).toFixed(0)}
                        </span>
                      </div>
                    ))}

                    {lines.length > 3 && (
                      <p className="text-[11px] text-spice-muted italic pt-1">
                        + {lines.length - 3} more items in this order
                      </p>
                    )}
                  </div>

                  {/* Order Footer & CTAs */}
                  <div className="border-t border-spice-borderSubtle pt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="text-xs text-spice-stone truncate">
                      <span className="font-semibold text-spice-black">Destination: </span>
                      <span>
                        {order.shipping_city}, {order.shipping_state} ({order.shipping_pincode})
                      </span>
                    </div>

                    <Link href={`/account/orders/${order.id}`}>
                      <Button
                        variant="outline"
                        size="sm"
                        rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
                        className="w-full sm:w-auto text-xs font-semibold uppercase tracking-wider border-saffron-600"
                      >
                        View Order Details
                      </Button>
                    </Link>
                  </div>
                </div>
              );
            })}

            {/* Pagination Controls */}
            {pagination.total_pages > 1 && (
              <div className="mt-8 flex items-center justify-between border-t border-spice-borderSubtle pt-6">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <span className="text-xs text-spice-stone font-medium">
                  Page <strong className="text-spice-black">{currentPage}</strong> of{' '}
                  <strong className="text-spice-black">{pagination.total_pages}</strong>
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage >= pagination.total_pages}
                  onClick={() => setCurrentPage((p) => Math.min(pagination.total_pages, p + 1))}
                >
                  Next
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function OrdersPage() {
  return (
    <RouteGuard>
      <OrdersContent />
    </RouteGuard>
  );
}
