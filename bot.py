import os
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import asyncio

# =========================
# SOZLAMALAR
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 8588301820
REFERRAL_REWARD = 6000
MIN_WITHDRAW = 30000

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

# =========================
# DATABASE
# =========================

db = sqlite3.connect("bot.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    referred_by INTEGER DEFAULT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    payment TEXT,
    status TEXT DEFAULT 'pending'
)
""")

db.commit()


# =========================
# MAJBURIY OBUNA KANALLARI
# =========================

# Keyinchalik admin panel orqali qo'shamiz.
# Hozircha bo'sh.

REQUIRED_CHANNELS = []


# =========================
# FOYDALANUVCHI
# =========================

def add_user(user_id, username):
    cursor.execute(
        "SELECT id FROM users WHERE id = ?",
        (user_id,)
    )

    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users (id, username) VALUES (?, ?)",
            (user_id, username)
        )
        db.commit()


def get_user(user_id):
    cursor.execute(
        "SELECT id, username, balance, referrals, referred_by FROM users WHERE id = ?",
        (user_id,)
    )
    return cursor.fetchone()


# =========================
# OBUNA TEKSHIRISH
# =========================

async def check_subscription(user_id):

    for channel in REQUIRED_CHANNELS:

        try:
            member = await bot.get_chat_member(
                chat_id=channel,
                user_id=user_id
            )

            if member.status in ["left", "kicked"]:
                return False

        except Exception:
            return False

    return True


def subscription_keyboard():

    buttons = []

    for channel in REQUIRED_CHANNELS:
        buttons.append([
            InlineKeyboardButton(
                text="📢 Kanalga obuna bo‘lish",
                url=f"https://t.me/{channel.replace('@', '')}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="✅ Tekshirish",
            callback_data="check_sub"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# =========================
# ASOSIY MENYU
# =========================

def main_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Pul ishlash",
                    callback_data="earn"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Hisobim",
                    callback_data="account"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💸 Pul chiqarish",
                    callback_data="withdraw"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📞 Adminga murojaat",
                    callback_data="admin_contact"
                )
            ]
        ]
    )


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message):

    user_id = message.from_user.id
    username = message.from_user.username or ""

    add_user(user_id, username)

    # Referalni olish
    args = message.text.split()

    if len(args) > 1:

        try:
            referrer_id = int(args[1])

            if referrer_id != user_id:

                user = get_user(user_id)

                # Faqat birinchi marta referal biriktiriladi
                if user and user[4] is None:

                    referrer = get_user(referrer_id)

                    if referrer:

                        cursor.execute(
                            "UPDATE users SET referred_by = ? WHERE id = ?",
                            (referrer_id, user_id)
                        )

                        cursor.execute(
                            """
                            UPDATE users
                            SET balance = balance + ?,
                                referrals = referrals + 1
                            WHERE id = ?
                            """,
                            (REFERRAL_REWARD, referrer_id)
                        )

                        db.commit()

        except ValueError:
            pass

    subscribed = await check_subscription(user_id)

    if not subscribed:

        await message.answer(
            "🔐 <b>Botdan foydalanish uchun barcha kanallarga obuna bo‘ling.</b>\n\n"
            "Obuna bo‘lgach, <b>✅ Tekshirish</b> tugmasini bosing.",
            reply_markup=subscription_keyboard()
        )

        return

    await message.answer(
        "🎉 <b>Botga xush kelibsiz!</b>\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=main_menu()
    )


# =========================
# TEKSHIRISH
# =========================

@dp.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery):

    user_id = callback.from_user.id

    subscribed = await check_subscription(user_id)

    if not subscribed:

        await callback.answer(
            "❌ Hali barcha kanallarga obuna bo‘lmagansiz!",
            show_alert=True
        )

        return

    await callback.message.edit_text(
        "✅ <b>Obuna tasdiqlandi!</b>\n\n"
        "Asosiy menyu:",
        reply_markup=main_menu()
    )

    await callback.answer()


# =========================
# PUL ISHLASH
# =========================

@dp.callback_query(F.data == "earn")
async def earn(callback: CallbackQuery):

    user_id = callback.from_user.id

    bot_username = (await bot.get_me()).username

    referral_link = (
        f"https://t.me/{bot_username}?start={user_id}"
    )

    user = get_user(user_id)

    await callback.message.edit_text(
        "💰 <b>PUL ISHLASH</b>\n\n"
        f"👥 Referallar: <b>{user[3]}</b>\n"
        f"💵 Har bir referal: <b>{REFERRAL_REWARD:,} UZS</b>\n\n"
        "🔗 <b>Sizning referal havolangiz:</b>\n"
        f"<code>{referral_link}</code>\n\n"
        "Havolangizni do‘stlaringizga yuboring.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Orqaga",
                        callback_data="menu"
                    )
                ]
            ]
        )
    )

    await callback.answer()


# =========================
# HISOB
# =========================

@dp.callback_query(F.data == "account")
async def account(callback: CallbackQuery):

    user_id = callback.from_user.id
    user = get_user(user_id)

    await callback.message.edit_text(
        "👤 <b>HISOBIM</b>\n\n"
        f"🆔 ID: <code>{user[0]}</code>\n"
        f"👥 Referallar: <b>{user[3]}</b>\n"
        f"💰 Balans: <b>{user[2]:,} UZS</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Orqaga",
                        callback_data="menu"
                    )
                ]
            ]
        )
    )

    await callback.answer()


# =========================
# PUL CHIQARISH HOLATLARI
# =========================

class WithdrawState(StatesGroup):
    amount = State()
    payment = State()


@dp.callback_query(F.data == "withdraw")
async def withdraw(callback: CallbackQuery, state: FSMContext):

    user = get_user(callback.from_user.id)

    if user[2] < MIN_WITHDRAW:

        await callback.message.edit_text(
            "💸 <b>Pul chiqarish</b>\n\n"
            f"💰 Balansingiz: <b>{user[2]:,} UZS</b>\n"
            f"⚠️ Minimal pul chiqarish: <b>{MIN_WITHDRAW:,} UZS</b>",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ Orqaga",
                            callback_data="menu"
                        )
                    ]
                ]
            )
        )

        await callback.answer()
        return

    await state.set_state(WithdrawState.amount)

    await callback.message.answer(
        "💸 <b>Pul chiqarish</b>\n\n"
        f"Balansingiz: <b>{user[2]:,} UZS</b>\n\n"
        "Qancha pul chiqarmoqchisiz?"
    )

    await callback.answer()


@dp.message(WithdrawState.amount)
async def withdraw_amount(message: Message, state: FSMContext):

    try:
        amount = int(message.text.replace(" ", ""))

    except ValueError:

        await message.answer(
            "❌ Faqat raqam kiriting."
        )

        return

    user = get_user(message.from_user.id)

    if amount < MIN_WITHDRAW:

        await message.answer(
            f"❌ Minimal summa: <b>{MIN_WITHDRAW:,} UZS</b>"
        )

        return

    if amount > user[2]:

        await message.answer(
            "❌ Balansingiz yetarli emas."
        )

        return

    await state.update_data(amount=amount)

    await state.set_state(WithdrawState.payment)

    await message.answer(
        "💳 <b>To‘lov ma’lumotingizni yuboring.</b>\n\n"
        "Masalan: karta raqami yoki siz foydalanadigan to‘lov ma'lumoti."
    )


@dp.message(WithdrawState.payment)
async def withdraw_payment(message: Message, state: FSMContext):

    data = await state.get_data()

    amount = data["amount"]
    payment = message.text

    user_id = message.from_user.id

    cursor.execute(
        """
        INSERT INTO withdrawals (user_id, amount, payment)
        VALUES (?, ?, ?)
        """,
        (user_id, amount, payment)
    )

    db.commit()

    await state.clear()

    await message.answer(
        "✅ <b>So‘rovingiz qabul qilindi!</b>\n\n"
        f"💰 Summa: <b>{amount:,} UZS</b>\n"
        "⏳ Admin tekshiruvini kuting."
    )

    await bot.send_message(
        ADMIN_ID,
        "💸 <b>YANGI PUL CHIQARISH SO‘ROVI</b>\n\n"
        f"👤 ID: <code>{user_id}</code>\n"
        f"💰 Summa: <b>{amount:,} UZS</b>\n"
        f"💳 To‘lov: <code>{payment}</code>"
    )


# =========================
# ADMINGA MUROJAAT
# =========================

@dp.callback_query(F.data == "admin_contact")
async def admin_contact(callback: CallbackQuery):

    await callback.message.edit_text(
        "📞 <b>Adminga murojaat</b>\n\n"
        "Savolingizni yozib yuboring. "
        "Xabaringiz adminga yuboriladi.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Orqaga",
                        callback_data="menu"
                    )
                ]
            ]
        )
    )

    await callback.answer()


# =========================
# ADMIN XABAR QABUL QILISH
# =========================

@dp.message(F.text)
async def messages(message: Message):

    # Adminning oddiy xabarlarini o'tkazib yuborish
    if message.from_user.id == ADMIN_ID:
        return

    # Foydalanuvchi adminga murojaat qilgan bo'lishi mumkin
    await bot.send_message(
        ADMIN_ID,
        "📩 <b>FOYDALANUVCHIDAN XABAR</b>\n\n"
        f"👤 ID: <code>{message.from_user.id}</code>\n"
        f"👤 Username:
