'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Boxes,
  Search,
  AlertTriangle,
  CheckCircle2,
  Edit2,
  RotateCcw,
  Save,
  Check,
} from 'lucide-react';
import AdminLayout from '../../../components/admin/AdminLayout';
import Button from '../../../components/common/Button';
import Badge from '../../../components/common/Badge';
import Modal from '../../../components/common/Modal';
import adminService from '../../../services/adminService';

function AdminInventoryContent() {
  const searchParams = useSearchParams();
  const initialLowStock = searchParams.get('low_stock') === 'true';

  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [lowStockOnly, setLowStockOnly] = useState(initialLowStock);
  const [errorMessage, setErrorMessage] = useState('');
  const [successToast, setSuccessToast] = useState('');

  // Edit Stock Modal
  const [selectedItem, setSelectedItem] = useState(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [newQuantity, setNewQuantity] = useState(0);
  const [newReorderLevel, setNewReorderLevel] = useState(10);
  const [isSaving, setIsSaving] = useState(false);

  const loadInventory = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage('');
    try {
      const res = await adminService.getInventory({
        search: searchQuery.trim(),
        low_stock: lowStockOnly,
      });
      const list = res?.results || (Array.isArray(res) ? res : []);
      setItems(list);
    } catch (err) {
      console.error('Error loading inventory:', err);
      setErrorMessage('Unable to fetch inventory balance.');
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, lowStockOnly]);

  useEffect(() => {
    loadInventory();
  }, [loadInventory]);

  const handleOpenEdit = (item) => {
    setSelectedItem(item);
    setNewQuantity(item.quantity_on_hand ?? 0);
    setNewReorderLevel(item.reorder_level ?? 10);
    setIsEditModalOpen(true);
  };

  const handleSaveStock = async (e) => {
    e.preventDefault();
    if (!selectedItem) return;
    setIsSaving(true);
    try {
      await adminService.updateStock(
        selectedItem.id || selectedItem.variant_id,
        parseInt(newQuantity) || 0,
        parseInt(newReorderLevel) || 10
      );
      setIsEditModalOpen(false);
      setSuccessToast(`Stock updated for ${selectedItem.variant_name} (${selectedItem.sku})`);
      setTimeout(() => setSuccessToast(''), 3500);
      loadInventory();
    } catch (err) {
      alert(err?.message || 'Failed to update inventory balance.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AdminLayout
      title="Warehouse Inventory &amp; Stock Levels"
      subtitle="Monitor cold storage inventory, reserved checkout allocations, and reorder triggers."
    >
      {/* Toast */}
      {successToast && (
        <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          <span className="font-bold">{successToast}</span>
        </div>
      )}

      {/* Control bar */}
      <div className="bg-white p-4 rounded-2xl border border-stone-200 shadow-xs mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              loadInventory();
            }}
            className="relative min-w-[240px]"
          >
            <Search className="h-4 w-4 text-stone-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search SKU or spice name..."
              className="w-full pl-9 pr-3 py-2 rounded-xl border border-stone-300 text-xs text-spice-black focus:outline-none focus:ring-2 focus:ring-saffron-500"
            />
          </form>

          <label className="flex items-center gap-2 text-xs font-semibold text-spice-black cursor-pointer select-none">
            <input
              type="checkbox"
              checked={lowStockOnly}
              onChange={(e) => setLowStockOnly(e.target.checked)}
              className="rounded border-stone-300 text-saffron-600 focus:ring-saffron-500 h-4 w-4"
            />
            <span>Show Low Stock Only</span>
          </label>
        </div>

        <Button
          variant="outline-stone"
          size="sm"
          onClick={loadInventory}
          leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
        >
          Refresh Balance
        </Button>
      </div>

      {/* Inventory Table */}
      <div className="bg-white rounded-2xl border border-stone-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-600 font-bold border-b border-stone-200 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Spice Product &amp; Variant</th>
                <th className="py-3 px-4">SKU Reference</th>
                <th className="py-3 px-4">Pack Size</th>
                <th className="py-3 px-4">On Hand</th>
                <th className="py-3 px-4">Reserved</th>
                <th className="py-3 px-4">Available</th>
                <th className="py-3 px-4">Reorder Level</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-stone-400">
                    <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-saffron-600 border-t-transparent" />
                    <p className="text-xs text-stone-500 mt-2">Checking warehouse stock...</p>
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-stone-400">
                    No inventory records match current filters.
                  </td>
                </tr>
              ) : (
                items.map((item) => {
                  const onHand = item.quantity_on_hand ?? 0;
                  const reserved = item.quantity_reserved ?? 0;
                  const available = item.quantity_available ?? (onHand - reserved);
                  const isLow = available <= (item.reorder_level ?? 10);

                  return (
                    <tr key={item.id || item.variant_id} className="hover:bg-stone-50/80 transition-colors">
                      <td className="py-3 px-4">
                        <span className="font-bold text-spice-black block">
                          {item.product_name || 'Spice Product'}
                        </span>
                        <span className="text-[11px] text-stone-500">
                          {item.variant_name}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono font-semibold text-spice-black">
                        {item.sku}
                      </td>
                      <td className="py-3 px-4 text-stone-600 font-medium">
                        {item.weight_in_grams}g
                      </td>
                      <td className="py-3 px-4 tabular-nums font-semibold text-stone-700">
                        {onHand}
                      </td>
                      <td className="py-3 px-4 tabular-nums text-amber-700">
                        {reserved > 0 ? `${reserved} reserved` : '0'}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold tabular-nums ${
                            isLow
                              ? 'bg-red-100 text-red-800'
                              : 'bg-emerald-100 text-emerald-800'
                          }`}
                        >
                          {available} units
                        </span>
                      </td>
                      <td className="py-3 px-4 tabular-nums text-stone-500">
                        {item.reorder_level ?? 10}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          variant="outline-stone"
                          size="xs"
                          onClick={() => handleOpenEdit(item)}
                          leftIcon={<Edit2 className="h-3 w-3" />}
                        >
                          Adjust
                        </Button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* EDIT INVENTORY MODAL */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        title="Adjust Warehouse Stock"
        description={`Variant: ${selectedItem?.product_name} (${selectedItem?.variant_name})`}
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <Button variant="ghost" size="sm" onClick={() => setIsEditModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={isSaving}
              onClick={handleSaveStock}
              leftIcon={<Save className="h-4 w-4" />}
            >
              Save Stock Balance
            </Button>
          </div>
        }
      >
        <form onSubmit={handleSaveStock} className="space-y-4 py-2 text-xs">
          <div className="p-3.5 rounded-xl bg-stone-50 border border-stone-200 text-xs space-y-1">
            <div className="flex justify-between">
              <span className="text-stone-500">SKU:</span>
              <span className="font-mono font-bold text-spice-black">{selectedItem?.sku}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-stone-500">Currently Reserved:</span>
              <span className="font-bold text-amber-700">{selectedItem?.quantity_reserved ?? 0} units</span>
            </div>
          </div>

          <div>
            <label className="block font-bold text-spice-black mb-1">
              Quantity on Hand (Physical Warehouse Total) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              min={selectedItem?.quantity_reserved || 0}
              required
              value={newQuantity}
              onChange={(e) => setNewQuantity(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-stone-300 text-xs font-mono font-bold text-spice-black focus:ring-2 focus:ring-saffron-500"
            />
            <span className="text-[11px] text-stone-500 mt-1 block">
              Must be at least {selectedItem?.quantity_reserved || 0} to satisfy active customer reservations.
            </span>
          </div>

          <div>
            <label className="block font-bold text-spice-black mb-1">
              Reorder Warning Threshold (Units)
            </label>
            <input
              type="number"
              min={0}
              value={newReorderLevel}
              onChange={(e) => setNewReorderLevel(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-stone-300 text-xs font-mono text-spice-black focus:ring-2 focus:ring-saffron-500"
            />
          </div>
        </form>
      </Modal>
    </AdminLayout>
  );
}

export default function AdminInventoryPage() {
  return (
    <React.Suspense
      fallback={
        <div className="min-h-[60vh] flex items-center justify-center">
          <div className="h-8 w-8 rounded-full border-2 border-saffron-600 border-t-transparent animate-spin" />
        </div>
      }
    >
      <AdminInventoryContent />
    </React.Suspense>
  );
}
