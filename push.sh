#!/usr/bin/env bash
# Pushes to AyushHarshit/daily-swipe using the PAT in the local .token file.
#
# Security: the token is supplied to git via GIT_ASKPASS (stdin of the password
# prompt), NOT embedded in the remote URL or argv. This means the token never
# appears in process listings, git config, shell history, or git error output.
# .token is gitignored and must never be committed.
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -s .token ]]; then
  echo "ERROR: .token is empty. Paste your GitHub personal access token into it first." >&2
  exit 1
fi

BRANCH="${1:-$(git symbolic-ref --short HEAD)}"

# Temporary askpass helper that prints the PAT for git's password prompt.
ASKPASS="$(mktemp)"
trap 'rm -f "$ASKPASS"' EXIT
cat > "$ASKPASS" <<'EOF'
#!/usr/bin/env bash
tr -d ' \t\r\n' < "$GIT_TOKEN_FILE"
EOF
chmod +x "$ASKPASS"

# remote.origin.url is https://AyushHarshit@github.com/... (username only, no token),
# which both supplies the username and dodges the global insteadOf SSH rewrite.
GIT_TOKEN_FILE="$PWD/.token" \
GIT_ASKPASS="$ASKPASS" \
GIT_TERMINAL_PROMPT=0 \
git push origin "$BRANCH"
