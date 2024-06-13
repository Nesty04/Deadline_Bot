from datetime import datetime, timedelta
import telebot
from Deadline_and_Notification import Deadline, Notification
import threading
import sqlite3


class DeadlineBot:
    def __init__(self, token: str):
        self.bot = telebot.TeleBot(token)
        self.user_data = {}
        self.conn = sqlite3.connect('deadlines.db', check_same_thread=False)
        self.create_tables()
        self.load_user_data()

        # Настройка команд
        self.bot.message_handler(commands=['start'])(self.start)
        self.bot.message_handler(commands=['add_deadline'])(self.add_deadline)
        self.bot.message_handler(commands=['add_notification'])(self.add_notification)
        self.bot.message_handler(commands=['edit_notification'])(self.edit_notification)
        self.bot.message_handler(commands=['list_deadlines'])(self.list_deadlines)
        self.bot.message_handler(commands=['delete_deadline'])(self.delete_deadline)
        self.bot.message_handler(commands=['list_notification'])(self.list_notification)
        self.bot.message_handler(commands=['edit_deadline'])(self.edit_deadline)
        self.bot.message_handler(commands=['delete_notification'])(self.delete_notification)

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS deadlines (
                            chat_id INTEGER,
                            name TEXT,
                            due_date TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS notifications (
                            chat_id INTEGER,
                            time TEXT)''')
        self.conn.commit()

    def load_user_data(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM deadlines')
        deadlines = cursor.fetchall()
        cursor.execute('SELECT * FROM notifications')
        notifications = cursor.fetchall()

        for chat_id, name, due_date in deadlines:
            if chat_id not in self.user_data:
                self.user_data[chat_id] = {'deadlines': [], 'notifications': []}
            self.user_data[chat_id]['deadlines'].append(Deadline(name, datetime.strptime(due_date, '%d.%m.%Y %H:%M')))

        for chat_id, time in notifications:
            if chat_id not in self.user_data:
                self.user_data[chat_id] = {'deadlines': [], 'notifications': []}
            self.user_data[chat_id]['notifications'].append(Notification(datetime.strptime(time, '%H:%M')))

    def save_deadline(self, chat_id, name, due_date):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO deadlines (chat_id, name, due_date) VALUES (?, ?, ?)',
                       (chat_id, name, due_date.strftime('%d.%m.%Y %H:%M')))
        self.conn.commit()

    def delete_deadline_from_db(self, chat_id, name):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM deadlines WHERE chat_id = ? AND name = ?', (chat_id, name))
        self.conn.commit()

    def save_notification(self, chat_id, time):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO notifications (chat_id, time) VALUES (?, ?)',
                       (chat_id, time.strftime('%H:%M')))
        self.conn.commit()

    def delete_notification_from_db(self, chat_id, time):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM notifications WHERE chat_id = ? AND time = ?',
                       (chat_id, time.strftime('%H:%M')))
        self.conn.commit()

    def start(self, message):
        chat_id = message.chat.id
        if chat_id not in self.user_data:
            self.user_data[chat_id] = {'deadlines': [], 'notifications': []}
        self.bot.send_message(chat_id, "Добро пожаловать в дедлайн-бот! Используйте /add_deadline, \
/add_notification, /edit_notification, /list_deadlines, /list_notification, /delete_deadline, чтобы управлять вашими дедлайнами и уведомлениями!")
        time = datetime.strptime('12:00', "%H:%M").time()
        notification_time = datetime.combine(datetime.now(), time)
        self.user_data[chat_id]['notifications'].append(Notification(notification_time))
        self.save_notification(chat_id, notification_time)
        self.schedule_notification(chat_id, notification_time)

    def add_deadline(self, message):
        chat_id = message.chat.id
        msg = self.bot.reply_to(message, 'Что надо сделать?')
        self.bot.register_next_step_handler(msg, self.process_name_deadline, chat_id)

    def process_name_deadline(self, message, chat_id):
        name = message.text
        self.user_data[chat_id]['current_deadline_name'] = name
        msg = self.bot.reply_to(message, 'Введите дату дедлайна в формате <DD.MM.YYYY> <HH:MM>')
        self.bot.register_next_step_handler(msg, self.process_date_deadline, chat_id)

    def process_date_deadline(self, message, chat_id):
        try:
            due_date = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
            formatted_date = due_date.strftime('%d.%m.%Y %H:%M')
            now = datetime.now()
            if due_date < now:
                self.bot.send_message(chat_id, 'Дедлайн уже сгорел!')
            else:
                name = self.user_data[chat_id].pop('current_deadline_name')
                self.user_data[chat_id]['deadlines'].append(Deadline(name, due_date))
                self.save_deadline(chat_id, name, due_date)
                self.bot.send_message(chat_id, f"Дедлайн '{name}' установлен на {formatted_date}")
        except (IndexError, ValueError):
            self.bot.send_message(chat_id, "Использование: <DD.MM.YYYY> <HH:MM>")

    def delete_deadline(self, message):
        chat_id = message.chat.id
        msg = self.bot.reply_to(message, 'Введите название дедлайна, который нужно удалить:')
        self.bot.register_next_step_handler(msg, self.process_name_delete_deadline, chat_id)

    def process_name_delete_deadline(self, message, chat_id):
        name = message.text
        self.user_data[chat_id]['deadlines'] = [deadline for deadline in self.user_data[chat_id]['deadlines'] if deadline.name != name]
        self.delete_deadline_from_db(chat_id, name)
        self.bot.send_message(chat_id, f'Дэдлайн {name} удалён')

    def edit_deadline(self, message):
        chat_id = message.chat.id
        msg = self.bot.reply_to(message, 'Введите название дедлайна, который нужно изменить:')
        self.bot.register_next_step_handler(msg, self.process_name_edit_deadline, chat_id)

    def process_name_edit_deadline(self, message, chat_id):
        self.user_data[chat_id]['current_edit_deadline_name'] = message.text
        msg = self.bot.reply_to(message, 'Введите новую дату дедлайна в формате <DD.MM.YYYY> <HH:MM>')
        self.bot.register_next_step_handler(msg, self.process_date_edit_deadline, chat_id)

    def process_date_edit_deadline(self, message, chat_id):
        try:
            new_due_date = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
            formatted_new_due_date = new_due_date.strftime('%d.%m.%Y %H:%M')
            now = datetime.now()
            if new_due_date < now:
                self.bot.send_message(chat_id, 'Новая дата дедлайна уже прошла!')
            else:
                name = self.user_data[chat_id].pop('current_edit_deadline_name')
                deadlines = self.user_data[chat_id]['deadlines']
                for deadline in deadlines:
                    if deadline.name == name:
                        self.delete_deadline_from_db(chat_id, name)
                        deadline.due_date = new_due_date
                        self.save_deadline(chat_id, name, new_due_date)
                        self.bot.send_message(chat_id, f"Дедлайн '{name}' изменен на {formatted_new_due_date}")
                        break
                else:
                    self.bot.send_message(chat_id, "Дедлайн не найден.")
        except (IndexError, ValueError):
            self.bot.send_message(chat_id, "Использование: <DD.MM.YYYY> <HH:MM>")

    def add_notification(self, message):
        chat_id = message.chat.id
        msg = self.bot.reply_to(message, 'Введите время уведомления в формате: <HH:MM>')
        self.bot.register_next_step_handler(msg, self.process_time_notification, chat_id)

    def process_time_notification(self, message, chat_id):
        try:
            time = datetime.strptime(message.text, "%H:%M").time()
            notification_time = datetime.combine(datetime.now(), time)
            if any(n.time.time() == time for n in self.user_data[chat_id]['notifications']):
                self.bot.send_message(chat_id, "Уведомление на это время уже установлено.")
            else:
                self.user_data[chat_id]['notifications'].append(Notification(notification_time))
                self.save_notification(chat_id, notification_time)
                self.schedule_notification(chat_id, notification_time)
                self.bot.send_message(chat_id, f"Уведомление установлено на: {time.strftime('%H:%M')}")
        except (IndexError, ValueError):
            self.bot.send_message(chat_id, "Формат: <HH:MM>")

    def list_notification(self, message):
        chat_id = message.chat.id
        notifications = self.user_data[chat_id]['notifications']
        valid_notifications = []
        for notification1 in notifications:
            for notification2 in notifications:
                if notification1.time != notification2.time and notification1 != notification2:
                    valid_notifications.append(notification1)
        self.user_data[chat_id]['notifications'] = valid_notifications
        if not notifications:
            self.bot.send_message(chat_id, "Никаких уведомлений не установлено.")
        else:
            notifications_str = "\n".join(str(notification) for notification in notifications)
            self.bot.send_message(chat_id, f"Текущие уведомления:\n{notifications_str}")

    def delete_notification(self, message):
        chat_id = message.chat.id
        msg = self.bot.reply_to(message, 'Введите время уведомления в формате: <HH:MM>, которое нужно удалить:')
        self.bot.register_next_step_handler(msg, self.process_time_delete_notification, chat_id)

    def process_time_delete_notification(self, message, chat_id):
        try:
            time = datetime.strptime(message.text, "%H:%M")
            notifications = self.user_data[chat_id]['notifications']
            for notification in notifications:
                if notification.time.time() == time.time():
                    self.delete_notification_from_db(chat_id, time)
                    self.user_data[chat_id]['notifications'].remove(notification)
                    self.bot.send_message(chat_id, f"Уведомление на время {time.strftime('%H:%M')} удалено.")
                    break
                else:
                    self.bot.send_message(chat_id, f"Уведомление на время {time.strftime('%H:%M')} не найдено.")
        except (IndexError, ValueError):
            self.bot.send_message(chat_id, "Формат: <HH:MM>")

    def edit_notification(self, message):
        chat_id = message.chat.id
        msg = self.bot.reply_to(message, 'Введите старое и новое время в формате: <old_HH:MM> <new_HH:MM>')
        self.bot.register_next_step_handler(msg, self.process_time_edit_notification, chat_id)

    def process_time_edit_notification(self, message, chat_id):
        try:
            old_time_str, new_time_str = message.text.split()
            old_time = datetime.strptime(old_time_str, "%H:%M").time()
            new_time = datetime.strptime(new_time_str, "%H:%M").time()
            notifications = self.user_data[chat_id]['notifications']
            for notification in notifications:
                if notification.time.time() == old_time:
                    self.delete_notification_from_db(chat_id, old_time)
                    self.user_data[chat_id]['notifications'].remove(notification.time)
                    notification.time = datetime.combine(datetime.now(), new_time)
                    self.save_notification(chat_id, notification.time)
                    self.schedule_notification(chat_id, notification.time)
                    self.bot.send_message(chat_id, f"Время уведомления обновлено с {old_time.strftime('%H:%M')} на {new_time.strftime('%H:%M')}")
                    break
            else:
                self.bot.send_message(chat_id, "Не найдено никаких уведомлений на это время.")
        except (IndexError, ValueError):
            self.bot.send_message(chat_id, "Использование: <old_HH:MM> <new_HH:MM>")

    def list_deadlines(self, message):
        chat_id = message.chat.id
        valid_deadlines = []
        now = datetime.now()
        deadlines = self.user_data[chat_id]['deadlines']
        for deadline in deadlines:
            if deadline.due_date > now:
                valid_deadlines.append(deadline)
            else:
                self.delete_deadline_from_db(chat_id, deadline.name)
        self.user_data[chat_id]['deadlines'] = valid_deadlines
        if not deadlines:
            self.bot.send_message(chat_id, "Никаких дедлайнов не установлено.")
        else:
            deadlines_str = "\n".join(str(deadline) for deadline in deadlines)
            self.bot.send_message(chat_id, f"Текущие дедлайны:\n{deadlines_str}")

    def schedule_notification(self, chat_id, time: datetime):
        now = datetime.now()
        target_time = time
        if target_time < now:
            target_time += timedelta(days=1)
        delay = (target_time - now).total_seconds()
        threading.Timer(delay, self.send_notifications, args=(chat_id,)).start()

    def send_notifications(self, chat_id):
        deadlines = self.user_data[chat_id]['deadlines']
        deadlines_str = "\n".join(str(deadline) for deadline in deadlines)
        if deadlines_str:
            self.bot.send_message(chat_id, f"Предстоящие дедлайны:\n{deadlines_str}")
        else:
            self.bot.send_message(chat_id, "Нет никаких дедлайнов.")

    def run(self):
        self.bot.infinity_polling()