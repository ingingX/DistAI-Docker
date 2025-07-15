#!/usr/bin/env python
"""
Smoke‑test script

--------
Usage:
- Send text-only requests to trigger BERT worker
- Send image-only requests to trigger MobileNet worker
- Send both text and image to trigger CLIP worker
--------

--------
Supports command-line arguments:
--api        localhost or coordinator API (default: http://coordinator:8000/infer)
--mode       text | image | both
--text       optional string input
--image_url  public URL to image
--------

--------
Examples
# Run from host machine
python scripts/test_request.py --api http://localhost:8000/infer --mode text --text "This is a BERT test"
python scripts/test_request.py --api http://localhost:8000/infer --mode image --image_url "https://picsum.photos/256"
python scripts/test_request.py --api http://localhost:8000/infer --mode both --text "This is a CLIP test" --image_url "https://picsum.photos/256"

# Run from within Docker container
docker-compose exec coordinator python /scripts/test_request.py --mode text --text "test BERT input"
docker-compose exec coordinator python /scripts/test_request.py --mode image --image_url "https://picsum.photos/256"
docker-compose exec coordinator python /scripts/test_request.py --mode both --text "a cat" --image_url "https://picsum.photos/256"
--------
"""

import os, base64, argparse, requests

# Download image and encode to base64
def fetch_image_b64(url: str) -> str:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return base64.b64encode(resp.content).decode()

# main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api', default=os.getenv('API_URL', 'http://coordinator:8000/infer'),
                        help='Coordinator /infer endpoint')
    parser.add_argument('--image_url', default='https://picsum.photos/256',
                        help='Image URL for testing')
    parser.add_argument('--text', default='a random photo',
                        help='Text prompt for testing')
    parser.add_argument('--mode', choices=['text', 'image', 'both'], default='both',
                        help='Type of input to send (default: both)')
    args = parser.parse_args()

    payload = {}

    if args.mode in ('image', 'both'):
        try:
            img_b64 = fetch_image_b64(args.image_url)
            payload['image_base64'] = img_b64
        except Exception as e:
            print("Image fetch failed:", e)
            return

    if args.mode in ('text', 'both'):
        if args.text.strip():
            payload['text'] = args.text

    print(f'Sending {args.mode} request to {args.api} ...')
    # Send task to coordinator
    try:
        r = requests.post(args.api, json=payload, timeout=30)
        print('Status:', r.status_code)
        print('Response:', r.json())
    except Exception as e:
        print('Request failed:', e)

if __name__ == '__main__':
    main()
