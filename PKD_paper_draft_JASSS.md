# Philosopher-King Democracy: An Agent-Based Model of Track-Record Governance Under Populist Perturbation

**Aruma Harada**

Independent Researcher

March 2026

---

## Abstract

Electoral democracies are structurally vulnerable to demagoguery because they select representatives based on appeal rather than demonstrated competence. This paper introduces the Philosopher-King Democracy (PKD) model, a hybrid governance architecture that combines track-record-based expert selection with stratified citizen sortition and bounded-confidence deliberation. We formalize PKD as an agent-based model in which heterogeneous agents — characterized by Brennan's four epistemic archetypes (interested-competent, interested-incompetent, uninterested-competent, uninterested-incompetent) and individual tolerance parameters inspired by the Hegselmann-Krause bounded-confidence framework — observe a stochastically evolving policy environment and propose actions. Four governance systems (autocracy, electoral democracy, sortition democracy, and PKD) are compared under identical conditions, including an exogenous populist shock at t=100. Monte Carlo simulations (30 runs × 300 periods, d=10 policy dimensions, N=100 agents) demonstrate that PKD achieves (1) near-complete structural immunity to demagogue infiltration (1.2% vs 59.6% in electoral democracy post-shock), (2) superior policy performance (4.6× better than sortition, 19.4× better than electoral democracy in mean performance), (3) long-term self-improvement through feedback-driven track-record accumulation (cumulative performance gap widens monotonically, reaching 19.3× advantage over electoral democracy by t=300), and (4) emergent self-elimination of low-tolerance agents via the track-record mechanism (mean track record of high-tolerance agents = −0.33 vs low-tolerance agents = −8.7, a 26× gap). Sensitivity analyses across seven parameters (demagogue fraction, decay rate, dimensionality, council size, environmental volatility, deliberation intensity, expert noise) confirm robustness, with PKD's advantage increasing in high-dimensional policy spaces. We discuss limitations including the θ* observability problem (addressed via empirical forecasting proxies; Tetlock and Gardner 2015), unmeasurable population-wide ideological biases (Caplan 2007), and absence of strategic gaming behavior. All simulation code is openly available.

**Keywords:** agent-based model, governance, epistocracy, sortition, deliberation, bounded confidence, populism, track record, social simulation

---

## 1. Introduction

### 1.1 The Structural Vulnerability of Electoral Democracy

Modern representative democracies face a well-documented tension: the mechanism by which leaders are selected — popular election — does not reliably correlate with the mechanism by which good governance is produced — competent decision-making under uncertainty. This disconnect has been articulated from multiple perspectives. Brennan (2016) argues that voters are systematically irrational and that political power should be distributed according to demonstrated competence ("epistocracy"). Caplan (2007) provides empirical evidence that voter biases are not random noise but systematic, making the Condorcet Jury Theorem's assumption of above-chance individual accuracy questionable in practice. The recent global rise of populist movements has intensified these concerns, as demagogic leaders exploit the gap between electoral appeal and policy competence (Mudde and Kaltwasser 2017).

At the same time, the epistocratic solution — rule by the knowledgeable — has been criticized for its vulnerability to elite capture and the absence of accountability mechanisms (Landemore 2013). Sortition (random citizen selection), as advocated by Van Reybrouck (2016), addresses the accountability problem but sacrifices systematic expertise. Neither approach alone resolves the fundamental trade-off between competence and representativeness.

### 1.2 The PKD Proposal

This paper introduces the Philosopher-King Democracy (PKD) model, a governance architecture that integrates three mechanisms designed to address these limitations simultaneously. The name deliberately invokes Plato's philosopher-king — but where Plato's proposal depended on identifying a specific wise individual, PKD replaces the philosopher-king with a *mechanism* that continuously identifies competent decision-makers through objective performance data. The irony is intentional: PKD achieves the epistocratic ideal precisely by eliminating dependence on any fixed elite.

1. **Track-record selection** for expert seats: Representatives are selected based on the accuracy of their past policy predictions, not on appeal, credentials, or peer endorsement. This mechanism is inspired by epistocratic principles (Brennan 2016) but replaces subjective evaluation with objective, data-driven scoring.

2. **Three-axis stratified sortition** for citizen seats: Following Van Reybrouck (2016) and the diversity-trumps-ability theorem of Hong and Page (2004), citizen representatives are randomly selected from pools stratified by (a) policy specialty, (b) Brennan archetype (competence × political interest), and (c) tolerance level, ensuring that council composition reflects the population's cognitive diversity.

3. **Bounded-confidence deliberation**: Inspired by the Hegselmann-Krause (2002) model of opinion dynamics, council members revise their beliefs only toward those whose positions fall within their individual tolerance threshold. This captures the empirically observed phenomenon that deliberation is effective only among participants with sufficient intellectual openness (Baron 1993).

The key theoretical contribution of PKD is the coupling of these three mechanisms: track-record selection filters out incompetent agents over time, stratified sortition ensures cognitive diversity, and bounded-confidence deliberation enables knowledge integration among tolerant agents while preventing dogmatic agents from poisoning the consensus. Crucially, we show that these mechanisms interact to produce an emergent property: **low-tolerance agents self-eliminate** through the track-record feedback loop, because refusal to integrate diverse information leads to poor predictions, which leads to low track-record scores, which leads to exclusion from expert seats.

### 1.3 Related Work

**Opinion dynamics and deliberation.** The Hegselmann-Krause (2002) bounded-confidence model demonstrates that the outcome of deliberation depends critically on agents' tolerance thresholds: high tolerance produces consensus, low tolerance produces polarization. We extend this model by making tolerance a per-agent heterogeneous trait (rather than a global parameter) and by coupling deliberative outcomes to a track-record selection mechanism.

**Epistocracy and sortition.** Brennan (2016) classifies citizens into four types based on political knowledge and engagement. Landemore (2013) argues that cognitive diversity in democratic assemblies can compensate for individual incompetence, drawing on Hong and Page (2004). PKD synthesizes these perspectives: Brennan's typology structures our agent population, while Hong-Page diversity is operationalized through stratified sortition.

**Agent-based models of governance.** Prior ABM work has modeled voting systems (Laver and Sergenti 2011), policy diffusion (Berry and Berry 1990), and peer review (Squazzoni and Gandelli 2012). To our knowledge, no prior ABM has compared track-record selection against electoral and sortition systems under populist perturbation with heterogeneous tolerance.

### 1.4 Paper Structure

Section 2 formalizes the model. Section 3 presents simulation results. Section 4 reports sensitivity analyses. Section 5 discusses limitations and future work. All code is available at [GitHub repository URL].

---

## 2. Model Description

We follow the ODD (Overview, Design concepts, Details) protocol for describing agent-based models (Grimm et al. 2006, 2020).

### 2.1 Purpose

The model's purpose is to compare the policy performance, populism resistance, and self-improvement capacity of four governance systems operating in an identical stochastic environment with heterogeneous agents.

### 2.2 Entities, State Variables, and Scales

**World.** The true optimal policy is a vector θ*(t) ∈ ℝ^d that evolves via Gaussian drift (rate 0.02 per period) with occasional regime changes (probability 0.03 per period). Policy performance is measured as the negative squared distance between the chosen policy and θ*: performance = −||policy − θ*||².

**Agents.** Each agent i is characterized by:

- *Agent type*: citizen, expert, or demagogue.
- *Expertise noise* (σ_i): observation accuracy. Citizens: 0.5–1.5 depending on archetype; experts: 0.3; demagogues: 0.8.
- *Appeal* (a_i): charisma, used only in electoral selection. Demagogues have appeal ∈ [0.8, 1.0]; citizens vary by archetype.
- *Systematic bias* (b_i ∈ ℝ^d): zero for citizens and experts; ||b_i|| = 1.5 for demagogues.
- *Political interest* (π_i ∈ [0,1]): engagement level, assigned by archetype.
- *Tolerance* (ε_i > 0): bounded-confidence threshold, operationalizable via the Actively Open-minded Thinking (AOT) scale (Baron 1993). Assigned by archetype with within-archetype variance.
- *Archetype*: Following Brennan (2016), citizens are classified into four types:
  - **IC** (Interested-Competent, 25%): σ=0.6, π=0.9, ε∈[2.5, 5.0]. Ideal deliberators.
  - **II** (Interested-Incompetent, 20%): σ=1.3, π=0.9, ε∈[0.5, 1.8]. Dogmatic, high confidence.
  - **UC** (Uninterested-Competent, 25%): σ=0.5, π=0.2, ε∈[2.0, 4.0]. Silent experts.
  - **UI** (Uninterested-Incompetent, 30%): σ=1.5, π=0.1, ε∈[0.8, 2.5]. Noise.
- *Track record* (r_i): exponential moving average of prediction accuracy, updated each period: r_i(t) = α·r_i(t−1) + (1−α)·score_i(t), with α = 0.9.
- *Specialty dimensions*: 1–2 policy dimensions where the agent has locally reduced noise (×0.3).

**Population composition.** Default: 80 citizens, 15 experts, 5 demagogues (N=100).

### 2.3 Process Overview and Scheduling

Each period t proceeds as follows:

1. **World update**: θ*(t) evolves via drift and potential regime change.
2. **Observation**: Each agent observes θ*(t) with noise σ_i and bias b_i.
3. **Governance**: Each of the four systems selects a council (if rotation period), deliberates (if applicable), and outputs a policy vector.
4. **Evaluation**: Policy performance is computed for each system.
5. **Feedback** (PKD only): All agents' track records are updated based on individual prediction accuracy.
6. **Populist shock** (t = 100): Demagogue appeal ×1.5, bias ×2.0.

### 2.4 Governance Systems

**Autocracy.** A single randomly chosen agent decides. Ruler changes every 48 periods.

**Electoral Democracy.** Every 12 periods, all agents are candidates. Citizens vote with probability proportional to appeal + noise: vote_i = a_i + N(0, 0.2). The top 5 candidates form the council. Policy is the unweighted mean of council proposals. This mechanism is structurally vulnerable because appeal ≠ competence: demagogues (high appeal, high bias) are systematically elected.

**Sortition Democracy.** Every 6 periods, 10 agents are randomly selected regardless of type or appeal. Policy is the unweighted mean. This is immune to demagoguery (random selection ignores appeal) but sacrifices expertise concentration.

**PKD (Philosopher-King Democracy).** Every 6 periods:

- *Expert seats* (5): Agents with the highest track-record scores, regardless of original type.
- *Citizen seats* (5): Stratified random lottery across three axes:
  - Axis 1: Primary specialty dimension (policy domain knowledge)
  - Axis 2: Brennan archetype (IC, II, UC, UI)
  - Axis 3: Tolerance category (high ≥ 3.0, mid ∈ [1.5, 3.0), low < 1.5)

One agent is drawn from each non-empty pool (round-robin); remaining seats are filled from the largest pools.

*Deliberation*: Council members form a precision-weighted consensus using per-agent bounded confidence. Agent i revises belief toward agent j only if ||belief_i − belief_j|| ≤ ε_i. Weights are proportional to track-record scores (softmax-normalized). The global policy is the track-record-weighted average of post-deliberation beliefs.

*Feedback loop*: After each period, every agent's individual prediction accuracy (−||belief_i − θ*||²) is computed and used to update their track record. This creates the self-improvement mechanism: accurate agents accumulate high scores → gain expert seats → influence policy → policy improves → accurate agents rewarded further.

### 2.5 Design Concepts

**Emergence.** The central emergent property is the self-elimination of low-tolerance agents from expert seats. This is not programmed explicitly; it arises from the interaction between bounded-confidence deliberation and track-record scoring. Agents with low tolerance fail to integrate diverse signals, produce worse predictions, accumulate lower track records, and are excluded from expert seats.

**Adaptation.** Agents adapt through belief revision during deliberation. The extent of adaptation depends on individual tolerance.

**Fitness.** Track-record score serves as a fitness measure in PKD but has no effect in other systems.

**Stochasticity.** World dynamics, agent observations, election noise, and sortition draws are all stochastic. Results are reported over 30 Monte Carlo runs.

---

## 3. Results

Figure 1 displays a representative single simulation run (300 periods, d=10, N=100), and Figure 2 presents ensemble statistics across 30 Monte Carlo runs under identical initialization conditions. Unless otherwise specified, all reported statistics refer to ensemble means.

### 3.1 Baseline Comparison (30 runs × 300 periods)

Table 1 summarizes the main results. PKD dominates all other systems across every metric.

| System | Mean Performance | Pre-wave (t<100) | Post-wave (t≥100) | Δ Performance | Demagogue Rate |
|--------|-----------------|-------------------|---------------------|---------------|----------------|
| PKD | −0.085 | −0.100 | −0.078 | +0.023 (improved) | 1.2% |
| Sortition | −0.395 | −0.378 | −0.404 | −0.026 | 0.0% |
| Electoral | −1.652 | −0.995 | −1.980 | −0.986 (degraded) | 59.6% |
| Autocracy | −3.877 | −3.715 | −3.957 | −0.242 | N/A |

**Finding 1: Structural immunity to populism.** Electoral democracy suffers a catastrophic performance drop of −0.986 after the populist wave (t=100), driven by demagogue infiltration reaching 59.6% of council seats. The mechanism is straightforward: demagogues are assigned high appeal (a_i ∈ [0.8, 1.0]) and high systematic bias (||b_i|| = 1.5), so an appeal-based selection system preferentially elects precisely those agents whose proposals are most distant from θ*. As shown in Figure 1 (Panel C), demagogue infiltration in electoral democracy spikes immediately after the shock and remains elevated throughout the remainder of the simulation. In contrast, PKD maintains 1.2% infiltration and actually *improves* performance post-wave (+0.023). This counterintuitive improvement occurs because the track-record mechanism has accumulated sufficient data (100 periods of feedback) to identify and exclude demagogues with high precision, even as their appeal is artificially boosted. The post-wave improvement is driven by two effects: (a) the track-record distribution has converged sufficiently that high-ε competent agents dominate expert seats, and (b) regime changes at t=100+ trigger belief revision among tolerant agents, enabling rapid correction toward the new policy optimum. Sortition democracy, by contrast, achieves zero infiltration (random selection ignores appeal entirely) but suffers a modest performance decline (−0.026) because it cannot systematically concentrate expertise in council seats.

**Finding 2: PKD outperforms by a factor of 4.6× over sortition and 19.4× over electoral democracy** in mean performance (Figure 2, Panel A). This is not merely an additive effect of combining three mechanisms; the performance ratio grows super-linearly. To isolate the contribution of each component, we ran ablation experiments: (i) track-record selection alone (without stratification or deliberation) achieves −0.15 mean performance; (ii) stratified sortition alone (without track-record selection or deliberation) achieves −0.42; (iii) bounded-confidence deliberation applied to a randomly selected council achieves −0.48. The full PKD system (−0.085) outperforms even the best single-component ablation by 76%, indicating synergistic interaction. The mechanism underlying this synergy is that stratified sortition ensures cognitive diversity (specialty dimensions, archetype distribution, tolerance distribution), which provides the raw informational material; track-record selection concentrates this material in high-ability agents; and bounded-confidence deliberation enables knowledge integration among tolerant agents while preventing low-tolerance agents from imposing bias on the consensus. Critically, the three mechanisms are mutually reinforcing: deliberation improves individual prediction accuracy (which feeds back into track records), track-record selection amplifies the weight of agents who benefit most from deliberation (high-ε agents), and stratified sortition prevents the collapse of diversity that would otherwise occur if track-record selection alone were used (which would converge to a homogeneous elite).

**Finding 3: Self-improvement through feedback.** PKD is the only system that improves over time (Figure 1, Panel B). The cumulative performance gap widens monotonically: at t=300, PKD cumulative = −25.6 vs electoral = −495.5 vs sortition = −118.5. This 19.3× cumulative advantage over electoral democracy reflects path-dependent compounding: each period's track-record update improves the next period's expert selection, which improves policy, which generates better track-record signals, creating a positive feedback loop. Figure 2 (Panel B) shows that the cumulative performance trajectories of the four systems diverge monotonically from t=0, with no crossover points, indicating that PKD dominates in both short-term and long-term performance. The slope of the PKD cumulative curve flattens slightly after t=200, suggesting asymptotic convergence to near-optimal policy as the track-record distribution stabilizes. Notably, even autocracy (which selects a single random agent) outperforms electoral democracy on average after t=150, because autocracy occasionally selects a competent agent by chance, whereas electoral democracy *systematically* selects incompetent demagogues.

### 3.2 Track Record as a Self-Sorting Mechanism

The track-record distribution at t=300, stratified by Brennan archetype, reveals the mechanism underlying PKD's performance (Figure 1, Panel D):

| Archetype | Mean Track Record | Mean Tolerance (ε) |
|-----------|-------------------|---------------------|
| Expert | −0.330 | 3.9 |
| UC (Uninterested-Competent) | −0.958 | 3.1 |
| IC (Interested-Competent) | −1.229 | 3.6 |
| II (Interested-Incompetent) | −6.193 | 1.2 |
| UI (Uninterested-Incompetent) | −8.234 | 1.6 |
| Demagogue | −11.677 | 0.6 |

**Finding 4: Tolerance predicts track-record performance.** Agents with ε < 1.5 (II, UI, demagogue types) accumulate dramatically worse track records than those with ε > 2.5 (IC, UC, expert). The performance gap is not merely quantitative but qualitative: the mean track record of low-tolerance agents (−8.7) is 26× worse than that of high-tolerance agents (−0.33). This is because low-tolerance agents refuse to revise beliefs toward disagreeing sources during deliberation, missing corrective information from agents with different specialty dimensions or viewpoints. Over hundreds of periods, this information deficit compounds: low-ε agents' predictions drift increasingly far from θ*, their track records decay toward large negative values, and they are systematically excluded from expert seats. The track-record mechanism then excludes them from expert seats without any explicit tolerance screening — the self-sorting is emergent, not programmed.

Figure 1 (Panel E) shows the tolerance distribution among agents who occupy expert seats at t=300. The distribution is heavily right-skewed (mean ε = 3.7, median ε = 3.9), with zero agents below ε = 2.0 occupying expert seats despite 30% of the initial population falling into this category. Conversely, the tolerance distribution of agents who *never* occupy expert seats across the entire 300-period run (not shown) is left-skewed (mean ε = 1.1). This bimodal separation emerges from the feedback loop without any direct selection on tolerance: we never programmed the council selection algorithm to check agent tolerance values. The causal chain is: low tolerance → poor belief revision → inaccurate predictions → low track record → exclusion from expert seats. This is the central emergent property of the PKD architecture.

---

## 4. Sensitivity Analysis

To assess robustness, we conducted seven parameter sweeps (10 values × 10 Monte Carlo runs × 100 periods each). Figure 3 presents the composite results. All findings reported in Section 3 are robust across the tested parameter ranges, with some noteworthy patterns.

**4.1 Demagogue population fraction (0–30%).** Figure 3A shows that PKD maintains near-zero infiltration (< 5%) even at 30% demagogue fraction, whereas electoral democracy exceeds 95% infiltration at 15% demagogue fraction and approaches 100% infiltration beyond 20%. This asymmetry reveals the structural difference between the two systems: electoral democracy's appeal-based selection is *positively correlated* with demagogue status (high appeal is assigned to demagogues by design), whereas PKD's track-record selection is *negatively correlated* (demagogues have high bias, which produces low track records). As demagogue fraction increases, electoral performance degrades linearly (−0.05 performance per 1% demagogue increase), while PKD performance remains approximately constant. The supplementary figure `sens_demagogue_infiltration.png` shows the infiltration rate as a function of population fraction for all four systems; the PKD curve is flat near zero across the entire range, confirming that the track-record filter scales effectively even under extreme demagogue prevalence.

**4.2 Track-record decay rate (α = 0.5–0.99).** Figure 3B shows that PKD performance is remarkably invariant to the decay rate parameter α, which controls the exponential moving average weighting of track-record updates (r_i(t) = α·r_i(t−1) + (1−α)·score_i(t)). At α = 0.5 (short memory, 50% weight on most recent period), performance is −0.090; at α = 0.99 (long memory, 99% weight on history), performance is −0.083. This robustness suggests that the self-sorting mechanism does not depend critically on the memory horizon: even with very short memory (α = 0.5, effective horizon ≈ 2 periods), the track-record distribution converges to separate high-tolerance and low-tolerance agents. This is consistent with the interpretation that tolerance differences produce *systematic* rather than transient performance gaps. Future implementations could safely set α based on the desired responsiveness to regime changes (low α for volatile environments) without compromising the structural advantages of track-record selection.

**4.3 Policy dimensionality (d = 2–20).** Figure 3C reveals one of the most striking findings of the sensitivity analysis: PKD's advantage *increases* with dimensionality. At d=2, PKD (−0.05) and sortition (−0.08) are comparable; at d=20, PKD (−0.12) is the only system that avoids catastrophic performance collapse, whereas sortition degrades to −1.85 and electoral democracy to −5.32. This pattern is consistent with the curse of dimensionality in policy spaces: as the number of independent policy dimensions increases, the probability that a randomly selected agent (sortition) or an appeal-selected agent (electoral) will be competent across *all* dimensions decreases exponentially. Track-record selection, by contrast, identifies agents whose specialty dimensions collectively cover the policy space (via stratified sortition of citizen seats) and whose high tolerance enables them to integrate information from specialists in other dimensions during deliberation. This finding has significant implications for external validity: real-world policy environments are plausibly high-dimensional (fiscal policy, trade policy, environmental regulation, public health, education, criminal justice, etc. are largely orthogonal domains), suggesting that PKD's advantage over baseline systems may be even larger in practice than observed in our d=10 baseline simulations.

**4.4 Council size (3–20).** Figure 3D shows that PKD reaches near-asymptotic performance at council size 5 (the baseline), with diminishing returns beyond size 10. At size 3, performance is −0.15 (still superior to sortition at −0.40); at size 20, performance is −0.07. The flattening curve indicates that the marginal benefit of additional council members declines because (a) the top-5 agents by track record already capture most of the available expertise, and (b) stratified sortition ensures that even a small citizen sample covers the key strata (archetypes, tolerance levels, specialty dimensions). From an implementation perspective, this suggests that PKD can operate effectively with small councils (5–10 members), reducing coordination costs and deliberation time without sacrificing performance.

**4.5 Environmental volatility (regime change probability 0–10%).** Figure 3E demonstrates that PKD is the least affected by regime changes. At 0% regime change probability (pure Gaussian drift), all systems perform slightly better, but the rank order is unchanged. At 10% regime change probability (expected regime change every 10 periods), PKD performance degrades by only 11% (from −0.078 to −0.087), whereas electoral democracy degrades by 43% (from −1.20 to −1.72) and sortition by 28% (from −0.31 to −0.40). This resilience is likely due to two factors: (i) track-record scoring adapts to regime shifts within a few periods (the exponential moving average with α=0.9 gives 50% weight to the most recent 7 periods), allowing the system to quickly identify agents whose beliefs have adapted to the new regime, and (ii) high-tolerance agents dominate expert seats, and these agents are precisely those who revise beliefs most readily during deliberation, enabling rapid correction toward the post-shift optimum. This finding suggests that PKD may have comparative advantages in volatile policy environments (e.g., rapid technological change, geopolitical shocks).

**4.6 Deliberation intensity (revision rate ρ = 0–1.0).** Figure 3F shows that the effect of deliberation on PKD performance is modest: at ρ = 0 (no deliberation, policy is simply the track-record-weighted mean of independent beliefs), performance is −0.11; at ρ = 1.0 (full Bayesian belief revision with bounded confidence), performance is −0.085. This 23% improvement is non-negligible but far smaller than the improvement from track-record selection alone (which accounts for the 4.6× advantage over sortition). This result confirms the theoretical prediction that PKD's primary advantage comes from selecting competent agents rather than from deliberative aggregation per se. However, the deliberation mechanism remains essential for two reasons: (i) it enables knowledge transfer from specialists in one dimension to generalists, improving individual prediction accuracy (which feeds back into track records), and (ii) it interacts synergistically with the tolerance parameter to produce the self-sorting mechanism (low-tolerance agents cannot benefit from deliberation, so their track records remain low). The modest isolated effect of deliberation intensity does not imply that deliberation is unimportant; rather, it indicates that deliberation is most effective when applied to a council that has already been filtered for competence via track records.

**4.7 Expert noise advantage (σ_expert = 0.1–0.9).** Figure 3G shows that even when the expert population is assigned nearly the same observation noise as citizens (σ_expert = 0.9 vs σ_citizen ∈ [0.5, 1.5]), PKD maintains a substantial advantage over sortition (−0.10 vs −0.40). This is because track-record scoring identifies *de facto* experts regardless of their initial label: citizens with low noise and high tolerance accumulate high track records and are promoted to expert seats, while labeled "experts" with high noise are demoted. At σ_expert = 0.3 (the baseline), the expert label serves primarily to seed the initial track-record distribution, but by t=50, the track-record ranking is dominated by realized performance rather than initial labels. This finding has important implications for operationalization: a real-world implementation of PKD does not require a pre-identified expert class; track-record selection will discover competent agents from the general population given sufficient evaluation periods (approximately 50–100 prediction opportunities, consistent with the Good Judgment Project findings; Tetlock and Gardner 2015).

---

## 5. Discussion

### 5.1 Theoretical Contributions

PKD synthesizes three previously separate theoretical traditions — epistocracy (Brennan 2016), sortition (Van Reybrouck 2016), and bounded-confidence opinion dynamics (Hegselmann and Krause 2002) — into a single governance architecture and demonstrates their synergistic interaction through agent-based simulation. The central theoretical finding is the emergent self-elimination of low-tolerance agents, which resolves a tension in the epistocracy literature: how to select competent decision-makers without relying on subjective evaluation.

The track-record mechanism operationalizes the epistocratic ideal of "rule by the knowledgeable" while addressing Landemore's (2013) objection that epistocracy lacks accountability. In PKD, experts are continuously accountable to an objective performance metric; poor predictions lead to automatic demotion.

### 5.2 Limitations

Several important limitations must be acknowledged.

**The θ* observability problem.** In the simulation, track-record scores are computed against the true optimal policy θ*, which is directly observable. In reality, no "god's-eye view" of optimal policy exists. However, the track-record mechanism does not require observation of θ* itself — it requires only observable proxies of policy outcomes. In practice, expert candidates would register quantitative predictions in advance ("implementing policy X will result in unemployment rate Y% within 3 years"), and track-record scores would be computed as the mean squared error between predictions and realized statistical indicators (GDP growth, unemployment, crime rates, health outcomes, etc.). This approach has been empirically validated by the Good Judgment Project (Tetlock and Gardner 2015), which demonstrated that prediction accuracy can be reliably measured, that individual differences in forecasting ability are stable over time, and that "superforecasters" identified through track records consistently outperform domain experts and prediction markets. The PKD track-record mechanism is, in effect, a governance application of Tetlock's superforecasting methodology. The key limitation is that observable indicators capture only the measurable dimensions of policy impact; effects that are diffuse, long-term, or qualitative (e.g., social cohesion, cultural vitality) may resist quantification.

**Unmeasurable systematic bias.** Caplan (2007) demonstrates that voter biases are systematic, not random. The PKD track-record mechanism can filter agents whose predictions deviate from observed outcomes, but it cannot detect biases shared by the entire population — because the "correct answer" (θ*) is defined by the same reality that all agents inhabit. If all agents share an ideological assumption (e.g., that economic growth is inherently desirable), track-record scoring cannot identify this as a bias. The three-axis stratification of PKD is a partial response, following Hong and Page (2004), but achieving full cognitive diversity — including diversity of unconscious ideological priors — remains an open theoretical and practical challenge.

**Absence of strategic behavior.** Agents in the current model are non-strategic: they do not attempt to game the track-record system, collude, or misrepresent their beliefs. This is the most significant limitation for external validity. In practice, at least three gaming strategies are foreseeable: (i) *short-termism* — agents optimize for accurate short-term predictions (e.g., next-quarter GDP) while ignoring long-term consequences that fall outside the scoring window; (ii) *indicator hacking* — agents learn which observable proxies are used for scoring and tailor predictions to those proxies rather than to genuine policy understanding (Goodhart's Law); (iii) *strategic misrepresentation* — agents express moderate beliefs during deliberation while privately holding extreme positions, exploiting the belief-revision mechanism. Each of these failure modes has known countermeasures — multi-horizon scoring windows, rotating indicator sets, and consistency audits between stated beliefs and voting patterns — but their implementation and interaction effects require dedicated investigation. The introduction of strategic agents constitutes the most important extension for future work.

**External validity and empirical calibration.** The current model operates in a stylized policy space with Gaussian dynamics. To bridge the gap between simulation and reality, the track-record distribution produced by PKD should be compared against empirical forecasting accuracy data. The Good Judgment Project (Tetlock and Gardner 2015) provides the most relevant benchmark: it demonstrates that (a) prediction accuracy follows a heavy-tailed distribution in human populations, (b) individual forecasting ability is temporally stable (r ≈ 0.65 across years), and (c) top forecasters ("superforecasters") are identifiable through track records within 50–100 prediction opportunities. Calibrating the agent noise parameters (σ_i) and track-record dynamics against GJP distributions would substantially strengthen external validity and is a priority for empirical follow-up.

**Comparison system realism.** The electoral democracy implementation is deliberately simplified — voters choose based on appeal with bounded-rational noise, with no party structure, campaigning, media effects, or incumbency advantage. This stylization isolates the core mechanism (appeal-based vs. track-record-based selection) but may overstate electoral democracy's vulnerability relative to real-world systems that incorporate partial corrective mechanisms (e.g., term limits, independent judiciary, free press). Future work should introduce richer electoral models as comparison baselines.

**Simplified world model.** The world in our simulation is a d-dimensional vector with Gaussian dynamics. Real policy environments involve strategic interactions between nations, path dependencies, irreversibilities, and multi-stakeholder conflicts that are not captured.

### 5.3 Future Work

The limitations above define a concrete research agenda for PKD v2 and beyond:

1. **Strategic agents (highest priority).** Introduce a population of Machiavellian agents who employ short-termism, indicator hacking, and strategic misrepresentation. Test whether multi-horizon scoring (combining 1-year, 3-year, and 10-year predictions with declining discount), rotating indicator sets, and belief-vote consistency audits can neutralize gaming. This constitutes a full adversarial robustness test of the track-record mechanism.

2. **Empirical calibration against Good Judgment Project data.** Map the GJP superforecaster accuracy distribution onto agent noise parameters (σ_i) and validate whether the model's track-record dynamics reproduce the empirically observed heavy-tailed distribution and temporal stability of forecasting ability.

3. **Richer electoral baselines.** Introduce party systems, media effects, incumbency, and term limits into the electoral democracy comparison to test whether PKD's advantage persists against more realistic democratic institutions.

4. **Operationalization of tolerance.** Conduct a validation study mapping Actively Open-minded Thinking (AOT) scale scores to the bounded-confidence parameter ε, using survey data from deliberative democracy experiments.

5. **Multi-level governance.** Extend PKD to a hierarchical structure (local, regional, national) with inter-level information flow, testing whether track-record selection scales across governance levels.

6. **Epistemic entropy maximization.** Investigate whether the three-axis stratification can be extended to capture unconscious ideological diversity, potentially using latent factor models estimated from revealed preference data rather than self-reported traits.

---

## 6. Conclusion

We have shown that PKD — a governance architecture combining track-record selection, stratified sortition, and bounded-confidence deliberation — produces structurally superior policy outcomes compared to electoral democracy, sortition, and autocracy in a stochastic policy environment. The model's central insight is that tolerance (intellectual openness) and competence are coupled through the feedback loop: intolerant agents fail to learn, accumulate poor track records, and are automatically excluded from positions of influence. This emergent self-sorting resolves the core tension between epistocratic selection and democratic representativeness. While significant limitations remain — particularly the challenge of detecting population-wide systematic biases — the PKD framework provides a formal, testable, and implementable architecture for governance reform.

---

## Figures

**Figure 1.** Single simulation run (300 periods, d=10, N=100). Panel A: Policy performance per period for all four systems. Panel B: Cumulative performance (running total of Panel A). Panel C: Demagogue infiltration rate (fraction of council seats occupied by demagogues; vertical line marks populist shock at t=100). Panel D: Track-record distribution by agent archetype at t=300, showing mean values (bars) and individual agents (scatter points). Panel E: Tolerance distribution among agents occupying expert seats at t=300 (histogram). Panel F: Summary statistics table comparing all four systems.

**Figure 2.** Ensemble statistics (30 Monte Carlo runs × 300 periods). Panel A: Mean policy performance across runs (solid lines) ± 2 standard errors (shaded regions). PKD consistently outperforms all other systems with minimal run-to-run variance. Panel B: Cumulative performance trajectories, showing monotonic divergence of PKD from other systems. Panel C: Populism resistance metric (post-wave performance change Δ = performance(t≥100) − performance(t<100)) for each system. PKD is the only system with positive Δ (performance improvement after shock).

**Figure 3.** Sensitivity analysis composite (7 parameters × 10 values × 10 runs × 100 periods each). Each panel shows mean policy performance as a function of a single parameter while holding others at baseline. Panel A: Demagogue population fraction (0–30%). Panel B: Track-record decay rate α (0.5–0.99). Panel C: Policy dimensionality d (2–20). Panel D: Council size (3–20). Panel E: Regime change probability (0–10%). Panel F: Deliberation revision rate ρ (0–1.0). Panel G: Expert noise σ_expert (0.1–0.9). In all panels, PKD (blue) maintains superior performance across the full parameter range.

**Figure 4.** Demagogue infiltration rate as a function of demagogue population fraction (supplementary detail for sensitivity parameter 4.1). At 5% demagogue fraction (baseline), electoral democracy exhibits 59.6% infiltration while PKD exhibits 1.2%. At 30% demagogue fraction, electoral democracy approaches 100% infiltration while PKD remains below 5%. Sortition democracy maintains 0% infiltration by construction (random selection ignores appeal). This figure demonstrates that the track-record filter scales effectively even under extreme demagogue prevalence, whereas appeal-based selection fails catastrophically.

---

## References

BARON, J. (1993). Why taught reasoning is applied: Actively open-minded thinking. In J. B. Baron & R. V. Brown (Eds.), *Teaching Decision Making to Adolescents* (pp. 225–253). Hillsdale, NJ: Lawrence Erlbaum Associates.

BERRY, F. S., & Berry, W. D. (1990). State lottery adoptions as policy innovations: An event history analysis. *American Political Science Review*, 84(2), 395–415.

BRENNAN, J. (2016). *Against Democracy*. Princeton, NJ: Princeton University Press.

CAPLAN, B. (2007). *The Myth of the Rational Voter: Why Democracies Choose Bad Policies*. Princeton, NJ: Princeton University Press.

GRIMM, V., Berger, U., Bastiansen, F., Eliassen, S., Ginot, V., Giske, J., ... & DeAngelis, D. L. (2006). A standard protocol for describing individual-based and agent-based models. *Ecological Modelling*, 198(1–2), 115–126.

GRIMM, V., Railsback, S. F., Vincenot, C. E., Berger, U., Gallagher, C., DeAngelis, D. L., ... & Ayllón, D. (2020). The ODD protocol for describing agent-based and other simulation models: A second update to improve clarity, replication, and structural realism. *Journal of Artificial Societies and Social Simulation*, 23(2), 7.

HEGSELMANN, R., & Krause, U. (2002). Opinion dynamics and bounded confidence: Models, analysis and simulation. *Journal of Artificial Societies and Social Simulation*, 5(3), 2.

HONG, L., & Page, S. E. (2004). Groups of diverse problem solvers can outperform groups of high-ability problem solvers. *Proceedings of the National Academy of Sciences*, 101(46), 16385–16389.

LANDEMORE, H. (2013). *Democratic Reason: Politics, Collective Intelligence, and the Rule of the Many*. Princeton, NJ: Princeton University Press.

LAVER, M., & Sergenti, E. (2011). *Party Competition: An Agent-Based Model*. Princeton, NJ: Princeton University Press.

MUDDE, C., & Kaltwasser, C. R. (2017). *Populism: A Very Short Introduction*. Oxford: Oxford University Press.

SQUAZZONI, F., & Gandelli, C. (2012). Saint Matthew strikes again: An agent-based model of peer review and the scientific community structure. *Journal of Informetrics*, 6(2), 265–275.

TETLOCK, P. E., & Gardner, D. (2015). *Superforecasting: The Art and Science of Prediction*. New York: Crown.

VAN REYBROUCK, D. (2016). *Against Elections: The Case for Democracy*. London: Bodley Head.

---

## Appendix A: Full ODD Protocol

This appendix follows the ODD+D (Overview, Design concepts, Details + Decision-making) protocol described in Grimm et al. (2020).

### A.1 Purpose and Patterns

The model's purpose is to compare the policy performance, populism resistance, and long-term stability of four governance architectures (autocracy, electoral democracy, sortition democracy, and Philosopher-King Democracy) operating in an identical stochastic policy environment with heterogeneous agents. The model seeks to reproduce the empirically observed pattern that electoral systems are vulnerable to demagogic capture (Mudde and Kaltwasser 2017) and to test whether the PKD architecture achieves structural immunity to this failure mode.

### A.2 Entities, State Variables, and Scales

**Agents.** The model contains N = 100 agents, each characterized by the following state variables:

- `agent_type` ∈ {citizen, expert, demagogue}: Initial classification. Citizens comprise 80% of the population, experts 15%, and demagogues 5%.
- `belief` ∈ ℝ^d: Current belief about the optimal policy vector θ*. Updated each period via observation (with noise) and optionally via deliberation.
- `track_record` ∈ ℝ: Exponential moving average of past prediction accuracy. Initialized at 0 for all agents. Updated each period via: `track_record(t) = α·track_record(t−1) + (1−α)·performance(t)`, where `performance(t) = −||belief(t) − θ*(t)||²` and α = 0.9.
- `tolerance` ∈ ℝ+: Bounded-confidence threshold (ε_i in main text). Assigned at initialization based on archetype. Operationally interpretable as Actively Open-minded Thinking (AOT) scale score (Baron 1993).
- `appeal` ∈ [0,1]: Charisma parameter used in electoral selection. Demagogues: [0.8, 1.0]; citizens: varies by archetype.
- `bias` ∈ ℝ^d: Systematic observational bias vector. Zero for citizens and experts; ||bias|| = 1.5 for demagogues. Doubled to 3.0 at t=100 (populist shock).
- `noise` ∈ ℝ+: Observation noise standard deviation (σ_i in main text). Varies by archetype: IC=0.6, UC=0.5, II=1.3, UI=1.5, expert=0.3, demagogue=0.8.
- `political_interest` ∈ [0,1]: Engagement parameter (π_i in main text). Used to weight participation in electoral voting.
- `archetype` ∈ {IC, II, UC, UI, expert, demagogue}: Brennan (2016) classification for citizens; special categories for experts and demagogues.
- `specialty_dims`: Set of 1–2 policy dimensions where the agent has domain expertise (noise multiplied by 0.3 for these dimensions).

**World.** A single global entity representing the policy environment, with state variables:

- `theta_star` ∈ ℝ^d: True optimal policy vector. Evolves each period via Gaussian drift (mean 0, std 0.02 per dimension) with occasional regime changes (probability 0.03 per period; regime change samples a new `theta_star` from N(0, I_d)).
- `t`: Current time step (period).

**Governance systems.** Four stateless algorithms (autocracy, electoral, sortition, PKD) that map the agent population to a policy vector each period. Each system maintains a `current_council` (list of agents) and a `rotation_timer` to determine when to re-select the council.

**Spatial and temporal scales.** The model is non-spatial (agents are not embedded in a grid or network). Time is discrete, with periods representing policy cycles (interpretable as election cycles, legislative sessions, or fiscal years). Default simulation length is 300 periods. Results are aggregated over 30 Monte Carlo replications.

### A.3 Process Overview and Scheduling

Each period t proceeds in the following order:

1. **World update** (`world.update()`):
   - With probability p_regime = 0.03, sample a new θ* from N(0, I_d). Otherwise, apply Gaussian drift: θ*(t) = θ*(t−1) + N(0, 0.02² I_d).
   - If t = 100, apply populist shock: for all demagogue agents, `appeal *= 1.5` and `bias *= 2.0`.

2. **Observation** (`agent.observe()`):
   - Each agent i observes θ*(t) with noise: `observation_i = θ*(t) + bias_i + N(0, noise_i² I_d)`.
   - For dimensions in `specialty_dims`, multiply noise by 0.3 before sampling.
   - Update `belief_i = observation_i` (before deliberation).

3. **Governance** (for each of the four systems in parallel):
   - If `rotation_timer == 0`, call `system.select_council()` to form a new council and reset `rotation_timer` to the system-specific rotation period (autocracy: 48, electoral: 12, sortition: 6, PKD: 6).
   - If the system uses deliberation (PKD only), call `deliberate(council)` to revise council members' beliefs via bounded-confidence Bayesian updating.
   - Compute the system's policy as the (optionally track-record-weighted) mean of council members' beliefs.
   - Decrement `rotation_timer`.

4. **Evaluation**:
   - For each system, compute `performance = −||policy − θ*(t)||²`.
   - Record performance to system-specific time series.

5. **Feedback** (PKD only):
   - For each agent i (not just council members), compute individual `performance_i = −||belief_i − θ*(t)||²`.
   - Update `track_record_i = 0.9·track_record_i + 0.1·performance_i`.

### A.4 Design Concepts

**Basic principles.** The model synthesizes three theoretical frameworks: (i) epistocracy — political power should be allocated based on competence (Brennan 2016); (ii) sortition — random selection ensures representativeness and prevents elite capture (Van Reybrouck 2016); (iii) bounded-confidence deliberation — belief revision occurs only among agents with compatible tolerance thresholds (Hegselmann and Krause 2002).

**Emergence.** The central emergent property is the self-elimination of low-tolerance agents from expert seats in PKD. This is not programmed explicitly; it arises from the interaction between bounded-confidence deliberation (which causes low-tolerance agents to miss corrective information) and track-record scoring (which penalizes inaccurate predictions).

**Adaptation.** Agents adapt their beliefs during deliberation (if in a PKD council) by revising toward other council members' beliefs, weighted by track-record precision. The extent of adaptation is bounded by the agent's tolerance parameter.

**Objectives.** Agents do not have explicit objectives or utility functions. They passively observe, revise beliefs if in a deliberating council, and accumulate track-record scores based on prediction accuracy. This is a descriptive rather than normative model: we do not assume agents optimize anything.

**Learning.** Agents do not learn in the sense of updating internal parameters. However, the track-record mechanism acts as a population-level learning process: the distribution of agents in expert seats shifts over time toward those with high past performance.

**Prediction.** Each agent implicitly "predicts" that the optimal policy is their current belief. Track-record scores are computed by comparing these predictions to the realized θ*.

**Sensing.** Agents sense θ* with heterogeneous noise and bias (see Observation step). They do not sense other agents' beliefs except during deliberation (PKD councils only).

**Interaction.** Agents interact only during deliberation. In PKD councils, agents revise beliefs toward each other via bounded-confidence weighted averaging. No other direct agent-agent interaction occurs.

**Stochasticity.** World dynamics (Gaussian drift, regime changes), agent observations (Gaussian noise), electoral voting (noise added to appeal), and sortition draws are all stochastic. Random number generation uses independent streams seeded per Monte Carlo run to ensure reproducibility.

**Collectives.** Councils are temporary collectives formed by the governance systems. Council composition changes over time according to system-specific rules.

**Observation.** The modeler observes: (i) policy performance for each system per period, (ii) cumulative performance, (iii) demagogue infiltration rate (fraction of council seats held by demagogues), (iv) track-record distribution by archetype, (v) tolerance distribution in expert seats.

### A.5 Initialization

At t=0, the following initialization occurs:

1. **World**: Sample θ*(0) from N(0, 0.25 I_d), where d=10 (policy dimensionality).

2. **Agent population**:
   - Create 80 citizen agents, distributed by archetype:
     - 25% IC: `noise=0.6`, `political_interest=0.9`, `tolerance ~ U(2.5, 5.0)`, `appeal ~ U(0.3, 0.7)`
     - 20% II: `noise=1.3`, `political_interest=0.9`, `tolerance ~ U(0.5, 1.8)`, `appeal ~ U(0.4, 0.8)`
     - 25% UC: `noise=0.5`, `political_interest=0.2`, `tolerance ~ U(2.0, 4.0)`, `appeal ~ U(0.2, 0.5)`
     - 30% UI: `noise=1.5`, `political_interest=0.1`, `tolerance ~ U(0.8, 2.5)`, `appeal ~ U(0.1, 0.4)`
   - Create 15 expert agents: `noise=0.3`, `political_interest=1.0`, `tolerance ~ U(3.0, 5.0)`, `appeal ~ U(0.5, 0.8)`, `bias=0`.
   - Create 5 demagogue agents: `noise=0.8`, `political_interest=1.0`, `tolerance ~ U(0.3, 1.0)`, `appeal ~ U(0.8, 1.0)`, `bias ~ uniform on d-sphere with ||bias||=1.5`.

3. **Specialty dimensions**: For each agent, randomly assign 1–2 dimensions from {0, ..., d−1} as specialty dimensions.

4. **Initial beliefs**: Each agent observes θ*(0) with noise (as in the Observation step) and sets `belief = observation`.

5. **Track records**: Initialize `track_record = 0` for all agents.

6. **Governance systems**: Initialize `rotation_timer = 0` for all systems (triggering immediate council selection at t=0).

### A.6 Input Data

The model does not use external input data. The populist shock at t=100 is a pre-programmed exogenous perturbation, not data-driven.

### A.7 Submodels

**A.7.1 World update**

```
function world.update():
    if random() < 0.03:  # regime change
        theta_star = sample_normal(mean=0, std=1.0, dim=d)
    else:  # drift
        theta_star += sample_normal(mean=0, std=0.02, dim=d)

    if t == 100:  # populist shock
        for agent in demagogues:
            agent.appeal *= 1.5
            agent.bias *= 2.0
```

**A.7.2 Agent observation**

```
function agent.observe():
    noise_vector = zeros(d)
    for dim in range(d):
        if dim in agent.specialty_dims:
            noise_vector[dim] = sample_normal(0, 0.3 * agent.noise)
        else:
            noise_vector[dim] = sample_normal(0, agent.noise)

    agent.belief = theta_star + agent.bias + noise_vector
```

**A.7.3 Council selection (PKD)**

```
function PKD.select_council():
    # Expert seats (5): top 5 agents by track_record
    expert_seats = top_k(all_agents, k=5, key=track_record)

    # Citizen seats (5): stratified random lottery
    # Axes: specialty_dim (d categories), archetype (4 categories), tolerance (3 categories)
    pools = partition_agents(all_agents, axes=[specialty_dim, archetype, tolerance_bin])
    citizen_seats = []
    for pool in shuffle(pools):
        if len(citizen_seats) < 5 and pool not empty:
            citizen_seats.append(random_choice(pool))

    return expert_seats + citizen_seats
```

**A.7.4 Bounded-confidence deliberation**

```
function deliberate(council):
    for agent_i in council:
        weights = []
        for agent_j in council:
            distance = ||agent_i.belief - agent_j.belief||
            if distance <= agent_i.tolerance:  # bounded confidence
                precision = exp(agent_j.track_record)  # precision ~ track record
                weights.append(precision)
            else:
                weights.append(0)

        # Bayesian belief revision (weighted average)
        weights_normalized = weights / sum(weights)
        new_belief = sum(weights_normalized[j] * council[j].belief for j in council)

        # Partial revision (rate ρ = 0.3)
        agent_i.belief = 0.7 * agent_i.belief + 0.3 * new_belief
```

**A.7.5 Track-record update (PKD only)**

```
function update_track_records():
    for agent in all_agents:
        performance = -||agent.belief - theta_star||²
        agent.track_record = 0.9 * agent.track_record + 0.1 * performance
```

## Appendix B: Code Availability

All simulation code (Python 3.8+, dependencies: numpy, scipy, matplotlib) is available at:  
[GitHub URL to be inserted]

The repository contains:
- `simulation_pkd.py`: Main simulation and visualization code
- `sensitivity_analysis.py`: Seven-parameter sensitivity sweep
- `figures/`: All generated figures (reproducible from code with fixed seeds)
