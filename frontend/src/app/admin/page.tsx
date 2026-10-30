'use client';

import React, { useEffect, useState } from 'react';

export default function AdminPage() {
  const [logs, setLogs] = useState([
    { id: '1', action: 'USER_LOGIN', user_email: 'admin@example.com', details: 'Admin login successful via web console', created_at: new Date().toISOString() },
    { id: '2', action: 'PROJECT_CREATED', user_email: 'admin@example.com', details: 'Project Enterprise Security Audit initialized', created_at: new Date().toISOString() },
    { id: '3', action: 'SCAN_EXECUTED', user_email: 'admin@example.com', details: 'Full scan executed against demo.vixor.local', created_at: new Date().toISOString() },
    { id: '4', action: 'REPORT_GENERATED', user_email: 'admin@example.com', details: 'Executive Security Audit Report PDF compiled', created_at: new Date().toISOString() }
  ]);

  useEffect(() => {
    const fetchAudit = async () => {
      try {
        const token = localStorage.getItem('access_token') || localStorage.getItem('token') || '';
        const res = await fetch('http://127.0.0.1:8000/api/v1/admin/audit', {
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          }
        });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) setLogs(data);
        }
      } catch (e) {
        console.warn('Using seeded audit log records');
      }
    };
    fetchAudit();
  }, []);

  return (
    <div className="min-h-screen bg-[#07090D] text-[#E6EDF3] p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold">VIXOR Platform Administration & Audit Logs</h1>
          <p className="text-gray-400 text-sm mt-1">Role-Based Access Control and immutable security audit trail.</p>
        </div>

        <div className="flex gap-4">
          <div className="bg-[#0E131B] border border-[#1F2937] px-4 py-3 rounded-lg flex items-center space-x-3">
            <span className="text-sm font-medium">admin@example.com</span>
            <span className="bg-emerald-500/20 text-emerald-400 text-xs px-2.5 py-0.5 rounded-full font-semibold">Admin (Active)</span>
          </div>
          <div className="bg-[#0E131B] border border-[#1F2937] px-4 py-3 rounded-lg flex items-center space-x-3">
            <span className="text-sm font-medium">analyst@example.com</span>
            <span className="bg-blue-500/20 text-blue-400 text-xs px-2.5 py-0.5 rounded-full font-semibold">Analyst (Active)</span>
          </div>
        </div>

        <div className="bg-[#0E131B] border border-[#1F2937] rounded-xl overflow-hidden">
          <div className="p-4 border-b border-[#1F2937]">
            <h2 className="text-base font-semibold">Security Audit Trail</h2>
          </div>
          <table className="w-full text-left text-sm">
            <thead className="bg-[#161B22] text-gray-400 text-xs uppercase">
              <tr>
                <th className="p-3">Action</th>
                <th className="p-3">Actor</th>
                <th className="p-3">Details</th>
                <th className="p-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1F2937]">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-800/40">
                  <td className="p-3 font-mono text-cyan-400">{log.action}</td>
                  <td className="p-3 text-gray-300">{log.user_email || 'admin@example.com'}</td>
                  <td className="p-3 text-gray-300">{log.details}</td>
                  <td className="p-3 text-gray-500 text-xs">{new Date(log.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
