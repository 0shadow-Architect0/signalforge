"""Adversarial Thesis Engine - Red Team AI for Strategic Intelligence.

The first automated adversary that actively fights your confirmation bias.
For every thesis you hold, it:
- Builds the strongest possible counter-argument
- Hunts for disconfirming evidence
- Monitors kill criteria
- Tracks your bias patterns over time
- Runs continuous stress tests on your assumptions

This is NOT a chatbot that argues with you.
This is a persistent, evidence-based strategic adversary that never sleeps.
"""

from signalforge.adversarial.engine import AdversarialEngine
from signalforge.adversarial.kill_criteria import (
    KillCriteriaGenerator,
    KillCriteriaMonitor,
)
from signalforge.adversarial.red_team import RedTeamBuilder
from signalforge.adversarial.bias_tracker import BiasTracker
from signalforge.adversarial.config import AdversarialConfig

__all__ = [
    "AdversarialEngine",
    "KillCriteriaGenerator",
    "KillCriteriaMonitor",
    "RedTeamBuilder",
    "BiasTracker",
    "AdversarialConfig",
]
