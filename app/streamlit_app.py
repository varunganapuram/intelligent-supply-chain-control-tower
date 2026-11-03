"""Olist delivery review: reporting, model audit and daily case planning."""
from pathlib import Path
import sys
import json
import html
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.common import ROOT
from src.analytics import wilson
from src.optimization import Scenario, optimize

st.set_page_config(page_title='Olist · Delivery review', layout='wide')
st.markdown('<style>' + (ROOT/'app/styles.css').read_text() + '</style>', unsafe_allow_html=True)

BLUE = 'rgb(37,99,235)'
RED = 'rgb(220,38,38)'
GREEN = 'rgb(22,163,74)'
PURPLE = 'rgb(147,51,234)'
ORANGE = 'rgb(234,88,12)'
INK = '#000000'
px.defaults.template = 'plotly_white'
px.defaults.color_discrete_sequence = [BLUE, RED, GREEN, PURPLE, ORANGE]
PAGES = ['Overview', 'Seller performance', 'Regional delivery', 'Customer reviews', 'Risk review', 'Case planning']
STATES = {'AC':'Acre','AL':'Alagoas','AP':'Amapá','AM':'Amazonas','BA':'Bahia',
    'CE':'Ceará','DF':'Distrito Federal','ES':'Espírito Santo','GO':'Goiás','MA':'Maranhão',
    'MT':'Mato Grosso','MS':'Mato Grosso do Sul','MG':'Minas Gerais','PA':'Pará','PB':'Paraíba',
    'PR':'Paraná','PE':'Pernambuco','PI':'Piauí','RJ':'Rio de Janeiro','RN':'Rio Grande do Norte',
    'RS':'Rio Grande do Sul','RO':'Rondônia','RR':'Roraima','SC':'Santa Catarina','SP':'São Paulo',
    'SE':'Sergipe','TO':'Tocantins'}

@st.cache_data
def _read(name, source_mtime):
    return pd.read_parquet(ROOT/'data/processed'/f'{name}.parquet')

@st.cache_data
def _report(name, source_mtime):
    return pd.read_csv(ROOT/'reports'/f'{name}.csv')

def read(name):
    return _read(name,(ROOT/'data/processed'/f'{name}.parquet').stat().st_mtime_ns)

def report(name):
    return _report(name,(ROOT/'reports'/f'{name}.csv').stat().st_mtime_ns)

def pct(v, decimals=1):
    return '—' if pd.isna(v) else f'{v:.{decimals}%}'

def number(v, decimals=0):
    return '—' if pd.isna(v) else f'{v:,.{decimals}f}'

def state_name(code):
    return f'{STATES.get(code, code)} ({code})'

def chart(fig, percent=False, horizontal=False):
    fig.update_layout(paper_bgcolor='white', plot_bgcolor='white',
        font=dict(family='Arial, sans-serif', size=12, color=INK, weight=300),
        title=dict(font=dict(size=14, color=INK)), margin=dict(l=4, r=16, t=24, b=8),
        legend=dict(title_text='', orientation='h', y=-.22, x=0,font=dict(color=INK,weight=300)),
        hoverlabel=dict(bgcolor='white', font_color=INK))
    fig.update_layout(bargap=.18)
    for trace in fig.data:
        if trace.type=='scatter':
            trace.marker.opacity=1
            if 'lines' in (trace.mode or ''):
                trace.line.width=4
                trace.marker.size=8
        elif trace.type=='bar':
            trace.marker.opacity=1
            trace.marker.line.width=0
            trace.textfont=dict(color=INK,weight=300)
            if trace.texttemplate:
                trace.textposition='outside'
                trace.cliponaxis=False
    fig.update_xaxes(showline=False, zeroline=False, gridcolor='#edf0f3',color=INK,
        tickfont=dict(color=INK,weight=300),title_font=dict(color=INK,size=11,weight=300))
    fig.update_yaxes(showline=False, zeroline=False, gridcolor='#edf0f3',color=INK,
        tickfont=dict(color=INK,weight=300),title_font=dict(color=INK,size=11,weight=300))
    for annotation in fig.layout.annotations:
        annotation.font.color=INK
        annotation.font.weight=300
    if percent:
        (fig.update_xaxes if horizontal else fig.update_yaxes)(tickformat='.0%')
    st.plotly_chart(fig, width='stretch', config={'displayModeBar':False})

def metrics(items):
    for column, (label, value, note) in zip(st.columns(len(items)), items):
        with column:
            st.metric(label, value)
            if note:
                st.caption(note)

def note(label, text, kind='normal'):
    st.markdown(f'<div class="report-note {kind}"><strong>{html.escape(label)}</strong><p>{html.escape(text)}</p></div>', unsafe_allow_html=True)

LABELS = {'customer_state':'State','primary_seller_id':'Seller ID','seller_id':'Seller ID',
    'orders':'Orders','eligible_orders':'Delivered orders','late_orders':'Late orders',
    'late_rate':'Late rate','ci_low':'95% interval, lower','ci_high':'95% interval, upper',
    'avg_delivery_days':'Mean days','delivery_days':'Delivery days','p90':'P90 days',
    'primary_category':'Main category','review_score':'Review score','order_id':'Order ID',
    'purchase_date':'Purchase date','is_late':'Eventually late','risk_probability':'Model risk',
    'risk_category':'Risk band','risk_rank':'Daily rank','label_known_at':'Outcome recorded',
    'prediction_as_of':'Purchase time','expected_net_benefit':'Net value (assumed)',
    'selected_for_intervention':'Selected','assumed_delay_impact':'Delay impact (assumed)',
    'intervention_cost':'Case cost','promised_days':'Promised days'}

def table(frame, height=None, labels=None):
    names={**LABELS, **(labels or {})}
    formats={}
    for c in frame:
        if c in ['late_rate','ci_low','ci_high','risk_probability','dissatisfaction_rate','observed_precision']:
            formats[names.get(c,c)]='{:.1%}'
        elif c in ['delivery_days','avg_delivery_days','p90','mean_score']:
            formats[names.get(c,c)]='{:,.1f}'
        elif c in ['orders','eligible_orders','late_orders','reviewed','dissatisfied']:
            formats[names.get(c,c)]='{:,.0f}'
        elif c in ['expected_net_benefit','assumed_delay_impact','intervention_cost']:
            formats[names.get(c,c)]='R$ {:,.2f}'
    renamed=frame.rename(columns=names)
    st.dataframe(renamed.style.format(formats, na_rep='—'), hide_index=True,
        width='stretch', height=height or 'auto')

def region_summary(frame):
    return frame.groupby('customer_state').agg(orders=('order_id','size'),
        late_orders=('is_late','sum'),late_rate=('is_late','mean'),
        delivery_days=('delivery_days','mean'),p90=('delivery_days',lambda x:x.quantile(.9))).reset_index()

def download(frame, name='orders.csv', label='Download the underlying rows'):
    st.download_button(label, frame.to_csv(index=False), file_name=name, mime='text/csv')

if not (ROOT/'reports/kpis.json').exists():
    st.error('The reporting files are missing. See the setup instructions in README.md.')
    st.stop()

orders=read('fct_order')
orders['purchase_date']=pd.to_datetime(orders.purchase_date)
model_metadata=json.loads((ROOT/'reports/model_evaluation.json').read_text())
model_date=pd.Timestamp(model_metadata['model_available_at'])
st.sidebar.markdown('<div class="report-brand">Delivery review</div><div class="report-source">Olist marketplace · Brazil</div>', unsafe_allow_html=True)
page=st.sidebar.radio('Report sections', PAGES, label_visibility='collapsed')
st.sidebar.divider()
st.sidebar.markdown('**Report filters**')
regions=st.sidebar.multiselect('Customer state', sorted(orders.customer_state.dropna().unique()), format_func=state_name)
risk_page=page in PAGES[4:]
date_range=(orders.purchase_date.min().date(),orders.purchase_date.max().date())
if not risk_page:
    date_range=st.sidebar.date_input('Purchase dates', date_range)
else:
    st.sidebar.caption(f'Replay dates are selected within the report. This model is available from {model_date:%d %B %Y}.')
with st.sidebar.expander('About this report'):
    st.write('Historical marketplace orders from 2016–2018. The source has no live tracking feed or intervention records.')
    st.write('A late delivery arrives after the promised calendar date. Canceled and unresolved orders are outside that rate.')
st.sidebar.caption('Source: Olist public dataset\n\nPrepared as an analytical case study.')

filtered=orders[orders.customer_state.isin(regions)] if regions else orders.copy()
if not risk_page and len(date_range)==2:
    filtered=filtered[filtered.purchase_date.between(pd.Timestamp(date_range[0]),pd.Timestamp(date_range[1]))]
eligible=filtered[filtered.is_late.notna()]
head, context=st.columns([3,2], vertical_alignment='bottom')
with head:
    st.title(page)
with context:
    scope=', '.join(regions) if regions else 'All customer states'
    if risk_page:
        period=f'{model_date:%B}–August 2018 replay'
    elif len(date_range)==2:
        period=f'{date_range[0]:%d %b %Y} – {date_range[1]:%d %b %Y}'
    else:
        period='Select a date range'
    st.markdown(f'<div class="report-context">{html.escape(scope)}<br>{html.escape(period)}</div>',unsafe_allow_html=True)
DESCRIPTIONS = [
    'Delivery against the promised date, with order volume and the main exceptions.',
    'Compare sellers with enough completed orders to make the rates useful.',
    'Separate the size of a delivery problem from the percentage of orders affected.',
    'Review scores and delay severity for orders with a recorded outcome.',
    'Rank purchases for review, then check what the model got right and where it failed.',
    'Choose a daily queue under a case limit and budget. All financial inputs are assumptions.']
st.markdown(f'<p class="page-description">{DESCRIPTIONS[PAGES.index(page)]}</p>',unsafe_allow_html=True)

if page==PAGES[0]:
    metrics([
        ('On-time delivery',pct(1-eligible.is_late.mean(),2),f'{number(eligible.is_late.sum())} late / {len(eligible):,} delivered'),
        ('Orders placed',f'{len(filtered):,}',f'{len(filtered)-len(eligible):,} outside the punctuality measure'),
        ('Typical delivery',number(eligible.delivery_days.median(),1)+' days','Median elapsed time from purchase'),
        ('P90 delivery',number(eligible.delivery_days.quantile(.9),1)+' days','90% of completed deliveries arrive within this time')])
    st.divider()
    monthly=filtered.assign(month=filtered.purchase_date.dt.to_period('M').dt.to_timestamp()).groupby('month').agg(
        orders=('order_id','size'),delivered=('is_late','count'),late_orders=('is_late','sum'),late_rate=('is_late','mean')).reset_index()
    trend=monthly[monthly.delivered.ge(100)]
    left,right=st.columns([2.5,1],gap='large')
    with left:
        st.subheader('Late deliveries by purchase month')
        fig=go.Figure(go.Scatter(x=trend.month,y=trend.late_rate,mode='lines+markers',
            line=dict(color=BLUE,width=2),marker=dict(size=5),name='Late rate',
            customdata=trend[['delivered','late_orders']],
            hovertemplate='%{x|%b %Y}<br>%{y:.1%} late<br>%{customdata[1]:,.0f} / %{customdata[0]:,.0f} delivered<extra></extra>'))
        if len(trend):
            peak=trend.loc[trend.late_rate.idxmax()]
            fig.add_trace(go.Scatter(x=[peak.month],y=[peak.late_rate],mode='markers',marker=dict(size=11,color=RED),showlegend=False,hoverinfo='skip'))
            fig.add_hline(y=eligible.is_late.mean(),line_dash='dot',line_color='#9eabb5',annotation_text='Selected-period average',annotation_position='bottom left',annotation_font_size=10)
        fig.update_layout(height=280,showlegend=False)
        fig.update_yaxes(title_text=None,range=[0,max(.1,trend.late_rate.max()*1.15)] if len(trend) else [0,.1])
        chart(fig,percent=True)
        volume=px.bar(trend,x='month',y='delivered',color_discrete_sequence=[GREEN],labels={'month':'','delivered':'Delivered'})
        volume.update_layout(height=120,bargap=.35)
        volume.update_xaxes(dtick='M3',tickformat='%b %y')
        volume.update_yaxes(nticks=3,title_text=None)
        chart(volume)
        st.caption('The lower bars show completed-delivery volume. Months with fewer than 100 completed deliveries are left out of the trend.')
    with right:
        st.subheader('Reading the results')
        if len(trend):
            peak=trend.loc[trend.late_rate.idxmax()]
            note(peak.month.strftime('%B %Y'),f'{pct(peak.late_rate)} late: {int(peak.late_orders):,} of {int(peak.delivered):,} delivered orders. Start the month-by-month investigation here.','attention')
        region=region_summary(eligible)
        if len(region) and eligible.is_late.sum()>0:
            most=region.loc[region.late_orders.idxmax()]
            note(STATES.get(most.customer_state,most.customer_state),f'{int(most.late_orders):,} late orders, or {pct(most.late_orders/eligible.is_late.sum(),0)} of all late cases in this selection. Volume matters alongside the rate.')
        st.caption('These are investigation leads. Region, seller and category effects overlap.')
    st.divider()
    left,right=st.columns([2,1],gap='large')
    with left:
        st.subheader('Where the late orders are')
        regional=region_summary(eligible).query('orders>=100').sort_values('late_orders',ascending=False).head(8)
        display=regional.copy()
        display.customer_state=display.customer_state.map(state_name)
        table(display[['customer_state','orders','late_orders','late_rate','p90']])
        st.caption('Ranked by late-order count. At least 100 completed deliveries per state.')
    with right:
        st.subheader('Orders outside the rate')
        excluded=filtered[filtered.is_late.isna()].groupby('order_status').size().sort_values(ascending=False).reset_index(name='orders')
        table(excluded, labels={'order_status':'Recorded status'})
        st.caption('Missing or inconsistent completed-delivery outcomes are also excluded. A missing result is not counted as on time.')
    with st.expander('Metric definitions and source checks'):
        st.write('On time means the actual delivery calendar date is on or before the promised date. Elapsed delivery time is measured from purchase. Items and payments are aggregated separately before orders are joined.')
        table(report('status_coverage'),labels={'order_status':'Status','eligible':'Valid completed deliveries'})

elif page==PAGES[1]:
    minimum=st.select_slider('Minimum completed orders per seller',options=[10,25,50,100,250,500],value=50)
    f=eligible[eligible.seller_count.eq(1)]
    seller=f.groupby('primary_seller_id').agg(eligible_orders=('order_id','size'),late_orders=('is_late','sum'),late_rate=('is_late','mean'),avg_delivery_days=('delivery_days','mean')).reset_index()
    seller['ci_low'],seller['ci_high']=wilson(seller.late_orders,seller.eligible_orders)
    seller=seller[seller.eligible_orders.ge(minimum)].sort_values(['late_orders','late_rate'],ascending=False)
    metrics([('Sellers in comparison',f'{len(seller):,}',f'At least {minimum} completed orders each'),
        ('Single-seller deliveries',f'{len(f):,}','Multi-seller orders excluded'),
        ('Late rate',pct(f.is_late.mean()),'All single-seller deliveries in the selected period')])
    st.divider()
    left,right=st.columns([2.2,1],gap='large')
    with left:
        st.subheader('Order volume and late rate')
        fig=px.scatter(seller,x='eligible_orders',y='late_rate',size='late_orders',hover_name='primary_seller_id',size_max=28,
            labels={'eligible_orders':'Completed orders','late_rate':'Late rate'},color_discrete_sequence=[PURPLE])
        fig.update_traces(marker_opacity=.6,marker_line_width=0)
        fig.add_hline(y=f.is_late.mean(),line_dash='dot',line_color='#a5b0ba')
        fig.update_layout(height=320)
        chart(fig,percent=True)
    with right:
        note('Compare the sample size','A high percentage from a few orders is weak evidence. The dotted line is the overall single-seller late rate. Bubble size represents late-order count.')
        note('Attribution limit','Shipping milestones are recorded for the whole order. Single-seller comparisons reduce ambiguity, but do not establish who caused a delay.')
    st.subheader('Sellers with the most late orders')
    table(seller.head(30),height=410)
    chosen=st.selectbox('Inspect a seller',seller.primary_seller_id.tolist(),format_func=lambda x:x[:12]+'…') if len(seller) else None
    if chosen:
        detail=f[f.primary_seller_id.eq(chosen)].copy()
        st.caption(f'Full seller ID: {chosen} · {len(detail):,} completed deliveries · {pct(detail.is_late.mean())} late')
        table(detail[['order_id','purchase_date','is_late','delivery_days','primary_category']].sort_values('purchase_date',ascending=False).head(100))
        download(detail[['order_id','purchase_date','is_late','delivery_days','primary_category']],f'seller_{chosen}.csv')

elif page==PAGES[2]:
    region=region_summary(eligible)
    threshold=st.select_slider('Minimum completed orders per state',options=[0,50,100,250,500],value=100)
    region=region[region.orders.ge(threshold)]
    region['state_name']=region.customer_state.map(state_name)
    left,right=st.columns([1.25,1],gap='large')
    with left:
        st.subheader('Late rate by destination')
        fig=px.bar(region.sort_values('late_rate'),x='late_rate',y='state_name',orientation='h',labels={'late_rate':'Late rate','state_name':''},custom_data=['orders','late_orders'],color_discrete_sequence=[ORANGE])
        fig.update_traces(hovertemplate='%{y}<br>%{x:.1%} late<br>%{customdata[1]:,.0f} late / %{customdata[0]:,.0f} deliveries<extra></extra>')
        fig.add_vline(x=eligible.is_late.mean(),line_dash='dot',line_color='#a5b0ba')
        fig.update_layout(height=540)
        chart(fig,percent=True,horizontal=True)
        st.caption('Dotted line: selected-period average. Hover for order counts.')
    with right:
        st.subheader('How long deliveries take')
        fig=px.scatter(region,x='orders',y='p90',hover_name='state_name',size='late_orders',size_max=32,
            labels={'orders':'Completed orders','p90':'P90 delivery time, days'},color_discrete_sequence=[BLUE])
        fig.update_layout(height=260)
        chart(fig)
        stage=eligible[eligible.item_count.eq(1)&eligible.seller_count.eq(1)]
        after=stage[stage.handoff_after_item_deadline.eq(1)]
        before=stage[stage.handoff_after_item_deadline.eq(0)]
        note('Dispatch timing deserves a closer look',f'In one-item, one-seller orders, {pct(after.is_late.mean())} of deliveries with a handoff after the item deadline were late. The rate was {pct(before.is_late.mean())} for handoffs within the deadline.')
        st.caption('This is a retrospective association. The source contains 189 lifecycle timestamp anomalies; check the records before assigning responsibility.')
    st.subheader('State-level detail')
    display=region.sort_values('late_orders',ascending=False).drop(columns='state_name')
    display.customer_state=display.customer_state.map(state_name)
    table(display)
    with st.expander('Distance assumptions'):
        st.write('Distance uses median coordinates for each ZIP prefix and the mean straight-line seller-to-customer distance across items. It is not the carrier route. Geographic outliers are documented in the quality report.')
    download(region,'state_delivery_summary.csv')

elif page==PAGES[3]:
    reviewed=filtered[filtered.review_score.notna()]
    paired=reviewed[reviewed.is_late.notna()].assign(punctuality=lambda d:np.where(d.is_late.eq(1),'Late','On time'))
    comparison=paired.groupby('punctuality').agg(reviewed=('review_score','count'),dissatisfied=('review_score',lambda s:s.le(2).sum()),mean_score=('review_score','mean')).reset_index()
    comparison['dissatisfaction_rate']=comparison.dissatisfied/comparison.reviewed
    metrics([('Orders with a review',f'{len(reviewed):,}','Latest answered review per order'),
        ('Low review scores',pct(reviewed.review_score.le(2).mean()),'Scores of 1 or 2 out of 5'),
        ('Average score',number(reviewed.review_score.mean(),2)+' / 5','All reviewed orders in the selection')])
    st.divider()
    left,right=st.columns([1.3,1],gap='large')
    with left:
        st.subheader('Low review scores by delivery outcome')
        fig=px.bar(comparison,x='punctuality',y='dissatisfaction_rate',color='punctuality',color_discrete_map={'On time':GREEN,'Late':RED},text_auto='.1%',labels={'punctuality':'','dissatisfaction_rate':'Share rating 1 or 2'})
        fig.update_layout(height=290,showlegend=False)
        fig.update_traces(textposition='outside',cliponaxis=False,width=.5)
        fig.update_yaxes(range=[0,max(.15,comparison.dissatisfaction_rate.max()*1.2)] if len(comparison) else [0,1])
        chart(fig,percent=True)
    with right:
        st.subheader('The comparison in numbers')
        table(comparison,labels={'punctuality':'Delivery','reviewed':'Reviewed orders','dissatisfied':'Scores 1–2','mean_score':'Mean score','dissatisfaction_rate':'Low-score rate'})
        st.caption('Only reviewed orders with a valid delivery outcome enter this comparison. Unreviewed customers are not represented.')
        note('Interpret with care','Delivery delays and low ratings are associated in this dataset. These figures do not isolate the effect of lateness from product, seller or customer differences.')
    st.subheader('How late were the late deliveries?')
    late=eligible[eligible.is_late.eq(1)].copy()
    late['delay_band']=pd.cut(late.delay_days,bins=[0,2,7,14,30,np.inf],labels=['1–2 days','3–7 days','8–14 days','15–30 days','Over 30 days'])
    severity=late.groupby('delay_band',observed=False).size().reset_index(name='orders')
    fig=px.bar(severity,x='delay_band',y='orders',text_auto=',.0f',labels={'delay_band':'Days after the promise','orders':'Late orders'},color_discrete_sequence=[PURPLE])
    fig.update_layout(height=250)
    chart(fig)

else:
    risks=read('fct_order_risk')
    features=read('ml_delivery_features')
    q=risks.merge(features[['order_id','item_value','customer_state','is_late','label_known_at','primary_category','promised_days','seller_prior_late_rate']],on='order_id',validate='one_to_one')
    q['replay_day']=pd.to_datetime(q.prediction_as_of).dt.date
    days=sorted(q.replay_day.unique())
    day=st.selectbox('Purchase day',days,index=len(days)//2,format_func=lambda d:d.strftime('%d %b %Y'))
    q=q[q.replay_day.eq(day)]
    if regions:
        q=q[q.customer_state.isin(regions)]
    evaluation=json.loads((ROOT/'reports/model_evaluation.json').read_text())
    quality=evaluation.get('probability_quality',{})
    st.caption(f'Each order is scored at purchase using the model available from {model_date:%d %B %Y}. This is retrospective historical revalidation, not an independent prospective test.')
    if page==PAGES[4]:
        metrics([('Purchases in this batch',f'{len(q):,}',day.strftime('%d %b %Y')),
            ('High-risk band',f'{q.risk_category.eq("High").sum():,}','Threshold set on the final calibration cohort'),
            ('Late cases found in top 50/day',pct(evaluation['test']['precision_at_50_daily']),f'{model_date:%B}–August evaluation · {evaluation["test"]["n"]:,} delivered orders')])
        st.divider()
        left,right=st.columns([2.3,1],gap='large')
        with left:
            st.subheader('Purchase-time review queue')
            reveal=st.checkbox('Show eventual delivery outcomes',value=False)
            show=['risk_rank','order_id','customer_state','risk_probability','risk_category','primary_category']
            if reveal:
                show+=['is_late','label_known_at']
            table(q.sort_values('risk_probability',ascending=False)[show].head(50),height=490)
            st.caption('Outcome columns are hidden until requested. They are never inputs to these purchase-time predictions.')
        with right:
            note('Revalidation complete: operational gate failed',f'Mean predicted risk was {pct(quality.get("mean_predicted_risk",np.nan))}; observed lateness was {pct(quality.get("observed_late_rate",np.nan))}. The pre-specified calibration gates did not pass. Operational use is not approved.','attention')
            st.subheader('Risk bands in this batch')
            bands=q.groupby('risk_category').size().reindex(['Low','Medium','High'],fill_value=0).reset_index(name='orders')
            fig=px.bar(bands,x='orders',y='risk_category',orientation='h',labels={'orders':'Purchases','risk_category':''},color='risk_category',color_discrete_map={'Low':GREEN,'Medium':ORANGE,'High':RED})
            fig.update_layout(showlegend=False)
            fig.update_layout(height=190)
            chart(fig)
        with st.expander('Validation results and model factors'):
            result=pd.DataFrame([['ROC-AUC',f'{evaluation["test"]["roc_auc"]:.3f}'],['Average precision',f'{evaluation["test"]["average_precision"]:.3f}'],
                ['Observed late prevalence',pct(evaluation['test']['late_rate'])],['Brier score — selected probabilities',f'{evaluation["test"]["brier"]:.4f}'],
                ['Brier score — constant baseline',f'{quality.get("constant_brier",np.nan):.4f}']],columns=['Measure','Test result'])
            table(result)
            st.caption('Lower Brier is better. Raw, sigmoid and isotonic probabilities were compared on forward validation before this evaluation period. All attempted versions and acceptance results are retained.')
            table(pd.DataFrame([{'Acceptance gate':k.replace('_',' '),'Passed':v} for k,v in quality.get('acceptance_gates',{}).items()]))
            importance=report('feature_importance').sort_values('ap_drop_mean')
            fig=px.bar(importance,x='ap_drop_mean',y='feature',orientation='h',labels={'ap_drop_mean':'Decrease in average precision','feature':''})
            fig.update_layout(height=370)
            chart(fig)
            st.caption('Permutation importance describes model associations, not the effect of an intervention.')
        download(q.sort_values('risk_probability',ascending=False),f'risk_review_{day}.csv','Download this purchase batch')
    else:
        note('Planning assumptions','The dataset contains no measured intervention effects or costs. Model probabilities also overestimate later-period risk. The amounts below demonstrate the allocation method; they are not validated savings.','attention')
        assumptions, results=st.columns([1,2.25],gap='large')
        with assumptions:
            st.subheader('Daily limits')
            capacity=st.number_input('Daily case capacity',0,1000,50,5)
            budget=st.number_input('Daily budget (BRL)',0.,50000.,500.,50.)
            region_cap=st.number_input('Maximum cases per state',0,1000,50,5)
            st.subheader('Cost and effectiveness')
            cost=st.number_input('Case cost (BRL)',0.,1000.,5.,1.)
            effect=st.slider('Assumed effectiveness',0.,1.,.2,.05)
            with st.expander('Delay impact assumptions'):
                impact=st.number_input('Base delay impact (BRL)',0.,10000.,150.,25.)
                fraction=st.slider('Additional impact / item value',0.,2.,.25,.05)
            scenario=Scenario(int(capacity),budget,cost,effect,impact,fraction,int(region_cap))
        result=optimize(q,scenario)
        selected=result[result.selected_for_intervention]
        with results:
            st.subheader('Selected cases')
            metrics([('Cases',f'{len(selected):,}',f'Limit: {capacity:,}'),
                ('Assumed cost',f'R$ {selected.intervention_cost.sum():,.0f}',f'Budget: R$ {budget:,.0f}'),
                ('Assumed net value',f'R$ {selected.expected_net_benefit.sum():,.0f}','Scenario estimate')])
            if not len(selected):
                st.caption('No cases selected under the current limits and assumptions.')
            show=['order_id','customer_state','risk_probability','expected_net_benefit']
            reveal=st.checkbox('Show eventual delivery outcomes',value=False)
            if reveal:
                show+=['is_late']
            table(selected.sort_values('expected_net_benefit',ascending=False)[show],height=360)
            download(result.sort_values(['selected_for_intervention','expected_net_benefit'],ascending=False),f'case_plan_{day}_{scenario.scenario_id}.csv','Download the full decision file')
            st.caption(f'{len(q)-len(selected):,} purchases left unselected. The allocator can leave capacity unused when expected value is nonpositive.')
            if reveal:
                known=selected[selected.is_late.notna()]
                st.caption(f'Later outcomes: {int(known.is_late.sum())} late deliveries among {len(known)} selected with valid outcomes; {len(selected)-len(known)} without an eligible result.')
        with st.expander('Compare policies across the test period'):
            comparison=report('strategy_comparison')
            names={'strategy':'Selection policy','selected':'Selected','labeled':'Valid outcomes','late_captured':'Late cases found','observed_precision':'Late-case precision','scenario_cost':'Assumed cost','scenario_net_benefit':'Assumed net value'}
            table(comparison,labels=names)
            st.caption('The policies share daily capacity, budget and state limits. Optimized value and late-case detection are different objectives; queue sizes can differ.')
        if (ROOT/'reports/scenario_sensitivity.csv').exists():
            with st.expander('Sensitivity to assumed effectiveness'):
                table(report('scenario_sensitivity')[['scenario_name','selected','assumed_cost','hypothetical_net_benefit']],labels={'scenario_name':'Assumption','selected':'Selected cases','assumed_cost':'Assumed cost','hypothetical_net_benefit':'Assumed net value'})

st.markdown('<div class="report-footer">Olist public historical data · Order-level delivery measures · Definitions and exclusions documented in the project notes</div>',unsafe_allow_html=True)
