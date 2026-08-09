import re, subprocess, difflib, wave, math, array
from pathlib import Path

TURNS=[
('m',"You ever sit there at night thinking, man... I really need to get my whole life together?"),
('f',"Tonight?"),('m',"Well... eventually."),
('f',"Good. Because tonight you're exhausted, overwhelmed, and being a little dramatic."),
('m',"A little?"),('f',"I'm being supportive."),
('m',"I think that's where people get stuck. They start thinking about forever. Forever sober. Forever disciplined. Never screwing up again."),
('f',"Forever is huge. Try today."),('m',"Just today?"),
('f',"Today is plenty. What do you need to do before you go to sleep without making your life worse?"),
('m',"Wanting a better life matters."),
('f',"Absolutely. But your actions eventually need to find out about this wonderful new plan."),
('m',"So make the call. Go home when you know you should go home. Show up tomorrow. Tell the truth."),
('f',"Desire gets you pointed in the right direction."),('m',"And your feet still have to move."),
('m',"One thing I've learned is that things get dangerous when you disappear into your own head."),
('f',"Especially when your brain starts saying, don't tell anybody. I can handle this myself. How'd that strategy work last time?"),
('m',"Rude. Accurate, though."),
('f',"Call somebody before you do the thing you already know you're going to regret. Not afterward."),
('m',"And sometimes you have to admit you can't control everything."),('f',"He hates this section."),
('m',"I really do."),('f',"I know."),
('m',"You don't have to have every spiritual answer figured out. Call it God. Faith. Purpose. Your Higher Power. Something bigger than whatever emotion happens to be screaming the loudest right now."),
('f',"Because not every feeling deserves a vote."),
('m',"Ask for enough direction to do the next right thing. That's enough for today."),
('m',"At the end of the day, take a minute and be honest with yourself. What did I do right? Where was I full of crap? Did I hurt somebody? Is there something I need to apologize for or make right?"),
('f',"And then fix what you can. Don't turn self-reflection into a three-hour meeting about how terrible you are."),
('m',"Be accountable."),('f',"Not cruel."),('m',"You're still going to have bad days."),
('f',"You'll get angry. Tired. Lonely. Somebody will get on your last nerve."),
('m',"You might even screw something up."),
('f',"But one bad decision does not require another one. A bad day doesn't need a sequel."),
('m',"Get honest. Reach out. Correct course. And keep moving."),
('m',"Eventually something else happens. You stop spending every waking minute thinking about your own problems."),
('f',"Which is healthy, because that room gets crowded."),
('m',"You help somebody. You check on somebody. You encourage the person who's a few steps behind you."),
('f',"And suddenly your worst years aren't completely wasted. They taught you something another person might need."),
('m',"That's what a comeback usually looks like. Not some giant movie moment. You get through today differently. Then tomorrow. Then another day."),
('f',"And after a while, you start collecting evidence."),('m',"Evidence of what?"),
('f',"That maybe you're not that old version of yourself anymore. You're just still used to talking about yourself like you are."),
('m',"So no. You don't need a whole new life tonight."),('f',"You need some honesty."),
('m',"Some willingness."),('f',"People you can call."),('m',"Something bigger than yourself."),
('f',"And one decent decision."),('m',"Today."),
('f',"Of course, tomorrow morning you're probably going to wake up and feel absolutely zero motivation."),
('m',"Can I enjoy this victory for like ten seconds?"),('f',"Nope.")]


def ts(s):
    h,m,rest=s.replace(',','.').split(':')
    return int(h)*3600+int(m)*60+float(rest)


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
        res.append((max(0,cues[i][0]-0.35), cues[j][1]+0.40))
        i=j+1
    return res

male=[t for s,t in TURNS if s=='m']; female=[t for s,t in TURNS if s=='f']
mm=map_turns(parse_srt('male.srt'),male); fm=map_turns(parse_srt('female.srt'),female)
Path('cleanparts').mkdir(exist_ok=True)


def dur(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',path]))


def energy_trim_wav(src,dst,pre=0.080,post=0.110):
    w=wave.open(src,'rb'); ch=w.getnchannels(); sw=w.getsampwidth(); rate=w.getframerate(); n=w.getnframes(); raw=w.readframes(n); w.close()
    assert sw==2
    vals=array.array('h'); vals.frombytes(raw)
    win=max(1,int(rate*0.010)); rms=[]
    for f0 in range(0,n,win):
        f1=min(n,f0+win); ss=0; count=0
        for i in range(f0*ch,f1*ch):
            v=vals[i]; ss+=v*v; count+=1
        rms.append(math.sqrt(ss/max(1,count)))
    peak=max(rms) if rms else 0
    threshold=max(18.0,peak*0.008)
    active=[i for i,v in enumerate(rms) if v>=threshold]
    if active:
        a=max(0,active[0]*win-int(pre*rate)); b=min(n,(active[-1]+1)*win+int(post*rate))
    else:
        a=0; b=n
    out=vals[a*ch:b*ch]
    ww=wave.open(dst,'wb'); ww.setnchannels(ch); ww.setsampwidth(sw); ww.setframerate(rate); ww.writeframes(out.tobytes()); ww.close()


def extract(src,spans,prefix):
    for n,(a,z) in enumerate(spans):
        raw=f'cleanparts/{prefix}{n:02d}_raw.wav'; trim=f'cleanparts/{prefix}{n:02d}_trim.wav'; out=f'cleanparts/{prefix}{n:02d}.wav'
        subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',str(a),'-to',str(z),'-i',src,'-vn','-ac','2','-ar','48000','-c:a','pcm_s16le',raw],check=True)
        energy_trim_wav(raw,trim)
        d=dur(trim); fadeout=max(0,d-0.010)
        subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',trim,'-af',f'afade=t=in:st=0:d=0.006,afade=t=out:st={fadeout}:d=0.010','-ac','2','-ar','48000','-c:a','pcm_s16le',out],check=True)

extract('male.mp4',mm,'m'); extract('female.mp4',fm,'f')
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-t','0.095','-c:a','pcm_s16le','cleanparts/silence.wav'],check=True)
mi=fi=0; entries=[]; clips=[]
for sp,text in TURNS:
    if sp=='m': p=f'cleanparts/m{mi:02d}.wav'; mi+=1
    else: p=f'cleanparts/f{fi:02d}.wav'; fi+=1
    clips.append((p,text)); entries += [f"file '../{p}'","file 'silence.wav'"]
Path('cleanparts/concat.txt').write_text('\n'.join(entries))
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i','cleanparts/concat.txt','-af','loudnorm=I=-16:LRA=9:TP=-1.5','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','video2_humanized_dialogue_CLEAN.m4a'],check=True)


def fmt(t):
    h=int(t//3600); t-=h*3600; m=int(t//60); t-=m*60; s=int(t); ms=int(round((t-s)*1000))
    if ms==1000: s+=1; ms=0
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

current=0.0; caps=[]
for k,(p,text) in enumerate(clips,1):
    d=dur(p); caps.append(f'{k}\n{fmt(current)} --> {fmt(current+d)}\n{text}\n'); current+=d+0.095
Path('video2_humanized_dialogue_CLEAN.srt').write_text('\n'.join(caps))
print('CLEAN DURATION',current)
