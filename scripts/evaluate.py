"""One command: python scripts/evaluate.py --live. No synthetic pass claims."""
import argparse
import asyncio
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import store
from app.engine import answer, validate_quotes
from app.ingestion import load_kb

async def evaluate(live,only=None):
    # Evaluation questions are synthetic. Keep their counters/errors out of the
    # actual application's records and never sync test fixtures to Supabase.
    import tempfile, os
    store.DATA=Path(tempfile.mkdtemp(prefix='evaluation-',dir=ROOT/'work'))
    store.TEST_MODE=True
    os.environ.pop('SUPABASE_URL',None);os.environ.pop('SUPABASE_SECRET_KEY',None)
    store.init()
    cases=json.loads((ROOT/'tests/questions.json').read_text(encoding='utf-8'))
    if only:cases=[c for c in cases if c['id'] in only]
    results=[]
    for case in cases:
        a=await answer(case['question'],dict(case.get('context',{})),offline=not live)
        checks={'expected_intent':a['intent'] in case['intent'],'citations_valid':bool(a['citations']) and validate_quotes(a['citations'],load_kb(),a.get('entity'))}
        for v in case.get('contains',[]):checks['contains '+v]=v.lower() in a['text'].lower()
        for v in case.get('absent',[]):checks['excludes '+v]=v.lower() not in a['text'].lower()
        if 'source' in case:checks['correct_source']=any(c['id'].startswith(case['source']+':') for c in a['citations'])
        if 'language' in case:checks['language']=a['language']==case['language']
        passed=all(checks.values())
        row={'id':case['id'],'type':case['type'],'question':case['question'],'passed':passed,'checks':checks,'answer':a}
        results.append(row)
        print(f"{case['id']:02d} {'PASS' if passed else 'FAIL'} {case['type']} ({a['intent']})",flush=True)
        if live:await asyncio.sleep(5)
    mode='live' if live else 'offline'
    report={'mode':mode,'run_at':datetime.now(timezone.utc).isoformat(),'passed':sum(r['passed'] for r in results),'total':len(results),'results':results}
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    name=f'{mode}-evaluation'+('-targeted' if only else '')
    (reports/(name+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    md=[f'# {mode.title()} evaluation',f'\nRun: {report["run_at"]}\n',f'Passed: {report["passed"]}/{report["total"]}\n',
        'Offline mode verifies deterministic behavior only; it does not validate Groq routing or translation. Live mode calls the configured Groq model. Assertions check observable behavior, source identity, price context, and quote integrity; they are not a clinical or exhaustive semantic audit.\n',
        '| # | Scenario | Result | Failed checks |','|---|---|---|---|']
    for r in results:md.append(f'| {r["id"]} | {r["type"]} | {"PASS" if r["passed"] else "FAIL"} | '+', '.join(k for k,v in r['checks'].items() if not v)+' |')
    (reports/(name+'.md')).write_text('\n'.join(md),encoding='utf-8')
    if live and not only:
        submission=['# Answers to the eight required assessment types','These bracket substitutions match the seven approved sources. Actual live run; no answers edited after generation.\n']
        for r in results[:8]:
            submission.extend([f'## {r["id"]}. {r["type"]}',r['question'],'',r['answer']['text'],'','Sources:'])
            for c in r['answer']['citations']:submission.append(f'- [{c["title"]}]({c["url"]}) — line {c["line"]}: {c["quote"]}')
            submission.append('')
        (reports/'required-eight-answers.md').write_text('\n'.join(submission),encoding='utf-8')
    return report['passed']==report['total']

if __name__=='__main__':
    (ROOT/'work').mkdir(exist_ok=True)
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');parser.add_argument('--only');args=parser.parse_args()
    unit=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=ROOT).returncode
    ok=asyncio.run(evaluate(args.live,[int(i) for i in args.only.split(',')] if args.only else None))
    if args.live and not args.only:
        report=json.loads((ROOT/'reports/live-evaluation.json').read_text(encoding='utf-8'))
        failed=[f"{r['id']} ({r['type']})" for r in report['results'] if not r['passed']]
        result_text=(f"Live evaluation: **{report['passed']}/{report['total']} passed**, run {report['run_at']}. "
                     f"Infrastructure/security suite: **{'passed' if unit==0 else 'failed'}**. "
                     f"Current failed question cases: {', '.join(failed) if failed else 'none'}.\n\n"
                     "The initial run was 32/36. Two questions exposed missing ‘how much’ routing, one Arabic cost question was over-refused, and one assertion incorrectly matched ‘approved pages’ as discount approval. These failures and their original answers are preserved in `reports/initial-evaluation.md` and `.json`. A repeated infrastructure run also exposed shared test rate-limit state; the tests now isolate their runtime state and never sync fixtures to Supabase.\n\n"
                     "See `reports/live-evaluation.md` for the current per-case report and `reports/required-eight-answers.md` for submission answers. Passing this finite suite does not guarantee perfect semantic accuracy or medical safety. Cloud synchronization and seven-day uptime are not included in these results.")
        readme=ROOT/'README.md';text=readme.read_text(encoding='utf-8')
        start='<!-- TEST_RESULTS_START -->';end='<!-- TEST_RESULTS_END -->'
        if start in text and end in text:
            text=text.split(start)[0]+start+'\n'+result_text+'\n'+end+text.split(end)[1]
            readme.write_text(text,encoding='utf-8')
    raise SystemExit(0 if unit==0 and ok else 1)
