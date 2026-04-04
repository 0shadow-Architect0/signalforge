# Command Surface

## Command philosophy
SignalForge should feel like operating a foundry, not prompting a black box.
The command system exists to make strategic work explicit, reproducible, and inspectable.

## Primary command groups

| Group | Commands | Purpose |
|---|---|---|
| intake | add, batch, inspect | Create canonical sources from raw material |
| analyze | source, compare, whitespaces | Strategic interpretation of sources |
| semantic | status, test | LLM-powered deep understanding layer |
| thesis | create, merge, refine | Generate and refine product theses |
| decide | evaluate, commit, revisit | Decision evaluation and state transitions |
| adversarial | audit, stress-test, red-team, bias-audit | Red team AI for strategic theses |
| drift | snapshot, analyze, portfolio | Temporal signal dynamics |
| convergence | scan, emergence | Cross-domain intersection detection |
| portfolio | review, lane, rebalance, map, drift | Portfolio-level control room |
| export | markdown, json, publish-pack | Controlled translation to public surfaces |

## Why the surface matters
A strong command surface gives SignalForge three structural advantages:
1. reproducibility for serious builders
2. composability for autonomous agents
3. a clean bridge into API and UI layers later without losing product clarity

## Semantic intelligence commands
The `forge semantic` namespace controls the LLM-powered deep understanding layer.

### `forge semantic status`
Show semantic layer configuration status. Displays provider, model, and whether the layer is enabled or in deterministic-only mode.

### `forge semantic test`
Test semantic layer connectivity. Sends a test completion to verify the LLM provider is reachable.

## Adversarial engine commands
The `forge adversarial` namespace is where SignalForge stops being a thesis advocate and starts being an intellectual adversary.

### `forge adversarial audit`
Run a full adversarial audit on a single thesis. Combines kill criteria checking, red team analysis, and bias detection into one report with a green/yellow/orange/red status.

### `forge adversarial stress-test`
Portfolio-level stress test across all theses. Detects simultaneous collapse risk, groupthink patterns, and shared assumption concentration.

### `forge adversarial red-team`
Build the strongest possible argument against a thesis. Produces anti-thesis, load-bearing assumptions, failure modes, counter-evidence search queries, and a vulnerability score.

### `forge adversarial bias-audit`
Audit confirmation bias across all theses. Detects evidence asymmetry, anchoring, motivated reasoning, and portfolio groupthink.

## Drift engine commands
The `forge drift` namespace tracks how strategic signals evolve over time.

### `forge drift snapshot`
Record a signal snapshot for a thesis. Captures the full multi-dimensional score state at a point in time for trajectory analysis.

### `forge drift analyze`
Analyze drift dynamics for a single thesis. Computes velocity, acceleration, momentum, and volatility. Classifies signal phase as emerging, strengthening, stable, decaying, dormant, or volatile.

### `forge drift portfolio`
Full portfolio drift overview. Shows classification distribution, highest momentum thesis, and most volatile thesis.

## Convergence radar commands
The `forge convergence` namespace scans for cross-domain intersection.

### `forge convergence scan`
Scan all theses for convergence patterns. Produces convergence points with score, type (synergistic, competing, complementary, orthogonal), and signal strength (supersignal, strong, moderate, weak).

### `forge convergence emergence`
Detect emergent opportunities from signal convergence. Finds cases where convergence plus drift suggest a new opportunity that no individual thesis captured alone.

## Portfolio control commands
The `forge portfolio` namespace is where SignalForge stops behaving like an artifact generator and starts behaving like a strategic operating system.

### `forge portfolio review`
Generate the canonical review packet across all active directions.

### `forge portfolio lane`
Explain why a thesis belongs in `flagship`, `incubation`, `watchtower`, `merge-candidate`, or `decommission`.

### `forge portfolio rebalance`
Recommend how attention and execution energy should move across the portfolio.

### `forge portfolio drift`
Generate explicit drift records with severity, cause, and recommended action.

## Unified command
### `forge analyze`
Run all 4 engines together: semantic enrichment, adversarial analysis, drift computation, and convergence scanning in a single pass.

## Related documents
- `docs/command-contracts.md`
- `docs/portfolio-review.md`
- `docs/decision-graph.md`
