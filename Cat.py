import sys
import os
import random
import subprocess
import shutil
from ctypes import windll, Structure, c_long, byref
import importlib.util

# Ensure PyQt5 can load Qt DLLs and Windows platform plugins.
if os.name == 'nt':
    try:
        spec = importlib.util.find_spec('PyQt5')
        if spec and spec.origin:
            pyqt_root = os.path.dirname(spec.origin)
            for bin_path in [
                os.path.join(pyqt_root, 'Qt5', 'bin'),
                os.path.join(pyqt_root, 'Qt', 'bin'),
            ]:
                if os.path.isdir(bin_path):
                    try:
                        os.add_dll_directory(bin_path)
                    except Exception:
                        pass
                    break

            plugin_root = None
            platform_path = None
            for root_candidate in [
                os.path.join(pyqt_root, 'Qt5', 'plugins'),
                os.path.join(pyqt_root, 'Qt', 'plugins'),
            ]:
                if os.path.isdir(root_candidate):
                    plugin_root = root_candidate
                    break
            if plugin_root:
                platform_path = os.path.join(plugin_root, 'platforms')
                if os.path.isdir(platform_path):
                    os.environ['QT_PLUGIN_PATH'] = plugin_root
                    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = platform_path
    except Exception as e:
        print('Qt plugin path setup failed:', e, file=sys.stderr)

try:
    from PyQt5 import QtWidgets, QtGui, QtCore
except ModuleNotFoundError:
    print('PyQt5 is not installed. Install it with `pip install PyQt5`.', file=sys.stderr)
    raise

try:
    spec2 = importlib.util.find_spec('PyQt5')
    if spec2 and spec2.origin:
        pyqt_root2 = os.path.dirname(spec2.origin)
        for candidate in (os.path.join(pyqt_root2, 'Qt', 'plugins', 'platforms'), os.path.join(pyqt_root2, 'Qt5', 'plugins', 'platforms')):
            if os.path.isdir(candidate):
                try:
                    QtCore.QCoreApplication.addLibraryPath(candidate)
                except Exception:
                    pass
                break
except Exception:
    pass


class RECT(Structure):
    _fields_ = [('left', c_long), ('top', c_long), ('right', c_long), ('bottom', c_long)]


def get_work_area():
    """Return (left, top, right, bottom) of work area (area not covered by taskbar)."""
    rect = RECT()
    SPI_GETWORKAREA = 0x0030
    windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, byref(rect), 0)
    return rect.left, rect.top, rect.right, rect.bottom


class HappinessBar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFixedSize(18, 64)
        self.level = 75

    def set_level(self, value):
        self.level = max(0, min(100, int(value)))
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
        outer = self.rect().adjusted(0, 0, -1, -1)
        painter.setBrush(QtGui.QColor(220, 220, 220, 240))
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 1))
        painter.drawRect(outer)

        inner = outer.adjusted(2, 2, -2, -2)
        painter.setBrush(QtGui.QColor(30, 30, 30, 220))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(inner)

        fill_height = int(inner.height() * (self.level / 100.0))
        fill_rect = QtCore.QRect(
            inner.left(),
            inner.bottom() - fill_height,
            inner.width(),
            fill_height,
        )
        painter.setBrush(QtGui.QColor(255, 128, 182))
        painter.drawRect(fill_rect)

        if fill_height > 4:
            block_h = max(4, inner.height() // 10)
            for y in range(inner.bottom() - fill_height, inner.bottom(), block_h + 1):
                block = QtCore.QRect(inner.left() + 1, y, inner.width() - 2, min(block_h, inner.bottom() - y))
                painter.setBrush(QtGui.QColor(255, 180, 210))
                painter.drawRect(block)
        painter.end()


class CatWindow(QtWidgets.QLabel):
    def __init__(self, gifs_path="gif"):
        super().__init__(None)
        self.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.gifs_path = os.path.join(os.path.dirname(__file__), gifs_path)
        self.speeds = {
            "idle": 75,
            "win_cheer": 70,
            "spin": 70,
            "walk": 70,
            "run": 95,
            "jump": 85,
            "fall": 80,
            "attack": 90,
            "click": 70,
            "pet": 70,
        }

        self.movies = {}
        for name in ["idle", "win_cheer", "spin", "walk", "run", "jump", "fall", "attack"]:
            if not os.path.exists(self.gifs_path):
                continue
            candidates = [f for f in os.listdir(self.gifs_path) if name in f.lower()]
            if not candidates:
                continue

            left_file = None
            right_file = None
            for f in candidates:
                lf = f.lower()
                if "left" in lf or "_l" in lf or "-l" in lf or "l.ft" in lf:
                    left_file = f
                else:
                    right_file = f if right_file is None else right_file

            if not right_file and candidates:
                right_file = candidates[0]

            entry = {}
            if right_file:
                path = os.path.join(self.gifs_path, right_file)
                m = QtGui.QMovie(path)
                m.setCacheMode(QtGui.QMovie.CacheAll)
                m.setSpeed(self.speeds.get(name, 75))
                entry['right'] = m
            if left_file:
                path = os.path.join(self.gifs_path, left_file)
                m = QtGui.QMovie(path)
                m.setCacheMode(QtGui.QMovie.CacheAll)
                m.setSpeed(self.speeds.get(name, 75))
                entry['left'] = m

            if 'left' in entry and 'right' in entry:
                self.movies[name] = entry
            else:
                self.movies[name] = entry.get('right') or entry.get('left')

        self.current_movie = None
        self.current_movie_side = 'right'
        self.flip = False

        self.click_animation_name = "pet"
        if "pet" not in self.movies:
            self.click_animation_name = "win_cheer"

        self.margin = 8
        self.scale = 1.8

        # Physics
        self.vx = 0.0
        self.vy = 0.0
        self.gravity = 1400.0
        self.max_speed = 360.0
        self.friction = 1200.0

        self.state = "idle"
        self.state_timer = 0.0
        self.spin_duration = 0.0
        self.click_effect_duration = 0.0
        self.click_effect_active = False

        self.chase_mode = False  # Chế độ rượt đuổi con trỏ chuột

        self.happiness = 75
        self.happiness_bar = HappinessBar()
        self.happiness_bar.set_level(self.happiness)
        self.happiness_bar.hide()
        self.bar_visibility_timer = 0.0

        self.jump_to_edge = False
        self.jump_edge_direction = 1

        self.app_open_timer = 0.0
        self.opening_app = False
        self.open_app_target = None
        self.open_app_position = None
        self.app_commands = [
            ["notepad.exe"],
            ["calc.exe"],
            ["mspaint.exe"],
        ]

        self.timing_misses = 0
        self.timing_meter = 0.0
        self.timing_direction = 1
        self.timing_target_start = 0.3
        self.timing_target_width = 0.2

        self.mouse_jump_timer = 0.0

        self.dragging = False
        self.mouse_pressed = False
        self.drag_offset = QtCore.QPoint(0, 0)
        self.press_pos = QtCore.QPoint(0, 0)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.tick)
        self.last_time = QtCore.QTime.currentTime()
        self.timer.start(16)

        self.choose_start_position()
        self.show_idle()

    def choose_start_position(self):
        left, top, right, bottom = get_work_area()
        w, h = 96, 96
        x = right - w - self.margin
        y = bottom - h - self.margin
        self.setGeometry(int(x), int(y), w, h)

    def setup_tray(self, icon_filename="tray_icon.png"):
        try:
            icon_path = os.path.join(os.path.dirname(__file__), icon_filename)
            if os.path.exists(icon_path):
                tray_icon = QtGui.QIcon(icon_path)
            else:
                pm = self.pixmap()
                tray_icon = QtGui.QIcon(pm) if pm is not None else QtGui.QIcon()

            self.tray_menu = QtWidgets.QMenu()
            self._show_action = self.tray_menu.addAction("Show Cat")
            
            # --- THÊM NÚT CHASE VÀO TRONG MENU KHAY HỆ THỐNG ---
            self._chase_action = self.tray_menu.addAction("Chase Mouse")
            self._chase_action.setCheckable(True)
            self._chase_action.triggered.connect(self.toggle_chase)
            # ----------------------------------------------------

            self._exit_action = self.tray_menu.addAction("Exit")
            self._show_action.triggered.connect(self.toggle_visible)
            self._exit_action.triggered.connect(self.exit_app)

            self.tray = QtWidgets.QSystemTrayIcon(tray_icon, parent=None)
            self.tray.setToolTip("Desktop Cat")
            self.tray.activated.connect(self.on_tray_activated)
            self.tray.show()
        except Exception:
            pass

    def toggle_chase(self, checked):
        """Bật / Tắt chế độ rượt đuổi con trỏ chuột"""
        self.chase_mode = checked
        if not self.chase_mode:
            self.show_idle()

    def on_tray_activated(self, reason):
        try:
            if reason == QtWidgets.QSystemTrayIcon.Trigger:
                self.tray_menu.exec_(QtGui.QCursor.pos())
        except Exception:
            pass

    def toggle_visible(self):
        try:
            if self.isVisible():
                self.hide()
                self._show_action.setText("Show Cat")
            else:
                self.show()
                self._show_action.setText("Hide Cat")
        except Exception:
            pass

    def exit_app(self):
        try:
            try:
                self.happiness_bar.hide()
            except Exception:
                pass
            try:
                if hasattr(self, 'tray'):
                    self.tray.hide()
            except Exception:
                pass
            QtWidgets.QApplication.quit()
        except Exception:
            os._exit(0)

    def play_movie(self, name, flip=False):
        entry = self.movies.get(name)
        if not entry:
            return

        if isinstance(entry, dict):
            side = 'left' if flip and 'left' in entry else 'right'
            movie = entry.get(side)
            self.current_movie_side = side
        else:
            movie = entry
            self.current_movie_side = 'right'

        if not movie:
            return

        if self.current_movie is movie:
            self.flip = flip and self.current_movie_side == 'right'
            return

        if self.current_movie:
            try:
                self.current_movie.frameChanged.disconnect(self.on_frame_changed)
            except Exception:
                pass
            try:
                self.current_movie.stop()
            except Exception:
                pass

        self.current_movie = movie
        self.flip = flip and self.current_movie_side == 'right'
        movie.frameChanged.connect(self.on_frame_changed)
        movie.start()

        pix = movie.currentPixmap()
        if not pix.isNull():
            if self.flip:
                pix = pix.transformed(QtGui.QTransform().scale(-1, 1))
            if self.scale != 1.0:
                pix = pix.scaled(int(pix.width() * self.scale), int(pix.height() * self.scale), QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
            self.setPixmap(pix)
            self.resize(pix.size())

    def position_happiness_bar(self, x, y, w, h):
        left, top, right, bottom = get_work_area()
        bar_x = x - self.happiness_bar.width() - 12
        if bar_x < left + self.margin:
            bar_x = x + w + 12
        bar_y = y + (h - self.happiness_bar.height()) // 2
        bar_y = max(top + self.margin, min(bar_y, bottom - self.happiness_bar.height() - self.margin))
        self.happiness_bar.move(int(bar_x), int(bar_y))

    def adjust_happiness(self, delta):
        old = self.happiness
        self.happiness = max(0, min(100, self.happiness + delta))
        if int(self.happiness) != int(old):
            self.happiness_bar.set_level(self.happiness)

    def on_frame_changed(self, _frame):
        if not self.current_movie:
            return
        pix = self.current_movie.currentPixmap()
        if pix.isNull():
            return
        if self.flip and self.current_movie_side == 'right':
            pix = pix.transformed(QtGui.QTransform().scale(-1, 1))
        if self.scale != 1.0:
            pix = pix.scaled(int(pix.width() * self.scale), int(pix.height() * self.scale), QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.setPixmap(pix)
        if self.width() != pix.width() or self.height() != pix.height():
            self.resize(pix.size())

    def show_idle(self):
        self.state = "idle"
        self.vx = 0
        self.play_movie("idle", flip=self.flip)

    def show_spin(self):
        self.state = "spin"
        self.state_timer = 0
        self.spin_duration = random.uniform(2.0, 3.5)
        self.vx = 0
        self.play_movie("spin", flip=self.flip)

    def show_win_cheer(self):
        self.state = "win_cheer"
        self.state_timer = 0
        self.vx = 0
        self.play_movie("win_cheer", flip=self.flip)

    def start_attack(self, direction=-1):
        self.state = "attack"
        self.state_timer = 0
        self.vx = 0
        self.vy = 0
        self.play_movie("attack", flip=(direction < 0))

    def start_click_effect(self):
        self.state = "click_effect"
        self.state_timer = 0
        self.click_effect_active = True
        self.click_effect_duration = random.uniform(1.0, 2.0)
        self.vx = 0
        self.vy = 0
        self.bar_visibility_timer = 2.5
        self.happiness_bar.show()
        self.play_movie(self.click_animation_name, flip=self.flip)

    def start_mouse_jump(self, target_pos=None):
        self.state = "mouse_jump"
        self.state_timer = 0
        self.click_effect_active = True
        self.mouse_jump_timer = 3.0
        direction = random.choice([-1, 1])
        self.vx = 260 * direction
        self.vy = -680.0
        self.flip = direction < 0
        self.play_movie("jump", flip=self.flip)
        self.happiness_bar.show()
        self.bar_visibility_timer = 2.5
        self.setFocus()

    def start_jump(self, direction=-1, toward_edge=False):
        self.state = "jump"
        self.vy = -680.0
        self.vx = 220.0 * direction
        self.flip = direction < 0
        self.jump_to_edge = toward_edge
        self.jump_edge_direction = direction
        self.play_movie("jump", flip=(direction < 0))

    def start_timing_game(self):
        self.state = "timing_game"
        self.state_timer = 0
        self.timing_misses = 0
        self.reset_timing_bar()
        self.click_effect_active = True
        self.play_movie("attack", flip=self.flip)
        self.happiness_bar.show()
        self.setFocus()

    def reset_timing_bar(self):
        self.timing_meter = 0.0
        self.timing_direction = 1
        self.timing_target_start = random.uniform(0.2, 0.6)
        self.timing_target_width = 0.18

    def process_timing_press(self):
        if self.state != "timing_game":
            return
        hit_zone = self.timing_target_start <= self.timing_meter <= self.timing_target_start + self.timing_target_width
        self.click_effect_active = False
        self.happiness_bar.hide()
        if hit_zone:
            self.adjust_happiness(15)
            self.show_win_cheer()
        else:
            self.adjust_happiness(-15)
            self.show_idle()

    def start_walk(self, direction=-1):
        self.state = "walk"
        self.vx = 90 * direction
        self.flip = direction < 0
        self.play_movie("walk", flip=(direction < 0))

    def start_run(self, direction=-1):
        self.state = "run"
        self.vx = 200 * direction
        self.flip = direction < 0
        self.jump_to_edge = False
        self.play_movie("run", flip=(direction < 0))

    def start_open_app(self):
        left, top, right, bottom = get_work_area()
        self.state = "open_app"
        self.state_timer = 0
        self.opening_app = True
        self.open_app_target = random.choice(self.app_commands)
        self.setFocus()

        self.play_movie("run", flip=self.flip)
        w = max(self.width(), 1)
        h = max(self.height(), 1)

        min_x = left + self.margin
        max_x = right - w - self.margin
        target_y = bottom - h - self.margin
        if max_x <= min_x:
            target_x = min_x
        else:
            target_x = random.randint(int(min_x), int(max_x))
        self.open_app_position = (target_x, target_y)

        current_x = self.x()
        self.move(current_x, int(target_y))
        self.vy = 0

        dx = target_x - current_x
        if abs(dx) < 6:
            self.move(int(target_x), int(target_y))
            self.vx = 0
            self.opening_app = False
            self.app_open_timer = 1.2
            self.play_movie("idle", flip=self.flip)
        else:
            self.vx = 220 if dx > 0 else -220
            self.flip = dx < 0
            self.play_movie("run", flip=self.flip)

    def finish_open_app(self):
        if self.open_app_target:
            try:
                subprocess.Popen(self.open_app_target, shell=False)
            except Exception:
                pass
        self.opening_app = False
        self.open_app_target = None
        self.open_app_position = None
        self.show_idle()

    def start_fall(self):
        self.state = "fall"
        self.state_timer = 0
        self.vx = 0
        self.vy = 0
        self.play_movie("fall", flip=self.flip)

    def tick(self):
        if self.dragging:
            return

        now = QtCore.QTime.currentTime()
        dt = max(0.001, self.last_time.msecsTo(now) / 1000.0)
        self.last_time = now

        left, top, right, bottom = get_work_area()

        geom = self.geometry()
        w = geom.width()
        h = geom.height()

        ground_y = bottom - h - self.margin

        self.state_timer += dt

        if self.state == "mouse_jump":
            self.mouse_jump_timer -= dt
            if self.mouse_jump_timer <= 0:
                self.start_timing_game()
            self.position_happiness_bar(geom.x(), geom.y(), w, h)
            self.happiness_bar.show()
            return
        elif self.state == "timing_game":
            self.timing_meter += dt * 0.35 * self.timing_direction
            if self.timing_meter <= 0:
                self.timing_meter = 0
                self.timing_direction = 1
            elif self.timing_meter >= 1:
                self.timing_meter = 1
                self.timing_direction = -1
            self.position_happiness_bar(geom.x(), geom.y(), w, h)
            return
        elif self.state == "open_app":
            if self.open_app_position:
                target_x, target_y = self.open_app_position
                min_x = left + self.margin
                max_x = right - w - self.margin
                dx = target_x - geom.x()
                if abs(dx) < 6 and abs(geom.y() - target_y) < 6:
                    x = target_x
                    y = target_y
                    if self.opening_app:
                        self.opening_app = False
                        self.vx = 0
                        self.vy = 0
                        self.app_open_timer = 1.2
                        self.play_movie("idle", flip=self.flip)
                else:
                    self.vx = 220 if dx > 0 else -220
                    self.flip = dx < 0
                    x = geom.x() + self.vx * dt
                    y = target_y
                    x = max(min_x, min(x, max_x))
                    if (self.vx > 0 and x >= target_x) or (self.vx < 0 and x <= target_x):
                        x = target_x
                        self.vx = 0
                        if self.opening_app:
                            self.opening_app = False
                            self.app_open_timer = 1.2
                            self.play_movie("idle", flip=self.flip)
            else:
                x = geom.x()
                y = geom.y()
            self.move(int(x), int(y))
            self.position_happiness_bar(x, int(y), w, h)
            if self.app_open_timer > 0:
                self.app_open_timer -= dt
                if self.app_open_timer <= 0:
                    self.finish_open_app()
            return

        # --- CHẾ ĐỘ CHASE MOUSE ---
        if self.chase_mode and self.state not in ("jump", "fall", "click_effect"):
            mouse_pos = QtGui.QCursor.pos()
            cat_center_x = geom.x() + w // 2
            dx = mouse_pos.x() - cat_center_x

            if abs(dx) > 20:
                dir_choice = 1 if dx > 0 else -1
                if abs(dx) > 200:
                    if self.state != "run":
                        self.start_run(dir_choice)
                    else:
                        self.vx = 220 * dir_choice
                else:
                    if self.state != "walk":
                        self.start_walk(dir_choice)
                    else:
                        self.vx = 110 * dir_choice
            else:
                self.vx = 0
                if self.state != "idle":
                    self.show_idle()

        # Gravitational physics
        if self.state != "click_effect":
            self.vy += self.gravity * dt

        x = geom.x() + self.vx * dt
        y = geom.y() + self.vy * dt

        # Chuyển đổi trạng thái hành động ngẫu nhiên (chỉ chạy khi không bật Chase Mode)
        if not self.chase_mode:
            happiness_factor = self.happiness / 100.0
            if self.state == "idle":
                active_chance = 0.35 + 0.25 * happiness_factor
                idle_hold = 0.4 if self.happiness >= 50 else 0.8
                if self.state_timer > idle_hold:
                    if random.random() < active_chance:
                        self.state_timer = 0
                        action = random.choices(
                            ["walk", "run", "jump", "spin", "win_cheer", "idle"],
                            [0.25, 0.20, 0.25, 0.15, 0.10, 0.05]
                        )[0]
                        dir_choice = random.choice([-1, 1])
                        if action == "walk":
                            self.start_walk(dir_choice)
                        elif action == "run":
                            self.start_run(dir_choice)
                        elif action == "jump":
                            self.start_jump(dir_choice, toward_edge=False)
                        elif action == "spin":
                            self.show_spin()
                        elif action == "win_cheer":
                            self.show_win_cheer()
                    elif random.random() < 0.15:
                        self.state_timer = 0
                        self.show_idle()

            elif self.state in ("walk", "run"):
                jump_chance = 0.15 + 0.05 * happiness_factor
                open_app_chance = 0.01

                if self.state_timer > random.uniform(0.4, 0.9) and random.random() < jump_chance:
                    self.state_timer = 0
                    self.start_jump(-1 if self.flip else 1, toward_edge=False)
                elif self.state_timer > random.uniform(0.8, 1.5) and random.random() < open_app_chance:
                    self.state_timer = 0
                    self.start_open_app()
                elif self.state_timer > random.uniform(1.2, 2.8):
                    self.state_timer = 0
                    self.show_idle()

            elif self.state == "spin":
                if self.state_timer > self.spin_duration:
                    self.state_timer = 0
                    self.show_idle()
            elif self.state == "win_cheer":
                if self.state_timer > random.uniform(1.2, 2.0):
                    self.state_timer = 0
                    self.show_idle()
            elif self.state == "click_effect":
                if self.state_timer > self.click_effect_duration:
                    self.state_timer = 0
                    self.click_effect_active = False
                    self.show_idle()
                else:
                    self.adjust_happiness(8 * dt)
            elif self.state == "attack":
                if self.state_timer > 0.8:
                    self.state_timer = 0
                    self.show_idle()

        # Ma sát giảm tốc khi ở chế độ tự do
        if not self.chase_mode and self.state in ("idle", "walk"):
            if self.vx > 0:
                self.vx = max(0, self.vx - self.friction * dt)
            elif self.vx < 0:
                self.vx = min(0, self.vx + self.friction * dt)

        # Giới hạn tốc độ
        if self.vx > self.max_speed:
            self.vx = self.max_speed
        if self.vx < -self.max_speed:
            self.vx = -self.max_speed

        # Va chạm cạnh màn hình trái / phải
        if x < left + self.margin:
            x = left + self.margin
            if self.vx < 0:
                self.vx = 0
            if self.state in ("walk", "run") and not self.chase_mode:
                self.show_idle()
        if x + w > right - self.margin:
            x = right - w - self.margin
            if self.vx > 0:
                self.vx = 0
            if self.state in ("walk", "run") and not self.chase_mode:
                self.show_idle()

        self.position_happiness_bar(x, int(y), w, h)

        # Tiếp đất (Ground Collision)
        if y >= ground_y:
            y = ground_y
            self.vy = 0
            if self.state in ("jump", "fall"):
                self.show_idle()

        if self.state == "click_effect":
            self.adjust_happiness(2 * dt)
        elif self.state == "idle":
            self.adjust_happiness(-0.5 * dt)

        self.move(int(x), int(y))
        self.position_happiness_bar(x, int(y), w, h)

        if self.state not in ("mouse_jump", "timing_game") and self.bar_visibility_timer > 0:
            self.bar_visibility_timer -= dt
            if self.bar_visibility_timer <= 0:
                self.happiness_bar.hide()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.click_effect_active or self.state in ("mouse_jump", "timing_game"):
                return
            self.mouse_pressed = True
            self.dragging = False
            self.drag_offset = event.pos()
            self.press_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.mouse_pressed:
            if not self.dragging and (event.pos() - self.press_pos).manhattanLength() > 4:
                self.dragging = True
            if self.dragging:
                new_pos = self.mapToGlobal(event.pos() - self.drag_offset)
                left, top, right, bottom = get_work_area()
                w = self.width()
                h = self.height()
                x = max(left + self.margin, min(new_pos.x(), right - w - self.margin))
                y = max(top + self.margin, min(new_pos.y(), bottom - h - self.margin))
                self.move(x, y)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.click_effect_active:
                self.mouse_pressed = False
                self.dragging = False
                return

            was_dragging = self.dragging
            self.mouse_pressed = False
            self.dragging = False
            if was_dragging:
                global_pos = event.globalPos()
                x = global_pos.x() - self.width() // 2
                y = global_pos.y() - self.height() // 2
                left, top, right, bottom = get_work_area()
                x = max(left + self.margin, min(x, right - self.width() - self.margin))
                y = max(top + self.margin, min(y, bottom - self.height() - self.margin))
                self.move(x, y)
                if y < bottom - self.height() - self.margin:
                    self.start_fall()
                return

            self.start_timing_game()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space:
            self.process_timing_press()
        elif event.key() in (QtCore.Qt.Key_J, QtCore.Qt.Key_Up):
            self.start_jump(random.choice([-1, 1]))

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.state == "timing_game":
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
            bar = QtCore.QRect(8, self.height() - 20, self.width() - 16, 12)
            painter.fillRect(bar, QtGui.QColor(0, 0, 0, 180))
            target_rect = QtCore.QRect(
                bar.left() + int(bar.width() * self.timing_target_start),
                bar.top(),
                max(4, int(bar.width() * self.timing_target_width)),
                bar.height(),
            )
            painter.fillRect(target_rect, QtGui.QColor(120, 255, 120, 220))
            cursor_x = bar.left() + int(bar.width() * self.timing_meter)
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 2))
            painter.drawLine(cursor_x, bar.top(), cursor_x, bar.bottom())
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255)))
            painter.drawText(bar.adjusted(2, -18, 0, 0), QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, "SPACE")
            painter.end()


def main():
    app = QtWidgets.QApplication(sys.argv)
    cat = CatWindow(gifs_path="gif")
    cat.setup_tray()
    cat.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()