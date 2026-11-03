"""Deployment gate, distinct from successful historical-research pipeline execution."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]

def main():
    result=json.loads((ROOT/'reports/calibration_revalidation.json').read_text())
    failed=[name for name,passed in result['acceptance_gates'].items() if not passed]
    if failed or not result.get('operational_use_approved',False):
        print('NOT APPROVED FOR OPERATIONAL USE')
        if failed:
            print('Failed calibration gates: '+', '.join(failed))
        print('Historical revalidation is complete. Representative prospective validation and an authorized deployment review are required.')
        return 1
    print('Model readiness gate passed')
    return 0

if __name__=='__main__':
    sys.exit(main())
