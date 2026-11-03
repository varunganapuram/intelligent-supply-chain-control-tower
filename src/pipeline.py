"""One-command reproducible pipeline. Fail fast and record stage durations."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime,timezone
import pandas as pd
from src.common import ROOT,load_env,write_json

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--from-stage',choices=['ingest','warehouse','analytics','features','models','optimization'],default='ingest')
    args=parser.parse_args()
    load_env()
    order=['ingest','warehouse','analytics','features','models','optimization']
    start=order.index(args.from_stage)
    timing={}
    from ingestion.load_olist import run as ingest
    from src.analytics import run as analytics
    from src.features import run as features
    from src.models import run as models
    from src.optimization import run as optimization
    def warehouse():
        dbt=Path(sys.executable).parent / ('dbt.exe' if os.name=='nt' else 'dbt')
        result=subprocess.run([str(dbt),'build','--project-dir',str(ROOT/'dbt_supply_chain'),
            '--profiles-dir',str(ROOT/'dbt_supply_chain')],cwd=ROOT,text=True,capture_output=True)
        (ROOT/'reports/dbt_build.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        print(result.stdout,flush=True)
        result.check_returncode()
        shutil.copy(ROOT/'dbt_supply_chain/target/run_results.json',ROOT/'reports/dbt_run_results.json')
    from pathlib import Path
    actions={'ingest':ingest,'warehouse':warehouse,'analytics':analytics,'features':features}
    for stage in order[start:]:
        print(f'Starting {stage}',flush=True)
        tick=time.perf_counter()
        if stage=='models':
            f=pd.read_parquet(ROOT/'data/processed/ml_delivery_features.parquet')
            models(f)
        elif stage=='optimization':
            optimization(pd.read_parquet(ROOT/'data/processed/fct_order_risk.parquet'),
                pd.read_parquet(ROOT/'data/processed/ml_delivery_features.parquet'))
        else:
            actions[stage]()
        timing[stage]=round(time.perf_counter()-tick,3)
        write_json('reports/pipeline_run.json',dict(status='running',completed=timing,run_at=datetime.now(timezone.utc).isoformat()))
    write_json('reports/pipeline_run.json',dict(status='success',completed=timing,run_at=datetime.now(timezone.utc).isoformat()))
    print(json.dumps(timing),flush=True)

if __name__=='__main__':
    main()
