from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, simpledialog, ttk

from db import FilmDatabase


class FilmTrackerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("35mm Film Shot Tracker")
        self.root.geometry("1100x650")
        self.root.minsize(900, 560)

        self.db = FilmDatabase("data/film_tracker.db")

        self.selected_collection_id: int | None = None
        self.selected_shot_id: int | None = None

        self.collection_map: dict[str, int] = {}

        self._build_ui()
        self._load_collections()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        container = ttk.Frame(self.root, padding=12)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=3)
        container.rowconfigure(0, weight=1)

        self._build_collection_panel(container)
        self._build_shot_panel(container)

    def _build_collection_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Roll Collections", padding=10)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(0, weight=1)

        self.collection_list = tk.Listbox(panel, exportselection=False)
        self.collection_list.grid(row=0, column=0, sticky="nsew")
        self.collection_list.bind("<<ListboxSelect>>", self._on_collection_selected)

        scrollbar = ttk.Scrollbar(panel, orient="vertical", command=self.collection_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.collection_list.configure(yscrollcommand=scrollbar.set)

        buttons = ttk.Frame(panel)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        buttons.columnconfigure(2, weight=1)

        ttk.Button(buttons, text="Add", command=self._add_collection).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(buttons, text="Rename", command=self._rename_collection).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(buttons, text="Delete", command=self._delete_collection).grid(row=0, column=2, sticky="ew", padx=(4, 0))

    def _build_shot_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Shots", padding=10)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        self.collection_hint_var = tk.StringVar(value="Select or add a roll collection to begin.")
        ttk.Label(panel, textvariable=self.collection_hint_var).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.shot_tree = ttk.Treeview(
            panel,
            columns=("frame", "shutter", "fstop", "date", "notes"),
            show="headings",
            selectmode="browse",
            height=12,
        )
        self.shot_tree.heading("frame", text="Frame")
        self.shot_tree.heading("shutter", text="Shutter Speed")
        self.shot_tree.heading("fstop", text="F-Stop")
        self.shot_tree.heading("date", text="Shot Date")
        self.shot_tree.heading("notes", text="Notes")

        self.shot_tree.column("frame", width=70, anchor="center")
        self.shot_tree.column("shutter", width=120, anchor="center")
        self.shot_tree.column("fstop", width=90, anchor="center")
        self.shot_tree.column("date", width=120, anchor="center")
        self.shot_tree.column("notes", width=320, anchor="w")

        self.shot_tree.grid(row=1, column=0, sticky="nsew")
        self.shot_tree.bind("<<TreeviewSelect>>", self._on_shot_selected)

        shot_scroll = ttk.Scrollbar(panel, orient="vertical", command=self.shot_tree.yview)
        shot_scroll.grid(row=1, column=1, sticky="ns")
        self.shot_tree.configure(yscrollcommand=shot_scroll.set)

        form = ttk.LabelFrame(panel, text="Shot Details", padding=10)
        form.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        for idx in range(6):
            form.columnconfigure(idx, weight=1)

        ttk.Label(form, text="Shutter Speed *").grid(row=0, column=0, sticky="w")
        self.shutter_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.shutter_var).grid(row=1, column=0, sticky="ew", padx=(0, 8))

        ttk.Label(form, text="F-Stop *").grid(row=0, column=1, sticky="w")
        self.fstop_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.fstop_var).grid(row=1, column=1, sticky="ew", padx=(0, 8))

        ttk.Label(form, text="Frame #").grid(row=0, column=2, sticky="w")
        self.frame_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.frame_var).grid(row=1, column=2, sticky="ew", padx=(0, 8))

        ttk.Label(form, text="Shot Date (YYYY-MM-DD)").grid(row=0, column=3, sticky="w")
        self.date_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.date_var).grid(row=1, column=3, sticky="ew", padx=(0, 8))

        ttk.Label(form, text="Notes").grid(row=0, column=4, sticky="w")
        self.notes_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.notes_var).grid(row=1, column=4, sticky="ew", padx=(0, 8))

        buttons = ttk.Frame(form)
        buttons.grid(row=1, column=5, sticky="ew")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        buttons.columnconfigure(2, weight=1)

        ttk.Button(buttons, text="Save Shot", command=self._save_shot).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(buttons, text="Delete Shot", command=self._delete_shot).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(buttons, text="Clear", command=self._clear_shot_form).grid(row=0, column=2, sticky="ew", padx=(4, 0))

    # Collections
    def _load_collections(self) -> None:
        collections = self.db.list_collections()

        self.collection_list.delete(0, tk.END)
        self.collection_map.clear()

        for row in collections:
            label = row["name"]
            self.collection_list.insert(tk.END, label)
            self.collection_map[label] = int(row["id"])

        if self.selected_collection_id is not None:
            self._restore_collection_selection()

    def _restore_collection_selection(self) -> None:
        for idx in range(self.collection_list.size()):
            label = self.collection_list.get(idx)
            if self.collection_map.get(label) == self.selected_collection_id:
                self.collection_list.selection_clear(0, tk.END)
                self.collection_list.selection_set(idx)
                self.collection_list.activate(idx)
                self.collection_list.see(idx)
                return

        self.selected_collection_id = None
        self._load_shots_for_selected_collection()

    def _get_selected_collection_id(self) -> int | None:
        selection = self.collection_list.curselection()
        if not selection:
            return None
        label = self.collection_list.get(selection[0])
        return self.collection_map.get(label)

    def _on_collection_selected(self, _event: object) -> None:
        self.selected_collection_id = self._get_selected_collection_id()
        self.selected_shot_id = None
        self._clear_shot_form()
        self._load_shots_for_selected_collection()

    def _add_collection(self) -> None:
        name = simpledialog.askstring(
            "New Roll Collection",
            "Enter roll collection name (e.g., Portra 400 - Roll 3):",
            parent=self.root,
        )
        if name is None:
            return

        cleaned = name.strip()
        if not cleaned:
            messagebox.showerror("Invalid Name", "Collection name cannot be empty.")
            return

        try:
            new_id = self.db.create_collection(cleaned)
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not create collection.\n\n{exc}")
            return

        self.selected_collection_id = new_id
        self._load_collections()
        self._load_shots_for_selected_collection()

    def _rename_collection(self) -> None:
        collection_id = self._get_selected_collection_id()
        if collection_id is None:
            messagebox.showinfo("Select Collection", "Select a collection to rename.")
            return

        current_name = self.collection_list.get(self.collection_list.curselection()[0])
        new_name = simpledialog.askstring(
            "Rename Collection",
            "New collection name:",
            parent=self.root,
            initialvalue=current_name,
        )
        if new_name is None:
            return

        cleaned = new_name.strip()
        if not cleaned:
            messagebox.showerror("Invalid Name", "Collection name cannot be empty.")
            return

        try:
            self.db.rename_collection(collection_id, cleaned)
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not rename collection.\n\n{exc}")
            return

        self.selected_collection_id = collection_id
        self._load_collections()

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
        self.selected_shot_id = None
        self._clear_shot_form()
        self._load_collections()
        self._load_shots_for_selected_collection()

    # Shots
    def _load_shots_for_selected_collection(self) -> None:
        self.shot_tree.delete(*self.shot_tree.get_children())

        if self.selected_collection_id is None:
            self.collection_hint_var.set("Select or add a roll collection to begin.")
            return

        selected_label = ""
        selection = self.collection_list.curselection()
        if selection:
            selected_label = self.collection_list.get(selection[0])

        shots = self.db.list_shots_for_collection(self.selected_collection_id)
        self.collection_hint_var.set(f"Collection: {selected_label} ({len(shots)} shot(s))")

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
                    shot["shutter_speed"],
                    shot["f_stop"],
                    date,
                    notes,
                ),
            )

    def _on_shot_selected(self, _event: object) -> None:
        selection = self.shot_tree.selection()
        if not selection:
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
        self.notes_var.set(row["notes"] or "")

    def _validate_shot_fields(self) -> tuple[str, str, int | None, str | None, str | None] | None:
        shutter = self.shutter_var.get().strip()
        f_stop = self.fstop_var.get().strip()
        frame_raw = self.frame_var.get().strip()
        shot_date_raw = self.date_var.get().strip()
        notes_raw = self.notes_var.get().strip()

        if not shutter:
            messagebox.showerror("Validation Error", "Shutter speed is required.")
            return None
        if not f_stop:
            messagebox.showerror("Validation Error", "F-stop is required.")
            return None

        frame_value: int | None = None
        if frame_raw:
            try:
                frame_value = int(frame_raw)
            except ValueError:
                messagebox.showerror("Validation Error", "Frame number must be a whole number.")
                return None

            if frame_value <= 0:
                messagebox.showerror("Validation Error", "Frame number must be greater than zero.")
                return None

        shot_date: str | None = None
        if shot_date_raw:
            try:
                datetime.strptime(shot_date_raw, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Validation Error", "Shot date must be in YYYY-MM-DD format.")
                return None
            shot_date = shot_date_raw

        notes = notes_raw if notes_raw else None
        return shutter, f_stop, frame_value, shot_date, notes

    def _save_shot(self) -> None:
        if self.selected_collection_id is None:
            messagebox.showinfo("Select Collection", "Select a collection before saving a shot.")
            return

        validated = self._validate_shot_fields()
        if validated is None:
            return

        shutter, f_stop, frame_number, shot_date, notes = validated

        try:
            if self.selected_shot_id is None:
                self.db.create_shot(
                    self.selected_collection_id,
                    shutter,
                    f_stop,
                    frame_number,
                    shot_date,
                    notes,
                )
            else:
                self.db.update_shot(
                    self.selected_shot_id,
                    shutter,
                    f_stop,
                    frame_number,
                    shot_date,
                    notes,
                )
        except Exception as exc:
            # Surface unique frame constraint collisions and other DB errors clearly.
            messagebox.showerror("Database Error", f"Could not save shot.\n\n{exc}")
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
        self.notes_var.set("")
        self.shot_tree.selection_remove(self.shot_tree.selection())


def main() -> None:
    root = tk.Tk()
    app = FilmTrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
