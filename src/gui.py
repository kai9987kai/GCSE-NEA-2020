"""Tkinter front end.

Rebuilt around three changes to the 2020 version:

* **No worker threads.**  The old ``roll`` ran in a ``Thread`` and called
  ``time.sleep`` while writing to Tk variables and popping up message boxes.
  Tkinter is not thread safe, so that could deadlock or crash the interpreter.
  The dice animation is now scheduled with ``widget.after``, on the main loop.
* **No nested ``mainloop``.**  The leaderboard window used to start a second
  event loop inside the first.  It is now an ordinary modal dialog.
* **Layout that survives resizing.**  Absolute ``place()`` co-ordinates are
  replaced with ``grid`` and ttk widgets.
"""

from __future__ import annotations

import random
import tkinter as tk
from tkinter import messagebox, ttk

from .auth import UserStore
from .engine import DiceGame, GameConfig, TurnEvent
from .leaderboard import Leaderboard
from .paths import PROJECT_ROOT

TITLE = "Dice Game"
PLAYERS_PER_GAME = 2

#: Cosmetic dice-tumble animation, in milliseconds.
FLICKER_FRAMES = 6
FLICKER_MS = 60
SETTLE_MS = 260

DIE_FONT = ("Helvetica", 44, "bold")
SCORE_FONT = ("Helvetica", 26, "bold")
HEADING_FONT = ("Helvetica", 18, "bold")


def _apply_icon(window: tk.Misc) -> None:
    """Best-effort window icon; ``.ico`` files only load on some platforms."""
    try:
        window.iconbitmap(str(PROJECT_ROOT / "favicon.ico"))
    except tk.TclError:
        pass


class LoginFrame(ttk.Frame):
    """Collects and verifies one set of credentials per player."""

    def __init__(self, master: DiceApp) -> None:
        super().__init__(master.root, padding=24)
        self.app = master
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.prompt = tk.StringVar(value="Log in player 1")
        self._build()

    def _build(self) -> None:
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text=TITLE, font=HEADING_FONT).grid(
            row=0, column=0, columnspan=2, pady=(0, 4)
        )
        ttk.Label(self, textvariable=self.prompt, foreground="#1a7f37").grid(
            row=1, column=0, columnspan=2, pady=(0, 16)
        )

        ttk.Label(self, text="Username").grid(row=2, column=0, sticky="w", pady=4)
        self.username_entry = ttk.Entry(self, textvariable=self.username)
        self.username_entry.grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(self, text="Password").grid(row=3, column=0, sticky="w", pady=4)
        self.password_entry = ttk.Entry(self, textvariable=self.password, show="●")
        self.password_entry.grid(row=3, column=1, sticky="ew", pady=4)

        buttons = ttk.Frame(self)
        buttons.grid(row=4, column=0, columnspan=2, pady=(18, 0), sticky="e")
        ttk.Button(buttons, text="Log in", command=self.submit).grid(row=0, column=0)

        self.hint = ttk.Label(self, text="", foreground="#b3261e", wraplength=320)
        self.hint.grid(row=5, column=0, columnspan=2, pady=(12, 0))

        for widget in (self.username_entry, self.password_entry):
            widget.bind("<Return>", lambda _event: self.submit())
        self.username_entry.focus_set()

    def submit(self) -> None:
        username = self.username.get().strip()
        password = self.password.get()

        if not username or not password:
            self._reject("Enter both a username and a password.")
            return
        if username in self.app.players:
            self._reject(f"{username} is already playing - log in as someone else.")
            return
        if not self.app.store.authenticate(username, password):
            self._reject("Invalid username or password.")
            return

        self.hint.configure(text="")
        self.app.add_player(username)
        self.username.set("")
        self.password.set("")
        remaining = PLAYERS_PER_GAME - len(self.app.players)
        if remaining:
            self.prompt.set(f"Welcome {username}. Log in player {len(self.app.players) + 1}")
            self.username_entry.focus_set()

    def _reject(self, message: str) -> None:
        self.hint.configure(text=message)
        self.password.set("")
        self.password_entry.focus_set()


class GameFrame(ttk.Frame):
    """The board: scores, the dice, a turn log and the controls."""

    def __init__(self, master: DiceApp, game: DiceGame) -> None:
        super().__init__(master.root, padding=20)
        self.app = master
        self.game = game
        self._rng = random.Random()
        self._after_id: str | None = None

        self.status = tk.StringVar(value=game.status_line())
        self.score_vars = {name: tk.StringVar(value="0") for name in game.players}
        self.die_vars = [tk.StringVar(value="-") for _ in range(3)]
        self._build()
        self._refresh()

    # -- layout --------------------------------------------------------
    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        ttk.Label(self, textvariable=self.status, font=HEADING_FONT).grid(
            row=0, column=0, pady=(0, 12)
        )

        scores = ttk.Frame(self)
        scores.grid(row=1, column=0, pady=(0, 16))
        self.name_labels = {}
        for column, name in enumerate(self.game.players):
            scores.columnconfigure(column, weight=1, minsize=150)
            label = ttk.Label(scores, text=name, font=("Helvetica", 12))
            label.grid(row=0, column=column, padx=16)
            ttk.Label(scores, textvariable=self.score_vars[name], font=SCORE_FONT).grid(
                row=1, column=column, padx=16
            )
            self.name_labels[name] = label

        dice = ttk.Frame(self)
        dice.grid(row=2, column=0, pady=(0, 16))
        self.die_labels = []
        for index, variable in enumerate(self.die_vars):
            label = ttk.Label(
                dice,
                textvariable=variable,
                font=DIE_FONT,
                width=2,
                anchor="center",
                relief="solid",
                borderwidth=2,
                padding=8,
            )
            label.grid(row=0, column=index, padx=8)
            self.die_labels.append(label)
        self.die_labels[2].grid_remove()  # only shown after a double

        log_box = ttk.LabelFrame(self, text="Turn log", padding=8)
        log_box.grid(row=3, column=0, sticky="nsew")
        log_box.columnconfigure(0, weight=1)
        log_box.rowconfigure(0, weight=1)
        self.log = tk.Listbox(log_box, height=7, activestyle="none")
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_box, orient="vertical", command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

        controls = ttk.Frame(self)
        controls.grid(row=4, column=0, pady=(16, 0), sticky="ew")
        controls.columnconfigure(1, weight=1)
        self.roll_button = ttk.Button(controls, text="Roll", command=self.roll)
        self.roll_button.grid(row=0, column=0, padx=(0, 8))
        ttk.Button(controls, text="Leaderboard", command=self.show_leaderboard).grid(
            row=0, column=2, padx=4
        )
        self.new_game_button = ttk.Button(controls, text="New game", command=self.new_game)
        self.new_game_button.grid(row=0, column=3, padx=4)

        self.app.root.bind("<Return>", self._roll_shortcut)
        self.app.root.bind("<space>", self._roll_shortcut)

    # -- play ----------------------------------------------------------
    def _roll_shortcut(self, _event: tk.Event) -> None:
        if str(self.roll_button["state"]) != "disabled":
            self.roll()

    def roll(self) -> None:
        if self.game.is_finished or self._after_id is not None:
            return
        self.roll_button.configure(state="disabled")
        event = self.game.take_turn()
        self._play_animation(event)

    def _play_animation(self, event: TurnEvent) -> None:
        """Reveal an already-decided turn one die at a time."""
        if event.is_tie_break:
            values = [event.tie_break_roll]
        else:
            assert event.result is not None
            values = list(event.result.dice)
            if event.result.bonus_die is not None:
                values.append(event.result.bonus_die)

        for index, label in enumerate(self.die_labels):
            if index < len(values):
                label.grid()
                self.die_vars[index].set("-")
            else:
                label.grid_remove()

        steps = []
        for slot, value in enumerate(values):
            for _ in range(FLICKER_FRAMES):
                steps.append((slot, self._rng.randint(1, 6), FLICKER_MS))
            steps.append((slot, value, SETTLE_MS))
        self._step(steps, 0, event)

    def _step(self, steps: list[tuple], index: int, event: TurnEvent) -> None:
        if index >= len(steps):
            self._after_id = None
            self._complete_turn(event)
            return
        slot, value, delay = steps[index]
        self.die_vars[slot].set(str(value))
        self._after_id = self.after(delay, lambda: self._step(steps, index + 1, event))

    def _complete_turn(self, event: TurnEvent) -> None:
        self.log.insert(tk.END, event.describe())
        self.log.see(tk.END)
        self._refresh()
        if self.game.is_finished:
            self._declare_winner()
        else:
            self.roll_button.configure(state="normal")

    def _refresh(self) -> None:
        self.status.set(self.game.status_line())
        for name, variable in self.score_vars.items():
            variable.set(str(self.game.scores[name]))
        current = self.game.current_player
        for name, label in self.name_labels.items():
            label.configure(
                font=("Helvetica", 12, "bold" if name == current else "normal"),
                foreground="#1a7f37" if name == current else "",
            )

    def _declare_winner(self) -> None:
        winner = self.game.winner
        assert winner is not None
        score = self.game.scores[winner]
        self.roll_button.configure(state="disabled")

        board = Leaderboard.load()
        improved = board.record(winner, score)
        if improved:
            board.save()
        rank = board.rank_of(winner)

        message = f"Well done {winner}, you won with {score} points."
        if improved:
            message += f"\n\nNew personal best - ranked #{rank} on the leaderboard."
        messagebox.showinfo("Winner!", message, parent=self)
        self.new_game_button.focus_set()

    def new_game(self) -> None:
        self._cancel_animation()
        self.game.reset()
        self.log.delete(0, tk.END)
        # A tie-break shows a single die, so restore the pair before a new match.
        for index, variable in enumerate(self.die_vars):
            variable.set("-")
            if index < 2:
                self.die_labels[index].grid()
            else:
                self.die_labels[index].grid_remove()
        self.roll_button.configure(state="normal")
        self._refresh()

    def show_leaderboard(self) -> None:
        LeaderboardDialog(self.app.root)

    # -- teardown ------------------------------------------------------
    def _cancel_animation(self) -> None:
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

    def destroy(self) -> None:
        self._cancel_animation()
        for sequence in ("<Return>", "<space>"):
            try:
                self.app.root.unbind(sequence)
            except tk.TclError:
                pass
        super().destroy()


class LeaderboardDialog(tk.Toplevel):
    """Modal high-score table. No nested ``mainloop``."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.title("Leaderboard")
        self.geometry("380x420")
        self.transient(master)
        self.resizable(False, True)
        _apply_icon(self)

        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        columns = ("rank", "player", "score", "date")
        tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="none")
        for column, heading, width in (
            ("rank", "#", 40),
            ("player", "Player", 140),
            ("score", "Score", 70),
            ("date", "Achieved", 100),
        ):
            tree.heading(column, text=heading)
            tree.column(column, width=width, anchor="center" if column != "player" else "w")
        tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)

        entries = Leaderboard.load().top()
        if entries:
            for rank, entry in enumerate(entries, start=1):
                tree.insert(
                    "", tk.END, values=(rank, entry.name, entry.score, entry.achieved or "-")
                )
        else:
            ttk.Label(container, text="No games have been won yet.").grid(row=1, column=0, pady=12)

        ttk.Button(container, text="Close", command=self.destroy).grid(
            row=2, column=0, columnspan=2, pady=(12, 0), sticky="ew"
        )

        self.bind("<Escape>", lambda _event: self.destroy())
        self.grab_set()


class DiceApp:
    """Owns the window and swaps between the login and game screens."""

    def __init__(
        self,
        store: UserStore | None = None,
        config: GameConfig | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.root = tk.Tk()
        self.store = store if store is not None else UserStore.load()
        self.config = config or GameConfig()
        self.rng = rng or random.Random()
        self.players: list[str] = []
        self.frame: ttk.Frame | None = None

        self.root.title(TITLE)
        self.root.minsize(520, 560)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        _apply_icon(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        self.show(LoginFrame(self))

    def show(self, frame: ttk.Frame) -> None:
        if self.frame is not None:
            self.frame.destroy()
        self.frame = frame
        frame.grid(row=0, column=0, sticky="nsew")

    def add_player(self, username: str) -> None:
        self.players.append(username)
        if len(self.players) == PLAYERS_PER_GAME:
            game = DiceGame(self.players, config=self.config, rng=self.rng)
            self.show(GameFrame(self, game))

    def quit(self) -> None:
        if self.frame is not None:
            self.frame.destroy()
            self.frame = None
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


#: Backwards-compatible alias for the 2020 entry point.
App = DiceApp


def main(config: GameConfig | None = None) -> int:
    DiceApp(config=config).run()
    return 0
