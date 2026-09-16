# Dice Game

A two-player dice game, originally written as a GCSE NEA in 2020 and rebuilt
here with a tested rules engine, a rewritten Tkinter interface and a terminal
version for machines without a display.

```bash
python main.py            # graphical version
python main.py --cli      # terminal version
python main.py --help     # every option
```

No dependencies beyond the standard library. Python 3.9 or newer; the
graphical version also needs `tkinter` (`sudo apt install python3-tk` on
Debian and Ubuntu, bundled everywhere else).

Demo accounts `User1`–`User5` are created on first run with the password
`password`. They exist so the login screen has something to accept — change
them before using this anywhere that matters.

## The rules

* Two players take **five turns each**.
* A turn is two dice. Their total is added to your score, then:
  * an **even** total earns **+10**;
  * an **odd** total costs **−5**.
* Roll a **double** and you get one extra die, added to the same turn.
* Scores stop at zero (pass `--allow-negative` to let them go below).
* Highest score after five rounds wins. **Level scores go to sudden death**:
  both players roll a single die, repeating until someone rolls higher.
* Winners are recorded on the leaderboard, which keeps each player's best.

## Options

| Option | Effect |
| --- | --- |
| `--cli` | Play in the terminal instead of opening a window |
| `--rounds N` | Turns per player (default 5) |
| `--allow-negative` | Let scores fall below zero |
| `--seed N` | Seed the dice for a reproducible game |
| `--players ONE TWO` | Skip the login and use these names (`--cli` only) |
| `--auto` | Play every turn automatically, for demos (`--cli` only) |

## Layout

```
main.py              Command line entry point
src/rules.py         Dice and scoring, as pure functions
src/engine.py        Turn order, rounds, tie-breaks, the winner
src/auth.py          Accounts, salted PBKDF2-SHA256 password hashes
src/leaderboard.py   High scores, one best row per player
src/paths.py         Where saved data lives
src/gui.py           Tkinter interface
src/cli.py           Terminal interface
tests/               79 tests, standard library only
```

The rules and the engine never import `tkinter`, so the game can be tested,
scripted and replayed without a display.

Saved data lives beside the code by default: `Leaderboard.txt` and
`users.json` (untracked, created on first run). Set `DICE_GAME_DATA_DIR` to
put them somewhere else.

## Development

```bash
python -m unittest discover -s tests -t . -v    # tests
ruff check . && ruff format --check .            # lint and formatting
python main.py --cli --players Ada Grace --auto --seed 1   # smoke test
```

CI runs the suite on Python 3.9, 3.11 and 3.13.

## What changed in the rebuild

The 2020 code is in the history if you want to compare. These were the faults
worth fixing, each now covered by a regression test:

| Fault | Then | Now |
| --- | --- | --- |
| Login accepted anything | `if password == password:` is always true, so any password worked for a known username | Salted PBKDF2-SHA256 hashes, compared in constant time |
| One player got more turns | The game ended after five *total* rolls, so player one rolled three times and player two twice | Five rounds, one turn each per round |
| A draw was unplayable | A level score produced no winner, and the end-of-game check never fired again | Sudden-death roll-off until somebody wins |
| Personal bests never updated | `update_leaderboard` compared a score string to an integer, so the branch never ran — and on the one input where it did, `int()` was called on a player's name and raised `ValueError` | One row per player, keeping their best |
| Duplicate leaderboard rows | Every win was appended as a new line | Rows are merged on save |
| `User1,9` outranked `User1,28` | Rows were sorted as text | Sorted numerically |
| Dice rolled on a worker thread | `roll()` ran in a `Thread`, called `time.sleep`, then wrote to Tk variables and opened dialogs — Tkinter is not thread safe | Animated with `after()` on the main loop |
| Leaderboard window froze the game | It started a second `mainloop()` inside the first | An ordinary modal dialog |
| Leaderboard moved between runs | Opened by relative path, so it followed the working directory | Resolved against the project root |
| Both seats could be one account | Nothing stopped the same user logging in twice | Duplicate players are rejected |
| Fixed-size window | Every widget was placed at hard-coded pixel co-ordinates | `grid` layout with ttk widgets |

The old `src/dice.py` is gone; `login()` became `src/auth.py`, `roll()` became
`src/rules.py`, and the leaderboard functions became `src/leaderboard.py`.

## Credits

Original 2020 NEA by [@kai9987kai](https://github.com/kai9987kai), with the
first Tkinter interface by **SCR44GR**. Licensed under the terms in
[LICENSE](LICENSE).
