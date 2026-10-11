import telebot

TOKEN = "8410579644:AAFAx9BEaQoQkETCjGKBoX3mP4pnBXmEeV8"
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=["start"])
def send_chat_id(message):
    bot.reply_to(message, f"Chat ID: {message.chat.id}")


if __name__ == "__main__":
    bot.infinity_polling()
