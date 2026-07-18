from __future__ import annotations
import random
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
import tkinter as tk
from tkinter import ttk, messagebox

class Direction(Enum):
    UP = auto()
    DOWN = auto()
    IDLE = auto()
class ElevatorState(Enum):
    IDLE = auto()
    MOVING = auto()
    DOOR_OPEN = auto()

@dataclass
class Person:
    _id_counter = 1
    origin_floor: int
    destination_floor: int
    request_time: float
    id: int = field(init=False)
    board_time: Optional[float] = None
    arrival_time: Optional[float] = None
    def __post_init__(self):
        self.id = Person._id_counter
        Person._id_counter += 1
    @property
    def direction(self) -> Direction:
        return Direction.UP if self.destination_floor > self.origin_floor else Direction.DOWN

    @property
    def wait_time(self) -> Optional[float]:
        if self.board_time is None:
            return None
        return self.board_time - self.request_time

    @property
    def travel_time(self) -> Optional[float]:
        if self.arrival_time is None or self.board_time is None:
            return None
        return self.arrival_time - self.board_time

class Floor:
    def __init__(self, number: int):
        self.number = number
        self.waiting_up: deque[Person] = deque()
        self.waiting_down: deque[Person] = deque()
    def add_person(self, person: Person) -> None:
        queue = self.waiting_up if person.direction == Direction.UP else self.waiting_down
        queue.append(person)
    def pop_waiting(self, direction: Direction) -> Optional[Person]:
        queue = self.waiting_up if direction == Direction.UP else self.waiting_down
        return queue.popleft() if queue else None
    @property
    def up_call(self) -> bool:
        return len(self.waiting_up) > 0
    @property
    def down_call(self) -> bool:
        return len(self.waiting_down) > 0
    def __len__(self) -> int:
        return len(self.waiting_up) + len(self.waiting_down)

class Elevator:
    def __init__(self, num_floors: int, capacity: int = 8,
                 speed_floors_per_sec: float = 1.6, dwell_time: float = 1.2):
        self.num_floors = num_floors
        self.capacity = capacity
        self.speed = speed_floors_per_sec
        self.dwell_time = dwell_time

        self.current_floor: float = 1.0
        self.direction: Direction = Direction.IDLE
        self.state: ElevatorState = ElevatorState.IDLE
        self.passengers: list[Person] = []
        self.target_floors: set[int] = set()
        self.door_timer: float = 0.0
    def has_capacity(self) -> bool:
        return len(self.passengers) < self.capacity
    def add_target(self, floor: int) -> None:
        self.target_floors.add(floor)
    def _nearest_target_in_direction(self, direction: Direction) -> Optional[int]:
        if direction == Direction.UP:
            candidates = [f for f in self.target_floors if f >= self.current_floor]
            return min(candidates) if candidates else None
        if direction == Direction.DOWN:
            candidates = [f for f in self.target_floors if f <= self.current_floor]
            return max(candidates) if candidates else None
        return None
    def _decide_direction(self) -> Direction:
        ups = [f for f in self.target_floors if f > self.current_floor]
        downs = [f for f in self.target_floors if f < self.current_floor]

        if self.direction == Direction.UP and ups:
            return Direction.UP
        if self.direction == Direction.DOWN and downs:
            return Direction.DOWN

        if ups and downs:
            return Direction.UP if (min(ups) - self.current_floor) <= (self.current_floor - max(downs)) else Direction.DOWN
        if ups:
            return Direction.UP
        if downs:
            return Direction.DOWN
        return Direction.IDLE
    def advance(self, dt: float) -> Optional[int]:
        if self.state == ElevatorState.MOVING:
            target = self._nearest_target_in_direction(self.direction)
            if target is None:
                self.state = ElevatorState.IDLE
                self.direction = Direction.IDLE
                return None
            step = self.speed * dt
            if self.direction == Direction.UP:
                self.current_floor = min(self.current_floor + step, target)
                reached = self.current_floor >= target
            else:
                self.current_floor = max(self.current_floor - step, target)
                reached = self.current_floor <= target
            if reached:
                self.current_floor = float(target)
                self.target_floors.discard(target)
                self.state = ElevatorState.DOOR_OPEN
                self.door_timer = 0.0
                return target
            return None
        if self.state == ElevatorState.DOOR_OPEN:
            self.door_timer += dt
            if self.door_timer >= self.dwell_time:
                if self.target_floors:
                    self.direction = self._decide_direction()
                    self.state = ElevatorState.MOVING
                else:
                    self.direction = Direction.IDLE
                    self.state = ElevatorState.IDLE
            return None
        if self.target_floors:
            self.direction = self._decide_direction()
            self.state = ElevatorState.MOVING
        return None

class Controller:
    def __init__(self, elevator: Elevator, floors: dict[int, Floor]):
        self.elevator = elevator
        self.floors = floors
        self.completed: list[Person] = []

    def request_pickup(self, origin: int, destination: int, clock: float) -> Person:
        person = Person(origin_floor=origin, destination_floor=destination, request_time=clock)
        self.floors[origin].add_person(person)
        self.elevator.add_target(origin)
        return person

    def tick(self, dt: float, clock: float) -> list[str]:
        arrived_floor = self.elevator.advance(dt)
        if arrived_floor is None:
            return []
        return self._handle_arrival(arrived_floor, clock)

    def _handle_arrival(self, floor: int, clock: float) -> list[str]:
        messages = []
        exiting = [p for p in self.elevator.passengers if p.destination_floor == floor]
        for person in exiting:
            person.arrival_time = clock
            self.elevator.passengers.remove(person)
            self.completed.append(person)
            messages.append(f"Person #{person.id} exited at floor {floor}")
        floor_obj = self.floors[floor]
        serve_direction = self.elevator.direction
        if serve_direction == Direction.IDLE:
            if floor_obj.up_call:
                serve_direction = Direction.UP
            elif floor_obj.down_call:
                serve_direction = Direction.DOWN
        boarded = 0
        while serve_direction != Direction.IDLE and self.elevator.has_capacity():
            person = floor_obj.pop_waiting(serve_direction)
            if person is None:
                break
            person.board_time = clock
            self.elevator.passengers.append(person)
            self.elevator.add_target(person.destination_floor)
            boarded += 1
            messages.append(f"Person #{person.id} boarded at floor {floor} -> {person.destination_floor}")
        if boarded and (floor_obj.up_call or floor_obj.down_call):
            messages.append(f"Elevator full at floor {floor}, some passengers still waiting")

        return messages

    @property
    def average_wait_time(self) -> Optional[float]:
        waits = [p.wait_time for p in self.completed if p.wait_time is not None]
        return sum(waits) / len(waits) if waits else None

class Building:
    def __init__(self, num_floors: int = 50, elevator_capacity: int = 8):
        self.num_floors = num_floors
        self.floors: dict[int, Floor] = {i: Floor(i) for i in range(1, num_floors + 1)}
        self.elevator = Elevator(num_floors=num_floors, capacity=elevator_capacity)
        self.controller = Controller(self.elevator, self.floors)
        self.clock: float = 0.0
    def request(self, origin: int, destination: int) -> Person:
        return self.controller.request_pickup(origin, destination, self.clock)
    def tick(self, dt: float) -> list[str]:
        self.clock += dt
        return self.controller.tick(dt, self.clock)
    @property
    def waiting_count(self) -> int:
        return sum(len(f) for f in self.floors.values())
    def random_request(self) -> Person:
        origin = random.randint(1, self.num_floors)
        destination = random.randint(1, self.num_floors)
        while destination == origin:
            destination = random.randint(1, self.num_floors)
        return self.request(origin, destination)

class ElevatorSimulatorGUI:
    FLOOR_HEIGHT = 12
    TOP_MARGIN = 20
    SHAFT_X0 = 110
    SHAFT_X1 = 180
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("شبیه‌ساز آسانسور هوشمند")
        self.root.geometry("1000x760")

        self.building = Building(num_floors=50, elevator_capacity=8)
        self.auto_spawn = tk.BooleanVar(value=False)
        self.auto_spawn_timer = 0.0
        self.speed_multiplier = tk.DoubleVar(value=1.0)

        self._build_layout()
        self._loop()
    def _build_layout(self):
        canvas_height = self.TOP_MARGIN * 2 + self.FLOOR_HEIGHT * self.building.num_floors
        self.canvas = tk.Canvas(self.root, width=220, height=canvas_height, bg="white")
        self.canvas.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self._draw_shaft()

        right_panel = ttk.Frame(self.root)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        request_frame = ttk.LabelFrame(right_panel, text="درخواست آسانسور", padding=10)
        request_frame.pack(fill=tk.X, pady=5)

        ttk.Label(request_frame, text="طبقه مبدا:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.origin_spin = ttk.Spinbox(request_frame, from_=1, to=self.building.num_floors, width=8)
        self.origin_spin.set(1)
        self.origin_spin.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(request_frame, text="طبقه مقصد:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.destination_spin = ttk.Spinbox(request_frame, from_=1, to=self.building.num_floors, width=8)
        self.destination_spin.set(10)
        self.destination_spin.grid(row=0, column=3, padx=5, pady=5)
        ttk.Button(request_frame, text="ثبت درخواست", command=self._on_request).grid(
            row=0, column=4, padx=10, pady=5)
        ttk.Button(request_frame, text="درخواست تصادفی", command=self._on_random_request).grid(
            row=0, column=5, padx=5, pady=5)
        ttk.Checkbutton(request_frame, text="تولید خودکار درخواست", variable=self.auto_spawn).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=5, pady=5)
        ttk.Label(request_frame, text="سرعت شبیه‌سازی:").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        ttk.Scale(request_frame, from_=0.5, to=5.0, variable=self.speed_multiplier,
                  orient=tk.HORIZONTAL, length=140).grid(row=1, column=3, columnspan=3, padx=5, pady=5)
        status_frame = ttk.LabelFrame(right_panel, text="وضعیت آسانسور", padding=10)
        status_frame.pack(fill=tk.X, pady=5)
        self.status_labels: dict[str, ttk.Label] = {}
        keys = ["طبقه فعلی", "جهت حرکت", "وضعیت", "مسافران", "منتظر در ساختمان",
                "درخواست‌های سرویس‌شده", "میانگین زمان انتظار"]
        for i, key in enumerate(keys):
            ttk.Label(status_frame, text=f"{key}:").grid(row=i // 2, column=(i % 2) * 2,
                                                           sticky="e", padx=5, pady=4)
            lbl = ttk.Label(status_frame, text="—", foreground="blue")
            lbl.grid(row=i // 2, column=(i % 2) * 2 + 1, sticky="w", padx=5, pady=4)
            self.status_labels[key] = lbl
        log_frame = ttk.LabelFrame(right_panel, text="گزارش رویدادها", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = tk.Text(log_frame, height=18, state="disabled", wrap="word")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    def _draw_shaft(self):
        self.canvas.delete("all")
        n = self.building.num_floors
        for f in range(1, n + 2):
            y = self.TOP_MARGIN + (n - f + 1) * self.FLOOR_HEIGHT
            self.canvas.create_line(self.SHAFT_X0, y, self.SHAFT_X1, y, fill="#dddddd")
        for f in range(1, n + 1, 5):
            y = self.TOP_MARGIN + (n - f + 0.5) * self.FLOOR_HEIGHT
            self.canvas.create_text(self.SHAFT_X0 - 15, y, text=str(f), font=("Segoe UI", 7))
        self.canvas.create_line(self.SHAFT_X0, self.TOP_MARGIN, self.SHAFT_X0,
                                 self.TOP_MARGIN + n * self.FLOOR_HEIGHT, fill="black")
        self.canvas.create_line(self.SHAFT_X1, self.TOP_MARGIN, self.SHAFT_X1,
                                 self.TOP_MARGIN + n * self.FLOOR_HEIGHT, fill="black")
    def _center_y(self, floor_value: float) -> float:
        n = self.building.num_floors
        return self.TOP_MARGIN + (n - floor_value + 0.5) * self.FLOOR_HEIGHT

    def _redraw(self):
        self._draw_shaft()
        n = self.building.num_floors
        for f, floor_obj in self.building.floors.items():
            y = self._center_y(f)
            if floor_obj.up_call:
                self.canvas.create_oval(self.SHAFT_X0 - 8, y - 3, self.SHAFT_X0 - 2, y + 3, fill="#2ecc71", outline="")
            if floor_obj.down_call:
                self.canvas.create_oval(self.SHAFT_X0 - 8, y + 3, self.SHAFT_X0 - 2, y + 9, fill="#e74c3c", outline="")
        elevator = self.building.elevator
        car_half = self.FLOOR_HEIGHT * 0.42
        y = self._center_y(elevator.current_floor)
        color = "#3498db" if elevator.state != ElevatorState.DOOR_OPEN else "#f1c40f"
        self.canvas.create_rectangle(self.SHAFT_X0 + 4, y - car_half, self.SHAFT_X1 - 4, y + car_half,
                                      fill=color, outline="black")
        self.canvas.create_text((self.SHAFT_X0 + self.SHAFT_X1) / 2, y,
                                 text=f"{round(elevator.current_floor)} | {len(elevator.passengers)}/{elevator.capacity}",
                                 font=("Segoe UI", 7, "bold"))
    def _on_canvas_click(self, event):
        n = self.building.num_floors
        floor = n - int((event.y - self.TOP_MARGIN) // self.FLOOR_HEIGHT)
        floor = max(1, min(n, floor))
        self.origin_spin.set(floor)

    def _on_request(self):
        try:
            origin = int(self.origin_spin.get())
            destination = int(self.destination_spin.get())
            if origin == destination:
                raise ValueError("طبقه مبدا و مقصد نباید یکسان باشند.")
            if not (1 <= origin <= self.building.num_floors) or not (1 <= destination <= self.building.num_floors):
                raise ValueError("طبقه باید بین ۱ تا ۵۰ باشد.")
        except ValueError as e:
            messagebox.showerror("خطای ورودی", str(e))
            return
        person = self.building.request(origin, destination)
        self._append_log(f"Person #{person.id} requested pickup at floor {origin} -> {destination}")

    def _on_random_request(self):
        person = self.building.random_request()
        self._append_log(f"Person #{person.id} requested pickup at floor "
                          f"{person.origin_floor} -> {person.destination_floor} (random)")

    def _append_log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _update_status_labels(self):
        elevator = self.building.elevator
        direction_text = {Direction.UP: "بالا", Direction.DOWN: "پایین", Direction.IDLE: "ثابت"}
        state_text = {ElevatorState.IDLE: "بی‌کار", ElevatorState.MOVING: "در حرکت", ElevatorState.DOOR_OPEN: "درب باز"}
        avg_wait = self.building.controller.average_wait_time

        self.status_labels["طبقه فعلی"].config(text=f"{elevator.current_floor:.1f}")
        self.status_labels["جهت حرکت"].config(text=direction_text[elevator.direction])
        self.status_labels["وضعیت"].config(text=state_text[elevator.state])
        self.status_labels["مسافران"].config(text=f"{len(elevator.passengers)}/{elevator.capacity}")
        self.status_labels["منتظر در ساختمان"].config(text=str(self.building.waiting_count))
        self.status_labels["درخواست‌های سرویس‌شده"].config(text=str(len(self.building.controller.completed)))
        self.status_labels["میانگین زمان انتظار"].config(
            text=f"{avg_wait:.2f} s" if avg_wait is not None else "—")
    def _loop(self):
        dt = 0.05 * self.speed_multiplier.get()
        messages = self.building.tick(dt)
        for message in messages:
            self._append_log(message)

        if self.auto_spawn.get():
            self.auto_spawn_timer += dt
            if self.auto_spawn_timer >= 4.0:
                self.auto_spawn_timer = 0.0
                self._on_random_request()
        self._redraw()
        self._update_status_labels()
        self.root.after(50, self._loop)
def main():
    root = tk.Tk()
    ElevatorSimulatorGUI(root)
    root.mainloop()
if __name__ == "__main__":
    main()