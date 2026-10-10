# Colonna sonora sintetizzata per il trailer (50 s, Re minore -> Re maggiore)
import numpy as np, wave, sys
SR=44100; T=50.0; N=int(SR*T)
L=np.zeros(N); Rr=np.zeros(N)
rng=np.random.default_rng(42)
def mf(n): return 440*2**((n-69)/12)
def put(sig,t,pan=0.0,g=1.0):
    i=int(t*SR)
    if i>=N: return
    j=min(N,i+len(sig)); s=sig[:j-i]*g
    L[i:j]+=s*np.sqrt((1-pan)/2)*1.414; Rr[i:j]+=s*np.sqrt((1+pan)/2)*1.414
def tt(d): return np.arange(int(d*SR))/SR
def adsr(d,a,r,s=1.0):
    t=tt(d); e=np.minimum(1,t/max(a,1e-4))*s
    e*=np.clip((d-t)/max(r,1e-4),0,1); return e
def saw(f,d,bright=1.0,detune=0.0):
    t=tt(d); out=np.zeros_like(t); nh=int(min(40,7000/f)*bright)+1
    for k in range(1,nh+1): out+=np.sin(2*np.pi*f*k*t+k*1.7)/k
    return out*.55
def supersaw(f,d,bright=.5,voices=5,spread=.012):
    out=0
    for v in range(voices):
        det=1+spread*(v-(voices-1)/2)/((voices-1)/2+1e-9)
        out=out+saw(f*det,d,bright)
    return out/voices
def lowpass(x,a):  # one-pole, a in (0,1]; vectorizzato a blocchi via filtro esponenziale
    y=np.empty_like(x); acc=0.0
    for i in range(0,len(x),1):
        acc+=a*(x[i]-acc); y[i]=acc
    return y
def noise(d): return rng.standard_normal(int(d*SR))
def smooth(x,k): return np.convolve(x,np.ones(k)/k,'same')

# ---------- strumenti ----------
def pad(notes,t0,d,g=.05,bright=.45,att=.8,rel=1.2,spread=.6):
    for i,n in enumerate(notes):
        s=supersaw(mf(n),d+rel,bright)*adsr(d+rel,att,rel)
        put(s,t0,pan=(i/(max(1,len(notes)-1))-.5)*spread,g=g)
def choir(notes,t0,d,g=.06):
    for i,n in enumerate(notes):
        f0=mf(n); t=tt(d); vib=1+.006*np.sin(2*np.pi*5.2*t+i)
        out=np.zeros_like(t)
        for k in range(1,int(5000/f0)):
            fk=f0*k; a=np.exp(-((fk-700)/260)**2)+.6*np.exp(-((fk-1150)/300)**2)+.25*np.exp(-((fk-2600)/500)**2)+.05/k
            out+=a*np.sin(2*np.pi*fk*np.cumsum(vib)/SR+k)
        put(out*adsr(d,1.5,1.8),t0,pan=(i%2-.5)*.7,g=g)
def pluck(n,t0,g=.12,pan=0,d=.6):
    t=tt(d); f=mf(n); s=(np.sin(2*np.pi*f*t)+.4*np.sin(2*np.pi*2*f*t)*np.exp(-t*9)+.15*np.sin(2*np.pi*3*f*t)*np.exp(-t*14))*np.exp(-t*5.5)*np.minimum(1,t/.003)
    put(s,t0,pan,g)
def bell(n,t0,g=.1,pan=0,d=3.0):
    t=tt(d); f=mf(n)
    s=np.sin(2*np.pi*f*t)*np.exp(-t*1.2)+.5*np.sin(2*np.pi*f*2.756*t)*np.exp(-t*3)+.3*np.sin(2*np.pi*f*5.404*t)*np.exp(-t*6)+.2*np.sin(2*np.pi*f*.5*t)*np.exp(-t*1.5)
    put(s*np.minimum(1,t/.002),t0,pan,g)
def taiko(t0,g=.5,f0=62,pan=0):
    t=tt(1.0); fr=f0*(1+1.2*np.exp(-t*28)); s=np.sin(2*np.pi*np.cumsum(fr)/SR)*np.exp(-t*5.5)
    n=smooth(noise(1.0),18)*np.exp(-t*30)*3; put((s+n)*np.minimum(1,t/.002),t0,pan,g)
def tom(t0,f0=110,g=.25,pan=0):
    t=tt(.5); fr=f0*(1+.5*np.exp(-t*20)); put(np.sin(2*np.pi*np.cumsum(fr)/SR)*np.exp(-t*9),t0,pan,g)
def snare(t0,g=.15,pan=0):
    t=tt(.25); n=noise(.25); n=n-smooth(n,6); put((n*np.exp(-t*22)+.5*np.sin(2*np.pi*190*t)*np.exp(-t*30)),t0,pan,g)
def boom(t0,g=1.0):
    t=tt(4.0); fr=28+70*np.exp(-t*3); s=np.sin(2*np.pi*np.cumsum(fr)/SR)*np.exp(-t*.9)*np.minimum(1,t/.004)
    put(s,t0,0,g)
def crash(t0,g=.25,d=4.0):
    t=tt(d); n=noise(d); n=n-smooth(n,3); put(n*np.exp(-t*1.4)*np.minimum(1,t/.002),t0,-.2,g); 
    n2=noise(d); n2=n2-smooth(n2,3); put(n2*np.exp(-t*1.4)*np.minimum(1,t/.002),t0,.2,g)
def braam(notes,t0,d=3.5,g=.12):
    t=tt(d)
    for i,n in enumerate(notes):
        f=mf(n); out=np.zeros_like(t); op=np.clip(t/.25,0,1)*np.exp(-t*.5)
        for k in range(1,int(min(60,6000/f))):
            for det in (.995,1.0,1.006):
                out+=np.sin(2*np.pi*f*det*k*t+k)/k*np.exp(-k/(1+op*22))
        out=np.tanh(out*1.6)
        put(out*adsr(d,.01,1.5),t0,pan=(i/(len(notes)-1)-.5)*.6 if len(notes)>1 else 0,g=g)
def riser(t0,d,g=.2):
    t=tt(d); n=noise(d); p=t/d
    # rumore filtrato che si apre + tono che sale
    a=.004+.25*p**2; y=np.empty_like(n); acc=0.0
    for i in range(len(n)): acc+=a[i]*(n[i]-acc); y[i]=acc
    tone=np.sin(2*np.pi*np.cumsum(110*2**(p*2.5))/SR)*.25
    put((y*2.2+tone)*p**2.2,t0,0,g)
def reverse_swell(t0,d,n=62,g=.15):
    t=tt(d); f=mf(n); s=(np.sin(2*np.pi*f*t)+.5*np.sin(2*np.pi*f*2.756*t))*np.exp(-(d-t)*2.2)
    nn=noise(d)*np.exp(-(d-t)*3)*.3; put(s+nn,t0,0,g)
def click(t0,g=.12):
    t=tt(.03); n=noise(.03); n=np.diff(n,prepend=0); put(n*np.exp(-t*250),t0,rng.uniform(-.3,.3),g)

# ---------- partitura ----------
Dm=[50,53,57,62]; Bb=[46,53,58,62]; F=[45,53,57,60]; C=[48,52,55,60]; Dmaj=[50,54,57,62,66]
# 0-5: prompt
t=tt(5.2); drone=np.sin(2*np.pi*mf(26)*t)*.6+np.sin(2*np.pi*mf(38)*t)*.3
put(drone*np.clip(t/4.5,0,1)**2,0,0,.35)
sh=(np.sin(2*np.pi*mf(74)*t)+np.sin(2*np.pi*mf(81)*t)*.7)*(.5+.5*np.sin(2*np.pi*.6*t))*np.clip(t/3,0,1)*np.clip((5.1-t)/.3,0,1)
put(sh,0,.3,.02)
PROMPT_LEN=84
for i in range(PROMPT_LEN): click(.7+3.4*i/PROMPT_LEN+rng.uniform(0,.012),g=.10)
riser(3.6,1.4,g=.16); reverse_swell(3.8,1.2,n=62,g=.12)
# 5: esplosione
boom(5.0,1.0); crash(5.0,.18,5); braam([26,38,45,50],5.0,3.8,.10)
# 5-13.2 galassia: pad + arpeggio
prog=[Dm,Bb,F,C]
for k in range(4):
    pad(prog[k],5.2+k*2.05,2.05,g=.085,att=.6 if k else 1.0)
arp=[62,65,69,74,72,69,65,69]
step=60/105/2
tq=5.6;i=0
while tq<13.2:
    ch=prog[min(3,int((tq-5.2)/2.05))]
    n=ch[(i%4)]+24 if i%2==0 else arp[i%8]
    pluck(n,tq,g=.13+.05*(i%4==0),pan=.5*np.sin(i*.9)); i+=1; tq+=step
riser(11.9,2.7,.17)
# 14.6-25 città
beat=60/105; B0=14.6
boom(14.6,.8); crash(14.6,.12,3); taiko(14.6,.7)
for k in range(5):
    pad(prog[k%4],B0+k*4*beat,4*beat,g=.05,bright=.55)
nb=int((25.2-B0)/beat)
for b in range(nb):
    tb=B0+b*beat
    if b%2==0: taiko(tb,.55)
    if b%4==3: taiko(tb+beat/2,.35,f0=75)
    if b>=4: snare(tb+beat,.06,pan=.2) if b%2 else None
    # ostinato archi bassi (crome)
    root=prog[(b//4)%4][0]-12
    for h in (0,1):
        s=saw(mf(root),beat/2*.9,.6)*adsr(beat/2*.9,.005,.08); put(s,tb+h*beat/2,-.3,.07)
        s=saw(mf(root+12),beat/2*.9,.5)*adsr(beat/2*.9,.005,.08); put(s,tb+h*beat/2,.3,.04)
# 25.2-33.4 luci: pieno
boom(25.2,.9); crash(25.2,.2,4); braam([38,45,50,57],25.2,3,.07)
B1=25.2; nb=int((33.4-B1)/beat)
for b in range(nb):
    tb=B1+b*beat; ch=prog[(b//4)%4]
    taiko(tb,.6); taiko(tb+beat/2,.3,f0=80,pan=.2)
    if b%2: snare(tb,.12)
    if b%4==3: tom(tb+beat*.5,140,.2,-.4); tom(tb+beat*.75,110,.2,.4)
    root=ch[0]-12
    for h in range(4):
        s=saw(mf(root),beat/4*.85,.7)*adsr(beat/4*.85,.004,.05); put(s,tb+h*beat/4,(h%2-.5)*.4,.08)
    for h in range(4):
        pluck(ch[h%4]+24+(12 if h==3 else 0),tb+h*beat/4,g=.05,pan=(h-1.5)*.3)
for k in range(4):
    pad([n+12 for n in prog[k%4]],B1+k*4*beat,4*beat,g=.05,bright=.6,att=.3)
# luci che si accendono: campane
for k,n in enumerate([74,77,81,86,84,81,77,81,86,89]):
    bell(n,25.4+k*.42,g=.05,pan=np.sin(k)*.6)
boom(29.6,.6); crash(29.6,.12,3)
# 33.4-41.4 globo: respiro
reverse_swell(32.4,1.0,n=74,g=.12)
crash(33.4,.08,4)
choir([50,57,62,65],33.6,4.4,g=.05); choir([46,53,58,62],37.6,4.0,g=.05)
pad([38,45],33.6,8,g=.05,bright=.3,att=2)
for k,n in enumerate([69,72,74,77,76,74,72,69]):
    pluck(n+12,34.2+k*.75,g=.05,pan=(k%2-.5)*.6); bell(n,34.2+k*.75,g=.025)
# 39.5-43 build
riser(39.6,3.4,.24)
tq=41.0; d=.18
while tq<42.95:
    snare(tq,.05+.12*(tq-41)/2,pan=rng.uniform(-.2,.2)); tq+=d; d=max(.045,d*.9)
for k in range(8): taiko(41.6+k*.175,.25+.04*k,f0=70)
# 43: IMPATTO + Re maggiore
boom(43.0,1.2); crash(43.0,.28,6); braam([26,38,45,50,54],43.0,4.5,.12); taiko(43.0,.9,f0=50)
pad(Dmaj,43.05,5.6,g=.06,bright=.5,att=.05,rel=1.5)
choir([62,66,69,74],43.2,6.0,g=.04)
for k,n in enumerate([74,78,81,86]): bell(n,45.4+k*.2,g=.07,pan=(k-1.5)*.3)
for k,n in enumerate([81,78,74]): bell(n,46.8+k*.25,g=.05,pan=(1-k)*.3)
bell(50,48.0,g=.08,d=2)

# ---------- riverbero (convoluzione FFT) ----------
def reverb(x,seconds=2.8,seed=1):
    r=np.random.default_rng(seed); n=int(seconds*SR); t=np.arange(n)/SR
    ir=r.standard_normal(n)*np.exp(-t*2.4); ir=smooth(ir,4); ir[:int(.02*SR)]*=np.linspace(0,1,int(.02*SR))
    m=len(x)+n; nf=1<<(m-1).bit_length()
    y=np.fft.irfft(np.fft.rfft(x,nf)*np.fft.rfft(ir,nf),nf)[:len(x)]
    return y/np.max(np.abs(ir))*.02
wl,wr=reverb(L,seed=1),reverb(Rr,seed=2)
mixL=L+wl*.9; mixR=Rr+wr*.9
mix=np.stack([mixL,mixR],1)
# master: compressione morbida + fade
fade=np.ones(N); k=int(1.0*SR); fade[-k:]=np.linspace(1,0,k)**1.5
mix*=fade[:,None]
mix/=np.percentile(np.abs(mix),99.95)
mix=np.tanh(mix*1.1)/np.tanh(1.1)
mix*=.92/np.max(np.abs(mix))
w=wave.open(sys.argv[1],'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix*32767).astype(np.int16).tobytes()); w.close()
print("ok")
