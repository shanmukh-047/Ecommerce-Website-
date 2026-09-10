'use client';

import React, { useState } from 'react';
import { MapPin, Phone, Mail, Clock, MessageSquare, CheckCircle2, ArrowRight } from 'lucide-react';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import { useToast } from '../../components/common/Toast';

export default function ContactPage() {
  const { success } = useToast();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    subject: 'Order Enquiry',
    message: '',
  });
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setIsSubmitted(true);
    success('Thank you for reaching out! Our team in Shimoga will reply within 24 hours.', 'Message Sent');
  };

  return (
    <div className="min-h-screen bg-spice-canvas py-12 sm:py-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-12 space-y-3">
          <h1 className="text-3xl sm:text-4xl font-display font-extrabold text-spice-black">
            Customer Care &amp; Plantation Visits
          </h1>
          <p className="text-xs sm:text-sm text-spice-stone">
            Have questions regarding single-origin spice grades, wholesale consignments, or order tracking? We are here to help.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12">
          {/* Left Column: Contact Cards */}
          <div className="lg:col-span-5 space-y-6">
            <div className="p-6 rounded-2xl bg-white border border-spice-border shadow-xs space-y-4">
              <div className="flex items-start gap-3.5">
                <div className="h-10 w-10 rounded-xl bg-saffron-50 text-saffron-700 flex items-center justify-center shrink-0 border border-saffron-200">
                  <MapPin className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-spice-black font-display">Central Operations &amp; Packaging</h3>
                  <p className="text-xs text-spice-stone mt-1 leading-relaxed">
                    Bharat Masala Products Pvt Ltd<br />
                    B.H. Road, Thirthahalli &amp; Shimoga<br />
                    Karnataka, India — 577432
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3.5 pt-3 border-t border-spice-borderSubtle">
                <div className="h-10 w-10 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center shrink-0 border border-emerald-200">
                  <Phone className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-spice-black font-display">Helpline &amp; WhatsApp Desk</h3>
                  <p className="text-xs text-spice-stone mt-1 leading-relaxed">
                    +91 99887 76600<br />
                    <span className="text-[11px] text-spice-muted">Monday – Saturday, 9:00 AM to 6:00 PM IST</span>
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3.5 pt-3 border-t border-spice-borderSubtle">
                <div className="h-10 w-10 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center shrink-0 border border-amber-200">
                  <Mail className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-spice-black font-display">Email Sourcing &amp; Support</h3>
                  <p className="text-xs text-spice-stone mt-1 leading-relaxed">
                    support@bharatmasala.com<br />
                    wholesale@bharatmasala.com
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3.5 pt-3 border-t border-spice-borderSubtle">
                <div className="h-10 w-10 rounded-xl bg-stone-100 text-stone-700 flex items-center justify-center shrink-0 border border-stone-200">
                  <Clock className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-spice-black font-display">Estate Dispatch Timelines</h3>
                  <p className="text-xs text-spice-stone mt-1 leading-relaxed">
                    Orders cold-milled and packed within 24 hours of confirmation.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Contact Form */}
          <div className="lg:col-span-7">
            <div className="p-6 sm:p-8 rounded-3xl bg-white border border-spice-border shadow-xs">
              {isSubmitted ? (
                <div className="text-center py-12 space-y-4">
                  <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
                    <CheckCircle2 className="h-6 w-6" />
                  </div>
                  <h3 className="text-lg font-bold font-display text-emerald-950">
                    Enquiry Received Successfully
                  </h3>
                  <p className="text-xs text-emerald-800 max-w-sm mx-auto">
                    A representative from our Thirthahalli plantation desk will review your note and respond promptly.
                  </p>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  <h3 className="text-base font-bold font-display text-spice-black mb-1">
                    Send Us a Message
                  </h3>
                  <p className="text-xs text-spice-stone mb-4">
                    Fill out the details below and we will connect with you via email or phone.
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Input
                      label="Your Name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="e.g. Ananya Sharma"
                      required
                    />

                    <Input
                      label="Email Address"
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="ananya@example.com"
                      required
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Input
                      label="Phone Number"
                      type="tel"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      placeholder="9876543210"
                    />

                    <div>
                      <label className="block text-xs font-semibold text-spice-stone mb-1.5">
                        Enquiry Type
                      </label>
                      <select
                        value={formData.subject}
                        onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                        className="w-full rounded-xl border border-spice-border bg-spice-canvas/50 px-3.5 py-2 text-xs sm:text-sm text-spice-black focus:border-saffron-600 focus:bg-white focus:outline-none"
                      >
                        <option value="Order Enquiry">Existing Order Status</option>
                        <option value="Wholesale">B2B Wholesale Procurement</option>
                        <option value="Product Quality">Spice Quality &amp; Batch COA</option>
                        <option value="Farm Visit">Malenadu Plantation Visit</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-spice-stone mb-1.5">
                      Your Message
                    </label>
                    <textarea
                      rows={4}
                      value={formData.message}
                      onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                      placeholder="How can we assist you with our single-origin spices?"
                      required
                      className="w-full rounded-xl border border-spice-border bg-spice-canvas/50 p-3.5 text-xs sm:text-sm text-spice-black focus:border-saffron-600 focus:bg-white focus:outline-none focus:ring-2 focus:ring-saffron-500/20"
                    />
                  </div>

                  <Button type="submit" variant="primary" size="md" rightIcon={<ArrowRight className="h-4 w-4" />}>
                    Send Enquiry
                  </Button>
                </form>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
