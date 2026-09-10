'use client';

import React from 'react';
import Link from 'next/link';
import { BookOpen, Volume2, Sparkles, ArrowRight, Clock } from 'lucide-react';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';

const CULINARY_STORIES = [
  {
    title: 'The Black Gold of the Malabar Coast',
    category: 'Harvest Journal',
    readTime: '4 min read',
    excerpt:
      'Why true Tellicherry Garbled Extra Bold pepper must ripen fully on the vine until the berries turn crimson before drying on bamboo mats.',
    author: 'Sharada Hegde, Master Blender',
  },
  {
    title: 'Unlocking Curcumin: Cold-Milling vs Industrial Grinding',
    category: 'Terroir & Science',
    readTime: '5 min read',
    excerpt:
      'Industrial hammer mills exceed 80°C, stripping spices of their precious volatile aromatics. Why our <38°C cryogenic mill preserves therapeutic potency.',
    author: 'Dr. V. Rao, Food Technologist',
  },
  {
    title: 'Wayanad Cardamom: The Queen’s Morning Mist',
    category: 'Estate Origins',
    readTime: '3 min read',
    excerpt:
      'How the canopy shade of the Western Ghats shields young cardamom plants from harsh ultraviolet rays, concentrating aromatic cineole.',
    author: 'K. Nambiar, Third-Generation Planter',
  },
];

export default function StoriesPage() {
  return (
    <div className="min-h-screen bg-spice-canvas py-12 sm:py-16">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-saffron-100 text-xs font-semibold text-saffron-800">
            <BookOpen className="h-3.5 w-3.5" />
            <span>Folklore, Harvests &amp; Gastronomy</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-display font-extrabold text-spice-black">
            Stories from the Spice Terroir
          </h1>
          <p className="text-xs sm:text-sm text-spice-stone max-w-lg mx-auto">
            Oral culinary traditions, estate harvest notes, and culinary science from the farmers of Malenadu.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {CULINARY_STORIES.map((story, i) => (
            <article
              key={i}
              className="p-6 sm:p-7 rounded-3xl bg-white border border-spice-border shadow-xs flex flex-col justify-between space-y-6 hover:shadow-subtle transition-all"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between text-[11px] text-spice-muted">
                  <Badge variant="cardamom" size="xs">
                    {story.category}
                  </Badge>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {story.readTime}
                  </span>
                </div>

                <h2 className="text-base sm:text-lg font-bold font-display text-spice-black leading-snug">
                  {story.title}
                </h2>

                <p className="text-xs text-spice-stone leading-relaxed">{story.excerpt}</p>
              </div>

              <div className="pt-3 border-t border-spice-borderSubtle">
                <p className="text-[11px] font-medium text-saffron-800">{story.author}</p>
                <Link href="/products" className="inline-flex items-center gap-1 text-xs font-semibold text-saffron-700 hover:text-saffron-800 mt-2">
                  <span>Taste the harvest</span>
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}
