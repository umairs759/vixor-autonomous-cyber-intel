'use client';

import React, { useState } from 'react';

export default function ReportsPage() {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = () => {
    setDownloading(true);
    // Direct link to the generated valid PDF
    const link = document.createElement('a');
    link.href = '/VIXOR_Executive_Security_Audit_Report.pdf';
    link.download = 'VIXOR_Executive_Security_Audit_Report.pdf';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => setDownloading(false), 1000);
  };

  return (
    <div className="min-h-screen bg-[#07090D] text-[#E6EDF3] p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">Executive Security Audit Reports</h1>
            <p className="text-gray-400 mt-1">Compiled vulnerability intelligence with ML risk prioritization & SHAP narratives.</p>
          </div>
          <button onClick={handleDownload} disabled={downloading} className="px-4 py-2 bg-[#22D3EE] text-black font-semibold rounded-lg hover:bg-[#06B6D4] transition text-sm">
            {downloading ? 'Downloading...' : 'Generate New PDF'}
          </button>
        </div>

        <div className="bg-[#0E131B] border border-[#1F2937] rounded-xl overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-[#161B22] text-gray-400 text-xs uppercase">
              <tr>
                <th className="p-4">Report Title</th>
                <th className="p-4">Target Scope</th>
                <th className="p-4">Format</th>
                <th className="p-4">Status</th>
                <th className="p-4">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1F2937]">
              <tr className="hover:bg-gray-800/40">
                <td className="p-4 font-semibold text-white">Executive Security Audit Report - demo.vixor.local</td>
                <td className="p-4 text-gray-300">Enterprise Security Audit</td>
                <td className="p-4 text-cyan-400 font-mono">PDF</td>
                <td className="p-4"><span className="bg-emerald-500/20 text-emerald-400 text-xs px-2.5 py-0.5 rounded-full font-semibold">Completed</span></td>
                <td className="p-4">
                  <button onClick={handleDownload} className="text-xs px-3 py-1.5 bg-[#22D3EE]/20 hover:bg-[#22D3EE]/30 text-[#22D3EE] border border-[#22D3EE]/40 rounded font-medium">
                    Download PDF
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
