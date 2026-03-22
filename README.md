# Philosopher-King Democracy (PKD): Agent-Based Model

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

**A Data-Driven Deliberative Governance Architecture: Comparing Track-Record Selection vs Electoral Democracy Under Populist Perturbation**

## Overview

This repository contains the complete agent-based simulation code for the research paper:

**"Philosopher-King Democracy: An Agent-Based Model of Track-Record Governance Under Populist Perturbation"**
*Aruma Harada*
Submitted to *Journal of Artificial Societies and Social Simulation (JASSS)*, March 2026

### The Problem

Electoral democracies are structurally vulnerable to demagoguery because they select representatives based on **appeal** rather than **demonstrated competence**. Recent global rise of populist movements has intensified concerns about this fundamental design flaw.

### The Solution: PKD

Philosopher-King Democracy (PKD) is a hybrid governance architecture that integrates three mechanisms:

1. **Track-record selection** for expert seats — Representatives selected based on accuracy of past policy predictions, not appeal
2. **Three-axis stratified sortition** for citizen seats — Random selection stratified by (policy specialty × Brennan archetype × tolerance level)
3. **Bounded-confidence deliberation** — Council members revise beliefs only toward those within their tolerance threshold (Hegselmann-Krause model)

### Key Findings

Monte Carlo simulations (30 runs × 300 periods) demonstrate:

- **4.6× better performance** than sortition democracy
- **19.4× better performance** than electoral democracy
- **Near-complete structural immunity** to populism (1.2% demagogue infiltration vs 59.6% in electoral democracy)
- **Emergent self-sorting**: Low-tolerance agents automatically eliminated through track-record feedback loop
- **Long-term self-improvement**: Cumulative advantage grows monotonically over time

## Repository Structure

```
pkd-simulation/
├── simulation_pkd_v3.py          # Main simulation code (World, Agent, 4 governance systems)
├── sensitivity_analysis.py       # 7-parameter sensitivity sweep (if available)
├── PKD_paper_draft_JASSS.md      # Full paper draft (7300+ words)
├── figures/
│   ├── pkd_v3_single_run.png     # 6-panel single simulation visualization
│   └── pkd_v3_ensemble.png       # 3-panel ensemble statistics
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Installation

### Requirements

- Python 3.8 or higher
- NumPy
- Matplotlib
- SciPy

### Setup

```bash
# Clone the repository
git clone https://github.com/mugityateishoku/pkd-simulation.git
cd pkd-simulation

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Run a Single Simulation

```python
python simulation_pkd_v3.py
```

This will:
1. Run a single 300-period simulation with default parameters (d=10 dimensions, N=100 agents)
2. Generate a 6-panel visualization (`pkd_v3_single_run.png`)
3. Print summary statistics comparing all four governance systems

### Run Ensemble Analysis

Modify the `__main__` block in `simulation_pkd_v3.py` to call `run_ensemble()`:

```python
if __name__ == "__main__":
    results = run_ensemble(n_runs=30, n_periods=300)
    plot_ensemble(results)
    print_summary_statistics(results)
```

### Sensitivity Analysis

```python
python sensitivity_analysis.py
```

Sweeps across 7 parameters:
- Demagogue population fraction (0–30%)
- Track-record decay rate α (0.5–0.99)
- Policy dimensionality d (2–20)
- Council size (3–20)
- Regime change probability (0–10%)
- Deliberation revision rate ρ (0–1.0)
- Expert noise advantage (σ_expert = 0.1–0.9)

## Model Description

### Entities

**World**: Policy environment with true optimal policy θ*(t) ∈ ℝ^d that evolves via Gaussian drift + occasional regime changes.

**Agents** (N=100):
- 80 citizens (distributed across 4 Brennan archetypes: IC, II, UC, UI)
- 15 experts (low noise, high tolerance)
- 5 demagogues (high appeal, high bias, low tolerance)

Each agent characterized by:
- `expertise_std` (σ): observation noise
- `appeal` (a): charisma (used in electoral selection)
- `bias` (b): systematic observational distortion
- `tolerance` (ε): bounded-confidence threshold
- `track_record` (r): exponential moving average of prediction accuracy

### Four Governance Systems

1. **Autocracy**: Single randomly chosen agent decides (changes every 48 periods)
2. **Electoral Democracy**: Citizens vote based on appeal + noise; top 5 elected (every 12 periods)
3. **Sortition Democracy**: 10 random agents selected (every 6 periods)
4. **PKD**: 5 expert seats (top track records) + 5 citizen seats (stratified lottery) (every 6 periods)

### Process Overview (each period)

1. World updates (drift + potential regime change)
2. Agents observe θ* with noise and bias
3. Each governance system selects council (if rotation period)
4. PKD councils deliberate (bounded-confidence Bayesian belief revision)
5. Policy = (weighted) mean of council proposals
6. Performance evaluated: −||policy − θ*||²
7. Track records updated (PKD only)
8. At t=100: Populist shock (demagogue appeal ×1.5, bias ×2.0)

## Replication

All results in the paper are fully replicable using fixed random seeds. Default seed=42.

To reproduce **Figure 1** (single run):
```python
results = run_simulation(n_periods=300, n_dim=10, seed=42)
plot_single_run(results)
```

To reproduce **Figure 2** (ensemble):
```python
results = run_ensemble(n_runs=30, n_periods=300, seed=42)
plot_ensemble(results)
```

## Theoretical Background

PKD synthesizes three research traditions:

- **Epistocracy** (Brennan 2016): Political power allocated by competence
- **Sortition** (Van Reybrouck 2016): Random selection ensures representativeness
- **Bounded-confidence opinion dynamics** (Hegselmann & Krause 2002): Deliberation effective only among tolerant agents

Central theoretical contribution: **Emergent self-elimination of low-tolerance agents**

Agents with low tolerance (ε < 1.5) refuse to integrate diverse information → produce worse predictions → accumulate lower track records → excluded from expert seats. This is not programmed; it emerges from feedback loop.

## Citation

If you use this code in your research, please cite:

```bibtex
@article{harada2026pkd,
  title={Philosopher-King Democracy: An Agent-Based Model of Track-Record Governance Under Populist Perturbation},
  author={Harada, Aruma},
  journal={Journal of Artificial Societies and Social Simulation},
  year={2026},
  note={Under review}
}
```

## License

MIT License - see LICENSE file for details

## Author

**Aruma Harada**
Independent Researcher
Email: arumajiro2022@gmail.com
GitHub: [@mugityateishoku](https://github.com/mugityateishoku)

## Acknowledgments

This research was developed independently as part of a portfolio for university admissions (Tsukuba University AC program, August 2027). Special thanks to the developers of:
- The Good Judgment Project (Tetlock & Gardner 2015) for empirical validation of track-record forecasting
- The ODD protocol community (Grimm et al. 2006, 2020) for ABM standardization
- JASSS reviewers for constructive feedback

## References

- Brennan, J. (2016). *Against Democracy*. Princeton University Press.
- Hegselmann, R., & Krause, U. (2002). Opinion dynamics and bounded confidence. *JASSS*, 5(3), 2.
- Tetlock, P. E., & Gardner, D. (2015). *Superforecasting: The Art and Science of Prediction*. Crown.
- Van Reybrouck, D. (2016). *Against Elections: The Case for Democracy*. Bodley Head.
- Grimm, V., et al. (2020). The ODD protocol for describing agent-based models. *JASSS*, 23(2), 7.

## Contact

For questions, collaboration inquiries, or to report issues, please open an issue on GitHub or email arumajiro2022@gmail.com.
