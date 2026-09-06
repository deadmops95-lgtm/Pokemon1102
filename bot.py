import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# НАСТРОЙКИ
TOKEN = "ЗДЕСЬ_ВАШ_ТОКЕН_ОТ_BOTFATHER"
ADMIN_USERNAME = "Prokudin95"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("pokemon_bot.db")
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        coins INTEGER DEFAULT 100,
        pokeballs INTEGER DEFAULT 5,
        potions INTEGER DEFAULT 2
    )
    """)
    
    # Таблица покемонов игрока
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_pokemons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        pokemon_name TEXT,
        pokemon_id INTEGER,
        level INTEGER DEFAULT 1,
        hp INTEGER DEFAULT 100,
        gif_url TEXT
    )
    """)
    
    # Таблица стадионов (Gyms)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS gyms (
        gym_id INTEGER PRIMARY KEY,
        gym_name TEXT,
        holder_id INTEGER,
        holder_name TEXT,
        pokemon_name TEXT
    )
    """)
    
    # Инициализируем 3 базовых стадиона, если их нет
    cursor.execute("SELECT COUNT(*) FROM gyms")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO gyms VALUES (1, 'Стадион Канто (Огонь)', NULL, 'Вакантно', '-')")
        cursor.execute("INSERT INTO gyms VALUES (2, 'Стадион Джото (Вода)', NULL, 'Вакантно', '-')")
        cursor.execute("INSERT INTO gyms VALUES (3, 'Стадион Хоэнн (Трава)', NULL, 'Вакантно', '-')")
        
    conn.commit()
    conn.close()

init_db()

# --- ПРОВЕРКА НА АДМИНА ---
def is_admin(user_username: str) -> bool:
    if not user_username:
        return False
    return user_username.lower() == ADMIN_USERNAME.lower()

# --- ГЛАВНОЕ МЕНЮ ---
def main_menu_keyboard():
    kb = [
        [types.KeyboardButton(text="🗺 Исследовать карту"), types.KeyboardButton(text="🎒 Мой инвентарь")],
        [types.KeyboardButton(text="⚔️ Стадионы (Арена)"), types.KeyboardButton(text="👥 Мои покемоны")],
        [types.KeyboardButton(text="🏪 Магазин"), types.KeyboardButton(text="🏆 Рейтинг")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    conn = sqlite3.connect("pokemon_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
    conn.close()
    
    await message.answer(
        f"Привет, {message.from_user.first_name}! Добро пожаловать в мир Покемонов!\n"
        "Исследуй карту, лови анимированных покемонов, захватывай стадионы и стань лучшим тренером!",
        reply_markup=main_menu_keyboard()
    )

# --- АДМИНСКИЕ КОМАНДЫ ---
@dp.message(Command("add_money"))
async def cmd_add_money(message: types.Message):
    if not is_admin(message.from_user.username):
        return await message.answer("У вас нет прав администратора.")
    
    args = message.text.split()
    if len(args) < 3:
        return await message.answer("Использование: /add_money [ID_юзера] [сумма]")
    
    target_id, amount = int(args[1]), int(args[2])
    conn = sqlite3.connect("pokemon_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, target_id))
    conn.commit()
    conn.close()
    await message.answer(f"Успешно! Пользователю {target_id} добавлено {amount} монет.")

@dp.message(Command("give_all"))
async def cmd_give_all(message: types.Message):
    if not is_admin(message.from_user.username):
        return await message.answer("У вас нет прав администратора.")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Использование: /give_all [текст награды]")
    
    reward_text = args[1]
    conn = sqlite3.connect("pokemon_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET coins = coins + 500") # Например, даем всем 500 монет
    conn.commit()
    conn.close()
    await message.answer(f"📦 Рассылка для всех игроков выполнена! Награда: {reward_text}")

# --- СИСТЕМА СТАДИОНОВ ---
@dp.message(F.text == "⚔️ Стадионы (Арена)")
async def show_gyms(message: types.Message):
    conn = sqlite3.connect("pokemon_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT gym_id, gym_name, holder_name, pokemon_name FROM gyms")
    gyms = cursor.fetchall()
    conn.close()
    
    text = "🏟 **Список стадионов мира Покемонов:**\n\n"
    for gym_id, gym_name, holder_name, pokemon_name in gyms:
        text += f"🔹 **{gym_name}**\n👑 Лидер: {holder_name}\n🐾 Покемон защитник: {pokemon_name}\n\n"
    
    kb = [
        [types.InlineKeyboardButton(text="Бросить вызов Стадиону 1", callback_data="gym_1")],
        [types.InlineKeyboardButton(text="Бросить вызов Стадиону 2", callback_data="gym_2")],
        [types.InlineKeyboardButton(text="Бросить вызов Стадиону 3", callback_data="gym_3")]
    ]
    await message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("gym_"))
async def process_gym_battle(callback: types.CallbackQuery):
    gym_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name
    
    conn = sqlite3.connect("pokemon_bot.db")
    cursor = conn.cursor()
    
    # Проверяем, есть ли у игрока покемоны
    cursor.execute("SELECT id, pokemon_name FROM user_pokemons WHERE user_id = ?", (user_id,))
    my_pokemons = cursor.fetchall()
    
    if not my_pokemons:
        conn.close()
        return await callback.answer("У вас нет покемонов для битвы за стадион! Сначала поймайте их на карте.", show_alert=True)
    
    # Упрощенная логика захвата: победа рандомная или берем первого покемона
    fighter = my_pokemons[0][1]
    
    cursor.execute("UPDATE gyms SET holder_id = ?, holder_name = ?, pokemon_name = ? WHERE gym_id = ?", 
                   (user_id, username, fighter, gym_id))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(f"🎉 Поздравляем! Ваш покемон **{fighter}** победил защитника и захватил стадион! Теперь вы новый Лидер!")
    await callback.answer()

# Запуск бота
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
