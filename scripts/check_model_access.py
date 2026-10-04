"""Check existing authentication without printing token contents or downloading weights."""
import os
from pathlib import Path
import urllib.error
import urllib.request


def main():
    token_path = Path(os.environ.get('HF_TOKEN_PATH', Path(os.environ.get('HF_HOME', Path.home() / '.cache' / 'huggingface')) / 'token'))
    token = os.environ.get('HF_TOKEN') or (token_path.read_text().strip() if token_path.is_file() else '')
    url = 'https://huggingface.co/ai4bharat/indic-parler-tts/resolve/7b527af5ee8ed1f9a28d80b19703ed9bb8ba10ca/config.json'
    request = urllib.request.Request(url, method='HEAD', headers={'Authorization': f'Bearer {token}'} if token else {})
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            print('Indic Parler access: available (HTTP', response.status, ')')
    except urllib.error.HTTPError as exc:
        print('Indic Parler access: unavailable (HTTP', exc.code, '). Accept model terms and authenticate locally.')
        raise SystemExit(2)


if __name__ == '__main__':
    main()
