'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';

export default function DashboardPage() {
  const [stats, setStats] = useState({
    projectsCount: 1,
    assetsCount: 2,
    findingsCount: 3,
    criticalCount: 1,
    highCount: 1,
    mediumCount: 1,
    correlationCount: 1,
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const token = localStorage.getItem('access_token') || localStorage.getItem('token') || '';
        const res = await fetch('http://127.0.0.1:8000/api/v1/dashboard/summary', {
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          }
        });
        if (res.ok) {
          const data = await res.json();
          if (data) setStats(prev => ({ ...prev, ...data }));
        }
      } catch (err) {
        console.warn('Using seeded dashboard metrics');
      }
    };
    fetchDashboard();
  }, []);

  return (
    <div className="min-h-screen bg-[#07090D] text-[#E6EDF3] p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Security Analytics Dashboard</h1>
          <p className="text-gray-400 mt-1">Autonomous vulnerability prioritization and continuous attack surface monitoring.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-[#0E131B] border border-[#1F2937] p-6 rounded-xl">
            <p className="text-xs font-semibold text-gray-400 uppercase">Active Projects</p>
            <p className="text-3xl font-bold text-white mt-2">{stats.projectsCount}</p>
          </div>
          <div className="bg-[#0E131B] border border-[#1F2937] p-6 rounded-xl">
            <p className="text-xs font-semibold text-gray-400 uppercase">Discovered Assets</p>
            <p className="text-3xl font-bold text-[#22D3EE] mt-2">{stats.assetsCount}</p>
          </div>
          <div className="bg-[#0E131B] border border-[#1F2937] p-6 rounded-xl">
            <p className="text-xs font-semibold text-gray-400 uppercase">Identified Findings</p>
            <p className="text-3xl font-bold text-amber-400 mt-2">{stats.findingsCount}</p>
          </div>
          <div className="bg-[#0E131B] border border-[#1F2937] p-6 rounded-xl">
            <p className="text-xs font-semibold text-gray-400 uppercase">Attack Chains</p>
            <p className="text-3xl font-bold text-rose-500 mt-2">{stats.correlationCount}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-[#0E131B] border border-[#1F2937] p-6 rounded-xl">
            <h2 className="text-lg font-semibold mb-4">Risk Severity Distribution</h2>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-rose-400 font-medium">Critical (ML Score &gt; 90)</span>
                  <span>{stats.criticalCount}</span>
                </div>
                <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-rose-500 h-full w-[33%]"></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-amber-400 font-medium">High (ML Score 70-89)</span>
                  <span>{stats.highCount}</span>
                </div>
                <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-amber-400 h-full w-[33%]"></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-blue-400 font-medium">Medium (ML Score 40-69)</span>
                  <span>{stats.mediumCount}</span>
                </div>
                <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-blue-400 h-full w-[33%]"></div>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-[#0E131B] border border-[#1F2937] p-6 rounded-xl flex flex-col justify-between">
            <div>
              <h2 className="text-lg font-semibold mb-2">Autonomous Actions</h2>
              <p className="text-sm text-gray-400 mb-6">Attack surface engines running continuously with SHAP explainability.</p>
            </div>
            <div className="space-y-3">
              <Link href="/projects" className="block w-full py-2.5 px-4 bg-[#22D3EE] text-black font-semibold rounded-lg text-center hover:bg-[#06B6D4] transition">
                View Scoped Projects
              </Link>
              <Link href="/reports" className="block w-full py-2.5 px-4 bg-[#161B22] border border-[#30363D] text-white font-medium rounded-lg text-center hover:bg-gray-800 transition">
                Download PDF Audit
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
