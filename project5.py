import tkinter as tk
import math

class Pendulum:
    def __init__(self, angle=0.05, angular_velocity=0.0, length=1.0, mass=0.3):
        self.angle = angle                    
        self.angular_velocity = angular_velocity
        self.length = length                    
        self.mass = mass                       
class Cart:
    def __init__(self, x=0.0, velocity=0.0, mass=1.0):
        self.x = x                           
        self.velocity = velocity
        self.mass = mass
class Controller:
    FORCE_MAGNITUDE = 12.0

    def __init__(self):
        self.manual_force = 0.0

    def apply_left(self):
        self.manual_force = -self.FORCE_MAGNITUDE

    def apply_right(self):
        self.manual_force = self.FORCE_MAGNITUDE

    def stop(self):
        self.manual_force = 0.0
class Simulation:
    GRAVITY = 9.8
    CART_FRICTION = 0.999
    ANGLE_LIMIT = math.radians(50)
    CART_LIMIT = 1.3   

    def __init__(self, cart, pendulum):
        self.cart = cart
        self.pendulum = pendulum
        self.game_over = False
        self.survival_time = 0.0

    def step(self, force, dt=0.02):
        if self.game_over:
            return

        M = self.cart.mass
        m = self.pendulum.mass
        l = self.pendulum.length
        g = self.GRAVITY
        theta = self.pendulum.angle
        theta_dot = self.pendulum.angular_velocity

        temp = (force + m * l * theta_dot ** 2 * math.sin(theta)) / (M + m)
        theta_acc = (g * math.sin(theta) - math.cos(theta) * temp) / (
            l * (4.0 / 3.0 - (m * math.cos(theta) ** 2) / (M + m))
        )
        x_acc = temp - (m * l * theta_acc * math.cos(theta)) / (M + m)
        self.cart.velocity += x_acc * dt
        self.cart.velocity *= self.CART_FRICTION
        self.cart.x += self.cart.velocity * dt
        self.pendulum.angular_velocity += theta_acc * dt
        self.pendulum.angle += self.pendulum.angular_velocity * dt
        self.survival_time += dt

        if abs(self.pendulum.angle) > self.ANGLE_LIMIT:
            self.game_over = True
        if abs(self.cart.x) > self.CART_LIMIT:
            self.game_over = True
class GUI:
    CART_WIDTH = 80
    CART_HEIGHT = 30
    CART_Y = 300
    CENTER_PX = 300
    PIXELS_PER_METER = 180
    DT = 0.02

    def __init__(self, root):
        self.root = root
        self.root.title("بازی تعادل پاندول ")
        self.root.geometry("600x460")
        self.root.resizable(False, False)

        self.best_time = 0.0
        self.paused = False

        self.canvas = tk.Canvas(root, width=600, height=350, bg="white")
        self.canvas.pack()

        self.info_label = tk.Label(root, text="", font=("Tahoma", 11))
        self.info_label.pack(pady=5)

        self._build_buttons()
        self._new_game()

        self.root.bind("<KeyPress-Left>", lambda e: self.controller.apply_left())
        self.root.bind("<KeyPress-Right>", lambda e: self.controller.apply_right())
        self.root.bind("<KeyRelease-Left>", lambda e: self.controller.stop())
        self.root.bind("<KeyRelease-Right>", lambda e: self.controller.stop())
        self.root.bind("<KeyPress-r>", lambda e: self._new_game())
        self.root.bind("<KeyPress-p>", lambda e: self._toggle_pause())

        self._loop()

    def _build_buttons(self):
        frame = tk.Frame(self.root)
        frame.pack(pady=5)

        tk.Button(frame, text=" ادامه (P)", width=16, command=self._toggle_pause).grid(
            row=0, column=0, padx=5
        )
        tk.Button(frame, text="شروع دوباره (R)", width=16, command=self._new_game).grid(
            row=0, column=1, padx=5
        )

    def _new_game(self):
        self.cart = Cart(x=0.0)
        self.pendulum = Pendulum(angle=0.05)
        self.controller = Controller()
        self.simulation = Simulation(self.cart, self.pendulum)
        self.paused = False

    def _toggle_pause(self):
        self.paused = not self.paused

    def _loop(self):
        if not self.simulation.game_over and not self.paused:
            self.simulation.step(self.controller.manual_force, self.DT)

            if self.simulation.survival_time > self.best_time:
                self.best_time = self.simulation.survival_time

        self._draw()
        self.root.after(20, self._loop)

    def _draw(self):
        self.canvas.delete("all")

        ground_y = self.CART_Y + self.CART_HEIGHT / 2
        self.canvas.create_line(0, ground_y, 600, ground_y, fill="black")

        cart_px = self.CENTER_PX + self.cart.x * self.PIXELS_PER_METER
        self.canvas.create_rectangle(
            cart_px - self.CART_WIDTH / 2, self.CART_Y - self.CART_HEIGHT / 2,
            cart_px + self.CART_WIDTH / 2, self.CART_Y + self.CART_HEIGHT / 2,
            fill="steelblue"
        )

        pivot_x = cart_px
        pivot_y = self.CART_Y - self.CART_HEIGHT / 2
        length_px = self.pendulum.length * self.PIXELS_PER_METER
        bob_x = pivot_x + length_px * math.sin(self.pendulum.angle)
        bob_y = pivot_y - length_px * math.cos(self.pendulum.angle)

        self.canvas.create_line(pivot_x, pivot_y, bob_x, bob_y, width=4, fill="black")
        self.canvas.create_oval(
            bob_x - 12, bob_y - 12, bob_x + 12, bob_y + 12, fill="red"
        )

        if self.simulation.game_over:
            self.canvas.create_text(
                300, 40, text="GAME OVER - Press R to restart",
                font=("Tahoma", 14), fill="red"
            )
        elif self.paused:
            self.canvas.create_text(
                300, 40, text="بازی مکث شده - کلید P یا دکمه را بزن",
                font=("Tahoma", 14), fill="gray"
            )
        self.info_label.config(
            text=(
                f"زمان تعادل: {self.simulation.survival_time:.1f} ثانیه   |   "
                f"رکورد: {self.best_time:.1f} ثانیه"
            )
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = GUI(root)
    root.mainloop()
