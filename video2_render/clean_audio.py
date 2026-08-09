import re, subprocess, difflib
from pathlib import Path

SEQ='mfmfmfmfmfmfmfmmfmfmfmfmfmmfmfmfmfmmfmfmfmfmfmfmfmfmf'


def ts(s):
    h,m,rest=s.replace(',','.').split(':')
    return int(h)*3600+int(m)*60+float(rest)


def parse_srt(path):
    txt=Path(path).read_text(errors='ignore').strip()
    out=[]
    for b in re.split(r'\n\s*\n',txt):
        lines=[x.strip() for x in b.splitlines() if x.strip()]
        ti=next((i for i,l in enumerate(lines) if '-->' in l),None)
        if ti is None: continue
        a,z=[x.strip() for x in lines[ti].split('-->')]
        out.append((ts(a),ts(z),' '.join(lines[ti+1:])))
    return out


def norm(s):
    s=s.lower().replace('’',"'")
    s=re.sub(r'[^a-z0-9\s\']',' ',s)
    return ' '.join(s.split())


def map_turns(cues, expected):
    res=[]; i=0
    for turn in expected:
        target=norm(turn); tw=len(target.split()); best=None
        for j in range(i,min(len(cues),i+10)):
            cn=norm(' '.join(c[2] for c in cues[i:j+1])); cw=len(cn.split())
            score=difflib.SequenceMatcher(None,target,cn).ratio()-abs(cw-tw)/max(tw,1)*0.10
            if best is None or score>best[0]: best=(score,j)
            if cw>tw*1.7+5: break
        if best is None: raise RuntimeError('No cue match: '+turn)
        j=best[1]
        # Subtitle timestamps can sit inside consonant attacks/tails. Take generous handles.
        res.append((max(0,cues[i][0]-0.24), cues[j][1]+0.28))
        i=j+1
    return res

final=parse_srt('video2_humanized_dialogue.srt')
texts=[x[2] for x in final]
assert len(texts)==len(SEQ)==53
male=[t for s,t in zip(SEQ,texts) if s=='m']
female=[t for s,t in zip(SEQ,texts) if s=='f']
mm=map_turns(parse_srt('male.srt'),male)
fm=map_turns(parse_srt('female.srt'),female)
Path('cleanparts').mkdir(exist_ok=True)


def dur(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',path]))


def extract(src, spans, prefix):
    for n,(a,z) in enumerate(spans):
        raw=f'cleanparts/{prefix}{n:02d}_raw.wav'
        out=f'cleanparts/{prefix}{n:02d}.wav'
        subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',str(a),'-to',str(z),'-i',src,'-vn','-ac','2','-ar','48000','-c:a','pcm_s16le',raw],check=True)
        # Trim only exterior dead air while preserving a safety cushion around speech.
        trimmed=f'cleanparts/{prefix}{n:02d}_trim.wav'
        filt='silenceremove=start_periods=1:start_duration=0.01:start_threshold=-46dB:start_silence=0.075:stop_periods=1:stop_duration=0.01:stop_threshold=-46dB:stop_silence=0.095'
        subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',raw,'-af',filt,'-ac','2','-ar','48000','-c:a','pcm_s16le',trimmed],check=True)
        d=dur(trimmed)
        fadeout=max(0,d-0.012)
        subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',trimmed,'-af',f'afade=t=in:st=0:d=0.008,afade=t=out:st={fadeout}:d=0.012','-ac','2','-ar','48000','-c:a','pcm_s16le',out],check=True)

extract('male.mp4',mm,'m')
extract('female.mp4',fm,'f')
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-t','0.105','-c:a','pcm_s16le','cleanparts/silence.wav'],check=True)

mi=fi=0; entries=[]; clips=[]
for sp,text in zip(SEQ,texts):
    if sp=='m': p=f'cleanparts/m{mi:02d}.wav'; mi+=1
    else: p=f'cleanparts/f{fi:02d}.wav'; fi+=1
    clips.append((p,text))
    entries += [f"file '../{p}'", "file 'silence.wav'"]
Path('cleanparts/concat.txt').write_text('\n'.join(entries))
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i','cleanparts/concat.txt','-af','loudnorm=I=-16:LRA=9:TP=-1.5','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','video2_humanized_dialogue_CLEAN.m4a'],check=True)


def fmt(t):
    h=int(t//3600); t-=h*3600; m=int(t//60); t-=m*60; s=int(t); ms=int(round((t-s)*1000))
    if ms==1000: s+=1; ms=0
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

current=0.0; caps=[]
for k,(p,text) in enumerate(clips,1):
    d=dur(p)
    caps.append(f'{k}\n{fmt(current)} --> {fmt(current+d)}\n{text}\n')
    current+=d+0.105
Path('video2_humanized_dialogue_CLEAN.srt').write_text('\n'.join(caps))
print('CLEAN DURATION',current)
