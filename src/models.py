"""Frozen chronological train/selection/calibration/test with explicit label maturity."""
import hashlib
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.dummy import DummyClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss
from sklearn.inspection import permutation_importance
from sklearn.isotonic import IsotonicRegression
from xgboost import XGBClassifier
from src.common import ROOT, write_json, publish_frame
from src.features import FEATURES, NUMERIC, CATEGORICAL

VERSION = 'purchase-v3-frozen-20180701'
AVAILABLE_AT = pd.Timestamp('2018-07-01')

def preprocess():
    return ColumnTransformer([
        ('numeric', Pipeline([('imputer',SimpleImputer(strategy='median',keep_empty_features=True)),('scale',StandardScaler())]),NUMERIC),
        ('category',Pipeline([('imputer',SimpleImputer(strategy='most_frequent')),('encode',OneHotEncoder(handle_unknown='ignore',sparse_output=True))]),CATEGORICAL)])

def daily_ranking(y, p, dates, k=50):
    df = pd.DataFrame({'y':np.asarray(y,dtype=int),'p':p,'day':pd.to_datetime(dates).dt.date.to_numpy()})
    top = df.sort_values('p',ascending=False,kind='stable').groupby('day',sort=False).head(k)
    return dict(precision_at_50_daily=float(top.y.mean()),recall_at_50_daily=float(top.y.sum()/max(df.y.sum(),1)),
        selected=int(len(top)),late_captured=int(top.y.sum()))

def metrics(y,p,dates):
    y = np.asarray(y,dtype=int)
    return dict(n=len(y),late_rate=float(y.mean()),roc_auc=float(roc_auc_score(y,p)),
        average_precision=float(average_precision_score(y,p)),brier=float(brier_score_loss(y,p)),
        log_loss=float(log_loss(y,p)),**daily_ranking(y,p,dates))

def logit(p):
    p = np.clip(p,1e-6,1-1e-6)
    return np.log(p/(1-p)).reshape(-1,1)

class ProbabilityCalibrator:
    """Common logit-to-probability interface; the raw option is identity."""
    def __init__(self,method='raw'):
        self.method=method

    def fit(self,X,y):
        if self.method=='sigmoid':
            self.estimator=LogisticRegression(C=1.,max_iter=1000).fit(X,y)
        elif self.method=='isotonic':
            self.estimator=IsotonicRegression(out_of_bounds='clip').fit(np.asarray(X).ravel(),y)
        elif self.method!='raw':
            raise ValueError('Unknown calibration method')
        return self

    def predict_proba(self,X):
        if self.method=='raw':
            p=1/(1+np.exp(-np.asarray(X).ravel()))
        elif self.method=='sigmoid':
            p=self.estimator.predict_proba(X)[:,1]
        else:
            p=self.estimator.predict(np.asarray(X).ravel())
        p=np.clip(p,1e-6,1-1e-6)
        return np.column_stack([1-p,p])

def score(bundle, frame):
    missing = set(bundle['features'])-set(frame.columns)
    if missing:
        raise ValueError(f'Feature schema mismatch: missing {sorted(missing)}')
    p = bundle['model'].predict_proba(frame[bundle['features']])[:,1]
    return bundle['calibrator'].predict_proba(logit(p))[:,1]

def run(f):
    t = f.prediction_as_of
    known = f.label_known_at
    # Frozen selection protocol: docs/revalidation_protocol_v3.md.
    train = f[(t<'2018-01-01')&(known<'2018-02-01')&f.is_late.notna()]
    method_fit = f[(t>='2018-02-01')&(t<'2018-03-01')&(known<'2018-04-01')&f.is_late.notna()]
    validation = f[(t>='2018-04-01')&(t<'2018-05-01')&(known<'2018-06-01')&f.is_late.notna()]
    calibration = f[(t>='2018-05-01')&(t<'2018-06-01')&(known<AVAILABLE_AT)&f.is_late.notna()]
    test = f[(t>=AVAILABLE_AT)&(t<'2018-09-01')&f.is_late.notna()]
    splits = {name:dict(n=len(df),purchase_min=str(df.prediction_as_of.min()),purchase_max=str(df.prediction_as_of.max()),
        max_label_known_at=str(df.label_known_at.max())) for name,df in [('train',train),('method_fit',method_fit),('validation',validation),('calibration',calibration),('test',test)]}
    assert min(len(train),len(validation),len(calibration),len(test))>500
    coverage=[]
    cutoffs={'train':'2018-02-01','method_fit':'2018-04-01','validation':'2018-06-01','calibration':'2018-07-01'}
    for name,pstart,pend,cutoff in [('train','2016-01-01','2018-01-01','2018-02-01'),
        ('method_fit','2018-02-01','2018-03-01','2018-04-01'),
        ('validation','2018-04-01','2018-05-01','2018-06-01'),
        ('calibration','2018-05-01','2018-06-01','2018-07-01'),('test','2018-07-01','2018-09-01',None)]:
        cohort=f[(t>=pstart)&(t<pend)]
        matured=cohort.is_late.notna() if cutoff is None else cohort.is_late.notna()&(cohort.label_known_at<cutoff)
        coverage.append(dict(split=name,all_purchases=len(cohort),eventually_eligible=int(cohort.is_late.notna().sum()),
            labels_usable_at_cutoff=int(matured.sum()),excluded_or_unresolved=int(cohort.is_late.isna().sum()),
            eligible_but_not_yet_known=int((cohort.is_late.notna()&~matured).sum()),label_cutoff=cutoff or 'Final historical extract'))
    pd.DataFrame(coverage).to_csv(ROOT/'reports/label_coverage.csv',index=False)
    X, y = train[FEATURES],train.is_late.astype(int)
    candidates = {
        'constant':DummyClassifier(strategy='prior'),
        'logistic':LogisticRegression(C=.3,max_iter=1500,random_state=42),
        'xgboost_depth3':XGBClassifier(n_estimators=220,max_depth=3,learning_rate=.05,subsample=.85,colsample_bytree=.85,reg_lambda=5,random_state=42,n_jobs=4,eval_metric='logloss'),
        'xgboost_depth5':XGBClassifier(n_estimators=220,max_depth=5,learning_rate=.05,subsample=.85,colsample_bytree=.85,reg_lambda=8,min_child_weight=15,random_state=42,n_jobs=4,eval_metric='logloss')}
    fitted, comparisons = {}, []
    for name,est in candidates.items():
        pipeline = Pipeline([('preprocess',preprocess()),('estimator',est)])
        pipeline.fit(X,y)
        raw_val=pipeline.predict_proba(validation[FEATURES])[:,1]
        raw_fit=pipeline.predict_proba(method_fit[FEATURES])[:,1]
        for method in (['raw'] if name=='constant' else ['raw','sigmoid','isotonic']):
            transform=ProbabilityCalibrator(method).fit(logit(raw_fit),method_fit.is_late.astype(int))
            p=transform.predict_proba(logit(raw_val))[:,1]
            comparisons.append(dict(model=name+'__'+method,split='validation',**metrics(validation.is_late,p,validation.prediction_as_of)))
        fitted[name] = pipeline
        print(f'Compared {name} and calibration methods on April validation',flush=True)
    eligible_pairs=[c for c in comparisons if c['average_precision']>=1.05*c['late_rate']]
    best=min(eligible_pairs or comparisons,key=lambda c:(c['brier'],-c['average_precision']))['model']
    base_name,method=best.split('__')
    model = fitted[base_name]
    logistic = fitted['logistic']
    pd.DataFrame({'encoded_feature':logistic.named_steps['preprocess'].get_feature_names_out(),
        'coefficient':logistic.named_steps['estimator'].coef_[0]}).to_csv(ROOT/'reports/adjusted_logistic_coefficients.csv',index=False)
    calibrator = ProbabilityCalibrator(method).fit(logit(model.predict_proba(calibration[FEATURES])[:,1]),calibration.is_late.astype(int))
    bundle = dict(model=model,calibrator=calibrator,features=FEATURES,model_version=VERSION,
        available_at=AVAILABLE_AT,selected_model=best,selected_calibration_method=method,
        operational_use_approved=False,intended_use='historical_research_only')
    calibration_p = score(bundle,calibration)
    high, medium = float(np.quantile(calibration_p,.90)),float(np.quantile(calibration_p,.70))
    bundle['thresholds'] = dict(high=high,medium=medium)
    joblib.dump(bundle,ROOT/'artifacts/delivery_model.joblib')
    for name in ['constant','logistic','xgboost_depth3','xgboost_depth5']:
        p = fitted[name].predict_proba(test[FEATURES])[:,1]
        comparisons.append(dict(model=name,split='test_frozen_candidate',**metrics(test.is_late,p,test.prediction_as_of)))
    ptest = score(bundle,test)
    test_result = metrics(test.is_late,ptest,test.prediction_as_of)
    constant_test = next(c for c in comparisons if c['model']=='constant' and c['split']=='test_frozen_candidate')
    calibration_prior=float(calibration.is_late.mean())
    baseline_brier=float(brier_score_loss(test.is_late,np.full(len(test),calibration_prior)))
    reliability=pd.DataFrame({'probability':ptest,'outcome':test.is_late.to_numpy(dtype=int)})
    reliability['bin']=pd.qcut(reliability.probability,q=10,duplicates='drop')
    reliability=reliability.groupby('bin',observed=True).agg(n=('outcome','size'),predicted=('probability','mean'),observed=('outcome','mean')).reset_index()
    ece=float(np.average(np.abs(reliability.predicted-reliability.observed),weights=reliability.n))
    monthly=[]
    for month,g in test.assign(p=ptest,month=test.prediction_as_of.dt.to_period('M').astype(str)).groupby('month'):
        monthly.append(dict(month=month,n=len(g),predicted=float(g.p.mean()),observed=float(g.is_late.mean()),
            absolute_bias=float(abs(g.p.mean()-g.is_late.mean())),brier=float(brier_score_loss(g.is_late,g.p))))
    monthly_frame=pd.DataFrame(monthly)
    gates=dict(finite_probabilities=bool(np.isfinite(ptest).all() and ((ptest>=0)&(ptest<=1)).all()),
        pooled_bias_within_2pp=bool(abs(ptest.mean()-test.is_late.mean())<=.02),
        equal_frequency_ece_within_2pp=ece<=.02,
        brier_beats_calibration_prior=test_result['brier']<=baseline_brier,
        monthly_bias_within_3pp=bool(monthly_frame.absolute_bias.le(.03).all()))
    accepted=all(gates.values())
    probability_quality=dict(mean_predicted_risk=float(ptest.mean()),observed_late_rate=float(test.is_late.mean()),
        calibrated_brier=test_result['brier'],constant_brier=constant_test['brier'],
        calibration_prior=calibration_prior,calibration_prior_brier=baseline_brier,expected_calibration_error=ece,
        retrospective_accepted=accepted,acceptance_gates=gates,operational_use_approved=False,
        status='Retrospective revalidation passed all pre-specified statistical gates; prospective operational validation is not established'
            if accepted else 'Retrospective revalidation completed with failed acceptance gates; not accepted for operational probability use')
    comparisons.append(dict(model=best+'_calibrated',split='test_final',**test_result))
    # Bootstrap AP uncertainty on days, preserving within-day clustering.
    rng = np.random.default_rng(42)
    test_days = test.prediction_as_of.dt.date.to_numpy()
    days = np.unique(test_days)
    day_indices = {d:np.flatnonzero(test_days==d) for d in days}
    samples = [];bias_samples=[];brier_gain_samples=[]
    yt = test.is_late.to_numpy(dtype=int)
    for _ in range(150):
        idx = np.concatenate([day_indices[d] for d in rng.choice(days,len(days),replace=True)])
        samples.append(average_precision_score(yt[idx],ptest[idx]))
        bias_samples.append(float((ptest[idx]-yt[idx]).mean()))
        brier_gain_samples.append(float(((yt[idx]-calibration_prior)**2-(yt[idx]-ptest[idx])**2).mean()))
    test_result['ap_95pct_day_bootstrap'] = np.quantile(samples,[.025,.975]).tolist()
    probability_quality['mean_bias_95pct_day_bootstrap']=np.quantile(bias_samples,[.025,.975]).tolist()
    probability_quality['brier_gain_95pct_day_bootstrap']=np.quantile(brier_gain_samples,[.025,.975]).tolist()
    reliability.to_csv(ROOT/'reports/calibration.csv',index=False)
    monthly_frame.to_csv(ROOT/'reports/calibration_monthly.csv',index=False)
    write_json('reports/calibration_revalidation.json',dict(protocol='docs/revalidation_protocol_v3.md',model_version=VERSION,
        selected_model=best,selected_calibration_method=method,
        evaluation_purchases='July-August 2018',previously_examined_historical_data=True,
        independent_prospective_test=False,**probability_quality))
    pd.DataFrame(comparisons).to_csv(ROOT/'reports/model_comparison.csv',index=False)
    segments=[]
    for field in ['customer_state','primary_category']:
        for segment, g in test.assign(p=ptest).groupby(field):
            if len(g)>=100 and g.is_late.nunique()==2:
                segments.append(dict(field=field,segment=segment,**metrics(g.is_late,g.p,g.prediction_as_of)))
    for name,mask in [('new_seller',test.seller_prior_orders.eq(0)),('established_seller',test.seller_prior_orders.gt(0)),('distance_missing',test.distance_km.isna())]:
        g=test[mask]
        if len(g)>100 and g.is_late.nunique()==2:
            segments.append(dict(field='coverage',segment=name,**metrics(g.is_late,ptest[mask],g.prediction_as_of)))
    pd.DataFrame(segments).to_csv(ROOT/'reports/model_segments.csv',index=False)
    # Permutation explains ranking associations, not intervention effects.
    sample = test.sample(min(3000,len(test)),random_state=42)
    importance = permutation_importance(model,sample[FEATURES],sample.is_late.astype(int),scoring='average_precision',n_repeats=3,random_state=42,n_jobs=1)
    pd.DataFrame({'feature':FEATURES,'ap_drop_mean':importance.importances_mean,'ap_drop_std':importance.importances_std}).sort_values('ap_drop_mean',ascending=False).to_csv(ROOT/'reports/feature_importance.csv',index=False)
    for name,g in [('train',train),('validation',validation),('calibration',calibration),('test',test)]:
        pd.DataFrame({'feature':NUMERIC,'missing_rate':g[NUMERIC].isna().mean().values,'mean':g[NUMERIC].mean().values}).to_csv(ROOT/f'reports/feature_profile_{name}.csv',index=False)
    drift=[]
    for name,g in [('validation',validation),('calibration',calibration),('test',test)]:
        for c in CATEGORICAL:
            drift.append(dict(split=name,feature=c,unseen_category_rate=float((~g[c].isin(train[c].unique())).mean()),
                unique_categories=int(g[c].nunique()),training_categories=int(train[c].nunique())))
    pd.DataFrame(drift).to_csv(ROOT/'reports/categorical_drift.csv',index=False)
    replay = f[(t>=AVAILABLE_AT)&(t<'2018-09-01')].copy()
    p = score(bundle,replay)
    risks = replay[['order_id','prediction_as_of']].copy()
    risks['scoring_run_id'] = VERSION
    risks['model_version'] = VERSION
    risks['model_available_at'] = AVAILABLE_AT
    risks['risk_probability'] = p
    risks['risk_category'] = np.where(p>=high,'High',np.where(p>=medium,'Medium','Low'))
    risks['risk_rank'] = risks.assign(day=risks.prediction_as_of.dt.date).groupby('day').risk_probability.rank(method='first',ascending=False).astype(int)
    publish_frame('fct_order_risk',risks)
    # Representative one-feature reference comparisons, explicitly not additive/causal SHAP.
    examples=[]
    reference = calibration[FEATURES].copy()
    for idx in np.argsort(ptest)[-5:][::-1]:
        row = test.iloc[[idx]][FEATURES].copy()
        original = float(score(bundle,row)[0])
        for c in FEATURES:
            alternate = row.copy()
            alternate[c] = reference[c].median() if c in NUMERIC else reference[c].mode().iloc[0]
            examples.append(dict(order_id=test.iloc[idx].order_id,feature=c,value=str(row.iloc[0][c]),
                original_risk=original,reference_risk=float(score(bundle,alternate)[0])))
    pd.DataFrame(examples).to_csv(ROOT/'reports/local_reference_explanations.csv',index=False)
    report = dict(selected_model=best,model_version=VERSION,model_available_at=str(AVAILABLE_AT),
        feature_schema_sha256=hashlib.sha256(json.dumps(FEATURES).encode()).hexdigest(),
        splits=splits,label_cutoffs=cutoffs,selected_calibration_method=method,probability_quality=probability_quality,thresholds=dict(high=high,medium=medium,rule='Calibration probabilities: 90th and 70th percentiles; ties may increase workload'),
        calibration_workload=dict(high=int((calibration_p>=high).sum()),total=len(calibration)),test=test_result)
    write_json('reports/model_evaluation.json',report)
    return risks,report
