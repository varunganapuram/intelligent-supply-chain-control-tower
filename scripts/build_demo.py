"""Build a narrated walkthrough from screenshots of the running dashboard (Windows)."""
from pathlib import Path
import sys
import json
import subprocess
import tempfile
import wave
import imageio_ffmpeg
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.common import ROOT

def main():
    m=json.loads((ROOT/'reports/model_evaluation.json').read_text())
    names=['Overview','Seller performance','Regional delivery','Customer reviews','Risk review','Case planning']
    ap=m['test']['average_precision'];precision=m['test']['precision_at_50_daily']
    narration=[
        'This report looks at delivery performance in the public Olist marketplace dataset. This is a historical operations prototype, using more than ninety nine thousand orders from twenty sixteen through twenty eighteen. The decision is practical: where are delivery problems concentrated, which purchases look risky, and which cases should a limited operations team review? The overview shows ninety three point two three percent on time delivery among eligible completed deliveries. Almost three thousand canceled, unresolved, missing or invalid outcomes are reported separately. Behind the dashboard, Python loads unchanged source files into PostgreSQL, and twenty one dbt models create consistent analytical facts and dimensions.',
        'The seller page makes the grain of the analysis explicit. An order may contain several items and more than one seller, while delivery milestones are recorded at order level. To avoid assigning the same failure to every participant, seller reliability uses single seller orders. The minimum volume selector helps distinguish meaningful patterns from small samples. The table includes late counts, rates, and uncertainty intervals, and a seller drillthrough shows its underlying orders. Items, payments and reviews are aggregated independently before joining to orders, preventing duplicate joins from inflating business metrics. These are diagnostic associations. They do not establish which seller caused a particular delay.',
        'The geographic page shows delivery performance by customer state, alongside approximate shipping distance and elapsed delivery time. Coordinates are reduced to one median location per postal prefix before joining. Distance is a straight line approximation, not a measured carrier route. Regional leads can compare high volume areas, then investigate category mix, promises and handoff processes. Stage analysis is restricted to single item and single seller orders where an item shipping deadline can be paired with an order handoff. The quality report retains one hundred and eighty nine source timestamp anomalies, rather than concealing them. Operations should verify these records before attributing responsibility.',
        'The customer experience page connects delivery punctuality with selected customer reviews. Low ratings are defined as one or two out of five, and the denominator includes reviewed orders only. The late versus on time comparison further requires a valid completed delivery outcome. The delay severity distribution helps distinguish a small promise miss from a prolonged customer experience problem. Multiple reviews are reduced deterministically to the latest answered record per order. These charts describe observed relationships, not a causal estimate of how changing delivery time would change satisfaction. They also cannot represent customers who never submitted a review.',
        f'The predictive page replays historical purchase day batches. Each order is scored using attributes assumed available at checkout and seller outcomes observed strictly before that purchase. Actual delivery, final status, handoff and reviews never enter the feature allowlist. Training, selection, calibration and testing are chronological, with time for labels to mature. Raw, sigmoid and isotonic probabilities were compared using forward validation Brier score, with a ranking guard. On later July through August orders, average precision is {ap:.3f}, and precision at fifty cases per day is {precision*100:.1f} percent. A material finding is that The revalidated probabilities still overestimate later risk and fail the fixed acceptance gates. Operational use is not approved. The dashboard states this openly. Ranking is informative, but probability based operational decisions need revalidation.',
        'Finally, the intervention simulator converts risk into an explicit resource allocation scenario. A manager can set daily capacity, budget, case cost, assumed intervention effectiveness, and hypothetical delay impact. Google OR Tools selects cases to maximize assumed expected net benefit while respecting capacity, spending and regional limits. It may leave capacity unused when a case has no positive expected benefit. The default example allows fifty cases and a five hundred real daily budget, with twenty percent assumed effectiveness. None of these intervention effects or savings are measured in Olist. Retrospective outcomes are hidden until revealed for evaluation. The handoff includes tests, notebooks, the executive case study and an editable six page Power BI project. Native Power BI refresh and more than six thousand DAX reconciliations passed. Native pixel screenshots were unavailable. Probability revalidation failed its statistical gates, so operational probability use remains unapproved. The next business step is a controlled intervention pilot, with measured costs and customer experience guardrails.'
    ]
    with tempfile.TemporaryDirectory() as folder:
        work=Path(folder)
        (work/'narration.json').write_text(json.dumps(narration),encoding='utf-8')
        speech=r'''param([string]$Folder)
Add-Type -AssemblyName System.Speech
$speaker=New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.Rate=2
$texts=Get-Content -LiteralPath (Join-Path $Folder 'narration.json') -Raw | ConvertFrom-Json
for($i=0;$i -lt $texts.Count;$i++) {
  $speaker.SetOutputToWaveFile((Join-Path $Folder ("audio{0}.wav" -f $i)))
  $speaker.Speak($texts[$i])
}
$speaker.Dispose()
'''
        (work/'speech.ps1').write_text(speech)
        subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(work/'speech.ps1'),'-Folder',str(work)],check=True)
        ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
        segments=[];duration=0.
        for i,name in enumerate(names):
            im=Image.open(ROOT/'docs/screenshots'/f'{i+1:02d}.png').convert('RGB')
            im=im.crop((0,0,min(im.width,1512),min(im.height,1100)))
            im.thumbnail((1440,1025))
            frame=Image.new('RGB',(1440,1080),'#ffffff');frame.paste(im,((1440-im.width)//2,0))
            draw=ImageDraw.Draw(frame)
            try:font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
            except OSError:font=ImageFont.load_default()
            draw.text((24,1038),f'{i+1:02d} / {name}   |   Olist delivery review - historical analysis',fill='#536272',font=font)
            frame.save(work/f'frame{i}.png')
            audio=work/f'audio{i}.wav'
            with wave.open(str(audio)) as wav:duration+=wav.getnframes()/wav.getframerate()
            segment=work/f'segment{i}.mp4';segments.append(segment)
            subprocess.run([ffmpeg,'-y','-hide_banner','-loglevel','error','-loop','1','-framerate','5','-i',str(work/f'frame{i}.png'),'-i',str(audio),
                '-c:v','libx264','-preset','veryfast','-crf','23','-tune','stillimage','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-shortest',str(segment)],check=True)
            print(f'Rendered demo section {i+1}',flush=True)
        (work/'concat.txt').write_text('\n'.join("file '"+str(p).replace('\\','/')+"'" for p in segments))
        subprocess.run([ffmpeg,'-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(work/'concat.txt'),'-c','copy','-movflags','+faststart',str(ROOT/'docs/product_demo.mp4')],check=True)
        (ROOT/'reports/demo_validation.json').write_text(json.dumps({'format':'MP4 H264/AAC','duration_seconds':round(duration,2),'sections':6,
            'source':'Screenshots of the verified local Streamlit dashboard with synthesized narration; not native Power BI footage'},indent=2))
        (ROOT/'docs/demo_narration.txt').write_text('\n\n'.join(narration),encoding='utf-8')
        print(f'Demo duration: {duration:.1f} seconds',flush=True)

if __name__=='__main__':main()
