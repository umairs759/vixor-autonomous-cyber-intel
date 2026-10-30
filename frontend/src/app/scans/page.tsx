'use client';

import React from 'react';
import Link from 'next/link';

export default function ScansPage() {
  return (
    <div className="min-h-screen bg-[#07090D] text-[#E6EDF3] p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">Multi-Tool Vulnerability Scans</h1>
            <p className="text-gray-400 mt-1">Autonomous execution of Nuclei, OWASP ZAP, and Nmap service discovery.</p>
          </div>
          <button className="px-4 py-2 bg-[#22D3EE] text-black font-semibold rounded-lg hover:bg-[#06B6D4] transition text-sm">
            Launch New Scan
          </button>
        </div>

        <div className="bg-[#0E131B] border border-[#1F2937] rounded-xl overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-[#161B22] text-gray-400 text-xs uppercase">
              <tr>
                <th className="p-4">Target Domain</th>
                <th className="p-4">Scan Engines</th>
                <th className="p-4">Status</th>
                <th className="p-4">Findings</th>
                <th className="p-4">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1F2937]">
              <tr className="hover:bg-gray-800/40">
                <td className="p-4 font-mono font-semibold text-white">demo.vixor.local</td>
                <td className="p-4 text-xs">
                  <span className="bg-gray-800 text-cyan-400 px-2 py-0.5 rounded mr-1">Nuclei</span>
                  <span className="bg-gray-800 text-amber-400 px-2 py-0.5 rounded mr-1">OWASP ZAP</span>
                  <span className="bg-gray-800 text-blue-400 px-2 py-0.5 rounded">Nmap</span>
                </td>
                <td className="p-4"><span className="bg-emerald-500/20 text-emerald-400 text-xs px-2.5 py-0.5 rounded-full font-semibold">Completed</span></td>
                <td className="p-4 font-bold text-amber-400">3 Identified</td>
                <td className="p-4">
                  <Link href="/findings" className="text-xs px-3 py-1.5 bg-[#22D3EE]/20 hover:bg-[#22D3EE]/30 text-[#22D3EE] border border-[#22D3EE]/40 rounded font-medium">
                    View Findings
                  </Link>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
