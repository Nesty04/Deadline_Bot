
import telebot

from datetime import datetime, timedelta
import threading

class Deadline:
    def __init__(self, name: str, due_date: datetime):
        self.name = name
        self.due_date = due_date

    def __str__(self):
        return f"{self.name} - {self.due_date.strftime('%d-%m-%Y %H:%M')}"

class Notification:
    def __init__(self, time: datetime):
        self.time = time

    def __str__(self):
        return f"Уведомление в {self.time.strftime('%H:%M')}"

class DeadlineBot:
    def __init__(self, token: str):
        self.bot = telebot.TeleBot(token)
        self.name = ''
        self.date = []
        self.deadlines = []
        self.notifications = []
        self.chat_id = None
        

        # Настройка команд
        self.bot.message_handler(commands=['start'])(self.start)
        self.bot.message_handler(commands=['add_deadline'])(self.add_deadline)
        self.bot.message_handler(commands=['add_notification'])(self.add_notification)
        self.bot.message_handler(commands=['edit_notification'])(self.edit_notification)
        self.bot.message_handler(commands=['list_deadlines'])(self.list_deadlines)
        self.bot.message_handler(commands=['delete_deadline'])(self.delete_deadline)
        self.bot.message_handler(commands=['list_notification'])(self.list_notification)


    def start(self, message):
        self.chat_id = message.chat.id
        self.bot.send_message(message.chat.id, "Добро пожаловать в дедлайн-бот! Используйте /add_deadline, \
                              /add_notification, /edit_notification, /list_deadlines, /list_notification, /delete_deadline,  чтобы мэнэджить ваши дэдлайны и уведомления!")
        time = datetime.strptime('12:00', "%H:%M").time()
        self.notifications.append(Notification(datetime.combine(datetime.now(), time)))
        self.schedule_notification(datetime.combine(datetime.now(), time))

    def add_deadline(self, message):
        msg = self.bot.reply_to(message, 'Что надо сделать?')
        self.bot.register_next_step_handler(msg, self.process_name_deadline)

    def process_name_deadline(self, message):
        try:
            arg = message.text
            self.name = arg
            msg = self.bot.reply_to(message, 'Введите дату дедлайна!')
        except (IndexError, ValueError):
            self.bot.send_message(message.chat.id,'Использование: <name>')
        self.bot.register_next_step_handler(msg, self.process_date_deadline)

    def process_date_deadline(self, message):
        try:
            now = datetime.now()
            args = message.text.split()
            due_date = datetime.strptime(args[0] + " " + args[1], "%d-%m-%Y %H:%M")
            if due_date < now:
                self.bot.send_message(message.chat.id, 'Дэдлайн уже сгорел!')
            else:
                self.deadlines.append(Deadline(self.name, due_date))
                self.bot.send_message(message.chat.id, f"Дэдлайн '{self.name}' установлен на {due_date}")
        except (IndexError, ValueError):
            self.bot.send_message(message.chat.id, "Использование:  <DD-MM-YYYY> <HH:MM>")


    def delete_deadline(self, message):
        args = message.text.split()
        print(args)
        self.deadlines = [deadline for deadline in self.deadlines if deadline.name != ' '.join(args[1:])]

    def add_notification(self, message):
        msg = self.bot.reply_to(message, 'Введите время уведомления в формате: <HH:MM>')
        self.bot.register_next_step_handler(msg, self.process_time_notification)

    def process_time_notification(self, message):
        try:
            args = message.text
            time = datetime.strptime(args, "%H:%M").time()
            notification_time = datetime.combine(datetime.now(), time)
            self.notifications.append(Notification(notification_time))
            self.schedule_notification(notification_time)
            self.bot.send_message(message.chat.id, f"Уведомление установлено на: {time}")
        except (IndexError, ValueError):
            self.bot.send_message(message.chat.id, "Формат: <HH:MM>")
    # def add_notification(self, message):
    #     try:
    #         args = message.split()[1:]
    #         args = message.text.split()[1:]
    #         time = datetime.strptime(args[0], "%H:%M").time()
    #         notification_time = datetime.combine(datetime.now(), time)
    #         self.notifications.append(Notification(notification_time))
    #         self.schedule_notification(notification_time)
    #         self.bot.send_message(message.chat.id, f"Notification set for {time}")
    #     except (IndexError, ValueError):
    #         self.bot.send_message(message.chat.id, "Usage: /add_notification <HH:MM>")
    
    def list_notification(self, message):
        if not self.notifications:
            self.bot.send_message(message.chat.id, "Никаких уведомлений не установлено.")
        else:
            notifications_str = "\n".join(str(notification) for notification in self.notifications)
            self.bot.send_message(message.chat.id, f"Текущие уведомления:\n{notifications_str}")

    def edit_notification(self, message):
        try:
            args = message.text.split()[1:]
            old_time = datetime.strptime(args[0], "%H:%M").time()
            new_time = datetime.strptime(args[1], "%H:%M").time()
            for notification in self.notifications:
                if notification.time.time() == old_time:
                    notification.time = datetime.combine(datetime.now(), new_time)
                    self.schedule_notification(notification.time)
                    self.bot.send_message(message.chat.id,
                                           f"Время уведомления обновлено с {old_time} на {new_time}")
                    break
            else:
                self.bot.send_message(message.chat.id, "Не найдено никаких уведомлений на это время.")
        except (IndexError, ValueError):
            self.bot.send_message(message.chat.id, "Использование: /edit_notification <old_HH:MM> <new_HH:MM>")

    def list_deadlines(self, message):
        now = datetime.now()
        self.deadlines = [deadline for deadline in self.deadlines if deadline.due_date > now]
        if not self.deadlines:
            self.bot.send_message(message.chat.id, "Никаких дэдлайнов не установлено.")
        else:
            deadlines_str = "\n".join(str(deadline) for deadline in self.deadlines)
            self.bot.send_message(message.chat.id, f"Текущие дэдлайны:\n{deadlines_str}")


    def schedule_notification(self, time: datetime):
        now = datetime.now()
        target_time = time
        if target_time < now:
            target_time += timedelta(days=1)
        delay = (target_time - now).total_seconds()
        threading.Timer(delay, self.send_notifications).start()


    def send_notifications(self):
        deadlines_str = "\n".join(str(deadline) for deadline in self.deadlines)
        if deadlines_str:
            self.bot.send_message(self.chat_id, f"Предстоящие дэдлайны:\n{deadlines_str}")
        else:
            self.bot.send_message(self.chat_id, "Нет никаких дэдлайнов.")

    def run(self):
        self.bot.infinity_polling()
        

if __name__ == "__main__":
    TOKEN = "7204734336:AAGpG5Ovp1-r8btiPDfZsK3fgtdu7C-uj4w"
    bot = DeadlineBot(TOKEN)
    bot.run()