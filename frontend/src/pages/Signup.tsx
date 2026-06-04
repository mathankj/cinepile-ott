import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { auth } from "../api";
import { apiErrorMessage } from "../api/client";
import { useAuthStore } from "../stores/auth";
import AuthShell from "../components/auth/AuthShell";

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
    <AuthShell
      title="Create your account"
      footer={
        <span>
          Already on CinePile?{" "}
          <Link to="/login" className="text-white hover:underline">
            Sign in
          </Link>
          .
        </span>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <FloatingField
          id="signup-name"
          type="text"
          label="Full name"
          autoComplete="name"
          value={name}
          onChange={setName}
        />
        <FloatingField
          id="signup-email"
          type="email"
          label="Email"
          autoComplete="email"
          value={email}
          onChange={setEmail}
          required
        />
        <FloatingField
          id="signup-password"
          type="password"
          label="Password (8+ characters)"
          autoComplete="new-password"
          value={password}
          onChange={setPassword}
          minLength={8}
          required
        />
        {err && (
          <div
            role="alert"
            className="rounded border border-red-500/50 bg-red-500/10 p-3 text-sm text-red-200"
          >
            {err}
          </div>
        )}
        <button
          type="submit"
          disabled={busy}
          className="mt-2 w-full rounded bg-[var(--color-brand)] py-3 text-base font-semibold text-white transition-colors hover:bg-[var(--color-brand-hover)] active:bg-[var(--color-brand-dark)] disabled:opacity-60"
        >
          {busy ? "Creating account…" : "Sign Up"}
        </button>
      </form>
    </AuthShell>
  );
}

function FloatingField({
  id,
  label,
  type,
  value,
  onChange,
  autoComplete,
  required,
  minLength,
}: {
  id: string;
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete?: string;
  required?: boolean;
  minLength?: number;
}) {
  return (
    <div className="relative">
      <input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete}
        required={required}
        minLength={minLength}
        placeholder=" "
        className="input-auth"
      />
      <label htmlFor={id} className="input-auth-label">
        {label}
      </label>
    </div>
  );
}
