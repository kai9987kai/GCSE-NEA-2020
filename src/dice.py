import random
import time


def login():
    while True:
        username = input('What is your username? ')
        password = input('What is your password? ')
        if username not in ('User1', 'User2', 'User3', 'User4', 'User5'):
            print('Incorrect username, try again')
            continue

        if password != 'password':
            print('Incorrect password, try again')
            continue

        print(f'Welcome, {username} you have been successfully logged in.')
        return username


def roll(label, rolling, player_score, check_state):
    
    rolling()
    die1 = random.randint(1, 6)
    label.set(die1)
    time.sleep(2)
    rolling(state=False)
    time.sleep(0.5)
    die2 = random.randint(1, 6)
    rolling()
    label.set(die2)
    change = 10 if (die1 + die2) % 2 == 0 else -5
    points = die1 + die2 + change
    time.sleep(1)
    rolling(state=False)
    if die1 == die2:
        rolling()
        time.sleep(2)
        die2 = random.randint(1, 6)
        label.set(die2)
        points += die2
    rolling(state=False)
    player_score.set(player_score.get()+points)
    check_state()

def add_winner(winner):
    with open('Leaderboard.txt', '+a') as f:
        f.write(f'{winner[0]},{winner[1]}\n')
        f.close()


def get_leaderboard():
    try:
        with open('Leaderboard.txt', '+r') as f:
            return [line.replace('\n','') for line in f.readlines()]
    except FileNotFoundError:
        return []


def update_leaderboard(leaderboard, winner):
    for idx, item in enumerate(leaderboard):
        if item.split(',')[1] == winner[1] and int(item.split(',')[0]) < int(winner[0]):
                leaderboard[idx] = '{}, {}'.format(winner[0], winner[1])
    leaderboard.sort(reverse=True)
    return leaderboard


def save_leaderboard(leaderboard):
    if len(leaderboard) > 1:
        with open('Leaderboard.txt', 'w') as f:
            for item in leaderboard:
                f.write(f'{item}\n')
            f.close()
