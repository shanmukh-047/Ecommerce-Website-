'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck,
  CreditCard,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Lock,
  Smartphone,
  Banknote,
  ArrowRight,
  Truck,
  Building2,
} from 'lucide-react';
import Modal from '../common/Modal';
import Button from '../common/Button';
import Badge from '../common/Badge';
import paymentService from '../../services/paymentService';

// Safe Promise-based loader for Razorpay Checkout JS SDK
function loadRazorpayScript() {
  return new Promise((resolve) => {
    if (typeof window === 'undefined') return resolve(false);
    if (window.Razorpay) return resolve(true);

    const existing = document.getElementById('razorpay-checkout-script');
    if (existing) {
      if (window.Razorpay) return resolve(true);
      existing.addEventListener('load', () => resolve(true), { once: true });
      existing.addEventListener('error', () => resolve(false), { once: true });
      return;
    }

    const script = document.createElement('script');
    script.id = 'razorpay-checkout-script';
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

export default function PaymentModal({
  isOpen,
  onClose,
  order,
  user,
  selectedPaymentMethod = 'ONLINE',
  onPaymentSuccess,
  onPaymentFailure,
}) {
  // Status: 'IDLE' | 'LOADING_GATEWAY' | 'VERIFYING' | 'SUCCESS_ONLINE' | 'SUCCESS_COD' | 'FAILED'
  const [paymentStatus, setPaymentStatus] = useState('IDLE');
  const [errorMessage, setErrorMessage] = useState('');
  const [gatewayData, setGatewayData] = useState(null);
  const [isSubmittingCOD, setIsSubmittingCOD] = useState(false);

  const grandTotal = parseFloat(order?.grand_total || 0).toFixed(2);

  // Reset state on open/close
  useEffect(() => {
    if (isOpen) {
      setPaymentStatus('IDLE');
      setErrorMessage('');
      setGatewayData(null);
      setIsSubmittingCOD(false);
    }
  }, [isOpen]);

  // Initiate Razorpay order session on backend
  const initiateOnlinePayment = useCallback(async () => {
    if (!order?.id) return null;
    setPaymentStatus('LOADING_GATEWAY');
    setErrorMessage('');

    try {
      const res = await paymentService.initiatePayment(order.id);
      const gw = res?.gateway || res?.data?.gateway;
      if (!gw || !gw.gateway_order_id) {
        throw new Error('Payment gateway configuration not received from server.');
      }
      setGatewayData(gw);
      setPaymentStatus('IDLE');
      return gw;
    } catch (err) {
      console.error('Payment initiation error:', err);
      setPaymentStatus('FAILED');
      const msg =
        err?.response?.data?.message ||
        err?.message ||
        'Unable to connect to payment gateway. Please try again or choose Cash on Delivery.';
      setErrorMessage(msg);
      return null;
    }
  }, [order?.id]);

  // Launch official Razorpay Checkout popup
  const handleLaunchRazorpay = async () => {
    let gw = gatewayData;
    if (!gw) {
      gw = await initiateOnlinePayment();
      if (!gw) return;
    }

    const isLoaded = await loadRazorpayScript();
    if (!isLoaded || typeof window === 'undefined' || !window.Razorpay) {
      setPaymentStatus('FAILED');
      setErrorMessage('Unable to load secure payment gateway. Please check your internet connection and try again.');
      return;
    }

    const options = {
      key: gw.key_id,
      amount: gw.amount,
      currency: gw.currency || 'INR',
      name: gw.name || 'Bharat Masala',
      description: gw.description || `Order #${order?.order_number || ''}`,
      order_id: gw.gateway_order_id,
      prefill: {
        name: user?.full_name || `${user?.first_name || ''} ${user?.last_name || ''}`.trim() || '',
        email: user?.email || '',
        contact: user?.phone_number || '',
      },
      notes: {
        order_number: order?.order_number || '',
      },
      theme: {
        color: '#C05621',
      },
      handler: async function (response) {
        setPaymentStatus('VERIFYING');
        try {
          const verifiedPayment = await paymentService.verifyPayment(order.id, {
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
            payment_method: 'ONLINE',
          });
          setPaymentStatus('SUCCESS_ONLINE');
          if (onPaymentSuccess) {
            onPaymentSuccess(verifiedPayment);
          }
        } catch (err) {
          console.error('Payment signature verification error:', err);
          setPaymentStatus('FAILED');
          setErrorMessage(
            err?.response?.data?.message ||
              'Payment verification failed. If your bank account was debited, your order will be confirmed via automatic webhook settlement.'
          );
          if (onPaymentFailure) {
            onPaymentFailure(err);
          }
        }
      },
      modal: {
        ondismiss: function () {
          setPaymentStatus('IDLE');
        },
      },
    };

    try {
      const rzp = new window.Razorpay(options);
      rzp.on('payment.failed', function (resp) {
        console.error('Razorpay payment.failed:', resp?.error);
        setPaymentStatus('FAILED');
        setErrorMessage(resp?.error?.description || 'Transaction declined by payment network.');
        if (onPaymentFailure) {
          onPaymentFailure(resp?.error);
        }
      });
      rzp.open();
    } catch (err) {
      console.error('Razorpay popup error:', err);
      setPaymentStatus('FAILED');
      setErrorMessage('Could not open payment window. Please try again or switch to Cash on Delivery.');
    }
  };

  // Convert order to Cash on Delivery (COD)
  const handleSelectCOD = async () => {
    if (!order?.id) return;
    setIsSubmittingCOD(true);
    setErrorMessage('');

    try {
      const codPayment = await paymentService.createCODPayment(order.id);
      setPaymentStatus('SUCCESS_COD');
      if (onPaymentSuccess) {
        onPaymentSuccess(codPayment);
      }
    } catch (err) {
      console.error('COD conversion error:', err);
      setPaymentStatus('FAILED');
      setErrorMessage(
        err?.response?.data?.message ||
          err?.message ||
          'Unable to select Cash on Delivery. Please try again.'
      );
      if (onPaymentFailure) {
        onPaymentFailure(err);
      }
    } finally {
      setIsSubmittingCOD(false);
    }
  };

  const isWorking =
    paymentStatus === 'LOADING_GATEWAY' ||
    paymentStatus === 'VERIFYING' ||
    isSubmittingCOD;

  return (
    <Modal
      isOpen={isOpen}
      onClose={isWorking ? () => {} : onClose}
      title="Complete Payment"
      description={`Order #${order?.order_number || ''} · ₹${grandTotal}`}
      size="md"
      footer={
        paymentStatus === 'SUCCESS_ONLINE' || paymentStatus === 'SUCCESS_COD' ? (
          <Button
            variant="primary"
            size="md"
            isFullWidth
            onClick={onClose}
            rightIcon={<ArrowRight className="h-4 w-4" />}
          >
            View Confirmed Order Status
          </Button>
        ) : (
          <div className="flex items-center justify-between w-full gap-2">
            <Button
              variant="ghost"
              size="sm"
              disabled={isWorking}
              onClick={onClose}
            >
              Cancel
            </Button>

            {paymentStatus === 'FAILED' ? (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<RotateCcw className="h-4 w-4" />}
                onClick={() => {
                  setPaymentStatus('IDLE');
                  setErrorMessage('');
                }}
              >
                Try Again
              </Button>
            ) : (
              <Button
                variant="primary"
                size="sm"
                onClick={handleLaunchRazorpay}
                disabled={isWorking}
                isLoading={paymentStatus === 'LOADING_GATEWAY' || paymentStatus === 'VERIFYING'}
                leftIcon={<Lock className="h-3.5 w-3.5" />}
              >
                Proceed to Pay ₹{grandTotal}
              </Button>
            )}
          </div>
        )
      }
    >
      <div className="space-y-4 py-1 font-body">
        {/* Payable Summary Card */}
        <div className="p-4 rounded-xl bg-spice-canvas border border-spice-border flex items-center justify-between">
          <div>
            <span className="text-xs text-spice-muted block">Payable Amount (incl. GST)</span>
            <span className="text-2xl font-black font-display text-spice-black tabular-nums">
              ₹{grandTotal}
            </span>
          </div>
          <div className="text-right">
            <span className="text-[11px] text-spice-muted block">Order Reference</span>
            <span className="font-mono text-xs font-bold text-spice-black">
              #{order?.order_number}
            </span>
          </div>
        </div>

        {/* ONLINE PAYMENT CAPTURED SUCCESS */}
        {paymentStatus === 'SUCCESS_ONLINE' && (
          <div className="p-5 rounded-2xl bg-emerald-50 border border-emerald-200 text-center space-y-3">
            <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 mx-auto">
              <CheckCircle2 className="h-6 w-6" />
            </div>
            <div>
              <Badge variant="cardamom" size="sm" className="mb-2">
                Payment Captured
              </Badge>
              <h4 className="text-base font-bold text-emerald-950">Payment Confirmed!</h4>
              <p className="text-xs text-emerald-700 mt-1 max-w-sm mx-auto">
                Thank you! Your payment of ₹{grandTotal} was securely verified. Your estate spices are now reserved and scheduled for cold-milling and dispatch.
              </p>
            </div>
          </div>
        )}

        {/* CASH ON DELIVERY CONFIRMED SUCCESS */}
        {paymentStatus === 'SUCCESS_COD' && (
          <div className="p-5 rounded-2xl bg-saffron-50 border border-saffron-200 text-center space-y-3">
            <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-saffron-100 text-saffron-700 mx-auto">
              <Truck className="h-6 w-6" />
            </div>
            <div>
              <Badge variant="stone" size="sm" className="mb-2">
                Cash on Delivery
              </Badge>
              <h4 className="text-base font-bold text-saffron-950">Order Placed Successfully!</h4>
              <p className="text-xs text-saffron-800 mt-1 max-w-sm mx-auto">
                Your order is confirmed. Payment of ₹{grandTotal} will be collected in cash or UPI upon delivery at your doorstep.
              </p>
            </div>
          </div>
        )}

        {/* FAILURE NOTICE */}
        {paymentStatus === 'FAILED' && (
          <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800 space-y-2">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
              <div>
                <strong className="font-bold block">Payment Notice</strong>
                <p className="mt-0.5 text-red-700">{errorMessage || 'Unable to complete transaction.'}</p>
              </div>
            </div>
            <p className="text-[11px] text-red-600 pt-1 border-t border-red-100">
              Your items remain reserved. You can try again with another card/UPI app or choose Cash on Delivery.
            </p>
          </div>
        )}

        {/* PRIMARY GATEWAY CARD & COD SWITCH */}
        {paymentStatus !== 'SUCCESS_ONLINE' && paymentStatus !== 'SUCCESS_COD' && (
          <div className="space-y-4">
            {/* Online Gateway Overview */}
            <div className="p-4 rounded-xl bg-stone-50 border border-stone-200 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-bold text-spice-black text-xs flex items-center gap-1.5">
                  <CreditCard className="h-4 w-4 text-saffron-700" />
                  Razorpay Secure Online Checkout
                </span>
                <Badge variant="stone" size="xs">
                  PCI-DSS Level 1
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px] text-spice-stone pt-1">
                <div className="flex items-center gap-1.5">
                  <Smartphone className="h-3.5 w-3.5 text-emerald-600" />
                  <span>UPI: GPay, PhonePe, Paytm</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CreditCard className="h-3.5 w-3.5 text-blue-600" />
                  <span>Debit &amp; Credit Cards</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Building2 className="h-3.5 w-3.5 text-purple-600" />
                  <span>Net Banking (50+ Banks)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <ShieldCheck className="h-3.5 w-3.5 text-saffron-600" />
                  <span>Digital Wallets</span>
                </div>
              </div>

              {paymentStatus === 'LOADING_GATEWAY' && (
                <div className="py-2 text-center text-xs text-spice-stone">
                  <div className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-saffron-600 border-t-transparent mb-1" />
                  <p>Connecting to secure payment gateway...</p>
                </div>
              )}

              {paymentStatus === 'VERIFYING' && (
                <div className="py-2 text-center text-xs text-spice-stone">
                  <div className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent mb-1" />
                  <p>Verifying cryptographic payment signature with bank...</p>
                </div>
              )}
            </div>

            {/* COD Alternative Option */}
            <div className="rounded-xl border border-spice-borderSubtle bg-white p-3.5 flex items-center justify-between gap-3">
              <div className="flex items-start gap-2.5 min-w-0">
                <div className="p-2 rounded-lg bg-stone-100 text-stone-700 shrink-0 mt-0.5">
                  <Banknote className="h-4 w-4" />
                </div>
                <div>
                  <h5 className="text-xs font-bold text-spice-black">Prefer Cash on Delivery?</h5>
                  <p className="text-[11px] text-spice-stone">
                    Pay in cash or courier UPI QR upon parcel arrival at your doorstep.
                  </p>
                </div>
              </div>

              <Button
                variant="outline"
                size="xs"
                disabled={isWorking}
                isLoading={isSubmittingCOD}
                onClick={handleSelectCOD}
                className="shrink-0 text-xs font-semibold"
              >
                Select COD
              </Button>
            </div>

            {/* Trust Assurance Footer */}
            <div className="flex items-center justify-between text-[11px] text-spice-muted pt-2 border-t border-spice-borderSubtle">
              <span className="flex items-center gap-1">
                <Lock className="h-3 w-3 text-spice-muted" />
                256-Bit SSL Bank Encryption
              </span>
              <span>RBI Regulated Payment Infrastructure</span>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
