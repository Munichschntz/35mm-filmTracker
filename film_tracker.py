from __future__ import annotations

import csv
import tkinter as tk
import tkinter.font as tkfont
import tkinter.simpledialog as simpledialog
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk
import ttkbootstrap as tb

from db import FilmDatabase
from film_catalog import FilmCatalog, FilmStock
from roll_log import Roll, RollLog


def center_dialog_over_parent(window: tk.Toplevel, parent: tk.Misc, min_width: int, min_height: int) -> None:
    window.update_idletasks()
    parent_x = parent.winfo_x()
    parent_y = parent.winfo_y()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()
    dialog_width = max(min_width, window.winfo_reqwidth())
    dialog_height = max(min_height, window.winfo_reqheight())
    pos_x = parent_x + (parent_width - dialog_width) // 2
    pos_y = parent_y + (parent_height - dialog_height) // 2
    window.geometry(f"{dialog_width}x{dialog_height}+{max(0, pos_x)}+{max(0, pos_y)}")


class BaseDialog:
    """Base for all modal Toplevel dialogs.

    Subclasses create a window by calling ``self._init_window(...)`` which
    handles Toplevel creation, transient binding, optional min-size, and
    centering over the parent — so callers can never accidentally skip it.

    Typical subclass pattern::

        class MyDialog(BaseDialog):
            def __init__(self, parent, ...):
                self._init_window(parent, "Title", width=500, height=300)
                self._build()
                self._win.grab_set()
    """

    _win: tk.Toplevel  # set by _init_window; available to subclasses

    def _init_window(
        self,
        parent: tk.Misc,
        title: str,
        width: int,
        height: int,
        *,
        resizable: tuple[bool, bool] = (True, True),
        min_width: int | None = None,
        min_height: int | None = None,
    ) -> None:
        self._win = tb.Toplevel(parent)
        self._win.title(title)
        self._win.transient(parent)
        self._win.resizable(*resizable)
        if min_width is not None and min_height is not None:
            self._win.minsize(min_width, min_height)
        center_dialog_over_parent(self._win, parent, width, height)


class ValidationUtils:
    @staticmethod
    def parse_optional_iso(value: str | None) -> int | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        parsed = int(stripped)
        if parsed <= 0:
            raise ValueError("ISO must be a positive number.")
        return parsed

    @staticmethod
    def parse_optional_frame(value: str | None) -> int | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        parsed = int(stripped)
        if parsed <= 0:
            raise ValueError("Frame number must be greater than zero.")
        return parsed

    @staticmethod
    def parse_optional_date(value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        datetime.strptime(stripped, "%Y-%m-%d")
        return stripped

    @staticmethod
    def normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped if stripped else None


class CameraLensManagerDialog(BaseDialog):
    def __init__(
        self,
        parent: tk.Tk,
        title: str,
        items: list[str],
    ) -> None:
        self.result: list[str] | None = None
        self._init_window(parent, title, 400, 350)

        body = ttk.Frame(self._win, padding=12)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        self._win.columnconfigure(0, weight=1)
        self._win.rowconfigure(0, weight=1)

        ttk.Label(body, text=f"Manage {title}").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        # Listbox with scrollbar
        list_frame = ttk.Frame(body)
        list_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 8))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(list_frame, height=10)
        self.listbox.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        # Populate listbox with items
        for item in items:
            self.listbox.insert(tk.END, item)

        # Add item section
        add_frame = ttk.Frame(body)
        add_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        add_frame.columnconfigure(0, weight=1)

        ttk.Label(add_frame, text="Add new:").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.new_item_var = tk.StringVar()
        self.new_item_entry = ttk.Entry(add_frame, textvariable=self.new_item_var, width=40)
        self.new_item_entry.grid(row=1, column=0, sticky="ew")
        self.new_item_entry.focus_set()

        # Buttons
        button_frame = ttk.Frame(body)
        button_frame.grid(row=3, column=0, columnspan=2, sticky="ew")
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        ttk.Button(button_frame, text="Add", command=self._add_item).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(button_frame, text="Remove Selected", command=self._remove_item).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        dialog_buttons = ttk.Frame(body)
        dialog_buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=(12, 0))

        ttk.Button(dialog_buttons, text="Cancel", command=self._cancel).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(dialog_buttons, text="OK", command=self._ok).grid(row=0, column=1)

        self._win.bind("<Return>", self._on_return)
        self._win.bind("<Escape>", self._on_escape)
        self._win.grab_set()

    def _on_return(self, _event: tk.Event) -> None:
        # Only add if we're in the entry field, don't save on return
        if self._win.focus_get() == self.new_item_entry:
            self._add_item()

    def _on_escape(self, _event: tk.Event) -> None:
        self._cancel()

    def _add_item(self) -> None:
        new_item = self.new_item_var.get().strip()
        if not new_item:
            messagebox.showwarning("Empty Item", "Please enter a name before adding.", parent=self._win)
            return

        # Check for duplicates
        existing_items = self.listbox.get(0, tk.END)
        if new_item in existing_items:
            messagebox.showwarning("Duplicate", f"'{new_item}' already exists.", parent=self._win)
            return

        self.listbox.insert(tk.END, new_item)
        self.new_item_var.set("")
        self.new_item_entry.focus_set()

    def _remove_item(self) -> None:
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select an item to remove.", parent=self._win)
            return
        self.listbox.delete(selection[0])

    def _cancel(self) -> None:
        self.result = None
        self._win.destroy()

    def _ok(self) -> None:
        self.result = list(self.listbox.get(0, tk.END))
        self._win.destroy()

    def show(self) -> list[str] | None:
        self._win.wait_window(self._win)
        return self.result


class CollectionMetadataDialog(BaseDialog):
    def __init__(
        self,
        parent: tk.Tk,
        title: str,
        initial: dict[str, str],
        camera_presets: list[str],
        lens_presets: list[str],
    ) -> None:
        self.result: dict[str, str] | None = None
        self._init_window(parent, title, 560, 320, resizable=(False, False))

        body = ttk.Frame(self._win, padding=12)
        body.grid(row=0, column=0, sticky="nsew")

        labels = (
            ("Collection Name *", "name"),
            ("Film Stock", "film_stock"),
            ("ISO", "iso"),
            ("Roll Capacity", "capacity"),
            ("Camera", "camera"),
            ("Lens", "lens"),
            ("Lab", "lab"),
            ("Push/Pull", "push_pull"),
        )

        self.vars: dict[str, tk.StringVar] = {}
        for row_index, (label, key) in enumerate(labels):
            ttk.Label(body, text=label).grid(row=row_index, column=0, sticky="w", padx=(0, 8), pady=4)
            var = tk.StringVar(value=initial.get(key, ""))
            self.vars[key] = var
            if key == "camera":
                entry = ttk.Combobox(body, textvariable=var, values=camera_presets, width=38)
            elif key == "lens":
                entry = ttk.Combobox(body, textvariable=var, values=lens_presets, width=38)
            else:
                entry = ttk.Entry(body, textvariable=var, width=40)
            entry.grid(row=row_index, column=1, sticky="ew", pady=4)
            if key == "name":
                entry.focus_set()

        help_text = "Optional fields can be left blank. ISO and Roll Capacity must be positive whole numbers."
        ttk.Label(body, text=help_text).grid(row=len(labels), column=0, columnspan=2, sticky="w", pady=(6, 0))

        buttons = ttk.Frame(body)
        buttons.grid(row=len(labels) + 1, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self._cancel).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="Save", command=self._save).grid(row=0, column=1)

        self._win.bind("<Return>", self._on_return)
        self._win.bind("<Escape>", self._on_escape)
        self._win.grab_set()

    def _on_return(self, _event: tk.Event) -> None:
        self._save()

    def _on_escape(self, _event: tk.Event) -> None:
        self._cancel()

    def _cancel(self) -> None:
        self.result = None
        self._win.destroy()

    def _save(self) -> None:
        name = self.vars["name"].get().strip()
        if not name:
            messagebox.showerror("Validation Error", "Collection name cannot be empty.", parent=self._win)
            return

        iso_raw = self.vars["iso"].get().strip()
        if iso_raw:
            try:
                ValidationUtils.parse_optional_iso(iso_raw)
            except ValueError as exc:
                messagebox.showerror("Validation Error", str(exc), parent=self._win)
                return

        capacity_raw = self.vars["capacity"].get().strip()
        if capacity_raw:
            try:
                cap_int = int(capacity_raw)
                if cap_int <= 0:
                    raise ValueError("Roll capacity must be a positive number.")
            except ValueError as exc:
                messagebox.showerror("Validation Error", str(exc), parent=self._win)
                return

        self.result = {
            "name": name,
            "film_stock": self.vars["film_stock"].get().strip(),
            "iso": iso_raw,
            "capacity": capacity_raw,
            "camera": self.vars["camera"].get().strip(),
            "lens": self.vars["lens"].get().strip(),
            "lab": self.vars["lab"].get().strip(),
            "push_pull": self.vars["push_pull"].get().strip(),
        }
        self._win.destroy()

    def show(self) -> dict[str, str] | None:
        self._win.wait_window(self._win)
        return self.result


# ---------------------------------------------------------------------------
# Quick Tips Dialog
# ---------------------------------------------------------------------------

class QuickTipsDialog(BaseDialog):
    _TIPS = (
        "Capture: use Save + Next for sequential frame-by-frame entry.\n\n"
        "Review: filter by status to focus on processing stages "
        "(shot \u2192 developed \u2192 scanned \u2192 edited \u2192 printed).\n\n"
        "Organize: use Edit to keep roll-level metadata (film stock, camera, "
        "lens, capacity) complete.\n\n"
        "Bulk Update: select multiple shots in the list, choose a status, "
        "and click Mark Selected \u2014 or use Mark Visible to update all shown rows at once."
    )

    def __init__(self, parent: tk.Tk) -> None:
        self._init_window(parent, "Quick Tips", 620, 320)

        content = ttk.Frame(self._win, padding=12)
        content.grid(row=0, column=0, sticky="nsew")
        self._win.columnconfigure(0, weight=1)
        self._win.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        ttk.Label(content, text="Quick Tips").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(
            content, text=self._TIPS, justify="left", wraplength=580,
        ).grid(row=1, column=0, sticky="nsew")

        button_row = ttk.Frame(content)
        button_row.grid(row=2, column=0, sticky="e", pady=(12, 0))

        close_button = ttk.Button(button_row, text="Close", command=self._win.destroy)
        close_button.grid(row=0, column=0)
        close_button.focus_set()

        self._win.bind("<Escape>", lambda _e: self._win.destroy())
        self._win.bind("<Return>", lambda _e: self._win.destroy())
        self._win.protocol("WM_DELETE_WINDOW", self._win.destroy)
        self._win.grab_set()
        parent.wait_window(self._win)


# ---------------------------------------------------------------------------
# Preferences Dialog
# ---------------------------------------------------------------------------

class PreferencesDialog(BaseDialog):
    """Modal preferences window.

    Receives current preference values and preset lists at construction time,
    then calls ``on_save`` with keyword arguments when the user saves.
    The caller is responsible for persisting changes and updating the UI.
    """

    def __init__(
        self,
        parent: tk.Tk,
        status_values: tuple[str, ...],
        current_prefs: dict[str, str],
        camera_presets: list[str],
        lens_presets: list[str],
        open_camera_manager: object,
        open_lens_manager: object,
        on_save: object,
    ) -> None:
        self._status_values = status_values
        self._camera_presets: list[str] = list(camera_presets)
        self._lens_presets: list[str] = list(lens_presets)
        self._open_camera_manager = open_camera_manager
        self._open_lens_manager = open_lens_manager
        self._on_save = on_save

        self._init_window(parent, "Preferences", 560, 360, min_width=560, min_height=360)

        content = ttk.Frame(self._win, padding=12)
        content.grid(row=0, column=0, sticky="nsew")
        self._win.columnconfigure(0, weight=1)
        self._win.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(content)
        notebook.grid(row=0, column=0, sticky="nsew")

        general_tab  = ttk.Frame(notebook, padding=12)
        quick_tab    = ttk.Frame(notebook, padding=12)
        metadata_tab = ttk.Frame(notebook, padding=12)
        notebook.add(general_tab,  text="General")
        notebook.add(quick_tab,    text="Quick Entry")
        notebook.add(metadata_tab, text="Metadata")

        self._default_status_var = tk.StringVar(value=current_prefs["default_shot_status"])
        self._default_filter_var = tk.StringVar(value=current_prefs["default_status_filter"])
        self._clear_notes_var    = tk.BooleanVar(value=current_prefs.get("save_next_clear_notes") == "true")
        self._ctrl_enter_var     = tk.BooleanVar(value=current_prefs.get("enable_ctrl_enter_save_next") == "true")
        self._show_metadata_var  = tk.BooleanVar(value=current_prefs.get("show_collection_metadata_header") == "true")
        self._camera_summary_var = tk.StringVar()
        self._lens_summary_var   = tk.StringVar()

        self._build_general_tab(general_tab)
        self._build_quick_tab(quick_tab)
        self._build_metadata_tab(metadata_tab)
        self._refresh_preset_summaries()

        buttons = ttk.Frame(content)
        buttons.grid(row=1, column=0, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self._win.destroy).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="Save",   command=self._save).grid(row=0, column=1)

        self._win.grab_set()

    def _build_general_tab(self, tab: ttk.Frame) -> None:
        ttk.Label(tab, text="Default shot status for new entries").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            tab, textvariable=self._default_status_var,
            values=self._status_values, state="readonly", width=16,
        ).grid(row=1, column=0, sticky="w", pady=(4, 12))

        ttk.Label(tab, text="Default status filter when app starts").grid(row=2, column=0, sticky="w")
        ttk.Combobox(
            tab, textvariable=self._default_filter_var,
            values=("all", *self._status_values), state="readonly", width=16,
        ).grid(row=3, column=0, sticky="w", pady=(4, 12))

        ttk.Label(
            tab, text="Use these defaults to match your most common workflow.",
        ).grid(row=4, column=0, sticky="w")

    def _build_quick_tab(self, tab: ttk.Frame) -> None:
        ttk.Checkbutton(
            tab, text="Enable Ctrl+Enter to Save + Next",
            variable=self._ctrl_enter_var,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Checkbutton(
            tab, text="Clear notes after Save + Next",
            variable=self._clear_notes_var,
        ).grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Label(
            tab,
            text="Quick Entry is designed for rapid frame-by-frame logging while shooting.",
        ).grid(row=2, column=0, sticky="w")

    def _build_metadata_tab(self, tab: ttk.Frame) -> None:
        ttk.Checkbutton(
            tab, text="Show collection metadata summary in shot header",
            variable=self._show_metadata_var,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(
            tab,
            text="Metadata helps identify film stock, camera, and lens context while reviewing shots.",
        ).grid(row=1, column=0, sticky="w")
        ttk.Label(
            tab,
            text="Use Manage to add or remove list entries. These presets are reused in collection metadata dialogs.",
        ).grid(row=2, column=0, sticky="w", pady=(6, 0))

        ttk.Label(tab, text="Camera presets").grid(row=3, column=0, sticky="w", pady=(12, 0))
        cam_frame = ttk.Frame(tab)
        cam_frame.grid(row=4, column=0, sticky="ew", pady=(4, 8))
        cam_frame.columnconfigure(0, weight=1)
        ttk.Label(cam_frame, textvariable=self._camera_summary_var).grid(row=0, column=0, sticky="w", padx=(0, 4))
        ttk.Button(cam_frame, text="Manage", command=self._manage_cameras, width=10).grid(row=0, column=1, sticky="ew")

        ttk.Label(tab, text="Lens presets").grid(row=5, column=0, sticky="w")
        lens_frame = ttk.Frame(tab)
        lens_frame.grid(row=6, column=0, sticky="ew", pady=(4, 0))
        lens_frame.columnconfigure(0, weight=1)
        ttk.Label(lens_frame, textvariable=self._lens_summary_var).grid(row=0, column=0, sticky="w", padx=(0, 4))
        ttk.Button(lens_frame, text="Manage", command=self._manage_lenses, width=10).grid(row=0, column=1, sticky="ew")

    def _refresh_preset_summaries(self) -> None:
        def _fmt(values: list[str]) -> str:
            return ", ".join(values) if values else "No presets saved."
        self._camera_summary_var.set(_fmt(self._camera_presets))
        self._lens_summary_var.set(_fmt(self._lens_presets))

    def _manage_cameras(self) -> None:
        result = self._open_camera_manager(self._camera_presets)  # type: ignore[operator]
        if result is not None:
            self._camera_presets = [v.strip() for v in result if v.strip()]
            self._refresh_preset_summaries()

    def _manage_lenses(self) -> None:
        result = self._open_lens_manager(self._lens_presets)  # type: ignore[operator]
        if result is not None:
            self._lens_presets = [v.strip() for v in result if v.strip()]
            self._refresh_preset_summaries()

    def _save(self) -> None:
        if self._default_status_var.get() not in self._status_values:
            messagebox.showerror("Validation Error", "Invalid default shot status.", parent=self._win)
            return
        if self._default_filter_var.get() not in ("all", *self._status_values):
            messagebox.showerror("Validation Error", "Invalid default status filter.", parent=self._win)
            return
        self._on_save(  # type: ignore[operator]
            default_shot_status=self._default_status_var.get(),
            default_status_filter=self._default_filter_var.get(),
            save_next_clear_notes=self._clear_notes_var.get(),
            enable_ctrl_enter_save_next=self._ctrl_enter_var.get(),
            show_collection_metadata_header=self._show_metadata_var.get(),
            camera_presets=self._camera_presets,
            lens_presets=self._lens_presets,
        )
        self._win.destroy()


class FilmTrackerApp:
    STATUS_VALUES = ("shot", "developed", "scanned", "edited", "printed")
    DEFAULT_COLLECTION_PANE_WIDTH = 340
    SHUTTER_PRESETS = (
        "1/4000", "1/2000", "1/1000", "1/500", "1/250", "1/125",
        "1/60", "1/30", "1/15", "1/8", "1/4", "1/2", "1s", "2s", "4s", "B",
    )
    FSTOP_PRESETS = (
        "f/1.0", "f/1.2", "f/1.4", "f/1.8", "f/2", "f/2.8",
        "f/3.5", "f/4", "f/5.6", "f/8", "f/11", "f/16", "f/22", "f/32",
    )
    DEFAULT_PREFERENCES = {
        "default_shot_status": "shot",
        "default_status_filter": "all",
        "save_next_clear_notes": "true",
        "enable_ctrl_enter_save_next": "true",
        "show_collection_metadata_header": "true",
        "collection_pane_width": "",
        "camera_presets": "",
        "lens_presets": "",
        "last_selected_collection_id": "",
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("35mm Film Shot Tracker")
        self.root.geometry("1180x680")
        self.root.minsize(1020, 600)

        self._configure_styles()

        self.db = FilmDatabase("data/film_tracker.db")
        self.catalog = FilmCatalog()
        self.catalog.load()
        self.roll_log = RollLog(self.catalog)
        self.preferences = dict(self.DEFAULT_PREFERENCES)
        self._load_preferences()

        last_selected_id = self.preferences.get("last_selected_collection_id", "").strip()
        self.selected_collection_id: int | None = int(last_selected_id) if last_selected_id.isdigit() else None
        self.selected_shot_id: int | None = None
        self.active_status_filter = tk.StringVar(value=self.preferences["default_status_filter"])

        self.collection_id_to_item: dict[int, str] = {}
        self.collection_id_to_label: dict[int, str] = {}
        self.main_paned: ttk.PanedWindow | None = None
        self._pane_save_after_id: str | None = None
        self._form_dirty = False
        self._loading_form = False

        self._build_ui()
        self.root.bind("<Control-Return>", self._on_save_next_shortcut)
        self._load_collections()

    def _on_save_next_shortcut(self, _event: tk.Event) -> None:
        if not self._preference_bool("enable_ctrl_enter_save_next"):
            return
        self._save_shot(save_and_next=True)

    def _build_ui(self) -> None:
        self._build_menu()

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        container = ttk.PanedWindow(self.root, orient="horizontal")
        container.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.main_paned = container

        self._build_collection_panel(container)
        self._build_shot_panel(container)
        self.root.after_idle(self._restore_collection_pane_width)
        container.bind("<B1-Motion>", self._on_pane_dragging)
        container.bind("<ButtonRelease-1>", self._on_pane_drag_finished)

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)

        app_menu = tk.Menu(menubar, tearoff=False)
        app_menu.add_command(label="Preferences", command=self._open_preferences_window)
        app_menu.add_separator()
        app_menu.add_command(label="Quit", command=self.root.quit)

        menubar.add_cascade(label="App", menu=app_menu)

        tools_menu = tk.Menu(menubar, tearoff=False)
        tools_menu.add_command(label="Film Catalog...", command=self._open_film_catalog)
        tools_menu.add_command(label="Roll Tracker...", command=self._open_roll_tracker)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Quick Tips", command=self._show_help_tips)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def _open_film_catalog(self) -> None:
        FilmCatalogWindow(self.root, self.catalog)

    def _open_roll_tracker(self) -> None:
        RollTrackerWindow(self.root, self.catalog, self.roll_log)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("litera")
        base_font = tkfont.nametofont("TkDefaultFont")
        input_font = base_font.copy()
        input_font.configure(size=base_font.cget("size") + 1)
        self.input_font = input_font
        section_header_font = base_font.copy()
        section_header_font.configure(size=base_font.cget("size") + 2, weight="bold")
        self.section_header_font = section_header_font

        style.configure("TButton", padding=(8, 4))
        style.configure("Section.TLabelframe.Label", font=self.section_header_font)
        style.configure("Large.TEntry", font=self.input_font, padding=(6, 6))
        style.configure("Large.TCombobox", font=self.input_font, padding=(6, 6))

    def _load_preferences(self) -> None:
        stored = self.db.get_preferences()
        for key, default_value in self.DEFAULT_PREFERENCES.items():
            self.preferences[key] = stored.get(key, default_value)

        if self.preferences["default_shot_status"] not in self.STATUS_VALUES:
            self.preferences["default_shot_status"] = self.DEFAULT_PREFERENCES["default_shot_status"]
        if self.preferences["default_status_filter"] not in ("all", *self.STATUS_VALUES):
            self.preferences["default_status_filter"] = self.DEFAULT_PREFERENCES["default_status_filter"]

    def _save_preferences(self) -> None:
        for key, value in self.preferences.items():
            self.db.set_preference(key, value)

    def _preference_bool(self, key: str) -> bool:
        return self.preferences.get(key, "false").strip().lower() == "true"

    def _get_preset_list(self, key: str) -> list[str]:
        raw = self.preferences.get(key, "")
        values = [part.strip() for part in raw.split("|")]
        return [value for value in values if value]

    def _set_preset_list(self, key: str, values: list[str]) -> None:
        normalized = [value.strip() for value in values if value.strip()]
        self.preferences[key] = "|".join(normalized)

    def _remember_selected_collection(self) -> None:
        value = "" if self.selected_collection_id is None else str(self.selected_collection_id)
        self.preferences["last_selected_collection_id"] = value
        self.db.set_preference("last_selected_collection_id", value)
    def _manage_camera_presets(self, current_list: list[str]) -> list[str] | None:
        dialog = CameraLensManagerDialog(self.root, "Cameras", current_list)
        return dialog.show()

    def _manage_lens_presets(self, current_list: list[str]) -> list[str] | None:
        dialog = CameraLensManagerDialog(self.root, "Lenses", current_list)
        return dialog.show()


    def _build_collection_panel(self, parent: ttk.PanedWindow) -> None:
        panel = ttk.LabelFrame(parent, text="Roll Collections", padding=10, style="Section.TLabelframe")
        parent.add(panel, weight=1)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(0, weight=1)

        self.collection_list = ttk.Treeview(panel, columns=("label",), show="headings", selectmode="browse", height=18)
        self.collection_list.heading("label", text="Collection")
        self.collection_list.column("label", anchor="w")
        self.collection_list.grid(row=0, column=0, sticky="nsew")
        self.collection_list.bind("<<TreeviewSelect>>", self._on_collection_selected)
        self.collection_list.bind("<Double-1>", lambda _e: self._edit_collection())

        scrollbar = ttk.Scrollbar(panel, orient="vertical", command=self.collection_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.collection_list.configure(yscrollcommand=scrollbar.set)

        buttons = ttk.Frame(panel)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        buttons.columnconfigure(2, weight=1)
        buttons.columnconfigure(3, weight=1)
        buttons.columnconfigure(4, weight=1)
        buttons.columnconfigure(5, weight=1)

        ttk.Button(buttons, text="Add", command=self._add_collection).grid(row=0, column=0, columnspan=2, sticky="ew", padx=(0, 4))
        ttk.Button(buttons, text="Edit", command=self._edit_collection).grid(row=0, column=2, columnspan=2, sticky="ew", padx=4)
        ttk.Button(buttons, text="Delete", command=self._delete_collection).grid(row=0, column=4, columnspan=2, sticky="ew", padx=(4, 0))
        ttk.Button(buttons, text="Import", command=self._import_shots_csv).grid(row=1, column=0, columnspan=3, sticky="ew", padx=(0, 4), pady=(6, 0))
        ttk.Button(buttons, text="Export", command=self._export_shots_csv).grid(row=1, column=3, columnspan=3, sticky="ew", padx=(4, 0), pady=(6, 0))

    def _build_shot_panel(self, parent: ttk.PanedWindow) -> None:
        panel = ttk.LabelFrame(parent, text="Shots", padding=10, style="Section.TLabelframe")
        parent.add(panel, weight=4)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        top_bar = ttk.Frame(panel)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        top_bar.columnconfigure(0, weight=1)

        self.collection_hint_var = tk.StringVar(value="Select or add a roll collection to begin.")
        self.collection_meta_var = tk.StringVar(value="")
        ttk.Label(top_bar, textvariable=self.collection_hint_var).grid(row=0, column=0, sticky="w")
        filter_row = ttk.Frame(top_bar)
        filter_row.grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(filter_row, text="Status Filter:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.status_filter_combo = ttk.Combobox(
            filter_row,
            textvariable=self.active_status_filter,
            values=("all", *self.STATUS_VALUES),
            state="readonly",
            width=14,
            style="Large.TCombobox",
        )
        self.status_filter_combo.grid(row=0, column=1, sticky="w")
        if self.active_status_filter.get() not in ("all", *self.STATUS_VALUES):
            self.active_status_filter.set("all")
        self.status_filter_combo.bind("<<ComboboxSelected>>", self._on_status_filter_changed)
        ttk.Label(top_bar, textvariable=self.collection_meta_var, foreground="#4F4F4F").grid(row=2, column=0, sticky="w", pady=(6, 0))

        self.shot_tree = ttk.Treeview(
            panel,
            columns=("frame", "status", "shutter", "fstop", "date", "notes"),
            show="headings",
            selectmode="extended",
            height=12,
        )
        self.shot_tree.heading("frame", text="Frame")
        self.shot_tree.heading("status", text="Status")
        self.shot_tree.heading("shutter", text="Shutter Speed")
        self.shot_tree.heading("fstop", text="F-Stop")
        self.shot_tree.heading("date", text="Shot Date")
        self.shot_tree.heading("notes", text="Notes")

        self.shot_tree.column("frame", width=70, anchor="center")
        self.shot_tree.column("status", width=100, anchor="center")
        self.shot_tree.column("shutter", width=120, anchor="center")
        self.shot_tree.column("fstop", width=90, anchor="center")
        self.shot_tree.column("date", width=120, anchor="center")
        self.shot_tree.column("notes", width=250, anchor="w")

        self.shot_tree.tag_configure("shot", background="#FFF8E6")
        self.shot_tree.tag_configure("developed", background="#EAF7EA")
        self.shot_tree.tag_configure("scanned", background="#E8F4FF")
        self.shot_tree.tag_configure("edited", background="#F4ECFF")
        self.shot_tree.tag_configure("printed", background="#FFECEA")

        self.shot_tree.grid(row=1, column=0, sticky="nsew")
        self.shot_tree.bind("<<TreeviewSelect>>", self._on_shot_selected)

        shot_scroll = ttk.Scrollbar(panel, orient="vertical", command=self.shot_tree.yview)
        shot_scroll.grid(row=1, column=1, sticky="ns")
        self.shot_tree.configure(yscrollcommand=shot_scroll.set)

        legend_frame = ttk.Frame(panel)
        legend_frame.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
        legend_items = (
            ("shot", "#FFF8E6"),
            ("developed", "#EAF7EA"),
            ("scanned", "#E8F4FF"),
            ("edited", "#F4ECFF"),
            ("printed", "#FFECEA"),
        )
        for col_idx, (status_label, bg_color) in enumerate(legend_items):
            tk.Label(
                legend_frame,
                text=f"  {status_label}  ",
                background=bg_color,
                relief="flat",
                font=("TkDefaultFont", 8),
            ).grid(row=0, column=col_idx, padx=(0, 4))

        controls = ttk.LabelFrame(panel, text="Bulk Action", padding=(6, 4), style="Section.TLabelframe")
        controls.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        controls.columnconfigure(0, weight=0)
        controls.columnconfigure(1, weight=0)
        controls.columnconfigure(2, weight=0)
        controls.columnconfigure(3, weight=1)

        ttk.Label(controls, text="Bulk Status:").grid(row=0, column=0, sticky="w")
        self.bulk_status_var = tk.StringVar(value="developed")
        self.bulk_status_combo = ttk.Combobox(
            controls,
            textvariable=self.bulk_status_var,
            values=self.STATUS_VALUES,
            state="readonly",
            width=12,
        )
        self.bulk_status_combo.grid(row=0, column=1, sticky="w", padx=(4, 8))
        self.bulk_status_combo.current(1)
        ttk.Button(controls, text="Mark Selected", command=self._apply_status_to_selected).grid(row=0, column=2, sticky="w", padx=(0, 8))
        ttk.Button(controls, text="Mark Visible", command=self._apply_status_to_visible).grid(row=0, column=3, sticky="w")

        form = ttk.LabelFrame(panel, text="Shot Details", padding=10, style="Section.TLabelframe")
        form.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(2, weight=1)
        form.columnconfigure(3, weight=0)
        form.columnconfigure(4, weight=2)
        form.columnconfigure(5, weight=0)
        form.columnconfigure(6, weight=2)
        form.columnconfigure(7, weight=1)

        ttk.Label(form, text="Shutter Speed *").grid(row=0, column=0, sticky="w")
        self.shutter_var = tk.StringVar()
        self.shutter_entry = ttk.Combobox(form, textvariable=self.shutter_var, values=self.SHUTTER_PRESETS, style="Large.TCombobox")
        self.shutter_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))

        ttk.Label(form, text="F-Stop *").grid(row=0, column=1, sticky="w")
        self.fstop_var = tk.StringVar()
        self.fstop_entry = ttk.Combobox(form, textvariable=self.fstop_var, values=self.FSTOP_PRESETS, style="Large.TCombobox")
        self.fstop_entry.grid(row=1, column=1, sticky="ew", padx=(0, 8))

        ttk.Label(form, text="Frame #").grid(row=0, column=2, sticky="w")
        self.frame_var = tk.StringVar()
        self.frame_entry = ttk.Entry(form, textvariable=self.frame_var, style="Large.TEntry")
        self.frame_entry.grid(row=1, column=2, sticky="ew", padx=(0, 8))

        ttk.Label(form, text="Shot Date").grid(row=0, column=3, sticky="w")
        self.date_var = tk.StringVar()
        self.date_entry = ttk.Entry(form, textvariable=self.date_var, style="Large.TEntry", width=12)
        self.date_entry.grid(row=1, column=3, sticky="ew", padx=(0, 8))
        date_hint_frame = ttk.Frame(form)
        date_hint_frame.grid(row=2, column=3, sticky="w", padx=(0, 8))
        ttk.Label(date_hint_frame, text="YYYY-MM-DD", foreground="#888888").grid(row=0, column=0, sticky="w")
        ttk.Button(date_hint_frame, text="Today", command=self._set_date_today, width=6).grid(row=0, column=1, padx=(4, 0))

        ttk.Label(form, text="Notes").grid(row=0, column=4, columnspan=4, sticky="w")
        self.notes_text = tk.Text(form, height=3, wrap="word", font=self.input_font)
        self.notes_text.grid(row=1, column=4, columnspan=4, sticky="ew")
        self.notes_text.bind("<Tab>", self._notes_tab_to_status)

        ttk.Label(form, text="Status").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.status_var = tk.StringVar(value="shot")
        self.status_combo = ttk.Combobox(
            form,
            textvariable=self.status_var,
            values=self.STATUS_VALUES,
            state="readonly",
            width=12,
            style="Large.TCombobox",
        )
        self.status_combo.grid(row=3, column=0, sticky="ew", padx=(0, 8))
        self.status_combo.current(0)

        buttons = ttk.Frame(form)
        buttons.grid(row=3, column=1, columnspan=7, sticky="e", pady=(10, 0))
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        buttons.columnconfigure(2, weight=1)
        buttons.columnconfigure(3, weight=1)

        self.save_shot_btn = ttk.Button(buttons, text="Save Shot", command=self._save_shot)
        self.save_shot_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.save_next_btn = ttk.Button(buttons, text="Save + Next", command=self._save_shot_and_next)
        self.save_next_btn.grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(buttons, text="Delete Shot", command=self._delete_shot).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(buttons, text="Clear", command=self._clear_shot_form).grid(row=0, column=3, sticky="ew", padx=(4, 0))

        # Dirty-state tracking: trace StringVars and Notes widget
        for var in (self.shutter_var, self.fstop_var, self.frame_var, self.date_var, self.status_var):
            var.trace_add("write", self._on_form_field_changed)
        self.notes_text.bind("<<Modified>>", self._on_notes_modified)

    def _show_help_tips(self) -> None:
        QuickTipsDialog(self.root)

    def _restore_collection_pane_width(self, attempt: int = 0) -> None:
        if self.main_paned is None:
            return

        raw = self.preferences.get("collection_pane_width", "").strip()
        stored_width = int(raw) if raw.isdigit() else self.DEFAULT_COLLECTION_PANE_WIDTH

        self.root.update_idletasks()
        total_width = self.main_paned.winfo_width()
        if total_width <= 1:
            if attempt < 10:
                self.root.after(30, lambda: self._restore_collection_pane_width(attempt + 1))
            return

        min_left = 220
        min_right = 420
        max_left = max(min_left, total_width - min_right)
        target = max(min_left, min(stored_width, max_left))

        try:
            self.main_paned.sashpos(0, target)
        except tk.TclError:
            return

    def _on_pane_dragging(self, _event: tk.Event) -> None:
        if self.main_paned is None:
            return

        if self._pane_save_after_id is not None:
            self.root.after_cancel(self._pane_save_after_id)
        self._pane_save_after_id = self.root.after(150, self._save_collection_pane_width)

    def _on_pane_drag_finished(self, _event: tk.Event) -> None:
        if self._pane_save_after_id is not None:
            self.root.after_cancel(self._pane_save_after_id)
            self._pane_save_after_id = None
        self._save_collection_pane_width()

    def _save_collection_pane_width(self) -> None:
        self._pane_save_after_id = None
        if self.main_paned is None:
            return

        try:
            sash_position = int(self.main_paned.sashpos(0))
        except (tk.TclError, ValueError):
            return

        if sash_position <= 0:
            return

        value = str(sash_position)
        if self.preferences.get("collection_pane_width", "") == value:
            return

        self.preferences["collection_pane_width"] = value
        self.db.set_preference("collection_pane_width", value)

    def _set_date_today(self) -> None:
        self.date_var.set(date.today().isoformat())

    def _notes_tab_to_status(self, _event: tk.Event) -> str:
        self.status_combo.focus_set()
        return "break"

    def _on_form_field_changed(self, *_args: object) -> None:
        if not self._loading_form:
            self._form_dirty = True
            self.save_shot_btn.configure(text="Save Shot *")

    def _on_notes_modified(self, _event: tk.Event) -> None:
        if self.notes_text.edit_modified() and not self._loading_form:
            self._form_dirty = True
            self.save_shot_btn.configure(text="Save Shot *")
        self.notes_text.edit_modified(False)

    def _on_status_filter_changed(self, _event: object) -> None:
        self._load_shots_for_selected_collection()
        current_filter = self.active_status_filter.get()
        self.preferences["default_status_filter"] = current_filter
        self.db.set_preference("default_status_filter", current_filter)

    def _open_preferences_window(self) -> None:
        PreferencesDialog(
            parent=self.root,
            status_values=self.STATUS_VALUES,
            current_prefs=self.preferences,
            camera_presets=self._get_preset_list("camera_presets"),
            lens_presets=self._get_preset_list("lens_presets"),
            open_camera_manager=self._manage_camera_presets,
            open_lens_manager=self._manage_lens_presets,
            on_save=self._apply_preferences,
        )

    def _apply_preferences(
        self,
        *,
        default_shot_status: str,
        default_status_filter: str,
        save_next_clear_notes: bool,
        enable_ctrl_enter_save_next: bool,
        show_collection_metadata_header: bool,
        camera_presets: list[str],
        lens_presets: list[str],
    ) -> None:
        self.preferences["default_shot_status"] = default_shot_status
        self.preferences["default_status_filter"] = default_status_filter
        self.preferences["save_next_clear_notes"] = "true" if save_next_clear_notes else "false"
        self.preferences["enable_ctrl_enter_save_next"] = "true" if enable_ctrl_enter_save_next else "false"
        self.preferences["show_collection_metadata_header"] = "true" if show_collection_metadata_header else "false"
        self._set_preset_list("camera_presets", camera_presets)
        self._set_preset_list("lens_presets", lens_presets)
        self._save_preferences()

        self.active_status_filter.set(default_status_filter)
        self._load_shots_for_selected_collection()
        if self.selected_shot_id is None:
            self.status_var.set(default_shot_status)

    def _parse_optional_iso(self, value: str | None) -> int | None:
        return ValidationUtils.parse_optional_iso(value)

    def _prompt_collection_details(self, title: str, initial: dict[str, str]) -> dict[str, str] | None:
        dialog = CollectionMetadataDialog(
            self.root,
            title,
            initial,
            self._get_preset_list("camera_presets"),
            self._get_preset_list("lens_presets"),
        )
        result = dialog.show()
        if result is None:
            return None

        try:
            iso_value = self._parse_optional_iso(result.get("iso", ""))
        except ValueError as exc:
            messagebox.showerror("Validation Error", str(exc), parent=self.root)
            return None

        result["iso"] = "" if iso_value is None else str(iso_value)

        cap_raw = result.get("capacity", "").strip()
        if cap_raw:
            try:
                cap_int = int(cap_raw)
                if cap_int <= 0:
                    raise ValueError()
                result["capacity"] = str(cap_int)
            except ValueError:
                messagebox.showerror("Validation Error", "Roll capacity must be a positive whole number.", parent=self.root)
                return None
        else:
            result["capacity"] = ""

        return result

    def _format_collection_hint(
        self,
        collection_name: str,
        visible_shots_count: int,
        total_shots_count: int,
        active_filter: str,
    ) -> tuple[str, str]:
        if self.selected_collection_id is None:
            return "Select or add a roll collection to begin.", ""

        collection_for_count = self.db.get_collection(self.selected_collection_id)
        capacity = collection_for_count["capacity"] if collection_for_count is not None else None
        if active_filter == "all":
            if capacity is not None:
                count_text = f"{total_shots_count}/{capacity} shots"
            else:
                shot_word = "shot" if total_shots_count == 1 else "shots"
                count_text = f"{total_shots_count} {shot_word}"
        else:
            count_text = f"{visible_shots_count} shown / {total_shots_count} total"

        collection = collection_for_count
        if collection is None:
            return f"Collection: {collection_name} ({count_text})", ""

        details: list[str] = []
        if not self._preference_bool("show_collection_metadata_header"):
            return f"Collection: {collection_name} ({count_text})", ""

        stock = (collection["film_stock"] or "").strip()
        if stock:
            details.append(stock)
        if collection["iso"] is not None:
            details.append(f"ISO {collection['iso']}")
        camera = (collection["camera"] or "").strip()
        if camera:
            details.append(camera)
        lens = (collection["lens"] or "").strip()
        if lens:
            details.append(lens)

        detail_text = " | ".join(details)
        return f"Collection: {collection_name} ({count_text})", detail_text

    # Collections
    def _load_collections(self) -> None:
        collections = self.db.list_collections()

        self.collection_list.delete(*self.collection_list.get_children())
        self.collection_id_to_item.clear()
        self.collection_id_to_label.clear()

        for row in collections:
            label = str(row["name"])
            stock = (row["film_stock"] or "").strip()
            iso = row["iso"]
            if stock:
                label = f"{label} - {stock}"
            if iso is not None:
                label = f"{label} (ISO {iso})"
            shot_count = int(row["shot_count"])
            capacity = row["capacity"]
            if capacity is not None:
                label = f"{label} [{shot_count}/{capacity}]"
            else:
                shot_word = "shot" if shot_count == 1 else "shots"
                label = f"{label} [{shot_count} {shot_word}]"
            collection_id = int(row["id"])
            item = self.collection_list.insert("", tk.END, values=(label,))
            self.collection_id_to_item[collection_id] = item
            self.collection_id_to_label[collection_id] = label

        if self.selected_collection_id is not None:
            self._restore_collection_selection()

    def _restore_collection_selection(self) -> None:
        if self.selected_collection_id is not None:
            selected_item = self.collection_id_to_item.get(self.selected_collection_id)
            if selected_item is not None:
                self.collection_list.selection_set(selected_item)
                self.collection_list.focus(selected_item)
                self.collection_list.see(selected_item)
                return

        self.selected_collection_id = None
        self._remember_selected_collection()
        self._load_shots_for_selected_collection()

    def _get_selected_collection_id(self) -> int | None:
        selection = self.collection_list.selection()
        if not selection:
            return None
        selected_item = selection[0]
        for collection_id, item in self.collection_id_to_item.items():
            if item == selected_item:
                return collection_id
        return None

    def _get_selected_collection_label(self) -> str:
        collection_id = self._get_selected_collection_id()
        if collection_id is None:
            return ""
        return self.collection_id_to_label.get(collection_id, "")

    def _on_collection_selected(self, _event: object) -> None:
        self.selected_collection_id = self._get_selected_collection_id()
        self._remember_selected_collection()
        self.selected_shot_id = None
        self._clear_shot_form()
        self._load_shots_for_selected_collection()

    def _add_collection(self) -> None:
        details = self._prompt_collection_details(
            "New Roll Collection",
            {
                "name": "",
                "film_stock": "",
                "iso": "",
                "capacity": "",
                "camera": "",
                "lens": "",
                "lab": "",
                "push_pull": "",
            },
        )
        if details is None:
            return

        cap_raw = details.get("capacity", "").strip()
        capacity_int: int | None = int(cap_raw) if cap_raw else None

        try:
            new_id = self.db.create_collection(
                details["name"],
                details["film_stock"],
                self._parse_optional_iso(details["iso"]),
                details["camera"],
                details["lens"],
                details["lab"],
                details["push_pull"],
                capacity_int,
            )
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not create collection.\n\n{exc}", parent=self.root)
            return

        self.selected_collection_id = new_id
        self._remember_selected_collection()
        self._load_collections()
        self._load_shots_for_selected_collection()

    def _edit_collection(self) -> None:
        collection_id = self._get_selected_collection_id()
        if collection_id is None:
            messagebox.showinfo("Select Collection", "Select a collection to edit.", parent=self.root)
            return

        row = self.db.get_collection(collection_id)
        if row is None:
            messagebox.showerror("Database Error", "Could not load collection metadata.", parent=self.root)
            return

        details = self._prompt_collection_details(
            "Edit Collection Metadata",
            {
                "name": row["name"] or "",
                "film_stock": row["film_stock"] or "",
                "iso": "" if row["iso"] is None else str(row["iso"]),
                "capacity": "" if row["capacity"] is None else str(row["capacity"]),
                "camera": row["camera"] or "",
                "lens": row["lens"] or "",
                "lab": row["lab"] or "",
                "push_pull": row["push_pull"] or "",
            },
        )
        if details is None:
            return

        cap_raw = details.get("capacity", "").strip()
        capacity_int: int | None = int(cap_raw) if cap_raw else None

        try:
            self.db.update_collection_metadata(
                collection_id,
                details["name"],
                details["film_stock"],
                self._parse_optional_iso(details["iso"]),
                details["camera"],
                details["lens"],
                details["lab"],
                details["push_pull"],
                capacity_int,
            )
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not update collection metadata.\n\n{exc}", parent=self.root)
            return

        self.selected_collection_id = collection_id
        self._remember_selected_collection()
        self._load_collections()
        self._load_shots_for_selected_collection()

    def _delete_collection(self) -> None:
        collection_id = self._get_selected_collection_id()
        if collection_id is None:
            messagebox.showinfo("Select Collection", "Select a collection to delete.", parent=self.root)
            return

        count = self.db.shot_count_for_collection(collection_id)
        shot_word = "shot" if count == 1 else "shots"
        confirm = messagebox.askyesno(
            "Delete Collection",
            f"Delete this collection and its {count} {shot_word}? This cannot be undone.",
            parent=self.root,
        )
        if not confirm:
            return

        try:
            self.db.delete_collection(collection_id)
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not delete collection.\n\n{exc}", parent=self.root)
            return

        self.selected_collection_id = None
        self._remember_selected_collection()
        self.selected_shot_id = None
        self._clear_shot_form()
        self._load_collections()
        self._load_shots_for_selected_collection()

    def _export_shots_csv(self) -> None:
        collection_id = self._get_selected_collection_id()
        if collection_id is None:
            messagebox.showinfo("Select Collection", "Select a collection to export.", parent=self.root)
            return

        row = self.db.get_collection(collection_id)
        collection_name = str(row["name"]) if row is not None else "collection"
        suggested_name = collection_name.replace(" ", "_").lower()

        file_path = filedialog.asksaveasfilename(
            title="Export Shots to CSV",
            defaultextension=".csv",
            initialfile=f"{suggested_name}_shots.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            parent=self.root,
        )
        if not file_path:
            return

        rows = self.db.export_shots_for_collection(collection_id)
        fieldnames = ["frame_number", "status", "shutter_speed", "f_stop", "shot_date", "notes", "created_at"]

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                for row_data in rows:
                    writer.writerow({
                        "frame_number": row_data["frame_number"] if row_data["frame_number"] is not None else "",
                        "status": row_data["status"] or "shot",
                        "shutter_speed": row_data["shutter_speed"] or "",
                        "f_stop": row_data["f_stop"] or "",
                        "shot_date": row_data["shot_date"] or "",
                        "notes": row_data["notes"] or "",
                        "created_at": row_data["created_at"] or "",
                    })
        except Exception as exc:
            messagebox.showerror("Export Error", f"Could not export CSV.\n\n{exc}", parent=self.root)
            return

        messagebox.showinfo("Export Complete", f"Exported {len(rows)} shot(s) to:\n{file_path}", parent=self.root)

    def _import_shots_csv(self) -> None:
        collection_id = self._get_selected_collection_id()
        if collection_id is None:
            messagebox.showinfo("Select Collection", "Select a collection before importing shots.", parent=self.root)
            return

        file_path = filedialog.askopenfilename(
            title="Import Shots from CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            parent=self.root,
        )
        if not file_path:
            return

        parsed_rows: list[dict[str, object]] = []
        parse_errors: list[str] = []
        required_columns = {"shutter_speed", "f_stop"}

        try:
            with open(file_path, "r", newline="", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)
                headers = set(reader.fieldnames or [])
                missing = required_columns - headers
                if missing:
                    messagebox.showerror(
                        "Import Error",
                        f"CSV is missing required columns: {', '.join(sorted(missing))}",
                        parent=self.root,
                    )
                    return

                for index, record in enumerate(reader, start=2):
                    try:
                        shutter = (record.get("shutter_speed") or "").strip()
                        f_stop = (record.get("f_stop") or "").strip()
                        if not shutter or not f_stop:
                            raise ValueError("Shutter speed and f-stop are required.")

                        frame_value = ValidationUtils.parse_optional_frame(record.get("frame_number"))
                        shot_date = ValidationUtils.parse_optional_date(record.get("shot_date"))
                        status = (record.get("status") or "shot").strip().lower()
                        if status not in self.STATUS_VALUES:
                            raise ValueError(f"Invalid status '{status}'.")

                        parsed_rows.append(
                            {
                                "shutter_speed": shutter,
                                "f_stop": f_stop,
                                "frame_number": frame_value,
                                "shot_date": shot_date,
                                "notes": ValidationUtils.normalize_optional_text(record.get("notes")),
                                "status": status,
                                "_source_line": index,
                            }
                        )
                    except ValueError as exc:
                        parse_errors.append(f"Line {index}: {exc}")
        except Exception as exc:
            messagebox.showerror("Import Error", f"Could not read CSV file.\n\n{exc}", parent=self.root)
            return

        if not parsed_rows and not parse_errors:
            messagebox.showinfo("Import Shots", "No rows found to import.", parent=self.root)
            return

        inserted_count, db_errors = self.db.bulk_insert_shots(collection_id, parsed_rows)
        self._load_shots_for_selected_collection()

        messages: list[str] = [f"Imported {inserted_count} shot(s)."]
        if parse_errors:
            messages.append(f"Skipped {len(parse_errors)} row(s) due to validation errors.")
        if db_errors:
            messages.append(f"Skipped {len(db_errors)} row(s) due to database conflicts.")

        detail_lines = (parse_errors + db_errors)[:5]
        detail_text = ""
        if detail_lines:
            detail_text = "\n\nDetails (first 5):\n" + "\n".join(detail_lines)

        messagebox.showinfo("Import Complete", "\n".join(messages) + detail_text, parent=self.root)

    # Shots
    def _load_shots_for_selected_collection(self) -> None:
        self.shot_tree.delete(*self.shot_tree.get_children())

        if self.selected_collection_id is None:
            self.collection_hint_var.set("Select or add a roll collection to begin.")
            self.collection_meta_var.set("")
            return

        selected_label = self._get_selected_collection_label()

        active_filter = self.active_status_filter.get()
        selected_status = None if active_filter == "all" else active_filter
        shots = self.db.list_shots_for_collection(self.selected_collection_id, selected_status)
        total_shots = self.db.shot_count_for_collection(self.selected_collection_id)
        headline, metadata = self._format_collection_hint(
            selected_label,
            len(shots),
            total_shots,
            active_filter,
        )
        self.collection_hint_var.set(headline)
        self.collection_meta_var.set(metadata)

        for shot in shots:
            shot_id = int(shot["id"])
            frame = shot["frame_number"] if shot["frame_number"] is not None else "-"
            date = shot["shot_date"] or "-"
            notes = (shot["notes"] or "").strip()
            self.shot_tree.insert(
                "",
                tk.END,
                iid=str(shot_id),
                values=(
                    frame,
                    shot["status"],
                    shot["shutter_speed"],
                    shot["f_stop"],
                    date,
                    notes,
                ),
                tags=(shot["status"] or "shot",),
            )

    def _on_shot_selected(self, _event: object) -> None:
        selection = self.shot_tree.selection()
        if len(selection) != 1:
            self._clear_shot_form_fields_only()
            return

        shot_id = int(selection[0])
        row = self.db.get_shot(shot_id)
        if row is None:
            self._clear_shot_form_fields_only()
            return

        self.selected_shot_id = shot_id
        self._loading_form = True
        try:
            self.shutter_var.set(row["shutter_speed"])
            self.fstop_var.set(row["f_stop"])
            self.frame_var.set("" if row["frame_number"] is None else str(row["frame_number"]))
            self.date_var.set(row["shot_date"] or "")
            self._set_notes_text(row["notes"] or "")
            self.status_var.set(row["status"] or "shot")
        finally:
            self._loading_form = False
        self._form_dirty = False
        self.save_shot_btn.configure(text="Save Shot")
        self.save_next_btn.configure(state="disabled")

    def _get_notes_text(self) -> str:
        return self.notes_text.get("1.0", "end-1c").strip()

    def _set_notes_text(self, value: str) -> None:
        self.notes_text.delete("1.0", tk.END)
        if value:
            self.notes_text.insert("1.0", value)

    def _validate_shot_fields(self) -> tuple[str, str, int | None, str | None, str | None, str] | None:
        shutter = self.shutter_var.get().strip()
        f_stop = self.fstop_var.get().strip()
        frame_raw = self.frame_var.get().strip()
        shot_date_raw = self.date_var.get().strip()
        notes_raw = self._get_notes_text()
        status_raw = self.status_var.get().strip()

        if not shutter:
            messagebox.showerror("Validation Error", "Shutter speed is required.", parent=self.root)
            return None
        if not f_stop:
            messagebox.showerror("Validation Error", "F-stop is required.", parent=self.root)
            return None

        frame_value: int | None = None
        if frame_raw:
            try:
                frame_value = ValidationUtils.parse_optional_frame(frame_raw)
            except ValueError as exc:
                messagebox.showerror("Validation Error", str(exc), parent=self.root)
                return None

            if self.selected_collection_id is not None and self.db.frame_number_exists(
                self.selected_collection_id,
                frame_value,
                exclude_shot_id=self.selected_shot_id,
            ):
                messagebox.showerror(
                    "Validation Error",
                    f"Frame {frame_value} already exists in this collection.",
                    parent=self.root,
                )
                return None

        shot_date: str | None = None
        if shot_date_raw:
            try:
                shot_date = ValidationUtils.parse_optional_date(shot_date_raw)
            except ValueError:
                messagebox.showerror("Validation Error", "Shot date must be in YYYY-MM-DD format.", parent=self.root)
                return None

        if status_raw not in self.STATUS_VALUES:
            messagebox.showerror("Validation Error", "Invalid shot status.", parent=self.root)
            return None

        notes = notes_raw if notes_raw else None
        return shutter, f_stop, frame_value, shot_date, notes, status_raw

    def _save_shot_and_next(self) -> None:
        self._save_shot(save_and_next=True)

    def _save_shot(self, save_and_next: bool = False) -> None:
        if self.selected_collection_id is None:
            messagebox.showinfo("Select Collection", "Select a collection before saving a shot.", parent=self.root)
            return

        validated = self._validate_shot_fields()
        if validated is None:
            return

        shutter, f_stop, frame_number, shot_date, notes, status = validated
        is_new_shot = self.selected_shot_id is None

        try:
            if is_new_shot:
                self.db.create_shot(
                    self.selected_collection_id,
                    shutter,
                    f_stop,
                    frame_number,
                    shot_date,
                    notes,
                    status,
                )
            else:
                self.db.update_shot(
                    self.selected_shot_id,
                    shutter,
                    f_stop,
                    frame_number,
                    shot_date,
                    notes,
                    status,
                )
        except Exception as exc:
            # Surface unique frame constraint collisions and other DB errors clearly.
            messagebox.showerror("Database Error", f"Could not save shot.\n\n{exc}", parent=self.root)
            return

        self.selected_shot_id = None
        self._load_shots_for_selected_collection()

        if save_and_next and is_new_shot:
            next_frame = frame_number + 1 if frame_number is not None else self.db.next_frame_number_for_collection(self.selected_collection_id)
            self.frame_var.set(str(next_frame))
            self.shutter_var.set(shutter)
            self.fstop_var.set(f_stop)
            self.date_var.set(shot_date or "")
            if self._preference_bool("save_next_clear_notes"):
                self._set_notes_text("")
            else:
                self._set_notes_text(notes or "")
            self.status_var.set(status)
            self.frame_entry.focus_set()
            self.frame_entry.icursor(tk.END)
            return

        self._clear_shot_form()

    def _apply_status_to_selected(self) -> None:
        selection = self.shot_tree.selection()
        if not selection:
            messagebox.showinfo("Select Shots", "Select one or more shots to update status.", parent=self.root)
            return

        status = self.bulk_status_var.get().strip()
        if status not in self.STATUS_VALUES:
            messagebox.showerror("Validation Error", "Invalid bulk status.", parent=self.root)
            return

        try:
            shot_ids = [int(shot_id) for shot_id in selection]
            self.db.update_shot_status_many(shot_ids, status)
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not update statuses.\n\n{exc}", parent=self.root)
            return

        self.selected_shot_id = None
        self._clear_shot_form()
        self._load_shots_for_selected_collection()

    def _apply_status_to_visible(self) -> None:
        visible_ids = self.shot_tree.get_children()
        if not visible_ids:
            messagebox.showinfo("No Shots", "There are no visible shots to update.", parent=self.root)
            return

        status = self.bulk_status_var.get().strip()
        if status not in self.STATUS_VALUES:
            messagebox.showerror("Validation Error", "Invalid bulk status.", parent=self.root)
            return

        confirm = messagebox.askyesno(
            "Confirm Bulk Update",
            f"Mark all {len(visible_ids)} visible shot(s) as '{status}'?",
            parent=self.root,
        )
        if not confirm:
            return

        try:
            shot_ids = [int(shot_id) for shot_id in visible_ids]
            self.db.update_shot_status_many(shot_ids, status)
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not update statuses.\n\n{exc}", parent=self.root)
            return

        self.selected_shot_id = None
        self._clear_shot_form()
        self._load_shots_for_selected_collection()

    def _delete_shot(self) -> None:
        if self.selected_shot_id is None:
            messagebox.showinfo("Select Shot", "Select a shot to delete.", parent=self.root)
            return

        shot_row = self.db.get_shot(self.selected_shot_id)
        if shot_row is not None:
            frame = shot_row["frame_number"]
            shutter = shot_row["shutter_speed"]
            fstop = shot_row["f_stop"]
            if frame is not None:
                detail = f"frame {frame} ({shutter} @ {fstop})"
            else:
                detail = f"unframed shot ({shutter} @ {fstop})"
            confirm_msg = f"Delete {detail}? This cannot be undone."
        else:
            confirm_msg = "Delete the selected shot? This cannot be undone."
        confirm = messagebox.askyesno("Delete Shot", confirm_msg, parent=self.root)
        if not confirm:
            return

        try:
            self.db.delete_shot(self.selected_shot_id)
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not delete shot.\n\n{exc}", parent=self.root)
            return

        self.selected_shot_id = None
        self._clear_shot_form()
        self._load_shots_for_selected_collection()

    def _clear_shot_form(self) -> None:
        self._clear_shot_form_fields_only()
        self.shot_tree.selection_remove(self.shot_tree.selection())

    def _clear_shot_form_fields_only(self) -> None:
        self.selected_shot_id = None
        self._loading_form = True
        try:
            self.shutter_var.set("")
            self.fstop_var.set("")
            self.frame_var.set("")
            self.date_var.set("")
            self._set_notes_text("")
            self.status_var.set(self.preferences["default_shot_status"])
        finally:
            self._loading_form = False
        self._form_dirty = False
        self.save_shot_btn.configure(text="Save Shot")
        self.save_next_btn.configure(state="normal")


# ---------------------------------------------------------------------------
# Film Catalog Window
# ---------------------------------------------------------------------------

_TYPE_LABELS: dict[str, str] = {
    "color_negative": "Color Negative",
    "black_and_white": "Black & White",
    "slide": "Slide",
    "cinema": "Cinema",
    "": "Any",
}

_PROCESS_LABELS: dict[str, str] = {
    "C-41": "C-41",
    "BW": "BW",
    "E-6": "E-6",
    "ECN-2": "ECN-2",
    "": "Any",
}


class FilmCatalogWindow(BaseDialog):
    def __init__(self, parent: tk.Tk, catalog: FilmCatalog) -> None:
        self._catalog = catalog
        self._init_window(parent, "Film Catalog", 860, 580, min_width=720, min_height=480)

        self._var_iso_min = tk.StringVar()
        self._var_iso_max = tk.StringVar()
        self._var_type = tk.StringVar(value="")
        self._var_process = tk.StringVar(value="")
        self._var_search = tk.StringVar()

        self._build()
        self._refresh()
        self._win.grab_set()

    def _build(self) -> None:
        outer = ttk.Frame(self._win, padding=10)
        outer.pack(fill="both", expand=True)

        # ── filter bar ───────────────────────────────────────────────────
        fbar = ttk.LabelFrame(outer, text="Filter", padding=(8, 4))
        fbar.pack(fill="x", pady=(0, 6))

        ttk.Label(fbar, text="ISO min:").grid(row=0, column=0, sticky="w", padx=(0, 2))
        ttk.Entry(fbar, textvariable=self._var_iso_min, width=6).grid(row=0, column=1, padx=(0, 10))

        ttk.Label(fbar, text="ISO max:").grid(row=0, column=2, sticky="w", padx=(0, 2))
        ttk.Entry(fbar, textvariable=self._var_iso_max, width=6).grid(row=0, column=3, padx=(0, 10))

        ttk.Label(fbar, text="Type:").grid(row=0, column=4, sticky="w", padx=(0, 2))
        type_opts = ["", "color_negative", "black_and_white", "slide", "cinema"]
        type_menu = ttk.Combobox(
            fbar, textvariable=self._var_type,
            values=type_opts, state="readonly", width=16,
        )
        type_menu["values"] = type_opts
        type_menu.grid(row=0, column=5, padx=(0, 10))
        # show friendly labels in dropdown by overriding the displayed value
        type_menu.configure(postcommand=lambda: None)

        ttk.Label(fbar, text="Process:").grid(row=0, column=6, sticky="w", padx=(0, 2))
        proc_opts = ["", "C-41", "BW", "E-6", "ECN-2"]
        ttk.Combobox(
            fbar, textvariable=self._var_process,
            values=proc_opts, state="readonly", width=8,
        ).grid(row=0, column=7, padx=(0, 10))

        ttk.Label(fbar, text="Search:").grid(row=0, column=8, sticky="w", padx=(0, 2))
        ttk.Entry(fbar, textvariable=self._var_search, width=18).grid(row=0, column=9, padx=(0, 8))

        ttk.Button(fbar, text="Apply", command=self._refresh).grid(row=0, column=10, padx=(0, 4))
        ttk.Button(fbar, text="Clear", command=self._clear_filters).grid(row=0, column=11)

        # ── treeview ──────────────────────────────────────────────────────
        cols = ("name", "manufacturer", "type", "iso", "process", "push_pull")
        tree_frame = ttk.Frame(outer)
        tree_frame.pack(fill="both", expand=True)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings", selectmode="browse",
        )
        for col, heading, width in [
            ("name", "Film", 220),
            ("manufacturer", "Maker", 100),
            ("type", "Type", 130),
            ("iso", "ISO", 60),
            ("process", "Process", 70),
            ("push_pull", "Push/Pull", 80),
        ]:
            self._tree.heading(col, text=heading)
            self._tree.column(col, width=width, minwidth=50, anchor="w")
        self._tree.column("iso", anchor="e")
        self._tree.column("push_pull", anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # ── detail pane ───────────────────────────────────────────────────
        detail = ttk.LabelFrame(outer, text="Details", padding=(8, 4))
        detail.pack(fill="x", pady=(6, 0))

        self._lbl_notes = ttk.Label(detail, text="", wraplength=760, justify="left")
        self._lbl_notes.pack(anchor="w")

        self._lbl_warning = ttk.Label(
            detail, text="", foreground="#b45309", wraplength=760, justify="left",
        )
        self._lbl_warning.pack(anchor="w")

        btn_row = ttk.Frame(detail)
        btn_row.pack(anchor="e", pady=(4, 0))
        ttk.Button(btn_row, text="Recommend...", command=self._open_recommend).pack()

    # ------------------------------------------------------------------

    def _clear_filters(self) -> None:
        self._var_iso_min.set("")
        self._var_iso_max.set("")
        self._var_type.set("")
        self._var_process.set("")
        self._var_search.set("")
        self._refresh()

    def _refresh(self) -> None:
        query = self._var_search.get().strip()
        iso_min: int | None = None
        iso_max: int | None = None
        try:
            if self._var_iso_min.get().strip():
                iso_min = int(self._var_iso_min.get().strip())
            if self._var_iso_max.get().strip():
                iso_max = int(self._var_iso_max.get().strip())
        except ValueError:
            messagebox.showerror("Invalid ISO", "ISO min/max must be integers.", parent=self._win)
            return

        film_type = self._var_type.get()
        process = self._var_process.get()

        if query:
            films = self._catalog.search(query)
            # apply remaining filters on top of search
            if iso_min is not None:
                films = [f for f in films if f.iso >= iso_min]
            if iso_max is not None:
                films = [f for f in films if f.iso <= iso_max]
            if film_type:
                films = [f for f in films if f.type == film_type]
            if process:
                films = [f for f in films if f.process == process]
        else:
            films = self._catalog.filter(
                iso_min=iso_min,
                iso_max=iso_max,
                film_type=film_type or None,
                process=process or None,
            )

        self._tree.delete(*self._tree.get_children())
        for film in films:
            self._tree.insert(
                "", "end",
                iid=film.id,
                values=(
                    film.name,
                    film.manufacturer,
                    _TYPE_LABELS.get(film.type, film.type),
                    film.iso,
                    film.process,
                    "Yes" if film.is_push_pull_sensitive else "",
                ),
            )

        self._lbl_notes.config(text="")
        self._lbl_warning.config(text="")

    def _on_select(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        sel = self._tree.selection()
        if not sel:
            return
        film = self._catalog.get_by_id(sel[0])
        if film is None:
            return
        self._lbl_notes.config(text=film.notes or "")
        warning = film.exposure_warning
        self._lbl_warning.config(text=(f"\u26a0\ufe0f  {warning}") if warning else "")

    def _open_recommend(self) -> None:
        RecommendDialog(self._win, self._catalog)


# ---------------------------------------------------------------------------
# Recommendation Dialog
# ---------------------------------------------------------------------------

class RecommendDialog(BaseDialog):
    _SCENARIO_LABELS = [
        ("portrait", "Portrait"),
        ("low_light", "Low Light"),
        ("landscape", "Landscape"),
        ("budget", "Budget"),
        ("night", "Night"),
    ]

    def __init__(self, parent: tk.Toplevel, catalog: FilmCatalog) -> None:
        self._catalog = catalog
        self._init_window(parent, "Film Recommendations", 540, 440)
        self._var_scenario = tk.StringVar(value="portrait")
        self._build()
        self._run()
        self._win.grab_set()

    def _build(self) -> None:
        outer = ttk.Frame(self._win, padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Select shooting scenario:", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")

        radio_frame = ttk.Frame(outer)
        radio_frame.pack(anchor="w", pady=(4, 8))
        for value, label in self._SCENARIO_LABELS:
            ttk.Radiobutton(
                radio_frame, text=label,
                variable=self._var_scenario, value=value,
                command=self._run,
            ).pack(side="left", padx=6)

        ttk.Separator(outer).pack(fill="x", pady=(0, 8))

        self._text = tk.Text(
            outer, wrap="word", height=18, relief="flat",
            font=("TkDefaultFont", 9),
        )
        self._text.pack(fill="both", expand=True)
        self._text.tag_configure("film", font=("TkDefaultFont", 9, "bold"))
        self._text.tag_configure("warn", foreground="#b45309")
        self._text.configure(state="disabled")

        ttk.Button(outer, text="Close", command=self._win.destroy).pack(pady=(8, 0), anchor="e")

    def _run(self) -> None:
        scenario = self._var_scenario.get()
        results = self._catalog.recommend(scenario)
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        for i, (film, explanation) in enumerate(results, 1):
            self._text.insert("end", f"{i}. {film.name}", "film")
            lines = explanation.split("\n")
            first_line = lines[0]
            self._text.insert("end", f"\n   {first_line}\n")
            for extra in lines[1:]:
                self._text.insert("end", f"   {extra}\n", "warn")
            self._text.insert("end", "\n")
        self._text.configure(state="disabled")


# ---------------------------------------------------------------------------
# Roll Tracker Window
# ---------------------------------------------------------------------------

_STATUS_COLORS: dict[str, str] = {
    "loaded": "#2563eb",      # blue
    "in_progress": "#d97706", # amber
    "finished": "#16a34a",    # green
    "developed": "#7c3aed",   # purple
}


class RollTrackerWindow(BaseDialog):
    def __init__(self, parent: tk.Tk, catalog: FilmCatalog, roll_log: RollLog) -> None:
        self._catalog = catalog
        self._roll_log = roll_log
        self._init_window(parent, "Roll Tracker", 820, 520, min_width=700, min_height=420)
        self._selected_roll_id: str | None = None
        self._build()
        self._refresh()
        self._win.grab_set()

    def _build(self) -> None:
        outer = ttk.Frame(self._win, padding=10)
        outer.pack(fill="both", expand=True)

        # ── treeview ──────────────────────────────────────────────────────
        cols = ("film", "camera", "frames", "status", "date_loaded")
        tree_frame = ttk.Frame(outer)
        tree_frame.pack(fill="both", expand=True)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings", selectmode="browse",
        )
        for col, heading, width in [
            ("film", "Film", 200),
            ("camera", "Camera", 160),
            ("frames", "Frames", 60),
            ("status", "Status", 100),
            ("date_loaded", "Loaded", 100),
        ]:
            self._tree.heading(col, text=heading)
            self._tree.column(col, width=width, minwidth=40, anchor="w")
        self._tree.column("frames", anchor="e")

        for status, color in _STATUS_COLORS.items():
            self._tree.tag_configure(status, foreground=color)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # ── detail / notes ────────────────────────────────────────────────
        detail = ttk.LabelFrame(outer, text="Notes / Details", padding=(8, 4))
        detail.pack(fill="x", pady=(6, 4))
        self._lbl_detail = ttk.Label(detail, text="", wraplength=780, justify="left")
        self._lbl_detail.pack(anchor="w")

        # ── action bar ────────────────────────────────────────────────────
        bar = ttk.Frame(outer)
        bar.pack(fill="x")
        self._btn_frame   = ttk.Button(bar, text="+ Frame",       command=self._cmd_frame)
        self._btn_finish  = ttk.Button(bar, text="Mark Finished", command=self._cmd_finish)
        self._btn_develop = ttk.Button(bar, text="Set Developed", command=self._cmd_develop)
        self._btn_note    = ttk.Button(bar, text="Add Note",      command=self._cmd_note)

        ttk.Button(bar, text="New Roll", command=self._cmd_new_roll).pack(side="left", padx=(0, 4))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=6)
        self._btn_frame.pack(side="left", padx=2)
        self._btn_finish.pack(side="left", padx=2)
        self._btn_develop.pack(side="left", padx=2)
        self._btn_note.pack(side="left", padx=2)
        self._set_action_buttons_state("disabled")

    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for roll in self._roll_log.list_rolls():
            film = self._catalog.get_by_id(roll.film_id)
            film_name = film.name if film else roll.film_id
            self._tree.insert(
                "", "end",
                iid=roll.roll_id,
                tags=(roll.status,),
                values=(film_name, roll.camera, roll.frames_shot, roll.status.replace("_", " "), roll.date_loaded),
            )
        self._lbl_detail.config(text="")
        self._set_action_buttons_state("disabled")
        self._selected_roll_id = None

    def _on_select(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        sel = self._tree.selection()
        if not sel:
            return
        self._selected_roll_id = sel[0]
        roll = self._roll_log.get_roll(self._selected_roll_id)
        if roll is None:
            return
        parts = []
        if roll.lens:
            parts.append(f"Lens: {roll.lens}")
        if roll.location:
            parts.append(f"Location: {roll.location}")
        if roll.lab:
            parts.append(f"Lab: {roll.lab}")
        if roll.scanned:
            parts.append("Scanned")
        if roll.notes:
            parts.append(f"Notes: {roll.notes}")
        self._lbl_detail.config(text="  |  ".join(parts) if parts else "No additional details.")
        self._set_action_buttons_state("normal")

    def _set_action_buttons_state(self, state: str) -> None:
        for btn in (self._btn_frame, self._btn_finish, self._btn_develop, self._btn_note):
            btn.config(state=state)

    def _require_selection(self) -> str | None:
        if not self._selected_roll_id:
            messagebox.showinfo("No Selection", "Select a roll first.", parent=self._win)
            return None
        return self._selected_roll_id

    def _cmd_new_roll(self) -> None:
        NewRollDialog(self._win, self._catalog, self._roll_log, on_created=self._refresh)

    def _cmd_frame(self) -> None:
        roll_id = self._require_selection()
        if roll_id is None:
            return
        try:
            self._roll_log.increment_frame(roll_id)
            self._refresh()
            self._tree.selection_set(roll_id)
            self._tree.see(roll_id)
        except ValueError as exc:
            messagebox.showerror("Error", str(exc), parent=self._win)

    def _cmd_finish(self) -> None:
        roll_id = self._require_selection()
        if roll_id is None:
            return
        try:
            self._roll_log.mark_finished(roll_id)
            self._refresh()
        except ValueError as exc:
            messagebox.showerror("Error", str(exc), parent=self._win)

    def _cmd_develop(self) -> None:
        roll_id = self._require_selection()
        if roll_id is None:
            return
        lab = simpledialog.askstring("Lab", "Lab name (optional):", parent=self._win)
        try:
            self._roll_log.set_developed(roll_id, lab=lab)
            self._refresh()
        except ValueError as exc:
            messagebox.showerror("Error", str(exc), parent=self._win)

    def _cmd_note(self) -> None:
        roll_id = self._require_selection()
        if roll_id is None:
            return
        note = simpledialog.askstring("Add Note", "Enter note:", parent=self._win)
        if not note or not note.strip():
            return
        try:
            self._roll_log.attach_note(roll_id, note)
            self._refresh()
            self._tree.selection_set(roll_id)
            self._on_select(None)  # type: ignore[arg-type]
        except ValueError as exc:
            messagebox.showerror("Error", str(exc), parent=self._win)


# ---------------------------------------------------------------------------
# New Roll Dialog
# ---------------------------------------------------------------------------

class NewRollDialog(BaseDialog):
    def __init__(
        self,
        parent: tk.Toplevel,
        catalog: FilmCatalog,
        roll_log: RollLog,
        on_created: object,
    ) -> None:
        self._catalog = catalog
        self._roll_log = roll_log
        self._on_created = on_created
        self._all_films = catalog.filter()
        self._init_window(parent, "New Roll", 420, 400, resizable=(False, True))

        self._var_search = tk.StringVar()
        self._var_camera = tk.StringVar()
        self._var_lens   = tk.StringVar()
        self._var_loc    = tk.StringVar()
        self._selected_film: FilmStock | None = None

        self._build()
        self._win.grab_set()

    def _build(self) -> None:
        outer = ttk.Frame(self._win, padding=12)
        outer.pack(fill="both", expand=True)

        # Film search
        ttk.Label(outer, text="Film (type to filter):").pack(anchor="w")
        ttk.Entry(outer, textvariable=self._var_search).pack(fill="x", pady=(2, 4))
        self._var_search.trace_add("write", self._on_search_change)

        film_frame = ttk.Frame(outer)
        film_frame.pack(fill="both", expand=True)
        film_frame.columnconfigure(0, weight=1)
        film_frame.rowconfigure(0, weight=1)

        self._lb = tk.Listbox(film_frame, exportselection=False)
        lbvsb = ttk.Scrollbar(film_frame, orient="vertical", command=self._lb.yview)
        self._lb.configure(yscrollcommand=lbvsb.set)
        self._lb.grid(row=0, column=0, sticky="nsew")
        lbvsb.grid(row=0, column=1, sticky="ns")
        self._lb.bind("<<ListboxSelect>>", self._on_film_pick)
        self._populate_listbox(self._all_films)

        self._lbl_film = ttk.Label(outer, text="", foreground="#2563eb")
        self._lbl_film.pack(anchor="w", pady=(4, 0))

        # Camera / lens / location
        form = ttk.Frame(outer)
        form.pack(fill="x", pady=(6, 0))
        form.columnconfigure(1, weight=1)

        for row, (label, var) in enumerate([
            ("Camera *:", self._var_camera),
            ("Lens:",     self._var_lens),
            ("Location:", self._var_loc),
        ]):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=2, padx=(0, 6))
            ttk.Entry(form, textvariable=var).grid(row=row, column=1, sticky="ew", pady=2)

        # Buttons
        btn_row = ttk.Frame(outer)
        btn_row.pack(anchor="e", pady=(10, 0))
        ttk.Button(btn_row, text="Cancel", command=self._win.destroy).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Create Roll", command=self._submit).pack(side="left")

    def _populate_listbox(self, films: list[FilmStock]) -> None:
        self._lb.delete(0, "end")
        for film in films:
            self._lb.insert("end", f"{film.name}  (ISO {film.iso}, {film.process})")
        self._listbox_films = films

    def _on_search_change(self, *_: object) -> None:
        q = self._var_search.get().strip()
        if q:
            results = self._catalog.search(q)
        else:
            results = self._all_films
        self._populate_listbox(results)
        self._selected_film = None
        self._lbl_film.config(text="")

    def _on_film_pick(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        sel = self._lb.curselection()
        if not sel:
            return
        self._selected_film = self._listbox_films[sel[0]]
        self._lbl_film.config(text=f"Selected: {self._selected_film.name}")

    def _submit(self) -> None:
        if self._selected_film is None:
            messagebox.showerror("No Film", "Please select a film stock.", parent=self._win)
            return
        camera = self._var_camera.get().strip()
        if not camera:
            messagebox.showerror("Camera Required", "Please enter a camera name.", parent=self._win)
            return
        try:
            self._roll_log.create_roll(
                film_id=self._selected_film.id,
                camera=camera,
                lens=self._var_lens.get() or None,
                location=self._var_loc.get() or None,
            )
            self._win.destroy()
            if callable(self._on_created):
                self._on_created()
        except ValueError as exc:
            messagebox.showerror("Error", str(exc), parent=self._win)


# ---------------------------------------------------------------------------


def main() -> None:
    root = tb.Window(themename="litera")
    app = FilmTrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
