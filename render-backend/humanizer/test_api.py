import httpx

def test_analyze():
    print("Testing /api/analyze...")
    resp = httpx.post("http://127.0.0.1:8000/api/analyze", json={"text": "This is a test document. It is very fast-paced and delving into the details. It is written by me."})
    print("Status:", resp.status_code)
    print("Response:", resp.json())

def test_humanize():
    print("\nTesting /api/humanize...")
    resp = httpx.post("http://127.0.0.1:8000/api/humanize", json={
        "text": "This is a test document.",
        "tone": "casual",
        "reading_level": "medium",
        "strength": 1,
        "keep_length": True,
        "provider": None
    })
    print("Status:", resp.status_code)
    print("Response:", resp.json())

if __name__ == "__main__":
    test_analyze()
    test_humanize()
