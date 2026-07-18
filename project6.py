import tkinter as tk
from tkinter import ttk
import random

class Card:
    def __init__(self, card_id, balance=20000):
        self.card_id = card_id
        self.balance = balance
        self.history = []

    def has_credit(self, cost=5000):
        return self.balance >= cost

    def charge(self, cost=5000):
        if self.has_credit(cost):
            self.balance -= cost
            self.history.append(f"کسر {cost} تومان (مانده: {self.balance})")
            return True
        return False

    def recharge(self, amount):
        self.balance += amount
        self.history.append(f"شارژ {amount} تومان (مانده: {self.balance})")

class Passenger:
    _next_id = 1

    def __init__(self, name, card=None):
        self.id = Passenger._next_id
        Passenger._next_id += 1
        self.name = name
        self.card = card

    def __str__(self):
        return f"{self.name} (کارت: {self.card.card_id})"

class Sensor:
    def __init__(self):
        self.passenger_detected = False

    def detect(self, is_present):
        self.passenger_detected = is_present
        return self.passenger_detected

class Motor:

    STATES = ("closed", "opening", "open", "closing")

    def __init__(self):
        self.state = "closed"

    def start_opening(self):
        self.state = "opening"

    def finish_opening(self):
        self.state = "open"

    def start_closing(self):
        self.state = "closing"

    def finish_closing(self):
        self.state = "closed"

    @property
    def is_open(self):
        return self.state == "open"

class Gate:
    ENTRY_COST = 5000

    def __init__(self):
        self.sensor = Sensor()
        self.motor = Motor()
        self.log = []

    def request_entry(self, passenger):
        if passenger.card is None:
            self._add_log(f"{passenger.name}: کارتی وجود ندارد - ورود رد شد")
            return False

        if not passenger.card.has_credit(self.ENTRY_COST):
            self._add_log(f"{passenger.name}: موجودی ناکافی - ورود رد شد")
            return False

        passenger.card.charge(self.ENTRY_COST)
        self.sensor.detect(True)
        self.motor.start_opening()
        self._add_log(f"{passenger.name}: ورود موفق")
        return True

    def request_exit(self, passenger):
        self.sensor.detect(True)
        self.motor.start_opening()
        self._add_log(f"{passenger.name}: خروج انجام شد")
        return True

    def close(self):
        self.sensor.detect(False)
        self.motor.start_closing()
        self._add_log("گیت بسته شد")

    def _add_log(self, text):
        self.log.append(text)

class GUI:
    LEFT_POST = (90, 20, 110, 180)
    RIGHT_POST = (290, 20, 310, 180)

    BAR_CLOSED = (110, 90, 290, 110)
    BAR_OPEN = (90, 90, 110, 110)

    ANIMATION_STEPS = 12
    ANIMATION_DELAY_MS = 30
    AUTO_CLOSE_DELAY_MS = 2500

    def __init__(self, root):
        self.root = root
        self.root.title("شبیه‌ساز گیت مترو")
        self.root.geometry("460x560")
        self.root.resizable(False, False)

        self.gate = Gate()
        self.passengers = []
        self._create_default_passengers()

        self._build_canvas()
        self._build_passenger_controls()
        self._build_action_buttons()
        self._build_log_area()

        self._auto_close_job = None
        self.refresh_all()

    def _create_default_passengers(self):
        for name in ("پارسا", "امیر", "علی"):
            balance = random.choice([0, 3000, 15000, 30000])
            card = Card(f"C-{1000 + len(self.passengers) + 1}", balance)
            self.passengers.append(Passenger(name, card))

    def _build_canvas(self):
        self.canvas = tk.Canvas(self.root, width=400, height=200, bg="white")
        self.canvas.pack(pady=10)

        self.canvas.create_rectangle(*self.LEFT_POST, fill="gray")
        self.canvas.create_rectangle(*self.RIGHT_POST, fill="gray")

        self.bar = self.canvas.create_rectangle(*self.BAR_CLOSED, fill="red")

        self.status_text = self.canvas.create_text(
            200, 10, text="وضعیت گیت: بسته", font=("Tahoma", 12)
        )

    def _build_passenger_controls(self):
        frame = tk.LabelFrame(self.root, text="انتخاب مسافر", padx=10, pady=10)
        frame.pack(pady=5, fill="x", padx=10)

        self.passenger_var = tk.StringVar()
        self.passenger_combo = ttk.Combobox(
            frame, textvariable=self.passenger_var, state="readonly", width=35
        )
        self.passenger_combo.grid(row=0, column=0, columnspan=2, pady=5)
        self.passenger_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_balance())

        tk.Button(frame, text="افزودن مسافر جدید", command=self.add_passenger).grid(
            row=1, column=0, padx=5, pady=5, sticky="ew"
        )
        tk.Button(frame, text="شارژ کارت (+10000)", command=self.recharge_card).grid(
            row=1, column=1, padx=5, pady=5, sticky="ew"
        )

        self.balance_label = tk.Label(frame, text="", font=("Tahoma", 10))
        self.balance_label.grid(row=2, column=0, columnspan=2, pady=5)

    def _build_action_buttons(self):
        frame = tk.Frame(self.root)
        frame.pack(pady=5)

        tk.Button(frame, text="ورود مسافر", width=15, command=self.handle_enter).grid(
            row=0, column=0, padx=5
        )
        tk.Button(frame, text="خروج مسافر", width=15, command=self.handle_exit).grid(
            row=0, column=1, padx=5
        )
        tk.Button(frame, text="بستن دستی گیت", width=32, command=self.handle_manual_close).grid(
            row=1, column=0, columnspan=2, pady=5
        )

        self.message_label = tk.Label(self.root, text="", fg="blue", font=("Tahoma", 10))
        self.message_label.pack(pady=5)

    def _build_log_area(self):
        frame = tk.LabelFrame(self.root, text="تاریخچه رویدادها", padx=5, pady=5)
        frame.pack(pady=5, fill="both", expand=True, padx=10)

        self.log_box = tk.Listbox(frame, height=10)
        self.log_box.pack(fill="both", expand=True)

    def refresh_all(self):
        self.passenger_combo["values"] = [str(p) for p in self.passengers]
        if self.passengers and not self.passenger_var.get():
            self.passenger_combo.current(0)
        self.refresh_balance()
        self.refresh_log()

    def refresh_balance(self):
        passenger = self.get_selected_passenger()
        if passenger:
            self.balance_label.config(
                text=f"موجودی کارت {passenger.name}: {passenger.card.balance} تومان"
            )

    def refresh_log(self):
        self.log_box.delete(0, tk.END)
        for entry in reversed(self.gate.log[-50:]):
            self.log_box.insert(tk.END, entry)

    def get_selected_passenger(self):
        index = self.passenger_combo.current()
        if index >= 0:
            return self.passengers[index]
        return None

    def add_passenger(self):
        name = f"مسافر-{len(self.passengers) + 1}"
        card = Card(f"C-{1000 + len(self.passengers) + 1}", balance=10000)
        passenger = Passenger(name, card)
        self.passengers.append(passenger)
        self.refresh_all()
        self.passenger_combo.set(str(passenger))
        self.message_label.config(text=f"{name} اضافه شد")

    def recharge_card(self):
        passenger = self.get_selected_passenger()
        if passenger:
            passenger.card.recharge(10000)
            self.message_label.config(text=f"کارت {passenger.name} شارژ شد")
            self.refresh_balance()

    def handle_enter(self):
        passenger = self.get_selected_passenger()
        if not passenger:
            return
        success = self.gate.request_entry(passenger)
        self.message_label.config(
            text=(f"{passenger.name}: ورود موفق" if success else f"{passenger.name}: ورود رد شد")
        )
        self.refresh_balance()
        self.refresh_log()
        if success:
            self.animate_open()

    def handle_exit(self):
        passenger = self.get_selected_passenger()
        if not passenger:
            return
        self.gate.request_exit(passenger)
        self.message_label.config(text=f"{passenger.name}: خروج انجام شد")
        self.refresh_log()
        self.animate_open()

    def handle_manual_close(self):
        self._cancel_auto_close()
        self.animate_close()

    def animate_open(self):
        self._cancel_auto_close()
        self.canvas.itemconfig(self.status_text, text="وضعیت گیت: در حال باز شدن", fill="orange")
        self._run_animation(closing=False, on_finish=self._after_open_finished)

    def animate_close(self):
        self.canvas.itemconfig(self.status_text, text="وضعیت گیت: در حال بسته شدن", fill="orange")
        self._run_animation(closing=True, on_finish=self._after_close_finished)

    def _run_animation(self, closing, on_finish, step=0):
        start = self.BAR_OPEN if closing else self.BAR_CLOSED
        end = self.BAR_CLOSED if closing else self.BAR_OPEN

        ratio = step / self.ANIMATION_STEPS
        bar_coords = self._interpolate(start, end, ratio)
        self.canvas.coords(self.bar, *bar_coords)

        if step < self.ANIMATION_STEPS:
            self.root.after(
                self.ANIMATION_DELAY_MS,
                lambda: self._run_animation(closing, on_finish, step + 1),
            )
        else:
            on_finish()
    @staticmethod
    def _interpolate(start, end, ratio):
        return tuple(s + (e - s) * ratio for s, e in zip(start, end))
    def _after_open_finished(self):
        self.gate.motor.finish_opening()
        self.canvas.itemconfig(self.status_text, text="وضعیت گیت: باز", fill="green")
        self._auto_close_job = self.root.after(self.AUTO_CLOSE_DELAY_MS, self.animate_close)
    def _after_close_finished(self):
        self.gate.motor.finish_closing()
        self.gate.sensor.detect(False)
        self.canvas.itemconfig(self.status_text, text="وضعیت گیت: بسته", fill="black")
    def _cancel_auto_close(self):
        if self._auto_close_job is not None:
            self.root.after_cancel(self._auto_close_job)
            self._auto_close_job = None

if __name__ == "__main__":
    root = tk.Tk()
    app = GUI(root)
    root.mainloop()