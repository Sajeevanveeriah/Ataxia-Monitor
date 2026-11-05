# Ataxia-Monitor handoff

Develop the VW-MTC1 controller design, its circuit simulations and the Android monitoring prototype.

## Work at 5 November 2026

Source baseline: [main at ce628529](https://github.com/Sajeevanveeriah/Ataxia-Monitor/commit/ce62852988d1d803c604cf0e2de925d06d543058). Use the linked revision to distinguish these changes from later work.

- Verify long LTspice runs and investigate charger and touch limits ([d6603220](https://github.com/Sajeevanveeriah/Ataxia-Monitor/commit/d66032206929cd807de80da3698be58d7072dc76), 20 Oct 2026).
- Reject failed measurements in stepped LTspice tables ([e45df778](https://github.com/Sajeevanveeriah/Ataxia-Monitor/commit/e45df7787bd4b6637de15108c47967992ab7f7d8), 20 Oct 2026).

## Resume here

Review the touch-input design PR before changing the board. The Android prototype reads phone sensors. Board transport, device instrumentation and physical touch timing need their own measurements.

1 open pull request at the baseline. Recent work: [#6](https://github.com/Sajeevanveeriah/Ataxia-Monitor/pull/6) Redesign Rev B touch input for 5 ms gaps and bounded contact current. [Current list](https://github.com/Sajeevanveeriah/Ataxia-Monitor/pulls).

## Files and checks

[README.md](README.md), [VW-MTC1/README.md](VW-MTC1/README.md), [app/README.md](app/README.md), [docs/20261020-VW-MTC1-Verification-Rev01.md](docs/20261020-VW-MTC1-Verification-Rev01.md).

Start with [.github/workflows/verify.yml](.github/workflows/verify.yml) for hosted check definitions. Confirm the run belongs to the commit under review.

At the source revision, GitHub reported success across 3 check or status entries. [View checks](https://github.com/Sajeevanveeriah/Ataxia-Monitor/commit/ce62852988d1d803c604cf0e2de925d06d543058/checks).

## Next handoff

When pausing, replace the dated snapshot with the active branch or revision, what changed, the checks actually run and their results, and the first unfinished action. Record any blocker or decision the next person needs. Keep private data and credentials out of this file.
