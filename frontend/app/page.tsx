"use client";

/**
 * Module overview for frontend/app/page.tsx.
 * Implements user-facing UI behavior for this route or component.
 */

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { clearToken, getToken, setToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasSavedSession, setHasSavedSession] = useState(false);

  useEffect(() => {
    setHasSavedSession(!!getToken());
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.login({ email, password });
      setToken(res.access_token);
      router.push("/campaigns");
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto mt-24 max-w-md rounded-xl border bg-white p-6 shadow-sm">
      <h1 className="text-2xl font-bold">LaunchPad Conversion Lab</h1>
      <p className="mb-4 text-sm text-slate-600">Sign in to run closed-loop optimization.</p>
      {hasSavedSession ? (
        <div className="mb-3 rounded border bg-slate-50 p-3 text-sm">
          <p className="text-slate-700">A saved session is available.</p>
          <div className="mt-2 flex gap-2">
            <button className="rounded bg-slate-800 px-3 py-1 text-xs text-white" onClick={() => router.push("/campaigns")} type="button">
              Continue Saved Session
            </button>
            <button
              className="rounded border px-3 py-1 text-xs"
              onClick={() => {
                clearToken();
                setHasSavedSession(false);
              }}
              type="button"
            >
              Sign In As Different User
            </button>
          </div>
        </div>
      ) : null}
      <form className="space-y-3" onSubmit={onSubmit}>
        <input className="w-full rounded border p-2" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input className="w-full rounded border p-2" placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}
        <button className="w-full rounded bg-accent py-2 text-white" disabled={loading}>
          {loading ? "Signing in..." : "Sign In"}
        </button>
      </form>
    </div>
  );
}
