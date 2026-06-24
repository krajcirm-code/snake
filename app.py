import os
import random
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajny_kluc_pre_hadika'
socketio = SocketIO(app, cors_allowed_origins="*")

# Herné nastavenia
GRID_SIZE = 30
PLAYERS = {}
FOOD = []

def spawn_food():
    while len(FOOD) < 10:
        x = random.randint(0, GRID_SIZE - 1)
        y = random.randint(0, GRID_SIZE - 1)
        FOOD.append({'x': x, 'y': y})

spawn_food()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    # Nový hráč sa pripojí
    PLAYERS[request.sid] = {
        'body': [{'x': 15, 'y': 15}],
        'dir': 'RIGHT',
        'color': f"#{random.randint(50, 255):02x}{random.randint(50, 255):02x}{random.randint(50, 255):02x}",
        'score': 0
    }
    emit('game_state', {'players': PLAYERS, 'food': FOOD}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in PLAYERS:
        del PLAYERS[request.sid]

@socketio.on('move')
def handle_move(data):
    direction = data.get('direction')
    if request.sid in PLAYERS:
        player = PLAYERS[request.sid]
        # Zabránenie otočeniu do protismeru
        curr_dir = player['dir']
        if (direction == 'UP' and curr_dir != 'DOWN') or \
           (direction == 'DOWN' and curr_dir != 'UP') or \
           (direction == 'LEFT' and curr_dir != 'RIGHT') or \
           (direction == 'RIGHT' and curr_dir != 'LEFT'):
            player['dir'] = direction

def game_loop():
    while True:
        socketio.sleep(0.1)  # Tik hry (každých 100ms)
        if not PLAYERS:
            continue

        for player_id, player in list(PLAYERS.items()):
            head = player['body'][0]
            direction = player['dir']

            # Výpočet novej pozície hlavy
            if direction == 'UP':    new_head = {'x': head['x'], 'y': head['y'] - 1}
            elif direction == 'DOWN':  new_head = {'x': head['x'], 'y': head['y'] + 1}
            elif direction == 'LEFT':  new_head = {'x': head['x'] - 1, 'y': head['y']}
            elif direction == 'RIGHT': new_head = {'x': head['x'] + 1, 'y': head['y']}

            # Prechod cez steny (ako v slither.io / snake.io)
            new_head['x'] = (new_head['x'] + GRID_SIZE) % GRID_SIZE
            new_head['y'] = (new_head['y'] + GRID_SIZE) % GRID_SIZE

            # Vloženie novej hlavy
            player['body'].insert(0, new_head)

            # Kontrola kolízie s jedlom
            ate_food = False
            for f in FOOD:
                if f['x'] == new_head['x'] and f['y'] == new_head['y']:
                    FOOD.remove(f)
                    player['score'] += 1
                    ate_food = True
                    break

            if ate_food:
                spawn_food()
            else:
                player['body'].pop()  # Ak nezjedol jedlo, skráti sa chvost

            # Kontrola kolízie s inými hadmi (zjednoduchšené: ak narazíš do kohokoľvek, zomrieš)
            for other_id, other_player in PLAYERS.items():
                start_idx = 1 if other_id == player_id else 0
                for part in other_player['body'][start_idx:]:
                    if new_head['x'] == part['x'] and new_head['y'] == part['y']:
                        # Reset hráča pri smrti
                        player['body'] = [{'x': random.randint(0, GRID_SIZE-1), 'y': random.randint(0, GRID_SIZE-1)}]
                        player['score'] = 0

        socketio.emit('game_state', {'players': PLAYERS, 'food': FOOD})

# Spustenie hernej slučky na pozadí
socketio.start_background_task(game_loop)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)