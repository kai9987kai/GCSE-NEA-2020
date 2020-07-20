from tkinter import *
from tkinter.messagebox import showerror, showinfo
from src.dice import roll, add_winner, update_leaderboard, save_leaderboard, get_leaderboard
from threading import Thread
from tkinter import ttk

TITLE = 'DICE GAME'
WINSIZE = (800, 600)
PLAYERS_NUMS = 2

class Dashboard:

    def __init__(self, master):
        self.master = master
        self.players = []
        self.games = 0
        self.dice = IntVar(value=0)

    def show(self):
        self.root = Toplevel(self.master)
        self.turn = self.players[0]
        self.turn_name = StringVar(value="Play "+list(self.turn.keys())[0])
        self.logs = StringVar()
        self.__config()

    def __config(self):
        self.root.wm_title = TITLE
        self.root.geometry(f"{WINSIZE[0]}x{WINSIZE[1]}")
        self.root.wm_resizable(0, 0)
        self.__score()
        self.__add_buttons()
        self.root.protocol("WM_DELETE_WINDOW",
                           lambda: self.master.destroy())
        try:
            self.root.iconbitmap('favicon.ico')
        except:
            pass

    def set_players(self, players : list):
        for player in players:
            self.players.append({player:IntVar(value=0)})

    def __score(self):
        i = 0
        Label(self.root, text="Score", font=("Arial", 30)).place(x=325, y=50)
        for player in self.players:
            key = list(player.keys())[0]
            Label(self.root, textvariable=self.players[i][key], font=("Arial", 25)).place(x=340+(i*50), y=100); i+=1
        Label(self.root, textvariable=self.dice, font=("Arial", 60),borderwidth=2, relief="solid", bg="White").place(x=350, y=200)
        Label(self.root, textvariable=self.turn_name, font=("Arial", 24), fg="green").place(x=500, y=550)
        Label(self.root, textvariable=self.logs, font=("Arial", 24), fg="green").place(x=50, y=400)

    def __add_buttons(self):
        self.btn = Button(self.root, text="Roll",font=("Arial", 25), relief="solid", command=self.roll)
        self.btn_show_leaderboard = Button(self.root, text="LeaderBoard", font=("Arial", 14), relief="solid", command=lambda : LeaderBoard(self.root))
        self.btn.place(x=330, y=400)
        self.btn_show_leaderboard.place(x=50, y=550)
    
    def roll(self):
        self.btn.config(state="disabled")
        name = list(self.turn.keys())[0]
        player = self.turn[name]
        Thread(target=roll, args=(self.dice, self.rolling, player, self.check_state,)).start()
        self.turn = self.players[1] if self.turn.keys() == self.players[0].keys() else self.players[0]

        self.games += 1
    
    def rolling(self, state=True):
        name = self.turn_name.get().split()[1]
        if state:
            self.logs.set(name + " rolling..")
        else:
            self.logs.set("")

    def check_state(self):
        self.btn.config(state="normal")
        self.turn_name.set("Play "+list(self.turn.keys())[0])
        if self.games == 5:
            player_one = list(self.players[0].keys())[0]
            player_two = list(self.players[1].keys())[0]
            if not self.players[0][player_one].get() == self.players[1][player_two].get():
                if self.players[0][player_one].get() > self.players[1][player_two].get():
                    showinfo('WINNER!', f'Well done, {player_one} you won with {self.players[0][player_one].get()} Points')
                    add_winner([player_one, self.players[0][player_one].get()])
                    leaderboard = update_leaderboard(get_leaderboard(), [player_one, self.players[0][player_one].get()])
                    save_leaderboard(leaderboard)

                else:
                    showinfo('WINNER!', f'Well done, {player_two} you won with {self.players[1][player_two].get()} Points')
                    add_winner([player_two, self.players[1][player_two].get()])
                    leaderboard = update_leaderboard(get_leaderboard(), [player_two, self.players[1][player_two].get()])
                    save_leaderboard(leaderboard)
                self.finish_game(player_one, player_two)

    def finish_game(self, player_one, player_two):
        self.dice.set(value=0)
        self.players[0][player_one].set(value=0)
        self.players[1][player_two].set(value=0)
        self.turn = self.players[0]
        self.turn_name.set("Play "+list(self.turn.keys())[0])
        self.games = 0

class LeaderBoard:
    WINSIZE = (200, 500)


    def __init__(self, master):
        self.root = Toplevel(master)
        self.__config()

    
    def __config(self):
        self.root.geometry(f'{self.WINSIZE[0]}x{self.WINSIZE[1]}')
        self.root.wm_resizable(0, 0)
        self.__add_listbox()
        self.__add_leaderboard()
        try:
            self.root.iconbitmap('favicon.ico')
        except:
            pass
        self.root.mainloop()

    def __add_listbox(self):
        self.lst_box = Listbox(self.root)
        self.lst_box.place(x=10, y=50, width=180, height=350)

    def __add_leaderboard(self):
        with open('Leaderboard.txt', 'r') as data:
            lines = data.readlines()
            for line in lines:
                self.lst_box.insert(END, f"{line.split(',')[0]} - {line.split(',')[1]}")
            data.close()

class App:

    WINSIZE = (400, 200)
    BUTTON_POS = (WINSIZE[0]/3,WINSIZE[1]/1.5)
    ENTRY_POS = (120, WINSIZE[1]/4)
    LABEL_POS = (120, 25)

    def __init__(self):
        self.root = Tk()
        self.dashboard = Dashboard(self.root)
        self.password = StringVar()
        self.username = StringVar()
        self.users = []
        self.user_turn = StringVar(value='Log in player 1')
        self.__config()
    
    def __config(self):
        self.root.wm_title(TITLE)
        self.root.geometry(f"{self.WINSIZE[0]}x{self.WINSIZE[1]}")
        self.root.wm_resizable(0, 0)
        self.__add_labels()
        self.__add_entrys()
        self.__add_buttons()
        try:
            self.root.iconbitmap('favicon.ico')
        except:
            pass



    def __add_labels(self):
        x, y = self.LABEL_POS
        Label(self.root, text="Username:").place(x=x, y=y)
        Label(self.root, text="Password:").place(x=x, y=y*3)
        Label(self.root, textvariable=self.user_turn).place(x=x/7, y=y*7)
    
    def __add_entrys(self):
        x, y = self.ENTRY_POS
        Entry(self.root, textvariable=self.username).place(x=x, y=y)
        Entry(self.root, textvariable=self.password, show="●").place(x=x, y=y*2)
    
    def __add_buttons(self):
        x, y = self.BUTTON_POS
        ttk.Button(self.root, text="Login", command=self.to_validate).place(x=x+10, y=y)

    def to_validate(self):
        response = self.validation(self.username.get(), self.password.get())
        if response is not None:
            self.users.append(response)
            if len(self.users) == PLAYERS_NUMS:
                showinfo("Success", f"Welcome, {response} you have been successfully logged in.")
                self.root.withdraw()
                self.dashboard.set_players(self.users)
                self.dashboard.show()

            else:
                self.clean_vars()
                showinfo("Success!", f"Welcome, {response} you have been successfully logged in.")
                showinfo("Info","Please, login Player2")

    def clean_vars(self):
        self.username.set('')
        self.password.set('')
        self.user_turn.set('Log in player 2')

    @staticmethod
    def validation(username, password):
        users = ["User"+str(user_index) for user_index in range(7)]
        if username in users:
            if password == password:
                return username
        ## return username # for debug
        showerror("Error", "Invalid username or password!")
