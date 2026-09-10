import html,re,subprocess,sys,urllib.parse
S="/tmp/claude-1000/-home-devuser-github-writing-hub/f0054174-7a77-48fa-99de-89a438a528ca/scratchpad"
CK=f"{S}/hnu-cookies.txt"
def curl(url,follow=True):
    c=["curl","-s","-b",CK,"-c",CK,"--max-time","40"]+(["-L"] if follow else [])+[url]
    return subprocess.run(c,capture_output=True,text=True).stdout
def ziele(rid):
    h=html.unescape(curl(f"https://bibkat-hnu-de.ezproxy.hnu.de/vufind/Record/{rid}",follow=False))
    out=[]
    for m in re.findall(r'qurl=([^"&\s]+)',h):
        t=urllib.parse.unquote(m)
        if t not in out: out.append(t)
    return out
MARKER=re.compile(r'Neu-Ulm|Hochschule f.r angewandte Wissenschaften',re.I)
for zeile in sys.argv[1:]:
    rid,name=zeile.split("=",1)
    zs=ziele(rid)
    verdikt="KEIN VOLLTEXT-LINK"; wo=""
    for t in zs:
        seite=curl("https://ezproxy.hnu.de/login?qurl="+urllib.parse.quote(t,safe=""))
        host=re.sub(r'^https?://','',t).split('/')[0]
        if MARKER.search(seite):
            verdikt="HNU"; wo=host; break
        verdikt="FREMD/UNBELEGT"; wo=host
    print(f"{name:22} {rid:20} {verdikt:16} {wo[:40]}  ({len(zs)} Ziel(e))")
