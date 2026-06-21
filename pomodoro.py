import tkinter as tk
from tkinter import font as tkfont
import winsound
import threading

# ── 配置 ────────────────────────────────────────────────────────────────────
WORK_MINUTES = 25
SHORT_BREAK_MINUTES = 5
LONG_BREAK_MINUTES = 15
LONG_BREAK_INTERVAL = 4  # 每 N 个番茄后触发长休息

COLORS = {
    "work":        {"bg": "#c0392b", "fg": "#ffffff", "btn": "#96281b"},
    "short_break": {"bg": "#27ae60", "fg": "#ffffff", "btn": "#1e8449"},
    "long_break":  {"bg": "#2980b9", "fg": "#ffffff", "btn": "#1f6391"},
}

LABELS = {
    "work":        "专注",
    "short_break": "短休息",
    "long_break":  "长休息",
}


# ── 主窗口 ───────────────────────────────────────────────────────────────────
class PomodoroApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("番茄钟")
        self.resizable(False, False)
        self.configure(bg=COLORS["work"]["bg"])

        # 状态
        self.mode = "work"
        self.running = False
        self.remaining = WORK_MINUTES * 60
        self.completed_pomodoros = 0
        self._after_id = None

        self._build_ui()
        self._apply_theme()
        self._update_display()

        # 窗口居中
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    # ── UI 构建 ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        pad = dict(padx=20, pady=8)

        # 模式选择栏
        mode_frame = tk.Frame(self, bg=COLORS["work"]["bg"])
        mode_frame.pack(fill="x", padx=20, pady=(20, 0))

        self.mode_buttons = {}
        modes = [("work", "专注"), ("short_break", "短休息"), ("long_break", "长休息")]
        for m, label in modes:
            btn = tk.Button(
                mode_frame, text=label, relief="flat", cursor="hand2",
                font=("Microsoft YaHei", 10),
                command=lambda m=m: self._switch_mode(m),
            )
            btn.pack(side="left", expand=True, fill="x", padx=2)
            self.mode_buttons[m] = btn

        # 当前阶段标签
        self.phase_label = tk.Label(
            self, text="", font=("Microsoft YaHei", 13, "bold"),
        )
        self.phase_label.pack(pady=(18, 0))

        # 计时器大字
        timer_font = tkfont.Font(family="Consolas", size=72, weight="bold")
        self.timer_label = tk.Label(self, text="25:00", font=timer_font)
        self.timer_label.pack(pady=(0, 10))

        # 进度环（Canvas）
        self.canvas = tk.Canvas(self, width=260, height=10, highlightthickness=0)
        self.canvas.pack()
        self.progress_bg  = self.canvas.create_rectangle(0, 0, 260, 10, fill="#00000033", outline="")
        self.progress_bar = self.canvas.create_rectangle(0, 0, 0,   10, fill="white",     outline="")

        # 控制按钮
        btn_frame = tk.Frame(self, bg="white")
        btn_frame.pack(pady=24)

        self.start_btn = tk.Button(
            btn_frame, text="开始", width=10, relief="flat", cursor="hand2",
            font=("Microsoft YaHei", 12, "bold"),
            command=self._toggle,
        )
        self.start_btn.pack(side="left", padx=6)

        reset_btn = tk.Button(
            btn_frame, text="重置", width=8, relief="flat", cursor="hand2",
            font=("Microsoft YaHei", 12),
            command=self._reset,
        )
        reset_btn.pack(side="left", padx=6)

        # 番茄计数
        count_frame = tk.Frame(self, bg="white")
        count_frame.pack(pady=(0, 20))

        tk.Label(count_frame, text="今日番茄：",
                 font=("Microsoft YaHei", 10), bg="white", fg="#333").pack(side="left")
        self.count_label = tk.Label(count_frame, text="0",
                 font=("Microsoft YaHei", 10, "bold"), bg="white", fg="#c0392b")
        self.count_label.pack(side="left")

        # 番茄点阵（最多显示 LONG_BREAK_INTERVAL 个）
        self.dots_frame = tk.Frame(self, bg="white")
        self.dots_frame.pack(pady=(0, 24))

    # ── 主题 ────────────────────────────────────────────────────────────────
    def _apply_theme(self):
        c = COLORS[self.mode]
        bg, fg, btn_bg = c["bg"], c["fg"], c["btn"]

        self.configure(bg=bg)
        self.phase_label.configure(bg=bg, fg=fg, text=LABELS[self.mode])
        self.timer_label.configure(bg=bg, fg=fg)
        self.canvas.configure(bg=bg)
        self.canvas.itemconfig(self.progress_bar, fill=fg)

        for m, b in self.mode_buttons.items():
            if m == self.mode:
                b.configure(bg="white", fg=bg, activebackground="white", activeforeground=bg)
            else:
                b.configure(bg=btn_bg, fg=fg, activebackground=btn_bg, activeforeground=fg)
            b.master.configure(bg=bg)

        self.start_btn.configure(bg="white", fg=bg,
                                 activebackground="#eeeeee", activeforeground=bg)

        reset_btn = self.start_btn.master.winfo_children()[1]
        reset_btn.configure(bg=btn_bg, fg=fg,
                            activebackground=btn_bg, activeforeground=fg)

        self.count_label.master.configure(bg=bg)
        self.count_label.configure(bg=bg, fg="white")
        self.count_label.master.winfo_children()[0].configure(bg=bg, fg=fg)
        self.dots_frame.configure(bg=bg)
        self._refresh_dots()

    def _refresh_dots(self):
        for w in self.dots_frame.winfo_children():
            w.destroy()
        filled = self.completed_pomodoros % LONG_BREAK_INTERVAL
        for i in range(LONG_BREAK_INTERVAL):
            color = "white" if i < filled else COLORS[self.mode]["btn"]
            tk.Label(self.dots_frame, text="●", font=("Arial", 18),
                     bg=COLORS[self.mode]["bg"], fg=color).pack(side="left", padx=3)

    # ── 模式切换 ────────────────────────────────────────────────────────────
    def _switch_mode(self, mode):
        self._stop_timer()
        self.mode = mode
        durations = {"work": WORK_MINUTES, "short_break": SHORT_BREAK_MINUTES,
                     "long_break": LONG_BREAK_MINUTES}
        self.remaining = durations[mode] * 60
        self.running = False
        self.start_btn.configure(text="开始")
        self._apply_theme()
        self._update_display()

    # ── 计时器控制 ───────────────────────────────────────────────────────────
    def _toggle(self):
        if self.running:
            self._stop_timer()
            self.start_btn.configure(text="继续")
        else:
            self.running = True
            self.start_btn.configure(text="暂停")
            self._tick()

    def _reset(self):
        self._stop_timer()
        self._switch_mode(self.mode)

    def _stop_timer(self):
        self.running = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _tick(self):
        if not self.running:
            return
        if self.remaining > 0:
            self.remaining -= 1
            self._update_display()
            self._after_id = self.after(1000, self._tick)
        else:
            self._on_finish()

    def _on_finish(self):
        self.running = False
        self.start_btn.configure(text="开始")
        self._play_sound()

        if self.mode == "work":
            self.completed_pomodoros += 1
            self.count_label.configure(text=str(self.completed_pomodoros))
            if self.completed_pomodoros % LONG_BREAK_INTERVAL == 0:
                self._switch_mode("long_break")
            else:
                self._switch_mode("short_break")
        else:
            self._switch_mode("work")

    # ── 显示更新 ─────────────────────────────────────────────────────────────
    def _update_display(self):
        mins, secs = divmod(self.remaining, 60)
        self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")

        durations = {"work": WORK_MINUTES * 60, "short_break": SHORT_BREAK_MINUTES * 60,
                     "long_break": LONG_BREAK_MINUTES * 60}
        total = durations[self.mode]
        ratio = 1 - self.remaining / total
        self.canvas.coords(self.progress_bar, 0, 0, 260 * ratio, 10)

        # 标题栏实时显示
        mins, secs = divmod(self.remaining, 60)
        self.title(f"{mins:02d}:{secs:02d} — {LABELS[self.mode]}")

    # ── 声音 ─────────────────────────────────────────────────────────────────
    def _play_sound(self):
        def beep():
            for _ in range(3):
                winsound.Beep(880, 200)
        threading.Thread(target=beep, daemon=True).start()


if __name__ == "__main__":
    app = PomodoroApp()
    app.mainloop()
