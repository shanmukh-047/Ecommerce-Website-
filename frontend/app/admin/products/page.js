'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Image from 'next/image';
import {
  Package,
  Plus,
  Search,
  Upload,
  Edit2,
  Trash2,
  Check,
  AlertCircle,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import AdminLayout from '../../../components/admin/AdminLayout';
import Button from '../../../components/common/Button';
import Badge from '../../../components/common/Badge';
import Modal from '../../../components/common/Modal';
import adminService from '../../../services/adminService';

export default function AdminProductsPage() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // Add Product Modal
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isSubmittingProduct, setIsSubmittingProduct] = useState(false);
  const [productForm, setProductForm] = useState({
    name: '',
    category: '',
    tier: 'MALENADU_PRIME',
    form: 'WHOLE',
    short_description: '',
    variant_name: 'Standard Pack',
    weight_in_grams: 100,
    mrp: '150.00',
    selling_price: '135.00',
    initial_stock: 50,
    hsn_code: '0910',
    origin_region: 'Malenadu, Karnataka',
  });

  // Image Upload Modal
  const [isImageModalOpen, setIsImageModalOpen] = useState(false);
  const [selectedProductId, setSelectedProductId] = useState(null);
  const [imageFile, setImageFile] = useState(null);
  const [isUploadingImage, setIsUploadingImage] = useState(false);

  const loadCatalogData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage('');
    try {
      const [prodsRes, catsRes] = await Promise.all([
        adminService.getProducts({ search: searchQuery.trim(), category: selectedCategory }),
        adminService.getCategories(),
      ]);
      const prodList = prodsRes?.results || (Array.isArray(prodsRes) ? prodsRes : []);
      setProducts(prodList);
      setCategories(Array.isArray(catsRes) ? catsRes : catsRes?.results || []);
    } catch (err) {
      console.error('Error fetching catalog data:', err);
      setErrorMessage('Unable to load catalog products. Please retry.');
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, selectedCategory]);

  useEffect(() => {
    loadCatalogData();
  }, [loadCatalogData]);

  // Handle Add Product Submit
  const handleCreateProduct = async (e) => {
    e.preventDefault();
    if (!productForm.name || !productForm.category) {
      alert('Please fill out product name and category.');
      return;
    }
    setIsSubmittingProduct(true);
    try {
      await adminService.createProduct(productForm);
      setIsAddModalOpen(false);
      // Reset form
      setProductForm({
        name: '',
        category: categories[0]?.id || '',
        tier: 'MALENADU_PRIME',
        form: 'WHOLE',
        short_description: '',
        variant_name: 'Standard Pack',
        weight_in_grams: 100,
        mrp: '150.00',
        selling_price: '135.00',
        initial_stock: 50,
        hsn_code: '0910',
        origin_region: 'Malenadu, Karnataka',
      });
      loadCatalogData();
    } catch (err) {
      alert(err?.message || 'Failed to create product.');
    } finally {
      setIsSubmittingProduct(false);
    }
  };

  // Handle Image Upload
  const handleUploadImage = async (e) => {
    e.preventDefault();
    if (!selectedProductId || !imageFile) return;
    setIsUploadingImage(true);
    try {
      await adminService.uploadProductImage(selectedProductId, imageFile, true);
      setIsImageModalOpen(false);
      setImageFile(null);
      setSelectedProductId(null);
      loadCatalogData();
    } catch (err) {
      alert(err?.message || 'Failed to upload image.');
    } finally {
      setIsUploadingImage(false);
    }
  };

  return (
    <AdminLayout
      title="Estate Spices Catalog"
      subtitle="Manage single-origin spices, variants, pricing, and photography assets."
    >
      {/* Control bar */}
      <div className="bg-white p-4 rounded-2xl border border-stone-200 shadow-xs mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              loadCatalogData();
            }}
            className="relative min-w-[240px]"
          >
            <Search className="h-4 w-4 text-stone-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search spices, SKU..."
              className="w-full pl-9 pr-3 py-2 rounded-xl border border-stone-300 text-xs text-spice-black focus:outline-none focus:ring-2 focus:ring-saffron-500"
            />
          </form>

          {/* Category Dropdown */}
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-3 py-2 rounded-xl border border-stone-300 text-xs text-spice-black focus:outline-none focus:ring-2 focus:ring-saffron-500"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.slug || c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        <Button
          variant="primary"
          size="sm"
          onClick={() => {
            if (categories.length > 0 && !productForm.category) {
              setProductForm((prev) => ({ ...prev, category: categories[0].id }));
            }
            setIsAddModalOpen(true);
          }}
          leftIcon={<Plus className="h-4 w-4" />}
        >
          Add New Spice
        </Button>
      </div>

      {/* Products Table */}
      <div className="bg-white rounded-2xl border border-stone-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-600 font-bold border-b border-stone-200 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Spice Product</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Tier</th>
                <th className="py-3 px-4">Primary Variant</th>
                <th className="py-3 px-4">Price (MRP / Sell)</th>
                <th className="py-3 px-4">Available Stock</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-stone-400">
                    <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-saffron-600 border-t-transparent" />
                    <p className="text-xs text-stone-500 mt-2">Loading spice catalog...</p>
                  </td>
                </tr>
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-stone-400">
                    No products found matching filters.
                  </td>
                </tr>
              ) : (
                products.map((prod) => {
                  const primaryVariant = prod.variants?.[0] || {};
                  const stockQty = primaryVariant.stock_item?.quantity_on_hand ?? 0;
                  const thumb = prod.images?.[0]?.image_url || '/placeholder-spice.jpg';

                  return (
                    <tr key={prod.id} className="hover:bg-stone-50/80 transition-colors">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-stone-100 border border-stone-200 overflow-hidden relative shrink-0">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                              src={thumb}
                              alt={prod.name}
                              className="w-full h-full object-cover"
                            />
                          </div>
                          <div>
                            <span className="font-bold text-spice-black block">{prod.name}</span>
                            <span className="text-[10px] text-stone-400 font-mono">
                              SKU: {primaryVariant.sku || prod.slug}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-stone-600 font-medium">
                        {prod.category?.name || 'Spices'}
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="stone" size="xs">
                          {prod.tier}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-semibold text-spice-black block">
                          {primaryVariant.variant_name || 'Standard'}
                        </span>
                        <span className="text-[10px] text-stone-400">
                          {primaryVariant.weight_in_grams}g
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-bold text-spice-black tabular-nums block">
                          ₹{parseFloat(primaryVariant.selling_price || 0).toFixed(2)}
                        </span>
                        <span className="text-[10px] text-stone-400 line-through tabular-nums">
                          ₹{parseFloat(primaryVariant.mrp || 0).toFixed(2)}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold tabular-nums ${
                            stockQty <= 10
                              ? 'bg-red-100 text-red-800'
                              : 'bg-emerald-100 text-emerald-800'
                          }`}
                        >
                          {stockQty} units
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedProductId(prod.id);
                              setIsImageModalOpen(true);
                            }}
                            title="Upload Photo"
                            className="p-1.5 rounded-lg text-stone-500 hover:text-saffron-700 hover:bg-stone-100 transition-colors"
                          >
                            <Upload className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ADD SPICE MODAL */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Add Single-Origin Spice Product"
        description="Register master product with initial variant and inventory balance."
        size="lg"
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <Button variant="ghost" size="sm" onClick={() => setIsAddModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={isSubmittingProduct}
              onClick={handleCreateProduct}
            >
              Save Product &amp; Allocate Stock
            </Button>
          </div>
        }
      >
        <form onSubmit={handleCreateProduct} className="space-y-4 py-1 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-bold text-spice-black mb-1">
                Spice Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={productForm.name}
                onChange={(e) => setProductForm({ ...productForm, name: e.target.value })}
                placeholder="e.g. Malenadu Green Cardamom"
                className="w-full px-3 py-2 rounded-lg border border-stone-300 text-xs focus:ring-2 focus:ring-saffron-500"
              />
            </div>

            <div>
              <label className="block font-bold text-spice-black mb-1">
                Category <span className="text-red-500">*</span>
              </label>
              <select
                required
                value={productForm.category}
                onChange={(e) => setProductForm({ ...productForm, category: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-stone-300 text-xs focus:ring-2 focus:ring-saffron-500"
              >
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block font-bold text-spice-black mb-1">Spice Form</label>
              <select
                value={productForm.form}
                onChange={(e) => setProductForm({ ...productForm, form: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-stone-300 text-xs focus:ring-2 focus:ring-saffron-500"
              >
                <option value="WHOLE">Whole Spice</option>
                <option value="POWDER">Cold-Milled Powder</option>
                <option value="BLEND">Traditional Masala Blend</option>
              </select>
            </div>

            <div>
              <label className="block font-bold text-spice-black mb-1">Tier / Grade</label>
              <select
                value={productForm.tier}
                onChange={(e) => setProductForm({ ...productForm, tier: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-stone-300 text-xs focus:ring-2 focus:ring-saffron-500"
              >
                <option value="RESERVE">Reserve (Estate Harvest)</option>
                <option value="MALENADU_PRIME">Malenadu Prime</option>
                <option value="DAILY_ESSENTIALS">Daily Essentials</option>
              </select>
            </div>

            <div>
              <label className="block font-bold text-spice-black mb-1">HSN Code</label>
              <input
                type="text"
                value={productForm.hsn_code}
                onChange={(e) => setProductForm({ ...productForm, hsn_code: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-stone-300 text-xs focus:ring-2 focus:ring-saffron-500"
              />
            </div>
          </div>

          <div className="border-t border-stone-200 pt-3">
            <span className="font-bold text-spice-black text-[11px] uppercase tracking-wider block mb-2">
              Primary Packaging Variant &amp; Inventory
            </span>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div>
                <label className="block font-bold text-spice-black mb-1">Pack Size (g)</label>
                <input
                  type="number"
                  value={productForm.weight_in_grams}
                  onChange={(e) =>
                    setProductForm({ ...productForm, weight_in_grams: parseInt(e.target.value) || 100 })
                  }
                  className="w-full px-3 py-2 rounded-lg border border-stone-300 text-xs"
                />
              </div>
              <div>
                <label className="block font-bold text-spice-black mb-1">MRP (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  value={productForm.mrp}
                  onChange={(e) => setProductForm({ ...productForm, mrp: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-stone-300 text-xs"
                />
              </div>
              <div>
                <label className="block font-bold text-spice-black mb-1">Selling Price (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  value={productForm.selling_price}
                  onChange={(e) => setProductForm({ ...productForm, selling_price: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-stone-300 text-xs"
                />
              </div>
              <div>
                <label className="block font-bold text-spice-black mb-1">Initial Stock</label>
                <input
                  type="number"
                  value={productForm.initial_stock}
                  onChange={(e) =>
                    setProductForm({ ...productForm, initial_stock: parseInt(e.target.value) || 0 })
                  }
                  className="w-full px-3 py-2 rounded-lg border border-stone-300 text-xs"
                />
              </div>
            </div>
          </div>
        </form>
      </Modal>

      {/* UPLOAD IMAGE MODAL */}
      <Modal
        isOpen={isImageModalOpen}
        onClose={() => setIsImageModalOpen(false)}
        title="Upload Spice Photography"
        description="Upload high-resolution authentic estate photograph."
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <Button variant="ghost" size="sm" onClick={() => setIsImageModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={isUploadingImage}
              disabled={!imageFile}
              onClick={handleUploadImage}
            >
              Upload Photo
            </Button>
          </div>
        }
      >
        <div className="space-y-4 py-2 text-xs">
          <div className="border-2 border-dashed border-stone-300 rounded-xl p-6 text-center">
            <Upload className="h-8 w-8 text-stone-400 mx-auto mb-2" />
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setImageFile(e.target.files?.[0] || null)}
              className="text-xs text-stone-500"
            />
          </div>
        </div>
      </Modal>
    </AdminLayout>
  );
}
