"""Live smoke test against real B2 storage."""
import io
import sys

import httpx


def main() -> int:
    base = "http://localhost:8000"

    # 1) Login as admin
    r = httpx.post(
        f"{base}/v1/auth/login",
        json={"email": "admin@anjaneya.app", "password": "admin1234"},
    )
    if r.status_code != 200:
        print(f"login failed: {r.status_code} {r.text}")
        return 1
    token = r.json()["tokens"]["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    # 2) List titles to find a movie ID
    titles = httpx.get(f"{base}/v1/titles?type=movie&page_size=10").json()["items"]
    if not titles:
        print("no movie titles found; run scripts/seed_dev_data.py first")
        return 1
    movie_id = titles[0]["id"]
    print(f"using movie id={movie_id} ({titles[0]['slug']})")

    # 3) Upload a tiny fake mp4
    fake = io.BytesIO(b"FAKE MP4 BYTES FOR B2 SMOKE TEST " * 100)
    fake.name = "smoketest.mp4"

    print("uploading ~3 KB to B2 (allowing 180s for Neon cold-start + B2 round trip)...")
    r = httpx.post(
        f"{base}/v1/admin/titles/{movie_id}/upload-video",
        headers=h,
        files={"file": ("smoketest.mp4", fake, "video/mp4")},
        timeout=180,
    )
    if r.status_code != 200:
        print(f"upload failed: {r.status_code} {r.text}")
        return 1
    body = r.json()
    print(f"  key:          {body['key']}")
    print(f"  stored_ref:   {body['stored_ref']}")
    print(f"  playable_url: {body['playable_url'][:80]}...")

    # 4) Try to fetch the file from B2 via the presigned URL
    print("fetching from B2 via presigned URL...")
    r = httpx.get(body["playable_url"], timeout=30)
    if r.status_code != 200:
        print(f"FETCH FAILED: {r.status_code}")
        print(f"  body: {r.text[:300]}")
        return 1
    if not r.content.startswith(b"FAKE MP4 BYTES"):
        print(f"WRONG CONTENT: {r.content[:50]!r}")
        return 1
    print(f"  ok — {len(r.content)} bytes, content matches")

    # 5) Title detail should now show the bucket key as storage_url
    detail = httpx.get(f"{base}/v1/titles/{movie_id}").json()
    hls = [a for a in detail["assets"] if a["kind"] == "hls_manifest"]
    print(f"  title detail storage_url: {hls[0]['storage_url']}")
    print("\nB2 round-trip smoke test PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
