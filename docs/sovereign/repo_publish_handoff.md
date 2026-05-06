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

Run the publish preflight before creating the organization push:

```sh
python3 scripts/macos/verify_sovereign_publish_ready.py
python3 scripts/macos/verify_sovereign_publish_ready.py --strict
```

The non-strict run is useful during active development because it reports
warnings without failing the shell. The strict run is the final gate before the
Sovereign organization push.

Current known publish blockers to resolve on the final publish branch:

- `a.md` is a local investigation notebook and should not ship in the
  organization repo history if the branch can avoid it.
- Root/session `.pfsave` files are tracked in this working tree and should be
  removed from the publish branch or moved into an intentional fixture location
  with documentation.
- The working tree is intentionally dirty while the active implementation
  slices are still being assembled. Push only after reviewing and staging a
  focused set of files.

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
