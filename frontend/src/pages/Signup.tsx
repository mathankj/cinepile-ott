import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { auth } from "../api";
import { apiErrorMessage } from "../api/client";
import { useAuthStore } from "../stores/auth";

export default function Signup() {
  const nav = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const res = await auth.signup(email.trim(), password, name.trim() || null);
      setAuth(res.tokens.access_token, res.tokens.refresh_token, res.user);
      nav("/", { replace: true });
    } catch (e) {
      setErr(apiErrorMessage(e, "Couldn't create your account."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-[80vh] place-items-center px-4">
      <div className="w-full max-w-md rounded bg-black/75 p-8 md:p-12">
        <h1 className="mb-6 text-[2rem] font-bold">Create account</h1>
        <form onSubmit={onSubmit} className="space-y-4">
          <input
            type="text"
            placeholder="Full name (optional)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input-base"
          />
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
            placeholder="Password (8+ characters)"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input-base"
            minLength={8}
            required
          />
          {err && <div className="rounded border border-red-500/50 bg-red-500/10 p-3 text-sm text-red-200">{err}</div>}
          <button type="submit" disabled={busy} className="btn-primary w-full disabled:opacity-60">
            {busy ? "Creating…" : "Sign up"}
          </button>
        </form>
        <div className="mt-8 text-sm text-white/60">
          Already have an account?{" "}
          <Link to="/login" className="text-white hover:underline">
            Sign in
          </Link>
          .
        </div>
      </div>
    </div>
  );
}
