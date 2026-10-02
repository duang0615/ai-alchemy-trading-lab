"""不登入、不抓行情的公開包驗收。"""
from pathlib import Path
import json, re, hashlib
ROOT=Path(__file__).resolve().parents[1]

def main():
    research=json.loads((ROOT/'reports/research.json').read_text(encoding='utf-8'))
    audits=json.loads((ROOT/'reports/audit.json').read_text(encoding='utf-8'))
    accounting=json.loads((ROOT/'reports/accounting_audit.json').read_text(encoding='utf-8'))
    assert len(research['results'])==len(audits)==len(accounting)==68
    assert all(a['all_next_open_prices_match'] and a['all_positions_closed'] and a['checks']>0 for a in audits)
    assert all(all(a[k] for k in ['fee_formula_match','pnl_formula_match','final_equity_match','signal_uses_only_past_bars']) for a in accounting)
    assert len(research['examples'])==8
    spec=json.loads((ROOT/'strategies/momentum_eod/spec.json').read_text(encoding='utf-8'))
    assert research['metadata']['spec_sha256']==hashlib.sha256(json.dumps(spec,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest()
    for r in research['results']:
        c=research['curves'][r['run']]
        assert abs(c[-1]['equity']/10_000_000-1-r['account_return'])<1e-8
        for file in ['report.csv','trade_detail.csv','daily.csv','account_equity.csv']:
            assert (ROOT/'reports'/r['run']/file).exists()
    page=(ROOT/'index.html').read_text(encoding='utf-8')
    assert '__RESEARCH__' not in page
    for link in re.findall(r'href="([^"]+)"',page):
        if not link.startswith(('https:','http:','#')):assert (ROOT/link).exists(),link
    # Scan distributable files only; never inspect credentials/private provider data.
    secrets=[r'gh[pousr]_[A-Za-z0-9]{20,}',r'github_pat_[A-Za-z0-9_]{30,}',r'(?:app|dataset)-[A-Za-z0-9]{15,}',r'-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----']
    for f in ROOT.rglob('*'):
        if not f.is_file() or any(p in {'.git','.local','__pycache__'} for p in f.relative_to(ROOT).parts):continue
        if f.name.startswith('.env'):continue
        content=f.read_text(encoding='utf-8-sig')
        assert not any(re.search(pattern,content) for pattern in secrets),f.name
    evidence={'date':'2026-10-02','runs':68,'examples':8,'checks':['next-bar open fill','all positions closed','fees and P/L','final equity','past-only signal arithmetic','spec hash','all output files','local links','credential pattern scan'],
      'classroom_trial':'pending','local_browser_preview':'file protocol blocked; no browser-render validation claimed'}
    (ROOT/'reports/release_checks.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS: 68 runs / 8 examples / outputs / links / credentials')

if __name__=='__main__':main()
