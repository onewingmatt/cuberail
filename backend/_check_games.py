import urllib.request, json

def api(method, path, data=None, token=None):
    url = f"http://localhost:8000{path}"
    headers = {"Content-Type": "application/json"} if data is not None else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()}

for user, pw in [("browser_test","test123"), ("integration_test","test123"),
                 ("test_runner","test123")]:
    login = api("POST", "/api/auth/login", {"username": user, "password": pw})
    if "error" in login:
        continue
    token = login.get("access_token")
    games = api("GET", "/api/games/", token=token)
    if games:
        print(f"User '{user}' has {len(games)} open games:")
        for g in games:
            print(f"  {g['id']}: {g['game_type']}")
            state = api("GET", f"/api/games/{g['id']}/state", token=token)
            if "error" not in state:
                print(f"    current={str(state.get('current_player',''))[:16]}.. cubes={state.get('city_cubes')} tracks={state.get('laid_tracks')}")
        break
else:
    print("No open games found for any user")
