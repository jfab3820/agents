import os,re,subprocess,difflib
from pathlib import Path

ROOT=Path('.')
MALE_MP4='male.mp4'; FEMALE_MP4='female.mp4'; MALE_SRT='male.srt'; FEMALE_SRT='female.srt'

def ts(s):
    h,m,rest=s.replace(',','.').split(':'); return int(h)*3600+int(m)*60+float(rest)

def parse_srt(path):
    txt=Path(path).read_text(errors='ignore').strip()
    blocks=re.split(r'\n\s*\n',txt)
    out=[]
    for b in blocks:
        lines=[x.strip() for x in b.splitlines() if x.strip()]
        if len(lines)<3 or '-->' not in lines[1]: continue
        a,z=[x.strip() for x in lines[1].split('-->')]
        out.append((ts(a),ts(z),' '.join(lines[2:])))
    return out

def norm(s):
    s=s.lower().replace('’',"'")
    s=re.sub(r'[^a-z0-9\s\']',' ',s)
    return ' '.join(s.split())

def map_turns(cues, expected):
    res=[]; i=0
    for turn in expected:
        target=norm(turn); tw=len(target.split()); best=None
        maxj=min(len(cues), i+10)
        for j in range(i,maxj):
            cand=' '.join(c[2] for c in cues[i:j+1]); cn=norm(cand); cw=len(cn.split())
            ratio=difflib.SequenceMatcher(None,target,cn).ratio()
            penalty=abs(cw-tw)/max(tw,1)*0.10
            score=ratio-penalty
            if best is None or score>best[0]: best=(score,j,cn)
            if cw>tw*1.7+5: break
        if best is None: raise RuntimeError('No cue match: '+turn)
        j=best[1]
        start=max(0,cues[i][0]-0.08); end=cues[j][1]+0.10
        print(f'MAP {i}-{j} {best[0]:.3f}: {turn[:55]}')
        res.append((start,end)); i=j+1
    return res

male=[
"You ever sit there at night thinking, man... I really need to get my whole life together?",
"Well... eventually.","A little?",
"I think that's where people get stuck. They start thinking about forever. Forever sober. Forever disciplined. Never screwing up again.",
"Just today?","Wanting a better life matters.",
"So make the call. Go home when you know you should go home. Show up tomorrow. Tell the truth.",
"And your feet still have to move.",
"One thing I've learned is that things get dangerous when you disappear into your own head.",
"Rude. Accurate, though.",
"And sometimes you have to admit you can't control everything.","I really do.",
"You don't have to have every spiritual answer figured out. Call it God. Faith. Purpose. Your Higher Power. Something bigger than whatever emotion happens to be screaming the loudest right now.",
"Ask for enough direction to do the next right thing. That's enough for today.",
"At the end of the day, take a minute and be honest with yourself. What did I do right? Where was I full of crap? Did I hurt somebody? Is there something I need to apologize for or make right?",
"Be accountable.","You're still going to have bad days.","You might even screw something up.",
"Get honest. Reach out. Correct course. And keep moving.",
"Eventually something else happens. You stop spending every waking minute thinking about your own problems.",
"You help somebody. You check on somebody. You encourage the person who's a few steps behind you.",
"That's what a comeback usually looks like. Not some giant movie moment. You get through today differently. Then tomorrow. Then another day.",
"Evidence of what?","So no. You don't need a whole new life tonight.","Some willingness.","Something bigger than yourself.","Today.",
"Can I enjoy this victory for like ten seconds?"
]

female=[
"Tonight?","Good. Because tonight you're exhausted, overwhelmed, and being a little dramatic.","I'm being supportive.",
"Forever is huge. Try today.","Today is plenty. What do you need to do before you go to sleep without making your life worse?",
"Absolutely. But your actions eventually need to find out about this wonderful new plan.",
"Desire gets you pointed in the right direction.",
"Especially when your brain starts saying, don't tell anybody. I can handle this myself. How'd that strategy work last time?",
"Call somebody before you do the thing you already know you're going to regret. Not afterward.",
"He hates this section.","I know.","Because not every feeling deserves a vote.",
"And then fix what you can. Don't turn self-reflection into a three-hour meeting about how terrible you are.","Not cruel.",
"You'll get angry. Tired. Lonely. Somebody will get on your last nerve.",
"But one bad decision does not require another one. A bad day doesn't need a sequel.",
"Which is healthy, because that room gets crowded.",
"And suddenly your worst years aren't completely wasted. They taught you something another person might need.",
"And after a while, you start collecting evidence.",
"That maybe you're not that old version of yourself anymore. You're just still used to talking about yourself like you are.",
"You need some honesty.","People you can call.","And one decent decision.",
"Of course, tomorrow morning you're probably going to wake up and feel absolutely zero motivation.","Nope."
]

turns=[('m',0),('f',0),('m',1),('f',1),('m',2),('f',2),('m',3),('f',3),('m',4),('f',4),('m',5),('f',5),('m',6),('f',6),('m',7),('m',8),('f',7),('m',9),('f',8),('m',10),('f',9),('m',11),('f',10),('m',12),('f',11),('m',13),('m',14),('f',12),('m',15),('f',13),('m',16),('f',14),('m',17),('f',15),('m',18),('m',19),('f',16),('m',20),('f',17),('m',21),('f',18),('m',22),('f',19),('m',23),('f',20),('m',24),('f',21),('m',25),('f',22),('m',26),('f',23),('m',27),('f',24)]

mc=parse_srt(MALE_SRT); fc=parse_srt(FEMALE_SRT)
mm=map_turns(mc,male); fm=map_turns(fc,female)
Path('parts').mkdir(exist_ok=True)

def extract(src, spans, prefix):
    for n,(a,z) in enumerate(spans):
        out=f'parts/{prefix}{n:02d}.wav'
        subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',str(a),'-to',str(z),'-i',src,'-vn','-ac','2','-ar','48000','-c:a','pcm_s16le',out],check=True)
extract(MALE_MP4,mm,'m'); extract(FEMALE_MP4,fm,'f')
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-t','0.22','-c:a','pcm_s16le','parts/silence.wav'],check=True)

lst=[]
for sp,idx in turns:
    lst.append(f"file '{sp}{idx:02d}.wav'")
    lst.append("file 'silence.wav'")
Path('parts/concat.txt').write_text('\n'.join(lst))
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i','parts/concat.txt','-af','loudnorm=I=-16:LRA=9:TP=-1.5','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','video2_humanized_dialogue.m4a'],check=True)

# Build captions from actual part durations
current=0.0; cap=[]
alltexts=[]
for sp,idx in turns: alltexts.append(male[idx] if sp=='m' else female[idx])
for k,((sp,idx),text) in enumerate(zip(turns,alltexts),1):
    p=f'parts/{sp}{idx:02d}.wav'
    d=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',p]))
    def fmt(t):
        h=int(t//3600); t-=h*3600; m=int(t//60); t-=m*60; s=int(t); ms=int(round((t-s)*1000));
        if ms==1000: s+=1; ms=0
        return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
    cap.append(f'{k}\n{fmt(current)} --> {fmt(current+d)}\n{text}\n')
    current += d+0.22
Path('video2_humanized_dialogue.srt').write_text('\n'.join(cap))
print('FINAL DURATION',current)
