"""Generate final Prussian Rails hex map.
Uses staggered board coords (col, row) converted to axial (q, r) for engine.
Conversion: q = col, r = row - floor(col/2)
"""

import json

HEX_W = 40
HEX_H = 46
STAGGER = 23
ORIGIN_X = 265
ORIGIN_Y = 55
IMG_W = 1409
IMG_H = 1046

def pixel_to_board(px, py):
    """Convert pixel position to board (col, row)."""
    col = round((px - ORIGIN_X) / HEX_W)
    py_adj = py - (col % 2) * STAGGER
    row = round((py_adj - ORIGIN_Y) / HEX_H)
    return (col, row)

def board_to_axial(col, row):
    """Convert board (col, row) to axial (q, r)."""
    q = col
    r = row - (col // 2)  # integer division
    return (q, r)

def axial_to_board(q, r):
    """Convert axial (q, r) to board (col, row)."""
    col = q
    row = r + (col // 2)
    return (col, row)

def board_pixel(col, row):
    x = ORIGIN_X + col * HEX_W
    y = ORIGIN_Y + row * HEX_H + (col % 2) * STAGGER
    return (x, y)

def axial_pixel(q, r):
    col, row = axial_to_board(q, r)
    return board_pixel(col, row)

# Axial neighbors (standard flat-top)
AXIAL_DIRS = [(1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1)]

def axial_neighbors(q, r):
    return [(q + dq, r + dr) for dq, dr in AXIAL_DIRS]

# City positions on the board in (col, row), then convert to axial
cities_board = {
    "Flensburg": (0, 0), "Kiel": (3, 0), "Stralsund": (5, 0),
    "Stolp": (12, 0), "Danzig": (15, 0), "Königsberg": (16, 0),
    "Rostock": (4, 1), "Lübeck": (2, 2), "Neu Brandenburg": (6, 2),
    "Schneidemühl": (13, 2), "Hamburg": (0, 3), "Stettin": (8, 3),
    "Kreuz": (13, 3), "Bromberg": (14, 3),
    "Oldenburg": (-2, 4), "Bremen": (-1, 4), "Wittenberge": (3, 4),
    "Osnabrück": (-1, 5), "Bielefeld": (0, 6), "Hannover": (1, 6),
    "Braunschweig": (3, 6), "Duisburg": (-5, 7), "Wesel": (-4, 7),
    "Essen": (-3, 7), "Münster": (-2, 7), "Hamm": (0, 7),
    "Göttingen": (3, 7), "Magdeburg": (4, 7), "Berlin": (6, 7),
    "Frankfurt an der Oder": (8, 7), "Posen": (11, 7),
    "Dortmund": (-2, 8), "Kassel": (2, 8), "Halle": (4, 8),
    "Leipzig": (5, 8), "Kottbus": (9, 8),
    "Düsseldorf": (-4, 9), "Mühlhausen": (4, 9), "Erfurt": (5, 9),
    "Görlitz": (11, 9), "Liegnitz": (12, 9),
    "Aachen": (-5, 10), "Chemnitz": (7, 10), "Plauen": (7, 10),
    "Dresden": (8, 10), "Breslau": (11, 10),
    "Würzburg": (3, 11), "Waldenburg": (12, 11),
    "Köln": (-4, 12), "Koblenz": (-2, 12), "Mainz": (-1, 12),
    "Bamberg": (4, 12), "Frankfurt am Main": (-2, 13),
    "Nürnberg": (6, 13), "Regensburg": (8, 13),
    "Saarbrücken": (-3, 14), "Mannheim": (0, 15), "Augsburg": (3, 15),
    "Karlsruhe": (0, 16), "Heilbronn": (1, 16),
    "Strasbourg": (-2, 17), "Stuttgart": (2, 17),
    "Freiburg im Breisgau": (-1, 18), "München": (3, 18),
}

incomes = {
    "Hamburg": 3, "Berlin": 3, "Köln": 2,
    "Frankfurt am Main": 2, "Leipzig": 2,
    "Dresden": 2, "Breslau": 2, "München": 3,
    "Königsberg": 3, "Mannheim": 1,
}

# Convert to axial
cities_axial = {}
for name, (col, row) in cities_board.items():
    q, r = board_to_axial(col, row)
    cities_axial[name] = (q, r)

# Build hex grid
all_hexes = {}
for name, (q, r) in cities_axial.items():
    key = f"{q},{r}"
    all_hexes[key] = {"terrain": "urban", "city": name, "income": incomes.get(name, 0)}

# Expand: add axial neighbors that fall within the board bounds
q_vals = [v[0] for v in cities_axial.values()]
r_vals = [v[1] for v in cities_axial.values()]
min_q, max_q = min(q_vals), max(q_vals)
min_r, max_r = min(r_vals), max(r_vals)

# Fill a rectangular grid within bounds
for q in range(min_q - 2, max_q + 3):
    for r in range(min_r - 2, max_r + 3):
        key = f"{q},{r}"
        if key in all_hexes:
            continue
        # Check if this hex's pixel center is within the board image
        px, py = axial_pixel(q, r)
        if 20 <= px <= IMG_W - 20 and 15 <= py <= IMG_H - 15:
            all_hexes[key] = {"terrain": "plains"}

# Remove isolated hexes (1 or fewer neighbors in the map)
for key in list(all_hexes.keys()):
    if "city" in all_hexes[key]:
        continue
    q, r = map(int, key.split(','))
    n = sum(1 for nq, nr in axial_neighbors(q, r) if f"{nq},{nr}" in all_hexes)
    if n <= 1:
        del all_hexes[key]

# Set terrain types
for key in list(all_hexes.keys()):
    if "city" in all_hexes[key]:
        continue
    q, r = map(int, key.split(','))
    col, _ = axial_to_board(q, r)
    
    # Mountains in south
    if r >= 15 and q <= 2:
        all_hexes[key]["terrain"] = "mountains"
    elif r >= 16 and q <= 4:
        all_hexes[key]["terrain"] = "mountains"
    elif r >= 17:
        all_hexes[key]["terrain"] = "mountains"
    elif r >= 13 and q >= 10:
        all_hexes[key]["terrain"] = "mountains"
    # Hills in central-west
    elif r >= 9 and r <= 12 and q <= -1:
        all_hexes[key]["terrain"] = "hills"
    elif r >= 10 and r <= 13 and q <= 1:
        all_hexes[key]["terrain"] = "hills"
    elif r >= 11 and r <= 13 and q <= 3:
        all_hexes[key]["terrain"] = "hills"

# Berlin approach hexes
berlin_bq, berlin_br = cities_axial["Berlin"]
berlin_approaches = []
for dq in range(-2, 3):
    for dr in range(-2, 3):
        q, r = berlin_bq + dq, berlin_br + dr
        if (dq, dr) == (0, 0):
            continue
        dist = max(abs(dq), abs(dr), abs(dq + dr))
        if 1 <= dist <= 2:
            key = f"{q},{r}"
            if key in all_hexes and "city" not in all_hexes[key]:
                all_hexes[key]["terrain"] = "berlin_approach"
                berlin_approaches.append({"q": q, "r": r})

# Companies
companies = [
    {"id": "Preußische Ostbahn", "color": "#1a1a1a", "home": "Königsberg",
     "start_income": 3, "track_count": 20, "ability": "build_4"},
    {"id": "Niederschlesisch-Märkische", "color": "#8B4513", "home": "Breslau",
     "start_income": 2, "track_count": 17, "ability": "no_city_penalty"},
    {"id": "Königlich-Sächsische", "color": "#FF8C00", "home": "Leipzig",
     "start_income": 1, "track_count": 11, "ability": "build_1_2"},
    {"id": "Königlich-Bayerische", "color": "#0000FF", "home": "München",
     "start_income": 3, "track_count": 16, "ability": "discount_1"},
    {"id": "Main-Weser-Bahn", "color": "#DAA520", "home": "Kassel",
     "start_income": 2, "track_count": 14, "ability": "double_best_income"},
    {"id": "Großherzoglich Badische", "color": "#CC0000", "home": "Mannheim",
     "start_income": 1, "track_count": 15, "ability": "free_rural"},
    {"id": "Köln-Mindener", "color": "#800080", "home": "Köln",
     "start_income": 1, "track_count": 12, "ability": "max_spend_5"},
    {"id": "Berlin-Hamburger", "color": "#006400", "home": "Hamburg",
     "start_income": 1, "track_count": 13, "ability": "connect_both"},
]

output = {
    "name": "prussian_rails",
    "grid_type": "hex_axial",
    "hex_size": 27,
    "grid_bounds": {"q_min": min_q - 2, "q_max": max_q + 2, "r_min": min_r - 2, "r_max": max_r + 2},
    "background_image": "/prussian_rails_board.png",
    "image_origin_x": ORIGIN_X,
    "image_origin_y": ORIGIN_Y,
    "image_width": IMG_W,
    "image_height": IMG_H,
    "terrain_costs": {
        "plains": 2, "hills": 3, "mountains": 4,
        "berlin_approach": 2, "urban": 2, "water": 999
    },
    "starting_money": {"3": 40, "4": 30, "5": 24},
    "berlin_approach_hexes": berlin_approaches,
    "auction_order": [c["id"] for c in companies],
    "companies": companies,
    "hexes": {}
}
for key in sorted(all_hexes.keys(), key=lambda k: (int(k.split(",")[1]), int(k.split(",")[0]))):
    output["hexes"][key] = all_hexes[key]

with open("app/engine/maps/prussian_rails_hex.json", "w") as f:
    json.dump(output, f, indent=2)

city_count = sum(1 for v in all_hexes.values() if "city" in v)
print(f"Hexes: {len(all_hexes)}")
print(f"Cities: {city_count}")
print(f"Berlin approaches: {len(berlin_approaches)}")
print(f"Axial bounds: q=[{min_q},{max_q}] r=[{min_r},{max_r}]")

# Print axial coords of key cities for verification
for name in ["Flensburg", "Hamburg", "Berlin", "Köln", "München", "Königsberg", "Breslau"]:
    q, r = cities_axial[name]
    px, py = axial_pixel(q, r)
    print(f"  {name}: axial=({q},{r}) pixel=({px},{py})")
