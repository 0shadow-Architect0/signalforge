# Command Contracts

## Command philosophy
SignalForge should feel like operating a foundry, not prompting a black box.
Commands are explicit, composable, and artifact-oriented.

## Command map
```mermaid
mindmap
  root((forge))
    intake
      add
      batch
      inspect
    analyze
      source
      compare
      whitespaces
      portfolio
    semantic
      status
      test
    evidence
      audit
      refresh
    thesis
      create
      merge
      refine
    decide
      evaluate
      commit
      revisit
    experiment
      create
      pack
    adversarial
      audit
      stress-test
      red-team
      bias-audit
    drift
      snapshot
      analyze
      portfolio
    convergence
      scan
      emergence
    portfolio
      map
      review
      drift
    export
      markdown
      json
      publish-pack
```

## Shared flags
```text
--workspace <name>        logical portfolio or operating context
--source <id>             one or more source ids
--artifact <id>           one or more artifact ids
--format md|json|both     output surface
--evidence-mode strict|balanced|exploratory
--write / --no-write      persist outputs or preview only
--explain                 attach rationale and scoring breakdown
```

## Primary contracts

### `forge intake add`
Create one canonical source from a repo URL, paper URL, article URL, or note path.

**Example**
```bash
forge intake add https://github.com/example/project --type repo --workspace signalforge-lab
```

**Writes**
- `sources/<type>/src_*.md`
- `system/index/src_*.json`
- `system/runs/run_*.json`

### `forge analyze compare`
Compare multiple sources and extract overlapping capabilities, strategic wedges, and category patterns.

**Example**
```bash
forge analyze compare --source src_repo_001 --source src_paper_004 --source src_note_002 --workspace signalforge-lab
```

**Writes**
- `insights/insight_compare_*.md`
- `opportunities/opp_*.md`
- optional JSON companions

### `forge semantic status`
Show semantic layer configuration status.

**Returns**
- enabled/disabled state
- provider name
- model, base URL, temperature, max tokens
- guidance for enabling if disabled

### `forge semantic test`
Test semantic layer connectivity.

**Returns**
- connection success/failure confirmation

### `forge evidence audit`
Inspect the vitality of the evidence supporting a thesis or decision bundle.

**Writes**
- `decisions/evidence/audit_*.md`
- `system/index/audit_*.json`
- optional trigger summary in `portfolio/drift/`

**Returns**
- bundle health
- freshness score
- convergence score
- contradiction score
- evidence gaps
- hard triggers
- soft triggers
- recommended review timing

### `forge thesis create`
Generate a named product thesis from sources, insights, or opportunities.

**Example**
```bash
forge thesis create --source src_repo_001 --source src_paper_004 --title "Decision-grade builder memory engine"
```

**Writes**
- `theses/thesis_*.md`
- `system/index/thesis_*.json`

### `forge decide evaluate`
Score a thesis across the decision framework before any final commitment.

**Writes**
- `decisions/evaluations/eval_*.md`
- `system/index/eval_*.json`
- optional evidence-gap report in `portfolio/reviews/`

**Returns**
- weighted score
- confidence
- recommended posture
- dimension scorecard
- review horizon
- evidence gaps

### `forge decide commit`
Record the official state transition for a thesis.

**Decision states**
- build
- incubate
- watch
- combine
- reject

**Writes**
- `decisions/decision_*.md`
- `portfolio/maps/*.md`
- `system/index/decision_*.json`

### `forge experiment pack`
Generate an execution package from a committed decision.

**Outputs**
- experiment brief
- repo plan
- issue tree
- launch hypothesis
- artifact references

### `forge adversarial audit`
Run a full adversarial audit on a single thesis: kill criteria, red team analysis, and bias detection.

**Example**
```bash
forge adversarial audit thesis_signalforge-001 --workspace signalforge-lab
```

**Returns**
- overall status (green/yellow/orange/red)
- vulnerability score
- kill criteria triggered vs total
- anti-thesis summary
- bias indicators
- actionable recommendation

### `forge adversarial stress-test`
Run portfolio-level stress test across all theses.

**Example**
```bash
forge adversarial stress-test --workspace signalforge-lab
```

**Returns**
- portfolio alert level (green/yellow/orange/red)
- composite risk score
- theses at risk count
- bias health status
- groupthink risks
- portfolio-level recommendation

### `forge adversarial red-team`
Build the strongest possible case against a thesis (steel-man opposition).

**Example**
```bash
forge adversarial red-team thesis_signalforge-001 --workspace signalforge-lab
```

**Returns**
- anti-thesis statement
- anti-thesis confidence
- load-bearing assumptions with failure probability
- counter-evidence search queries
- failure modes with early warning signals
- steel-man opposition
- market concerns, timing risks, execution traps
- overall vulnerability score

### `forge adversarial bias-audit`
Audit confirmation bias across all theses in a workspace.

**Example**
```bash
forge adversarial bias-audit --workspace signalforge-lab
```

**Returns**
- overall health (healthy/warning/critical)
- bias rate
- individual bias findings per thesis
- bias types: evidence_asymmetry, anchoring, motivated_reasoning
- groupthink risks across the portfolio

### `forge drift snapshot`
Record a signal snapshot for a thesis, capturing its current multi-dimensional score state.

**Example**
```bash
forge drift snapshot thesis_signalforge-001 --workspace signalforge-lab
```

**Returns**
- snapshot confirmation
- composite score
- timestamp

### `forge drift analyze`
Analyze temporal drift dynamics for a single thesis across accumulated snapshots.

**Example**
```bash
forge drift analyze thesis_signalforge-001 --workspace signalforge-lab
```

**Returns**
- signal phase (emerging/strengthening/stable/decaying/dormant/volatile)
- momentum score
- volatility score
- velocity vector across all dimensions
- snapshot count and confidence
- recommended action

### `forge drift portfolio`
Full portfolio drift overview across all theses.

**Example**
```bash
forge drift portfolio --workspace signalforge-lab
```

**Returns**
- total theses tracked
- classification distribution
- highest momentum thesis
- most volatile thesis
- per-thesis drift details

### `forge convergence scan`
Scan all theses for cross-domain convergence patterns.

**Example**
```bash
forge convergence scan --workspace signalforge-lab
```

**Returns**
- convergence points sorted by score
- signal strength (supersignal/strong/moderate/weak)
- convergence type (complementary/competing/synergistic/orthogonal)
- opportunity space description
- contributing thesis IDs

### `forge convergence emergence`
Detect emergent opportunities from signal convergence across theses.

**Example**
```bash
forge convergence emergence --workspace signalforge-lab
```

**Returns**
- total convergence points found
- strong signal count
- emergent opportunity descriptions
- contributing theses per opportunity

### `forge analyze` (unified)
Run all 4 engines together: semantic + adversarial + drift + convergence.

**Returns**
- unified analysis report combining all engine outputs

### `forge portfolio review`
Produce an updated view of all active directions, their evidence strength, and drift risk.

**Writes**
- `portfolio/reviews/review_*.md`
- `portfolio/drift/drift_*.md`

### `forge portfolio lane`
Explain the current operating lane for a thesis.

**Returns**
- lane classification
- supporting signals
- evidence gaps
- recommended next action

### `forge portfolio rebalance`
Propose how attention and execution energy should shift across the portfolio.

**Returns**
- attention changes by thesis
- merge suggestions
- decommission candidates
- review priorities

### `forge export publish-pack`
Prepare a public-facing bundle from selected internal artifacts.

**Outputs**
- README narrative
- architecture summary
- artifact screenshots or excerpts
- launch copy snippets
- selected example artifacts

## User flow encoded as commands
```mermaid
sequenceDiagram
    participant Builder
    participant Forge
    participant Workspace

    Builder->>Forge: forge intake batch sources.yaml
    Forge->>Workspace: write canonical sources
    Builder->>Forge: forge analyze compare --source A --source B --source C
    Forge->>Workspace: write insight memo + opportunities
    Builder->>Forge: forge thesis create --source A --source B --source C
    Forge->>Workspace: write thesis
    Builder->>Forge: forge adversarial audit thesis_signalforge-001
    Forge->>Builder: display status + vulnerability + recommendation
    Builder->>Forge: forge drift snapshot thesis_signalforge-001
    Forge->>Workspace: record signal snapshot
    Builder->>Forge: forge convergence scan
    Forge->>Builder: display convergence points
    Builder->>Forge: forge decide evaluate thesis_signalforge-001 --explain
    Forge->>Workspace: write evaluation memo + scorecard
    Builder->>Forge: forge decide commit thesis_signalforge-001 --decision build
    Forge->>Workspace: write decision memo
    Builder->>Forge: forge experiment pack decision_build_signalforge-001
    Forge->>Workspace: write experiment and repo pack
    Builder->>Forge: forge portfolio review
    Forge->>Workspace: write portfolio review + drift map
```

## Contract rule
A valid SignalForge command should always do at least one of the following:
- create a durable artifact
- update portfolio state
- improve decision clarity
- prepare execution surfaces
- strengthen adversarial resilience
- capture temporal dynamics
