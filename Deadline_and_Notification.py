from datetime import datetime

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