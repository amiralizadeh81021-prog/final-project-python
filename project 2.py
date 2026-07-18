import tkinter as tk
from tkinter import ttk
import random
from collections import deque

GREEN_LIGHT_SECONDS = 4.0
YELLOW_LIGHT_SECONDS = 1.5
CAR_RELEASE_SECONDS = 0.7
CAR_SPAWN_CHANCE = 0.5
CROSS_SECONDS = 1.0


class Car:
    _id_counter = 1

    def __init__(self):
        self.id = Car._id_counter
        Car._id_counter += 1

class TrafficLight:

    COLORS = {
        "red": "#e74c3c",
        "yellow": "#f1c40f",
        "green": "#2ecc71",
    }

    def __init__(self):
        self.state = "red"

    def set_state(self, state: str):
        self.state = state

    @property
    def is_green(self):
        return self.state == "green"

    def color(self):
        return self.COLORS[self.state]

class Lane:
    def __init__(self, direction: str):
        self.direction = direction
        self.queue = deque()
        self.light = TrafficLight()
    def add_car(self):
        self.queue.append(Car())
    def release_car(self):
        if self.light.is_green and self.queue:
            return self.queue.popleft()
        return None
    def __len__(self):
        return len(self.queue)


class Intersection:

    DIRECTIONS = ["N", "S", "E", "W"]
    def __init__(self):
        self.lanes = {d: Lane(d) for d in self.DIRECTIONS}
    def add_random_car(self):
        direction = random.choice(self.DIRECTIONS)
        self.lanes[direction].add_car()

class Controller:
    def __init__(self, intersection: Intersection,
                 green_seconds: float = GREEN_LIGHT_SECONDS,
                 yellow_seconds: float = YELLOW_LIGHT_SECONDS,
                 release_interval: float = CAR_RELEASE_SECONDS):
        self.intersection = intersection
        self.green_seconds = green_seconds
        self.yellow_seconds = yellow_seconds
        self.release_interval = release_interval

        self.order = list(Intersection.DIRECTIONS)
        self.current_index = 0
        self.phase = "green"       
        self.phase_timer = 0.0
        self.release_timer = 0.0
        self.last_released_direction = None

        self._activate_current()

    def current_direction(self):
        return self.order[self.current_index]

    def _activate_current(self):
        current = self.current_direction()
        for direction, lane in self.intersection.lanes.items():
            if direction == current:
                lane.light.set_state(self.phase)  
            else:
                lane.light.set_state("red")

    def tick(self, dt: float):
        self.phase_timer += dt
        self.release_timer += dt
        self.last_released_direction = None

        if self.release_timer >= self.release_interval:
            self.release_timer = 0.0
            direction = self.current_direction()
            released_car = self.intersection.lanes[direction].release_car()
            if released_car:
                self.last_released_direction = direction
        if self.phase == "green" and self.phase_timer >= self.green_seconds:
            self.phase_timer = 0.0
            self.phase = "yellow"
            self._activate_current()
        elif self.phase == "yellow" and self.phase_timer >= self.yellow_seconds:
            self.phase_timer = 0.0
            self.phase = "green"
            self.current_index = (self.current_index + 1) % len(self.order)
            self._activate_current()

class SimulatorGUI:
    SIZE = 600
    CENTER = SIZE // 2
    ROAD_HALF_WIDTH = 50
    MAX_VISIBLE_CARS = 8
    STOP_MARGIN = 15
    CAR_GAP = 22
    FRAME_MS = 100
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Traffic Light Simulator")

        self.intersection = Intersection()
        self.controller = Controller(self.intersection)
        self.moving_cars = []
        controls = ttk.Frame(root, padding=(10, 10, 10, 0))
        controls.pack(fill="x")
        self.green_var = tk.DoubleVar(value=self.controller.green_seconds)
        self.yellow_var = tk.DoubleVar(value=self.controller.yellow_seconds)
        self._build_slider(controls, "زمان چراغ سبز (ثانیه):", self.green_var,
                            0.5, 15.0, self._on_green_change, row=0)
        self._build_slider(controls, "زمان چراغ زرد (ثانیه):", self.yellow_var,
                            0.2, 5.0, self._on_yellow_change, row=1)
        self.canvas = tk.Canvas(root, width=self.SIZE, height=self.SIZE, bg="#dfe6e9")
        self.canvas.pack(padx=10, pady=10)

        self._draw_roads()
        self._loop()
    def _build_slider(self, parent, label_text, variable, frm, to, on_change, row):
        label = ttk.Label(parent, text=label_text)
        label.grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        value_label = ttk.Label(parent, text=f"{variable.get():.1f}")
        value_label.grid(row=row, column=2, sticky="w", padx=(8, 0))

        def _wrapped(event=None):
            value_label.config(text=f"{variable.get():.1f}")
            on_change(variable.get())

        slider = ttk.Scale(parent, from_=frm, to=to, orient="horizontal",
                            variable=variable, command=_wrapped, length=220)
        slider.grid(row=row, column=1, sticky="ew")
        parent.columnconfigure(1, weight=1)
    def _on_green_change(self, value):
        self.controller.green_seconds = float(value)
    def _on_yellow_change(self, value):
        self.controller.yellow_seconds = float(value)
    def _draw_roads(self):
        c = self.canvas
        size, center, half = self.SIZE, self.CENTER, self.ROAD_HALF_WIDTH
        c.create_rectangle(center - half, 0, center + half, size, fill="#636e72", outline="")
        c.create_rectangle(0, center - half, size, center + half, fill="#636e72", outline="")
        c.create_line(center, 0, center, size, fill="white", dash=(6, 6))
        c.create_line(0, center, size, center, fill="white", dash=(6, 6))

    def _loop(self):
        dt = self.FRAME_MS / 1000.0

        if random.random() < CAR_SPAWN_CHANCE * dt * 2:
            self.intersection.add_random_car()
        self.controller.tick(dt)
        if self.controller.last_released_direction:
            self.moving_cars.append({
                "direction": self.controller.last_released_direction,
                "progress": 0.0,
            })
        step = dt / CROSS_SECONDS
        for car in self.moving_cars:
            car["progress"] += step
        self.moving_cars = [c for c in self.moving_cars if c["progress"] < 1.0]
        self._render()
        self.root.after(self.FRAME_MS, self._loop)

    def _render(self):
        c = self.canvas
        c.delete("dynamic")
        center, half = self.CENTER, self.ROAD_HALF_WIDTH
        light_pos = {
            "N": (center - half - 22, center - half - 22),
            "S": (center + half + 22, center + half + 22),
            "E": (center + half + 22, center - half - 22),
            "W": (center - half - 22, center + half + 22),
        }

        for direction, lane in self.intersection.lanes.items():
            x, y = light_pos[direction]
            c.create_oval(x - 12, y - 12, x + 12, y + 12,
                          fill=lane.light.color(), outline="black", width=2, tags="dynamic")
            c.create_text(x, y - 22, text=direction, font=("Tahoma", 10, "bold"), tags="dynamic")

            count = min(len(lane), self.MAX_VISIBLE_CARS)
            for i in range(count):
                self._draw_queued_car(direction, i)
        for car in self.moving_cars:
            self._draw_crossing_car(car["direction"], car["progress"])
    def _stop_line_point(self, direction):
        center, half, margin = self.CENTER, self.ROAD_HALF_WIDTH, self.STOP_MARGIN
        if direction == "N":
            return center - half // 2, center - half - margin
        if direction == "S":
            return center + half // 2, center + half + margin
        if direction == "E":
            return center + half + margin, center - half // 2
        if direction == "W":
            return center - half - margin, center + half // 2

    def _draw_queued_car(self, direction, index):
        c = self.canvas
        w, h = 18, 12
        sx, sy = self._stop_line_point(direction)
        if direction == "N":
            x, y = sx, sy - index * self.CAR_GAP
        elif direction == "S":
            x, y = sx, sy + index * self.CAR_GAP
        elif direction == "E":
            x, y = sx + index * self.CAR_GAP, sy
        else:
            x, y = sx - index * self.CAR_GAP, sy
        colors = {"N": "#0984e3", "S": "#e17055", "E": "#00b894", "W": "#6c5ce7"}
        if direction in ("N", "S"):
            c.create_rectangle(x - w // 2, y - h // 2, x + w // 2, y + h // 2,
                                fill=colors[direction], tags="dynamic")
        else:
            c.create_rectangle(x - h // 2, y - w // 2, x + h // 2, y + w // 2,
                                fill=colors[direction], tags="dynamic")

    def _crossing_path(self, direction):
        center, half, margin = self.CENTER, self.ROAD_HALF_WIDTH, self.STOP_MARGIN
        edge = 20
        if direction == "N":
            x = center - half // 2
            return (x, center - half - margin), (x, self.SIZE - edge)
        if direction == "S":
            x = center + half // 2
            return (x, center + half + margin), (x, edge)
        if direction == "E":
            y = center - half // 2
            return (center + half + margin, y), (edge, y)
        y = center + half // 2
        return (center - half - margin, y), (self.SIZE - edge, y)

    def _draw_crossing_car(self, direction, progress):
        c = self.canvas
        w, h = 18, 12
        (x1, y1), (x2, y2) = self._crossing_path(direction)
        x = x1 + (x2 - x1) * progress
        y = y1 + (y2 - y1) * progress
        colors = {"N": "#0984e3", "S": "#e17055", "E": "#00b894", "W": "#6c5ce7"}
        if direction in ("N", "S"):
            c.create_rectangle(x - w // 2, y - h // 2, x + w // 2, y + h // 2,
                                fill=colors[direction], tags="dynamic")
        else:
            c.create_rectangle(x - h // 2, y - w // 2, x + h // 2, y + w // 2,
                                fill=colors[direction], tags="dynamic")

def main():
    root = tk.Tk()
    SimulatorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()