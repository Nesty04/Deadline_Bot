from datetime import datetime, timedelta
import telebot
from Deadline_and_Notification import Deadline, Notification
import threading

class DeadlineBot:
    def __init__(self, token: str):
        self.bot = telebot.TeleBot(token)
        self.user_data = {}

        # Настройка команд
        self.bot.message_handler(commands=['start'])(self.start)
        self.bot.message_handler(commands=['add_deadline'])(self.add_deadline)
        self.bot.message_handler(commands=['add_notification'])(self.add_notification)
        self.bot.message_handler(commands=['edit_notification'])(self.edit_notification)
        self.bot.message_handler(commands=['list_deadlines'])(self.list_deadlines)
        self.bot.message_handler(commands=['delete_deadline'])(self.delete_deadline)
        self.bot.message_handler(commands=['list_notification'])(self.list_notification)

    def start(self, message):
        chat_id = message.chat.id
        self.user_data[chat_id] = {
            'deadlines': [],
            'notifications': []
        }
        self.bot.send_message(chat_id, "Добро пожаловать в дедлайн-бот! Используйте /add_deadline, \
/add_notification, /edit_notification, /list_deadlines, /list_notification, /delete_deadline, чтобы управлять вашими дедлайнами и уведомлениями!")
        time = datetime.strptime('12:00', "%H:%M").time()
        notification_time = datetime.combine(datetime.now(), time)
        self.user_data[chat_id]['notifications'].append(Notification(notification_time))
        self.schedule_notification(chat_id, notification_time)

    def add_deadline(self, message):
        chat_id = message.chat.id
        msg = self.bot.reply_to(message, 'Что надо сделать?')
        self.bot.register_next_step_handler(msg, self.process_name_deadline, chat_id)

    def process_name_deadline(self, message, chat_id):
        name = message.text
        self.user_data[chat_id]['current_deadline_name'] = name
        msg = self.bot.reply_to(message, 'Введите дату дедлайна в формате <DD-MM-YYYY> <HH:MM>')
        self.bot.register_next_step_handler(msg, self.process_date_deadline, chat_id)

    def process_date_deadline(self, message, chat_id):
        try:
            due_date = datetime.strptime(message.text, "%d-%m-%Y %H:%M")
            now = datetime.now()
            if due_date < now:
                self.bot.send_message(chat_id, 'Дедлайн уже сгорел!')
            else:
                name = self.user_data[chat_id].pop('current_deadline_name')
                self.user_data[chat_id]['deadlines'].append(Deadline(name, due_date))
                self.bot.send_message(chat_id, f"Дедлайн '{name}' установлен на {due_date}")
        except (IndexError, ValueError):
            self.bot.send_message(chat_id, "Использование: <DD-MM-YYYY> <HH:MM>")

    def delete_deadline(self, message):
        chat_id = message.chat.id
        msg = self.bot.reply_to(message, 'Введите название дедлайна, который нужно удалить:')
        self.bot.register_next_step_handler(msg, self.process_name_delete_deadline, chat_id)

    def process_name_delete_deadline(self, message, chat_id):
        name = message.text
        self.user_data[chat_id]['deadlines'] = [deadline for deadline in self.user_data[chat_id]['deadlines'] if deadline.name != name]

    def add_notification(self, message):
        chat_id = message.chat.id
        msg = self.bot.reply_to(message, 'Введите время уведомления в формате: <HH:MM>')
        self.bot.register_next_step_handler(msg, self.process_time_notification, chat_id)

    def process_time_notification(self, message, chat_id):
        try:
            time = datetime.strptime(message.text, "%H:%M").time()
            notification_time = datetime.combine(datetime.now(), time)
            self.user_data[chat_id]['notifications'].append(Notification(notification_time))
            self.schedule_notification(chat_id, notification_time)
            self.bot.send_message(chat_id, f"Уведомление установлено на: {time}")
        except (IndexError, ValueError):
            self.bot.send_message(chat_id, "Формат: <HH:MM>")


    def list_notification(self, message):
        chat_id = message.chat.id
        notifications = self.user_data[chat_id]['notifications']
        if not notifications:
            self.bot.send_message(chat_id, "Никаких уведомлений не установлено.")
        else:
            notifications_str = "\n".join(str(notification) for notification in notifications)
            self.bot.send_message(chat_id, f"Текущие уведомления:\n{notifications_str}")

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
                    notification.time = datetime.combine(datetime.now(), new_time)
                    self.schedule_notification(chat_id, notification.time)
                    self.bot.send_message(chat_id, f"Время уведомления обновлено с {old_time} на {new_time}")
                    break
            else:
                self.bot.send_message(chat_id, "Не найдено никаких уведомлений на это время.")
        except (IndexError, ValueError):
            self.bot.send_message(chat_id, "Использование: <old_HH:MM> <new_HH:MM>")

    def list_deadlines(self, message):
        chat_id = message.chat.id
        now = datetime.now()
        deadlines = self.user_data[chat_id]['deadlines']
        self.user_data[chat_id]['deadlines'] = [deadline for deadline in deadlines if deadline.due_date > now]
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
