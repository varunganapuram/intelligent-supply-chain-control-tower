"""Optional browser acceptance check. Start Streamlit first; Chrome required."""
from pathlib import Path
import sys,json,argparse
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.common import ROOT

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8501');args=parser.parse_args()
    pages=['Overview','Seller performance','Regional delivery','Customer reviews','Risk review','Case planning']
    out=ROOT/'docs/screenshots';out.mkdir(exist_ok=True)
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        page=browser.new_page(viewport={'width':1512,'height':1100},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.url,wait_until='networkidle')
        page.get_by_role('heading',name=pages[0],exact=True).wait_for(timeout=60000)
        for i,name in enumerate(pages):
            page.get_by_text(name,exact=True).first.click()
            page.get_by_role('heading',name=name,exact=True).wait_for(timeout=60000)
            page.wait_for_timeout(2500)
            if i<5:
                page.locator('.js-plotly-plot').first.wait_for(timeout=60000)
                page.wait_for_function("() => [...document.querySelectorAll('.js-plotly-plot')].every(e => e._fullLayout && e.querySelector('.main-svg'))",timeout=60000)
            page.wait_for_timeout(1800)
            if page.locator('[data-testid="stException"]').count():errors.append(page.locator('[data-testid="stException"]').inner_text())
            page.screenshot(path=str(out/f'{i+1:02d}.png'),full_page=True)
        page.get_by_role('spinbutton',name='Daily case capacity').fill('0')
        page.get_by_role('spinbutton',name='Daily case capacity').press('Enter')
        page.wait_for_timeout(2000)
        if page.locator('[data-testid="stException"]').count():errors.append(page.locator('[data-testid="stException"]').inner_text())
        browser.close()
    (ROOT/'reports/browser_checks.json').write_text(json.dumps(dict(pages_opened=6,zero_capacity_checked=True,errors=errors),indent=2))
    assert not errors,errors
    print('Six dashboard pages and zero-capacity scenario passed')

if __name__=='__main__':main()
