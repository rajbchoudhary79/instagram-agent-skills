#!/usr/bin/env sh
# Install the creator-content-kit skills.
#
#   scripts/install.sh                 -> ~/.claude/skills/            (all projects, Claude Code)
#   scripts/install.sh --project DIR   -> DIR/.claude/skills/          (one project)
#   scripts/install.sh --dest DIR      -> DIR/                         (any agent that reads SKILL.md folders)
#   scripts/install.sh --link          symlink instead of copy (edits in this repo apply immediately)
#
# All skills are installed side by side so they can find creator-core.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
DEST="${HOME}/.claude/skills"
MODE=copy

while [ $# -gt 0 ]; do
  case "$1" in
    --project) DEST="$2/.claude/skills"; shift 2 ;;
    --dest) DEST="$2"; shift 2 ;;
    --link) MODE=link; shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

command -v python3 >/dev/null 2>&1 || echo "warning: python3 not found; the skills' tools need Python 3.8+" >&2
mkdir -p "$DEST"
for dir in "$ROOT"/skills/*/; do
  dir=${dir%/}
  [ -f "$dir/SKILL.md" ] || continue
  name=$(basename "$dir")
  target="$DEST/$name"
  if [ -e "$target" ] || [ -L "$target" ]; then
    rm -rf "$target"
  fi
  if [ "$MODE" = link ]; then
    ln -s "$dir" "$target"
  else
    cp -R "$dir" "$target"
    find "$target" -name '__pycache__' -type d -prune -exec rm -rf {} +
  fi
  echo "installed $name -> $target"
done

echo
echo "Next: create your creator profile"
echo "  python3 \"$DEST/creator-core/scripts/profile.py\" init"
echo "or ask your agent: \"set up my Instagram creator profile\""
