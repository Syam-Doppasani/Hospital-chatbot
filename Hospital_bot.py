import logging
import gspread
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from oauth2client.service_account import ServiceAccountCredentials

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(name)

# State definitions
NAME, AGE, ISSUE, EMAIL = range(4)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Enter_your_google_sheet_name").sheet1

# Email setup
EMAIL_USER = "Enter_sender_email.id"
EMAIL_PASS = "Enter_Your_Password"

def send_confirmation_email(name, age, issue, email):
    try:
        subject = "Hospital Appointment Confirmation"
        body = f"""
        Hello {name},

        Your appointment has been successfully booked.
        Age: {age}
        Issue: {issue}

        Thank you for choosing City Hospital.
        """

        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, email, msg.as_string())
        server.quit()
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📋 Hospital Info", callback_data="info")],
        [InlineKeyboardButton("🏥 Book Appointment", callback_data="book")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "\U0001F3E5 *Welcome to Grenich Hospital!*\n\n"
        "Use the buttons below to:\n"
        "• 📋 View hospital info\n"
        "• 🏥 Book an appointment\n\n"
        "_Please do not type manually. Use buttons only._",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "info":
        await query.message.reply_text(
            "🏥 *Grenich Hospital Info:*\n"
            "- Cardiology, Ortho, Pediatrics\n"
            "🕘 9 AM – 6 PM\n"
            "📞 123-456-7890",
            parse_mode="Markdown"
        )

    elif query.data == "book":
        await query.message.reply_text("👤 Please enter your full name:")
        return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("🧓 Please enter your age:")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["age"] = update.message.text
    await update.message.reply_text("🩺 Please describe your issue:")
    return ISSUE

async def get_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["issue"] = update.message.text
    await update.message.reply_text("📧 Enter your email address:")
    return EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email"] = update.message.text

    name = context.user_data["name"]
    age = context.user_data["age"]
    issue = context.user_data["issue"]
    email = context.user_data["email"]

    sheet.append_row([name, age, issue, email])
    send_confirmation_email(name, age, issue, email)
await update.message.reply_text(
        "✅ Appointment booked and confirmation email sent!",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("❌ Cancel")]], resize_keyboard=True
        )
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Process cancelled. Type /start to begin again.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token("Enter_your_token").build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^book$")],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            ISSUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_issue)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
        },
        fallbacks=[MessageHandler(filters.Regex("❌ Cancel"), cancel)],
        per_chat=True,
        per_message=False
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(info|book)$"))

    print("🤖 Bot is running...")
    app.run_polling()

if name == 'main':
    main()
