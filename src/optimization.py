"""Integer CP-SAT allocation; all financial effects are hypothetical scenarios."""
from dataclasses import dataclass, asdict
import hashlib
import json
import numpy as np
import pandas as pd
from ortools.sat.python import cp_model
from src.common import ROOT, publish_frame, write_json

@dataclass(frozen=True)
class Scenario:
    capacity: int = 50
    budget: float = 500.
    cost: float = 5.
    effectiveness: float = .20
    impact: float = 150.
    value_fraction: float = .25
    region_cap: int = 50

    def validate(self):
        if self.capacity<0 or self.region_cap<0 or self.budget<0 or self.cost<0 or self.impact<0 or self.value_fraction<0 or not 0<=self.effectiveness<=1:
            raise ValueError('Nonnegative constraints and effectiveness between 0 and 1 required')
        if not all(np.isfinite(v) for v in asdict(self).values()):
            raise ValueError('Scenario inputs must be finite')

    @property
    def scenario_id(self):
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True).encode()).hexdigest()[:12]

def optimize(orders, scenario=Scenario()):
    scenario.validate()
    df = orders.copy().reset_index(drop=True)
    if df.order_id.duplicated().any():
        raise ValueError('One candidate row per order required')
    p = df.risk_probability.to_numpy(dtype=float)
    if not np.isfinite(p).all() or ((p<0)|(p>1)).any():
        raise ValueError('Probabilities must be finite and in [0,1]')
    df['assumed_delay_impact'] = scenario.impact+scenario.value_fraction*pd.to_numeric(df.item_value,errors='coerce').fillna(0).clip(lower=0)
    df['intervention_cost'] = scenario.cost
    df['expected_net_benefit'] = p*scenario.effectiveness*df.assumed_delay_impact-scenario.cost
    df['selected_for_intervention'] = False
    model = cp_model.CpModel()
    x = [model.new_bool_var(f'x_{i}') for i in range(len(df))]
    model.add(sum(x)<=scenario.capacity)
    cost_cents = int(np.ceil(scenario.cost*100-1e-9))
    model.add(sum(cost_cents*v for v in x)<=int(np.floor(scenario.budget*100+1e-9)))
    for state,indices in df.groupby('customer_state',dropna=False).groups.items():
        model.add(sum(x[i] for i in indices)<=scenario.region_cap)
    coeff = np.rint(df.expected_net_benefit.to_numpy()*10000).astype(int)
    for i in range(len(df)):
        if coeff[i]<=0:
            model.add(x[i]==0)
    model.maximize(sum(int(coeff[i])*x[i] for i in range(len(df))))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds=5
    solver.parameters.num_search_workers=1
    solver.parameters.random_seed=42
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        raise RuntimeError(f'Optimization status {solver.status_name(status)}')
    df['selected_for_intervention'] = pd.Series([bool(solver.value(v)) for v in x],dtype=bool)
    df['scenario_id'] = scenario.scenario_id
    df['solver_status'] = solver.status_name(status)
    selected = df[df.selected_for_intervention]
    assert len(selected)<=scenario.capacity and selected.intervention_cost.sum()<=scenario.budget+1e-8
    assert selected.groupby('customer_state',dropna=False).size().max()<=scenario.region_cap if len(selected) else True
    return df

def baseline_selection(g, column, scenario, rng=None):
    ordered = g.sample(frac=1,random_state=rng) if column is None else g.sort_values(column,ascending=column=='promised_days',kind='stable')
    # All comparators obey the same capacity, budget and regional caps.
    selected=[]; states={}; spent=0.
    for i,row in ordered.iterrows():
        state=row.customer_state
        if len(selected)>=scenario.capacity:
            break
        if spent+scenario.cost>scenario.budget+1e-9 or states.get(state,0)>=scenario.region_cap:
            continue
        selected.append(i); spent+=scenario.cost; states[state]=states.get(state,0)+1
    return g.loc[selected]

def run(risks, features):
    observed = features[['order_id','is_late','seller_prior_late_rate','promised_days','item_value','customer_state']]
    candidates = risks.merge(observed,on='order_id',validate='one_to_one')
    candidates['replay_day'] = candidates.prediction_as_of.dt.date.astype(str)
    scenario = Scenario()
    scenarios=[Scenario(effectiveness=e) for e in [.1,.2,.3]]
    outputs=[]; comparisons=[]
    for day,g in candidates.groupby('replay_day',sort=True):
        allocated = optimize(g,scenario)
        outputs.append(allocated)
        alternatives = [('Optimized scenario',allocated[allocated.selected_for_intervention]),
            ('Highest risk',baseline_selection(g,'risk_probability',scenario)),
            ('Shortest promise',baseline_selection(g,'promised_days',scenario)),
            ('Prior seller risk',baseline_selection(g,'seller_prior_late_rate',scenario))]
        alternatives += [(f'Random seed {seed}',baseline_selection(g,None,scenario,seed)) for seed in range(10)]
        for name,s in alternatives:
            impact = scenario.impact+scenario.value_fraction*s.item_value.fillna(0)
            comparisons.append(dict(day=day,strategy=name,selected=len(s),labeled=int(s.is_late.notna().sum()),
                late_captured=int(s.is_late.sum()),predicted_late=float(s.risk_probability.sum()),
                scenario_cost=len(s)*scenario.cost,
                scenario_net_benefit=float((s.risk_probability*scenario.effectiveness*impact-scenario.cost).sum())))
    full=pd.concat(outputs,ignore_index=True)
    for alternate in scenarios:
        if alternate.scenario_id==scenario.scenario_id:
            continue
        outputs_extra=[optimize(g,alternate) for _,g in candidates.groupby('replay_day',sort=True)]
        full=pd.concat([full,*outputs_extra],ignore_index=True)
    cols=['order_id','prediction_as_of','scenario_id','replay_day','selected_for_intervention','expected_net_benefit','intervention_cost','assumed_delay_impact','solver_status']
    publish_frame('fct_intervention_scenario',full[cols])
    assumptions=pd.DataFrame([dict(scenario_id=s.scenario_id,scenario_name=f'Assumed effectiveness {s.effectiveness:.0%}',**asdict(s),
        interpretation='Hypothetical BRL amounts; no measured intervention effects') for s in scenarios])
    publish_frame('dim_scenario',assumptions)
    chosen=full[full.selected_for_intervention]
    sensitivity=chosen.groupby('scenario_id').agg(selected=('order_id','size'),assumed_cost=('intervention_cost','sum'),
        hypothetical_net_benefit=('expected_net_benefit','sum')).reset_index()
    assumptions.merge(sensitivity,on='scenario_id',how='left').fillna({'selected':0,'assumed_cost':0,'hypothetical_net_benefit':0}).to_csv(ROOT/'reports/scenario_sensitivity.csv',index=False)
    comparison=pd.DataFrame(comparisons)
    comparison.to_csv(ROOT/'reports/strategy_daily.csv',index=False)
    totals=comparison.groupby('strategy')[['selected','labeled','late_captured','predicted_late','scenario_cost','scenario_net_benefit']].sum()
    totals['observed_precision']=totals.late_captured/totals.labeled.replace(0,np.nan)
    totals.to_csv(ROOT/'reports/strategy_comparison.csv')
    return full,totals
