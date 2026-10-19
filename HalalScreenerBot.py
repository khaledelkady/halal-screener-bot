import os
import uuid
import datetime
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from supabase import create_client, Client

# ==========================================
# ⚙️ الإعدادات العامة والتوكنات
# ==========================================
BOT_TOKEN = "8819247611:AAGkpqCE26vbEUAFjB_xXklerWW4rEcoxDA"
ADMIN_GROUP_ID = -1005329281552

SUPABASE_URL = "https://jwoqeqocruykcpdpmhbe.supabase.co"
SUPABASE_KEY = "sb_publishable_Fhv5oyonIHhZFvfb_67z0g_z-ke_TnZ"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

PACKAGES = {
    "pkg_1m": {"name": "اشتراك شهر واحد (1 Month)", "price": "$5", "days": 30},
    "pkg_3m": {"name": "اشتراك 3 أشهر (3 Months)", "price": "$15", "days": 90},
    "pkg_6m": {"name": "اشتراك 6 أشهر (6 Months)", "price": "$25", "days": 180},
    "pkg_1y": {"name": "اشتراك سنة كاملة (1 Year)", "price": "$50", "days": 365}
}

PAYMENT_DETAILS = (
    "💳 *بيانات الدفع المتاحة:*\n\n"
    "📱 *Vodafone Cash:* `+201063532958`\n"
    "🏦 *InstaPay:* `khaledalqadicib@instapay`\n"
    "🌐 *USDT (BEP20 / ERC20):*\n`0x252fdf5f78f907206e7e85f36cd08c6c67d89366`\n\n"
    "📌 بعد إتمام التحويل، يرجى إرسال صورة إيصال التحويل في هذه المحادثة فوراً لتأكيد الاشتراك وتوليد المفتاح."
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def generate_license_key(pkg_code):
    suffix = str(uuid.uuid4()).upper()[:8]
    prefix = "HALAL-1M" if "1m" in pkg_code else ("HALAL-3M" if "3m" in pkg_code else ("HALAL-6M" if "6m" in pkg_code else "HALAL-1Y"))
    return f"{prefix}-{suffix[:4]}-{suffix[4:]}"

def save_key_to_supabase(key, user_id, pkg_name, days):
    expiry_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    data = {
        "key": key,
        "user_id": user_id,
        "pkg_name": pkg_name,
        "expiry_date": expiry_date,
        "is_active": True,
        "hwid": None
    }
    supabase.table("keys").insert(data).execute()
    return expiry_date

PENDING_RECEIPTS = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"مرحباً بك {user.first_name} في بوت التفعيل الخاص بـ *فاحص الأسهم الشرعي* (Calm Capital) 🚀\n\n"
        "يمكنك اختيار الباقة المناسبة والاشتراك لتفعيل البرنامج فوراً على جهازك."
    )
    keyboard = [
        [InlineKeyboardButton("🛒 عرض باقات الاشتراك والأسعار", callback_data="show_packages")],
        [InlineKeyboardButton("ℹ️ المساعدة والدعم الفني", callback_data="help_support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "show_packages":
        keyboard = [
            [InlineKeyboardButton("🗓️ شهر واحد - $5", callback_data="buy_pkg_1m")],
            [InlineKeyboardButton("🗓️ 3 أشهر - $15", callback_data="buy_pkg_3m")],
            [InlineKeyboardButton("🗓️ 6 أشهر - $25", callback_data="buy_pkg_6m")],
            [InlineKeyboardButton("🗓️ 1 سنة (أفضل قيمة) - $50", callback_data="buy_pkg_1y")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
        ]
        await query.message.edit_text("اختر باقة الاشتراك المناسبة لك:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "help_support":
        help_txt = (
            "ℹ️ *الدعم الفني والمساعدة:*\n\n"
            "• للاستفسار أو طلب المساعدة، تواصل مباشرة مع الإدارة عبر التليجرام: @k7Trader\n"
            "• بعد إتمام عملية الدفع ورفع الإيصال، يتم مراجعة التحويل وتوليد كود التفعيل خلال دقائق معدودة."
        )
        keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]]
        await query.message.edit_text(help_txt, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("buy_"):
        pkg_key = data.replace("buy_", "")
        pkg = PACKAGES.get(pkg_key)
        context.user_data["selected_pkg"] = pkg_key
        
        msg = f"لقد اخترت: *{pkg['name']}*\nالقيمة: *{pkg['price']}*\n\n" + PAYMENT_DETAILS
        keyboard = [[InlineKeyboardButton("🔙 العودة للباقات", callback_data="show_packages")]]
        await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "main_menu":
        await start_command(update, context)

    elif data.startswith("approve_"):
        receipt_id = data.replace("approve_", "")
        pending = PENDING_RECEIPTS.get(receipt_id)
        if pending:
            pkg_key = pending["pkg_key"]
            pkg = PACKAGES[pkg_key]
            user_id = pending["user_id"]
            key = generate_license_key(pkg_key)

            try:
                expiry_date = save_key_to_supabase(key, user_id, pkg["name"], pkg["days"])
                if receipt_id in PENDING_RECEIPTS:
                    del PENDING_RECEIPTS[receipt_id]

                success_msg = (
                    f"🎉 *تم تأكيد اشتراكك بنجاح!*\n\n"
                    f"📦 *الباقة:* {pkg['name']}\n"
                    f"🔑 *مفتاح التفعيل الخاص بك:*\n`{key}`\n\n"
                    f"⏳ *ينتهي الاشتراك في:* {expiry_date}\n\n"
                    f"📌 *طريقة التفعيل:* قم بنسخ المفتاح وألصقه داخل الشاشة المغلقة في البرنامج واضغط 'تفعيل'."
                )
                await context.bot.send_message(chat_id=user_id, text=success_msg, parse_mode="Markdown")
                await query.message.edit_caption(caption=f"✅ *تم تأكيد الإيصال وحفظ المفتاح أونلاين:*\n`{key}`\nللمستخدم: {pending['user_name']}", parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Error approving: {e}")
                await query.answer("حدث خطأ أثناء حفظ المفتاح في قاعدة البيانات", show_alert=True)

    elif data.startswith("reject_"):
        receipt_id = data.replace("reject_", "")
        pending = PENDING_RECEIPTS.get(receipt_id)
        if pending:
            user_id = pending["user_id"]
            if receipt_id in PENDING_RECEIPTS:
                del PENDING_RECEIPTS[receipt_id]

            reject_msg = "❌ *عذراً، تعذر تأكيد إيصال التحويل.*\nيرجى التواصل مع الدعم الفني أو إعادة إرسال إيصال صحيح."
            try:
                await context.bot.send_message(chat_id=user_id, text=reject_msg, parse_mode="Markdown")
            except Exception:
                pass

            await query.message.edit_caption(caption=f"❌ *تم رفض الإيصال* للمستخدم: {pending['user_name']}", parse_mode="Markdown")

async def handle_photo_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    pkg_key = context.user_data.get("selected_pkg", "pkg_1m")
    pkg = PACKAGES[pkg_key]

    photo_file = update.message.photo[-1].file_id
    receipt_id = str(uuid.uuid4())[:8]

    PENDING_RECEIPTS[receipt_id] = {
        "user_id": user.id,
        "user_name": f"{user.first_name} (@{user.username or 'NoUsername'})",
        "pkg_key": pkg_key,
        "photo_id": photo_file,
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    admin_caption = (
        f"📥 *إيصال تحويل جديد قيد المراجعة:*\n\n"
        f"👤 *المستخدم:* {user.first_name} (@{user.username or 'بدون'})\n"
        f"🆔 *ID:* `{user.id}`\n"
        f"📦 *الباقة المطلوبة:* {pkg['name']} ({pkg['price']})\n"
        f"🔢 *معرف الإيصال:* `{receipt_id}`"
    )
    keyboard = [
        [
            InlineKeyboardButton("✅ تأكيد وتوليد المفتاح", callback_data=f"approve_{receipt_id}"),
            InlineKeyboardButton("❌ رفض الإيصال", callback_data=f"reject_{receipt_id}")
        ]
    ]

    await context.bot.send_photo(
        chat_id=ADMIN_GROUP_ID,
        photo=photo_file,
        caption=admin_caption,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

    await update.message.reply_text("✅ تم استلام صورة الإيصال بنجاح وجاري مراجعتها من قبل الإدارة. سيتم إرسال مفتاح التفعيل لك فور التأكيد خلال دقائق! 🎉")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_receipt))

    print("🤖 Bot is running on Cloud with Supabase...")
    app.run_polling()

if __name__ == "__main__":
    main()
