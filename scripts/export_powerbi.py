"""Generate editable PBIP/PBIR and a TMSL import semantic model from verified exports.

The JSON report definitions are validated against Microsoft's public schemas.
Power BI Desktop rendering/refresh remains a separate acceptance check.
"""
from pathlib import Path
import json
import sys
import uuid
import hashlib
import urllib.request
import urllib.parse
import pandas as pd
import jsonschema
from referencing import Registry,Resource
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.common import ROOT,write_json

P=ROOT/'powerbi'
REPORT=P/'ControlTower.Report'
MODEL=P/'ControlTower.SemanticModel'
BASE='https://developer.microsoft.com/json-schemas/fabric/'

def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2),encoding='utf-8')

def schema(path):return BASE+path+'/schema.json'

def col(table,column):
    return {'Column':{'Expression':{'SourceRef':{'Entity':table}},'Property':column}}

def measure(name):
    return {'Measure':{'Expression':{'SourceRef':{'Entity':'Orders'}},'Property':name}}

def projection(field,name):
    return {'field':field,'queryRef':name,'nativeQueryRef':name}

MEASURES={
'Total Orders':('COUNTROWS(Orders)','#,0'),
'Eligible Orders':('COUNT(Orders[is_late])','#,0'),
'Excluded Orders':('[Total Orders]-[Eligible Orders]','#,0'),
'Late Orders':('SUM(Orders[is_late])','#,0'),
'Late Delivery %':('DIVIDE([Late Orders],[Eligible Orders])','0.0%'),
'On-Time Delivery %':('IF([Eligible Orders]>0,1-[Late Delivery %])','0.0%'),
'Average Delivery Days':('AVERAGE(Orders[delivery_days])','0.0'),
'P90 Delivery Days':('PERCENTILEX.INC(FILTER(Orders,NOT ISBLANK(Orders[is_late])),Orders[delivery_days],0.9)','0.0'),
'Average Delay Days':('AVERAGE(Orders[delay_days])','0.0'),
'Item Value':('SUM(Orders[item_value])','R$ #,0.00'),
'Reviewed Orders':('COUNT(Orders[review_score])','#,0'),
'Low Review Orders':('CALCULATE(COUNTROWS(Orders),Orders[review_score] IN {1,2})','#,0'),
'Dissatisfaction %':('DIVIDE([Low Review Orders],[Reviewed Orders])','0.0%'),
'Single-Seller Eligible':('CALCULATE([Eligible Orders],Orders[seller_count]=1)','#,0'),
'Single-Seller Late %':('DIVIDE(CALCULATE([Late Orders],Orders[seller_count]=1),[Single-Seller Eligible])','0.0%'),
'Scored Orders':('COUNTROWS(Risk)','#,0'),
'High Risk Orders':('CALCULATE(COUNTROWS(Risk),Risk[risk_category]="High")','#,0'),
'Mean Risk':('AVERAGE(Risk[risk_probability])','0.0%'),
'Selected Cases':('IF(HASONEVALUE(Scenario[scenario_id]),CALCULATE(COUNTROWS(Decisions),Decisions[selected_for_intervention]=TRUE()))','#,0'),
'Assumed Investigation Cost':('IF(HASONEVALUE(Scenario[scenario_id]),CALCULATE(SUM(Decisions[intervention_cost]),Decisions[selected_for_intervention]=TRUE()))','R$ #,0.00'),
'Simulated Net Benefit':('IF(HASONEVALUE(Scenario[scenario_id]),CALCULATE(SUM(Decisions[expected_net_benefit]),Decisions[selected_for_intervention]=TRUE()))','R$ #,0.00'),
'Model Test AP':('MAX(ModelEvaluation[average_precision])','0.000'),
'Model Precision at 50 per Day':('MAX(ModelEvaluation[precision_at_50_daily])','0.0%'),
'Scenario Assumed Effectiveness':('SELECTEDVALUE(Scenario[effectiveness])','0%'),
}

def main():
    evaluation=json.loads((ROOT/'reports/model_evaluation.json').read_text())
    pd.DataFrame([evaluation['test']]).drop(columns=['ap_95pct_day_bootstrap']).to_csv(ROOT/'reports/model_evaluation.csv',index=False)
    sources={'Orders':'fct_order','Date':'dim_date','Sellers':'dim_seller','Risk':'fct_order_risk',
        'Decisions':'fct_intervention_scenario','Scenario':'dim_scenario','ModelEvaluation':'model_evaluation'}
    tables=[]
    # Explicit types prevent text/date/decimal ambiguity in Power Query.
    datetime_columns={'order_purchase_timestamp','order_approved_at','order_delivered_carrier_date','order_delivered_customer_date',
        'order_estimated_delivery_date','purchase_date','first_shipping_limit','date_key','prediction_as_of','model_available_at'}
    numeric_columns={'item_count','seller_count','item_value','freight_value','weight_g','volume_cm3','distance_km','payment_value','payment_count',
        'review_score','is_late','delivery_days','delay_days','promised_days','handoff_days','transit_days','handoff_after_item_deadline',
        'latitude','longitude','year','month','weekday','risk_probability','risk_rank','expected_net_benefit','intervention_cost','assumed_delay_impact',
        'capacity','budget','cost','effectiveness','impact','value_fraction','region_cap'}
    for name,file in sources.items():
        frame=pd.read_csv(ROOT/'reports'/f'{file}.csv',nrows=5)
        columns=[];mtypes=[]
        for c in frame.columns:
            if c in datetime_columns:
                dtype,mtype='dateTime','type datetime'
            elif c in {'eligible_delivery','selected_for_intervention'}:
                dtype,mtype='boolean','type logical'
            elif c in numeric_columns or (name=='ModelEvaluation' and pd.api.types.is_numeric_dtype(frame[c])):
                dtype,mtype='double','type number'
            else:
                dtype,mtype='string','type text'
            columns.append(dict(name=c,dataType=dtype,sourceColumn=c,summarizeBy='none'))
            mtypes.append('{"'+c+'", '+mtype+'}')
        expression=['let',f'    Source = Csv.Document(File.Contents(DataFolder & "{file}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
            '    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
            '    EmptyToNull = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),',
            '    Typed = Table.TransformColumnTypes(EmptyToNull, {'+', '.join(mtypes)+'}, "en-US")',
            'in','    Typed']
        table=dict(name=name,columns=columns,partitions=[dict(name=name,mode='import',source=dict(type='m',expression=expression))])
        if name=='Orders':
            table['measures']=[dict(name=k,expression=v[0],formatString=v[1],description='See docs/kpi_dictionary.md; simulation measures are hypothetical.') for k,v in MEASURES.items()]
        tables.append(table)
    relationships=[]
    for src,sc,dst,dc in [('Orders','purchase_date','Date','date_key'),('Orders','primary_seller_id','Sellers','seller_id'),
                         ('Risk','order_id','Orders','order_id'),('Decisions','order_id','Orders','order_id'),('Decisions','scenario_id','Scenario','scenario_id')]:
        relationships.append(dict(name=str(uuid.uuid5(uuid.NAMESPACE_URL,f'{src}.{sc}->{dst}.{dc}')),fromTable=src,fromColumn=sc,toTable=dst,toColumn=dc,
            fromCardinality='many',toCardinality='one',crossFilteringBehavior='oneDirection'))
    bim=dict(name='ControlTower',compatibilityLevel=1600,model=dict(culture='en-US',defaultPowerBIDataSourceVersion='powerBI_V3',
        expressions=[dict(name='DataFolder',kind='m',expression='"'+str(ROOT/'reports').replace('\\','/')+'/" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]')],
        tables=tables,relationships=relationships))
    dump(MODEL/'model.bim',bim)
    dump(MODEL/'definition.pbism',{'$schema':schema('item/semanticModel/definitionProperties/1.0.0'),'version':'1.0','settings':{}})
    dump(P/'ControlTower.pbip',{'$schema':schema('pbip/pbipProperties/1.0.0'),'version':'1.0','artifacts':[{'report':{'path':'ControlTower.Report'}}],'settings':{'enableAutoRecovery':True}})
    dump(REPORT/'definition.pbir',{'$schema':schema('item/report/definitionProperties/2.0.0'),'version':'4.0','datasetReference':{'byPath':{'path':'../ControlTower.SemanticModel'}}})
    dump(REPORT/'definition/report.json',{'$schema':schema('item/report/definition/report/3.0.0'),'themeCollection':{}})
    dump(REPORT/'definition/version.json',{'$schema':schema('item/report/definition/versionMetadata/1.0.0'),'version':'2.0.0'})
    page_names=['Overview','Seller performance','Regional delivery','Customer reviews','Risk review','Case planning']
    page_ids=[f'page{i+1:02d}' for i in range(6)]
    dump(REPORT/'definition/pages/pages.json',{'$schema':schema('item/report/definition/pagesMetadata/1.0.0'),'pageOrder':page_ids,'activePageName':page_ids[0]})
    specs=[
        [('Total Orders','Eligible Orders','On-Time Delivery %','P90 Delivery Days'),('lineChart','Date','year_month',['Late Delivery %'],'Monthly punctuality'),('clusteredBarChart','Orders','order_status',['Total Orders'],'Status and exclusions')],
        [('Single-Seller Eligible','Single-Seller Late %','Average Delivery Days','Excluded Orders'),('clusteredBarChart','Sellers','seller_state',['Single-Seller Late %'],'Single-seller late rate by origin state'),('tableEx','Sellers','seller_id',['Single-Seller Eligible','Single-Seller Late %'],'Seller diagnostic table: assess sample sizes')],
        [('Eligible Orders','Late Delivery %','Average Delivery Days','P90 Delivery Days'),('clusteredBarChart','Orders','customer_state',['Late Delivery %'],'Customer state reliability'),('clusteredBarChart','Orders','primary_category',['Average Delivery Days'],'Primary category duration')],
        [('Reviewed Orders','Dissatisfaction %','Average Delay Days','Late Orders'),('clusteredColumnChart','Orders','review_score',['Reviewed Orders'],'Review distribution'),('clusteredColumnChart','Orders','is_late',['Dissatisfaction %'],'Low-review rate by delivery outcome')],
        [('Scored Orders','High Risk Orders','Model Test AP','Model Precision at 50 per Day'),('clusteredColumnChart','Risk','risk_category',['Scored Orders'],'Purchase-time risk bands'),('tableEx','Risk','order_id',[], 'Purchase-time risk queue')],
        [('Selected Cases','Assumed Investigation Cost','Simulated Net Benefit','Scenario Assumed Effectiveness'),('clusteredColumnChart','Decisions','replay_day',['Selected Cases'],'Cases selected per purchase day'),('tableEx','Decisions','order_id',[],'Scenario decisions: hypothetical financial effects')]
    ]
    for i,(pid,label,spec) in enumerate(zip(page_ids,page_names,specs)):
        folder=REPORT/'definition/pages'/pid
        dump(folder/'page.json',{'$schema':schema('item/report/definition/page/2.0.0'),'name':pid,'displayName':label,'displayOption':'FitToPage','width':1280,'height':720})
        z=0
        def visual(kind,roles,title,x,y,w,h):
            nonlocal z
            z+=1; vid=f'{pid}v{z:02d}'
            title_objects={'title':[{'properties':{'show':{'expr':{'Literal':{'Value':'true'}}},
                'text':{'expr':{'Literal':{'Value':"'"+title.replace("'","''")+"'"}}}}}]}
            obj={'$schema':schema('item/report/definition/visualContainer/2.4.0'),'name':vid,
                'position':dict(x=x,y=y,z=z,width=w,height=h,tabOrder=z),
                'visual':dict(visualType=kind,query={'queryState':{role:{'projections':ps} for role,ps in roles.items()}},
                    visualContainerObjects=title_objects)}
            dump(folder/'visuals'/vid/'visual.json',obj)
        for j,m in enumerate(spec[0]):
            visual('card',{'Values':[projection(measure(m),f'Orders.{m}')]},m,20+j*315,20,300,140)
        for j,(kind,t,c,ms,title) in enumerate(spec[1:]):
            if kind=='tableEx':
                ps=[projection(col(t,c),f'{t}.{c}')]+[projection(measure(m),f'Orders.{m}') for m in ms]
                if t=='Risk':
                    ps += [projection(col(t,c2),f'{t}.{c2}') for c2 in ['prediction_as_of','risk_probability','risk_category','risk_rank']]
                if t=='Decisions':
                    ps += [projection(col(t,c2),f'{t}.{c2}') for c2 in ['selected_for_intervention','expected_net_benefit','solver_status']]
                roles={'Values':ps}
            else:
                roles={'Category':[projection(col(t,c),f'{t}.{c}')], 'Y':[projection(measure(m),f'Orders.{m}') for m in ms]}
            visual(kind,roles,title,20+j*630,180,610,420)
        # Slicers filter the semantic graph; day slicer constrains daily scenario interpretation.
        slicers=[('Date','year_month'),('Orders','customer_state')]
        if i==5:slicers=[('Decisions','replay_day'),('Scenario','scenario_name')]
        if i==4:slicers=[('Risk','prediction_as_of'),('Orders','customer_state')]
        for j,(t,c) in enumerate(slicers):
            visual('slicer',{'Values':[projection(col(t,c),f'{t}.{c}')]},c,20+j*630,620,610,80)
    dump(P/'theme.json',{'name':'Delivery review','dataColors':['#2563eb','#dc2626','#16a34a','#9333ea','#ea580c'],'background':'#ffffff','foreground':'#000000','tableAccent':'#2563eb'})
    (P/'measures.dax').write_text('\n\n'.join(f'{name} = {expr}' for name,(expr,fmt) in MEASURES.items()),encoding='utf-8')
    # Validate every report file, following public schema references with a small local cache.
    cache=P/'schemas';cache.mkdir(exist_ok=True)
    schema_index={}
    def retrieve(uri):
        filename=hashlib.sha256(uri.encode()).hexdigest()+'.json'
        schema_index[uri]=filename
        file=cache/filename
        if not file.exists():
            file.write_bytes(urllib.request.urlopen(uri,timeout=60).read())
        return Resource.from_contents(json.loads(file.read_text(encoding='utf-8-sig')))
    registry=Registry(retrieve=retrieve)
    count=0
    for file in [P/'ControlTower.pbip',MODEL/'definition.pbism',REPORT/'definition.pbir']+list((REPORT/'definition').rglob('*.json')):
        obj=json.loads(file.read_text())
        resource=retrieve(obj['$schema'])
        Validator=jsonschema.validators.validator_for(resource.contents)
        Validator(resource.contents,registry=registry).validate(obj)
        count+=1
    dump(cache/'index.json',schema_index)
    write_json('reports/powerbi_validation.json',dict(json_schema_files_validated=count,
        status='JSON schemas validated. Native Desktop refresh/DAX evidence is recorded separately in native_powerbi_acceptance.json; no pixel screenshot acceptance is implied.',
        semantic_model='TMSL model.bim; CSV Import with DataFolder parameter',pages=6))
    print(f'Power BI: {count} JSON files validated; see separate native Desktop acceptance evidence')

if __name__=='__main__':main()
