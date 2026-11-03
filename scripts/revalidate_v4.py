"""Reproduce the retained v4 experiment without replacing the published model."""
from pathlib import Path
import json
import sys
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.common import ROOT
from src.experiments import rolling_v4 as experiment

def main():
    output=ROOT/'data/processed/revalidation_v4/reproduced'
    for name in ['reports','artifacts','data/processed']:
        (output/name).mkdir(parents=True,exist_ok=True)
    experiment.ROOT=output
    def write_json(name,value):
        (output/name).write_text(json.dumps(value,indent=2,default=str)+'\n')
    def publish_frame(name,frame):
        frame.to_parquet(output/'data/processed'/f'{name}.parquet',index=False)
        frame.to_csv(output/'reports'/f'{name}.csv',index=False)
    experiment.write_json=write_json
    experiment.publish_frame=publish_frame
    experiment.run(pd.read_parquet(ROOT/'data/processed/ml_delivery_features.parquet'))
    print(f'Experiment evidence: {output}. Published model and database were not changed.')

if __name__=='__main__':
    main()
