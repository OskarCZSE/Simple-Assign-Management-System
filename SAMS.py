import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import csv
import copy
import random
import os

#Config
DEFAULT_IMPORT = './Harmonogram.csv'
DEFAULT_EXPORT = './Gotowy_Harmonogram.csv'
DEFAULT_ENCODING = 'cp1250'
weekDays = ["Pn", "Wt", "Sr", "Cz", "Pt"]

#Code

colsUpToWeekDays = 6

class Person:
    def __init__(self, desk, uid, surname, name, floor, section, availability):
        self.desk = desk
        self.uid = ("0" + uid) if len(uid) == 2 else uid
        self.surname = surname
        self.name = name
        self.floor = floor
        self.section = section
        self.availability = availability
    
    @classmethod
    def from_csv_fields(cls, fields):
        desk, uid, surname, name, floor, section = fields[:colsUpToWeekDays]
        availability = fields[colsUpToWeekDays:]
        return cls(desk, uid, surname, name, floor, section, availability)

    def is_manager(self):
        sec = (self.section or "").strip().lower()
        return sec == "kierownik"

    def is_director(self):
        sec = (self.section or "").strip().lower()
        return sec == "dyrektor"

def getPersonArray(pathToImportCSV=DEFAULT_IMPORT, csv_encoding=DEFAULT_ENCODING):
    globalArray = []
    with open(pathToImportCSV, mode ='r', encoding=csv_encoding)as file:
        csvFile = csv.reader(file)

        headers = next(csvFile, None)[0]
        values = [s.strip() for s in headers.split(";")]
    
    
        for lines in csvFile:
            line = [s.strip() for s in lines[0].split(";")]

            newPerson = Person.from_csv_fields(line)
            globalArray.append(newPerson)
    return globalArray

def asignPeopleToWeek(people, floor, presence_fraction):
    FloorArray = [p for p in people if p.floor == str(floor)]
    targetForFloor = max(1, round(len(FloorArray) * presence_fraction))


    #@TODO: Currently works only for 40% because i forgot to do it properly and test it, gonna fix it later
    nom_pool = copy.deepcopy([p for p in FloorArray if not p.is_director() and not p.is_manager()])
    normal_pool = copy.deepcopy(nom_pool) + copy.deepcopy(nom_pool) + copy.deepcopy([p for p in FloorArray if p.is_manager()])

    # for i in range(max(1, round(pct / 20))):


    random.shuffle(normal_pool)

    asignDict = {wd: [] for wd in weekDays}

    for p in FloorArray:
        if p.is_director():
            for wd in weekDays:
                if all(existing.desk != p.desk for existing in asignDict[wd]):
                    asignDict[wd].append(p)

    for p in FloorArray:
        if p.is_manager():
            day = "Wt"
            if all(existing.desk != p.desk for existing in asignDict[day]):
                asignDict[day].append(p)

    Dayid = 0
    for p in normal_pool:
        available_indices = [i for i, d in enumerate(weekDays) if i < len(p.availability) and p.availability[i].strip().lower() == "true"]
        if not available_indices:
            continue

        tried = 0
        while tried < len(available_indices):
            day_index = available_indices[Dayid % len(available_indices)]
            day = weekDays[day_index]
            if len(asignDict[day]) < targetForFloor and all(existing.desk != p.desk for existing in asignDict[day]):
                asignDict[day].append(p)
                break
            Dayid = (Dayid + 1) % len(available_indices)
            tried += 1
        else:
            placed = False
            for di in available_indices:
                cand = weekDays[di]
                if all(existing.desk != p.desk for existing in asignDict[cand]):
                    asignDict[cand].append(p)
                    placed = True
                    break
            if not placed:
                shortest = min(available_indices, key=lambda k: len(asignDict[weekDays[k]]))
                asignDict[weekDays[shortest]].append(p)

    return asignDict

def format_assignment_to_csv(assignments, csv_path, week_days=weekDays, encoding=DEFAULT_ENCODING):
    header = ["UID", "Desk", "Surname", "Name", "Section"] + week_days

    people_map = {}
    for d in week_days:
        for p in assignments.get(d, []):
            key = (p.uid, p.desk)
            if key not in people_map:
                people_map[key] = p

    def name_key(key):
        p = people_map[key]
        return (p.surname.lower(), p.name.lower())

    sorted_keys = sorted(people_map.keys(), key=name_key)

    rows = [header]
    weekday_totals = {d: 0 for d in week_days}

    for key in sorted_keys:
        p = people_map[key]
        row = [p.uid, p.desk, p.surname, p.name, p.section]
        for d in week_days:
            present = any((p.uid == q.uid and p.desk == q.desk) for q in assignments.get(d, []))
            if present:
                row.append("X")
                weekday_totals[d] += 1
            else:
                row.append("-")
        rows.append(row)

    totals_row = ["", "", "", "", ""]
    for d in week_days:
        totals_row.append(str(weekday_totals[d]))
    rows.append(totals_row)

    with open(csv_path, mode="w", encoding=encoding, newline="") as f:
        writer = csv.writer(f, delimiter=";")
        for r in rows:
            writer.writerow(r)
    return csv_path

# GUI (AI generated, was too lazy to do it rn, gonna do it later myself)

class SchedulerGUI:
    def __init__(self, root):
        self.root = root
        root.title("Scheduler GUI")
        self.create_widgets()
        self.load_defaults()

    def create_widgets(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.grid(column=0, row=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Import
        ttk.Label(frm, text="Import:").grid(column=0, row=0, sticky="w")
        self.import_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.import_var, width=50).grid(column=1, row=0, sticky="ew")
        ttk.Button(frm, text="Browse", command=self.browse_import).grid(column=2, row=0)

        # Export
        ttk.Label(frm, text="Export:").grid(column=0, row=1, sticky="w")
        self.export_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.export_var, width=50).grid(column=1, row=1, sticky="ew")
        ttk.Button(frm, text="Browse", command=self.browse_export).grid(column=2, row=1)

        ttk.Label(frm, text="% Osób w biurze:").grid(column=0, row=2, sticky="w")
        self.presence_pct_var = tk.IntVar()
        self.presence_pct_var.trace_add("write", self._update_presence_fraction)
        ttk.Entry(frm, textvariable=self.presence_pct_var, width=10).grid(column=1, row=2, sticky="w")
        self.presence_frac_lbl = ttk.Label(frm, text="0.40 (fraction used)")
        self.presence_frac_lbl.grid(column=2, row=2, sticky="w")

        self.run_btn = ttk.Button(frm, text="Pozyskaj Harmonogram", command=self.run_thread)
        self.run_btn.grid(column=0, row=3, pady=10)

        ttk.Label(frm, text="Podgląd:").grid(column=0, row=4, columnspan=3, sticky="w", pady=(10,0))
        self.preview = tk.Text(frm, height=20, width=120, wrap="none", font=("Courier", 10))
        self.preview.grid(column=0, row=5, columnspan=3, sticky="nsew")
        frm.rowconfigure(5, weight=1)

        xscroll = ttk.Scrollbar(frm, orient="horizontal", command=self.preview.xview)
        xscroll.grid(column=0, row=6, columnspan=3, sticky="ew")
        self.preview.configure(xscrollcommand=xscroll.set)

        yscroll = ttk.Scrollbar(frm, orient="vertical", command=self.preview.yview)
        yscroll.grid(column=3, row=5, sticky="ns")
        self.preview.configure(yscrollcommand=yscroll.set)

        ttk.Button(frm, text="Open Export Folder", command=self.open_export_folder).grid(column=0, row=7, pady=8)
        ttk.Label(frm, text="Stworzone przez: Oskar Ciebielski © 2026").grid(column=1, row=7, sticky="w")
        ttk.Button(frm, text="Quit", command=self.root.quit).grid(column=2, row=7, pady=8)

    def load_defaults(self):
        self.import_var.set(DEFAULT_IMPORT)
        self.export_var.set(DEFAULT_EXPORT)
        self.presence_pct_var.set(40) 
        self._update_presence_fraction()

    def browse_import(self):
        p = filedialog.askopenfilename(filetypes=[("CSV files","*.csv"),("All files","*.*")])
        if p:
            self.import_var.set(p)

    def browse_export(self):
        p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files","*.csv"),("All files","*.*")])
        if p:
            self.export_var.set(p)

    def open_export_folder(self):
        path = self.export_var.get()
        if not path:
            messagebox.showinfo("Info", "No export path set")
            return
        folder = os.path.dirname(os.path.abspath(path))
        try:
            if os.name == 'nt':
                os.startfile(folder)
            elif os.name == 'posix':
                os.system(f'xdg-open "{folder}"')
            else:
                messagebox.showinfo("Info", folder)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def run_thread(self):
        t = threading.Thread(target=self.run_assignment)
        t.start()

    def _update_presence_fraction(self, *args):
        try:
            pct = int(self.presence_pct_var.get())
        except Exception:
            pct = 0
        pct = max(0, min(100, pct))
        frac = pct / 100.0
        self.presence_frac_lbl.config(text=f"{pct}%")
        return frac

    def _read_csv_rows(self, path, encoding=DEFAULT_ENCODING):
        rows = []
        with open(path, mode="r", encoding=encoding, errors="replace") as f:
            reader = csv.reader(f, delimiter=";")
            for r in reader:
                rows.append([cell.strip() for cell in r])
        return rows

    def _rows_to_fixed_table(self, rows):
        if not rows:
            return ""
        ncols = max(len(r) for r in rows)
        widths = [0]*ncols
        for r in rows:
            for i in range(ncols):
                cell = r[i] if i < len(r) else ""
                widths[i] = max(widths[i], len(str(cell)))
        lines = []
        for r in rows:
            padded = []
            for i in range(ncols):
                cell = str(r[i]) if i < len(r) else ""
                padded.append(cell.ljust(widths[i] + 2))
            lines.append("".join(padded).rstrip())
        return "\n".join(lines)

    def run_assignment(self):
        self.run_btn.config(state="disabled")
        self.preview.delete("1.0", tk.END)
        try:
            imp = self.import_var.get()
            exp = self.export_var.get()
            presence_pct = int(self.presence_pct_var.get())
            presence_pct = max(0, min(100, presence_pct))
            presence = presence_pct / 100.0


            if not os.path.exists(imp):
                raise FileNotFoundError(f"Import file not found: {imp}")

            people = getPersonArray(imp, DEFAULT_ENCODING)
            if not people:
                raise ValueError("No people parsed from import CSV.")

            ass0 = asignPeopleToWeek(people, 0, presence)
            ass1 = asignPeopleToWeek(people, 1, presence)
            combined = { day: list(ass0.get(day, [])) + list(ass1.get(day, [])) for day in weekDays }

            format_assignment_to_csv(combined, exp, week_days=weekDays, encoding=DEFAULT_ENCODING)

            rows = self._read_csv_rows(exp, encoding=DEFAULT_ENCODING)
            table_text = self._rows_to_fixed_table(rows)
            self.preview.insert("1.0", table_text)

        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.run_btn.config(state="normal")

# Main
if __name__ == "__main__":
    root = tk.Tk()
    app = SchedulerGUI(root)
    root.geometry("1100x700")
    root.mainloop()
