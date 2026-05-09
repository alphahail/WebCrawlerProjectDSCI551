import sys
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config

if "--offline" in sys.argv:
    config.DB_CONFIG = config.LOCAL_CONFIG
    print("Running in offline mode, connecting to local PostgreSQL")
else:
    print("Connecting to Supabase")

import database


BG       = "#0e0f11"
SURFACE  = "#16181c"
SURFACE2 = "#1e2026"
BORDER   = "#2a2d35"
ACCENT   = "#e8a045"
ACCENT2  = "#5b8dd9"
TEXT     = "#d4d0c8"
TEXT_DIM = "#6e6e6e"
TEXT_MID = "#9a9690"
WHITE    = "#ffffff"


def fmt(n):
    if n is None:
        return "—"
    try:
        return f"{int(n):,}"
    except (ValueError, TypeError):
        return str(n)


def fmt_count(n):
    if n is None:
        return "—"
    try:
        n = int(n)
    except (ValueError, TypeError):
        return "—"
    if n >= 1_000_000:
        v = n / 1_000_000
        return f"{v:.1f}m".rstrip("0").rstrip(".")
    if n >= 1_000:
        v = n / 1_000
        return f"{v:.1f}k".rstrip("0").rstrip(".")
    return str(n)


def fmt_date(val):
    if not val:
        return ""
    return str(val)[:10]


def fmt_tags(tags):
    if not tags:
        return ""
    if isinstance(tags, list):
        return "  ".join(tags[:8])
    return str(tags)


def run_in_thread(fn):
    t = threading.Thread(target=fn, daemon=True)
    t.start()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SpaceBattles Story Browser")
        self.geometry("1500x760")
        self.minsize(1200, 600)
        self.configure(bg=BG)

        self.conn          = None
        self.current_page  = 1
        self.per_page      = 30
        self.total_pages   = 1
        self.active_story  = None
        self.stories       = {}
        self.tm_urls       = []
        self.open_url      = ""
        self.tag_values    = []
        self.selected_tags = []
        self.tag_popup     = None

        self.build_ui()
        self.connect()

    def connect(self):
        def task():
            try:
                self.conn = database.get_conn()
                self.after(0, self.on_connected)
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: messagebox.showerror(
                    "Connection error",
                    f"Could not connect to database:\n\n{msg}\n\n"
                    "Check DB_CONFIG in app/config.py"
                ))
        run_in_thread(task)

    def on_connected(self):
        self.load_stats()
        self.load_tags()
        self.load_stories()

    def build_ui(self):
        self.apply_styles()

        header = tk.Frame(self, bg=SURFACE, height=52)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(header, text="SB", bg=ACCENT, fg="#1a0f00",
                 font=("Courier", 10, "bold"), padx=8, pady=2
                 ).pack(side="left", padx=(16, 8), pady=12)

        tk.Label(header, text="Story Browser", bg=SURFACE, fg=WHITE,
                 font=("Helvetica", 14, "bold")
                 ).pack(side="left", pady=12)

        self.stats_var = tk.StringVar(value="Connecting...")
        tk.Label(header, textvariable=self.stats_var,
                 bg=SURFACE, fg=TEXT_DIM, font=("Courier", 9)
                 ).pack(side="right", padx=20)

        paned = tk.PanedWindow(self, orient="horizontal",
                               bg=BG, sashwidth=4, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        left  = tk.Frame(paned, bg=BG)
        right = tk.Frame(paned, bg=SURFACE)
        paned.add(left,  minsize=700)
        paned.add(right, minsize=300)

        self.build_filters(left)
        self.build_story_list(left)
        self.build_pagination(left)
        self.build_detail(right)

    def apply_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview",
            background=SURFACE, foreground=TEXT,
            fieldbackground=SURFACE, rowheight=30,
            font=("Helvetica", 11), borderwidth=0,
        )
        style.configure("Treeview.Heading",
            background=SURFACE2, foreground=TEXT_MID,
            font=("Courier", 9, "bold"), relief="flat",
        )
        style.map("Treeview",
            background=[("selected", SURFACE2)],
            foreground=[("selected", ACCENT)],
        )
        style.configure("TScrollbar",
            background=SURFACE2, troughcolor=BG,
            arrowcolor=TEXT_DIM, borderwidth=0,
        )

    def make_col(self, parent, label_text):
        col = tk.Frame(parent, bg=SURFACE)
        col.pack(side="left", padx=(0, 10), anchor="n")
        tk.Label(col, text=label_text, bg=SURFACE, fg=TEXT_DIM,
                 font=("Courier", 8)).pack(anchor="w")
        return col

    def build_filters(self, parent):
        bar = tk.Frame(parent, bg=SURFACE, pady=10, padx=12)
        bar.pack(fill="x")

        search_col = self.make_col(bar, "Search")
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_col, textvariable=self.search_var,
                                bg=BG, fg=TEXT, insertbackground=TEXT,
                                relief="flat", font=("Helvetica", 11), width=16)
        search_entry.pack(ipady=4)
        search_entry.bind("<Return>", lambda e: self.apply_filters())

        author_col = self.make_col(bar, "Author")
        self.author_var = tk.StringVar()
        author_entry = tk.Entry(author_col, textvariable=self.author_var,
                                bg=BG, fg=TEXT, insertbackground=TEXT,
                                relief="flat", font=("Helvetica", 11), width=13)
        author_entry.pack(ipady=4)
        author_entry.bind("<Return>", lambda e: self.apply_filters())

        tag_col = self.make_col(bar, "Tags")
        self.tag_var   = tk.StringVar(value="")
        self.tag_entry = tk.Entry(tag_col, textvariable=self.tag_var,
                                  bg=BG, fg=TEXT, insertbackground=TEXT,
                                  relief="flat", font=("Helvetica", 11), width=14)
        self.tag_entry.pack(ipady=4, anchor="w")
        self.tag_entry.bind("<Return>",   lambda e: self.add_tag_from_entry())
        self.tag_entry.bind("<Down>",     lambda e: self.focus_tag_listbox())
        self.tag_entry.bind("<Escape>",   lambda e: self.close_tag_dropdown())
        self.tag_entry.bind("<FocusOut>", lambda e: self.after(150, self.close_tag_dropdown))
        self.tag_var.trace_add("write",   self.filter_tag_dropdown)

        self.pills_frame = tk.Frame(tag_col, bg=SURFACE)
        self.pills_frame.pack(anchor="w", pady=(3, 0))

        sort_col = self.make_col(bar, "Sort")
        self.sort_var = tk.StringVar(value="Last updated")
        sort_menu = ttk.Combobox(sort_col, textvariable=self.sort_var,
                                 state="readonly", width=14,
                                 font=("Courier", 10),
                                 values=["Last updated", "Last threadmark",
                                         "Title A-Z", "Author A-Z",
                                         "Word count", "Watchers",
                                         "Replies", "Views"])
        sort_menu.pack()

        min_watch_col = self.make_col(bar, "Min watchers")
        self.min_watchers_var = tk.StringVar(value="0")
        tk.Spinbox(min_watch_col, textvariable=self.min_watchers_var,
                   from_=0, to=9_999_999, increment=100,
                   bg=BG, fg=TEXT, insertbackground=TEXT,
                   buttonbackground=SURFACE2, relief="flat",
                   font=("Helvetica", 11), width=8
                   ).pack(ipady=4)

        min_words_col = self.make_col(bar, "Min words")
        self.min_words_var = tk.StringVar(value="0")
        tk.Spinbox(min_words_col, textvariable=self.min_words_var,
                   from_=0, to=9_999_999, increment=1000,
                   bg=BG, fg=TEXT, insertbackground=TEXT,
                   buttonbackground=SURFACE2, relief="flat",
                   font=("Helvetica", 11), width=8
                   ).pack(ipady=4)

        btn_col = tk.Frame(bar, bg=SURFACE)
        btn_col.pack(side="left", anchor="n", padx=(4, 0), pady=(14, 0))

        tk.Button(btn_col, text="Apply", command=self.apply_filters,
                  bg=ACCENT, fg="#1a0f00", font=("Helvetica", 10, "bold"),
                  relief="flat", padx=12, pady=3, cursor="hand2"
                  ).pack(side="left", padx=(0, 6))

        tk.Button(btn_col, text="Clear", command=self.clear_filters,
                  bg=SURFACE2, fg=TEXT_MID, font=("Courier", 10),
                  relief="flat", padx=10, pady=3, cursor="hand2"
                  ).pack(side="left")

        self.count_var = tk.StringVar(value="")
        count_bar = tk.Frame(parent, bg=SURFACE, padx=12, pady=4)
        count_bar.pack(fill="x")
        tk.Label(count_bar, textvariable=self.count_var,
                 bg=SURFACE, fg=TEXT_DIM, font=("Courier", 9)
                 ).pack(anchor="w")

    def build_story_list(self, parent):
        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill="both", expand=True)

        cols = ("title", "author", "words", "watchers",
                "replies", "views", "tm_date", "latest")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings",
                                  selectmode="browse")

        self.tree.heading("title",    text="Title")
        self.tree.heading("author",   text="Author")
        self.tree.heading("words",    text="Words")
        self.tree.heading("watchers", text="Watchers")
        self.tree.heading("replies",  text="Replies")
        self.tree.heading("views",    text="Views")
        self.tree.heading("tm_date",  text="Last TM")
        self.tree.heading("latest",   text="Latest threadmark")

        self.tree.column("title",    width=200, minwidth=140, stretch=True)
        self.tree.column("author",   width=110, minwidth=80,  stretch=False)
        self.tree.column("words",    width=65,  minwidth=55,  stretch=False)
        self.tree.column("watchers", width=75,  minwidth=60,  stretch=False)
        self.tree.column("replies",  width=65,  minwidth=55,  stretch=False)
        self.tree.column("views",    width=65,  minwidth=55,  stretch=False)
        self.tree.column("tm_date",  width=90,  minwidth=80,  stretch=False)
        self.tree.column("latest",   width=180, minwidth=120, stretch=True)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self.on_story_select)
        self.tree.tag_configure("odd",  background=SURFACE)
        self.tree.tag_configure("even", background=SURFACE2)

    def build_pagination(self, parent):
        self.page_frame = tk.Frame(parent, bg=BG, pady=6)
        self.page_frame.pack(fill="x")

    def build_detail(self, parent):
        title_bar = tk.Frame(parent, bg=SURFACE2, height=36)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        tk.Label(title_bar, text="Story detail",
                 bg=SURFACE2, fg=TEXT_DIM, font=("Courier", 9, "bold"),
                 padx=14).pack(side="left", pady=8)

        self.detail_title = tk.Label(parent, text="Select a story",
                                     bg=SURFACE, fg=TEXT_MID,
                                     font=("Helvetica", 13, "bold"),
                                     wraplength=280, justify="left",
                                     padx=14, pady=10)
        self.detail_title.pack(fill="x")

        self.detail_meta = tk.Label(parent, text="",
                                    bg=SURFACE, fg=TEXT_DIM,
                                    font=("Courier", 9),
                                    wraplength=280, justify="left",
                                    padx=14)
        self.detail_meta.pack(fill="x")

        self.detail_stats = tk.Label(parent, text="",
                                     bg=SURFACE, fg=TEXT_MID,
                                     font=("Courier", 9),
                                     wraplength=280, justify="left",
                                     padx=14, pady=2)
        self.detail_stats.pack(fill="x")

        self.detail_tags_text = tk.Text(parent,
                                        bg=SURFACE, fg=ACCENT2,
                                        font=("Courier", 9),
                                        height=1,
                                        relief="flat",
                                        padx=14, pady=4,
                                        wrap="none",
                                        state="disabled",
                                        cursor="arrow")
        self.detail_tags_text.pack(fill="x")

        self.detail_url = tk.Label(parent, text="",
                                   bg=SURFACE, fg=ACCENT,
                                   font=("Courier", 8),
                                   wraplength=280, justify="left",
                                   padx=14, cursor="hand2")
        self.detail_url.pack(fill="x")
        self.detail_url.bind("<Button-1>", self.open_story_url)

        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=14, pady=8)

        tk.Label(parent, text="THREADMARKS",
                 bg=SURFACE, fg=TEXT_DIM, font=("Courier", 8, "bold"),
                 padx=14).pack(anchor="w")

        self.tm_count_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.tm_count_var,
                 bg=SURFACE, fg=ACCENT, font=("Courier", 10, "bold"),
                 padx=14).pack(anchor="w", pady=(0, 6))

        tm_frame  = tk.Frame(parent, bg=SURFACE)
        tm_frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        tm_scroll = ttk.Scrollbar(tm_frame, orient="vertical")
        self.tm_list = tk.Listbox(tm_frame, bg=BG, fg=TEXT,
                                  selectbackground=SURFACE2,
                                  selectforeground=ACCENT,
                                  font=("Helvetica", 10),
                                  relief="flat", borderwidth=0,
                                  activestyle="none",
                                  yscrollcommand=tm_scroll.set)
        tm_scroll.config(command=self.tm_list.yview)
        self.tm_list.pack(side="left", fill="both", expand=True)
        tm_scroll.pack(side="right", fill="y")

        self.tm_list.bind("<Double-Button-1>", self.open_threadmark)

        tk.Label(parent, text="double-click a threadmark to open it",
                 bg=SURFACE, fg=TEXT_DIM, font=("Courier", 8),
                 padx=14).pack(anchor="w", pady=(0, 8))

    def filter_tag_dropdown(self, *args):
        typed = self.tag_var.get().lower()
        if not typed:
            filtered = [t for t in self.tag_values if t not in self.selected_tags]
        else:
            filtered = [t for t in self.tag_values
                        if typed in t.lower() and t not in self.selected_tags]
        if filtered:
            self.show_tag_dropdown(filtered)
        else:
            self.close_tag_dropdown()

    def show_tag_dropdown(self, values):
        x = self.tag_entry.winfo_rootx()
        y = self.tag_entry.winfo_rooty() + self.tag_entry.winfo_height() + 2

        if self.tag_popup is None or not self.tag_popup.winfo_exists():
            self.tag_popup = tk.Toplevel(self)
            self.tag_popup.wm_overrideredirect(True)
            self.tag_popup.configure(bg=BORDER)

            frame = tk.Frame(self.tag_popup, bg=SURFACE, bd=0)
            frame.pack(fill="both", expand=True, padx=1, pady=1)

            scrollbar = ttk.Scrollbar(frame, orient="vertical")
            self.tag_listbox = tk.Listbox(
                frame,
                bg=SURFACE, fg=TEXT,
                selectbackground=ACCENT, selectforeground="#1a0f00",
                font=("Helvetica", 10),
                relief="flat", borderwidth=0,
                activestyle="none",
                height=8,
                yscrollcommand=scrollbar.set,
            )
            scrollbar.config(command=self.tag_listbox.yview)
            self.tag_listbox.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            self.tag_listbox.bind("<<ListboxSelect>>", self.on_tag_select)
            self.tag_listbox.bind("<Return>",          self.on_tag_select)
            self.tag_listbox.bind("<Escape>", lambda e: self.close_tag_dropdown())

        popup_h = min(len(values), 8) * 22 + 4
        self.tag_popup.geometry(f"168x{popup_h}+{x}+{y}")
        self.tag_listbox.delete(0, "end")
        for v in values:
            self.tag_listbox.insert("end", f"  {v}")
        self.tag_popup.lift()

    def close_tag_dropdown(self):
        if self.tag_popup and self.tag_popup.winfo_exists():
            self.tag_popup.destroy()
        self.tag_popup = None

    def focus_tag_listbox(self):
        if self.tag_popup and self.tag_popup.winfo_exists():
            self.tag_listbox.focus_set()
            if not self.tag_listbox.curselection():
                self.tag_listbox.selection_set(0)
                self.tag_listbox.activate(0)

    def on_tag_select(self, event):
        sel = self.tag_listbox.curselection()
        if sel:
            value = self.tag_listbox.get(sel[0]).strip()
            self.close_tag_dropdown()
            self.add_tag(value)

    def add_tag_from_entry(self):
        value = self.tag_var.get().strip()
        if value:
            self.add_tag(value)

    def add_tag(self, tag):
        if tag and tag not in self.selected_tags:
            self.selected_tags.append(tag)
            self.draw_pills()
        self.tag_var.set("")
        self.tag_entry.focus_set()

    def remove_tag(self, tag):
        if tag in self.selected_tags:
            self.selected_tags.remove(tag)
            self.draw_pills()

    def draw_pills(self):
        for widget in self.pills_frame.winfo_children():
            widget.destroy()

        for tag in self.selected_tags:
            pill = tk.Frame(self.pills_frame, bg=SURFACE2, padx=4, pady=1)
            pill.pack(side="top", anchor="w", pady=(0, 2))

            display = tag if len(tag) <= 18 else tag[:16] + "..."

            tk.Label(pill, text=display, bg=SURFACE2, fg=ACCENT2,
                     font=("Courier", 9)).pack(side="left")

            tk.Button(pill, text="x", bg=SURFACE2, fg=TEXT_DIM,
                      font=("Courier", 8), relief="flat",
                      cursor="hand2", padx=2, pady=0,
                      command=lambda t=tag: self.remove_tag(t)
                      ).pack(side="left")

    def load_stats(self):
        def task():
            try:
                s    = database.get_stats(self.conn)
                text = (f"{fmt(s['total_stories'])} stories  "
                        f"{fmt(s['total_posts'])} threadmarks  "
                        f"{fmt(s['total_authors'])} authors")
                self.after(0, lambda: self.stats_var.set(text))
            except Exception:
                self.after(0, lambda: self.stats_var.set("Stats unavailable"))
        run_in_thread(task)

    def load_tags(self):
        def task():
            try:
                tags   = database.get_tags(self.conn)
                values = [
                    t["tag"].replace("\n", " ").replace("\r", "").strip()
                    for t in tags
                ]
                self.after(0, lambda: self.set_tag_values(values))
            except Exception:
                pass
        run_in_thread(task)

    def set_tag_values(self, values):
        self.tag_values = values

    def load_stories(self):
        sort_map = {
            "Last updated":    "last_checked",
            "Last threadmark": "latest_threadmark_date",
            "Title A-Z":       "title",
            "Author A-Z":      "author",
            "Word count":      "word_count",
            "Watchers":        "watchers",
            "Replies":         "replies",
            "Views":           "views",
        }
        sort_key = sort_map.get(self.sort_var.get(), "last_checked")
        tags     = self.selected_tags if self.selected_tags else None

        try:
            min_watchers   = int(self.min_watchers_var.get() or 0)
            min_word_count = int(self.min_words_var.get() or 0)
        except ValueError:
            min_watchers   = 0
            min_word_count = 0

        def task():
            try:
                result = database.get_stories(
                    self.conn,
                    search         = self.search_var.get().strip() or None,
                    author         = self.author_var.get().strip() or None,
                    tag            = tags,
                    sort           = sort_key,
                    page           = self.current_page,
                    per_page       = self.per_page,
                    min_watchers   = min_watchers,
                    min_word_count = min_word_count,
                )
                self.after(0, lambda: self.draw_stories(result))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: messagebox.showerror("Query error", msg))
        run_in_thread(task)

    def draw_stories(self, result):
        self.tree.delete(*self.tree.get_children())
        self.stories = {}

        total             = result["total"]
        self.total_pages  = result["pages"]
        self.current_page = result["page"]

        self.count_var.set(
            f"{fmt(total)} stories found  "
            f"page {self.current_page} of {self.total_pages}"
        )

        for i, s in enumerate(result["stories"]):
            latest  = s.get("latest_threadmark_title") or "—"
            tm_date = fmt_date(s.get("latest_threadmark_date")) or "—"
            iid     = str(s["id"])
            self.tree.insert("", "end", iid=iid,
                tags=("even" if i % 2 else "odd",),
                values=(
                    s.get("title")             or "—",
                    s.get("author")            or "—",
                    fmt_count(s.get("word_count_num")),
                    fmt(s.get("watchers")),
                    fmt_count(s.get("replies_num")),
                    fmt_count(s.get("views_num")),
                    tm_date,
                    latest,
                ))
            self.stories[iid] = s

        self.draw_pagination()

    def draw_pagination(self):
        for w in self.page_frame.winfo_children():
            w.destroy()

        if self.total_pages <= 1:
            return

        def go(p):
            self.current_page = p
            self.load_stories()

        tk.Button(self.page_frame, text="Prev",
                  command=lambda: go(self.current_page - 1),
                  state="normal" if self.current_page > 1 else "disabled",
                  bg=SURFACE2, fg=TEXT_MID, relief="flat",
                  font=("Courier", 9), padx=8, pady=2
                  ).pack(side="left", padx=(6, 2))

        pages_to_show = set([1, self.total_pages])
        for p in range(max(1, self.current_page - 2),
                       min(self.total_pages, self.current_page + 2) + 1):
            pages_to_show.add(p)

        prev = 0
        for p in sorted(pages_to_show):
            if p - prev > 1:
                tk.Label(self.page_frame, text="...",
                         bg=BG, fg=TEXT_DIM, font=("Courier", 9)
                         ).pack(side="left", padx=2)
            is_current = (p == self.current_page)
            tk.Button(self.page_frame, text=str(p),
                      command=(lambda pg=p: go(pg)),
                      bg=ACCENT if is_current else SURFACE2,
                      fg="#1a0f00" if is_current else TEXT_MID,
                      font=("Courier", 9, "bold" if is_current else "normal"),
                      relief="flat", padx=8, pady=2,
                      state="disabled" if is_current else "normal"
                      ).pack(side="left", padx=2)
            prev = p

        tk.Button(self.page_frame, text="Next",
                  command=lambda: go(self.current_page + 1),
                  state="normal" if self.current_page < self.total_pages else "disabled",
                  bg=SURFACE2, fg=TEXT_MID, relief="flat",
                  font=("Courier", 9), padx=8, pady=2
                  ).pack(side="left", padx=(2, 6))

    def on_story_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        iid   = sel[0]
        story = self.stories.get(iid)
        if story:
            self.active_story = story["id"]
            self.show_detail(story)
            self.load_threadmarks(story["id"])

    def show_detail(self, story):
        self.detail_title.config(text=story.get("title") or "—")

        self.detail_meta.config(
            text=(f"By {story.get('author') or '—'}  "
                  f"{fmt_count(story.get('word_count_num'))} words  "
                  f"updated {fmt_date(story.get('last_checked'))}")
        )

        self.detail_stats.config(
            text=(f"Watchers: {fmt(story.get('watchers'))}  "
                  f"Replies: {fmt_count(story.get('replies_num'))}  "
                  f"Views: {fmt_count(story.get('views_num'))}")
        )

        tags       = story.get("tags") or []
        clean_tags = [t.replace("\n", " ").replace("\r", "").strip() for t in tags]
        display    = "   ".join(t.replace(" ", "\u00a0") for t in clean_tags)
        self.detail_tags_text.config(state="normal")
        self.detail_tags_text.delete("1.0", "end")
        self.detail_tags_text.insert("1.0", display)
        self.detail_tags_text.config(state="disabled")

        url = story.get("url") or ""
        self.open_url = url
        self.detail_url.config(text=url[:60] + ("..." if len(url) > 60 else ""))

        self.tm_count_var.set("")
        self.tm_list.delete(0, "end")
        self.tm_urls = []

    def load_threadmarks(self, story_id):
        def task():
            try:
                tms = database.get_threadmarks(self.conn, story_id)
                self.after(0, lambda: self.draw_threadmarks(tms))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: self.tm_count_var.set(f"Error: {msg}"))
        run_in_thread(task)

    def draw_threadmarks(self, tms):
        self.tm_list.delete(0, "end")
        self.tm_urls = []
        self.tm_count_var.set(f"{len(tms)} threadmarks")

        for t in tms:
            date  = fmt_date(t.get("timestamp"))
            title = t.get("title") or "Untitled"
            self.tm_list.insert("end", f"  {date}  {title}")
            self.tm_urls.append(t.get("post_url") or "")

    def apply_filters(self):
        self.close_tag_dropdown()
        self.current_page = 1
        self.load_stories()

    def clear_filters(self):
        self.search_var.set("")
        self.author_var.set("")
        self.tag_var.set("")
        self.selected_tags = []
        self.draw_pills()
        self.close_tag_dropdown()
        self.sort_var.set("Last updated")
        self.min_watchers_var.set("0")
        self.min_words_var.set("0")
        self.current_page = 1
        self.load_stories()

    def open_story_url(self, event):
        if self.open_url:
            import webbrowser
            webbrowser.open(self.open_url)

    def open_threadmark(self, event):
        idx = self.tm_list.curselection()
        if not idx:
            return
        url = self.tm_urls[idx[0]]
        if url:
            import webbrowser
            webbrowser.open(url)

    def on_close(self):
        self.close_tag_dropdown()
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()