'use client';

import React from 'react';
import Hero from '../components/home/Hero';
import CategorySection from '../components/home/CategorySection';
import FeaturedSection from '../components/home/FeaturedSection';
import WhyChooseUs from '../components/home/WhyChooseUs';
import PopularSection from '../components/home/PopularSection';
import QualityPromise from '../components/home/QualityPromise';
import Storytelling from '../components/home/Storytelling';
import HomeCTA from '../components/home/HomeCTA';
import FloatingActions from '../components/home/FloatingActions';

export default function HomePage() {
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
