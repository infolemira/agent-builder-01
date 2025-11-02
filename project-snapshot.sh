#!/usr/bin/env bash
set -e

OUT="project-snapshot-$(date +%Y%m%d-%H%M%S).txt"

echo "=== AGENT BUILDER 01 – SNAPSHOT ===" > "$OUT"
echo "Date: $(date -Is)" >> "$OUT"
echo "" >> "$OUT"

if [ -d "backend" ]; then
  echo "## BACKEND" >> "$OUT"
  (cd backend && \
    echo "- git branch:" >> "../$OUT" && git rev-parse --abbrev-ref HEAD >> "../$OUT" || true
  )
  echo "- tree:" >> "$OUT"
  (cd backend && { command -v tree >/dev/null && tree -a -I node_modules || find . -maxdepth 3 -print; }) >> "$OUT" || true
  echo "- package.json:" >> "$OUT"
  (cd backend && cat package.json 2>/dev/null || true) >> "$OUT"
  echo "- .env.example (samo ključevi):" >> "$OUT"
  (cd backend && sed 's/=.*/=***REDACTED*** /' .env.example 2>/dev/null || true) >> "$OUT"
  echo "" >> "$OUT"
fi

if [ -d "frontend" ]; then
  echo "## FRONTEND" >> "$OUT"
  (cd frontend && \
    echo "- git branch:" >> "../$OUT" && git rev-parse --abbrev-ref HEAD >> "../$OUT" || true
  )
  echo "- tree:" >> "$OUT"
  (cd frontend && { command -v tree >/dev/null && tree -a -I node_modules || find . -maxdepth 3 -print; }) >> "$OUT" || true
  echo "- package.json:" >> "$OUT"
  (cd frontend && cat package.json 2>/dev/null || true) >> "$OUT"
  echo "- .env.local.example (samo ključevi):" >> "$OUT"
  (cd frontend && sed 's/=.*/=***REDACTED*** /' .env.local.example 2>/dev/null || true) >> "$OUT"
  echo "" >> "$OUT"
fi

echo "## ROOT TREE (do 2 nivoa):" >> "$OUT"
{ command -v tree >/dev/null && tree -a -I node_modules -L 2 || find . -maxdepth 2 -print; } >> "$OUT" || true
echo "" >> "$OUT"

echo "## MANUAL NOTES (popuni ručno ispod, samo tekst):" >> "$OUT"
cat >> "$OUT" <<'EON'
RENDER_BACKEND_URL=***
RENDER_ENV_SET=YES/NO
SUPABASE_PROJECT_URL=***
FEATURES_DONE= (npr. auth verify, ai/query radi…)
FEATURES_TODO= (npr. streaming, historija, rate limit…)
EON

echo ""
echo "✅ Kreirano: $OUT"
echo "➡️  Otvori taj .txt fajl, kopiraj sav sadržaj i zalijepi ovdje u chat (ili preuzmi i uploadaj)."
