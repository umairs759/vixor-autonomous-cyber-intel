'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function TopNav() {
  const pathname = usePathname();

  // Login page par nav bar hide rahega
  if (pathname === '/login' || pathname === '/') {
    return null;
  }

  const navItems = [
    { name: 'Dashboard', href: '/dashboard' },
    { name: 'Projects', href: '/projects' },
    { name: 'Scans', href: '/scans' },
    { name: 'Findings', href: '/findings' },
    { name: 'Correlations', href: '/correlations' },
    { name: 'Reports', href: '/reports' },
    { name: 'Admin', href: '/admin' },
  ];

  const handleSignOut = () => {
    document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    document.cookie = 'token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    localStorage.removeItem('access_token');
    localStorage.removeItem('token');
    window.location.href = '/login';
  };

  return (
    <header className="border-b border-[#1F2937] bg-[#0E131B] px-6 py-2.5 flex items-center justify-between sticky top-0 z-50">
      <div className="flex items-center space-x-6">
        <Link href="/dashboard" className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded bg-[#22D3EE] flex items-center justify-center text-black font-black text-sm">
            V
          </div>
          <span className="font-bold tracking-wider text-white text-base">VIXOR</span>
        </Link>

        <nav className="flex items-center space-x-1">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  isActive
                    ? 'bg-[#161B22] text-[#22D3EE] border border-[#22D3EE]/40 font-semibold'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800/60'
                }`}
              >
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2 bg-[#161B22] border border-[#1F2937] px-3 py-1 rounded-lg text-xs text-gray-300">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>admin@example.com</span>
        </div>
        <button
          onClick={handleSignOut}
          className="flex items-center space-x-1.5 bg-[#161B22] hover:bg-rose-950/40 border border-[#1F2937] hover:border-rose-800 text-gray-400 hover:text-rose-300 px-3 py-1 rounded-lg text-xs font-medium transition"
        >
          <span>Sign out</span>
        </button>
      </div>
    </header>
  );
}
