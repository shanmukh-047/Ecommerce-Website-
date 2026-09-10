'use client';

import React from 'react';
import Link from 'next/link';
import { Truck, Clock, ShieldCheck, MapPin, Package, ArrowRight } from 'lucide-react';
import Button from '../../components/common/Button';

export default function ShippingPolicyPage() {
  return (
    <div className="min-h-screen bg-spice-canvas py-12 sm:py-16">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-saffron-100 text-xs font-semibold text-saffron-800">
            <Truck className="h-3.5 w-3.5" />
            <span>Fulfillment &amp; Delivery Logistics</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-display font-extrabold text-spice-black">
            Shipping &amp; Transit Policy
          </h1>
          <p className="text-xs sm:text-sm text-spice-stone max-w-lg mx-auto">
            Transparent delivery timelines, moisture-barrier packaging standards, and nationwide courier partner integrations.
          </p>
        </div>

        <div className="rounded-3xl p-6 sm:p-10 bg-white border border-spice-border shadow-xs space-y-8 text-xs sm:text-sm text-spice-stone leading-relaxed">
          {/* Section 1 */}
          <section className="space-y-3">
            <h2 className="text-base sm:text-lg font-bold font-display text-spice-black flex items-center gap-2">
              <Clock className="h-5 w-5 text-saffron-600" />
              <span>1. Order Processing &amp; Cold-Milling Timelines</span>
            </h2>
            <p>
              To deliver the most aromatic experience, whole spices and spice blends are freshly nitrogen-packed or ground upon order receipt at our central estate mill in Thirthahalli.
            </p>
            <ul className="list-disc pl-5 space-y-1 text-spice-black">
              <li>Orders placed Monday through Saturday before 2:00 PM IST are packed and handed to courier partners within 24 hours.</li>
              <li>Orders placed after 2:00 PM IST or on Sundays/national holidays are dispatched on the next operational business day.</li>
            </ul>
          </section>

          {/* Section 2 */}
          <section className="space-y-3 pt-6 border-t border-spice-borderSubtle">
            <h2 className="text-base sm:text-lg font-bold font-display text-spice-black flex items-center gap-2">
              <MapPin className="h-5 w-5 text-saffron-600" />
              <span>2. Domestic Delivery SLAs by Region</span>
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border border-spice-border rounded-xl overflow-hidden">
                <thead className="bg-stone-50 border-b border-spice-border">
                  <tr>
                    <th className="p-3 font-semibold text-spice-black">Destination Region</th>
                    <th className="p-3 font-semibold text-spice-black">Estimated Transit Time</th>
                    <th className="p-3 font-semibold text-spice-black">Primary Carriers</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-spice-borderSubtle">
                  <tr>
                    <td className="p-3 font-medium text-spice-black">Karnataka &amp; Kerala (Origin States)</td>
                    <td className="p-3 text-spice-stone">1 to 2 Business Days</td>
                    <td className="p-3 text-spice-muted">Delhivery / Blue Dart</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-spice-black">South India Metros (Chennai, Hyderabad)</td>
                    <td className="p-3 text-spice-stone">2 to 3 Business Days</td>
                    <td className="p-3 text-spice-muted">Delhivery Express</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-spice-black">North, West, and Central Metros (Mumbai, Delhi NCR)</td>
                    <td className="p-3 text-spice-stone">3 to 4 Business Days</td>
                    <td className="p-3 text-spice-muted">Blue Dart / Shiprocket</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-spice-black">East, Northeast &amp; Tier-3 Upcountry</td>
                    <td className="p-3 text-spice-stone">4 to 6 Business Days</td>
                    <td className="p-3 text-spice-muted">Speed Post / Delhivery Surface</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* Section 3 */}
          <section className="space-y-3 pt-6 border-t border-spice-borderSubtle">
            <h2 className="text-base sm:text-lg font-bold font-display text-spice-black flex items-center gap-2">
              <Package className="h-5 w-5 text-saffron-600" />
              <span>3. Shipping Charges &amp; Free Shipping Threshold</span>
            </h2>
            <p>
              We offer <strong className="text-spice-black font-semibold">Free Standard Shipping on all prepaid orders exceeding ₹499</strong> anywhere across India.
            </p>
            <p>
              For orders below ₹499, a nominal flat rate shipping charge of <strong className="text-spice-black font-semibold">₹49</strong> is applied at checkout to partially subsidize regional express transit costs.
            </p>
          </section>

          {/* Section 4 */}
          <section className="space-y-3 pt-6 border-t border-spice-borderSubtle">
            <h2 className="text-base sm:text-lg font-bold font-display text-spice-black flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-saffron-600" />
              <span>4. Real-Time Consignment Tracking</span>
            </h2>
            <p>
              As soon as your consignment leaves our facility, an Air Waybill (AWB) number is registered in our tracking system. You will receive an SMS and email notification with direct tracking links.
            </p>
            <div className="pt-2">
              <Link href="/track">
                <Button variant="outline-stone" size="sm" rightIcon={<ArrowRight className="h-3.5 w-3.5" />}>
                  Track an Active Shipment Online &rarr;
                </Button>
              </Link>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
