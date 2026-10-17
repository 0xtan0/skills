#!/usr/bin/env bash
# Link skills from this repo into ~/.claude/skills.
# Usage: scripts/install.sh [skill-name ...]   (no names: every skill)
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
dest="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$dest"

if [ "$#" -eq 0 ]; then
  set -- $(ls "$repo/skills")
fi

for name in "$@"; do
  src="$repo/skills/$name"
  if [ ! -f "$src/SKILL.md" ]; then
    echo "skip $name: no $src/SKILL.md" >&2
    continue
  fi
  target="$dest/$name"
  if [ -L "$target" ]; then
    ln -sfn "$src" "$target"
    echo "relinked $name"
  elif [ -e "$target" ]; then
    echo "skip $name: $target exists and is not a link; move it away first" >&2
  else
    ln -s "$src" "$target"
    echo "linked $name"
  fi
done
