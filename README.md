# The Keeper Index

Composite goalkeeper performance ratings for NCAA Division I field hockey.

Site: https://jmckinley.github.io/fh-goalkeeper-ratings/

## What it is

A four-factor rating of every qualifying D1 goalkeeper, built only from published NCAA statistics and a full-season results file, designed so that a keeper on a losing team is measured on the same footing as a keeper on a champion.

Factors, equal weight, rank-sum:

1. Save percentage
2. Shots on goal faced per game
3. Goals saved above average per game (expected goals on shots faced at the league-average save rate, minus actual goals against)
4. Strength of schedule (NCAA RPI formula, from all D1 results)

Candidate factors were tested by measuring how closely the resulting rating tracks the NCAA RPI team ranking. Goals against per game was rejected on that test (rank correlation 0.79 with RPI). The four-factor rating's correlation is 0.25.

## Repository layout

- `index.html`, `rankings.html`, `methodology.html`, `lessons.html`, `data.html`, `about.html`, `style.css`: the static site, served by GitHub Pages from the repository root
- `data/ratings_2026.csv`, `data/ratings_2026.json`: all 80 keepers with inputs, derived values, factor ranks, and every rating variant
- `data/team_sos_2026.csv`: strength of schedule for all 86 D1 teams
- `data/results_2026.csv`: every D1 result, Aug. 28 to Nov. 3, 2026
- `scripts/build_ratings.py`: fetches the NCAA pages and the scoreboard and rebuilds the data files

## Reproducing

```
cd scripts
python3 build_ratings.py --fetch
```

Requires Python 3.9+ and curl. No other dependencies.

## Disclosure

The author's daughter is a D1 goalkeeper and appears in the rankings. The method was fixed before any rankings were produced, every variant built is published, and the factor-selection test is external to any individual keeper. See the About page.

## Version

1.0, November 2026. Regular season through Nov. 3.
