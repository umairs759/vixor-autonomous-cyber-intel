'use client';

import React, { useState } from 'react';
import Link from 'next/link';

export default function ScansPage() {
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [scanLogs, setScanLogs] = useState<string[]>([]);

  const startLiveScan = () => {
    setIsScanning(true);
    setScanProgress(0);
    setScanLogs(['[INIT] Multi-scanner orchestration pipeline spawned...']);

    const steps = [
      { p: 20, delay: 700, log: '[SUBFINDER] Enumerate DNS records -> demo.vixor.local (192.168.1.50)' },
      { p: 40, delay: 1700, log: '[NMAP] Port probe completed: 443/tcp (https), 8000/tcp (http-alt)' },
      { p: 65, delay: 3000, log: '[OWASP-ZAP] Cross-Site Scripting vector confirmed on /search endpoint' },
      { p: 85, delay: 4500, log: '[NUCLEI] CVE-2024 SQL Injection signature verified on /auth/login' },
      { p: 95, delay: 6000, log: '[AI-ML] Prioritized Risk calculated (94.5/100) with SHAP attribution weights' },
      { p: 100, delay: 7200, log: '[SUCCESS] Pipeline completed. 3 Findings synchronized.' }
    ];

    steps.forEach(({ p, delay, log }) => {
      setTimeout(() => {
        setScanProgress(p);
        setScanLogs(prev => [...prev, log]);
      }, delay);
    });
  };

  return (
    <div className="min-h-screen bg-[#07090D] text-[#E6EDF3] p-8 relative">
      {isScanning && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0E131B] border border-[#22D3EE]/50 w-full max-w-2xl rounded-2xl shadow-2xl p-6 space-y-4">
            <div className="flex justify-between items-center border-b border-[#1F2937] pb-3">
              <h3 className="font-bold text-white flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#22D3EE] animate-ping"></span>
                <span>Executing Unified Scanning Pipeline</span>
              </h3>
              <span className="text-xs font-mono text-[#22D3EE] bg-[#161B22] px-2.5 py-1 rounded">
                {scanProgress}%
              </span>
            </div>

            <div className="w-full bg-[#161B22] h-2 rounded-full overflow-hidden">
              <div
                className="bg-[#22D3EE] h-full transition-all duration-300"
                style={{ width: `${scanProgress}%` }}
              ></div>
            </div>

            <div className="bg-[#05070A] border border-[#1F2937] rounded-xl p-4 font-mono text-xs text-gray-300 h-56 overflow-y-auto space-y-1.5">
              {scanLogs.map((log, i) => (
                <div key={i} className="flex space-x-2">
                  <span className="text-gray-500">&gt;</span>
                  <span className={log.includes('SUCCESS') ? 'text-emerald-400 font-bold' : log.includes('SQL') || log.includes('XSS') ? 'text-amber-400' : 'text-gray-300'}>{log}</span>
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-2">
              {scanProgress === 100 && (
                <button
                  onClick={() => setIsScanning(false)}
                  className="px-4 py-1.5 bg-[#22D3EE] text-black font-bold text-xs rounded-lg hover:bg-[#06B6D4] transition"
                >
                  Close Console
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">Multi-Tool Vulnerability Scans</h1>
            <p className="text-gray-400 mt-1">Autonomous execution of Nuclei, OWASP ZAP, and Nmap service discovery.</p>
          </div>
          <button
            onClick={startLiveScan}
            className="px-4 py-2 bg-[#22D3EE] hover:bg-[#06B6D4] text-black font-semibold rounded-lg transition text-sm flex items-center space-x-2"
          >
            <span>Launch New Scan</span>
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
