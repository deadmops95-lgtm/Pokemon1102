import asyncio
import os
import random
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ТОКЕН ВПИСАН НАПРЯМУЮ ИЛИ БЕРЕТСЯ ИЗ ПЕРЕМЕННЫХ
TOKEN = "8542022207:AAHc-j-B51pRwZSJHblIs33OTGD0eUvzYo0"
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

# --- АДМИНСКИЕ КОМАНДЫ ДЛЯ @Prokudin95 ---
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
    cursor.execute("UPDATE users SET coins = coins + 200, pokeballs = pokeballs + 3")
    conn.commit()
    conn.close()
    await message.answer(f"📦 Рассылка для всех игроков выполнена!\nНаграда: {reward_text}")

# --- ПОИСК ПОКЕМОНОВ НА КАРТЕ (С 1 ПО 5 ПОКОЛЕНИЕ) ---
# База популярных покемонов с 1 по 5 поколения (ID, Имя, Ссылка на анимацию/гифку)
POKEMON_DATABASE = [
    # 1 поколение
    (1, "Bulbasaur", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/1.gif"),
    (4, "Charmander", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/4.gif"),
    (7, "Squirtle", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/7.gif"),
    (25, "Pikachu", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/25.gif"),
    (150, "Mewtwo", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/150.gif"),
    # 2 поколение
    (152, "Chikorita", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/152.gif"),
    (155, "Cyndaquil", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/155.gif"),
    (158, "Totodile", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/158.gif"),
    # 3 поколение
    (252, "Treecko", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/252.gif"),
    (255, "Torchic", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/255.gif"),
    (258, "Mudkip", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/258.gif"),
    # 4 поколение
    (387, "Turtwig", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/387.gif"),
    (390, "Chimchar", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/390.gif"),
    (393, "Piplup", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/393.gif"),
    # 5 поколение
    (495, "Snivy", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/495.gif"),
    (498, "Tepig", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/498.gif"),
    (501, "Oshawott", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/501.gif"),
]

@dp.message(F.text == "🗺 Исследовать карту")
async def explore_map(message: types.Message):
    user_id = message.from_user.id
    
    # Шанс встретить покемона или найти монеты
    event = random.choice(["pokemon", "pokemon", "coins", "empty"])
    
    if event == "coins":
        conn = sqlite3.connect("pokemon_bot.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET coins = coins + 30 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return await message.answer("🗺 Вы исследовали тропинку и нашли тайник с **30 монетами**! 🪙")
    
    if event == "empty":
        return await message.answer("🗺 Вы долго бродили по высокой траве, но никого не встретили. Попробуйте еще раз!")

    # Встреча с покемоном
    poke_id, poke_name, poke_gif = random.choice(POKEMON_DATABASE)
    
    kb = [[types.InlineKeyboardButton(text="🎯 Бросить покебол", callback_data=f"catch_{poke_id}_{poke_name}")]]
    
    await message.answer_animation(
        animation=poke_gif,
        caption=f"⚡️ Дикий **{poke_name}** преградил вам путь!\nУ вас есть покебол, попробуйте его поймать!",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
    )

@dp.callback_query(F.data.startswith("catch_"))
async def catch_pokemon(callback: types.CallbackQuery):
    data = callback.data.split("_")
    poke_id = int(data[1])
    poke_name = data[2]
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("pokemon_bot.db")
    cursor = conn.cursor()
    
    # Проверяем наличие покеболов
    cursor.execute("SELECT pokeballs FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if not res or res[0] <= 0:
        conn.close()
        return await callback.answer("❌ У вас закончились покеболы! Купите их в магазине.", show_alert=True)
    
    # Списываем покебол
    cursor.execute("UPDATE users SET pokeballs = pokeballs - 1 WHERE user_id = ?", (user_id,))
    
    # Шанс поимки 70%
    success = random.random() < 0.7
    
    if success:
        # Находим гифку для сохранения
        poke_gif = next((p[2] for p in POKEMON_DATABASE if p[0] == poke_id), "")
        cursor.execute("INSERT INTO user_pokemons (user_id, pokemon_name, pokemon_id, gif_url) VALUES (?, ?, ?, ?)",
                       (user_id, poke_name, poke_id, poke_gif))
        conn.commit()
        conn.close()
        await callback.message.edit_caption(caption=f"🎉 Успех! Вы поймали **{poke_name}** в свою коллекцию!")
    else:
        conn.commit()
        conn.close()
        await callback.message.edit_caption(caption=f"💨 О нет! **{poke_name}** вырвался из покебола и убежал...")
    
    await callback.answer()

# --- ПРОСМОТР ПОКЕМОНОВ ИГРОКА ---
@dp.message(F.text == "👥 Мои покемоны")
async def show_my_pokemons(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("pokemon_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT pokemon_name, level, hp FROM user_pokemons WHERE user_id = ?", (user_id,))
    pokemons = cursor.fetchall()
    conn.close()
    
    if not pokemons:
        return await message.answer("У вас пока нет покемонов. Отправляйтесь на карту исследовать мир!")
    
    text = "🎒 **Ваши покемоны:**\n\n"
    for idx, (p_name, p_lvl, p_hp) in enumerate(pokemons, 1):
        text += f"{idx}. **{p_name}** (Уровень: {p_lvl} | HP: {p_hp})\n"
    
    await message.answer(text, parse_mode="Markdown")

# --- ИНВЕНТАРЬ И МАГАЗИН ---
@dp.message(F.text == "🎒 Мой инвентарь")
async def show_inventory(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("pokemon_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT coins, pokeballs, potions FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return await message.answer("Сначала введите /start")
    
    coins, pokeballs, potions = user
    await message.answer(
        f"🎒 **Ваш инвентарь:**\n\n"
        f"🪙 Монеты: {coins}\n"
        f"🔴 Покеболы: {pokeballs}\n"
        f"🧪 Зелья лечения: {potions}"
    )

@dp.message(F.text == "🏪 Магазин")
async def show_shop(message: types.Message):
    kb = [
        [types.InlineKeyboardButton(text="Купить 5 покеболов (50 монет)", callback_data="buy_pokeballs")],
        [types.InlineKeyboardButton(text="Купить 2 зелья (30 монет)", callback_data="buy_potions")]
    ]
    await message.answer("🏪 **Магазин предметов:**\nВыберите товар для покупки:", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    action = callback.data
    
    conn = sqlite3.connect("pokemon_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    coins = cursor.fetchone()[0]
    
    if action == "buy_pokeballs":
        if coins < 50:
            conn.close()
            return await callback.answer("❌ Не хватает монет!", show_alert=True)
        cursor.execute("UPDATE users SET coins = coins - 50, pokeballs = pokeballs + 5 WHERE user_id = ?", (user_id,))
        msg = "Вы успешно купили 5 покеболов!"
    elif action == "buy_potions":
        if coins < 30:
            conn.close()
            return await callback.answer("❌ Не хватает монет!", show_alert=True)
        cursor.execute("UPDATE users SET coins = coins - 30, potions = potions + 2 WHERE user_id = ?", (user_id,))
        msg = "Вы успешно купили 2 зелья!"
        
    conn.commit()
    conn.close()
    await callback.answer(msg, show_alert=True)
    await callback.message.edit_text(msg)

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
        text += f"🔹 **{gym_name}**\n👑 Лидер: {holder_name}\n🐾 Защитник: {pokemon_name}\n\n"
    
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
    
    cursor.execute("SELECT id, pokemon_name FROM user_pokemons WHERE user_id = ?", (user_id,))
    my_pokemons = cursor.fetchall()
    
    if not my_pokemons:
        conn.close()
        return await callback.answer("У вас нет покемонов для битвы! Сначала поймайте их на карте.", show_alert=True)
    
    fighter = my_pokemons[0][1]
    
    cursor.execute("UPDATE gyms SET holder_id = ?, holder_name = ?, pokemon_name = ? WHERE gym_id = ?", 
                   (user_id, username, fighter, gym_id))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(f"🎉 Поздравляем! Ваш покемон **{fighter}** победил и захватил стадион! Теперь вы новый Лидер!")
    await callback.answer()

# --- РЕЙТИНГ ---
@dp.message(F.text == "🏆 Рейтинг")
async def show_rating(message: types.Message):
    conn = sqlite3.connect("pokemon_bot.db")
    cursor = conn.cursor()
    # Считаем количество покемонов у каждого игрока
    cursor.execute("""
        SELECT u.username, COUNT(p.id) as count 
        FROM users u 
        LEFT JOIN user_pokemons p ON u.user_id = p.user_id 
        GROUP BY u.user_id 
        ORDER BY count DESC 
        LIMIT 5
    """)
    top_users = cursor.fetchall()
    conn.close()
    
    text = "🏆 **Топ-5 тренеров по покемонам:**\n\n"
    for idx, (uname, count) in enumerate(top_users, 1):
        name = uname if uname else "Тренер без никнейма"
        text += f"{idx}. @{name} — {count} покемонов\n"
        
    await message.answer(text, parse_mode="Markdown")

# Запуск бота
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
