'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  Package,
  ShoppingBag,
  CreditCard,
  Boxes,
  LogOut,
  Store,
  Menu,
  X,
  ShieldCheck,
  Bell,
  Key,
  Lock,
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import AdminRouteGuard from './AdminRouteGuard';
import adminService from '../../services/adminService';
import authService from '../../services/authService';
import Modal from '../common/Modal';
import Button from '../common/Button';
import Input from '../common/Input';

const NAV_ITEMS = [
  { label: 'Overview Dashboard', href: '/admin-dashboard', icon: LayoutDashboard },
  { label: 'Products & Spices', href: '/admin/products', icon: Package },
  { label: 'Customer Orders', href: '/admin/orders', icon: ShoppingBag },
  {
    label: 'Payment Verifications',
    href: '/admin/payments',
    icon: CreditCard,
    badgeKey: 'pending_payments',
  },
  {
    label: 'Inventory & Stock',
    href: '/admin/inventory',
    icon: Boxes,
    badgeKey: 'low_stock_products',
  },
];

export default function AdminLayout({ children, title, subtitle }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [metrics, setMetrics] = useState({ pending_payments: 0, low_stock_products: 0 });

  // Staff Password Change Modal State
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);

  // Quick poll for notification badges
  useEffect(() => {
    let mounted = true;
    async function loadBadges() {
      try {
        const data = await adminService.getDashboard();
        if (mounted && data) {
          setMetrics({
            pending_payments: data.pending_payments || 0,
            low_stock_products: data.low_stock_products || 0,
          });
        }
      } catch {
        // Quiet fallback
      }
    }
    loadBadges();
    return () => {
      mounted = false;
    };
  }, [pathname]);

  const handleLogout = async () => {
    await logout();
    router.push('/admin-login');
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess('');

    if (!currentPassword) {
      setPasswordError('Please enter your current password.');
      return;
    }
    if (!newPassword || newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters long.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match.');
      return;
    }
    if (currentPassword === newPassword) {
      setPasswordError('New password must be different from your current password.');
      return;
    }

    setIsUpdatingPassword(true);
    try {
      await authService.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setPasswordSuccess('Password updated successfully!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => {
        setIsPasswordModalOpen(false);
        setPasswordSuccess('');
      }, 1500);
    } catch (err) {
      const msg =
        err?.details?.current_password?.[0] ||
        err?.details?.new_password?.[0] ||
        err?.userMessage ||
        err?.message ||
        'Failed to update password.';
      setPasswordError(msg);
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  return (
    <AdminRouteGuard>
      <div className="min-h-screen bg-stone-50 flex flex-col md:flex-row text-spice-black font-body">
        {/* Mobile Header */}
        <div className="md:hidden bg-spice-earth text-white px-4 py-3 flex items-center justify-between border-b border-stone-800">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-saffron-500" />
            <span className="font-display font-bold text-sm tracking-wide">Bharat Masala Admin</span>
          </div>
          <button
            type="button"
            onClick={() => setIsMobileOpen(!isMobileOpen)}
            className="p-1.5 rounded-lg text-stone-300 hover:text-white hover:bg-stone-800"
          >
            {isMobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>

        {/* Sidebar */}
        <aside
          className={`${
            isMobileOpen ? 'block' : 'hidden'
          } md:block w-full md:w-64 bg-spice-earth text-stone-200 shrink-0 flex flex-col justify-between border-r border-stone-800 z-30 min-h-[calc(100vh-53px)] md:min-h-screen sticky top-0`}
        >
          <div>
            {/* Brand Logo & Tag */}
            <div className="p-6 border-b border-stone-800 hidden md:flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-saffron-600 flex items-center justify-center text-white shadow-saffron-glow">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <span className="font-display font-black text-sm text-white tracking-wide block">
                  BHARAT MASALA
                </span>
                <span className="text-[10px] uppercase font-bold tracking-widest text-saffron-400">
                  Staff Control Deck
                </span>
              </div>
            </div>

            {/* Nav items */}
            <nav className="p-4 space-y-1">
              <span className="text-[10px] uppercase font-bold text-stone-500 tracking-wider px-3 mb-2 block">
                Store Operations
              </span>
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href || (item.href !== '/admin-dashboard' && pathname.startsWith(item.href));
                const badgeCount = item.badgeKey ? metrics[item.badgeKey] : 0;

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setIsMobileOpen(false)}
                    className={`flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                      isActive
                        ? 'bg-saffron-600 text-white shadow-xs'
                        : 'text-stone-300 hover:bg-stone-800/80 hover:text-white'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Icon className={`h-4 w-4 ${isActive ? 'text-white' : 'text-stone-400'}`} />
                      <span>{item.label}</span>
                    </div>

                    {badgeCount > 0 && (
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full tabular-nums ${
                          isActive
                            ? 'bg-white text-saffron-700'
                            : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        }`}
                      >
                        {badgeCount}
                      </span>
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* User Info & Footer */}
          <div className="p-4 border-t border-stone-800 space-y-3">
            <Link
              href="/"
              target="_blank"
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold text-stone-400 hover:text-white hover:bg-stone-800/60 transition-colors"
            >
              <Store className="h-4 w-4 text-stone-500" />
              <span>View Customer Storefront</span>
            </Link>

            <div className="bg-stone-800/60 p-3 rounded-xl border border-stone-700/50 flex items-center justify-between">
              <div className="truncate pr-2">
                <span className="text-xs font-bold text-white block truncate">
                  {user?.full_name || user?.email || 'Staff User'}
                </span>
                <span className="text-[10px] text-saffron-400 font-medium">
                  {user?.is_superuser ? 'Super Administrator' : 'Operations Staff'}
                </span>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  type="button"
                  onClick={() => {
                    setIsPasswordModalOpen(true);
                    setPasswordError('');
                    setPasswordSuccess('');
                  }}
                  title="Change Password"
                  className="p-1.5 text-stone-400 hover:text-saffron-400 hover:bg-stone-800 rounded-lg transition-colors"
                >
                  <Key className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={handleLogout}
                  title="Log Out"
                  className="p-1.5 text-stone-400 hover:text-red-400 hover:bg-stone-800 rounded-lg transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 min-w-0 p-4 sm:p-8 flex flex-col">
          {/* Top Bar / Header */}
          {(title || subtitle) && (
            <div className="mb-6 sm:mb-8 pb-4 border-b border-stone-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                {title && <h1 className="text-xl sm:text-2xl font-bold font-display text-spice-black tracking-tight">{title}</h1>}
                {subtitle && <p className="text-xs sm:text-sm text-spice-stone mt-0.5">{subtitle}</p>}
              </div>
            </div>
          )}

          <div className="flex-1">{children}</div>
        </main>

        {/* Change Password Modal */}
        <Modal
          isOpen={isPasswordModalOpen}
          onClose={() => setIsPasswordModalOpen(false)}
          title="Change Staff Password"
          description="Update your operations credentials"
        >
          {passwordSuccess ? (
            <div className="py-4 text-center space-y-2">
              <div className="w-12 h-12 bg-green-50 border border-green-200 text-green-700 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <p className="text-sm font-bold text-spice-black">Password Changed</p>
              <p className="text-xs text-stone-500">{passwordSuccess}</p>
            </div>
          ) : (
            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              {passwordError && (
                <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800 flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
                  <span>{passwordError}</span>
                </div>
              )}

              <div>
                <Input
                  label="Current Password"
                  type={showCurrentPassword ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  leftIcon={<Lock className="h-4 w-4" />}
                  rightIcon={
                    <button
                      type="button"
                      onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                      className="text-stone-400 hover:text-stone-600"
                      aria-label="Toggle current password visibility"
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
                  required
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  leftIcon={<Lock className="h-4 w-4" />}
                  rightIcon={
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="text-stone-400 hover:text-stone-600"
                      aria-label="Toggle new password visibility"
                    >
                      {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  }
                  placeholder="Min 8 characters"
                />
              </div>

              <div>
                <Input
                  label="Confirm New Password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  required
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  leftIcon={<Lock className="h-4 w-4" />}
                  rightIcon={
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="text-stone-400 hover:text-stone-600"
                      aria-label="Toggle confirm password visibility"
                    >
                      {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  }
                  placeholder="Re-enter new password"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsPasswordModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  isLoading={isUpdatingPassword}
                >
                  Save Password
                </Button>
              </div>
            </form>
          )}
        </Modal>
      </div>
    </AdminRouteGuard>
  );
}
