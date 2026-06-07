import json
from pathlib import Path
from collections import defaultdict

RAW_DIR = Path("data/raw/t20s_json")
OUT_FILE = Path("data/processed/t20_player_stats.json")


def new_player_record():
    return {
        "_matches": set(),
        "matches": 0,
        "batting": {
            "innings": 0,
            "runs": 0,
            "balls": 0,
            "outs": 0,
            "fours": 0,
            "sixes": 0,
            "dots": 0,
        },
        "bowling": {
            "innings": 0,
            "balls": 0,
            "runsConceded": 0,
            "wickets": 0,
            "dots": 0,
            "foursConceded": 0,
            "sixesConceded": 0,
            "wides": 0,
            "noBalls": 0,
        },
        "fielding": {
            "catches": 0,
            "runOuts": 0,
            "stumpings": 0,
        },
    }


players = defaultdict(new_player_record)


def touch_player(name, match_id):
    if name:
        players[name]["_matches"].add(match_id)


def is_legal_ball(extras):
    return "wides" not in extras


def is_bowler_wicket(kind):
    return kind not in {
        "run out",
        "retired hurt",
        "retired out",
        "obstructing the field",
    }


def is_batter_out(kind):
    return kind not in {"retired hurt", "retired not out"}


def process_match(path):
    match_id = path.stem

    with open(path, "r", encoding="utf-8") as f:
        match = json.load(f)

    for innings in match.get("innings", []):
        batters_in_innings = set()
        bowlers_in_innings = set()

        for over in innings.get("overs", []):
            for delivery in over.get("deliveries", []):
                batter = delivery.get("batter")
                non_striker = delivery.get("non_striker")
                bowler = delivery.get("bowler")
                runs = delivery.get("runs", {})
                extras = delivery.get("extras", {})

                batter_runs = runs.get("batter", 0)
                total_runs = runs.get("total", 0)

                touch_player(batter, match_id)
                touch_player(non_striker, match_id)
                touch_player(bowler, match_id)

                if batter:
                    batters_in_innings.add(batter)
                if bowler:
                    bowlers_in_innings.add(bowler)

                players[batter]["batting"]["runs"] += batter_runs

                if is_legal_ball(extras):
                    players[batter]["batting"]["balls"] += 1

                    if batter_runs == 0:
                        players[batter]["batting"]["dots"] += 1
                    elif batter_runs == 4:
                        players[batter]["batting"]["fours"] += 1
                    elif batter_runs == 6:
                        players[batter]["batting"]["sixes"] += 1

                if is_legal_ball(extras):
                    players[bowler]["bowling"]["balls"] += 1

                bowler_runs = total_runs
                bowler_runs -= extras.get("byes", 0)
                bowler_runs -= extras.get("legbyes", 0)
                players[bowler]["bowling"]["runsConceded"] += bowler_runs

                if is_legal_ball(extras):
                    if batter_runs == 0:
                        players[bowler]["bowling"]["dots"] += 1
                    elif batter_runs == 4:
                        players[bowler]["bowling"]["foursConceded"] += 1
                    elif batter_runs == 6:
                        players[bowler]["bowling"]["sixesConceded"] += 1

                players[bowler]["bowling"]["wides"] += extras.get("wides", 0)
                players[bowler]["bowling"]["noBalls"] += extras.get("noballs", 0)

                for wicket in delivery.get("wickets", []):
                    kind = wicket.get("kind")
                    player_out = wicket.get("player_out")

                    touch_player(player_out, match_id)

                    if player_out and is_batter_out(kind):
                        players[player_out]["batting"]["outs"] += 1

                    if bowler and player_out and is_bowler_wicket(kind):
                        players[bowler]["bowling"]["wickets"] += 1

                    for fielder in wicket.get("fielders", []):
                        name = fielder.get("name")
                        if not name:
                            continue

                        touch_player(name, match_id)

                        if kind in {"caught", "caught and bowled"}:
                            players[name]["fielding"]["catches"] += 1
                        elif kind == "run out":
                            players[name]["fielding"]["runOuts"] += 1
                        elif kind == "stumped":
                            players[name]["fielding"]["stumpings"] += 1

        for name in batters_in_innings:
            players[name]["batting"]["innings"] += 1

        for name in bowlers_in_innings:
            players[name]["bowling"]["innings"] += 1


def add_rates(record):
    bat = record["batting"]
    bowl = record["bowling"]

    bat_balls = bat["balls"]
    bat_outs = bat["outs"]
    bowl_balls = bowl["balls"]
    bowl_wickets = bowl["wickets"]

    bat["average"] = round(bat["runs"] / bat_outs, 2) if bat_outs else None
    bat["strikeRate"] = round((bat["runs"] / bat_balls) * 100, 2) if bat_balls else None
    bat["dotBallRate"] = round((bat["dots"] / bat_balls) * 100, 2) if bat_balls else None
    bat["boundaryRate"] = round(((bat["fours"] + bat["sixes"]) / bat_balls) * 100, 2) if bat_balls else None
    bat["fourRate"] = round((bat["fours"] / bat_balls) * 100, 2) if bat_balls else None
    bat["sixRate"] = round((bat["sixes"] / bat_balls) * 100, 2) if bat_balls else None
    bat["ballsPerDismissal"] = round(bat_balls / bat_outs, 2) if bat_outs else None

    bowl["overs"] = f"{bowl_balls // 6}.{bowl_balls % 6}"
    bowl["economy"] = round((bowl["runsConceded"] / bowl_balls) * 6, 2) if bowl_balls else None
    bowl["strikeRate"] = round(bowl_balls / bowl_wickets, 2) if bowl_wickets else None
    bowl["average"] = round(bowl["runsConceded"] / bowl_wickets, 2) if bowl_wickets else None
    bowl["dotBallRate"] = round((bowl["dots"] / bowl_balls) * 100, 2) if bowl_balls else None
    bowl["boundaryConcededRate"] = round(((bowl["foursConceded"] + bowl["sixesConceded"]) / bowl_balls) * 100, 2) if bowl_balls else None
    bowl["extrasRate"] = round(((bowl["wides"] + bowl["noBalls"]) / bowl_balls) * 100, 2) if bowl_balls else None
    bowl["wicketsPerMatch"] = round(bowl_wickets / record["matches"], 2) if record["matches"] else None
    bowl["wicketsPerBowlingInnings"] = round(bowl_wickets / bowl["innings"], 2) if bowl["innings"] else None


def main():
    files = sorted(RAW_DIR.glob("*.json"))
    print(f"Found {len(files)} match files")

    for path in files:
        process_match(path)

    output = {}
    for name, record in players.items():
        record["matches"] = len(record["_matches"])
        del record["_matches"]
        add_rates(record)
        output[name] = record

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Saved: {OUT_FILE}")
    print(f"Players found: {len(output)}")


if __name__ == "__main__":
    main()