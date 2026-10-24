from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from organizer import Move, apply_plan, build_plan, count_protected_files


class DateiSortierer:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.folder: Path | None = None
        self.plan: list[Move] = []
        self.root.title("DateiSortierer")
        self.root.geometry("920x620")
        self.root.minsize(700, 440)
        self.root.configure(background="#f3f5f4")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("App.TFrame", background="#f3f5f4")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("Title.TLabel", background="#f3f5f4", foreground="#172b27", font=("Segoe UI", 22, "bold"))
        style.configure("Body.TLabel", background="#f3f5f4", foreground="#52645e", font=("Segoe UI", 10))
        style.configure("Status.TLabel", background="#f3f5f4", foreground="#52645e", font=("Segoe UI", 9))
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 9))
        style.configure("Treeview", rowheight=30, font=("Segoe UI", 10), background="#ffffff", fieldbackground="#ffffff")
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#e7eeeb", foreground="#263d36", padding=8)

        page = ttk.Frame(root, style="App.TFrame", padding=24)
        page.pack(fill="both", expand=True)
        ttk.Label(page, text="DateiSortierer", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            page,
            text="Dateien nach Typ ordnen und gleiche Dateinamen als Gruppe zusammenhalten.",
            style="Body.TLabel",
        ).pack(anchor="w", pady=(4, 20))

        controls = ttk.Frame(page, style="App.TFrame")
        controls.pack(fill="x", pady=(0, 12))
        self.choose_button = ttk.Button(controls, text="Ordner auswählen", command=self.choose_folder)
        self.choose_button.pack(side="left")
        self.folder_label = ttk.Label(controls, text="Noch kein Ordner ausgewählt", style="Body.TLabel")
        self.folder_label.pack(side="left", padx=12, fill="x", expand=True)
        self.refresh_button = ttk.Button(controls, text="Vorschau aktualisieren", command=self.refresh, state="disabled")
        self.refresh_button.pack(side="right")

        table_frame = ttk.Frame(page, style="Panel.TFrame", padding=1)
        table_frame.pack(fill="both", expand=True)
        columns = ("source", "destination", "reason")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.table.heading("source", text="Datei")
        self.table.heading("destination", text="Neuer Speicherort")
        self.table.heading("reason", text="Einordnung")
        self.table.column("source", width=250, minwidth=140)
        self.table.column("destination", width=390, minwidth=180)
        self.table.column("reason", width=180, minwidth=120)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        footer = ttk.Frame(page, style="App.TFrame")
        footer.pack(fill="x", pady=(14, 0))
        self.status_label = ttk.Label(footer, text="Wähle einen Ordner, um die Vorschau zu erstellen.", style="Status.TLabel")
        self.status_label.pack(side="left", fill="x", expand=True)
        self.sort_button = ttk.Button(footer, text="Jetzt sortieren", style="Primary.TButton", command=self.sort_files, state="disabled")
        self.sort_button.pack(side="right")

    def choose_folder(self) -> None:
        selected = filedialog.askdirectory(title="Ordner mit zu sortierenden Dateien auswählen")
        if selected:
            self.folder = Path(selected)
            self.folder_label.configure(text=str(self.folder))
            self.refresh_button.configure(state="normal")
            self.refresh()

    def refresh(self) -> None:
        if self.folder is None:
            return
        try:
            self.plan = build_plan(self.folder)
            protected_count = count_protected_files(self.folder)
        except OSError as error:
            messagebox.showerror("Ordner kann nicht gelesen werden", str(error))
            return

        self.table.delete(*self.table.get_children())
        for move in self.plan:
            self.table.insert("", "end", values=(move.source.name, str(move.destination.relative_to(self.folder)), move.reason))
        count = len(self.plan)
        status = f"{count} Datei{'en' if count != 1 else ''} in der Vorschau" if count else "Keine Dateien zum Sortieren gefunden."
        if protected_count:
            status += f" {protected_count} App-/Systemdateien oder Verknüpfungen bleiben unangetastet."
        self.status_label.configure(text=status)
        self.sort_button.configure(state="normal" if count else "disabled")

    def sort_files(self) -> None:
        if not self.plan:
            return
        approved = messagebox.askyesno(
            "Dateien jetzt sortieren?",
            f"Es werden {len(self.plan)} Dateien verschoben. Bestehende Dateien werden nicht überschrieben. Fortfahren?",
        )
        if not approved:
            return
        try:
            count = apply_plan(self.plan)
        except OSError as error:
            messagebox.showerror("Sortieren fehlgeschlagen", str(error))
        else:
            messagebox.showinfo("Fertig", f"{count} Dateien wurden sortiert.")
            self.refresh()


def main() -> None:
    root = tk.Tk()
    DateiSortierer(root)
    root.mainloop()


if __name__ == "__main__":
    main()