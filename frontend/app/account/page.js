'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  User,
  Mail,
  Phone,
  Building2,
  MapPin,
  Package,
  Plus,
  Trash2,
  Edit2,
  CheckCircle2,
  AlertTriangle,
  LogOut,
  Calendar,
  Shield,
  Lock,
  Eye,
  EyeOff,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../components/common/Toast';
import RouteGuard from '../../components/common/RouteGuard';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import Card from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import Modal from '../../components/common/Modal';
import Select from '../../components/common/Select';
import authService from '../../services/authService';
import orderService from '../../services/orderService';

const INDIAN_STATES = [
  { value: 'KA', label: 'Karnataka' },
  { value: 'KL', label: 'Kerala' },
  { value: 'TN', label: 'Tamil Nadu' },
  { value: 'AP', label: 'Andhra Pradesh' },
  { value: 'TS', label: 'Telangana' },
  { value: 'MH', label: 'Maharashtra' },
  { value: 'GA', label: 'Goa' },
  { value: 'GJ', label: 'Gujarat' },
  { value: 'DL', label: 'Delhi' },
  { value: 'RJ', label: 'Rajasthan' },
  { value: 'UP', label: 'Uttar Pradesh' },
  { value: 'WB', label: 'West Bengal' },
  { value: 'MP', label: 'Madhya Pradesh' },
  { value: 'PB', label: 'Punjab' },
  { value: 'HR', label: 'Haryana' },
  { value: 'OD', label: 'Odisha' },
  { value: 'AS', label: 'Assam' },
  { value: 'BR', label: 'Bihar' },
  { value: 'CG', label: 'Chhattisgarh' },
  { value: 'JH', label: 'Jharkhand' },
  { value: 'UK', label: 'Uttarakhand' },
  { value: 'HP', label: 'Himachal Pradesh' },
  { value: 'JK', label: 'Jammu and Kashmir' },
  { value: 'PY', label: 'Puducherry' },
  { value: 'CH', label: 'Chandigarh' },
  { value: 'SK', label: 'Sikkim' },
  { value: 'TR', label: 'Tripura' },
  { value: 'ML', label: 'Meghalaya' },
  { value: 'MN', label: 'Manipur' },
  { value: 'MZ', label: 'Mizoram' },
  { value: 'NL', label: 'Nagaland' },
  { value: 'AR', label: 'Arunachal Pradesh' },
  { value: 'AN', label: 'Andaman & Nicobar' },
  { value: 'DN', label: 'Dadra & Nagar Haveli' },
  { value: 'LD', label: 'Lakshadweep' },
  { value: 'LA', label: 'Ladakh' },
];

const ADDRESS_TYPES = [
  { value: 'HOME', label: 'Home (All Day Delivery)' },
  { value: 'WORK', label: 'Office / Commercial (10 AM - 6 PM)' },
  { value: 'OTHER', label: 'Other' },
];

const STATUS_CONFIG = {
  PENDING_PAYMENT: { label: 'Payment Pending', bg: 'bg-amber-50 text-amber-800 border-amber-200' },
  CONFIRMED: { label: 'Confirmed', bg: 'bg-saffron-50 text-saffron-800 border-saffron-200' },
  PROCESSING: { label: 'Processing', bg: 'bg-blue-50 text-blue-800 border-blue-200' },
  SHIPPED: { label: 'Shipped', bg: 'bg-purple-50 text-purple-800 border-purple-200' },
  DELIVERED: { label: 'Delivered', bg: 'bg-emerald-50 text-emerald-800 border-emerald-200' },
  CANCELLED: { label: 'Cancelled', bg: 'bg-red-50 text-red-700 border-red-200' },
  FAILED: { label: 'Payment Failed', bg: 'bg-red-50 text-red-700 border-red-200' },
  REFUNDED: { label: 'Refunded', bg: 'bg-stone-100 text-stone-700 border-stone-200' },
};

export default function AccountPage() {
  const { user, isAuthenticated, isWholesale, logout, refreshProfile } = useAuth();
  const { success, error: showError } = useToast();

  const [activeTab, setActiveTab] = useState('profile'); // 'profile' | 'orders' | 'addresses'

  // Profile Edit Modal State
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editFirstName, setEditFirstName] = useState('');
  const [editLastName, setEditLastName] = useState('');
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);

  // Address Book State
  const [addresses, setAddresses] = useState([]);
  const [isLoadingAddresses, setIsLoadingAddresses] = useState(true);
  const [isAddAddressOpen, setIsAddAddressOpen] = useState(false);
  const [isSavingAddress, setIsSavingAddress] = useState(false);
  const [addressForm, setAddressForm] = useState({
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

  // Recent Orders State
  const [recentOrders, setRecentOrders] = useState([]);
  const [isLoadingOrders, setIsLoadingOrders] = useState(true);
  const [ordersError, setOrdersError] = useState(null);

  // Security / Change Password State
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmNewPassword, setShowConfirmNewPassword] = useState(false);
  const [passwordErrors, setPasswordErrors] = useState({});
  const [passwordApiError, setPasswordApiError] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordSuccessMessage, setPasswordSuccessMessage] = useState('');

  // Fetch addresses
  const loadAddresses = useCallback(async () => {
    try {
      const data = await authService.getAddresses();
      setAddresses(Array.isArray(data) ? data : data?.results || []);
    } catch {
      setAddresses([]);
    } finally {
      setIsLoadingAddresses(false);
    }
  }, []);

  // Fetch recent orders
  const loadRecentOrders = useCallback(async () => {
    setIsLoadingOrders(true);
    setOrdersError(null);
    try {
      const res = await orderService.getOrders(1);
      const list = res?.results || (Array.isArray(res) ? res : []);
      setRecentOrders(list);
    } catch (err) {
      setOrdersError(err.message || 'Unable to fetch recent orders');
    } finally {
      setIsLoadingOrders(false);
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    loadAddresses();
    loadRecentOrders();
  }, [isAuthenticated, loadAddresses, loadRecentOrders]);

  const openEditModal = () => {
    setEditFirstName(user?.first_name || '');
    setEditLastName(user?.last_name || '');
    setIsEditModalOpen(true);
  };

  const handleUpdateProfile = async (e) => {
    e?.preventDefault();
    setIsUpdatingProfile(true);
    try {
      await authService.updateMe({
        first_name: editFirstName.trim(),
        last_name: editLastName.trim(),
      });
      await refreshProfile();
      success('Profile details updated successfully', 'Profile Updated');
      setIsEditModalOpen(false);
    } catch (err) {
      showError(err.message || 'Could not update profile', 'Update Error');
    } finally {
      setIsUpdatingProfile(false);
    }
  };

  const handleSaveAddress = async (e) => {
    e?.preventDefault();
    if (!addressForm.recipient_name || !addressForm.phone_number || !addressForm.address_line_1 || !addressForm.pincode) {
      showError('Please fill in all required address fields', 'Validation Notice');
      return;
    }

    setIsSavingAddress(true);
    try {
      await authService.addAddress(addressForm);
      success('Address added to your address book', 'Address Saved');
      setIsAddAddressOpen(false);
      setAddressForm({
        recipient_name: '',
        phone_number: '',
        address_line_1: '',
        address_line_2: '',
        landmark: '',
        city: '',
        state: 'KA',
        pincode: '',
        address_type: 'HOME',
        is_default_shipping: false,
      });
      loadAddresses();
    } catch (err) {
      showError(err.message || 'Could not save address', 'Error');
    } finally {
      setIsSavingAddress(false);
    }
  };

  const handleDeleteAddress = async (id) => {
    try {
      await authService.deleteAddress(id);
      success('Address removed', 'Deleted');
      loadAddresses();
    } catch (err) {
      showError(err.message || 'Failed to remove address', 'Error');
    }
  };

  const validatePasswordChange = () => {
    const errs = {};
    if (!currentPassword) {
      errs.currentPassword = 'Current password is required.';
    }
    if (!newPassword) {
      errs.newPassword = 'New password is required.';
    } else if (newPassword.length < 8) {
      errs.newPassword = 'New password must be at least 8 characters long.';
    }
    if (!confirmNewPassword) {
      errs.confirmNewPassword = 'Confirmation password is required.';
    } else if (newPassword !== confirmNewPassword) {
      errs.confirmNewPassword = 'New passwords do not match.';
    }
    if (currentPassword && newPassword && currentPassword === newPassword) {
      errs.newPassword = 'New password must be different from current password.';
    }
    setPasswordErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleChangePassword = async (e) => {
    e?.preventDefault();
    setPasswordApiError('');
    setPasswordSuccessMessage('');

    if (!validatePasswordChange()) return;

    setIsChangingPassword(true);
    try {
      await authService.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmNewPassword,
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmNewPassword('');
      setPasswordSuccessMessage('Password changed successfully! Your account credentials have been updated.');
      success('Your password has been changed securely.', 'Password Updated');
    } catch (err) {
      console.error('Change password error:', err);
      if (err.details && typeof err.details === 'object') {
        const fieldErrors = {};
        for (const [key, val] of Object.entries(err.details)) {
          const msg = Array.isArray(val) ? val.join(' ') : String(val);
          if (key === 'current_password') fieldErrors.currentPassword = msg;
          else if (key === 'new_password') fieldErrors.newPassword = msg;
          else if (key === 'confirm_password') fieldErrors.confirmNewPassword = msg;
          else fieldErrors.general = msg;
        }
        if (Object.keys(fieldErrors).length > 0) {
          setPasswordErrors(fieldErrors);
          if (fieldErrors.general) setPasswordApiError(fieldErrors.general);
        }
      } else {
        setPasswordApiError(err.userMessage || err.message || 'Failed to update password. Please check your current password.');
      }
    } finally {
      setIsChangingPassword(false);
    }
  };

  const wholesaleProfile = user?.wholesale_profile;
  const verificationStatus = wholesaleProfile?.verification_status;

  return (
    <RouteGuard>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        {/* User Greeting & Stats Banner */}
        <div className="rounded-2xl bg-white border border-spice-border p-6 sm:p-8 shadow-subtle mb-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-saffron-100 text-2xl font-bold font-serif text-saffron-800 border border-saffron-300 shadow-xs">
                {(user?.first_name?.[0] || user?.email?.[0] || 'U').toUpperCase()}
              </div>

              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h1 className="text-xl sm:text-2xl font-bold font-display text-spice-black">
                    {user?.full_name || user?.first_name || 'Valued Customer'}
                  </h1>
                  {isWholesale ? (
                    <Badge variant="cardamom" size="sm" hasDot>
                      Verified Wholesale Buyer
                    </Badge>
                  ) : verificationStatus === 'PENDING' ? (
                    <Badge variant="warning" size="sm" hasDot>
                      B2B Verification Pending
                    </Badge>
                  ) : (
                    <Badge variant="stone" size="sm">
                      Retail Member
                    </Badge>
                  )}
                </div>

                <div className="flex items-center gap-4 text-xs text-spice-stone mt-1.5 flex-wrap">
                  <span className="flex items-center gap-1">
                    <Mail className="h-3.5 w-3.5 text-spice-muted" />
                    {user?.email}
                  </span>
                  {user?.phone_number && (
                    <span className="flex items-center gap-1">
                      <Phone className="h-3.5 w-3.5 text-spice-muted" />
                      {user?.phone_number}
                    </span>
                  )}
                  {user?.date_joined && (
                    <span className="flex items-center gap-1 text-spice-muted">
                      <Calendar className="h-3.5 w-3.5" />
                      Member since {new Date(user.date_joined).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Button
                variant="outline-stone"
                size="sm"
                onClick={openEditModal}
                leftIcon={<Edit2 className="h-3.5 w-3.5" />}
              >
                Edit Profile
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={logout}
                leftIcon={<LogOut className="h-3.5 w-3.5 text-red-500" />}
                className="text-red-600 hover:bg-red-50 hover:text-red-700"
              >
                Sign Out
              </Button>
            </div>
          </div>
        </div>

        {/* Wholesale Status Notice (if applicant) */}
        {wholesaleProfile && (
          <div className="mb-8">
            <Card
              variant={
                verificationStatus === 'APPROVED'
                  ? 'default'
                  : verificationStatus === 'REJECTED'
                  ? 'flat'
                  : 'elevated'
              }
              padding="md"
              className={
                verificationStatus === 'PENDING'
                  ? 'border-amber-200 bg-amber-50/40'
                  : verificationStatus === 'REJECTED'
                  ? 'border-red-200 bg-red-50/40'
                  : 'border-emerald-200 bg-emerald-50/30'
              }
            >
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-xl bg-white shadow-2xs shrink-0 mt-0.5">
                  <Building2 className="h-5 w-5 text-spice-black" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 flex-wrap mb-1">
                    <h3 className="text-sm font-bold text-spice-black">
                      B2B Account: {wholesaleProfile.company_name}
                    </h3>
                    <Badge
                      variant={
                        verificationStatus === 'APPROVED'
                          ? 'cardamom'
                          : verificationStatus === 'REJECTED'
                          ? 'danger'
                          : 'warning'
                      }
                      size="sm"
                    >
                      Status: {verificationStatus}
                    </Badge>
                  </div>

                  <p className="text-xs text-spice-stone">
                    GSTIN: <span className="font-mono">{wholesaleProfile.masked_gstin}</span> • PAN: <span className="font-mono">{wholesaleProfile.masked_pan}</span> • Business Type: {wholesaleProfile.business_type}
                  </p>

                  {verificationStatus === 'PENDING' && (
                    <div className="mt-2.5 flex items-center gap-1.5 text-xs text-amber-800 bg-white/70 p-2 rounded-lg border border-amber-200/60">
                      <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
                      <span>Our manager is verifying your commercial tax credentials. Wholesale pricing activates upon approval.</span>
                    </div>
                  )}

                  {verificationStatus === 'APPROVED' && (
                    <div className="mt-2.5 flex items-center gap-1.5 text-xs text-emerald-800 bg-white/70 p-2 rounded-lg border border-emerald-200/60">
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
                      <span>Approved for B2B commercial pricing slabs with automated GST tax invoices.</span>
                    </div>
                  )}

                  {verificationStatus === 'REJECTED' && (
                    <div className="mt-2.5 text-xs text-red-800 bg-white/70 p-2 rounded-lg border border-red-200/60">
                      <strong>Application Rejected:</strong> {wholesaleProfile.rejection_reason || 'Could not verify GSTIN records with state portal.'}
                    </div>
                  )}
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex border-b border-spice-borderSubtle mb-8 gap-2 sm:gap-6 overflow-x-auto no-scrollbar">
          <button
            type="button"
            onClick={() => setActiveTab('profile')}
            className={`pb-3.5 px-2 text-sm font-bold transition-all border-b-2 flex items-center gap-2 shrink-0 ${
              activeTab === 'profile'
                ? 'border-saffron-600 text-saffron-800'
                : 'border-transparent text-spice-stone hover:text-spice-black'
            }`}
          >
            <User className="h-4 w-4" />
            <span>Profile &amp; Details</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('orders')}
            className={`pb-3.5 px-2 text-sm font-bold transition-all border-b-2 flex items-center gap-2 shrink-0 ${
              activeTab === 'orders'
                ? 'border-saffron-600 text-saffron-800'
                : 'border-transparent text-spice-stone hover:text-spice-black'
            }`}
          >
            <Package className="h-4 w-4" />
            <span>My Orders</span>
            {recentOrders.length > 0 && (
              <Badge variant="saffron" size="xs">
                {recentOrders.length}
              </Badge>
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('addresses')}
            className={`pb-3.5 px-2 text-sm font-bold transition-all border-b-2 flex items-center gap-2 shrink-0 ${
              activeTab === 'addresses'
                ? 'border-saffron-600 text-saffron-800'
                : 'border-transparent text-spice-stone hover:text-spice-black'
            }`}
          >
            <MapPin className="h-4 w-4" />
            <span>Saved Addresses</span>
            {addresses.length > 0 && (
              <Badge variant="stone" size="xs">
                {addresses.length}
              </Badge>
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('security')}
            className={`pb-3.5 px-2 text-sm font-bold transition-all border-b-2 flex items-center gap-2 shrink-0 ${
              activeTab === 'security'
                ? 'border-saffron-600 text-saffron-800'
                : 'border-transparent text-spice-stone hover:text-spice-black'
            }`}
          >
            <Shield className="h-4 w-4" />
            <span>Security &amp; Password</span>
          </button>
        </div>

        {/* TAB 1: PROFILE & OVERVIEW */}
        {activeTab === 'profile' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-6">
              {/* Account Details Card */}
              <Card variant="default" padding="md" className="rounded-2xl">
                <div className="flex items-center justify-between mb-4 border-b border-spice-borderSubtle pb-3">
                  <h2 className="text-base font-bold font-display text-spice-black flex items-center gap-2">
                    <User className="h-4 w-4 text-saffron-600" />
                    <span>Personal Information</span>
                  </h2>
                  <Button variant="outline-stone" size="xs" onClick={openEditModal} leftIcon={<Edit2 className="h-3 w-3" />}>
                    Edit Details
                  </Button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-spice-muted block mb-0.5">First Name</span>
                    <span className="font-semibold text-spice-black">{user?.first_name || '—'}</span>
                  </div>
                  <div>
                    <span className="text-spice-muted block mb-0.5">Last Name</span>
                    <span className="font-semibold text-spice-black">{user?.last_name || '—'}</span>
                  </div>
                  <div>
                    <span className="text-spice-muted block mb-0.5">Email Address</span>
                    <span className="font-semibold text-spice-black">{user?.email || '—'}</span>
                  </div>
                  <div>
                    <span className="text-spice-muted block mb-0.5">Phone Number</span>
                    <span className="font-semibold text-spice-black">{user?.phone_number || '—'}</span>
                  </div>
                  <div>
                    <span className="text-spice-muted block mb-0.5">Account Tier</span>
                    <span className="font-semibold text-spice-black">
                      {isWholesale ? 'Wholesale Commercial Buyer' : 'Retail Spice Enthusiast'}
                    </span>
                  </div>
                  <div>
                    <span className="text-spice-muted block mb-0.5">Member Since</span>
                    <span className="font-semibold text-spice-black">
                      {user?.date_joined
                        ? new Date(user.date_joined).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })
                        : 'Active Member'}
                    </span>
                  </div>
                </div>
              </Card>

              {/* Recent Orders Quick Summary */}
              <Card variant="default" padding="md" className="rounded-2xl">
                <div className="flex items-center justify-between mb-4 border-b border-spice-borderSubtle pb-3">
                  <h2 className="text-base font-bold font-display text-spice-black flex items-center gap-2">
                    <Package className="h-4 w-4 text-saffron-600" />
                    <span>Recent Spice Orders</span>
                  </h2>
                  <Link href="/account/orders">
                    <span className="text-xs font-bold text-saffron-700 hover:text-saffron-800">
                      View All Orders &rarr;
                    </span>
                  </Link>
                </div>

                {isLoadingOrders ? (
                  <div className="space-y-3">
                    <div className="h-16 rounded-xl bg-spice-borderSubtle animate-pulse" />
                    <div className="h-16 rounded-xl bg-spice-borderSubtle animate-pulse" />
                  </div>
                ) : recentOrders.length === 0 ? (
                  <div className="py-6 text-center">
                    <p className="text-xs text-spice-stone">No spice orders placed yet.</p>
                    <Link href="/products" className="mt-3 inline-block">
                      <Button variant="primary" size="xs">
                        Browse Harvests
                      </Button>
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {recentOrders.slice(0, 3).map((order) => {
                      const cfg = STATUS_CONFIG[order.order_status] || {
                        label: order.order_status,
                        bg: 'bg-stone-100 text-stone-800 border-stone-200',
                      };
                      return (
                        <div
                          key={order.id}
                          className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl border border-spice-border bg-spice-canvas gap-2"
                        >
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-xs font-bold text-spice-black">
                                #{order.order_number}
                              </span>
                              <span
                                className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold ${cfg.bg}`}
                              >
                                {cfg.label}
                              </span>
                            </div>
                            <p className="text-[11px] text-spice-muted mt-0.5">
                              {order.created_at
                                ? new Date(order.created_at).toLocaleDateString('en-IN', {
                                    day: 'numeric',
                                    month: 'short',
                                    year: 'numeric',
                                  })
                                : ''}{' '}
                              • {order.total_quantity || order.lines?.length || 0} packs
                            </p>
                          </div>

                          <div className="flex items-center justify-between sm:justify-end gap-3">
                            <span className="text-xs font-extrabold text-spice-black tabular-nums">
                              ₹{parseFloat(order.grand_total || 0).toFixed(2)}
                            </span>
                            <Link href={`/account/orders/${order.id}`}>
                              <Button variant="outline-stone" size="xs">
                                Details
                              </Button>
                            </Link>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Card>
            </div>

            {/* Right Support Column */}
            <div className="space-y-6">
              <Card variant="flat" padding="md" className="rounded-2xl">
                <h3 className="text-xs font-bold uppercase tracking-wider text-spice-black mb-2">
                  Customer Assistance Desk
                </h3>
                <p className="text-xs text-spice-stone leading-relaxed mb-3">
                  Have questions regarding cold-milled batches, wholesale invoices, or shipment tracking? Reach our estate logistics desk directly.
                </p>
                <div className="space-y-1 text-xs">
                  <p className="text-spice-stone">
                    Email:{' '}
                    <strong className="text-saffron-800 font-semibold">care@bharatmasala.com</strong>
                  </p>
                  <p className="text-spice-stone">
                    Desk:{' '}
                    <strong className="text-spice-black font-semibold">+91 (080) 4122-SPICE</strong>
                  </p>
                  <p className="text-[11px] text-spice-muted pt-1">
                    Operating Hours: Mon – Sat, 9:00 AM – 7:00 PM IST
                  </p>
                </div>
              </Card>
            </div>
          </div>
        )}

        {/* TAB 2: MY ORDERS */}
        {activeTab === 'orders' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold font-display text-spice-black flex items-center gap-2">
                  <Package className="h-4 w-4 text-saffron-600" />
                  <span>My Spice Orders</span>
                </h2>
                <p className="text-xs text-spice-stone mt-0.5">
                  Track harvest dispatches, transit updates, and digital tax invoices
                </p>
              </div>

              <Link href="/account/orders">
                <Button variant="primary" size="sm">
                  Full Order History &rarr;
                </Button>
              </Link>
            </div>

            {isLoadingOrders ? (
              <div className="space-y-4">
                <div className="h-28 rounded-2xl bg-spice-borderSubtle animate-pulse" />
                <div className="h-28 rounded-2xl bg-spice-borderSubtle animate-pulse" />
              </div>
            ) : ordersError ? (
              <div className="p-6 rounded-2xl bg-red-50/50 border border-red-200 text-xs text-red-700">
                {ordersError}
              </div>
            ) : recentOrders.length === 0 ? (
              <div className="p-10 text-center rounded-2xl bg-white border border-dashed border-spice-border">
                <Package className="h-10 w-10 text-spice-muted mx-auto mb-3" />
                <h3 className="text-sm font-bold text-spice-black">No Orders Placed Yet</h3>
                <p className="text-xs text-spice-stone max-w-sm mx-auto mt-1 mb-4">
                  Discover authentic Malenadu single-origin spices, hand-harvested and stone-ground to perfection.
                </p>
                <Link href="/products">
                  <Button variant="primary" size="sm">
                    Explore Spice Catalog
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-4">
                {recentOrders.map((order) => {
                  const cfg = STATUS_CONFIG[order.order_status] || {
                    label: order.order_status,
                    bg: 'bg-stone-100 text-stone-800 border-stone-200',
                  };
                  const lines = order.lines || [];
                  return (
                    <Card key={order.id} variant="default" padding="md" className="rounded-2xl">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-spice-borderSubtle pb-3 gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-sm font-bold text-spice-black">
                              #{order.order_number}
                            </span>
                            <span
                              className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${cfg.bg}`}
                            >
                              {cfg.label}
                            </span>
                          </div>
                          <p className="text-xs text-spice-muted mt-1">
                            Placed on{' '}
                            {order.created_at
                              ? new Date(order.created_at).toLocaleDateString('en-IN', {
                                  day: 'numeric',
                                  month: 'short',
                                  year: 'numeric',
                                })
                              : 'Recent'}
                          </p>
                        </div>

                        <div className="text-left sm:text-right">
                          <span className="text-[11px] text-spice-muted block">Grand Total</span>
                          <span className="text-base font-extrabold text-spice-black tabular-nums">
                            ₹{parseFloat(order.grand_total || 0).toFixed(2)}
                          </span>
                        </div>
                      </div>

                      {/* Items */}
                      <div className="py-3 space-y-1.5">
                        {lines.slice(0, 2).map((line) => (
                          <div key={line.id} className="flex items-center justify-between text-xs text-spice-stone">
                            <span className="truncate pr-2">
                              • {line.product_name} ({line.variant_name || `${line.weight_in_grams}g`}) × {line.quantity}
                            </span>
                            <span className="font-semibold text-spice-black tabular-nums shrink-0">
                              ₹{parseFloat(line.line_subtotal || 0).toFixed(0)}
                            </span>
                          </div>
                        ))}
                        {lines.length > 2 && (
                          <p className="text-[11px] text-spice-muted italic">
                            + {lines.length - 2} more item(s)
                          </p>
                        )}
                      </div>

                      <div className="border-t border-spice-borderSubtle pt-3 flex items-center justify-between">
                        <span className="text-xs text-spice-stone">
                          Ship to: {order.shipping_city}, {order.shipping_state}
                        </span>
                        <Link href={`/account/orders/${order.id}`}>
                          <Button variant="outline-stone" size="xs">
                            View Order Details &rarr;
                          </Button>
                        </Link>
                      </div>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* TAB 3: SAVED ADDRESSES */}
        {activeTab === 'addresses' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold font-display text-spice-black flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-saffron-600" />
                  <span>Saved Delivery Addresses</span>
                </h2>
                <p className="text-xs text-spice-stone mt-0.5">
                  Manage shipping destinations for quick single-tap checkout
                </p>
              </div>

              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsAddAddressOpen(true)}
                leftIcon={<Plus className="h-3.5 w-3.5" />}
              >
                Add Address
              </Button>
            </div>

            {isLoadingAddresses ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="h-32 rounded-xl bg-spice-borderSubtle animate-pulse" />
                <div className="h-32 rounded-xl bg-spice-borderSubtle animate-pulse" />
              </div>
            ) : addresses.length === 0 ? (
              <div className="p-8 text-center rounded-2xl bg-white border border-dashed border-spice-border">
                <MapPin className="h-8 w-8 text-spice-muted mx-auto mb-2" />
                <p className="text-xs font-semibold text-spice-black">No addresses saved yet</p>
                <p className="text-[11px] text-spice-stone mt-0.5 mb-4">
                  Add a delivery address to speed up your spice orders.
                </p>
                <Button variant="outline" size="sm" onClick={() => setIsAddAddressOpen(true)}>
                  Add First Address
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {addresses.map((addr) => (
                  <Card key={addr.id} variant="default" padding="md" className="relative flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className="text-xs font-bold text-spice-black">
                          {addr.recipient_name}
                        </span>
                        {addr.is_default_shipping && (
                          <Badge variant="saffron" size="xs">
                            Default
                          </Badge>
                        )}
                      </div>

                      <p className="text-xs text-spice-stone leading-relaxed">
                        {addr.address_line_1}
                        {addr.address_line_2 && <>, {addr.address_line_2}</>}
                        {addr.landmark && <>, Near {addr.landmark}</>}
                      </p>

                      <p className="text-xs text-spice-stone mt-1">
                        {addr.city}, {addr.state} — <strong className="text-spice-black">{addr.pincode}</strong>
                      </p>

                      <p className="text-[11px] text-spice-muted mt-2">
                        Phone: {addr.phone_number}
                      </p>
                    </div>

                    <div className="pt-3 border-t border-spice-borderSubtle mt-3 flex justify-end">
                      <button
                        type="button"
                        onClick={() => handleDeleteAddress(addr.id)}
                        className="text-xs text-red-600 hover:text-red-700 flex items-center gap-1"
                        aria-label={`Delete address for ${addr.recipient_name}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        <span>Remove</span>
                      </button>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 4: SECURITY & PASSWORD */}
        {activeTab === 'security' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-6">
              <Card variant="default" padding="lg" className="rounded-2xl">
                <div className="border-b border-spice-borderSubtle pb-4 mb-6">
                  <h2 className="text-base font-bold font-display text-spice-black flex items-center gap-2">
                    <Lock className="h-4 w-4 text-saffron-600" />
                    <span>Change Password</span>
                  </h2>
                  <p className="text-xs text-spice-stone mt-1">
                    Update your password regularly to protect your Bharat Masala account and saved orders.
                  </p>
                </div>

                {passwordSuccessMessage && (
                  <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-cardamom-200 bg-cardamom-50 p-3.5 text-xs text-cardamom-800 animate-slideUp">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-cardamom-600 mt-0.5" />
                    <div className="flex-1 font-medium leading-relaxed">{passwordSuccessMessage}</div>
                  </div>
                )}

                {passwordApiError && (
                  <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 p-3.5 text-xs text-red-700 animate-slideUp">
                    <AlertTriangle className="h-4 w-4 shrink-0 text-red-600 mt-0.5" />
                    <div className="flex-1 font-medium leading-relaxed">{passwordApiError}</div>
                  </div>
                )}

                <form onSubmit={handleChangePassword} className="space-y-4 max-w-lg">
                  <div>
                    <Input
                      label="Current Password"
                      type={showCurrentPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      required
                      value={currentPassword}
                      onChange={(e) => {
                        setCurrentPassword(e.target.value);
                        if (passwordErrors.currentPassword) {
                          setPasswordErrors((prev) => ({ ...prev, currentPassword: '' }));
                        }
                      }}
                      error={passwordErrors.currentPassword}
                      leftIcon={<Lock className="h-4 w-4" />}
                      rightIcon={
                        <button
                          type="button"
                          onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                          className="text-spice-stone hover:text-spice-black focus:outline-none"
                          aria-label={showCurrentPassword ? 'Hide current password' : 'Show current password'}
                        >
                          {showCurrentPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                      }
                      placeholder="••••••••••••"
                    />
                  </div>

                  <div>
                    <Input
                      label="New Password"
                      type={showNewPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      required
                      value={newPassword}
                      onChange={(e) => {
                        setNewPassword(e.target.value);
                        if (passwordErrors.newPassword) {
                          setPasswordErrors((prev) => ({ ...prev, newPassword: '' }));
                        }
                      }}
                      error={passwordErrors.newPassword}
                      leftIcon={<Lock className="h-4 w-4" />}
                      rightIcon={
                        <button
                          type="button"
                          onClick={() => setShowNewPassword(!showNewPassword)}
                          className="text-spice-stone hover:text-spice-black focus:outline-none"
                          aria-label={showNewPassword ? 'Hide new password' : 'Show new password'}
                        >
                          {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                      }
                      placeholder="Min 8 characters"
                    />
                    <p className="mt-1 text-[11px] text-spice-stone">
                      Must be at least 8 characters long and differ from your current password.
                    </p>
                  </div>

                  <div>
                    <Input
                      label="Confirm New Password"
                      type={showConfirmNewPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      required
                      value={confirmNewPassword}
                      onChange={(e) => {
                        setConfirmNewPassword(e.target.value);
                        if (passwordErrors.confirmNewPassword) {
                          setPasswordErrors((prev) => ({ ...prev, confirmNewPassword: '' }));
                        }
                      }}
                      error={passwordErrors.confirmNewPassword}
                      leftIcon={<Lock className="h-4 w-4" />}
                      rightIcon={
                        <button
                          type="button"
                          onClick={() => setShowConfirmNewPassword(!showConfirmNewPassword)}
                          className="text-spice-stone hover:text-spice-black focus:outline-none"
                          aria-label={showConfirmNewPassword ? 'Hide confirm password' : 'Show confirm password'}
                        >
                          {showConfirmNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                      }
                      placeholder="Re-enter new password"
                    />
                  </div>

                  <div className="pt-2">
                    <Button
                      type="submit"
                      variant="primary"
                      size="md"
                      isLoading={isChangingPassword}
                      className="font-semibold text-xs shadow-saffron-glow"
                    >
                      Update Password
                    </Button>
                  </div>
                </form>
              </Card>
            </div>

            {/* Sidebar Security Info */}
            <div className="space-y-6">
              <Card variant="flat" padding="md" className="rounded-2xl border border-spice-border bg-spice-canvas">
                <h3 className="text-xs font-bold uppercase tracking-wider text-spice-black mb-3 flex items-center gap-1.5">
                  <Shield className="h-3.5 w-3.5 text-cardamom-700" />
                  <span>Security &amp; Account Protection</span>
                </h3>
                <ul className="text-xs text-spice-stone space-y-2.5">
                  <li className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-cardamom-600 mt-1.5 shrink-0" />
                    <span>Passwords are hashed with strong PBKDF2-SHA256 and never stored in plaintext.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-cardamom-600 mt-1.5 shrink-0" />
                    <span>Changing your password updates your credentials immediately across all sessions.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-cardamom-600 mt-1.5 shrink-0" />
                    <span>One-time password recovery links expire automatically after 1 hour.</span>
                  </li>
                </ul>
              </Card>
            </div>
          </div>
        )}

        {/* Edit Profile Modal */}
        <Modal
          isOpen={isEditModalOpen}
          onClose={() => setIsEditModalOpen(false)}
          title="Edit Profile"
          description="Update your account name"
          footer={
            <>
              <Button variant="ghost" size="sm" onClick={() => setIsEditModalOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleUpdateProfile}
                isLoading={isUpdatingProfile}
              >
                Save Changes
              </Button>
            </>
          }
        >
          <form onSubmit={handleUpdateProfile} className="space-y-4">
            <Input
              label="First Name"
              value={editFirstName}
              onChange={(e) => setEditFirstName(e.target.value)}
              placeholder="First name"
            />
            <Input
              label="Last Name"
              value={editLastName}
              onChange={(e) => setEditLastName(e.target.value)}
              placeholder="Last name"
            />
          </form>
        </Modal>

        {/* Add Address Modal */}
        <Modal
          isOpen={isAddAddressOpen}
          onClose={() => setIsAddAddressOpen(false)}
          title="Add Delivery Address"
          description="Enter full Indian shipping address"
          footer={
            <>
              <Button variant="ghost" size="sm" onClick={() => setIsAddAddressOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSaveAddress}
                isLoading={isSavingAddress}
              >
                Save Address
              </Button>
            </>
          }
        >
          <form onSubmit={handleSaveAddress} className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input
                label="Recipient Full Name"
                required
                value={addressForm.recipient_name}
                onChange={(e) => setAddressForm({ ...addressForm, recipient_name: e.target.value })}
                placeholder="Aarav Sharma"
              />
              <Input
                label="Phone Number"
                type="tel"
                required
                value={addressForm.phone_number}
                onChange={(e) => setAddressForm({ ...addressForm, phone_number: e.target.value })}
                placeholder="9876543210"
              />
            </div>

            <Input
              label="Flat, House no., Building, Apartment"
              required
              value={addressForm.address_line_1}
              onChange={(e) => setAddressForm({ ...addressForm, address_line_1: e.target.value })}
              placeholder="House 42, 3rd Cross, Malenadu Enclave"
            />

            <Input
              label="Area, Street, Sector, Village"
              value={addressForm.address_line_2}
              onChange={(e) => setAddressForm({ ...addressForm, address_line_2: e.target.value })}
              placeholder="Kuvempu Nagar"
            />

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Input
                label="Landmark (Optional)"
                value={addressForm.landmark}
                onChange={(e) => setAddressForm({ ...addressForm, landmark: e.target.value })}
                placeholder="Near Post Office"
              />
              <Input
                label="City"
                required
                value={addressForm.city}
                onChange={(e) => setAddressForm({ ...addressForm, city: e.target.value })}
                placeholder="Shimoga"
              />
              <Input
                label="PIN Code"
                required
                value={addressForm.pincode}
                onChange={(e) => setAddressForm({ ...addressForm, pincode: e.target.value })}
                placeholder="577201"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Select
                label="State / Province"
                required
                value={addressForm.state}
                onChange={(e) => setAddressForm({ ...addressForm, state: e.target.value })}
                options={INDIAN_STATES}
              />

              <Select
                label="Address Category"
                value={addressForm.address_type}
                onChange={(e) => setAddressForm({ ...addressForm, address_type: e.target.value })}
                options={ADDRESS_TYPES}
              />
            </div>
          </form>
        </Modal>
      </div>
    </RouteGuard>
  );
}
