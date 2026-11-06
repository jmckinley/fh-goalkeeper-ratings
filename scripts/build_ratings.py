"""
The Keeper Index: build script.

Reproduces data/ratings_2026.json and data/ratings_2026.csv from three inputs:
  1. NCAA D1 save-percentage leaderboard (stat 444), all pages
  2. NCAA D1 saves-per-game leaderboard (stat 431), all pages
  3. Every D1 result for the season (data/results_2026.csv)

Usage:
  python3 build_ratings.py --fetch        # pulls NCAA pages and the scoreboard, then builds
  python3 build_ratings.py                # builds from cached html in ./cache and data/results_2026.csv

Rating definition (v1.0):
  SV%     = saves / (saves + GA)
  SOG/G   = (saves + GA) / games
  GSAA/G  = ((saves + GA) * (1 - league_avg_sv_pct) - GA) / games
  SOS     = 2/3 * opp win pct (excluding games vs rated team) + 1/3 * opp-opp win pct   (NCAA RPI formula)
  Each keeper is ranked 1..N on each factor (higher is better on all four).
  Sum of ranks, ascending; ties broken by SV%.
"""
import argparse, csv, datetime, html, json, os, re, statistics as st, subprocess
from collections import defaultdict

NCAA = "https://www.ncaa.com/stats/fieldhockey/d1/current/individual/{stat}{page}"
RPI = "https://www.ncaa.com/rankings/fieldhockey/d1/ncaa-field-hockey-rpi"
SB = "https://www.ncaa.com/scoreboard/fieldhockey/d1/{y}/{m:02d}/{d:02d}"
IVY = {'Dartmouth','Harvard','Yale','Princeton','Brown','Cornell','Columbia','Penn'}
TEAM_MAP = {'App State':'appalachian-st','LIU':'long-island','UAlbany':'albany-ny','Michigan St.':'michigan-st','Ohio St.':'ohio-st','Penn St.':'penn-st','Indiana':'indiana','Michigan':'michigan','Ohio':'ohio','Penn':'penn'}

def get(url):
    return subprocess.run(['curl','-sS','-m','30','-A','Mozilla/5.0',url],capture_output=True,text=True).stdout

def table_rows(s):
    out=[]
    for r in re.findall(r'<tr[^>]*>(.*?)</tr>',s,re.S):
        c=[html.unescape(re.sub('<[^>]+>','',x)).strip() for x in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>',r,re.S)]
        if c and c[0]!='Rank' and len(c)>5: out.append(c)
    return out

def fetch_all(cache):
    os.makedirs(cache,exist_ok=True)
    for stat in (444,431):
        for p in ('','/p2','/p3','/p4'):
            open(f'{cache}/{stat}{p.replace("/","_")}.html','w').write(get(NCAA.format(stat=stat,page=p)))
    open(f'{cache}/rpi.html','w').write(get(RPI))

def fetch_results(start,end,path):
    games=[]; d=start
    while d<=end:
        out=get(SB.format(y=d.year,m=d.month,d=d.day))
        for m in re.finditer(r'"startDate":"([^"]+)".*?"teams":\[(.*?)\]',out,re.S):
            if m.group(1).replace('\\/','/')!=f"{d.month:02d}/{d.day:02d}/{d.year}": continue
            t=re.findall(r'"seoname":"([^"]+)","nameShort":"([^"]+)".*?"score":(\d+|null),"isWinner":(true|false)',m.group(2),re.S)
            if len(t)==2 and all(x[2]!='null' for x in t):
                games.append((str(d),t[0][0],int(t[0][2]),t[1][0],int(t[1][2])))
        d+=datetime.timedelta(days=1)
    games=list(dict.fromkeys(games))
    with open(path,'w',newline='') as f:
        w=csv.writer(f); w.writerow(['date','team_a','score_a','team_b','score_b']); w.writerows(games)
    return games

def load_results(path):
    with open(path) as f:
        r=csv.reader(f); next(r); return [(a,b,int(c),d,int(e)) for a,b,c,d,e in r]

def sos_table(games):
    opp=defaultdict(list)
    for _,a,_,b,_ in games: opp[a].append(b); opp[b].append(a)
    def wp(t,exclude=None):
        w=l=ti=0
        for _,a,sa,b,sb in games:
            if t not in (a,b): continue
            o=b if a==t else a
            if o==exclude: continue
            s_t,s_o=(sa,sb) if a==t else (sb,sa)
            if s_t>s_o: w+=1
            elif s_t<s_o: l+=1
            else: ti+=1
        n=w+l+ti; return (w+0.5*ti)/n if n else 0
    owp={t:st.mean(wp(o,exclude=t) for o in opp[t]) for t in opp}
    oowp={t:st.mean(owp[o] for o in opp[t]) for t in opp}
    return {t:(2/3)*owp[t]+(1/3)*oowp[t] for t in opp}

def slug(team,seos):
    if team in TEAM_MAP: return TEAM_MAP[team]
    n=lambda x: re.sub(r'[^a-z]','',x.lower().replace('st.','state'))
    c=[s for s in seos if n(s)==n(team) or n(s).startswith(n(team)) or n(team).startswith(n(s))]
    if len(c)!=1: raise SystemExit(f'cannot map team {team}: {c}')
    return c[0]

def build(cache,results_path,out_json,out_csv,as_of):
    sv={}
    for p in ('','_p2','_p3','_p4'):
        f=f'{cache}/444{p}.html'
        if os.path.exists(f):
            for c in table_rows(open(f).read()):
                sv[(c[1],c[2])]=dict(cl=c[3],g=int(c[5]),min=int(c[6]),saves=int(c[8]),ga=int(c[9]))
    spg=set()
    for p in ('','_p2','_p3','_p4'):
        f=f'{cache}/431{p}.html'
        if os.path.exists(f):
            for c in table_rows(open(f).read()): spg.add((c[1],c[2]))
    rpi={};conf={}
    for c in table_rows(open(f'{cache}/rpi.html').read()):
        if c[0].isdigit(): rpi[c[1]]=int(c[0]); conf[c[1]]=c[3]
    games=load_results(results_path); sos=sos_table(games); seos=sorted(sos)
    rec=defaultdict(lambda:[0,0,0])
    for _,a,sa,b,sb in games:
        if sa==sb: rec[a][2]+=1; rec[b][2]+=1
        else:
            w,l=(a,b) if sa>sb else (b,a); rec[w][0]+=1; rec[l][1]+=1
    ks=[]
    for (name,team),v in sv.items():
        if (name,team) not in spg: continue
        s=slug(team,seos); r=rec[s]
        d=dict(name=name,team=team,conf=conf.get(team,''),cl=v['cl'],g=v['g'],min=v['min'],saves=v['saves'],ga=v['ga'],
               rec=f"{r[0]}-{r[1]}"+(f"-{r[2]}" if r[2] else ""),rpi=rpi.get(team),sos=sos[s])
        d['shots']=d['saves']+d['ga']; d['pct']=d['saves']/d['shots']; d['sfpg']=d['shots']/d['g']; d['spg']=d['saves']/d['g']; d['gapg']=d['ga']/d['g']
        ks.append(d)
    lg=sum(d['saves'] for d in ks)/sum(d['shots'] for d in ks)
    for d in ks:
        d['xga']=d['shots']*(1-lg); d['gsaa']=d['xga']-d['ga']; d['gsaapg']=d['gsaa']/d['g']
    def ranks(key,asc=False):
        o=sorted(ks,key=lambda d:(d[key] if asc else -d[key])); return {id(d):i+1 for i,d in enumerate(o)}
    R={k:ranks(k) for k in ['pct','sfpg','sos','gsaapg','spg']}; R['gapg']=ranks('gapg',True)
    for d in ks:
        for k in R: d['r_'+k]=R[k][id(d)]
    variants={'v4':['pct','sfpg','gsaapg','sos'],'v3':['pct','spg','sos'],'v3s':['pct','sfpg','sos'],'vga':['pct','gapg','sos']}
    for key,comps in variants.items():
        for d in ks: d['sum_'+key]=sum(d['r_'+c] for c in comps)
        for i,d in enumerate(sorted(ks,key=lambda d:(d['sum_'+key],-d['pct']))): d['rank_'+key]=i+1
    def z(key):
        mu=st.mean(d[key] for d in ks); sd=st.pstdev(d[key] for d in ks); return {id(d):(d[key]-mu)/sd for d in ks}
    Z=[z(k) for k in variants['v4']]
    for d in ks: d['z_v4']=sum(zz[id(d)] for zz in Z)
    for i,d in enumerate(sorted(ks,key=lambda d:-d['z_v4'])): d['zr_v4']=i+1
    out=sorted(ks,key=lambda d:d['rank_v4'])
    fields=['rank_v4','name','team','conf','cl','rec','rpi','g','min','shots','saves','ga','pct','sfpg','spg','gapg','xga','gsaa','gsaapg','sos','r_pct','r_sfpg','r_gsaapg','r_sos','r_spg','r_gapg','sum_v4','zr_v4','rank_v3','rank_v3s','rank_vga']
    clean=[{k:(round(d[k],4) if isinstance(d[k],float) else d[k]) for k in fields} for d in out]
    json.dump({'as_of':as_of,'league_avg_sv_pct':round(lg,4),'n':len(clean),'keepers':clean},open(out_json,'w'),indent=1)
    with open(out_csv,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(clean)
    print(f'{len(clean)} keepers rated; league avg SV% {lg:.3f}')
    for d in out[:10]: print(d['rank_v4'],d['name'],d['team'],d['sum_v4'])

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--fetch',action='store_true'); ap.add_argument('--cache',default='cache')
    ap.add_argument('--results',default='../data/results_2026.csv'); ap.add_argument('--start',default='2026-08-27'); ap.add_argument('--end',default='2026-11-03')
    a=ap.parse_args()
    if a.fetch:
        fetch_all(a.cache)
        fetch_results(datetime.date.fromisoformat(a.start),datetime.date.fromisoformat(a.end),a.results)
    build(a.cache,a.results,'../data/ratings_2026.json','../data/ratings_2026.csv',a.end)
