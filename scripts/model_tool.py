"""Inspect and install models with an explicit command-line confirmation."""
import argparse
import json
from pathlib import Path

from malayalam_voice_studio.tts.model_manager import download_plan, install


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('model', choices=['praha', 'parler', 'indicf5'])
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    plan = download_plan(args.model)
    print(json.dumps(plan, indent=2))
    print(f"Total: {plan['bytes'] / 1024**3:.2f} GiB; license: {plan['license']}")
    if args.install:
        if input('Type DOWNLOAD to approve these files: ').strip() != 'DOWNLOAD':
            print('No model files downloaded.')
            return
        install(Path('models'), plan, print)


if __name__ == '__main__':
    main()
