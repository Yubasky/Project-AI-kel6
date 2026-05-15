import urllib.request
import json

url = 'http://localhost/Project-AI/app/api.php'
data = {
    "budget": 15000000,
    "profile": "Gaming",
    "method": "sugeno",
    "brand": "",
    "os": "",
    "min_display": 0
}
req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})

try:
    response = urllib.request.urlopen(req)
    print("STATUS:", response.status)
    print("RESPONSE:", response.read().decode('utf-8')[:500])
except Exception as e:
    print("ERROR:", e)
    if hasattr(e, 'read'):
        print("DETAIL:", e.read().decode('utf-8'))
