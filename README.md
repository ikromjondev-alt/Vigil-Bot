# Vigil-Bot
import discord
from discord.ext import commands, tasks
import datetime
import sqlite3
import asyncio
from typing import Optional
TOKEN = 
# ========== БАЗА ДАННЫХ ==========
class SimpleDB:
    def __init__(self):
        self.conn = sqlite3.connect('bot_data.db')
        self.c = self.conn.cursor()
        self.init_db()
    
    def init_db(self):
        self.c.execute('''CREATE TABLE IF NOT EXISTS mutes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER, user_id INTEGER, mod_id INTEGER,
            reason TEXT, end_time TEXT, active INTEGER DEFAULT 1
        )''')
        
        self.c.execute('''CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER, user_id INTEGER, mod_id INTEGER,
            reason TEXT, date TEXT
        )''')
        
        self.c.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER, action TEXT, user_id INTEGER,
            mod_id INTEGER, reason TEXT, time TEXT
        )''')
        
        self.conn.commit()
        print("✅ База данных создана")
    
    def add_mute(self, guild_id, user_id, mod_id, reason, end_time):
        self.c.execute('INSERT INTO mutes VALUES (NULL,?,?,?,?,?,1)',
                      (guild_id, user_id, mod_id, reason, str(end_time)))
        self.conn.commit()
    
    def add_warning(self, guild_id, user_id, mod_id, reason):
        self.c.execute('INSERT INTO warnings VALUES (NULL,?,?,?,?,?)',
                      (guild_id, user_id, mod_id, reason, str(datetime.datetime.now())))
        self.conn.commit()
    
    def add_log(self, guild_id, action, user_id, mod_id, reason):
        self.c.execute('INSERT INTO logs VALUES (NULL,?,?,?,?,?,?)',
                      (guild_id, action, user_id, mod_id, reason, str(datetime.datetime.now())))
        self.conn.commit()
    
    def close(self):
        self.conn.close()

db = SimpleDB()
# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ========== ОСНОВНЫЕ КОМАНДЫ ==========
@bot.tree.command(name="ping", description="Проверить работу бота")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Понг! {round(bot.latency*1000)}мс")

@bot.tree.command(name="help", description="Показать все команды")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 ПОМОЩЬ", color=0x3498db)
    embed.add_field(name="👮 МОДЕРАЦИЯ", value="`/mute @user 1h причина` - Мут\n`/unmute @user` - Снять мут\n`/warn @user причина` - Варн\n`/kick @user причина` - Кик\n`/ban @user причина` - Бан\n`/unban ID` - Разбан", inline=False)
    embed.add_field(name="💬 СООБЩЕНИЯ", value="`/say текст` - Отправить от бота\n`/dm текст` - Всем в ЛС\n`/dmuser @user текст` - Конкретному", inline=False)
    embed.add_field(name="⚠️ ДРУГОЕ", value="`/report @user причина` - Пожаловаться\n`/mod @user` - Назначить модератора\n`/logs` - Посмотреть логи", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)
    # ========== МОДЕРАЦИЯ ==========
@bot.tree.command(name="mute", description="Выдать мут пользователю")
async def mute_cmd(interaction: discord.Interaction, user: discord.Member, duration: str, reason: Optional[str] = "Не указана"):
    try:
        # Конвертируем время
        units = {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800}
        unit = duration[-1].lower()
        if unit not in units:
            await interaction.response.send_message("❌ Используйте: 1m, 1h, 1d, 1w", ephemeral=True)
            return
        
        value = int(duration[:-1])
        seconds = value * units[unit]
        end_time = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        
        # Выдаем мут
        await user.timeout(end_time, reason=reason)
        
        # Сохраняем
        db.add_mute(interaction.guild.id, user.id, interaction.user.id, reason, end_time)
        db.add_log(interaction.guild.id, "MUTE", user.id, interaction.user.id, reason)
        
        # Отправляем ответ
        embed = discord.Embed(title="🔇 МУТ ВЫДАН", color=0xf39c12)
        embed.add_field(name="👤 Пользователь", value=user.mention)
        embed.add_field(name="⏰ Длительность", value=duration)
        embed.add_field(name="📝 Причина", value=reason)
        embed.add_field(name="👮 Модератор", value=interaction.user.mention)
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="unmute", description="Снять мут")
async def unmute_cmd(interaction: discord.Interaction, user: discord.Member):
    try:
        await user.timeout(None, reason="Снятие мута")
        db.add_log(interaction.guild.id, "UNMUTE", user.id, interaction.user.id, "Снятие")
        await interaction.response.send_message(f"🔓 Мут снят с {user.mention}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)
@bot.tree.command(name="warn", description="Выдать предупреждение")
async def warn_cmd(interaction: discord.Interaction, user: discord.Member, reason: str):
    db.add_warning(interaction.guild.id, user.id, interaction.user.id, reason)
    db.add_log(interaction.guild.id, "WARN", user.id, interaction.user.id, reason)
    await interaction.response.send_message(f"⚠️ {user.mention} получил предупреждение: {reason}")

@bot.tree.command(name="kick", description="Кикнуть пользователя")
async def kick_cmd(interaction: discord.Interaction, user: discord.Member, reason: Optional[str] = "Не указана"):
    try:
        await user.kick(reason=reason)
        db.add_log(interaction.guild.id, "KICK", user.id, interaction.user.id, reason)
        await interaction.response.send_message(f"👢 {user.mention} кикнут: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="ban", description="Забанить пользователя")
async def ban_cmd(interaction: discord.Interaction, user: discord.Member, reason: Optional[str] = "Не указана"):
    try:
        await user.ban(reason=reason, delete_message_days=1)
        db.add_log(interaction.guild.id, "BAN", user.id, interaction.user.id, reason)
        await interaction.response.send_message(f"🔨 {user.mention} забанен: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="unban", description="Разбанить пользователя")
async def unban_cmd(interaction: discord.Interaction, user_id: str):
    try:
        user = discord.Object(id=int(user_id))
        await interaction.guild.unban(user, reason="Разбан")
        db.add_log(interaction.guild.id, "UNBAN", int(user_id), interaction.user.id, "Разбан")
        await interaction.response.send_message(f"✅ Пользователь {user_id} разбанен")
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)
        # ========== СООБЩЕНИЯ ==========
@bot.tree.command(name="say", description="Отправить сообщение от имени бота")
async def say_cmd(interaction: discord.Interaction, message: str):
    await interaction.response.send_message("✅ Отправлено", ephemeral=True)
    await interaction.channel.send(message)
    db.add_log(interaction.guild.id, "SAY", 0, interaction.user.id, message)

@bot.tree.command(name="dm", description="Отправить сообщение всем участникам")
async def dm_all(interaction: discord.Interaction, message: str):
    await interaction.response.send_message("⏳ Начинаю рассылку...", ephemeral=True)
    sent = 0
    for member in interaction.guild.members:
        if not member.bot:
            try:
                await member.send(f"📨 Сообщение от {interaction.guild.name}:\n{message}")
                sent += 1
                await asyncio.sleep(0.5)
            except:
                pass
    await interaction.followup.send(f"✅ Отправлено {sent} участникам", ephemeral=True)
    db.add_log(interaction.guild.id, "DM_ALL", 0, interaction.user.id, f"Отправлено {sent}")

@bot.tree.command(name="dmuser", description="Отправить сообщение конкретному пользователю")
async def dm_user(interaction: discord.Interaction, user: discord.Member, message: str):
    try:
        await user.send(f"📨 Сообщение от {interaction.guild.name}:\n{message}")
        await interaction.response.send_message(f"✅ Сообщение отправлено {user.mention}", ephemeral=True)
        db.add_log(interaction.guild.id, "DM_USER", user.id, interaction.user.id, message)
    except:
        await interaction.response.send_message(f"❌ Не удалось отправить {user.mention}", ephemeral=True)
# репорты 
import discord
from discord.ext import commands
import datetime

class ReportButtons(discord.ui.View):
    def __init__(self, reporter_id):
        super().__init__(timeout=None)
        self.reporter_id = reporter_id

    @discord.ui.button(label="✅ Одобрено", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Репорт одобрен модератором {interaction.user.mention}", ephemeral=True
        )
        try:
            user = await interaction.guild.fetch_member(self.reporter_id)
            await user.send(f"Ваш репорт одобрен модератором {interaction.user.mention}")
        except:
            pass
        self.stop()

    @discord.ui.button(label="❌ Отказано", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Репорт отклонён модератором {interaction.user.mention}", ephemeral=True
        )
        try:
            user = await interaction.guild.fetch_member(self.reporter_id)
            await user.send(f"Ваш репорт отклонён модератором {interaction.user.mention}")
        except:
            pass
        self.stop()

    @discord.ui.button(label="⏳ В процессе", style=discord.ButtonStyle.gray)
    async def pending(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Репорт в процессе рассмотрения модератором {interaction.user.mention}", ephemeral=True
        )
        self.stop()


@bot.tree.command(name="report", description="Пожаловаться на пользователя")
async def report_cmd(interaction: discord.Interaction,
                     user: discord.Member,
                     reason: str,
                     proof: discord.Attachment = None):

    # Проверка файла
    if proof and not proof.content_type.startswith(('image/', 'video/')):
        await interaction.response.send_message(
            "❌ Прикрепите фото или видео как доказательство!",
            ephemeral=True
        )
        return

    # Канал для репортов
    channel_name = "📢-репорты"
    report_channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)

    if not report_channel:
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=True)
        }
        report_channel = await interaction.guild.create_text_channel(
            channel_name, overwrites=overwrites
        )

    # Embed репорта
    embed = discord.Embed(
        title="⚠️ Новый репорт",
        color=0xe74c3c,
        timestamp=datetime.datetime.now()
    )
    embed.add_field(name="Нарушитель", value=f"{user.mention} ({user.id})", inline=True)
    embed.add_field(name="Жалобщик", value=f"{interaction.user.mention} ({interaction.user.id})", inline=True)
    embed.add_field(name="Причина", value=reason, inline=False)
    if proof:
        if proof.content_type.startswith("image/"):
            embed.set_image(url=proof.url)
        else:
            embed.add_field(name="Доказательство", value=f"[Файл]({proof.url})", inline=False)

    embed.set_footer(text=f"ID репорта: {interaction.id}")

    view = ReportButtons(interaction.user.id)
    await report_channel.send(embed=embed, view=view)

    # Подтверждение пользователю
    await interaction.response.send_message(
        "✅ Ваш репорт отправлен модераторам!", ephemeral=True
    )

    # Лог в базу
    db.add_log(interaction.guild.id, "REPORT_CREATED", user.id, interaction.user.id, reason)
    # ========== МОДЕРАТОРЫ ==========
@bot.tree.command(name="mod", description="Назначить модератора")
async def mod_cmd(interaction: discord.Interaction, user: discord.Member, log_channel: discord.TextChannel):
    role_name = "👮 Модератор"
    role = discord.utils.get(interaction.guild.roles, name=role_name)
    
    if not role:
        try:
            role = await interaction.guild.create_role(
                name=role_name,
                color=discord.Color.blue(),
                permissions=discord.Permissions(
                    kick_members=True,
                    ban_members=True,
                    manage_messages=True,
                    moderate_members=True
                )
            )
        except:
            await interaction.response.send_message("❌ Нет прав для создания ролей!", ephemeral=True)
            return
    
    try:
        await user.add_roles(role)
        
        # Создаём эмбед
        embed = discord.Embed(
            title="✅ Назначение модератора",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Пользователь", value=f"{user.mention}", inline=True)
        embed.add_field(name="Назначил", value=f"{interaction.user.mention}", inline=True)
        embed.add_field(name="Роль", value=f"{role.mention}", inline=True)
        embed.set_footer(text="Время назначения")
        
        # Отправляем эмбед в канал логов
        await log_channel.send(embed=embed)
        
        # Ответ пользователю, что назначение прошло
        await interaction.response.send_message(f"✅ {user.mention} теперь модератор! Информация отправлена в {log_channel.mention}", ephemeral=True)
        
        # Логирование в базу, если есть
        db.add_log(interaction.guild.id, "MOD", user.id, interaction.user.id, "Назначение")
        
    except:
        await interaction.response.send_message("❌ Нет прав для выдачи ролей!", ephemeral=True)
# ========== ЛОГИ ==========

# Словарь для хранения выбранного лог-канала
bot.log_channels = {}  # guild_id: channel_id

# Команда для выбора лог-канала
@bot.tree.command(name="log_channel", description="Устанавливает канал для логирования действий")
async def log_channel_cmd(interaction: discord.Interaction, channel: discord.TextChannel):
    bot.log_channels[interaction.guild.id] = channel.id
    await interaction.response.send_message(f"✅ Канал {channel.mention} выбран для логов!", ephemeral=True)

# Функция отправки логов
async def send_log(guild_id, message):
    channel_id = bot.log_channels.get(guild_id)
    if not channel_id:
        return
    channel = bot.get_channel(channel_id)
    if channel:
        try:
            await channel.send(message)
        except:
            pass

# Слушатели событий

# Роли
@bot.event
async def on_guild_role_create(role):
    await send_log(role.guild.id, f"➕ Роль создана: {role.name}")

@bot.event
async def on_guild_role_delete(role):
    await send_log(role.guild.id, f"➖ Роль удалена: {role.name}")

@bot.event
async def on_guild_role_update(before, after):
    await send_log(before.guild.id, f"🎨 Роль изменена: {before.name} → {after.name}, цвет: {after.color}")

# Каналы
@bot.event
async def on_guild_channel_create(channel):
    await send_log(channel.guild.id, f"➕ Канал создан: {channel.name}")

@bot.event
async def on_guild_channel_delete(channel):
    await send_log(channel.guild.id, f"➖ Канал удалён: {channel.name}")

# Сообщения
@bot.event
async def on_message_delete(message):
    if message.guild:
        await send_log(message.guild.id, f"🗑 Сообщение удалено от {message.author.mention}: {message.content}")

@bot.event
async def on_message_edit(before, after):
    if before.guild:
        await send_log(before.guild.id, f"✏ Сообщение от {before.author.mention} изменено:\nСтарое: {before.content}\nНовое: {after.content}")

# Голосовые события
@bot.event
async def on_voice_state_update(member, before, after):
    if not member.guild:
        return

    # Вход в голосовой канал
    if before.channel is None and after.channel is not None:
        asyncio.create_task(send_log(member.guild.id, f"🎤 {member.mention} зашёл в голосовой канал {after.channel.name}"))

    # Выход из голосового канала
    if before.channel is not None and after.channel is None:
        asyncio.create_task(send_log(member.guild.id, f"🚪 {member.mention} вышел из голосового канала {before.channel.name}"))

    # Перемещение между каналами
    if before.channel is not None and after.channel is not None and before.channel != after.channel:
        asyncio.create_task(send_log(member.guild.id, f"🔀 {member.mention} переместился из {before.channel.name} в {after.channel.name}"))

    # Микрофон (mute/unmute)
    if before.self_mute != after.self_mute:
        status = "включил микрофон" if not after.self_mute else "выключил микрофон"
        asyncio.create_task(send_log(member.guild.id, f"🎙 {member.mention} {status}"))

    # Наушники / деаф (deaf/undeaf)
    if before.self_deaf != after.self_deaf:
        status = "включил наушники" if not after.self_deaf else "выключил наушники"
        asyncio.create_task(send_log(member.guild.id, f"🎧 {member.mention} {status}"))
        # ========== АВТО-РОЛЬ ==========
# Перед запуском бота создаём словарь для хранения ролей
if not hasattr(bot, "autoroles"):
    bot.autoroles = {}

@bot.tree.command(name="setautorole", description="Устанавливает роль, которая будет выдаваться автоматически новым участникам")
async def setautorole_cmd(interaction: discord.Interaction, role: discord.Role):
    # Сохраняем роль в словаре
    bot.autoroles[interaction.guild.id] = role.id
    
    await interaction.response.send_message(
        f"✅ Роль {role.mention} теперь будет выдаваться автоматически новым участникам!", 
        ephemeral=True
    )

# ========== СЛУШАТЕЛЬ ПРИСОЕДИНЕНИЯ ==========
@bot.event
async def on_member_join(member):
    if member.bot:
        return
    
    role_id = bot.autoroles.get(member.guild.id)
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role)
            except:
                pass  # Если нет прав, игнорируем
# ========== АВТО-СНЯТИЕ МУТОВ ==========
@tasks.loop(minutes=1)
async def check_mutes():
    now = datetime.datetime.now()
    db.c.execute('SELECT * FROM mutes WHERE active = 1')
    mutes = db.c.fetchall()
    
    for mute in mutes:
        id, guild_id, user_id, mod_id, reason, end_time, active = mute
        end = datetime.datetime.fromisoformat(end_time)
        if end < now:
            guild = bot.get_guild(guild_id)
            if guild:
                member = guild.get_member(user_id)
                if member:
                    try:
                        await member.timeout(None, reason="Авто-снятие")
                    except:
                        pass
            db.c.execute('UPDATE mutes SET active = 0 WHERE id = ?', (id,))
    db.conn.commit()
# Приветсвие:
async def generate_welcome_image(member: discord.Member):
    """Генерирует красивую картинку для приветствия"""
    try:
        # Скачиваем аватар пользователя
        async with aiohttp.ClientSession() as session:
            async with session.get(str(member.avatar.url)) as resp:
                if resp.status == 200:
                    avatar_data = await resp.read()
        
        # Создаем изображение (фон)
        width, height = 1024, 400
        background = Image.new('RGBA', (width, height), (54, 57, 63, 255))
        draw = ImageDraw.Draw(background)
        
        # Добавляем аватар (круглый)
        avatar = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
        avatar = avatar.resize((200, 200))
        
        # Создаем маску для круга
        mask = Image.new('L', (200, 200), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, 200, 200), fill=255)
        
        # Накладываем аватар
        avatar_circle = Image.new('RGBA', (200, 200), (0, 0, 0, 0))
        avatar_circle.paste(avatar, (0, 0), mask)
        background.paste(avatar_circle, (width//2 - 100, 50), avatar_circle)
        
        # Добавляем текст
        try:
            font_large = ImageFont.truetype("arial.ttf", 48)
            font_small = ImageFont.truetype("arial.ttf", 32)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Текст приветствия
        text = f"Добро пожаловать, {member.name}!"
        draw.text((width//2, 270), text, font=font_large, 
                 fill=(255, 255, 255), anchor="mm")
        
        # Подтекст
        subtitle = f"Ты участник №{member.guild.member_count}"
        draw.text((width//2, 330), subtitle, font=font_small,
                 fill=(200, 200, 200), anchor="mm")
        
        # Сохраняем в буфер
        buffer = io.BytesIO()
        background.save(buffer, format='PNG')
        buffer.seek(0)
        
        return buffer
        
    except Exception as e:
        print(f"Ошибка генерации изображения: {e}")
        return None
# Прощание (Goodbye)  
@bot.event
async def on_member_remove(member: discord.Member):
    """Обработчик выхода участника"""
    try:
        settings = db.c.execute(
            'SELECT * FROM welcome_settings WHERE guild_id = ?',
            (member.guild.id,)
        ).fetchone()
        
        if not settings or not settings.get('goodbye_enabled', 0):
            return
        
        channel_id = settings.get('goodbye_channel_id') or settings.get('channel_id')
        if not channel_id:
            return
        
        channel = member.guild.get_channel(channel_id)
        if not channel:
            return
        
        # Сообщение прощания
        goodbye_msg = settings.get('goodbye_message')
        if not goodbye_msg:
            goodbye_messages = [
                "😢 {user} покинул нас...",
                "🚪 {user} вышел с сервера",
                "👋 Прощай, {user}! Надеемся вернешься!",
                "💔 {user} нас покинул",
                "🌌 {user} отправился в иные миры..."
            ]
            goodbye_msg = random.choice(goodbye_messages)
        
        goodbye_msg = goodbye_msg.replace('{user}', member.name)
        goodbye_msg = goodbye_msg.replace('{guild}', member.guild.name)
        
        embed = discord.Embed(
            description=goodbye_msg,
            color=0xff5555,
            timestamp=datetime.datetime.now()
        )
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        embed.set_footer(text=f"Был с нами с {member.joined_at.strftime('%d.%m.%Y')}")
        
        await channel.send(embed=embed)
        
    except Exception as e:
        print(f"Ошибка в goodbye: {e}") 
# ========== СТАФФ ==========
@bot.tree.command(name="staff", description="Показать список стаффа сервера")
async def staff_cmd(interaction: discord.Interaction):
    guild = interaction.guild

    owner = guild.owner
    admins = []
    mods = []

    for member in guild.members:
        perms = member.guild_permissions

        if member == owner:
            continue

        if perms.administrator:
            admins.append(member)
        elif (
            perms.ban_members
            or perms.kick_members
            or perms.moderate_members
            or perms.manage_messages
        ):
            mods.append(member)

    embed = discord.Embed(
        title="📋 Стафф сервера",
        color=0x2f3136
    )

    # Владелец
    embed.add_field(
        name="👑 Владелец",
        value=f"⚫ {owner.mention}",
        inline=False
    )

    # Администраторы
    if admins:
        admins_text = "\n".join(f"⚫ {m.mention} 👑" for m in admins)
    else:
        admins_text = "⚫ Нет"

    embed.add_field(
        name="🛡️ Администраторы",
        value=admins_text,
        inline=False
    )

    # Модераторы
    if mods:
        mods_text = "\n".join(f"⚫ {m.mention}" for m in mods)
    else:
        mods_text = "⚫ Нет"

    embed.add_field(
        name="🔨 Модераторы",
        value=mods_text,
        inline=False
    )

    embed.set_footer(
        text=f"Всего стаффа: {1 + len(admins) + len(mods)}"
    )

    await interaction.response.send_message(embed=embed)
# ========== ЗАПУСК БОТА ==========
@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен!')
    print(f'✅ Серверов: {len(bot.guilds)}')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Синхронизировано {len(synced)} команд')
    except Exception as e:
        print(f'❌ Ошибка синхронизации: {e}')
    
    check_mutes.start()
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"/help | {len(bot.guilds)} серверов"
        )
    )

@bot.event
async def on_guild_join(guild):
    print(f'✅ Добавлен на сервер: {guild.name}')

# ========== ТОЧКА ВХОДА ==========
async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    print("🚀 Запускаю бота...")
    asyncio.run(main())                  
