"""Validate the historical portfolio handoff; report deployment readiness separately."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET
import nbformat

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.common import ROOT

def main():
    checks={}
    def report(name):
        return json.loads((ROOT/'reports'/f'{name}.json').read_text(encoding='utf-8-sig'))
    pipeline=report('pipeline_run')
    checks['full_pipeline']=pipeline['status']=='success' and set(pipeline['completed'])=={'ingest','warehouse','analytics','features','models','optimization'}
    dbt=report('dbt_run_results')
    checks['warehouse_no_errors']=all(r['status'] in {'success','pass','warn'} for r in dbt['results'])
    tests=ET.parse(ROOT/'reports/pytest_results.xml').getroot()
    suites=[tests] if tests.tag=='testsuite' else list(tests)
    checks['tests_no_failures_errors_or_skips']=bool(suites) and all(int(s.attrib.get('tests',0))>0 and all(int(s.attrib.get(k,0))==0 for k in ['failures','errors','skipped']) for s in suites)
    browser=report('browser_checks')
    checks['six_dashboard_pages']=browser['pages_opened']==6 and browser['zero_capacity_checked'] and not browser['errors']
    checks['powerbi_schema']=report('powerbi_validation')['json_schema_files_validated']==60
    native=report('native_powerbi_acceptance')
    checks['native_powerbi_data_and_dax']=native['status']=='passed' and native['refreshed_tables']==7 and native['comparisons']==6101 and all(c['passed'] for c in native['checks'])
    books=list((ROOT/'notebooks').glob('*.ipynb'))
    checks['executed_notebooks']=len(books)==3
    for path in books:
        cells=[c for c in nbformat.read(path,as_version=4).cells if c.cell_type=='code']
        checks['executed_notebooks'] &= bool(cells) and all(c.execution_count is not None and not any(o.output_type=='error' for o in c.outputs) for c in cells)
    final=report('final_artifact_checks')
    checks['offline_report_and_video']=final['offline_html_pages']==6 and not final['html_errors'] and final['video_full_decode']=='passed'
    checks['deliverables_present']=all((ROOT/name).is_file() and (ROOT/name).stat().st_size>0 for name in [
        'README.md','docs/executive_case_study.pdf','docs/dashboard_snapshot.html','docs/product_demo.mp4',
        'powerbi/ControlTower.pbip','powerbi/ControlTower.Report/definition/version.json','docs/model_card.md'])
    quality=report('calibration_revalidation')
    scientific_pass=all(quality['acceptance_gates'].values())
    checks['calibration_result_disclosed']=quality['retrospective_accepted']==scientific_pass and quality['independent_prospective_test'] is False and quality['operational_use_approved'] is False
    checks['failed_attempts_retained']=all((ROOT/f'reports/legacy_v{n}/calibration_revalidation.json').is_file() for n in [2,3,4])
    result=dict(scope='Historical Olist portfolio prototype; engineering and disclosure acceptance',
        submission_ready=all(checks.values()),checks=checks,
        calibration_statistical_acceptance=scientific_pass,
        operational_use_approved=quality['operational_use_approved'],
        limitations=['Retrospective evaluation data was previously examined.',
            'Native pixel review and full native visual interactions remain unverified.',
            'Calibration failed its fixed statistical gates; probabilities are research-only.',
            'One warehouse warning retains documented source timestamp anomalies.'])
    (ROOT/'reports/submission_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 0 if result['submission_ready'] else 1

if __name__=='__main__':
    sys.exit(main())
