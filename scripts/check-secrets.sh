#!/bin/bash
# Script to check repository for exposed secrets
# Usage: ./scripts/check-secrets.sh

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔍 Scanning repository for secrets..."

SECRET_PATTERNS=(
    "AIzaSy[A-Za-z0-9_-]{35}"
    "gsk_[A-Za-z0-9_-]{50}"
    "sk-[A-Za-z0-9]{32,}"
    "xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,32}"
    "AKIA[0-9A-Z]{16}"
    "-----BEGIN.*PRIVATE KEY-----"
    "password\s*=\s*['\"][^'\"]+['\"]"
    "api[_-]?key\s*=\s*['\"][^'\"]+['\"]"
    "secret[_-]?key\s*=\s*['\"][^'\"]+['\"]"
)

FOUND_SECRETS=0

# Check all files (excluding .git, node_modules, etc.)
for file in $(git ls-files); do
    # Skip binary files
    if file "$file" | grep -q "binary"; then
        continue
    fi
    
    # Skip .env.example files (they should have placeholders)
    if [[ "$file" == *.env.example ]]; then
        continue
    fi
    
    for pattern in "${SECRET_PATTERNS[@]}"; do
        if grep -qiE "$pattern" "$file" 2>/dev/null; then
            echo -e "${RED}⚠️  Potential secret found in: $file${NC}"
            grep -iE "$pattern" "$file" | head -1 | sed 's/^/   /'
            FOUND_SECRETS=1
        fi
    done
done

if [ $FOUND_SECRETS -eq 0 ]; then
    echo -e "${GREEN}✓ No secrets found in tracked files${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}🚨 Secrets detected! Please review and remove them.${NC}"
    exit 1
fi




