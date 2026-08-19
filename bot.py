import asyncio
import logging
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# === SOZLAMALAR ===
BOT_TOKEN = "TOKENINGizni_SHU_YERGA_YOZING"  # BotFather'dan token
ADMIN_ID = 123456789  # O'z Telegram ID raqamingiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Vaqtinchalik ma'lumotlar bazasi
users_db = {}     # {user_id: {"balance": 0.0}}
channels_db = []  # Majburiy kanallar ro'yxati

class AdminStates(StatesGroup):
    waiting_for_channel = State()

# === MAJBURIY OBUNANI TEKSHIRISH ===
async def check_subscriptions(user_id: int) -> bool:
    for channel in channels_db:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in users_db:
        users_db[user_id] = {"balance": 0.0}

    is_subscribed = await check_subscriptions(user_id)
    
    if not is_subscribed:
        keyboard_buttons = []
        for ch in channels_db:
            keyboard_buttons.append([InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{ch.replace('@', '')}")])
        
        keyboard_buttons.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")])
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await message.answer(
            "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling va "
            "<b>'✅ Obunani tekshirish'</b> tugmasini bosing:",
            reply_markup=markup,
            parse_mode="HTML"
        )
        return

    await show_main_menu(message)

async def show_main_menu(message: types.Message):
    user_id = message.from_user.id
    balance = users_db.get(user_id, {}).get("balance", 0.0)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Pul ishlash", callback_data="earn_money"),
         InlineKeyboardButton(text="📤 Pul chiqarish", callback_data="withdraw_money")],
        [InlineKeyboardButton(text="👤 Kabinet / ID", callback_data="cabinet"),
         InlineKeyboardButton(text="👨‍💻 Adminga murojaat", callback_data="contact_admin")]
    ])
    
    if user_id == ADMIN_ID:
        markup.inline_keyboard.append([InlineKeyboardButton(text="⚙️ Admin Panel (Kanal qo'shish)", callback_data="admin_panel")])

    text = (
        f"<b>Xush kelibsiz!</b>\n\n"
        f"Sizning ID raqamingiz: <code>{user_id}</code>\n"
        f"Balansingiz: <b>{balance} so'm</b>"
    )
    
    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=markup, parse_mode="HTML")

# === CALLBACK TUGMALAR ===
@dp.callback_query(F.data == "check_sub")
async def process_check_sub(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not await check_subscriptions(user_id):
        await callback.answer("❌ Siz hali hamma kanalga obuna bo'lmadingiz!", show_alert=True)
        return
    
    await callback.answer("✅ Rahmat, obuna tasdiqlandi!")
    await show_main_menu(callback.message)

@dp.callback_query(F.data == "cabinet")
async def process_cabinet(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    balance = users_db.get(user_id, {}).get("balance", 0.0)
    text = (
        f"👤 <b>Shaxsiy kabinet</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"💰 Balans: <b>{balance} so'm</b>"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]])
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@dp.callback_query(F.data == "earn_money")
async def process_earn(callback: types.CallbackQuery):
    text = "💰 <b>Pul ishlash bo'limi</b>\n\nTez orada bu yerda pullik vazifalar chiqadi!"
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]])
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@dp.callback_query(F.data == "withdraw_money")
async def process_withdraw(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    balance = users_db.get(user_id, {}).get("balance", 0.0)
    text = (
        f"📤 <b>Pul chiqarish bo'limi</b>\n\n"
        f"Sizning balansingiz: <b>{balance} so'm</b>\n"
        f"Pul chiqarish uchun minimal summa: 10,000 so'm.\n\n"
        f"<i>Pul chiqarish bo'yicha murojaat uchun adminga yozing.</i>"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]])
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@dp.callback_query(F.data == "contact_admin")
async def process_contact(callback: types.CallbackQuery):
    text = "👨‍💻 <b>Adminga murojaat qilish:</b>\n\nSavollaringiz bo'lsa @AdminUsername ga yozing."
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]])
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@dp.callback_query(F.data == "back_to_menu")
async def process_back(callback: types.CallbackQuery):
    await show_main_menu(callback.message)

# === ADMIN PANEL (KANAL QO'SHISH) ===
@dp.callback_query(F.data == "admin_panel")
async def process_admin(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    channels_list = "\n".join(channels_db) if channels_db else "Hozircha kanallar yo'q."
    text = (
        f"⚙️ <b>Admin Panel (Kanal egasi menyusi)</b>\n\n"
        f"Majburiy kanallar:\n{channels_list}\n\n"
        f"Jami foydalanuvchilar: {len(users_db)} ta"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton(text="🗑 Kanallarni tozalash", callback_data="clear_channels")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@dp.callback_query(F.data == "add_channel")
async def process_add_channel(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.answer("Kanal username'sini yuboring (masalan: <code>@kanal_nomi</code>):", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_channel)
    await callback.answer()

@dp.message(AdminStates.waiting_for_channel)
async def save_channel(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    channel = message.text.strip()
    if not channel.startswith("@"):
        await message.answer("❌ Xato! '@' bilan boshlanishi kerak. Qaytadan yuboring:")
        return
    
    channels_db.append(channel)
    await state.clear()
    await message.answer(f"✅ Kanal qo'shildi: {channel}\nBosh menyuga qaytish uchun /start ni bosing.")

@dp.callback_query(F.data == "clear_channels")
async def process_clear(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    channels_db.clear()
    await callback.answer("Barcha kanallar o'chirildi!", show_alert=True)
    await process_admin(callback)

# === BOTNI UYG'OQ SAQLASH (KEEP-ALIVE SERVER) ===
async def handle(request):
    return web.Response(text="Bot is running!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

# === ASOSIY ISHGA TUSHIRISH ===
async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Web serverni va botni birgalikda ishga tushiramiz (Uyg'oq saqlash uchun)
    asyncio.create_task(web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
