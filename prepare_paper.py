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
'component_results':f"Ten record seats yield error {interval(est('record_only_10'))}, while baseline PKD increases coverage from {pct('record_only_10')} to {pct()}. The hybrid's error is {(mean()/mean('record_only_10')-1)*100:.1f}% higher than that of ten record seats, a relative increase in error rather than a welfare percentage. Removing deliberation changes error by {interval(contrast('no_deliberation'),6)}: a small reduction, about {100*abs(contrast('no_deliberation')['mean'])/mean():.2f}% of baseline error. It does not support an accuracy benefit of this deliberation operator. Ten lottery seats with score weighting give error {interval(est('lottery_only_10'))}; using equal final policy weights in the hybrid gives {interval(est('equal_weights'))}. Both record-based composition and final weighting matter. A uniform lottery changes error by {interval(contrast('uniform_lottery'))} and lowers coverage to {pct('uniform_lottery')}. Perfect type screening reduces labeled-demagogue occupancy but raises error to {fmt(mean('screened_lottery'))}; excluding low-noise non-citizens is not automatically beneficial. Freezing all records at period 100 changes PKD error by {interval(contrast('frozen_after_100'))}, consistent with little additional benefit of continued updating in this fixed-ability setting.",
'election_results':f"With a clean public record channel, the election's error falls from {interval(est('election_weight_0',SYSTEM_ELECTION))} at record weight zero to {interval(est('election_weight_0.75',SYSTEM_ELECTION))} at weight 0.75. At weight one it is {interval(est('election_weight_1',SYSTEM_ELECTION))}; the five-point sweep is not strictly monotonic. Even at weight one, the ordinary election retains random utility noise and differs in aggregation and schedule, so it need not coincide with direct record selection. At record weight 0.75, information error of 2 raises election error to {fmt(mean('electoral_information_noise_2',SYSTEM_ELECTION))}, and campaign contamination of 2 raises it to {fmt(mean('electoral_media_amplification_2',SYSTEM_ELECTION))}.",
'matched_results':f"The full-period paired election-minus-record-selection error difference is {interval(contrast('matched_record_selection','election'))}. After the first six periods, the largest absolute period-level difference across all 30 runs is below 10⁻¹², consistent with floating-point rounding.",
'scoring_results':f"At indicator-noise standard deviations 0.5, 1 and 2, PKD errors are {fmt(mean('proxy_noise_0.5'))}, {fmt(mean('proxy_noise_1'))} and {fmt(mean('proxy_noise_2'))}, respectively. Delays of 3, 12 and 24 periods yield {fmt(mean('feedback_delay_3'))}, {fmt(mean('feedback_delay_12'))} and {fmt(mean('feedback_delay_24'))}. Scoring only one coordinate gives error {fmt(mean('scored_dimensions_1'))}, while three and five coordinates give {fmt(mean('scored_dimensions_3'))} and {fmt(mean('scored_dimensions_5'))}. This restricted grid establishes sensitivity to feedback quality; it does not identify a universal threshold at which PKD fails.",
'gaming_results':f"Independent and coordinated herding raise PKD error to {fmt(mean('independent_herding'))} and {fmt(mean('coordinated_herding'))}, and labeled-agent occupancy to {pct('independent_herding',m='mean_demagogue_fraction')} and {pct('coordinated_herding',m='mean_demagogue_fraction')}. Copying a perfect current indicator produces low error ({fmt(mean('indicator_targeting_0'))}) despite occupancy of {pct('indicator_targeting_0',m='mean_demagogue_fraction')}. Copying noisy current indicators instead gives error {fmt(mean('indicator_targeting_0.5'))} at noise 0.5 and {fmt(mean('indicator_targeting_1'))} at noise 1, with approximately half of the council occupied by labeled agents. Restricting copying to the previous period yields errors {fmt(mean('indicator_targeting_firewall_0.5'))} and {fmt(mean('indicator_targeting_firewall_1'))} for those noisy indicators. However, lagged copying of a perfect indicator still gives error {fmt(mean('indicator_targeting_firewall_0'))} and occupancy {pct('indicator_targeting_firewall_0',m='mean_demagogue_fraction')}. A one-period separation is therefore not a general guarantee against gaming.",
'shock_results':f"The paired shock-induced increase in PKD error is {interval(contrast(SYSTEM_PKD,'shock'),7)}, compared with {interval(contrast(SYSTEM_SORTITION,'shock'))} for the random council, {interval(contrast(SYSTEM_ELECTION,'shock'))} for the default election and {interval(contrast(SYSTEM_APPEAL,'shock'))} for appeal ranking. The PKD effect is small in absolute units under this specific parameter shock. It cannot be interpreted as resistance to political shocks generally, and the positive effect is not evidence that the shock improves PKD.",
'sensitivity_results':f"Raising the initially low-noise type's standard deviation to 0.6 and 0.9 raises PKD error to {fmt(mean('expert_noise_0.6'))} and {fmt(mean('expert_noise_0.9'))}. Raising the labeled-demagogue fraction to 15% and 30% yields error {fmt(mean('demagogue_fraction_0.15'))} and {fmt(mean('demagogue_fraction_0.3'))}; occupancy rises to {pct('demagogue_fraction_0.15',m='mean_demagogue_fraction')} and {pct('demagogue_fraction_0.3',m='mean_demagogue_fraction')}. Low error therefore does not imply universal exclusion of that type. Record-decay values 0.5 and 0.99 yield errors {fmt(mean('track_decay_0.5'))} and {fmt(mean('track_decay_0.99'))}. Regime-change probabilities 0 and 0.1 leave honest-model errors unchanged to numerical precision, as predicted by the translation invariance in Section 3. This is not a test passed for real-world adaptation. Dimension and bias changes are reported in Table B2 without treating the resulting ranks as a global robustness guarantee.",
'interaction_results':f"The four PKD errors are {', '.join(fmt(mean(c)) for c in ['interaction_noise_0_delay_0','interaction_noise_0_delay_12','interaction_noise_1_delay_0','interaction_noise_1_delay_12'])}, respectively (ordered as noise/delay 0/0, 0/12, 1/0 and 1/12)."
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
def expand(match):
    token=match.group(1)
    if token=='REFERENCES':return '\n\n'.join(references)
    kind,key,*caption=token.split('|')
    if kind=='EQ':return '\n$$\n'+equations[key]+'\n$$\n'
    if kind=='FIG':return f'![{caption[0]}](../results/preprint_2026/analysis/{key}.png)\n\n'+caption[0]
    if kind=='TABLE':
        spec=tables[key];lines=[caption[0],'','| '+' | '.join(spec['headers'])+' |','| '+' | '.join(['---']*len(spec['headers']))+' |']
        lines.extend('| '+' | '.join(row)+' |' for row in spec['rows']);return '\n'.join(lines)
    raise ValueError(token)
(paper/'manuscript.md').write_text(re.sub(r'\[\[(.*?)\]\]',expand,text),encoding='utf-8')
print('Resolved claims, tables, and',len(references),'references')
