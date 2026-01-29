import random
import sqlite3
import arcade
from arcade.gui import UIManager, UIFlatButton, UITextureButton, UILabel, UIInputText, UITextArea, UISlider, UIDropdown, \
    UIMessageBox  # Это разные виджеты
from arcade.gui.widgets.layout import UIAnchorLayout, UIBoxLayout
from arcade.camera import Camera2D
from pyglet.graphics import Batch
from arcade.particles import FadeParticle, Emitter, EmitBurst, EmitInterval, EmitMaintainCount

SCREEN_W = 1280
SCREEN_H = 720
TITLE = "Platformer"
WINDOW = arcade.Window(SCREEN_W, SCREEN_H, TITLE)

# Физика и движение
GRAVITY = 4            # Пикс/с^2
MOVE_SPEED = 8          # Пикс/с
JUMP_SPEED = 50          # Начальный импульс прыжка, пикс/с
LADDER_SPEED = 5        # Скорость по лестнице

TILE_SCALING = 1

LIVES = 3

LEVELS = ['level_test', 'level_1', 'level_2']

MAPS = ['Maps/Test_map.tmx','Maps/Level_1.tmx', 'Maps/Level_2.tmx']

CHARACTERS = [['Character/character_beige_walk_a.png', 'Character/character_beige_walk_b.png',
                'Character/character_beige_climb_a.png', 'Character/character_beige_climb_b.png',
                'Character/character_beige_jump.png'],
                ['Character/character_green_walk_a.png', 'Character/character_green_walk_b.png',
                 'Character/character_green_climb_a.png', 'Character/character_green_climb_b.png',
                 'Character/character_green_jump.png'],
                ['Character/character_pink_walk_a.png', 'Character/character_pink_walk_b.png',
                 'Character/character_pink_climb_a.png', 'Character/character_pink_climb_b.png',
                 'Character/character_pink_jump.png'],
                ['Character/character_purple_walk_a.png', 'Character/character_purple_walk_b.png',
                 'Character/character_purple_climb_a.png', 'Character/character_purple_climb_b.png',
                 'Character/character_purple_jump.png'],
                ['Character/character_yellow_walk_a.png', 'Character/character_yellow_walk_b.png',
                 'Character/character_yellow_climb_a.png', 'Character/character_yellow_climb_b.png',
                 'Character/character_yellow_jump.png']
                ]

PLAYER_NAME = ''

# Качество жизни прыжка
COYOTE_TIME = 0.08        # Сколько после схода с платформы можно ещё прыгнуть
JUMP_BUFFER = 0.12        # Если нажали прыжок чуть раньше приземления, мы его «запомним» (тоже лайфхак для улучшения качества жизни игрока)
MAX_JUMPS = 1             # С двойным прыжком всё лучше, но не сегодня
EXTRA_JUMPS = 0

# Камера
CAMERA_LERP = 0.12        # Плавность следования камеры
WORLD_COLOR = arcade.color.SKY_BLUE

background_music = arcade.load_sound('Music/retro-dreamscape_92772.mp3')
PLAYER_MUSIC = background_music.play(loop=True, volume=0.5)

SPARK_TEX = [
    arcade.make_soft_circle_texture(8, arcade.color.PASTEL_YELLOW),
    arcade.make_soft_circle_texture(8, arcade.color.PEACH),
    arcade.make_soft_circle_texture(8, arcade.color.BABY_BLUE),
    arcade.make_soft_circle_texture(8, arcade.color.ELECTRIC_CRIMSON),
]


def make_trail(attached_sprite, maintain=60):
    # «След за объектом»: поддерживаем постоянное число частиц
    emit = Emitter(
        center_xy=(attached_sprite.center_x, attached_sprite.center_y - 20),
        emit_controller=EmitMaintainCount(maintain),
        particle_factory=lambda e: FadeParticle(
            filename_or_texture=random.choice(SPARK_TEX),
            change_xy=arcade.math.rand_in_circle((0.0, 0.0), 1.6),
            lifetime=random.uniform(0.35, 0.6),
            start_alpha=220, end_alpha=0,
            scale=random.uniform(1, 2),
        ),
    )
    # Хитрость: каждое обновление будем прижимать центр к спрайту (см. ниже)
    emit._attached = attached_sprite
    return emit


class Res_level(arcade.View):
    def __init__(self, level, score, time):
        super().__init__()
        arcade.set_background_color(arcade.color.DARK_SLATE_GRAY)
        self.batch = Batch()
        self.manager = UIManager()
        self.manager.enable()
        self.level = level
        self.score = score
        self.time = time

        self.anchor_layout = UIAnchorLayout()
        self.box_layout = UIBoxLayout(vertical=True, space_between=10)

        self.setup_widgets()

        self.anchor_layout.add(self.box_layout)
        self.manager.add(self.anchor_layout)

    def setup_widgets(self):
        con = sqlite3.connect('Saves.sqlite')
        if self.level == 0:
            score = con.cursor().execute(f'''SELECT level_test_score FROM results WHERE player_name = ?''',
                                    [PLAYER_NAME, ]).fetchone()[0]
        elif self.level == 1:
            score = con.cursor().execute(f'''SELECT level_1_score FROM results WHERE player_name = ?''',
                                    [PLAYER_NAME, ]).fetchone()[0]
        elif self.level == 2:
            score = con.cursor().execute(f'''SELECT level_2_score FROM results WHERE player_name = ?''',
                                    [PLAYER_NAME, ]).fetchone()[0]
        if self.level == 0:
            time = con.cursor().execute(f'''SELECT level_test_time FROM results WHERE player_name = ?''',
                                    [PLAYER_NAME, ]).fetchone()[0]
        elif self.level == 1:
            time = con.cursor().execute(f'''SELECT level_1_time FROM results WHERE player_name = ?''',
                                    [PLAYER_NAME, ]).fetchone()[0]
        elif self.level == 2:
            time = con.cursor().execute(f'''SELECT level_2_time FROM results WHERE player_name = ?''',
                                    [PLAYER_NAME, ]).fetchone()[0]
        con.close()
        self.box_layout.add(UILabel(text='Рекорд'))
        label = UILabel(text=f'score: {score}', font_size=30)
        self.box_layout.add(label)
        label_time = UILabel(text=f'time: {time}', font_size=30)
        self.box_layout.add(label_time)
        self.box_layout.add(UILabel(text='Результат'))
        label = UILabel(text=f'score: {self.score}', font_size=30)
        self.box_layout.add(label)
        label_time = UILabel(text=f'time: {self.time}', font_size=30)
        self.box_layout.add(label_time)

        texture_normal = arcade.load_texture(":resources:/gui_basic_assets/button/red_normal.png")
        texture_hovered = arcade.load_texture(":resources:/gui_basic_assets/button/red_hover.png")
        texture_pressed = arcade.load_texture(":resources:/gui_basic_assets/button/red_press.png")
        button_ok = UITextureButton(text='OK', texture=texture_normal,
                                       texture_hovered=texture_hovered,
                                       texture_pressed=texture_pressed,
                                       scale=1.0)
        button_ok.on_click = lambda x: WINDOW.show_view(MenuView())
        self.box_layout.add(button_ok)



    def on_draw(self):
        self.clear()
        self.batch.draw()
        self.manager.draw()


class Create_player(arcade.View):
    def __init__(self):
        super().__init__()
        arcade.set_background_color(arcade.color.DARK_SLATE_GRAY)
        self.batch = Batch()
        self.manager = UIManager()
        self.manager.enable()

        self.anchor_layout = UIAnchorLayout()
        self.box_layout = UIBoxLayout(vertical=True, space_between=10)

        self.setup_widgets()

        self.anchor_layout.add(self.box_layout)
        self.manager.add(self.anchor_layout)

    def setup_widgets(self):
        input_text = UIInputText(width=200, height=100, text='Имя профиля')
        input_text.on_change = lambda text: self.change(text.new_value)
        self.box_layout.add(input_text)
        texture_normal = arcade.load_texture(":resources:/gui_basic_assets/button/red_normal.png")
        texture_hovered = arcade.load_texture(":resources:/gui_basic_assets/button/red_hover.png")
        texture_pressed = arcade.load_texture(":resources:/gui_basic_assets/button/red_press.png")
        button_ok = UITextureButton(text='Создать аккаунт', texture=texture_normal,
                                       texture_hovered=texture_hovered,
                                       texture_pressed=texture_pressed,
                                       scale=1.0)
        button_ok.on_click = lambda x: self.new_log()
        self.box_layout.add(button_ok)
        button_no = UITextureButton(text='Отмена', texture=texture_normal,
                                       texture_hovered=texture_hovered,
                                       texture_pressed=texture_pressed,
                                       scale=1.0)
        button_no.on_click = lambda x: WINDOW.show_view(Login())
        self.box_layout.add(button_no)

    def on_draw(self):
        self.clear()
        self.batch.draw()
        self.manager.draw()


    def change(self, text):
        self.p_name = str(text)

    def new_log(self):
        con = sqlite3.connect('Saves.sqlite')
        con.cursor().execute(f'''INSERT INTO results(player_name) VALUES(?)''', [self.p_name, ])
        con.commit()
        con.close()
        WINDOW.show_view(Login())


class Login(arcade.View):
    def __init__(self):
        super().__init__()
        arcade.set_background_color(arcade.color.DARK_SLATE_GRAY)
        self.batch = Batch()
        self.manager = UIManager()
        self.manager.enable()

        self.anchor_layout = UIAnchorLayout()
        self.box_layout = UIBoxLayout(vertical=True, space_between=10)

        self.setup_widgets()
        self.player_name = ''

        self.anchor_layout.add(self.box_layout)
        self.manager.add(self.anchor_layout)

    def setup_widgets(self):
        con = sqlite3.connect('Saves.sqlite')
        label = UILabel('Выберите профиль', width=200, height=100, font_size=24)
        self.box_layout.add(label)
        sp = [x[0] for x in con.cursor().execute('SELECT player_name FROM results').fetchall()]
        con.close()
        dropdown = UIDropdown(options=sp, width=200, height=50, font_size=20, default=sp[0])
        dropdown.on_change = lambda value: self.change(value)
        self.box_layout.add(dropdown)
        texture_normal = arcade.load_texture(":resources:/gui_basic_assets/button/red_normal.png")
        texture_hovered = arcade.load_texture(":resources:/gui_basic_assets/button/red_hover.png")
        texture_pressed = arcade.load_texture(":resources:/gui_basic_assets/button/red_press.png")
        button_start = UITextureButton(text='Играть', texture=texture_normal,
                                        texture_hovered=texture_hovered,
                                        texture_pressed=texture_pressed,
                                        scale=1.0)
        button_start.on_click = lambda x: self.start()
        self.box_layout.add(button_start)
        button_create = UITextureButton(text='Создать новый профиль', texture=texture_normal,
                                        texture_hovered=texture_hovered,
                                        texture_pressed=texture_pressed,
                                        scale=1.0)
        button_create.on_click = lambda event: WINDOW.show_view(Create_player())
        self.box_layout.add(button_create)

    def start(self):
        global PLAYER_NAME
        PLAYER_NAME = str(self.player_name)
        WINDOW.show_view(MenuView())

    def change(self, value):
        self.player_name = value.new_value

    def on_draw(self):
        self.clear()
        self.batch.draw()
        self.manager.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        pass


class MenuView(arcade.View):
    def __init__(self):
        super().__init__()
        arcade.set_background_color(arcade.color.DARK_SLATE_GRAY)
        self.batch = Batch()
        self.manager = UIManager()
        self.manager.enable()

        self.combination = []
        self.cheat_code = [arcade.key.UP, arcade.key.UP, arcade.key.DOWN, arcade.key.DOWN, arcade.key.LEFT,
                           arcade.key.RIGHT, arcade.key.LEFT, arcade.key.RIGHT, arcade.key.B, arcade.key.A]

        self.anchor_layout = UIAnchorLayout()
        self.box_layout = UIBoxLayout(vertical=True, space_between=10)

        self.setup_widgets()

        self.anchor_layout.add(self.box_layout)
        self.manager.add(self.anchor_layout)

    def setup_widgets(self):
        button_ret = UIFlatButton(text='Вернуться к выбору профиля', font_size=20, font_color=arcade.color.SKY_BLUE,
                                    width=300, height=100, color=arcade.color.RED, x=20, y=SCREEN_H - 120)
        button_ret.on_click = lambda x: WINDOW.show_view(Login())
        self.manager.add(button_ret)
        button = UIFlatButton(text='Level 1', width=200, height=100, color=arcade.color.GRAY)
        button.on_click = lambda event: WINDOW.show_view(Platformer(1))
        self.box_layout.add(button)
        button = UIFlatButton(text='Level 2', width=200, height=100, color=arcade.color.GRAY)
        button.on_click = lambda event: WINDOW.show_view(Platformer(2))
        self.box_layout.add(button)
        #button = UIFlatButton(text='Level test', width=200, height=100, color=arcade.color.GRAY)
        #button.on_click = lambda event: WINDOW.show_view(Platformer(0))
        #self.box_layout.add(button)

    def on_draw(self):
        self.clear()
        self.batch.draw()
        self.manager.draw()

    #def on_update(self, dt):

    def on_mouse_press(self, x, y, button, modifiers):
        pass

    def on_key_press(self, key, modifiers):
        self.combination.append(key)
        if self.combination == self.cheat_code:
            WINDOW.show_view(Platformer(0))
        elif len(self.combination) >= len(self.cheat_code):
            self.combination = []
        if self.combination[0] != self.cheat_code[0]:
            self.combination = []


class Player(arcade.Sprite):
    def __init__(self, character):
        super().__init__()
        self.hero = 0
        self.charater = CHARACTERS[character]
        self.texture = arcade.load_texture(self.charater[0])
        self.center_x, self.center_y = 128, 256
        self.scale = 0.8
        self.lives = LIVES
        self.extra_lives = 0
        self.jumps_left = MAX_JUMPS
        self.extra_jumps = EXTRA_JUMPS
        # self.change_x = 0
        # self.change_y = 0


    def update(self, dt: float, on_leader=False, grounded=True):
        # self.center_x += self.change_x
        # self.center_y += self.change_y
        if self.change_x != 0 or self.change_y != 0:
            self.hero += 1 / MOVE_SPEED
        self.hero %= 2
        if on_leader:
            self.hero += 2
        elif not grounded:
            self.hero = -1
        self.texture = arcade.load_texture(self.charater[int(self.hero)])

#class Platformer(arcade.Window):
class Platformer(arcade.View):
    def __init__(self, map):
        #super().__init__(SCREEN_W, SCREEN_H, TITLE, antialiasing=True)
        super().__init__()
        arcade.set_background_color(WORLD_COLOR)

        self.map = map

        # Камеры
        self.world_camera = Camera2D()
        self.gui_camera = Camera2D()

        # Списки спрайтов
        self.player_list = arcade.SpriteList()
        self.walls = arcade.SpriteList(use_spatial_hash=True)  # Очень много статичных — хэш спасёт вас
        self.platforms = arcade.SpriteList()  # Двигающиеся платформы
        self.ladders = arcade.SpriteList()
        self.coins = arcade.SpriteList()
        self.hazards = arcade.SpriteList()  # Шипы/лава
        self.sprite_extra_lives = arcade.SpriteList()
        self.lever = arcade.SpriteList()
        self.f_lever = False
        self.exit = arcade.SpriteList()
        self.background = arcade.SpriteList()
        self.decor = arcade.SpriteList()

        self.emitters = []
        self.trail = None

        # Игрок
        self.player = None
        self.spawn_point = (128, 256)  # Куда респавнить после шипов

        # Физика
        self.engine = None

        self.timer = 0

        # Ввод
        self.left = self.right = self.up = self.down = self.jump_pressed = False
        self.jump_buffer_timer = 0.0
        self.time_since_ground = 999.0

        self.f_jump = False

        # Счёт
        self.score = 0
        self.batch = Batch()
        self.text_info = arcade.Text("WASD/стрелки — ходьба/лестницы • SPACE — прыжок",
                                     16, 16, arcade.color.GRAY, 14, batch=self.batch)
        self.setup()

    def setup(self):
        # --- Игрок ---
        self.player_list.clear()
        self.player = Player(0)
        self.player.center_x, self.player.center_y = self.spawn_point
        self.player_list.append(self.player)

        # --- Мир: сделаем крошечную арену руками ---
        # Пол из «травы»
        tile_map = arcade.load_tilemap(MAPS[self.map], scaling=TILE_SCALING)
        self.walls = tile_map.sprite_lists["walls"]
        # Лестница
        self.ladders = tile_map.sprite_lists["ladders"]
        # Двигающаяся платформа (влево-вправо)
        self.platforms = tile_map.sprite_lists["platforms"]
        # Монетки
        self.coins = tile_map.sprite_lists["coins"]
        # Шипы (притворимся лавой)
        self.hazards = tile_map.sprite_lists["hazard"]
        # доп сердца
        self.sprite_extra_lives = tile_map.sprite_lists["extra_lives"]
        self.lever = tile_map.sprite_lists['lever']
        self.exit = tile_map.sprite_lists['exit']
        self.background = tile_map.sprite_lists['background']
        self.decor = tile_map.sprite_lists['decor']

        self.trail = make_trail(self.player)
        self.emitters.append(self.trail)

        # --- Физический движок платформера ---
        # Статичные — в walls, подвижные — в platforms, лестницы — ladders.
        self.engine = arcade.PhysicsEnginePlatformer(
            player_sprite=self.player,
            gravity_constant=GRAVITY,
            walls=self.walls,
            platforms=self.platforms,
            ladders=self.ladders
        )

        # Сбросим вспомогательные таймеры
        self.jump_buffer_timer = 0
        self.time_since_ground = 999.0
        self.player.jumps_left = MAX_JUMPS

    def on_draw(self):
        self.clear()

        # --- Мир ---
        self.world_camera.use()
        self.walls.draw()
        self.platforms.draw()
        self.ladders.draw()
        self.hazards.draw()
        self.coins.draw()
        self.sprite_extra_lives.draw()
        self.lever.draw()
        self.exit.draw()
        self.player_list.draw()
        self.trail.draw()
        self.background.draw()
        self.decor.draw()


        # --- GUI ---
        self.gui_camera.use()
        self.batch.draw()

    def on_key_press(self, key, modifiers):
        if key in (arcade.key.LEFT, arcade.key.A):
            self.left = True
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self.right = True
        elif key in (arcade.key.UP, arcade.key.W):
            self.up = True
        elif key in (arcade.key.DOWN, arcade.key.S):
            self.down = True
        elif key == arcade.key.SPACE:
            self.jump_pressed = True
            self.jump_buffer_timer = JUMP_BUFFER
        elif key == arcade.key.E and arcade.check_for_collision_with_list(self.player, self.lever):
            self.f_lever = not self.f_lever
            if self.f_lever:
                self.lever[0].texture = arcade.load_texture('Tiles/lever/lever_right.png')
                self.exit[1].texture = arcade.load_texture('Tiles/door/door_open.png')
                self.exit[0].texture = arcade.load_texture('Tiles/door/door_open_top.png')
            else:
                self.lever[0].texture = arcade.load_texture('Tiles/lever/lever_left.png')
                self.exit[1].texture = arcade.load_texture('Tiles/door/door_closed.png')
                self.exit[0].texture = arcade.load_texture('Tiles/door/door_closed_top.png')

    def on_key_release(self, key, modifiers):
        if key in (arcade.key.LEFT, arcade.key.A):
            self.left = False
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self.right = False
        elif key in (arcade.key.UP, arcade.key.W):
            self.up = False
        elif key in (arcade.key.DOWN, arcade.key.S):
            self.down = False
        elif key == arcade.key.SPACE:
            self.jump_pressed = False
            self.f_jump = True
            # Вариативная высота прыжка: отпустили рано — подрежем скорость вверх
            if self.player.change_y > 0:
                self.player.change_y *= 0.45 #self.text_score

    def on_update(self, dt: float):
        self.trail.update()
        if self.trail:
            self.trail.center_x = self.player.center_x
            self.trail.center_y = self.player.center_y - 30
        self.timer += dt
        # Обработка горизонтального движения
        move = 0
        if self.left and not self.right:
            move = -MOVE_SPEED
        elif self.right and not self.left:
            move = MOVE_SPEED
        self.player.change_x = move

        # Лестницы имеют приоритет над гравитацией: висим/лезем
        on_ladder = self.engine.is_on_ladder()  # На лестнице?
        if on_ladder:
            # По лестнице вверх/вниз
            if self.up and not self.down:
                self.player.change_y = LADDER_SPEED
            elif self.down and not self.up:
                self.player.change_y = -LADDER_SPEED
            else:
                self.player.change_y = 0

        # Если не на лестнице — работает обычная гравитация движка
        # Прыжок: can_jump() + койот + буфер
        grounded = self.engine.can_jump(y_distance=6)  # Есть пол под ногами?
        if grounded:
            self.time_since_ground = 0
            self.player.jumps_left = MAX_JUMPS
            self.player.extra_jumps = EXTRA_JUMPS
        else:
            self.time_since_ground += dt

        # Учтём «запомненный» пробел
        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= dt

        want_jump = self.jump_pressed or (self.jump_buffer_timer > 0)

        # Можно прыгать, если стоим на земле или в пределах койот-времени
        if want_jump:
            can_coyote = (self.time_since_ground <= COYOTE_TIME)
            if grounded or can_coyote:
                # Просим движок прыгнуть: он корректно задаст начальную вертикальную скорость
                self.engine.jump(JUMP_SPEED)
                self.jump_buffer_timer = 0
            elif self.player.extra_jumps > 0 and self.f_jump:
                self.engine.jump(JUMP_SPEED * 2)
                self.jump_buffer_timer = 0
                self.player.extra_jumps -= 1


        # Обновляем физику — движок сам двинет игрока и платформы
        self.engine.update()

        # Собираем монетки и проверяем опасности
        for coin in arcade.check_for_collision_with_list(self.player, self.coins):
            coin.remove_from_sprite_lists()
            self.score += 1

        for extra_live in arcade.check_for_collision_with_list(self.player, self.sprite_extra_lives):
            extra_live.remove_from_sprite_lists()
            self.player.extra_lives += 1

        if arcade.check_for_collision_with_list(self.player, self.exit) and self.f_lever:
            con = sqlite3.connect('Saves.sqlite')
            if self.map == 0:
                if (self.score > con.cursor().execute('''SELECT level_test_score FROM results WHERE player_name = ?''',
                                            [PLAYER_NAME,]).fetchone()[0]):
                    con.cursor().execute(f'''UPDATE results
                                    SET level_test_score = ?
                                    WHERE player_name = ?''', [self.score, str(PLAYER_NAME)])
                if (self.timer < con.cursor().execute('''SELECT level_test_score FROM results WHERE player_name = ?''',
                                            [PLAYER_NAME,]).fetchone()[0]):
                    con.cursor().execute(f'''UPDATE results
                                    SET level_test_time = ?
                                    WHERE player_name = ?''', [round(self.timer, 3), str(PLAYER_NAME)])
            elif self.map == 1:
                if (self.score > con.cursor().execute('''SELECT level_1_score FROM results WHERE player_name = ?''',
                                            [PLAYER_NAME,]).fetchone()[0]):
                    con.cursor().execute(f'''UPDATE results
                                    SET level_1_score = ?
                                    WHERE player_name = ?''', [self.score, PLAYER_NAME])
                if (self.timer < con.cursor().execute('''SELECT level_1_time FROM results WHERE player_name = ?''',
                                            [PLAYER_NAME,]).fetchone()[0]):
                    con.cursor().execute(f'''UPDATE results
                                    SET level_1_time = ?
                                    WHERE player_name = ?''', [round(self.timer, 3), PLAYER_NAME])
            elif self.map == 2:
                if (self.score > con.cursor().execute('''SELECT level_2_score FROM results WHERE player_name = ?''',
                                            [PLAYER_NAME,]).fetchone()[0]):
                    con.cursor().execute(f'''UPDATE results
                                                SET level_2_score = ?
                                                WHERE player_name = ?''', [self.score, PLAYER_NAME])
                if (self.timer < con.cursor().execute('''SELECT level_2_score FROM results WHERE player_name = ?''',
                                            [PLAYER_NAME, ]).fetchone()[0]):
                    con.cursor().execute(f'''UPDATE results
                                    SET level_2_time = ?
                                    WHERE player_name = ?''', [round(self.timer, 3), PLAYER_NAME])
            con.commit()
            con.close()
            WINDOW.show_view(Res_level(self.map, self.score, round(self.timer, 3)))

        if arcade.check_for_collision_with_list(self.player, self.hazards):
            # «Ау» -> респавн
            self.player.center_x, self.player.center_y = self.spawn_point
            self.player.change_x = self.player.change_y = 0
            self.time_since_ground = 999
            self.player.jumps_left = MAX_JUMPS
            self.player.extra_jumps = EXTRA_JUMPS
            if self.player.extra_lives == 0:
                self.player.lives -= 1
            else:
                self.player.extra_lives -= 1
            if self.player.lives == 0:
                self.player.lives = 3
                self.score = 0
                self.coins.clear()
                self.sprite_extra_lives.clear()
                tm = arcade.load_tilemap(MAPS[self.map], scaling=TILE_SCALING)
                self.coins = tm.sprite_lists["coins"]
                self.sprite_extra_lives = tm.sprite_lists['extra_lives']
        elif self.player.center_y < 0:
            # «Ау» -> респавн
            self.player.center_x, self.player.center_y = self.spawn_point
            self.player.change_x = self.player.change_y = 0
            self.time_since_ground = 999
            self.player.jumps_left = MAX_JUMPS
            self.player.extra_jumps = EXTRA_JUMPS


        # Камера — плавно к игроку и в рамках мира
        target = (self.player.center_x, self.player.center_y)
        cx, cy = self.world_camera.position
        smooth = (cx + (target[0] - cx) * CAMERA_LERP,
                  cy + (target[1] - cy) * CAMERA_LERP)

        half_w = self.world_camera.viewport_width / 2
        half_h = self.world_camera.viewport_height / 2
        # Ограничим, чтобы за края уровня не выглядывало небо
        world_w = 2000 ** 2  # Мы руками построили пол до x = 2000
        world_h = 900 ** 2
        cam_x = max(half_w, min(world_w - half_w, smooth[0]))
        cam_y = max(half_h, min(world_h - half_h, smooth[1]))

        self.world_camera.position = (cam_x, cam_y)
        self.gui_camera.position = (SCREEN_W / 2, SCREEN_H / 2)

        self.player.update(dt, on_ladder, grounded)

        # Обновим счёт
        self.text_score = arcade.Text(f"Счёт: {self.score}",
                                      16, SCREEN_H - 36, arcade.color.DARK_SLATE_GRAY,
                                      20, batch=self.batch)
        self.text_lives = arcade.Text(chr(9829) * self.player.lives, 16, SCREEN_H - 60, arcade.color.RED, 14, batch=self.batch)
        self.text_extra_lives = arcade.Text(chr(128153) * self.player.extra_lives, 16 + self.player.lives * 25,
                                            SCREEN_H - 60, arcade.color.BLUE, 14, batch=self.batch)
        self.text_timer = arcade.Text(f'{round(self.timer, 3)}', 16, SCREEN_H - 96,
                                      arcade.color.DARK_SLATE_GRAY, batch = self.batch)


def setup_game(width=1220, height=850, title="Аркадный Бегун"):
    game = Platformer(0)
    game.setup()
    return game


def main():
    # setup_game()
    WINDOW.show_view(Login())
    arcade.run()


if __name__ == "__main__":
    main()
arcade.stop_sound(PLAYER_MUSIC)
