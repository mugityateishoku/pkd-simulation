"""Populate manuscript claims and tables directly from released estimates."""
from pathlib import Path
import json,re,csv,html
from simulation_pkd_v32 import *

root=Path('results/preprint_2026'); data=json.loads((root/'analysis/results.json').read_text())
manifest=json.loads((root/'study_manifest.json').read_text())
def est(c='baseline',s=SYSTEM_PKD,m='loss'):return data[c][s][m]
def mean(c='baseline',s=SYSTEM_PKD,m='loss'):return est(c,s,m)['mean']
def fmt(x,n=4):return f'{x:.{n}f}'
def interval(e,n=4):return f"{e['mean']:.{n}f} [{e['low']:.{n}f}, {e['high']:.{n}f}]"
def contrast(name,group='components'):return next(r for r in data['_paired'][group] if r.get('condition',r.get('system'))==name)
def pct(c='baseline',s=SYSTEM_PKD,m='mean_represented_population_share'):return f'{100*mean(c,s,m):.1f}%'

fields={
'pkd_loss':fmt(mean()),'sort_loss':fmt(mean(s=SYSTEM_SORTITION)),'elect_loss':fmt(mean(s=SYSTEM_ELECTION)),
'record10_loss':fmt(mean('record_only_10')),'pool_loss':fmt(mean(s=SYSTEM_POOL_SCORE)),
'delib_change':fmt(contrast('no_deliberation')['mean'],6),
'analytic_pool_loss':'0.087817','equal_pool_interval':interval(est(s=SYSTEM_POOL_EQUAL)),
'baseline_results':f"PKD's mean error is {interval(est())}, compared with {interval(est(s=SYSTEM_SORTITION))} for a random council of ten and {interval(est(s=SYSTEM_ELECTION))} for the default election. The unrestricted population mean achieves {interval(est(s=SYSTEM_POOL_EQUAL))}; using score weights for all agents lowers it further to {interval(est(s=SYSTEM_POOL_SCORE))}. Thus the hybrid council is not the most accurate aggregator among the tested mechanisms. Its stratum coverage is {pct()}, compared with {pct(s=SYSTEM_SORTITION)} for the random council and {pct(s=SYSTEM_ELECTION)} for the five-seat election. These comparisons confound council size unless size is explicitly matched.",
'component_results':f"Ten record seats yield error {interval(est('record_only_10'))}, while baseline PKD increases coverage from {pct('record_only_10')} to {pct()}. The hybrid's error is {(mean()/mean('record_only_10')-1)*100:.1f}% higher than that of ten record seats, a relative increase in error rather than a welfare percentage. Removing deliberation changes error by {interval(contrast('no_deliberation'),6)}: a small reduction, about {100*abs(contrast('no_deliberation')['mean'])/mean():.2f}% of baseline error. It does not support an accuracy benefit of this deliberation operator. Ten lottery seats with score weighting give error {interval(est('lottery_only_10'))}; using equal final policy weights in the hybrid gives {interval(est('equal_weights'))}. Both record-based composition and final weighting matter. A uniform lottery changes error by {interval(contrast('uniform_lottery'))} and lowers coverage to {pct('uniform_lottery')}. Perfect type screening reduces labeled-demagogue occupancy but raises error to {fmt(mean('screened_lottery'))}; excluding low-noise non-citizens is not automatically beneficial. Freezing all records at period 100 changes PKD error by {interval(contrast('frozen_after_100'))}, consistent with little additional benefit of continued updating under the largely stable observation traits.",
'election_results':f"With a clean public record channel, the election's error falls from {interval(est('election_weight_0',SYSTEM_ELECTION))} at record weight zero to {interval(est('election_weight_0.75',SYSTEM_ELECTION))} at weight 0.75. At weight one it is {interval(est('election_weight_1',SYSTEM_ELECTION))}; the five-point sweep is not strictly monotonic. Even at weight one, the ordinary election retains random utility noise and differs in aggregation and schedule, so it need not coincide with direct record selection. At record weight 0.75, information error of 2 raises election error to {fmt(mean('electoral_information_noise_2',SYSTEM_ELECTION))}, and campaign contamination of 2 raises it to {fmt(mean('electoral_media_amplification_2',SYSTEM_ELECTION))}.",
'matched_results':f"The full-period paired election-minus-record-selection error difference is {interval(contrast('matched_record_selection','election'))}. After the first six periods, the largest absolute period-level difference across all 30 runs is below 10⁻¹², consistent with floating-point rounding.",
'scoring_results':f"At indicator-noise standard deviations 0.5, 1 and 2, PKD errors are {fmt(mean('proxy_noise_0.5'))}, {fmt(mean('proxy_noise_1'))} and {fmt(mean('proxy_noise_2'))}, respectively. Delays of 3, 12 and 24 periods yield {fmt(mean('feedback_delay_3'))}, {fmt(mean('feedback_delay_12'))} and {fmt(mean('feedback_delay_24'))}. Scoring only one coordinate gives error {fmt(mean('scored_dimensions_1'))}, while three and five coordinates give {fmt(mean('scored_dimensions_3'))} and {fmt(mean('scored_dimensions_5'))}. This restricted grid establishes sensitivity to feedback quality; it does not identify a universal threshold at which PKD fails.",
'gaming_results':f"Independent and coordinated herding raise PKD error to {fmt(mean('independent_herding'))} and {fmt(mean('coordinated_herding'))}, and labeled-agent occupancy to {pct('independent_herding',m='mean_demagogue_fraction')} and {pct('coordinated_herding',m='mean_demagogue_fraction')}. Copying a perfect current indicator produces low error ({fmt(mean('indicator_targeting_0'))}) despite occupancy of {pct('indicator_targeting_0',m='mean_demagogue_fraction')}. Copying noisy current indicators instead gives error {fmt(mean('indicator_targeting_0.5'))} at noise 0.5 and {fmt(mean('indicator_targeting_1'))} at noise 1, with approximately half of the council occupied by labeled agents. Restricting copying to the previous period yields errors {fmt(mean('indicator_targeting_firewall_0.5'))} and {fmt(mean('indicator_targeting_firewall_1'))} for those noisy indicators. However, lagged copying of a perfect indicator still gives error {fmt(mean('indicator_targeting_firewall_0'))} and occupancy {pct('indicator_targeting_firewall_0',m='mean_demagogue_fraction')}. A one-period separation is therefore not a general guarantee against gaming.",
'shock_results':f"The paired shock-induced increase in PKD error is {interval(contrast(SYSTEM_PKD,'shock'),7)}, compared with {interval(contrast(SYSTEM_SORTITION,'shock'))} for the random council, {interval(contrast(SYSTEM_ELECTION,'shock'))} for the default election and {interval(contrast(SYSTEM_APPEAL,'shock'))} for appeal ranking. The PKD effect is small in absolute units under this specific parameter shock. It cannot be interpreted as resistance to political shocks generally, and the positive effect is not evidence that the shock improves PKD.",
'sensitivity_results':f"Raising the initially low-noise type's standard deviation to 0.6 and 0.9 raises PKD error to {fmt(mean('expert_noise_0.6'))} and {fmt(mean('expert_noise_0.9'))}. Raising the labeled-demagogue fraction to 15% and 30% yields error {fmt(mean('demagogue_fraction_0.15'))} and {fmt(mean('demagogue_fraction_0.3'))}; occupancy rises to {pct('demagogue_fraction_0.15',m='mean_demagogue_fraction')} and {pct('demagogue_fraction_0.3',m='mean_demagogue_fraction')}. Low error therefore does not imply universal exclusion of that type. Record-decay values 0.5 and 0.99 yield errors {fmt(mean('track_decay_0.5'))} and {fmt(mean('track_decay_0.99'))}. Regime-change probabilities 0 and 0.1 leave honest-model errors unchanged to numerical precision, as predicted by the translation invariance in Section 3. This is not a test passed for real-world adaptation. Dimension and bias changes are reported in Table B2 without treating the resulting ranks as a global robustness guarantee.",
'interaction_results':f"The four PKD errors are {', '.join(fmt(mean(c)) for c in ['interaction_noise_0_delay_0','interaction_noise_0_delay_12','interaction_noise_1_delay_0','interaction_noise_1_delay_12'])}, respectively (ordered as noise/delay 0/0, 0/12, 1/0 and 1/12)."
}
# October review: all new passages derive from deposited run-based estimates.
review=json.loads(Path('results/review_2026/archived_analysis/claims.json').read_text())
follow=json.loads(Path('results/review_2026/followup/analysis/results.json').read_text())
follow_manifest=json.loads(Path('results/review_2026/followup/manifest.json').read_text())
verification=json.loads(Path('results/review_2026/followup/verification.json').read_text())
def fe(c='baseline_observed',m='loss',window=None):
    return next(e for e in follow['window_estimates' if window else 'estimates']
                if e['condition']==c and e['metric']==m and (not window or e['window']==window))
def fc(first,second,m='loss'):
    return next(e for e in follow['paired_contrasts'] if e['first']==first and e['second']==second and e['metric']==m)
def scale(e,factor):return {k:v*factor if k in ('mean','low','high','mcse') else v for k,v in e.items()}
def percent_interval(e):return interval(scale(e,100),1)+'%'
def aw(c,start=30):return next(e for e in review['delay_windows'] if e['condition']==c and e['start_inclusive']==start)
def cw(c,start):return next(e for e in review['component_windows'] if e['condition']==c and e['start_inclusive']==start)
def paired_window(e):return {k:e['paired_vs_baseline_'+k] for k in ('mean','low','high')}
composition=next(e for e in review['matched_composition'] if e['metric']=='loss' and e['start_inclusive']==0)
coverage=next(e for e in review['matched_composition'] if e['metric']=='represented_population_share' and e['start_inclusive']==0)
fields['followup_abstract']=f"Lottery members hold 50% of baseline seats but receive {100*fe(m='effective_lottery_weight')['mean']:.1f}% of the realized input coefficients. With averaging disabled in both weighting conditions, equal input weights increase error while leaving membership unchanged."
fields['followup_design']="The council follow-up holds size at ten and varies record seats over 0, 2, 5, 8 and 10, crossed with equal or score-based final weights and with deliberation disabled. A replay of the original deliberating five-plus-five baseline is the eleventh condition. All conditions reuse the original 30 seeds and 300 periods, giving 330 executions and 99,000 PKD period records. Four configurations repeat September settings; these replays add influence observations rather than independent replication. The observer calls the original decision method, draws no random numbers, returns the original output unchanged and checks reconstruction using the coefficient vector in Section 3.4. At a fixed seat mix, weighting changes leave registered estimates, records and council selection unchanged in these honest-agent conditions. A manifest fixes the follow-up grid and source hashes before execution, after the exploratory question was chosen."
fields['component_results']=f"Ten record seats yield error {interval(est('record_only_10'))}, while baseline PKD has coverage {pct()} compared with {pct('record_only_10')} for ten record seats. Removing deliberation changes full-run error by {interval(contrast('no_deliberation'),6)}, about {100*abs(contrast('no_deliberation')['mean'])/mean():.2f}% of baseline error. That small reduction is concentrated during initialization: the paired difference over periods 30–299 is {interval(paired_window(cw('no_deliberation',30)),6)}, and over 90–299 is {interval(paired_window(cw('no_deliberation',90)),6)}. Thus no sustained accuracy improvement from removing this operator is established. Ten lottery seats with score weighting give error {interval(est('lottery_only_10'))}; equal final policy weights with the original deliberation retained give {interval(est('equal_weights'))}. This latter change leaves local neighborhood weights score-based. A uniform lottery changes error by {interval(contrast('uniform_lottery'))} and lowers coverage to {pct('uniform_lottery')}. Perfect type screening reduces labeled-demagogue occupancy but raises error to {fmt(mean('screened_lottery'))}. Freezing all records at period 100 changes error by {interval(contrast('frozen_after_100'))}, consistent with little additional benefit of continued updating under the largely stable observation traits."
fields['composition_matched_results']=f"A cleaner composition comparison disables deliberation in both ten-seat councils and retains score weighting. Replacing five record seats with five stratified lottery seats then increases mean error by {interval(composition)}, or {composition['relative_change_of_means_percent']:.1f}% relative to the record-only mean. It increases nominal stratum coverage by {interval(scale(coverage,100),2)} percentage points. This is a within-model accuracy–coverage tradeoff; the percentage error increase is not a welfare percentage."
fields['influence_results']=f"""In the original baseline, lottery members occupy five of ten seats but their registered estimates receive only {percent_interval(fe(m='effective_lottery_weight'))} of the realized input coefficients. Over periods 30–299 this share is {percent_interval(fe(m='effective_lottery_weight',window='periods_30_onward'))}. The equivalent input count is {interval(fe(m='effective_input_count'),2)}, compared with ten when every original input has equal weight. Across all 300 periods, {percent_interval(fe(m='ever_seated_population_fraction',window='all_periods'))} of agents are seated at least once, and {percent_interval(fe(m='ever_lottery_seated_population_fraction',window='all_periods'))} are seated through the lottery at least once. These finite-run fractions measure participation over time, not individual inclusion fairness.

With deliberation disabled and the same five-plus-five councils, score weighting gives error {interval(fe('record_05_score'))}, compared with {interval(fe('record_05_equal'))} for equal weighting. The paired score-minus-equal difference is {interval(fc('record_05_score','record_05_equal'))}. Equal weighting gives lottery estimates exactly 50% of total weight; nominal membership and stratum coverage are identical in the paired runs. The low-error hybrid therefore combines broader nominal membership with strongly unequal input weights in this population. Across the five tested seat mixes, more record seats reduce mean error and nominal coverage under both weighting rules. At eight record seats, the two lottery members receive only {percent_interval(fe('record_08_score','effective_lottery_weight'))} of the input weight under score weighting. These results do not identify an optimal allocation."""
fields['delay_window_results']=f"The full-run delay comparison mixes startup and subsequent operation. In the post hoc periods 30–299 window, baseline error is {fmt(aw('baseline')['mean'],6)}; delays 3, 12 and 24 have paired differences {interval(paired_window(aw('feedback_delay_3')),6)}, {interval(paired_window(aw('feedback_delay_12')),6)} and {interval(paired_window(aw('feedback_delay_24')),6)}. The periods 90–299 comparisons likewise have intervals spanning zero (deposited tables). The sizable full-run penalties are mainly initial costs of starting with zero records and delayed feedback. These estimates neither establish equivalence nor predict behavior under repeated, unanticipated changes in individual competence. Figure C1 separates the initial and later windows."
fields['scoring_results']=fields['scoring_results'].replace('This restricted grid establishes sensitivity to feedback quality; it does not identify a universal threshold at which PKD fails.','These are specification sensitivities: coordinate restriction changes score scale as well as information. The grid does not identify a universal failure threshold.')
fields['review_verification']=f"All 9,000 baseline PKD losses in the observer replay exactly match the September archive. Across all 99,000 observed decisions, the largest coordinate discrepancy between the returned policy and the reconstructed weighted inputs is {max(v['policy_reconstruction_max_gap'] for v in verification):.2g}. The model source hash remains unchanged. These checks support computational consistency; same-code, same-seed replay is not an independent replication. The archived-analysis tables report the duplicate-condition identity, startup and later windows, composition contrasts with deliberation held off, and dimension-normalized error. The follow-up tables report every declared seat mix and weighting rule, with full run summaries and period-level council identities and coefficients."
figure_paths={
    'review_influence':'results/review_2026/followup/analysis/figure_followup.png',
    'review_delay':'results/review_2026/archived_analysis/delay_initialization.png',
}

text=Path('paper_template.md').read_text(encoding='utf-8')
for key,value in fields.items():text=text.replace('{{'+key+'}}',value)
assert '{{' not in text
paper=Path('paper');paper.mkdir(exist_ok=True)
(paper/'manuscript_source.md').write_text(text,encoding='utf-8')
(paper/'claim_values.json').write_text(json.dumps(fields,indent=2),encoding='utf-8')

names={SYSTEM_PKD:'PKD',SYSTEM_SORTITION:'Random council of 10',SYSTEM_SORTITION_DELIBERATION:'Random + deliberation',SYSTEM_ELECTION:'Ballot election of 5',SYSTEM_APPEAL:'Appeal ranking of 5',SYSTEM_AUTOCRACY:'Random single ruler',SYSTEM_POOL_EQUAL:'All 100 equal mean',SYSTEM_POOL_SCORE:'All 100 score weighted'}
tables={}
tables['baseline']={'headers':['Mechanism','Error [95% interval]','Biased type seats','Coverage'], 'widths':[2.1,2.35,1.2,1.05], 'rows':[[name,interval(est(s=s)),pct(s=s,m='mean_demagogue_fraction'),pct(s=s)] for s,name in names.items()]}
tables['parameters']={'headers':['Quantity','Baseline value'], 'widths':[3.0,3.7], 'rows':[
['Population / dimensions','100 agents / 10 dimensions'],['Citizen / low-noise / biased counts','80 / 15 / 5'],['Citizen type counts','20 IC / 16 II / 20 UC / 24 UI'],['Observation noise SD by type','0.6 / 1.3 / 0.5 / 1.5 / 0.3 / 0.8'],['Specialty coordinates / noise multiplier','One or two / 0.3'],['Bias norm before / after period 100','1.5 / 3.0 for biased type only'],['State drift SD / redraw probability','0.02 / 0.03'],['Record decay / initial records','0.9 / zero'],['PKD record seats / lottery seats','5 / 5'],['PKD / sortition / election / ruler cycle','6 / 6 / 12 / 48 periods'],['Deliberation step size','0.3'],['Indicator noise / delay / scored dimensions','0 / 0 / 10'],['Election record weight / utility noise','0.25 / Gumbel scale 0.2'],['Election information noise / media multiplier','0.75 / 0.5'],['Runs / periods / shock time','30 / 300 / zero-based 100'],['All-agent score weights','Normalized exponential of prior records']]}
base=manifest['conditions']['baseline']
table_rows=[]
for i,(name,cfg) in enumerate(manifest['conditions'].items(),1):
    changes={k:v for k,v in cfg.items() if v!=base[k]}
    desc='; '.join(f'{k} = {v}' for k,v in changes.items()) or 'Baseline parameters in Table A1'
    table_rows.append([str(i),name.replace('_',' '),desc])
tables['conditions']={'headers':['ID','Condition','Changes from baseline'], 'widths':[.35,2.15,4.2], 'rows':table_rows}
prefixes=('expert_noise','track_decay','n_dim','regime_change','demagogue_bias','demagogue_fraction','interaction_')
tables['sensitivity']={'headers':['Condition','PKD error','Random council','Election error'],'widths':[3.0,1.25,1.25,1.2], 'rows':[[c.replace('_',' '),fmt(mean(c)),fmt(mean(c,SYSTEM_SORTITION)),fmt(mean(c,SYSTEM_ELECTION))] for c in manifest['conditions'] if c.startswith(prefixes)]}
follow_rows=[]
for c in follow_manifest['conditions']:
    cfg=follow_manifest['conditions'][c]
    label='Baseline replay' if c=='baseline_observed' else f"{cfg['n_expert_seats']} record + {cfg['n_citizen_seats']} lottery"
    follow_rows.append([label,'Score' if cfg['pkd_score_weighting'] else 'Equal',interval(fe(c)),percent_interval(fe(c,'effective_lottery_weight')),f"{100*fe(c,'represented_population_share')['mean']:.1f}%"])
tables['followup']={'headers':['Council','Weights','Error [95% interval]','Lottery input share [95% interval]','Coverage'],'widths':[1.45,.8,1.8,1.8,.85],'rows':follow_rows}

(paper/'tables.json').write_text(json.dumps(tables,indent=2),encoding='utf-8')

refs=json.loads(Path('references/crossref_metadata.json').read_text())
references=[]
for key,v in refs.items():
    au=[]
    for a in v.get('author',[]):
        initials=' '.join(x[0]+'.' for x in re.split(r'[\s-]+',a.get('given','')) if x)
        au.append(a.get('family','').replace('Degroot','DeGroot')+', '+initials)
    year={'Lorenz2010':2010}.get(key,v.get('published',{}).get('date-parts',[[0]])[0][0])
    title=html.unescape(re.sub('<[^>]+>','',v['title'][0]))
    journal=v.get('container-title',[''])
    journal=journal[0] if journal else v.get('publisher','')
    volume=v.get('volume',''); issue=v.get('issue',''); pages=v.get('page',v.get('article-number',''))
    punctuation='' if title.endswith(('!','?','.')) else '.'
    references.append('; '.join(au)+f' ({year}). {title}'+punctuation+' '+journal+(f', {volume}' if volume else '')+(f'({issue})' if issue else '')+(f', {pages}' if pages else '')+'. https://doi.org/'+v['DOI'])
references.extend([
'Brennan, J. (2016). Against Democracy. Princeton University Press. https://press.princeton.edu/books/hardcover/9780691162607/against-democracy',
'Hegselmann, R.; Krause, U. (2002). Opinion dynamics and bounded confidence: Models, analysis and simulation. Journal of Artificial Societies and Social Simulation, 5(3), 2. https://jasss.soc.surrey.ac.uk/5/3/2.html'
])
references.sort(key=str.casefold)
(paper/'references.json').write_text(json.dumps(references,indent=2),encoding='utf-8')
equations={
'1':r'x_i(t)=\theta(t)+b_i+\varepsilon_i(t),\qquad L_s(t)=\|p_s(t)-\theta(t)\|^2',
'2':r'R_i(t+1)=\alpha R_i(t)-(1-\alpha)\sum_{k=1}^{q}[x_{ik}(t)-y_k(t)]^2\quad(\delta=0)',
'3':r'w_i=\frac{e^{R_i}}{\sum_{j\in C}e^{R_j}},\qquad N_i=\{j\in C:\|x_j-x_i\|\le\tau_i\}',
'4':r'z_i=(1-\rho)x_i+\rho\frac{\sum_{j\in N_i}e^{R_j}x_j}{\sum_{j\in N_i}e^{R_j}},\qquad p=\sum_{i\in C}w_i z_i',
'5':r'\sum_{i\in C}w_i[(1-\rho)x_i+\rho p]=(1-\rho)p+\rho p=p',
'6':r'E\|\bar{x}-\theta\|^2=\|N^{-1}\sum_i b_i\|^2+N^{-2}\sum_i\mathrm{tr}(\Sigma_i)'}
equations['7']=r'v_j=(1-\rho)w_j+\rho\sum_{i\in C}w_i A_{ij},\qquad \sum_{j\in C}v_j=1'
def expand(match):
    token=match.group(1)
    if token=='REFERENCES':return '\n\n'.join(references)
    kind,key,*caption=token.split('|')
    if kind=='EQ':return '\n$$\n'+equations[key]+'\n$$\n'
    if kind=='FIG':return f"![{caption[0]}](../{figure_paths.get(key, 'results/preprint_2026/analysis/'+key+'.png')})\n\n"+caption[0]
    if kind=='TABLE':
        spec=tables[key];lines=[caption[0],'','| '+' | '.join(spec['headers'])+' |','| '+' | '.join(['---']*len(spec['headers']))+' |']
        lines.extend('| '+' | '.join(row)+' |' for row in spec['rows']);return '\n'.join(lines)
    raise ValueError(token)
(paper/'manuscript.md').write_text(re.sub(r'\[\[(.*?)\]\]',expand,text),encoding='utf-8')
print('Resolved claims, tables, and',len(references),'references')
