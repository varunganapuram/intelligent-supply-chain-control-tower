"""Standalone report, using the same restrained presentation as the app."""
from pathlib import Path
import sys,json,html
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.common import ROOT

BLUE,RUST='rgb(37,99,235)','rgb(220,38,38)'
GREEN,PURPLE,ORANGE='rgb(22,163,74)','rgb(147,51,234)','rgb(234,88,12)'
NAMES=['Overview','Seller performance','Regional delivery','Customer reviews','Risk review','Case planning']

def read(name):return pd.read_csv(ROOT/'reports'/f'{name}.csv')

def table(df, formats=None):
    return df.style.format(formats or {},na_rep='—').hide(axis='index').to_html()

def main():
    k=json.loads((ROOT/'reports/kpis.json').read_text())
    m=json.loads((ROOT/'reports/model_evaluation.json').read_text())
    monthly=read('agg_monthly').query('eligible_orders>=100')
    region=read('agg_region')
    seller=read('agg_seller').query('eligible_orders>=50').nlargest(15,'late_orders')
    cx=read('customer_experience').assign(delivery=lambda d:d.is_late.map({0.:'On time',1.:'Late'}))
    calibration=read('calibration')
    policy=read('strategy_comparison')
    policy=policy[~policy.strategy.str.startswith('Random')]
    figs=[
        px.line(monthly,x='purchase_month',y='late_rate',markers=True,labels={'purchase_month':'Purchase month','late_rate':'Late rate'}),
        px.bar(seller.sort_values('late_orders'),x='late_orders',y='seller_id',orientation='h',labels={'late_orders':'Late deliveries','seller_id':'Seller ID'}),
        px.bar(region.query('eligible_orders>=100').sort_values('late_rate'),x='late_rate',y='customer_state',orientation='h',labels={'late_rate':'Late rate','customer_state':'Destination state'}),
        px.bar(cx,x='delivery',y='dissatisfaction_rate',color='delivery',color_discrete_map={'On time':GREEN,'Late':RUST},text_auto='.1%',labels={'delivery':'Delivery outcome','dissatisfaction_rate':'Reviews scoring 1 or 2'}),
        px.line(calibration,x='predicted',y='observed',markers=True,labels={'predicted':'Mean predicted risk','observed':'Observed late rate'}),
        px.bar(policy,x='late_captured',y='strategy',orientation='h',labels={'late_captured':'Eventual late deliveries captured','strategy':'Selection policy'})]
    figs[0].add_hline(y=k['late_rate'],line_dash='dot',line_color='#a5b0ba')
    figs[4].add_shape(type='line',x0=0,y0=0,x1=1,y1=1,line=dict(color='#b6c0c8',dash='dot'))
    figs[4].update_xaxes(tickformat='.0%',range=[0,1]);figs[4].update_yaxes(tickformat='.0%',range=[0,1])
    figs[0].update_yaxes(tickformat='.0%')
    figs[2].update_xaxes(tickformat='.0%')
    figs[3].update_yaxes(tickformat='.0%');figs[3].update_layout(showlegend=False)
    peak=monthly.loc[monthly.late_rate.idxmax()]
    notes=[
        ('March 2018 needs explanation',f'The peak month was {pd.Timestamp(peak.purchase_month):%B %Y}: {peak.late_rate:.1%} late, affecting {int(peak.late_orders):,} orders. The dotted line is the overall rate. Months with fewer than 100 valid deliveries are omitted.'),
        ('Start with volume, then inspect the rate','These sellers have at least 50 valid single-seller deliveries. The chart is ranked by late-order count. Review the sample size and uncertainty before attributing a problem to a seller.'),
        ('A percentage is only part of the picture','States shown have at least 100 valid deliveries. Combine the late rate with the number of affected orders and the delivery-time distribution. Regional, seller and category effects overlap.'),
        ('Use the reviewed-order denominator',f'{cx.loc[cx.delivery.eq("Late"),"dissatisfaction_rate"].iloc[0]:.1%} of reviewed late deliveries received a score of 1 or 2, compared with {cx.loc[cx.delivery.eq("On time"),"dissatisfaction_rate"].iloc[0]:.1%} of on-time deliveries. This is an association, not an isolated effect of lateness.'),
        ('Revalidation completed; acceptance failed',f'The revised model predicts {m["probability_quality"]["mean_predicted_risk"]:.1%} mean risk on the later test cohort, versus {m["test"]["late_rate"]:.1%} observed. Ranking has some value, but probabilities need revalidation. The dotted diagonal shows perfect calibration.'),
        ('The value objective is hypothetical','Each policy uses the same daily case, budget and state limits. Optimized value is not the same objective as finding the most late deliveries. The queues differ in size. No savings or intervention effects are measured in Olist.')]
    titles=['Late deliveries by purchase month','Sellers with the most late deliveries','Late rate by destination','Low review scores by delivery outcome','Later-period calibration check','Policy comparison on later outcomes']
    details=[
        table(region.nlargest(8,'late_orders')[['customer_state','eligible_orders','late_orders','late_rate']].rename(columns={'customer_state':'State','eligible_orders':'Valid deliveries','late_orders':'Late orders','late_rate':'Late rate'}),{'Late rate':'{:.1%}'}),
        table(seller[['seller_id','eligible_orders','late_orders','late_rate','late_rate_ci_low','late_rate_ci_high']].rename(columns={'seller_id':'Seller ID','eligible_orders':'Valid deliveries','late_orders':'Late orders','late_rate':'Late rate','late_rate_ci_low':'95% lower','late_rate_ci_high':'95% upper'}),{'Late rate':'{:.1%}','95% lower':'{:.1%}','95% upper':'{:.1%}'}),
        table(region.query('eligible_orders>=100').nlargest(12,'late_orders')[['customer_state','eligible_orders','late_orders','late_rate','p90_delivery_days']].rename(columns={'customer_state':'State','eligible_orders':'Valid deliveries','late_orders':'Late orders','late_rate':'Late rate','p90_delivery_days':'P90 days'}),{'Late rate':'{:.1%}','P90 days':'{:.1f}'}),
        table(cx[['delivery','reviewed','dissatisfied','dissatisfaction_rate']].rename(columns={'delivery':'Delivery','reviewed':'Reviewed orders','dissatisfied':'Scores 1–2','dissatisfaction_rate':'Low-score rate'}),{'Low-score rate':'{:.1%}'}),
        table(pd.DataFrame({'Test measure':['ROC-AUC','Average precision','Top-50 daily precision','Brier, calibrated','Brier, constant'],
            'Result':[f'{m["test"]["roc_auc"]:.3f}',f'{m["test"]["average_precision"]:.3f}',f'{m["test"]["precision_at_50_daily"]:.2%}',f'{m["test"]["brier"]:.4f}',f'{m["probability_quality"]["constant_brier"]:.4f}']})),
        table(policy[['strategy','selected','labeled','late_captured','observed_precision']].rename(columns={'strategy':'Policy','selected':'Selected','labeled':'Valid outcomes','late_captured':'Late cases','observed_precision':'Late-case precision'}),{'Late-case precision':'{:.1%}'})]
    sections=[]
    for i,(fig,title,description,detail) in enumerate(zip(figs,titles,notes,details)):
        fig.update_layout(template='plotly_white',paper_bgcolor='white',plot_bgcolor='white',
            font=dict(family='Arial',size=12,color='#000000',weight=300),colorway=[BLUE,RUST,GREEN,PURPLE,ORANGE],height=390,
            margin=dict(l=6,r=15,t=15,b=30))
        if i in [0,4]:
            fig.update_traces(line_color=BLUE if i==0 else GREEN)
        if i in [1,2,5]:
            fig.update_traces(marker_color={1:PURPLE,2:ORANGE,5:BLUE}[i])
        for trace in fig.data:
            if trace.type=='scatter' and 'lines' in (trace.mode or ''):
                trace.line.width=4
                trace.marker.size=8
            elif trace.type=='bar':
                trace.marker.opacity=1
        fig.update_layout(bargap=.18)
        fig.update_xaxes(gridcolor='#edf0f3',color='#000000',tickfont=dict(color='#000000',weight=300),title_font=dict(color='#000000',weight=300))
        fig.update_yaxes(gridcolor='#edf0f3',color='#000000',tickfont=dict(color='#000000',weight=300),title_font=dict(color='#000000',weight=300))
        rendered=fig.to_html(full_html=False,include_plotlyjs=True if i==0 else False,div_id=f'chart{i}',config={'displayModeBar':False})
        sections.append(f'<section class="panel" id="page{i}" style="display:{"block" if i==0 else "none"}"><h2>{title}</h2><div class="report-grid"><div>{rendered}</div><aside><h3>{description[0]}</h3><p>{html.escape(description[1])}</p></aside></div><div class="table-wrap">{detail}</div></section>')
    css='''body{font:14px Arial,sans-serif;font-weight:300;color:#000000;background:#fff;margin:0}main{max-width:1160px;margin:auto;padding:32px 36px 20px}header{display:flex;justify-content:space-between;border-bottom:1px solid #dce2e7;padding-bottom:18px;color:#000000;font-size:12px}header strong{font-weight:800;color:#000000;font-size:16px}h1{font-size:29px;font-weight:800;letter-spacing:-.4px;margin:26px 0 10px}h2{font-size:17px;font-weight:300;margin-top:26px}h3{font-size:13px;font-weight:300;color:#000000;margin-top:0}p{color:#000000;line-height:1.7}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:28px;margin:28px 0}.metric{font-size:12px;color:#000000}.metric strong{display:block;font-size:27px;color:#000000;font-weight:300;margin-top:8px}nav{display:flex;gap:24px;border-bottom:1px solid #dce2e7;margin-top:30px;flex-wrap:wrap}nav button{background:none;border:0;border-bottom:2px solid transparent;color:#000000;font:13px Arial;padding:12px 0;cursor:pointer}nav button.active{border-color:#000000;color:#000000}.report-grid{display:grid;grid-template-columns:3fr 1fr;gap:35px;align-items:start}aside{border-left:2px solid #b76743;padding:3px 0 3px 15px;margin-top:25px;font-size:13px}.table-wrap{overflow:auto;margin-top:20px}table{border-collapse:collapse;width:100%;font-size:12px}th{text-align:left;background:#f2f4f6;font-weight:300;color:#000000}th,td{padding:11px 12px;border-bottom:1px solid #e3e7eb}td:not(:first-child){text-align:right}footer{font-size:11px;color:#000000;border-top:1px solid #dce2e7;margin-top:32px;padding-top:16px;line-height:1.8}a{color:#000000}@media(max-width:750px){main{padding:20px}.report-grid{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,1fr)}nav{gap:15px}}'''
    page=f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Olist · Delivery review</title><style>{css}</style></head><body><main><header><strong>Delivery review</strong><span>Olist marketplace · Brazil · 2016–2018</span></header><h1>Delivery performance</h1><p>Delivery against the promised date, with order volume and the main exceptions.</p><div class="metrics">'
    for label,value in [('On-time delivery',f'{k["on_time_rate"]:.2%}'),('Orders placed',f'{k["total_orders"]:,}'),('Valid deliveries',f'{k["eligible_orders"]:,}'),('P90 delivery',f'{k["p90_delivery_days"]:.1f} days')]:
        page+=f'<div class="metric">{label}<strong>{value}</strong></div>'
    page+='</div><nav>'+''.join(f'<button class="{"active" if i==0 else ""}" onclick="show({i})">{name}</button>' for i,name in enumerate(NAMES))+'</nav>'+''.join(sections)
    page+=f'<footer>{k["excluded_orders"]:,} orders are outside the completed-delivery punctuality measure. Source: <a href="https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce">Olist public dataset</a>, CC BY-NC-SA 4.0.<br>Offline report. For filters, purchase-day replay and editable planning inputs, open the Streamlit application. No actual intervention savings are established.</footer>'
    page+='</main><script>function show(n){document.querySelectorAll(".panel").forEach((e,i)=>e.style.display=i===n?"block":"none");document.querySelectorAll("nav button").forEach((e,i)=>e.classList.toggle("active",i===n));window.dispatchEvent(new Event("resize"));}</script></body></html>'
    (ROOT/'docs/dashboard_snapshot.html').write_text(page,encoding='utf-8')
    print('Updated standalone delivery review')

if __name__=='__main__':main()
