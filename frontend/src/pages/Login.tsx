import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { auth } from "../api";
import { apiErrorMessage } from "../api/client";
import { useAuthStore } from "../stores/auth";

export default function Login() {
  const nav = useNavigate();
  const loc = useLocation();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const redirect = (loc.state as { from?: string } | null)?.from ?? "/";

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const res = await auth.login(email.trim(), password);
      setAuth(res.tokens.access_token, res.tokens.refresh_token, res.user);
      nav(redirect, { replace: true });
    } catch (e) {
      setErr(apiErrorMessage(e, "Couldn't sign you in. Check your credentials."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-[80vh] place-items-center px-4">
      <div className="w-full max-w-md rounded bg-black/75 p-8 md:p-12">
        <h1 className="mb-6 text-[2rem] font-bold">Sign In</h1>
        <form onSubmit={onSubmit} className="space-y-4">
          <input
            type="email"
            placeholder="Email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input-base"
            required
          />
          <input
            type="password"
            placeholder="Password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input-base"
            minLength={8}
            required
          />
          {err && <div className="rounded border border-red-500/50 bg-red-500/10 p-3 text-sm text-red-200">{err}</div>}
          <button type="submit" disabled={busy} className="btn-primary w-full disabled:opacity-60">
            {busy ? "Signing in…" : "Sign In"}
          </button>
        </form>
        <div className="mt-8 text-sm text-white/60">
          New to Anjaneya?{" "}
          <Link to="/signup" className="text-white hover:underline">
            Sign up now
          </Link>
          .
        </div>
      </div>
    </div>
  );
}
