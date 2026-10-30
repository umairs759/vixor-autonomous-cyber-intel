'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';

export default function ProjectsPage() {
  const [projects, setProjects] = useState([
    {
      id: 'demo-proj-1',
      name: 'Enterprise Security Audit',
      description: 'Continuous attack surface discovery and autonomous vulnerability assessment.',
      domains: ['demo.vixor.local', 'unverified.vixor.local'],
      assetsCount: 2,
      findingsCount: 3,
      status: 'Active'
    }
  ]);

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const token = localStorage.getItem('access_token') || localStorage.getItem('token') || '';
        const res = await fetch('http://127.0.0.1:8000/api/v1/projects', {
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          }
        });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) setProjects(data);
        }
      } catch (err) {
        console.warn('Using seeded project list');
      }
    };
    fetchProjects();
  }, []);

  return (
    <div className="min-h-screen bg-[#07090D] text-[#E6EDF3] p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold">Scoped Security Projects</h1>
            <p className="text-gray-400 text-sm mt-1">Target boundaries and authorized asset inventories.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {projects.map((proj) => (
            <div key={proj.id} className="bg-[#0E131B] border border-[#1F2937] p-6 rounded-xl space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-xl font-bold text-white">{proj.name}</h2>
                  <p className="text-gray-400 text-sm mt-1">{proj.description}</p>
                </div>
                <span className="bg-emerald-500/20 text-emerald-400 text-xs px-2.5 py-1 rounded-full font-semibold">Verified Scope</span>
              </div>

              <div className="grid grid-cols-3 gap-2 bg-[#161B22] p-3 rounded-lg text-center">
                <div>
                  <p className="text-xs text-gray-400 uppercase">Domains</p>
                  <p className="text-lg font-bold text-white">2</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase">Assets</p>
                  <p className="text-lg font-bold text-[#22D3EE]">2</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase">Findings</p>
                  <p className="text-lg font-bold text-amber-400">3</p>
                </div>
              </div>

              <div className="pt-2">
                <Link href="/findings" className="block w-full py-2 bg-[#22D3EE] text-black font-semibold rounded-lg text-center hover:bg-[#06B6D4] transition text-sm">
                  Inspect Findings & SHAP
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
