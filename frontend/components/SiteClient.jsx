'use client';

import React from 'react';
import Hero from './home/Hero';
import CategorySection from './home/CategorySection';
import FeaturedSection from './home/FeaturedSection';
import WhyChooseUs from './home/WhyChooseUs';
import PopularSection from './home/PopularSection';
import QualityPromise from './home/QualityPromise';
import Storytelling from './home/Storytelling';
import HomeCTA from './home/HomeCTA';
import FloatingActions from './home/FloatingActions';

export default function SiteClient() {
  return (
    <>
      <Hero />
      <CategorySection />
      <FeaturedSection />
      <WhyChooseUs />
      <PopularSection />
      <QualityPromise />
      <Storytelling />
      <HomeCTA />
      <FloatingActions />
    </>
  );
}
