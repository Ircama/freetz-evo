# Syncing with upstream Freetz-NG

Freetz-EVO stays in sync with [Freetz-NG/freetz-ng](https://github.com/Freetz-NG/freetz-ng). New upstream commits (firmware support, toolchain updates, bug fixes) are merged regularly so that Freetz-EVO always builds on the latest Freetz-NG foundation.

Two mechanisms handle this sync:

| Mechanism | When it runs |
|---|---|
| **GitHub Actions** (`.github/workflows/sync-upstream.yml`) | Automatically on a schedule and on every push |
| **`tools/sync-upstream-manual.sh`** | On demand, from a developer's machine |

---

## tools/sync-upstream-manual.sh

### Prerequisites

- Run from the root of the `freetz-evo` checkout.
- The working tree must be **clean** (no uncommitted changes, no untracked files that would conflict). Commit or stash everything first.
- Internet access to `https://github.com/Freetz-NG/freetz-ng.git`.

### Usage

```bash
tools/sync-upstream-manual.sh [--dry-run | --diff | --log | --help]
```

| Option | Description |
|---|---|
| *(no option)* | Interactive merge: fetches upstream, merges into a staging branch, fast-forwards `master`, and asks whether to push. |
| `--log` | Lists upstream commits that have not yet been merged into `master`. No changes are made. |
| `--diff` | Shows a `git diff --stat` of all files changed between `master` and upstream. No changes are made. |
| `--dry-run` | Performs the merge into a temporary staging branch. If the merge is clean it reports success; if there are conflicts it shows them. Either way the changes are **not** pushed and the staging branch is deleted. |
| `--help` | Prints usage and exits. |

### Typical workflow

```bash
# 1. Check what is pending
tools/sync-upstream-manual.sh --log

# 2. Preview affected files
tools/sync-upstream-manual.sh --diff

# 3. Test the merge (no push)
tools/sync-upstream-manual.sh --dry-run

# 4. Perform the actual merge; script asks before pushing
tools/sync-upstream-manual.sh
```

### What the script does internally

1. Adds `upstream` remote pointing to `Freetz-NG/freetz-ng` (idempotent).
2. Fetches `upstream/master`.
3. Updates the local `upstream-mirror` branch to track `upstream/master`.
4. Checks whether `master` already contains all upstream commits; exits cleanly if so.
5. Aborts if the working tree is dirty.
6. Creates a timestamped staging branch `sync/upstream-YYYYMMDD-HHmmss`.
7. Runs `git merge upstream/master --no-edit` on the staging branch.
8. If the merge succeeds:
   - In `--dry-run` mode: deletes the branch and exits without pushing.
   - Otherwise: fast-forwards `master` to the staging branch, deletes the staging branch, and asks whether to push to `origin`.
9. If the merge produces conflicts:
   - In `--dry-run` mode: aborts the merge automatically and reports the conflicting files.
   - Otherwise: leaves the staging branch with conflicts and prints step-by-step resolution instructions.

### Resolving merge conflicts

When the script stops with "❌ Merge conflicts detected!" you are left on the staging branch. Resolve the conflicts manually and then complete the sync:

```bash
# Edit conflicted files, then:
git add <resolved-file> ...
git merge --continue

# Merge the staging branch back into master
git checkout master
git merge --ff-only sync/upstream-<timestamp>

# Delete the staging branch
git branch -d sync/upstream-<timestamp>

# Push
git push --force-with-lease origin master
git push origin upstream-mirror --force-with-lease
```

To abort instead and return to `master` as it was:

```bash
git merge --abort
git checkout master
git branch -D sync/upstream-<timestamp>
```

### Keeping the working tree clean before syncing

The script refuses to run if there are uncommitted changes. Typical causes and solutions:

| Symptom | Solution |
|---|---|
| Modified tracked files (e.g. `tools/translate_cache/*.json`) | `git add . && git commit -m "chore: your message"` then push |
| Untracked build artefacts (e.g. `tools/gennmtab`, broken symlinks) | `rm -f <file>` — do **not** add build artefacts to `.gitignore` without understanding their origin first |
| Stash preferred | `git stash` before sync, `git stash pop` after |

### Notes

- Always modify files in **`freetz-ng`** (the development repo), never directly in `freetz-evo` (the build/release repo). `freetz-evo` receives changes only through the sync mechanism.
- The GitHub Actions workflow uses the same merge strategy. If the workflow is up to date there may be nothing to sync manually.
- The `upstream-mirror` branch is a read-only mirror of `Freetz-NG/freetz-ng master` and is updated on every sync. It is used by the GitHub Actions workflow status badge.
