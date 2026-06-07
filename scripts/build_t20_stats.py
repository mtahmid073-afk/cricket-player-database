import json
from pathlib import Path
from collections import defaultdict

RAW_DIR = Path("data/raw/t20s_json")
OUT_FILE = Path("data/processed/t20_player_stats.json")

players = defaultdict(lambda: {
    "batting": {
        "runs": 0,
        "balls": 0,
        "outs": 0,
        "fours": 0,
        "sixes": 0,
        "dots": 0
    },
    "bowling": {
        "balls": 0,
        "runsConceded": 0,
        "wickets": 0,
        "dots": 0,
        "foursConceded": 0,
        "sixesConceded": 0,
        "wides": 0,
        "noBalls": 0
    },
    "fielding": {
        "catches": 0,
        "runOuts": 0,
        "stumpings": 0
    }
})

def is_legal_ball(extras):
    return not ("wides" in extras)

def process_match(path):
    with open(path, "r", encoding="utf-8") as f:
        match = json.load(f)

    for innings in match.get("innings", []):
        overs = innings.get("overs", [])

        for over in overs:
            for delivery in over.get("deliveries", []):
                batter = delivery["batter"]
                bowler = delivery["bowler"]
                runs = delivery["runs"]
                extras = delivery.get("extras", {})

                batter_runs = runs.get("batter", 0)
                total_runs = runs.get("total", 0)

                # Batting
                players[batter]["batting"]["runs"] += batter_runs

                if is_legal_ball(extras):
                    players[batter]["batting"]["balls"] += 1

                    if batter_runs == 0:
                        players[batter]["batting"]["dots"] += 1
                    elif batter_runs == 4:
                        players[batter]["batting"]["fours"] += 1
                    elif batter_runs == 6:
                        players[batter]["batting"]["sixes"] += 1

                # Bowling
                if is_legal_ball(extras):
                    players[bowler]["bowling"]["balls"] += 1

                # Bowler conceded runs except byes and leg byes
                bowler_runs = total_runs
                bowler_runs -= extras.get("byes", 0)
                bowler_runs -= extras.get("legbyes", 0)

                players[bowler]["bowling"]["runsConceded"] += bowler_runs

                if batter_runs == 0:
                    players[bowler]["bowling"]["dots"] += 1
                elif batter_runs == 4:
                    players[bowler]["bowling"]["foursConceded"] += 1
                elif batter_runs == 6:
                    players[bowler]["bowling"]["sixesConceded"] += 1

                players[bowler]["bowling"]["wides"] += extras.get("wides", 0)
                players[bowler]["bowling"]["noBalls"] += extras.get("noballs", 0)

                # Wickets
                for wicket in delivery.get("wickets", []):
                    kind = wicket.get("kind")
                    player_out = wicket.get("player_out")

                    if kind not in ["run out", "retired hurt", "retired out", "obstructing the field"]:
                        players[player_out]["batting"]["outs"] += 1
                        players[bowler]["bowling"]["wickets"] += 1

                    for fielder in wicket.get("fielders", []):
                        name = fielder.get("name")
                        if not name:
                            continue

                        if kind == "caught":
                            players[name]["fielding"]["catches"] += 1
                        elif kind == "run out":
                            players[name]["fielding"]["runOuts"] += 1
                        elif kind == "stumped":
                            players[name]["fielding"]["stumpings"] += 1

def add_rates(record):
    bat = record["batting"]
    bowl = record["bowling"]

    bat["average"] = round(bat["runs"] / bat["outs"], 2) if bat["outs"] else None
    bat["strikeRate"] = round((bat["runs"] / bat["balls"]) * 100, 2) if bat["balls"] else None
    bat["dotBallRate"] = round((bat["dots"] / bat["balls"]) * 100, 2) if bat["balls"] else None
    bat["boundaryRate"] = round(((bat["fours"] + bat["sixes"]) / bat["balls"]) * 100, 2) if bat["balls"] else None

    bowl["overs"] = f"{bowl['balls'] // 6}.{bowl['balls'] % 6}"
    bowl["economy"] = round((bowl["runsConceded"] / bowl["balls"]) * 6, 2) if bowl["balls"] else None
    bowl["strikeRate"] = round(bowl["balls"] / bowl["wickets"], 2) if bowl["wickets"] else None
    bowl["dotBallRate"] = round((bowl["dots"] / bowl["balls"]) * 100, 2) if bowl["balls"] else None

def main():
    files = list(RAW_DIR.glob("*.json"))
    print(f"Found {len(files)} match files")

    for path in files:
        process_match(path)

    output = {}
    for name, record in players.items():
        add_rates(record)
        output[name] = record

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Saved: {OUT_FILE}")
    print(f"Players found: {len(output)}")

if __name__ == "__main__":
    main()