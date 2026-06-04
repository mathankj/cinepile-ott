#!/usr/bin/env bash
# Capture screenshots for the 4 remaining viewports.
# Reuses an already-built browse binary; assumes frontend on :5173 and backend on :8000.
set -uo pipefail

B="$HOME/.claude/skills/gstack/browse/dist/browse"
OUT="C:/Users/matha/Temp/anjaneya-ott/docs/qa/screenshots"
FE="http://localhost:5173"

VIEWPORTS=("414x896" "768x1024" "1280x800" "1920x1080")

# Stable shot helper: set viewport AFTER goto so it doesn't reset, then wait + sleep
shot() {
  local vp="$1" name="$2" url="$3"
  mkdir -p "$OUT/$vp"
  "$B" goto "$url" >/dev/null 2>&1
  "$B" viewport "$vp" >/dev/null 2>&1
  "$B" wait --networkidle >/dev/null 2>&1 || true
  sleep 1
  "$B" screenshot "$OUT/$vp/$name.png" >/dev/null 2>&1
  echo "  $vp $name"
}

# Login helper: clear storage, navigate, fill, submit, pick profile
login_user() {
  local email="$1" password="$2"
  "$B" goto "$FE/login" >/dev/null 2>&1
  "$B" eval "localStorage.clear(); sessionStorage.clear();" >/dev/null 2>&1
  "$B" goto "$FE/login" >/dev/null 2>&1
  "$B" wait --networkidle >/dev/null 2>&1
  sleep 1
  local snap
  snap=$("$B" snapshot 2>/dev/null)
  # Find email + password refs (textbox elements)
  local email_ref pass_ref login_btn
  email_ref=$(echo "$snap" | grep -i 'textbox.*email' | head -1 | grep -oE '@e[0-9]+' | head -1)
  pass_ref=$(echo "$snap" | grep -i 'textbox.*password' | head -1 | grep -oE '@e[0-9]+' | head -1)
  login_btn=$(echo "$snap" | grep -iE 'button.*(log in|login|sign in)' | head -1 | grep -oE '@e[0-9]+' | head -1)
  # Fallbacks
  [ -z "$email_ref" ] && email_ref=$(echo "$snap" | grep 'textbox' | head -1 | grep -oE '@e[0-9]+')
  [ -z "$pass_ref" ] && pass_ref=$(echo "$snap" | grep 'textbox' | head -2 | tail -1 | grep -oE '@e[0-9]+')
  [ -z "$login_btn" ] && login_btn=$(echo "$snap" | grep 'button' | head -1 | grep -oE '@e[0-9]+')
  "$B" fill "$email_ref" "$email" >/dev/null 2>&1
  "$B" fill "$pass_ref" "$password" >/dev/null 2>&1
  "$B" click "$login_btn" >/dev/null 2>&1
  "$B" wait --networkidle >/dev/null 2>&1
  sleep 2
  # Pick first profile
  snap=$("$B" snapshot 2>/dev/null)
  local prof_ref
  prof_ref=$(echo "$snap" | grep -iE 'button.*profile|generic.*profile' | head -1 | grep -oE '@e[0-9]+' | head -1)
  if [ -z "$prof_ref" ]; then
    # fallback: any button on /profiles page
    prof_ref=$(echo "$snap" | grep -E 'button' | head -1 | grep -oE '@e[0-9]+' | head -1)
  fi
  [ -n "$prof_ref" ] && "$B" click "$prof_ref" >/dev/null 2>&1
  "$B" wait --networkidle >/dev/null 2>&1
  sleep 2
}

for VP in "${VIEWPORTS[@]}"; do
  echo "Viewport set to $VP"

  # --- ANON routes ---
  # Clear storage to ensure logged-out state
  "$B" goto "$FE/" >/dev/null 2>&1
  "$B" eval "localStorage.clear(); sessionStorage.clear();" >/dev/null 2>&1

  shot "$VP" "home-anon"     "$FE/"
  shot "$VP" "login"         "$FE/login"
  shot "$VP" "signup"        "$FE/signup"
  shot "$VP" "browse"        "$FE/browse"
  shot "$VP" "browse-filter" "$FE/browse?type=movie&genre=drama"
  shot "$VP" "search"        "$FE/search?q=hero"
  shot "$VP" "title-1"       "$FE/title/1"
  shot "$VP" "title-4"       "$FE/title/4"
  shot "$VP" "season-4-1"    "$FE/title/4/season/1"
  shot "$VP" "watch-1"       "$FE/watch/1"
  shot "$VP" "subscribe"     "$FE/subscribe"
  shot "$VP" "me-list"       "$FE/me/list"
  shot "$VP" "me-history"    "$FE/me/history"
  shot "$VP" "profiles"      "$FE/profiles"

  # --- USER AUTH routes ---
  login_user "user@anjaneya.app" "user1234"
  shot "$VP" "profiles-auth" "$FE/profiles"
  shot "$VP" "home-auth"     "$FE/"
  shot "$VP" "title-1-auth"  "$FE/title/1"
  shot "$VP" "title-4-auth"  "$FE/title/4"
  shot "$VP" "season-4-1-auth" "$FE/title/4/season/1"
  shot "$VP" "watch-1-auth"  "$FE/watch/1"

  # --- ADMIN routes ---
  "$B" goto "$FE/" >/dev/null 2>&1
  "$B" eval "localStorage.clear(); sessionStorage.clear();" >/dev/null 2>&1
  login_user "admin@anjaneya.app" "admin1234"
  shot "$VP" "admin"            "$FE/admin"
  shot "$VP" "admin-titles"     "$FE/admin/titles"
  shot "$VP" "admin-titles-new" "$FE/admin/titles/new"
  shot "$VP" "admin-users"      "$FE/admin/users"
  shot "$VP" "admin-audit"      "$FE/admin/audit"

  # Clear for next viewport
  "$B" goto "$FE/" >/dev/null 2>&1
  "$B" eval "localStorage.clear(); sessionStorage.clear();" >/dev/null 2>&1
done

echo "DONE"
