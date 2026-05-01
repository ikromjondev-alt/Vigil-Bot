import discord
from discord import app_commands
from discord.ext import commands
import datetime
import asyncio

  
LOG_CHANNEL_ID = 1488299933143535766  # логи
AUTO_ROLE_ID = "👤 | Member`s "    # Авто выдача ролец

intents = discord.Intents.all() # Ҳамма имкониятларни ёқамиз

class FlareBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        
        self.add_view(ReviewSystem()) 
        await self.tree.sync()



bot = FlareBot() #(Шаблон Flare Bot`a)
tree = bot.tree


# --- 2. ЛОГЛАР ФУНКЦИЯСИ ---
async def send_log(guild, title, description, color=discord.Color.orange()):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.now())
        await channel.send(embed=embed)

# --- 3. MODERATION COMMANDS ---

# БАН (Даже пользватель вышел из сервера)
@tree.command(name="ban", description="Бан пользователя по ID или упоминанию")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, user: discord.User, reason: str = "Не указана"):
    await interaction.guild.ban(user, reason=reason)
    await interaction.response.send_message(f"✅ {user} забанен. Причина: {reason}", ephemeral=True)
    await send_log(interaction.guild, "🔨 Бан", f"Модератор: {interaction.user.mention}\nОбъект: {user.mention}\nПричина: {reason}", discord.Color.red())

# РАЗБАН
@tree.command(name="unban", description="Разбанить пользователя по ID")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: str):
    user = await bot.fetch_user(int(user_id))
    await interaction.guild.unban(user)
    await interaction.response.send_message(f"✅ {user.name} разбанен.", ephemeral=True)
    await send_log(interaction.guild, "🔓 Разбан", f"Админ: {interaction.user.mention}\nID пользователя: {user_id}", discord.Color.green())

# МУТ (Timeout)
@tree.command(name="mute", description="Замутить пользователя (тайм-аут)")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "Не указана"):
    duration = datetime.timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await interaction.response.send_message(f"🤐 {member.mention} замучен на {minutes} мин. Причина: {reason}", ephemeral=True)
    await send_log(interaction.guild, "🔇 Мут", f"Модератор: {interaction.user.mention}\nОбъект: {member.mention}\nВремя: {minutes}м", discord.Color.blue())

# КИК
@tree.command(name="kick", description="Выгнать пользователя с сервера")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Не указана"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 {member.mention} выгнан с сервера.", ephemeral=True)

# САЙ (SAY)
@tree.command(name="say", description="Отправить сообщение от имени бота")
async def say(interaction: discord.Interaction, text: str):
    await interaction.channel.send(text)
    await interaction.response.send_message("Отправлено!", ephemeral=True)

# EMBED 
@tree.command(name="embed", description="Создать Embed сообщение")
async def embed_cmd(interaction: discord.Interaction, title: str, description: str):
    emb = discord.Embed(title=title, description=description, color=discord.Color.random())
    await interaction.channel.send(embed=emb)
    await interaction.response.send_message("Embed создан!", ephemeral=True)

# --- 4. SETUP & MODAL (АНКЕТА) ---

# APPLY

import discord
from discord.ext import commands
from discord import app_commands, ui  # Импорты на месте
import datetime

# --- ВОТ ТУТ ВВОДИ СВОИ АЙДИ (НАСТРОЙКИ) ---
LOG_CHANNEL_ID = 1403101585193701427    # ID канала для логов
APPLY_CHANNEL_ID = 1488299933143535766  # ID канала для заявок
MOD_ROLE_NAME = "👮 Модератор"           # Название роли для выдачи

# Список ролей с доступом (проверь названия 1 в 1)
ALLOWED_ROLES = [
    "♣️ | Deputy Server Owner", "⚜️ | Chief Administrator",
    "🔱 | Deputy chief Administrator", "🪪 | Chief Moderator",
    "🗡️ | Deputy Chief Moderator", "♦️ | Senior Administrator"
]

# --- ОКНО ОТКЛОНЕНИЯ ---
class RejectReasonModal(ui.Modal, title="Причина отклонения"):
    reason = ui.TextInput(label="Укажите причину", style=discord.TextStyle.paragraph, min_length=5, required=True)

    def __init__(self, member: discord.Member):
        super().__init__()
        self.member = member

    async def on_submit(self, interaction: discord.Interaction):
        try:
            embed_user = discord.Embed(title="🚫 Отказ", description=f"Ваша заявка в **{interaction.guild.name}** отклонена.", color=discord.Color.red())
            embed_user.add_field(name="Причина:", value=self.reason.value)
            await self.member.send(embed=embed_user)
        except: pass
        await interaction.response.send_message(f"❌ Отклонено. Причина: {self.reason.value}", ephemeral=False)
        await interaction.message.edit(view=None)
        log_chan = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_chan:
            await log_chan.send(f"🚫 **Лог:** {interaction.user.mention} отклонил {self.member.mention}. Причина: {self.reason.value}")

# ---  СИСТЕМА КНОПОК ---
class ReviewSystem(ui.View):
    def __init__(self, member_id: int = None):
        super().__init__(timeout=None)
        self.member_id = member_id

    def has_access(self, user):
        user_roles = [role.name for role in user.roles]
        return any(name in user_roles for name in ALLOWED_ROLES) or user.guild_permissions.administrator

    @ui.button(label="✅ Принять", style=discord.ButtonStyle.green, custom_id="v_accept_final")
    async def approve(self, interaction: discord.Interaction, button: ui.Button):
        if not self.has_access(interaction.user):
            return await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
        member = interaction.guild.get_member(self.member_id)
        role = discord.utils.get(interaction.guild.roles, name=MOD_ROLE_NAME)
        if member and role:
            await member.add_roles(role)
            await interaction.response.send_message(f"✅ {member.mention} принят!", ephemeral=False)
            await interaction.message.edit(view=None)
            log_chan = interaction.guild.get_channel(LOG_CHANNEL_ID)
            if log_chan: await log_chan.send(f"📥 **Лог:** {interaction.user.mention} принял {member.mention}")
        else:
            await interaction.response.send_message("❌ Ошибка: Юзер или роль не найдены.", ephemeral=True)

    @ui.button(label="❌ Отклонить", style=discord.ButtonStyle.red, custom_id="v_reject_final")
    async def reject(self, interaction: discord.Interaction, button: ui.Button):
        if not self.has_access(interaction.user):
            return await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
        member = interaction.guild.get_member(self.member_id)
        if member: await interaction.response.send_modal(RejectReasonModal(member))
        else: await interaction.response.send_message("❌ Кандидат вышел.", ephemeral=True)




# --- 4. КОМАНДА APPLY ---
@bot.tree.command(name="apply", description="Подать заявку")
async def apply(interaction: discord.Interaction, возраст: int, о_себе: str):
    chan = bot.get_channel(APPLY_CHANNEL_ID)
    if not chan: return await interaction.response.send_message("Ошибка канала!")
    embed = discord.Embed(title="📩 Заявка", color=discord.Color.blue())
    embed.add_field(name="От:", value=interaction.user.mention)
    embed.add_field(name="Возраст:", value=возраст)
    embed.add_field(name="Инфо:", value=о_себе)
    await chan.send(embed=embed, view=ReviewSystem(interaction.user.id))
    await interaction.response.send_message("✅ Отправлено!", ephemeral=True)
# --- ПЕРЕМЕННЫЕ ---
warns = {}
tech_mode = False

# --- CLEAR (Очистка) ---
@bot.tree.command(name="clear", description="Очистить сообщения")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, количество: int):
    if tech_mode and interaction.user.id != bot.owner_id:
        return await interaction.response.send_message("🛠 Бот на тех-работах!", ephemeral=True)
    
    await interaction.channel.purge(limit=количество)
    await interaction.response.send_message(f"✅ Удалено сообщений: {количество}", ephemeral=True)

# --- WARN (Выдать варн) ---
@bot.tree.command(name="warn", description="Выдать предупреждение")
@discord.app_commands.checks.has_permissions(kick_members=True)
async def warn(interaction: discord.Interaction, пользователь: discord.Member, причина: str = "Нарушение"):
    if tech_mode: return await interaction.response.send_message("🛠 Тех-работы", ephemeral=True)
    
    uid = str(пользователь.id)
    warns[uid] = warns.get(uid, 0) + 1
    
    embed = discord.Embed(title="⚠️ Предупреждение", color=discord.Color.red())
    embed.add_field(name="Нарушитель:", value=пользователь.mention)
    embed.add_field(name="Варнов:", value=f"{warns[uid]}/3")
    embed.add_field(name="Причина:", value=причина)
    
    await interaction.response.send_message(embed=embed)
    
    if warns[uid] >= 3:
        await пользователь.kick(reason="3/3 варна")
        warns[uid] = 0
        await interaction.followup.send(f"🚀 {пользователь.display_name} кикнут за  3/3 Warns.")

# --- UNWARN (Снять варн) ---
@bot.tree.command(name="unwarn", description="Снять предупреждение")
@discord.app_commands.checks.has_permissions(kick_members=True)
async def unwarn(interaction: discord.Interaction, пользователь: discord.Member):
    uid = str(пользователь.id)
    if warns.get(uid, 0) > 0:
        warns[uid] -= 1
        await interaction.response.send_message(f"✅ Снята предупреждение с {пользователь.mention}. Осталось: {warns[uid]}")
    else:
        await interaction.response.send_message("У юзера нет варнов.", ephemeral=True)

# --- UNMUTE (Размутить) ---
@bot.tree.command(name="unmute", description="Снять мут с пользователя")
@discord.app_commands.checks.has_permissions(manage_roles=True)
async def unmute(interaction: discord.Interaction, пользователь: discord.Member):
    role = discord.utils.get(interaction.guild.roles, name="Muted")
    if role and role in пользователь.roles:
        await пользователь.remove_roles(role)
        await interaction.response.send_message(f"🔊 {пользователь.mention} размучен.")
    else:
        await interaction.response.send_message("Роль не найдена или юзер не в муте.", ephemeral=True)

# --- TECH (Тех-работы) ---
import discord
from discord import app_commands
from discord.ext import commands

# --- ОСНОВНЫЕ НАСТРОЙКИ ---
OWNER_ID = 1017792690533969891  # Твой ID
MAINTENANCE_MODE = False        # Переменная состояния

# --- КОМАНДА УПРАВЛЕНИЯ ТЕХ-РАБОТАМИ ---
@bot.tree.command(name="tech", description="Переключить режим тех-работ (Только для Овнера)")
@app_commands.describe(status="True - включить работы, False - выключить")
async def tech(interaction: discord.Interaction, status: bool):
    global MAINTENANCE_MODE
    
    # Проверка на права доступа
    if interaction.user.id != 1017792690533969981:
        await interaction.response.send_message("❌ У вас нет прав доступа к этой системе.", ephemeral=True)
        return

    MAINTENANCE_MODE = status
    
    if MAINTENANCE_MODE:
        #EMBED TEXT
        embed_on = discord.Embed(
            title="🛠 Режим тех-работ: ВКЛЮЧЕН",
            description=(
                "**Уважаемые участники!**\n\n"
                "Mod Bot временно уходит на обслуживание.\n"
                "⏳ **Период:** 01.04.2026 — 03.04.2026\n"
                "⚙️ **Причина:** Технические работы на стороне хостинга.\n\n"
                "Я обязательно уведомлю всех о включении. Спасибо за терпение! 🙌"
            ),
            color=0xFFA500
        )
        await interaction.response.send_message(content="@everyone", embed=embed_on)
    else:
        # Сообщение о включении
        embed_off = discord.Embed(
            title="✅ Бот снова в строю!",
            description="Технические работы успешно завершены. Все функции Mod Bot доступны в обычном режиме.",
            color=0x00FF00 
        )
        await interaction.response.send_message(embed=embed_off)

# --- ГЛОБАЛЬНЫЙ ФИЛЬТР КОМАНД  ---
@bot.before_invoke
async def before_any_command(ctx):

    if MAINTENANCE_MODE and ctx.author.id != OWNER_ID:
        # Отправляем сообщение и прерываем выполнение команды
        await ctx.send(
            f"🛠 **{ctx.author.name}**, извини, но сейчас идут тех-работы. Бот временно недоступен.", 
            delete_after=7
        )
        raise commands.CheckFailure("Maintenance mode active")

# --- ОБРАБОТЧИК ОШИБОК  ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        return # Просто игнорируем ошибку блокировки доступа
    raise error


# --- DM (Личка одному пользователю) ---
@bot.tree.command(name="dm", description="Отправить личное сообщение пользователю")
@discord.app_commands.checks.has_permissions(administrator=True)
async def dm(interaction: discord.Interaction, пользователь: discord.Member, сообщение: str):
    if tech_mode and interaction.user.id != bot.owner_id:
        return await interaction.response.send_message("🛠 Тех-работы", ephemeral=True)
    
    try:
        # Добавляем interaction.user в текст
        await пользователь.send(
            f"📬 **Новое сообщение!**\n"
            f"**От администратора:** {interaction.user.display_name}\n\n"
            f"**Текст:** {сообщение}"
        )
        await interaction.response.send_message(f"✅ Отправлено {пользователь.mention}", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ Личка закрыта у {пользователь.mention}", ephemeral=True)

# --- DMALL (Рассылка всем) ---
@bot.tree.command(name="dmall", description="Рассылка всем участникам")
@discord.app_commands.checks.has_permissions(administrator=True)
async def dmall(interaction: discord.Interaction, сообщение: str):
 
    if interaction.user.id != 123456789012345678: # OWNER ID
        return await interaction.response.send_message("❌ Только владелец может делать рассылку!", ephemeral=True)

    await interaction.response.send_message("🚀 Рассылка пошла...", ephemeral=True)
    
    success = 0
    for member in interaction.guild.members:
        if member.bot: continue
        try:
            await member.send(
                f"📢 **Объявление сервера {interaction.guild.name}**\n"
                f"**От:** {interaction.user.mention}\n" # Упоминание или display_name
                f"-----------------------------------\n"
                f"{сообщение}"
            )
            success += 1
        except:
            continue
            
    await interaction.followup.send(f"📊 Готово! Получили: {success} чел.", ephemeral=True)
# STAFF
@bot.tree.command(name="staff", description="Показать весь состав администрации")
async def staff(interaction: discord.Interaction):

    roles_to_check = [
        "👑 | Server owner",
        "♣️ | Deputy Server Owner",
        "⚜️ | Chief Administrator",
        "🔱 | Deputy chief Administrator",
        "🪪 | Chief Moderator",
        "🗡️ | Deputy Chief Moderator",
        "🆘 | Technical Administrator",
        "♦️ | Senior Administrator",
        "👮 Модератор"
    ]
    
    embed = discord.Embed(
        title=f"🏛️ Состав администрации {interaction.guild.name}",
        color=discord.Color.from_rgb(43, 45, 49), 
        description="Ниже представлен список действующих лиц сервера:"
    )
    
    any_found = False
    
    for r_name in roles_to_check:
        role = discord.utils.get(interaction.guild.roles, name=r_name)
        if role:

            members = [m.mention for m in role.members if not m.bot]
            if members:
                embed.add_field(
                    name=f"✨ {r_name}", 
                    value="> " + "\n> ".join(members), 
                    inline=False
                )
                any_found = True
                
    if not any_found:
        return await interaction.response.send_message("❌ На сервере пока не назначены роли из списка администрации.", ephemeral=True)

    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_footer(text=f"ModBot • Система управления персоналом", icon_url=bot.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

# New commands
@bot.tree.command(name="donate", description="Показать реквизиты для поддержки проекта")
async def donate(interaction: discord.Interaction):
    embed = discord.Embed(
        title="💎 Поддержка проекта",
        description=(
            "Если вы хотите помочь нашему серверу развиваться и оплачивать хостинг, "
            "вы можете сделать добровольное пожертвование.\n\n"
            "**📍 Наши реквизиты:**\n"
            "🔸 `UZCARD` — **5614 6821 1076 2236**\n"
            "🔹 `Visa Card` — **4023 0605 1354 0384**\n\n"
            "⚠️ **После оплаты:** Обязательно скиньте чек в ЛС владельцу: @ikromdjon.\n"
            "Благодарим за поддержку! ❤️"
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Запросил: {interaction.user.display_name}")
    

    await interaction.response.send_message(embed=embed, ephemeral=False)

# NEW COMMANDS
import random

@bot.tree.command(name="8ball", description="Спроси у магического шара совета")
async def ball(interaction: discord.Interaction, вопрос: str):
    # Список классических и авторских ответов
    responses = [
        "Бесспорно! ✅",
        "Предрешено. ✨",
        "Никаких сомнений. 😎",
        "Можешь быть уверен в этом. 👍",
        "Мне кажется — да. 🌊",
        "Вероятнее всего. 📈",
        "Знаки говорят — «да». 🔮",
        "Пока не ясно, попробуй снова. 🔄",
        "Спроси позже, я сейчас на вайбе. 💤",
        "Лучше не рассказывать тебе об этом сейчас... 🤐",
        "Даже не думай. ❌",
        "Мой ответ — «нет». 🛑",
        "По моим данным — нет. 📉",
        "Перспективы не очень... ☁️",
        "Весьма сомнительно. 🤔"
    ]
    
    answer = random.choice(responses)
    
    embed = discord.Embed(
        title="🎱 Магический Шар предсказывает...",
        description=f"**Ваш вопрос:** {вопрос}\n**Мой ответ:** {answer}",
        color=0x2f3136 # Цвет в стиле «Ауры»
    )
    
    # Добавим маленькую иконку шара для стиля
    embed.set_thumbnail(url="https://i.imgur.com/vHdfD9I.png") # Ссылка на иконку шара 8
    embed.set_footer(text=f"спросил: {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed)

# NEW COMMAND OWNER
@bot.tree.command(name="owner", description="История, провалы и триумф создателя Mod Bot")
async def owner(interaction: discord.Interaction):
    owner_id = 1017792690533969981 
    owner_user = await bot.fetch_user(owner_id)
    
    embed = discord.Embed(
        title="📂 SYSTEM ARCHIVE: THE ARCHITECT'S JOURNEY",
        description=(
            "За каждой строчкой чистого кода стоят сотни ошибок и исправлений. "
            "Это честная история создания **Mod Bot**."
        ),
        color=0x2b2d31
    )

    # Личный профиль
    embed.add_field(
        name="👤 ЛИЧНОСТЬ",
        value=f"**Developer:** {owner_user.mention}\n**Локация:** Ташкент 🇺🇿\n**Статус:** 17 years old / Visionary",
        inline=True
    )
    
    # Хронология (Timeline)
    embed.add_field(
        name="⏳ ТАЙМЛАЙН",
        value=(
            "• **Октябрь 2023:** Старт обучения. Первые ошибки в синтаксисе.\n"
            "• **Конец 2023:** Первый запуск сайта на **VS Code**.\n"
            "• **2024-2025:** Переход на мобильную разработку Python.\n"
            "• **2026:** Официальный релиз масштабного проекта **Mod Bot**."
        ),
        inline=False
    )

    # ПРОВАЛЫ 
    embed.add_field(
        name="📉 ПУТЬ ЧЕРЕЗ ПРОВАЛЫ",
        value=(
            "Мой путь не был идеальным. Были моменты, когда из-за одной ошибки "
            "**стирались целые модули кода**, а Pydroid вылетал в самый важный момент. "
            "Я сталкивался с критическими багами, которые не мог решить днями, и "
            "непониманием со стороны, зачем кодить на телефоне. Но каждый провал "
            "становился уроком, а каждая ошибка — ступенькой к стабильному **Mod Bot**."
        ),
        inline=False
    )

    # Технологический подвиг
    embed.add_field(
        name="⚙️ ТЕХНИЧЕСКИЙ ФАКТ",
        value=(
            "Весь этот огромный проект был **полностью написан на экране смартфона**. "
            "Без клавиатуры, без монитора, в любых условиях — от школьной парты до ночного Ташкента. "
            "Я доказал, что отсутствие условий — это лишь оправдание для тех, кто не хочет действовать."
        ),
        inline=False
    )

    # Будущее
    embed.add_field(
        name="🚀 ВЗГЛЯД В БУДУЩЕЕ",
        value=(
            "Mod Bot — это только начало. В планах создание глобальных IT-экосистем и "
            "проектов нового поколения. Мой путь начался в 2023-м, и я не остановлюсь, "
            "пока мои идеи не изменят индустрию в Узбекистане и за его пределами."
        ),
        inline=False
    )

    # Финальный манифест
    embed.description = (
        "*«В октябре 2023-го я был просто парнем с VS Code. Сегодня я — разработчик "
        "систем на мобильном устройстве. Провалы научили меня большему, чем успех. "
        "Помни: важен не девайс в руках, а огонь в сердце».*"
    )

    if owner_user.avatar:
        embed.set_thumbnail(url=owner_user.avatar.url)
    
    embed.set_footer(
        text="Mod Bot | Built on Mistakes & Triumphs | Tashkent 🇺🇿", 
        icon_url=bot.user.avatar.url
    )

    # Кнопки
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Написать (ЛС)", url=f"https://discord.com/users/{owner_id}", style=discord.ButtonStyle.link))
    view.add_item(discord.ui.Button(label="Поддержать путь", custom_id="sup_dev", style=discord.ButtonStyle.success))
    
    await interaction.response.send_message(embed=embed, view=view)



# --- 5. ЗАПУСК ---
@bot.event
async def on_ready():
    print(f"Бот Ахмедова работает <3 {bot.user}")
    await bot.change_presence(activity=discord.Game(name="Bot owner Akhmedov. Python by Akhmedov"))