from __future__ import annotations

import csv
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
import ttkbootstrap as tb

from db import FilmDatabase


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


class CameraLensManagerDialog:
    def __init__(
        self,
        parent: tk.Tk,
        title: str,
        items: list[str],
    ) -> None:
        self.parent = parent
        self.result: list[str] | None = None

        self.window = tb.Toplevel(parent)
        self.window.title(title)
        self.window.transient(parent)
        self.window.grab_set()
        self.window.resizable(True, True)
        self.window.geometry("400x350")

        body = ttk.Frame(self.window, padding=12)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)

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

        self.window.bind("<Return>", self._on_return)
        self.window.bind("<Escape>", self._on_escape)

    def _on_return(self, _event: tk.Event) -> None:
        # Only add if we're in the entry field, don't save on return
        if self.window.focus_get() == self.new_item_entry:
            self._add_item()

    def _on_escape(self, _event: tk.Event) -> None:
        self._cancel()

    def _add_item(self) -> None:
        new_item = self.new_item_var.get().strip()
        if not new_item:
            messagebox.showwarning("Empty Item", "Please enter a name before adding.", parent=self.window)
            return

        # Check for duplicates
        existing_items = self.listbox.get(0, tk.END)
        if new_item in existing_items:
            messagebox.showwarning("Duplicate", f"'{new_item}' already exists.", parent=self.window)
            return

        self.listbox.insert(tk.END, new_item)
        self.new_item_var.set("")
        self.new_item_entry.focus_set()

    def _remove_item(self) -> None:
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select an item to remove.", parent=self.window)
            return
        self.listbox.delete(selection[0])

    def _cancel(self) -> None:
        self.result = None
        self.window.destroy()

    def _ok(self) -> None:
        self.result = list(self.listbox.get(0, tk.END))
        self.window.destroy()

    def show(self) -> list[str] | None:
        self.parent.wait_window(self.window)
        return self.result


class CollectionMetadataDialog:
    def __init__(
        self,
        parent: tk.Tk,
        title: str,
        initial: dict[str, str],
        camera_presets: list[str],
        lens_presets: list[str],
    ) -> None:
        self.parent = parent
        self.result: dict[str, str] | None = None

        self.window = tb.Toplevel(parent)
        self.window.title(title)
        self.window.transient(parent)
        self.window.grab_set()
        self.window.resizable(False, False)

        body = ttk.Frame(self.window, padding=12)
        body.grid(row=0, column=0, sticky="nsew")

        labels = (
            ("Collection Name *", "name"),
            ("Film Stock", "film_stock"),
            ("ISO", "iso"),
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

        help_text = "Optional fields can be left blank. ISO must be a positive whole number."
        ttk.Label(body, text=help_text).grid(row=len(labels), column=0, columnspan=2, sticky="w", pady=(6, 0))

        buttons = ttk.Frame(body)
        buttons.grid(row=len(labels) + 1, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self._cancel).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="Save", command=self._save).grid(row=0, column=1)

        self.window.bind("<Return>", self._on_return)
        self.window.bind("<Escape>", self._on_escape)

    def _on_return(self, _event: tk.Event) -> None:
        self._save()

    def _on_escape(self, _event: tk.Event) -> None:
        self._cancel()

    def _cancel(self) -> None:
        self.result = None
        self.window.destroy()

    def _save(self) -> None:
        name = self.vars["name"].get().strip()
        if not name:
            messagebox.showerror("Validation Error", "Collection name cannot be empty.", parent=self.window)
            return

        iso_raw = self.vars["iso"].get().strip()
        if iso_raw:
            try:
                ValidationUtils.parse_optional_iso(iso_raw)
            except ValueError as exc:
                messagebox.showerror("Validation Error", str(exc), parent=self.window)
                return

        self.result = {
            "name": name,
            "film_stock": self.vars["film_stock"].get().strip(),
            "iso": iso_raw,
            "camera": self.vars["camera"].get().strip(),
            "lens": self.vars["lens"].get().strip(),
            "lab": self.vars["lab"].get().strip(),
            "push_pull": self.vars["push_pull"].get().strip(),
        }
        self.window.destroy()

    def show(self) -> dict[str, str] | None:
        self.parent.wait_window(self.window)
        return self.result


class FilmTrackerApp:
    STATUS_VALUES = ("shot", "developed", "scanned", "edited", "printed")
    DEFAULT_PREFERENCES = {
        "default_shot_status": "shot",
        "default_status_filter": "all",
        "save_next_clear_notes": "true",
        "enable_ctrl_enter_save_next": "true",
        "show_collection_metadata_header": "true",
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
        self.preferences = dict(self.DEFAULT_PREFERENCES)
        self._load_preferences()

        last_selected_id = self.preferences.get("last_selected_collection_id", "").strip()
        self.selected_collection_id: int | None = int(last_selected_id) if last_selected_id.isdigit() else None
        self.selected_shot_id: int | None = None
        self.active_status_filter = tk.StringVar(value=self.preferences["default_status_filter"])

        self.collection_id_to_item: dict[int, str] = {}
        self.collection_id_to_label: dict[int, str] = {}

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

        container = ttk.Frame(self.root, padding=12)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=4)
        container.rowconfigure(0, weight=1)

        self._build_collection_panel(container)
        self._build_shot_panel(container)

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)

        app_menu = tk.Menu(menubar, tearoff=False)
        app_menu.add_command(label="Preferences", command=self._open_preferences_window)
        app_menu.add_separator()
        app_menu.add_command(label="Quit", command=self.root.quit)

        menubar.add_cascade(label="App", menu=app_menu)
        self.root.config(menu=menubar)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("litera")
        base_font = tkfont.nametofont("TkDefaultFont")
        input_font = base_font.copy()
        input_font.configure(size=base_font.cget("size") + 1)
        self.input_font = input_font

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
    def _manage_camera_presets(self, var: tk.StringVar) -> None:
        current_list = self._get_preset_list("camera_presets")
        dialog = CameraLensManagerDialog(self.root, "Cameras", current_list)
        result = dialog.show()
        if result is not None:
            self._set_preset_list("camera_presets", result)
            var.set(", ".join(result))

    def _manage_lens_presets(self, var: tk.StringVar) -> None:
        current_list = self._get_preset_list("lens_presets")
        dialog = CameraLensManagerDialog(self.root, "Lenses", current_list)
        result = dialog.show()
        if result is not None:
            self._set_preset_list("lens_presets", result)
            var.set(", ".join(result))


    def _build_collection_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Roll Collections", padding=10)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(0, weight=1)

        self.collection_list = ttk.Treeview(panel, columns=("label",), show="headings", selectmode="browse", height=18)
        self.collection_list.heading("label", text="Collection")
        self.collection_list.column("label", anchor="w")
        self.collection_list.grid(row=0, column=0, sticky="nsew")
        self.collection_list.bind("<<TreeviewSelect>>", self._on_collection_selected)

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

    def _build_shot_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Shots", padding=10)
        panel.grid(row=0, column=1, sticky="nsew")
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

        controls = ttk.Frame(panel)
        controls.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
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

        form = ttk.LabelFrame(panel, text="Shot Details", padding=10)
        form.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
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
        self.shutter_entry = ttk.Entry(form, textvariable=self.shutter_var, style="Large.TEntry")
        self.shutter_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))

        ttk.Label(form, text="F-Stop *").grid(row=0, column=1, sticky="w")
        self.fstop_var = tk.StringVar()
        self.fstop_entry = ttk.Entry(form, textvariable=self.fstop_var, style="Large.TEntry")
        self.fstop_entry.grid(row=1, column=1, sticky="ew", padx=(0, 8))

        ttk.Label(form, text="Frame #").grid(row=0, column=2, sticky="w")
        self.frame_var = tk.StringVar()
        self.frame_entry = ttk.Entry(form, textvariable=self.frame_var, style="Large.TEntry")
        self.frame_entry.grid(row=1, column=2, sticky="ew", padx=(0, 8))

        ttk.Label(form, text="Shot Date").grid(row=0, column=3, sticky="w")
        self.date_var = tk.StringVar()
        self.date_entry = ttk.Entry(form, textvariable=self.date_var, style="Large.TEntry", width=12)
        self.date_entry.grid(row=1, column=3, sticky="ew", padx=(0, 8))

        ttk.Label(form, text="Notes").grid(row=0, column=4, columnspan=4, sticky="w")
        self.notes_text = tk.Text(form, height=3, wrap="word", font=self.input_font)
        self.notes_text.grid(row=1, column=4, columnspan=4, sticky="ew")

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

        ttk.Button(buttons, text="Save Shot", command=self._save_shot).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(buttons, text="Save + Next", command=self._save_shot_and_next).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(buttons, text="Delete Shot", command=self._delete_shot).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(buttons, text="Clear", command=self._clear_shot_form).grid(row=0, column=3, sticky="ew", padx=(4, 0))

    def _on_status_filter_changed(self, _event: object) -> None:
        self._load_shots_for_selected_collection()

    def _open_preferences_window(self) -> None:
        window = tb.Toplevel(self.root)
        window.title("Preferences")
        window.transient(self.root)
        window.grab_set()
        window.minsize(560, 360)

        content = ttk.Frame(window, padding=12)
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(content)
        notebook.grid(row=0, column=0, sticky="nsew")

        general_tab = ttk.Frame(notebook, padding=12)
        quick_tab = ttk.Frame(notebook, padding=12)
        metadata_tab = ttk.Frame(notebook, padding=12)
        workflow_tab = ttk.Frame(notebook, padding=12)

        notebook.add(general_tab, text="General")
        notebook.add(quick_tab, text="Quick Entry")
        notebook.add(metadata_tab, text="Metadata")
        notebook.add(workflow_tab, text="Workflow")

        default_status_var = tk.StringVar(value=self.preferences["default_shot_status"])
        default_filter_var = tk.StringVar(value=self.preferences["default_status_filter"])
        clear_notes_var = tk.BooleanVar(value=self._preference_bool("save_next_clear_notes"))
        ctrl_enter_var = tk.BooleanVar(value=self._preference_bool("enable_ctrl_enter_save_next"))
        show_metadata_var = tk.BooleanVar(value=self._preference_bool("show_collection_metadata_header"))
        camera_presets_var = tk.StringVar(value=", ".join(self._get_preset_list("camera_presets")))
        lens_presets_var = tk.StringVar(value=", ".join(self._get_preset_list("lens_presets")))

        ttk.Label(general_tab, text="Default shot status for new entries").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            general_tab,
            textvariable=default_status_var,
            values=self.STATUS_VALUES,
            state="readonly",
            width=16,
        ).grid(row=1, column=0, sticky="w", pady=(4, 12))

        ttk.Label(general_tab, text="Default status filter when app starts").grid(row=2, column=0, sticky="w")
        ttk.Combobox(
            general_tab,
            textvariable=default_filter_var,
            values=("all", *self.STATUS_VALUES),
            state="readonly",
            width=16,
        ).grid(row=3, column=0, sticky="w", pady=(4, 12))

        ttk.Label(
            general_tab,
            text="Use these defaults to match your most common workflow.",
        ).grid(row=4, column=0, sticky="w")

        ttk.Checkbutton(
            quick_tab,
            text="Enable Ctrl+Enter to Save + Next",
            variable=ctrl_enter_var,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        ttk.Checkbutton(
            quick_tab,
            text="Clear notes after Save + Next",
            variable=clear_notes_var,
        ).grid(row=1, column=0, sticky="w", pady=(0, 8))

        ttk.Label(
            quick_tab,
            text="Quick Entry is designed for rapid frame-by-frame logging while shooting.",
        ).grid(row=2, column=0, sticky="w")

        ttk.Checkbutton(
            metadata_tab,
            text="Show collection metadata summary in shot header",
            variable=show_metadata_var,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        ttk.Label(
            metadata_tab,
            text="Metadata helps identify film stock, camera, and lens context while reviewing shots.",
        ).grid(row=1, column=0, sticky="w")

        ttk.Label(metadata_tab, text="Camera presets").grid(row=2, column=0, sticky="w", pady=(12, 0))
        camera_preset_frame = ttk.Frame(metadata_tab)
        camera_preset_frame.grid(row=3, column=0, sticky="ew", pady=(4, 8))
        camera_preset_frame.columnconfigure(0, weight=1)
        ttk.Entry(camera_preset_frame, textvariable=camera_presets_var, width=40).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(
            camera_preset_frame,
            text="Manage",
            command=lambda: self._manage_camera_presets(camera_presets_var),
            width=10,
        ).grid(row=0, column=1, sticky="ew")

        ttk.Label(metadata_tab, text="Lens presets").grid(row=4, column=0, sticky="w")
        lens_preset_frame = ttk.Frame(metadata_tab)
        lens_preset_frame.grid(row=5, column=0, sticky="ew", pady=(4, 0))
        lens_preset_frame.columnconfigure(0, weight=1)
        ttk.Entry(lens_preset_frame, textvariable=lens_presets_var, width=40).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(
            lens_preset_frame,
            text="Manage",
            command=lambda: self._manage_lens_presets(lens_presets_var),
            width=10,
        ).grid(row=0, column=1, sticky="ew")

        ttk.Label(workflow_tab, text="Task Tips").grid(row=0, column=0, sticky="w")
        ttk.Label(
            workflow_tab,
            text="Capture: use Save + Next for sequential frame entry.\n"
            "Review: filter by status to focus on processing stages.\n"
            "Organize: use Edit Meta to keep roll-level context complete.",
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        buttons = ttk.Frame(content)
        buttons.grid(row=1, column=0, sticky="e", pady=(12, 0))

        def apply_preferences() -> None:
            if default_status_var.get() not in self.STATUS_VALUES:
                messagebox.showerror("Validation Error", "Invalid default shot status.", parent=window)
                return
            if default_filter_var.get() not in ("all", *self.STATUS_VALUES):
                messagebox.showerror("Validation Error", "Invalid default status filter.", parent=window)
                return

            self.preferences["default_shot_status"] = default_status_var.get()
            self.preferences["default_status_filter"] = default_filter_var.get()
            self.preferences["save_next_clear_notes"] = "true" if clear_notes_var.get() else "false"
            self.preferences["enable_ctrl_enter_save_next"] = "true" if ctrl_enter_var.get() else "false"
            self.preferences["show_collection_metadata_header"] = "true" if show_metadata_var.get() else "false"
            camera_presets = [part.strip() for part in camera_presets_var.get().split(",") if part.strip()]
            lens_presets = [part.strip() for part in lens_presets_var.get().split(",") if part.strip()]
            self._set_preset_list("camera_presets", camera_presets)
            self._set_preset_list("lens_presets", lens_presets)
            self._save_preferences()

            self.active_status_filter.set(default_filter_var.get())
            self._load_shots_for_selected_collection()
            if self.selected_shot_id is None:
                self.status_var.set(self.preferences["default_shot_status"])

            window.destroy()

        ttk.Button(buttons, text="Cancel", command=window.destroy).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="Save", command=apply_preferences).grid(row=0, column=1)

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
        return result

    def _format_collection_hint(self, collection_name: str, shots_count: int) -> tuple[str, str]:
        if self.selected_collection_id is None:
            return "Select or add a roll collection to begin.", ""

        collection = self.db.get_collection(self.selected_collection_id)
        if collection is None:
            return f"Collection: {collection_name} ({shots_count} shot(s))", ""

        details: list[str] = []
        if not self._preference_bool("show_collection_metadata_header"):
            return f"Collection: {collection_name} ({shots_count} shot(s))", ""

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
        return f"Collection: {collection_name} ({shots_count} shot(s))", detail_text

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
                "camera": "",
                "lens": "",
                "lab": "",
                "push_pull": "",
            },
        )
        if details is None:
            return

        try:
            new_id = self.db.create_collection(
                details["name"],
                details["film_stock"],
                self._parse_optional_iso(details["iso"]),
                details["camera"],
                details["lens"],
                details["lab"],
                details["push_pull"],
            )
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not create collection.\n\n{exc}")
            return

        self.selected_collection_id = new_id
        self._remember_selected_collection()
        self._load_collections()
        self._load_shots_for_selected_collection()

    def _edit_collection(self) -> None:
        collection_id = self._get_selected_collection_id()
        if collection_id is None:
            messagebox.showinfo("Select Collection", "Select a collection to edit.")
            return

        row = self.db.get_collection(collection_id)
        if row is None:
            messagebox.showerror("Database Error", "Could not load collection metadata.")
            return

        details = self._prompt_collection_details(
            "Edit Collection Metadata",
            {
                "name": row["name"] or "",
                "film_stock": row["film_stock"] or "",
                "iso": "" if row["iso"] is None else str(row["iso"]),
                "camera": row["camera"] or "",
                "lens": row["lens"] or "",
                "lab": row["lab"] or "",
                "push_pull": row["push_pull"] or "",
            },
        )
        if details is None:
            return

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
            )
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not update collection metadata.\n\n{exc}")
            return

        self.selected_collection_id = collection_id
        self._remember_selected_collection()
        self._load_collections()
        self._load_shots_for_selected_collection()

    def _delete_collection(self) -> None:
        collection_id = self._get_selected_collection_id()
        if collection_id is None:
            messagebox.showinfo("Select Collection", "Select a collection to delete.")
            return

        count = self.db.shot_count_for_collection(collection_id)
        confirm = messagebox.askyesno(
            "Delete Collection",
            f"Delete this collection and its {count} shot(s)? This cannot be undone.",
        )
        if not confirm:
            return

        try:
            self.db.delete_collection(collection_id)
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not delete collection.\n\n{exc}")
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
            messagebox.showinfo("Select Collection", "Select a collection to export.")
            return

        row = self.db.get_collection(collection_id)
        collection_name = str(row["name"]) if row is not None else "collection"
        suggested_name = collection_name.replace(" ", "_").lower()

        file_path = filedialog.asksaveasfilename(
            title="Export Shots to CSV",
            defaultextension=".csv",
            initialfile=f"{suggested_name}_shots.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
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
            messagebox.showerror("Export Error", f"Could not export CSV.\n\n{exc}")
            return

        messagebox.showinfo("Export Complete", f"Exported {len(rows)} shot(s) to:\n{file_path}")

    def _import_shots_csv(self) -> None:
        collection_id = self._get_selected_collection_id()
        if collection_id is None:
            messagebox.showinfo("Select Collection", "Select a collection before importing shots.")
            return

        file_path = filedialog.askopenfilename(
            title="Import Shots from CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
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
                            }
                        )
                    except ValueError as exc:
                        parse_errors.append(f"Line {index}: {exc}")
        except Exception as exc:
            messagebox.showerror("Import Error", f"Could not read CSV file.\n\n{exc}")
            return

        if not parsed_rows and not parse_errors:
            messagebox.showinfo("Import Shots", "No rows found to import.")
            return

        inserted_count, db_errors = self.db.bulk_insert_shots(collection_id, parsed_rows)
        self._load_shots_for_selected_collection()

        messages: list[str] = [f"Imported {inserted_count} shot(s)."]
        if parse_errors:
            messages.append(f"Skipped {len(parse_errors)} row(s) due to validation errors.")
        if db_errors:
            messages.append(f"Skipped {len(db_errors)} row(s) due to database conflicts.")

        detail_lines = parse_errors[:5] + db_errors[:5]
        detail_text = ""
        if detail_lines:
            detail_text = "\n\nDetails (first 5):\n" + "\n".join(detail_lines)

        messagebox.showinfo("Import Complete", "\n".join(messages) + detail_text)

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
        headline, metadata = self._format_collection_hint(selected_label, len(shots))
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
            self.selected_shot_id = None
            return

        shot_id = int(selection[0])
        row = self.db.get_shot(shot_id)
        if row is None:
            self.selected_shot_id = None
            return

        self.selected_shot_id = shot_id
        self.shutter_var.set(row["shutter_speed"])
        self.fstop_var.set(row["f_stop"])
        self.frame_var.set("" if row["frame_number"] is None else str(row["frame_number"]))
        self.date_var.set(row["shot_date"] or "")
        self._set_notes_text(row["notes"] or "")
        self.status_var.set(row["status"] or "shot")

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
            messagebox.showerror("Validation Error", "Shutter speed is required.")
            return None
        if not f_stop:
            messagebox.showerror("Validation Error", "F-stop is required.")
            return None

        frame_value: int | None = None
        if frame_raw:
            try:
                frame_value = ValidationUtils.parse_optional_frame(frame_raw)
            except ValueError as exc:
                messagebox.showerror("Validation Error", str(exc))
                return None

            if self.selected_collection_id is not None and self.db.frame_number_exists(
                self.selected_collection_id,
                frame_value,
                exclude_shot_id=self.selected_shot_id,
            ):
                messagebox.showerror(
                    "Validation Error",
                    f"Frame {frame_value} already exists in this collection.",
                )
                return None

        shot_date: str | None = None
        if shot_date_raw:
            try:
                shot_date = ValidationUtils.parse_optional_date(shot_date_raw)
            except ValueError:
                messagebox.showerror("Validation Error", "Shot date must be in YYYY-MM-DD format.")
                return None

        if status_raw not in self.STATUS_VALUES:
            messagebox.showerror("Validation Error", "Invalid shot status.")
            return None

        notes = notes_raw if notes_raw else None
        return shutter, f_stop, frame_value, shot_date, notes, status_raw

    def _save_shot_and_next(self) -> None:
        self._save_shot(save_and_next=True)

    def _save_shot(self, save_and_next: bool = False) -> None:
        if self.selected_collection_id is None:
            messagebox.showinfo("Select Collection", "Select a collection before saving a shot.")
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
            messagebox.showerror("Database Error", f"Could not save shot.\n\n{exc}")
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
            messagebox.showinfo("Select Shots", "Select one or more shots to update status.")
            return

        status = self.bulk_status_var.get().strip()
        if status not in self.STATUS_VALUES:
            messagebox.showerror("Validation Error", "Invalid bulk status.")
            return

        try:
            shot_ids = [int(shot_id) for shot_id in selection]
            self.db.update_shot_status_many(shot_ids, status)
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not update statuses.\n\n{exc}")
            return

        self.selected_shot_id = None
        self._clear_shot_form()
        self._load_shots_for_selected_collection()

    def _apply_status_to_visible(self) -> None:
        visible_ids = self.shot_tree.get_children()
        if not visible_ids:
            messagebox.showinfo("No Shots", "There are no visible shots to update.")
            return

        status = self.bulk_status_var.get().strip()
        if status not in self.STATUS_VALUES:
            messagebox.showerror("Validation Error", "Invalid bulk status.")
            return

        confirm = messagebox.askyesno(
            "Confirm Bulk Update",
            f"Mark all {len(visible_ids)} visible shot(s) as '{status}'?",
        )
        if not confirm:
            return

        try:
            shot_ids = [int(shot_id) for shot_id in visible_ids]
            self.db.update_shot_status_many(shot_ids, status)
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not update statuses.\n\n{exc}")
            return

        self.selected_shot_id = None
        self._clear_shot_form()
        self._load_shots_for_selected_collection()

    def _delete_shot(self) -> None:
        if self.selected_shot_id is None:
            messagebox.showinfo("Select Shot", "Select a shot to delete.")
            return

        confirm = messagebox.askyesno("Delete Shot", "Delete the selected shot?")
        if not confirm:
            return

        try:
            self.db.delete_shot(self.selected_shot_id)
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not delete shot.\n\n{exc}")
            return

        self.selected_shot_id = None
        self._clear_shot_form()
        self._load_shots_for_selected_collection()

    def _clear_shot_form(self) -> None:
        self.shutter_var.set("")
        self.fstop_var.set("")
        self.frame_var.set("")
        self.date_var.set("")
        self._set_notes_text("")
        self.status_var.set(self.preferences["default_shot_status"])
        self.shot_tree.selection_remove(self.shot_tree.selection())


def main() -> None:
    root = tb.Window(themename="litera")
    app = FilmTrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
