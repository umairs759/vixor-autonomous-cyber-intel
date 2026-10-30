'use client';

import React, { useState } from 'react';

export default function FindingsPage() {
  const [findings] = useState([
    {
      id: 'f-1',
      title: 'SQL Injection in Authentication API Endpoint',
      severity: 'CRITICAL',
      cvss: 9.8,
      tool: 'Nuclei',
      asset: 'demo.vixor.local:443',
      ml_score: 94.5,
      risk_class: 'CRITICAL',
      shap: { 'Exploitability': '+0.45', 'Asset Criticality': '+0.35', 'Auth Required': '-0.15' },
      narrative: 'Critical SQL injection detected on public-facing login API with verified exploitation vector.',
      remediation: 'Implement parameterized queries and use SQLAlchemy ORM binding.'
    },
    {
      id: 'f-2',
      title: 'Cross-Site Scripting (Reflected) in Search Query',
      severity: 'HIGH',
      cvss: 7.5,
      tool: 'OWASP ZAP',
      asset: 'demo.vixor.local:443',
      ml_score: 78.2,
      risk_class: 'HIGH',
      shap: { 'Exploitability': '+0.32', 'Asset Criticality': '+0.28', 'WAF Present': '-0.10' },
      narrative: 'Reflected XSS vulnerability in query parameter allowing session hijacking under standard browser contexts.',
      remediation: 'Sanitize all user-supplied input and configure Content Security Policy (CSP).'
    },
    {
      id: 'f-3',
      title: 'Outdated OpenSSL Service with Known Vulnerabilities',
      severity: 'MEDIUM',
      cvss: 5.3,
      tool: 'Nmap',
      asset: 'api.vixor.local:8000',
      ml_score: 52.0,
      risk_class: 'MEDIUM',
      shap: { 'Service Exposure': '+0.25', 'Patch Availability': '+0.20' },
      narrative: 'Legacy OpenSSL version identified on port 443 with known moderate cryptographic weaknesses.',
      remediation: 'Upgrade OpenSSL to the latest TLS 1.3 compliant release.'
    }
  ]);

  return (
    <div className="min-h-screen bg-[#07090D] text-[#E6EDF3] p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Identified Vulnerabilities & Explainable AI (XAI)</h1>
          <p className="text-gray-400 mt-1">Multi-tool findings prioritized by Machine Learning models with SHAP attribution.</p>
        </div>

        <div className="space-y-4">
          {findings.map((f) => (
            <div key={f.id} className="bg-[#0E131B] border border-[#1F2937] p-6 rounded-xl space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <div className="flex items-center space-x-3">
                    <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${
                      f.severity === 'CRITICAL' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                      f.severity === 'HIGH' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                      'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                    }`}>{f.severity}</span>
                    <span className="text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded font-mono">Tool: {f.tool}</span>
                    <span className="text-xs text-gray-400 font-mono">Target: {f.asset}</span>
                  </div>
                  <h2 className="text-xl font-bold mt-2 text-white">{f.title}</h2>
                </div>
                <div className="text-right">
                  <p className="text-xs uppercase text-gray-400 font-semibold">ML Risk Score</p>
                  <p className="text-2xl font-black text-[#22D3EE]">{f.ml_score} <span className="text-xs text-gray-400">/ 100</span></p>
                </div>
              </div>

              <div className="bg-[#161B22] p-4 rounded-lg border border-[#30363D]">
                <p className="text-xs font-semibold uppercase text-cyan-400 mb-2">SHAP Feature Attribution (Explainable AI)</p>
                <div className="grid grid-cols-3 gap-4 text-xs mb-3">
                  {Object.entries(f.shap).map(([key, val]) => (
                    <div key={key} className="bg-black/30 p-2 rounded">
                      <span className="text-gray-400 block">{key}:</span>
                      <span className="font-mono font-bold text-white">{val}</span>
                    </div>
                  ))}
                </div>
                <p className="text-sm text-gray-300"><span className="text-gray-400 font-semibold">Risk Narrative:</span> {f.narrative}</p>
                <p className="text-sm text-emerald-400 mt-2"><span className="font-semibold text-gray-400">Remediation:</span> {f.remediation}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
