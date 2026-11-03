"""Generate evidence-based portfolio documentation, executed notebooks and PDF."""
from pathlib import Path
import sys
import json
import os
import tempfile
import html
import textwrap
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import plotly.express as px
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor,white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.common import ROOT

def read(name):return pd.read_csv(ROOT/'reports'/f'{name}.csv')
def load(name):return json.loads((ROOT/'reports'/f'{name}.json').read_text())
def save(name,text):(ROOT/name).write_text(text.strip()+'\n',encoding='utf-8')

def notebooks():
    setup="""from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
ROOT = Path.cwd()
def report(name): return pd.read_csv(ROOT / 'reports' / (name + '.csv'))
def metadata(name): return json.loads((ROOT / 'reports' / (name + '.json')).read_text())
plt.rcParams.update({'figure.figsize': (11, 4), 'axes.spines.top': False, 'axes.spines.right': False})
"""
    specs=[('01_data_profiling',[
        ('markdown','# Source profiling and grain validation\nOriginal data is preserved. Null outcomes, repeated geolocations and multiple reviews are handled explicitly.'),
        ('code',setup),
        ('code',"profile = metadata('source_profile')\npd.DataFrame([{'table': k, 'rows': v['rows'], 'duplicate_keys': v['duplicate_keys'], 'exact_duplicates': v['exact_duplicate_rows']} for k,v in profile.items()])"),
        ('code',"pd.DataFrame({k:v['nulls'] for k,v in profile.items()}).fillna('').T"),
        ('code',"metadata('data_quality')"),
        ('code',"status=report('status_coverage')\nstatus.set_index('order_status')['orders'].plot.barh(title='Order status coverage'); plt.tight_layout(); plt.show()"),
        ('code',"orders=pd.read_parquet(ROOT/'data/processed/fct_order.parquet')\nitems=pd.read_parquet(ROOT/'data/processed/fct_order_item.parquet')\nassert orders.order_id.is_unique\nassert abs(float(pd.to_numeric(orders.item_value).sum())-float(pd.to_numeric(items.price).sum()))<.01\nprint('Source grain and monetary reconciliation passed')"),
        ('markdown','See reports/source_profile.json for every column, null count and source SHA-256. Known timestamp anomalies remain in the quality report.')]),
    ('02_sla_analysis',[
        ('markdown','# SLA diagnostics and operational investigation\nRates are associations; seller diagnostics use single-seller orders. Wilson intervals show uncertainty.'),
        ('code',setup),('code',"metadata('kpis')"),
        ('code',"monthly=report('agg_monthly')\nmonthly.query('eligible_orders>=100').plot(x='purchase_month',y='late_rate',marker='o',title='Monthly late rate: at least 100 eligible deliveries'); plt.xticks(rotation=45);plt.tight_layout();plt.show()"),
        ('code',"regions=report('agg_region').query('eligible_orders>=500').sort_values('late_rate',ascending=False)\nregions[['customer_state','eligible_orders','late_rate','late_rate_ci_low','late_rate_ci_high','p90_delivery_days']]"),
        ('code',"regions.plot.bar(x='customer_state',y='late_rate',title='Regions with at least 500 eligible orders');plt.tight_layout();plt.show()"),
        ('code',"report('agg_seller').query('eligible_orders>=50').sort_values('late_rate',ascending=False).head(15)"),
        ('code',"report('customer_experience')"),('code',"report('fulfillment_stages')"),
        ('code',"report('region_category_strata').query('eligible>=100').sort_values('late_rate',ascending=False).head(20)"),
        ('markdown','Compare state patterns within primary-category strata before proposing a regional intervention. Handoff/transit comparisons are retrospective diagnostics, excluded from prediction features. No observed association establishes a cause.')]),
    ('03_model_diagnostics',[
        ('markdown','# Chronological model validation and policy evaluation\nCandidates and calibration methods are selected by forward validation Brier score with a ranking guard. July-August revalidation is retrospective; failed gates are retained.'),
        ('code',setup),('code',"metadata('model_evaluation')"),('code',"report('model_comparison')"),
        ('code',"cal=report('calibration')\nplt.plot(cal.predicted,cal.observed,'o-',label='Observed');plt.plot([0,1],[0,1],'--',color='gray',label='Perfect calibration');plt.xlabel('Mean predicted risk');plt.ylabel('Observed late rate');plt.legend();plt.title('Out-of-time probability calibration');plt.show()"),
        ('code',"importance=report('feature_importance').sort_values('ap_drop_mean')\nimportance.plot.barh(x='feature',y='ap_drop_mean',title='Permutation average-precision decrease');plt.tight_layout();plt.show()"),
        ('code',"report('model_segments').query(\"field=='customer_state'\").sort_values('average_precision',ascending=False)"),
        ('code',"report('adjusted_logistic_coefficients').assign(absolute=lambda d:d.coefficient.abs()).sort_values('absolute',ascending=False).head(20)"),
        ('code',"report('strategy_comparison')"),('code',"report('scenario_sensitivity')"),
        ('markdown','Local reference changes and global permutation importance explain associations, not intervention effects. Delivered-only labels, attribute-version assumptions, right censoring and temporal calibration shifts limit operational claims.')])]
    with tempfile.TemporaryDirectory() as folder:
        kernels=Path(folder)/'kernels';kernel=kernels/'controltower';kernel.mkdir(parents=True)
        (kernel/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'Control Tower','language':'python'}))
        for name,cells in specs:
            nb=nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell(t) if kind=='markdown' else nbformat.v4.new_code_cell(t) for kind,t in cells])
            km=KernelManager(kernel_name='controltower',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernels)]))
            NotebookClient(nb,km=km,timeout=180,resources={'metadata':{'path':str(ROOT)}}).execute()
            nb.metadata['kernelspec']={'display_name':'Python 3','language':'python','name':'python3'}
            nbformat.write(nb,ROOT/'notebooks'/f'{name}.ipynb')
            print(f'Executed {name}',flush=True)

def figures(k,m):
    folder=ROOT/'docs/figures';folder.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#334155','text.color':'#17243a','axes.titlesize':13})
    monthly=read('agg_monthly').query('eligible_orders>=100')
    fig,ax=plt.subplots(figsize=(9,2.8));ax.plot(pd.to_datetime(monthly.purchase_month),100*monthly.late_rate,color='#365c7d',linewidth=2)
    ax.set_ylabel('Late deliveries (%)');ax.set_title('Purchase months with at least 100 eligible deliveries',loc='left');fig.autofmt_xdate();fig.tight_layout();fig.savefig(folder/'monthly.png',dpi=160);plt.close(fig)
    regions=read('agg_region').query('eligible_orders>=500').nlargest(8,'late_rate').sort_values('late_rate')
    fig,ax=plt.subplots(figsize=(8,3));ax.barh(regions.customer_state,regions.late_rate*100,color='#365c7d');ax.set_xlabel('Late deliveries (%)');ax.set_title('Highest late rates among states with 500+ eligible orders',loc='left');fig.tight_layout();fig.savefig(folder/'regions.png',dpi=160);plt.close(fig)
    cal=read('calibration');fig,ax=plt.subplots(figsize=(5,3));ax.plot(cal.predicted,cal.observed,'o-',color='#365c7d');ax.plot([0,1],[0,1],'--',color='#94a3b8');ax.set(xlabel='Predicted risk',ylabel='Observed late rate',title='Test calibration');fig.tight_layout();fig.savefig(folder/'calibration.png',dpi=160);plt.close(fig)
    strategies=read('strategy_comparison');s=strategies[~strategies.strategy.str.startswith('Random')]
    fig,ax=plt.subplots(figsize=(8,3));ax.barh(s.strategy,s.late_captured,color='#365c7d');ax.set_xlabel('Observed late deliveries captured');ax.set_title('Queues optimize different objectives and may differ in size',loc='left');fig.tight_layout();fig.savefig(folder/'strategies.png',dpi=160);plt.close(fig)

def docs(k,m,dq):
    test=m['test'];strategy=read('strategy_comparison').set_index('strategy')
    quality=m.get('probability_quality',{})
    calibration_note=(f"The selected probability method overestimates later-period risk: mean predicted {quality.get('mean_predicted_risk',0):.2%} versus observed {test['late_rate']:.2%}. Its test Brier {test['brier']:.4f} is worse than the constant baseline {quality.get('constant_brier',0):.4f}. Ranking still exceeds prevalence on average precision, but these probabilities do not pass an operational calibration acceptance gate. Monetary outputs remain demonstrative scenarios; retrain and revalidate prospectively before real decisions.")
    regions=read('agg_region').query('eligible_orders>=500').nlargest(5,'late_rate')
    stage=read('fulfillment_stages')
    quality='# Data quality and exclusions\n\nNo source files are edited. The profile records every null count, key duplicate count, exact duplicate count and file hash.\n\n'+pd.DataFrame([{'check':key,'count':value} for key,value in dq.items()]).to_markdown(index=False)
    quality+='\n\nThe 189 distinct lifecycle warnings comprise carrier-before-purchase and delivery-before-carrier anomalies. They are retained and reported. Order punctuality uses valid purchase/actual/promise dates; stage timing is a separate diagnostic and requires caution. Repeated geolocation rows are reduced by median coordinates after bounding-box validation; reviews are reduced deterministically to one selected record per order. Four nonpositive product dimensions/weights remain visible in diagnostics. No negative item amounts or missing seller/product references were found.\n'
    save('docs/data_quality.md',quality)
    save('docs/source_to_target.md','# Source-to-target mapping\n\n'+pd.DataFrame([
        {'source':v['file'],'rows':v['rows'],'staging':'stg_'+key,'target':{'orders':'fct_order','order_items':'fct_order_item / fct_order_seller','geolocation':'dim_geography','order_payments':'Order payment aggregate','order_reviews':'Selected review on fct_order','category_translation':'dim_product.category'}.get(key,'dim_'+key.rstrip('s'))} for key,v in load('source_profile').items()]).to_markdown(index=False)+'\n\nAll raw columns load as text without changing original files. Staging SQL explicitly types timestamps, numeric amounts and dimensions. ZIP prefixes stay text to retain leading zeros.\n')
    splits=pd.DataFrame(m['splits']).T
    save('docs/model_card.md',f'''# Model card

Model version: **{m['model_version']}**. Selected candidate: **{m['selected_model']}**, selected by forward validation Brier score among candidates with useful validation ranking. Available for replay on **1 July 2018**. Checkout-time lateness prediction conditional on eventual eligible delivery, not all-cause order failure.

## Development windows and label availability

Training purchases precede January 2018, with labels known before February. February outcomes known before April fit raw/sigmoid/isotonic method candidates. April validation, known before June, selects the base/method pair by Brier score with a ranking guard. May data, known before July, defines the final calibration and risk thresholds. July-August purchases form the retrospective evaluation. The exact protocol is in revalidation_protocol_v3.md; legacy failures are retained. Source delivery timestamps approximate when eligible labels became observable; no status-event audit trail is available.

{splits.to_markdown()}

The buffers reduce preferential inclusion of quick deliveries but cannot eliminate right censoring or delivered-only selection. Label coverage by period must be considered when interpreting results. The final data extraction supplies outcomes through October 2018.

## Measured out-of-time performance

- ROC-AUC: {test['roc_auc']:.4f}
- Average precision: {test['average_precision']:.4f}; day-bootstrap 95% interval {test['ap_95pct_day_bootstrap'][0]:.4f}-{test['ap_95pct_day_bootstrap'][1]:.4f}
- Test late prevalence: {test['late_rate']:.2%}
- Brier score: {test['brier']:.4f}
- Precision at 50 per purchase day: {test['precision_at_50_daily']:.2%}; recall {test['recall_at_50_daily']:.2%}

**Probability acceptance finding:** {calibration_note}

`reports/model_comparison.csv` includes constant, logistic and two fixed gradient-boosting candidates. Preprocessing is fitted on training rows only. Raw probabilities, sigmoid and isotonic methods were compared on forward validation. The selected method is refitted on the final calibration cohort; raw selection retains the estimator probabilities. Calibration is not guaranteed under temporal distribution shift; the reliability curve and Brier score must be read with prevalence. All Olist evaluation periods were previously examined during development. This is retrospective revalidation, not a newly unseen or prospective test. Versioned attempts and the unchanged acceptance gates are published.

Risk thresholds: High >= {m['thresholds']['high']:.6f}; Medium >= {m['thresholds']['medium']:.6f}. These are calibration 90th/70th percentiles, not guaranteed daily workload caps; the optimizer controls actual capacity. Calibration high-risk workload is {m['calibration_workload']['high']} of {m['calibration_workload']['total']} eligible cases.

## Explanations and limitations

The allowlist is documented in `feature_dictionary.md`. Seller outcomes must strictly precede each purchase; equal-time outcomes are excluded. Final status, actual shipping/delivery events, durations, payments and reviews never enter predictors. Historical product metadata, price and seller assignment are assumed to reflect checkout attributes; Olist cannot verify this immutability.

Global importance uses validation-frozen model permutation importance on a fixed test sample; it explains ranking associations. Local examples replace one feature with its calibration-cohort reference value. These are nonadditive reference comparisons, not SHAP values and not causal intervention effects. Adjusted logistic coefficients provide conditional associations, with numeric features standardized and categorical encodings correlated.

Model performance varies by region, category, missing-distance and seller history; see model_segments.csv. Feature missingness and means by split are exported for drift review. Sparse segment estimates are unstable. Retraining, probability monitoring and an intervention pilot are prerequisites for real use. The package versions are locked; only load trusted joblib files.
''')
    save('docs/operational_findings.md',f'''# Operational findings

## Observed performance

{k['total_orders']:,} orders, {k['eligible_orders']:,} eligible deliveries, {k['late_orders']:,} late deliveries: on-time rate **{k['on_time_rate']:.2%}**. P90 delivery is {k['p90_delivery_days']:.1f} elapsed days. {k['excluded_orders']:,} orders are outside the delivered-order punctuality denominator.

## Geographic investigation queue

{regions[['customer_state','eligible_orders','late_rate','late_rate_ci_low','late_rate_ci_high','p90_delivery_days']].to_markdown(index=False)}

Prioritize investigation of high-rate, high-volume regions and inspect within-category comparisons in region_category_strata.csv. Regional differences may reflect promises, route mix, sellers, seasonality or source quality; they are not causal effects. Wilson intervals describe binomial rate uncertainty, not correction for multiple comparisons or seller/time clustering.

## Fulfillment and customer experience

{stage.to_markdown(index=False)}

Stage analysis is limited to one item and one seller with available handoff/deadline timestamps. Handoff associations warrant checking seller dispatch and carrier event recording. Long transit and late handoff can overlap; do not add them as independent causes. Customer-review comparisons are in customer_experience.csv and require reviewed orders; the dataset cannot represent unreviewed experiences.

## Ranking and decisions

Highest-risk ranking captured {int(strategy.loc['Highest risk','late_captured']):,} eventual late deliveries among {int(strategy.loc['Highest risk','labeled']):,} selected with eligible labels. The optimized 20% assumed-effectiveness scenario selected {int(strategy.loc['Optimized scenario','selected']):,} cases and captured {int(strategy.loc['Optimized scenario','late_captured']):,} eventual late deliveries. Queue sizes differ because allocation may leave capacity unused when expected net benefit is nonpositive.

{calibration_note}

Compare observed late-case capture separately from expected net benefit. Assumptions are BRL 5/case, BRL 150 base delay impact + 25% of item value, BRL 500 daily budget, 50 cases/day, maximum 50/state and 20% assumed effectiveness. The 10%/30% alternatives are sensitivity scenarios, not measured effects. No avoided delays or actual savings are established.

## Management actions

1. Audit high-volume regional and seller groups using sample sizes, uncertainty and primary-category strata.
2. Validate timestamp anomalies and whether checkout promises/seller assignments are version-stable.
3. Review the model reliability curve and segment performance before using risk probabilities for monetary decisions.
4. Pilot interventions prospectively; measure incremental outcome improvements and actual costs before adopting a value objective.
''')
    timings=load('pipeline_run')
    plans=load('query_plans')
    save('docs/query_performance.md','# Query performance evidence\n\nMeasured EXPLAIN ANALYZE/BUFFERS plans are stored in reports/query_plans.json. These are local prototype timings, not production SLAs.\n\n'+pd.DataFrame([{'query':name,'execution_ms':plan[0]['Execution Time'],'plan':plan[0]['Plan']['Node Type']} for name,plan in plans.items()]).to_markdown(index=False)+'\n\nIndexes cover order_id, purchase_date and primary_seller_id; item/bridge indexes cover order_id and seller_id. The daily lookup can use the purchase-date index. Aggregate scans may correctly choose sequential scans. Inspect plans against workload before adding more indexes.\n\nLast measured stages: '+str(timings['completed']))
    save('docs/demo_script.md',f'''# 3-5 minute product walkthrough

The delivered MP4 is a narrated walkthrough using screenshots from the running Streamlit dashboard. It is not a recording of native Power BI. Native Desktop data refresh and DAX acceptance passed; pixel screenshot review was unavailable.

0:00-0:35 - Explain the business decision and historical Olist source. Show total orders, {k['on_time_rate']:.2%} on-time delivery and denominator exclusions.

0:35-1:10 - Seller and geographic diagnostics. Explain single-seller attribution, minimum volumes and uncertainty. Select a seller and inspect its orders.

1:10-1:35 - Customer experience. Compare reviewed late/on-time deliveries without making causal claims.

1:35-2:20 - Purchase-time risk. Explain chronological training, seller history available before purchase and a model available from 1 July 2018. Show AP {test['average_precision']:.3f} and precision at 50/day {test['precision_at_50_daily']:.1%}. Reveal eventual outcomes only for retrospective comparison.

2:20-3:20 - Simulate 50 daily cases, a BRL 500 budget and 20% effectiveness. Change effectiveness and cost. Show the selected queue and why nonpositive value may leave capacity unused. Explain that these values are assumptions.

3:20-3:50 - Show data quality, test evidence and the editable Power BI source. Recommend a prospective intervention trial before claiming savings. End with a regional lead reviewing the highest-value eligible cases under an explicit daily budget.
''')

def snapshot(k,m):
    from scripts.export_review_snapshot import main
    main()

def pdf(k,m):
    path=ROOT/'docs/executive_case_study.pdf'
    c=canvas.Canvas(str(path),pagesize=(595,842));c.setTitle('Intelligent Supply Chain Control Tower | Executive Case Study');c.setAuthor('Supply Chain Analytics Portfolio')
    navy=HexColor('#263e54');teal=HexColor('#365c7d');muted=HexColor('#52637a')
    def base(n,label):
        c.setStrokeColor(HexColor('#dce2e7'));c.line(38,774,557,774)
        c.setFillColor(navy);c.setFont('Helvetica-Bold',10);c.drawString(38,808,'Olist | Delivery performance review')
        c.setFillColor(muted);c.setFont('Helvetica',9);c.drawString(38,788,label)
        c.setFont('Helvetica',8);c.drawString(38,25,'Olist historical data | CC BY-NC-SA 4.0 | Intervention values are assumptions');c.drawRightString(557,25,str(n))
    def title(text,y=735):
        c.setFillColor(navy);c.setFont('Helvetica-Bold',23);c.drawString(38,y,text)
    def para(text,y,size=10,width=519,color=navy):
        p=Paragraph(text,ParagraphStyle('body',fontName='Helvetica',fontSize=size,leading=size*1.5,textColor=color))
        _,h=p.wrap(width,700);p.drawOn(c,38,y-h);return y-h-13
    def heading(text,y):
        c.setFillColor(teal);c.setFont('Helvetica-Bold',12);c.drawString(38,y,text);return y-12
    def metrics(items,y):
        for i,(label,value) in enumerate(items):
            x=38+i*176;c.setStrokeColor(HexColor('#dce2e7'));c.line(x,y-75,x+166,y-75)
            c.setFillColor(muted);c.setFont('Helvetica',9);c.drawString(x+12,y-20,label)
            c.setFillColor(navy);c.setFont('Helvetica-Bold',22);c.drawString(x+12,y-52,value)
    base(1,'Summary and scope');title('Delivery performance review')
    y=para('Predictive Delivery Risk, SLA Monitoring &amp; Intervention Optimization',710,12)
    y=para('A decision-support prototype for an operations leader who needs to understand delivery reliability, spot risky purchases and allocate limited investigation capacity.',y)
    metrics([('Source orders',f"{k['total_orders']:,}"),('On-time delivery',f"{k['on_time_rate']:.2%}"),('P90 delivery',f"{k['p90_delivery_days']:.1f} days")],y-3)
    y-=110;y=heading('What the data establishes',y)
    y=para(f"The source contains {k['eligible_orders']:,} eligible completed deliveries, of which {k['late_orders']:,} arrived after the promised calendar date. Another {k['excluded_orders']:,} orders are reported separately because a valid completed-delivery outcome cannot be established.",y)
    c.drawImage(str(ROOT/'docs/figures/monthly.png'),38,260,width=519,height=162,preserveAspectRatio=True,mask='auto')
    y=heading('The operating decision',230)
    y=para('Use the dashboard to select an investigation cohort, review its sample size and risk, then allocate cases under an explicit daily budget. Validate proposed actions with a prospective intervention pilot.',y)
    y=heading('Interpretation boundary',y)
    para('This is historical Olist data, not a live logistics feed. Item value, freight and payments are kept distinct. No actual intervention, avoided delay or realized cost saving is observed.',y)
    c.showPage()
    base(2,'Operational findings');title('Regional and seller findings')
    y=para('Regional differences and seller performance are investigation signals. Order-level shipping milestones do not establish which seller or carrier caused a delay.',705)
    c.drawImage(str(ROOT/'docs/figures/regions.png'),38,420,width=519,height=220,preserveAspectRatio=True,mask='auto')
    y=heading('Protect the denominator and attribution',390)
    y=para('Seller comparisons use single-seller orders and publish sample sizes with Wilson intervals. Handoff/deadline diagnostics further restrict the cohort to one item and one seller. Primary-category reports assign each order to its first item category.',y)
    y=heading('Data quality is visible',y)
    y=para('The warehouse reconciles order counts and independent item/payment totals. It flags 189 lifecycle anomalies rather than silently deleting them: 166 carrier timestamps precede purchase and 23 actual deliveries precede carrier handoff. Eight delivered-status orders lack actual delivery timestamps.',y)
    y=heading('Recommended operational checks',y)
    y=para('1. Review high-rate regions with meaningful volume and compare primary-category strata.<br/>2. Audit seller dispatch and carrier event recording before attributing accountability.<br/>3. Investigate low review scores by delivery punctuality while retaining the reviewed-order denominator.',y)
    para('Uncertainty intervals describe observed rate uncertainty; they do not correct for all time/seller clustering or prove a causal regional effect.',y,9,color=muted)
    c.showPage()
    base(3,'Model evaluation');title('Purchase-time model review')
    y=para('Checkout attributes and strictly earlier completed-delivery seller history enter the model. Actual delivery, handoff, duration, final status, payments and reviews are excluded from predictors.',705)
    metrics([('Selected model',m['selected_model'].split('__')[0].capitalize()),('Test ROC-AUC',f"{m['test']['roc_auc']:.3f}"),('Test AP',f"{m['test']['average_precision']:.3f}")],y-3)
    y-=110;y=heading('Chronology and label maturity',y)
    y=para('Training uses pre-January 2018 purchases. February fits calibration-method candidates; April forward validation selects the base/method pair; May defines final calibration and thresholds. Every fitting cutoff precedes July evaluation purchases. July-August evaluation is retrospective: those historical outcomes were examined in earlier versions.',y)
    y=para(f"The final test has {m['test']['n']:,} eligible deliveries and {m['test']['late_rate']:.2%} late prevalence. Precision at 50 cases per purchase day is {m['test']['precision_at_50_daily']:.2%}, with recall {m['test']['recall_at_50_daily']:.2%}. The day-bootstrap 95% AP interval is {m['test']['ap_95pct_day_bootstrap'][0]:.3f}-{m['test']['ap_95pct_day_bootstrap'][1]:.3f}.",y)
    c.drawImage(str(ROOT/'docs/figures/calibration.png'),112,160,width=370,height=220,preserveAspectRatio=True,mask='auto')
    para(f"Revalidation completed but acceptance failed: selected probabilities overestimate the later cohort. Brier {m['test']['brier']:.3f} exceeds the constant baseline {m.get('probability_quality',{}).get('constant_brier',0):.3f}. Ranking remains informative, but probability-based monetary scenarios require revalidation. Delivered-only labels and residual censoring also limit generalization.",130,9,color=muted)
    c.showPage()
    base(4,'Planning assumptions and handoff');title('Daily case planning')
    y=para('OR-Tools maximizes the sum of predicted risk x assumed effectiveness x assumed delay impact, minus investigation cost. Daily capacity, budget and regional caps constrain allocation; nonpositive value can leave capacity unused.',705)
    y=para('Default scenario: 50 cases/day, BRL 500/day budget, BRL 5/case, 20% effectiveness, and impact of BRL 150 plus 25% of item value. Sensitivity scenarios use 10% and 30% effectiveness. All these quantities are assumptions.',y)
    c.drawImage(str(ROOT/'docs/figures/strategies.png'),38,370,width=519,height=195,preserveAspectRatio=True,mask='auto')
    y=heading('Observed capture versus simulated value',340)
    y=para('Highest-risk, shortest-promise, seller-history and seeded-random policies obey the same limits. Offline late-case capture is observed only where labels exist. Expected net benefit is a scenario estimate, not a measured saving. Different queue sizes prevent a simplistic precision-only comparison.',y)
    y=heading('Delivered implementation and remaining acceptance',y)
    y=para('Included: PostgreSQL/dbt warehouse, Python pipeline, trained model, strict-time features, scenario allocator, six-page Streamlit dashboard, executed notebooks, tests, CSV/Parquet outputs, a portable report and an editable six-page Power BI project.',y)
    y=para('Native Desktop refreshed all seven tables and passed 6,101 DAX reconciliations. A required report-format file was fixed. Graphics capture was unavailable, so no pixel-level screenshot acceptance is claimed. Historical probability revalidation failed its preset gates; operational use remains unapproved.',y)
    para('Next step: validate checkout event immutability and operational costs, then run a controlled intervention pilot with calibration and customer-experience guardrails. Source: kaggle.com/datasets/olistbr/brazilian-ecommerce (Olist, 2018).',y,9,color=muted)
    c.save()
    print('Created four-page executive case study',flush=True)

def main():
    k,m,dq=load('kpis'),load('model_evaluation'),load('data_quality')
    docs(k,m,dq);figures(k,m);snapshot(k,m);notebooks();pdf(k,m)

if __name__=='__main__':main()
