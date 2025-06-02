import os
import time
import asyncio
import aiohttp
import aiofiles
import random
from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import (
    UsernameNotOccupiedError,
    UsernameInvalidError,
    PeerIdInvalidError,
)

api_id = 12108701
api_hash = "fb82e09eca95fd95b213b68a5a78f693"

client = TelegramClient("dake_session", api_id, api_hash)

HELP_TEXT = """dake v2 
==========================
※ .dake - вывод хелпа 
※ .dh (время в секундах) (файл с шаблонами) (название картинки, если ее нет то просто точка) (комментарий от себя)
※ .save (имя) - сохранить картинку
※ .dxadd (id или @username) [название_медиа] - добавить цель с медиа или без
※ .dxrem (id) - удалить таргет
※ .dxlist - список целей (всех)
※ .st - остановить все автоответы
※ .dz - остановить команду .dh 
※ .dtime - аптайм бота
※ .dclear - остановить всё 	
※ .id - узнать айди чата либо человека реплаем
==========================
soft by @BloodyDake // Купить софт там же"""

HELP_IMAGE_URL = "https://i.postimg.cc/c1Qx7S32/1000049329.jpg"
TEMPLATES_DIR = "templates"
IMAGES_DIR = "images"
TEMPLATES_FILE = os.path.join(TEMPLATES_DIR, "templates.txt")

DX_TEMPLATES = [
    "я тебе мать ебал", "ты пидорасина ебаная", "ты слабый пидорас", "на клык тебе скинул", "ты сын шалавы", 
    "я тебе жопу разорву", "ты ебучий лох", "закрой сосало", "ты ничтожный телок", "я тебе мать в рот ебал", 
    "на тебе хуй", "ты слабак ебаный", "я твою мать трахал", "соси хуй шестерка", "ты сын шлюхи", 
    "я тебя отпижу", "я тебе ноги оторву", "я твоего отца ебал", "соси как шлюха", "твоя мать — путана"
]

os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

start_time = time.time()
auto_targets = {}
dh_tasks = {}
last_reply_time = {}

import io

async def download_file(url: str, path: str) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(path, mode='wb')
                    await f.write(await resp.read())
                    await f.close()
                    return True
    except Exception as e:
        print("ошибка загрузки файла:", e)
    return False

async def download_file_in_memory(url: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    return io.BytesIO(data)
    except Exception:
        pass
    return None

async def read_template_lines(filename: str):
    path = os.path.join(TEMPLATES_DIR, filename)
    if not os.path.isfile(path):
        return []
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in await f.readlines() if line.strip()]
    return lines

async def get_random_template_line():
    if os.path.isfile(TEMPLATES_FILE):
        async with aiofiles.open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in await f.readlines() if line.strip()]
        if lines:
            return random.choice(lines)
    return random.choice(DX_TEMPLATES)

async def dh_worker(chat_id, cooldown, template_file, image_name, comment):
    try:
        lines = await read_template_lines(template_file)
        if not lines:
            return
        index = 0
        while True:
            line = lines[index]
            index = (index + 1) % len(lines)
            text = (comment + "\n" if comment else "") + line
            img_path = None
            if image_name != ".":
                possible_path = os.path.join(IMAGES_DIR, image_name)
                if os.path.isfile(possible_path):
                    img_path = possible_path
            if img_path:
                await client.send_file(chat_id, img_path, caption=text)
            else:
                await client.send_message(chat_id, text)
            await asyncio.sleep(cooldown)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print("ошибка в dh_worker:", e)

async def safe_get_user(uid_or_username: str):
    try:
        if uid_or_username.startswith("@"):
            entity = await client.get_entity(uid_or_username)
            return entity
        try:
            uid_int = int(uid_or_username)
            entity = await client.get_entity(uid_int)
            return entity
        except ValueError:
            uname = uid_or_username.lstrip("@")
            entity = await client.get_entity(uname)
            return entity
    except (UsernameNotOccupiedError, UsernameInvalidError, PeerIdInvalidError):
        return None
    except Exception:
        return None

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.(.+)"))
async def commands_handler(event):
    me = await client.get_me()
    if event.sender_id != me.id:
        return

    text = event.raw_text
    args = text.strip().split(maxsplit=4)
    cmd = args[0][1:].lower()
    cid = event.chat_id

    if cmd in {"dake", "help"}:
        if event.is_private:
            try:
                await event.delete()
            except Exception:
                pass
        path = os.path.join(IMAGES_DIR, "help.jpg")
        if not os.path.exists(path):
            ok = await download_file(HELP_IMAGE_URL, path)
            if not ok:
                await event.respond("ошибка загрузки help.jpg")
                return
        await client.send_file(cid, path, caption=HELP_TEXT)

    elif cmd == "dtime":
        uptime = int(time.time() - start_time)
        d, rem = divmod(uptime, 86400)
        h, rem = divmod(rem, 3600)
        m, _ = divmod(rem, 60)
        msg = f"{d}д {h}ч {m}м" if d else f"{h}ч {m}м" if h else f"{m}м"
        await event.edit(f"аптайм бота: {msg}")

    elif cmd == "id":
        if event.is_reply:
            reply = await event.get_reply_message()
            if reply.sender_id:
                await event.edit(f"id пользователя в реплае: {reply.sender_id}")
            else:
                await event.edit("нет sender_id в реплае")
        else:
            await event.edit(f"id чата: {cid}")

    elif cmd == "save":
        if len(args) < 2:
            await event.edit(".save <имя>")
            return
        if not event.is_reply:
            await event.edit("ответь на медиа-сообщение")
            return
        reply = await event.get_reply_message()
        name = args[1]
        ext = None
        if reply.photo:
            ext = ".jpg"
        elif reply.document and reply.document.mime_type:
            ext = os.path.splitext(reply.file.name)[1] if reply.file.name else None
            if ext is None:
                ext = ".bin"
        elif reply.video:
            ext = ".mp4"
        if not ext:
            await event.edit("тип медиа не поддерживается")
            return
        path = os.path.join(IMAGES_DIR, name + ext)
        await reply.download_media(file=path)
        await event.edit(f"сохранено как {name + ext}")

    elif cmd == "dxadd":
        if len(args) < 2:
            await event.edit(".dxadd <id или @username> [медиа]")
            return
        uid_or_username = args[1]
        media_name = args[2] if len(args) > 2 else None

        user = await safe_get_user(uid_or_username)
        if not user:
            await event.edit("ошибка: пользователь не найден")
            return

        if media_name:
            media_path = os.path.join(IMAGES_DIR, media_name)
            if not os.path.isfile(media_path):
                await event.edit(f"медиа {media_name} не найдено в images")
                return

        if cid not in auto_targets:
            auto_targets[cid] = {}
        auto_targets[cid][str(user.id)] = (media_name, user.username or user.first_name or str(user.id))
        await event.edit(f"цель {user.id} добавлена с медиа: {media_name or 'нет'}")

    elif cmd == "dxrem":
        if len(args) < 2:
            await event.edit(".dxrem <id>")
            return
        uid = args[1]
        if cid in auto_targets and uid in auto_targets[cid]:
            del auto_targets[cid][uid]
            await event.edit(f"цель {uid} удалена")
        else:
            await event.edit("цель не найдена")

    elif cmd == "dxlist":
        lines = []
        for chat_key, targets in auto_targets.items():
            try:
                chat = await client.get_entity(chat_key)
                chat_name = chat.title if hasattr(chat, "title") else f"чат {chat_key}"
            except:
                chat_name = f"чат {chat_key}"
            for i, (uid, (media, uname)) in enumerate(targets.items(), 1):
                lines.append(f"[{chat_name}] target {i} - {uname} / {uid} (медиа: {media or 'нет'})")
        await event.edit("\n".join(lines) if lines else "целей нет")

    elif cmd in {"dz", "st"}:
        if cid in dh_tasks:
            dh_tasks[cid].cancel()
            del dh_tasks[cid]
        await event.edit("остановлено")

    elif cmd == "dclear":
        if cid in dh_tasks:
            dh_tasks[cid].cancel()
            del dh_tasks[cid]
        if cid in auto_targets:
            auto_targets[cid].clear()
        await event.edit("всё остановлено")

    elif cmd == "dh":
        if len(args) < 4:
            await event.edit("использование: .dh <кд> <файл шаблона> <картинка или .> [коммент]")
            return
        try:
            cooldown = int(args[1])
        except ValueError:
            await event.edit("кд должно быть числом")
            return
        template_file = args[2]
        image_name = args[3]
        comment = args[4] if len(args) > 4 else ""
        if cid in dh_tasks:
            dh_tasks[cid].cancel()
        dh_tasks[cid] = asyncio.create_task(dh_worker(cid, cooldown, template_file, image_name, comment))
        await event.edit(f".dh запущена: кд={cooldown}, шаблон={template_file}, картинка={image_name}, комментарий='{comment}'")

    else:
        await event.edit("неизвестная команда")

@client.on(events.NewMessage(incoming=True))
async def auto_reply_targets(event):
    me = await client.get_me()
    if event.sender_id == me.id:
        return

    cid = event.chat_id
    uid = str(event.sender_id)

    if cid not in auto_targets or uid not in auto_targets[cid]:
        return

    now = time.time()
    key = (cid, uid)

    if key in last_reply_time and now - last_reply_time[key] < 15:
        return

    media_name, username = auto_targets[cid][uid]
    text = await get_random_template_line()
    full_text = f"{username} {text}"

    reply_to_id = event.message.id

    if media_name and media_name != ".":
        media_path = os.path.join(IMAGES_DIR, media_name)
        if os.path.isfile(media_path):
            await client.send_file(cid, media_path, caption=full_text, reply_to=reply_to_id)
        else:
            await client.send_message(cid, full_text, reply_to=reply_to_id)
    else:
        await client.send_message(cid, full_text, reply_to=reply_to_id)

    last_reply_time[key] = now

async def main():
    await client.start()
    print("бот запущен")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
