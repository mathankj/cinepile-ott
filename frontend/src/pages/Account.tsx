import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { auth } from "../api";
import { apiErrorMessage } from "../api/client";
import { useAuthStore } from "../stores/auth";

/**
 * Account page — /account (protected).
 *
 * Shows the signed-in user's details from the auth store and hosts the
 * change-password form. Changing the password revokes every OTHER session
 * server-side and returns a fresh token pair for THIS one — we must swap the
 * stored tokens immediately or the next request would 401.
 */
export default function Account() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="mx-auto max-w-[640px] px-4 md:px-8 py-12">
      <h1 className="mb-8 text-[2rem] font-bold">Account</h1>

      {/* Profile details */}
      <div className="rounded border border-white/10 bg-[var(--color-bg-elevated)] p-5">
        <h3 className="text-sm uppercase tracking-wider text-white/60">Your details</h3>
        <dl className="mt-4 grid grid-cols-[120px_1fr] gap-y-3 text-sm">
          <dt className="text-white/60">Email</dt>
          <dd className="font-medium">{user?.email ?? "—"}</dd>
          <dt className="text-white/60">Name</dt>
          <dd>{user?.full_name ?? "—"}</dd>
          <dt className="text-white/60">Role</dt>
          <dd className="capitalize">{user?.role.replace("_", " ") ?? "—"}</dd>
          <dt className="text-white/60">Member since</dt>
          <dd>{user ? new Date(user.created_at).toLocaleDateString() : "—"}</dd>
        </dl>
      </div>

      <ChangePasswordCard />
    </div>
  );
}

function ChangePasswordCard() {
  const setTokens = useAuthStore((s) => s.setTokens);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const changeM = useMutation({
    mutationFn: () => auth.changePassword(current, next),
    onSuccess: (tokens) => {
      // The backend revoked all other sessions and rotated ours — store the
      // fresh pair so this session keeps working.
      setTokens(tokens.access_token, tokens.refresh_token);
      setDone(true);
      setErr(null);
      setCurrent("");
      setNext("");
      setConfirm("");
    },
    onError: (e) => setErr(apiErrorMessage(e)),
  });

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setDone(false);
    if (next.length < 8) {
      setErr("New password must be at least 8 characters.");
      return;
    }
    if (next !== confirm) {
      setErr("New passwords don't match.");
      return;
    }
    setErr(null);
    changeM.mutate();
  }

  return (
    <form
      onSubmit={onSubmit}
      className="mt-6 rounded border border-white/10 bg-[var(--color-bg-elevated)] p-5"
    >
      <h3 className="text-sm uppercase tracking-wider text-white/60">Change password</h3>
      <p className="mt-1 text-sm text-white/70">
        Changing your password signs you out everywhere else.
      </p>

      <label className="mt-4 block text-xs uppercase tracking-wider text-white/60">
        Current password
      </label>
      <input
        type="password"
        autoComplete="current-password"
        className="input-base"
        value={current}
        onChange={(e) => setCurrent(e.target.value)}
      />
      <label className="mt-3 block text-xs uppercase tracking-wider text-white/60">
        New password
      </label>
      <input
        type="password"
        autoComplete="new-password"
        className="input-base"
        value={next}
        onChange={(e) => setNext(e.target.value)}
      />
      <label className="mt-3 block text-xs uppercase tracking-wider text-white/60">
        Confirm new password
      </label>
      <input
        type="password"
        autoComplete="new-password"
        className="input-base"
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
      />

      {err && (
        <div className="mt-4 rounded border border-red-500/50 bg-red-500/10 p-3 text-sm text-red-200">
          {err}
        </div>
      )}
      {done && (
        <div className="mt-4 rounded border border-green-500/50 bg-green-500/10 p-3 text-sm text-green-200">
          Password changed. All your other sessions have been signed out.
        </div>
      )}

      <button
        type="submit"
        className="btn-primary mt-5"
        disabled={changeM.isPending || !current || !next || !confirm}
      >
        {changeM.isPending ? "Changing…" : "Change password"}
      </button>
    </form>
  );
}
