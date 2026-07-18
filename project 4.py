from __future__ import annotations
import numpy as np
from scipy import signal
from dataclasses import dataclass
from typing import Optional
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import tkinter as tk
from tkinter import ttk, messagebox

class TransferFunction:
    def __init__(self, order: int, K: float, wn: float, zeta: Optional[float] = None):
        self._validate_inputs(order, K, wn, zeta)

        self.order = order
        self.K = K
        self.wn = wn
        self.zeta = zeta
        self.num, self.den = self._build_coefficients()
    @staticmethod
    def _validate_inputs(order: int, K: float, wn: float, zeta: Optional[float]) -> None:
        if order not in (1, 2):
            raise ValueError("مرتبه سیستم باید 1 یا 2 باشد.")
        if wn <= 0:
            raise ValueError("wn باید عددی مثبت باشد.")
        if K == 0:
            raise ValueError("K نباید صفر باشد.")
        if order == 2:
            if zeta is None:
                raise ValueError("برای سیستم مرتبه دوم مقدار zeta الزامی است.")
            if zeta < 0:
                raise ValueError("zeta باید عددی نامنفی باشد.")

    def _build_coefficients(self):

        if self.order == 1:
            num = [self.K * self.wn]
            den = [1, self.wn]
        else:
            num = [self.K * self.wn ** 2]
            den = [1, 2 * self.zeta * self.wn, self.wn ** 2]
        return num, den

    def as_scipy_tf(self) -> signal.TransferFunction:
        return signal.TransferFunction(self.num, self.den)

    def describe(self) -> str:
        if self.order == 1:
            return f"G(s) = {self.K}*{self.wn} / (s + {self.wn})"
        return f"G(s) = {self.K}*{self.wn}^2 / (s^2 + 2*{self.zeta}*{self.wn}*s + {self.wn}^2)"

class StepResponse:
    def __init__(self, tf: TransferFunction, t_final: Optional[float] = None, num_points: int = 3000):
        self.tf = tf
        self.t_final = t_final if t_final is not None else self._estimate_t_final()
        self.num_points = num_points
        self.t, self.y = self._simulate()

    def _estimate_t_final(self) -> float:
        wn = self.tf.wn
        zeta = self.tf.zeta if self.tf.order == 2 else 1.0
        zeta = max(zeta, 0.05)  
        t_final = 8 / (zeta * wn)
        return max(t_final, 1.0)

    def _simulate(self):
        system = self.tf.as_scipy_tf()
        t_array = np.linspace(0, self.t_final, self.num_points)
        t_out, y_out = signal.step(system, T=t_array)
        return t_out, y_out

@dataclass
class AnalysisResult:
    final_value: float
    rise_time: Optional[float]
    settling_time: Optional[float]
    overshoot_percent: float
    peak_value: float
    peak_time: Optional[float]

class Analyzer:
    def __init__(self, step_response: StepResponse, settling_tolerance: float = 0.02):
        self.t = step_response.t
        self.y = step_response.y
        self.tol = settling_tolerance

    def analyze(self) -> AnalysisResult:
        final_value = self.y[-1]

        rise_time = self._compute_rise_time(final_value)
        settling_time = self._compute_settling_time(final_value)
        peak_value, peak_time = self._compute_peak()
        overshoot = self._compute_overshoot(final_value, peak_value)

        return AnalysisResult(
            final_value=final_value,
            rise_time=rise_time,
            settling_time=settling_time,
            overshoot_percent=overshoot,
            peak_value=peak_value,
            peak_time=peak_time,
        )
    def _compute_rise_time(self, final_value: float) -> Optional[float]:
        low, high = 0.1 * final_value, 0.9 * final_value

        try:
            t_low = self.t[np.where(self.y >= low)[0][0]]
            t_high = self.t[np.where(self.y >= high)[0][0]]
            return float(t_high - t_low)
        except IndexError:
            return None

    def _compute_settling_time(self, final_value: float) -> Optional[float]:

        band = self.tol * abs(final_value)
        outside_band = np.where(np.abs(self.y - final_value) > band)[0]

        if len(outside_band) == 0:
            return float(self.t[0])  

        last_outside_index = outside_band[-1]
        if last_outside_index + 1 >= len(self.t):
            return None  
        return float(self.t[last_outside_index + 1])
    def _compute_peak(self):
        peak_index = int(np.argmax(self.y))
        return float(self.y[peak_index]), float(self.t[peak_index])

    def _compute_overshoot(self, final_value: float, peak_value: float) -> float:
        if final_value == 0:
            return 0.0
        overshoot = (peak_value - final_value) / final_value * 100
        return max(overshoot, 0.0)

class Plotter:
    def __init__(self, figsize=(7, 5)):
        self.fig, self.ax = plt.subplots(figsize=figsize)

    def plot(self, step_response: StepResponse, result: AnalysisResult, tf: TransferFunction):
        self.ax.clear()
        t, y = step_response.t, step_response.y
        self.ax.plot(t, y, color="#1f77b4", linewidth=2, label="Step ")

        self.ax.axhline(result.final_value, color="gray", linestyle="--", linewidth=1,
                         label=f"Final value= {result.final_value:.3f}")
        band = 0.02 * abs(result.final_value)
        self.ax.axhspan(result.final_value - band, result.final_value + band,
                         color="green", alpha=0.1)
        if result.settling_time is not None:
            self.ax.axvline(result.settling_time, color="green", linestyle=":", linewidth=1.5,
                             label=f"Settling Time = {result.settling_time:.3f}s")
        if result.overshoot_percent > 0.01:
            self.ax.plot(result.peak_time, result.peak_value, "ro")
            self.ax.annotate(f"Overshoot = {result.overshoot_percent:.2f}%",
                              xy=(result.peak_time, result.peak_value),
                              xytext=(result.peak_time, result.peak_value * 1.05),
                              color="red")

        if result.rise_time is not None:
            self.ax.text(0.98, 0.05, f"Rise Time = {result.rise_time:.3f}s",
                          transform=self.ax.transAxes, ha="right",
                          bbox=dict(boxstyle="round", fc="white", alpha=0.8))
        self.ax.set_title(tf.describe())
        self.ax.set_xlabel("زمان (ثانیه)")
        self.ax.set_ylabel("Output")
        self.ax.grid(True, alpha=0.3)
        self.ax.legend(loc="lower right")
        self.fig.tight_layout()
        return self.fig

class ControlAnalyzerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("تحلیل‌گر پاسخ سیستم‌های مرتبه اول و دوم")
        self.root.geometry("950x650")
        self.plotter = Plotter()
        self.canvas: Optional[FigureCanvasTkAgg] = None
        self._build_layout()

    def _build_layout(self):
        input_frame = ttk.LabelFrame(self.root, text="پارامترهای سیستم", padding=15)
        input_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        ttk.Label(input_frame, text="مرتبه سیستم:").grid(row=0, column=0, sticky="w", pady=5)
        self.order_var = tk.IntVar(value=2)
        order_frame = ttk.Frame(input_frame)
        order_frame.grid(row=0, column=1, pady=5)
        ttk.Radiobutton(order_frame, text="اول", variable=self.order_var, value=1,
                         command=self._toggle_zeta_field).pack(side=tk.LEFT)
        ttk.Radiobutton(order_frame, text="دوم", variable=self.order_var, value=2,
                         command=self._toggle_zeta_field).pack(side=tk.LEFT)

        ttk.Label(input_frame, text="بهره K:").grid(row=1, column=0, sticky="w", pady=5)
        self.K_entry = ttk.Entry(input_frame, width=12)
        self.K_entry.insert(0, "1.0")
        self.K_entry.grid(row=1, column=1, pady=5)

        ttk.Label(input_frame, text="ωn:").grid(row=2, column=0, sticky="w", pady=5)
        self.wn_entry = ttk.Entry(input_frame, width=12)
        self.wn_entry.insert(0, "2.0")
        self.wn_entry.grid(row=2, column=1, pady=5)

        ttk.Label(input_frame, text="ζ (میرایی):").grid(row=3, column=0, sticky="w", pady=5)
        self.zeta_entry = ttk.Entry(input_frame, width=12)
        self.zeta_entry.insert(0, "0.5")
        self.zeta_entry.grid(row=3, column=1, pady=5)
        run_btn = ttk.Button(input_frame, text="رسم و تحلیل", command=self._on_run)
        run_btn.grid(row=4, column=0, columnspan=2, pady=20)
        result_frame = ttk.LabelFrame(input_frame, text="نتایج تحلیل", padding=10)
        result_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=10)
        self.result_labels = {}
        for i, key in enumerate(["زمان صعود", "زمان نشست", "فراجهش (%)", "مقدار نهایی"]):
            ttk.Label(result_frame, text=f"{key}:").grid(row=i, column=0, sticky="w", pady=3)
            lbl = ttk.Label(result_frame, text="—", foreground="blue")
            lbl.grid(row=i, column=1, sticky="w", pady=3)
            self.result_labels[key] = lbl

        self.plot_frame = ttk.Frame(self.root)
        self.plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._embed_canvas()
        self._toggle_zeta_field()

    def _embed_canvas(self):
        self.canvas = FigureCanvasTkAgg(self.plotter.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas.draw()

    def _toggle_zeta_field(self):
        if self.order_var.get() == 1:
            self.zeta_entry.configure(state="disabled")
        else:
            self.zeta_entry.configure(state="normal")

    def _on_run(self):
        try:
            order = self.order_var.get()
            K = float(self.K_entry.get())
            wn = float(self.wn_entry.get())
            zeta = float(self.zeta_entry.get()) if order == 2 else None

            tf = TransferFunction(order=order, K=K, wn=wn, zeta=zeta)
            step_resp = StepResponse(tf)
            result = Analyzer(step_resp).analyze()

            self.plotter.plot(step_resp, result, tf)
            self.canvas.draw()

            self._update_result_labels(result)
        except ValueError as e:
            messagebox.showerror("خطای ورودی", str(e))
        except Exception as e:
            messagebox.showerror("خطا", f"مشکلی پیش آمد:\n{e}")
    def _update_result_labels(self, result: AnalysisResult):
        rt = f"{result.rise_time:.3f} s" if result.rise_time is not None else "—"
        st = f"{result.settling_time:.3f} s" if result.settling_time is not None else "—"
        self.result_labels["زمان صعود"].config(text=rt)
        self.result_labels["زمان نشست"].config(text=st)
        self.result_labels["فراجهش (%)"].config(text=f"{result.overshoot_percent:.2f}")
        self.result_labels["مقدار نهایی"].config(text=f"{result.final_value:.3f}")
def main():
    root = tk.Tk()
    app = ControlAnalyzerGUI(root)
    root.mainloop()
if __name__ == "__main__":
    main()