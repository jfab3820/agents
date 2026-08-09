import ast, re, subprocess, difflib, wave, math, array
from pathlib import Path

# Reuse the approved script without executing the older cleaner.
tree=ast.parse(Path('video2_render/clean_audio.py').read_text())
TURNS=None
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TURNS' for t in node.targets):
        TURNS=ast.literal_eval(node.value); break
assert TURNS and len(TURNS)==53


def ts(s):
    h,m,rest=s.replace(',','.').split(':'); return int(h)*3600+int(m)*60+float(rest)

def parse_srt(path):
    txt=Path(path).read_text(errors='ignore').strip(); out=[]
    for b in re.split(r'\n\s*\n',txt):
        lines=[x.strip() for x in b.splitlines() if x.strip()]
        ti=next((i for i,l in enumerate(lines) if '-->' in l),None)
        if ti is None: continue
        a,z=[x.strip() for x in lines[ti].split('-->')]
        out.append((ts(a),ts(z),' '.join(lines[ti+1:])))
    return out

def norm(s):
    return ' '.join(re.sub(r"[^a-z0-9\s']",' ',s.lower().replace('’',"'")).split())

def map_exact(cues, expected):
    res=[]; i=0
    for turn in expected:
        target=norm(turn); tw=len(target.split()); best=None
        for j in range(i,min(len(cues),i+10)):
            cn=norm(' '.join(c[2] for c in cues[i:j+1])); cw=len(cn.split())
            score=difflib.SequenceMatcher(None,target,cn).ratio()-abs(cw-tw)/max(tw,1)*0.10
            if best is None or score>best[0]: best=(score,j)
            if cw>tw*1.7+5: break
        if best is None: raise RuntimeError('No cue match: '+turn)
        j=best[1]; res.append((cues[i][0],cues[j][1])); i=j+1
    return res

def source_duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',path]))

def safe_handles(spans,total,pre=0.22,post=0.26):
    out=[]
    for k,(a,z) in enumerate(spans):
        left=0 if k==0 else (spans[k-1][1]+a)/2
        right=total if k==len(spans)-1 else (z+spans[k+1][0])/2
        out.append((max(left,a-pre),min(right,z+post)))
    return out

def energy_trim_wav(src,dst,pre=0.070,post=0.095):
    w=wave.open(src,'rb'); ch=w.getnchannels(); sw=w.getsampwidth(); rate=w.getframerate(); n=w.getnframes(); raw=w.readframes(n); w.close(); assert sw==2
    vals=array.array('h'); vals.frombytes(raw); win=max(1,int(rate*0.008)); rms=[]
    for f0 in range(0,n,win):
        f1=min(n,f0+win); ss=0; count=0
        for i in range(f0*ch,f1*ch):
            v=vals[i]; ss+=v*v; count+=1
        rms.append(math.sqrt(ss/max(1,count)))
    peak=max(rms) if rms else 0; threshold=max(14.0,peak*0.006)
    active=[i for i,v in enumerate(rms) if v>=threshold]
    if active:
        a=max(0,active[0]*win-int(pre*rate)); b=min(n,(active[-1]+1)*win+int(post*rate))
    else: a,b=0,n
    ww=wave.open(dst,'wb'); ww.setnchannels(ch); ww.setsampwidth(sw); ww.setframerate(rate); ww.writeframes(vals[a*ch:b*ch].tobytes()); ww.close()

def dur(path): return source_duration(path)

def extract(src,spans,prefix):
    for n,(a,z) in enumerate(spans):
        raw=f'parts2/{prefix}{n:02d}_raw.wav'; trim=f'parts2/{prefix}{n:02d}_trim.wav'; out=f'parts2/{prefix}{n:02d}.wav'
        subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',str(a),'-to',str(z),'-i',src,'-vn','-ac','2','-ar','48000','-c:a','pcm_s16le',raw],check=True)
        energy_trim_wav(raw,trim); d=dur(trim); fadeout=max(0,d-0.009)
        subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',trim,'-af',f'afade=t=in:st=0:d=0.005,afade=t=out:st={fadeout}:d=0.009','-ac','2','-ar','48000','-c:a','pcm_s16le',out],check=True)

male=[t for s,t in TURNS if s=='m']; female=[t for s,t in TURNS if s=='f']
mm=safe_handles(map_exact(parse_srt('male.srt'),male),source_duration('male.mp4'))
fm=safe_handles(map_exact(parse_srt('female.srt'),female),source_duration('female.mp4'))
Path('parts2').mkdir(exist_ok=True); extract('male.mp4',mm,'m'); extract('female.mp4',fm,'f')
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-t','0.105','-c:a','pcm_s16le','parts2/silence.wav'],check=True)
mi=fi=0; clips=[]; entries=[]
for sp,text in TURNS:
    if sp=='m': p=f'parts2/m{mi:02d}.wav'; mi+=1
    else: p=f'parts2/f{fi:02d}.wav'; fi+=1
    clips.append((p,text)); entries += [f"file '../{p}'","file 'silence.wav'"]
Path('parts2/concat.txt').write_text('\n'.join(entries))
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i','parts2/concat.txt','-af','loudnorm=I=-16:LRA=9:TP=-1.5','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','video2_humanized_dialogue_CLEAN.m4a'],check=True)

def fmt(t):
    h=int(t//3600); t-=h*3600; m=int(t//60); t-=m*60; s=int(t); ms=int(round((t-s)*1000));
    if ms==1000: s+=1; ms=0
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
current=0.0; caps=[]
for k,(p,text) in enumerate(clips,1):
    d=dur(p); caps.append(f'{k}\n{fmt(current)} --> {fmt(current+d)}\n{text}\n'); current+=d+0.105
Path('video2_humanized_dialogue_CLEAN.srt').write_text('\n'.join(caps))
print('CLEAN DURATION',current)
