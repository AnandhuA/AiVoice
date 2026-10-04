"""JSON event transport for a worker running in an isolated Python environment."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys


class EventWriter:
    def put(self, event):
        print('MVS_EVENT ' + json.dumps(event, ensure_ascii=False), flush=True)


class FileCancellation:
    def __init__(self, path: str):
        self.path = Path(path)

    def is_set(self):
        return self.path.exists()


def main():
    job = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    os.environ['HF_HOME'] = str(Path(job['model_root']) / 'hf-cache')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from .core.jobs import generation_worker
    generation_worker(job['project'], job['model_root'], job['cache'], job['device'],
                      job['ffmpeg'], job['selected'], job['force'], EventWriter(),
                      FileCancellation(job['cancel_file']))


if __name__ == '__main__':
    main()
