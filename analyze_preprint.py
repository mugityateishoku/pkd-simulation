"""Derive every preprint number and figure from independent run summaries."""
from pathlib import Path
import argparse, csv, json, math
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from simulation_pkd_v32 import *


def ci(values):
    x=np.asarray(values, dtype=float)
    m=float(x.mean()); se=float(x.std(ddof=1)/np.sqrt(len(x))) if len(x)>1 else 0.
    half=float(stats.t.ppf(.975,len(x)-1))*se if len(x)>1 else 0.
    return {'mean':m,'low':m-half,'high':m+half,'n':len(x),'mcse':se}


def analyze(root):
    manifest=json.loads((root/'study_manifest.json').read_text())
    runs={}
    for name in manifest['conditions']:
        with (root/'raw'/name/'run_summary.csv').open() as f:
            rows=list(csv.DictReader(f))
        groups={}
        for row in rows:
            groups.setdefault(row['system'],[]).append(row)
        runs[name]={s:sorted(v,key=lambda r:int(r['run'])) for s,v in groups.items()}
    def values(condition,system,metric='loss'):
        field='mean_performance' if metric=='loss' else metric
        a=np.array([float(r[field]) for r in runs[condition][system]])
        return -a if metric=='loss' else a
    def paired(c1,s1,c0='baseline',s0=SYSTEM_PKD,metric='loss'):
        return ci(values(c1,s1,metric)-values(c0,s0,metric))
    table=[]; summary={}
    for name, systems in runs.items():
        summary[name]={}
        for system in systems:
            metrics={m:ci(values(name,system,m)) for m in ['loss','mean_demagogue_fraction','mean_represented_population_share','mean_representation_js_divergence']}
            summary[name][system]=metrics
            table.append({'condition':name,'system':system,**{f'{m}_{k}':v for m,x in metrics.items() for k,v in x.items()}})
    out=root/'analysis'; out.mkdir(exist_ok=True)
    write_csv(out/'all_condition_estimates.csv',table)
    components=['no_deliberation','record_only_10','record_only_5','lottery_only_10','uniform_lottery','screened_lottery','equal_weights','frozen_after_100']
    component_rows=[{'condition':c,**paired(c,SYSTEM_PKD)} for c in components]
    write_csv(out/'component_paired_loss_changes.csv',component_rows)
    shock=[]
    for system in runs['baseline']:
        a=values('baseline',system,'post_minus_pre')
        b=values('shock_absent',system,'post_minus_pre')
        shock.append({'system':system,**ci(-a+b)})
    write_csv(out/'shock_paired_did_loss.csv',shock)
    elections=[]
    for c in runs:
        if c.startswith('election_') or c.startswith('electoral_') or c=='matched_record_selection':
            elections.append({'condition':c,**paired(c,SYSTEM_ELECTION,c,SYSTEM_PKD)})
    write_csv(out/'election_minus_pkd_loss.csv',elections)
    # A zero-record election is the information-sweep control, not baseline.
    gains=[]
    for w in [0.,.25,.5,.75,1.]:
        c=f'election_weight_{w:g}'
        gains.append({'weight':w,**paired(c,SYSTEM_ELECTION,'election_weight_0',SYSTEM_ELECTION)})
    write_csv(out/'election_weight_paired_changes.csv',gains)
    summary['_paired']={'components':component_rows,'shock':shock,'election':elections,'election_gain':gains}
    (out/'results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    plt.rcParams.update({'font.size':12,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':220})
    def save(fig,name):
        fig.tight_layout(); fig.savefig(out/(name+'.png'),bbox_inches='tight'); fig.savefig(out/(name+'.pdf'),bbox_inches='tight'); plt.close(fig)
    def errorplot(ax,labels,estimates,color='#176575'):
        means=np.array([x['mean'] for x in estimates]); low=np.array([x['low'] for x in estimates]); high=np.array([x['high'] for x in estimates])
        ax.errorbar(means,np.arange(len(labels)),xerr=[means-low,high-means],fmt='o',capsize=3,color=color)
        ax.set_yticks(np.arange(len(labels)),labels); ax.invert_yaxis(); ax.grid(axis='x',alpha=.2)
    baseline_systems=[SYSTEM_PKD,SYSTEM_SORTITION,SYSTEM_SORTITION_DELIBERATION,SYSTEM_ELECTION,SYSTEM_APPEAL,SYSTEM_AUTOCRACY,SYSTEM_POOL_EQUAL,SYSTEM_POOL_SCORE]
    labels=['PKD 5 record + 5 lottery','Random council of 10','Random council + deliberation','Ballot election of 5','Appeal ranking of 5','Random single ruler','All 100 equal mean','All 100 score weighted']
    fig,axes=plt.subplots(1,2,figsize=(10,4.4),gridspec_kw={'width_ratios':[1.6,1]})
    errorplot(axes[0],labels,[summary['baseline'][s]['loss'] for s in baseline_systems]); axes[0].set_xscale('log'); axes[0].set_xlabel('Mean squared Euclidean error (log scale)'); axes[0].set_title('A  Accuracy and unconstrained benchmarks')
    council=baseline_systems[:6]
    errorplot(axes[1],[l for l in ['PKD','Random council','Random + deliberation','Ballot election','Appeal ranking','Single ruler']],[summary['baseline'][s]['mean_represented_population_share'] for s in council], '#ae5837'); axes[1].set_xlabel('Population share in represented strata'); axes[1].set_title('B  Descriptive coverage')
    save(fig,'figure1_baseline')
    fig,axes=plt.subplots(1,2,figsize=(10,4.2))
    clabels=['No deliberation','10 record seats','5 record seats','10 lottery seats, weighted','Uniform lottery','Type screened lottery','Equal policy weights','Freeze scores at t = 100']
    errorplot(axes[0],clabels,component_rows); axes[0].axvline(0,color='black',lw=.8); axes[0].set_xlabel('Error change from PKD baseline'); axes[0].set_title('A  Paired component changes')
    errorplot(axes[1],clabels,[summary[c][SYSTEM_PKD]['mean_represented_population_share'] for c in components], '#ae5837'); axes[1].set_xlabel('Population share in represented strata'); axes[1].set_title('B  Descriptive coverage')
    save(fig,'figure2_components')
    fig,axes=plt.subplots(1,3,figsize=(11,3.4))
    for s,color,label in [(SYSTEM_ELECTION,'#7953a3','Election'),(SYSTEM_PKD,'#176575','PKD')]:
        ws=[0.,.25,.5,.75,1.]; ys=[summary[f'election_weight_{w:g}'][s]['loss'] for w in ws]
        axes[0].errorbar(ws,[x['mean'] for x in ys],yerr=[(x['high']-x['low'])/2 for x in ys],marker='o',capsize=2,color=color,label=label)
    axes[0].set_xlabel('Weight on individual\npublic record'); axes[0].set_ylabel('Mean error'); axes[0].legend(); axes[0].set_title('A  Clean record channel')
    for ax,field,title in [(axes[1],'electoral_information_noise','B  Record information error'),(axes[2],'electoral_media_amplification','C  Campaign contamination')]:
        cs=['election_weight_0.75']+[f'{field}_{v:g}' for v in [.25,1.,2.]]
        es=[paired(c,SYSTEM_ELECTION,c,SYSTEM_PKD) for c in cs]
        ax.errorbar([0,.25,1.,2.],[x['mean'] for x in es],yerr=[(x['high']-x['low'])/2 for x in es],marker='o',capsize=2,color='#7953a3')
        ax.axhline(0,color='black',lw=.8); ax.set_xlabel('Error or amplification\nparameter'); ax.set_ylabel('Election error minus PKD error'); ax.set_title(title)
    save(fig,'figure3_election')
    fig,axes=plt.subplots(1,3,figsize=(10.5,3.3))
    for ax,field,vs,title in [(axes[0],'proxy_noise',[0.,.5,1.,2.],'A  Shared scoring noise'),(axes[1],'feedback_delay',[0,3,12,24],'B  Feedback delay'),(axes[2],'scored_dimensions',[1,3,5,10],'C  Number of scored dimensions')]:
        default=0 if field!='scored_dimensions' else 10
        for s,color,label in [(SYSTEM_PKD,'#176575','PKD'),(SYSTEM_ELECTION,'#7953a3','Election'),(SYSTEM_POOL_SCORE,'#ae5837','All score weighted')]:
            ys=[summary['baseline' if v==default else f'{field}_{v:g}'][s]['loss'] for v in vs]
            ax.errorbar(vs,[x['mean'] for x in ys],yerr=[(x['high']-x['low'])/2 for x in ys],marker='o',capsize=2,label=label,color=color)
        ax.set_xlabel(field.replace('_',' ')); ax.set_ylabel('Mean error'); ax.set_title(title)
    axes[0].legend(fontsize=10); save(fig,'figure4_scoring')
    gaming=['baseline','independent_herding','coordinated_herding','indicator_targeting_0','indicator_targeting_0.5','indicator_targeting_1','indicator_targeting_firewall_0','indicator_targeting_firewall_0.5','indicator_targeting_firewall_1']
    glabel=['No strategy','Independent herding','Coordinated herding','Current indicator, noise 0','Current indicator, noise 0.5','Current indicator, noise 1','Lagged indicator, noise 0','Lagged indicator, noise 0.5','Lagged indicator, noise 1']
    fig,axes=plt.subplots(1,2,figsize=(10,4.4))
    for ax,metric,title in [(axes[0],'loss','A  Mean error'),(axes[1],'mean_demagogue_fraction','B  Labeled strategic agents in council')]:
        errorplot(ax,glabel,[summary[c][SYSTEM_PKD][metric] for c in gaming]); ax.set_title(title)
    axes[0].set_xscale('log'); axes[0].set_xlabel('Squared Euclidean error (log scale)'); axes[1].set_xlabel('Council share'); save(fig,'figure5_gaming')
    fig,ax=plt.subplots(figsize=(7,3.6)); errorplot(ax,[r['system'] for r in shock],shock); ax.axvline(0,color='black',lw=.8); ax.set_xlabel('Shock induced error change, paired difference in differences'); save(fig,'figureS1_shock')
    # Every displayed estimate is traceable to a raw run summary and a formula.
    write_csv(out/'artifact_map.csv',[{'artifact':p.name,'input':'raw/*/run_summary.csv','generator':'analyze_preprint.py'} for p in sorted(out.iterdir()) if p.is_file()])


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,default=Path('results/preprint_2026')); a=p.parse_args(); analyze(a.input)
