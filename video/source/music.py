import numpy as np, wave, sys
SR=44100; T=15.0; N=int(SR*T); L=np.zeros(N); R=np.zeros(N)
rng=np.random.default_rng(7)
def f(n): return 440*2**((n-69)/12)
def add(sig,t,pan=0.0,g=1.0):
    i=int(t*SR); j=min(N,i+len(sig)); s=sig[:j-i]*g
    L[i:j]+=s*(1-pan)/1; R[i:j]+=s*(1+pan)/1
def env(n,a=.005,d=.2):
    t=np.arange(n)/SR; e=np.minimum(1,t/a)*np.exp(-t/d); return e
def tone(freq,dur,a=.01,d=.3,kind='sine'):
    n=int(dur*SR); t=np.arange(n)/SR
    if kind=='sine': s=np.sin(2*np.pi*freq*t)
    elif kind=='saw': s=sum(np.sin(2*np.pi*freq*k*t)/k for k in range(1,9))*.6
    elif kind=='bell': s=np.sin(2*np.pi*freq*t)+.5*np.sin(2*np.pi*freq*2.76*t)*np.exp(-t*6)+.25*np.sin(2*np.pi*freq*5.4*t)*np.exp(-t*12)
    return s*env(n,a,d)
def kick():
    n=int(.35*SR); t=np.arange(n)/SR; fr=50+110*np.exp(-t*30)
    return np.sin(2*np.pi*np.cumsum(fr)/SR)*np.exp(-t*9)
def hat(d=.04):
    n=int(.08*SR); s=rng.standard_normal(n); s=np.diff(s,prepend=0); return s*env(n,.001,d)*.5
def clap():
    n=int(.25*SR); s=rng.standard_normal(n); s=np.convolve(s,np.ones(6)/6,'same')
    e=np.zeros(n); 
    for o in (0,.01,.02): k=int(o*SR); e[k:]+=np.exp(-np.arange(n-k)/SR/0.05)
    return s*e*.5
def click():
    n=int(.03*SR); s=rng.standard_normal(n); s=np.diff(s,prepend=0); return s*env(n,.0005,.006)
def whoosh(dur):
    n=int(dur*SR); s=rng.standard_normal(n); t=np.arange(n)/SR
    # crude rising lowpass via moving average shrinking
    out=np.zeros(n); y=0
    a=np.linspace(.01,.35,n)
    for i in range(n): y+=a[i]*(s[i]-y); out[i]=y
    return out*(t/dur)**2*.8

beat=.5
# pad chords (Am F C G) every 2s
chords=[[57,60,64,69],[53,57,60,65],[48,55,60,64],[55,59,62,67]]
for k in range(8):
    t0=k*2.0
    if t0>=14.2: break
    for i,n in enumerate(chords[k%4]):
        dur=2.3
        s=tone(f(n),dur,a=.25,d=1.4,kind='saw')*.035
        s+=tone(f(n)*1.003,dur,a=.25,d=1.4,kind='saw')*.025
        add(s,t0,pan=(i-1.5)*.25)
    # bass
    if t0>=2.0 and t0<12.9:
        root=chords[k%4][0]-12
        for b in range(4):
            tb=t0+b*beat+(.2 if t0==2.0 else .2)
            if tb<12.9: add(tone(f(root),.45,a=.005,d=.18,kind='saw')*.16,tb)
# drums from 2.2 to 12.9
t=2.2; bi=0
while t<12.85:
    add(kick()*.9,t)
    add(hat(),t+beat/2,pan=.3,g=.35)
    if bi%2==1: add(clap(),t,pan=-.1,g=.5)
    if 5.2<=t<8.4: add(hat(.02),t+beat/4,pan=-.3,g=.2); add(hat(.02),t+3*beat/4,pan=-.3,g=.2)
    t+=beat; bi+=1
# typing clicks
for i in range(13): add(click(),.15+i*(0.85/13)+rng.uniform(0,.02),pan=rng.uniform(-.3,.3),g=.5)
tt=5.4
while tt<7.95: add(click(),tt,pan=rng.uniform(-.4,.4),g=.35); tt+=rng.uniform(.035,.08)
# whooshes into cuts
for c in (2.2,5.2,8.4,11.2,12.9): add(whoosh(.45),c-.45,g=.35)
# lights off blips (descending)
penta=[81,79,76,74,72,69]
for i,n in enumerate(penta): add(tone(f(n),.35,a=.002,d=.12,kind='bell')*.18,8.4+1.25+i*.16,pan=(i-2.5)*.15)
# notification ding
add(tone(f(88),.8,a=.002,d=.35,kind='bell')*.22,8.4+2.15); add(tone(f(93),.8,a=.002,d=.35,kind='bell')*.18,8.4+2.27)
# word pops
up=[69,72,74,76,79,81,84,86,88,91]
for i,n in enumerate(up): add(tone(f(n),.2,a=.002,d=.07,kind='sine')*.14,11.2+.05+i*.1,pan=(i%2-.5)*.4)
# final chime at 14.2: Am add9 bell
for i,n in enumerate([57,64,69,71,72,76]):
    add(tone(f(n),1.0,a=.003,d=.7,kind='bell')*.12,14.2+i*.025,pan=(i-2.5)*.15)
add(kick()*.8,14.2)
# master
mix=np.stack([L,R],1)
fade=np.ones(N); k=int(.35*SR); fade[-k:]=np.linspace(1,0,k); fade[:int(.01*SR)]=np.linspace(0,1,int(.01*SR))
mix*=fade[:,None]
mix=np.tanh(mix*1.4)/np.tanh(1.4)
mix/=np.max(np.abs(mix))/0.89
w=wave.open(sys.argv[1],'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix*32767).astype(np.int16).tobytes()); w.close()
