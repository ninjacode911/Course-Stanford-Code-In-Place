# space_shooter.py
import tkinter as tk
import random
import time

# ---------- Configuration ----------
CANVAS_WIDTH = 600
CANVAS_HEIGHT = 800
FPS = 60               # target frames per second
PLAYER_WIDTH = 50
PLAYER_HEIGHT = 30
PLAYER_SPEED = 8
BULLET_WIDTH = 4
BULLET_HEIGHT = 10
BULLET_SPEED = 12
ENEMY_SIZE = 36
ENEMY_SPEED = 2.0      # base downward speed
ENEMY_HOR_SPEED = 1.5  # sideways oscillation speed
ENEMY_SPAWN_DELAY = 1200  # ms between spawn attempts
MAX_ENEMIES = 10
INITIAL_LIVES = 3
STAR_COUNT = 80
STAR_SPEED_MIN = 0.7
STAR_SPEED_MAX = 2.0

# ---------- Utility ----------
def rects_overlap(a_left, a_top, a_right, a_bottom,
                  b_left, b_top, b_right, b_bottom):
    return not (a_right < b_left or a_left > b_right or a_bottom < b_top or a_top > b_bottom)

# ---------- Game Objects ----------
class Player:
    def __init__(self, canvas):
        self.canvas = canvas
        self.width = PLAYER_WIDTH
        self.height = PLAYER_HEIGHT
        self.x = CANVAS_WIDTH // 2
        self.y = CANVAS_HEIGHT - 60
        self.vx = 0
        self.id = None
        self.color = 'lightblue'
        self.draw()

    def draw(self):
        if self.id:
            self.canvas.delete(self.id)
        # draw a simple ship as triangle + cockpit rectangle
        left = self.x - self.width // 2
        right = self.x + self.width // 2
        top = self.y - self.height // 2
        bottom = self.y + self.height // 2
        points = [left, bottom, self.x, top, right, bottom]
        self.id = self.canvas.create_polygon(points, fill=self.color, outline='black')

    def move(self):
        self.x += self.vx
        # clamp to canvas
        half = self.width // 2
        if self.x - half < 0:
            self.x = half
        if self.x + half > CANVAS_WIDTH:
            self.x = CANVAS_WIDTH - half
        self.draw()

    def set_velocity(self, vx):
        self.vx = vx

    def center(self):
        return self.x, self.y

class Bullet:
    def __init__(self, canvas, x, y):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.id = canvas.create_rectangle(
            x - BULLET_WIDTH//2, y - BULLET_HEIGHT,
            x + BULLET_WIDTH//2, y, fill='yellow', outline=''
        )

    def update(self):
        self.y -= BULLET_SPEED
        self.canvas.coords(
            self.id,
            self.x - BULLET_WIDTH//2, self.y - BULLET_HEIGHT,
            self.x + BULLET_WIDTH//2, self.y
        )

    def off_screen(self):
        return self.y + BULLET_HEIGHT < 0

    def destroy(self):
        try:
            self.canvas.delete(self.id)
        except tk.TclError:
            pass

class Enemy:
    def __init__(self, canvas, x, y, speed, pattern_seed=0, color='red'):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.size = ENEMY_SIZE
        self.speed = speed
        self.seed = pattern_seed
        self.spawn_time = time.time()
        self.color = color
        self.id = canvas.create_oval(
            self.x - self.size/2, self.y - self.size/2,
            self.x + self.size/2, self.y + self.size/2,
            fill=color, outline='black'
        )

    def update(self):
        elapsed = (time.time() - self.spawn_time)
        # downward movement
        self.y += self.speed
        # horizontal oscillation (gives zig-zag)
        self.x += ENEMY_HOR_SPEED * math_sin_wave(elapsed, self.seed)
        self.canvas.coords(
            self.id,
            self.x - self.size/2, self.y - self.size/2,
            self.x + self.size/2, self.y + self.size/2
        )

    def off_screen(self):
        return self.y - self.size/2 > CANVAS_HEIGHT

    def destroy(self):
        try:
            self.canvas.delete(self.id)
        except tk.TclError:
            pass

    def bbox(self):
        return (self.x - self.size/2, self.y - self.size/2, self.x + self.size/2, self.y + self.size/2)

class Star:
    def __init__(self, canvas):
        self.canvas = canvas
        self.x = random.uniform(0, CANVAS_WIDTH)
        self.y = random.uniform(0, CANVAS_HEIGHT)
        self.speed = random.uniform(STAR_SPEED_MIN, STAR_SPEED_MAX)
        self.size = random.choice([1, 2, 3])
        self.id = canvas.create_oval(self.x, self.y, self.x + self.size, self.y + self.size, fill='white', outline='')

    def update(self):
        self.y += self.speed
        if self.y > CANVAS_HEIGHT:
            self.y = 0
            self.x = random.uniform(0, CANVAS_WIDTH)
            self.speed = random.uniform(STAR_SPEED_MIN, STAR_SPEED_MAX)
        self.canvas.coords(self.id, self.x, self.y, self.x + self.size, self.y + self.size)

# ---------- Helpers ----------
def math_sin_wave(t, seed=0):
    # a deterministic-ish oscillation based on time and seed
    # avoid importing math at top-level for safety; use here
    import math
    # frequency and amplitude tuned for gentle zig-zag
    freq = 1.1 + (seed % 3) * 0.2
    amp = 1.2 + (seed % 5) * 0.5
    return math.sin(t * freq + seed) * amp

# ---------- Game Class ----------
class SpaceShooter:
    def __init__(self, root):
        self.root = root
        self.canvas = tk.Canvas(root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg='black')
        self.canvas.pack()
        self.running = False
        self.player = Player(self.canvas)
        self.bullets = []
        self.enemies = []
        self.stars = [Star(self.canvas) for _ in range(STAR_COUNT)]
        self.score = 0
        self.lives = INITIAL_LIVES
        self.last_spawn = 0
        self.paused = False
        self.game_over = False
        self.level = 1
        self.enemy_spawn_delay = ENEMY_SPAWN_DELAY
        self.setup_ui()
        self.bind_keys()
        self.start()

    def setup_ui(self):
        # HUD elements
        self.score_text = self.canvas.create_text(12, 12, anchor='nw', text=f"Score: {self.score}", fill='white', font=('Arial', 14))
        self.lives_text = self.canvas.create_text(CANVAS_WIDTH-12, 12, anchor='ne', text=f"Lives: {self.lives}", fill='white', font=('Arial', 14))
        self.level_text = self.canvas.create_text(CANVAS_WIDTH//2, 12, anchor='n', text=f"Level: {self.level}", fill='white', font=('Arial', 14))

    def bind_keys(self):
        self.root.bind('<KeyPress-Left>', lambda e: self.player.set_velocity(-PLAYER_SPEED))
        self.root.bind('<KeyRelease-Left>', lambda e: self.player.set_velocity(0) if not self.is_key_down('Right') else None)
        self.root.bind('<KeyPress-Right>', lambda e: self.player.set_velocity(PLAYER_SPEED))
        self.root.bind('<KeyRelease-Right>', lambda e: self.player.set_velocity(0) if not self.is_key_down('Left') else None)
        self.root.bind('<space>', lambda e: self.fire_bullet())
        self.root.bind('r', lambda e: self.restart() if self.game_over else None)
        self.keys_held = set()
        # track key down/up manually for simultaneous keys
        def on_keydown(event):
            self.keys_held.add(event.keysym)
        def on_keyup(event):
            self.keys_held.discard(event.keysym)
        self.root.bind('<KeyPress>', on_keydown)
        self.root.bind('<KeyRelease>', on_keyup)

    def is_key_down(self, name):
        return name in self.keys_held

    def start(self):
        self.running = True
        self.game_loop()

    def stop(self):
        self.running = False

    def fire_bullet(self):
        if self.game_over:
            return
        px, py = self.player.center()
        bullet = Bullet(self.canvas, px, py - PLAYER_HEIGHT//2 - 2)
        self.bullets.append(bullet)

    def spawn_enemy_if_needed(self):
        now = int(time.time()*1000)
        # reduce delay slightly as level increases
        delay = max(350, self.enemy_spawn_delay - (self.level-1)*100)
        if now - self.last_spawn < delay:
            return
        self.last_spawn = now
        if len(self.enemies) >= MAX_ENEMIES + (self.level - 1) * 2:
            return
        # spawn at random x near top
        x = random.uniform(ENEMY_SIZE/2, CANVAS_WIDTH - ENEMY_SIZE/2)
        y = -ENEMY_SIZE/2
        speed = ENEMY_SPEED + (self.level - 1) * 0.5 + random.random() * 0.8
        seed = random.randint(0, 20)
        color = random.choice(['red', 'orange', 'magenta', 'cyan'])
        e = Enemy(self.canvas, x, y, speed, seed, color)
        self.enemies.append(e)

    def update_objects(self):
        # update stars
        for s in self.stars:
            s.update()
        # update player
        self.player.move()
        # bullets
        for b in list(self.bullets):
            b.update()
            if b.off_screen():
                b.destroy()
                self.bullets.remove(b)
        # enemies
        for e in list(self.enemies):
            e.update()
            if e.off_screen():
                # enemy reached bottom — player loses a life
                e.destroy()
                self.enemies.remove(e)
                self.lives -= 1
                self.canvas.itemconfigure(self.lives_text, text=f"Lives: {self.lives}")
                if self.lives <= 0:
                    self.end_game(False)

    def handle_collisions(self):
        # bullet-enemy collisions
        for b in list(self.bullets):
            b_bbox = (b.x - BULLET_WIDTH/2, b.y - BULLET_HEIGHT, b.x + BULLET_WIDTH/2, b.y)
            for e in list(self.enemies):
                ex1, ey1, ex2, ey2 = e.bbox()
                if rects_overlap(b_bbox[0], b_bbox[1], b_bbox[2], b_bbox[3], ex1, ey1, ex2, ey2):
                    # collision!
                    try:
                        b.destroy()
                    except:
                        pass
                    try:
                        e.destroy()
                    except:
                        pass
                    if b in self.bullets:
                        self.bullets.remove(b)
                    if e in self.enemies:
                        self.enemies.remove(e)
                    self.score += 100
                    self.canvas.itemconfigure(self.score_text, text=f"Score: {self.score}")
                    break  # bullet gone, move to next bullet

        # enemy-player collisions
        px, py = self.player.center()
        p_left = px - PLAYER_WIDTH/2
        p_right = px + PLAYER_WIDTH/2
        p_top = py - PLAYER_HEIGHT/2
        p_bottom = py + PLAYER_HEIGHT/2
        for e in list(self.enemies):
            ex1, ey1, ex2, ey2 = e.bbox()
            if rects_overlap(p_left, p_top, p_right, p_bottom, ex1, ey1, ex2, ey2):
                # collision with player
                e.destroy()
                if e in self.enemies:
                    self.enemies.remove(e)
                self.lives -= 1
                self.canvas.itemconfigure(self.lives_text, text=f"Lives: {self.lives}")
                if self.lives <= 0:
                    self.end_game(False)

    def check_win_condition(self):
        # optionally define a win condition (survive N waves)
        # For this simple version, if the score reaches some threshold, you win.
        if self.score >= 3000:
            self.end_game(True)

    def game_loop(self):
        if not self.running:
            return
        if not self.paused and not self.game_over:
            # spawn enemies
            self.spawn_enemy_if_needed()
            # update objects
            self.update_objects()
            # handle collisions
            self.handle_collisions()
            # check win
            self.check_win_condition()
            # level up based on score
            new_level = 1 + self.score // 800
            if new_level != self.level:
                self.level = new_level
                self.canvas.itemconfigure(self.level_text, text=f"Level: {self.level}")
            # occasionally increase difficulty
        # schedule next frame
        self.root.after(int(1000 / FPS), self.game_loop)

    def end_game(self, won):
        self.game_over = True
        self.running = False
        # hide active objects (but keep HUD)
        for b in list(self.bullets):
            b.destroy()
        for e in list(self.enemies):
            e.destroy()
        self.bullets.clear()
        self.enemies.clear()
        text = "YOU WIN!" if won else "GAME OVER"
        color = 'green' if won else 'red'
        # big overlay
        self.overlay = self.canvas.create_rectangle(40, CANVAS_HEIGHT//2 - 80, CANVAS_WIDTH - 40, CANVAS_HEIGHT//2 + 80, fill='black', outline='white')
        self.msg = self.canvas.create_text(CANVAS_WIDTH//2, CANVAS_HEIGHT//2 - 20, text=text, fill=color, font=('Helvetica', 36, 'bold'))
        self.sub = self.canvas.create_text(CANVAS_WIDTH//2, CANVAS_HEIGHT//2 + 20,
                                           text="Press 'r' to restart", fill='white', font=('Helvetica', 16))
        # still allow restart by pressing 'r'
        # Keep HUD visible

    def restart(self):
        # clear canvas and reinitialize everything
        try:
            self.canvas.delete("all")
        except tk.TclError:
            pass
        self.player = Player(self.canvas)
        self.bullets = []
        self.enemies = []
        # rebuild stars
        self.stars = [Star(self.canvas) for _ in range(STAR_COUNT)]
        self.score = 0
        self.lives = INITIAL_LIVES
        self.level = 1
        self.enemy_spawn_delay = ENEMY_SPAWN_DELAY
        self.last_spawn = 0
        self.setup_ui()
        self.game_over = False
        self.running = True
        self.game_loop()

# ---------- Entry point ----------
def main():
    root = tk.Tk()
    root.title("Space Ace- Navnit's Code In Place Project")
    game = SpaceShooter(root)
    root.resizable(False, False)
    # instructions label (outside canvas)
    instr = tk.Label(root, text="Use ← → to move. Space to shoot. 'r' to restart after game over.", fg='white', bg='black')
    instr.pack(fill='x')
    root.mainloop()

if __name__ == '__main__':
    main()
