import tkinter as tk
from tkinter import ttk
import pyautogui
import threading
from pynput import mouse
from pynput import keyboard
import cv2
import numpy as np
import time


class ColorDisplay(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, width=50, height=20, **kwargs)
        self.rect = self.create_rectangle(0, 0, 50, 20, fill='white')

    def set_color(self, color):
        if color is not None:
            # Convert BGR to RGB for display
            rgb_color = f'#{color[2]:02x}{color[1]:02x}{color[0]:02x}'
            self.itemconfig(self.rect, fill=rgb_color)
        else:
            self.itemconfig(self.rect, fill='white')


class AutomationBot:
    def __init__(self):
        self.config = {
            'player_coords': None,
            'npc_color': None,
            'scan_area': [(0, 0), (1920, 1080)],
            'tile_width': 64,
            'tile_height': 32,
            'color_tolerance': 30,
            'click_delay': 0.5,
            'attack_delay': 0.2,
            'hotkey': keyboard.Key.f6
        }
        self.bot_running = False
        self.selection_mode = None
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        self.keyboard_listener.start()

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

        self.setup_gui()

    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("Enhanced Bot")
        self.root.resizable(False, False)

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="5")
        settings_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Player position settings
        ttk.Label(settings_frame, text="Player Position:").grid(row=0, column=0, sticky="w")
        self.player_pos_label = ttk.Label(settings_frame, text="Click to set")
        self.player_pos_label.grid(row=0, column=1, sticky="w")
        ttk.Button(settings_frame, text="Set Position", command=self.start_position_selection).grid(row=0, column=2,
                                                                                                    padx=5)

        # NPC Color settings
        ttk.Label(settings_frame, text="NPC Color:").grid(row=1, column=0, sticky="w")
        self.color_display = ColorDisplay(settings_frame)
        self.color_display.grid(row=1, column=1, sticky="w")
        ttk.Button(settings_frame, text="Set Color", command=self.start_color_selection).grid(row=1, column=2, padx=5)

        # Color tolerance slider
        ttk.Label(settings_frame, text="Color Tolerance:").grid(row=2, column=0, sticky="w")
        self.tolerance_var = tk.IntVar(value=self.config['color_tolerance'])
        self.tolerance_slider = ttk.Scale(
            settings_frame,
            from_=1,
            to=100,
            orient="horizontal",
            variable=self.tolerance_var,
            command=self.update_tolerance
        )
        self.tolerance_slider.grid(row=2, column=1, sticky="ew")
        self.tolerance_label = ttk.Label(settings_frame, text=str(self.config['color_tolerance']))
        self.tolerance_label.grid(row=2, column=2)

        # Hotkey indicator
        hotkey_frame = ttk.Frame(settings_frame)
        hotkey_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=(5, 0))
        ttk.Label(hotkey_frame, text="Stop Hotkey: F6", font=('Arial', 9, 'bold')).pack(side="left")

        # Control frame
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="5")
        control_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.start_button = ttk.Button(control_frame, text="Start", command=self.start_bot)
        self.start_button.grid(row=0, column=0, padx=5)

        self.stop_button = ttk.Button(control_frame, text="Stop", command=self.stop_bot, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)

        self.status_label = ttk.Label(control_frame, text="Ready")
        self.status_label.grid(row=1, column=0, columnspan=2)

    def on_key_press(self, key):
        if key == self.config['hotkey'] and self.bot_running:
            self.root.after(0, self.stop_bot)

    def update_tolerance(self, *args):
        value = self.tolerance_var.get()
        self.config['color_tolerance'] = value
        self.tolerance_label.config(text=str(value))

    def find_color_location(self):
        screenshot = pyautogui.screenshot()
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        target_color = self.config['npc_color']

        lower_bound = np.array([max(0, c - self.config['color_tolerance']) for c in target_color])
        upper_bound = np.array([min(255, c + self.config['color_tolerance']) for c in target_color])
        mask = cv2.inRange(img, lower_bound, upper_bound)

        y_coords, x_coords = np.where(mask > 0)

        if len(x_coords) > 0 and len(y_coords) > 0:
            # Find the closest color match to the player
            player_x, player_y = self.config['player_coords']
            distances = [(x, y, ((x - player_x) ** 2 + (y - player_y) ** 2) ** 0.5)
                         for x, y in zip(x_coords, y_coords)]
            closest = min(distances, key=lambda x: x[2])
            return (closest[0], closest[1])
        return None

    def bot_loop(self):
        while self.bot_running:
            if not self.config['player_coords'] or not self.config['npc_color']:
                time.sleep(0.5)
                continue

            try:
                # Find the NPC color location
                npc_pos = self.find_color_location()
                if npc_pos:
                    npc_x, npc_y = npc_pos
                    player_x, player_y = self.config['player_coords']
                    tile_width = self.config['tile_width']
                    tile_height = self.config['tile_height']

                    # Calculate tile centers
                    npc_center_x = npc_x + (tile_width // 2)
                    npc_center_y = npc_y + (tile_height // 2)
                    player_tile_x = player_x // tile_width
                    player_tile_y = player_y // tile_height
                    npc_tile_x = npc_x // tile_width
                    npc_tile_y = npc_y // tile_height

                    # Check if the NPC is adjacent to the player (not diagonal)
                    is_adjacent = (
                            (abs(npc_tile_x - player_tile_x) == 1 and npc_tile_y == player_tile_y) or
                            (abs(npc_tile_y - player_tile_y) == 1 and npc_tile_x == player_tile_x)
                    )

                    if is_adjacent:
                        # Continue clicking the NPC until it's no longer found
                        while npc_pos:
                            print(f"Attacking color at: {npc_center_x}, {npc_center_y}")
                            pyautogui.click(npc_center_x, npc_center_y)
                            time.sleep(self.config['attack_delay'])

                            # Re-check if the NPC color is still present
                            npc_pos = self.find_color_location()  # Update to check if the color is still there
                    else:
                        # Move to the adjacent tile center
                        if npc_tile_x < player_tile_x:  # NPC is to the left
                            move_x = (npc_tile_x + 1) * tile_width + (tile_width // 2)
                            move_y = npc_center_y
                        elif npc_tile_x > player_tile_x:  # NPC is to the right
                            move_x = (npc_tile_x - 1) * tile_width + (tile_width // 2)
                            move_y = npc_center_y
                        elif npc_tile_y < player_tile_y:  # NPC is above
                            move_x = npc_center_x
                            move_y = (npc_tile_y + 1) * tile_height + (tile_height // 2)
                        elif npc_tile_y > player_tile_y:  # NPC is below
                            move_x = npc_center_x
                            move_y = (npc_tile_y - 1) * tile_height + (tile_height // 2)

                        print(f"Moving to tile center: {move_x}, {move_y}")
                        pyautogui.click(move_x, move_y)
                        time.sleep(5)
                else:
                    time.sleep(0.5)
            except Exception as e:
                print(f"Error in bot loop: {e}")
                time.sleep(0.5)

    def start_position_selection(self):
        self.selection_mode = 'position'
        self.status_label.config(text="Click to set player position.")
        threading.Thread(target=self.listen_for_click, daemon=True).start()

    def start_color_selection(self):
        self.selection_mode = 'color'
        self.status_label.config(text="Click to sample NPC color.")
        threading.Thread(target=self.listen_for_click, daemon=True).start()

    def listen_for_click(self):
        def on_click(x, y, button, pressed):
            if pressed:
                if self.selection_mode == 'position':
                    self.config['player_coords'] = (x, y)
                    self.player_pos_label.config(text=f"X: {x}, Y: {y}")
                    self.status_label.config(text="Player position set")
                elif self.selection_mode == 'color':
                    try:
                        # Take a screenshot and get the color at the clicked position
                        screenshot = pyautogui.screenshot()
                        # Convert PIL image to numpy array and BGR color space
                        img_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                        # Get color at clicked coordinates
                        color = img_np[y, x].tolist()  # Convert to list for JSON serialization
                        self.config['npc_color'] = color
                        # Update color display
                        self.color_display.set_color(color)
                        self.status_label.config(text=f"Color set: BGR={color}")
                    except Exception as e:
                        print(f"Error setting color: {e}")
                        self.status_label.config(text="Error setting color!")

                self.selection_mode = None
                return False

        with mouse.Listener(on_click=on_click) as listener:
            listener.join()

    def start_bot(self):
        if not self.config['player_coords'] or not self.config['npc_color']:
            self.status_label.config(text="Set position and color first!")
            return

        self.bot_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Bot running (F6 to stop)")
        threading.Thread(target=self.bot_loop, daemon=True).start()

    def stop_bot(self):
        self.bot_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="Bot stopped")

    def __del__(self):
        if hasattr(self, 'keyboard_listener'):
            self.keyboard_listener.stop()


if __name__ == "__main__":
    bot = AutomationBot()
    bot.root.mainloop()
