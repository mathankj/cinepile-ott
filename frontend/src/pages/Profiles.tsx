/**
 * Profile picker — "Who's watching?" Netflix-style screen.
 *
 * Two modes: "select" (default — pick a profile and go) and "manage"
 * (allow renaming + deleting + adding). Toggle in the bottom CTA.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { me } from "../api";
import { apiErrorMessage } from "../api/client";
import { useProfileStore } from "../stores/profile";
import { AVATAR_OPTIONS } from "../lib/avatars";
import { Avatar } from "../components/Avatar";
import type { Profile } from "../api/types";

export default function ProfilesPage() {
  const nav = useNavigate();
  const qc = useQueryClient();
  const setActive = useProfileStore((s) => s.setActive);
  const [editing, setEditing] = useState(false);
  const [adding, setAdding] = useState(false);
  const [renameTarget, setRenameTarget] = useState<Profile | null>(null);

  const profilesQ = useQuery({ queryKey: ["profiles"], queryFn: me.listProfiles });

  function selectProfile(p: Profile) {
    setActive(p);
    nav("/", { replace: true });
  }

  return (
    <div className="grid min-h-screen place-items-center bg-black px-4 py-12">
      <div className="w-full max-w-4xl">
        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-12 text-center text-[clamp(2rem,5vw,3.5rem)] font-light text-white"
        >
          {editing ? "Manage Profiles" : "Who's watching?"}
        </motion.h1>

        {profilesQ.isLoading && (
          <div className="text-center text-white/60">Loading profiles…</div>
        )}

        {profilesQ.data && (
          <motion.div
            initial="hidden"
            animate="show"
            variants={{
              hidden: {},
              show: { transition: { staggerChildren: 0.06, delayChildren: 0.1 } },
            }}
            className="flex flex-wrap justify-center gap-6 md:gap-10"
          >
            {profilesQ.data.items.map((p) => (
              <ProfileTile
                key={p.id}
                profile={p}
                editing={editing}
                onClick={() => (editing ? setRenameTarget(p) : selectProfile(p))}
              />
            ))}
            {profilesQ.data.items.length < profilesQ.data.max_profiles && (
              <AddTile onClick={() => setAdding(true)} />
            )}
          </motion.div>
        )}

        <div className="mt-14 flex justify-center">
          <button
            type="button"
            onClick={() => setEditing((v) => !v)}
            className="rounded border border-white/40 px-6 py-2 text-sm uppercase tracking-wider text-white/70 transition-colors hover:border-white hover:text-white"
          >
            {editing ? "Done" : "Manage Profiles"}
          </button>
        </div>
      </div>

      {adding && (
        <ProfileFormModal
          mode="create"
          onClose={() => setAdding(false)}
          onSaved={() => {
            qc.invalidateQueries({ queryKey: ["profiles"] });
            setAdding(false);
          }}
        />
      )}
      {renameTarget && (
        <ProfileFormModal
          mode="edit"
          profile={renameTarget}
          onClose={() => setRenameTarget(null)}
          onSaved={() => {
            qc.invalidateQueries({ queryKey: ["profiles"] });
            setRenameTarget(null);
          }}
        />
      )}
    </div>
  );
}

function ProfileTile({
  profile,
  editing,
  onClick,
}: {
  profile: Profile;
  editing: boolean;
  onClick: () => void;
}) {
  return (
    <motion.button
      variants={{ hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0 } }}
      whileHover={{ scale: 1.04 }}
      transition={{ duration: 0.2 }}
      type="button"
      onClick={onClick}
      className="group flex flex-col items-center"
    >
      <div className="relative rounded-md ring-2 ring-transparent group-hover:ring-white">
        {/* lg = 120px, xl = 160px — keep the picker tile size we already had */}
        <div className="block md:hidden">
          <Avatar value={profile.avatar} size="lg" alt={profile.name} />
        </div>
        <div className="hidden md:block">
          <Avatar value={profile.avatar} size="xl" alt={profile.name} />
        </div>
        {editing && (
          <div className="absolute inset-0 grid place-items-center rounded-md bg-black/60">
            <Pencil size={28} className="text-white" />
          </div>
        )}
      </div>
      <div className="mt-3 text-[15px] text-white/80 group-hover:text-white">
        {profile.name}
        {profile.kind === "kid" && (
          <span className="ml-2 rounded bg-white/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wider">
            Kid
          </span>
        )}
      </div>
    </motion.button>
  );
}

function AddTile({ onClick }: { onClick: () => void }) {
  return (
    <motion.button
      variants={{ hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0 } }}
      whileHover={{ scale: 1.04 }}
      transition={{ duration: 0.2 }}
      type="button"
      onClick={onClick}
      className="group flex flex-col items-center"
    >
      <div className="grid h-[120px] w-[120px] md:h-[160px] md:w-[160px] place-items-center rounded-md border-2 border-dashed border-white/30 text-white/40 group-hover:border-white group-hover:text-white">
        <Plus size={48} />
      </div>
      <div className="mt-3 text-[15px] text-white/60 group-hover:text-white">Add Profile</div>
    </motion.button>
  );
}

function ProfileFormModal({
  mode,
  profile,
  onClose,
  onSaved,
}: {
  mode: "create" | "edit";
  profile?: Profile;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(profile?.name ?? "");
  const [avatar, setAvatar] = useState(profile?.avatar ?? "default");
  const [kind, setKind] = useState<"adult" | "kid">(profile?.kind ?? "adult");
  const [err, setErr] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: async () => {
      if (mode === "create") {
        return me.createProfile({ name: name.trim(), avatar, kind });
      }
      return me.updateProfile(profile!.id, { name: name.trim(), avatar, kind });
    },
    onSuccess: onSaved,
    onError: (e) => setErr(apiErrorMessage(e, "Couldn't save profile.")),
  });

  const remove = useMutation({
    mutationFn: () => me.deleteProfile(profile!.id),
    onSuccess: onSaved,
    onError: (e) => setErr(apiErrorMessage(e, "Couldn't delete profile.")),
  });

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/80 px-4 animate-fade-in" role="dialog">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.18 }}
        className="w-full max-w-md rounded-md bg-[var(--color-bg-elevated)] p-8"
      >
        <h2 className="mb-6 text-2xl font-bold text-white">
          {mode === "create" ? "Add Profile" : "Edit Profile"}
        </h2>

        <label className="mb-2 block text-xs uppercase tracking-wider text-white/60">
          Name
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={32}
          autoFocus
          className="input-base mb-5"
          placeholder="Profile name"
        />

        <label className="mb-2 block text-xs uppercase tracking-wider text-white/60">
          Avatar
        </label>
        <div className="mb-5 grid grid-cols-5 gap-2.5">
          {AVATAR_OPTIONS.map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => setAvatar(a.id)}
              aria-label={`Choose avatar: ${a.label}`}
              className={`rounded-lg transition ${
                avatar === a.id ? "ring-2 ring-white ring-offset-2 ring-offset-[var(--color-bg-elevated)]" : "ring-2 ring-transparent hover:ring-white/40"
              }`}
            >
              <Avatar value={a.id} size="md" alt={a.label} />
            </button>
          ))}
        </div>

        <label className="mb-2 flex items-center gap-2 text-sm text-white">
          <input
            type="checkbox"
            checked={kind === "kid"}
            onChange={(e) => setKind(e.target.checked ? "kid" : "adult")}
            className="h-4 w-4 accent-white"
          />
          Kids profile (filters content to U-rated)
        </label>

        {err && (
          <div role="alert" className="mt-4 rounded border border-red-500/50 bg-red-500/10 p-3 text-sm text-red-200">
            {err}
          </div>
        )}

        <div className="mt-8 flex items-center justify-between gap-3">
          <div>
            {mode === "edit" && profile && !profile.is_primary && (
              <button
                type="button"
                onClick={() => remove.mutate()}
                disabled={remove.isPending}
                className="inline-flex items-center gap-2 rounded border border-red-500/40 px-4 py-2 text-sm text-red-300 hover:bg-red-500/10"
              >
                <Trash2 size={14} /> Delete
              </button>
            )}
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-white/30 px-5 py-2 text-sm text-white/80 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => save.mutate()}
              disabled={save.isPending || !name.trim()}
              className="rounded bg-white px-5 py-2 text-sm font-semibold text-black hover:bg-white/85 disabled:opacity-50"
            >
              {save.isPending ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
