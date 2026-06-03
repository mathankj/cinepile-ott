import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { auth } from "../api";
import { apiErrorMessage } from "../api/client";
import { useAuthStore } from "../stores/auth";
import AuthShell from "../components/auth/AuthShell";

export default function Login() {
  const nav = useNavigate();
  const loc = useLocation();
  const setAuth = useAuthStore((s) => s.setAuth);
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
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
      setErr(apiErrorMessage(e, t("auth.wrong_credentials")));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title={t("auth.sign_in_title")}
      footer={
        <span>
          {t("auth.new_to_brand")}{" "}
          <Link to="/signup" className="text-white hover:underline">
            {t("auth.sign_up_now")}
          </Link>
          .
        </span>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <FloatingField
          id="login-email"
          type="email"
          label={t("auth.email")}
          autoComplete="email"
          value={email}
          onChange={setEmail}
          required
        />
        <FloatingField
          id="login-password"
          type="password"
          label={t("auth.password")}
          autoComplete="current-password"
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
          {busy ? t("auth.signing_in") : t("auth.sign_in_cta")}
        </button>
        <div className="mt-3 flex items-center justify-between text-sm text-white/70">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="h-4 w-4 accent-white"
            />
            {t("auth.remember_me")}
          </label>
          <Link to="/login" className="hover:underline">
            {t("auth.need_help")}
          </Link>
        </div>
      </form>
    </AuthShell>
  );
}

/**
 * Netflix-style floating-label input. The <input> uses `placeholder=" "` so
 * `:not(:placeholder-shown)` triggers the label lift. The label is a sibling
 * positioned absolutely over the input.
 */
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
