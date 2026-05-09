#!/bin/bash
# sync-upstream-manual.sh
#
# Manually sync freetz-evo with upstream Freetz-NG/freetz-ng.
# Uses the same merge strategy as the GitHub Actions workflow.
#
# Usage:
#   ./sync-upstream-manual.sh              # Interactive merge
#   ./sync-upstream-manual.sh --dry-run    # Show what would happen
#   ./sync-upstream-manual.sh --diff       # Show diff with upstream
#   ./sync-upstream-manual.sh --log        # Show upstream commits not yet merged
#
set -euo pipefail

UPSTREAM_BRANCH="master"
LOCAL_BRANCH="master"
MIRROR_BRANCH="upstream-mirror"
LLM_MERGE_BUNDLE_ROOT=".git/sync-upstream-llm"

# ── Parse arguments ───────────────────────────────────────────
DRY_RUN=false
DIFF_ONLY=false
LOG_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --dry-run)  DRY_RUN=true ;;
        --diff)     DIFF_ONLY=true ;;
        --log)      LOG_ONLY=true ;;
        --help|-h)
            echo "Usage: $0 [--dry-run|--diff|--log]"
            echo ""
            echo "  --dry-run  Attempt merge but do not push (shows conflicts if any)"
            echo "  --diff     Show file diff between master and upstream"
            echo "  --log      Show upstream commits not yet merged into master"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Run: $0 --help"
            exit 1
            ;;
    esac
done

finalize_sync_branch() {
    if [ "$DRY_RUN" = true ]; then
        echo "🔍 DRY RUN: merge is clean. Reverting..."
        git checkout "$LOCAL_BRANCH"
        git branch -D "$SYNC_BRANCH"
        echo "No changes were made."
        exit 0
    fi

    echo "▸ Updating master..."
    git checkout "$LOCAL_BRANCH"
    git merge --ff-only "$SYNC_BRANCH"
    git branch -d "$SYNC_BRANCH"

    echo ""
    read -rp "Push to origin? [Y/n] " push_confirm
    if [[ "${push_confirm:-Y}" == [yY] ]]; then
        echo "▸ Pushing master..."
        git push --force-with-lease origin "$LOCAL_BRANCH"

        echo "▸ Pushing upstream-mirror..."
        git push origin "$MIRROR_BRANCH" --force-with-lease

        echo ""
        echo "✅ Sync complete! Master is up-to-date with upstream."
    else
        echo "Not pushed. You can push later with:"
        echo "  git push --force-with-lease origin $LOCAL_BRANCH"
        echo "  git push origin $MIRROR_BRANCH --force-with-lease"
    fi

    exit 0
}

is_llm_merge_candidate() {
    case "$1" in
        *.c|*.cc|*.cpp|*.css|*.h|*.html|*.in|*.js|*.json|*.m4|*.md|*.mk|*.php|*.pl|*.py|*.sh|*.txt|*.xml|*.yml|*.yaml)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

write_llm_merge_bundle() {
    local file="$1"
    local bundle_name="${file//\//__}"
    local bundle_dir="$LLM_MERGE_BUNDLE_ROOT/$bundle_name"

    mkdir -p "$bundle_dir"
    git show ":1:$file" > "$bundle_dir/base" 2>/dev/null || true
    git show ":2:$file" > "$bundle_dir/local" 2>/dev/null || true
    git show ":3:$file" > "$bundle_dir/remote" 2>/dev/null || true
    cp "$file" "$bundle_dir/conflicted" 2>/dev/null || true

    cat > "$bundle_dir/prompt.md" <<EOF
# Merge request for $file

Goal: produce a single merged file that preserves both the local Freetz-EVO
changes and the incoming remote changes without duplicating behavior.

Available inputs:
- base: common ancestor
- local: current Freetz-EVO branch
- remote: incoming branch being merged
- conflicted: Git's current conflict-marked file, when available

Merge rules:
- Keep upstream bug fixes unless they directly conflict with an intentional
  Freetz-EVO customization.
- Keep Freetz-EVO-specific behavior unless upstream already provides an
  equivalent implementation.
- Remove duplicate comments, duplicate branches, and duplicate list entries
  after merging both sides.
- Preserve shell syntax, quoting style, and the surrounding file structure.
EOF
}

prepare_llm_merge_bundles() {
    local file
    local prepared=0

    rm -rf "$LLM_MERGE_BUNDLE_ROOT"

    while IFS= read -r file; do
        [ -n "$file" ] || continue
        if is_llm_merge_candidate "$file"; then
            write_llm_merge_bundle "$file"
            prepared=$((prepared + 1))
        fi
    done < <(git diff --name-only --diff-filter=U)

    if [ "$prepared" -gt 0 ]; then
        echo "🧠 Prepared $prepared LLM merge bundle(s) under $LLM_MERGE_BUNDLE_ROOT"
        echo "   Each bundle contains base/local/remote/conflicted snapshots plus a prompt.md."
        echo ""
    fi
}

# ── Preflight ─────────────────────────────────────────────────
echo "▸ Fetching upstream..."
git remote add upstream "https://github.com/Freetz-NG/freetz-ng.git" 2>/dev/null || true
git fetch upstream "$UPSTREAM_BRANCH" --no-tags

# Reuse previously validated manual conflict resolutions.
# This is the safest form of automation: Git only reapplies exact/similar
# conflict preimages and still leaves unresolved cases for manual review.
git config --local rerere.enabled true
git config --local rerere.autoupdate true

# Update upstream-mirror
git branch -f "$MIRROR_BRANCH" "upstream/$UPSTREAM_BRANCH"

MERGE_BASE=$(git merge-base "$LOCAL_BRANCH" "upstream/$UPSTREAM_BRANCH")
UPSTREAM_HEAD=$(git rev-parse "upstream/$UPSTREAM_BRANCH")
NEW_COMMITS=$(git rev-list --count "$MERGE_BASE".."upstream/$UPSTREAM_BRANCH")

echo "  Upstream HEAD: $(git rev-parse --short upstream/$UPSTREAM_BRANCH)"
echo "  Merge base:    $(git rev-parse --short $MERGE_BASE)"
echo "  New commits:   $NEW_COMMITS"
echo ""

# ── Diff mode ─────────────────────────────────────────────────
if [ "$DIFF_ONLY" = true ]; then
    echo "▸ Files changed in upstream since last sync:"
    git diff --stat "$LOCAL_BRANCH"..upstream/"$UPSTREAM_BRANCH"
    echo ""
    echo "For full diff: git diff $LOCAL_BRANCH..upstream/$UPSTREAM_BRANCH"
    exit 0
fi

# ── Log mode ──────────────────────────────────────────────────
if [ "$LOG_ONLY" = true ]; then
    echo "▸ Upstream commits not yet merged:"
    git log --oneline --no-merges "$MERGE_BASE"..upstream/"$UPSTREAM_BRANCH" | head -50
    TOTAL=$(git rev-list --count --no-merges "$MERGE_BASE"..upstream/"$UPSTREAM_BRANCH")
    if [ "$TOTAL" -gt 50 ]; then
        echo "  ... and $((TOTAL - 50)) more commits"
    fi
    exit 0
fi

# ── Check if sync needed ─────────────────────────────────────
if [ "$MERGE_BASE" = "$UPSTREAM_HEAD" ]; then
    echo "✅ Already up-to-date with upstream. Nothing to do."
    exit 0
fi

# ── Ensure clean working tree ─────────────────────────────────
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "ERROR: Working tree is dirty. Commit or stash changes first."
    echo ""
    git status --short
    exit 1
fi

# ── Ensure we're on master ────────────────────────────────────
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "$LOCAL_BRANCH" ]; then
    echo "▸ Switching to $LOCAL_BRANCH..."
    git checkout "$LOCAL_BRANCH"
fi

# ── Create staging branch ────────────────────────────────────
DATE_TAG=$(date +%Y%m%d-%H%M%S)
SYNC_BRANCH="sync/upstream-${DATE_TAG}"

echo "▸ Creating staging branch: $SYNC_BRANCH"
git checkout -b "$SYNC_BRANCH"

# ── Attempt merge ─────────────────────────────────────────────
echo "▸ Merging upstream ($NEW_COMMITS commits)..."
echo ""

if git merge "upstream/$UPSTREAM_BRANCH" \
     --no-edit \
     -m "Merge upstream freetz-ng ($(date +%Y-%m-%d))

Synced with Freetz-NG/freetz-ng@$(git rev-parse --short upstream/$UPSTREAM_BRANCH)
New upstream commits: $NEW_COMMITS"; then

    echo ""
    echo "✅ Merge succeeded without conflicts!"
    echo ""
    finalize_sync_branch

else
    echo ""
    echo "❌ Merge conflicts detected!"
    echo "ℹ️  rerere enabled: known conflict patterns may auto-resolve after first manual fix."
    echo ""

    # ── Auto-resolve modify/delete and known auto-generated conflicts ─────────
    # git status porcelain codes for unmerged entries:
    #   UD = deleted by them (upstream deleted, we modified) → keep ours
    #   DU = deleted by us (we deleted, upstream modified)   → keep our deletion
    #   UU = both modified                                   → special handling
    #
    # AUTO_OURS_FILES: files auto-generated by EVO's own workflows that will
    # conflict with upstream's equivalent automation on every sync.  EVO's
    # version is always authoritative for these files.
    #
    # Example: docs/juis/README.md is updated by both EVO's "juis: automatic
    # update" workflow (which uses obfuscated download.example.com URLs) and
    # upstream's "docs: automatic update" bot (which uses download.avm.de).
    # Both bots update the same overlapping firmware-list section, producing
    # a UU conflict on every sync where both bots have run.  Adding the file
    # here tells the resolver to always keep EVO's version without prompting.
    AUTO_OURS_FILES=(
        "README.md"                             # Fully rewritten for Freetz-EVO branding
        "docs/juis/README.md"
        "docs/libs/README.md"
        # upstream GH-Pages deploy workflow – not used in our fork, always keep deleted
        ".github/workflows/github_ghpages.yml"
    )
    AUTO_RESOLVED=()
    while IFS= read -r line; do
        xy="${line:0:2}"
        file="${line:3}"
        if [ "$xy" = "UD" ]; then
            # Upstream deleted, we modified → keep our version
            git add -- "$file"
            AUTO_RESOLVED+=("keep-ours: $file")
        elif [ "$xy" = "DU" ]; then
            # We deleted, upstream modified → keep our deletion
            git rm --quiet -- "$file"
            AUTO_RESOLVED+=("keep-deletion: $file")
        elif [ "$xy" = "UU" ] || [ "$xy" = "AA" ]; then
            # Both modified/added → keep ours if it's a known EVO-owned file
            for pattern in "${AUTO_OURS_FILES[@]}"; do
                if [[ "$file" == $pattern ]]; then
                    git checkout --ours -- "$file" 2>/dev/null || true
                    if [ -f "$file" ]; then
                        git add -- "$file"
                        AUTO_RESOLVED+=("take-ours (auto-generated): $file")
                    else
                        # Our version is a deletion → keep the file removed
                        git rm --quiet -- "$file" 2>/dev/null || true
                        AUTO_RESOLVED+=("keep-deleted: $file")
                    fi
                    break
                fi
            done
        fi
    done < <(git status --porcelain)

    if [ ${#AUTO_RESOLVED[@]} -gt 0 ]; then
        echo "⚙️  Auto-resolved conflicts:"
        for r in "${AUTO_RESOLVED[@]}"; do
            echo "   ✔ $r"
        done
        echo ""
    fi

    # Check if all conflicts are now resolved
    REMAINING=$(git diff --name-only --diff-filter=U)
    if [ -z "$REMAINING" ]; then
        echo "✅ All conflicts auto-resolved!"
        GIT_EDITOR=true git merge --continue
        echo ""
        finalize_sync_branch
    fi

    prepare_llm_merge_bundles

    echo "Remaining conflicts (require manual resolution):"
    echo "$REMAINING"
    echo ""

    if [ -d "$LLM_MERGE_BUNDLE_ROOT" ]; then
        echo "LLM-assisted conflict review:"
        echo "  - Open the relevant prompt.md under $LLM_MERGE_BUNDLE_ROOT"
        echo "  - Merge base/local/remote so both upstream and Freetz-EVO contributions survive"
        echo "  - Apply the merged result, then git add <file> and git merge --continue"
        echo ""
    fi

    if [ "$DRY_RUN" = true ]; then
        echo "🔍 DRY RUN: conflicts found. Aborting merge..."
        git merge --abort
        git checkout "$LOCAL_BRANCH"
        git branch -D "$SYNC_BRANCH"
        echo "No changes were made."
        exit 1
    fi

    echo "You are now on branch '$SYNC_BRANCH' with unresolved conflicts."
    echo ""
    echo "Options:"
    echo "  1. Resolve conflicts now:"
    echo "     - Edit the conflicted files"
    echo "     - git add <resolved-files>"
    echo "     - git merge --continue"
    echo "     - git checkout master && git merge --ff-only $SYNC_BRANCH"
    echo "     - git push --force-with-lease origin master"
    echo ""
    echo "  2. Abort and return to master:"
    echo "     - git merge --abort"
    echo "     - git checkout master"
    echo "     - git branch -D $SYNC_BRANCH"
    echo ""

    read -rp "Abort merge and return to master? [y/N] " abort_confirm
    if [[ "$abort_confirm" == [yY] ]]; then
        git merge --abort
        git checkout "$LOCAL_BRANCH"
        git branch -D "$SYNC_BRANCH"
        echo "Merge aborted. Master is unchanged."
    else
        echo ""
        echo "Resolve conflicts, then run:"
        echo "  git add . && git merge --continue"
        echo "  git checkout master && git merge --ff-only $SYNC_BRANCH"
        echo "  git push --force-with-lease origin master"
    fi
    exit 1
fi
