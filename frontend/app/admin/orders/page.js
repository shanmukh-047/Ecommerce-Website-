'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  ShoppingBag,
  Search,
  Truck,
  CheckCircle2,
  Clock,
  Eye,
  ArrowRight,
  Filter,
  User,
  MapPin,
  Calendar,
} from 'lucide-react';
import AdminLayout from '../../../components/admin/AdminLayout';
import Button from '../../../components/common/Button';
import Badge from '../../../components/common/Badge';
import Modal from '../../../components/common/Modal';
import adminService from '../../../services/adminService';

const STATUS_TRANSITIONS = {
  PENDING_PAYMENT: ['CONFIRMED', 'CANCELLED'],
  CONFIRMED: ['PROCESSING', 'CANCELLED'],
  PROCESSING: ['SHIPPED', 'CANCELLED'],
  SHIPPED: ['DELIVERED'],
  DELIVERED: [],
  CANCELLED: [],
};

function AdminOrdersContent() {
  const searchParams = useSearchParams();
  const initialOrderId = searchParams.get('order_id');

  const [orders, setOrders] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [paymentStatusFilter, setPaymentStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // Selected Order Detail Modal
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [transitionNotes, setTransitionNotes] = useState('');

  const loadOrders = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage('');
    try {
      const res = await adminService.getOrders({
        status: statusFilter === 'ALL' ? '' : statusFilter,
        payment_status: paymentStatusFilter === 'ALL' ? '' : paymentStatusFilter,
        search: searchQuery.trim(),
      });
      const orderList = res?.results || (Array.isArray(res) ? res : []);
      setOrders(orderList);

      // If URL had order_id, auto-select it
      if (initialOrderId && !selectedOrder) {
        const found = orderList.find((o) => o.id === initialOrderId);
        if (found) {
          setSelectedOrder(found);
          setIsDetailModalOpen(true);
        }
      }
    } catch (err) {
      console.error('Error fetching orders:', err);
      setErrorMessage('Unable to load orders. Please retry.');
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, paymentStatusFilter, searchQuery, initialOrderId, selectedOrder]);

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  const handleTransitionStatus = async (toStatus) => {
    if (!selectedOrder) return;
    setIsUpdatingStatus(true);
    try {
      const updated = await adminService.updateOrderStatus(
        selectedOrder.id,
        toStatus,
        transitionNotes.trim()
      );
      setSelectedOrder(updated);
      setTransitionNotes('');
      loadOrders();
    } catch (err) {
      alert(err?.message || 'Failed to update order status.');
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  return (
    <AdminLayout
      title="Customer Orders &amp; Fulfillment"
      subtitle="Track processing, milling queue, and courier dispatch across Indian states."
    >
      {/* Search and Filters */}
      <div className="bg-white p-4 rounded-2xl border border-stone-200 shadow-xs mb-6 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Status Tabs */}
          <div className="flex flex-wrap items-center gap-1.5 p-1 bg-stone-100 rounded-xl">
            <span className="text-[11px] font-bold text-stone-500 uppercase px-2">Order Status:</span>
            {[
              { id: 'ALL', label: 'All Orders' },
              { id: 'PENDING_PAYMENT', label: 'Pending Payment' },
              { id: 'CONFIRMED', label: 'Confirmed' },
              { id: 'PROCESSING', label: 'Processing' },
              { id: 'SHIPPED', label: 'Shipped' },
              { id: 'DELIVERED', label: 'Delivered' },
              { id: 'CANCELLED', label: 'Cancelled' },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setStatusFilter(tab.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  statusFilter === tab.id
                    ? 'bg-white text-saffron-700 shadow-xs'
                    : 'text-stone-600 hover:text-spice-black'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Search box */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              loadOrders();
            }}
            className="relative min-w-[240px]"
          >
            <Search className="h-4 w-4 text-stone-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search order #, customer..."
              className="w-full pl-9 pr-3 py-2 rounded-xl border border-stone-300 text-xs text-spice-black placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-saffron-500"
            />
          </form>
        </div>

        {/* Payment Status Filter Subtabs */}
        <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-stone-100">
          <span className="text-[11px] font-bold text-stone-500 uppercase px-2">Payment Status:</span>
          {[
            { id: 'ALL', label: 'All Payments' },
            { id: 'CAPTURED', label: 'Paid (Captured)' },
            { id: 'PENDING', label: 'Pending (COD / Unpaid)' },
            { id: 'FAILED', label: 'Failed' },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setPaymentStatusFilter(tab.id)}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                paymentStatusFilter === tab.id
                  ? 'bg-stone-800 text-white shadow-2xs'
                  : 'text-stone-500 hover:text-spice-black hover:bg-stone-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Orders List Table */}
      <div className="bg-white rounded-2xl border border-stone-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-600 font-bold border-b border-stone-200 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Order Number</th>
                <th className="py-3 px-4">Customer Details</th>
                <th className="py-3 px-4">Items</th>
                <th className="py-3 px-4">Grand Total</th>
                <th className="py-3 px-4">Payment</th>
                <th className="py-3 px-4">Fulfillment Status</th>
                <th className="py-3 px-4">Placed Date</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-stone-400">
                    <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-saffron-600 border-t-transparent" />
                    <p className="text-xs text-stone-500 mt-2">Loading customer orders...</p>
                  </td>
                </tr>
              ) : orders.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-stone-400">
                    No orders matching filter.
                  </td>
                </tr>
              ) : (
                orders.map((ord) => (
                  <tr key={ord.id} className="hover:bg-stone-50/80 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-spice-black">
                      #{ord.order_number}
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-bold text-spice-black block">
                        {ord.shipping_recipient_name || 'Customer'}
                      </span>
                      <span className="text-[11px] text-stone-500">
                        {ord.user_email || ord.shipping_phone_number}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-stone-600 font-medium">
                      {ord.lines?.length || 1} items
                    </td>
                    <td className="py-3 px-4 font-bold text-spice-black tabular-nums">
                      ₹{parseFloat(ord.grand_total || 0).toFixed(2)}
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-semibold text-spice-black block">
                        {ord.payment_gateway === 'COD'
                          ? 'Cash on Delivery'
                          : ord.payment_gateway === 'RAZORPAY'
                          ? 'Razorpay'
                          : ord.payment_gateway || 'Direct'}
                      </span>
                      <span
                        className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          ord.payment_status === 'CAPTURED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : ord.payment_status === 'PENDING'
                            ? 'bg-amber-100 text-amber-800'
                            : ord.payment_status === 'FAILED'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-stone-100 text-stone-600'
                        }`}
                      >
                        {ord.payment_status || (ord.order_status === 'CONFIRMED' ? 'CONFIRMED' : 'PENDING')}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          ord.order_status === 'CONFIRMED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : ord.order_status === 'PENDING_PAYMENT'
                            ? 'bg-amber-100 text-amber-800'
                            : ord.order_status === 'PROCESSING'
                            ? 'bg-blue-100 text-blue-800'
                            : ord.order_status === 'SHIPPED'
                            ? 'bg-purple-100 text-purple-800'
                            : ord.order_status === 'DELIVERED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-stone-100 text-stone-700'
                        }`}
                      >
                        {ord.order_status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-stone-500 text-[11px]">
                      {new Date(ord.created_at).toLocaleDateString('en-IN', {
                        day: 'numeric',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Button
                        variant="outline-stone"
                        size="xs"
                        onClick={() => {
                          setSelectedOrder(ord);
                          setIsDetailModalOpen(true);
                        }}
                        leftIcon={<Eye className="h-3 w-3" />}
                      >
                        Manage
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ORDER DETAILS & TRANSITION MODAL */}
      <Modal
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        title={`Order #${selectedOrder?.order_number || ''}`}
        description={`Status: ${selectedOrder?.order_status || ''}`}
        size="lg"
      >
        {selectedOrder && (
          <div className="space-y-4 py-2 text-xs">
            {/* Status Transition Action Bar */}
            <div className="p-4 rounded-xl bg-spice-canvas border border-spice-border">
              <span className="font-bold text-spice-black block mb-2">
                Order Status Workflow
              </span>
              <div className="flex flex-wrap items-center gap-2">
                {(STATUS_TRANSITIONS[selectedOrder.order_status] || []).map((targetStatus) => (
                  <Button
                    key={targetStatus}
                    variant={targetStatus === 'CANCELLED' ? 'danger' : 'primary'}
                    size="xs"
                    isLoading={isUpdatingStatus}
                    onClick={() => handleTransitionStatus(targetStatus)}
                  >
                    Transition to {targetStatus}
                  </Button>
                ))}
                {(STATUS_TRANSITIONS[selectedOrder.order_status] || []).length === 0 && (
                  <span className="text-stone-500 text-[11px]">
                    No further status transitions available for this order state.
                  </span>
                )}
              </div>
            </div>

            {/* Customer, Shipping & Payment 3-Card Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-3.5 rounded-xl bg-stone-50 border border-stone-200">
                <span className="font-bold text-spice-black block mb-1">Customer Details</span>
                <p className="text-stone-700 font-semibold">{selectedOrder.shipping_recipient_name}</p>
                <p className="text-stone-500">{selectedOrder.user_email}</p>
                <p className="text-stone-500">{selectedOrder.shipping_phone_number}</p>
              </div>

              <div className="p-3.5 rounded-xl bg-stone-50 border border-stone-200">
                <span className="font-bold text-spice-black block mb-1">Delivery Destination</span>
                <p className="text-stone-700">
                  {selectedOrder.shipping_address_line_1 || selectedOrder.shipping_address_line1}
                  {selectedOrder.shipping_address_line_2 && `, ${selectedOrder.shipping_address_line_2}`}
                </p>
                <p className="text-stone-500">
                  {selectedOrder.shipping_city}, {selectedOrder.shipping_state} -{' '}
                  <span className="font-mono font-bold text-spice-black">
                    {selectedOrder.shipping_pincode || selectedOrder.shipping_postal_code}
                  </span>
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-stone-50 border border-stone-200">
                <span className="font-bold text-spice-black block mb-1">Payment Method &amp; State</span>
                <p className="text-stone-700 font-semibold">
                  {selectedOrder.payment_gateway === 'COD'
                    ? 'Cash on Delivery'
                    : selectedOrder.payment_gateway === 'RAZORPAY'
                    ? 'Razorpay Online'
                    : selectedOrder.payment_gateway || 'Direct'}
                </p>
                <div className="mt-1 flex items-center gap-1.5">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      selectedOrder.payment_status === 'CAPTURED'
                        ? 'bg-emerald-100 text-emerald-800'
                        : selectedOrder.payment_status === 'PENDING'
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-stone-100 text-stone-700'
                    }`}
                  >
                    {selectedOrder.payment_status || (selectedOrder.order_status === 'CONFIRMED' ? 'CONFIRMED' : 'PENDING')}
                  </span>
                </div>
              </div>
            </div>

            {/* Line Items */}
            <div className="border border-stone-200 rounded-xl overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-stone-50 font-bold border-b border-stone-200 text-[11px]">
                  <tr>
                    <th className="py-2.5 px-3">Item</th>
                    <th className="py-2.5 px-3">SKU</th>
                    <th className="py-2.5 px-3">Qty</th>
                    <th className="py-2.5 px-3 text-right">Price</th>
                    <th className="py-2.5 px-3 text-right">Subtotal</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {(selectedOrder.lines || []).map((line) => (
                    <tr key={line.id}>
                      <td className="py-2.5 px-3 font-semibold text-spice-black">
                        {line.product_name} ({line.variant_name})
                      </td>
                      <td className="py-2.5 px-3 font-mono text-[11px] text-stone-500">
                        {line.sku}
                      </td>
                      <td className="py-2.5 px-3 tabular-nums">{line.quantity}</td>
                      <td className="py-2.5 px-3 text-right tabular-nums">
                        ₹{parseFloat(line.unit_price || 0).toFixed(2)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-spice-black tabular-nums">
                        ₹{parseFloat(line.line_subtotal || 0).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-stone-50 font-bold border-t border-stone-200">
                  <tr>
                    <td colSpan={4} className="py-2.5 px-3 text-right">Grand Total:</td>
                    <td className="py-2.5 px-3 text-right font-black text-spice-black text-sm tabular-nums">
                      ₹{parseFloat(selectedOrder.grand_total || 0).toFixed(2)}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}
      </Modal>
    </AdminLayout>
  );
}

export default function AdminOrdersPage() {
  return (
    <React.Suspense
      fallback={
        <div className="min-h-[60vh] flex items-center justify-center">
          <div className="h-8 w-8 rounded-full border-2 border-saffron-600 border-t-transparent animate-spin" />
        </div>
      }
    >
      <AdminOrdersContent />
    </React.Suspense>
  );
}
