import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone, timedelta
from backend.firebase_config import db
from backend.utils import parse_expiration_date
from firebase_admin import auth


def _normalize_expiration(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif hasattr(value, "to_datetime"):
        dt = value.to_datetime()
    elif isinstance(value, str):
        dt = parse_expiration_date(value)
    else:
        raise ValueError(f"Formato de fecha no soportado: {type(value)}")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


class AdminTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Husky Admin - License Management")
        self.root.geometry("600x700")
        self.root.resizable(True, True)
        self.center_window()

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', rowheight=25, font=('Arial', 9))
        style.configure('Treeview.Heading', font=('Arial', 10, 'bold'), background='#e0e0e0')

        main_frame = tk.Frame(root, bg='#f5f5f5')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        title_label = tk.Label(main_frame, text="User Licenses Overview",
                               font=('Arial', 12, 'bold'), bg='#f5f5f5', fg='#333')
        title_label.pack(pady=(0, 10))

        button_frame = tk.Frame(main_frame, bg='#f5f5f5')
        button_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Button(button_frame, text="🔄 Refresh List", command=self.refresh_users,
                  bg='#4CAF50', fg='white', font=('Arial', 9, 'bold'),
                  relief='flat', padx=25, pady=6).pack(side=tk.LEFT)
        tk.Button(button_frame, text="❌ Close", command=root.quit,
                  bg='#f44336', fg='white', font=('Arial', 9, 'bold'),
                  relief='flat', padx=25, pady=6).pack(side=tk.RIGHT)

        table_frame = tk.LabelFrame(main_frame, text="Users", font=('Arial', 9, 'bold'),
                                    bg='#f5f5f5', fg='#666', padx=5, pady=5)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ("Email", "Status", "Days Left", "Expiration")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=130, anchor='center')

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.on_user_select)

        action_frame = tk.LabelFrame(main_frame, text="Manage Selected User",
                                     font=('Arial', 9, 'bold'), bg='#f5f5f5', fg='#666',
                                     padx=10, pady=10)
        action_frame.pack(fill=tk.X, pady=(0, 10))

        self.selected_label = tk.Label(action_frame,
                                       text="No user selected\n(Click a row to manage)",
                                       font=('Arial', 10, 'bold'),
                                       bg='#f5f5f5', fg='#666',
                                       justify='center')
        self.selected_label.pack(pady=8)

        days_row = tk.Frame(action_frame, bg='#f5f5f5')
        days_row.pack(pady=5)
        tk.Label(days_row, text="Add days:", bg='#f5f5f5', font=('Arial', 9), fg='#333')\
            .grid(row=0, column=0, padx=(0, 10), sticky='w')

        self.days_var = tk.StringVar(value="7")
        days_combo = ttk.Combobox(days_row, textvariable=self.days_var,
                                  values=["1", "3", "7", "15", "30"],
                                  state="readonly", width=8, font=('Arial', 9))
        days_combo.grid(row=0, column=1, padx=(0, 20), sticky='w')

        self.apply_btn = tk.Button(action_frame, text="✅ Apply Days",
                                   command=self.apply_days,
                                   bg='#2196F3', fg='white', font=('Arial', 9, 'bold'),
                                   relief='flat', padx=30, pady=6)
        self.apply_btn.pack(pady=10)

        self.apply_btn.bind("<Enter>", lambda e: self.apply_btn.config(bg='#1976D2'))
        self.apply_btn.bind("<Leave>", lambda e: self.apply_btn.config(bg='#2196F3'))

        self.refresh_users()

    def center_window(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - 300
        y = (self.root.winfo_screenheight() // 2) - 350
        self.root.geometry(f"600x700+{x}+{y}")

    def refresh_users(self):
        self.tree.delete(*self.tree.get_children())
        try:
            auth_users = auth.list_users()
            now = datetime.now(timezone.utc)

            for user in auth_users.users:
                email = user.email
                if not email:
                    continue

                doc_ref = db.collection('users').document(email)
                doc = doc_ref.get()
                data = doc.to_dict() if doc.exists else None

                status = data.get('status', 'pending') if data else 'pending'
                exp_field = data.get('expiration_date') if data else None

                if exp_field and status != 'pending':
                    try:
                        exp_date = _normalize_expiration(exp_field)

                        # si ya venció, de una vez marcamos inactive en la base
                        if now >= exp_date and status != "inactive":
                            doc_ref.update({"status": "inactive"})
                            status_display = "🔴 Inactive"
                            days_left = 0
                            exp_formatted = exp_date.strftime("%m/%d %H:%M")
                        else:
                            days_left = max(0, (exp_date - now).days)
                            exp_formatted = exp_date.strftime("%m/%d %H:%M")
                            status_display = "🟢 Active"
                    except Exception:
                        days_left = "Error"
                        exp_formatted = "Invalid"
                        status_display = "🔴 Error"
                elif status == 'pending':
                    days_left = "No License"
                    exp_formatted = "N/A"
                    status_display = "🟡 Pending"
                else:
                    days_left = "No date"
                    exp_formatted = "N/A"
                    status_display = "🔴 Inactive"

                self.tree.insert(
                    "",
                    tk.END,
                    values=(email, status_display, days_left, exp_formatted),
                    iid=email
                )

            # colores
            for item in self.tree.get_children():
                status_val = self.tree.item(item)['values'][1]
                if "Active" in status_val:
                    self.tree.item(item, tags=('active',))
                elif "Pending" in status_val:
                    self.tree.item(item, tags=('pending',))
                else:
                    self.tree.item(item, tags=('inactive',))

            self.tree.tag_configure('active', background='#e8f5e8', foreground='#000')
            self.tree.tag_configure('pending', background='#fff3cd', foreground='#000')
            self.tree.tag_configure('inactive', background='#f8d7da', foreground='#000')

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load users: {str(e)}")

    def on_user_select(self, event):
        selection = self.tree.selection()
        if selection:
            full_email = selection[0]
            self.selected_email = full_email
            self.selected_label.config(text=f"Selected: {full_email}", fg='#333')
            self.apply_btn.config(state='normal')
        else:
            self.selected_email = None
            self.selected_label.config(text="No user selected\n(Click a row to manage)", fg='#666')
            self.apply_btn.config(state='disabled')

    def apply_days(self):
        if not getattr(self, 'selected_email', None):
            messagebox.showwarning("Warning", "Select a user from the list first.")
            return

        try:
            days_to_add = int(self.days_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid days selection.")
            return

        self.add_days_to_user(self.selected_email, days_to_add)
        self.refresh_users()
        self.apply_btn.config(state='disabled')

    def add_days_to_user(self, email, days_to_add):
        doc_ref = db.collection('users').document(email)
        doc = doc_ref.get()
        now_utc = datetime.now(timezone.utc)

        if not doc.exists:
            new_exp_date = now_utc + timedelta(days=days_to_add)
            doc_ref.set({
                "status": "active",
                "expiration_date": new_exp_date,
                "device_id": ""  # primer uso
            })
            messagebox.showinfo("Success", f"User {email} activated with {days_to_add} days.")
            return

        data = doc.to_dict()
        exp_field = data.get("expiration_date")

        if not exp_field:
            new_exp_date = now_utc + timedelta(days=days_to_add)
        else:
            current_exp = _normalize_expiration(exp_field)
            new_exp_date = current_exp + timedelta(days=days_to_add)

        # aquí SÍ preservamos device_id porque hacemos update
        doc_ref.update({
            "status": "active",
            "expiration_date": new_exp_date
        })

        days_remaining = max(0, (new_exp_date - now_utc).days)
        messagebox.showinfo(
            "Success",
            f"Added {days_to_add} days to {email}.\nNow: {days_remaining} days left."
        )


def main():
    root = tk.Tk()
    app = AdminTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()
