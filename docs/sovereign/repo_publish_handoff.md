# Sovereign Realms Repo Publish Handoff

This checkout is still the active Permafrost-derived working tree:

```text
/Users/dev/Desktop/OpenGL RTS game engine
```

Do not nest a second Git repository inside this folder. When the current branch
is ready to publish under the Sovereign Realms organization, use a dedicated
sibling checkout with the production repo name:

```text
/Users/dev/Desktop/sovereign-realms-engine
```

Recommended GitHub target:

```text
https://github.com/sovereignrealms/sovereign-realms-engine
git@github.com:sovereignrealms/sovereign-realms-engine.git
```

## Initial Repo Role

`sovereign-realms-engine` should remain a Permafrost-derived engine fork with
the upstream root layout intact. That keeps upstream sync and future PR review
practical while adding Sovereign-specific game packages in dedicated folders:

```text
scripts/sovereign/
assets/sovereign/
docs/sovereign/
tools/asset_validation/
```

Later, after the vertical slice stabilizes, game-only content can split into a
second repo such as:

```text
https://github.com/sovereignrealms/sovereign-realms-game
```

That later game repo can pin the engine fork as a submodule, subtree, release
archive, or sibling checkout.

## Publish Checklist

1. Keep the current working branch clean enough to push.
2. Exclude generated captures, QA output, local notebooks, and app bundles.
3. Preserve upstream `LICENSE.txt` and copyright notices.
4. Keep `NOTICE.md` and `CHANGES.md` with the Permafrost-derived modification
   history.
5. Push the branch to `sovereignrealms/sovereign-realms-engine`.
6. Keep OpenGL as the reference backend until Metal parity and scale gates are
   repeatedly green.

Current publish-preflight branch:

```text
codex/sovereign-publish-preflight
```

Current strict preflight status:

```text
SOVEREIGN_PUBLISH_READY_PASS fails=0 warnings=0 strict=1
```

The branch is ready for the organization push from a packaging hygiene
perspective. GitHub repository creation/push permissions are the remaining
operational step.

Run the publish preflight before creating the organization push:

```sh
python3 scripts/macos/verify_sovereign_publish_ready.py
python3 scripts/macos/verify_sovereign_publish_ready.py --strict
```

The non-strict run is useful during active development because it reports
warnings without failing the shell. The strict run is the final gate before the
Sovereign organization push.

Resolved publish blockers:

- `a.md` is no longer tracked by the publish-preflight branch.
- Root/session `.pfsave` files are no longer tracked by the publish-preflight
  branch.
- The publish-preflight branch is clean and strict preflight passes.

## Local Migration Shape

When ready to make the sibling folder, prefer a clean clone or worktree rather
than a Finder rename:

```sh
cd /Users/dev/Desktop
git clone /Users/dev/Desktop/OpenGL\ RTS\ game\ engine sovereign-realms-engine
cd sovereign-realms-engine
git remote add sovereign git@github.com:sovereignrealms/sovereign-realms-engine.git
```

If the GitHub repo already exists, use `git remote set-url sovereign ...`
instead of adding a duplicate remote.

For this checkout, a local HTTPS remote named `sovereign` is also acceptable:

```sh
git remote add sovereign https://github.com/sovereignrealms/sovereign-realms-engine.git
```
