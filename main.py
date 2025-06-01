from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.core.clipboard import Clipboard
from kivy.uix.label import Label
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line
from kivy.utils import platform
import os
import sqlite3
import re

# Константы
TABS = ["Notes", "Tasks", "Ideas", "Links", "Archive", "Clipboard"]
DATA_FOLDER = "data" if platform != 'android' else os.path.join(os.path.expanduser('~'), 'data')
MAX_CLIPBOARD = 30
LANGUAGE = 'ru'

# Список популярных ключевых слов языков программирования (добавьте/удалите свои слова)
PROGRAMMING_KEYWORDS = [
    'def', 'class', 'if', 'else', 'for', 'while', 'return', 'import', 'from',
    'function', 'var', 'let', 'const', 'async', 'await', 'try', 'catch', 'finally',
    'public', 'private', 'protected', 'static', 'void', 'int', 'string', 'bool'
]

# Словарь переводов
TRANSLATIONS = {
    'ru': {
        'save': 'Сохранить',
        'add': 'Добавить',
        'new_cell': 'Новая ячейка',
        'edit': 'E',
        'copy': 'CO',
        'delete': 'X',
        'notes': 'Заметки',
        'tasks': 'Задачи',
        'ideas': 'Идеи',
        'links': 'Ссылки',
        'archive': 'Архив',
        'clipboard': 'Буфер обмена',
        'sort_alpha': 'А - Я',
        'sort_length': 'ДЛИНА',
        'sort_type': 'КОД'
    }
}

# Создание папки для данных
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER, exist_ok=True)

# Подключение к базе данных
conn = sqlite3.connect(os.path.join(DATA_FOLDER, 'notepad.db'))
cursor = conn.cursor()

# Создание таблиц
for tab in TABS:
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {tab.lower()} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL
        )
    ''')
conn.commit()

class Cell(BoxLayout):
    text = StringProperty("")

    def __init__(self, text, cell_id, on_edit, on_remove, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=150, **kwargs)
        self.text = text
        self.cell_id = cell_id
        self.on_edit = on_edit
        self.on_remove = on_remove

        # Фон и границы ячейки
        with self.canvas.before:
            Color(0.1, 0.1, 0.1, 1)  # Цвет фона ячейки
            self.rect = Rectangle(pos=self.pos, size=self.size)
            Color(0.7, 0.7, 0.7, 1)  # Цвет границ
            self.border = Line(rectangle=(self.x, self.y, self.width, self.height), width=1)
        self.bind(pos=self.update_rect, size=self.update_rect)

        # Прокручиваемая область для текста
        self.scroll = ScrollView(bar_width=0, size_hint=(0.8, 1))
        self.label = Label(
            text=text,
            halign='left',
            valign='top',
            size_hint_y=None,
            text_size=(self.scroll.width, None),
            color=(1, 1, 1, 1)  # Цвет текста
        )
        self.label.bind(texture_size=lambda instance, value: setattr(self.label, 'height', value[1]))
        self.scroll.add_widget(self.label)
        self.add_widget(self.scroll)

        # Привязка ширины
        self.scroll.bind(width=lambda instance, value: setattr(self.label, 'text_size', (value, None)))

        # Кнопки
        btn_copy = Button(
            text=TRANSLATIONS[LANGUAGE]['copy'],
            size_hint_x=0.1,
            background_color=(0.2, 0.6, 0.8, 1)  # Цвет кнопки "Копировать"
        )
        btn_copy.bind(on_press=self.copy_text)
        btn_edit = Button(
            text=TRANSLATIONS[LANGUAGE]['edit'],
            size_hint_x=0.1,
            background_color=(0.7, 0.9, 0.7, 1)  # Цвет кнопки "Редактировать"
        )
        btn_edit.bind(on_press=self.edit_text)
        btn_delete = Button(
            text=TRANSLATIONS[LANGUAGE]['delete'],
            size_hint_x=0.1,
            background_color=(0.8, 0.2, 0.2, 1)  # Цвет кнопки "Удалить"
        )
        btn_delete.bind(on_press=lambda x: self.on_remove())
        self.add_widget(btn_copy)
        self.add_widget(btn_edit)
        self.add_widget(btn_delete)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.border.rectangle = (self.x, self.y, self.width, self.height)

    def copy_text(self, *args):
        Clipboard.copy(self.text)

    def edit_text(self, *args):
        content = BoxLayout(orientation='vertical')
        ti = TextInput(text=self.text, multiline=True, size_hint_y=0.9)
        btn_save = Button(text=TRANSLATIONS[LANGUAGE]['save'], size_hint_y=0.1)
        content.add_widget(ti)
        content.add_widget(btn_save)
        popup = Popup(title=TRANSLATIONS[LANGUAGE]['edit'], content=content, size_hint=(1, 1))

        def save_and_close(instance):
            new_text = ti.text.strip()
            if new_text:
                self.text = new_text
                self.label.text = new_text
                self.on_edit(new_text)
                popup.dismiss()

        btn_save.bind(on_press=save_and_close)
        popup.open()

class TabContent(BoxLayout):
    def __init__(self, tab_name, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.tab_name = tab_name
        self.cells = []
        self.clipboard_set = set() if tab_name == "Clipboard" else None
        self.sort_alpha_reverse = False
        self.sort_length_reverse = False
        self.sort_type_reverse = False

        # Панель сортировки
        self.sort_bar = BoxLayout(size_hint_y=None, height=80)
        btn_alpha = Button(
            text=TRANSLATIONS[LANGUAGE]['sort_alpha'],  # Фиксированный текст "А - Я"
            size_hint_x=1/3,
            background_color=(0.5, 0.5, 0.5, 1)  # Цвет кнопки "А - Я"
        )
        btn_length = Button(
            text=TRANSLATIONS[LANGUAGE]['sort_length'],  # Фиксированный текст "ДЛИНА"
            size_hint_x=1/3,
            background_color=(0.5, 0.5, 0.5, 1)  # Цвет кнопки "ДЛИНА"
        )
        btn_type = Button(
            text=TRANSLATIONS[LANGUAGE]['sort_type'],  # Фиксированный текст "КОД"
            size_hint_x=1/3,
            background_color=(0.5, 0.5, 0.5, 1)  # Цвет кнопки "КОД"
        )
        btn_alpha.bind(on_press=self.sort_alpha)
        btn_length.bind(on_press=self.sort_length)
        btn_type.bind(on_press=self.sort_type)
        self.sort_bar.add_widget(btn_alpha)
        self.sort_bar.add_widget(btn_length)
        self.sort_bar.add_widget(btn_type)
        self.add_widget(self.sort_bar)

        # Список ячеек
        self.scroll = ScrollView()
        self.box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5, padding=10)
        self.box.bind(minimum_height=self.box.setter('height'))
        self.scroll.add_widget(self.box)
        self.add_widget(self.scroll)

        # Копирайт с ссылкой (измените текст и ссылку здесь)
        copyright_text = "[color=00FFFF][ref=https://t.me/pro_100_design]Дмитрий Кузьмин[/ref][/color]"
        copyright_label = Label(
            text=copyright_text,
            markup=True,
            size_hint_y=None,
            height=30,
            halign='center'
        )
        copyright_label.bind(on_ref_press=lambda instance, url: print(f"Открытие ссылки: {url}"))
        self.add_widget(copyright_label)

        # Отступ для поднятия копирайта
        spacer = BoxLayout(size_hint_y=None, height=40)  # Увеличен до 40 пикселей
        self.add_widget(spacer)

        # Кнопка добавления
        add_btn = Button(
            text=TRANSLATIONS[LANGUAGE]['add'],
            size_hint_y=None,
            height=80,
            background_color=(0.3, 0.7, 0.3, 1)  # Цвет кнопки "Добавить"
        )
        add_btn.bind(on_press=self.add_cell_popup)
        self.add_widget(add_btn)

        self.load_cells()

        if tab_name == "Clipboard":
            cursor.execute(f'SELECT text FROM {self.tab_name.lower()}')
            for row in cursor.fetchall():
                self.clipboard_set.add(row[0])
            Clock.schedule_interval(self.check_clipboard, 1)

    def sort_alpha(self, instance):
        self.sort_alpha_reverse = not self.sort_alpha_reverse
        self.cells.sort(key=lambda x: x.text.lower(), reverse=self.sort_alpha_reverse)
        self.reload_box()

    def sort_length(self, instance):
        self.sort_length_reverse = not self.sort_length_reverse
        self.cells.sort(key=lambda x: len(x.text), reverse=self.sort_length_reverse)
        self.reload_box()

    def sort_type(self, instance):
        self.sort_type_reverse = not self.sort_type_reverse
        self.cells.sort(key=lambda x: self.count_keywords(x.text), reverse=not self.sort_type_reverse)
        self.reload_box()

    def count_keywords(self, text):
        return sum(len(re.findall(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE)) for kw in PROGRAMMING_KEYWORDS)

    def reload_box(self):
        self.box.clear_widgets()
        for cell in self.cells:
            self.box.add_widget(cell)

    def load_cells(self):
        cursor.execute(f'SELECT id, text FROM {self.tab_name.lower()}')
        rows = cursor.fetchall()
        self.cells.clear()
        self.box.clear_widgets()
        for row in rows:
            cell_id, text = row
            self.add_cell(text, cell_id)

    def add_cell_popup(self, *args):
        ti = TextInput(hint_text='Введите текст', multiline=True)
        btn_add = Button(
            text=TRANSLATIONS[LANGUAGE]['add'],
            size_hint_y=None,
            height=60,
            background_color=(0.3, 0.7, 0.3, 1)  # Цвет кнопки "Добавить" в окне
        )
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(ti)
        layout.add_widget(btn_add)
        popup = Popup(title=TRANSLATIONS[LANGUAGE]['new_cell'], content=layout, size_hint=(0.9, 0.5), pos_hint={'top': 0.95})

        def add_and_close(instance):
            text = ti.text.strip()
            if text:
                self.add_cell(text)
                popup.dismiss()

        btn_add.bind(on_press=add_and_close)
        popup.open()

    def add_cell(self, text, cell_id=None):
        if cell_id is None:
            cursor.execute(f'INSERT INTO {self.tab_name.lower()} (text) VALUES (?)', (text,))
            conn.commit()
            cell_id = cursor.lastrowid

        cell = Cell(text, cell_id,
                    on_edit=lambda new_text: self.update_cell(cell_id, new_text),
                    on_remove=lambda: self.remove_cell(cell_id))
        self.cells.append(cell)
        self.box.add_widget(cell)

    def update_cell(self, cell_id, new_text):
        cursor.execute(f'UPDATE {self.tab_name.lower()} SET text = ? WHERE id = ?', (new_text, cell_id))
        conn.commit()
        for cell in self.cells:
            if cell.cell_id == cell_id:
                cell.text = new_text
                self.label.text = new_text
                break

    def remove_cell(self, cell_id):
        cursor.execute(f'DELETE FROM {self.tab_name.lower()} WHERE id = ?', (cell_id,))
        conn.commit()
        for cell in self.cells:
            if cell.cell_id == cell_id:
                self.box.remove_widget(cell)
                self.cells.remove(cell)
                break

    def check_clipboard(self, dt):
        try:
            content = Clipboard.paste()
            if content and content.strip() and content not in self.clipboard_set:
                self.clipboard_set.add(content)
                self.add_cell(content)
                cursor.execute(f'SELECT COUNT(*) FROM {self.tab_name.lower()}')
                count = cursor.fetchone()[0]
                if count > MAX_CLIPBOARD:
                    cursor.execute(f'SELECT id FROM {self.tab_name.lower()} ORDER BY id ASC LIMIT 1')
                    oldest_id = cursor.fetchone()[0]
                    cursor.execute(f'DELETE FROM {self.tab_name.lower()} WHERE id = ?', (oldest_id,))
                    conn.commit()
                    for cell in self.cells:
                        if cell.cell_id == oldest_id:
                            self.box.remove_widget(cell)
                            self.cells.remove(cell)
                            break
        except Exception as e:
            print(f"Ошибка при чтении буфера обмена: {e}")

class NotepadApp(TabbedPanel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_default_tab = False
        # Цвета вкладок
        colors = [
            (0.9, 0.7, 0.7, 1),  # Вкладка 1
            (0.7, 0.9, 0.7, 1),  # Вкладка 2
            (0.7, 0.7, 0.9, 1),  # Вкладка 3
            (0.9, 0.9, 0.7, 1),  # Вкладка 4
            (0.8, 0.7, 0.9, 1),  # Вкладка 5
            (0.7, 0.9, 0.9, 1)   # Вкладка 6
        ]
        for i, name in enumerate(TABS):
            tab = TabbedPanelItem(text=TRANSLATIONS[LANGUAGE][name.lower()], background_color=colors[i % len(colors)])
            tab.content = TabContent(name)
            self.add_widget(tab)

        # Установка первой вкладки ("Заметки") по умолчанию
        self.default_tab = self.tab_list[0]

class MainApp(App):
    def build(self):
        return NotepadApp()

if __name__ == '__main__':
    MainApp().run()