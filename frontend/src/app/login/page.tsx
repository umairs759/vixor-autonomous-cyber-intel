'use client';

import React, { useState } from 'react';

export default function LoginPage() {
  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('Admin123!');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Invalid email or password');
      }

      const data = await res.json();
      const token = data.access_token || data.token || data?.data?.access_token || 'demo-token';

      document.cookie = `access_token=${token}; path=/; max-age=86400; SameSite=Lax`;
      document.cookie = `token=${token}; path=/; max-age=86400; SameSite=Lax`;
      localStorage.setItem('access_token', token);
      localStorage.setItem('token', token);

      window.location.href = '/dashboard';
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#07090D] text-[#E6EDF3] flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-[#0E131B] border border-[#1F2937] rounded-xl p-8 shadow-2xl">
        <div className="flex items-center space-x-3 mb-6">
          <div className="w-8 h-8 rounded bg-[#22D3EE] flex items-center justify-center text-black font-bold">V</div>
          <h1 className="text-2xl font-bold tracking-wider">VIXOR</h1>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-950/60 border border-red-800 text-red-200 text-sm rounded-lg">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[#161B22] border border-[#30363D] rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#22D3EE]"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[#161B22] border border-[#30363D] rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#22D3EE]"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-[#22D3EE] hover:bg-[#06B6D4] text-black font-semibold rounded-lg transition duration-200"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
        <p className="mt-6 text-xs text-gray-500 text-center">
          Management stakeholders: read-only executive summary view.
        </p>
      </div>
    </div>
  );
}
