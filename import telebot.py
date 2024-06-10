import telebot


token = ''
bot = telebot.TeleBot(token)

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "Howdy, how are you doing?")
bot.infinity_polling()