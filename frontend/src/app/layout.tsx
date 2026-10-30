import React from 'react';
import TopNav from '@/components/TopNav';
import './globals.css';

export const metadata = {
  title: 'VIXOR — Vulnerability Intelligence Platform',
  description: 'Autonomous attack surface discovery and contextual ML risk prioritization',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#07090D] text-[#E6EDF3]">
        <TopNav />
        {children}
      </body>
    </html>
  );
}
