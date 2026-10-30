'use client';

import React from 'react';

export default function CorrelationsPage() {
  return (
    <div className="min-h-screen bg-[#07090D] text-[#E6EDF3] p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Security Correlation Engine</h1>
          <p className="text-gray-400 mt-1">Multi-stage attack chains synthesized from co-located vulnerability findings.</p>
        </div>

        <div className="bg-[#0E131B] border border-[#1F2937] p-6 rounded-xl space-y-6">
          <div className="flex justify-between items-start">
            <div>
              <span className="bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs px-3 py-1 rounded-full font-bold">
                Critical Attack Chain
              </span>
              <h2 className="text-2xl font-bold text-white mt-3">Chained Web Authentication Bypass to Lateral Service Pivot</h2>
              <p className="text-sm text-gray-400 mt-1">Target Scope: demo.vixor.local (Enterprise Security Audit)</p>
            </div>
            <div className="bg-[#161B22] border border-[#30363D] p-4 rounded-xl text-center">
              <p className="text-xs uppercase text-gray-400 font-semibold">Combined Risk Score</p>
              <p className="text-4xl font-black text-rose-500 mt-1">88 <span className="text-sm text-gray-400">/ 100</span></p>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-semibold uppercase text-cyan-400">Multi-Step Attack Progression</h3>
            
            <div className="flex items-center space-x-4 bg-[#161B22] p-4 rounded-lg border-l-4 border-rose-500">
              <div className="w-8 h-8 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center font-bold">1</div>
              <div>
                <p className="font-semibold text-white">Step 1: SQL Injection Exploitation</p>
                <p className="text-xs text-gray-400">Public-facing /api/v1/auth/login endpoint bypassed to extract session credentials.</p>
              </div>
            </div>

            <div className="flex items-center space-x-4 bg-[#161B22] p-4 rounded-lg border-l-4 border-amber-500">
              <div className="w-8 h-8 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold">2</div>
              <div>
                <p className="font-semibold text-white">Step 2: Session Hijacking via Reflected XSS</p>
                <p className="text-xs text-gray-400">Client-side script injection used to hijack administrative session tokens.</p>
              </div>
            </div>

            <div className="flex items-center space-x-4 bg-[#161B22] p-4 rounded-lg border-l-4 border-blue-500">
              <div className="w-8 h-8 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold">3</div>
              <div>
                <p className="font-semibold text-white">Step 3: Lateral Pivot to Internal API (api.vixor.local)</p>
                <p className="text-xs text-gray-400">Stolen administrative credentials leveraged to access internal management services on port 8000.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
