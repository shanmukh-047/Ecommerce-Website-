'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  Package,
  Calendar,
  CreditCard,
  MapPin,
  Truck,
  CheckCircle2,
  Clock,
  Printer,
  ChevronRight,
  AlertTriangle,
  ArrowLeft,
  XCircle,
  FileText,
  ShieldCheck,
  Copy,
  ExternalLink,
  Lock,
  Smartphone,
  RotateCcw,
} from 'lucide-react';
import RouteGuard from '../../../../components/common/RouteGuard';
import { useAuth } from '../../../../context/AuthContext';
import { useToast } from '../../../../components/common/Toast';
import orderService from '../../../../services/orderService';
import paymentService from '../../../../services/paymentService';
import shippingService from '../../../../services/shippingService';
import PaymentModal from '../../../../components/checkout/PaymentModal';
import Button from '../../../../components/common/Button';
import Badge from '../../../../components/common/Badge';
import Modal from '../../../../components/common/Modal';
import Skeleton from '../../../../components/common/Skeleton';
import ErrorState from '../../../../components/common/ErrorState';

const STATUS_CONFIG = {
  PENDING_PAYMENT: {
    label: 'Pending Payment',
    color: 'amber',
    bg: 'bg-amber-50 text-amber-900 border-amber-300',
    description: 'Awaiting payment confirmation. Inventory is reserved for this order.',
  },
  CONFIRMED: {
    label: 'Order Confirmed',
    color: 'saffron',
    bg: 'bg-saffron-50 text-saffron-900 border-saffron-300',
    description: 'Payment verified and captured. Order has been queued for warehouse dispatch.',
  },
  PROCESSING: {
    label: 'Processing & Milling',
    color: 'blue',
    bg: 'bg-blue-50 text-blue-900 border-blue-300',
    description: 'Fresh batch spices are being weighed, seal-packed, and prepared for carrier pickup.',
  },
  SHIPPED: {
    label: 'Dispatched in Transit',
    color: 'purple',
    bg: 'bg-purple-50 text-purple-900 border-purple-300',
    description: 'Carrier has picked up shipment from Shimoga facility and is en route.',
  },
  DELIVERED: {
    label: 'Delivered',
    color: 'emerald',
    bg: 'bg-emerald-50 text-emerald-900 border-emerald-300',
    description: 'Package successfully delivered to destination.',
  },
  CANCELLED: {
    label: 'Cancelled',
    color: 'red',
    bg: 'bg-red-50 text-red-900 border-red-300',
    description: 'Order was cancelled and reserved inventory was returned to stock.',
  },
  FAILED: {
    label: 'Payment Failed',
    color: 'red',
    bg: 'bg-red-50 text-red-900 border-red-300',
    description: 'Gateway payment attempt failed or expired.',
  },
  REFUNDED: {
    label: 'Refunded',
    color: 'stone',
    bg: 'bg-stone-100 text-stone-900 border-stone-300',
    description: 'Payment was refunded back to original source.',
  },
};

const SHIPMENT_STATUS_CONFIG = {
  PENDING: { label: 'Pending Allocation', bg: 'bg-stone-100 text-stone-800 border-stone-200' },
  LABEL_GENERATED: { label: 'Label Created', bg: 'bg-blue-50 text-blue-800 border-blue-200' },
  READY_FOR_PICKUP: { label: 'Ready for Carrier', bg: 'bg-amber-50 text-amber-800 border-amber-200' },
  IN_TRANSIT: { label: 'In Transit', bg: 'bg-purple-50 text-purple-800 border-purple-200' },
  OUT_FOR_DELIVERY: { label: 'Out for Delivery', bg: 'bg-indigo-50 text-indigo-800 border-indigo-200' },
  DELIVERED: { label: 'Delivered', bg: 'bg-emerald-50 text-emerald-800 border-emerald-200' },
  FAILED_DELIVERY: { label: 'Delivery Attempt Failed', bg: 'bg-red-50 text-red-800 border-red-200' },
  RETURNED_TO_ORIGIN: { label: 'Returned to Origin', bg: 'bg-red-50 text-red-800 border-red-200' },
  CANCELLED: { label: 'Cancelled', bg: 'bg-stone-100 text-stone-800 border-stone-200' },
};

function OrderDetailContent() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const orderId = params?.id;
  const { success, error: showToastError } = useToast();

  const [order, setOrder] = useState(null);
  const [paymentDetails, setPaymentDetails] = useState(null);
  const [shippingTracking, setShippingTracking] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Cancellation Modal State
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [isCancelling, setIsCancelling] = useState(false);

  // Payment Modal State
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [copiedAwb, setCopiedAwb] = useState('');

  const fetchOrderDetail = useCallback(async () => {
    if (!orderId) return;
    setIsLoading(true);
    setError(null);

    try {
      // 1. Fetch Authoritative Order Data
      const orderData = await orderService.getOrderById(orderId);
      setOrder(orderData);

      // 2. Fetch Payment Information (non-blocking if not created yet)
      try {
        const payRes = await paymentService.getPaymentDetails(orderId);
        setPaymentDetails(payRes);
      } catch (payErr) {
        setPaymentDetails(null);
      }

      // 3. Fetch Shipping & Tracking Information
      try {
        const shipRes = await shippingService.getOrderTracking(orderId);
        setShippingTracking(shipRes);
      } catch (shipErr) {
        setShippingTracking(null);
      }
    } catch (err) {
      console.error('Failed to load order details:', err);
      setError(err.message || 'Unable to retrieve order details.');
    } finally {
      setIsLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    fetchOrderDetail();
  }, [fetchOrderDetail]);

  // Cancel order handler
  const handleCancelOrder = async () => {
    setIsCancelling(true);
    try {
      const updatedOrder = await orderService.cancelOrder(orderId, cancelReason || 'Cancelled by customer.');
      setOrder(updatedOrder);
      setIsCancelModalOpen(false);
      success('Order cancelled and reserved stock released.', 'Order Cancelled');
      fetchOrderDetail();
    } catch (err) {
      showToastError(err.message || 'Failed to cancel order.', 'Cancellation Error');
    } finally {
      setIsCancelling(false);
    }
  };

  const copyToClipboard = (text) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedAwb(text);
      success('AWB Number copied to clipboard!', 'Copied');
      setTimeout(() => setCopiedAwb(''), 3000);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-spice-canvas py-10">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 space-y-6">
          <Skeleton height="20px" width="200px" />
          <Skeleton height="140px" className="w-full rounded-2xl" />
          <Skeleton height="280px" className="w-full rounded-2xl" />
        </div>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="min-h-screen bg-spice-canvas flex items-center justify-center p-4">
        <ErrorState
          title="Order Not Found"
          message={error || 'We could not locate this order in your account.'}
          retryLabel="View All Orders"
          onRetry={() => router.push('/account/orders')}
          className="max-w-lg w-full py-16"
        />
      </div>
    );
  }

  const statusCfg = STATUS_CONFIG[order.order_status] || {
    label: order.order_status,
    bg: 'bg-stone-100 text-stone-900 border-stone-300',
    description: 'Order status updated.',
  };

  const isPendingPayment = order.order_status === 'PENDING_PAYMENT';
  const lines = order.lines || [];
  const statusHistory = order.status_history || [];
  const shipments = shippingTracking?.shipments || [];

  const formattedDate = order.created_at
    ? new Date(order.created_at).toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : 'Recent';

  return (
    <div className="min-h-screen bg-spice-canvas pb-20 pt-4 sm:pt-6 print:bg-white print:p-0">
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb & Top Actions */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 print:hidden">
          <nav aria-label="Breadcrumb" className="flex items-center text-xs text-spice-stone">
            <Link href="/" className="hover:text-saffron-700 transition-colors">
              Home
            </Link>
            <ChevronRight className="mx-1.5 h-3.5 w-3.5 text-spice-muted" />
            <Link href="/account/orders" className="hover:text-saffron-700 transition-colors">
              My Orders
            </Link>
            <ChevronRight className="mx-1.5 h-3.5 w-3.5 text-spice-muted" />
            <span className="font-mono font-bold text-spice-black truncate max-w-[180px]">
              #{order.order_number}
            </span>
          </nav>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => window.print()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-spice-border bg-white px-3 py-1.5 text-xs font-semibold text-spice-black hover:bg-spice-canvas transition-colors shadow-2xs"
            >
              <Printer className="h-3.5 w-3.5 text-spice-stone" />
              <span>Print Receipt</span>
            </button>
            <Link href="/account/orders">
              <Button variant="outline" size="sm" leftIcon={<ArrowLeft className="h-3.5 w-3.5" />}>
                All Orders
              </Button>
            </Link>
          </div>
        </div>

        {/* Order Status Hero Banner */}
        <div className="mb-6 rounded-2xl border bg-white p-6 shadow-subtle">
          <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-spice-borderSubtle pb-4 gap-4">
            <div>
              <div className="flex items-center gap-3 mb-1 flex-wrap">
                <h1 className="text-xl sm:text-2xl font-bold font-mono text-spice-black tracking-tight">
                  Order #{order.order_number}
                </h1>
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold ${statusCfg.bg}`}
                >
                  <span className="h-2 w-2 rounded-full bg-current" />
                  {statusCfg.label}
                </span>
              </div>
              <p className="text-xs text-spice-stone flex items-center gap-2">
                <Calendar className="h-3.5 w-3.5 text-spice-muted" />
                <span>Placed on {formattedDate}</span>
              </p>
            </div>

            {/* Actions for Pending Orders */}
            {isPendingPayment && (
              <div className="flex flex-wrap items-center gap-2 print:hidden">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setIsPaymentModalOpen(true)}
                  leftIcon={<CreditCard className="h-4 w-4" />}
                >
                  Complete Payment • ₹{parseFloat(order.grand_total || 0).toFixed(0)}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsCancelModalOpen(true)}
                  className="text-xs text-red-600 border-red-200 hover:bg-red-50 hover:border-red-300"
                >
                  Cancel Order
                </Button>
              </div>
            )}
          </div>

          <p className="mt-4 text-xs text-spice-stone leading-relaxed">
            {statusCfg.description}
          </p>

          {/* Pending Payment Callout Notice */}
          {isPendingPayment && (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50/70 p-3.5 flex items-start gap-3">
              <AlertTriangle className="h-4 w-4 text-amber-700 shrink-0 mt-0.5" />
              <div className="text-xs text-amber-900 leading-relaxed flex-1">
                <strong className="font-semibold block">Inventory Reservation Active</strong>
                <span>
                  Your selected whole spices and value packs are held in stock. Please complete payment within the reservation window to confirm milling and dispatch.
                </span>
              </div>
              <Button
                variant="primary"
                size="xs"
                onClick={() => setIsPaymentModalOpen(true)}
                className="shrink-0"
              >
                Pay Now
              </Button>
            </div>
          )}
        </div>

        {/* 2-Column Grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 items-start">
          {/* Left Column: Line Items, Shipment Tracking & Timeline (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            {/* Shipment Tracking Section */}
            <div className="rounded-2xl border border-spice-border bg-white p-5 sm:p-6 shadow-subtle">
              <div className="flex items-center justify-between border-b border-spice-borderSubtle pb-3 mb-4">
                <h2 className="text-sm font-bold font-display text-spice-black uppercase tracking-wider flex items-center gap-2">
                  <Truck className="h-4 w-4 text-saffron-700" />
                  <span>Shipment &amp; Delivery Tracking</span>
                </h2>
                {shipments.length > 0 && (
                  <Badge variant="cardamom" size="xs">
                    {shipments.length} {shipments.length === 1 ? 'Package' : 'Packages'}
                  </Badge>
                )}
              </div>

              {shipments.length === 0 ? (
                <div className="rounded-xl bg-spice-canvas/60 border border-spice-borderSubtle p-4 text-xs text-spice-stone space-y-2">
                  <div className="flex items-center gap-2 font-semibold text-spice-black">
                    <Clock className="h-4 w-4 text-saffron-700" />
                    <span>
                      {isPendingPayment
                        ? 'Consignment Awaiting Payment Clearance'
                        : 'Milling & Warehouse Packaging in Progress'}
                    </span>
                  </div>
                  <p className="leading-relaxed">
                    {isPendingPayment
                      ? 'Consignment generation and carrier pickup scheduling will trigger immediately once payment is captured.'
                      : 'Our Shimoga estate team is preparing your single-origin spices. A carrier AWB tracking number will be assigned upon parcel handover.'}
                  </p>
                  <div className="pt-2 flex items-center gap-2 text-[11px] text-spice-muted">
                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                    <span>Dispatches via Delhivery, Blue Dart, or India Post Speed Post with live tracking</span>
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  {shipments.map((shipment) => {
                    const shipStatusCfg = SHIPMENT_STATUS_CONFIG[shipment.status] || {
                      label: shipment.status,
                      bg: 'bg-stone-100 text-stone-800 border-stone-200',
                    };
                    const events = shipment.tracking_events || [];

                    return (
                      <div key={shipment.id} className="rounded-xl border border-spice-border p-4 space-y-4">
                        {/* Shipment Header */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-spice-borderSubtle pb-3">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-xs font-bold text-spice-black">
                                {shipment.shipment_number}
                              </span>
                              <span
                                className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold ${shipStatusCfg.bg}`}
                              >
                                {shipStatusCfg.label}
                              </span>
                            </div>
                            <p className="text-[11px] text-spice-muted mt-0.5">
                              Carrier: <strong className="text-spice-black">{shipment.courier_name}</strong>
                              {shipment.shipped_at && (
                                <>
                                  {' '}• Dispatched on{' '}
                                  {new Date(shipment.shipped_at).toLocaleDateString('en-IN', {
                                    day: 'numeric',
                                    month: 'short',
                                  })}
                                </>
                              )}
                            </p>
                          </div>

                          {shipment.awb_number && (
                            <div className="flex items-center gap-1.5">
                              <span className="text-xs font-mono font-bold text-spice-black bg-stone-100 px-2 py-1 rounded-md border border-stone-200">
                                AWB: {shipment.awb_number}
                              </span>
                              <button
                                type="button"
                                onClick={() => copyToClipboard(shipment.awb_number)}
                                className="p-1 rounded hover:bg-stone-100 text-spice-stone"
                                title="Copy AWB"
                              >
                                <Copy className="h-3.5 w-3.5" />
                              </button>
                              <Link
                                href={`/track?awb=${encodeURIComponent(shipment.awb_number)}`}
                                className="p-1 rounded hover:bg-stone-100 text-saffron-700"
                                title="Open Public Tracking"
                              >
                                <ExternalLink className="h-3.5 w-3.5" />
                              </Link>
                            </div>
                          )}
                        </div>

                        {/* Estimated Delivery */}
                        {shipment.estimated_delivery_date && (
                          <div className="flex items-center gap-2 text-xs text-spice-stone bg-emerald-50/60 p-2.5 rounded-lg border border-emerald-200/60">
                            <Truck className="h-4 w-4 text-emerald-700 shrink-0" />
                            <span>
                              Estimated Delivery by{' '}
                              <strong className="text-emerald-950">
                                {new Date(shipment.estimated_delivery_date).toLocaleDateString('en-IN', {
                                  weekday: 'short',
                                  day: 'numeric',
                                  month: 'short',
                                  year: 'numeric',
                                })}
                              </strong>
                            </span>
                          </div>
                        )}

                        {/* Tracking Milestones */}
                        {events.length > 0 && (
                          <div className="pt-2">
                            <h4 className="text-xs font-bold uppercase tracking-wider text-spice-black mb-3">
                              Carrier Transit Events
                            </h4>
                            <div className="relative pl-5 space-y-3 before:absolute before:left-1.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-spice-border">
                              {events.map((evt, idx) => (
                                <div key={evt.id || idx} className="relative text-xs">
                                  <div className="absolute -left-5 top-1 h-2 w-2 rounded-full bg-saffron-600 ring-2 ring-white" />
                                  <div>
                                    <div className="flex items-center gap-2 flex-wrap">
                                      <span className="font-bold text-spice-black">{evt.status}</span>
                                      {evt.location && (
                                        <span className="text-spice-stone">({evt.location})</span>
                                      )}
                                      <span className="text-[10px] text-spice-muted">
                                        {new Date(evt.event_timestamp || evt.created_at).toLocaleString('en-IN', {
                                          day: 'numeric',
                                          month: 'short',
                                          hour: '2-digit',
                                          minute: '2-digit',
                                        })}
                                      </span>
                                    </div>
                                    {evt.description && (
                                      <p className="text-[11px] text-spice-stone mt-0.5 leading-relaxed">
                                        {evt.description}
                                      </p>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Line Items Table */}
            <div className="rounded-2xl border border-spice-border bg-white p-5 sm:p-6 shadow-subtle">
              <h2 className="text-sm font-bold font-display text-spice-black uppercase tracking-wider mb-4 flex items-center gap-2">
                <Package className="h-4 w-4 text-saffron-700" />
                <span>Purchased Spices &amp; Packs ({lines.length})</span>
              </h2>

              <div className="divide-y divide-spice-borderSubtle">
                {lines.map((line) => (
                  <div key={line.id} className="py-3.5 flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <h4 className="text-xs sm:text-sm font-bold text-spice-black leading-snug">
                        {line.product_name}
                      </h4>
                      <p className="text-xs text-spice-stone mt-0.5">
                        Pack: <span className="font-semibold">{line.variant_name || `${line.weight_in_grams}g`}</span>
                        {line.sku && (
                          <span className="text-spice-muted ml-2 font-mono text-[11px]">
                            SKU: {line.sku}
                          </span>
                        )}
                      </p>
                      <p className="text-[11px] text-spice-muted mt-1">
                        ₹{parseFloat(line.unit_price || 0).toFixed(0)} × {line.quantity} units
                      </p>
                    </div>

                    <div className="text-right shrink-0">
                      <span className="text-sm font-extrabold text-spice-black tabular-nums">
                        ₹{parseFloat(line.line_subtotal || 0).toFixed(2)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Order Status History Timeline */}
            {statusHistory.length > 0 && (
              <div className="rounded-2xl border border-spice-border bg-white p-5 sm:p-6 shadow-subtle">
                <h2 className="text-sm font-bold font-display text-spice-black uppercase tracking-wider mb-4 flex items-center gap-2">
                  <Clock className="h-4 w-4 text-saffron-700" />
                  <span>Order Audit Milestones</span>
                </h2>

                <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-spice-border">
                  {statusHistory.map((hist, idx) => (
                    <div key={hist.id || idx} className="relative">
                      <div className="absolute -left-6 top-1 h-2.5 w-2.5 rounded-full bg-saffron-600 ring-4 ring-white" />
                      <div>
                        <span className="text-xs font-bold text-spice-black uppercase tracking-wide">
                          {hist.to_status}
                        </span>
                        <span className="text-[11px] text-spice-muted ml-2">
                          {new Date(hist.created_at).toLocaleString('en-IN', {
                            day: 'numeric',
                            month: 'short',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                        {hist.notes && (
                          <p className="text-xs text-spice-stone mt-0.5 italic leading-relaxed">
                            &ldquo;{hist.notes}&rdquo;
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Payment Details & Delivery Info (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            {/* Payment Lifecycle Card */}
            <div className="rounded-2xl border border-spice-border bg-white p-5 sm:p-6 shadow-subtle">
              <div className="flex items-center justify-between border-b border-spice-borderSubtle pb-3 mb-4">
                <h2 className="text-sm font-bold font-display text-spice-black uppercase tracking-wider flex items-center gap-2">
                  <CreditCard className="h-4 w-4 text-saffron-700" />
                  <span>Payment Settlement</span>
                </h2>
                {paymentDetails?.status && (
                  <Badge
                    variant={
                      paymentDetails.status === 'CAPTURED'
                        ? 'cardamom'
                        : paymentDetails.status === 'FAILED'
                        ? 'danger'
                        : 'warning'
                    }
                    size="xs"
                  >
                    {paymentDetails.status}
                  </Badge>
                )}
              </div>

              <div className="space-y-3 text-xs">
                <div className="flex justify-between text-spice-stone">
                  <span>Payment Provider</span>
                  <strong className="text-spice-black">
                    {paymentDetails?.gateway === 'PHONEPE_QR' ? 'PhonePe UPI QR' : 'Razorpay Secure'}
                  </strong>
                </div>

                {paymentDetails?.payment_method && (
                  <div className="flex justify-between text-spice-stone">
                    <span>Payment Method</span>
                    <strong className="text-spice-black">{paymentDetails.payment_method}</strong>
                  </div>
                )}

                {paymentDetails?.utr_number && (
                  <div className="flex justify-between text-spice-stone">
                    <span>UTR Reference</span>
                    <span className="font-mono font-bold text-spice-black">{paymentDetails.utr_number}</span>
                  </div>
                )}

                {paymentDetails?.payment_number && (
                  <div className="flex justify-between text-spice-stone">
                    <span>Transaction ID</span>
                    <span className="font-mono text-spice-black">{paymentDetails.payment_number}</span>
                  </div>
                )}

                {paymentDetails?.gateway_payment_id && (
                  <div className="flex justify-between text-spice-stone">
                    <span>Gateway Reference</span>
                    <span className="font-mono text-spice-muted text-[11px]">
                      {paymentDetails.gateway_payment_id}
                    </span>
                  </div>
                )}

                {paymentDetails?.captured_at && (
                  <div className="flex justify-between text-spice-stone">
                    <span>Settled On</span>
                    <span className="text-spice-black">
                      {new Date(paymentDetails.captured_at).toLocaleDateString('en-IN', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                )}

                {/* Verification in progress Callout */}
                {paymentDetails?.status === 'PENDING_VERIFICATION' && (
                  <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 space-y-1.5 mt-2">
                    <div className="flex items-center gap-1.5 font-bold text-amber-950">
                      <Clock className="h-4 w-4 text-amber-700 animate-pulse" />
                      <span>Payment Verification in Progress</span>
                    </div>
                    <p className="text-[11px] text-amber-800 leading-relaxed">
                      Your UTR reference <strong className="font-mono">{paymentDetails.utr_number}</strong> has been submitted. Our estate finance desk verifies incoming UPI payments promptly during business hours.
                    </p>
                  </div>
                )}

                {/* Unpaid / Failed Actions */}
                {isPendingPayment && paymentDetails?.status !== 'PENDING_VERIFICATION' && (
                  <div className="pt-3 border-t border-spice-borderSubtle">
                    <Button
                      variant="primary"
                      size="md"
                      isFullWidth
                      leftIcon={<Lock className="h-4 w-4" />}
                      onClick={() => setIsPaymentModalOpen(true)}
                    >
                      Complete Payment (₹{parseFloat(order.grand_total || 0).toFixed(2)})
                    </Button>
                  </div>
                )}

                {/* Failed Attempt Notice */}
                {paymentDetails?.status === 'FAILED' && (
                  <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800 space-y-2 mt-2">
                    <div className="flex items-center gap-1.5 font-bold">
                      <AlertTriangle className="h-4 w-4 text-red-600" />
                      <span>Previous Attempt Failed</span>
                    </div>
                    {paymentDetails.failure_reason && (
                      <p className="text-[11px] text-red-700">{paymentDetails.failure_reason}</p>
                    )}
                    <Button
                      variant="primary"
                      size="xs"
                      isFullWidth
                      leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
                      onClick={() => setIsPaymentModalOpen(true)}
                    >
                      Retry Payment
                    </Button>
                  </div>
                )}
              </div>
            </div>

            {/* Delivery Address Snapshot */}
            <div className="rounded-2xl border border-spice-border bg-white p-5 sm:p-6 shadow-subtle">
              <h2 className="text-sm font-bold font-display text-spice-black uppercase tracking-wider mb-3 flex items-center gap-2">
                <MapPin className="h-4 w-4 text-saffron-700" />
                <span>Delivery Destination</span>
              </h2>

              <div className="text-xs text-spice-stone space-y-1 leading-relaxed">
                <p className="font-bold text-spice-black text-sm">{order.shipping_recipient_name}</p>
                <p>
                  {order.shipping_address_line_1}
                  {order.shipping_address_line_2 && `, ${order.shipping_address_line_2}`}
                  {order.shipping_landmark && ` (Near ${order.shipping_landmark})`}
                </p>
                <p>
                  {order.shipping_city}, {order.shipping_state} -{' '}
                  <span className="font-mono font-bold text-spice-black">{order.shipping_pincode}</span>
                </p>
                <p className="text-spice-muted pt-1">
                  Contact: <strong className="text-spice-black">{order.shipping_phone_number}</strong>
                </p>

                {order.customer_notes && (
                  <div className="mt-3 pt-3 border-t border-spice-borderSubtle">
                    <span className="text-[11px] font-semibold text-spice-black block">Special Instructions:</span>
                    <p className="text-[11px] italic text-spice-stone">&ldquo;{order.customer_notes}&rdquo;</p>
                  </div>
                )}
              </div>
            </div>

            {/* Financial Breakdown */}
            <div className="rounded-2xl border border-spice-border bg-white p-5 sm:p-6 shadow-subtle">
              <h2 className="text-sm font-bold font-display text-spice-black uppercase tracking-wider mb-4">
                Financial Breakdown
              </h2>

              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between text-spice-stone">
                  <span>Items Subtotal</span>
                  <span className="font-semibold text-spice-black tabular-nums">
                    ₹{parseFloat(order.items_subtotal || 0).toFixed(2)}
                  </span>
                </div>

                {parseFloat(order.total_discount || 0) > 0 && (
                  <div className="flex justify-between text-emerald-700 font-semibold">
                    <span>Discount Applied</span>
                    <span className="tabular-nums">
                      -₹{parseFloat(order.total_discount).toFixed(2)}
                    </span>
                  </div>
                )}

                <div className="flex justify-between text-spice-stone">
                  <span>Shipping &amp; Logistics</span>
                  <span className="font-semibold tabular-nums">
                    {parseFloat(order.shipping_fee || 0) === 0 ? (
                      <span className="text-emerald-700 font-bold">FREE</span>
                    ) : (
                      `₹${parseFloat(order.shipping_fee).toFixed(2)}`
                    )}
                  </span>
                </div>

                <div className="flex justify-between text-spice-muted text-[11px]">
                  <span>GST (Statutory Goods &amp; Services Tax)</span>
                  <span>Included in prices</span>
                </div>

                <div className="border-t border-spice-borderSubtle pt-3 flex justify-between text-sm font-bold text-spice-black">
                  <span>Grand Total</span>
                  <span className="text-xl font-extrabold text-spice-black tabular-nums">
                    ₹{parseFloat(order.grand_total || 0).toFixed(2)}
                  </span>
                </div>
              </div>
            </div>

            {/* Origin Assurance */}
            <div className="rounded-2xl border border-dashed border-spice-border bg-spice-canvas/60 p-4 text-center">
              <div className="flex items-center justify-center gap-1.5 text-xs font-bold text-saffron-800 uppercase tracking-wider mb-1">
                <ShieldCheck className="h-4 w-4 text-saffron-700" />
                <span>Single-Origin Western Ghats Guarantee</span>
              </div>
              <p className="text-[11px] text-spice-stone leading-relaxed">
                Processed, packed, and quality audited under Central FSSAI License 11223344556677.
              </p>
            </div>
          </div>
        </div>

        {/* Cancellation Reason Modal */}
        <Modal
          isOpen={isCancelModalOpen}
          onClose={() => setIsCancelModalOpen(false)}
          title="Cancel Spice Order"
          description={`Release inventory reservation for Order #${order.order_number}`}
          footer={
            <>
              <Button variant="ghost" size="sm" onClick={() => setIsCancelModalOpen(false)}>
                Keep Order
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCancelOrder}
                isLoading={isCancelling}
                className="text-red-600 border-red-200 hover:bg-red-50 hover:border-red-300"
              >
                Confirm Cancellation
              </Button>
            </>
          }
        >
          <div className="space-y-3">
            <p className="text-xs text-spice-stone">
              Orders in <strong className="text-spice-black">Pending Payment</strong> status can be cancelled immediately without penalty. Reserved stock will be returned to the estate inventory ledger.
            </p>
            <label className="block text-xs font-semibold text-spice-black">
              Reason for Cancellation (Optional)
            </label>
            <textarea
              rows={3}
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="e.g. Changed address, will place new order with extra spices"
              className="w-full rounded-xl border border-spice-border p-3 text-xs focus:border-saffron-600 focus:outline-none"
            />
          </div>
        </Modal>

        {/* Payment Gateway Modal */}
        <PaymentModal
          isOpen={isPaymentModalOpen}
          onClose={() => setIsPaymentModalOpen(false)}
          order={order}
          user={user}
          selectedPaymentMethod="ONLINE"
          onPaymentSuccess={() => {
            fetchOrderDetail();
          }}
          onPaymentFailure={() => {
            fetchOrderDetail();
          }}
        />
      </div>
    </div>
  );
}

export default function OrderDetailPage() {
  return (
    <RouteGuard>
      <OrderDetailContent />
    </RouteGuard>
  );
}
