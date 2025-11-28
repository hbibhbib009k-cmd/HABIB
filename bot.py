import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
import config

# DB helper
def init_db():
    conn = sqlite3.connect(config.DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS buttons (
        name TEXT PRIMARY KEY,
        content TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT
    )""")
    conn.commit()
    conn.close()

def add_button_db(name, content):
    conn = sqlite3.connect(config.DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO buttons (name, content) VALUES (?,?)", (name,content))
    conn.commit(); conn.close()

def get_buttons_db():
    conn = sqlite3.connect(config.DB_PATH)
    cur = conn.cursor(); cur.execute("SELECT name FROM buttons")
    rows = cur.fetchall(); conn.close()
    return [r[0] for r in rows]

def get_button_content(name):
    conn = sqlite3.connect(config.DB_PATH)
    cur = conn.cursor(); cur.execute("SELECT content FROM buttons WHERE name=?", (name,))
    r = cur.fetchone(); conn.close()
    return r[0] if r else None

# Bot
bot = Bot(token=config.API_TOKEN)
dp = Dispatcher()

@dp.message(Command(commands=['start']))
async def cmd_start(msg: types.Message):
    # register user
    conn = sqlite3.connect(config.DB_PATH)
    cur = conn.cursor(); cur.execute("INSERT OR IGNORE INTO users (id,username) VALUES (?,?)", (msg.from_user.id, msg.from_user.username))
    conn.commit(); conn.close()

    kb = InlineKeyboardBuilder()
    for name in get_buttons_db():
        kb.button(text=name, callback_data=f"btn_{name}")
    kb.adjust(1)
    await msg.answer("اختر من القائمة:", reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data.startswith('btn_'))
async def callback_button(cq: types.CallbackQuery):
    name = cq.data[4:]
    content = get_button_content(name)
    if content is None:
        await cq.message.edit_text("لا يوجد محتوى لهذا الزر.")
    else:
        await cq.message.edit_text(f"🔹 {name}:\n{content}")

# admin commands to add/delete buttons
@dp.message(Command(commands=['addbtn']))
async def cmd_addbtn(msg: types.Message):
    if msg.from_user.id != config.OWNER_ID:
        return await msg.reply('هذا الأمر للمالك فقط.')
    parts = msg.text.split(None,1)
    if len(parts) < 2:
        return await msg.reply('استخدم: /addbtn اسم_الزر')
    name = parts[1].strip()
    await msg.reply('الآن أرسل محتوى الزر:')
    # wait for next message
    def check(m: types.Message):
        return m.from_user.id == config.OWNER_ID and m.reply_to_message is None
    try:
        reply = await dp.wait_for('message', timeout=120, check=check)
        add_button_db(name, reply.text)
        await reply.reply(f'تمت إضافة الزر {name}')
    except asyncio.TimeoutError:
        await msg.reply('انتهى الوقت. أعد المحاولة.')

@dp.message(Command(commands=['delbtn']))
async def cmd_delbtn(msg: types.Message):
    if msg.from_user.id != config.OWNER_ID:
        return await msg.reply('هذا الأمر للمالك فقط.')
    parts = msg.text.split(None,1)
    if len(parts) < 2: return await msg.reply('استخدم: /delbtn اسم_الزر')
    name = parts[1].strip(); conn = sqlite3.connect(config.DB_PATH)
    cur = conn.cursor(); cur.execute('DELETE FROM buttons WHERE name=?',(name,)); conn.commit(); conn.close()
    await msg.reply('تم الحذف إن وُجد')

if __name__ == '__main__':
    init_db()
    Dispatcher.set_current(dp)
    import asyncio
    asyncio.run(dp.start_polling(bot))
