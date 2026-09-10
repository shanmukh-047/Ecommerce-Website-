'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ShoppingBag,
  TrendingUp,
  CreditCard,
  AlertTriangle,
  Package,
  Users,
  Clock,
  ArrowUpRight,
  CheckCircle2,
  Boxes,
  RotateCcw,
} from 'lucide-react';
import AdminLayout from '../../components/admin/AdminLayout';
import Badge from '../../components/common/Badge';
import Button from '../../components/common/Button';
import adminService from '../../services/adminService';

export default function AdminDashboardPage() {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  const fetchDashboardData = async () => {
    setIsLoading(true);
    setErrorMessage('');
    try {
      const res = await adminService.getDashboard();
      setData(res);
    } catch (err) {
      console.error('Error loading dashboard metrics:', err);
      setErrorMessage('Unable to load administrative metrics. Please check network connection.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  return (
    <AdminLayout
      title="Store Operations Dashboard"
      subtitle="Real-time estate metrics, pending UPI verifications, and inventory health."
    >
      {errorMessage && (
        <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800 flex items-center justify-between">
          <span>{errorMessage}</span>
          <Button variant="outline" size="xs" onClick={fetchDashboardData} leftIcon={<RotateCcw className="h-3 w-3" />}>
            Retry
          </Button>
        </div>
      )}

      {/* KPI Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        {/* Card 1: Revenue */}
        <div className="bg-white p-5 rounded-2xl border border-stone-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-spice-stone uppercase tracking-wider">Captured Revenue</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black font-display text-spice-black tabular-nums">
              ₹{parseFloat(data?.stats?.revenue || data?.total_revenue || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
            <span className="text-[11px] text-stone-500 block mt-1">
              Verified online &amp; collected COD
            </span>
          </div>
        </div>

        {/* Card 2: Total Orders */}
        <div className="bg-white p-5 rounded-2xl border border-stone-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-spice-stone uppercase tracking-wider">Total Orders</span>
            <div className="w-8 h-8 rounded-xl bg-saffron-50 text-saffron-700 flex items-center justify-center">
              <ShoppingBag className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black font-display text-spice-black tabular-nums">
              {data?.stats?.total_orders ?? data?.total_orders ?? 0}
            </span>
            <span className="text-[11px] text-emerald-700 font-bold block mt-1">
              +{data?.stats?.orders_today ?? data?.orders_today ?? 0} today
            </span>
          </div>
        </div>

        {/* Card 3: Pending Orders */}
        <Link
          href="/admin/orders?status=CONFIRMED"
          className="bg-white p-5 rounded-2xl border border-stone-200 shadow-xs hover:border-saffron-400 transition-colors block group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-saffron-900 uppercase tracking-wider">To Fulfill</span>
            <div className="w-8 h-8 rounded-xl bg-saffron-50 text-saffron-700 flex items-center justify-center group-hover:scale-105 transition-transform">
              <Package className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black font-display text-saffron-950 tabular-nums">
              {data?.stats?.pending_orders ?? data?.pending_orders ?? 0}
            </span>
            <span className="text-[11px] text-saffron-800 font-semibold block mt-1 flex items-center gap-1">
              <span>Awaiting warehouse pack</span>
              <ArrowUpRight className="h-3 w-3" />
            </span>
          </div>
        </Link>

        {/* Card 4: Pending COD Collections */}
        <Link
          href="/admin/payments?gateway=COD"
          className="bg-white p-5 rounded-2xl border border-stone-200 shadow-xs hover:border-amber-400 transition-colors block group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-amber-900 uppercase tracking-wider">Pending COD</span>
            <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center group-hover:scale-105 transition-transform">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black font-display text-amber-950 tabular-nums">
              {data?.stats?.pending_cod_payments ?? 0}
            </span>
            <span className="text-[11px] text-amber-800 font-semibold block mt-1 flex items-center gap-1">
              <span>Due on courier delivery</span>
              <ArrowUpRight className="h-3 w-3" />
            </span>
          </div>
        </Link>

        {/* Card 5: Low Stock Alert */}
        <Link
          href="/admin/inventory?low_stock=true"
          className="bg-white p-5 rounded-2xl border border-stone-200 shadow-xs hover:border-red-400 transition-colors block group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-red-900 uppercase tracking-wider">Low Stock SKUs</span>
            <div className="w-8 h-8 rounded-xl bg-red-50 text-red-600 flex items-center justify-center group-hover:scale-105 transition-transform">
              <AlertTriangle className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black font-display text-red-950 tabular-nums">
              {data?.stats?.low_stock_products ?? data?.low_stock_products ?? 0}
            </span>
            <span className="text-[11px] text-red-700 font-semibold block mt-1 flex items-center gap-1">
              <span>Replenish reorder level</span>
              <ArrowUpRight className="h-3 w-3" />
            </span>
          </div>
        </Link>
      </div>

      {/* Secondary Metrics & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Quick Actions Panel */}
        <div className="bg-spice-canvas/80 p-6 rounded-2xl border border-spice-border">
          <h2 className="text-sm font-bold font-display text-spice-black uppercase tracking-wider mb-4">
            Quick Operations
          </h2>
          <div className="space-y-2.5">
            <Link
              href="/admin/payments"
              className="flex items-center justify-between p-3 rounded-xl bg-white border border-stone-200 hover:border-saffron-500 hover:shadow-xs transition-all text-xs font-bold text-spice-black"
            >
              <div className="flex items-center gap-2.5">
                <CreditCard className="h-4 w-4 text-saffron-600" />
                <span>Payment Transactions &amp; COD Collections</span>
              </div>
              <span className="bg-amber-100 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded-full">
                {data?.stats?.pending_cod_payments ?? 0} COD
              </span>
            </Link>

            <Link
              href="/admin/orders"
              className="flex items-center justify-between p-3 rounded-xl bg-white border border-stone-200 hover:border-saffron-500 hover:shadow-xs transition-all text-xs font-bold text-spice-black"
            >
              <div className="flex items-center gap-2.5">
                <ShoppingBag className="h-4 w-4 text-saffron-700" />
                <span>Manage Customer Orders</span>
              </div>
              <span className="text-stone-400 text-xs">&rarr;</span>
            </Link>

            <Link
              href="/admin/products"
              className="flex items-center justify-between p-3 rounded-xl bg-white border border-stone-200 hover:border-saffron-500 hover:shadow-xs transition-all text-xs font-bold text-spice-black"
            >
              <div className="flex items-center gap-2.5">
                <Package className="h-4 w-4 text-cardamom-700" />
                <span>Manage Spices Catalog</span>
              </div>
              <span className="text-stone-400 text-xs">&rarr;</span>
            </Link>

            <Link
              href="/admin/inventory"
              className="flex items-center justify-between p-3 rounded-xl bg-white border border-stone-200 hover:border-saffron-500 hover:shadow-xs transition-all text-xs font-bold text-spice-black"
            >
              <div className="flex items-center gap-2.5">
                <Boxes className="h-4 w-4 text-stone-700" />
                <span>Adjust Inventory Stock</span>
              </div>
              <span className="text-stone-400 text-xs">&rarr;</span>
            </Link>
          </div>
        </div>

        {/* Store Catalog Snapshot */}
        <div className="bg-white p-6 rounded-2xl border border-stone-200">
          <h2 className="text-sm font-bold font-display text-spice-black uppercase tracking-wider mb-4">
            Catalog &amp; Customers
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3.5 rounded-xl bg-stone-50 border border-stone-100">
              <span className="text-[11px] font-semibold text-stone-500 block">Active Products</span>
              <span className="text-xl font-bold font-display text-spice-black mt-1 block">
                {data?.stats?.total_products ?? data?.total_products ?? 0}
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-stone-50 border border-stone-100">
              <span className="text-[11px] font-semibold text-stone-500 block">Registered Customers</span>
              <span className="text-xl font-bold font-display text-spice-black mt-1 block">
                {data?.stats?.total_customers ?? data?.total_customers ?? 0}
              </span>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-stone-100 text-xs text-spice-stone">
            All spices stored in cold storage warehouse under Central FSSAI license.
          </div>
        </div>

        {/* System & Payment Architecture Notice */}
        <div className="bg-white p-6 rounded-2xl border border-stone-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              <h2 className="text-sm font-bold font-display text-spice-black uppercase tracking-wider">
                Payment Gateways Active
              </h2>
            </div>
            <p className="text-xs text-spice-stone leading-relaxed">
              Razorpay Online Gateway (supporting UPI apps, credit/debit cards, net banking) and Cash on Delivery (COD) are operational. Online orders are captured automatically with cryptographic HMAC signature verification.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-stone-100 flex items-center justify-between text-[11px] text-stone-500">
            <span>Gateways: Razorpay &amp; COD</span>
            <Badge variant="emerald" size="xs">Live</Badge>
          </div>
        </div>
      </div>

      {/* Recent Orders Table */}
      <div className="bg-white rounded-2xl border border-stone-200 shadow-xs mb-8 overflow-hidden">
        <div className="p-5 border-b border-stone-100 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold font-display text-spice-black uppercase tracking-wider">
              Recent Customer Orders
            </h2>
            <p className="text-xs text-stone-500 mt-0.5">Live feed of orders placed by customers.</p>
          </div>
          <Link
            href="/admin/orders"
            className="text-xs font-bold text-saffron-700 hover:text-saffron-800 transition-colors"
          >
            View All Orders &rarr;
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-600 font-bold border-b border-stone-200 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Order #</th>
                <th className="py-3 px-4">Customer</th>
                <th className="py-3 px-4">Amount</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Date</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {!data?.recent_orders || data.recent_orders.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-stone-400">
                    No recent orders found.
                  </td>
                </tr>
              ) : (
                data.recent_orders.map((ord) => (
                  <tr key={ord.id} className="hover:bg-stone-50/80 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-spice-black">
                      #{ord.order_number}
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-semibold block text-spice-black">
                        {ord.shipping_recipient_name || 'Customer'}
                      </span>
                      <span className="text-[11px] text-stone-500">{ord.user_email}</span>
                    </td>
                    <td className="py-3 px-4 font-bold text-spice-black tabular-nums">
                      ₹{parseFloat(ord.grand_total || 0).toFixed(2)}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          ord.order_status === 'CONFIRMED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : ord.order_status === 'PENDING_PAYMENT'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-stone-100 text-stone-700'
                        }`}
                      >
                        {ord.order_status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-stone-500">
                      {new Date(ord.created_at).toLocaleDateString('en-IN', {
                        day: 'numeric',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        href={`/admin/orders?order_id=${ord.id}`}
                        className="text-saffron-700 font-bold hover:underline"
                      >
                        Details
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Payments Table */}
      <div className="bg-white rounded-2xl border border-stone-200 shadow-xs mb-8 overflow-hidden">
        <div className="p-5 border-b border-stone-100 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold font-display text-spice-black uppercase tracking-wider">
              Recent Payment Transactions
            </h2>
            <p className="text-xs text-stone-500 mt-0.5">Online gateway captures and COD order settlements.</p>
          </div>
          <Link
            href="/admin/payments"
            className="text-xs font-bold text-saffron-700 hover:text-saffron-800 transition-colors"
          >
            Manage All Payments &rarr;
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-600 font-bold border-b border-stone-200 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Payment #</th>
                <th className="py-3 px-4">Order Reference</th>
                <th className="py-3 px-4">Method &amp; Gateway</th>
                <th className="py-3 px-4">Amount</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Date</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {!data?.recent_payments || data.recent_payments.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-stone-400">
                    No recent payment transactions found.
                  </td>
                </tr>
              ) : (
                data.recent_payments.map((p) => (
                  <tr key={p.id} className="hover:bg-stone-50/80 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-spice-black">
                      {p.payment_number}
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-mono font-bold text-spice-black block">
                        #{p.order_number || p.order}
                      </span>
                      <span className="text-[11px] text-stone-500">{p.user_email}</span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-semibold text-spice-black block">
                        {p.gateway === 'COD'
                          ? 'Cash on Delivery'
                          : p.gateway === 'RAZORPAY'
                          ? 'Razorpay Online'
                          : p.gateway === 'PHONEPE_QR'
                          ? 'Legacy UPI QR'
                          : p.gateway}
                      </span>
                      <span className="text-[10px] text-stone-400 font-mono">
                        {p.gateway_payment_id || p.utr_number || 'Direct'}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-bold text-spice-black tabular-nums">
                      ₹{parseFloat(p.amount || 0).toFixed(2)}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          p.status === 'CAPTURED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : p.status === 'PENDING'
                            ? 'bg-amber-100 text-amber-800'
                            : p.status === 'PENDING_VERIFICATION'
                            ? 'bg-orange-100 text-orange-800'
                            : p.status === 'FAILED'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-stone-100 text-stone-700'
                        }`}
                      >
                        {p.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-stone-500">
                      {new Date(p.created_at).toLocaleDateString('en-IN', {
                        day: 'numeric',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        href="/admin/payments"
                        className="text-saffron-700 font-bold hover:underline"
                      >
                        Manage
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AdminLayout>
  );
}
