'use client';

import React, { useState, useEffect, useCallback, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import {
  Truck,
  Search,
  MapPin,
  Calendar,
  Clock,
  ShieldCheck,
  ArrowRight,
  Package,
  AlertCircle,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';
import shippingService from '../../services/shippingService';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import Card from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import Skeleton from '../../components/common/Skeleton';
import EmptyState from '../../components/common/EmptyState';
import ErrorState from '../../components/common/ErrorState';

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

function TrackContent() {
  const searchParams = useSearchParams();
  const initialAwb = searchParams.get('awb') || searchParams.get('shipment') || '';

  const [query, setQuery] = useState(initialAwb);
  const [trackingData, setTrackingData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchedQuery, setSearchedQuery] = useState('');

  const handleTrack = useCallback(async (trackingRef) => {
    const trimmed = (trackingRef || query || '').trim();
    if (!trimmed) return;

    setIsLoading(true);
    setError(null);
    setSearchedQuery(trimmed);

    try {
      const data = await shippingService.trackPublic(trimmed);
      setTrackingData(data);
    } catch (err) {
      setTrackingData(null);
      setError(
        err.message ||
          'No shipment found matching the provided tracking reference. Please verify your AWB or order details.'
      );
    } finally {
      setIsLoading(false);
    }
  }, [query]);

  // Auto-search if query param provided in URL
  useEffect(() => {
    if (initialAwb) {
      handleTrack(initialAwb);
    }
  }, [initialAwb, handleTrack]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    handleTrack(query);
  };

  const statusCfg = trackingData?.status
    ? SHIPMENT_STATUS_CONFIG[trackingData.status] || {
        label: trackingData.status,
        bg: 'bg-stone-100 text-stone-800 border-stone-200',
      }
    : null;

  const events = trackingData?.tracking_events || trackingData?.events || [];

  return (
    <div className="min-h-screen bg-spice-canvas pb-20 pt-8 sm:pt-12">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 space-y-8">
        {/* Header Hero */}
        <div className="text-center space-y-3 max-w-2xl mx-auto">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-saffron-100 text-saffron-800 border border-saffron-300 shadow-xs mb-1">
            <Truck className="h-6 w-6" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold font-display text-spice-black tracking-tight">
            Track Your Spice Consignment
          </h1>
          <p className="text-xs sm:text-sm text-spice-stone">
            Enter your carrier AWB (Air Waybill) or Shipment Number to view live transit updates directly from our Western Ghats dispatch hub.
          </p>
        </div>

        {/* Search Bar Card */}
        <Card variant="elevated" padding="md" className="rounded-2xl max-w-2xl mx-auto">
          <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-spice-muted" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter AWB or Shipment No. (e.g. BMP-AWB-XXXX or SHP-...)"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-spice-border bg-white text-xs text-spice-black focus:border-saffron-600 focus:outline-none placeholder:text-spice-muted transition-all"
              />
            </div>
            <Button
              type="submit"
              variant="primary"
              size="md"
              disabled={!query.trim() || isLoading}
              isLoading={isLoading}
              className="shrink-0"
              leftIcon={<Search className="h-4 w-4" />}
            >
              Track Package
            </Button>
          </form>

          <div className="mt-3 flex items-center justify-between text-[11px] text-spice-muted pt-2 border-t border-spice-borderSubtle">
            <span className="flex items-center gap-1">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
              Public Tracking (Customer PII is securely redacted)
            </span>
            <Link href="/account/orders" className="text-saffron-700 hover:text-saffron-800 font-semibold">
              Signed in? View My Orders &rarr;
            </Link>
          </div>
        </Card>

        {/* Loading State */}
        {isLoading && (
          <div className="max-w-2xl mx-auto space-y-4">
            <Skeleton height="140px" className="w-full rounded-2xl" />
            <Skeleton height="240px" className="w-full rounded-2xl" />
          </div>
        )}

        {/* Error State */}
        {!isLoading && error && (
          <div className="max-w-2xl mx-auto">
            <ErrorState
              title="Consignment Not Found"
              message={error}
              retryLabel="Search Again"
              onRetry={() => handleTrack(searchedQuery)}
              className="rounded-2xl border border-spice-border bg-white p-8"
            />
          </div>
        )}

        {/* Tracking Details View */}
        {!isLoading && !error && trackingData && (
          <div className="max-w-2xl mx-auto space-y-6">
            {/* Status Summary Card */}
            <div className="rounded-2xl border border-spice-border bg-white p-6 shadow-subtle space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-spice-borderSubtle pb-4 gap-3">
                <div>
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-mono text-base font-bold text-spice-black">
                      AWB: {trackingData.awb_number || trackingData.shipment_number}
                    </span>
                    {statusCfg && (
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-bold ${statusCfg.bg}`}
                      >
                        <span className="h-1.5 w-1.5 rounded-full bg-current" />
                        {statusCfg.label}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-spice-stone">
                    Consignment Ref: <span className="font-mono font-semibold">{trackingData.shipment_number}</span>
                  </p>
                </div>

                <div className="text-left sm:text-right">
                  <span className="text-xs text-spice-muted block">Carrier Partner</span>
                  <span className="text-sm font-bold text-spice-black">{trackingData.courier_name}</span>
                </div>
              </div>

              {/* Delivery Schedule Banner */}
              {trackingData.estimated_delivery_date && (
                <div className="flex items-center gap-3 p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs text-emerald-900">
                  <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
                  <div>
                    <span className="block font-semibold">
                      Estimated Delivery by{' '}
                      {new Date(trackingData.estimated_delivery_date).toLocaleDateString('en-IN', {
                        weekday: 'long',
                        day: 'numeric',
                        month: 'long',
                        year: 'numeric',
                      })}
                    </span>
                    <span className="text-[11px] text-emerald-700">
                      Standard cold-chain spice preservation in transit.
                    </span>
                  </div>
                </div>
              )}

              {trackingData.shipped_at && (
                <p className="text-xs text-spice-stone flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5 text-spice-muted" />
                  <span>
                    Dispatched on{' '}
                    {new Date(trackingData.shipped_at).toLocaleDateString('en-IN', {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </p>
              )}
            </div>

            {/* Tracking Events Timeline */}
            <div className="rounded-2xl border border-spice-border bg-white p-6 shadow-subtle">
              <h3 className="text-sm font-bold font-display text-spice-black uppercase tracking-wider mb-6 flex items-center gap-2">
                <Clock className="h-4 w-4 text-saffron-700" />
                <span>Consignment Transit History</span>
              </h3>

              {events.length === 0 ? (
                <div className="py-8 text-center text-xs text-spice-stone">
                  <Package className="h-8 w-8 text-spice-muted mx-auto mb-2" />
                  <p className="font-semibold text-spice-black">Label Created</p>
                  <p className="text-[11px] text-spice-muted mt-0.5">
                    Carrier has been notified. Milestone scans will update automatically upon parcel pickup.
                  </p>
                </div>
              ) : (
                <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-spice-border">
                  {events.map((evt, idx) => (
                    <div key={evt.id || idx} className="relative text-xs">
                      <div className="absolute -left-6 top-1 h-3 w-3 rounded-full bg-saffron-600 ring-4 ring-white" />
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-bold text-spice-black text-sm">{evt.status}</span>
                          {evt.location && (
                            <span className="text-xs font-semibold text-saffron-800 bg-saffron-50 px-2 py-0.5 rounded border border-saffron-200">
                              {evt.location}
                            </span>
                          )}
                          <span className="text-[11px] text-spice-muted ml-auto">
                            {new Date(evt.event_timestamp || evt.created_at).toLocaleString('en-IN', {
                              day: 'numeric',
                              month: 'short',
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        </div>
                        {evt.description && (
                          <p className="text-xs text-spice-stone mt-1 leading-relaxed">
                            {evt.description}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Empty State before any search */}
        {!isLoading && !error && !trackingData && !initialAwb && (
          <div className="max-w-2xl mx-auto rounded-2xl border border-dashed border-spice-border bg-white p-10 text-center space-y-3">
            <Package className="h-10 w-10 text-spice-muted mx-auto" />
            <h3 className="text-sm font-bold text-spice-black">Ready to Track</h3>
            <p className="text-xs text-spice-stone max-w-sm mx-auto">
              Find your AWB tracking number in your dispatch SMS, email invoice, or Order History dashboard.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function TrackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-spice-canvas py-12 flex items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-3 border-saffron-600 border-t-transparent" />
        </div>
      }
    >
      <TrackContent />
    </Suspense>
  );
}
