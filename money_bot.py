import logging
from datetime import datetime
from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from telegram import Update
from telegram.ext import CallbackContext
import dropbox
import tempfile
import os
import io  

# Stadien der Konversation
START, SUPPORT, BUY, PRODUCT_SELECTION, CONFIRM_ADDRESS, CONFIRMATION, WAITING_PAYMENT, DELIVERY_CONFIRMED = range(8)

# Dropbox Token
token = 'sl.BggvoEOM1ps4Dl0DGHrERYSRVo73VsBQ-JqpImV5V1Zat4cS8B2VKzTeBo7JWOgbxSDX7lWhSX95fpOciKv7g2-JaNChzb932z1GogdzAs2tstiLdYWIp9Oz2NCjGMn9RwcURUVwXO8'

# Einrichten des Loggings
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO  # Hier das gewünschte Log-Level angeben, z.B. logging.DEBUG
)

logger = logging.getLogger(__name__)

# Handler für alle eingehenden Nachrichten
def log_all_messages(update, context):
    username = update.effective_user.username
    message_text = update.message.text
    logger.info("log_all_messages called")  # Debug-Nachricht hinzufügen

    # Nachricht speichern
    log_message(f"Message from {username}: {message_text}", username=username)

# Handler für "/start" Befehl
def start(update, context):
    reply_keyboard = [['Buy', 'Support']]
    update.message.reply_text(
        'Welcome to Fake Money Order Chat!\n Here you can easily place your orders.\n'
        'If there are problems please write "/restart" to start write "/start" in the chat.\n'
        'Please select an option:',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return START  # Setze den Konversationszustand auf START

# Handler für "Restart" Befehl
def restart(update: Update, context: CallbackContext):
    log_message('Restart requested', update)
    update.message.reply_text(
        '/restart',
        reply_markup=ReplyKeyboardMarkup([['Buy', 'Support']])
    )
    return START

# Handler für "Support" Option
def support(update, context):
    username = update.message.from_user.username
    log_message(f"Support requested by user {username}", update)  # Benötigt das "update"-Objekt

    context.user_data['name'] = None  # Zur Speicherung des Namens des Benutzers
    update.message.reply_text(
        'Please enter your Telegram username (@...) and briefly describe your concern or problem.\n'
        'We will contact you within a week.',
        reply_markup=ReplyKeyboardMarkup([['/restart']], one_time_keyboard=True)
    )

    return 'wait_for_username'  # Auf Benutzerantwort warten

# Erstelle eine Verbindung zur Dropbox
dbx = dropbox.Dropbox(token)

# Handler für Benutzerantwort
def wait_for_username(update, context):
    username = update.message.from_user.username
    user_response = update.message.text

    # Benutzernamen speichern
    context.user_data['name'] = username

    # Nachricht speichern
    log_message(f"User {username} response: {user_response}", update)

    # Dateinamen festlegen
    file_name = "support_names.txt"

    # Datei von Dropbox herunterladen, falls vorhanden
    try:
        _, res = dbx.files_download(f"/logs/{file_name}")
        existing_content = res.content
    except dropbox.exceptions.ApiError:
        existing_content = b""  # Leerer Inhalt, wenn die Datei nicht vorhanden ist

    # Neuen Inhalt hinzufügen
    updated_content = existing_content + user_response.encode('utf-8') + b'\n'

    # Dateiinhalt aktualisieren und wieder hochladen
    updated_file = io.BytesIO(updated_content)
    dbx.files_upload(updated_file.read(), f"/logs/{file_name}", mode=dropbox.files.WriteMode.overwrite)

    return START

# Handler für "Buy" Option
def buy(update, context):
    reply_keyboard = [['100€ = 2000€', '200€ = 5000€', '400€ = 1200€', '500€ = 15000€', '1000€ = 40000€']]
    update.message.reply_text(
        'You can find a product picture in the profile picture.\n'
        'If you want to see more product pictures before you order write us via our support section.\n'
        'To get there type /restart then press Support.\n'
        'Please select a product:',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return PRODUCT_SELECTION

# Handler für Produktauswahl
def product_selection(update, context):
    product = update.message.text
    log_message(f"Product selected: {product}", update)  # Benötigt das "update"-Objekt
    update.message.reply_text(
        'Please enter your name & complete address where you want your delivery to arrive.\n'
        'Username, First name (optional), last name, country, postal code, city, street & number'
    )
    return CONFIRM_ADDRESS

# Handler für Adresseingabe
def confirm_address(update, context):
    address = update.message.text
    log_message(f"Address confirmed: {address}", update)  # Benötigt das "update"-Objekt
    reply_keyboard = [['Confirm', '/restart']]
    update.message.reply_text(
        f'Please confirm your name & address:\n{address}\n\n'
        'Press "Confirm" to proceed or "/restart" to start over.',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return CONFIRMATION

# Handler für Zahlungsbestätigung
def confirmation(update, context):
    choice = update.message.text
    if choice == 'Confirm':
        update.message.reply_text(
            'Please send the money to the following Bitcoin Address and send a screenshot of the payment to this chat.\n'
            'Bitcoin Address:'
        )
        update.message.reply_text(
            '9d1a3f90-2655-462f-92e5-049b3a640102'
        )
        log_message("Payment confirmation requested", update)
        return WAITING_PAYMENT
    elif choice == 'Restart':
        log_message("Restart requested")
        return START
    
# Zahlungsbestätigung
def payment_confirmation(context):
    chat_id = context.job.context
    context.bot.send_message(
        chat_id=chat_id,
        text='Payment confirmed.\nYour delivery will be shipped within 1 month.',
        reply_markup=ReplyKeyboardMarkup([['/restart']], one_time_keyboard=True)
    )
    log_message("Payment confirmed", update=None)  # Hier das Update-Argument korrekt übergeben

# Handler für Lieferbestätigung
def delivery_confirmed(update, context):
    update.message.reply_text('Payment confirmed.\nYour delivery will be shipped within 1 month.')
    log_message("Delivery confirmed", username=update.effective_user.username)
    return start(update, context)

# Handler für unbekannte Eingaben
def unknown(update, context):
    update.message.reply_text("Sorry, I didn't understand that command.")

# Handler für das Speichern von Fotos und Videos und Fortsetzen des Gesprächs
def save_media_and_continue(update, context):
    chat_id = update.message.chat_id
    media = update.message.effective_attachment  # Medienanhang abrufen

    if media:
        if isinstance(media, list):
            file_id = media[-1].file_id  # Das letzte Element der Liste verwenden
        else:
            file_id = media.file_id

        # Medien speichern
        save_media(context.bot, chat_id, file_id)

        # Nachricht speichern
        log_message("Media saved", update)

        # Weitere Aktionen ausführen...
        update.message.reply_text('Waiting for confirmation of payment by a human.\nPlease wait...')

        # Setzen des Zeitplans für die Zahlungsbestätigung
        context.job_queue.run_once(payment_confirmation, 43200, context=update.message.chat_id)  # Zeit anpassen
    else:
        update.message.reply_text('Please send a photo or video.')  # Eine Benachrichtigung senden

def save_media(bot, chat_id, file_id):
    file = bot.get_file(file_id)
    file_extension = file.file_path.split('.')[-1]  # Dateierweiterung extrahieren
    file_path = f'/media/{file_id}.{file_extension}'  # Passe den Speicherort nach Bedarf an
    dbx = dropbox.Dropbox(token)
    file_data = io.BytesIO(file.download_as_bytearray())
    dbx.files_upload(file_data.read(), file_path)

# Funktion zum Schreiben des Logs mit Zeitstempel und Datum
def log_message(message, update):
    # Dropbox-Verbindung herstellen
    dbx = dropbox.Dropbox(token)

    # Dateipfad zur Logdatei
    log_file_path = "/logs/log.txt"
    _, res = dbx.files_download(log_file_path)

    # Datei herunterladen
    _, res = dbx.files_download(log_file_path)
    existing_content = res.content.decode('utf-8')

    # Inhalt der Lognachricht mit Zeitstempel und Datum
    log_content = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n"

    # Neuen Inhalt hinzufügen
    updated_content = existing_content + log_content

    # Aktualisierte Datei hochladen
    dbx.files_upload(updated_content.encode('utf-8'), log_file_path, mode=dropbox.files.WriteMode.overwrite)

# Handler für alle eingehenden Nachrichten mit Logging
def log_all_messages(update, context):
    message_text = update.message.text
    log_message(f"Message from {update.effective_user.username}: {message_text}", update)

    # Nachricht speichern
    log_message(message_text, username=update.effective_user.username)

# Hauptfunktion zum Start des Bots
def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    updater = Updater('6254784752:AAHSu42YYqbWPpjbRntw_GeyJIlJwGG3tak', use_context=True)  # Bot-Token

    dp = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            START: [MessageHandler(Filters.regex('^(Support)$'), support),
                    MessageHandler(Filters.regex('^(Buy)$'), buy)],
            SUPPORT: [MessageHandler(Filters.text, support)],
            PRODUCT_SELECTION: [MessageHandler(Filters.regex('^(100€ = 2000€|200€ = 5000€|400€ = 1200€|500€ = 15000€|1000€ = 40000€)$'), product_selection)],
            CONFIRM_ADDRESS: [MessageHandler(Filters.text, confirm_address)],
            CONFIRMATION: [MessageHandler(Filters.regex('^(Confirm)$'), confirmation)],
            WAITING_PAYMENT: [MessageHandler(Filters.photo | Filters.video, save_media_and_continue)],  # Aktualisierter Handler
            DELIVERY_CONFIRMED: [MessageHandler(Filters.text, delivery_confirmed)],
            'wait_for_username': [MessageHandler(Filters.text, wait_for_username)]
        },
        fallbacks=[CommandHandler('restart', restart)]
    )

    dp.add_handler(conv_handler)
    dp.add_handler(MessageHandler(Filters.command, unknown,Filters.text, log_all_messages))
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('restart', restart))


    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
    