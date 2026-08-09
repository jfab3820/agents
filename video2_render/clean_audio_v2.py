import subprocess
from pathlib import Path

# Patch the older cleanup script at runtime so its trim stage only removes
# silence from the OUTSIDE edges of each speaker turn. Internal pauses stay.
real_run = subprocess.run

def safe_run(args, *a, **kw):
    if isinstance(args, list) and '-af' in args:
        args = list(args)
        i = args.index('-af') + 1
        if isinstance(args[i], str) and args[i].startswith('silenceremove=start_periods=1:'):
            args[i] = (
                'silenceremove=start_periods=1:start_duration=0.01:'
                'start_threshold=-46dB:start_silence=0.075,'
                'areverse,'
                'silenceremove=start_periods=1:start_duration=0.01:'
                'start_threshold=-46dB:start_silence=0.095,'
                'areverse'
            )
    return real_run(args, *a, **kw)

subprocess.run = safe_run
code = Path('video2_render/clean_audio.py').read_text()
exec(compile(code, 'video2_render/clean_audio.py', 'exec'), {'__name__': '__main__'})
