#!/usr/bin/env bash
# ==============================================================================
# EcoSort Repository Verification Script
# Automated test script to validate repository setup, hygiene, sync, and branch protection.
# ==============================================================================
set -euo pipefail

# Visual formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

FAILED_CHECKS=0

pass() {
  echo -e "  [${GREEN}PASS${NC}] $1"
}

fail() {
  echo -e "  [${RED}FAIL${NC}] $1"
  FAILED_CHECKS=$((FAILED_CHECKS + 1))
}

info() {
  echo -e "${BLUE}==>${NC} $1"
}

warn() {
  echo -e "  [${YELLOW}WARN${NC}] $1"
}

echo "======================================================================"
echo "          EcoSort Monorepo Verification & Governance Check            "
echo "======================================================================"

# Determine repo root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

# ------------------------------------------------------------------------------
# Test 1: Verify Default Branch
# ------------------------------------------------------------------------------
info "Test 1: Verifying default branch configuration..."
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
if [[ "${CURRENT_BRANCH}" == "main" ]]; then
  pass "Current branch is 'main'."
else
  fail "Expected current branch to be 'main', found '${CURRENT_BRANCH}'."
fi

# ------------------------------------------------------------------------------
# Test 2: Verify Git Working Tree Hygiene
# ------------------------------------------------------------------------------
info "Test 2: Verifying Git working tree is clean..."
UNCOMMITTED_CHANGES="$(git status --porcelain)"
if [[ -z "${UNCOMMITTED_CHANGES}" ]]; then
  pass "Working directory is clean (zero unstaged/uncommitted files)."
else
  fail "Working directory contains uncommitted changes:\n${UNCOMMITTED_CHANGES}"
fi

# ------------------------------------------------------------------------------
# Test 3: Verify Ignored Internal Artifacts
# ------------------------------------------------------------------------------
info "Test 3: Verifying critical governance ignore rules..."
if git check-ignore -q GEMINI.md; then
  pass "GEMINI.md is properly ignored by .gitignore."
else
  fail "GEMINI.md is NOT ignored by .gitignore (critical leak risk)."
fi

if git check-ignore -q sprint1_pr_report.md; then
  pass "*_pr_report.md pattern is properly ignored."
else
  fail "PR report files (e.g., sprint1_pr_report.md) are NOT ignored."
fi

if git check-ignore -q PR_REPORT.md; then
  pass "PR_REPORT.md pattern is properly ignored."
else
  fail "PR_REPORT.md is NOT ignored."
fi

if git check-ignore -q ml/datasets/sample.jpg; then
  pass "Raw ML dataset images (ml/**/*.jpg) are properly ignored."
else
  fail "Raw ML dataset images are NOT ignored in ml/datasets/."
fi

# ------------------------------------------------------------------------------
# Test 4: Verify Remote Origin & Sync Status
# ------------------------------------------------------------------------------
info "Test 4: Verifying remote 'origin' synchronization..."
REMOTE_URL="$(git remote get-url origin 2>/dev/null || echo "")"
if [[ -n "${REMOTE_URL}" ]]; then
  pass "Remote origin exists: ${REMOTE_URL}"
else
  fail "No remote 'origin' configured."
fi

if [[ -n "${REMOTE_URL}" ]]; then
  timeout 15 git fetch origin main --quiet || true
  LOCAL_HASH="$(git rev-parse HEAD 2>/dev/null || echo "local_none")"
  REMOTE_HASH="$(git rev-parse origin/main 2>/dev/null || echo "remote_none")"

  if [[ "${LOCAL_HASH}" == "${REMOTE_HASH}" ]]; then
    pass "Local HEAD is in sync with origin/main (${LOCAL_HASH:0:7})."
  else
    fail "Local HEAD (${LOCAL_HASH:0:7}) does not match origin/main (${REMOTE_HASH:0:7})."
  fi
fi

# ------------------------------------------------------------------------------
# Test 5: Verify GitHub Branch Protection Rules on 'main'
# ------------------------------------------------------------------------------
info "Test 5: Verifying GitHub branch protection on 'main' via GitHub API..."

# Extract owner and repo from gh repo view
REPO_FULL="$(timeout 15 gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")"

if [[ -z "${REPO_FULL}" ]]; then
  fail "Unable to resolve repository name via gh CLI."
else
  pass "Resolved repository: ${REPO_FULL}"
  
  # Fetch branch protection JSON
  PROTECTION_JSON="$(timeout 15 gh api "repos/${REPO_FULL}/branches/main/protection" 2>/dev/null || echo "{}")"

  # 5.1 Required approving reviews >= 1
  REQ_REVIEWS="$(echo "${PROTECTION_JSON}" | jq -r 'if .required_pull_request_reviews != null then .required_pull_request_reviews.required_approving_review_count else 0 end' 2>/dev/null || echo 0)"
  if [[ "${REQ_REVIEWS}" -ge 1 ]]; then
    pass "Required approving review count is ${REQ_REVIEWS} (>= 1 required)."
  else
    fail "Required approving review count is ${REQ_REVIEWS} (expected >= 1)."
  fi

  # 5.2 Dismiss stale reviews
  DISMISS_STALE="$(echo "${PROTECTION_JSON}" | jq -r 'if .required_pull_request_reviews != null then (.required_pull_request_reviews.dismiss_stale_reviews | tostring) else "null" end' 2>/dev/null || echo "null")"
  if [[ "${DISMISS_STALE}" == "true" ]]; then
    pass "Dismiss stale reviews on new commit is ENABLED."
  else
    fail "Dismiss stale reviews on new commit is NOT enabled."
  fi

  # 5.3 Enforce for admins
  ENFORCE_ADMINS="$(echo "${PROTECTION_JSON}" | jq -r 'if .enforce_admins != null then (.enforce_admins.enabled | tostring) else "null" end' 2>/dev/null || echo "null")"
  if [[ "${ENFORCE_ADMINS}" == "true" ]]; then
    pass "Enforce admins is ENABLED."
  else
    fail "Enforce admins is NOT enabled."
  fi

  # 5.4 Block force pushes
  ALLOW_FORCE="$(echo "${PROTECTION_JSON}" | jq -r 'if .allow_force_pushes != null then (.allow_force_pushes.enabled | tostring) else "null" end' 2>/dev/null || echo "null")"
  if [[ "${ALLOW_FORCE}" == "false" ]]; then
    pass "Force pushes are BLOCKED (allow_force_pushes = false)."
  else
    fail "Force pushes are NOT blocked (allow_force_pushes = ${ALLOW_FORCE})."
  fi

  # 5.5 Block branch deletion
  ALLOW_DEL="$(echo "${PROTECTION_JSON}" | jq -r 'if .allow_deletions != null then (.allow_deletions.enabled | tostring) else "null" end' 2>/dev/null || echo "null")"
  if [[ "${ALLOW_DEL}" == "false" ]]; then
    pass "Branch deletion is BLOCKED (allow_deletions = false)."
  else
    fail "Branch deletion is NOT blocked (allow_deletions = ${ALLOW_DEL})."
  fi
fi

# ------------------------------------------------------------------------------
# Final Verification Summary
# ------------------------------------------------------------------------------
echo "======================================================================"
if [[ ${FAILED_CHECKS} -eq 0 ]]; then
  echo -e "${GREEN}ALL CHECKS PASSED SUCCESSFULLY (0 failures).${NC}"
  echo "Repository is verified, synchronized, and fully protected."
  exit 0
else
  echo -e "${RED}VERIFICATION FAILED with ${FAILED_CHECKS} error(s).${NC}"
  exit 1
fi
