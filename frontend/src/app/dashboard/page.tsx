'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';

export default function DashboardPage() {
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [scanLogs, setScanLogs] = useState<string[]>([]);

  const startLiveScan = () => {
    setIsScanning(true);
    setScanProgress(0);
    setScanLogs(['[INIT] Authenticating session & verifying target scope boundaries...']);

    const milestones = [
      { p: 15, delay: 800, log: '[DISCOVERY] Target demo.vixor.local resolved -> IP: 192.168.1.50 (Port 443 https)' },
      { p: 30, delay: 1800, log: '[DISCOVERY] Target api.vixor.local resolved -> IP: 192.168.1.51 (Port 8000 http)' },
      { p: 45, delay: 3000, log: '[SCAN:NMAP] Service probing: OpenSSL legacy daemon detected on 192.168.1.50:443' },
      { p: 60, delay: 4200, log: '[SCAN:ZAP] Web spider active. Injected payload /search?q=<script> -> Reflected XSS verified!' },
      { p: 75, delay: 5600, log: '[SCAN:NUCLEI] Executing 4,200+ CVE checks... SQL Injection verified on /api/v1/auth/login' },
      { p: 88, delay: 7000, log: '[AI-ENGINE] Feeding feature vectors to XGBoost model. Contextual ML Risk: 94.5/100 (CRITICAL)' },
      { p: 95, delay: 8400, log: '[XAI:SHAP] Exploitability (+0.45), Asset Criticality (+0.35) -> Chained Attack Risk: 88' },
      { p: 100, delay: 9600, log: '[COMPLETE] Multi-engine scan finished. 3 Findings committed to database & telemetry updated.' }
    ];

    milestones.forEach(({ p, delay, log }) => {
      setTimeout(() => {
        setScanProgress(p);
        setScanLogs(prev => [...prev, log]);
      }, delay);
    });
  };

  return (
    <div className="min-h-screen bg-[#07090D] text-[#E6EDF3] p-6 lg:p-8 space-y-6 relative">
      {/* Live Interactive Scanning Modal */}
      {isScanning && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0E131B] border border-[#22D3EE]/50 w-full max-w-3xl rounded-2xl shadow-2xl p-6 space-y-5">
            <div className="flex justify-between items-center border-b border-[#1F2937] pb-4">
              <div className="flex items-center space-x-3">
                <span className="w-3 h-3 rounded-full bg-[#22D3EE] animate-ping"></span>
                <h3 className="font-bold text-lg text-white">VIXOR Autonomous Scanning Engine Live</h3>
              </div>
              <span className="text-xs font-mono bg-[#161B22] text-[#22D3EE] px-3 py-1 rounded border border-[#22D3EE]/30">
                {scanProgress}% COMPLETED
              </span>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-[#161B22] h-2.5 rounded-full overflow-hidden border border-gray-800">
              <div
                className="bg-gradient-to-r from-cyan-500 via-amber-400 to-emerald-400 h-full transition-all duration-300"
                style={{ width: `${scanProgress}%` }}
              ></div>
            </div>

            {/* Terminal Console Stream */}
            <div className="bg-[#05070A] border border-[#1F2937] rounded-xl p-4 font-mono text-xs text-gray-300 h-64 overflow-y-auto space-y-2">
              {scanLogs.map((log, index) => (
                <div key={index} className="flex space-x-2">
                  <span className="text-gray-500 select-none">&gt;</span>
                  <span className={
                    log.includes('CRITICAL') || log.includes('SQL Injection') ? 'text-rose-400 font-bold' :
                    log.includes('Reflected XSS') || log.includes('HIGH') ? 'text-amber-400 font-semibold' :
                    log.includes('COMPLETE') ? 'text-emerald-400 font-bold' :
                    log.includes('AI-ENGINE') || log.includes('SHAP') ? 'text-[#22D3EE]' :
                    'text-gray-300'
                  }>
                    {log}
                  </span>
                </div>
              ))}
            </div>

            <div className="flex justify-between items-center pt-2">
              <p className="text-xs text-gray-500">Autonomous multi-tool probe running against authorized scope.</p>
              {scanProgress === 100 ? (
                <button
                  onClick={() => setIsScanning(false)}
                  className="px-5 py-2 bg-[#22D3EE] text-black font-bold text-xs rounded-lg hover:bg-[#06B6D4] transition"
                >
                  Close & View Telemetry
                </button>
              ) : (
                <span className="text-xs text-gray-400 font-mono animate-pulse">Running engine pipelines...</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-[#1F2937] gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <span className="flex h-3 w-3 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
            <h1 className="text-2xl font-bold tracking-tight text-white">VIXOR Security Operations Center (SOC)</h1>
          </div>
          <p className="text-gray-400 text-xs mt-1">Autonomous Attack Surface Intelligence & Explainable AI Prioritization Pipeline</p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={startLiveScan}
            className="px-4 py-2 bg-[#161B22] border border-[#22D3EE]/50 hover:bg-[#22D3EE]/10 text-xs font-semibold rounded-lg text-[#22D3EE] transition flex items-center space-x-2"
          >
            <span className="w-2 h-2 rounded-full bg-[#22D3EE] animate-pulse"></span>
            <span>Trigger Full Scan</span>
          </button>
          <Link href="/reports" className="px-4 py-2 bg-[#22D3EE] hover:bg-[#06B6D4] text-black text-xs font-bold rounded-lg transition shadow-lg shadow-cyan-500/20">
            Export Executive PDF
          </Link>
        </div>
      </div>

      {/* Top 4 KPI Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#0E131B] border border-[#1F2937] p-5 rounded-xl">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Scoped Projects</p>
              <p className="text-3xl font-black text-white mt-1">01</p>
            </div>
            <span className="p-2 rounded-lg bg-cyan-500/10 text-[#22D3EE] text-xs font-mono">100% Active</span>
          </div>
          <div className="mt-4 flex items-center text-[11px] text-gray-400">
            <span className="text-emerald-400 font-semibold mr-1">Bound:</span> Enterprise Security Audit
          </div>
        </div>

        <div className="bg-[#0E131B] border border-[#1F2937] p-5 rounded-xl">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Monitored Assets</p>
              <p className="text-3xl font-black text-[#22D3EE] mt-1">02</p>
            </div>
            <span className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 text-xs font-mono">2 Live Hosts</span>
          </div>
          <div className="mt-4 flex items-center text-[11px] text-gray-400">
            <span className="text-cyan-400 font-semibold mr-1">Discovery:</span> demo.vixor.local | api.vixor.local
          </div>
        </div>

        <div className="bg-[#0E131B] border border-[#1F2937] p-5 rounded-xl">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Vulnerabilities Detected</p>
              <p className="text-3xl font-black text-amber-400 mt-1">03</p>
            </div>
            <span className="p-2 rounded-lg bg-rose-500/10 text-rose-400 text-xs font-mono">1 Critical</span>
          </div>
          <div className="mt-4 flex items-center text-[11px] text-gray-400">
            <span className="text-amber-400 font-semibold mr-1">Tools:</span> Nuclei, OWASP ZAP, Nmap
          </div>
        </div>

        <div className="bg-[#0E131B] border border-[#1F2937] p-5 rounded-xl">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Attack Chains Correlated</p>
              <p className="text-3xl font-black text-rose-500 mt-1">01</p>
            </div>
            <span className="p-2 rounded-lg bg-rose-500/20 text-rose-400 text-xs font-bold">Risk: 88/100</span>
          </div>
          <div className="mt-4 flex items-center text-[11px] text-gray-400">
            <span className="text-rose-400 font-semibold mr-1">Vector:</span> Auth Bypass to Lateral Pivot
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-[#0E131B] border border-[#1F2937] p-6 rounded-xl space-y-5">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-base font-bold text-white">Continuous AI Risk Prioritization vs Static CVSS</h2>
                <p className="text-xs text-gray-400 mt-0.5">Machine Learning (Random Forest & XGBoost) feature-weighted risk index</p>
              </div>
              <span className="text-[11px] bg-[#161B22] border border-[#30363D] px-2.5 py-1 rounded text-cyan-400 font-mono">
                XAI Enabled
              </span>
            </div>

            <div className="space-y-4 pt-2">
              <div>
                <div className="flex justify-between text-xs mb-1.5 font-medium">
                  <span className="flex items-center space-x-2 text-rose-400">
                    <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                    <span>Critical Risk Exposure (Score &gt; 90)</span>
                  </span>
                  <span className="font-mono text-white">1 Finding (94.5 / 100)</span>
                </div>
                <div className="w-full bg-[#161B22] h-2.5 rounded-full overflow-hidden border border-gray-800">
                  <div className="bg-gradient-to-r from-rose-600 to-rose-400 h-full w-[94.5%] rounded-full"></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1.5 font-medium">
                  <span className="flex items-center space-x-2 text-amber-400">
                    <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                    <span>High Risk Vulnerability (Score 70-89)</span>
                  </span>
                  <span className="font-mono text-white">1 Finding (78.2 / 100)</span>
                </div>
                <div className="w-full bg-[#161B22] h-2.5 rounded-full overflow-hidden border border-gray-800">
                  <div className="bg-gradient-to-r from-amber-600 to-amber-400 h-full w-[78.2%] rounded-full"></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1.5 font-medium">
                  <span className="flex items-center space-x-2 text-blue-400">
                    <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                    <span>Medium Service Exposure (Score 40-69)</span>
                  </span>
                  <span className="font-mono text-white">1 Finding (52.0 / 100)</span>
                </div>
                <div className="w-full bg-[#161B22] h-2.5 rounded-full overflow-hidden border border-gray-800">
                  <div className="bg-gradient-to-r from-blue-600 to-blue-400 h-full w-[52%] rounded-full"></div>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-[#1F2937] grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
              <div className="bg-[#161B22] p-3 rounded-lg border border-[#30363D]">
                <p className="text-gray-400 text-[10px] uppercase font-semibold">Web Tier (443)</p>
                <p className="font-bold text-white mt-1">Nginx 1.24 + React</p>
                <span className="text-[10px] text-rose-400 font-mono">2 Vulnerabilities</span>
              </div>
              <div className="bg-[#161B22] p-3 rounded-lg border border-[#30363D]">
                <p className="text-gray-400 text-[10px] uppercase font-semibold">API Tier (8000)</p>
                <p className="font-bold text-white mt-1">FastAPI + Python 3.11</p>
                <span className="text-[10px] text-blue-400 font-mono">1 Service Warning</span>
              </div>
              <div className="bg-[#161B22] p-3 rounded-lg border border-[#30363D] col-span-2 sm:col-span-1">
                <p className="text-gray-400 text-[10px] uppercase font-semibold">Data Layer</p>
                <p className="font-bold text-white mt-1">PostgreSQL 15</p>
                <span className="text-[10px] text-emerald-400 font-mono">Encrypted & Isolated</span>
              </div>
            </div>
          </div>

          <div className="bg-[#0E131B] border border-[#1F2937] rounded-xl overflow-hidden">
            <div className="p-4 border-b border-[#1F2937] flex justify-between items-center">
              <h2 className="text-sm font-bold text-white">Active Vulnerability Triage Queue</h2>
              <Link href="/findings" className="text-xs text-[#22D3EE] hover:underline font-medium">
                View All Findings &rarr;
              </Link>
            </div>
            <div className="divide-y divide-[#1F2937] text-xs">
              <div className="p-4 flex items-center justify-between hover:bg-[#161B22]/50 transition">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="bg-rose-500/20 text-rose-400 text-[10px] px-2 py-0.5 rounded font-bold">CRITICAL</span>
                    <span className="font-semibold text-white">SQL Injection in Authentication API</span>
                  </div>
                  <p className="text-gray-400 text-[11px]">Nuclei Engine | Target: demo.vixor.local:443</p>
                </div>
                <div className="text-right">
                  <span className="font-bold text-rose-400 font-mono text-sm">94.5</span>
                  <p className="text-[10px] text-gray-500">ML Risk Score</p>
                </div>
              </div>

              <div className="p-4 flex items-center justify-between hover:bg-[#161B22]/50 transition">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="bg-amber-500/20 text-amber-400 text-[10px] px-2 py-0.5 rounded font-bold">HIGH</span>
                    <span className="font-semibold text-white">Cross-Site Scripting (Reflected) in Search Query</span>
                  </div>
                  <p className="text-gray-400 text-[11px]">OWASP ZAP | Target: demo.vixor.local:443</p>
                </div>
                <div className="text-right">
                  <span className="font-bold text-amber-400 font-mono text-sm">78.2</span>
                  <p className="text-[10px] text-gray-500">ML Risk Score</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          <div className="bg-[#0E131B] border border-[#1F2937] p-6 rounded-xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-white uppercase tracking-wider text-rose-400">
                Attack Chain Correlation
              </h2>
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
            </div>

            <div className="p-4 rounded-xl bg-gradient-to-br from-rose-950/40 to-transparent border border-rose-900/40 text-center">
              <p className="text-[10px] text-gray-400 uppercase font-semibold">Chained Compromise Feasibility</p>
              <p className="text-4xl font-black text-rose-500 mt-1">88 <span className="text-xs text-gray-400">/ 100</span></p>
              <p className="text-xs text-gray-300 mt-2 font-medium">Auth Bypass to Lateral Pivot</p>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="p-2.5 bg-[#161B22] rounded-lg border border-[#30363D] flex items-center space-x-3">
                <span className="w-5 h-5 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center font-bold text-[10px]">1</span>
                <span className="text-gray-300">SQLi bypasses auth guard</span>
              </div>
              <div className="p-2.5 bg-[#161B22] rounded-lg border border-[#30363D] flex items-center space-x-3">
                <span className="w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold text-[10px]">2</span>
                <span className="text-gray-300">Reflected XSS exfiltrates token</span>
              </div>
              <div className="p-2.5 bg-[#161B22] rounded-lg border border-[#30363D] flex items-center space-x-3">
                <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-[10px]">3</span>
                <span className="text-gray-300">Lateral call to internal API (8000)</span>
              </div>
            </div>

            <Link href="/correlations" className="block text-center w-full py-2 bg-[#161B22] hover:bg-gray-800 border border-[#30363D] text-xs font-semibold text-cyan-400 rounded-lg transition">
              Inspect Correlation Graph &rarr;
            </Link>
          </div>

          <div className="bg-[#0E131B] border border-[#1F2937] p-6 rounded-xl space-y-4">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider text-cyan-400">
              SHAP Attribution Engine
            </h2>
            <p className="text-xs text-gray-400">
              Dynamic Explainable AI (XAI) feature weights calculated for prioritized findings.
            </p>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between p-2 bg-[#161B22] rounded border border-[#30363D]">
                <span className="text-gray-400">Exploitability</span>
                <span className="font-mono font-bold text-emerald-400">+0.45</span>
              </div>
              <div className="flex justify-between p-2 bg-[#161B22] rounded border border-[#30363D]">
                <span className="text-gray-400">Asset Criticality</span>
                <span className="font-mono font-bold text-cyan-400">+0.35</span>
              </div>
              <div className="flex justify-between p-2 bg-[#161B22] rounded border border-[#30363D]">
                <span className="text-gray-400">Auth Barrier</span>
                <span className="font-mono font-bold text-gray-400">-0.15</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
