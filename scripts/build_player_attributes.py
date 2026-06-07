import json
from pathlib import Path

IN_FILE = Path("data/processed/t20_player_stats.json")
OUT_FILE = Path("data/processed/t20_player_attributes.json")


def clamp_1_20(value):
    if value is None:
        return None
    return max(1, min(20, round(value)))


def avg_scores(*scores):
    clean = [s for s in scores if s is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean))


def apply_confidence(raw_score, default_score, opportunities, target_opportunities):
    if raw_score is None:
        return default_score
    confidence = min(1, opportunities / target_opportunities) if target_opportunities else 1
    return clamp_1_20(default_score * (1 - confidence) + raw_score * confidence)


# -------------------------
# Batting fixed range scores
# Shifted up +2 and capped at 20
# -------------------------

def score_batting_sr(sr):
    if sr is None: return None
    if sr < 70: return 4
    if sr < 80: return 6
    if sr < 90: return 7
    if sr < 100: return 9
    if sr < 110: return 10
    if sr < 120: return 12
    if sr < 140: return 14
    if sr < 150: return 16
    if sr < 160: return 18
    return 20


def score_batting_average(avg):
    if avg is None: return None
    if avg < 8: return 4
    if avg < 12: return 6
    if avg < 16: return 8
    if avg < 20: return 10
    if avg < 25: return 12
    if avg < 30: return 14
    if avg < 35: return 16
    if avg < 40: return 18
    return 20


def score_boundary_rate(rate):
    if rate is None: return None
    if rate < 4: return 5
    if rate < 6: return 8
    if rate < 8: return 10
    if rate < 10: return 12
    if rate < 12: return 14
    if rate < 14: return 16
    if rate < 16: return 18
    return 20


def score_six_rate(rate):
    if rate is None: return None
    if rate == 0: return 4
    if rate <= 1: return 7
    if rate <= 2: return 10
    if rate <= 3: return 12
    if rate <= 4: return 14
    if rate <= 5: return 16
    if rate <= 6.5: return 18
    return 20


def score_batting_dot_rate(rate):
    # Lower is better.
    if rate is None: return None
    if rate >= 60: return 5
    if rate >= 55: return 7
    if rate >= 50: return 9
    if rate >= 45: return 11
    if rate >= 40: return 13
    if rate >= 35: return 15
    if rate >= 30: return 17
    if rate >= 25: return 19
    return 20


def score_balls_per_dismissal(bpd):
    if bpd is None: return None
    if bpd < 5: return 4
    if bpd <= 8: return 6
    if bpd <= 12: return 8
    if bpd <= 16: return 10
    if bpd <= 21: return 12
    if bpd <= 27: return 14
    if bpd <= 34: return 16
    if bpd <= 44: return 18
    return 20


# -------------------------
# Bowling fixed range scores
# Shifted up +2 and capped at 20
# -------------------------

def score_bowling_economy(econ):
    # Lower is better.
    if econ is None: return None
    if econ >= 12: return 4
    if econ >= 11: return 6
    if econ >= 10: return 8
    if econ >= 9: return 10
    if econ >= 8: return 12
    if econ >= 7: return 14
    if econ >= 6: return 16
    if econ >= 5: return 18
    return 20


def score_bowling_sr(sr, balls_bowled=0):
    # Lower is better. If a player bowled enough balls but took no wickets, give low score.
    if sr is None:
        return 4 if balls_bowled >= 24 else None
    if sr >= 40: return 4
    if sr >= 34: return 6
    if sr >= 30: return 8
    if sr >= 26: return 10
    if sr >= 22: return 12
    if sr >= 18: return 14
    if sr >= 15: return 16
    if sr >= 12: return 18
    return 20


def score_bowling_average(avg, balls_bowled=0):
    # Lower is better. If a player bowled enough balls but took no wickets, give low score.
    if avg is None:
        return 4 if balls_bowled >= 24 else None
    if avg >= 40: return 4
    if avg >= 35: return 6
    if avg >= 30: return 8
    if avg >= 26: return 10
    if avg >= 22: return 12
    if avg >= 18: return 14
    if avg >= 15: return 16
    if avg >= 12: return 18
    return 20


def score_bowling_dot_rate(rate):
    # Higher is better.
    if rate is None: return None
    if rate < 25: return 4
    if rate < 30: return 6
    if rate < 35: return 8
    if rate < 40: return 10
    if rate < 45: return 12
    if rate < 50: return 14
    if rate < 55: return 16
    if rate < 60: return 18
    return 20


def score_boundary_conceded_rate(rate):
    # Lower is better.
    if rate is None: return None
    if rate >= 18: return 4
    if rate >= 16: return 6
    if rate >= 14: return 8
    if rate >= 12: return 10
    if rate >= 10: return 12
    if rate >= 8: return 14
    if rate >= 6: return 16
    if rate >= 4: return 18
    return 20


def score_extras_rate(rate):
    # Lower is better.
    if rate is None: return None
    if rate >= 10: return 4
    if rate >= 8: return 6
    if rate >= 6: return 8
    if rate >= 5: return 10
    if rate >= 4: return 12
    if rate >= 3: return 14
    if rate >= 2: return 16
    if rate >= 1: return 18
    return 20


def score_wickets_per_match(wpm):
    if wpm is None: return None
    if wpm < 0.25: return 4
    if wpm < 0.50: return 6
    if wpm < 0.75: return 8
    if wpm < 1.00: return 10
    if wpm < 1.25: return 12
    if wpm < 1.50: return 14
    if wpm < 1.75: return 16
    if wpm < 2.00: return 18
    return 20


def build_attributes_for_player(rec):
    bat = rec["batting"]
    bowl = rec["bowling"]
    field = rec["fielding"]

    bat_balls = bat.get("balls", 0)
    bowl_balls = bowl.get("balls", 0)

    # Batting metric scores
    avg_score = score_batting_average(bat.get("average"))
    sr_score = score_batting_sr(bat.get("strikeRate"))
    boundary_score = score_boundary_rate(bat.get("boundaryRate"))
    six_score = score_six_rate(bat.get("sixRate"))
    dot_score = score_batting_dot_rate(bat.get("dotBallRate"))
    bpd_score = score_balls_per_dismissal(bat.get("ballsPerDismissal"))

    # Batting raw attributes
    batting_overall_raw = avg_scores(avg_score, sr_score, bpd_score)
    technique_raw = avg_scores(avg_score, bpd_score, dot_score)
    timing_raw = avg_scores(sr_score, boundary_score, dot_score, avg_score)
    placement_raw = avg_scores(dot_score, boundary_score, avg_score)
    range360_raw = avg_scores(boundary_score, six_score, sr_score)
    defensive_raw = avg_scores(bpd_score, avg_score)
    neutral_raw = avg_scores(dot_score, avg_score, sr_score)
    attacking_raw = avg_scores(boundary_score, six_score, sr_score)
    creativity_raw = avg_scores(range360_raw, six_score, boundary_score)
    aggression_raw = avg_scores(sr_score, boundary_score, six_score)
    concentration_raw = avg_scores(bpd_score, avg_score)
    judgement_raw = avg_scores(bpd_score, avg_score, dot_score)

    # Sample-size protection. Full confidence at 500 balls faced.
    batting_overall = apply_confidence(batting_overall_raw, 8, bat_balls, 500)
    technique = apply_confidence(technique_raw, 8, bat_balls, 500)
    timing = apply_confidence(timing_raw, 8, bat_balls, 500)
    placement = apply_confidence(placement_raw, 8, bat_balls, 500)
    range360 = apply_confidence(range360_raw, 8, bat_balls, 500)
    defensive = apply_confidence(defensive_raw, 8, bat_balls, 500)
    neutral = apply_confidence(neutral_raw, 8, bat_balls, 500)
    attacking = apply_confidence(attacking_raw, 8, bat_balls, 500)
    creativity = apply_confidence(creativity_raw, 8, bat_balls, 500)
    aggression = apply_confidence(aggression_raw, 8, bat_balls, 500)
    concentration = apply_confidence(concentration_raw, 8, bat_balls, 500)
    judgement = apply_confidence(judgement_raw, 8, bat_balls, 500)

    # Bowling metric scores
    econ_score = score_bowling_economy(bowl.get("economy"))
    bowl_sr_score = score_bowling_sr(bowl.get("strikeRate"), bowl_balls)
    bowl_avg_score = score_bowling_average(bowl.get("average"), bowl_balls)
    bowl_dot_score = score_bowling_dot_rate(bowl.get("dotBallRate"))
    boundary_control_score = score_boundary_conceded_rate(bowl.get("boundaryConcededRate"))
    extras_control_score = score_extras_rate(bowl.get("extrasRate"))
    wickets_score = score_wickets_per_match(bowl.get("wicketsPerBowlingInnings") or bowl.get("wicketsPerMatch"))

    # If player barely bowled, treat bowling as unavailable, not secretly average.
    if bowl_balls < 24:
        bowling_attrs = {
            "accuracy": None,
            "bowlingSpeed": None,
            "swing": None,
            "turn": None,
            "flight": None,
            "variations": None,
            "intelligence": None,
            "defensiveBowling": None,
            "neutralBowling": None,
            "attackingBowling": None,
        }
        bowling_overall = None
    else:
        bowling_overall_raw = avg_scores(econ_score, bowl_avg_score, bowl_sr_score, wickets_score)
        accuracy_raw = avg_scores(econ_score, bowl_dot_score, extras_control_score, boundary_control_score)
        defensive_bowling_raw = avg_scores(econ_score, bowl_dot_score, boundary_control_score)
        neutral_bowling_raw = avg_scores(econ_score, bowl_sr_score, bowl_dot_score)
        attacking_bowling_raw = avg_scores(bowl_sr_score, bowl_avg_score, wickets_score)
        variations_raw = avg_scores(boundary_control_score, econ_score, wickets_score)
        intelligence_raw = avg_scores(econ_score, extras_control_score, bowl_dot_score)

        # Full confidence at 600 balls bowled.
        bowling_overall = apply_confidence(bowling_overall_raw, 8, bowl_balls, 600)
        bowling_attrs = {
            "accuracy": apply_confidence(accuracy_raw, 8, bowl_balls, 600),
            "bowlingSpeed": None,
            "swing": None,
            "turn": None,
            "flight": None,
            "variations": apply_confidence(variations_raw, 8, bowl_balls, 600),
            "intelligence": apply_confidence(intelligence_raw, 8, bowl_balls, 600),
            "defensiveBowling": apply_confidence(defensive_bowling_raw, 8, bowl_balls, 600),
            "neutralBowling": apply_confidence(neutral_bowling_raw, 8, bowl_balls, 600),
            "attackingBowling": apply_confidence(attacking_bowling_raw, 8, bowl_balls, 600),
        }

    # Fielding/physical simple estimates for now.
    catching = clamp_1_20(8 + min(8, field.get("catches", 0) // 5))
    reflexes = clamp_1_20(8 + min(7, (field.get("catches", 0) + field.get("runOuts", 0) + field.get("stumpings", 0)) // 6))
    ground_fielding = clamp_1_20(8 + min(7, field.get("runOuts", 0) // 3))
    strength = clamp_1_20(avg_scores(six_score, boundary_score))

    return {
        "sourceStats": rec,
        "attributeScoreInputs": {
            "batting": {
                "averageScore": avg_score,
                "strikeRateScore": sr_score,
                "boundaryRateScore": boundary_score,
                "sixRateScore": six_score,
                "dotBallRateScore": dot_score,
                "ballsPerDismissalScore": bpd_score,
            },
            "bowling": {
                "economyScore": econ_score,
                "bowlingStrikeRateScore": bowl_sr_score,
                "bowlingAverageScore": bowl_avg_score,
                "bowlingDotBallRateScore": bowl_dot_score,
                "boundaryControlScore": boundary_control_score,
                "extrasControlScore": extras_control_score,
                "wicketsScore": wickets_score,
            },
        },
        "attributes": {
            "batting": {
                "technique": technique,
                "timing": timing,
                "footwork": None,
                "placement": placement,
                "range360": range360,
                "defensiveShots": defensive,
                "neutralShots": neutral,
                "attackingShots": attacking,
                "vsPace": None,
                "vsSpin": None,
                "creativity": creativity,
            },
            "bowling": bowling_attrs,
            "fielding": {
                "catching": catching,
                "reflexes": reflexes,
                "groundFielding": ground_fielding,
                "throwPower": clamp_1_20(avg_scores(strength, ground_fielding)),
                "throwAccuracy": clamp_1_20(avg_scores(ground_fielding, reflexes)),
                "keeping": clamp_1_20(8 + min(10, field.get("stumpings", 0))),
                "collecting": clamp_1_20(avg_scores(8 + min(10, field.get("stumpings", 0)), reflexes)),
                "stumping": clamp_1_20(8 + min(10, field.get("stumpings", 0) * 2)),
            },
            "physical": {
                "strength": strength,
                "speed": 10,
                "agility": 10,
                "maxFitness": 10,
                "endurance": apply_confidence(10, 8, bat_balls + bowl_balls, 900),
                "stamina": apply_confidence(10, 8, bat_balls + bowl_balls, 900),
            },
            "mental": {
                "concentration": concentration,
                "temperament": concentration,
                "aggression": aggression,
                "judgement": judgement,
                "leadership": None,
            },
            "overall": {
                "batting_overall": batting_overall,
                "bowling_overall": bowling_overall,
                "fielding_overall": clamp_1_20(avg_scores(catching, ground_fielding, reflexes)),
            },
        },
    }


def main():
    with open(IN_FILE, "r", encoding="utf-8") as f:
        stats = json.load(f)

    output = {name: build_attributes_for_player(rec) for name, rec in stats.items()}

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Saved: {OUT_FILE}")
    print(f"Players converted: {len(output)}")


if __name__ == "__main__":
    main()
