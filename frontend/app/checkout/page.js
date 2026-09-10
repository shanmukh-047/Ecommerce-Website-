'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import {
  ShieldCheck,
  MapPin,
  Plus,
  Truck,
  CreditCard,
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  Lock,
  ChevronRight,
  Sparkles,
  ShoppingBag,
  Smartphone,
  Building2,
  Wallet,
  Banknote,
} from 'lucide-react';
import RouteGuard from '../../components/common/RouteGuard';
import PaymentModal from '../../components/checkout/PaymentModal';
import { useCart } from '../../context/CartContext';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../components/common/Toast';
import authService from '../../services/authService';
import orderService from '../../services/orderService';
import paymentService from '../../services/paymentService';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import Select from '../../components/common/Select';
import Modal from '../../components/common/Modal';
import Badge from '../../components/common/Badge';
import Skeleton from '../../components/common/Skeleton';

const INDIAN_STATES = [
  { value: 'KA', label: 'Karnataka' },
  { value: 'KL', label: 'Kerala' },
  { value: 'TN', label: 'Tamil Nadu' },
  { value: 'MH', label: 'Maharashtra' },
  { value: 'AP', label: 'Andhra Pradesh' },
  { value: 'TG', label: 'Telangana' },
  { value: 'GA', label: 'Goa' },
  { value: 'DL', label: 'Delhi NCR' },
  { value: 'GJ', label: 'Gujarat' },
  { value: 'RJ', label: 'Rajasthan' },
  { value: 'WB', label: 'West Bengal' },
  { value: 'UP', label: 'Uttar Pradesh' },
  { value: 'MP', label: 'Madhya Pradesh' },
  { value: 'PB', label: 'Punjab' },
  { value: 'HR', label: 'Haryana' },
  { value: 'OR', label: 'Odisha' },
  { value: 'AS', label: 'Assam' },
  { value: 'BR', label: 'Bihar' },
  { value: 'CH', label: 'Chandigarh' },
  { value: 'CG', label: 'Chhattisgarh' },
  { value: 'JH', label: 'Jharkhand' },
  { value: 'UK', label: 'Uttarakhand' },
  { value: 'HP', label: 'Himachal Pradesh' },
  { value: 'JK', label: 'Jammu and Kashmir' },
];

const FREE_SHIPPING_THRESHOLD = 499;
const STANDARD_SHIPPING_FEE = 50;

const PAYMENT_METHODS = [
  {
    id: 'ONLINE',
    name: 'Pay Online',
    desc: 'Instant UPI (GPay, PhonePe, Paytm), Cards & Net Banking via Razorpay',
    icon: CreditCard,
    badge: 'Fast & Secure',
  },
  {
    id: 'COD',
    name: 'Cash on Delivery (COD)',
    desc: 'Pay cash or courier UPI QR upon parcel arrival at your doorstep',
    icon: Banknote,
    badge: 'Pay on Delivery',
  },
];

function CheckoutContent() {
  const router = useRouter();
  const { user } = useAuth();
  const {
    items,
    itemCount,
    subtotal,
    discountAmount,
    netSubtotal,
    appliedCouponCode,
    hasValidationIssues,
    isLoading: isCartLoading,
    fetchCart,
  } = useCart();
  const { success, error: showToastError } = useToast();

  const [addresses, setAddresses] = useState([]);
  const [selectedAddressId, setSelectedAddressId] = useState('');
  const [customerNotes, setCustomerNotes] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('ONLINE');
  const [isLoadingAddresses, setIsLoadingAddresses] = useState(true);
  const [isSubmittingOrder, setIsSubmittingOrder] = useState(false);
  const [isAddAddressModalOpen, setIsAddAddressModalOpen] = useState(false);

  // Payment Gateway Modal State
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [placedOrder, setPlacedOrder] = useState(null);

  // New Address Form State
  const [newAddress, setNewAddress] = useState({
    recipient_name: '',
    phone_number: '',
    address_line_1: '',
    address_line_2: '',
    landmark: '',
    city: '',
    state: 'KA',
    pincode: '',
    address_type: 'HOME',
    is_default_shipping: true,
  });
  const [isSavingAddress, setIsSavingAddress] = useState(false);
  const [addressError, setAddressError] = useState('');

  // Shipping math
  const isFreeShipping = subtotal >= FREE_SHIPPING_THRESHOLD;
  const shippingFee = isFreeShipping || items.length === 0 ? 0 : STANDARD_SHIPPING_FEE;
  const finalTotal = netSubtotal + shippingFee;

  // Load customer addresses
  useEffect(() => {
    let isMounted = true;
    async function loadAddresses() {
      setIsLoadingAddresses(true);
      try {
        const data = await authService.getAddresses();
        if (isMounted) {
          const list = Array.isArray(data) ? data : data?.results || [];
          setAddresses(list);

          // Auto-select default or first address
          const defaultAddr = list.find((a) => a.is_default_shipping) || list[0];
          if (defaultAddr) {
            setSelectedAddressId(defaultAddr.id);
          } else if (list.length === 0) {
            // Pre-fill recipient with user profile name & phone
            setNewAddress((prev) => ({
              ...prev,
              recipient_name: user?.full_name || `${user?.first_name || ''} ${user?.last_name || ''}`.trim(),
              phone_number: user?.phone_number || '',
            }));
            setIsAddAddressModalOpen(true);
          }
        }
      } catch (err) {
        console.error('Failed to load saved addresses:', err);
      } finally {
        if (isMounted) setIsLoadingAddresses(false);
      }
    }

    loadAddresses();
    return () => {
      isMounted = false;
    };
  }, [user]);

  // Handle new address creation
  const handleSaveAddress = async (e) => {
    e.preventDefault();
    setAddressError('');
    setIsSavingAddress(true);

    try {
      const saved = await authService.addAddress(newAddress);
      const savedAddr = saved?.data || saved;
      setAddresses((prev) => [savedAddr, ...prev]);
      setSelectedAddressId(savedAddr.id);
      setIsAddAddressModalOpen(false);
      success('Delivery address saved successfully', 'Address Added');
    } catch (err) {
      setAddressError(err.message || 'Failed to save address. Please verify your PIN code and phone number.');
    } finally {
      setIsSavingAddress(false);
    }
  };

  // Place Order Action
  const handlePlaceOrder = async () => {
    if (!selectedAddressId) {
      showToastError('Please select or add a delivery address to proceed.', 'Address Required');
      return;
    }

    if (items.length === 0) {
      showToastError('Your basket is empty.', 'Cart Empty');
      router.push('/products');
      return;
    }

    if (hasValidationIssues) {
      showToastError('Please return to your cart and resolve out-of-stock items before checking out.', 'Cart Notice');
      router.push('/cart');
      return;
    }

    setIsSubmittingOrder(true);
    try {
      // 1. Create order on backend (authoritative atomic stock reservation)
      const order = await orderService.checkout(selectedAddressId, customerNotes.trim());

      // 2. Refresh cart state (backend cleared user's cart)
      await fetchCart();

      // 3. Process payment method choice
      if (paymentMethod === 'COD') {
        // Confirm order via Cash on Delivery immediately
        await paymentService.createCODPayment(order.id);
        success(`Order #${order.order_number} placed successfully with Cash on Delivery!`, 'Order Confirmed');
        router.push(`/account/orders/${order.id}`);
      } else {
        // Open Razorpay online gateway modal
        setPlacedOrder(order);
        setIsPaymentModalOpen(true);
        success(`Order #${order.order_number} created! Proceeding to online payment.`, 'Order Initiated');
      }
    } catch (err) {
      showToastError(
        err?.response?.data?.message || err?.message || 'Unable to place order. Please verify that all items are in stock.',
        'Checkout Failed'
      );
    } finally {
      setIsSubmittingOrder(false);
    }
  };

  if (isCartLoading) {
    return (
      <div className="min-h-screen bg-spice-canvas py-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <Skeleton height="30px" width="240px" className="mb-6" />
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <div className="lg:col-span-8 space-y-6">
              <Skeleton height="180px" className="rounded-2xl" />
              <Skeleton height="140px" className="rounded-2xl" />
            </div>
            <div className="lg:col-span-4">
              <Skeleton height="360px" className="rounded-2xl" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // If cart is empty, redirect or prompt
  if (items.length === 0) {
    return (
      <div className="min-h-screen bg-spice-canvas flex items-center justify-center py-16 px-4">
        <div className="max-w-md w-full rounded-2xl border border-spice-border bg-white p-8 text-center shadow-subtle">
          <ShoppingBag className="mx-auto h-12 w-12 text-saffron-600 mb-3" />
          <h2 className="text-xl font-bold font-display text-spice-black mb-2">
            Your Basket is Empty
          </h2>
          <p className="text-xs text-spice-stone mb-6">
            You must have at least one spice item in your basket to proceed through checkout.
          </p>
          <Link href="/products">
            <Button variant="primary" size="md">
              Explore Spices &amp; Pantry
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-spice-canvas pb-24 pt-4 sm:pt-6">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Breadcrumbs */}
        <nav aria-label="Breadcrumb" className="mb-6 flex items-center text-xs text-spice-stone">
          <Link href="/" className="hover:text-saffron-700 transition-colors">
            Home
          </Link>
          <ChevronRight className="mx-1.5 h-3.5 w-3.5 text-spice-muted" />
          <Link href="/cart" className="hover:text-saffron-700 transition-colors">
            Basket
          </Link>
          <ChevronRight className="mx-1.5 h-3.5 w-3.5 text-spice-muted" />
          <span className="font-semibold text-spice-black">Checkout &amp; Delivery</span>
        </nav>

        {/* Page Title */}
        <div className="mb-8 flex items-center justify-between border-b border-spice-borderSubtle pb-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold font-display text-spice-black tracking-tight">
              Express Checkout
            </h1>
            <p className="mt-1 text-xs text-spice-stone">
              Direct-from-estate order fulfillment under statutory FSSAI compliance
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-emerald-700 font-semibold bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-full">
            <Lock className="h-3.5 w-3.5" />
            <span>256-Bit SSL Secured</span>
          </div>
        </div>

        {/* Validation Warning */}
        {hasValidationIssues && (
          <div className="mb-6 rounded-2xl border border-red-300 bg-red-50 p-4 text-red-900 shadow-2xs">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-red-950">
                  Cart Inventory Notice
                </h4>
                <p className="mt-0.5 text-xs text-red-800 leading-relaxed">
                  One or more items in your basket exceed available stock. Please return to your{' '}
                  <Link href="/cart" className="font-bold underline hover:text-red-950">
                    shopping basket
                  </Link>{' '}
                  to adjust quantities before completing your order.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 2-Column Main Layout */}
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 items-start">
          {/* Left Column: Delivery Address, Shipping Method, Payment (8 cols) */}
          <div className="lg:col-span-8 space-y-6">
            {/* Section 1: Delivery Address Selection */}
            <div className="rounded-2xl border border-spice-border bg-white p-5 sm:p-6 shadow-subtle">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="h-7 w-7 rounded-lg bg-saffron-50 text-saffron-700 flex items-center justify-center font-bold text-xs">
                    1
                  </div>
                  <h2 className="text-base font-bold text-spice-black font-display uppercase tracking-wider">
                    Select Delivery Destination
                  </h2>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsAddAddressModalOpen(true)}
                  leftIcon={<Plus className="h-3.5 w-3.5" />}
                  className="text-xs font-semibold"
                >
                  Add New Address
                </Button>
              </div>

              {isLoadingAddresses ? (
                <div className="space-y-3">
                  <Skeleton height="70px" className="w-full rounded-xl" />
                  <Skeleton height="70px" className="w-full rounded-xl" />
                </div>
              ) : addresses.length === 0 ? (
                <div className="rounded-xl border border-dashed border-spice-border p-6 text-center">
                  <MapPin className="mx-auto h-8 w-8 text-spice-muted mb-2" />
                  <p className="text-xs text-spice-stone mb-3">
                    No delivery address found. Please add a shipping destination to complete your purchase.
                  </p>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setIsAddAddressModalOpen(true)}
                    leftIcon={<Plus className="h-4 w-4" />}
                  >
                    Add Delivery Address
                  </Button>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {addresses.map((addr) => {
                    const isSelected = selectedAddressId === addr.id;
                    return (
                      <div
                        key={addr.id}
                        onClick={() => setSelectedAddressId(addr.id)}
                        className={`relative rounded-xl border p-4 cursor-pointer transition-all ${
                          isSelected
                            ? 'border-saffron-600 bg-saffron-50/40 ring-2 ring-saffron-500/20 shadow-2xs'
                            : 'border-spice-border bg-white hover:border-spice-stone/40'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <input
                              type="radio"
                              name="shipping_address"
                              checked={isSelected}
                              onChange={() => setSelectedAddressId(addr.id)}
                              className="h-4 w-4 text-saffron-600 focus:ring-saffron-500 border-spice-border"
                            />
                            <span className="text-xs font-bold text-spice-black">
                              {addr.recipient_name}
                            </span>
                          </div>

                          <Badge variant="stone" size="xs">
                            {addr.address_type}
                          </Badge>
                        </div>

                        <p className="text-xs text-spice-stone leading-relaxed pl-6">
                          {addr.address_line_1}
                          {addr.address_line_2 && `, ${addr.address_line_2}`}
                          {addr.landmark && ` (Near ${addr.landmark})`}
                          <br />
                          {addr.city}, {addr.state} -{' '}
                          <span className="font-mono font-bold text-spice-black">{addr.pincode}</span>
                        </p>

                        <p className="text-[11px] text-spice-muted mt-2 pl-6">
                          Contact: {addr.phone_number}
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Section 2: Shipping Method (Authoritative Backend Sourced) */}
            <div className="rounded-2xl border border-spice-border bg-white p-5 sm:p-6 shadow-subtle">
              <div className="flex items-center gap-2 mb-3">
                <div className="h-7 w-7 rounded-lg bg-saffron-50 text-saffron-700 flex items-center justify-center font-bold text-xs">
                  2
                </div>
                <h2 className="text-base font-bold text-spice-black font-display uppercase tracking-wider">
                  Shipping &amp; Logistics Method
                </h2>
              </div>

              <div className="rounded-xl border border-saffron-600/30 bg-saffron-50/30 p-4 flex items-center justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-white border border-saffron-200 text-saffron-700 shrink-0 mt-0.5">
                    <Truck className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-xs font-bold text-spice-black">
                        Standard Tracked Estate Delivery
                      </h4>
                      <span className="rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.2">
                        Western Ghats Direct
                      </span>
                    </div>
                    <p className="text-[11px] text-spice-stone mt-0.5 leading-relaxed">
                      Dispatched directly from Shimoga, Karnataka. Fully tracked with automated SMS/WhatsApp alerts.
                    </p>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span className="text-sm font-bold text-spice-black tabular-nums">
                    {shippingFee === 0 ? (
                      <span className="text-emerald-700 font-extrabold">FREE</span>
                    ) : (
                      `₹${shippingFee.toFixed(2)}`
                    )}
                  </span>
                </div>
              </div>
            </div>

            {/* Section 3: Customer Delivery Instructions / Notes */}
            <div className="rounded-2xl border border-spice-border bg-white p-5 sm:p-6 shadow-subtle">
              <div className="flex items-center gap-2 mb-3">
                <div className="h-7 w-7 rounded-lg bg-saffron-50 text-saffron-700 flex items-center justify-center font-bold text-xs">
                  3
                </div>
                <h2 className="text-base font-bold text-spice-black font-display uppercase tracking-wider">
                  Delivery Notes / Special Instructions
                </h2>
              </div>

              <textarea
                rows={2}
                value={customerNotes}
                onChange={(e) => setCustomerNotes(e.target.value.slice(0, 500))}
                placeholder="Optional instructions for courier (e.g., Gate code, leave with security, call upon arrival)..."
                className="w-full rounded-xl border border-spice-border bg-spice-canvas/40 p-3 text-xs text-spice-black placeholder-spice-muted focus:border-saffron-600 focus:bg-white focus:outline-none focus:ring-2 focus:ring-saffron-500/20 resize-none"
              />
              <div className="text-right mt-1">
                <span className="text-[10px] text-spice-muted">{customerNotes.length} / 500 chars</span>
              </div>
            </div>

            {/* Section 4: Payment Gateway Selection */}
            <div className="rounded-2xl border border-spice-border bg-white p-5 sm:p-6 shadow-subtle">
              <div className="flex items-center gap-2 mb-4">
                <div className="h-7 w-7 rounded-lg bg-saffron-50 text-saffron-700 flex items-center justify-center font-bold text-xs">
                  4
                </div>
                <h2 className="text-base font-bold text-spice-black font-display uppercase tracking-wider">
                  Select Payment Method
                </h2>
              </div>

              <div className="space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {PAYMENT_METHODS.map((pm) => {
                    const isSelected = paymentMethod === pm.id;
                    const Icon = pm.icon;
                    return (
                      <label
                        key={pm.id}
                        className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
                          isSelected
                            ? 'border-saffron-600 bg-saffron-50/40 ring-1 ring-saffron-600 shadow-xs'
                            : 'border-spice-border bg-white hover:border-spice-stone hover:bg-spice-canvas/30'
                        }`}
                      >
                        <input
                          type="radio"
                          name="payment_method"
                          value={pm.id}
                          checked={isSelected}
                          onChange={() => setPaymentMethod(pm.id)}
                          className="mt-0.5 h-4 w-4 text-saffron-600 focus:ring-saffron-500 border-spice-border"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-1 mb-0.5">
                            <span className="text-xs font-bold text-spice-black flex items-center gap-1.5">
                              <Icon className="h-3.5 w-3.5 text-saffron-700" />
                              {pm.name}
                            </span>
                            {pm.badge && (
                              <Badge variant="stone" size="2xs">
                                {pm.badge}
                              </Badge>
                            )}
                          </div>
                          <span className="text-[11px] text-spice-stone leading-tight block">
                            {pm.desc}
                          </span>
                        </div>
                      </label>
                    );
                  })}
                </div>

                <div className="rounded-xl bg-spice-canvas/60 p-3 border border-spice-borderSubtle text-[11px] text-spice-muted flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-emerald-600 shrink-0" />
                    <span>
                      End-to-end 256-bit SSL encrypted. Settled via Razorpay banking network.
                    </span>
                  </div>
                  <Badge variant="stone" size="xs">
                    PCI-DSS Level 1
                  </Badge>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Order Items Summary & Payment CTA (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            <div className="sticky top-24 rounded-2xl border border-spice-border bg-white p-5 sm:p-6 shadow-subtle">
              <div className="flex items-center justify-between border-b border-spice-borderSubtle pb-3 mb-4">
                <h2 className="text-base font-bold font-display text-spice-black uppercase tracking-wider">
                  Order Summary
                </h2>
                <span className="text-xs text-spice-stone font-semibold">
                  {itemCount} {itemCount === 1 ? 'Item' : 'Items'}
                </span>
              </div>

              {/* Items Mini List */}
              <div className="divide-y divide-spice-borderSubtle max-h-56 overflow-y-auto mb-4 pr-1">
                {items.map((item) => (
                  <div key={item.id} className="py-2.5 flex items-center justify-between gap-3 text-xs">
                    <div className="relative h-10 w-10 rounded-lg bg-spice-canvas border border-spice-border overflow-hidden shrink-0 flex items-center justify-center text-spice-muted">
                      {item.product_image ? (
                        <Image
                          src={item.product_image}
                          alt={item.product_name || 'Spice'}
                          fill
                          sizes="40px"
                          className="object-cover object-center"
                        />
                      ) : (
                        <ShoppingBag className="h-4 w-4" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-spice-black truncate">{item.product_name}</p>
                      <p className="text-[11px] text-spice-muted truncate">
                        {item.variant_name || `${item.weight_in_grams}g`} × {item.quantity}
                      </p>
                    </div>
                    <span className="font-bold text-spice-black tabular-nums shrink-0">
                      ₹{parseFloat(item.line_total || 0).toFixed(0)}
                    </span>
                  </div>
                ))}
              </div>

              {/* Cost Calculations */}
              <div className="space-y-2 border-t border-spice-borderSubtle pt-3 text-xs">
                <div className="flex justify-between text-spice-stone">
                  <span>Items Subtotal</span>
                  <span className="font-semibold text-spice-black tabular-nums">
                    ₹{subtotal.toFixed(2)}
                  </span>
                </div>

                {discountAmount > 0 && (
                  <div className="flex justify-between text-emerald-700 font-semibold">
                    <span className="flex items-center gap-1">
                      <Sparkles className="h-3.5 w-3.5" />
                      Promo Code ({appliedCouponCode})
                    </span>
                    <span className="tabular-nums">-₹{discountAmount.toFixed(2)}</span>
                  </div>
                )}

                <div className="flex justify-between text-spice-stone">
                  <span>Delivery Fee</span>
                  <span className="font-semibold tabular-nums">
                    {shippingFee === 0 ? (
                      <span className="text-emerald-700 font-bold">FREE</span>
                    ) : (
                      `₹${shippingFee.toFixed(2)}`
                    )}
                  </span>
                </div>

                <div className="flex justify-between text-spice-muted text-[11px]">
                  <span>GST &amp; Taxes</span>
                  <span>Included in prices</span>
                </div>

                <div className="border-t border-spice-borderSubtle pt-3 flex justify-between text-sm font-bold text-spice-black">
                  <span>Total Payable</span>
                  <span className="text-xl font-extrabold text-spice-black tabular-nums">
                    ₹{finalTotal.toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Submit CTA */}
              <div className="mt-6">
                <Button
                  variant="primary"
                  size="lg"
                  isFullWidth
                  disabled={isSubmittingOrder || !selectedAddressId || hasValidationIssues}
                  isLoading={isSubmittingOrder}
                  onClick={handlePlaceOrder}
                  rightIcon={<ArrowRight className="h-4 w-4" />}
                  className="font-bold uppercase tracking-wider text-xs shadow-md"
                >
                  {paymentMethod === 'COD'
                    ? `Confirm Order (Cash on Delivery) • ₹${Math.round(finalTotal)}`
                    : `Proceed to Pay Online • ₹${Math.round(finalTotal)}`}
                </Button>

                {!selectedAddressId && (
                  <p className="mt-2 text-center text-[11px] text-amber-700 font-medium">
                    Please select or add a delivery address
                  </p>
                )}
              </div>

              {/* Trust Guarantee */}
              <div className="mt-5 border-t border-spice-borderSubtle pt-4 space-y-1.5 text-[11px] text-spice-stone">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                  <span>100% Guaranteed Western Ghats Origin</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                  <span>Licensed under FSSAI Regulations</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Add New Address Modal */}
      <Modal
        isOpen={isAddAddressModalOpen}
        onClose={() => setIsAddAddressModalOpen(false)}
        title="Add New Delivery Destination"
        size="md"
        footer={
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="md"
              className="flex-1"
              onClick={() => setIsAddAddressModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="md"
              className="flex-1"
              isLoading={isSavingAddress}
              onClick={handleSaveAddress}
            >
              Save Address
            </Button>
          </div>
        }
      >
        <form onSubmit={handleSaveAddress} className="space-y-4">
          {addressError && (
            <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-xs text-red-700">
              {addressError}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Recipient Full Name"
              required
              value={newAddress.recipient_name}
              onChange={(e) => setNewAddress({ ...newAddress, recipient_name: e.target.value })}
              placeholder="e.g. Ramesh Hegde"
            />
            <Input
              label="10-Digit Mobile Number"
              required
              type="tel"
              value={newAddress.phone_number}
              onChange={(e) => setNewAddress({ ...newAddress, phone_number: e.target.value })}
              placeholder="e.g. 9876543210"
            />
          </div>

          <Input
            label="Address Line 1 (Flat, House No., Building)"
            required
            value={newAddress.address_line_1}
            onChange={(e) => setNewAddress({ ...newAddress, address_line_1: e.target.value })}
            placeholder="e.g. #42, Sharada Nilaya, Main Road"
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Address Line 2 (Area, Colony)"
              value={newAddress.address_line_2}
              onChange={(e) => setNewAddress({ ...newAddress, address_line_2: e.target.value })}
              placeholder="e.g. Kuvempu Nagar"
            />
            <Input
              label="Landmark"
              value={newAddress.landmark}
              onChange={(e) => setNewAddress({ ...newAddress, landmark: e.target.value })}
              placeholder="e.g. Opp. City Post Office"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Input
              label="City / Town"
              required
              value={newAddress.city}
              onChange={(e) => setNewAddress({ ...newAddress, city: e.target.value })}
              placeholder="e.g. Shimoga"
            />
            <Select
              label="State"
              required
              value={newAddress.state}
              onChange={(e) => setNewAddress({ ...newAddress, state: e.target.value })}
              options={INDIAN_STATES}
            />
            <Input
              label="6-Digit PIN Code"
              required
              maxLength={6}
              value={newAddress.pincode}
              onChange={(e) => setNewAddress({ ...newAddress, pincode: e.target.value })}
              placeholder="577201"
            />
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="set-default-shipping"
              checked={newAddress.is_default_shipping}
              onChange={(e) => setNewAddress({ ...newAddress, is_default_shipping: e.target.checked })}
              className="h-4 w-4 text-saffron-600 focus:ring-saffron-500 rounded border-spice-border"
            />
            <label htmlFor="set-default-shipping" className="text-xs text-spice-black font-medium">
              Save as my default delivery destination
            </label>
          </div>
        </form>
      </Modal>

      {/* Payment Gateway Modal */}
      {placedOrder && (
        <PaymentModal
          isOpen={isPaymentModalOpen}
          onClose={() => {
            setIsPaymentModalOpen(false);
            router.push(`/account/orders/${placedOrder.id}`);
          }}
          order={placedOrder}
          user={user}
          selectedPaymentMethod={paymentMethod}
          onPaymentSuccess={() => {
            router.push(`/account/orders/${placedOrder.id}`);
          }}
          onPaymentFailure={(err) => {
            console.warn('Payment failure callback in checkout:', err);
          }}
        />
      )}
    </div>
  );
}

export default function CheckoutPage() {
  return (
    <RouteGuard>
      <CheckoutContent />
    </RouteGuard>
  );
}
