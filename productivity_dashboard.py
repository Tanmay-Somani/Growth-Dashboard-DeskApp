import sys
import json
import os
import logging
import winsound
import datetime
import platform
import ctypes
import numpy as np
import matplotlib.pyplot as plt
from plyer import notification

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QLineEdit, QPushButton, QComboBox,
    QScrollArea, QCheckBox, QDialog, QMenuBar, QDialogButtonBox,
    QTextEdit, QSpacerItem, QSizePolicy, QMessageBox, QGridLayout,
    QListWidget, QListWidgetItem, QAbstractItemView,
    QGroupBox, QSpinBox
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QAction, QFont, QPixmap

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()], format="%(asctime)s - %(levelname)s - %(message)s")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Productivity Tracker Paths ---
DATA_FILE = os.path.join(SCRIPT_DIR, "productivity_data.json")
SETTINGS_FILE = os.path.join(SCRIPT_DIR, "settings.json")

# --- RPG Tracker Paths ---
RPG_DATA_DIR = os.path.join(SCRIPT_DIR, "stats")
RPG_WALLPAPER_DIR = os.path.join(SCRIPT_DIR, "Wallpaper")
RPG_DATA_FILE = os.path.join(RPG_DATA_DIR, "progress_data.json")
RPG_WALLPAPER_FILE = os.path.join(RPG_WALLPAPER_DIR, "wallpaper.png")

# --- Create RPG Directories ---
os.makedirs(RPG_DATA_DIR, exist_ok=True)
os.makedirs(RPG_WALLPAPER_DIR, exist_ok=True)

class EditTaskDialog(QDialog):
    """A dialog for editing the text of a task."""
    def __init__(self, current_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Task")
        self.setMinimumSize(400, 150)
        layout = QVBoxLayout(self)
        self.entry = QLineEdit(current_text)
        self.entry.setFont(QFont("Segoe UI", 10))
        self.entry.setMinimumHeight(30)
        layout.addWidget(self.entry)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.entry.setFocus()

    def get_text(self):
        return self.entry.text().strip()


class ProductivityApp(QMainWindow):
    """The main application window for the Productivity Tracker."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Personal Growth Dashboard")
        self.setGeometry(100, 100, 1200, 800)

        # Productivity Data
        self.data = self._load_json(DATA_FILE, self._get_default_data())
        self.settings = self._load_json(SETTINGS_FILE, {"theme": "dark"})
        self.pomodoro_time = 25 * 60
        self.pomodoro_timer_running = False
        self.task_widgets = {}

        # RPG Stats Data
        self.rpg_widgets = {}
        self.STATS = {
            "ATK": "Strength Training", "DEF": "Bodybuilding & Health",
            "CHA": "People Skills", "INT": "Books & Learning",
            "WIS": "Reflection & Life Experience", "LUK": "Random Opportunities",
            "STA": "Energy, Stamina", "FAM": "Fame and Popularity",
            "GOLD": "Finance & Resources"
        }

        self._create_ui()
        self._create_menu()

        self.pomodoro_timer = QTimer(self)
        self.pomodoro_timer.setInterval(1000)
        self.pomodoro_timer.timeout.connect(self._update_pomodoro_timer)
        
        self._set_theme(self.settings.get("theme", "dark"))
        self.tab_widget.setCurrentIndex(0)
        self._on_tab_change(0)

    # --- Generic Data Handling ---
    def _get_default_data(self):
        return {
            "Eat the Frog": {"frog": {"title": "", "done": False}, "other_tasks": []},
            "Eisenhower": {"do": [], "schedule": [], "delegate": [], "delete": []},
            "Todo List": {"tasks": [], "filter": "all"},
            "3/3/3": {
                "outcomes": [{"title": "", "done": False} for _ in range(3)],
                "deep_work": [{"title": "", "done": False} for _ in range(3)],
                "maintenance": [{"title": "", "done": False} for _ in range(3)],
            },
            "Ivy Lee Method": {"tasks": [{"title": "", "done": False} for _ in range(6)], "notes": ""}
        }

    def _load_json(self, file_path, default_data):
        if not os.path.exists(file_path):
            return default_data
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                if default_data:
                    for key, value in default_data.items():
                        data.setdefault(key, value)
                return data
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Error loading {file_path}: {e}")
            return default_data

    def _save_json(self, data, file_path):
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            logging.error(f"Error saving {file_path}: {e}")

    # --- UI Creation ---
    def _create_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        clear_all_action = QAction("&Clear All Tasks", self)
        clear_all_action.triggered.connect(self._clear_all_tasks)
        file_menu.addAction(clear_all_action)
        file_menu.addSeparator()
        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        navigate_menu = menu_bar.addMenu("&Navigate")
        tab_names = ["Dashboard", "RPG Stats", "Todo List", "Eat the Frog", "Eisenhower", "3/3/3", "Ivy Lee Method", "Pomodoro", "Help"]
        for i, name in enumerate(tab_names):
            action = QAction(name, self)
            action.triggered.connect(lambda _, index=i: self.tab_widget.setCurrentIndex(index))
            navigate_menu.addAction(action)

        view_menu = menu_bar.addMenu("&View")
        light_mode_action = QAction("Light Mode", self)
        light_mode_action.triggered.connect(lambda: self._set_theme("light"))
        view_menu.addAction(light_mode_action)
        dark_mode_action = QAction("Dark Mode", self)
        dark_mode_action.triggered.connect(lambda: self._set_theme("dark"))
        view_menu.addAction(dark_mode_action)
        
        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _create_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        header_layout = QHBoxLayout()
        title_label = QLabel("Personal Growth Dashboard")
        title_label.setObjectName("titleLabel")
        self.theme_toggle_button = QPushButton("↻")
        self.theme_toggle_button.setObjectName("themeToggleButton")
        self.theme_toggle_button.setFixedSize(40, 40)
        self.theme_toggle_button.clicked.connect(self._toggle_theme)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.theme_toggle_button)
        main_layout.addLayout(header_layout)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self._on_tab_change)
        main_layout.addWidget(self.tab_widget)
        
        tabs = {
            "Dashboard": self._create_dashboard_tab,
            "RPG Stats": self._create_rpg_tab,
            "Todo List": self._create_todo_list_tab,
            "Eat the Frog": self._create_eat_the_frog_tab,
            "Eisenhower": self._create_eisenhower_tab,
            "3/3/3": self._create_333_tab,
            "Ivy Lee Method": self._create_ivy_lee_tab,
            "Pomodoro": self._create_pomodoro_tab,
            "Help": self._create_help_tab
        }
        for name, creator_func in tabs.items():
            self.tab_widget.addTab(creator_func(), name)

    def _set_theme(self, theme_name):
        self.settings["theme"] = theme_name
        stylesheet = LIGHT_STYLESHEET if theme_name == "light" else DARK_STYLESHEET
        self.setStyleSheet(stylesheet)
        tooltip = "Switch to Dark Mode" if theme_name == "light" else "Switch to Light Mode"
        self.theme_toggle_button.setToolTip(tooltip)
        # Regenerate graph on theme change if RPG tab is active
        if self.tab_widget.tabText(self.tab_widget.currentIndex()) == "RPG Stats":
            self._load_rpg_stats_data()

    def _toggle_theme(self):
        self._set_theme("light" if self.settings.get("theme") == "dark" else "dark")

    def _on_tab_change(self, index):
        tab_name = self.tab_widget.tabText(index).lower().replace(' ', '_').replace('-', '_')
        loader_func = getattr(self, f"_load_{tab_name}_data", None)
        if loader_func:
            loader_func()
        if tab_name == "dashboard":
            self._update_dashboard()

    # --- All Tab Creation Methods ---
    def _create_rpg_tab(self):
        tab = QWidget()
        main_layout = QHBoxLayout(tab)

        # Left side for inputs
        input_container = QGroupBox("Log Today's Stats")
        input_layout = QVBoxLayout()
        
        stats_grid = QGridLayout()
        self.rpg_widgets = {}
        row = 0
        for key, desc in self.STATS.items():
            label = QLabel(f"{desc} (+{key}):")
            spin_box = QSpinBox()
            spin_box.setRange(0, 10)
            stats_grid.addWidget(label, row, 0)
            stats_grid.addWidget(spin_box, row, 1)
            self.rpg_widgets[key] = spin_box
            row += 1
        
        input_layout.addLayout(stats_grid)
        
        log_button = QPushButton("Log Progress & Update Wallpaper")
        log_button.clicked.connect(self._log_rpg_progress)
        input_layout.addWidget(log_button)
        input_layout.addStretch()
        input_container.setLayout(input_layout)

        # Right side for graph display
        graph_container = QGroupBox("Latest Stats")
        graph_layout = QVBoxLayout()
        self.rpg_graph_label = QLabel("Log your first day of stats to see the graph!")
        self.rpg_graph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rpg_graph_label.setMinimumSize(500, 500)
        graph_layout.addWidget(self.rpg_graph_label)
        graph_container.setLayout(graph_layout)

        main_layout.addWidget(input_container, 1)
        main_layout.addWidget(graph_container, 2)
        return tab
        
    def _create_dashboard_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.dash_status_label = QLabel("Current Status: Idle")
        self.dash_status_label.setObjectName("headerLabel")
        self.dash_stats_label = QLabel("Task statistics will appear here.")
        self.dash_stats_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.dash_stats_label.setWordWrap(True)
        layout.addWidget(self.dash_status_label)
        layout.addWidget(self.dash_stats_label)
        return tab

    def _create_task_list_ui(self, placeholder_text, add_callback):
        container = QWidget()
        main_layout = QVBoxLayout(container)
        
        input_layout = QHBoxLayout()
        entry = QLineEdit()
        entry.setPlaceholderText(placeholder_text)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(lambda: add_callback(entry))
        input_layout.addWidget(entry)
        input_layout.addWidget(add_btn)
        main_layout.addLayout(input_layout)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollListContent")
        task_list_layout = QVBoxLayout(scroll_content)
        task_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        return container, task_list_layout

    def _create_eat_the_frog_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.task_widgets["Eat the Frog"] = {}
        frog_box = QGroupBox("Today's Frog (Your Most Important Task)")
        frog_layout = QHBoxLayout()
        frog_checkbox = QCheckBox()
        frog_entry = QLineEdit()
        frog_layout.addWidget(frog_checkbox)
        frog_layout.addWidget(frog_entry)
        frog_box.setLayout(frog_layout)
        layout.addWidget(frog_box)
        frog_checkbox.stateChanged.connect(self._save_eat_the_frog_data)
        frog_entry.textChanged.connect(self._save_eat_the_frog_data)
        
        other_tasks_container, task_list_layout = self._create_task_list_ui("Add a secondary task...", self._add_other_frog_task)
        other_tasks_box = QGroupBox("Other Tasks")
        other_tasks_box.setLayout(other_tasks_container.layout())
        layout.addWidget(other_tasks_box)
        
        self.task_widgets["Eat the Frog"].update({"frog_checkbox": frog_checkbox, "frog_entry": frog_entry, "other_tasks_layout": task_list_layout})
        return tab

    def _create_eisenhower_tab(self):
        tab = QWidget()
        layout = QGridLayout(tab)
        self.task_widgets["Eisenhower"] = {}
        quadrants = {"do": ("Urgent & Important (Do)", 0, 0), "schedule": ("Important, Not Urgent (Schedule)", 0, 1), "delegate": ("Urgent, Not Important (Delegate)", 1, 0), "delete": ("Not Urgent, Not Important (Delete)", 1, 1)}
        
        for key, (title, row, col) in quadrants.items():
            box = QGroupBox(title)
            box_layout = QVBoxLayout()
            list_widget = QListWidget()

            list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            list_widget.setDragEnabled(True)
            list_widget.setAcceptDrops(True)
            list_widget.setDropIndicatorShown(True)
            list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
            
            list_widget.itemChanged.connect(self._save_eisenhower_data)
            list_widget.model().rowsMoved.connect(self._save_eisenhower_data)
            list_widget.model().rowsInserted.connect(self._save_eisenhower_data)

            self.task_widgets["Eisenhower"][key] = list_widget
            box_layout.addWidget(list_widget)
            box.setLayout(box_layout)
            layout.addWidget(box, row, col)

        input_layout = QHBoxLayout()
        task_entry = QLineEdit(placeholderText="Add new task to 'Do' quadrant...")
        add_button = QPushButton("Add")
        add_button.clicked.connect(lambda: self._add_eisenhower_task(task_entry))
        input_layout.addWidget(task_entry)
        input_layout.addWidget(add_button)
        layout.addLayout(input_layout, 2, 0, 1, 2)
        return tab

    def _create_todo_list_tab(self):
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        self.task_widgets["Todo List"] = {}
        filter_layout = QHBoxLayout()
        filter_buttons = {"All": "all", "Active": "active", "Completed": "completed"}
        for text, key in filter_buttons.items():
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setChecked(self.data["Todo List"]["filter"] == key)
            btn.clicked.connect(lambda _, f=key: self._set_todo_filter(f))
            filter_layout.addWidget(btn)
            self.task_widgets["Todo List"][f"filter_{key}"] = btn
        main_layout.addLayout(filter_layout)
        task_list = QListWidget()
        self.task_widgets["Todo List"]["list"] = task_list
        main_layout.addWidget(task_list)
        input_layout = QHBoxLayout()
        task_entry = QLineEdit(placeholderText="Add a new todo task...")
        priority_combo = QComboBox()
        priority_combo.addItems(["High", "Medium", "Low"])
        add_btn = QPushButton("Add Task")
        add_btn.clicked.connect(lambda: self._add_todo_task(task_entry, priority_combo))
        input_layout.addWidget(task_entry)
        input_layout.addWidget(priority_combo)
        input_layout.addWidget(add_btn)
        main_layout.addLayout(input_layout)
        clear_btn = QPushButton("Clear Completed Tasks")
        clear_btn.clicked.connect(self._clear_completed_todos)
        main_layout.addWidget(clear_btn, 0, Qt.AlignmentFlag.AlignRight)
        return tab

    def _create_category_box(self, title, key_name):
        box = QGroupBox(title)
        box_layout = QVBoxLayout()
        self.task_widgets["3/3/3"][key_name] = []
        for _ in range(3):
            row_layout = QHBoxLayout()
            checkbox = QCheckBox()
            entry = QLineEdit()
            row_layout.addWidget(checkbox)
            row_layout.addWidget(entry)
            box_layout.addLayout(row_layout)
            self.task_widgets["3/3/3"][key_name].append({"checkbox": checkbox, "entry": entry})
            checkbox.stateChanged.connect(self._save_333_data)
            entry.textChanged.connect(self._save_333_data)
        box.setLayout(box_layout)
        return box

    def _create_333_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.task_widgets["3/3/3"] = {}
        categories = {"outcomes": "3 Major Outcomes", "deep_work": "3 Deep Work Blocks", "maintenance": "3 Maintenance Tasks"}
        for key, title in categories.items():
            layout.addWidget(self._create_category_box(title, key))
        layout.addStretch()
        return tab

    def _create_ivy_lee_tab(self):
        tab_widget = QWidget()
        main_layout = QHBoxLayout(tab_widget)
        self.task_widgets["Ivy Lee Method"] = {"task_entries": [], "notes_editor": None}
        tasks_box = QGroupBox("The 6 Most Important Tasks")
        tasks_layout = QVBoxLayout()
        for i in range(6):
            entry_layout = QHBoxLayout()
            checkbox = QCheckBox()
            entry = QLineEdit(placeholderText=f"Task #{i+1}")
            entry_layout.addWidget(QLabel(f"{i+1}."))
            entry_layout.addWidget(checkbox)
            entry_layout.addWidget(entry)
            tasks_layout.addLayout(entry_layout)
            self.task_widgets["Ivy Lee Method"]["task_entries"].append({"checkbox": checkbox, "entry": entry})
            checkbox.stateChanged.connect(self._save_ivy_lee_data)
            entry.textChanged.connect(self._save_ivy_lee_data)
        tasks_box.setLayout(tasks_layout)
        notes_box = QGroupBox("Daily Notes")
        notes_layout = QVBoxLayout()
        notes_editor = QTextEdit()
        notes_editor.textChanged.connect(self._save_ivy_lee_data)
        self.task_widgets["Ivy Lee Method"]["notes_editor"] = notes_editor
        notes_layout.addWidget(notes_editor)
        notes_box.setLayout(notes_layout)
        main_layout.addWidget(tasks_box, 1)
        main_layout.addWidget(notes_box, 1)
        return tab_widget
        
    def _create_pomodoro_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pomodoro_label = QLabel("25:00", objectName="timerLabel")
        buttons, buttons_layout = {"Start": self._start_pomodoro, "Stop": self._stop_pomodoro, "Reset": self._reset_pomodoro}, QHBoxLayout()
        for text, callback in buttons.items():
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            buttons_layout.addWidget(btn)
        layout.addWidget(self.pomodoro_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(buttons_layout)
        return tab
        
    def _create_help_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        help_text = QTextEdit(readOnly=True)
        help_text.setHtml("""
            <h1>Productivity Methods Explained</h1>
            <p><b>&bull; RPG Stats:</b> Track your personal growth across different life attributes like an RPG character.</p>
            <p><b>&bull; Todo List:</b> A powerful list to manage daily tasks with priorities and filtering.</p>
            <p><b>&bull; Eat the Frog:</b> Complete your single most important task for the day.</p>
            <p><b>&bull; Eisenhower Matrix:</b> Prioritize tasks based on urgency and importance.</p>
            <p><b>&bull; 3/3/3 Rule:</b> Structure your day with 3 major outcomes, 3 deep work blocks, and 3 maintenance tasks.</p>
            <p><b>&bull; Ivy Lee Method:</b> List and tackle the six most important tasks for the next day in order.</p>
            <hr>
            <h1>Application Features</h1>
            <p><b>&bull; Dashboard:</b> Get a live overview of your task statistics and Pomodoro status.</p>
            <p><b>&bull; Pomodoro Timer:</b> Use a built-in timer for focused work sessions.</p>
            <p><b>&bull; Auto-Save:</b> All data is saved automatically when you close the application.</p>
        """)
        layout.addWidget(help_text)
        return tab
        
    # --- Data Loaders ---
    def _load_rpg_stats_data(self):
        data = self._load_json(RPG_DATA_FILE, {})
        today = datetime.date.today().isoformat()
        
        if data and today in data:
            for key, spin_box in self.rpg_widgets.items():
                spin_box.setValue(data[today].get(key, 0))

        if data:
            self._generate_rpg_graph(update_display=True)
        else:
            self.rpg_graph_label.setText("Log your first day of stats to see the graph!")

    def _clear_layout(self, layout):
        if layout is None: return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _load_eat_the_frog_data(self):
        data = self.data["Eat the Frog"]
        widgets = self.task_widgets["Eat the Frog"]
        widgets["frog_entry"].setText(data["frog"]["title"])
        widgets["frog_checkbox"].setChecked(data["frog"]["done"])
        self._clear_layout(widgets["other_tasks_layout"])
        for idx, task in enumerate(data.get("other_tasks", [])):
            task_widget = QWidget()
            task_layout = QHBoxLayout(task_widget)
            checkbox = QCheckBox(task["title"])
            checkbox.setChecked(task["done"])
            checkbox.stateChanged.connect(lambda state, i=idx: self._toggle_other_frog_task(i, state))
            delete_btn = QPushButton("Delete")
            delete_btn.setObjectName("deleteButton")
            delete_btn.clicked.connect(lambda _, i=idx: self._delete_other_frog_task(i))
            task_layout.addWidget(checkbox)
            task_layout.addStretch()
            task_layout.addWidget(delete_btn)
            widgets["other_tasks_layout"].addWidget(task_widget)

    def _load_eisenhower_data(self):
        for key, list_widget in self.task_widgets["Eisenhower"].items():
            list_widget.clear()
            for task in self.data["Eisenhower"].get(key, []):
                item = QListWidgetItem(task["title"])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if task["done"] else Qt.CheckState.Unchecked)
                list_widget.addItem(item)
    
    def _create_todo_item_widget(self, task, index):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        checkbox = QCheckBox()
        checkbox.setChecked(task["done"])
        checkbox.stateChanged.connect(lambda state, i=index: self._toggle_todo_task_status(i, state))
        title = QLabel(task["title"])
        if task["done"]: title.setObjectName("taskDone")
        priority_colors = {"High": "#e55039", "Medium": "#f6b93b", "Low": "#78e08f"}
        priority_label = QLabel(task["priority"])
        priority_label.setObjectName("priorityLabel")
        priority_label.setStyleSheet(f"background-color: {priority_colors[task['priority']]}; color: white; padding: 2px 5px; border-radius: 4px;")
        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("deleteButton")
        delete_btn.clicked.connect(lambda _, i=index: self._delete_todo_task(i))
        layout.addWidget(checkbox)
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(priority_label)
        layout.addWidget(delete_btn)
        return widget

    def _load_todo_list_data(self):
        list_widget = self.task_widgets["Todo List"]["list"]
        list_widget.clear()
        current_filter = self.data["Todo List"]["filter"]
        for i, task in enumerate(self.data["Todo List"]["tasks"]):
            if (current_filter == "all" or (current_filter == "active" and not task["done"]) or (current_filter == "completed" and task["done"])):
                item_widget = self._create_todo_item_widget(task, i)
                list_item = QListWidgetItem(list_widget)
                list_item.setSizeHint(item_widget.sizeHint())
                list_widget.addItem(list_item)
                list_widget.setItemWidget(list_item, item_widget)
    
    def _load_333_data(self):
        data = self.data["3/3/3"]
        widgets = self.task_widgets["3/3/3"]
        for key in widgets:
            for i in range(3):
                widgets[key][i]["entry"].setText(data.get(key, [])[i].get("title", ""))
                widgets[key][i]["checkbox"].setChecked(data.get(key, [])[i].get("done", False))

    def _load_ivy_lee_method_data(self):
        data, widgets = self.data["Ivy Lee Method"], self.task_widgets["Ivy Lee Method"]
        tasks = data.get("tasks", [])
        for i in range(6):
            task_data = tasks[i] if i < len(tasks) else {}
            widgets["task_entries"][i]["entry"].setText(task_data.get("title", ""))
            widgets["task_entries"][i]["checkbox"].setChecked(task_data.get("done", False))
        widgets["notes_editor"].setPlainText(data.get("notes", ""))

    # --- RPG Logic Methods ---
    def _log_rpg_progress(self):
        today = datetime.date.today().isoformat()
        data = self._load_json(RPG_DATA_FILE, {})
        if today not in data:
            data[today] = {}
        
        for key, spin_box in self.rpg_widgets.items():
            data[today][key] = spin_box.value()
            
        self._save_json(data, RPG_DATA_FILE)
        self._generate_rpg_graph(update_display=True)
        self._set_rpg_wallpaper()
        self._send_rpg_notification()

        QMessageBox.information(self, "Success", "Progress logged and wallpaper updated!")

    # --- MODIFIED: This function is now theme-aware ---
    def _generate_rpg_graph(self, update_display=False):
        data = self._load_json(RPG_DATA_FILE, {})
        if not data:
            return

        # Define colors based on the current theme
        is_dark_theme = self.settings.get("theme", "dark") == "dark"
        bg_color = '#212121' if is_dark_theme else '#f0f0f0'
        text_color = '#eee' if is_dark_theme else '#111'
        grid_color = '#555' if is_dark_theme else '#bbb'
        line_color = '#3f51b5'
        fill_color = '#3f51b5'

        latest = list(data.keys())[-1]
        values = data[latest]
        labels = list(self.STATS.values())
        stats_keys = list(self.STATS.keys())
        stats_values = [values.get(k, 0) for k in stats_keys]

        num_vars = len(stats_keys)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        stats_values += stats_values[:1]
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
        
        # Apply theme colors
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
        ax.spines['polar'].set_edgecolor(grid_color)

        ax.fill(angles, stats_values, color=fill_color, alpha=0.25)
        ax.plot(angles, stats_values, color=line_color, linewidth=2)
        
        ax.set_yticks(range(0, 11, 2))
        ax.set_ylim(0, 10)
        ax.tick_params(axis='y', colors=text_color)
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=10, color=text_color)
        
        title = plt.title(f"RPG Stats for {latest}", size=15, y=1.1)
        title.set_color(text_color)
        
        ax.grid(color=grid_color)
        
        plt.tight_layout()

        # Save with the correct background color
        plt.savefig(RPG_WALLPAPER_FILE, facecolor=fig.get_facecolor())
        plt.close()

        if update_display:
            pixmap = QPixmap(RPG_WALLPAPER_FILE)
            self.rpg_graph_label.setPixmap(pixmap.scaled(
                self.rpg_graph_label.width(), 
                self.rpg_graph_label.height(), 
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

    def _set_rpg_wallpaper(self):
        path = os.path.abspath(RPG_WALLPAPER_FILE)
        if platform.system() == "Windows":
            ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)
        elif platform.system() == "Darwin":
            os.system(f"osascript -e 'tell application \"System Events\" to set picture of every desktop to \"{path}\"'")
        elif platform.system() == "Linux":
            os.system(f"gsettings set org.gnome.desktop.background picture-uri file://{path}")
        else:
            logging.warning("Wallpaper setting not supported on this OS.")

    def _send_rpg_notification(self):
        try:
            notification.notify(
                title="RPG Progress Tracker",
                message="Your daily stats have been logged and your wallpaper updated!",
                timeout=10
            )
        except Exception as e:
            logging.error(f"Failed to send notification: {e}")

    # --- Data Savers & Actions ---
    def _save_and_update(self):
        self._update_dashboard()

    def _save_eat_the_frog_data(self):
        widgets = self.task_widgets["Eat the Frog"]
        self.data["Eat the Frog"]["frog"]["title"] = widgets["frog_entry"].text()
        self.data["Eat the Frog"]["frog"]["done"] = widgets["frog_checkbox"].isChecked()
        self._save_and_update()

    def _add_other_frog_task(self, entry_widget):
        if title := entry_widget.text().strip():
            self.data["Eat the Frog"]["other_tasks"].append({"title": title, "done": False})
            entry_widget.clear()
            self._load_eat_the_frog_data()
            self._save_and_update()

    def _toggle_other_frog_task(self, index, state):
        self.data["Eat the Frog"]["other_tasks"][index]["done"] = (state == Qt.CheckState.Checked.value)
        self._save_and_update()
        
    def _delete_other_frog_task(self, index):
        self.data["Eat the Frog"]["other_tasks"].pop(index)
        self._load_eat_the_frog_data()
        self._save_and_update()

    def _add_eisenhower_task(self, entry_widget):
        if title := entry_widget.text().strip():
            self.data["Eisenhower"]["do"].append({"title": title, "done": False})
            entry_widget.clear()
            self._load_eisenhower_data()
            self._save_and_update()

    def _save_eisenhower_data(self):
        for key, list_widget in self.task_widgets["Eisenhower"].items():
            self.data["Eisenhower"][key] = [{"title": list_widget.item(i).text(), "done": list_widget.item(i).checkState() == Qt.CheckState.Checked} for i in range(list_widget.count())]
        self._save_and_update()

    def _set_todo_filter(self, new_filter):
        self.data["Todo List"]["filter"] = new_filter
        for key, btn in self.task_widgets["Todo List"].items():
            if key.startswith("filter_") and isinstance(btn, QPushButton):
                btn.setChecked(key == f"filter_{new_filter}")
        self._load_todo_list_data()

    def _add_todo_task(self, entry, combo):
        if title := entry.text().strip():
            self.data["Todo List"]["tasks"].append({"title": title, "done": False, "priority": combo.currentText()})
            entry.clear()
            self._load_todo_list_data()
            self._save_and_update()

    def _toggle_todo_task_status(self, index, state):
        self.data["Todo List"]["tasks"][index]["done"] = (state == Qt.CheckState.Checked.value)
        self._load_todo_list_data()
        self._save_and_update()

    def _delete_todo_task(self, index):
        self.data["Todo List"]["tasks"].pop(index)
        self._load_todo_list_data()
        self._save_and_update()

    def _clear_completed_todos(self):
        self.data["Todo List"]["tasks"] = [t for t in self.data["Todo List"]["tasks"] if not t["done"]]
        self._load_todo_list_data()
        self._save_and_update()
    
    def _save_333_data(self):
        widgets = self.task_widgets["3/3/3"]
        for key in widgets:
            for i in range(3):
                self.data["3/3/3"][key][i]["title"] = widgets[key][i]["entry"].text()
                self.data["3/3/3"][key][i]["done"] = widgets[key][i]["checkbox"].isChecked()
        self._save_and_update()

    def _save_ivy_lee_data(self):
        widgets = self.task_widgets["Ivy Lee Method"]["task_entries"]
        self.data["Ivy Lee Method"]["tasks"] = [{"title": w["entry"].text().strip(), "done": w["checkbox"].isChecked()} for w in widgets]
        self.data["Ivy Lee Method"]["notes"] = self.task_widgets["Ivy Lee Method"]["notes_editor"].toPlainText()
        self._save_and_update()


    # --- Dashboard and Pomodoro ---
    def _update_dashboard(self):
        status = f"Pomodoro session running ({self.pomodoro_time//60:02d}:{self.pomodoro_time%60:02d})" if self.pomodoro_timer_running else "Idle"
        self.dash_status_label.setText(f"Current Status: {status}")
        stats_text = "<b>Task Statistics</b><br><br>"
        total, completed = 0, 0
        methods = {
            "Todo List": (len(self.data["Todo List"]["tasks"]), sum(1 for t in self.data["Todo List"]["tasks"] if t.get("done"))),
            "Eat the Frog": ((1 if self.data["Eat the Frog"]["frog"]["title"] else 0) + len(self.data["Eat the Frog"]["other_tasks"]), (1 if self.data["Eat the Frog"]["frog"]["done"] else 0) + sum(1 for t in self.data["Eat the Frog"]["other_tasks"] if t.get("done"))),
            "Eisenhower": (sum(len(q) for q in self.data["Eisenhower"].values()), sum(sum(1 for t in q if t.get("done")) for q in self.data["Eisenhower"].values())),
            "3/3/3": (sum(len([t for t in c if t.get("title")]) for c in self.data["3/3/3"].values()), sum(sum(1 for t in c if t.get("done")) for c in self.data["3/3/3"].values())),
            "Ivy Lee Method": (len([t for t in self.data["Ivy Lee Method"]["tasks"] if t.get("title")]), sum(1 for t in self.data["Ivy Lee Method"]["tasks"] if t.get("done")))
        }
        for name, (count, done) in methods.items():
            if count > 0:
                stats_text += f"&bull; <b>{name}:</b> {done} of {count} complete.<br>"
                total, completed = total + count, completed + done
        progress = (completed / total * 100) if total > 0 else 0
        stats_text += f"<hr><b>Overall:</b> {completed} of {total} complete ({progress:.0f}%)"
        self.dash_stats_label.setText(stats_text)

    def _update_pomodoro_timer(self):
        if self.pomodoro_timer_running and self.pomodoro_time > 0:
            self.pomodoro_time -= 1
            self.pomodoro_label.setText(f"{self.pomodoro_time // 60:02d}:{self.pomodoro_time % 60:02d}")
        else:
            if self.pomodoro_timer_running: winsound.MessageBeep(winsound.MB_ICONINFORMATION)
            self._stop_pomodoro()
        self._update_dashboard()

    def _start_pomodoro(self):
        if not self.pomodoro_timer_running:
            self.pomodoro_timer_running = True
            self.pomodoro_timer.start(1000)

    def _stop_pomodoro(self):
        self.pomodoro_timer_running = False
        self.pomodoro_timer.stop()
        self._update_dashboard()

    def _reset_pomodoro(self):
        self._stop_pomodoro()
        self.pomodoro_time = 25 * 60
        self.pomodoro_label.setText("25:00")
        self._update_dashboard()

    # --- App-level Actions ---
    def _clear_all_tasks(self):
        if QMessageBox.question(self, 'Clear All Tasks', "Are you sure you want to delete all data? This cannot be undone.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.data = self._get_default_data()
            self._on_tab_change(self.tab_widget.currentIndex())

    def _show_about_dialog(self):
        QMessageBox.about(self, "About Personal Growth Dashboard", "<b>A Basic Tracker v0.6</b><br><br>A modern toolkit for productivity methods and tracking to improve upon traditional techniques. An integrated system developed by Tanmay Somani. <br> Contact me at my email:tanmaysomani2003@gmail.com")

    def closeEvent(self, event):
        self._save_json(self.data, DATA_FILE)
        self._save_json(self.settings, SETTINGS_FILE)
        event.accept()

# --- STYLESHEETS (MODIFIED FOR SPINBOX) ---
SHARED_STYLES = """
    QGroupBox { font-weight: bold; background-image: none; }
    QPushButton { 
        border: 1px solid transparent; padding: 6px 12px; font-weight: bold; 
        border-radius: 5px; background-image: none;
    }
    QPushButton:hover { background-color: #4d5ec1; border: 1px solid #5c6bc0; }
    QPushButton:pressed { background-color: #5c6bc0; }
    QPushButton:checked { background-color: #303f9f; }
    QPushButton#deleteButton { background-color: #c0392b; }
    QPushButton#deleteButton:hover { background-color: #e74c3c; border: 1px solid #ff6b5b; }
    QCheckBox::indicator { width: 18px; height: 18px; }
    QMenu::item:selected { background-color: #3f51b5; }
    QLabel#timerLabel { font-size: 48pt; font-weight: bold; }
    QLabel#titleLabel { font-size: 16pt; font-weight: bold; }
    QLabel#taskDone { text-decoration: line-through; color: #888; }
    QPushButton#themeToggleButton { font-size: 14pt; border-radius: 20px; }

    /* --- ADDED: Custom SpinBox Styling --- */
    QSpinBox {
        padding-right: 20px; /* Make room for buttons */
        font-size: 11pt;
    }
    QSpinBox::up-button, QSpinBox::down-button {
        subcontrol-origin: border;
        width: 20px;
        border-left-width: 1px;
        border-left-style: solid;
    }
    QSpinBox::up-button {
        subcontrol-position: top right;
        border-top-right-radius: 4px;
    }
    QSpinBox::down-button {
        subcontrol-position: bottom right;
        border-bottom-right-radius: 4px;
    }
    QSpinBox::up-arrow {
        image: url(up_arrow.png); /* You need to provide these images */
        width: 10px;
        height: 10px;
    }
    QSpinBox::down-arrow {
        image: url(down_arrow.png); /* You need to provide these images */
        width: 10px;
        height: 10px;
    }
"""

LIGHT_STYLESHEET = SHARED_STYLES + """
    QMainWindow, QDialog { background-color: #f0f0f0; }
    QWidget { color: #111; font-family: "Segoe UI", sans-serif; font-size: 10pt; background-image: none; }
    QWidget#scrollListContent { background-color: #ffffff; }
    QListWidget { border-radius: 5px; }
    QTabWidget::pane { border: 1px solid #d0d0d0; }
    QTabBar::tab { background-color: #e0e0e0; color: #333; padding: 10px 20px; border: 1px solid #d0d0d0; border-bottom: none; }
    QTabBar::tab:selected { background-color: #3f51b5; color: white; }
    QLabel, QCheckBox { background-color: transparent; }
    QLabel#headerLabel { color: #3f51b5; font-size: 14pt; font-weight: bold; }
    QPushButton { background-color: #3f51b5; color: white; }
    QPushButton:disabled { background-color: #cccccc; color: #888888; border: 1px solid #bbbbbb; }
    QLineEdit, QTextEdit, QScrollArea, QListWidget, QComboBox, QSpinBox { background-color: #ffffff; border: 1px solid #d0d0d0; border-radius: 4px; padding: 5px; color: #111; }
    QMenuBar { background-color: #e0e0e0; color: #333; }
    QMenuBar::item:selected { background-color: #3f51b5; color: white; }
    QMenu { background-color: #f0f0f0; border: 1px solid #d0d0d0; }
    QPushButton#themeToggleButton { background-color: #e0e0e0; color: #111; }
    QGroupBox { border: 1px solid #d0d0d0; border-radius: 5px; margin-top: 8px; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 8px; }
    
    QSpinBox::up-button, QSpinBox::down-button {
        background-color: #e0e0e0;
        border-left-color: #d0d0d0;
    }
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {
        background-color: #d0d0d0;
    }
"""

DARK_STYLESHEET = SHARED_STYLES + """
    QMainWindow, QDialog { background-color: #212121; }
    QWidget { color: #eee; font-family: "Segoe UI", sans-serif; font-size: 10pt; background-image: none; }
    QWidget#scrollListContent { background-color: #2c2c2c; }
    QListWidget { border-radius: 5px; }
    QTabWidget::pane { border: 1px solid #3a3a3a; }
    QTabBar::tab { background-color: #2c2c2c; color: #ccc; padding: 10px 20px; border: 1px solid #3a3a3a; border-bottom: none; }
    QTabBar::tab:selected { background-color: #3f51b5; color: white; }
    QLabel, QCheckBox { background-color: transparent; }
    QLabel#taskDone { color: #777; }
    QLabel#headerLabel { color: #3f51b5; font-size: 14pt; font-weight: bold; }
    QPushButton { background-color: #3f51b5; color: white; }
    QPushButton:disabled { background-color: #444444; color: #888888; border: 1px solid #555555; }
    QLineEdit, QTextEdit, QScrollArea, QListWidget, QComboBox, QSpinBox { background-color: #2c2c2c; border: 1px solid #3a3a3a; border-radius: 4px; padding: 5px; color: #eee; }
    QComboBox::drop-down { border: none; }
    QComboBox QAbstractItemView { background-color: #3a3a3a; color: #eee; selection-background-color: #3f51b5; }
    QMenuBar { background-color: #2c2c2c; color: #ccc; }
    QMenuBar::item:selected { background-color: #3f51b5; color: white; }
    QMenu { background-color: #2c2c2c; border: 1px solid #3a3a3a; }
    QPushButton#themeToggleButton { background-color: #2c2c2c; color: #eee; }
    QGroupBox { border: 1px solid #3a3a3a; border-radius: 5px; margin-top: 8px; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 8px; }

    QSpinBox::up-button, QSpinBox::down-button {
        background-color: #3a3a3a;
        border-left-color: #555;
    }
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {
        background-color: #4a4a4a;
    }
"""

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProductivityApp()
    window.show()
    sys.exit(app.exec())