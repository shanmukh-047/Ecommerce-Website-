'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  CreditCard,
  CheckCircle2,
  XCircle,
  Clock,
  Search,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  RotateCcw,
  Image as ImageIcon,
  Check,
} from 'lucide-react';
import AdminLayout from '../../../components/admin/AdminLayout';
import Button from '../../../components/common/Button';
import Badge from '../../../components/common/Badge';
import Modal from '../../../components/common/Modal';
import adminService from '../../../services/adminService';

export default function AdminPaymentsPage() {
  const [payments, setPayments] = useState([]);
  const [pagination, setPagination] = useState({ count: 0, next: null, previous: null });
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [gatewayFilter, setGatewayFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // Modals state
  const [selectedPayment, setSelectedPayment] = useState(null);
  const [isVerifyModalOpen, setIsVerifyModalOpen] = useState(false);
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
  const [isScreenshotModalOpen, setIsScreenshotModalOpen] = useState(false);
  const [isCODCollectedModalOpen, setIsCODCollectedModalOpen] = useState(false);
  const [verifyNotes, setVerifyNotes] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [isProcessingAction, setIsProcessingAction] = useState(false);
  const [actionSuccessMessage, setActionSuccessMessage] = useState('');

  const loadPayments = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage('');
    try {
      const res = await adminService.getPayments({
        status: statusFilter === 'ALL' ? '' : statusFilter,
        gateway: gatewayFilter === 'ALL' ? '' : gatewayFilter,
        search: searchQuery.trim(),
      });
      const results = res?.results || (Array.isArray(res) ? res : []);
      setPayments(results);
      setPagination({
        count: res?.count || results.length,
        next: res?.next,
        previous: res?.previous,
      });
    } catch (err) {
      console.error('Error fetching payments:', err);
      setErrorMessage('Unable to load payment transactions. Please retry.');
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, gatewayFilter, searchQuery]);

  useEffect(() => {
    loadPayments();
  }, [loadPayments]);

  const handleVerify = async (e) => {
    e.preventDefault();
    if (!selectedPayment) return;
    setIsProcessingAction(true);
    try {
      await adminService.verifyPayment(selectedPayment.id, verifyNotes.trim());
      setIsVerifyModalOpen(false);
      setSelectedPayment(null);
      setVerifyNotes('');
      setActionSuccessMessage(`Payment for Order #${selectedPayment.order_number} verified and confirmed!`);
      setTimeout(() => setActionSuccessMessage(''), 4000);
      loadPayments();
    } catch (err) {
      alert(err?.message || 'Failed to verify payment.');
    } finally {
      setIsProcessingAction(false);
    }
  };

  const handleReject = async (e) => {
    e.preventDefault();
    if (!selectedPayment || !rejectReason.trim()) return;
    setIsProcessingAction(true);
    try {
      await adminService.rejectPayment(selectedPayment.id, rejectReason.trim());
      setIsRejectModalOpen(false);
      setSelectedPayment(null);
      setRejectReason('');
      setActionSuccessMessage(`Payment for Order #${selectedPayment.order_number} marked as rejected.`);
      setTimeout(() => setActionSuccessMessage(''), 4000);
      loadPayments();
    } catch (err) {
      alert(err?.message || 'Failed to reject payment.');
    } finally {
      setIsProcessingAction(false);
    }
  };

  const handleConfirmCODCollected = async (e) => {
    e.preventDefault();
    if (!selectedPayment) return;
    setIsProcessingAction(true);
    try {
      await adminService.markCODCollected(selectedPayment.id);
      setIsCODCollectedModalOpen(false);
      setSelectedPayment(null);
      setActionSuccessMessage(`COD Payment of ₹${parseFloat(selectedPayment.amount || 0).toFixed(2)} for Order #${selectedPayment.order_number} marked as collected!`);
      setTimeout(() => setActionSuccessMessage(''), 4000);
      loadPayments();
    } catch (err) {
      alert(err?.message || 'Failed to confirm COD collection.');
    } finally {
      setIsProcessingAction(false);
    }
  };

  return (
    <AdminLayout
      title="Payments &amp; Collections Management"
      subtitle="Monitor online gateway transactions, verify COD collections, and audit legacy records."
    >
      {/* Toast banner */}
      {actionSuccessMessage && (
        <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          <span className="font-bold">{actionSuccessMessage}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-stone-200 shadow-xs mb-6 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Method Filter */}
          <div className="flex flex-wrap items-center gap-1.5 p-1 bg-stone-100 rounded-xl">
            <span className="text-[11px] font-bold text-stone-500 uppercase px-2">Gateway:</span>
            {[
              { id: 'ALL', label: 'All Gateways' },
              { id: 'RAZORPAY', label: 'Razorpay Online' },
              { id: 'COD', label: 'Cash on Delivery (COD)' },
              { id: 'PHONEPE_QR', label: 'Legacy UPI QR' },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setGatewayFilter(tab.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  gatewayFilter === tab.id
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
              loadPayments();
            }}
            className="relative min-w-[240px]"
          >
            <Search className="h-4 w-4 text-stone-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search order #, customer, ID..."
              className="w-full pl-9 pr-3 py-2 rounded-xl border border-stone-300 text-xs text-spice-black placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-saffron-500"
            />
          </form>
        </div>

        {/* Status Tabs */}
        <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-stone-100">
          <span className="text-[11px] font-bold text-stone-500 uppercase px-2">Status:</span>
          {[
            { id: 'ALL', label: 'All Statuses' },
            { id: 'CAPTURED', label: 'Captured' },
            { id: 'PENDING', label: 'Pending (COD / Orders)' },
            { id: 'PENDING_VERIFICATION', label: 'Legacy Verification' },
            { id: 'FAILED', label: 'Failed' },
            { id: 'REFUNDED', label: 'Refunded' },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setStatusFilter(tab.id)}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                statusFilter === tab.id
                  ? 'bg-stone-800 text-white shadow-2xs'
                  : 'text-stone-500 hover:text-spice-black hover:bg-stone-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Payments List Table */}
      <div className="bg-white rounded-2xl border border-stone-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-600 font-bold border-b border-stone-200 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Order Reference</th>
                <th className="py-3 px-4">Amount</th>
                <th className="py-3 px-4">Payment Method / Gateway</th>
                <th className="py-3 px-4">Gateway Transaction ID</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Proof</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-stone-400">
                    <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-saffron-600 border-t-transparent" />
                    <p className="text-xs text-stone-500 mt-2">Loading transactions...</p>
                  </td>
                </tr>
              ) : payments.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-stone-400">
                    No transactions matching selected filters.
                  </td>
                </tr>
              ) : (
                payments.map((p) => (
                  <tr key={p.id} className="hover:bg-stone-50/80 transition-colors">
                    <td className="py-3 px-4">
                      <span className="font-mono font-bold text-spice-black block">
                        #{p.order_number || p.order}
                      </span>
                      <span className="text-[11px] text-stone-500">{p.user_email}</span>
                    </td>
                    <td className="py-3 px-4 font-bold text-spice-black tabular-nums">
                      ₹{parseFloat(p.amount || 0).toFixed(2)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-spice-black block">
                          {p.gateway === 'COD'
                            ? 'Cash on Delivery'
                            : p.gateway === 'RAZORPAY'
                            ? 'Razorpay Online'
                            : p.gateway === 'PHONEPE_QR'
                            ? 'Legacy Manual UPI'
                            : p.gateway}
                        </span>
                        {p.gateway === 'PHONEPE_QR' && (
                          <Badge variant="stone" size="2xs">
                            Legacy
                          </Badge>
                        )}
                      </div>
                      <span className="text-[10px] text-stone-400">{p.payment_method}</span>
                    </td>
                    <td className="py-3 px-4">
                      {p.gateway_payment_id ? (
                        <span className="font-mono font-bold text-spice-black bg-stone-100 px-2 py-0.5 rounded border border-stone-200 select-all">
                          {p.gateway_payment_id}
                        </span>
                      ) : p.utr_number ? (
                        <span className="font-mono text-stone-700 bg-stone-100 px-2 py-0.5 rounded border border-stone-200 select-all">
                          UTR: {p.utr_number}
                        </span>
                      ) : (
                        <span className="font-mono text-stone-400 text-[11px]">
                          {p.gateway_order_id || 'Pending Gateway'}
                        </span>
                      )}
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
                    <td className="py-3 px-4">
                      {p.payment_screenshot ? (
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedPayment(p);
                            setIsScreenshotModalOpen(true);
                          }}
                          className="inline-flex items-center gap-1 text-saffron-700 hover:text-saffron-800 font-bold"
                        >
                          <ImageIcon className="h-3.5 w-3.5" />
                          <span>View Proof</span>
                        </button>
                      ) : (
                        <span className="text-stone-300">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-stone-500 text-[11px]">
                      {new Date(p.created_at).toLocaleDateString('en-IN', {
                        day: 'numeric',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {p.gateway === 'COD' && p.status === 'PENDING' ? (
                        <Button
                          variant="primary"
                          size="xs"
                          leftIcon={<Check className="h-3 w-3" />}
                          onClick={() => {
                            setSelectedPayment(p);
                            setIsCODCollectedModalOpen(true);
                          }}
                        >
                          Mark Collected
                        </Button>
                      ) : p.status === 'PENDING_VERIFICATION' ? (
                        <div className="inline-flex items-center gap-1.5">
                          <Button
                            variant="primary"
                            size="xs"
                            leftIcon={<Check className="h-3 w-3" />}
                            onClick={() => {
                              setSelectedPayment(p);
                              setIsVerifyModalOpen(true);
                            }}
                          >
                            Verify
                          </Button>
                          <Button
                            variant="outline"
                            size="xs"
                            className="text-red-600 border-red-200 hover:bg-red-50"
                            onClick={() => {
                              setSelectedPayment(p);
                              setIsRejectModalOpen(true);
                            }}
                          >
                            Reject
                          </Button>
                        </div>
                      ) : (
                        <span className="text-stone-400 text-[11px]">Completed</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* VERIFY CONFIRMATION MODAL */}
      <Modal
        isOpen={isVerifyModalOpen}
        onClose={() => setIsVerifyModalOpen(false)}
        title="Confirm Payment Verification"
        description={`Authoritatively mark payment as CAPTURED and confirm Order #${selectedPayment?.order_number}`}
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <Button variant="ghost" size="sm" onClick={() => setIsVerifyModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={isProcessingAction}
              onClick={handleVerify}
              leftIcon={<CheckCircle2 className="h-4 w-4" />}
            >
              Confirm &amp; Capture ₹{parseFloat(selectedPayment?.amount || 0).toFixed(2)}
            </Button>
          </div>
        }
      >
        <form onSubmit={handleVerify} className="space-y-3 py-2 text-xs">
          <div className="p-3 rounded-xl bg-stone-50 border border-stone-200 space-y-1">
            <div className="flex justify-between">
              <span className="text-stone-500">Customer UTR:</span>
              <strong className="font-mono text-spice-black select-all">{selectedPayment?.utr_number}</strong>
            </div>
            <div className="flex justify-between">
              <span className="text-stone-500">Order Reference:</span>
              <strong className="font-mono text-spice-black">#{selectedPayment?.order_number}</strong>
            </div>
            <div className="flex justify-between">
              <span className="text-stone-500">Amount:</span>
              <strong className="text-emerald-700">₹{parseFloat(selectedPayment?.amount || 0).toFixed(2)}</strong>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-spice-black mb-1">
              Internal Audit Notes (Optional)
            </label>
            <input
              type="text"
              value={verifyNotes}
              onChange={(e) => setVerifyNotes(e.target.value)}
              placeholder="e.g. Verified in Axis bank statement ending 4821"
              className="w-full px-3 py-2 rounded-lg border border-stone-300 text-xs focus:ring-2 focus:ring-saffron-500"
            />
          </div>
        </form>
      </Modal>

      {/* REJECT MODAL */}
      <Modal
        isOpen={isRejectModalOpen}
        onClose={() => setIsRejectModalOpen(false)}
        title="Reject Payment Reference"
        description={`Mark payment attempt as FAILED for Order #${selectedPayment?.order_number}`}
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <Button variant="ghost" size="sm" onClick={() => setIsRejectModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              isLoading={isProcessingAction}
              disabled={!rejectReason.trim()}
              onClick={handleReject}
            >
              Reject Payment
            </Button>
          </div>
        }
      >
        <form onSubmit={handleReject} className="space-y-3 py-2 text-xs">
          <p className="text-stone-600">
            Rejecting this payment will notify the customer and allow them to resubmit their genuine UTR reference.
          </p>
          <div>
            <label className="block text-xs font-bold text-spice-black mb-1">
              Reason for Rejection <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g. UTR not found in bank statement / Amount mismatch"
              className="w-full px-3 py-2 rounded-lg border border-stone-300 text-xs focus:ring-2 focus:ring-red-500"
            />
          </div>
        </form>
      </Modal>

      {/* SCREENSHOT MODAL */}
      <Modal
        isOpen={isScreenshotModalOpen}
        onClose={() => setIsScreenshotModalOpen(false)}
        title="Customer Payment Screenshot"
        description={`Uploaded for Order #${selectedPayment?.order_number}`}
      >
        {selectedPayment?.payment_screenshot && (
          <div className="py-2 flex items-center justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={selectedPayment.payment_screenshot}
              alt="Payment Screenshot"
              className="max-h-[70vh] rounded-lg border border-stone-200 object-contain shadow-md"
            />
          </div>
        )}
      </Modal>

      {/* CONFIRM COD COLLECTED MODAL */}
      <Modal
        isOpen={isCODCollectedModalOpen}
        onClose={() => setIsCODCollectedModalOpen(false)}
        title="Confirm COD Payment Collection"
        description={`Confirm cash collection for Order #${selectedPayment?.order_number}`}
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <Button
              variant="ghost"
              size="sm"
              disabled={isProcessingAction}
              onClick={() => setIsCODCollectedModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={isProcessingAction}
              onClick={handleConfirmCODCollected}
              leftIcon={<CheckCircle2 className="h-4 w-4" />}
            >
              Confirm Payment Collected
            </Button>
          </div>
        }
      >
        <div className="space-y-3 py-2 text-xs">
          <p className="text-stone-700 leading-relaxed">
            Confirm that payment of <strong className="text-emerald-700 font-bold">₹{parseFloat(selectedPayment?.amount || 0).toFixed(2)}</strong> has been collected for Order <strong className="text-spice-black font-mono">#{selectedPayment?.order_number}</strong>?
          </p>
          <div className="p-3 rounded-xl bg-stone-50 border border-stone-200 text-[11px] text-stone-600 space-y-1">
            <div className="flex justify-between">
              <span>Customer:</span>
              <strong className="text-spice-black">{selectedPayment?.user_email}</strong>
            </div>
            <div className="flex justify-between">
              <span>Payment Method:</span>
              <strong className="text-spice-black">Cash on Delivery (COD)</strong>
            </div>
            <div className="flex justify-between">
              <span>Action:</span>
              <span className="text-emerald-700 font-bold">Status &rarr; CAPTURED</span>
            </div>
          </div>
        </div>
      </Modal>
    </AdminLayout>
  );
}
