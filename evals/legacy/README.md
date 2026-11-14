# Historical evaluation sources

[promptfoo/](promptfoo/README.md) preserves the former shared evaluation suite
from public source revision `2705078474de0cbdb92beb7c2db9dd97f2e08fc8`.
Its 36 tracked files retain their exact Git blob bytes and original relative
layout, including the original README, provider settings, scenarios, fixtures,
assertions, retained answers, package manifest, dependency lock, and nested
`legacy/` source inventory. The nested inventory records the earlier retired
runner at its own source revision; it has not been regenerated or requalified.

The archived suite targets retired packaged workflows and role-composition
APIs. Its commands and claims are historical. Do not run it against current
Dotbrain or treat it as the current evaluation route. Current model-free
calibration and native qualification guidance live in [the native guide](../native/README.md).
Neither archival preservation nor passing calibration promotes an old result to
qualification for the redesigned product.

## Inspect or reproduce historical context

Read a file at its original location with:

```sh
git show 2705078474de0cbdb92beb7c2db9dd97f2e08fc8:evals/README.md
```

For historical reproduction, use a separate checkout of that whole revision:

```sh
git worktree add --detach <historical-checkout> 2705078474de0cbdb92beb7c2db9dd97f2e08fc8
```

Inspect its original `evals/README.md` and repository setup in that checkout.
The fixture derives its repository root and Python environment from the original
layout and calls the product APIs from that revision. Running this relocated
copy with current product code does not reproduce that environment. Dependency
installation or native execution requires its own applicable authorization;
creating a historical checkout grants neither.

Existing ignored `evals/results/` and `evals/node_modules/` stay at their original
locations untouched. Preserve each held result's tested revision, provider,
runtime/model settings, raw evidence, failures, and attempt history. The archive
does not change provider behavior, reset exhausted allowances, sanitize old
evidence, or claim that a historical live run passed.
