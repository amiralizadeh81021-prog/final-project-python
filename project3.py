from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Optional, List
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, messagebox

class Tank:
    def __init__(self, area: float, outlet_coeff: float, max_height: float,
                 initial_level: float = 0.0):
        if area <= 0:
            raise ValueError("Tank cross-sectional area must be positive.")
        if outlet_coeff < 0:
            raise ValueError("Outlet coefficient cannot be negative.")
        if max_height <= 0:
            raise ValueError("Maximum height must be positive.")
        self.area = area
        self.outlet_coeff = outlet_coeff
        self.max_height = max_height
        self.level = min(max(initial_level, 0.0), max_height)
    def outflow(self) -> float:
        """Natural outlet flow due to gravity (Torricelli's law)."""
        return self.outlet_coeff * np.sqrt(max(self.level, 0.0))
    def update(self, dt: float, qin: float, extra_outflow: float = 0.0) -> None:
        qout = self.outflow() + extra_outflow
        dh_dt = (qin - qout) / self.area
        self.level += dh_dt * dt
        self.level = min(max(self.level, 0.0), self.max_height)

class Pump:
    def __init__(self, max_flow: float):
        if max_flow <= 0:
            raise ValueError("Pump maximum flow rate must be positive.")
        self.max_flow = max_flow
        self.flow = 0.0

    def set_command(self, command: float) -> None:
        """command in [0,1] -> pump flow proportional."""
        command = min(max(command, 0.0), 1.0)
        self.flow = command * self.max_flow

class Sensor:
    def __init__(self, noise_std: float = 0.0):
        self.noise_std = max(noise_std, 0.0)

    def read(self, true_level: float) -> float:
        if self.noise_std == 0:
            return true_level
        return true_level + np.random.normal(0, self.noise_std)

class Controller:
    name = "Base"

    def __init__(self, setpoint: float):
        self.setpoint = setpoint

    def compute(self, measured_level: float, dt: float) -> float:
        raise NotImplementedError

    def reset(self) -> None:
        pass

class OnOffController(Controller):
    name = "On-Off"

    def __init__(self, setpoint: float, hysteresis: float = 0.2):
        super().__init__(setpoint)
        self.hysteresis = max(hysteresis, 0.0)
        self._state = 1  # 1 = on, 0 = off

    def compute(self, measured_level: float, dt: float) -> float:
        lower = self.setpoint - self.hysteresis / 2
        upper = self.setpoint + self.hysteresis / 2

        if measured_level < lower:
            self._state = 1
        elif measured_level > upper:
            self._state = 0
        return float(self._state)

    def reset(self) -> None:
        self._state = 1

class PIDController(Controller):
    name = "PID"

    def __init__(self, setpoint: float, Kp: float, Ki: float, Kd: float,
                 output_limits: tuple = (0.0, 1.0)):
        super().__init__(setpoint)
        self.Kp, self.Ki, self.Kd = Kp, Ki, Kd
        self.out_min, self.out_max = output_limits

        self._integral = 0.0
        self._prev_measurement: Optional[float] = None

    def compute(self, measured_level: float, dt: float) -> float:
        error = self.setpoint - measured_level
        tentative_integral = self._integral + error * dt

        if self._prev_measurement is None:
            derivative = 0.0
        else:
            derivative = -(measured_level - self._prev_measurement) / dt
        self._prev_measurement = measured_level

        output_unclamped = (self.Kp * error +
                            self.Ki * tentative_integral +
                            self.Kd * derivative)

        output = min(max(output_unclamped, self.out_min), self.out_max)
        if output == output_unclamped:
            self._integral = tentative_integral
        return output

    def reset(self) -> None:
        self._integral = 0.0
        self._prev_measurement = None

@dataclass
class SimulationResult:
    controller_name: str
    t: np.ndarray
    level: np.ndarray
    control_signal: np.ndarray
    setpoint: float

class Simulation:
    def __init__(self, tank: Tank, pump: Pump, sensor: Sensor, controller: Controller,
                 duration: float, dt: float,
                 disturbance_time: Optional[float] = None,
                 disturbance_flow: float = 0.0):
        self.tank = tank
        self.pump = pump
        self.sensor = sensor
        self.controller = controller
        self.duration = duration
        self.dt = dt
        self.disturbance_time = disturbance_time
        self.disturbance_flow = disturbance_flow

    def run(self) -> SimulationResult:
        self.controller.reset()

        steps = int(self.duration / self.dt)
        t_arr = np.zeros(steps)
        level_arr = np.zeros(steps)
        control_arr = np.zeros(steps)

        for i in range(steps):
            t = i * self.dt

            measured = self.sensor.read(self.tank.level)
            command = self.controller.compute(measured, self.dt)
            self.pump.set_command(command)

            extra_out = 0.0
            if self.disturbance_time is not None and t >= self.disturbance_time:
                extra_out = self.disturbance_flow

            self.tank.update(self.dt, self.pump.flow, extra_outflow=extra_out)

            t_arr[i] = t
            level_arr[i] = self.tank.level
            control_arr[i] = command

        return SimulationResult(
            controller_name=self.controller.name,
            t=t_arr,
            level=level_arr,
            control_signal=control_arr,
            setpoint=self.controller.setpoint,
        )

@dataclass
class PerformanceMetrics:
    controller_name: str
    rise_time: Optional[float]
    settling_time: Optional[float]
    overshoot_percent: float
    steady_state_error: float
    iae: float
    switch_count: int

class PerformanceAnalyzer:
    def __init__(self, result: SimulationResult, settling_tolerance: float = 0.02):
        self.result = result
        self.tol = settling_tolerance

    def analyze(self) -> PerformanceMetrics:
        t, y, sp = self.result.t, self.result.level, self.result.setpoint

        rise_time = self._rise_time(t, y, sp)
        settling_time = self._settling_time(t, y, sp)
        overshoot = self._overshoot(y, sp)
        steady_error = abs(sp - y[-1])
        iae = float(np.trapz(np.abs(sp - y), t))
        switches = self._switch_count(self.result.control_signal)

        return PerformanceMetrics(
            controller_name=self.result.controller_name,
            rise_time=rise_time,
            settling_time=settling_time,
            overshoot_percent=overshoot,
            steady_state_error=steady_error,
            iae=iae,
            switch_count=switches,
        )

    @staticmethod
    def _rise_time(t, y, sp) -> Optional[float]:
        low, high = 0.1 * sp, 0.9 * sp
        try:
            t_low = t[np.where(y >= low)[0][0]]
            t_high = t[np.where(y >= high)[0][0]]
            return float(t_high - t_low)
        except IndexError:
            return None

    def _settling_time(self, t, y, sp) -> Optional[float]:
        band = self.tol * abs(sp) if sp != 0 else self.tol
        outside = np.where(np.abs(y - sp) > band)[0]
        if len(outside) == 0:
            return float(t[0])
        last_outside = outside[-1]
        if last_outside + 1 >= len(t):
            return None
        return float(t[last_outside + 1])

    @staticmethod
    def _overshoot(y, sp) -> float:
        if sp == 0:
            return 0.0
        peak = np.max(y)
        return max((peak - sp) / sp * 100, 0.0)

    @staticmethod
    def _switch_count(control_signal: np.ndarray) -> int:
        diffs = np.diff(control_signal)
        return int(np.sum(np.abs(diffs) > 0.5))

class Plotter:
    def __init__(self, figsize=(8, 6)):
        self.fig, (self.ax_level, self.ax_control) = plt.subplots(
            2, 1, figsize=figsize, sharex=True, height_ratios=[2.5, 1]
        )
    def plot(self, results: List[SimulationResult],
             disturbance_time: Optional[float] = None):
        self.ax_level.clear()
        self.ax_control.clear()
        colors = ["#1f77b4", "#d62728", "#2ca02c"]
        for i, res in enumerate(results):
            color = colors[i % len(colors)]
            self.ax_level.plot(res.t, res.level, color=color, linewidth=2,
                               label=f"Water Level ({res.controller_name})")
            self.ax_control.step(res.t, res.control_signal, color=color,
                                 linewidth=1.2, where="post",
                                 label=f"Control Command ({res.controller_name})")
        if results:
            sp = results[0].setpoint
            self.ax_level.axhline(sp, color="gray", linestyle="--", linewidth=1,
                                   label=f"Setpoint = {sp:.2f}")
        if disturbance_time is not None:
            self.ax_level.axvline(disturbance_time, color="orange", linestyle=":",
                                   linewidth=1.5, label="Disturbance Moment")
            self.ax_control.axvline(disturbance_time, color="orange", linestyle=":",
                                     linewidth=1.5)
        self.ax_level.set_ylabel("Water Level (m)")
        self.ax_level.grid(True, alpha=0.3)
        self.ax_level.legend(loc="lower right", fontsize=8)
        self.ax_level.set_title("Tank Level Response and Control Signal")

        self.ax_control.set_ylabel("Pump Command")
        self.ax_control.set_xlabel("Time (s)")
        self.ax_control.set_ylim(-0.1, 1.1)
        self.ax_control.grid(True, alpha=0.3)
        self.ax_control.legend(loc="upper right", fontsize=8)

        self.fig.tight_layout()
        return self.fig

class TankControlGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Water Tank Level Control Simulation")
        self.root.geometry("1100x700")

        self.plotter = Plotter()
        self.canvas: Optional[FigureCanvasTkAgg] = None
        self._build_layout()
    def _build_layout(self):
        input_frame = ttk.LabelFrame(self.root, text="Parameters", padding=12)
        input_frame.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        row = 0
        def add_field(label, default, width=10):
            nonlocal row
            ttk.Label(input_frame, text=label).grid(row=row, column=0, sticky="w", pady=3)
            entry = ttk.Entry(input_frame, width=width)
            entry.insert(0, default)
            entry.grid(row=row, column=1, pady=3)
            row += 1
            return entry
        ttk.Label(input_frame, text="— Tank —", font=("", 9, "bold")).grid(row=row, column=0, columnspan=2, pady=(0, 4))
        row += 1
        self.area_entry = add_field("Cross-section Area (m²):", "1.0")
        self.outlet_entry = add_field("Outlet Coefficient c:", "0.5")
        self.maxh_entry = add_field("Max Height (m):", "5.0")
        self.init_level_entry = add_field("Initial Level (m):", "0.0")

        ttk.Label(input_frame, text="— Pump & Setpoint —", font=("", 9, "bold")).grid(row=row, column=0, columnspan=2, pady=(8, 4))
        row += 1
        self.maxflow_entry = add_field("Max Pump Flow (m³/s):", "1.0")
        self.setpoint_entry = add_field("Setpoint (m):", "2.0")

        ttk.Label(input_frame, text="— On-Off —", font=("", 9, "bold")).grid(row=row, column=0, columnspan=2, pady=(8, 4))
        row += 1
        self.hysteresis_entry = add_field("Hysteresis (m):", "0.2")

        ttk.Label(input_frame, text="— PID —", font=("", 9, "bold")).grid(row=row, column=0, columnspan=2, pady=(8, 4))
        row += 1
        self.kp_entry = add_field("Kp:", "2.0")
        self.ki_entry = add_field("Ki:", "0.5")
        self.kd_entry = add_field("Kd:", "0.1")

        ttk.Label(input_frame, text="— Simulation —", font=("", 9, "bold")).grid(row=row, column=0, columnspan=2, pady=(8, 4))
        row += 1
        self.duration_entry = add_field("Duration (s):", "60")
        self.dt_entry = add_field("Time step dt (s):", "0.05")

        self.disturb_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(input_frame, text="Add Disturbance (sudden draw-off)",
                        variable=self.disturb_var).grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 3))
        row += 1
        self.disturb_time_entry = add_field("Disturbance Time (s):", "30")
        self.disturb_flow_entry = add_field("Disturbance Flow (m³/s):", "0.5")

        ttk.Label(input_frame, text="— Run Mode —", font=("", 9, "bold")).grid(row=row, column=0, columnspan=2, pady=(8, 4))
        row += 1
        self.mode_var = tk.StringVar(value="compare")
        mode_frame = ttk.Frame(input_frame)
        mode_frame.grid(row=row, column=0, columnspan=2, pady=3)
        ttk.Radiobutton(mode_frame, text="On-Off", variable=self.mode_var, value="onoff").pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="PID", variable=self.mode_var, value="pid").pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="Compare Both", variable=self.mode_var, value="compare").pack(anchor="w")
        row += 1
        ttk.Button(input_frame, text="Run", command=self._on_run).grid(
            row=row, column=0, columnspan=2, pady=15)
        row += 1
        result_frame = ttk.LabelFrame(input_frame, text="Performance Results", padding=8)
        result_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        columns = ("metric", "onoff", "pid")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=6)
        self.tree.heading("metric", text="Metric")
        self.tree.heading("onoff", text="On-Off")
        self.tree.heading("pid", text="PID")
        self.tree.column("metric", width=110)
        self.tree.column("onoff", width=70, anchor="center")
        self.tree.column("pid", width=70, anchor="center")
        self.tree.pack()
        self.plot_frame = ttk.Frame(self.root)
        self.plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        self._embed_canvas()
    def _embed_canvas(self):
        self.canvas = FigureCanvasTkAgg(self.plotter.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas.draw()
    def _build_tank_pump_sensor(self):
        tank = Tank(
            area=float(self.area_entry.get()),
            outlet_coeff=float(self.outlet_entry.get()),
            max_height=float(self.maxh_entry.get()),
            initial_level=float(self.init_level_entry.get()),
        )
        pump = Pump(max_flow=float(self.maxflow_entry.get()))
        sensor = Sensor(noise_std=0.0)
        return tank, pump, sensor
    def _run_one(self, controller: Controller) -> SimulationResult:
        tank, pump, sensor = self._build_tank_pump_sensor()

        disturbance_time = None
        disturbance_flow = 0.0
        if self.disturb_var.get():
            disturbance_time = float(self.disturb_time_entry.get())
            disturbance_flow = float(self.disturb_flow_entry.get())
        sim = Simulation(
            tank=tank, pump=pump, sensor=sensor, controller=controller,
            duration=float(self.duration_entry.get()),
            dt=float(self.dt_entry.get()),
            disturbance_time=disturbance_time,
            disturbance_flow=disturbance_flow,
        )
        return sim.run()
    def _on_run(self):
        try:
            setpoint = float(self.setpoint_entry.get())
            mode = self.mode_var.get()
            results: List[SimulationResult] = []

            if mode in ("onoff", "compare"):
                onoff_ctrl = OnOffController(setpoint, hysteresis=float(self.hysteresis_entry.get()))
                results.append(self._run_one(onoff_ctrl))

            if mode in ("pid", "compare"):
                pid_ctrl = PIDController(
                    setpoint,
                    Kp=float(self.kp_entry.get()),
                    Ki=float(self.ki_entry.get()),
                    Kd=float(self.kd_entry.get()),
                )
                results.append(self._run_one(pid_ctrl))

            disturbance_time = float(self.disturb_time_entry.get()) if self.disturb_var.get() else None
            self.plotter.plot(results, disturbance_time=disturbance_time)
            self.canvas.draw()

            self._update_result_table(results)

        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred:\n{e}")

    def _update_result_table(self, results: List[SimulationResult]):
        for row in self.tree.get_children():
            self.tree.delete(row)

        metrics_by_name = {}
        for res in results:
            metrics_by_name[res.controller_name] = PerformanceAnalyzer(res).analyze()

        def fmt(m: Optional[PerformanceMetrics], attr: str) -> str:
            if m is None:
                return "—"
            val = getattr(m, attr)
            if val is None:
                return "—"
            if isinstance(val, float):
                return f"{val:.3f}"
            return str(val)
        onoff_m = metrics_by_name.get("On-Off")
        pid_m = metrics_by_name.get("PID")
        rows = [
            ("Rise Time (s)", "rise_time"),
            ("Settling Time (s)", "settling_time"),
            ("Overshoot (%)", "overshoot_percent"),
            ("Steady-State Error", "steady_state_error"),
            ("IAE", "iae"),
            ("Switch Count", "switch_count"),
        ]
        for label, attr in rows:
            self.tree.insert("", "end", values=(label, fmt(onoff_m, attr), fmt(pid_m, attr)))
def main():
    root = tk.Tk()
    app = TankControlGUI(root)
    root.mainloop()
if __name__ == "__main__":
    main()