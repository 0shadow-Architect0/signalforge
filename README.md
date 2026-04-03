# SignalForge

Strategic signal intelligence platform. Detect, track, and analyze opportunity signals across domains using adversarial red teams, temporal drift analysis, and cross-domain convergence radar.

## Architecture

SignalForge has 4 specialized engines that work independently or together through the unified analysis pipeline:

```
Sources ──► Semantic Layer ──► Adversarial Engine
                │                    │
                ▼                    ▼
          SignalDrift Engine ──► Convergence Radar
                │                    │
                └────► Unified Analysis ──► Report
```

### 1. Semantic Intelligence Layer
LLM-powered enrichment of sources, comparisons, contradictions, and whitespace analysis. Works with any OpenAI-compatible provider.

**Supported providers:** Zhipu AI (GLM-5), OpenAI, Ollama, vLLM, Together AI, Groq, Mistral

### 2. Adversarial Thesis Engine
Red-team your own strategic theses before the market does.

- **Kill Criteria Monitor** - generates and monitors conditions that would invalidate a thesis
- **Red Team Builder** - constructs the strongest possible argument against your thesis
- **Bias Tracker** - detects confirmation bias, anchoring, and motivated reasoning across your portfolio

### 3. SignalDrift Engine
Track how your signals evolve over time. Every signal is a living entity with velocity, acceleration, and momentum.

- **TimeSeriesStore** - records signal snapshots at each analysis pass
- **DriftAnalyzer** - computes velocity (rate of change per dimension), acceleration, momentum, and volatility
- **SignalClassifier** - classifies signal lifecycle phase: EMERGING, STRENGTHENING, STABLE, DECAYING, DORMANT
- **Divergence Detection** - finds when related signals split in opposite directions

### 4. Convergence Radar
Detect when signals from different domains converge on the same opportunity space. When 3+ signals converge, that's a super-signal worth 10x more than any individual signal.

- **OverlapDetector** - multi-dimensional similarity computation
- **ConvergenceRadar** - cluster detection with graph-based grouping
- **Emergence Detection** - meta-signal when convergence + strengthening = new opportunity

## Installation

```bash
git clone https://github.com/0shadow-Architect0/signalforge.git
cd signalforge
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick Start

### Add a source
```bash
forge source add "https://arxiv.org/abs/2401.xxxxx" --type paper
```

### Create a thesis
```bash
forge thesis create my-thesis --name "AI Agent Infrastructure"
```

### Run unified analysis
```bash
forge analyze
```

### Individual engine commands
```bash
forge adversarial audit my-thesis          # Full adversarial audit
forge adversarial red-team my-thesis       # Build anti-thesis
forge adversarial stress-test              # Portfolio stress test
forge adversarial bias-audit               # Confirmation bias check

forge drift snapshot my-thesis             # Record signal snapshot
forge drift analyze my-thesis              # Show velocity/momentum
forge drift portfolio                      # Full drift overview

forge convergence scan                     # Find convergence patterns
forge convergence emergence                # Detect emergent opportunities

forge semantic status                      # Check provider config
forge semantic test                        # Test LLM connection
```

### JSON output
```bash
forge analyze --json | jq '.summary'
```

## Configuration

### LLM Provider (optional - works without LLM in deterministic mode)

```bash
# Zhipu AI GLM-5
export SF_SEMANTIC_PROVIDER=openai
export SF_SEMANTIC_BASE_URL=https://open.bigmodel.cn/api/paas/v4
export SF_SEMANTIC_API_KEY=your_key_here
export SF_SEMANTIC_MODEL=glm-5

# OpenAI
export SF_SEMANTIC_PROVIDER=openai
export SF_SEMANTIC_API_KEY=sk-...
export SF_SEMANTIC_MODEL=gpt-4o-mini

# Ollama (local)
export SF_SEMANTIC_PROVIDER=openai
export SF_SEMANTIC_BASE_URL=http://localhost:11434/v1
export SF_SEMANTIC_API_KEY=ollama
export SF_SEMANTIC_MODEL=llama3
```

When no provider is configured, all engines run in deterministic mode using heuristic algorithms.

### Persistence

SignalForge uses SQLite (`~/.signalforge/signalforge.db`) to persist snapshots, reports, and convergence events across sessions.

## Project Structure

```
signalforge/
├── src/signalforge/
│   ├── adversarial/          # Red team + kill criteria + bias tracking
│   │   ├── engine.py         # Full adversarial orchestration
│   │   ├── kill_criteria.py  # Kill condition monitoring
│   │   ├── red_team.py       # Anti-thesis builder
│   │   ├── bias_tracker.py   # Confirmation bias detection
│   │   └── config.py
│   ├── drift/                # Temporal signal dynamics
│   │   ├── timeseries.py     # Snapshot store
│   │   ├── analyzer.py       # Velocity/acceleration/momentum
│   │   ├── classifier.py     # Lifecycle phase classification
│   │   └── config.py
│   ├── convergence/          # Cross-domain intersection detection
│   │   ├── radar.py          # Cluster + emergence detection
│   │   ├── overlap.py        # Multi-dimensional similarity
│   │   └── config.py
│   ├── semantic/             # LLM-powered enrichment
│   │   ├── provider.py       # OpenAI-compatible provider
│   │   ├── enricher.py       # Source/comparison/whitespace enrichment
│   │   ├── evidence.py       # Evidence chain extraction
│   │   ├── prompts.py        # LLM prompt templates
│   │   └── config.py
│   ├── unified.py            # All-engine pipeline + report
│   ├── persistence.py        # SQLite backend
│   ├── analysis.py           # Core analysis functions
│   ├── models.py             # Pydantic data models
│   ├── artifacts.py          # Artifact persistence
│   ├── workspace.py          # Workspace management
│   └── cli/main.py           # Typer CLI with all commands
├── tests/                    # 52 passing tests
│   ├── test_semantic.py
│   ├── test_adversarial.py
│   ├── test_drift.py
│   ├── test_convergence.py
│   └── test_smoke.py
└── pyproject.toml
```

## Signal Lifecycle

```
EMERGING ──► STRENGTHENING ──► STABLE ──► DECAYING ──► DORMANT
   │              │               │           │            │
   └─ invest ─────┘               └─ monitor ─┘            └─ prune
```

## Convergence Types

| Type | Meaning | Action |
|------|---------|--------|
| Synergistic | Complementary capabilities, high overlap | Merge resources |
| Competing | Same capabilities, same space | Pick one, abandon the other |
| Complementary | Different capabilities, shared space | Build integration |
| Orthogonal | No meaningful overlap | Track separately |

## License

MIT
