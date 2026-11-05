#!/usr/bin/env bash
# Build the clean KSSH-FOR-Friends tree and push it. Token comes from $GHT (never printed or stored).
#   export GHT=...   (fine-grained token: only KSSH-FOR-Friends, Contents: read and write)
#   curl -fsSL https://raw.githubusercontent.com/ykinfohome7/ssh-connector/claude/friends-export/scripts/push-friends-repo.sh | bash
set -euo pipefail
[ -n "${GHT:-}" ] || { echo "Няма токен - пусни първо командата с точките (export GHT)"; exit 1; }
W=$(mktemp -d /tmp/kssh-friends.XXXXXX); trap 'rm -rf "$W"' EXIT
cd "$W"
echo "== 1. Изтегляне"
git clone -q https://github.com/ykinfohome7/ssh-connector src
cd src
echo "== 2. Сглобяване"
git show origin/claude/friends-export:scripts/build-friends-repo.sh > "$W/build.sh"
sh "$W/build.sh" "$W/out" | tail -1
cd "$W/out"
git init -q -b main
ID=(-c user.name=ykinfohome7 -c user.email=ykinfohome7@users.noreply.github.com)
git "${ID[@]}" add -A
git "${ID[@]}" commit -q -m "KSSH for Friends: initial tree (1.4.1 + snippet library, no personal data)"
echo "== 3. Качване"
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=http.extraHeader
GIT_CONFIG_VALUE_0="Authorization: Basic $(printf 'ykinfohome7:%s' "$GHT" | base64 -w0)"
export GIT_CONFIG_VALUE_0
git push -q --force https://github.com/ykinfohome7/KSSH-FOR-Friends.git main
echo "== ГОТОВО: commit $(git rev-parse --short HEAD), файлове: $(git ls-files | wc -l)"
