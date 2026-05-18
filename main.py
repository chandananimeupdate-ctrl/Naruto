"""
NARUTO RPG BOT v2 — Professional Edition
400+ Characters | Speed Battles | Transform System | Stone Drops
NC Economy | Level System | Paginated /mychar | Photo Battles
"""
import asyncio, random, os, time, re, unicodedata, io, json, html as _html
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
import urllib.request
from telegram import (InlineKeyboardButton as Btn, InlineKeyboardMarkup as Kbd,
                      Update, BotCommand, InputMediaPhoto,
                      ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove)
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler,
                           ContextTypes, MessageHandler, filters)
from telegram.error import BadRequest

TOKEN = os.getenv("BOT_TOKEN", "8676998237:AAHOhapMythGy-9VE5EEUkYSTwQ_A2IhdAc")
MONGO_URL = os.getenv("MONGO_URL", (
    "mongodb://LAKSHMANLOVCHINNU:LAKSH_LUB_CHINNU@"
    "ac-kpncihe-shard-00-00.yfyatwy.mongodb.net:27017,"
    "ac-kpncihe-shard-00-01.yfyatwy.mongodb.net:27017,"
    "ac-kpncihe-shard-00-02.yfyatwy.mongodb.net:27017/"
    "?ssl=true&replicaSet=atlas-zftykc-shard-0&authSource=admin"
))
_mongo_client  = AsyncIOMotorClient(MONGO_URL)
_mongo_db      = _mongo_client["naruto_rpg"]
users_col      = _mongo_db["users"]
chars_col      = _mongo_db["chars"]
training_col   = _mongo_db["training"]
groups_col     = _mongo_db["groups"]
counters_col   = _mongo_db["counters"]
clans_col      = _mongo_db["clan_admins"]
clan_req_col   = _mongo_db["clan_requests"]
weapons_col    = _mongo_db["user_weapons"]
clan_members_col = _mongo_db["clan_members"]

async def _next_char_id() -> int:
    doc = await counters_col.find_one_and_update(
        {"_id": "char_id"}, {"$inc": {"seq": 1}},
        upsert=True, return_document=True)
    return doc["seq"]

def _cdoc(d):
    """Normalise a MongoDB char document so code can use d['id']."""
    if d is None:
        return None
    d = dict(d)
    d.setdefault("id", d.get("_id"))
    return d

# ─── BANNERS ────────────────────────────────────────────────────
START_BANNER   = "https://repgyetdcodkynrbxocg.supabase.co/storage/v1/object/public/images/telegram-1778647040209-38f0ceac.jpg"
SUMMON_BANNER  = "https://files.catbox.moe/qop9az.jpg"
SHOP_BANNER    = "https://files.catbox.moe/0zsksd.jpg"
STATS_BANNER   = "https://files.catbox.moe/8o6qm3.jpg"
VILLAGE_BANNER = "https://repgyetdcodkynrbxocg.supabase.co/storage/v1/object/public/images/telegram-1778637727969-b33c08c4.jpg"
CLAN_BANNER    = "https://files.catbox.moe/or4r17.jpg"

# Pre-downloaded banner bytes — populated at startup so banners always send
# even if the remote URL is temporarily unreachable.
_BANNER_CACHE: dict = {}   # url → io.BytesIO bytes (seekable)

# ─── PREMIUM / CUSTOM EMOJI ──────────────────────────────────────
# How to fill in your own IDs:
#   1. Open a Telegram channel/group that has a Naruto emoji pack active.
#   2. Forward any message containing those custom emoji to your bot's DM.
#   3. The bot will automatically reply with each emoji's ID.
#   4. Paste the ID into the matching key below.
#   5. Messages that use pe() must use parse_mode="HTML" — see examples below.
#
# Good packs to search on Telegram:
#   "Naruto Emoji", "Shinobi Pack", "Anime RPG Stickers", "Naruto Animated"
#
# IDs marked "REPLACE_ME" fall back to the plain emoji until you fill them in.

PE: dict[str, str] = {
    # ── UI chrome ──────────────────────────────────────────────────
    "sword":      "6035338995536238141",   # <tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji>  weapon / battle
    "shield":     "6039727447090403055",   # <tg-emoji emoji-id='6039727447090403055'>🛡️</tg-emoji>  defense
    "hp":         "5427095369278299187",   # <tg-emoji emoji-id='5427095369278299187'>❤️</tg-emoji>  health points
    "chakra":     "5382228835234236951",   # <tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji>  chakra
    "star":       "5424892463372312872",   # <tg-emoji emoji-id='5424892463372312872'>⭐</tg-emoji>  rarity / rank
    "coin":       "6032916496542339992",   # <tg-emoji emoji-id='6032916496542339992'>🪙</tg-emoji>  NC currency  (user-specified)
    "fire":       "6001182426301209831",   # <tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji>  fire / rage   (updated)
    "lightning":  "5812074410667938253",   # <tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji>  lightning     (updated)
    "skull":      "5426953124256424318",   # ☠️  death / KO    (NarutoAnimate)
    "trophy":     "5426976939850080222",   # 😁  victory       (NarutoAnimate)
    "scroll":     "5426895906702107044",   # 🤔  mission/think  (NarutoAnimate)
    "village":    "5427342518876381603",   # ☺️  home/village   (NarutoAnimate)
    "clan":       "5224388744156557558",   # <tg-emoji emoji-id='5224388744156557558'>⚜️</tg-emoji>  clan symbol    (NarutoPack_Emoji)
    "rank":       "5424767857781122187",   # <tg-emoji emoji-id='5960921054976151481'>😎</tg-emoji>  rank/swagger   (NarutoAnimate)
    "diamond":    "5454122580564786042",   # 💍  rare/epic      (NarutoPack_Emoji)
    "leaf":       "5426872512015244606",   # <tg-emoji emoji-id='5426872512015244606'>👣</tg-emoji>  leaf/travel    (NarutoAnimate)
    "stone":      "5427394299002101953",   # 😑  stone-faced    (NarutoAnimate)
    "exp":        "5352706840654283152",   # <tg-emoji emoji-id='5798530836890390483'>🔴</tg-emoji>  exp / grind    (updated)
    "team":       "5424663099233805040",   # 😊  friendly/team  (NarutoAnimate)
    "summon":     "5424982129404552325",   # 😜  summon/gacha   (NarutoAnimate)
    "shop":       "5424640546360533904",   # 🙂  shop           (NarutoAnimate)
    "daily":      "5424830993800373710",   # 🙂  daily reward   (NarutoAnimate)
    "map":        "5425114616260731920",   # <tg-emoji emoji-id='5425114616260731920'>🏃</tg-emoji>  travel/map     (NarutoAnimate)
    # ── Naruto-specific ────────────────────────────────────────────
    "kunai":      "5224667002202764346",   # <tg-emoji emoji-id='5224388744156557558'>⚜️</tg-emoji>  weapon/kunai   (NarutoPack_Emoji)
    "sharingan":  "6035051267087143217",   # <tg-emoji emoji-id='6035051267087143217'>👁</tg-emoji>  Sharingan eye  (Reo_sad pack)
    "rasengan":   "5426957509418031897",   # 😵  spiral/dizzy   (NarutoAnimate)
    "sage":       "5425111072912713470",   # 😶‍🌫️ sage mode/mist  (NarutoAnimate)
    "bijuu":      "5427397421443325675",   # 😱  tailed beast   (NarutoAnimate)
    "anbu":       "5425113284820869526",   # 😶  masked/silent  (NarutoAnimate)
    "akatsuki":   "5427071300281572656",   # <tg-emoji emoji-id='5798580443762659706'>😈</tg-emoji>  devil/Akatsuki (NarutoAnimate)
    "curse":      "5427302588565430059",   # 👿  curse mark     (NarutoAnimate)
    "byakugan":   "6034945975963881533",   # <tg-emoji emoji-id='6035051267087143217'>👁</tg-emoji>  Byakugan eye   (Reo_sad pack)
    "susanoo":    "5427206638996037048",   # 🤬  power/Susanoo  (NarutoAnimate)
    "round":      "5769455402945090965",   # <tg-emoji emoji-id='5769455402945090965'>🔄</tg-emoji>  round/NC badge
    # ── MostRandomPack UI objects (explore / shop / stats / village) ─
    "flame":      "5958749833043908494",   # <tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji>  fire/flame      (MostRandomPack)
    "chain":      "5958595510573994440",   # <tg-emoji emoji-id='5958595510573994440'>⛓</tg-emoji>  chain/bound     (MostRandomPack)
    "blood":      "5960999309280284625",   # <tg-emoji emoji-id='5960999309280284625'>🩸</tg-emoji>  blood/damage    (MostRandomPack)
    "bolt":       "5960943740993408746",   # <tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji>️  bolt/power      (MostRandomPack)
    "moon2":      "5958677716248039553",   # <tg-emoji emoji-id='5958677716248039553'>🌙</tg-emoji>  moon/night      (MostRandomPack)
    "web":        "5960831599397310319",   # 🕸  web/trap        (MostRandomPack)
    "gem2":       "5933651800807705779",   # <tg-emoji emoji-id='5454122580564786042'>💎</tg-emoji>  rare gem        (MostRandomPack)
    # ── Colored dot indicators (HP bars / battle status) ─────────────
    "dot_red":    "5798530836890390483",   # <tg-emoji emoji-id='5798530836890390483'>🔴</tg-emoji>  enemy HP dot    (MostRandomPack)
    "dot_blue":   "5798483635199807367",   # <tg-emoji emoji-id='5798483635199807367'>🔵</tg-emoji>  player HP dot   (updated)
    "dot_green":  "5958636789504676899",   # <tg-emoji emoji-id='5958636789504676899'>🟢</tg-emoji>  full HP dot     (MostRandomPack)
    "dot_purple": "5769297434047943583",   # <tg-emoji emoji-id='5769297434047943583'>🟣</tg-emoji>  purple indicator (MostRandomPack)
    "dot_yellow": "5915696866120438280",   # <tg-emoji emoji-id='5915696866120438280'>🟡</tg-emoji>  yellow indicator (MostRandomPack)
    "dot_white":  "5981211262166504080",   # <tg-emoji emoji-id='5981211262166504080'>⚪️</tg-emoji>  white/empty dot (MostRandomPack)
    "dot_black":  "5981276193482084008",   # <tg-emoji emoji-id='5981276193482084008'>⚫️</tg-emoji>  black dot       (MostRandomPack)
    # ── Extra MostRandomPack objects ─────────────────────────────────
    "wolf":       "6003600664687546316",   # <tg-emoji emoji-id='6003600664687546316'>🐺</tg-emoji>  beast/wolf      (MostRandomPack)
    "wolf2":      "6005875631554826239",   # <tg-emoji emoji-id='6003600664687546316'>🐺</tg-emoji>  wolf variant    (MostRandomPack)
    "bat":        "5915934025624587718",   # <tg-emoji emoji-id='5915934025624587718'>🦇</tg-emoji>  bat             (MostRandomPack)
    "spider":     "5915873204592708984",   # <tg-emoji emoji-id='5915873204592708984'>🕷</tg-emoji>  spider          (MostRandomPack)
    "heart2":     "5913280629188857765",   # <tg-emoji emoji-id='5427095369278299187'>❤️</tg-emoji>  heart           (MostRandomPack)
    "triangle":   "5798863108445310738",   # <tg-emoji emoji-id='5798863108445310738'>🔺</tg-emoji>  red triangle    (MostRandomPack)
    "smirk":      "5769196747129622547",   # 😏  smirk           (MostRandomPack)
    "cool":       "5960921054976151481",   # <tg-emoji emoji-id='5960921054976151481'>😎</tg-emoji>  cool/sunglasses (MostRandomPack)
    "devil2":     "5798580443762659706",   # <tg-emoji emoji-id='5798580443762659706'>😈</tg-emoji>  devil variant   (MostRandomPack)
    "star3":      "5958689149450981191",   # <tg-emoji emoji-id='5424892463372312872'><tg-emoji emoji-id='5424892463372312872'>⭐</tg-emoji>️</tg-emoji>  star            (MostRandomPack)
    "diamond3":   "5771399137639534615",   # <tg-emoji emoji-id='5454122580564786042'>💎</tg-emoji>  diamond         (MostRandomPack)
    "fire4":      "5958475135525589052",   # <tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji>  fire            (MostRandomPack)
    "ghost":      "5769356343819374390",   # 👽  ghost/alien     (MostRandomPack)
    "web2":       "5915838664465718719",   # 🕸  cobweb          (MostRandomPack)
    "hat":        "5913400475956285496",   # 🎩  top hat         (MostRandomPack)
    "turtle":     "5812433134926434604",   # 🐢  turtle          (MostRandomPack)
    # ── Nature / element icons ────────────────────────────────────────
    "nat_fire":   "6001182426301209831",   # <tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji>  fire nature
    "nat_water":  "5814583814030102764",   # <tg-emoji emoji-id='5814583814030102764'>💧</tg-emoji>  water nature
    "nat_light":  "5812074410667938253",   # <tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji>  lightning nature
    "nat_wood":   "5802979783058919252",   # <tg-emoji emoji-id='5802979783058919252'>🌲</tg-emoji>  wood release
    "nat_ice":    "5852541321947910127",   # <tg-emoji emoji-id='5852541321947910127'>❄️</tg-emoji>  ice nature
    "nat_sun":    "5814672393435617023",   # <tg-emoji emoji-id='5814672393435617023'>☀️</tg-emoji>  yang/sun
    "nat_exp":    "5998841304052669228",   # <tg-emoji emoji-id='5998841304052669228'>💥</tg-emoji>  explosion nature
    "nat_gear":   "5999047234849611002",   # <tg-emoji emoji-id='5999047234849611002'>⚙️</tg-emoji>  metal/gear nature
    # ── Action / status icons ─────────────────────────────────────────
    "crit":       "5803297348645818019",   # <tg-emoji emoji-id='5998841304052669228'>💥</tg-emoji>  critical hit
    "xmark":      "5803134797018566405",   # <tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji>  miss / fail
    "exp_side":   "5978792181966573862",   # <tg-emoji emoji-id='5769297434047943583'>🟣</tg-emoji>  explore exp side
    "arrow_up":   "5803416753031615097",   # <tg-emoji emoji-id='5803416753031615097'>⬆️</tg-emoji>  up arrow
    "arrow_down": "5803204762035818905",   # <tg-emoji emoji-id='5803204762035818905'>⬇️</tg-emoji>  down arrow
    "arrow_right":"5802908349162851914",   # <tg-emoji emoji-id='5802908349162851914'>➡️</tg-emoji>  right arrow
    "arrow_left": "5803046350757039898",   # <tg-emoji emoji-id='5803046350757039898'>⬅️</tg-emoji>  left arrow
}

# Plain-text fallbacks shown when the custom emoji ID is not yet set
# or the user does not have Telegram Premium.
_PE_FALLBACK: dict[str, str] = {
    "sword": "<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji>",  "shield": "<tg-emoji emoji-id='6039727447090403055'>🛡️</tg-emoji>",  "hp": "<tg-emoji emoji-id='5427095369278299187'>❤️</tg-emoji>",      "chakra": "<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji>",
    "star":  "<tg-emoji emoji-id='5424892463372312872'>⭐</tg-emoji>",   "coin":   "<tg-emoji emoji-id='6032916496542339992'>🪙</tg-emoji>",  "fire": "<tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji>",     "lightning": "<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji>",
    "skull": "<tg-emoji emoji-id='5426953124256424318'>💀</tg-emoji>",  "trophy": "<tg-emoji emoji-id='5426976939850080222'>🏆</tg-emoji>",  "scroll": "📜",   "village": "<tg-emoji emoji-id='5427342518876381603'>🏘️</tg-emoji>",
    "clan":  "<tg-emoji emoji-id='5224388744156557558'>🏯</tg-emoji>",  "rank":   "<tg-emoji emoji-id='5424767857781122187'>🎖️</tg-emoji>", "diamond": "<tg-emoji emoji-id='5454122580564786042'>💎</tg-emoji>",  "leaf": "<tg-emoji emoji-id='5426872512015244606'>🍃</tg-emoji>",
    "stone": "<tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji>",  "exp":    "<tg-emoji emoji-id='5352706840654283152'>📈</tg-emoji>",  "team": "<tg-emoji emoji-id='5425113284820869526'>👥</tg-emoji>",     "summon": "✨",
    "shop":  "🛒",  "daily":  "📅",  "map": "<tg-emoji emoji-id='5425114616260731920'>🗺️</tg-emoji>",
    "kunai": "<tg-emoji emoji-id='6035338995536238141'><tg-emoji emoji-id='6035338995536238141'>🗡</tg-emoji>️</tg-emoji>", "sharingan": "<tg-emoji emoji-id='6035051267087143217'><tg-emoji emoji-id='6035051267087143217'>👁</tg-emoji>️</tg-emoji>", "rasengan": "<tg-emoji emoji-id='5426957509418031897'>🌀</tg-emoji>", "sage": "<tg-emoji emoji-id='5425111072912713470'>🐸</tg-emoji>",
    "bijuu": "👹",  "anbu": "😺",    "akatsuki": "<tg-emoji emoji-id='5958677716248039553'>🌙</tg-emoji>", "curse": "<tg-emoji emoji-id='5427302588565430059'>🔱</tg-emoji>",
    "byakugan": "🔮", "susanoo": "<tg-emoji emoji-id='5798483635199807367'>🔵</tg-emoji>",
    "round": "<tg-emoji emoji-id='5769455402945090965'>🔄</tg-emoji>",
    "flame": "<tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji>",  "chain": "<tg-emoji emoji-id='5958595510573994440'>⛓</tg-emoji>",   "blood": "<tg-emoji emoji-id='5960999309280284625'>🩸</tg-emoji>",  "bolt": "<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji>️",
    "moon2": "<tg-emoji emoji-id='5958677716248039553'>🌙</tg-emoji>",  "web":   "🕸",   "gem2":  "<tg-emoji emoji-id='5454122580564786042'>💎</tg-emoji>",
    "dot_red": "<tg-emoji emoji-id='5798530836890390483'>🔴</tg-emoji>",  "dot_blue": "<tg-emoji emoji-id='5798483635199807367'>🔵</tg-emoji>",  "dot_green": "<tg-emoji emoji-id='5958636789504676899'>🟢</tg-emoji>",
    "dot_purple": "<tg-emoji emoji-id='5769297434047943583'>🟣</tg-emoji>", "dot_yellow": "<tg-emoji emoji-id='5915696866120438280'>🟡</tg-emoji>", "dot_white": "<tg-emoji emoji-id='5981211262166504080'>⚪️</tg-emoji>", "dot_black": "<tg-emoji emoji-id='5981276193482084008'>⚫️</tg-emoji>",
    "wolf": "<tg-emoji emoji-id='6003600664687546316'>🐺</tg-emoji>",  "wolf2": "<tg-emoji emoji-id='6003600664687546316'>🐺</tg-emoji>",   "bat": "<tg-emoji emoji-id='5915934025624587718'>🦇</tg-emoji>",    "spider": "<tg-emoji emoji-id='5915873204592708984'>🕷</tg-emoji>",
    "heart2": "<tg-emoji emoji-id='5427095369278299187'>❤️</tg-emoji>", "triangle": "<tg-emoji emoji-id='5798863108445310738'>🔺</tg-emoji>", "smirk": "😏", "cool": "<tg-emoji emoji-id='5960921054976151481'>😎</tg-emoji>",
    "devil2": "<tg-emoji emoji-id='5798580443762659706'>😈</tg-emoji>", "star3": "<tg-emoji emoji-id='5424892463372312872'><tg-emoji emoji-id='5424892463372312872'>⭐</tg-emoji>️</tg-emoji>",   "diamond3": "<tg-emoji emoji-id='5454122580564786042'>💎</tg-emoji>", "fire4": "<tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji>",
    "ghost": "👽",  "web2": "🕸",   "hat": "🎩",    "turtle": "🐢",
    "nat_fire": "<tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji>", "nat_water": "<tg-emoji emoji-id='5814583814030102764'>💧</tg-emoji>", "nat_light": "<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji>", "nat_wood": "<tg-emoji emoji-id='5802979783058919252'>🌲</tg-emoji>",
    "nat_ice": "<tg-emoji emoji-id='5852541321947910127'>❄️</tg-emoji>",  "nat_sun": "<tg-emoji emoji-id='5814672393435617023'>☀️</tg-emoji>",  "nat_exp": "<tg-emoji emoji-id='5998841304052669228'>💥</tg-emoji>",   "nat_gear": "<tg-emoji emoji-id='5999047234849611002'>⚙️</tg-emoji>",
    "crit": "<tg-emoji emoji-id='5998841304052669228'>💥</tg-emoji>",  "xmark": "<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji>",  "exp_side": "<tg-emoji emoji-id='5769297434047943583'>🟣</tg-emoji>",
    "arrow_up": "<tg-emoji emoji-id='5803416753031615097'>⬆️</tg-emoji>", "arrow_down": "<tg-emoji emoji-id='5803204762035818905'>⬇️</tg-emoji>", "arrow_right": "<tg-emoji emoji-id='5802908349162851914'>➡️</tg-emoji>", "arrow_left": "<tg-emoji emoji-id='5803046350757039898'>⬅️</tg-emoji>",
}


import re as _re_pe_strip

def _pe_plain(s: str) -> str:
    """Strip all HTML tags so inner content of <tg-emoji> is always plain text."""
    return _re_pe_strip.sub(r'<[^>]+>', '', s).strip()

def pe(key: str, fallback: str | None = None) -> str:
    """Return a Telegram custom emoji HTML tag.

    Use inside messages sent with parse_mode='HTML'.
    Falls back gracefully to the plain emoji when no ID is configured.
    Inner content is always stripped to plain text to avoid nested <tg-emoji> tags.

    Example:
        text = f"{pe('trophy')} <b>Victory!</b> +{nc} NC {pe('coin')}"
        await msg.reply_text(text, parse_mode="HTML")
    """
    eid = PE.get(key, "REPLACE_ME")
    fb  = fallback or _PE_FALLBACK.get(key, "")
    if not eid or eid == "REPLACE_ME":
        return fb
    return f'<tg-emoji emoji-id="{eid}">{_pe_plain(fb)}</tg-emoji>'


def hesc(text: str) -> str:
    """Escape a string for safe insertion into an HTML Telegram message."""
    return _html.escape(str(text))

# ─── DATTEBAYO PHOTO CACHE ───────────────────────────────────────
class PhotoCache:
    API = "https://dattebayo-api.onrender.com"
    PAGE_SIZE = 20

    def __init__(self):
        self._data: dict = {}   # lowercase_name -> images[0]  (portrait)
        self._alt:  dict = {}   # lowercase_name -> images[1]  (alt/form/attack pose)
        self._loaded = False

    async def load(self):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                page = 1
                while True:
                    r = await client.get(
                        f"{self.API}/characters",
                        params={"page": page, "limit": self.PAGE_SIZE},
                        headers={"Accept": "application/json"},
                    )
                    if r.status_code != 200:
                        break
                    body = r.json()
                    chars = body.get("characters", [])
                    total = body.get("total", 0)
                    if not chars:
                        break
                    for ch in chars:
                        name = ch.get("name", "")
                        images = ch.get("images", [])
                        if name and images:
                            key = name.lower()
                            self._data[key] = images[0]
                            # Also store ASCII-normalised key: "Hyūga"→"Hyuga", "Ōtsutsuki"→"Otsutsuki"
                            norm = unicodedata.normalize('NFKD', name).encode('ascii','ignore').decode().lower()
                            if norm != key:
                                self._data[norm] = images[0]
                            if len(images) > 1:
                                self._alt[key] = images[1]
                                if norm != key:
                                    self._alt[norm] = images[1]
                    fetched = page * self.PAGE_SIZE
                    if fetched >= total:
                        break
                    page += 1
            self._loaded = True
            print(f"📸 Dattebayo photo cache: {len(self._data)} characters loaded")
            # Assign representative character photos to generic WILD enemy types.
            # These names will never appear in the Dattebayo API so we map them manually.
            _WILD_CHAR_MAP = {
                "Sand Ninja":        "Gaara",
                "Sound Ninja":       "Orochimaru",
                "Mist Assassin":     "Zabuza Momochi",
                "Stone Guardian":    "Hiruzen Sarutobi",
                "Cloud Striker":     "Killer B",
                "Rogue Jonin":       "Kakashi Hatake",
                "Akatsuki Grunt":    "Konan",
                "Rogue Jinchuriki":  "Killer B",
                "Elite ANBU":        "Itachi Uchiha",
                "Puppet Master":     "Sasori",
                "Ice Village Ninja": "Haku",
                "Explosion Corps":   "Deidara",
                "Medical Ninja":     "Tsunade",
                "Wood Shinobi":      "Yamato",
                "Lava Shinobi":      "Han",
            }
            assigned = 0
            for wild in WILDS:
                if not wild.get("photo"):
                    mapped = _WILD_CHAR_MAP.get(wild["name"])
                    if mapped:
                        p = self.get(mapped)
                        if p:
                            wild["photo"] = p
                            assigned += 1
            print(f"🖼️  Wild enemy photos assigned: {assigned}/{len(WILDS)}")
        except Exception as e:
            print(f"<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji>  Photo cache load error: {e}")

    # Known name mismatches between the bot and the Dattebayo API
    _NAME_ALIASES: dict = {
        "pain (nagato)":       "nagato",
        "pain nagato":         "nagato",
        "guy sensei":          "might guy",
        "maito gai":           "might guy",
        "kaguya otsutsuki (full power)": "kaguya otsutsuki",
        "madara (ten-tails jinchuriki)": "madara uchiha",
        "hashirama (god of shinobi)":    "hashirama senju",
        "obito (ten-tails jinchuriki)":  "obito uchiha",
        "minato (fourth hokage)":        "minato namikaze",
        "killer bee":          "killer b",
        "bee":                 "killer b",
        "third hokage":        "hiruzen sarutobi",
        "fourth hokage":       "minato namikaze",
        "fifth hokage":        "tsunade",
        "sixth hokage":        "kakashi hatake",
        "seventh hokage":      "naruto uzumaki",
    }

    # Hard-coded fallback photos — used when Dattebayo API is unavailable.
    # All URLs are stable Naruto Fandom wiki CDN images (static.wikia.nocookie.net).
    _STATIC_FALLBACKS: dict = {
        # Main cast
        "naruto uzumaki":    "https://static.wikia.nocookie.net/naruto/images/9/97/Naruto_newshot.png",
        "naruto":            "https://static.wikia.nocookie.net/naruto/images/9/97/Naruto_newshot.png",
        "sasuke uchiha":     "https://static.wikia.nocookie.net/naruto/images/2/21/Sasuke_newshot.png",
        "sasuke":            "https://static.wikia.nocookie.net/naruto/images/2/21/Sasuke_newshot.png",
        "sakura haruno":     "https://static.wikia.nocookie.net/naruto/images/3/3f/Sakura_newshot.png",
        "sakura":            "https://static.wikia.nocookie.net/naruto/images/3/3f/Sakura_newshot.png",
        "kakashi hatake":    "https://static.wikia.nocookie.net/naruto/images/2/27/Kakashi_Hatake.png",
        "kakashi":           "https://static.wikia.nocookie.net/naruto/images/2/27/Kakashi_Hatake.png",
        # Team 10
        "shikamaru nara":    "https://static.wikia.nocookie.net/naruto/images/1/10/Shikamaru_newshot.png",
        "shikamaru":         "https://static.wikia.nocookie.net/naruto/images/1/10/Shikamaru_newshot.png",
        "shikaku nara":      "https://static.wikia.nocookie.net/naruto/images/e/e3/Shikaku.png",
        "shikaku":           "https://static.wikia.nocookie.net/naruto/images/e/e3/Shikaku.png",
        "ino yamanaka":      "https://static.wikia.nocookie.net/naruto/images/f/f5/Ino_newshot.png",
        "ino":               "https://static.wikia.nocookie.net/naruto/images/f/f5/Ino_newshot.png",
        "choji akimichi":    "https://static.wikia.nocookie.net/naruto/images/f/f6/Choji_newshot.png",
        "choji":             "https://static.wikia.nocookie.net/naruto/images/f/f6/Choji_newshot.png",
        "asuma sarutobi":    "https://static.wikia.nocookie.net/naruto/images/1/13/Asuma_newshot.png",
        # Team 8
        "hinata hyuga":      "https://static.wikia.nocookie.net/naruto/images/4/46/Hinata_newshot.png",
        "hinata":            "https://static.wikia.nocookie.net/naruto/images/4/46/Hinata_newshot.png",
        "hanabi hyuga":      "https://static.wikia.nocookie.net/naruto/images/4/43/Hanabi_Hy%C5%ABga.png",
        "hanabi":            "https://static.wikia.nocookie.net/naruto/images/4/43/Hanabi_Hy%C5%ABga.png",
        "neji hyuga":        "https://static.wikia.nocookie.net/naruto/images/7/70/Neji_Hyuga.png",
        "neji":              "https://static.wikia.nocookie.net/naruto/images/7/70/Neji_Hyuga.png",
        "kiba inuzuka":      "https://static.wikia.nocookie.net/naruto/images/a/ad/Kiba_newshot.png",
        "kiba":              "https://static.wikia.nocookie.net/naruto/images/a/ad/Kiba_newshot.png",
        "shino aburame":     "https://static.wikia.nocookie.net/naruto/images/b/bf/Shino_newshot.png",
        "shino":             "https://static.wikia.nocookie.net/naruto/images/b/bf/Shino_newshot.png",
        "kurenai yuhi":      "https://static.wikia.nocookie.net/naruto/images/3/32/Kurenai_newshot.png",
        # Team Guy
        "rock lee":          "https://static.wikia.nocookie.net/naruto/images/4/4e/Rock_Lee_newshot.png",
        "tenten":            "https://static.wikia.nocookie.net/naruto/images/3/3c/TenTen_newshot.png",
        "might guy":         "https://static.wikia.nocookie.net/naruto/images/1/10/Guy_newshot.png",
        "guy":               "https://static.wikia.nocookie.net/naruto/images/1/10/Guy_newshot.png",
        # Sannin & Kage
        "jiraiya":           "https://static.wikia.nocookie.net/naruto/images/7/7f/Jiraiya_newshot.png",
        "tsunade":           "https://static.wikia.nocookie.net/naruto/images/7/7b/Tsunade_newshot.png",
        "orochimaru":        "https://static.wikia.nocookie.net/naruto/images/0/09/Orochimaru_newshot.png",
        "hiruzen sarutobi":  "https://static.wikia.nocookie.net/naruto/images/4/49/Hiruzen_newshot.png",
        "minato namikaze":   "https://static.wikia.nocookie.net/naruto/images/5/56/Minato_newshot.png",
        "minato":            "https://static.wikia.nocookie.net/naruto/images/5/56/Minato_newshot.png",
        "hashirama senju":   "https://static.wikia.nocookie.net/naruto/images/c/c8/Hashirama_newshot.png",
        "hashirama":         "https://static.wikia.nocookie.net/naruto/images/c/c8/Hashirama_newshot.png",
        "tobirama senju":    "https://static.wikia.nocookie.net/naruto/images/7/72/Tobirama_newshot.png",
        "tobirama":          "https://static.wikia.nocookie.net/naruto/images/7/72/Tobirama_newshot.png",
        # Akatsuki
        "itachi uchiha":     "https://static.wikia.nocookie.net/naruto/images/b/bb/Itachi_newshot.png",
        "itachi":            "https://static.wikia.nocookie.net/naruto/images/b/bb/Itachi_newshot.png",
        "pain":              "https://static.wikia.nocookie.net/naruto/images/2/22/Nagato2.png",
        "nagato":            "https://static.wikia.nocookie.net/naruto/images/2/22/Nagato2.png",
        "konan":             "https://static.wikia.nocookie.net/naruto/images/b/b0/Konan_newshot.png",
        "kisame hoshigaki":  "https://static.wikia.nocookie.net/naruto/images/b/b8/Kisame_newshot.png",
        "kisame":            "https://static.wikia.nocookie.net/naruto/images/b/b8/Kisame_newshot.png",
        "deidara":           "https://static.wikia.nocookie.net/naruto/images/a/aa/Deidara_newshot.png",
        "sasori":            "https://static.wikia.nocookie.net/naruto/images/0/0c/Sasori_newshot.png",
        "hidan":             "https://static.wikia.nocookie.net/naruto/images/a/af/Hidan_newshot.png",
        "kakuzu":            "https://static.wikia.nocookie.net/naruto/images/8/82/Kakuzu_newshot.png",
        "zetsu":             "https://static.wikia.nocookie.net/naruto/images/2/2e/Zetsu_newshot.png",
        "obito uchiha":      "https://static.wikia.nocookie.net/naruto/images/d/df/Obito_newshot.png",
        "tobi":              "https://static.wikia.nocookie.net/naruto/images/d/df/Obito_newshot.png",
        "madara uchiha":     "https://static.wikia.nocookie.net/naruto/images/9/9a/Madara_newshot.png",
        "madara":            "https://static.wikia.nocookie.net/naruto/images/9/9a/Madara_newshot.png",
        "kaguya otsutsuki":  "https://static.wikia.nocookie.net/naruto/images/3/33/Kaguya_Newshot.png",
        "kaguya":            "https://static.wikia.nocookie.net/naruto/images/3/33/Kaguya_Newshot.png",
        # Other popular chars
        "gaara":             "https://static.wikia.nocookie.net/naruto/images/c/c5/Gaara_newshot.png",
        "temari":            "https://static.wikia.nocookie.net/naruto/images/e/e8/Temari_newshot.png",
        "kankuro":           "https://static.wikia.nocookie.net/naruto/images/3/30/Kankuro_newshot.png",
        "killer b":          "https://static.wikia.nocookie.net/naruto/images/6/60/Killer_B_newshot.png",
        "killer bee":        "https://static.wikia.nocookie.net/naruto/images/6/60/Killer_B_newshot.png",
        "bee":               "https://static.wikia.nocookie.net/naruto/images/6/60/Killer_B_newshot.png",
        "zabuza momochi":    "https://static.wikia.nocookie.net/naruto/images/a/a9/Zabuza_newshot.png",
        "zabuza":            "https://static.wikia.nocookie.net/naruto/images/a/a9/Zabuza_newshot.png",
        "haku":              "https://static.wikia.nocookie.net/naruto/images/5/50/Haku_newshot.png",
        "kabuto yakushi":    "https://static.wikia.nocookie.net/naruto/images/e/e9/Kabuto_newshot.png",
        "kabuto":            "https://static.wikia.nocookie.net/naruto/images/e/e9/Kabuto_newshot.png",
        "sai":               "https://static.wikia.nocookie.net/naruto/images/e/e3/Sai_newshot.png",
        "yamato":            "https://static.wikia.nocookie.net/naruto/images/e/eb/Yamato_newshot.png",
        "shizune":           "https://static.wikia.nocookie.net/naruto/images/5/5f/Shizune_newshot.png",
        "anko mitarashi":    "https://static.wikia.nocookie.net/naruto/images/9/97/Anko_newshot.png",
        "konohamaru sarutobi": "https://static.wikia.nocookie.net/naruto/images/f/f8/Konohamaru_newshot.png",
        "konohamaru":        "https://static.wikia.nocookie.net/naruto/images/f/f8/Konohamaru_newshot.png",
        "izumo kamizuki":    "https://static.wikia.nocookie.net/naruto/images/6/60/Izumo_newshot.png",
        "kotetsu hagane":    "https://static.wikia.nocookie.net/naruto/images/3/3f/Kotetsu_newshot.png",
        "iruka umino":       "https://static.wikia.nocookie.net/naruto/images/4/47/Iruka_newshot.png",
        "iruka":             "https://static.wikia.nocookie.net/naruto/images/4/47/Iruka_newshot.png",
        "fugaku uchiha":     "https://static.wikia.nocookie.net/naruto/images/c/c3/Fugaku_newshot.png",
        "fugaku":            "https://static.wikia.nocookie.net/naruto/images/c/c3/Fugaku_newshot.png",
        "mikoto uchiha":     "https://static.wikia.nocookie.net/naruto/images/8/8b/Mikoto_Uchiha.png",
        "kushina uzumaki":   "https://static.wikia.nocookie.net/naruto/images/0/0d/Kushina_newshot.png",
        "kushina":           "https://static.wikia.nocookie.net/naruto/images/0/0d/Kushina_newshot.png",
        "han":               "https://static.wikia.nocookie.net/naruto/images/3/3b/Han_newshot.png",
    }

    # Words that are modifiers/adjectives prepended to real character names.
    # Stripping these lets "Young Shino" → "Shino", "Old Man Third" → "Third", etc.
    _MODIFIER_WORDS = {
        "young","old","elder","teen","child","adult","part","early","late",
        "reanimated","edo","masked","true","real","base","final","perfect",
        "great","mini","dark","fake","ghost","sage","sand","earth","fire",
        "wind","water","lightning","ice","lava","wood","explosion","puppet",
        "medical","yin","yang","light","shadow","ninja","shinobi","jonin",
        "genin","chunin","anbu","rogue","wild","mist","stone","cloud","sound",
        "leaf","konoha","hidden",
    }

    def get(self, name: str) -> str | None:
        # NOTE: do NOT bail early when _data is empty — static fallbacks must
        # still be reachable when the Dattebayo API cache hasn't loaded yet.
        key = name.lower()
        # 0. Apply known aliases (Pain (Nagato) → nagato, etc.)
        key = self._NAME_ALIASES.get(key, key)
        # 0b. Also try ASCII-normalised key in aliases
        norm_key = unicodedata.normalize('NFKD', key).encode('ascii','ignore').decode()
        if norm_key != key:
            key = self._NAME_ALIASES.get(norm_key, key)
        # 1. Exact match
        if key in self._data:
            return self._data[key]
        # 2. Strip parenthetical modifier: "Naruto (Baryon Mode)" → "naruto"
        base = re.sub(r'\s*\([^)]*\)', '', key).strip()
        if base and base in self._data:
            return self._data[base]
        # 3. API name starts with our base
        for k, v in self._data.items():
            if base and len(base) >= 3 and k.startswith(base):
                return v
        # 4. Our base is contained in an API name
        for k, v in self._data.items():
            if base and len(base) > 4 and base in k:
                return v
        # 5. Strip leading modifier words to get the core name
        #    e.g. "Young Shino" → "shino", "Reanimated Minato" → "minato"
        base_words = base.split()
        core_words = [w for w in base_words if w not in self._MODIFIER_WORDS]
        core = " ".join(core_words).strip()
        if core and core != base:
            if core in self._data:
                return self._data[core]
            for k, v in self._data.items():
                if len(core) >= 3 and k.startswith(core):
                    return v
            for k, v in self._data.items():
                if len(core) > 4 and core in k:
                    return v
        # 6. Try the content inside parentheses as a name
        paren_match = re.search(r'\(([^)]+)\)', key)
        if paren_match:
            inner = paren_match.group(1).strip()
            if inner in self._data:
                return self._data[inner]
            for word in inner.split():
                if len(word) >= 4:
                    for k, v in self._data.items():
                        if k.startswith(word) or word in k:
                            return v
        # 7. Try EVERY meaningful word in the name as a substring search.
        #    "Young Shino" → "shino" matches "shino aburame".
        #    "Kotetsu Hagane" → "kotetsu" matches "kotetsu hagane".
        all_words = base_words if base_words else key.split()
        for word in all_words:
            if len(word) >= 4 and word not in self._MODIFIER_WORDS:
                for k, v in self._data.items():
                    if word in k:
                        return v
        # 8. Static fallback for chars not in Dattebayo API
        orig_key = name.lower()
        if orig_key in self._STATIC_FALLBACKS:
            return self._STATIC_FALLBACKS[orig_key]
        for fb_key, fb_url in self._STATIC_FALLBACKS.items():
            if fb_key in orig_key or orig_key in fb_key:
                return fb_url
        return None

    def get_alt(self, name: str) -> str | None:
        """Return alt image (images[1] — action/form pose) if available, else images[0].
        For form names like 'Naruto (Baryon Mode)' this returns Naruto's images[1],
        which is typically a different art/form compared to the default portrait.
        """
        # NOTE: do NOT bail early when _data is empty — fall through to get() which
        # checks static fallbacks even when the Dattebayo API cache hasn't loaded.
        key = name.lower()
        # Apply known aliases
        key = self._NAME_ALIASES.get(key, key)
        norm_key = unicodedata.normalize('NFKD', key).encode('ascii','ignore').decode()
        if norm_key != key:
            key = self._NAME_ALIASES.get(norm_key, key)
        # Strip parenthetical form modifier to find the base character
        base = re.sub(r'\s*\([^)]*\)', '', key).strip()
        # Try alt image for exact base name
        if base and base in self._alt:
            return self._alt[base]
        # Try alt via prefix match (e.g. "naruto" → "naruto uzumaki")
        for k, v in self._alt.items():
            if base and len(base) >= 3 and k.startswith(base):
                return v
        # Try alt via each meaningful word
        base_words = [w for w in base.split() if w not in self._MODIFIER_WORDS]
        for word in base_words:
            if len(word) >= 4:
                for k, v in self._alt.items():
                    if word in k:
                        return v
        # Fall back to normal portrait (includes static fallbacks)
        return self.get(name)

PHOTO_CACHE = PhotoCache()

# ─── JUTSU IMAGE CACHE ──────────────────────────────────────────
class JutsuCache:
    """Maps jutsu/technique name → Wikia image URL (from Dattebayo API)."""
    API = "https://dattebayo-api.onrender.com"
    PAGE_SIZE = 20

    def __init__(self):
        self._data: dict = {}   # lowercase_jutsu_name -> image_url
        self._loaded = False

    async def load(self):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                page = 1
                while True:
                    r = await client.get(
                        f"{self.API}/characters",
                        params={"page": page, "limit": self.PAGE_SIZE},
                        headers={"Accept": "application/json"},
                    )
                    if r.status_code != 200:
                        break
                    body = r.json()
                    chars = body.get("characters", [])
                    total = body.get("total", 0)
                    if not chars:
                        break
                    for ch in chars:
                        images = ch.get("images", [])
                        if not images:
                            continue
                        # Prefer images[1] for jutsu flash — it is usually a
                        # different pose / form art, making attacks look distinct
                        img = images[1] if len(images) > 1 else images[0]
                        for jutsu_name in ch.get("jutsu", []):
                            key = jutsu_name.lower().strip()
                            if key and key not in self._data:
                                self._data[key] = img
                    if page * self.PAGE_SIZE >= total:
                        break
                    page += 1
            self._loaded = True
            print(f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> Jutsu cache: {len(self._data)} techniques mapped")
        except Exception as e:
            print(f"<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji>  Jutsu cache load error: {e}")

    def get(self, jutsu_name: str, fallback: str | None = None) -> str | None:
        if not self._data:
            return fallback
        key = jutsu_name.lower().strip()
        if key in self._data:
            return self._data[key]
        # Partial match: check if query is contained in any jutsu key
        for k, v in self._data.items():
            if key and len(key) > 4 and (key in k or k in key):
                return v
        return fallback

JUTSU_CACHE = JutsuCache()

# ─── MOVE IMAGE CACHE (Naruto Fandom MediaWiki) ─────────────────
class MoveImageCache:
    """Fetches jutsu images from Naruto Fandom MediaWiki API — free, no key needed."""
    WIKI_API   = "https://naruto.fandom.com/api.php"
    THUMB_SIZE = 400

    # Maps bot move display name (lowercase) → Naruto wiki page title
    MOVE_MAP: dict = {
        "rasengan":                       "Rasengan",
        "wind rasenshuriken":             "Wind Release: Rasenshuriken",
        "sage rasenshuriken":             "Wind Release: Rasenshuriken",
        "rasenshuriken sage":             "Wind Release: Rasenshuriken",
        "tailed beast bomb":              "Tailed Beast Ball",
        "flying thunder god":             "Flying Thunder God Technique",
        "baryon mode strike":             "Baryon Mode",
        "clone barrage":                  "Shadow Clone Technique",
        "shadow clone jutsu":             "Shadow Clone Technique",
        "vacuum sphere":                  "Wind Release: Vacuum Sphere",
        "chidori":                        "Chidori",
        "kirin":                          "Kirin",
        "raikiri":                        "Chidori",
        "black lightning":                "Black Lightning",
        "lariat":                         "Lightning Release: Lariat",
        "double lariat":                  "Lightning Release: Double Lariat",
        "chidori senbon":                 "Chidori Senbon",
        "indra's arrow":                  "Indra's Arrow",
        "great fireball":                 "Fire Release: Great Fireball Technique",
        "amaterasu":                      "Amaterasu",
        "phoenix flower":                 "Fire Release: Phoenix Sage Fire Technique",
        "dragon flame jutsu":             "Fire Release: Dragon Fire Technique",
        "ash pile burning":               "Ash Pile Burning",
        "perfect susanoo":                "Susanoo",
        "dust release detach":            "Dust Release: Detachment of the Primitive World Technique",
        "dance of camellia":              "Dance of the Camellia",
        "dance of the larch":             "Dance of the Larch",
        "dance of clematis":              "Dance of the Clematis: Vine",
        "bracken dance":                  "Dance of the Bracken Fern",
        "water dragon bullet":            "Water Release: Water Dragon Bullet Technique",
        "exploding water":                "Water Release: Exploding Water Colliding Wave",
        "hidden mist jutsu":              "Hidden Mist Technique",
        "water fang bullet":              "Water Release: Water Fang Bullet",
        "paper bomb sea":                 "Paper Person of God Technique",
        "sand coffin":                    "Sand Binding Coffin",
        "sand burial":                    "Sand Binding Funeral",
        "sand storm":                     "Sand Binding Coffin",
        "iron sand drizzle":              "Iron Sand World Method",
        "shukaku sphere":                 "Tailed Beast Ball",
        "desert requiem":                 "Sand Waterfall Funeral",
        "shadow bind jutsu":              "Shadow Imitation Technique",
        "shadow sewing":                  "Shadow Sewing Technique",
        "shadow king strangling":         "Shadow Imitation Technique",
        "tsukuyomi":                      "Tsukuyomi",
        "totsuka blade":                  "Sword of Totsuka",
        "izanagi":                        "Izanagi",
        "kotoamatsukami":                 "Kotoamatsukami",
        "izanami":                        "Izanami",
        "almighty push":                  "Shinra Tensei",
        "planetary devastation":          "Chibaku Tensei",
        "shinra tensei":                  "Shinra Tensei",
        "gedo chains":                    "Chains of the Outer Path",
        "gedo statue":                    "Demonic Statue of the Outer Path",
        "chibaku tensei":                 "Chibaku Tensei",
        "six paths sage":                 "Six Paths Sage Mode",
        "truth-seeking balls":            "Truth-Seeking Ball",
        "gedo art of rinbo":              "Limbo: Border Jail",
        "tengai shinsei":                 "Tengai Shinsei",
        "infinite tsukuyomi":             "Infinite Tsukuyomi",
        "leaf hurricane":                 "Leaf Hurricane",
        "primary lotus":                  "Primary Lotus",
        "hidden lotus":                   "Reverse Lotus",
        "evening elephant":               "Evening Elephant",
        "night guy":                      "Night Guy",
        "dynamic entry":                  "Dynamic Entry",
        "eight trigrams 64 palms":        "Eight Trigrams Sixty-Four Palms",
        "eight trigrams rotation":        "Eight Trigrams Palms Revolving Heaven",
        "twin lion fists":                "Twin Lion Fists",
        "wood dragon jutsu":              "Wood Release Secret Technique: Nativity of a World of Trees",
        "thousand-hand buddha":           "Sage Art Wood Release: True Several Thousand Hands",
        "wood spike wall":                "Wood Release: Smothering Binding Technique",
        "advent of world flowers":        "Wood Release: Serial Pillar Houses Jutsu",
        "wood clone jutsu":               "Wood Clone Technique",
        "mystical palm":                  "Mystical Palm Technique",
        "strength of a hundred":          "Strength of a Hundred Technique",
        "monster strength punch":         "Cherry Blossom Impact",
        "c1 clay birds":                  "C1",
        "c2 dragon":                      "C2",
        "c3 massive bomb":                "C3",
        "c4 karura":                      "C4 Karura",
        "c0 ultimate art":                "C0",
        "lava style melting":             "Lava Release: Melting Apparition Technique",
        "lava style golem":               "Lava Release: Scorching Rock Golem Technique",
        "ice style dome prison":          "Ice Release: Ice Prison Technique",
        "crystal ice mirrors":            "Ice Release: Crystal-Ice Mirrors",
        "storm release shark":            "Storm Release: Thunder Cloud Inner Wave",
        "eight branches":                 "Eight Branches Technique",
        "kusanagi sword":                 "Kusanagi Sword: Long Sword of the Sky",
        "fang over fang":                 "Fang Passing Fang",
        "sage mode strike":               "Sage Mode",
        "summoning gamabunta":            "Summoning Technique",
        "summoning manda":                "Summoning Technique",
        "gentle fist strike":             "Gentle Fist",
        "earth spear":                    "Earth Release: Earth Spear",
        "scorpion tail":                  "Puppet: Savage Blade",
        "hundred puppet army":            "One Hundred Puppet Army",
        "sealing jutsu":                  "Sealing Technique: Phantom Dragons Nine Consuming Seals",
        "poison gas bomb":                "Poison Cloud Technique",
        "insect swarm":                   "Insect Gathering Technique",
        "paper shuriken":                 "Paper Shuriken",
        "super beast scroll":             "Super Beast Imitating Drawing",
        "butterfly bomb":                 "Butterfly Mode",
        "chakra chains":                  "Adamantine Sealing Chains",
    }

    def __init__(self):
        self._data: dict = {}
        self._loaded = False

    async def load(self):
        try:
            import httpx
            unique_pages = list(set(self.MOVE_MAP.values()))
            page_to_img: dict = {}
            BATCH = 10
            async with httpx.AsyncClient(timeout=40, follow_redirects=True) as client:
                for i in range(0, len(unique_pages), BATCH):
                    batch = unique_pages[i:i + BATCH]
                    r = await client.get(self.WIKI_API, params={
                        "action":      "query",
                        "titles":      "|".join(batch),
                        "prop":        "pageimages",
                        "format":      "json",
                        "pithumbsize": self.THUMB_SIZE,
                        "pilicense":   "any",
                    })
                    if r.status_code != 200:
                        continue
                    pages = r.json().get("query", {}).get("pages", {})
                    for pid, page_data in pages.items():
                        if pid == "-1":
                            continue
                        title = page_data.get("title", "")
                        url   = page_data.get("thumbnail", {}).get("source", "")
                        if title and url:
                            page_to_img[title] = url
            for move_lower, wiki_title in self.MOVE_MAP.items():
                url = page_to_img.get(wiki_title)
                if url:
                    self._data[move_lower] = url
            self._loaded = True
            print(f"<tg-emoji emoji-id='5427397421443325675'>🎯</tg-emoji> Move image cache: {len(self._data)}/{len(self.MOVE_MAP)} jutsu images loaded")
        except Exception as e:
            print(f"<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji>  Move image cache load error: {e}")

    def get(self, move_display_name: str) -> str | None:
        if not self._data:
            return None
        return self._data.get(move_display_name.lower().strip())

MOVE_IMAGE_CACHE = MoveImageCache()

# ─── BEST PHOTO HELPER ──────────────────────────────────────────
def best_char_photo(char_name: str) -> str | None:
    """Return the best available photo for a character.
    For form characters like 'Naruto (Baryon Mode)', tries to return
    a form-specific image from the wiki, then falls back to alt/portrait.
    """
    paren = re.search(r'\(([^)]+)\)', char_name)
    if paren:
        form_name = paren.group(1).lower()
        # Direct MOVE_IMAGE_CACHE lookup on form name
        form_img = MOVE_IMAGE_CACHE.get(form_name)
        if form_img:
            return form_img
        # Partial match inside MOVE_IMAGE_CACHE (e.g. "baryon mode" in "baryon mode strike")
        for k, v in MOVE_IMAGE_CACHE._data.items():
            if form_name in k or k in form_name:
                return v
        # Alt image (different art from portrait)
        return PHOTO_CACHE.get_alt(char_name)
    return PHOTO_CACHE.get(char_name)

def get_form_photo(char_name: str, form_name: str) -> str | None:
    """Return the best photo specifically for a transformed form.
    Priority: wiki image for form name → alt pose of char → normal portrait.
    E.g. char='Naruto', form='Baryon Mode' → tries 'Baryon Mode' in wiki cache.
    """
    fn = form_name.lower().strip()
    # 1. Direct wiki image for the form name
    img = MOVE_IMAGE_CACHE.get(fn)
    if img:
        return img
    # 2. Partial match (e.g. "baryon mode" matches "baryon mode strike" key)
    for k, v in MOVE_IMAGE_CACHE._data.items():
        if fn and (fn in k or k in fn):
            return v
    # 3. Try as if the char name has parens: "Naruto (Baryon Mode)"
    combined = f"{char_name} ({form_name})"
    img = PHOTO_CACHE.get_alt(combined)
    if img:
        return img
    # 4. Alt pose of the character (usually a powered-up art)
    img = PHOTO_CACHE.get_alt(char_name)
    if img:
        return img
    # 5. Normal portrait as last resort
    return PHOTO_CACHE.get(char_name)

# ─── NATURE EMOJI ───────────────────────────────────────────────
NAT_EMO = {
    "Fire":"🔥","Wind":"💨","Lightning":"⚡","Earth":"🪨","Water":"💧",
    "Yin":"🌑","Yang":"☀️","Yin-Yang":"🌓","Taijutsu":"👊","Medical":"💊",
    "Explosion":"💥","Wood":"🌲","Sand":"🌪️","Lava":"🌋","Scorch":"🌡️",
    "Ice":"❄️","Poison":"☠️","Metal":"⚙️","Ghost":"👻","Puppet":"🪆",
    "Storm":"⛈️",
}

# ─── NATURE CHART ───────────────────────────────────────────────
ADV = {
    "Fire":      {"s":["Wind","Wood","Ice"],          "w":["Water","Sand","Earth"]},
    "Wind":      {"s":["Lightning","Sand","Scorch"],   "w":["Fire","Water"]},
    "Lightning": {"s":["Water","Earth","Metal"],       "w":["Wind","Sand"]},
    "Earth":     {"s":["Fire","Lightning","Poison"],   "w":["Water","Wood","Explosion"]},
    "Water":     {"s":["Fire","Earth","Sand","Lava"],  "w":["Lightning","Wind"]},
    "Yin":       {"s":["Yang","Medical","Ghost"],      "w":["Yin-Yang"]},
    "Yang":      {"s":["Yin-Yang","Taijutsu"],         "w":["Yin"]},
    "Yin-Yang":  {"s":["Yin","Yang"],                  "w":[]},
    "Taijutsu":  {"s":["Earth","Sand","Puppet"],       "w":["Yang","Medical"]},
    "Medical":   {"s":["Yin","Taijutsu","Poison"],     "w":["Fire","Lightning"]},
    "Explosion": {"s":["Earth","Wood","Sand","Ice"],   "w":["Water","Wind"]},
    "Wood":      {"s":["Water","Earth","Sand"],        "w":["Fire","Explosion","Scorch"]},
    "Sand":      {"s":["Wind","Lightning"],            "w":["Water","Wood","Earth"]},
    "Lava":      {"s":["Wood","Ice","Earth"],          "w":["Water","Wind"]},
    "Scorch":    {"s":["Wood","Ice"],                  "w":["Water","Wind"]},
    "Ice":       {"s":["Water","Wind"],                "w":["Fire","Lava","Scorch"]},
    "Poison":    {"s":["Medical","Taijutsu"],           "w":["Earth","Explosion"]},
    "Metal":     {"s":["Earth","Sand"],                "w":["Lightning","Fire"]},
    "Ghost":     {"s":["Taijutsu","Earth"],             "w":["Yin","Yang"]},
    "Puppet":    {"s":["Taijutsu","Wind"],              "w":["Fire","Lightning"]},
    "Storm":     {"s":["Earth","Sand"],                "w":["Lightning","Wind"]},
}
ALL_NATURES = list(ADV.keys())

def type_mult(atk_n, def_n):
    info = ADV.get(atk_n, {})
    if def_n in info.get("s",[]): return 1.5
    if def_n in info.get("w",[]): return 0.75
    return 1.0

def eff_text(mult):
    if mult >= 1.5: return "<tg-emoji emoji-id='5803416753031615097'>⬆️</tg-emoji> SUPER EFFECTIVE"
    if mult <= 0.75: return "<tg-emoji emoji-id='5803204762035818905'>⬇️</tg-emoji> not very effective"
    return "<tg-emoji emoji-id='5802908349162851914'>➡️</tg-emoji> normal"

# ─── KEKKEI GENKAI ──────────────────────────────────────────────
KG = {
    "Sharingan":           {"crit":20,"acc":10,"desc":"Copy moves · +20% crit · +10% acc"},
    "Mangekyou Sharingan": {"crit":30,"acc":15,"desc":"Amaterasu+Tsukuyomi · +30% crit · ignore 15% def"},
    "Rinnegan":            {"chakra_reduce":0.30,"all_stats":0.10,"desc":"30% chakra reduction · +10% all stats"},
    "Byakugan":            {"acc":25,"pierce":0.15,"desc":"+25% accuracy · pierce 15% defense"},
    "Tenseigan":           {"acc":20,"crit":15,"desc":"+20% acc · +15% crit · Gentle Fist"},
    "Wood Release":        {"regen":0.08,"desc":"Regen 8% max HP each turn"},
    "Magnet Release":      {"reflect":0.15,"desc":"Reflect 15% damage received back"},
    "Lava Release":        {"type_bonus":{"Fire":0.25,"Earth":0.20},"desc":"+25% Fire · +20% Earth"},
    "Storm Release":       {"aoe":True,"acc":10,"desc":"All attacks splash · +10% acc"},
    "Explosion Release":   {"type_bonus":{"Explosion":0.30},"pierce_def":0.20,"desc":"+30% Explosion · ignore 20% def"},
    "Bone Release":        {"def_bonus":15,"no_crit":True,"desc":"+15% DEF · immune to crits"},
    "Scorch Release":      {"dot":"scorch","desc":"Every hit applies Scorch DoT"},
    "Puppet Jutsu":        {"stun_immune":True,"def_bonus":10,"desc":"Immune to stun · +10% DEF"},
    "Sand Armor":          {"shield":0.15,"desc":"Auto-shield 15% max HP each battle"},
    "Medical Ninjutsu":    {"regen":0.12,"revive":True,"desc":"Regen 12% HP/turn · one revive"},
    "Space-Time":          {"speed":30,"dodge_chance":15,"desc":"+30 SPD · 15% dodge chance"},
    "Ice Release":         {"type_bonus":{"Ice":0.25,"Water":0.15},"desc":"+25% Ice · +15% Water"},
    "Swift Release":       {"speed":25,"crit":10,"desc":"+25 SPD · +10% crit"},
    "Boil Release":        {"dot":"burn","type_bonus":{"Water":0.20},"desc":"Attacks inflict Burn · +20% Water"},
    "Karma Seal":          {"all_stats":0.15,"crit":15,"desc":"+15% all stats · +15% crit · Otsutsuki power"},
    "None":                {"all_stats":0.05,"desc":"+5% all base stats"},
}

CLAN_KG = {
    "Uchiha":"Sharingan","Senju":"Wood Release","Hyuga":"Byakugan",
    "Uzumaki":"None","Nara":"None","Akimichi":"None","Yamanaka":"None",
    "Sarutobi":"None","Hatake":"Sharingan","Namikaze":"Space-Time",
    "Subaku":"Sand Armor","Kaguya":"Bone Release","Terumi":"Lava Release",
    "Hozuki":"None","Hidan":"None","Kakuzu":"None","Deidara":"Explosion Release",
    "Sasori":"Puppet Jutsu","Konan":"None","Aburame":"None",
    "Otsutsuki":"Rinnegan","Yuki":"Ice Release","Momochi":"None",
    "Inuzuka":"None","Lee":"None","Haruno":"Medical Ninjutsu",
    "Darui":"Storm Release","Pakura":"Scorch Release","Rasa":"Magnet Release",
    "Tsutsuki":"Tenseigan","Orochimaru":"None","Zetsu":"None",
    "Shimura":"None","Morino":"None","Kamizuki":"None","Gekko":"None",
    "Namiashi":"None","Shiranui":"None","Mitarashi":"None","Yuhi":"None",
    "Nohara":"Medical Ninjutsu","Kato":"None","Ukki":"None",
    "Hoshigaki":"None","Munashi":"Magnet Release","Kuriarare":"None",
    "Ringo":"None","Akebino":"None","Suikazan":"None","Hoshigaki":"None",
    "Kurosuki":"None","Nii":"None","Kakei":"None",
}

# ─── VILLAGES ───────────────────────────────────────────────────
VILLAGES = {
    "Konoha":  {"desc":"Village Hidden in the Leaves","exp":0.15,"chakra":0.10,"emoji":"🍃"},
    "Suna":    {"desc":"Village Hidden in the Sand","def":0.12,"spd":0.05,"emoji":"🌵"},
    "Kiri":    {"desc":"Village Hidden in the Mist","crit":0.12,"atk":0.05,"emoji":"🌊"},
    "Kumo":    {"desc":"Village Hidden in the Clouds","spd":0.15,"lightning":0.10,"emoji":"⚡"},
    "Iwa":     {"desc":"Village Hidden in the Stone","hp":0.15,"def":0.08,"emoji":"🪨"},
    "Oto":     {"desc":"Village Hidden in the Sound","atk":0.12,"yin":0.10,"emoji":"🎵"},
    "Akatsuki":{"desc":"Criminal Organization","atk":0.20,"def":-0.05,"emoji":"🔴"},
    "Wanderer":{"desc":"No affiliation — free spirit","all":0.05,"emoji":"🌍"},
}

# Full display names + country for /village menu
VILLAGE_INFO = {
    "Konoha":  {"full":"Hidden Leaf Village",  "country":"Land of Fire 🔥",        "kage":"Hokage"},
    "Suna":    {"full":"Hidden Sand Village",  "country":"Land of Wind 💨",         "kage":"Kazekage"},
    "Kiri":    {"full":"Hidden Mist Village",  "country":"Land of Water 💧",        "kage":"Mizukage"},
    "Kumo":    {"full":"Hidden Cloud Village", "country":"Land of Lightning ⚡",    "kage":"Raikage"},
    "Iwa":     {"full":"Hidden Stone Village", "country":"Land of Earth 🪨",        "kage":"Tsuchikage"},
    "Oto":     {"full":"Hidden Sound Village", "country":"Land of Sound 🎵",        "kage":"Otokage"},
    "Akatsuki":{"full":"Akatsuki",             "country":"Wandering 🌑",            "kage":"Leader (Pain)"},
    "Wanderer":{"full":"No Affiliation",       "country":"Anywhere 🌍",             "kage":"None"},
}

# ─── VILLAGE AREAS (for /travel) ────────────────────────────────
VILLAGE_AREAS = {
    "Konoha": [
        {"name":"Training Grounds","emoji":"🌳","desc":"The iconic Team 7 training field. Encounter genin sparring sessions.","bonus":"exp","bonus_val":0.15},
        {"name":"Forest of Death","emoji":"🌲","desc":"The second exam forest — dense and dangerous. High-level enemies lurk here.","bonus":"nc","bonus_val":0.20},
        {"name":"Hokage Rock","emoji":"🗿","desc":"The iconic carved cliffside overlooking Konoha. Gain wisdom and chakra.","bonus":"chakra","bonus_val":0.25},
        {"name":"Konoha Academy","emoji":"🏫","desc":"Where future shinobi are born. Train with students and chunin instructors.","bonus":"exp","bonus_val":0.10},
        {"name":"Ichiraku Ramen","emoji":"🍜","desc":"Naruto's favourite spot! Eat well and restore HP before battle.","bonus":"heal","bonus_val":1.0},
        {"name":"Konoha Market","emoji":"🛒","desc":"Busy civilian district. Find rare items and NC from merchants.","bonus":"nc","bonus_val":0.10},
        {"name":"Hot Springs","emoji":"♨️","desc":"Relax in Konoha's famous hot springs. Recover chakra and stamina.","bonus":"chakra","bonus_val":0.20},
        {"name":"ANBU HQ","emoji":"🎭","desc":"The secret base of the ANBU Black Ops. Elite enemy encounters.","bonus":"nc","bonus_val":0.30},
        {"name":"Uchiha District","emoji":"🔥","desc":"The historic Uchiha compound. Sharingan users train here.","bonus":"exp","bonus_val":0.25},
        {"name":"Hyuga Compound","emoji":"👁️","desc":"The noble Hyuga clan estate. Gentle Fist masters guard this place.","bonus":"exp","bonus_val":0.20},
    ],
    "Suna": [
        {"name":"Desert Training Grounds","emoji":"🏜️","desc":"Scorching sands where Suna shinobi hone their wind and sand arts.","bonus":"exp","bonus_val":0.15},
        {"name":"Wind Valley","emoji":"💨","desc":"Howling desert winds test your speed and reflexes.","bonus":"nc","bonus_val":0.20},
        {"name":"Kazekage Tower","emoji":"🏰","desc":"The seat of Suna power. Face the Kazekage's elite guards.","bonus":"nc","bonus_val":0.30},
        {"name":"Puppet Workshop","emoji":"🪆","desc":"Sasori's legacy lives on. Master puppeteers craft and duel here.","bonus":"exp","bonus_val":0.20},
        {"name":"Sand Dunes","emoji":"🌵","desc":"Endless golden dunes. Wild sand-ninja and desert beasts roam free.","bonus":"nc","bonus_val":0.15},
        {"name":"Suna Market","emoji":"🏪","desc":"Trading post at the desert crossroads. Rare goods and bounties.","bonus":"nc","bonus_val":0.10},
        {"name":"Iron Sand Forge","emoji":"⚙️","desc":"Where Iron Sand weapons are forged. High temp combat training.","bonus":"exp","bonus_val":0.25},
        {"name":"Desert Prison","emoji":"⛓️","desc":"Suna's high-security lockup. Encounter criminal ninja escapees.","bonus":"nc","bonus_val":0.25},
    ],
    "Kiri": [
        {"name":"Mist Training Grounds","emoji":"🌊","desc":"Visibility zero. Silent killing masters train in eternal mist.","bonus":"exp","bonus_val":0.20},
        {"name":"Blood Swamp","emoji":"🩸","desc":"The dreaded killing fields of Kiri. Only the strong survive.","bonus":"nc","bonus_val":0.30},
        {"name":"Mizukage Tower","emoji":"🏯","desc":"Command centre of the Mist. Face the Mizukage's personal guard.","bonus":"nc","bonus_val":0.35},
        {"name":"Sword Collection Hall","emoji":"⚔️","desc":"Home of the Seven Ninja Swordsmen blades. Legendary encounters.","bonus":"exp","bonus_val":0.30},
        {"name":"Harbor District","emoji":"⛵","desc":"Kiri's foggy port. Smugglers and rogue ninja frequent these docks.","bonus":"nc","bonus_val":0.15},
        {"name":"Hidden Grotto","emoji":"🌀","desc":"A secret cave beneath Kiri. Rare chakra ore and wild beasts.","bonus":"chakra","bonus_val":0.30},
        {"name":"Bubble Island","emoji":"🫧","desc":"Saiken's territory — acid bubbles and mist beasts everywhere.","bonus":"nc","bonus_val":0.20},
    ],
    "Kumo": [
        {"name":"Lightning Temple","emoji":"⛩️","desc":"Sacred grounds where lightning-nature masters meditate and spar.","bonus":"exp","bonus_val":0.20},
        {"name":"Cloud Peak","emoji":"🏔️","desc":"The highest point in Kumo. Raikage-level winds and enemies.","bonus":"nc","bonus_val":0.25},
        {"name":"Raikage Building","emoji":"🏢","desc":"The Raikage's fortress. Confront A's most powerful retainers.","bonus":"nc","bonus_val":0.30},
        {"name":"Thunder Plains","emoji":"⚡","desc":"Open highlands struck by constant lightning. Speed battles only.","bonus":"exp","bonus_val":0.25},
        {"name":"Kumo Market","emoji":"🏪","desc":"Cloud village trade hub. NC flows freely between shinobi.","bonus":"nc","bonus_val":0.10},
        {"name":"Killer Bee's Studio","emoji":"🎤","desc":"The Eight-Tails jinchuriki's rap training room. Chaotic and powerful.","bonus":"chakra","bonus_val":0.25},
        {"name":"Cloud Garrison","emoji":"🪖","desc":"Military barracks. Elite Kumo soldiers guard the walls 24/7.","bonus":"exp","bonus_val":0.15},
    ],
    "Iwa": [
        {"name":"Stone Quarry","emoji":"🪨","desc":"Where Iwa ninja train their Earth Release with raw boulders.","bonus":"exp","bonus_val":0.15},
        {"name":"Earth Arena","emoji":"🏟️","desc":"Iwa's colosseum. Battle Earth-style gladiators for glory and NC.","bonus":"nc","bonus_val":0.25},
        {"name":"Tsuchikage Fortress","emoji":"🏰","desc":"The Third's legacy. Stone golems and veteran Iwa jonin patrol here.","bonus":"nc","bonus_val":0.30},
        {"name":"Mountain Shrine","emoji":"⛰️","desc":"Ancient altar on Iwa's highest peak. Meditation grants chakra.","bonus":"chakra","bonus_val":0.30},
        {"name":"Dust Release Grounds","emoji":"💨","desc":"Where the Tsuchikage's bloodline is tested. Particle-level combat.","bonus":"exp","bonus_val":0.30},
        {"name":"Underground Tunnels","emoji":"⛏️","desc":"Vast cave network under Iwa. Ambushes around every corner.","bonus":"nc","bonus_val":0.20},
    ],
    "Oto": [
        {"name":"Sound Lab","emoji":"🔊","desc":"Orochimaru's experiments echo here. Cursed enemies roam free.","bonus":"exp","bonus_val":0.25},
        {"name":"Underground Tunnels","emoji":"🕳️","desc":"Oto's hidden passages. Rogue ninja and sound-users lurk within.","bonus":"nc","bonus_val":0.20},
        {"name":"Curse Mark Grounds","emoji":"🌑","desc":"Where Orochimaru brands his chosen. Powerful cursed enemies.","bonus":"nc","bonus_val":0.30},
        {"name":"Otokage Chamber","emoji":"🐍","desc":"The snake sage's throne room. Face his most loyal subordinates.","bonus":"nc","bonus_val":0.35},
        {"name":"Oto Training Pit","emoji":"⚔️","desc":"Brutal underground arena. Only the strongest Oto ninja last here.","bonus":"exp","bonus_val":0.20},
        {"name":"Sound Dojo","emoji":"🎵","desc":"Master the three-sound genjutsu. Illusion-based opponents test you.","bonus":"exp","bonus_val":0.15},
    ],
    "Akatsuki": [
        {"name":"Akatsuki Lair","emoji":"🔴","desc":"The secret base of the criminal organization. S-rank encounters.","bonus":"nc","bonus_val":0.40},
        {"name":"Hidden Cave","emoji":"🗻","desc":"Where Akatsuki members gather. Confront Pain's shadow clones.","bonus":"exp","bonus_val":0.30},
        {"name":"Pain's Tower","emoji":"👁️","desc":"The Rinnegan throne. Six Paths surround you at every turn.","bonus":"nc","bonus_val":0.45},
        {"name":"Ring Assembly","emoji":"💍","desc":"Where the rings are assigned. Face each member's guardian beast.","bonus":"exp","bonus_val":0.35},
        {"name":"Konan's Paper Realm","emoji":"🦋","desc":"600 billion paper bombs surround you. Survive if you can.","bonus":"nc","bonus_val":0.35},
        {"name":"Sasori's Workshop","emoji":"🪆","desc":"Hundreds of puppets await. Hundred Puppet Army encounters.","bonus":"exp","bonus_val":0.25},
    ],
    "Wanderer": [
        {"name":"Ancient Ruins","emoji":"🏛️","desc":"Forgotten temples from the Sage of Six Paths era. Hidden treasures.","bonus":"nc","bonus_val":0.20},
        {"name":"Hidden Valley","emoji":"🌄","desc":"A peaceful valley known only to wanderers. Restore chakra freely.","bonus":"chakra","bonus_val":0.30},
        {"name":"Merchant Road","emoji":"🛤️","desc":"Bustling trade route crossing all countries. NC flows here.","bonus":"nc","bonus_val":0.15},
        {"name":"Sage Mountain","emoji":"🦅","desc":"Where the great Toads reside. Sage Mode training opportunities.","bonus":"exp","bonus_val":0.30},
        {"name":"Border Outpost","emoji":"🚩","desc":"Where rival village patrols clash. Multi-village enemy encounters.","bonus":"nc","bonus_val":0.25},
        {"name":"Abandoned Temple","emoji":"⛩️","desc":"Cursed ruins filled with rogue shinobi. High risk, high reward.","bonus":"nc","bonus_val":0.25},
    ],
}

CLANS = {
    "Uchiha":"Sharingan eye users — Fire & Lightning masters",
    "Hyuga":"Byakugan seers — Gentle Fist specialists",
    "Uzumaki":"Massive chakra reserves — sealing experts (+20% HP)",
    "Senju":"Will of Fire — Wood Release bloodline",
    "Nara":"Shadow manipulation geniuses (IQ 200+)",
    "Akimichi":"Multi-size transformation — colossal power",
    "Yamanaka":"Mind-transfer & psychic jutsu clan",
    "Sarutobi":"God of Shinobi lineage — Fire mastery",
    "Hatake":"Copy-ninja bloodline — can learn any jutsu",
    "Namikaze":"Yellow Flash — Space-Time ninjutsu masters",
    "Subaku":"Sand-controlling royals of Suna",
    "Kaguya":"Bone Release — ultimate bodily weapon",
    "Terumi":"Lava & Boil Release dual bloodline",
    "Hozuki":"Hydrification technique — liquid body",
    "Hidan":"Jashin immortal cursed ritual clan",
    "Kakuzu":"Five hearts — multi-element immortal",
    "Deidara":"Explosion Release art masters",
    "Sasori":"Puppet masters — immortal through puppetry",
    "Konan":"Paper ninjutsu — 600 billion bombs",
    "Aburame":"Parasitic insect colony clan",
    "Otsutsuki":"Celestial clan — Kaguya's bloodline",
    "Yuki":"Ice Release — ancient Kiri bloodline",
    "Momochi":"Demon of the Mist — silent killing",
    "Inuzuka":"Animal-partners — fang techniques",
    "Lee":"Pure Taijutsu — no ninjutsu needed",
    "Haruno":"Medical ninjutsu specialists",
    "Darui":"Storm Release + Black Lightning",
    "Pakura":"Scorch Release — Suna's hero",
    "Rasa":"Magnet Release — Fourth Kazekage",
    "Tsutsuki":"Tenseigan — Hamura's descendant line",
    "Orochimaru":"Snake sage — immortality seeker",
    "Zetsu":"Black & White duality — spy clan",
    "Shimura":"Root ANBU — Danzo's clan",
    "Nohara":"Rin's heritage — Medical specialists",
}

# ─── TAILED BEASTS ──────────────────────────────────────────────
BEASTS = {
    "Shukaku": {
        "tails":1,"host":"Gaara","host_chars":["Gaara","Gaara (Fifth Kazekage)"],
        "nat":"Sand","power":5000,"emoji":"🪶",
        "village":"Suna",
        "ability":"Iron Sand Devastation — AoE Sand prison + crushing burial",
        "desc":"The One-Tail. An ancient sand tanuki sealed in Gaara. Fills the battlefield with iron sand.",
        "photo":"https://files.catbox.moe/shukaku.jpg",
        "battle_hp":3500,"battle_atk":320,
        "catch_hp_boost":300,"catch_atk_boost":40,
    },
    "Matatabi":{
        "tails":2,"host":"Yugito","host_chars":["Yugito Nii"],
        "nat":"Fire","power":6000,"emoji":"🔵",
        "village":"Kumo",
        "ability":"Blue Flame Burial — massive Fire AoE that can't be extinguished",
        "desc":"The Two-Tails. A giant blue flaming cat spirit. Commands undying blue fire.",
        "photo":"https://files.catbox.moe/matatabi.jpg",
        "battle_hp":4200,"battle_atk":370,
        "catch_hp_boost":350,"catch_atk_boost":50,
    },
    "Isobu":   {
        "tails":3,"host":"Yagura","host_chars":["Yagura Karatachi"],
        "nat":"Water","power":7000,"emoji":"🐢",
        "village":"Kiri",
        "ability":"Coral Spike Wave — Water+Earth eruption, coral spike AoE",
        "desc":"The Three-Tails. A colossal turtle sealed in Yagura, the Fourth Mizukage.",
        "photo":"https://files.catbox.moe/isobu.jpg",
        "battle_hp":4900,"battle_atk":400,
        "catch_hp_boost":400,"catch_atk_boost":55,
    },
    "Son Goku":{
        "tails":4,"host":"Roshi","host_chars":["Roshi"],
        "nat":"Lava","power":8000,"emoji":"🐒",
        "village":"Iwa",
        "ability":"Lava Rasenshuriken — melts all defenses with volcanic lava",
        "desc":"The Four-Tails. A lava-spewing monkey king sealed in Roshi of Iwa.",
        "photo":"https://files.catbox.moe/songoku.jpg",
        "battle_hp":5600,"battle_atk":440,
        "catch_hp_boost":450,"catch_atk_boost":65,
    },
    "Kokuo":   {
        "tails":5,"host":"Han","host_chars":["Han"],
        "nat":"Water","power":8500,"emoji":"🐎",
        "village":"Iwa",
        "ability":"Steam Ninjutsu — scalding super-pressurised steam blast",
        "desc":"The Five-Tails. A graceful dolphin-horse sealed in Han of Iwa.",
        "photo":"https://files.catbox.moe/kokuo.jpg",
        "battle_hp":6000,"battle_atk":460,
        "catch_hp_boost":480,"catch_atk_boost":70,
    },
    "Saiken":  {
        "tails":6,"host":"Utakata","host_chars":["Utakata"],
        "nat":"Water","power":9000,"emoji":"🐌",
        "village":"Kiri",
        "ability":"Acid Bubble Bomb — corrosive AoE that melts through anything",
        "desc":"The Six-Tails. A massive slug sealed in Utakata, a missing-nin of Kiri.",
        "photo":"https://files.catbox.moe/saiken.jpg",
        "battle_hp":6400,"battle_atk":490,
        "catch_hp_boost":520,"catch_atk_boost":75,
    },
    "Chomei":  {
        "tails":7,"host":"Fuu","host_chars":["Fuu"],
        "nat":"Wind","power":9500,"emoji":"🦋",
        "village":"Wanderer",
        "ability":"Scale Powder Blindness — wind-borne scales block all sight",
        "desc":"The Seven-Tails. A giant beetle sealed in Fuu. Scale powder blinds enemies.",
        "photo":"https://files.catbox.moe/chomei.jpg",
        "battle_hp":6800,"battle_atk":510,
        "catch_hp_boost":560,"catch_atk_boost":80,
    },
    "Gyuki":   {
        "tails":8,"host":"Killer Bee","host_chars":["Killer Bee"],
        "nat":"Lightning","power":9800,"emoji":"🐂",
        "village":"Kumo",
        "ability":"Tailed Beast Ball + Ink — explosive beam followed by blinding ink AoE",
        "desc":"The Eight-Tails. An ox-octopus sealed in Killer Bee of Kumo. Most cooperative beast.",
        "photo":"https://files.catbox.moe/gyuki.jpg",
        "battle_hp":7200,"battle_atk":540,
        "catch_hp_boost":600,"catch_atk_boost":88,
    },
    "Kurama":  {
        "tails":9,"host":"Naruto","host_chars":["Naruto Uzumaki","Naruto (Baryon Mode)","Minato Namikaze"],
        "nat":"Yang","power":10000,"emoji":"🦊",
        "village":"Konoha",
        "ability":"Bijuu Bomb — nuke-level Yang AoE that levels mountains",
        "desc":"The Nine-Tails. The mightiest of the nine beasts, sealed in Naruto. Immense Yang chakra.",
        "photo":"https://files.catbox.moe/kurama.jpg",
        "battle_hp":8000,"battle_atk":600,
        "catch_hp_boost":700,"catch_atk_boost":100,
    },
}

# Village → tailed beast that roams there (anime-accurate)
VILLAGE_BEAST = {
    "Konoha":   "Kurama",
    "Suna":     "Shukaku",
    "Kiri":     "Isobu",
    "Kumo":     "Gyuki",
    "Iwa":      "Son Goku",
    "Oto":      None,
    "Akatsuki": None,
    "Wanderer": "Chomei",
}

# ─── EYE POWERS (Dojutsu) ───────────────────────────────────────
EYE_POWERS = {
    "Sharingan": {
        "emoji": "🔴",
        "tiers": 3,
        "desc": "Three-tomoe visual jutsu — copies any technique, predicts movement, casts basic genjutsu",
        "clans": ["Uchiha"],
        "abilities": [
            "Copy Jutsu — memorise any ninjutsu/taijutsu on sight",
            "Predict Attack — read muscle movement before it happens",
            "Genjutsu Cast — trap foes with eye contact",
        ],
        "upgrade": "Mangekyou Sharingan",
        "how_works": "Awakened by stress or trauma. Tracks chakra flow to copy techniques. 3-tomoe is the highest basic form.",
        "battle_bonus": {"acc": 10, "crit": 5},
    },
    "Mangekyou Sharingan": {
        "emoji": "🔴",
        "tiers": 1,
        "desc": "Grief-awakened eye — Amaterasu, Tsukuyomi, Susanoo",
        "clans": ["Uchiha"],
        "abilities": [
            "Amaterasu — black undying flames that burn for 7 days",
            "Tsukuyomi — 72-hour illusion compressed into 1 second",
            "Susanoo — giant ethereal warrior armour (partial→full→perfect)",
        ],
        "upgrade": "Eternal Mangekyou Sharingan",
        "how_works": "Awakened upon witnessing the death of a loved one. Each eye holds a unique ability. Overuse causes blindness.",
        "battle_bonus": {"atk": 30, "acc": 15, "crit": 10},
    },
    "Eternal Mangekyou Sharingan": {
        "emoji": "🔴",
        "tiers": 1,
        "desc": "Perfect Susanoo unlocked — no vision loss, godly power",
        "clans": ["Uchiha"],
        "abilities": [
            "Perfect Susanoo — building-sized warrior, only 2 users in history",
            "Blaze Release: Kagutsuchi — shape and control Amaterasu",
            "Enhanced Tsukuyomi — deeper, longer illusion",
        ],
        "upgrade": "Rinnegan (requires Six Paths chakra)",
        "how_works": "Transplanting a sibling's Mangekyou eliminates blindness. Madara and Sasuke are the only known users.",
        "battle_bonus": {"atk": 50, "acc": 20, "crit": 15, "def": 15},
    },
    "Rinnegan": {
        "emoji": "💜",
        "tiers": 1,
        "desc": "God's eye — Six Paths jutsu, gravity control, soul extraction",
        "clans": ["Uzumaki", "Uchiha", "Otsutsuki"],
        "abilities": [
            "Almighty Push — repels all matter in a sphere",
            "Planetary Devastation — rips earth chunks and levitates them",
            "Limbo Clone — invisible shadow clones in another dimension",
            "Outer Path — revive the dead, transmit chakra through black receivers",
            "Six Paths Sage Mode — senses invisible attacks",
        ],
        "upgrade": "Rinne-Sharingan (Otsutsuki only)",
        "how_works": "Requires merging Indra's AND Asura's chakra, or Otsutsuki heritage. Madara, Nagato, Sasuke, Hagoromo are known users.",
        "battle_bonus": {"atk": 55, "def": 25, "acc": 25},
    },
    "Byakugan": {
        "emoji": "⬜",
        "tiers": 1,
        "desc": "Nearly 360° piercing vision — sees chakra network, enables Gentle Fist",
        "clans": ["Hyuga"],
        "abilities": [
            "Gentle Fist — strike chakra points to close tenketsu",
            "Eight Trigrams 64 Palms — 64 rapid chakra point strikes",
            "Eight Trigrams 128 Palms — double the devastation",
            "Chakra Network Sight — see and disrupt internal chakra flow",
        ],
        "upgrade": "Tenseigan",
        "how_works": "Hyuga kekkei genkai. Provides 359° vision (one blind spot). Sees through solid objects. Closes chakra gates with precision strikes.",
        "battle_bonus": {"acc": 18, "crit": 8, "def": 15},
    },
    "Tenseigan": {
        "emoji": "🔵",
        "tiers": 1,
        "desc": "Hamura's dojutsu — gravity manipulation, Tenseigan Chakra Mode",
        "clans": ["Tsutsuki", "Otsutsuki"],
        "abilities": [
            "Tenseigan Chakra Mode — golden aura, Truth-Seeking Balls",
            "Gravity Release — control gravitational fields",
            "Truth-Seeking Balls — 9 black orbs of any elemental combo",
        ],
        "upgrade": None,
        "how_works": "Formed by combining Byakugan with Otsutsuki chakra. Toneri was the last known user. Provides godly power equivalent to Six Paths.",
        "battle_bonus": {"atk": 65, "def": 35, "spd": 25},
    },
    "Rinne-Sharingan": {
        "emoji": "🔴💜",
        "tiers": 1,
        "desc": "Kaguya's third eye — Infinite Tsukuyomi, dimensional travel",
        "clans": ["Otsutsuki"],
        "abilities": [
            "Infinite Tsukuyomi — moon-projected dream that seals all humanity",
            "Dimensional Shift — open portals to any of Kaguya's dimensions",
            "Ash Killing Bones — disintegrate targets on contact",
            "All-Killing Ash Bone — insta-kill projectiles",
        ],
        "upgrade": None,
        "how_works": "The original dojutsu from which all others evolved. Only Kaguya possesses this. Located in the forehead, connected to the Ten-Tails.",
        "battle_bonus": {"atk": 90, "def": 55, "acc": 35},
    },
    "Jougan": {
        "emoji": "🔷",
        "tiers": 1,
        "desc": "Boruto's mysterious pure eye — sees chakra pathways, dimensional rifts",
        "clans": ["Uzumaki", "Otsutsuki"],
        "abilities": [
            "Chakra Rift Vision — detect invisible rifts between dimensions",
            "Isshiki Tracking — can perceive sukunahikona-shrunken objects",
            "Karma Link — resonates with Otsutsuki Karma seals",
        ],
        "upgrade": None,
        "how_works": "A mysterious dojutsu exclusive to Boruto, granted by his Otsutsuki heritage and Karma seal. True potential unknown.",
        "battle_bonus": {"acc": 20, "crit": 12},
    },
}

# Map character names → their dojutsu
CHAR_EYE_POWER = {
    "Sasuke Uchiha":              "Rinnegan",
    "Itachi Uchiha":              "Mangekyou Sharingan",
    "Madara Uchiha":              "Eternal Mangekyou Sharingan",
    "Madara (Ten-Tails Jinchuriki)":"Rinnegan",
    "Obito Uchiha":               "Mangekyou Sharingan",
    "Kakashi Hatake":             "Mangekyou Sharingan",
    "Shisui Uchiha":              "Mangekyou Sharingan",
    "Sarada Uchiha":              "Sharingan",
    "Pain (Nagato)":              "Rinnegan",
    "Kaguya Otsutsuki":           "Rinne-Sharingan",
    "Kaguya Otsutsuki (Full Power)":"Rinne-Sharingan",
    "Hagoromo Otsutsuki":         "Rinnegan",
    "Hamura Otsutsuki":           "Tenseigan",
    "Toneri Otsutsuki":           "Tenseigan",
    "Isshiki Otsutsuki":          "Rinne-Sharingan",
    "Neji Hyuga":                 "Byakugan",
    "Hinata Hyuga":               "Byakugan",
    "Hiashi Hyuga":               "Byakugan",
    "Hanabi Hyuga":               "Byakugan",
    "Boruto Uzumaki":             "Jougan",
}

# ─── MOVE LIBRARY ───────────────────────────────────────────────
def mv(name,pw,ac,ch,tp,ef,desc):
    return {"name":name,"power":pw,"acc":ac,"chakra":ch,"type":tp,"effect":ef,"desc":desc}

M = {
# WIND
"rasengan":        mv("Rasengan",90,95,50,"Wind","stun:10","Spiraling chakra sphere"),
"rasenshuriken":   mv("Wind Rasenshuriken",130,82,70,"Wind","spd_down:20","Giant wind-blade shuriken"),
"shadow_clone":    mv("Shadow Clone Jutsu",60,100,30,"Wind","def_up:20","Creates shadow clones"),
"tbb":             mv("Tailed Beast Bomb",155,70,80,"Yang","aoe:0","Bijuu Bomb devastation"),
"ftg":             mv("Flying Thunder God",110,95,60,"Wind","dodge_next:0","Teleportation strike"),
"wind_cutter":     mv("Wind Vacuum Blade",85,92,40,"Wind","bleed:0","Slicing vacuum blade"),
"wind_wall":       mv("Wind Wall",70,100,35,"Wind","def_up:25","Barrier of compressed wind"),
"rasenshuriken3":  mv("Sage Rasenshuriken",155,78,90,"Wind","spd_down:30","Sage wind shuriken"),
"baryon_strike":   mv("Baryon Mode Strike",200,90,110,"Yang","stun:25","Life-force burning punch"),
"clone_barrage":   mv("Clone Barrage",90,92,40,"Wind","multi_hit:0","Shadow clone assault"),
"wind_dance":      mv("Wind Dance Slash",80,95,35,"Wind","spd_down:10","Dancing wind blades"),
"vacuum_sphere":   mv("Vacuum Sphere",95,90,45,"Wind","multi_hit:0","Multiple vacuum bullets"),
# LIGHTNING
"chidori":         mv("Chidori",100,90,50,"Lightning","crit:20","Lightning blade strike"),
"kirin":           mv("Kirin",165,65,100,"Lightning","stun:30","Summons natural lightning"),
"raikiri":         mv("Raikiri",110,88,55,"Lightning","def_break:0","Enhanced lightning blade"),
"thunder_blade":   mv("Thunder Blade",85,92,40,"Lightning","stun:10","Crackling lightning slash"),
"lightning_ball":  mv("Lightning Ball",95,88,45,"Lightning","chain:0","Bouncing lightning orb"),
"black_lightning": mv("Black Lightning",130,82,70,"Lightning","burn:20","Darui's black thunder"),
"lariat":          mv("Lariat",120,88,55,"Lightning","def_break:0","Lightning clothesline"),
"thunder_god":     mv("Thunder God Fist",140,80,75,"Lightning","stun:20","Raikage-level punch"),
"lariat2":         mv("Double Lariat",140,82,70,"Lightning","def_break:0","Two-person Lariat"),
"chidori_senbon":  mv("Chidori Senbon",100,90,50,"Lightning","multi_hit:0","Lightning needles"),
"susanoo_arrow":   mv("Susanoo Arrow",155,78,85,"Lightning","pierce:0","Lightning arrow"),
"vanishing_strike":mv("Vanishing Strike",115,88,60,"Lightning","crit:15","High-speed Chidori"),
"indraarow":       mv("Indra's Arrow",240,70,120,"Lightning","aoe:0","Susanoo god-arrow"),
"lightning_fang":  mv("Lightning Fang",88,92,42,"Lightning","stun:8","Electric fang strike"),
"plasma_cutter":   mv("Plasma Cutter",105,86,52,"Lightning","def_break:0","Cutting plasma blade"),
# FIRE
"fireball":        mv("Great Fireball",90,95,40,"Fire","burn:10","Classic Uchiha fire"),
"amaterasu":       mv("Amaterasu",125,75,70,"Fire","burn:30","Black undying flames"),
"phoenix_flower":  mv("Phoenix Flower",80,92,35,"Fire","burn:15","Multiple fire blasts"),
"fire_dragon":     mv("Dragon Flame Jutsu",110,85,55,"Fire","burn:20","Spiraling dragon fire"),
"toad_fire":       mv("Toad Oil Bomb+Fire",120,82,60,"Fire","burn:25","Flammable toad oil ignition"),
"ash_pile":        mv("Ash Pile Burning",100,88,50,"Fire","stun:15","Exploding ash cloud"),
"perfect_susanoo": mv("Perfect Susanoo",205,75,110,"Fire","aoe:0","Building-sized warrior"),
"fire_vortex":     mv("Fire Style Vortex",95,88,48,"Fire","burn:15","Spinning fire tornado"),
"grand_fireball":  mv("Grand Fireball Art",115,85,58,"Fire","burn:20","Massive fireball"),
# EARTH
"earth_spear":     mv("Earth Spear",115,88,50,"Earth","def_up:15","Hardened earth lance"),
"rock_avalanche":  mv("Rock Avalanche",130,80,65,"Earth","stun:20","Boulder storm"),
"mud_wave":        mv("Mud Wall Wave",85,92,40,"Earth","def_up:20","Rising mud barrier"),
"earth_prison":    mv("Earth Prison Dome",100,85,50,"Earth","stun:25","Underground trap"),
"dust_release":    mv("Dust Release Detach",180,70,100,"Earth","aoe:0","Disintegration cube"),
"particle_ray":    mv("Particle Style Laser",155,72,90,"Earth","pierce:0","Atomic-level beam"),
"camelia_dance":   mv("Dance of Camellia",110,90,45,"Earth","pierce:0","Rapid bone stabs"),
"larch_dance":     mv("Dance of the Larch",120,85,55,"Earth","def_up:20","Bone armor burst"),
"clematis_vine":   mv("Dance of Clematis",140,80,70,"Earth","stun:20","Bone vine trap"),
"bracken_dance":   mv("Bracken Dance",165,72,85,"Earth","aoe:0","Bone forest eruption"),
"stone_fist":      mv("Stone Fist",88,93,38,"Earth","def_up:10","Rock-hard punch"),
"earth_dragon":    mv("Earth Dragon Jutsu",108,86,53,"Earth","stun:12","Dragon of earth"),
# WATER
"water_dragon":    mv("Water Dragon Bullet",110,88,55,"Water","stun:10","Coiling water dragon"),
"water_bullet":    mv("Water Bullet Jutsu",85,92,40,"Water","spd_down:10","High-pressure shot"),
"great_flood":     mv("Exploding Water",135,80,70,"Water","aoe:0","Massive water flood"),
"hidden_mist":     mv("Hidden Mist Jutsu",70,100,35,"Water","acc_down:20","Blinding mist cover"),
"water_shark":     mv("Water Fang Bullet",120,85,60,"Water","bleed:0","Rotating water fang"),
"steam_bomb":      mv("Boil Release Mist",125,82,65,"Water","burn:15","Corrosive steam AoE"),
"paper_bomb_sea":  mv("Paper Bomb Sea",205,70,110,"Water","aoe:0","600 billion bombs"),
"paper_shuriken":  mv("Paper Shuriken",80,95,30,"Water","multi_hit:0","Blade paper storm"),
"water_wave":      mv("Raging Water Wave",98,88,48,"Water","spd_down:12","Rushing water wave"),
"acid_mist":       mv("Acid Mist",85,90,42,"Water","poison:15","Corrosive vapor cloud"),
# SAND
"sand_coffin":     mv("Sand Coffin",100,88,50,"Sand","stun:20","Encases enemy in sand"),
"sand_burial":     mv("Sand Burial",155,75,75,"Sand","def_break:0","Crushing compression"),
"sand_storm":      mv("Sand Storm",90,92,45,"Sand","aoe:0","Blinding storm"),
"iron_sand":       mv("Iron Sand Drizzle",110,85,55,"Sand","poison:15","Poison-coated needles"),
"shukaku_blast":   mv("Shukaku Sphere",160,70,90,"Sand","aoe:0","Tailed Beast release"),
"sand_clone":      mv("Sand Clone",65,100,30,"Sand","def_up:20","Perfect sand decoy"),
"sand_wave":       mv("Sand Tsunami",118,83,58,"Sand","stun:15","Massive sand wave"),
"desert_requiem":  mv("Desert Requiem",145,76,75,"Sand","aoe:0","Sand graveyard jutsu"),
# YIN
"shadow_bind":     mv("Shadow Bind Jutsu",80,92,40,"Yin","stun:20","Shadow possession"),
"shadow_stitch":   mv("Shadow Sewing",100,85,55,"Yin","stun:15","Shadow needle pierce"),
"shadow_king":     mv("Shadow King Strangling",130,78,70,"Yin","stun:30","Ultimate shadow"),
"tsukuyomi":       mv("Tsukuyomi",140,75,80,"Yin","stun:25","72-hour genjutsu"),
"totsuka":         mv("Totsuka Blade",175,70,100,"Yin","seal:0","Sealing ethereal sword"),
"izanagi":         mv("Izanagi",120,88,70,"Yin","dodge_next:0","Rewrite reality once"),
"mind_transfer":   mv("Mind Transfer Jutsu",75,90,40,"Yin","skip_turn:0","Take control"),
"jashin_curse":    mv("Jashin Curse Ritual",120,85,60,"Yin","reflect_dmg:25","Cursed reflection"),
"koto_amatsukami": mv("Kotoamatsukami",130,88,75,"Yin","skip_turn:0","Subtle mind control"),
"kagura_mind":     mv("Kagura Mind",100,88,50,"Yin","stun:20","Genjutsu technique"),
"bringer_dark":    mv("Bringer of Darkness",95,90,50,"Yin","acc_down:30","Infinite darkness"),
"izanami":         mv("Izanami",110,82,75,"Yin","stun:30","Reality-loop trap"),
"ghost_blade":     mv("Ghost Blade",115,90,55,"Ghost","pierce:0","Intangible sword slash"),
"genjutsu_bind":   mv("Genjutsu Binding",82,91,42,"Yin","stun:18","Reality illusion bind"),
"dark_needle":     mv("Dark Needle",78,94,35,"Yin","poison:12","Shadow-infused needle"),
# YANG
"almighty_push":   mv("Almighty Push",150,85,80,"Yang","aoe:0","Massive repulsion force"),
"planetary_dev":   mv("Planetary Devastation",210,65,110,"Yang","aoe:0","Creates a small moon"),
"shinra_tensei":   mv("Shinra Tensei",130,90,70,"Yang","stun:20","Gravity repulsion"),
"human_path":      mv("Human Path",115,88,65,"Yang","soul_rip:0","Rips out the soul"),
"gedo_chain":      mv("Gedo Chains",130,80,70,"Yang","stun:20","Suppression chains"),
"gedo_mazo":       mv("Gedo Statue",170,78,95,"Yang","aoe:0","Outer Path chains"),
"chibaku_tensei":  mv("Chibaku Tensei",195,68,110,"Yang","aoe:0","Gravity-sphere trap"),
"six_paths_sage":  mv("Six Paths Sage",190,78,105,"Yin-Yang","aoe:0","Six Paths power"),
"sage_truth_fist": mv("Truth-Seeking Balls",185,75,100,"Yin-Yang","aoe:0","Yin-Yang orb blast"),
"limbo":           mv("Gedo Art of Rinbo",185,80,100,"Yin-Yang","unavoidable:0","Shadow realm"),
"tengai_meteor":   mv("Tengai Shinsei",220,65,120,"Yin-Yang","aoe:0","Heavenly meteor"),
"infinite_tsuk":   mv("Infinite Tsukuyomi",180,72,110,"Yin","stun:30","World-scale genjutsu"),
"meteorite":       mv("Meteorite Drop",225,65,120,"Earth","aoe:0","Meteor from sky"),
"gravity_pull":    mv("Gravity Pull",112,87,56,"Yang","stun:14","Gravitational attraction"),
# TAIJUTSU
"leaf_hurricane":  mv("Leaf Hurricane",85,95,20,"Taijutsu","spd_down:10","Spinning kick combo"),
"primary_lotus":   mv("Primary Lotus",130,82,30,"Taijutsu","stun:10","Bandage-wrap slam"),
"hidden_lotus":    mv("Hidden Lotus",200,70,50,"Taijutsu","stun:25","Eight-gates powered slam"),
"evening_elephant":mv("Evening Elephant",185,75,40,"Taijutsu","stun:20","7-vacuum fists"),
"night_guy":       mv("Night Guy",255,65,60,"Taijutsu","aoe:0","Eight-gates ultimate"),
"drunken_fist":    mv("Drunken Fist",90,88,15,"Taijutsu","dodge_up:15","Unpredictable style"),
"dynamic_entry":   mv("Dynamic Entry",100,90,10,"Taijutsu","stun:10","Running flying kick"),
"strong_fist":     mv("Strong Fist",110,92,25,"Taijutsu","def_break:0","Bone-breaking punch"),
"taijutsu_combo":  mv("Taijutsu Barrage",95,90,40,"Taijutsu","multi_hit:0","Rapid punch combo"),
"gentle_fist":     mv("Gentle Fist Strike",80,95,30,"Lightning","def_break:0","Tenketsu disabling"),
"byakugan_64":     mv("Eight Trigrams 64 Palms",120,90,60,"Lightning","chakra_drain:30","Tenketsu strike"),
"rotation":        mv("Eight Trigrams Rotation",110,85,50,"Lightning","reflect_dmg:0","Spinning barrier"),
"twin_lions":      mv("Twin Lion Fists",120,85,60,"Water","chakra_drain:20","Chakra lion strikes"),
"tiger_fist":      mv("Tiger Fist",92,92,22,"Taijutsu","stun:8","Powerful tiger strike"),
"swift_kick":      mv("Swift Kick Barrage",88,93,18,"Taijutsu","spd_down:8","Speed kick combo"),
# WOOD
"wood_dragon":     mv("Wood Dragon Jutsu",140,85,75,"Wood","chakra_drain:25","Chakra-draining dragon"),
"wood_golem":      mv("Wooden Statue Golem",170,75,90,"Wood","aoe:0","Massive wood giant"),
"thousand_hand":   mv("Thousand-Hand Buddha",225,70,110,"Wood","aoe:0","Giant wooden deity"),
"wood_clone":      mv("Wood Clone Jutsu",75,100,35,"Wood","def_up:20","Perfect living clone"),
"wood_spikes":     mv("Wood Spike Wall",95,90,45,"Wood","bleed:0","Bursting spike wall"),
"forest_trap":     mv("Advent of World Flowers",155,78,85,"Wood","aoe:0","Forest entanglement"),
"wood_prison":     mv("Wood Prison Jutsu",105,86,52,"Wood","stun:22","Tree prison entrapment"),
# MEDICAL
"monster_punch":   mv("Monster Strength Punch",165,88,40,"Medical","stun:20","Earth-cracking fist"),
"mystical_palm":   mv("Mystical Palm",65,100,50,"Medical","heal_self:20","Regenerative touch"),
"poison_gas":      mv("Poison Gas Bomb",80,90,40,"Medical","poison:25","Toxic cloud"),
"healing_seal":    mv("Strength of a Hundred",110,90,65,"Medical","revive:0","Forbidden seal"),
"katsuyu":         mv("Summoning Katsuyu",130,80,75,"Medical","team_heal:0","Giant slug summon"),
"chakra_scalpel":  mv("Chakra Scalpel",100,95,45,"Medical","def_break:0","Surgical blade"),
"antidote_fist":   mv("Antidote Punch",85,92,38,"Medical","def_break:0","Medic punch"),
# EXPLOSION
"c1_birds":        mv("C1 Clay Birds",80,95,35,"Explosion","multi_hit:0","Explosive bird swarm"),
"c2_dragon":       mv("C2 Dragon",120,82,60,"Explosion","aoe:0","Explosive clay dragon"),
"c3_bomb":         mv("C3 Massive Bomb",175,72,90,"Explosion","aoe:0","City-scale explosion"),
"c4_karura":       mv("C4 Karura",165,75,95,"Explosion","poison:20","Micro-bomb internal"),
"c0_ultimate":     mv("C0 Ultimate Art",255,60,120,"Explosion","self_dmg:30","Total detonation"),
"clay_wall":       mv("Clay Barrier",70,100,35,"Explosion","def_up:25","Absorbing clay wall"),
"clay_spider":     mv("Clay Spider Bomb",92,90,42,"Explosion","poison:12","Exploding spider clay"),
# PUPPET
"crow_puppet":     mv("Crow Puppet Attack",90,90,40,"Puppet","poison:10","Crow puppet assault"),
"black_ant":       mv("Black Ant Trap",110,85,55,"Puppet","stun:20","Entrapment puppet"),
"scorpion_tail":   mv("Scorpion Tail",100,90,50,"Puppet","poison:25","Hidden tail sting"),
"hundred_puppets": mv("Hundred Puppet Army",155,75,85,"Puppet","aoe:0","100 puppet assault"),
"puppet_3rd":      mv("3rd Kazekage Puppet",130,82,65,"Metal","stun:20","Iron-sand control"),
"sasori_combo":    mv("Puppet 3-Man Combo",110,88,50,"Puppet","stun:15","Triple puppet rush"),
"puppet_wall":     mv("Puppet Defense Wall",72,100,32,"Puppet","def_up:22","Puppet barrier"),
# LAVA/SCORCH/ICE/STORM/METAL
"lava_melt":       mv("Lava Style Melting",130,82,65,"Lava","burn:20","Acidic lava mist"),
"lava_giant":      mv("Lava Style Golem",155,75,85,"Lava","aoe:0","Volcanic rock giant"),
"boil_steam":      mv("Boil Style Mist",125,85,65,"Water","burn:15","Corrosive steam"),
"scorch_ball":     mv("Scorch Release Ball",120,85,60,"Scorch","burn:25","Incinerating sphere"),
"ice_dome":        mv("Ice Style Dome Prison",110,88,55,"Ice","stun:20","Frozen prison"),
"ice_mirrors":     mv("Crystal Ice Mirrors",130,80,70,"Ice","dodge_next:0","Mirror teleportation"),
"ice_needles":     mv("Ice Needles",85,95,35,"Ice","bleed:0","Razor ice shard storm"),
"storm_shark":     mv("Storm Release Shark",125,85,65,"Storm","chain:0","Lightning+water shark"),
"plasma_ball":     mv("Plasma Ball",140,80,75,"Storm","aoe:0","Electromagnetic AoE"),
"metal_prison":    mv("Metal Prison",100,88,50,"Metal","stun:20","Magnetic metal cage"),
"ice_lance":       mv("Ice Lance",95,90,46,"Ice","bleed:0","Sharp ice spear thrust"),
"blizzard":        mv("Blizzard Storm",108,86,54,"Ice","spd_down:18","Freezing blizzard"),
# POISON
"venom_strike":    mv("Venom Strike",92,90,42,"Poison","poison:20","Poison-laced punch"),
"poison_cloud":    mv("Poison Cloud",82,93,38,"Poison","poison:25","Toxic cloud burst"),
"toxic_spore":     mv("Toxic Spore",75,95,35,"Poison","poison:18","Spreading spores"),
# MISC
"summoning_toad":  mv("Summoning Gamabunta",150,72,85,"Wind","aoe:0","Giant toad boss"),
"summoning_snake": mv("Summoning Manda",145,75,80,"Yin","poison:20","Giant snake bite"),
"eight_branches":  mv("Eight Branches",130,85,70,"Yin","multi_hit:0","8-headed snake"),
"kusanagi":        mv("Kusanagi Sword",110,90,50,"Lightning","pierce:0","Snake legendary blade"),
"corpse_rein":     mv("Living Corpse Rein",60,100,80,"Yin","absorb:20","Body-stealing jutsu"),
"insect_swarm":    mv("Insect Swarm",90,92,35,"Earth","chakra_drain:15","Bug swarm drain"),
"ink_bird":        mv("Ink Clone Bird",75,100,35,"Wind","def_up:20","Ink art clone"),
"super_beast":     mv("Super Beast Scroll",120,85,60,"Wind","multi_hit:0","Ink lion beast"),
"sage_mode_atk":   mv("Sage Mode Strike",140,85,65,"Wind","crit:20","Nature energy enhanced"),
"rasenshuriken2":  mv("Rasenshuriken Sage",145,80,85,"Wind","spd_down:25","Enhanced shuriken"),
"fang_over_fang":  mv("Fang Over Fang",98,90,38,"Wind","multi_hit:0","Spinning dog-fang drill"),
"butterfly_bomb":  mv("Butterfly Bomb",155,78,78,"Earth","aoe:0","Butterfly mode explosion"),
"sealing_jutsu":   mv("Sealing Jutsu",88,90,45,"Yin","stun:20","Chakra seal technique"),
"chakra_chains":   mv("Chakra Chains",110,86,55,"Yang","stun:22","Sealing chains"),
"bone_drill":      mv("Bone Drill",105,88,48,"Earth","pierce:0","Spinning bone spike"),
"paper_blade":     mv("Paper Blade",86,92,38,"Water","bleed:0","Razor paper slash"),
"puppet_bomb":     mv("Puppet Bomb",102,88,46,"Explosion","burn:12","Hidden puppet explosive"),
"sword_gale":      mv("Sword Gale",96,91,44,"Wind","bleed:0","Wind-infused sword slash"),
"curse_seal":      mv("Curse Seal Release",125,82,62,"Yin","burn:15","Orochimaru's curse seal"),
"snake_fang":      mv("Snake Fang Strike",88,92,40,"Yin","poison:15","Quick snake bite"),
"water_whip":      mv("Water Whip",85,93,38,"Water","bleed:0","Water whip slash"),
"thunder_clap":    mv("Thunder Clap",102,88,50,"Lightning","stun:12","Explosive thunderclap"),
"earth_wall":      mv("Earth Wall",68,100,32,"Earth","def_up:28","Rising earth barrier"),
"fire_spin":       mv("Fire Spin",88,91,42,"Fire","burn:12","Spinning fire vortex"),
"shadow_slash":    mv("Shadow Slash",92,90,43,"Yin","bleed:0","Darkness-infused slash"),
"ice_prison":      mv("Ice Prison",108,86,53,"Ice","stun:24","Freezing prison dome"),
"sand_shield":     mv("Sand Shield",65,100,30,"Sand","def_up:30","Absolute sand defense"),
"lava_river":      mv("Lava River",122,83,62,"Lava","burn:22","Flowing lava stream"),
"chakra_burst":    mv("Chakra Burst",82,93,40,"Yang","aoe:0","Raw chakra explosion"),
"puppet":          mv("Basic Strike",50,100,10,"Taijutsu","","Basic attack"),
}

M["punch"] = mv("Basic Strike",50,100,10,"Taijutsu","","Basic attack")

# ─── NATURE → DEFAULT MOVES ─────────────────────────────────────
NAT_MOVES = {
    "Fire":      ["fireball","phoenix_flower","fire_dragon","ash_pile"],
    "Wind":      ["rasengan","wind_cutter","shadow_clone","wind_wall"],
    "Lightning": ["chidori","thunder_blade","lightning_ball","vanishing_strike"],
    "Earth":     ["earth_spear","rock_avalanche","mud_wave","earth_prison"],
    "Water":     ["water_dragon","water_bullet","hidden_mist","water_shark"],
    "Yin":       ["shadow_bind","kagura_mind","bringer_dark","genjutsu_bind"],
    "Yang":      ["almighty_push","shinra_tensei","gedo_chain","gravity_pull"],
    "Taijutsu":  ["leaf_hurricane","dynamic_entry","strong_fist","taijutsu_combo"],
    "Medical":   ["mystical_palm","chakra_scalpel","monster_punch","poison_gas"],
    "Sand":      ["sand_coffin","sand_clone","sand_burial","sand_storm"],
    "Wood":      ["wood_clone","wood_spikes","wood_dragon","forest_trap"],
    "Ice":       ["ice_dome","ice_mirrors","ice_needles","blizzard"],
    "Lava":      ["lava_melt","lava_giant","fire_dragon","rock_avalanche"],
    "Scorch":    ["scorch_ball","ash_pile","fire_dragon","wind_cutter"],
    "Explosion": ["c1_birds","c2_dragon","c3_bomb","clay_wall"],
    "Puppet":    ["crow_puppet","black_ant","scorpion_tail","sasori_combo"],
    "Metal":     ["metal_prison","earth_spear","rock_avalanche","thunder_blade"],
    "Storm":     ["storm_shark","plasma_ball","thunder_blade","water_dragon"],
    "Ghost":     ["ghost_blade","shadow_bind","kagura_mind","dark_needle"],
    "Poison":    ["poison_gas","insect_swarm","venom_strike","poison_cloud"],
    "Yin-Yang":  ["six_paths_sage","sage_truth_fist","limbo","tengai_meteor"],
}

# ─── CHARACTER FACTORY ──────────────────────────────────────────
RAR    = {"Common":"<tg-emoji emoji-id='5339146018288078089'>⚪</tg-emoji>","Uncommon":"<tg-emoji emoji-id='5339560611481162409'>🟢</tg-emoji>","Rare":"<tg-emoji emoji-id='5352805092326151076'>🔵</tg-emoji>","Epic":"<tg-emoji emoji-id='5287402623127818507'>🟣</tg-emoji>","Legendary":"<tg-emoji emoji-id='5354869292263311935'>🟡</tg-emoji>","Mythic":"<tg-emoji emoji-id='5341779159658042646'>🔴</tg-emoji>"}
RAR_BTN = {"Common":"","Uncommon":"","Rare":"","Epic":"","Legendary":"","Mythic":""}
RAR_RATES = {"Common":0.35,"Uncommon":0.28,"Rare":0.20,"Epic":0.10,"Legendary":0.05,"Mythic":0.02}

def C(name,rarity,nature,village,clan,photo,hp,atk,df,spd,cha,
      fm,fq,fb,move_keys,beast=None):
    moves = [dict(M[k]) for k in move_keys if k in M]
    if not moves: moves = [dict(M["punch"])]
    return {"name":name,"rarity":rarity,"nature":nature,"village":village,"clan":clan,
            "photo":photo,"base":{"hp":hp,"atk":atk,"def":df,"speed":spd,"chakra":cha},
            "form":{"name":fm,"req_chakra":fq,"buff":fb} if fm else None,
            "moves":moves,"tailed_beast":beast}

def Q(name,rar,nat,vil,clan,photo=None,hp=200,atk=200,df=170,spd=200,cha=300,
      fm=None,fq=0,fb=None,beast=None,moves=None):
    """Quick character builder using nature default moves"""
    mv_keys = moves if moves else NAT_MOVES.get(nat,["punch","taijutsu_combo","dynamic_entry","wind_cutter"])
    return C(name,rar,nat,vil,clan,photo,hp,atk,df,spd,cha,fm,fq,fb or {},mv_keys,beast)

PH = "https://files.catbox.moe/"

# ─── CHARACTERS (400+) ──────────────────────────────────────────
CHARACTERS = [
# ══ MYTHIC ══════════════════════════════════════════════════════
C("Naruto (Baryon Mode)","Mythic","Yang","Konoha","Uzumaki",None,
  500,550,300,500,700,"Final Baryon Mode",20000,
  {"hp":800,"atk":700,"def":300,"speed":650},
  ["baryon_strike","tbb","rasengan","rasenshuriken"],"Kurama"),

C("Kaguya Otsutsuki (Full Power)","Mythic","Yin-Yang","Wanderer","Otsutsuki",None,
  600,520,420,380,750,"Expansive Truth-Seeking Balls",20000,
  {"hp":1000,"atk":700,"def":550,"speed":460},
  ["sage_truth_fist","infinite_tsuk","tengai_meteor","limbo"]),

C("Isshiki Otsutsuki","Mythic","Yang","Wanderer","Otsutsuki",None,
  540,560,370,450,720,"Sukunahikona Full Release",20000,
  {"hp":850,"atk":730,"def":430,"speed":560},
  ["planetary_dev","tengai_meteor","almighty_push","chibaku_tensei"]),

C("Madara (Ten-Tails Jinchuriki)","Mythic","Yin-Yang","Akatsuki","Uchiha",None,
  580,540,400,400,740,"Six Paths Limbo Mode",22000,
  {"hp":950,"atk":720,"def":520,"speed":470},
  ["limbo","meteorite","tengai_meteor","sage_truth_fist"]),

C("Hashirama (God of Shinobi)","Mythic","Wood","Konoha","Senju",None,
  560,510,430,360,730,"Wood Golem Sage Bijuu Mode",20000,
  {"hp":900,"atk":680,"def":560,"speed":420},
  ["thousand_hand","wood_dragon","wood_golem","forest_trap"]),

# ══ LEGENDARY ═══════════════════════════════════════════════════
C("Naruto Uzumaki","Legendary","Wind","Konoha","Uzumaki",
  None,340,300,210,340,520,
  "Nine-Tails Chakra Mode",12000,{"hp":600,"atk":550,"def":150,"speed":450},
  ["rasengan","rasenshuriken","tbb","baryon_strike"],"Kurama"),

C("Sasuke Uchiha","Legendary","Lightning","Konoha","Uchiha",
  PH+"vp2o00.jpg",315,360,220,375,510,
  "Rinnegan Awakening",11000,{"hp":400,"atk":460,"def":240,"speed":520},
  ["chidori","amaterasu","perfect_susanoo","indraarow"]),

C("Madara Uchiha","Legendary","Fire","Akatsuki","Uchiha",None,
  400,420,300,370,620,"Ten-Tails Jinchuriki",15000,
  {"hp":700,"atk":620,"def":420,"speed":440},
  ["limbo","meteorite","tengai_meteor","perfect_susanoo"]),

C("Hashirama Senju","Legendary","Wood","Konoha","Senju",None,
  430,400,320,320,600,"Sage Mode Wood Golem",12000,
  {"hp":700,"atk":510,"def":440,"speed":380},
  ["thousand_hand","forest_trap","wood_dragon","wood_golem"]),

C("Minato Namikaze","Legendary","Wind","Konoha","Namikaze",None,
  320,385,235,460,540,"Yin-Yang Kurama Seal",12000,
  {"hp":520,"atk":520,"def":300,"speed":570},
  ["ftg","rasengan","rasenshuriken3","tbb"],"Kurama"),

C("Itachi Uchiha","Legendary","Fire","Akatsuki","Uchiha",None,
  305,370,225,380,530,"Perfect Susanoo Reborn",11000,
  {"hp":390,"atk":460,"def":300,"speed":420},
  ["amaterasu","tsukuyomi","totsuka","koto_amatsukami"]),

C("Pain (Nagato)","Legendary","Yang","Akatsuki","Uzumaki",None,
  350,390,260,330,560,"Six Paths of Pain",12000,
  {"hp":520,"atk":490,"def":320,"speed":380},
  ["almighty_push","planetary_dev","chibaku_tensei","shinra_tensei"]),

C("Kaguya Otsutsuki","Legendary","Yin-Yang","Wanderer","Otsutsuki",None,
  480,430,350,390,650,"All-Killing Ash Bone",15000,
  {"hp":800,"atk":580,"def":480,"speed":460},
  ["sage_truth_fist","infinite_tsuk","limbo","tengai_meteor"]),

C("Hagoromo Otsutsuki","Legendary","Yin-Yang","Wanderer","Otsutsuki",None,
  460,440,360,380,680,"Truth-Seeking Creation",15000,
  {"hp":750,"atk":560,"def":460,"speed":440},
  ["six_paths_sage","sage_truth_fist","chibaku_tensei","limbo"]),

C("Obito Uchiha","Legendary","Fire","Akatsuki","Uchiha",None,
  330,360,245,340,520,"Ten-Tails Jinchuriki",12000,
  {"hp":520,"atk":500,"def":320,"speed":390},
  ["gedo_mazo","wood_spikes","izanagi","gedo_chain"]),

C("Indra Otsutsuki","Legendary","Lightning","Wanderer","Otsutsuki",None,
  340,400,240,390,560,"Six Paths Susanoo",13000,
  {"hp":520,"atk":520,"def":310,"speed":450},
  ["indraarow","susanoo_arrow","kirin","perfect_susanoo"]),

C("Momoshiki Otsutsuki","Legendary","Yang","Akatsuki","Otsutsuki",None,
  370,410,270,360,590,"Momoshiki Transformed",13000,
  {"hp":580,"atk":540,"def":360,"speed":420},
  ["planetary_dev","almighty_push","tbb","sage_truth_fist"]),

C("Jigen","Legendary","Yang","Akatsuki","Otsutsuki",None,
  380,415,280,370,600,"Isshiki Karma Activated",13500,
  {"hp":600,"atk":560,"def":360,"speed":440},
  ["almighty_push","gravity_pull","planetary_dev","chibaku_tensei"]),

C("Toneri Otsutsuki","Legendary","Yin-Yang","Wanderer","Tsutsuki",None,
  360,400,280,370,580,"Tenseigan Chakra Mode",12500,
  {"hp":560,"atk":530,"def":350,"speed":440},
  ["six_paths_sage","chibaku_tensei","tengai_meteor","limbo"]),

C("Kakashi (6 Paths Copy)","Legendary","Lightning","Konoha","Hatake",None,
  330,390,260,380,550,"Six Paths Susanoo Kakashi",11500,
  {"hp":480,"atk":510,"def":330,"speed":440},
  ["raikiri","kirin","perfect_susanoo","koto_amatsukami"]),

# ══ EPIC ════════════════════════════════════════════════════════
C("Kakashi Hatake","Epic","Lightning","Konoha","Hatake",None,
  295,325,235,350,480,"Dual Mangekyou Susanoo",9000,
  {"hp":410,"atk":450,"def":295,"speed":400},
  ["chidori","raikiri","vanishing_strike","susanoo_arrow"]),

C("Jiraiya","Epic","Wind","Konoha","Uzumaki",None,
  335,345,225,310,500,"Sage Mode Toad Sage",8500,
  {"hp":460,"atk":460,"def":285,"speed":360},
  ["rasenshuriken","summoning_toad","toad_fire","sage_mode_atk"]),

C("Tsunade","Epic","Medical","Konoha","Senju",None,
  410,370,290,300,490,"Strength of Hundred Seal",8000,
  {"hp":700,"atk":460,"def":360,"speed":330},
  ["monster_punch","mystical_palm","healing_seal","katsuyu"]),

C("Orochimaru","Epic","Yin","Oto","Orochimaru",None,
  310,345,250,315,520,"True Form White Snake",8500,
  {"hp":415,"atk":430,"def":300,"speed":350},
  ["eight_branches","kusanagi","summoning_snake","corpse_rein"]),

C("Might Guy","Epic","Taijutsu","Konoha","Lee",None,
  305,355,205,450,160,"Eighth Gate Gate of Death",8000,
  {"hp":510,"atk":710,"def":80,"speed":700},
  ["dynamic_entry","evening_elephant","night_guy","strong_fist"]),

C("Killer Bee","Epic","Lightning","Kumo","Uzumaki",None,
  345,350,245,340,510,"Full Gyuki Transformation",9500,
  {"hp":610,"atk":490,"def":330,"speed":395},
  ["lariat","lariat2","thunder_blade","tbb"],"Gyuki"),

C("A (Fourth Raikage)","Epic","Lightning","Kumo","Darui",None,
  355,375,260,430,490,"Lightning Armor Full Power",9000,
  {"hp":500,"atk":500,"def":330,"speed":530},
  ["thunder_god","lariat","lightning_ball","black_lightning"]),

C("Onoki","Epic","Earth","Iwa","Kaguya",None,
  330,355,280,280,490,"Particle Style Maximum",8500,
  {"hp":450,"atk":470,"def":360,"speed":310},
  ["dust_release","particle_ray","rock_avalanche","earth_prison"]),

C("Mei Terumi","Epic","Water","Kiri","Terumi",None,
  290,315,235,310,470,"Dual Kekkei Genkai",8000,
  {"hp":390,"atk":410,"def":300,"speed":360},
  ["lava_melt","lava_giant","boil_steam","water_shark"]),

C("Deidara","Epic","Explosion","Akatsuki","Deidara",None,
  280,335,200,360,490,"C0 Final Art",8500,
  {"hp":410,"atk":510,"def":160,"speed":410},
  ["c1_birds","c2_dragon","c3_bomb","c0_ultimate"]),

C("Sasori","Epic","Earth","Akatsuki","Sasori",None,
  295,325,290,310,480,"Hiruko True Form",8000,
  {"hp":460,"atk":420,"def":410,"speed":345},
  ["scorpion_tail","hundred_puppets","puppet_3rd","iron_sand"]),

C("Kisame Hoshigaki","Epic","Water","Akatsuki","Momochi",None,
  380,340,260,310,500,"Shark Skin Fusion",8500,
  {"hp":560,"atk":460,"def":340,"speed":360},
  ["water_shark","great_flood","hidden_mist","water_dragon"]),

C("Kakuzu","Epic","Earth","Akatsuki","Kakuzu",None,
  360,325,285,295,495,"Five Hearts Mode",8000,
  {"hp":620,"atk":420,"def":380,"speed":325},
  ["earth_spear","fire_dragon","wind_wall","water_bullet"]),

C("Hidan","Epic","Yin","Akatsuki","Hidan",None,
  999,285,310,275,440,"Jashin Immortal Mode",7500,
  {"hp":999,"atk":390,"def":360,"speed":295},
  ["jashin_curse","shadow_bind","ghost_blade","kagura_mind"]),

C("Konan","Epic","Water","Akatsuki","Konan",None,
  275,300,225,315,460,"Paper Ocean Mode",8000,
  {"hp":370,"atk":395,"def":290,"speed":365},
  ["paper_bomb_sea","paper_shuriken","water_bullet","wind_wall"]),

C("Kabuto (Sage Mode)","Epic","Medical","Oto","Haruno",None,
  305,335,245,310,490,"Ryuchi Cave Sage Mode",8000,
  {"hp":415,"atk":440,"def":320,"speed":365},
  ["chakra_scalpel","poison_gas","sage_mode_atk","summoning_snake"]),

C("Yamato","Epic","Wood","Konoha","Senju",None,
  300,310,250,300,470,"Full Wood Suppression",7500,
  {"hp":410,"atk":410,"def":330,"speed":350},
  ["wood_dragon","wood_spikes","forest_trap","wood_clone"]),

C("Shisui Uchiha","Epic","Fire","Konoha","Uchiha",None,
  295,360,230,400,510,"Kotoamatsukami Mangekyou",9000,
  {"hp":400,"atk":470,"def":295,"speed":455},
  ["koto_amatsukami","amaterasu","susanoo_arrow","izanagi"]),

C("Gaara","Epic","Sand","Suna","Subaku",None,
  315,310,365,285,470,"Shukaku Partial Release",8000,
  {"hp":520,"atk":400,"def":480,"speed":315},
  ["sand_coffin","sand_burial","sand_storm","shukaku_blast"],"Shukaku"),

C("Yahiko","Epic","Wind","Akatsuki","Uzumaki",None,
  285,320,220,330,470,"Deva Path Pain",8500,
  {"hp":390,"atk":420,"def":285,"speed":385},
  ["shinra_tensei","almighty_push","wind_cutter","rasengan"]),

C("Kushina Uzumaki","Epic","Yang","Konoha","Uzumaki",None,
  320,330,235,320,500,"Nine-Tails Chakra Mode",8500,
  {"hp":470,"atk":435,"def":310,"speed":375},
  ["tbb","gedo_chain","rasengan","clone_barrage"],"Kurama"),

C("Tobirama Senju","Epic","Water","Konoha","Senju",None,
  305,345,240,370,500,"Edo Tensei Mastery",8000,
  {"hp":420,"atk":450,"def":310,"speed":425},
  ["water_dragon","great_flood","ftg","shadow_clone"]),

C("Hiruzen Sarutobi","Epic","Fire","Konoha","Sarutobi",None,
  315,340,250,300,500,"God of Shinobi Prime",8500,
  {"hp":430,"atk":450,"def":330,"speed":350},
  ["earth_spear","fireball","summoning_toad","dust_release"]),

C("Ashura Otsutsuki","Epic","Wood","Wanderer","Otsutsuki",None,
  330,350,270,310,510,"Six Paths Yang Power",9000,
  {"hp":460,"atk":460,"def":360,"speed":365},
  ["wood_golem","sage_mode_atk","rasengan","forest_trap"]),

C("Boruto Uzumaki","Epic","Lightning","Konoha","Uzumaki",None,
  295,335,215,370,490,"Karma Mark Phase 2",9000,
  {"hp":415,"atk":455,"def":280,"speed":440},
  ["chidori","rasengan","vanishing_strike","thunder_blade"]),

C("Kawaki","Epic","Yang","Konoha","Uzumaki",None,
  310,360,230,340,500,"Karma Seal Full Release",9500,
  {"hp":440,"atk":480,"def":305,"speed":400},
  ["almighty_push","sage_truth_fist","gedo_chain","tbb"]),

C("Koji Kashin","Epic","Fire","Konoha","Uzumaki",None,
  305,340,240,335,490,"Sage Mode Jiraiya Clone",8500,
  {"hp":420,"atk":450,"def":315,"speed":390},
  ["summoning_toad","toad_fire","sage_mode_atk","fire_dragon"]),

C("Ada","Epic","Yang","Akatsuki","Otsutsuki",None,
  285,330,225,350,480,"Senrigan Omniscience",8000,
  {"hp":395,"atk":440,"def":300,"speed":415},
  ["almighty_push","gravity_pull","chakra_burst","gedo_chain"]),

C("Boro","Epic","Water","Akatsuki","Uzumaki",None,
  380,340,280,310,470,"Scientific Regeneration",8000,
  {"hp":560,"atk":450,"def":365,"speed":355},
  ["acid_mist","water_wave","poison_gas","monster_punch"]),

C("Danzo Shimura","Epic","Wind","Konoha","Shimura",None,
  320,345,255,320,490,"Izanagi Ten Sharingan",8000,
  {"hp":435,"atk":455,"def":330,"speed":375},
  ["izanagi","wind_cutter","shadow_clone","izanami"]),

C("Yagura (4th Mizukage)","Epic","Water","Kiri","Hozuki",None,
  345,340,265,320,490,"Full Isobu Transformation",9000,
  {"hp":530,"atk":450,"def":355,"speed":375},
  ["water_dragon","great_flood","water_shark","hidden_mist"],"Isobu"),

C("Mu (2nd Tsuchikage)","Epic","Earth","Iwa","Kaguya",None,
  310,350,255,330,475,"Dust Release Mastery",8000,
  {"hp":420,"atk":465,"def":335,"speed":385},
  ["dust_release","particle_ray","earth_prison","mud_wave"]),

C("Third Raikage","Epic","Lightning","Kumo","Darui",None,
  370,385,285,400,480,"Hell Stab Full Power",9000,
  {"hp":510,"atk":510,"def":370,"speed":460},
  ["thunder_god","lariat","black_lightning","thunder_blade"]),

C("Utakata","Epic","Water","Kiri","Hozuki",None,
  340,325,250,310,480,"Full Saiken Transformation",8500,
  {"hp":510,"atk":435,"def":335,"speed":365},
  ["acid_mist","water_wave","water_shark","hidden_mist"],"Saiken"),

C("Konohamaru (Hokage)","Epic","Wind","Konoha","Sarutobi",None,
  300,330,235,325,470,"Rasengan Mastery Mode",8000,
  {"hp":410,"atk":445,"def":310,"speed":380},
  ["rasengan","shadow_clone","clone_barrage","wind_cutter"]),

# ══ RARE ════════════════════════════════════════════════════════
C("Rock Lee","Rare","Taijutsu","Konoha","Lee",None,
  285,335,185,425,205,"Eight Gates Gate of Wonder",7000,
  {"hp":410,"atk":610,"def":50,"speed":620},
  ["leaf_hurricane","primary_lotus","hidden_lotus","drunken_fist"]),

C("Neji Hyuga","Rare","Lightning","Konoha","Hyuga",None,
  275,305,245,365,450,"Eight Trigrams Empowerment",7000,
  {"hp":360,"atk":395,"def":315,"speed":415},
  ["byakugan_64","gentle_fist","rotation","twin_lions"]),

C("Shikamaru Nara","Rare","Yin","Konoha","Nara",None,
  265,255,235,275,450,"Shadow King Mode",6500,
  {"hp":345,"atk":330,"def":300,"speed":310},
  ["shadow_bind","shadow_stitch","shadow_king","mind_transfer"]),

C("Asuma Sarutobi","Rare","Wind","Konoha","Sarutobi",None,
  275,305,225,310,455,"Chakra Blades Mode",6500,
  {"hp":370,"atk":400,"def":295,"speed":360},
  ["wind_cutter","wind_wall","chakra_scalpel","ash_pile"]),

C("Sai","Rare","Wind","Konoha","Sarutobi",None,
  265,295,220,320,450,"Super Beast Ink Painting",6500,
  {"hp":355,"atk":390,"def":290,"speed":375},
  ["ink_bird","super_beast","wind_cutter","clone_barrage"]),

C("Hinata Hyuga","Rare","Water","Konoha","Hyuga",None,
  270,280,240,315,430,"Gentle Step Twin Lion Fists",6500,
  {"hp":345,"atk":370,"def":315,"speed":360},
  ["twin_lions","gentle_fist","rotation","byakugan_64"]),

C("Temari","Rare","Wind","Suna","Subaku",None,
  270,305,215,325,445,"Cyclone Scythe Mode",6500,
  {"hp":355,"atk":400,"def":280,"speed":375},
  ["wind_cutter","wind_wall","summoning_toad","sand_storm"]),

C("Kankuro","Rare","Puppet","Suna","Subaku",None,
  275,300,245,295,445,"Salamander Puppet Master",6500,
  {"hp":380,"atk":395,"def":325,"speed":340},
  ["crow_puppet","black_ant","scorpion_tail","sasori_combo"]),

C("Kimimaro","Rare","Earth","Oto","Kaguya",None,
  290,335,265,315,445,"Sage of Six Paths Bone",7000,
  {"hp":410,"atk":435,"def":350,"speed":360},
  ["camelia_dance","larch_dance","clematis_vine","bracken_dance"]),

C("Jugo","Rare","Yang","Oto","Uzumaki",None,
  330,340,260,305,455,"Full Cursed Seal Release",7000,
  {"hp":480,"atk":450,"def":345,"speed":350},
  ["taijutsu_combo","strong_fist","gedo_chain","wood_spikes"]),

C("Suigetsu Hozuki","Rare","Water","Kiri","Hozuki",None,
  270,305,220,320,440,"Full Liquid Form",6500,
  {"hp":355,"atk":400,"def":295,"speed":375},
  ["water_dragon","water_shark","great_flood","hidden_mist"]),

C("Karin","Rare","Yin","Oto","Uzumaki",None,
  260,270,230,295,445,"Chakra Chains Unleashed",6000,
  {"hp":345,"atk":360,"def":310,"speed":345},
  ["gedo_chain","chakra_scalpel","mystical_palm","kagura_mind"]),

C("Zabuza Momochi","Rare","Water","Kiri","Momochi",None,
  290,325,240,315,455,"Demon of the Mist",7000,
  {"hp":395,"atk":425,"def":320,"speed":370},
  ["hidden_mist","water_shark","water_dragon","ghost_blade"]),

C("Haku","Rare","Ice","Kiri","Yuki",None,
  265,300,235,370,445,"Crystal Ice Mirror System",6500,
  {"hp":355,"atk":395,"def":315,"speed":430},
  ["ice_mirrors","ice_dome","ice_needles","hidden_mist"]),

C("Darui","Rare","Lightning","Kumo","Darui",None,
  275,315,230,325,455,"Black Lightning Storm",7000,
  {"hp":375,"atk":415,"def":305,"speed":380},
  ["black_lightning","storm_shark","plasma_ball","thunder_blade"]),

C("Kurotsuchi","Rare","Earth","Iwa","Kaguya",None,
  270,305,250,305,445,"Quicklime Release",6500,
  {"hp":365,"atk":400,"def":335,"speed":360},
  ["earth_prison","mud_wave","rock_avalanche","earth_spear"]),

C("Chiyo","Rare","Puppet","Suna","Sasori",None,
  265,300,240,295,450,"Ten Puppets Mastery",6500,
  {"hp":355,"atk":395,"def":325,"speed":345},
  ["hundred_puppets","black_ant","scorpion_tail","poison_gas"]),

C("Ino Yamanaka","Rare","Yin","Konoha","Yamanaka",None,
  255,270,225,305,445,"Mind Body Transmission",6000,
  {"hp":340,"atk":360,"def":305,"speed":360},
  ["mind_transfer","kagura_mind","chakra_scalpel","mystical_palm"]),

C("Choji Akimichi","Rare","Earth","Konoha","Akimichi",None,
  310,310,255,280,440,"Butterfly Mode",6500,
  {"hp":450,"atk":420,"def":345,"speed":310},
  ["strong_fist","taijutsu_combo","rock_avalanche","butterfly_bomb"]),

C("Kiba Inuzuka","Rare","Wind","Konoha","Inuzuka",None,
  270,305,215,360,435,"Man-Beast Combination",6500,
  {"hp":370,"atk":405,"def":290,"speed":420},
  ["taijutsu_combo","fang_over_fang","dynamic_entry","clone_barrage"]),

C("Shino Aburame","Rare","Earth","Konoha","Aburame",None,
  265,275,245,290,440,"Parasitic Insect Armor",6000,
  {"hp":350,"atk":365,"def":330,"speed":340},
  ["insect_swarm","earth_prison","poison_gas","hidden_mist"]),

C("Anko Mitarashi","Rare","Yin","Konoha","Mitarashi",None,
  265,295,225,315,450,"Cursed Seal Mastery",6500,
  {"hp":355,"atk":390,"def":305,"speed":370},
  ["summoning_snake","poison_gas","shadow_bind","ghost_blade"]),

C("Sarada Uchiha","Rare","Fire","Konoha","Uchiha",None,
  270,315,225,340,455,"Three-Tomoe Sharingan",7000,
  {"hp":360,"atk":415,"def":300,"speed":400},
  ["chidori","fireball","monster_punch","vanishing_strike"]),

C("Mitsuki","Rare","Wind","Konoha","Orochimaru",None,
  270,310,220,365,455,"Sage Transformation",7000,
  {"hp":360,"atk":410,"def":295,"speed":430},
  ["wind_cutter","summoning_snake","lightning_ball","sage_mode_atk"]),

C("Fugaku Uchiha","Rare","Fire","Konoha","Uchiha",None,
  285,330,235,330,470,"Mangekyou Sharingan",7000,
  {"hp":385,"atk":435,"def":310,"speed":385},
  ["amaterasu","fireball","tsukuyomi","susanoo_arrow"]),

C("Pakura","Rare","Scorch","Suna","Pakura",None,
  270,310,220,325,450,"Scorch Release Mastery",7000,
  {"hp":365,"atk":410,"def":300,"speed":380},
  ["scorch_ball","wind_cutter","fire_dragon","ash_pile"]),

C("Rasa (4th Kazekage)","Rare","Sand","Suna","Rasa",None,
  285,320,255,300,460,"Gold Dust Wave",7000,
  {"hp":385,"atk":420,"def":340,"speed":350},
  ["iron_sand","sand_burial","metal_prison","sand_coffin"]),

C("Code","Rare","Yang","Akatsuki","Otsutsuki",None,
  295,340,230,355,465,"Claw Marks Full Release",7500,
  {"hp":400,"atk":445,"def":310,"speed":415},
  ["tbb","sage_truth_fist","gedo_chain","almighty_push"]),

C("Delta","Rare","Yang","Akatsuki","Uzumaki",None,
  280,330,230,350,455,"Scientific Ninja Tools",7000,
  {"hp":380,"atk":435,"def":310,"speed":410},
  ["thunder_blade","lariat","taijutsu_combo","lightning_ball"]),

C("Nagato (Young)","Rare","Yang","Akatsuki","Uzumaki",None,
  290,325,230,315,460,"Six Paths Awakening",7000,
  {"hp":390,"atk":430,"def":305,"speed":365},
  ["almighty_push","shinra_tensei","chibaku_tensei","gedo_chain"]),

C("Yugito Nii","Rare","Fire","Kumo","Nii",None,
  305,315,240,325,455,"Full Matatabi Transformation",7000,
  {"hp":440,"atk":420,"def":325,"speed":380},
  ["fireball","fire_dragon","fire_vortex","tbb"],"Matatabi"),

C("Himawari Uzumaki","Rare","Yang","Konoha","Uzumaki",None,
  270,295,230,310,445,"Byakugan Awakened",7000,
  {"hp":360,"atk":390,"def":310,"speed":365},
  ["gentle_fist","twin_lions","chakra_burst","tbb"]),

C("Metal Lee","Rare","Taijutsu","Konoha","Lee",None,
  270,300,205,380,210,"Inner Gate Opening",6500,
  {"hp":370,"atk":490,"def":60,"speed":540},
  ["leaf_hurricane","primary_lotus","strong_fist","taijutsu_combo"]),

C("Inojin Yamanaka","Rare","Yin","Konoha","Yamanaka",None,
  260,275,225,305,440,"Mind Transfer Art",6000,
  {"hp":345,"atk":365,"def":305,"speed":360},
  ["mind_transfer","ink_bird","super_beast","kagura_mind"]),

C("Shikadai Nara","Rare","Yin","Suna","Nara",None,
  260,265,230,285,445,"Shadow Stitching Mastery",6500,
  {"hp":345,"atk":352,"def":310,"speed":340},
  ["shadow_bind","shadow_stitch","shadow_king","genjutsu_bind"]),

C("Shinki","Rare","Metal","Suna","Rasa",None,
  275,310,255,305,450,"Iron Sand Full Control",7000,
  {"hp":370,"atk":410,"def":340,"speed":360},
  ["iron_sand","metal_prison","sand_coffin","puppet_wall"]),

C("Sumire Kakei","Rare","Water","Konoha","Kakei",None,
  265,285,230,315,445,"Gozu Tennou Release",6500,
  {"hp":350,"atk":380,"def":310,"speed":370},
  ["water_dragon","water_wave","wood_spikes","chakra_burst"]),

C("Mabui","Rare","Lightning","Kumo","Darui",None,
  260,295,225,330,440,"Transfer Technique",6000,
  {"hp":345,"atk":390,"def":305,"speed":385},
  ["thunder_blade","lightning_ball","plasma_cutter","vanishing_strike"]),

C("Samui","Rare","Lightning","Kumo","Darui",None,
  265,300,230,325,445,"Kumo Sword Style",6500,
  {"hp":350,"atk":395,"def":310,"speed":380},
  ["thunder_blade","black_lightning","sword_gale","plasma_cutter"]),

C("C (Kumo Jonin)","Rare","Lightning","Kumo","Darui",None,
  260,295,225,330,440,"Lightning Sensor Mode",6000,
  {"hp":345,"atk":390,"def":305,"speed":385},
  ["lightning_ball","thunder_blade","vanishing_strike","plasma_ball"]),

C("Deepa","Rare","Earth","Akatsuki","Ukki",None,
  295,325,270,310,455,"Carbon Release Shield",7000,
  {"hp":400,"atk":430,"def":360,"speed":365},
  ["earth_spear","stone_fist","rock_avalanche","earth_dragon"]),

C("Kinshiki Otsutsuki","Rare","Yang","Wanderer","Otsutsuki",None,
  310,330,265,310,460,"Divine Weapon Release",7000,
  {"hp":420,"atk":440,"def":350,"speed":365},
  ["almighty_push","planetary_dev","sage_truth_fist","gravity_pull"]),

C("Mangetsu Hozuki","Rare","Water","Kiri","Hozuki",None,
  275,310,225,320,450,"Seven Swords Mastery",7000,
  {"hp":370,"atk":410,"def":305,"speed":375},
  ["water_shark","water_dragon","great_flood","water_whip"]),

C("Ameyuri Ringo","Rare","Lightning","Kiri","Ringo",None,
  265,315,220,340,445,"Twin Thunder Swords",7000,
  {"hp":350,"atk":415,"def":300,"speed":400},
  ["thunder_blade","thunder_clap","black_lightning","plasma_cutter"]),

C("Raiga Kurosuki","Rare","Lightning","Kiri","Kurosuki",None,
  270,305,230,330,440,"Thunder Swords Combo",6500,
  {"hp":360,"atk":405,"def":310,"speed":385},
  ["thunder_blade","thunder_clap","lightning_ball","plasma_ball"]),

C("Zetsu White","Rare","Wood","Akatsuki","Zetsu",None,
  280,290,250,285,460,"White Zetsu Clone Army",6500,
  {"hp":375,"atk":385,"def":335,"speed":340},
  ["wood_clone","wood_spikes","insect_swarm","hidden_mist"]),

C("Zetsu Black","Rare","Yin","Akatsuki","Zetsu",None,
  270,305,240,295,455,"Kaguya's Will Manifest",7000,
  {"hp":360,"atk":400,"def":320,"speed":350},
  ["shadow_bind","mind_transfer","genjutsu_bind","dark_needle"]),

C("Rin Nohara","Rare","Medical","Konoha","Nohara",None,
  260,270,235,300,445,"Isobu Jinchuriki Form",7000,
  {"hp":345,"atk":360,"def":315,"speed":355},
  ["mystical_palm","chakra_scalpel","water_dragon","healing_seal"]),

C("Obito (Young)","Rare","Fire","Konoha","Uchiha",None,
  270,305,230,315,455,"Sharingan Awakening",7000,
  {"hp":360,"atk":400,"def":310,"speed":370},
  ["fireball","amaterasu","izanagi","ghost_blade"]),

C("Izuna Uchiha","Rare","Fire","Konoha","Uchiha",None,
  275,320,225,330,460,"Mangekyou Sharingan Izuna",7000,
  {"hp":370,"atk":420,"def":305,"speed":385},
  ["amaterasu","fireball","tsukuyomi","susanoo_arrow"]),

C("Kagami Uchiha","Rare","Fire","Konoha","Uchiha",None,
  270,310,225,325,450,"Mangekyo Sharingan",6500,
  {"hp":360,"atk":410,"def":305,"speed":380},
  ["fireball","fire_dragon","amaterasu","tsukuyomi"]),

C("Mito Uzumaki","Rare","Yang","Konoha","Uzumaki",None,
  295,295,250,300,470,"Kurama First Seal",7000,
  {"hp":400,"atk":390,"def":335,"speed":355},
  ["gedo_chain","chakra_chains","sealing_jutsu","tbb"],"Kurama"),

# ══ UNCOMMON ════════════════════════════════════════════════════
Q("Hanabi Hyuga","Uncommon","Lightning","Konoha","Hyuga",hp=255,atk=270,df=230,spd=310,cha=420,
  fm="Byakugan Mastery",fq=5500,fb={"hp":75,"atk":85,"def":80,"speed":55},
  moves=["gentle_fist","byakugan_64","rotation","twin_lions"]),
Q("Tenten","Uncommon","Metal","Konoha","Lee",hp=255,atk=275,df=225,spd=310,cha=415,
  fm="Ten Seals Mastery",fq=5000,fb={"hp":80,"atk":90,"def":80,"speed":55},
  moves=["ghost_blade","clone_barrage","earth_spear","metal_prison"]),
Q("Konohamaru Sarutobi","Uncommon","Wind","Konoha","Sarutobi",hp=260,atk=275,df=215,spd=310,cha=425,
  fm="Rasengan Mastery",fq=5500,fb={"hp":80,"atk":90,"def":80,"speed":55}),
Q("Iruka Umino","Uncommon","Wind","Konoha","Sarutobi",hp=250,atk=260,df=220,spd=300,cha=415,
  fm="Academy Jutsu Master",fq=4500,fb={"hp":80,"atk":85,"def":80,"speed":50}),
Q("Genma Shiranui","Uncommon","Wind","Konoha","Shiranui",hp=255,atk=265,df=220,spd=315,cha=415,
  fm="Senbon Mastery",fq=5000,fb={"hp":75,"atk":85,"def":75,"speed":55}),
Q("Karui","Uncommon","Lightning","Kumo","Darui",hp=255,atk=275,df=215,spd=325,cha=415,
  fm="Lightning Blade Style",fq=5000,fb={"hp":75,"atk":90,"def":80,"speed":55},
  moves=["thunder_blade","lightning_ball","ghost_blade","clone_barrage"]),
Q("Omoi","Uncommon","Lightning","Kumo","Darui",hp=255,atk=270,df=220,spd=320,cha=415,
  fm="Cloud Sword Technique",fq=5000,fb={"hp":75,"atk":90,"def":80,"speed":55},
  moves=["thunder_blade","lariat","lightning_ball","ghost_blade"]),
Q("Ao","Uncommon","Water","Kiri","Momochi",hp=255,atk=265,df=225,spd=305,cha=415,
  fm="Byakugan Stolen",fq=5000,fb={"hp":75,"atk":85,"def":80,"speed":55}),
Q("Chojuro","Uncommon","Water","Kiri","Momochi",hp=255,atk=270,df=230,spd=310,cha=415,
  fm="Hiramekarei Dual Blade",fq=5000,fb={"hp":75,"atk":85,"def":80,"speed":60}),
Q("Baki","Uncommon","Wind","Suna","Subaku",hp=250,atk=265,df=220,spd=310,cha=410,
  fm="Wind Style Master",fq=5000,fb={"hp":75,"atk":85,"def":75,"speed":55}),
Q("Inoichi Yamanaka","Uncommon","Yin","Konoha","Yamanaka",hp=255,atk=260,df=230,spd=295,cha=420,
  fm="Mind Body Transmission",fq=5000,fb={"hp":75,"atk":85,"def":80,"speed":55}),
Q("Shikaku Nara","Uncommon","Yin","Konoha","Nara",hp=255,atk=260,df=230,spd=285,cha=425,
  fm="Shadow King",fq=5000,fb={"hp":75,"atk":85,"def":80,"speed":55}),
Q("Sakon","Uncommon","Yin","Oto","Nara",hp=260,atk=275,df=225,spd=330,cha=415,
  fm="Orochimaru Elite",fq=5500,fb={"hp":85,"atk":90,"def":80,"speed":55}),
Q("Jirobo","Uncommon","Earth","Oto","Akimichi",hp=275,atk=280,df=255,spd=265,cha=405,
  fm="Curse Seal Earth Release",fq=5000,fb={"hp":85,"atk":95,"def":90,"speed":50}),
Q("Tayuya","Uncommon","Yin","Oto","Nara",hp=255,atk=265,df=225,spd=305,cha=415,
  fm="Demon Flute Genjutsu",fq=5000,fb={"hp":75,"atk":85,"def":75,"speed":55}),
Q("Kidomaru","Uncommon","Wood","Oto","Kaguya",hp=260,atk=270,df=235,spd=305,cha=415,
  fm="Spider Web Technique",fq=5000,fb={"hp":80,"atk":90,"def":80,"speed":55}),
Q("Kurenai Yuhi","Uncommon","Yin","Konoha","Yuhi",hp=255,atk=255,df=230,spd=300,cha=425,
  fm="Genjutsu Master",fq=5500,fb={"hp":75,"atk":85,"def":80,"speed":55}),
Q("Raidou Namiashi","Uncommon","Wind","Konoha","Namiashi",hp=255,atk=265,df=225,spd=305,cha=415,
  fm="ANBU Specialist",fq=5000,fb={"hp":75,"atk":85,"def":80,"speed":55}),
Q("Moegi","Uncommon","Wood","Konoha","Sarutobi",hp=250,atk=260,df=220,spd=300,cha=415,
  fm="Wood Release Awakening",fq=5000,fb={"hp":75,"atk":85,"def":80,"speed":55}),
Q("Chouji Butterfly","Uncommon","Earth","Konoha","Akimichi",hp=290,atk=285,df=245,spd=275,cha=415,
  fm="Butterfly Mode Wings",fq=5500,fb={"hp":90,"atk":95,"def":85,"speed":50}),
Q("Atsui","Uncommon","Lightning","Kumo","Darui",hp=255,atk=270,df=220,spd=315,cha=410,
  fm="Hot-Blooded Lightning",fq=4500,fb={"hp":75,"atk":85,"def":75,"speed":55}),
Q("Akatsuchi","Uncommon","Earth","Iwa","Kaguya",hp=275,atk=270,df=255,spd=270,cha=405,
  fm="Stone Golem Mode",fq=5000,fb={"hp":85,"atk":85,"def":90,"speed":45}),
Q("Karin (Uzumaki)","Uncommon","Yin","Akatsuki","Uzumaki",hp=255,atk=260,df=225,spd=300,cha=445,
  fm="Chakra Sensor Full",fq=5000,fb={"hp":75,"atk":80,"def":75,"speed":55}),
Q("Ebisu","Uncommon","Lightning","Konoha","Sarutobi",hp=250,atk=255,df=220,spd=295,cha=415,
  fm="Elite Jonin Style",fq=4500,fb={"hp":75,"atk":80,"def":75,"speed":50}),
Q("Hayate Gekko","Uncommon","Wind","Konoha","Gekko",hp=255,atk=265,df=225,spd=315,cha=415,
  fm="Dance Sword Technique",fq=5000,fb={"hp":75,"atk":85,"def":75,"speed":60}),
Q("Izumo Kamizuki","Uncommon","Water","Konoha","Kamizuki",hp=250,atk=260,df=225,spd=305,cha=410,
  fm="Gate Guard Jutsu",fq=4500,fb={"hp":75,"atk":80,"def":80,"speed":50}),
Q("Kotetsu Hagane","Uncommon","Earth","Konoha","Sarutobi",hp=252,atk=262,df=225,spd=302,cha=408,
  fm="Gate Guard Mode",fq=4500,fb={"hp":75,"atk":80,"def":80,"speed":50}),
Q("Yodo","Uncommon","Wind","Suna","Subaku",hp=250,atk=260,df=218,spd=308,cha=412,
  fm="Wind Puppet Control",fq=4500,fb={"hp":72,"atk":82,"def":72,"speed":52}),
Q("Araya","Uncommon","Earth","Suna","Kaguya",hp=268,atk=272,df=245,spd=282,cha=408,
  fm="Stone Armor Mode",fq=5000,fb={"hp":82,"atk":85,"def":88,"speed":42}),
Q("Denki Kaminarimon","Uncommon","Lightning","Konoha","Darui",hp=248,atk=258,df=218,spd=305,cha=412,
  fm="Lightning Circuit Mode",fq=4500,fb={"hp":72,"atk":82,"def":72,"speed":52}),
Q("Iwabe Yuino","Uncommon","Earth","Konoha","Kaguya",hp=265,atk=268,df=240,spd=278,cha=405,
  fm="Earth Style Awakening",fq=4500,fb={"hp":80,"atk":84,"def":84,"speed":45}),
Q("Namida","Uncommon","Water","Konoha","Nohara",hp=248,atk=252,df=220,spd=298,cha=408,
  fm="Cry Jutsu Mode",fq=4000,fb={"hp":70,"atk":75,"def":70,"speed":48}),
Q("Wasabi","Uncommon","Wind","Konoha","Inuzuka",hp=250,atk=258,df=218,spd=308,cha=408,
  fm="Cat-Fist Mode",fq=4500,fb={"hp":72,"atk":82,"def":72,"speed":52}),
Q("Gari","Uncommon","Explosion","Iwa","Deidara",hp=258,atk=270,df=222,spd=305,cha=412,
  fm="Explosion Style",fq=5000,fb={"hp":76,"atk":88,"def":75,"speed":52}),
Q("Yugao Uzuki","Uncommon","Wind","Konoha","Sarutobi",hp=255,atk=268,df=228,spd=315,cha=415,
  fm="Sword Dance Mode",fq=5000,fb={"hp":76,"atk":86,"def":78,"speed":56}),
Q("Torune Aburame","Uncommon","Earth","Konoha","Aburame",hp=260,atk=268,df=238,spd=295,cha=415,
  fm="Rinkaichuu Army",fq=5000,fb={"hp":78,"atk":86,"def":82,"speed":48}),
Q("Fu (ANBU)","Uncommon","Yin","Konoha","Shimura",hp=255,atk=268,df=228,spd=310,cha=415,
  fm="Root ANBU Mode",fq=5000,fb={"hp":76,"atk":88,"def":78,"speed":54}),
Q("Ibiki Morino","Uncommon","Yin","Konoha","Morino",hp=260,atk=262,df=238,spd=292,cha=420,
  fm="Interrogation Master",fq=5000,fb={"hp":78,"atk":82,"def":82,"speed":48}),
Q("Dan Kato","Uncommon","Yang","Konoha","Kato",hp=258,atk=265,df=228,spd=305,cha=415,
  fm="Spirit Body Mode",fq=5000,fb={"hp":78,"atk":84,"def":78,"speed":52}),
Q("Nawaki Senju","Uncommon","Wood","Konoha","Senju",hp=255,atk=262,df=228,spd=305,cha=415,
  fm="Wood Style Growth",fq=4500,fb={"hp":76,"atk":82,"def":78,"speed":52}),
Q("Jinin Akebino","Uncommon","Lightning","Kiri","Akebino",hp=258,atk=272,df=228,spd=312,cha=412,
  fm="Helmet Splitter Mode",fq=5000,fb={"hp":76,"atk":88,"def":78,"speed":54}),
Q("Kushimaru Kuriarare","Uncommon","Water","Kiri","Kuriarare",hp=255,atk=268,df=225,spd=318,cha=412,
  fm="Nuibari Sewing Mode",fq=5000,fb={"hp":75,"atk":86,"def":76,"speed":56}),
Q("Fuguki Suikazan","Uncommon","Water","Kiri","Suikazan",hp=268,atk=265,df=238,spd=298,cha=410,
  fm="Shark Skin Mode",fq=5000,fb={"hp":82,"atk":84,"def":82,"speed":50}),
Q("Jinpachi Munashi","Uncommon","Lightning","Kiri","Munashi",hp=260,atk=270,df=232,spd=308,cha=412,
  fm="Blast Sword Mode",fq=5000,fb={"hp":78,"atk":87,"def":78,"speed":52}),
Q("Aoba Yamashiro","Uncommon","Yin","Konoha","Sarutobi",hp=252,atk=260,df=222,spd=302,cha=415,
  fm="Crow Genjutsu",fq=4500,fb={"hp":74,"atk":82,"def":74,"speed":50}),
Q("Tekkai","Uncommon","Earth","Iwa","Kaguya",hp=265,atk=265,df=245,spd=272,cha=405,
  fm="Iron Boulder Mode",fq=4500,fb={"hp":80,"atk":82,"def":88,"speed":42}),

# ══ COMMON ══════════════════════════════════════════════════════
Q("Young Naruto","Common","Wind","Konoha","Uzumaki",hp=200,atk=205,df=155,spd=235,cha=300,
  fm="Sage Mode Attempt",fq=3000,fb={"hp":80,"atk":80,"def":40,"speed":60}),
Q("Academy Sasuke","Common","Lightning","Konoha","Uchiha",hp=190,atk=210,df=155,spd=235,cha=290,
  fm="Sharingan Awakened",fq=3000,fb={"hp":70,"atk":80,"def":40,"speed":60}),
Q("Konoha Chunin","Common","Wind","Konoha","Sarutobi",hp=180,atk=190,df=150,spd=210,cha=280,
  fm="Teamwork Formation",fq=2500,fb={"hp":60,"atk":70,"def":50,"speed":55}),
Q("Suna Genin","Common","Sand","Suna","Subaku",hp=175,atk=185,df=155,spd=205,cha=275,
  fm="Sand Wall Defense",fq=2500,fb={"hp":60,"atk":70,"def":55,"speed":55}),
Q("Kiri Mist Ninja","Common","Water","Kiri","Momochi",hp=180,atk=195,df=150,spd=215,cha=280,
  fm="Silent Killing Style",fq=2500,fb={"hp":65,"atk":70,"def":50,"speed":60}),
Q("Kumo Trainee","Common","Lightning","Kumo","Darui",hp=180,atk=195,df=150,spd=220,cha=275,
  fm="Lightning Style Basics",fq=2500,fb={"hp":65,"atk":70,"def":50,"speed":60}),
Q("Iwa Genin","Common","Earth","Iwa","Kaguya",hp=185,atk=185,df=165,spd=195,cha=270,
  fm="Stone Fist Technique",fq=2500,fb={"hp":65,"atk":70,"def":55,"speed":45}),
Q("Oto Sound Ninja","Common","Yin","Oto","Nara",hp=175,atk=195,df=145,spd=215,cha=280,
  fm="Sound Wave Jutsu",fq=2500,fb={"hp":60,"atk":70,"def":45,"speed":60}),
Q("Rogue Missing-nin","Common","Yin","Wanderer","Hidan",hp=180,atk=200,df=150,spd=215,cha=280,
  fm="Rogue Techniques",fq=2500,fb={"hp":65,"atk":75,"def":55,"speed":55}),
Q("ANBU Root Agent","Common","Lightning","Konoha","Hatake",hp=185,atk=205,df=155,spd=220,cha=280,
  fm="Root Training Protocol",fq=2500,fb={"hp":65,"atk":75,"def":55,"speed":60}),
Q("Konoha Jonin","Common","Wind","Konoha","Sarutobi",hp=185,atk=195,df=155,spd=215,cha=285,
  fm="Jonin Technique",fq=2800,fb={"hp":65,"atk":70,"def":55,"speed":60}),
Q("Suna Chunin","Common","Sand","Suna","Subaku",hp=178,atk=188,df=158,spd=208,cha=278,
  fm="Sand Art Master",fq=2500,fb={"hp":60,"atk":70,"def":55,"speed":55}),
Q("Kiri Swordsman","Common","Water","Kiri","Momochi",hp=182,atk=198,df=152,spd=218,cha=282,
  fm="Seven Swords Student",fq=2500,fb={"hp":62,"atk":72,"def":52,"speed":60}),
Q("Kumo Genin","Common","Lightning","Kumo","Darui",hp=178,atk=192,df=148,spd=218,cha=272,
  fm="Raiton Basics",fq=2500,fb={"hp":60,"atk":70,"def":48,"speed":60}),
Q("Iwa Chunin","Common","Earth","Iwa","Kaguya",hp=188,atk=188,df=168,spd=198,cha=272,
  fm="Earth Fortification",fq=2500,fb={"hp":65,"atk":68,"def":58,"speed":45}),
Q("Oto Genin","Common","Yin","Oto","Nara",hp=172,atk=192,df=142,spd=212,cha=278,
  fm="Sound Art Basics",fq=2200,fb={"hp":58,"atk":68,"def":42,"speed":55}),
Q("Wandering Ninja","Common","Yin","Wanderer","Hidan",hp=178,atk=196,df=148,spd=212,cha=276,
  fm="Wanderer's Way",fq=2200,fb={"hp":60,"atk":70,"def":50,"speed":55}),
Q("Konoha Genin","Common","Wind","Konoha","Sarutobi",hp=175,atk=185,df=148,spd=208,cha=275,
  fm="Team Coordination",fq=2000,fb={"hp":55,"atk":65,"def":45,"speed":55}),
Q("Akatsuki Spy","Common","Yin","Akatsuki","Hidan",hp=178,atk=198,df=148,spd=215,cha=280,
  fm="Double Agent Mode",fq=2500,fb={"hp":60,"atk":72,"def":48,"speed":58}),
Q("Medical Trainee","Common","Medical","Konoha","Haruno",hp=170,atk=175,df=155,spd=198,cha=280,
  fm="Medical Chakra Mode",fq=2500,fb={"hp":60,"atk":65,"def":55,"speed":50}),
Q("Sand Puppeteer","Common","Puppet","Suna","Sasori",hp=175,atk=190,df=158,spd=198,cha=275,
  fm="Puppet Master Basic",fq=2500,fb={"hp":58,"atk":68,"def":52,"speed":48}),
Q("Cloud Raikage Guard","Common","Lightning","Kumo","Darui",hp=182,atk=195,df=152,spd=218,cha=278,
  fm="Raikage Guard Mode",fq=2500,fb={"hp":62,"atk":70,"def":52,"speed":58}),
Q("Rain Ninja","Common","Water","Akatsuki","Konan",hp=175,atk=188,df=150,spd=210,cha=278,
  fm="Rain Hidden Style",fq=2200,fb={"hp":58,"atk":68,"def":50,"speed":55}),
Q("Zaku Abumi","Common","Wind","Oto","Nara",hp=175,atk=192,df=145,spd=215,cha=278,
  fm="Supersonic Wave Mode",fq=2500,fb={"hp":58,"atk":70,"def":45,"speed":60}),
Q("Kin Tsuchi","Common","Yin","Oto","Nara",hp=170,atk=185,df=145,spd=210,cha=278,
  fm="Bell Genjutsu Mode",fq=2000,fb={"hp":55,"atk":65,"def":45,"speed":55}),
Q("Dosu Kinuta","Common","Yin","Oto","Nara",hp=178,atk=190,df=148,spd=205,cha=278,
  fm="Sound Resonance Mode",fq=2200,fb={"hp":58,"atk":68,"def":48,"speed":52}),
Q("Inari (Wave)","Common","Taijutsu","Wanderer","Sarutobi",hp=160,atk=170,df=145,spd=195,cha=250,
  fm="Brave Heart Mode",fq=1500,fb={"hp":45,"atk":55,"def":40,"speed":50}),
Q("Young Sakura","Common","Medical","Konoha","Haruno",hp=168,atk=172,df=148,spd=198,cha=272,
  fm="Inner Sakura Release",fq=2000,fb={"hp":52,"atk":62,"def":48,"speed":48}),
Q("Young Ino","Common","Yin","Konoha","Yamanaka",hp=165,atk=170,df=145,spd=200,cha=275,
  fm="Mind Body Switch",fq=2000,fb={"hp":50,"atk":60,"def":45,"speed":50}),
Q("Young Shikamaru","Common","Yin","Konoha","Nara",hp=165,atk=168,df=148,spd=195,cha=275,
  fm="Shadow Bind Basic",fq=2000,fb={"hp":50,"atk":58,"def":48,"speed":48}),
Q("Young Choji","Common","Earth","Konoha","Akimichi",hp=188,atk=178,df=162,spd=185,cha=268,
  fm="Partial Expansion",fq=2000,fb={"hp":60,"atk":60,"def":55,"speed":40}),
Q("Young Hinata","Common","Water","Konoha","Hyuga",hp=165,atk=168,df=150,spd=200,cha=272,
  fm="Gentle Fist Basic",fq=2000,fb={"hp":50,"atk":58,"def":50,"speed":50},
  moves=["gentle_fist","twin_lions","rotation","byakugan_64"]),
Q("Young Kiba","Common","Wind","Konoha","Inuzuka",hp=170,atk=178,df=148,spd=210,cha=268,
  fm="Double Headed Wolf",fq=2000,fb={"hp":52,"atk":62,"def":45,"speed":58}),
Q("Young Shino","Common","Earth","Konoha","Aburame",hp=168,atk=170,df=150,spd=195,cha=270,
  fm="Bug Clone Mode",fq=2000,fb={"hp":52,"atk":60,"def":50,"speed":48}),
Q("Young Rock Lee","Common","Taijutsu","Konoha","Lee",hp=170,atk=180,df=140,spd=220,cha=180,
  fm="Training Weights Off",fq=2000,fb={"hp":50,"atk":70,"def":30,"speed":80}),
Q("Young Neji","Common","Lightning","Konoha","Hyuga",hp=168,atk=175,df=150,spd=210,cha=272,
  fm="Byakugan Activate",fq=2000,fb={"hp":50,"atk":62,"def":52,"speed":55},
  moves=["gentle_fist","rotation","byakugan_64","twin_lions"]),
Q("Young Tenten","Common","Metal","Konoha","Lee",hp=165,atk=172,df=148,spd=205,cha=268,
  fm="Scrolls Unleashed",fq=2000,fb={"hp":50,"atk":62,"def":48,"speed":52},
  moves=["ghost_blade","clone_barrage","earth_spear","metal_prison"]),
Q("Young Gaara","Common","Sand","Suna","Subaku",hp=175,atk=182,df=165,spd=190,cha=278,
  fm="Sand Shield Absolute",fq=2200,fb={"hp":55,"atk":62,"def":58,"speed":45}),
Q("Young Temari","Common","Wind","Suna","Subaku",hp=168,atk=175,df=148,spd=210,cha=270,
  fm="Fan Cyclone Mode",fq=2000,fb={"hp":52,"atk":62,"def":48,"speed":55}),
Q("Young Kankuro","Common","Puppet","Suna","Subaku",hp=170,atk=175,df=152,spd=200,cha=268,
  fm="Puppet Strings",fq=2000,fb={"hp":52,"atk":62,"def":50,"speed":48}),
Q("Academy Graduate","Common","Wind","Konoha","Sarutobi",hp=160,atk=165,df=140,spd=190,cha=260,
  fm="Genin Spirit",fq=1500,fb={"hp":45,"atk":55,"def":40,"speed":48}),
Q("Hidden Grass Ninja","Common","Earth","Wanderer","Sarutobi",hp=172,atk=178,df=150,spd=198,cha=268,
  fm="Grass Camouflage",fq=2000,fb={"hp":52,"atk":60,"def":48,"speed":50}),
Q("Hidden Rain Ninja","Common","Water","Akatsuki","Konan",hp=170,atk=178,df=148,spd=200,cha=270,
  fm="Rain Bullet Barrage",fq=2000,fb={"hp":52,"atk":62,"def":48,"speed":52}),
Q("Waterfall Ninja","Common","Water","Wanderer","Sarutobi",hp=170,atk=175,df=150,spd=200,cha=268,
  fm="Waterfall Style",fq=2000,fb={"hp":52,"atk":60,"def":50,"speed":52}),
Q("Rock Ninja","Common","Earth","Iwa","Kaguya",hp=182,atk=182,df=162,spd=192,cha=265,
  fm="Earth Style Basic",fq=2000,fb={"hp":58,"atk":62,"def":55,"speed":42}),
Q("Lightning Genin","Common","Lightning","Kumo","Darui",hp=175,atk=188,df=148,spd=215,cha=272,
  fm="Thunder Awakening",fq=2000,fb={"hp":55,"atk":68,"def":45,"speed":58}),
Q("Fire Trainee","Common","Fire","Konoha","Uchiha",hp=172,atk=185,df=148,spd=205,cha=272,
  fm="Fire Style Basics",fq=2000,fb={"hp":52,"atk":65,"def":45,"speed":52}),
Q("Ice Genin","Common","Ice","Kiri","Yuki",hp=168,atk=175,df=150,spd=205,cha=268,
  fm="Ice Style Awakening",fq=2000,fb={"hp":52,"atk":60,"def":50,"speed":52}),
Q("Puppet Genin","Common","Puppet","Suna","Sasori",hp=170,atk=178,df=155,spd=195,cha=268,
  fm="Puppet Control Basic",fq=2000,fb={"hp":52,"atk":62,"def":52,"speed":45}),
Q("Medical Genin","Common","Medical","Konoha","Haruno",hp=165,atk=168,df=152,spd=198,cha=275,
  fm="Healing Basics",fq=2000,fb={"hp":50,"atk":58,"def":50,"speed":48}),
Q("Explosion Trainee","Common","Explosion","Iwa","Deidara",hp=170,atk=185,df=145,spd=200,cha=268,
  fm="Clay Bomb Basic",fq=2000,fb={"hp":52,"atk":68,"def":42,"speed":52}),
Q("Taijutsu Specialist","Common","Taijutsu","Konoha","Lee",hp=175,atk=188,df=148,spd=220,cha=220,
  fm="Gate Opening Basic",fq=2000,fb={"hp":52,"atk":70,"def":38,"speed":68}),
Q("Yin Style Ninja","Common","Yin","Oto","Nara",hp=168,atk=180,df=145,spd=205,cha=275,
  fm="Genjutsu Release",fq=2000,fb={"hp":50,"atk":62,"def":43,"speed":52}),
Q("Yang Style Ninja","Common","Yang","Wanderer","Uzumaki",hp=178,atk=185,df=150,spd=205,cha=278,
  fm="Yang Power Surge",fq=2200,fb={"hp":58,"atk":65,"def":50,"speed":52}),
Q("Wood Style Trainee","Common","Wood","Konoha","Senju",hp=178,atk=178,df=155,spd=200,cha=275,
  fm="Wood Sprout Mode",fq=2200,fb={"hp":58,"atk":60,"def":52,"speed":48}),
Q("Lava Genin","Common","Lava","Iwa","Terumi",hp=175,atk=182,df=150,spd=198,cha=272,
  fm="Lava Style Basic",fq=2200,fb={"hp":55,"atk":64,"def":48,"speed":48}),
Q("Storm Trainee","Common","Storm","Kumo","Darui",hp=172,atk=182,df=148,spd=210,cha=272,
  fm="Storm Release Basic",fq=2200,fb={"hp":52,"atk":64,"def":46,"speed":55}),
Q("Sand Jonin","Common","Sand","Suna","Subaku",hp=182,atk=192,df=158,spd=210,cha=278,
  fm="Desert Burial Prep",fq=2500,fb={"hp":60,"atk":68,"def":55,"speed":55}),
Q("Mist Assassin","Common","Water","Kiri","Momochi",hp=178,atk=195,df=150,spd=218,cha=278,
  fm="Silent Kill Mode",fq=2500,fb={"hp":58,"atk":70,"def":48,"speed":60}),
Q("Stone Warrior","Common","Earth","Iwa","Kaguya",hp=188,atk=185,df=168,spd=195,cha=268,
  fm="Stone Armor Full",fq=2500,fb={"hp":65,"atk":65,"def":60,"speed":42}),
Q("Lightning Raider","Common","Lightning","Kumo","Darui",hp=178,atk=195,df=150,spd=220,cha=275,
  fm="Thunder Strike Mode",fq=2500,fb={"hp":58,"atk":70,"def":48,"speed":62}),
Q("Rogue Jonin","Common","Yin","Wanderer","Hidan",hp=188,atk=200,df=155,spd=215,cha=282,
  fm="Rogue Elite Mode",fq=2800,fb={"hp":62,"atk":75,"def":52,"speed":58}),
Q("Akatsuki Recruit","Common","Yin","Akatsuki","Hidan",hp=178,atk=195,df=150,spd=212,cha=280,
  fm="Akatsuki Initiate",fq=2500,fb={"hp":60,"atk":72,"def":50,"speed":56}),
Q("Dragon Country Ninja","Common","Fire","Wanderer","Sarutobi",hp=175,atk=185,df=150,spd=205,cha=272,
  fm="Dragon Flame Mode",fq=2200,fb={"hp":55,"atk":65,"def":48,"speed":52}),
Q("Waterfall Guard","Common","Water","Wanderer","Hozuki",hp=175,atk=182,df=152,spd=205,cha=272,
  fm="Water Clone Defense",fq=2200,fb={"hp":55,"atk":62,"def":52,"speed":52}),
Q("Snow Ninja","Common","Ice","Kiri","Yuki",hp=170,atk=178,df=150,spd=208,cha=270,
  fm="Ice Shield Mode",fq=2200,fb={"hp":52,"atk":62,"def":50,"speed":54}),
Q("Forest Ninja","Common","Wood","Konoha","Senju",hp=175,atk=178,df=152,spd=200,cha=272,
  fm="Forest Camouflage",fq=2200,fb={"hp":55,"atk":60,"def":52,"speed":50}),
Q("Iron Country Samurai","Common","Metal","Wanderer","Rasa",hp=182,atk=188,df=165,spd=198,cha=265,
  fm="Samurai Blade Mode",fq=2200,fb={"hp":58,"atk":65,"def":58,"speed":46}),
Q("Poison Specialist","Common","Poison","Kiri","Haruno",hp=168,atk=178,df=148,spd=202,cha=272,
  fm="Toxin Master",fq=2200,fb={"hp":50,"atk":62,"def":46,"speed":52}),
Q("Ghost Clan Ninja","Common","Ghost","Wanderer","Hidan",hp=172,atk=180,df=148,spd=208,cha=272,
  fm="Phantom Form",fq=2200,fb={"hp":52,"atk":62,"def":46,"speed":54}),
Q("Dust Country Guard","Common","Earth","Iwa","Kaguya",hp=180,atk=182,df=162,spd=195,cha=268,
  fm="Earth Dome Guard",fq=2200,fb={"hp":58,"atk":62,"def":56,"speed":44}),
Q("Skyfire Ninja","Common","Fire","Wanderer","Sarutobi",hp=172,atk=185,df=148,spd=205,cha=272,
  fm="Sky Flame Mode",fq=2200,fb={"hp":52,"atk":66,"def":46,"speed":52}),

# ══ NEW MYTHIC ═══════════════════════════════════════════════════
C("Naruto (Six Paths Sage Mode)","Mythic","Wind","Konoha","Uzumaki",None,
  520,540,310,490,720,"Six Paths Chakra Cloak",22000,
  {"hp":820,"atk":680,"def":290,"speed":620},
  ["rasengan","rasenshuriken","tbb","six_paths_sage"],"Kurama"),

C("Ten-Tails Obito","Mythic","Yin-Yang","Akatsuki","Uchiha",None,
  590,530,410,390,740,"Ten-Tails Full Absorption",21000,
  {"hp":940,"atk":700,"def":530,"speed":470},
  ["infinite_tsuk","tengai_meteor","gedo_mazo","limbo"]),

# ══ NEW LEGENDARY ════════════════════════════════════════════════
C("Sakura Haruno (Byakugou)","Legendary","Medical","Konoha","Haruno",None,
  420,390,280,340,560,"Strength of Hundred Seal Burst",13000,
  {"hp":750,"atk":540,"def":380,"speed":395},
  ["monster_punch","mystical_palm","healing_seal","katsuyu"]),

C("Rock Lee (Eight Gates)","Legendary","Taijutsu","Konoha","Lee",None,
  350,430,200,510,180,"Gate of Death Absolute",14000,
  {"hp":540,"atk":760,"def":60,"speed":780},
  ["evening_elephant","night_guy","dynamic_entry","primary_lotus"]),

C("Gaara (Fifth Kazekage)","Legendary","Sand","Suna","Subaku",None,
  400,380,390,320,580,"Shukaku Full Release",12500,
  {"hp":680,"atk":490,"def":530,"speed":370},
  ["sand_burial","sand_coffin","shukaku_blast","sand_storm"],"Shukaku"),

C("Kakashi (Sixth Hokage)","Legendary","Lightning","Konoha","Hatake",None,
  340,400,260,400,560,"Kamui Shuriken Mastery",12000,
  {"hp":500,"atk":530,"def":340,"speed":465},
  ["raikiri","vanishing_strike","chidori","koto_amatsukami"]),

# ══ NEW EPIC ═════════════════════════════════════════════════════
C("Hanzo of the Salamander","Epic","Poison","Wanderer","Hanzo",None,
  340,350,260,320,490,"Salamander Half-Body Sage",9000,
  {"hp":480,"atk":460,"def":340,"speed":375},
  ["poison_gas","acid_mist","summoning_snake","ghost_blade"]),

C("Gengetsu Hozuki","Epic","Water","Kiri","Hozuki",None,
  360,355,265,330,505,"Steaming Danger Tyranny",9000,
  {"hp":520,"atk":470,"def":350,"speed":385},
  ["water_shark","great_flood","hidden_mist","water_dragon"]),

C("Shin Uchiha","Epic","Fire","Akatsuki","Uchiha",None,
  325,365,245,345,490,"Transplanted Sharingan Army",8500,
  {"hp":445,"atk":480,"def":320,"speed":405},
  ["fireball","amaterasu","izanagi","chidori"]),

C("Urashiki Otsutsuki","Epic","Yin-Yang","Wanderer","Otsutsuki",None,
  360,380,270,355,510,"Time Lapse Rinnegan",9500,
  {"hp":510,"atk":500,"def":355,"speed":420},
  ["almighty_push","gravity_pull","tbb","sage_truth_fist"]),

C("Chojuro (Sixth Mizukage)","Epic","Water","Kiri","Hozuki",None,
  320,350,255,340,480,"Hiramekarei Twin Blade",8500,
  {"hp":435,"atk":460,"def":335,"speed":400},
  ["water_shark","water_dragon","great_flood","hidden_mist"]),

C("Han (Jinchuriki)","Epic","Earth","Wanderer","Kaguya",None,
  380,355,285,320,490,"Kokuo Steam Armor",9000,
  {"hp":560,"atk":470,"def":375,"speed":375},
  ["earth_spear","mud_wave","dust_release","strong_fist"]),

C("Roshi (Four Tails)","Epic","Lava","Iwa","Kaguya",None,
  360,360,265,310,490,"Son Goku Full Release",9000,
  {"hp":520,"atk":475,"def":350,"speed":365},
  ["lava_melt","lava_giant","fireball","rock_avalanche"]),

C("Kinkaku","Epic","Wind","Wanderer","Uzumaki",None,
  345,360,255,340,500,"Gold Dust Incarnation",8500,
  {"hp":490,"atk":475,"def":335,"speed":400},
  ["tbb","wind_cutter","wind_wall","clone_barrage"]),

# ══ NEW RARE ═════════════════════════════════════════════════════
C("Mifune","Rare","Metal","Wanderer","Rasa",None,
  280,320,240,380,445,"Iai Sword Mastery",7000,
  {"hp":375,"atk":420,"def":325,"speed":440},
  ["ghost_blade","sword_gale","vanishing_strike","strong_fist"]),

C("Toroi","Rare","Lightning","Kumo","Darui",None,
  275,315,235,335,455,"Magnetic Shuriken Style",7000,
  {"hp":370,"atk":415,"def":315,"speed":390},
  ["thunder_blade","lightning_ball","plasma_cutter","vanishing_strike"]),

C("Chino","Rare","Fire","Wanderer","Sarutobi",None,
  270,305,225,330,450,"Exploding Flame Signal Fire",6500,
  {"hp":360,"atk":400,"def":305,"speed":385},
  ["fireball","fire_dragon","ash_pile","fire_vortex"]),

C("Nowaki","Rare","Wind","Wanderer","Sarutobi",None,
  268,308,220,338,445,"Typhoon Release Mode",6500,
  {"hp":358,"atk":405,"def":300,"speed":395},
  ["wind_cutter","wind_wall","clone_barrage","sand_storm"]),

C("Guren","Rare","Ice","Oto","Yuki",None,
  275,315,240,325,450,"Crystal Ice Release",7000,
  {"hp":370,"atk":415,"def":320,"speed":380},
  ["ice_mirrors","ice_dome","ice_needles","water_shark"]),

C("Fuu (Seven Tails)","Rare","Wind","Wanderer","Uzumaki",None,
  295,310,235,340,455,"Chomei Full Release",7000,
  {"hp":400,"atk":410,"def":315,"speed":400},
  ["wind_cutter","clone_barrage","tbb","wind_wall"]),

# ══ 110+ NEW CHARACTERS (dattebayo API confirmed) ════════════════

# ── NEW EPIC ─────────────────────────────────────────────────────
C("Yagura Karatachi","Epic","Water","Kiri","Yagura",None,
  340,355,265,325,490,"Isobu Full Three-Tails Release",9000,
  {"hp":480,"atk":465,"def":345,"speed":380},
  ["water_shark","great_flood","water_dragon","hidden_mist"],"Isobu"),

C("Ginkaku","Epic","Wind","Wanderer","Uzumaki",None,
  340,358,255,338,498,"Silver Nine-Tails Chakra",8500,
  {"hp":475,"atk":468,"def":335,"speed":395},
  ["tbb","wind_cutter","wind_wall","chakra_chains"]),

C("Dan Kato","Epic","Yin","Konoha","Kato",None,
  320,340,250,315,485,"Spirit Release Possession",8500,
  {"hp":445,"atk":450,"def":330,"speed":370},
  ["genjutsu_bind","ghost_blade","dark_needle","shadow_bind"]),

C("Third Kazekage","Epic","Metal","Suna","Rasa",None,
  350,360,285,310,490,"Iron Sand Marionette Control",9000,
  {"hp":500,"atk":475,"def":375,"speed":360},
  ["iron_sand","metal_prison","sand_coffin","puppet_wall"]),

C("Mu (Second Tsuchikage)","Epic","Earth","Iwa","Kaguya",None,
  330,355,255,345,480,"Dust Release Erase Clone",8500,
  {"hp":455,"atk":465,"def":335,"speed":405},
  ["dust_release","earth_spear","mud_wave","vanishing_strike"]),

C("Daemon","Epic","Yang","Wanderer","Otsutsuki",None,
  360,350,280,360,505,"Reflective Killing Intent",9000,
  {"hp":510,"atk":465,"def":365,"speed":425},
  ["tbb","taijutsu_combo","almighty_push","chakra_burst"]),

C("Fuguki Suikazan","Epic","Water","Kiri","Momochi",None,
  345,352,268,325,485,"Seven Swords Hydration Master",8500,
  {"hp":490,"atk":462,"def":350,"speed":380},
  ["water_shark","water_dragon","great_flood","sword_gale"]),

C("Kimimaro","Epic","Earth","Wanderer","Kaguya",None,
  350,365,260,335,490,"Dance of the Seedling Fern",9000,
  {"hp":495,"atk":475,"def":340,"speed":395},
  ["earth_spear","taijutsu_combo","strong_fist","ghost_blade"]),

# ── NEW RARE ─────────────────────────────────────────────────────
C("Kagura Karatachi","Rare","Water","Kiri","Momochi",None,
  275,315,230,340,450,"Samehada Bond Mastery",7000,
  {"hp":370,"atk":415,"def":310,"speed":400},
  ["water_shark","water_dragon","sword_gale","great_flood"]),

C("Wasabi Izuno","Rare","Fire","Konoha","Inuzuka",None,
  265,300,225,335,440,"Cat Fang Transformation",6500,
  {"hp":350,"atk":395,"def":305,"speed":395},
  ["fireball","taijutsu_combo","fire_dragon","leaf_hurricane"]),

C("Namida Suzumeno","Rare","Water","Konoha","Hyuga",None,
  260,285,235,315,445,"Ultrasonic Cry Release",6000,
  {"hp":345,"atk":380,"def":315,"speed":370},
  ["water_wave","genjutsu_bind","water_dragon","chakra_burst"]),

C("Iwabe Yuino","Rare","Earth","Konoha","Sarutobi",None,
  275,305,250,300,440,"Earth Style Mastery Mode",6500,
  {"hp":370,"atk":400,"def":335,"speed":355},
  ["earth_spear","stone_fist","rock_avalanche","mud_wave"]),

C("Nawaki","Rare","Earth","Konoha","Senju",None,
  265,295,230,310,445,"Senju Will Awakening",6500,
  {"hp":350,"atk":390,"def":310,"speed":365},
  ["rasengan","earth_spear","clone_barrage","chakra_burst"]),

C("Mikoto Uchiha","Rare","Fire","Konoha","Uchiha",None,
  265,300,230,315,445,"Sharingan Clan Mother",6500,
  {"hp":350,"atk":395,"def":310,"speed":370},
  ["fireball","amaterasu","tsukuyomi","fire_dragon"]),

C("Ebizo","Rare","Puppet","Suna","Sasori",None,
  260,295,250,285,450,"Elder Puppet Master Arts",6500,
  {"hp":345,"atk":390,"def":335,"speed":340},
  ["scorpion_tail","puppet_bomb","puppet_wall","sand_burial"]),

C("Choza Akimichi","Rare","Earth","Konoha","Akimichi",None,
  295,305,265,270,440,"Partial Expansion Jutsu",7000,
  {"hp":400,"atk":400,"def":355,"speed":320},
  ["earth_spear","stone_fist","taijutsu_combo","mud_wave"]),

C("Shibi Aburame","Rare","Earth","Konoha","Aburame",None,
  270,295,240,290,445,"Insect Clone Host Colony",6500,
  {"hp":360,"atk":390,"def":320,"speed":345},
  ["insect_swarm","poison_cloud","earth_spear","clone_barrage"]),

C("Tsume Inuzuka","Rare","Wind","Konoha","Inuzuka",None,
  265,300,225,335,440,"Passing Fang Twin Style",6500,
  {"hp":350,"atk":395,"def":305,"speed":395},
  ["fang_over_fang","wind_cutter","taijutsu_combo","clone_barrage"]),

C("Hiashi Hyuga","Rare","Lightning","Konoha","Hyuga",None,
  275,310,245,305,450,"Eight Trigrams Clan Strike",7000,
  {"hp":370,"atk":410,"def":325,"speed":360},
  ["gentle_fist","byakugan_64","rotation","twin_lions"]),

C("Hizashi Hyuga","Rare","Lightning","Konoha","Hyuga",None,
  270,300,240,300,445,"Gentle Fist Branch House",6500,
  {"hp":360,"atk":395,"def":320,"speed":355},
  ["gentle_fist","rotation","twin_palms","chakra_burst"]),

C("Amado","Rare","Yin","Akatsuki","Shimura",None,
  255,280,235,295,450,"Kara Scientific Ninja Tools",6000,
  {"hp":340,"atk":375,"def":315,"speed":350},
  ["thunder_blade","plasma_ball","dark_needle","genjutsu_bind"]),

C("Zaku Abumi","Rare","Wind","Oto","Orochimaru",None,
  265,305,220,340,440,"Decapitating Airwaves Release",6500,
  {"hp":350,"atk":400,"def":300,"speed":400},
  ["wind_cutter","wind_wall","vacuum_sphere","clone_barrage"]),

C("Kin Tsuchi","Rare","Yin","Oto","Orochimaru",None,
  260,290,225,325,445,"Bells and Needles Genjutsu",6000,
  {"hp":345,"atk":385,"def":305,"speed":380},
  ["genjutsu_bind","dark_needle","shadow_bind","kagura_mind"]),

C("Dosu Kinuta","Rare","Yin","Oto","Orochimaru",None,
  270,300,240,305,440,"Melody Arm Resonance Wave",6500,
  {"hp":360,"atk":395,"def":320,"speed":360},
  ["earth_spear","stone_fist","genjutsu_bind","dark_needle"]),

C("Udon","Rare","Water","Konoha","Sarutobi",None,
  260,285,230,310,440,"Snot Clone Water Style",6000,
  {"hp":345,"atk":380,"def":310,"speed":365},
  ["water_wave","water_dragon","clone_barrage","chakra_burst"]),

C("Yugao Uzuki","Rare","Water","Konoha","Hatake",None,
  265,305,235,330,445,"Moon-Like Sword Dance",6500,
  {"hp":350,"atk":400,"def":315,"speed":390},
  ["sword_gale","vanishing_strike","water_wave","clone_barrage"]),

C("Aoba Yamashiro","Rare","Yin","Konoha","Yamanaka",None,
  260,290,230,315,445,"Mind Reading Raven Technique",6000,
  {"hp":345,"atk":385,"def":310,"speed":370},
  ["mind_transfer","shadow_bind","genjutsu_bind","dark_needle"]),

C("Ibiki Morino","Rare","Yin","Konoha","Shimura",None,
  270,290,250,290,445,"Interrogation Torture Arts",6500,
  {"hp":360,"atk":385,"def":335,"speed":345},
  ["shadow_bind","genjutsu_bind","dark_needle","earth_spear"]),

C("Sora","Rare","Wind","Konoha","Uzumaki",None,
  285,315,220,330,460,"Nine-Tails Clone Kyubi Mode",7000,
  {"hp":385,"atk":415,"def":300,"speed":390},
  ["tbb","wind_cutter","rasengan","clone_barrage"]),

C("Minato (Young)","Rare","Wind","Konoha","Namikaze",None,
  280,320,230,360,450,"Flying Thunder God Seal Mark",7000,
  {"hp":375,"atk":420,"def":310,"speed":420},
  ["ftg","rasengan","wind_cutter","clone_barrage"]),

C("Kushina (Young)","Rare","Yang","Konoha","Uzumaki",None,
  280,305,235,305,455,"Adamantine Sealing Chains",7000,
  {"hp":375,"atk":400,"def":315,"speed":360},
  ["chakra_chains","gedo_chain","tbb","sealing_jutsu"],"Kurama"),

C("Jiraiya (Young)","Rare","Wind","Konoha","Namikaze",None,
  275,310,225,320,450,"Toad Summoning Training",7000,
  {"hp":370,"atk":410,"def":305,"speed":375},
  ["toad_fire","rasengan","summoning_snake","sage_mode_atk"]),

C("Hiruzen (Young)","Rare","Fire","Konoha","Sarutobi",None,
  285,310,250,310,455,"God of Shinobi Youth",7000,
  {"hp":385,"atk":410,"def":335,"speed":365},
  ["fireball","fire_dragon","earth_spear","wood_dragon"]),

# ── NEW UNCOMMON ─────────────────────────────────────────────────
Q("Naruto (Genin)","Uncommon","Wind","Konoha","Uzumaki",hp=255,atk=260,df=215,spd=310,cha=420,
  fm="Nine-Tails First Touch",fq=5000,fb={"hp":80,"atk":85,"def":75,"speed":55}),
Q("Sasuke (Genin)","Uncommon","Fire","Konoha","Uchiha",hp=250,atk=268,df=220,spd=318,cha=415,
  fm="Sharingan First Eye",fq=4500,fb={"hp":75,"atk":90,"def":75,"speed":60}),
Q("Sakura (Genin)","Uncommon","Medical","Konoha","Haruno",hp=248,atk=255,df=228,spd=300,cha=418,
  fm="Inner Sakura Power",fq=4500,fb={"hp":75,"atk":80,"def":80,"speed":55}),
Q("Lee (Genin)","Uncommon","Taijutsu","Konoha","Lee",hp=255,atk=270,df=215,spd=325,cha=205,
  fm="Eight Gates First Gate",fq=4500,fb={"hp":75,"atk":95,"def":70,"speed":65}),
Q("Neji (Genin)","Uncommon","Lightning","Konoha","Hyuga",hp=252,atk=265,df=228,spd=308,cha=418,
  fm="Byakugan Mastery",fq=4500,fb={"hp":75,"atk":85,"def":80,"speed":60},
  moves=["gentle_fist","rotation","byakugan_64","twin_lions"]),
Q("Shikamaru (Genin)","Uncommon","Yin","Konoha","Nara",hp=248,atk=252,df=228,spd=288,cha=420,
  fm="Shadow Bind First",fq=4500,fb={"hp":75,"atk":80,"def":80,"speed":55}),
Q("Temari (Genin)","Uncommon","Wind","Suna","Subaku",hp=250,atk=262,df=218,spd=308,cha=412,
  fm="Wind Fanning Style",fq=4500,fb={"hp":75,"atk":85,"def":75,"speed":60}),
Q("Kankuro (Genin)","Uncommon","Puppet","Suna","Subaku",hp=252,atk=260,df=225,spd=302,cha=412,
  fm="Puppet Control Art",fq=4500,fb={"hp":75,"atk":85,"def":80,"speed":55}),
Q("Itachi (Young)","Uncommon","Fire","Konoha","Uchiha",hp=250,atk=268,df=222,spd=318,cha=418,
  fm="Genius Prodigy Mode",fq=5000,fb={"hp":75,"atk":90,"def":75,"speed":60}),
Q("Obito (Genin)","Uncommon","Fire","Konoha","Uchiha",hp=250,atk=260,df=222,spd=308,cha=412,
  fm="Team Minato Days",fq=4500,fb={"hp":75,"atk":85,"def":75,"speed":55}),
Q("Kakashi (Genin)","Uncommon","Lightning","Konoha","Hatake",hp=252,atk=265,df=225,spd=320,cha=415,
  fm="Child Prodigy Jonin",fq=4500,fb={"hp":75,"atk":90,"def":75,"speed":60}),
Q("Rin (Genin)","Uncommon","Medical","Konoha","Nohara",hp=248,atk=252,df=228,spd=300,cha=418,
  fm="Medical Nin Training",fq=4500,fb={"hp":75,"atk":80,"def":80,"speed":55}),
Q("Minato (Chunin)","Uncommon","Wind","Konoha","Namikaze",hp=255,atk=270,df=220,spd=328,cha=418,
  fm="FTG Early Form",fq=5000,fb={"hp":80,"atk":90,"def":75,"speed":65}),
Q("Kushina (Teen)","Uncommon","Yang","Konoha","Uzumaki",hp=255,atk=262,df=228,spd=300,cha=422,
  fm="Uzumaki Chains Young",fq=5000,fb={"hp":80,"atk":85,"def":80,"speed":55}),
Q("Madara (Young)","Uncommon","Fire","Konoha","Uchiha",hp=262,atk=278,df=232,spd=325,cha=420,
  fm="Uchiha Clan Prodigy",fq=5000,fb={"hp":80,"atk":95,"def":80,"speed":65}),
Q("Hashirama (Young)","Uncommon","Wood","Konoha","Senju",hp=268,atk=268,df=258,spd=308,cha=422,
  fm="Wood Awakening Early",fq=5000,fb={"hp":85,"atk":85,"def":90,"speed":55}),
Q("Tobirama (Young)","Uncommon","Water","Konoha","Senju",hp=258,atk=268,df=238,spd=318,cha=415,
  fm="Teleport Technique",fq=5000,fb={"hp":80,"atk":88,"def":82,"speed":62}),
Q("Yahiko (Young)","Uncommon","Wind","Akatsuki","Uzumaki",hp=250,atk=258,df=220,spd=308,cha=415,
  fm="Amegakure Rebel",fq=4500,fb={"hp":75,"atk":85,"def":75,"speed":55}),
Q("Nagato (Child)","Uncommon","Yang","Akatsuki","Uzumaki",hp=252,atk=262,df=222,spd=305,cha=420,
  fm="Rinnegan Awakening",fq=5000,fb={"hp":75,"atk":85,"def":75,"speed":55}),
Q("Konan (Young)","Uncommon","Water","Akatsuki","Konan",hp=250,atk=258,df=225,spd=305,cha=418,
  fm="Paper Shuriken Style",fq=4500,fb={"hp":75,"atk":82,"def":78,"speed":55}),
Q("Jiraiya (Child)","Uncommon","Wind","Konoha","Namikaze",hp=252,atk=260,df=218,spd=312,cha=415,
  fm="Toad Sage Trainee",fq=4500,fb={"hp":75,"atk":85,"def":73,"speed":58}),
Q("Tsunade (Young)","Uncommon","Medical","Konoha","Senju",hp=265,atk=270,df=235,spd=298,cha=422,
  fm="Hundred Strength Training",fq=5000,fb={"hp":85,"atk":95,"def":80,"speed":50}),
Q("Orochimaru (Young)","Uncommon","Yin","Konoha","Orochimaru",hp=255,atk=265,df=225,spd=312,cha=418,
  fm="Snake Sage Trainee",fq=5000,fb={"hp":75,"atk":88,"def":75,"speed":60}),
Q("Kimimaro (Young)","Uncommon","Earth","Wanderer","Kaguya",hp=260,atk=268,df=238,spd=312,cha=408,
  fm="Bone Dance Early",fq=5000,fb={"hp":78,"atk":88,"def":80,"speed":58}),
Q("Sora (Young)","Uncommon","Wind","Konoha","Uzumaki",hp=252,atk=260,df=215,spd=318,cha=415,
  fm="Nine-Tails Trace",fq=4500,fb={"hp":75,"atk":85,"def":70,"speed":60}),
Q("Daemon (Young)","Uncommon","Yang","Wanderer","Otsutsuki",hp=255,atk=262,df=225,spd=318,cha=415,
  fm="Reflect Kill Early",fq=5000,fb={"hp":75,"atk":85,"def":75,"speed":62}),
Q("Amado (Young)","Uncommon","Yin","Akatsuki","Shimura",hp=248,atk=252,df=228,spd=295,cha=420,
  fm="Kara Lab Prototype",fq=4500,fb={"hp":72,"atk":78,"def":78,"speed":48}),
Q("Pakura (Young)","Uncommon","Scorch","Suna","Pakura",hp=252,atk=262,df=220,spd=308,cha=412,
  fm="Scorch Infuse Style",fq=4500,fb={"hp":75,"atk":85,"def":73,"speed":57}),
Q("Rasa (Young)","Uncommon","Sand","Suna","Rasa",hp=258,atk=265,df=235,spd=295,cha=415,
  fm="Gold Dust Trace",fq=4500,fb={"hp":78,"atk":85,"def":80,"speed":50}),
Q("Choza (Young)","Uncommon","Earth","Konoha","Akimichi",hp=275,atk=265,df=248,spd=265,cha=405,
  fm="Akimichi Expansion",fq=4500,fb={"hp":85,"atk":85,"def":88,"speed":42}),
Q("Shibi (Young)","Uncommon","Earth","Konoha","Aburame",hp=252,atk=255,df=238,spd=288,cha=415,
  fm="Insect Host Early",fq=4500,fb={"hp":75,"atk":78,"def":83,"speed":48}),
Q("Tsume (Young)","Uncommon","Wind","Konoha","Inuzuka",hp=252,atk=268,df=218,spd=322,cha=408,
  fm="Twin Fang Style",fq=4500,fb={"hp":75,"atk":88,"def":72,"speed":58}),
Q("Hiashi (Young)","Uncommon","Lightning","Konoha","Hyuga",hp=255,atk=270,df=240,spd=300,cha=418,
  fm="Eight Trigrams Training",fq=4500,fb={"hp":75,"atk":88,"def":82,"speed":52}),
Q("Hizashi (Young)","Uncommon","Lightning","Konoha","Hyuga",hp=252,atk=265,df=235,spd=295,cha=415,
  fm="Gentle Fist Branch",fq=4500,fb={"hp":75,"atk":85,"def":80,"speed":50}),
Q("Ibiki (Young)","Uncommon","Yin","Konoha","Shimura",hp=252,atk=260,df=245,spd=292,cha=415,
  fm="Interrogation Arts",fq=4000,fb={"hp":75,"atk":80,"def":85,"speed":45}),
Q("Yugao (Young)","Uncommon","Water","Konoha","Hatake",hp=250,atk=262,df=225,spd=322,cha=412,
  fm="Sword Dance Style",fq=4500,fb={"hp":75,"atk":85,"def":75,"speed":62}),
Q("Aoba (Young)","Uncommon","Yin","Konoha","Yamanaka",hp=250,atk=258,df=225,spd=310,cha=415,
  fm="Mind Search Raven",fq=4500,fb={"hp":75,"atk":82,"def":76,"speed":55}),
Q("Udon (Young)","Uncommon","Water","Konoha","Sarutobi",hp=248,atk=255,df=222,spd=305,cha=410,
  fm="Snot Clone Style",fq=4000,fb={"hp":72,"atk":78,"def":75,"speed":52}),
Q("Wasabi (Young)","Uncommon","Fire","Konoha","Inuzuka",hp=250,atk=262,df=218,spd=325,cha=408,
  fm="Cat Claw Style",fq=4000,fb={"hp":72,"atk":85,"def":72,"speed":62}),
Q("Namida (Young)","Uncommon","Water","Konoha","Hyuga",hp=248,atk=255,df=222,spd=308,cha=412,
  fm="Ultrasonic Cry",fq=4000,fb={"hp":72,"atk":78,"def":74,"speed":52}),
Q("Iwabe (Chunin)","Uncommon","Earth","Konoha","Sarutobi",hp=255,atk=262,df=245,spd=295,cha=408,
  fm="Earth Wall Mastery",fq=4500,fb={"hp":78,"atk":82,"def":85,"speed":45}),
Q("Zaku (Young)","Uncommon","Wind","Oto","Orochimaru",hp=252,atk=268,df=218,spd=322,cha=408,
  fm="Airwave Style",fq=4500,fb={"hp":75,"atk":88,"def":72,"speed":62}),
Q("Dosu (Young)","Uncommon","Yin","Oto","Orochimaru",hp=255,atk=262,df=235,spd=298,cha=408,
  fm="Melody Arm Style",fq=4500,fb={"hp":75,"atk":82,"def":80,"speed":48}),
Q("Dan Kato (Young)","Uncommon","Yin","Konoha","Kato",hp=250,atk=258,df=222,spd=305,cha=418,
  fm="Spirit Body Early",fq=4500,fb={"hp":75,"atk":83,"def":76,"speed":55}),
Q("Nawaki (Child)","Uncommon","Earth","Konoha","Senju",hp=248,atk=252,df=222,spd=302,cha=410,
  fm="Senju Heritage",fq=4000,fb={"hp":72,"atk":78,"def":74,"speed":50}),
Q("Mikoto (Young)","Uncommon","Fire","Konoha","Uchiha",hp=250,atk=262,df=225,spd=312,cha=415,
  fm="Sharingan Clan Style",fq=4500,fb={"hp":75,"atk":85,"def":76,"speed":57}),
Q("Kagura (Young)","Uncommon","Water","Kiri","Momochi",hp=252,atk=262,df=225,spd=308,cha=410,
  fm="Samehada Bond",fq=4500,fb={"hp":75,"atk":85,"def":75,"speed":55}),
# ── NEW COMMON ───────────────────────────────────────────────────
Q("Sound Genin","Common","Yin","Oto","Orochimaru",hp=178,atk=190,df=148,spd=208,cha=275,
  fm="Curse Seal Trace",fq=1500,fb={"hp":40,"atk":50,"def":38,"speed":40}),
Q("Grass Chunin","Common","Earth","Kusa","Sarutobi",hp=175,atk=185,df=152,spd=200,cha=272,
  fm="Hidden Grass Style",fq=1500,fb={"hp":38,"atk":48,"def":40,"speed":38}),
Q("Rain Jonin","Common","Water","Akatsuki","Konan",hp=180,atk=190,df=155,spd=205,cha=278,
  fm="Rain Style Master",fq=1500,fb={"hp":40,"atk":50,"def":42,"speed":40}),
Q("Rock Chunin","Common","Earth","Iwa","Kaguya",hp=178,atk=192,df=158,spd=195,cha=275,
  fm="Earth Style Basics",fq=1500,fb={"hp":38,"atk":50,"def":45,"speed":35}),
Q("Waterfall Genin","Common","Water","Taki","Uzumaki",hp=175,atk=185,df=150,spd=205,cha=272,
  fm="Waterfall Style",fq=1500,fb={"hp":38,"atk":48,"def":38,"speed":40}),
Q("Star Ninja","Common","Fire","Hoshi","Sarutobi",hp=175,atk=188,df=148,spd=205,cha=270,
  fm="Star Chakra Infuse",fq=1500,fb={"hp":38,"atk":48,"def":38,"speed":40}),
Q("Mist Genin","Common","Water","Kiri","Momochi",hp=175,atk=185,df=152,spd=202,cha=272,
  fm="Hidden Mist Style",fq=1500,fb={"hp":38,"atk":48,"def":40,"speed":38}),
Q("Thunder Chunin","Common","Lightning","Kumo","Darui",hp=178,atk=190,df=150,spd=215,cha=272,
  fm="Static Lightning Style",fq=1500,fb={"hp":38,"atk":50,"def":38,"speed":42}),
Q("Forest Shinobi","Common","Wood","Konoha","Senju",hp=178,atk=185,df=158,spd=198,cha=275,
  fm="Wood Release Training",fq=1500,fb={"hp":40,"atk":48,"def":45,"speed":35}),
Q("Desert Wanderer","Common","Sand","Suna","Subaku",hp=175,atk=188,df=155,spd=200,cha=272,
  fm="Sand Cloak Style",fq=1500,fb={"hp":38,"atk":50,"def":42,"speed":38}),
Q("Iron Armor Ninja","Common","Metal","Wanderer","Rasa",hp=178,atk=188,df=162,spd=195,cha=272,
  fm="Iron Shell Mode",fq=1500,fb={"hp":40,"atk":48,"def":48,"speed":35}),
Q("Puppet Recruit","Common","Puppet","Suna","Sasori",hp=172,atk=182,df=155,spd=195,cha=270,
  fm="String Control",fq=1500,fb={"hp":38,"atk":48,"def":42,"speed":35}),
Q("Blast Corps Genin","Common","Explosion","Iwa","Deidara",hp=175,atk=192,df=148,spd=205,cha=270,
  fm="Minor Explosion Art",fq=1500,fb={"hp":38,"atk":52,"def":38,"speed":40}),
Q("Bone Shard Trainee","Common","Earth","Wanderer","Kaguya",hp=178,atk=188,df=158,spd=200,cha=272,
  fm="Bone Spike",fq=1500,fb={"hp":40,"atk":50,"def":45,"speed":38}),
Q("Jashin Cultist","Common","Yin","Wanderer","Hidan",hp=175,atk=188,df=152,spd=205,cha=272,
  fm="Jashin Ritual Curse",fq=1500,fb={"hp":38,"atk":52,"def":40,"speed":40}),
Q("Leaf Academy Student","Common","Wind","Konoha","Uzumaki",hp=170,atk=178,df=145,spd=200,cha=268,
  fm="First Jutsu Clone",fq=1000,fb={"hp":35,"atk":45,"def":35,"speed":38}),
Q("Suna Genin","Common","Sand","Suna","Subaku",hp=172,atk=180,df=148,spd=198,cha=268,
  fm="Sand Throw",fq=1000,fb={"hp":35,"atk":45,"def":38,"speed":36}),
Q("Iwa Genin","Common","Earth","Iwa","Kaguya",hp=175,atk=182,df=155,spd=192,cha=268,
  fm="Earth Barrier",fq=1000,fb={"hp":35,"atk":45,"def":42,"speed":32}),
Q("Kiri Genin","Common","Water","Kiri","Momochi",hp=172,atk=180,df=150,spd=200,cha=268,
  fm="Water Clone",fq=1000,fb={"hp":35,"atk":45,"def":38,"speed":38}),
Q("Kumo Jonin","Common","Lightning","Kumo","Darui",hp=185,atk=198,df=155,spd=222,cha=280,
  fm="Static Field",fq=1500,fb={"hp":40,"atk":52,"def":40,"speed":45}),
Q("Oto Jonin","Common","Yin","Oto","Orochimaru",hp=182,atk=192,df=152,spd=210,cha=278,
  fm="Sound Style",fq=1500,fb={"hp":38,"atk":50,"def":40,"speed":42}),
Q("Suna Jonin","Common","Sand","Suna","Subaku",hp=182,atk=192,df=158,spd=205,cha=275,
  fm="Sand Art",fq=1500,fb={"hp":40,"atk":50,"def":42,"speed":40}),
Q("Iwa Jonin","Common","Earth","Iwa","Kaguya",hp=185,atk=195,df=162,spd=200,cha=275,
  fm="Stone Armor",fq=1500,fb={"hp":40,"atk":50,"def":45,"speed":38}),
]

# Starters: only Common and Uncommon characters so new players get weak chars
STARTER_POOL = [c for c in CHARACTERS if c["rarity"] in ("Common", "Uncommon")]

# ─── WILD ENCOUNTERS ────────────────────────────────────────────
WILDS = [
    {"name":"Sand Ninja","nat":"Sand","hp":160,"atk":130,"def":110,"spd":140,
     "photo":None,"nc":(200,600),"chakra":(20,80),"exp":(30,80),
     "moves":[M["sand_coffin"],M["sand_clone"],M["wind_cutter"]]},
    {"name":"Sound Ninja","nat":"Yin","hp":145,"atk":140,"def":100,"spd":155,
     "photo":None,"nc":(200,650),"chakra":(20,90),"exp":(35,85),
     "moves":[M["kagura_mind"],M["ghost_blade"],M["poison_gas"]]},
    {"name":"Mist Assassin","nat":"Water","hp":150,"atk":135,"def":105,"spd":160,
     "photo":None,"nc":(250,700),"chakra":(25,95),"exp":(40,90),
     "moves":[M["hidden_mist"],M["water_shark"],M["ghost_blade"]]},
    {"name":"Stone Guardian","nat":"Earth","hp":210,"atk":120,"def":175,"spd":105,
     "photo":None,"nc":(300,750),"chakra":(30,100),"exp":(45,100),
     "moves":[M["rock_avalanche"],M["earth_spear"],M["earth_prison"]]},
    {"name":"Cloud Striker","nat":"Lightning","hp":155,"atk":150,"def":105,"spd":165,
     "photo":None,"nc":(300,750),"chakra":(30,100),"exp":(45,95),
     "moves":[M["thunder_blade"],M["lightning_ball"],M["lariat"]]},
    {"name":"Rogue Jonin","nat":"Yin","hp":220,"atk":170,"def":140,"spd":155,
     "photo":None,"nc":(600,1500),"chakra":(60,150),"exp":(80,180),
     "moves":[M["shadow_bind"],M["ghost_blade"],M["poison_gas"],M["bringer_dark"]]},
    {"name":"Akatsuki Grunt","nat":"Yin","hp":250,"atk":185,"def":155,"spd":150,
     "photo":None,"nc":(800,2000),"chakra":(80,200),"exp":(100,250),
     "moves":[M["shadow_king"],M["ghost_blade"],M["jashin_curse"],M["kagura_mind"]]},
    {"name":"Rogue Jinchuriki","nat":"Yang","hp":320,"atk":215,"def":165,"spd":170,
     "photo":None,"nc":(1000,2800),"chakra":(100,280),"exp":(150,350),
     "moves":[M["tbb"],M["almighty_push"],M["shinra_tensei"],M["gedo_chain"]]},
    {"name":"Elite ANBU","nat":"Lightning","hp":200,"atk":195,"def":160,"spd":195,
     "photo":None,"nc":(700,1800),"chakra":(70,175),"exp":(90,220),
     "moves":[M["chidori"],M["vanishing_strike"],M["thunder_blade"],M["clone_barrage"]]},
    {"name":"Puppet Master","nat":"Puppet","hp":175,"atk":165,"def":150,"spd":145,
     "photo":None,"nc":(500,1200),"chakra":(50,120),"exp":(65,160),
     "moves":[M["scorpion_tail"],M["crow_puppet"],M["poison_gas"],M["hundred_puppets"]]},
    {"name":"Ice Village Ninja","nat":"Ice","hp":160,"atk":140,"def":115,"spd":155,
     "photo":None,"nc":(280,720),"chakra":(28,95),"exp":(38,92),
     "moves":[M["ice_dome"],M["ice_needles"],M["hidden_mist"]]},
    {"name":"Explosion Corps","nat":"Explosion","hp":170,"atk":160,"def":110,"spd":145,
     "photo":None,"nc":(350,900),"chakra":(35,115),"exp":(50,130),
     "moves":[M["c1_birds"],M["c2_dragon"],M["clay_wall"]]},
    {"name":"Medical Ninja","nat":"Medical","hp":145,"atk":125,"def":120,"spd":140,
     "photo":None,"nc":(250,650),"chakra":(25,90),"exp":(35,88),
     "moves":[M["mystical_palm"],M["poison_gas"],M["chakra_scalpel"]]},
    {"name":"Wood Shinobi","nat":"Wood","hp":185,"atk":140,"def":155,"spd":130,
     "photo":None,"nc":(320,820),"chakra":(32,105),"exp":(42,110),
     "moves":[M["wood_clone"],M["wood_spikes"],M["wood_prison"]]},
    {"name":"Lava Shinobi","nat":"Lava","hp":175,"atk":155,"def":130,"spd":140,
     "photo":None,"nc":(400,1000),"chakra":(40,125),"exp":(55,140),
     "moves":[M["lava_melt"],M["lava_giant"],M["fire_dragon"]]},
]

# ─── SHOP ───────────────────────────────────────────────────────
SHOP = [
    {"id":"heal","name":"Full Heal Jutsu","desc":"Restore all HP instantly in battle","price":400,"type":"item","emoji":"<tg-emoji emoji-id='5427095369278299187'>💊</tg-emoji>"},
    {"id":"chakra_pill","name":"Chakra Recovery Pill","desc":"Restore 300 chakra instantly","price":250,"type":"item","emoji":"<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji>"},
    {"id":"exp_boost","name":"Training Scroll","desc":"2x EXP for next 5 battles","price":800,"type":"item","emoji":"📜"},
    {"id":"super_heal","name":"Mystic Recovery","desc":"Full heal + 500 chakra restoration","price":1500,"type":"item","emoji":"<tg-emoji emoji-id='5426872512015244606'>🌿</tg-emoji>"},
    {"id":"stone","name":"Transform Stone","desc":"Enables powerful transformation in battle","price":2000,"type":"item","emoji":"🪨"},
    {"id":"chakra_crystal","name":"Chakra Crystal","desc":"Restore 1000 chakra instantly","price":600,"type":"item","emoji":"<tg-emoji emoji-id='5454122580564786042'>💎</tg-emoji>"},
    {"id":"antidote","name":"Antidote","desc":"Remove all status effects from team","price":350,"type":"item","emoji":"🧪"},
    {"id":"battle_seal","name":"Battle Seal","desc":"Boost all stats by 10% for next battle","price":1200,"type":"item","emoji":"🔖"},
    {"id":"lucky_charm","name":"Lucky Charm","desc":"Triple stone drop rate for 3 battles","price":1800,"type":"item","emoji":"🍀"},
    {"id":"double_nc","name":"NC Multiplier","desc":"Double NC from next 3 explore wins","price":2500,"type":"item","emoji":"<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji>"},
    {"id":"mega_exp","name":"Mega EXP Scroll","desc":"5x EXP for next battle (massive boost)","price":3000,"type":"item","emoji":"📚"},
    {"id":"rebirth_token","name":"Rebirth Token","desc":"Instantly level up any character +10 levels","price":5000,"type":"item","emoji":"<tg-emoji emoji-id='5424892463372312872'>🌟</tg-emoji>"},
    {"id":"rare_scroll","name":"Rare Scroll","desc":"Guaranteed Rare character summon","price":3500,"type":"summon","emoji":"<tg-emoji emoji-id='5798483635199807367'>🔵</tg-emoji>"},
    {"id":"epic_scroll","name":"Epic Scroll","desc":"Guaranteed Epic character summon","price":10000,"type":"summon","emoji":"<tg-emoji emoji-id='5769297434047943583'>🟣</tg-emoji>"},
    {"id":"legendary_scroll","name":"Legendary Scroll","desc":"Guaranteed Legendary character summon","price":25000,"type":"summon","emoji":"<tg-emoji emoji-id='5915696866120438280'>🟡</tg-emoji>"},
    {"id":"mythic_scroll","name":"Mythic Scroll","desc":"Attempt Mythic summon (5% chance)","price":50000,"type":"summon","emoji":"🔮"},
    {"id":"rename","name":"Rename Token","desc":"Change your display nickname","price":500,"type":"item","emoji":"✏️"},
    {"id":"clan_reset","name":"Clan Reset","desc":"Reset your clan choice (one-time)","price":8000,"type":"item","emoji":"<tg-emoji emoji-id='5224388744156557558'>🧬</tg-emoji>"},
    {"id":"village_vip","name":"Village VIP Pass","desc":"+20% all village bonuses for 10 battles","price":3000,"type":"item","emoji":"<tg-emoji emoji-id='5424767857781122187'>🏅</tg-emoji>"},
]
SHOP_PAGE_SIZE = 6

# ─── WEAPONS (100+ items) ────────────────────────────────────────
# Each weapon: id, name, rarity, atk (damage bonus), ability (active skill name),
# buff (type+val applied on use), price (NC), desc
WEAPONS = [
    # ── Common (18) ──
    {"id":"kunai_sharp","name":"Sharpened Kunai","rarity":"Common","atk":20,"ability":"Quick Strike","buff":{"type":"spd_down","val":15},"price":400,"desc":"A battle-honed kunai with deadly edge"},
    {"id":"shuriken_set","name":"Shuriken Set","rarity":"Common","atk":18,"ability":"Fan Throw","buff":{"type":"multi_hit","val":0},"price":350,"desc":"Balanced throwing stars for rapid attacks"},
    {"id":"tanto_blade","name":"Tanto Blade","rarity":"Common","atk":22,"ability":"Thrust","buff":{"type":"bleed","val":20},"price":450,"desc":"Short blade favored by shinobi scouts"},
    {"id":"iron_knuckles","name":"Iron Knuckles","rarity":"Common","atk":25,"ability":"Heavy Punch","buff":{"type":"stun","val":30},"price":500,"desc":"Reinforced fighting gloves that stun on impact"},
    {"id":"chakra_thread","name":"Chakra Thread","rarity":"Common","atk":16,"ability":"Bind","buff":{"type":"skip_turn","val":20},"price":300,"desc":"Thin chakra-infused wires for trapping enemies"},
    {"id":"senbon_needle","name":"Senbon Needle","rarity":"Common","atk":14,"ability":"Nerve Strike","buff":{"type":"def_break","val":25},"price":280,"desc":"Medical needles repurposed for combat"},
    {"id":"smoke_tag","name":"Smoke Bomb Tag","rarity":"Common","atk":15,"ability":"Blind","buff":{"type":"acc_down","val":35},"price":320,"desc":"Explosive tag that creates blinding smoke"},
    {"id":"combat_knife","name":"Combat Knife","rarity":"Common","atk":23,"ability":"Slash","buff":{"type":"bleed","val":15},"price":420,"desc":"Standard-issue combat blade for genin"},
    {"id":"wire_trap","name":"Wire Trap","rarity":"Common","atk":12,"ability":"Ensnare","buff":{"type":"skip_turn","val":25},"price":260,"desc":"Wire mesh that immobilizes foes"},
    {"id":"bone_dagger","name":"Bone Dagger","rarity":"Common","atk":21,"ability":"Pierce","buff":{"type":"pierce","val":0},"price":400,"desc":"Carved from the bones of fallen beasts"},
    {"id":"leaf_blade","name":"Leaf Blade","rarity":"Common","atk":19,"ability":"Verdant Cut","buff":{"type":"spd_down","val":20},"price":380,"desc":"A blade blessed with leaf-style chakra"},
    {"id":"throwing_disc","name":"Throwing Disc","rarity":"Common","atk":17,"ability":"Ricochet","buff":{"type":"multi_hit","val":0},"price":340,"desc":"Flat disc that bounces between targets"},
    {"id":"grip_chains","name":"Grip Chains","rarity":"Common","atk":13,"ability":"Shackle","buff":{"type":"skip_turn","val":30},"price":290,"desc":"Heavy chains with spiked grips"},
    {"id":"foot_wraps","name":"Battle Wraps","rarity":"Common","atk":11,"ability":"Swift Kick","buff":{"type":"spd_down","val":10},"price":220,"desc":"Chakra-woven wraps that enhance leg strikes"},
    {"id":"henge_scroll","name":"Henge Scroll","rarity":"Common","atk":14,"ability":"Decoy Strike","buff":{"type":"dodge_next","val":0},"price":300,"desc":"Scroll that creates a distracting clone"},
    {"id":"gauntlet","name":"Combat Gauntlet","rarity":"Common","atk":24,"ability":"Guard Crush","buff":{"type":"def_break","val":20},"price":480,"desc":"Spiked gauntlet that shatters defenses"},
    {"id":"battle_fan_s","name":"Small Battle Fan","rarity":"Common","atk":16,"ability":"Wind Slash","buff":{"type":"spd_down","val":12},"price":310,"desc":"Compact fan that generates cutting wind"},
    {"id":"training_staff","name":"Training Staff","rarity":"Common","atk":20,"ability":"Staff Sweep","buff":{"type":"stun","val":20},"price":390,"desc":"Reinforced wooden staff used in training"},
    # ── Uncommon (18) ──
    {"id":"elemental_kunai","name":"Elemental Kunai","rarity":"Uncommon","atk":35,"ability":"Nature Strike","buff":{"type":"burn","val":25},"price":900,"desc":"Kunai infused with fire nature chakra"},
    {"id":"steel_fan","name":"Steel War Fan","rarity":"Uncommon","atk":38,"ability":"Whirlwind","buff":{"type":"aoe","val":0},"price":950,"desc":"Heavy steel fan that strikes all enemies"},
    {"id":"twin_sai","name":"Twin Sai","rarity":"Uncommon","atk":40,"ability":"Dual Pierce","buff":{"type":"pierce","val":0},"price":1000,"desc":"Matching sai that bypass armor"},
    {"id":"poison_needle","name":"Poison Needle","rarity":"Uncommon","atk":30,"ability":"Venom Inject","buff":{"type":"poison","val":40},"price":850,"desc":"Hollow needle packed with slow-acting poison"},
    {"id":"shadow_blade","name":"Shadow Blade","rarity":"Uncommon","atk":42,"ability":"Darkness Cut","buff":{"type":"acc_down","val":30},"price":1050,"desc":"Blade forged in the shadows of Kumogakure"},
    {"id":"wind_fan","name":"Wind Chakra Fan","rarity":"Uncommon","atk":36,"ability":"Air Slash","buff":{"type":"def_break","val":30},"price":920,"desc":"Fan channeling compressed air attacks"},
    {"id":"mist_sword_s","name":"Mist Shortsword","rarity":"Uncommon","atk":44,"ability":"Fog Slash","buff":{"type":"acc_down","val":35},"price":1100,"desc":"Sword from Kirigakure, shrouded in mist"},
    {"id":"fire_tag_scroll","name":"Fire Tag Scroll","rarity":"Uncommon","atk":37,"ability":"Flame Burst","buff":{"type":"burn","val":35},"price":930,"desc":"Scroll packed with explosive fire tags"},
    {"id":"thunder_rod","name":"Thunder Rod","rarity":"Uncommon","atk":39,"ability":"Lightning Strike","buff":{"type":"stun","val":40},"price":980,"desc":"Conductive rod that channels lightning"},
    {"id":"earth_hammer","name":"Earth Hammer","rarity":"Uncommon","atk":45,"ability":"Ground Smash","buff":{"type":"stun","val":35},"price":1100,"desc":"Heavy hammer imbued with earth chakra"},
    {"id":"water_whip","name":"Water Whip","rarity":"Uncommon","atk":32,"ability":"Torrent Lash","buff":{"type":"spd_down","val":30},"price":880,"desc":"Water chakra shaped into a cracking whip"},
    {"id":"sand_gauntlet","name":"Sand Gauntlet","rarity":"Uncommon","atk":38,"ability":"Sand Crush","buff":{"type":"def_break","val":28},"price":940,"desc":"Gauntlet wielding Suna's desert chakra"},
    {"id":"puppet_wire_b","name":"Puppet Wire","rarity":"Uncommon","atk":33,"ability":"Puppet Slash","buff":{"type":"skip_turn","val":35},"price":870,"desc":"Chakra wires connected to a small puppet"},
    {"id":"insect_blade","name":"Insect Blade","rarity":"Uncommon","atk":36,"ability":"Swarm Strike","buff":{"type":"poison","val":30},"price":910,"desc":"Blade that releases a cloud of attack bugs"},
    {"id":"paper_blade","name":"Paper Blade","rarity":"Uncommon","atk":34,"ability":"Origami Slash","buff":{"type":"bleed","val":35},"price":890,"desc":"A thousand paper sheets formed into a blade"},
    {"id":"yin_seal","name":"Yin Seal Bracer","rarity":"Uncommon","atk":41,"ability":"Seal Release","buff":{"type":"def_up","val":30},"price":1050,"desc":"Bracer storing compressed yin chakra"},
    {"id":"battle_club","name":"Spiked Club","rarity":"Uncommon","atk":46,"ability":"Brutal Smash","buff":{"type":"stun","val":30},"price":1120,"desc":"Heavy club that crushes bone and armor"},
    {"id":"wolf_fang","name":"Wolf Fang Blade","rarity":"Uncommon","atk":43,"ability":"Pack Hunt","buff":{"type":"multi_hit","val":0},"price":1070,"desc":"Blade shaped after the fang of a wolf"},
    # ── Rare (24) ──
    {"id":"chidori_kunai","name":"Chidori Kunai","rarity":"Rare","atk":60,"ability":"Lightning Blade Throw","buff":{"type":"stun","val":50},"price":2500,"desc":"Kunai charged with Chidori lightning chakra"},
    {"id":"rasengan_blade","name":"Rasengan Blade","rarity":"Rare","atk":65,"ability":"Spiraling Slash","buff":{"type":"def_break","val":50},"price":2800,"desc":"Blade wrapped in a perpetual rasengan spiral"},
    {"id":"flame_sword","name":"Flame Sword","rarity":"Rare","atk":62,"ability":"Katon Slash","buff":{"type":"burn","val":50},"price":2600,"desc":"Sword bathed in continuous fire chakra"},
    {"id":"lightning_spear","name":"Lightning Spear","rarity":"Rare","atk":70,"ability":"Thunder Thrust","buff":{"type":"pierce","val":0},"price":3000,"desc":"Spear that conducts Raiton chakra to tip"},
    {"id":"earth_crusher","name":"Earth Crusher","rarity":"Rare","atk":68,"ability":"Rock Avalanche","buff":{"type":"aoe","val":0},"price":2900,"desc":"Massive hammer that triggers earth jutsu on impact"},
    {"id":"water_blade_r","name":"Water Dragon Blade","rarity":"Rare","atk":63,"ability":"Suiryudan Slash","buff":{"type":"spd_down","val":45},"price":2650,"desc":"Blade that releases water dragons on impact"},
    {"id":"mist_blade_r","name":"Silent Killing Blade","rarity":"Rare","atk":72,"ability":"Silent Kill","buff":{"type":"acc_down","val":50},"price":3100,"desc":"Blade used in the Seven Swordsmen silent kill"},
    {"id":"cloud_sword","name":"Cloud Thunder Sword","rarity":"Rare","atk":66,"ability":"Raikage Flash","buff":{"type":"stun","val":45},"price":2750,"desc":"Sword of the Lightning Country warriors"},
    {"id":"stone_hammer","name":"Stone Fist Hammer","rarity":"Rare","atk":74,"ability":"Mountain Crush","buff":{"type":"def_break","val":55},"price":3200,"desc":"Hammer said to move like a crumbling mountain"},
    {"id":"demon_blade","name":"Demon Blade","rarity":"Rare","atk":75,"ability":"Cursed Strike","buff":{"type":"poison","val":55},"price":3300,"desc":"Blade cursed with demonic chakra from Orochimaru"},
    {"id":"iron_fan_r","name":"Iron War Fan","rarity":"Rare","atk":64,"ability":"Vacuum Wave","buff":{"type":"aoe","val":0},"price":2700,"desc":"Massive iron fan like Temari carries"},
    {"id":"sound_fork","name":"Sound Tuning Fork","rarity":"Rare","atk":58,"ability":"Sonic Blast","buff":{"type":"stun","val":60},"price":2400,"desc":"Vibrating fork that shatters eardrums"},
    {"id":"bone_lance","name":"Bone Lance","rarity":"Rare","atk":69,"ability":"Dead Bone Pulse","buff":{"type":"pierce","val":0},"price":2950,"desc":"Lance carved from shikotsumyaku bones"},
    {"id":"paper_bomb_sword","name":"Paper Bomb Sword","rarity":"Rare","atk":71,"ability":"Detonation Slash","buff":{"type":"burn","val":55},"price":3050,"desc":"Sword lined with paper explosives"},
    {"id":"twin_blades_r","name":"Dual Storm Blades","rarity":"Rare","atk":67,"ability":"Storm Dance","buff":{"type":"multi_hit","val":0},"price":2850,"desc":"Paired blades that perform a cutting dance"},
    {"id":"chakra_cannon_r","name":"Chakra Cannon","rarity":"Rare","atk":73,"ability":"Cannon Blast","buff":{"type":"aoe","val":0},"price":3150,"desc":"Arm-mounted device that fires compressed chakra"},
    {"id":"sharingan_kunai","name":"Sharingan Kunai","rarity":"Rare","atk":76,"ability":"Copy Blade","buff":{"type":"def_break","val":50},"price":3400,"desc":"Kunai infused with copied Sharingan jutsu"},
    {"id":"sand_blade_r","name":"Desert Fang Blade","rarity":"Rare","atk":61,"ability":"Sand Fang","buff":{"type":"bleed","val":50},"price":2550,"desc":"Blade that fires desert sand at high velocity"},
    {"id":"puppet_army_axe","name":"Puppet Army Axe","rarity":"Rare","atk":77,"ability":"Army of Puppets","buff":{"type":"aoe","val":0},"price":3500,"desc":"Axe that deploys multiple puppet arms"},
    {"id":"medical_blade","name":"Medical Scalpel","rarity":"Rare","atk":56,"ability":"Vital Strike","buff":{"type":"def_break","val":60},"price":2350,"desc":"Surgical scalpel aimed at vital points"},
    {"id":"snake_fang_r","name":"Snake Fang Blade","rarity":"Rare","atk":66,"ability":"Serpent Bite","buff":{"type":"poison","val":60},"price":2750,"desc":"Sword styled after Orochimaru's snake fangs"},
    {"id":"storm_spear","name":"Storm Release Spear","rarity":"Rare","atk":70,"ability":"Storm Thrust","buff":{"type":"aoe","val":0},"price":3000,"desc":"Spear channeling combined lightning and water"},
    {"id":"lava_blade","name":"Lava Release Blade","rarity":"Rare","atk":68,"ability":"Magma Slash","buff":{"type":"burn","val":60},"price":2900,"desc":"Blade coated in hardened lava-style chakra"},
    {"id":"magnet_hammer","name":"Magnet Release Hammer","rarity":"Rare","atk":65,"ability":"Magnetic Pull","buff":{"type":"skip_turn","val":40},"price":2700,"desc":"Hammer that pins foes with magnetic chakra"},
    # ── Epic (24) ──
    {"id":"kubikiribocho","name":"Kubikiribocho","rarity":"Epic","atk":100,"ability":"Beheading Strike","buff":{"type":"def_break","val":70},"price":6000,"desc":"The executioner's greatsword that repairs with blood"},
    {"id":"hiramekarei","name":"Hiramekarei","rarity":"Epic","atk":95,"ability":"Wave Burst","buff":{"type":"aoe","val":0},"price":5500,"desc":"Twin-handled sword that stores chakra energy"},
    {"id":"nuibari","name":"Nuibari","rarity":"Epic","atk":90,"ability":"Chain Stitch","buff":{"type":"skip_turn","val":50},"price":5000,"desc":"Slender needle sword that stitches foes together"},
    {"id":"kiba_swords","name":"Kiba Twin Swords","rarity":"Epic","atk":105,"ability":"Lightning Fangs","buff":{"type":"stun","val":65},"price":6500,"desc":"Lightning-charged twin swords of the Kiba"},
    {"id":"shibuki","name":"Shibuki Blast Sword","rarity":"Epic","atk":98,"ability":"Explosion Wave","buff":{"type":"aoe","val":0},"price":5800,"desc":"Scroll-lined sword that detonates on contact"},
    {"id":"samehada","name":"Samehada","rarity":"Epic","atk":110,"ability":"Chakra Shave","buff":{"type":"drain","val":50},"price":7000,"desc":"Sentient sword that feeds on enemy chakra"},
    {"id":"thunder_saber","name":"Thunder God Saber","rarity":"Epic","atk":108,"ability":"Raikiri Edge","buff":{"type":"pierce","val":0},"price":6800,"desc":"Saber charged with pure Raikiri lightning"},
    {"id":"sage_staff","name":"Sage Mode Staff","rarity":"Epic","atk":102,"ability":"Sage Strike","buff":{"type":"def_break","val":60},"price":6200,"desc":"Staff channeling senjutsu nature energy"},
    {"id":"dragon_scale","name":"Dragon Scale Blade","rarity":"Epic","atk":112,"ability":"Dragon Roar Slash","buff":{"type":"burn","val":65},"price":7200,"desc":"Blade layered in summoned dragon scales"},
    {"id":"kyubi_fang","name":"Kyubi Fang Blade","rarity":"Epic","atk":118,"ability":"Tailed Beast Bite","buff":{"type":"aoe","val":0},"price":7800,"desc":"Blade shaped from a crystallized Kyubi claw"},
    {"id":"space_time_kunai","name":"Space-Time Kunai","rarity":"Epic","atk":106,"ability":"Hiraishin Mark","buff":{"type":"dodge_next","val":0},"price":6600,"desc":"Kunai that bends space-time on impact"},
    {"id":"perfect_chakra_blade","name":"Perfect Chakra Blade","rarity":"Epic","atk":115,"ability":"Chakra Amplify","buff":{"type":"def_up","val":50},"price":7500,"desc":"Blade amplifying user's chakra on each swing"},
    {"id":"lightning_storm_blade","name":"Lightning Storm Blade","rarity":"Epic","atk":109,"ability":"Storm Barrage","buff":{"type":"multi_hit","val":0},"price":6900,"desc":"Blade that unleashes a lightning storm on swing"},
    {"id":"fire_demon_sword","name":"Fire Demon Sword","rarity":"Epic","atk":104,"ability":"Demon Fire Wave","buff":{"type":"burn","val":70},"price":6400,"desc":"Sword wielded by fire-nature demons of the era"},
    {"id":"earth_king_hammer","name":"Earth King Hammer","rarity":"Epic","atk":120,"ability":"Tectonic Slam","buff":{"type":"stun","val":60},"price":8000,"desc":"Hammer said to trigger small earthquakes on impact"},
    {"id":"water_dragon_sword","name":"Water Dragon Sword","rarity":"Epic","atk":103,"ability":"Dragon Scale Wave","buff":{"type":"aoe","val":0},"price":6300,"desc":"Sword that summons water dragons from each slash"},
    {"id":"wind_god_fan","name":"Wind God Fan","rarity":"Epic","atk":107,"ability":"Tempest Slash","buff":{"type":"spd_down","val":60},"price":6700,"desc":"Fan capable of generating catastrophic wind"},
    {"id":"yin_blade","name":"Yin Release Blade","rarity":"Epic","atk":113,"ability":"Void Edge","buff":{"type":"acc_down","val":60},"price":7300,"desc":"Blade channeling pure yin-release dark energy"},
    {"id":"yang_blade","name":"Yang Release Blade","rarity":"Epic","atk":116,"ability":"Life Force Edge","buff":{"type":"def_up","val":55},"price":7600,"desc":"Blade radiating regenerative yang-release light"},
    {"id":"bone_forest_lance","name":"Bone Forest Lance","rarity":"Epic","atk":111,"ability":"Dead Bone Forest","buff":{"type":"aoe","val":0},"price":7100,"desc":"Lance that erupts bone spires from the ground"},
    {"id":"shadow_king_blade","name":"Shadow King Blade","rarity":"Epic","atk":114,"ability":"Shadow Possession Slash","buff":{"type":"skip_turn","val":55},"price":7400,"desc":"Blade wielded alongside the shadow possession jutsu"},
    {"id":"explosion_hammer","name":"Explosion Hammer","rarity":"Epic","atk":122,"ability":"Explosive Strike","buff":{"type":"aoe","val":0},"price":8200,"desc":"Hammer packed with Deidara-style exploding clay"},
    {"id":"coral_blade","name":"Coral Blade","rarity":"Epic","atk":99,"ability":"Coral Binding","buff":{"type":"skip_turn","val":55},"price":5900,"desc":"Blade that grows coral around struck enemies"},
    {"id":"lava_axe","name":"Lava King Axe","rarity":"Epic","atk":117,"ability":"Magma Eruption","buff":{"type":"burn","val":70},"price":7700,"desc":"Axe channeling the extreme heat of lava-release"},
    # ── Legendary (12) ──
    {"id":"totsuka_blade","name":"Totsuka Blade","rarity":"Legendary","atk":180,"ability":"Sealing Slash","buff":{"type":"soul_rip","val":0},"price":25000,"desc":"The ethereal sword of sealing, carried by Itachi"},
    {"id":"seven_stars_kunai","name":"Seven Stars Kunai","rarity":"Legendary","atk":165,"ability":"Celestial Barrage","buff":{"type":"multi_hit","val":0},"price":22000,"desc":"Seven kunai that orbit with star-like chakra"},
    {"id":"hiraishin_blade","name":"Hiraishin Blade","rarity":"Legendary","atk":170,"ability":"Space-Time Cleave","buff":{"type":"unavoidable","val":0},"price":23000,"desc":"Minato's personal combat blade with seal marks"},
    {"id":"amaterasu_sword","name":"Amaterasu Sword","rarity":"Legendary","atk":190,"ability":"Black Flame Strike","buff":{"type":"burn","val":90},"price":28000,"desc":"Blade carrying black inextinguishable Amaterasu flames"},
    {"id":"dust_hammer","name":"Dust Release Hammer","rarity":"Legendary","atk":185,"ability":"Particle Dismantle","buff":{"type":"def_break","val":80},"price":26000,"desc":"Hammer channeling the Third Tsuchikage's dust release"},
    {"id":"raijin_blade","name":"Raijin Lightning Blade","rarity":"Legendary","atk":175,"ability":"God of Thunder Strike","buff":{"type":"stun","val":80},"price":24000,"desc":"Blade said to be carried by the god of lightning"},
    {"id":"fujin_spear","name":"Fujin Wind Spear","rarity":"Legendary","atk":172,"ability":"God of Wind Thrust","buff":{"type":"pierce","val":0},"price":23500,"desc":"Spear said to be carried by the god of wind"},
    {"id":"perfect_susanoo_sword","name":"Perfect Susanoo Sword","rarity":"Legendary","atk":200,"ability":"Susanoo Cleave","buff":{"type":"aoe","val":0},"price":30000,"desc":"The massive sword of a fully completed Susanoo"},
    {"id":"bijuu_bomb_cannon","name":"Bijuu Bomb Cannon","rarity":"Legendary","atk":195,"ability":"Bijuu Dama Blast","buff":{"type":"aoe","val":0},"price":29000,"desc":"Cannon that concentrates tailed beast chakra"},
    {"id":"six_path_staff","name":"Six Paths Staff","rarity":"Legendary","atk":188,"ability":"Truth Seeking Strike","buff":{"type":"unavoidable","val":0},"price":27000,"desc":"Staff wielded by the Sage of Six Paths"},
    {"id":"izanagi_blade","name":"Izanagi Blade","rarity":"Legendary","atk":182,"ability":"Reality Rewrite","buff":{"type":"dodge_next","val":0},"price":25500,"desc":"Blade that bends reality using the Izanagi ocular jutsu"},
    {"id":"limbo_sword","name":"Limbo Shadow Sword","rarity":"Legendary","atk":178,"ability":"Limbo Strike","buff":{"type":"unavoidable","val":0},"price":24500,"desc":"Sword that attacks through the invisible Limbo realm"},
    # ── Mythic (12) ──
    {"id":"sop_staff","name":"Sage of Six Paths Staff","rarity":"Mythic","atk":280,"ability":"Rikudo Chibaku Tensei","buff":{"type":"aoe","val":0},"price":80000,"desc":"The legendary staff of the founder of ninjutsu"},
    {"id":"otsutsuki_lance","name":"Otsutsuki Celestial Lance","rarity":"Mythic","atk":300,"ability":"Celestial Obliteration","buff":{"type":"unavoidable","val":0},"price":90000,"desc":"Lance wielded by the God Tree clan"},
    {"id":"kaguya_bone","name":"Kaguya Bone Blade","rarity":"Mythic","atk":275,"ability":"All-Killing Ash Bones","buff":{"type":"soul_rip","val":0},"price":78000,"desc":"A bone grown from Kaguya's own body, lethal on touch"},
    {"id":"hagoromo_staff","name":"Hagoromo's Staff","rarity":"Mythic","atk":290,"ability":"Creation of All Things","buff":{"type":"def_up","val":80},"price":85000,"desc":"Staff capable of creating life and matter"},
    {"id":"hamura_staff","name":"Hamura's Staff","rarity":"Mythic","atk":285,"ability":"Moon Gravity Crush","buff":{"type":"gravity_pull","val":0},"price":82000,"desc":"Staff linked to the moon and its gravitational force"},
    {"id":"indra_arrow","name":"Indra's Arrow Blade","rarity":"Mythic","atk":310,"ability":"Indra Arrow Strike","buff":{"type":"unavoidable","val":0},"price":95000,"desc":"Sasuke's most powerful attack crystallized into a blade"},
    {"id":"asura_hammer","name":"Asura Chakra Hammer","rarity":"Mythic","atk":295,"ability":"Asura Path Destroy","buff":{"type":"aoe","val":0},"price":88000,"desc":"The mechanical hammer arm of Asura's path"},
    {"id":"ten_tails_cannon","name":"Ten-Tails Cannon","rarity":"Mythic","atk":320,"ability":"Juubi Bomb","buff":{"type":"aoe","val":0},"price":100000,"desc":"Cannon manifesting the raw destructive power of the Ten-Tails"},
    {"id":"infinite_tsukuyomi_staff","name":"Infinite Tsukuyomi Staff","rarity":"Mythic","atk":305,"ability":"Eye of the Moon Strike","buff":{"type":"skip_turn","val":80},"price":92000,"desc":"Staff used to cast the Infinite Tsukuyomi genjutsu"},
    {"id":"truth_seeking_ball","name":"Truth-Seeking Ball Cannon","rarity":"Mythic","atk":298,"ability":"Ninshu Obliterate","buff":{"type":"def_break","val":90},"price":89000,"desc":"Condensed black chakra balls capable of nullifying all jutsu"},
    {"id":"karma_blade","name":"Karma Seal Blade","rarity":"Mythic","atk":288,"ability":"Karma Resonance","buff":{"type":"drain","val":70},"price":84000,"desc":"Blade hosting the Karma seal, absorbing enemy power"},
    {"id":"divine_tree_lance","name":"Divine Tree Lance","rarity":"Mythic","atk":315,"ability":"Chakra Harvest","buff":{"type":"drain","val":80},"price":97000,"desc":"Lance grown from the God Tree that harvests all chakra"},
]

WEAPON_RARITY_PRICE = {"Common":400,"Uncommon":900,"Rare":2500,"Epic":6000,"Legendary":25000,"Mythic":80000}
WEAPON_SHOP_SIZE = 5

def get_user_weapon_shop(uid: str):
    """Return 5 weapons unique to this user, refreshed daily."""
    from datetime import date as _date
    seed = int(uid) * 31 + int(_date.today().strftime("%Y%m%d"))
    rng = random.Random(seed)
    return rng.sample(WEAPONS, min(WEAPON_SHOP_SIZE, len(WEAPONS)))

def get_weapon_by_id(wid: str):
    return next((w for w in WEAPONS if w["id"] == wid), None)

RANKS=["Academy Student","Genin","Skilled Genin","Chunin","Elite Chunin","Jonin","Elite Jonin","ANBU","Kage Candidate","Kage"]
def rank_for_lv(lv): return RANKS[min(lv//10,len(RANKS)-1)]
def exp_for_lv(lv): return int(120*(lv**1.6))

# ─── DATABASE ───────────────────────────────────────────────────
async def init_db():
      """Create MongoDB indexes on first run."""
      await users_col.create_index("_id")
      await chars_col.create_index("uid")
      await chars_col.create_index([("uid", 1), ("level", -1)])
      await training_col.create_index([("uid", 1), ("char_id", 1)])
      await groups_col.create_index("_id")

async def db_get(uid):
    return await users_col.find_one({"_id": uid})

async def db_create(uid, name):
      try:
          await users_col.insert_one({
              "_id": uid, "name": name, "coins": 1500, "chakra": 0,
              "stones": 0, "nickname": "", "village": "Konoha", "clan": "",
              "rank": "Academy Student", "level": 1, "exp": 0,
              "wins": 0, "losses": 0, "daily_last": "", "mission_last": "",
              "exp_boost": 0, "streak": 0,
              "weapons": [], "equipped_weapon": None, "banned": False,
              "clan_rank": "Member", "clan_glory": 0,
          })
      except Exception:
          pass
  
async def db_set(uid, **kw):
      if not kw: return
      await users_col.update_one({"_id": uid}, {"$set": kw})
  
async def db_chars(uid):
      docs = await chars_col.find({"uid": uid}).sort([("level", -1), ("_id", 1)]).to_list(None)
      return [_cdoc(d) for d in docs]
async def db_team(uid):
      docs = await chars_col.find({"uid": uid, "in_team": 1}).sort([("slot", 1)]).to_list(None)
      return [_cdoc(d) for d in docs]
async def db_add_char(uid, name):
      pp = [random.randint(0, 31) for _ in range(5)]
      cd = get_cdata(name)
      rar = cd["rarity"] if cd else "Common"
      start_lv = {"Common": random.randint(1,5), "Uncommon": random.randint(3,8),
                  "Rare": random.randint(5,12),   "Epic": random.randint(8,18),
                  "Legendary": random.randint(15,25), "Mythic": random.randint(25,40)}.get(rar, 1)
      cid = await _next_char_id()
      await chars_col.insert_one({
          "_id": cid, "uid": uid, "char_name": name,
          "level": start_lv, "exp": 0,
          "pp_hp": pp[0], "pp_atk": pp[1], "pp_def": pp[2],
          "pp_spd": pp[3], "pp_cha": pp[4],
          "in_team": 0, "slot": 0, "forgotten_moves": []
      })
def pp_grade(v):
    if v==31: return "✨S"
    if v>=29: return "A+"
    if v>=24: return "A"
    if v>=18: return "B"
    if v>=11: return "C"
    if v>=5:  return "D"
    return "E"

def calc_stat(base, pp, lv=1):
    return int(base + pp*2 + (lv-1)*6)

# ── PP training cap per stat, by rarity ──────────────────────────
MAX_PP_BY_RARITY = {
    "Common":10, "Uncommon":15, "Rare":22,
    "Epic":32, "Legendary":45, "Mythic":63,
}

# ── Pending move-swap: uid → {char_id, char_name, new_move_key, new_move} ──
PENDING_MOVE_SWAP: dict = {}

# ── Level-up move unlocks: char_name → {level_threshold: move_key} ──
LEVEL_MOVE_UNLOCKS: dict = {
    "Naruto Uzumaki":     {10:"rasenshuriken",20:"rasenshuriken3",30:"tbb",40:"baryon_strike"},
    "Sasuke Uchiha":      {10:"raikiri",20:"kirin",30:"susanoo_arrow",40:"indraarow"},
    "Kakashi Hatake":     {10:"raikiri",20:"susanoo_arrow",30:"kirin"},
    "Minato Namikaze":    {10:"ftg",20:"rasenshuriken"},
    "Itachi Uchiha":      {10:"amaterasu",20:"totsuka",30:"koto_amatsukami"},
    "Madara Uchiha":      {10:"perfect_susanoo",20:"tengai_meteor",30:"limbo"},
    "Hashirama Senju":    {10:"wood_dragon",20:"forest_trap"},
    "Orochimaru":         {10:"curse_seal",20:"snake_fang"},
    "Gaara":              {10:"sand_burial",20:"desert_requiem",30:"shukaku_blast"},
    "Jiraiya":            {10:"toad_fire",20:"sage_mode_atk",30:"rasenshuriken2"},
    "Tsunade Senju":      {10:"monster_punch",20:"mystical_palm"},
    "Might Guy":          {10:"eight_gates",20:"evening_elephant"},
    "Killer Bee":         {10:"lariat2",20:"tbb"},
    "Nagato (Pain)":      {10:"chibaku_tensei",20:"planetary_dev"},
    "Konan":              {10:"paper_bomb_sea"},
    "Deidara":            {10:"c2_dragon",20:"c3_bomb"},
    "Sasori":             {10:"sasori_combo",20:"scorpion_tail"},
    "Shikamaru Nara":     {10:"shadow_king",20:"shadow_stitch"},
    "Temari":             {10:"vacuum_sphere",20:"wind_dance"},
    "Choji Akimichi":     {10:"butterfly_bomb"},
    "Ino Yamanaka":       {10:"mind_transfer",20:"koto_amatsukami"},
    "Shino Aburame":      {10:"insect_swarm",20:"poison_cloud"},
    "Sai":                {10:"super_beast"},
    "Yamato":             {10:"wood_dragon",20:"forest_trap"},
    "Darui":              {10:"black_lightning",20:"lariat"},
    "Sakura Haruno":      {10:"monster_punch",20:"mystical_palm"},
    "Rock Lee":           {10:"strong_fist",20:"dynamic_entry"},
    "Neji Hyuga":         {10:"rotation",20:"eight_trigrams"},
    "Hinata Hyuga":       {10:"twin_palms",20:"rotation"},
    "Kiba Inuzuka":       {10:"fang_over_fang"},
    "Kankuro":            {10:"scorpion_tail",20:"puppet_bomb"},
    "A (Fourth Raikage)": {10:"thunder_god",20:"lariat"},
    "Obito Uchiha":       {10:"perfect_susanoo",20:"gedo_mazo"},
}

def get_cdata(name):
    return next((c for c in CHARACTERS if c["name"]==name), None)

def get_char_moves(char_name: str, level: int) -> list:
    """Moves unlocked at given level: 1 move (lv1), +1 at lv10/20/30."""
    cd = get_cdata(char_name)
    if not cd or not cd.get("moves"):
        return [dict(M.get("punch", next(iter(M.values()))))]
    all_moves = cd["moves"]
    count = 1 + (1 if level >= 10 else 0) + (1 if level >= 20 else 0) + (1 if level >= 30 else 0)
    return all_moves[:min(count, len(all_moves))]

_EFF_MAP = {
    "burn":"Burn","stun":"Stun","poison":"Poison","bleed":"Bleed",
    "aoe":"AoE","def_up":"+DEF","spd_down":"-SPD","multi_hit":"Multi",
    "pierce":"Pierce","crit":"+Crit","def_break":"Break DEF",
    "soul_rip":"SoulRip","skip_turn":"Skip","unavoidable":"Sure-Hit",
    "dodge_next":"Dodge","reflect_dmg":"Reflect","seal":"Seal",
    "chain":"Chain","acc_down":"-Acc","gravity_pull":"Gravity",
    "chakra_drain":"Drain","scorch":"Scorch","self_dmg":"Recoil",
}
def fmt_effect(eff: str) -> str:
    if not eff: return ""
    tag, _, val = eff.partition(":")
    label = _EFF_MAP.get(tag, tag)
    return f"{label} {val}%" if val and val != "0" else label

def hp_bar(cur, mx, length=12):
    ratio = max(0, min(1, cur/max(mx,1)))
    filled = int(ratio*length)
    bar = "█"*filled + "░"*(length-filled)
    pct = int(ratio*100)
    color = "<tg-emoji emoji-id='5958636789504676899'>🟢</tg-emoji>" if pct>60 else ("<tg-emoji emoji-id='5915696866120438280'>🟡</tg-emoji>" if pct>30 else "<tg-emoji emoji-id='5798530836890390483'>🔴</tg-emoji>")
    return f"{color}[{bar}] {cur}/{mx}"

def nat_icon(nat): return NAT_EMO.get(nat,"<tg-emoji emoji-id='5426872512015244606'>🌿</tg-emoji>")

# HTML-mode nature icon — returns a pe() custom emoji tag for the given nature
_NAT_PE_KEY = {
    "Fire":"nat_fire","Water":"nat_water","Lightning":"nat_light",
    "Wood":"nat_wood","Ice":"nat_ice","Yang":"nat_sun","Explosion":"nat_exp",
    "Metal":"nat_gear",
}
def nat_pe(nat: str) -> str:
    key = _NAT_PE_KEY.get(nat)
    if key:
        return pe(key)
    return NAT_EMO.get(nat, "<tg-emoji emoji-id='5426872512015244606'>🌿</tg-emoji>")

# ─── LEVEL UP COSTS ─────────────────────────────────────────────
LEVELUP_COSTS = {1:20, 5:90, 10:160}
MAX_CHAR_LEVEL = 100

# ─── BATTLE ENGINE ──────────────────────────────────────────────
def apply_kg_to_attack(kg_name, base_crit, base_acc, move_type):
    info = KG.get(kg_name, KG["None"])
    crit = base_crit + info.get("crit", 0)
    acc  = min(100, base_acc + info.get("acc", 0))
    dmg_mult = 1.0 + info.get("all_stats", 0)
    tb = info.get("type_bonus", {})
    if move_type in tb:
        dmg_mult += tb[move_type]
    return crit, acc, dmg_mult

def resolve_attack(move, atk_stat, def_stat, atk_nat, def_nat, user_kg, enemy_kg,
                   atk_lv=1, def_lv=1):
    base_crit = 8
    crit, acc, dmg_mult = apply_kg_to_attack(user_kg, base_crit, move["acc"], move["type"])
    if not (random.randint(1,100) <= acc):
        return {"hit":False,"dmg":0,"crit":False,"mult":1.0,"eff_txt":"miss","effects":[],"reflect":0,"kg_def":""}
    mult = type_mult(move["type"], def_nat)
    is_crit = random.randint(1,100) <= crit
    if is_crit and KG.get(enemy_kg,{}).get("no_crit"): is_crit = False
    crit_m = 1.6 if is_crit else 1.0
    # Level advantage bonus: +2% per level
    lv_bonus = 1.0 + max(0, atk_lv - def_lv) * 0.02
    raw = int(move["power"]/100 * (atk_stat/max(def_stat*0.5,1)) * mult * crit_m * dmg_mult * lv_bonus * random.uniform(0.9,1.1) * 30)
    raw = max(1, raw)
    kg_def = ""
    reflected = 0
    info_d = KG.get(enemy_kg, KG["None"])
    if info_d.get("reflect"):
        reflected = int(raw * info_d["reflect"])
        kg_def = f"<tg-emoji emoji-id='5769455402945090965'>🔄</tg-emoji> Reflects <b>{reflected} HP</b>!"
    if info_d.get("pierce_def"):
        extra = int(raw * info_d["pierce_def"])
        raw += extra
        kg_def = f"<tg-emoji emoji-id='5454122580564786042'>💎</tg-emoji> Pierces <b>{extra}</b> extra!"
    effects = []
    ef = move.get("effect","") or ""
    if ":" in ef:
        etype, eval_ = ef.split(":",1)
        chance = int(eval_) if eval_.isdigit() else 0
        if etype in ("stun","burn","poison","bleed","scorch"):
            if chance==0 or random.randint(1,100)<=chance:
                effects.append(etype)
        elif etype in ("def_break","chakra_drain","spd_down","acc_down","def_up","dodge_next","multi_hit"):
            effects.append(etype)
        elif etype == "self_dmg":
            effects.append(f"self_dmg:{eval_}")
    if KG.get(user_kg,{}).get("dot") == "scorch":
        effects.append("scorch")
    et  = eff_text(mult)
    ct  = f"{pe('crit')} CRIT! " if is_crit else ""
    return {"hit":True,"dmg":raw,"crit":is_crit,"mult":mult,"eff_txt":f"{ct}{et}",
            "effects":effects,"reflect":reflected,"kg_def":kg_def}

def kg_turn_regen(kg_name, cur_hp, max_hp):
    info = KG.get(kg_name, KG["None"])
    regen = info.get("regen",0)
    if regen:
        gain = int(max_hp*regen)
        return gain, f"💚 {kg_name}: +{gain} HP"
    if info.get("shield") and cur_hp <= max_hp*0.3:
        gain = int(max_hp*info["shield"])
        return gain, f"<tg-emoji emoji-id='6039727447090403055'>🛡️</tg-emoji> Sand Armor: +{gain} HP"
    return 0, ""

def apply_dot(dot, hp):
    if not dot: return hp, ""
    dtype, turns = dot
    dmg = {"burn":22,"poison":28,"bleed":18,"scorch":25}.get(dtype,15)
    return max(0,hp-dmg), f"☠️ {dtype.title()} DoT **-{dmg} HP**"

def tick_dot(dot):
    if not dot: return None
    dtype, turns = dot
    return None if turns<=1 else (dtype, turns-1)

def apply_effects_to_state(effects, session, who):
    notes = []
    for e in effects:
        if e in ("stun","burn","poison","bleed","scorch"):
            if e=="stun":
                session[f"{who}_status"]="stun"; notes.append("😵 STUNNED!")
            else:
                session[f"{who}_dot"]=(e,3)
                icons={"burn":"<tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji>","poison":"☠️","bleed":"<tg-emoji emoji-id='5960999309280284625'>🩸</tg-emoji>","scorch":"🌡️"}
                notes.append(f"{icons.get(e, pe('lightning'))} {e.title()}!")
        elif e=="def_break":
            session[f"{who}_def_broken"]=True; notes.append("<tg-emoji emoji-id='6039727447090403055'>🛡️</tg-emoji> DEF broken!")
        elif e=="multi_hit":
            notes.append("<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> Multi-hit!")
    return notes

def apply_effects_pvp(effects, state, vid):
    notes = []
    for e in effects:
        if e in ("stun","burn","poison","bleed","scorch"):
            if e=="stun":
                state["status"][vid]="stun"; notes.append("😵 STUNNED!")
            else:
                state["dot"][vid]=(e,3)
                icons={"burn":"<tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji>","poison":"☠️","bleed":"<tg-emoji emoji-id='5960999309280284625'>🩸</tg-emoji>","scorch":"🌡️"}
                notes.append(f"{icons.get(e, pe('lightning'))} {e.title()}!")
        elif e=="def_break":
            state["def_broken"][vid]=True; notes.append("<tg-emoji emoji-id='6039727447090403055'>🛡️</tg-emoji> DEF broken!")
        elif e=="dodge_next":
            state["dodge_next"][vid]=True; notes.append("<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> Dodge next!")
        elif e=="multi_hit":
            notes.append("<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> Multi-hit combo!")
    return notes

# ─── DISPLAY HELPERS ────────────────────────────────────────────
def fmt_battle_text(session, log=""):
    """Format explore battle screen like the reference screenshot"""
    en   = session["enemy"]
    php,pmx = session["p_hp"],session["p_max_hp"]
    ehp,emx = session["e_hp"],session["e_max_hp"]
    pnat = session["p_nat"]; enat = en["nat"]
    pst  = " 😵STUN" if session.get("p_status")=="stun" else ""
    est  = " 😵STUN" if session.get("e_status")=="stun" else ""
    pdot = session.get("p_dot"); edot = session.get("e_dot")
    pdt  = f" ☠️{pdot[0]}({pdot[1]}t)" if pdot else ""
    edt  = f" ☠️{edot[0]}({edot[1]}t)" if edot else ""
    plv  = session.get("p_level",1); elv  = session.get("e_level",1)
    ptrans = "<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji>TRANSFORMED " if session.get("p_transformed") else ""
    # Bijuu Mode indicator
    bijuu_tag = ""
    if session.get("bijuu_active"):
        b_turns = session.get("bijuu_turns_left", 0)
        b_name  = session.get("bijuu_beast_name", "Beast")
        bi_info = BEASTS.get(b_name, {})
        bijuu_tag = f"<tg-emoji emoji-id='6003600664687546316'>🦊</tg-emoji>BIJUU MODE ({b_turns}t) "

    import re as _re
    def _log_html(s: str) -> str:
        # Log already contains HTML tags (<tg-emoji>, <b>, etc.) — do NOT escape.
        # Only convert any remaining **markdown** bold markers for safety.
        s = _re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
        s = _re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<b>\1</b>', s)
        return s

    txt  = f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> ━━━━ BATTLE ━━━━\n\n"
    txt += f"{pe('dot_red')} Wild : <b>{hesc(en['name'])}</b> [{hesc(enat)} {nat_pe(enat)}]\n"
    txt += f"Lv.{elv} | HP : {ehp}/{emx}{est}{edt}\n"
    txt += f"{hp_bar(ehp,emx)}\n\n"
    txt += f"{pe('dot_blue')} {ptrans}{bijuu_tag}<b>{hesc(session['p_char'])}</b> [{hesc(pnat)} {nat_pe(pnat)}]\n"
    txt += f"Lv.{plv} | HP : {php}/{pmx}{pst}{pdt}\n"
    txt += f"{hp_bar(php,pmx)}\n"

    # Active mechanics summary
    kg_info = KG.get(session.get("p_kg","None"), KG["None"])
    kg_notes = []
    if kg_info.get("crit"):    kg_notes.append(f"Crit+{kg_info['crit']}%")
    if kg_info.get("acc"):     kg_notes.append(f"Acc+{kg_info['acc']}%")
    if kg_info.get("regen"):   kg_notes.append(f"Regen {int(kg_info['regen']*100)}%/turn")
    if kg_info.get("reflect"): kg_notes.append(f"Reflect {int(kg_info['reflect']*100)}%")
    if kg_info.get("revive"):  kg_notes.append("1x Revive")
    nat_adv = ADV.get(session["p_nat"],{}).get("s",[])
    if nat_adv:                kg_notes.append(f"Strong vs {'/'.join(nat_adv[:2])}")
    if kg_notes:
        txt += f"KG: {' | '.join(kg_notes)}\n"

    # Show active char's tailed beast info
    cd = get_cdata(session["p_char"])
    tb_name = cd.get("tailed_beast") if cd else None
    if tb_name and tb_name in BEASTS:
        bi = BEASTS[tb_name]
        txt += f"{bi.get('emoji','🦊')} Beast: <b>{hesc(tb_name)}</b> ({bi['tails']} tails) | Pwr:{bi['power']:,}\n"

    # Show moves list
    base_crit = 8 + kg_info.get("crit", 0)
    if cd:
        txt += "\n"
        plv_for_moves = session.get("p_level", 1)
        for m in get_char_moves(session["p_char"], plv_for_moves):
            eff = fmt_effect(m.get("effect",""))
            eff_part = f" | {eff}" if eff else ""
            txt += f"• <b>{hesc(m['name'])}</b> [{hesc(m['type'])} {nat_pe(m['type'])}]\n"
            txt += f"  Pwr:{m['power']} | Acc:{m['acc']}% | Crit:{base_crit}%{eff_part}\n"

    if log:
        txt += f"\n<b>Last turn:</b>\n{_log_html(log)}"

    # Transform available?
    if session.get("transform_available") and not session.get("p_transformed"):
        txt += f"\n\n{pe('flame')} <b>TRANSFORM AVAILABLE!</b>"
    # Bijuu Mode available?
    if session.get("bijuu_avail") and not session.get("bijuu_active"):
        txt += f"\n<tg-emoji emoji-id='6003600664687546316'>🦊</tg-emoji> <b>BIJUU MODE READY!</b>"
    return txt

def fmt_pvp_text(state, log=""):
    tid = state["turn"]
    oid = state["p2"] if tid==state["p1"] else state["p1"]
    tc,oc = state["cur"][tid],state["cur"][oid]
    thp,ohp = state["hp"][tid],state["hp"][oid]
    tmx,omx = state["mhp"][tid],state["mhp"][oid]
    tkg,okg = state["kg"][tid],state["kg"][oid]
    tnat,onat = state["nat"][tid],state["nat"][oid]
    tlv,olv = state["lv"][tid],state["lv"][oid]
    tdot = state.get("dot",{}).get(tid); odot = state.get("dot",{}).get(oid)
    tst  = state.get("status",{}).get(tid,""); ost  = state.get("status",{}).get(oid,"")
    tdt  = f" ☠️{tdot[0]}({tdot[1]}t)" if tdot else ""
    odt  = f" ☠️{odot[0]}({odot[1]}t)" if odot else ""
    tss  = " 😵STUN" if tst=="stun" else ""; oss  = " 😵STUN" if ost=="stun" else ""
    ttrans = "<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> " if state.get("transformed",{}).get(tid) else ""
    otrans = "<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> " if state.get("transformed",{}).get(oid) else ""
    tn = state.get("names",{})

    tcd = get_cdata(tc); ocd = get_cdata(oc)
    txt  = f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> ━━━━ PVP BATTLE ━━━━\n\n"
    txt += f"<tg-emoji emoji-id='5798530836890390483'>🔴</tg-emoji> <b>{oc}</b> [{onat} {nat_icon(onat)}]\n"
    txt += f"Lv.{olv} | HP : {ohp}/{omx}{oss}{odt}\n"
    txt += f"{hp_bar(ohp,omx)}\n\n"
    txt += f"Turn : {tn.get(tid,'?')}\n"
    txt += f"<tg-emoji emoji-id='5798483635199807367'>🔵</tg-emoji> {ttrans}<b>{tc}</b> [{tnat} {nat_icon(tnat)}]\n"
    txt += f"Lv.{tlv} | HP : {thp}/{tmx}{tss}{tdt}\n"
    txt += f"{hp_bar(thp,tmx)}\n"

    tkg_info = KG.get(tkg, KG["None"])
    tbase_crit = 8 + tkg_info.get("crit", 0)
    tkg_notes = []
    if tkg_info.get("crit"):    tkg_notes.append(f"Crit+{tkg_info['crit']}%")
    if tkg_info.get("acc"):     tkg_notes.append(f"Acc+{tkg_info['acc']}%")
    if tkg_info.get("regen"):   tkg_notes.append(f"Regen {int(tkg_info['regen']*100)}%/turn")
    if tkg_info.get("reflect"): tkg_notes.append(f"Reflect {int(tkg_info['reflect']*100)}%")
    if tkg_info.get("revive"):  tkg_notes.append("1x Revive")
    tnat_adv = ADV.get(tnat,{}).get("s",[])
    if tnat_adv:                tkg_notes.append(f"Strong vs {'/'.join(tnat_adv[:2])}")
    if tkg_notes:
        txt += f"KG: {' | '.join(tkg_notes)}\n"

    if tcd:
        txt += "\n"
        for m in get_char_moves(tc, tlv):
            miss_pct = max(0, 100 - m["acc"])
            eff = fmt_effect(m.get("effect",""))
            eff_part = f" | {eff}" if eff else ""
            txt += f"• <b>{m['name']}</b> [{m['type']} {nat_icon(m['type'])}]\n"
            txt += f"  Pwr:{m['power']} | Acc:{m['acc']}% | Crit:{tbase_crit}%{eff_part}\n"

    if log:
        txt += f"\n<b>Last:</b>\n{log}"
    if state.get("transform_avail",{}).get(tid) and not state.get("transformed",{}).get(tid):
        txt += f"\n\n<tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji> <b>TRANSFORM AVAILABLE!</b>"
    return txt

def move_btns_explore(moves, uid, transform_avail=False, weapon=None, weapon_used=False, bijuu_avail=False):
    kb = []
    row = []
    for i,m in enumerate(moves):
        label = m['name'][:20]
        row.append(Btn(label, callback_data=f"ex:m{i}:{uid}"))
        if len(row)==2: kb.append(row); row=[]
    if row: kb.append(row)
    if weapon and not weapon_used:
        kb.append([Btn(f"Use Weapon: {weapon['name'][:18]}", callback_data=f"ex:wpn:{uid}")])
    special_row = []
    if transform_avail:
        special_row.append(Btn("TRANSFORM!", callback_data=f"ex:tf:{uid}"))
    if bijuu_avail:
        special_row.append(Btn("Bijuu Mode!", callback_data=f"ex:bijuu:{uid}"))
    if special_row:
        kb.append(special_row)
    last_row = []
    last_row.append(Btn("Weapons", callback_data=f"ex:weap:{uid}"))
    last_row.append(Btn("Switch", callback_data=f"ex:swlist:{uid}"))
    last_row.append(Btn("Run Away", callback_data=f"ex:run:{uid}"))
    kb.append(last_row)
    return kb

def move_btns_pvp(moves, c_uid, t_uid, transform_avail=False):
    kb = []
    row = []
    for i,m in enumerate(moves):
        label = m['name'][:20]
        row.append(Btn(label, callback_data=f"pm:{i}:{c_uid}:{t_uid}"))
        if len(row)==2: kb.append(row); row=[]
    if row: kb.append(row)
    last_row = []
    if transform_avail:
        last_row.append(Btn("TRANSFORM!", callback_data=f"pvtf:{c_uid}:{t_uid}"))
    last_row.append(Btn("Forfeit", callback_data=f"pf:{c_uid}:{t_uid}"))
    kb.append(last_row)
    return kb

async def safe_edit(query, text, kb, photo=None, parse_mode="HTML"):
    # Check the actual message type rather than relying on a session flag alone
    is_photo_msg = bool(query.message and query.message.photo)
    try:
        if photo and is_photo_msg:
            await query.edit_message_caption(
                caption=text[:1020], parse_mode=parse_mode, reply_markup=Kbd(kb))
        else:
            await query.edit_message_text(
                text, parse_mode=parse_mode, reply_markup=Kbd(kb))
        return
    except Exception:
        pass
    # Fallback: try the opposite method
    try:
        if photo and is_photo_msg:
            await query.edit_message_text(
                text, parse_mode=parse_mode, reply_markup=Kbd(kb))
        else:
            await query.edit_message_caption(
                caption=text[:1020], parse_mode=parse_mode, reply_markup=Kbd(kb))
        return
    except Exception:
        pass
    # Last resort: send a new message so the user always gets a response
    try:
        await query.message.reply_text(
            text[:1020], parse_mode=parse_mode, reply_markup=Kbd(kb))
    except Exception:
        pass

# ─── SESSIONS ───────────────────────────────────────────────────
EX    = {}  # uid -> explore session
PVP   = {}  # bkey -> pvp state
TRADE = {}  # tkey -> trade state

ADMIN_ID = os.getenv("ADMIN_ID", "6671520580")  # Bot admin — set via ADMIN_ID env var
CHAL = {}  # t_uid -> {challenger_id}

# ─── HELPERS ────────────────────────────────────────────────────
async def need_account(update):
    uid = str(update.effective_user.id)
    user = await db_get(uid)
    if not user:
        await update.message.reply_text("No account! Use /start first.")
        return False
    if user.get("banned"):
        await update.message.reply_text("Your account has been banned from this bot.")
        return False
    return True

def gacha_pull():
    r = random.random(); cum = 0
    for rar,rate in RAR_RATES.items():
        cum += rate
        if r <= cum:
            pool = [c for c in CHARACTERS if c["rarity"]==rar]
            return random.choice(pool) if pool else random.choice(CHARACTERS)
    return random.choice(CHARACTERS)

def gacha_guaranteed(rarity):
    pool = [c for c in CHARACTERS if c["rarity"]==rarity]
    return random.choice(pool) if pool else random.choice(CHARACTERS)

def display_name(user):
    nick = user.get("nickname","") or ""
    return nick if nick else user.get("name","Shinobi")

# ─── /start ─────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = str(update.effective_user.id)
    name = update.effective_user.first_name or "Shinobi"
    user = await db_get(uid)
    # Persistent reply keyboard with quick-action shortcuts
    QUICK_KB = ReplyKeyboardMarkup(
        [[KeyboardButton("/explore"), KeyboardButton("/close")],
         [KeyboardButton("/travel"),  KeyboardButton("/daily")]],
        resize_keyboard=True, one_time_keyboard=False)
    if user:
        vi  = VILLAGES.get(user["village"],{})
        dn  = display_name(user)
        nc  = user["coins"]
        caption = (
            f"{pe('round','🔄')} <b>Welcome back, {hesc(dn)}!</b> i think we enjoying this game\n\n"
            f"Play games with friends and make fun in group\n\n"
            f"U need any help then contact admins in group :\n"
            f"──────────────────────────────────────────\n"
            f"{pe('round','🔄')}<b>Group :</b> @narutoorgg"
        )
        # Send banner photo with the quick-keyboard embedded — always send photo
        banner = _get_banner(START_BANNER)
        sent = False
        for _banner_url in [banner, START_BANNER]:
            if not _banner_url:
                continue
            try:
                await update.message.reply_photo(
                    photo=_banner_url, caption=caption,
                    parse_mode="HTML", reply_markup=QUICK_KB)
                sent = True
                break
            except Exception:
                continue
        if not sent:
            await update.message.reply_text(caption, parse_mode="HTML", reply_markup=QUICK_KB)
        return

    await db_create(uid, name)
    ctx.user_data["picks"] = []
    # Show banner with Start button for new user
    kb = [[Btn("Start Your Journey!", callback_data=f"st:begin:0")]]
    new_caption = (
        f"{pe('leaf')} <b>Welcome to Naruto RPG!</b>\n\n"
        f"{pe('rasengan')} Your shinobi journey is about to begin!\n"
        f"Choose <b>3 starter characters</b> to form your first team."
    )
    try:
        await update.message.reply_photo(
            photo=START_BANNER, caption=new_caption,
            parse_mode="HTML", reply_markup=Kbd(kb))
    except:
        await update.message.reply_text(
            f"{pe('leaf')} <b>Welcome to Naruto RPG!</b>\n\nTap below to begin!",
            parse_mode="HTML", reply_markup=Kbd(kb))

async def show_starter(msg_or_q, ctx, idx, edit=False):
    n     = len(STARTER_POOL)
    char  = STARTER_POOL[idx % n]
    picks = ctx.user_data.get("picks",[])
    kg    = CLAN_KG.get(char["clan"],"None")
    ki    = KG.get(kg,KG["None"])
    rr    = RAR.get(char["rarity"],"⚪")
    photo = PHOTO_CACHE.get(char["name"])
    txt   = (
        f"{pe('rasengan')} <b>Choose Your Starter</b> ({len(picks)}/3 chosen)\n\n"
        f"{rr} <b>{hesc(char['name'])}</b> ⟨{hesc(char['rarity'])}⟩\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{pe('leaf')} {hesc(char['nature'])} {nat_icon(char['nature'])} | {pe('village')} {hesc(char['village'])} | {pe('clan')} {hesc(char['clan'])}\n"
        f"{pe('lightning')} <b>KG: {hesc(kg)}</b>\n<i>{hesc(ki['desc'])}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{pe('hp')} HP <b>{char['base']['hp']}</b> | {pe('sword')} ATK <b>{char['base']['atk']}</b>\n"
        f"{pe('shield')} DEF <b>{char['base']['def']}</b> | 💨 SPD <b>{char['base']['speed']}</b>"
    )
    if picks:
        txt += f"\n\n✅ <b>Picked:</b> {hesc(', '.join(picks))}"
    kb = [[Btn("Prev",callback_data=f"st:prev:{idx}"),
           Btn(f"Pick ({len(picks)}/3)",callback_data=f"st:pick:{idx}"),
           Btn("Next",callback_data=f"st:next:{idx}")]]
    if edit:
        try:
            is_photo_msg = hasattr(msg_or_q, 'message') and bool(msg_or_q.message and msg_or_q.message.photo)
            if photo and is_photo_msg:
                # Swap both photo and caption in one call
                await msg_or_q.edit_message_media(
                    media=InputMediaPhoto(media=photo, caption=txt[:1020], parse_mode="HTML"),
                    reply_markup=Kbd(kb))
            elif is_photo_msg:
                # Keep existing photo, just update caption + buttons
                await msg_or_q.edit_message_caption(
                    caption=txt[:1020], parse_mode="HTML", reply_markup=Kbd(kb))
            else:
                await msg_or_q.edit_message_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))
        except Exception:
            pass
    else:
        if photo:
            try:
                await msg_or_q.reply_photo(photo=photo, caption=txt[:1020], parse_mode="HTML", reply_markup=Kbd(kb))
                return
            except: pass
        await msg_or_q.reply_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))

async def cb_starter(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts = q.data.split(":")
    action = parts[1]; idx_s = parts[2]
    idx = int(idx_s); uid = str(q.from_user.id)
    picks = ctx.user_data.setdefault("picks",[])
    n = len(STARTER_POOL)
    if action=="begin":
        await show_starter(q.message, ctx, 0, edit=False); return
    if action=="next": await show_starter(q, ctx, (idx+1)%n, edit=True)
    elif action=="prev": await show_starter(q, ctx, (idx-1)%n, edit=True)
    elif action=="pick":
        cname = STARTER_POOL[idx%n]["name"]
        if cname in picks: await q.answer("Already picked!",show_alert=True); return
        picks.append(cname)
        ctx.user_data["picks"] = picks
        if len(picks)>=3:
            for cn in picks: await db_add_char(uid, cn)
            new_chars = await chars_col.find({"uid": uid}).sort([("_id", 1)]).limit(3).to_list(None)
            for sl, row in enumerate(new_chars, 1):
                await chars_col.update_one({"_id": row["_id"]}, {"$set": {"in_team": 1, "slot": sl}})
            done_txt = (
                f"<tg-emoji emoji-id='5426976939850080222'>🎉</tg-emoji> <b>Starters Confirmed!</b>\n\n" +
                "\n".join(f"  <tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> {c}" for c in picks) +
                "\n\n<tg-emoji emoji-id='5426872512015244606'>🍃</tg-emoji> Your journey begins now!\n"
                "• /explore — Battle wild enemies\n"
                "• /summon — Get more characters\n"
                "• /team — Manage your team\n"
                "• /help — All commands"
            )
            try: await q.edit_message_caption(caption=done_txt[:1020], parse_mode="HTML")
            except:
                try: await q.edit_message_text(done_txt, parse_mode="HTML")
                except: pass
        else:
            await show_starter(q, ctx, (idx+1)%n, edit=True)

# ─── /profile ───────────────────────────────────────────────────
def _get_achievements(user, chars):
    """Return list of (title, description) tuples earned by user."""
    ach  = []
    lv   = user.get("level", 1)
    wins = user.get("wins", 0)
    stones = user.get("stones", 0)
    nc   = user.get("coins", 0)
    total_chars = len(chars) if chars else 0
    # Level titles
    if lv >= 100: ach.append(("God of Shinobi",   "Reached the maximum level of 100"))
    elif lv >= 75: ach.append(("Legend",            "Reached Level 75"))
    elif lv >= 50: ach.append(("Elite Shinobi",     "Reached Level 50"))
    elif lv >= 25: ach.append(("Veteran",           "Reached Level 25"))
    elif lv >= 10: ach.append(("Rising Shinobi",    "Reached Level 10"))
    elif lv >= 5:  ach.append(("Rookie",            "Reached Level 5"))
    # Battle titles
    if wins >= 100: ach.append(("Unstoppable",      "Won 100 or more battles"))
    elif wins >= 50: ach.append(("Battle Hardened", "Won 50 or more battles"))
    elif wins >= 10: ach.append(("Warrior",         "Won 10 or more battles"))
    elif wins >= 1:  ach.append(("First Blood",     "Earned first battle victory"))
    # Collection titles
    if total_chars >= 50: ach.append(("Completionist", "Collected 50 or more characters"))
    elif total_chars >= 20: ach.append(("Hoarder",    "Collected 20 or more characters"))
    elif total_chars >= 5:  ach.append(("Collector",  "Collected 5 or more characters"))
    # Stone titles
    if stones >= 10: ach.append(("Stone Lord",  "Accumulated 10 or more evolution stones"))
    elif stones >= 5: ach.append(("Stone Keeper","Accumulated 5 or more evolution stones"))
    # Wealth titles
    if nc >= 100000: ach.append(("Ryo Millionaire", "Amassed 100,000 or more NC"))
    elif nc >= 50000: ach.append(("Wealthy Shinobi","Amassed 50,000 or more NC"))
    return ach


async def cmd_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid   = str(update.effective_user.id)
    user  = await db_get(uid)
    chars = await db_chars(uid)
    team  = await db_team(uid)
    en    = exp_for_lv(user["level"] + 1)
    bar   = hp_bar(user["exp"], en)
    kg    = CLAN_KG.get(user["clan"], "None")
    ki    = KG.get(kg, KG["None"])
    dn    = display_name(user)
    clan_rank     = user.get("clan_rank", "Member")
    clan_rank_tag = CLAN_RANK_EMOJIS.get(clan_rank, "")
    admin_tag     = f"   {pe('star')} <b>[ADMIN]</b>" if uid == ADMIN_ID else ""
    SEP = "──────────────────────"
    rank_line = (f"{hesc(user['rank'])} — Level {user['level']}/100"
                 + (f"  {clan_rank_tag} <b>{clan_rank}</b>" if clan_rank != "Member" else ""))
    _profile_txt = (
        f"{pe('anbu')} <b>User Profile:</b>\n"
        f"{SEP}\n"
        f"<b>{hesc(dn)}</b>{admin_tag}\n"
        f"{SEP}\n"
        f"{pe('rank')} <b>Stats:</b>\n"
        f"{rank_line}\n"
        f"EXP: {bar}\n"
        f"{SEP}\n"
        f"{pe('coin')} <b>Collection:</b>\n"
        f"1) {pe('coin')} <b>{user['coins']:,} NC</b>\n"
        f"2) {pe('exp')} <b>{user['exp']}</b>\n"
        f"3) {pe('stone')} <b>{user.get('stones',0)} Stones</b>\n"
        f"4) {pe('sword')} <b>{user['wins']} W</b>\n"
        f"5) {pe('skull')} <b>{user['losses']} L</b>\n"
        f"{SEP}\n"
        f"{pe('lightning')} <b>KG:</b>\n"
        f"<b>{hesc(kg)}</b>\n"
        f"<i>{hesc(ki['desc'])}</i>\n\n"
        f"{pe('team')} <b>{len(chars)}</b> chars   {pe('anbu')} <b>{len(team)}/6</b> team"
    )
    achievements = _get_achievements(user, chars)
    kb = [[Btn("Village", callback_data="menu:village"),
           Btn("Clan",    callback_data="menu:clan")]]
    if achievements:
        kb.append([Btn(f"Achievements ({len(achievements)})", callback_data="menu:achievements")])
    try:
        photos = await ctx.bot.get_user_profile_photos(int(uid), limit=1)
        if photos and photos.photos:
            file_id = photos.photos[0][-1].file_id
            await update.message.reply_photo(
                photo=file_id,
                caption=_profile_txt[:1020],
                parse_mode="HTML", reply_markup=Kbd(kb))
            return
    except: pass
    await update.message.reply_text(_profile_txt, parse_mode="HTML", reply_markup=Kbd(kb))

# ─── /mychar — PAGINATED LIST ───────────────────────────────────
MYCHAR_PER_PAGE = 20

async def cmd_mychar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid   = str(update.effective_user.id)
    chars = await db_chars(uid)
    if not chars:
        await update.message.reply_text(
            "<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> No characters yet! Use /summon.",
            reply_markup=Kbd([[Btn("Summon Now",callback_data=f"sm:s:{uid}")]])); return
    args  = ctx.args
    if args:
        # /mychar <name> — search for a specific character
        query = " ".join(args).lower()
        matches = [c for c in chars if query in c["char_name"].lower()]
        if not matches:
            await update.message.reply_text(
                f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> No character matching <code>{query}</code> found!\nUse /mychar to see all.",
                parse_mode="HTML"); return
        if len(matches)==1:
            await send_char_card(update.message, ctx, uid, chars.index(matches[0]), chars, edit=False)
        else:
            # Multiple copies — show picker
            kb=[[Btn(f"{c['char_name']} Lv.{c['level']}{'  [Team]' if c['in_team'] else ''}",
                     callback_data=f"mc:{c['id']}:view")] for c in matches]
            await update.message.reply_text(
                f"<tg-emoji emoji-id='5426895906702107044'>📋</tg-emoji> <b>{len(matches)} copies of this character:</b>\nChoose which one to view:",
                parse_mode="HTML", reply_markup=Kbd(kb))
        return
    await send_mychar_list(update.message, uid, chars, page=0, edit=False)

async def send_mychar_list(target, uid, chars, page=0, edit=False):
    total = len(chars)
    pages = max(1, (total + MYCHAR_PER_PAGE - 1) // MYCHAR_PER_PAGE)
    page  = max(0, min(page, pages-1))
    start = page * MYCHAR_PER_PAGE
    batch = chars[start:start+MYCHAR_PER_PAGE]

    lines = []
    for i,c in enumerate(batch, start+1):
        cd   = get_cdata(c["char_name"])
        rar  = RAR.get(cd["rarity"],"⚪") if cd else "⚪"
        team = " 👥" if c["in_team"] else "  "
        nat  = nat_icon(cd["nature"]) if cd else "🌿"
        lines.append(f"{i}. {rar}{team} <b>{hesc(c['char_name'])}</b> Lv.{c['level']} {nat}")

    txt = (
        f"🎒 <b>Your Characters:</b>\n\n"
        + "\n".join(lines) +
        f"\n\n{pe('exp')} Total: <b>{total}</b> | Page: <b>{page+1}/{pages}</b>"
    )
    kb = []
    nav = []
    if page > 0:
        nav.append(Btn("<",callback_data=f"ml:{uid}:{page-1}"))
    nav.append(Btn(f"{page+1}/{pages}",callback_data="noop"))
    if page < pages-1:
        nav.append(Btn(">",callback_data=f"ml:{uid}:{page+1}"))
    if nav: kb.append(nav)
    jump = []
    if page >= 5:
        jump.append(Btn("<<5",callback_data=f"ml:{uid}:{page-5}"))
    if page + 5 < pages:
        jump.append(Btn("5>>",callback_data=f"ml:{uid}:{page+5}"))
    if jump: kb.append(jump)
    kb.append([Btn("View Char Details",callback_data=f"mcd:{uid}:{page}")])

    if edit:
        is_photo = bool(getattr(target, 'message', None) and target.message.photo)
        try:
            if is_photo:
                await target.edit_message_caption(caption=txt[:1020], parse_mode="HTML", reply_markup=Kbd(kb))
            else:
                await target.edit_message_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))
        except: pass
    else:
        await target.reply_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))

async def _safe_edit(q, text: str, kb=None):
    """Edit a message in-place, handling both text and photo messages correctly.
    For photo messages, uses edit_message_caption (not edit_message_text which
    raises 'There is no text in the message to edit').
    Always uses HTML parse_mode — NEVER fall back to None (raw mode) because
    that would render <tg-emoji> tags as visible plain text.
    """
    markup = Kbd(kb) if kb else None
    is_photo = bool(q.message and q.message.photo)
    # Truncate safely so we never cut a <tg-emoji> tag in the middle.
    def _safe_trunc(s: str, limit: int) -> str:
        if len(s) <= limit:
            return s
        cut = s[:limit]
        # Walk back to ensure we don't slice inside an open HTML tag
        last_open = cut.rfind("<")
        last_close = cut.rfind(">")
        if last_open > last_close:
            cut = cut[:last_open]
        return cut
    safe_text = _safe_trunc(text, 1020)
    try:
        if is_photo:
            await q.edit_message_caption(caption=safe_text, parse_mode="HTML",
                                         reply_markup=markup)
        else:
            await q.edit_message_text(safe_text, parse_mode="HTML",
                                      reply_markup=markup)
        return
    except Exception:
        pass
    # Last resort: send a new reply (avoids silent failure) — still HTML only.
    try:
        await q.message.reply_text(safe_text, parse_mode="HTML",
                                   reply_markup=markup)
    except Exception:
        pass

def _safe_trunc_battle(s: str, limit: int = 1020) -> str:
    """Truncate battle text without cutting through an open <tg-emoji> tag."""
    if len(s) <= limit:
        return s
    cut = s[:limit]
    lo = cut.rfind("<")
    lc = cut.rfind(">")
    if lo > lc:
        cut = cut[:lo]
    return cut

async def make_vs_photo(p_char_name: str, enemy_name: str, enemy_url=None):
    """Create a side-by-side VS battle image using PIL. Returns BytesIO or None."""
    try:
        from PIL import Image, ImageDraw
        p_url = best_char_photo(p_char_name)
        e_url = enemy_url or PHOTO_CACHE.get(enemy_name.lower())

        async def _dl(url):
            if not url:
                return None
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10, follow_redirects=True) as cl:
                    r = await cl.get(url)
                    if r.status_code == 200 and r.content:
                        return Image.open(io.BytesIO(r.content)).convert("RGBA")
            except Exception:
                pass
            return None

        p_img = await _dl(p_url)
        e_img = await _dl(e_url)
        if not p_img and not e_img:
            return None

        SZ, VS_W, BD = 220, 60, 6
        W = SZ * 2 + VS_W + BD * 4
        H = SZ + BD * 2
        canvas = Image.new("RGB", (W, H), (18, 18, 24))
        draw = ImageDraw.Draw(canvas)

        def _fit(img):
            bg = Image.new("RGBA", (SZ, SZ), (30, 30, 40, 255))
            img.thumbnail((SZ, SZ), Image.LANCZOS)
            ox = (SZ - img.width) // 2
            oy = (SZ - img.height) // 2
            bg.paste(img, (ox, oy), img if img.mode == "RGBA" else None)
            return bg.convert("RGB")

        if p_img:
            canvas.paste(_fit(p_img), (BD, BD))
        if e_img:
            canvas.paste(_fit(e_img), (SZ + VS_W + BD * 3, BD))

        vx = SZ + BD * 2 + 6
        vy = H // 2 - 14
        draw.text((vx + 1, vy + 1), "VS", fill=(80, 0, 0))
        draw.text((vx, vy), "VS", fill=(220, 50, 50))
        draw.line([(SZ + BD * 2, BD), (SZ + BD * 2, H - BD)], fill=(60, 60, 80), width=2)
        draw.line([(SZ + VS_W + BD * 2, BD), (SZ + VS_W + BD * 2, H - BD)], fill=(60, 60, 80), width=2)

        buf = io.BytesIO()
        canvas.save(buf, format="JPEG", quality=82)
        buf.seek(0)
        buf.name = "battle_vs.jpg"
        return buf
    except Exception as e:
        print(f"make_vs_photo error: {e}")
        return None

async def _fetch_photo(url: str):
    """Pre-download a photo URL and return an io.BytesIO object for Telegram.
    Returns BytesIO on success, None on failure (never returns URL string —
    passing unverified URLs to edit_message_media causes silent failures).
    """
    if not url:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            r = await client.get(url)
            print(f"📷 _fetch_photo {url[:60]}… → HTTP {r.status_code} ({len(r.content)} bytes)")
            if r.status_code == 200 and r.content:
                buf = io.BytesIO(r.content)
                buf.name = "photo.jpg"
                return buf
            print(f"<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji> _fetch_photo non-200: {r.status_code}")
    except Exception as e:
        print(f"<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji> _fetch_photo exception: {e}")
    return None  # Do NOT fall back to URL — unverified URLs break edit_message_media

async def cb_mychar_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts = q.data.split(":")
    if q.data == "noop": return
    if parts[0] == "ml":
        uid = parts[1]; page = int(parts[2])
        if str(q.from_user.id) != uid:
            await q.answer("Not yours!",show_alert=True); return
        chars = await db_chars(uid)
        await send_mychar_list(q, uid, chars, page=page, edit=True)
    elif parts[0] == "mcd":
        await q.answer("Use /stats or /wiki to see full character details!", show_alert=True)
        return

async def send_char_card(target, ctx, uid, idx, chars, edit=False):
    c   = chars[idx]
    cd  = get_cdata(c["char_name"])
    if not cd: return
    kg  = CLAN_KG.get(cd["clan"],"None")
    ki  = KG.get(kg,KG["None"])
    rr  = RAR.get(cd["rarity"],"⚪")
    lv  = c["level"]
    hp  = calc_stat(cd["base"]["hp"],   c["pp_hp"],  lv)
    atk = calc_stat(cd["base"]["atk"],  c["pp_atk"], lv)
    dfc = calc_stat(cd["base"]["def"],   c["pp_def"],  lv)
    spd = calc_stat(cd["base"]["speed"],c["pp_spd"], lv)
    cha = cd["base"]["chakra"] + c["pp_cha"]*2
    tpp = c["pp_hp"]+c["pp_atk"]+c["pp_def"]+c["pp_spd"]+c["pp_cha"]
    ts  = "<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> In Team" if c["in_team"] else "<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Bench"
    form= cd.get("form",{})
    tb  = cd.get("tailed_beast")
    next_lv_exp = exp_for_lv(lv+1) if lv < MAX_CHAR_LEVEL else 0
    exp_bar = hp_bar(c["exp"], next_lv_exp) if next_lv_exp else "MAX LEVEL ✨"

    txt = (
        f"{rr} <b>{hesc(c['char_name'])}</b> ⟨{cd['rarity']}⟩\n"
        f"Lv.<b>{lv}</b>/100  |  EXP: {c['exp']}/{next_lv_exp}\n"
        f"{exp_bar}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5426872512015244606'>🌿</tg-emoji> {cd['nature']} {nat_icon(cd['nature'])} | <tg-emoji emoji-id='5427342518876381603'>🏘️</tg-emoji> {cd['village']} | <tg-emoji emoji-id='5224388744156557558'>🧬</tg-emoji> {cd['clan']}\n"
        f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>KG: {kg}</b> <i>{ki['desc'][:40]}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5427095369278299187'>❤️</tg-emoji> HP  {hp:>5}  [{pp_grade(c['pp_hp'])}]\n"
        f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> ATK {atk:>5}  [{pp_grade(c['pp_atk'])}]\n"
        f"<tg-emoji emoji-id='6039727447090403055'>🛡️</tg-emoji> DEF {dfc:>5}  [{pp_grade(c['pp_def'])}]\n"
        f"💨 SPD {spd:>5}  [{pp_grade(c['pp_spd'])}]\n"
        f"<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> CHK {cha:>5}  [{pp_grade(c['pp_cha'])}]\n"
        f"<tg-emoji emoji-id='5981204549132619885'>📊</tg-emoji> PP: {tpp}/155 ({int(tpp/155*100)}%)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji> Form: {form.get('name','None') if form else 'None'}\n"
        + (f"{pe('bijuu')} Beast: <b>{hesc(tb)}</b>\n" if tb else "")
        + f"{ts} ({idx+1}/{len(chars)})"
    )
    kb = [
        [Btn("<",callback_data=f"mc:{c['id']}:prev"),
         Btn("Moves",callback_data=f"mc:{c['id']}:moves"),
         Btn(">",callback_data=f"mc:{c['id']}:next")],
        [Btn("Toggle Team",callback_data=f"mc:{c['id']}:team"),
         Btn("List View",callback_data=f"ml:{uid}:0")],
        [Btn("Train",callback_data=f"mc:{c['id']}:train"),
         Btn("Release",callback_data=f"mc:{c['id']}:release")],
    ]
    photo = best_char_photo(cd["name"])
    if edit:
        try: await target.edit_message_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))
        except: pass
        return
    if photo:
        try:
            await target.reply_photo(photo=photo, caption=txt[:1020],
                parse_mode="HTML", reply_markup=Kbd(kb))
            return
        except: pass
    await target.reply_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))

async def cb_mychars(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts = q.data.split(":")
    cid   = int(parts[1]); action = parts[2]
    uid   = str(q.from_user.id)
    chars = await db_chars(uid)
    if not chars: await q.edit_message_text("No characters!"); return
    idx   = next((i for i,c in enumerate(chars) if c["id"]==cid), 0)

    if action in ("next","prev"):
        if action=="next": idx=(idx+1)%len(chars)
        else: idx=(idx-1)%len(chars)
        try: await q.message.delete()
        except: pass
        await send_char_card(q.message, ctx, uid, idx, chars, edit=False); return

    if action=="moves":
        c=chars[idx]; cd=get_cdata(c["char_name"])
        if not cd: return
        lines=[]
        for m in cd["moves"]:
            strong=[n for n in ALL_NATURES if type_mult(m["type"],n)>1.0]
            hint=f"<tg-emoji emoji-id='5803416753031615097'>⬆️</tg-emoji> vs {','.join(strong[:2])}" if strong else ""
            lines.append(f"<b>{m['name']}</b> {nat_icon(m['type'])}\n"
                         f"  <tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji>{m['power']} | <tg-emoji emoji-id='5427397421443325675'>🎯</tg-emoji>{m['acc']}% | <tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji>{m['chakra']} {hint}\n"
                         f"  <i>{m.get('desc','')}</i>")
        await _safe_edit(q,
            f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> <b>{c['char_name']} — Moveset</b>\n━━━━━━━━━━━━\n\n"+"\n\n".join(lines),
            [[Btn("Back",callback_data=f"mc:{cid}:back")]]); return

    if action=="back":
        chars=await db_chars(uid); idx=next((i for i,c in enumerate(chars) if c["id"]==cid),0)
        try: await q.message.delete()
        except: pass
        await send_char_card(q.message, ctx, uid, idx, chars, edit=False); return

    if action=="team":
        c=chars[idx]
        if c["in_team"]:
            await chars_col.update_one({"_id": c["id"]}, {"$set": {"in_team": 0, "slot": 0}})
            await q.answer("Removed from team!",show_alert=True)
        else:
            team=await db_team(uid)
            if len(team)>=6: await q.answer("Team full (6/6)!",show_alert=True); return
            await chars_col.update_one({"_id": c["id"]}, {"$set": {"in_team": 1, "slot": len(team)+1}})
            await q.answer("Added to team!",show_alert=True)
        chars=await db_chars(uid)
        try: await q.message.delete()
        except: pass
        await send_char_card(q.message, ctx, uid, idx, chars, edit=False); return

    if action=="train":
        c=chars[idx]
        prev_idx = (idx - 1) % len(chars)
        next_idx = (idx + 1) % len(chars)
        prev_id  = chars[prev_idx]["id"]
        next_id  = chars[next_idx]["id"]
        kb=[[Btn("Level Up",callback_data=f"lv:{c['id']}:{uid}")],
            [Btn("Train ATK",callback_data=f"tr:atk:{c['id']}:{uid}"),
             Btn("Train DEF",callback_data=f"tr:def:{c['id']}:{uid}")],
            [Btn("Train SPD",callback_data=f"tr:spd:{c['id']}:{uid}"),
             Btn("Train HP",callback_data=f"tr:hp:{c['id']}:{uid}")],
            [Btn("< Back",callback_data=f"mc:{prev_id}:train"),
             Btn("Next >",callback_data=f"mc:{next_id}:train")],
            [Btn("Back to Char",callback_data=f"mc:{cid}:back")]]
        await _safe_edit(q,
            f"🏋️ <b>Train {hesc(c['char_name'])}</b> (Lv.{c['level']}/100)\n\n"
            f"<tg-emoji emoji-id='5803416753031615097'>⬆️</tg-emoji> Level Up: 1lv=20NC | 5lv=90NC | 10lv=160NC\n"
            f"🏋️ Stat Train: 30 min (PP +1–3)\n"
            f"<i>({idx+1}/{len(chars)}) — use Back/Next to browse chars</i>", kb); return

    if action=="release":
        c=chars[idx]; cd=get_cdata(c["char_name"])
        ref={"Common":200,"Uncommon":500,"Rare":1500,"Epic":4000,
             "Legendary":12000,"Mythic":30000}.get(cd["rarity"] if cd else "Common",200)
        kb=[[Btn("Confirm",callback_data=f"mc:{cid}:dorelease"),
             Btn("Cancel",callback_data=f"mc:{cid}:back")]]
        await _safe_edit(q,
            f"<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji> Release <b>{c['char_name']}</b>?\nRefund: <b>{ref:,} NC</b>", kb); return

    if action=="dorelease":
        c=chars[idx]; cd=get_cdata(c["char_name"])
        ref={"Common":200,"Uncommon":500,"Rare":1500,"Epic":4000,
             "Legendary":12000,"Mythic":30000}.get(cd["rarity"] if cd else "Common",200)
        await chars_col.delete_one({"_id": c["id"]})
        user=await db_get(uid)
        await db_set(uid, coins=user["coins"]+ref)
        await _safe_edit(q, f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> Released <b>{c['char_name']}</b> — +<b>{ref:,} NC</b>")

# ─── LEVEL UP CALLBACK ──────────────────────────────────────────
async def cb_levelup(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts = q.data.split(":")
    cid = int(parts[1]); uid = parts[2]
    if str(q.from_user.id) != uid: return
    user = await db_get(uid)
    row = _cdoc(await chars_col.find_one({"_id": cid, "uid": uid}))
    if not row: return
    lv = row["level"]
    if lv >= MAX_CHAR_LEVEL:
        await q.answer("Already max level (100)!",show_alert=True); return
    remain = MAX_CHAR_LEVEL - lv
    opts = [(1,20),(5,90),(10,160)]
    kb = []
    for lvs,cost in opts:
        if lvs <= remain:
            ok = "[OK]" if user["coins"]>=cost else "[X]"
            kb.append([Btn(f"{ok} +{lvs} Levels — {cost} NC",
                           callback_data=f"lvc:{cid}:{uid}:{lvs}:{cost}")])
    kb.append([Btn("Back",callback_data=f"mc:{cid}:train")])
    await _safe_edit(q,
        f"<tg-emoji emoji-id='5803416753031615097'>⬆️</tg-emoji> <b>Level Up {row['char_name']}</b>\n"
        f"Current: Lv.{lv} | <tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> {user['coins']:,} NC\n\n"
        f"Choose level package:", kb)

async def cb_levelup_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts = q.data.split(":")
    cid = int(parts[1]); uid = parts[2]; lvs = int(parts[3]); cost = int(parts[4])
    if str(q.from_user.id) != uid: return
    user = await db_get(uid)
    if user["coins"] < cost:
        await q.answer(f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Need {cost:,} NC!",show_alert=True); return
    row = await chars_col.find_one({"_id": cid, "uid": uid}, {"level": 1})
    if not row: return
    cur_lv = row["level"]
    new_lv = min(MAX_CHAR_LEVEL, cur_lv + lvs)
    actual = new_lv - cur_lv
    await chars_col.update_one({"_id": cid}, {"$set": {"level": new_lv}})
    await db_set(uid, coins=user["coins"]-cost)
    await _safe_edit(q,
        f"<tg-emoji emoji-id='5803416753031615097'>⬆️</tg-emoji> <b>Level Up!</b>\nLv.{cur_lv} → Lv.{new_lv} (+{actual})\n<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> -{cost:,} NC")

# ─── /train CALLBACK ────────────────────────────────────────────
async def cb_train(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts   = q.data.split(":")
    ttype   = parts[1]; cid = int(parts[2]); uid = parts[3]
    if str(q.from_user.id)!=uid: return
    row = _cdoc(await chars_col.find_one({"_id": cid, "uid": uid}))
    if not row: await _safe_edit(q, "Not found!"); return
    ex = await training_col.find_one({"uid": uid, "char_id": cid})
    now = datetime.utcnow()
    if ex:
        ends = datetime.fromisoformat(ex["ends_at"])
        if ends > now:
            rem = int((ends-now).total_seconds()//60)
            await q.answer(f"Already training {ex['train_type'].upper()}! {rem}m left.",show_alert=True); return
        col_map={"atk":"pp_atk","def":"pp_def","spd":"pp_spd","hp":"pp_hp"}
        col=col_map.get(ex["train_type"],"pp_atk")
        cd_check = get_cdata(row["char_name"])
        rar_key  = cd_check["rarity"] if cd_check else "Common"
        pp_cap   = MAX_PP_BY_RARITY.get(rar_key, 22)
        cur_pp   = row[col]
        if cur_pp >= pp_cap:
            await q.answer(
                f"⛔ {row['char_name']}'s {ex['train_type'].upper()} training is MAXED out! "
                f"({cur_pp}/{pp_cap} PP — {rar_key} cap)",
                show_alert=True)
            await training_col.delete_one({"uid": uid, "char_id": cid})
            return
        gain=random.randint(1,3)
        nv=min(pp_cap, cur_pp+gain)
        await chars_col.update_one({"_id": cid}, {"$set": {col: nv}})
        await training_col.delete_one({"uid": uid, "char_id": cid})
        if nv >= pp_cap:
            await q.answer(
                f"<tg-emoji emoji-id='5426976939850080222'>🏆</tg-emoji> MAX REACHED! {row['char_name']}'s {ex['train_type'].upper()} is fully trained! ({rar_key})",
                show_alert=True)
    ends_at=(now+timedelta(minutes=30)).isoformat()
    await training_col.replace_one(
        {"uid": uid, "char_id": cid},
        {"uid": uid, "char_id": cid, "train_type": ttype, "ends_at": ends_at},
        upsert=True)
    # Block starting NEW training if this stat is already capped
    cd_check2 = get_cdata(row["char_name"])
    rar_key2  = cd_check2["rarity"] if cd_check2 else "Common"
    pp_cap2   = MAX_PP_BY_RARITY.get(rar_key2, 22)
    col_now   = {"atk":"pp_atk","def":"pp_def","spd":"pp_spd","hp":"pp_hp"}.get(ttype,"pp_atk")
    if row[col_now] >= pp_cap2:
        await q.answer(
            f"⛔ {row['char_name']}'s {ttype.upper()} training is already MAXED! "
            f"({row[col_now]}/{pp_cap2} PP)",
            show_alert=True)
        return
    await _safe_edit(q,
        f"🏋️ <b>{row['char_name']}</b> training <b>{ttype.upper()}</b> started!\n"
        f"⏱️ Ready in 30 minutes.\n"
        f"<tg-emoji emoji-id='5981204549132619885'>📊</tg-emoji> Current PP: {row[col_now]}/{pp_cap2} ({rar_key2} cap)")

TRAIN_PER_PAGE = 10

async def cmd_train(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid=str(update.effective_user.id)
    user=await db_get(uid)
    chars=await db_chars(uid)
    if not chars:
        await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> No characters! Use /summon."); return
    await send_train_list(update.message, uid, user, chars, page=0, edit=False)

async def send_train_list(target, uid, user, chars, page=0, edit=False):
    total=len(chars)
    pages=max(1,(total+TRAIN_PER_PAGE-1)//TRAIN_PER_PAGE)
    page=max(0,min(page,pages-1))
    start=page*TRAIN_PER_PAGE
    batch=chars[start:start+TRAIN_PER_PAGE]
    lines=[]
    for i,c in enumerate(batch,start+1):
        cd=get_cdata(c["char_name"])
        rr=RAR.get(cd["rarity"],"⚪") if cd else "⚪"
        lines.append(f"{i}. {rr} <b>{c['char_name']}</b> Lv.{c['level']}")
    txt=(f"🏋️ <b>Train Character</b>\n\n"
         f"<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> <b>{user['coins']:,} NC</b> | 💡 20 NC/level\n"
         f"Page {page+1}/{pages} — {total} chars total\n\n"
         +"\n".join(lines)+"\n\n<i>Tap a character to level up:</i>")
    # Char selection buttons
    kb=[[Btn(f"{c['char_name'][:20]} Lv.{c['level']}",
             callback_data=f"lv:{c['id']}:{uid}")] for c in batch]
    # Navigation
    nav=[]
    if page>0: nav.append(Btn("<",callback_data=f"tn:pg:{uid}:{page-1}"))
    nav.append(Btn(f"{page+1}/{pages}",callback_data="noop"))
    if page<pages-1: nav.append(Btn(">",callback_data=f"tn:pg:{uid}:{page+1}"))
    if nav: kb.append(nav)
    # Skip buttons
    skip=[]
    if page>=2: skip.append(Btn("-10",callback_data=f"tn:pg:{uid}:{max(0,page-10)}"))
    if page>=1: skip.append(Btn("-5",callback_data=f"tn:pg:{uid}:{max(0,page-5)}"))
    if page+1<pages: skip.append(Btn("+5",callback_data=f"tn:pg:{uid}:{min(pages-1,page+5)}"))
    if page+2<pages: skip.append(Btn("+10",callback_data=f"tn:pg:{uid}:{min(pages-1,page+10)}"))
    if skip: kb.append(skip)
    if edit:
        is_photo = bool(getattr(target, 'message', None) and target.message.photo)
        try:
            if is_photo:
                await target.edit_message_caption(caption=txt[:1020], parse_mode="HTML", reply_markup=Kbd(kb))
            else:
                await target.edit_message_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))
        except: pass
    else:
        await target.reply_text(txt,parse_mode="HTML",reply_markup=Kbd(kb))

async def cb_train_page(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    parts=q.data.split(":"); uid=parts[2]; page=int(parts[3])
    if str(q.from_user.id)!=uid: await q.answer("Not yours!",show_alert=True); return
    user=await db_get(uid); chars=await db_chars(uid)
    await send_train_list(q,uid,user,chars,page=page,edit=True)

# ─── /explore ───────────────────────────────────────────────────
async def cmd_explore(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid  = str(update.effective_user.id)
    team = await db_team(uid)
    if not team:
        await update.message.reply_text("❌ No team! Use /team to set one.",
            parse_mode="HTML",
            reply_markup=Kbd([[Btn("My Chars",callback_data="menu:chars")]])); return
    user   = await db_get(uid)
    # Use slot-1 char as the first fighter; sort team by slot
    team_sorted = sorted(team, key=lambda c: c.get("slot",99))
    p_row  = team_sorted[0]
    cd     = get_cdata(p_row["char_name"])
    if not cd: return
    pkg    = CLAN_KG.get(cd["clan"],"None")
    vi_i   = VILLAGES.get(user["village"],{})
    hp_b   = vi_i.get("hp",0)
    plv    = p_row["level"]
    php    = int(calc_stat(cd["base"]["hp"],p_row["pp_hp"],plv)*(1+hp_b))
    p_atk  = calc_stat(cd["base"]["atk"],p_row["pp_atk"],plv)
    p_def  = calc_stat(cd["base"]["def"],p_row["pp_def"],plv)
    p_spd  = int(calc_stat(cd["base"]["speed"],p_row["pp_spd"],plv)*(1+vi_i.get("spd",0)))
    # Tailed beast host bonus: beast power boosts HP and ATK
    tb_name = cd.get("tailed_beast")
    if tb_name and tb_name in BEASTS:
        beast_power = BEASTS[tb_name].get("power",0)
        php   = int(php   * (1 + beast_power/100000))
        p_atk = int(p_atk * (1 + beast_power/200000))

    # Pick enemy:
    # 8%  → Village tailed beast encounter (if not already caught)
    # 47% → Named CHARACTER from user's village
    # 45% → Wild creature
    enemy_photo = None
    user_village = user.get("village","Konoha")
    caught_beasts = list(user.get("caught_beasts") or [])
    is_beast_encounter = False
    beast_encounter_name = None
    village_chars = [c for c in CHARACTERS if c["village"]==user_village]
    if not village_chars:
        village_chars = CHARACTERS

    village_beast_name = VILLAGE_BEAST.get(user_village)
    beast_not_caught = village_beast_name and village_beast_name not in caught_beasts

    roll = random.random()
    if roll < 0.08 and beast_not_caught:
        # ── Tailed Beast Encounter ───────────────────────────────
        bi = BEASTS[village_beast_name]
        beast_enc_lvl = max(plv + 10, 30)
        wild = {
            "name":  village_beast_name,
            "nat":   bi["nat"],
            "hp":    bi["battle_hp"] + beast_enc_lvl * 20,
            "atk":   bi["battle_atk"] + beast_enc_lvl * 3,
            "def":   int(bi["battle_atk"] * 0.6),
            "spd":   180 + beast_enc_lvl * 2,
            "photo": bi.get("photo"),
            "nc":    (max(800, plv*80), max(2000, plv*180)),
            "chakra":(max(100, plv*15), max(300, plv*40)),
            "exp":   (max(200, plv*50), max(600, plv*120)),
            "moves": [M["tbb"], M["rasengan"], M["almighty_push"], M["rasenshuriken"]],
            "is_beast": True,
            "beast_name": village_beast_name,
            "is_char": False,
        }
        elv_s = beast_enc_lvl
        enemy_photo = bi.get("photo")
        is_beast_encounter = True
        beast_encounter_name = village_beast_name
    elif roll < 0.55:
        # ── Character enemy ──────────────────────────────────────
        ecd = random.choice(village_chars)
        elv = max(1, plv + random.randint(-8, 12))
        ehp = int(calc_stat(ecd["base"]["hp"], 15, elv) * 0.7)
        wild = {
            "name": ecd["name"],
            "nat":  ecd["nature"],
            "hp":   ehp,
            "atk":  int(calc_stat(ecd["base"]["atk"], 15, elv) * 0.7),
            "def":  int(calc_stat(ecd["base"]["def"], 15, elv) * 0.7),
            "spd":  int(calc_stat(ecd["base"]["speed"], 15, elv) * 0.7),
            "photo": PHOTO_CACHE.get(ecd["name"]),
            "nc":   (max(200, elv*30), max(500, elv*80)),
            "chakra":(max(20, elv*3), max(80, elv*10)),
            "exp":  (max(30, elv*8), max(100, elv*20)),
            "moves": ecd["moves"],
            "is_char": True,
        }
        elv_s = elv
        enemy_photo = PHOTO_CACHE.get(ecd["name"])
    else:
        # ── Wild creature ────────────────────────────────────────
        wild = dict(random.choice(WILDS))
        elv_s = max(1, plv + random.randint(-5, 8))
        wild["hp"] = wild.get("hp",150) + random.randint(-20,60)
        enemy_photo = wild.get("photo") or PHOTO_CACHE.get(wild.get("name",""))

    ehp = wild["hp"]

    # Speed determines who goes first
    e_spd = wild.get("spd", 150)
    p_goes_first = p_spd >= e_spd

    form = cd.get("form")
    req_chakra = form["req_chakra"] if form else 999999

    equipped_wid = user.get("equipped_weapon")
    equipped_weapon = get_weapon_by_id(equipped_wid) if equipped_wid else None
    tb_name_e = cd.get("tailed_beast")
    # Bijuu available only if user already caught that beast, or char is a special always-host
    ALWAYS_BIJUU_CHARS = {"Naruto (Baryon Mode)", "Naruto Uzumaki", "Minato Namikaze",
                          "Killer Bee", "Gaara", "Gaara (Fifth Kazekage)"}
    bijuu_av_e = (bool(tb_name_e and tb_name_e in BEASTS)
                  and (p_row["char_name"] in ALWAYS_BIJUU_CHARS
                       or tb_name_e in caught_beasts))
    session = {
        "p_char":p_row["char_name"],"p_char_id":p_row["id"],"p_level":plv,
        "p_hp":php,"p_max_hp":php,"p_atk":p_atk,"p_def":p_def,
        "p_spd":p_spd,"p_nat":cd["nature"],"p_kg":pkg,
        "p_status":"","p_dot":None,"p_def_broken":False,"p_revived":False,
        "p_battle_chakra":0,"p_transformed":False,"transform_available":False,
        "req_chakra":req_chakra,
        "enemy":wild,"e_hp":ehp,"e_max_hp":ehp,"e_level":elv_s,
        "e_status":"","e_dot":None,"e_def_broken":False,
        "is_photo":False,"turn":0,"uid":uid,
        "p_goes_first":p_goes_first,
        # Team battle data
        "team_order":[c["id"] for c in team_sorted],
        "team_idx":0,
        "team_map":{c["id"]:c for c in team_sorted},
        # Weapon data
        "equipped_weapon": equipped_weapon,
        "weapon_used": False,
        # Bijuu / tailed beast data
        "bijuu_avail": bijuu_av_e,
        "bijuu_active": False,
        "bijuu_turns_left": 0,
        "bijuu_beast_name": tb_name_e or "",
        "started_at": time.time(),
    }
    EX[uid] = session
    transform_avail = (session["p_battle_chakra"] >= req_chakra and
                       user.get("stones",0) >= 1 and form and not session["p_transformed"])
    session["transform_available"] = transform_avail

    # Show encounter screen first — photo with just Fight and Run
    encounter_txt = (
        f"<b>Wild Encounter!</b>\n\n"
        f"A wild <b>{hesc(wild['name'])}</b> appeared!\n"
        f"Lv.{elv_s}  {hesc(wild.get('nat','neutral'))} {nat_pe(wild.get('nat','neutral'))}\n\n"
        f"<i>What will you do?</i>"
    )
    if is_beast_encounter and beast_encounter_name:
        bi_enc = BEASTS[beast_encounter_name]
        encounter_txt = (
            f"<tg-emoji emoji-id='6003600664687546316'>🦊</tg-emoji> <b>TAILED BEAST ENCOUNTER!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{bi_enc.get('emoji','🦊')} <b>{hesc(beast_encounter_name)}</b> has emerged in {hesc(user_village)}!\n"
            f"<i>{hesc(bi_enc.get('desc',''))}</i>\n\n"
            f"Tails: {bi_enc['tails']} | Nature: {bi_enc['nat']} | Power: {bi_enc['power']:,}\n"
            f"<b>Lv.{elv_s}</b>\n\n"
            f"<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji> <i>Defeat it to seal it in your data!\n"
            f"Then use it in battle with compatible hosts!</i>\n\n"
            f"<i>What will you do?</i>"
        )
    kb = [[Btn("Fight", callback_data=f"ex:fight:{uid}"),
           Btn("Run", callback_data=f"ex:run:{uid}")]]
    battle_photo = enemy_photo
    if battle_photo:
        try:
            await update.message.reply_photo(
                photo=battle_photo, caption=encounter_txt[:1020],
                parse_mode="HTML", reply_markup=Kbd(kb))
            session["is_photo"] = True
            return
        except: pass
    await update.message.reply_text(encounter_txt, parse_mode="HTML", reply_markup=Kbd(kb))

async def cb_explore(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts  = q.data.split(":")
    action = parts[1]; uid = parts[2]
    if str(q.from_user.id)!=uid:
        await q.answer("Not your battle!",show_alert=True); return
    session = EX.get(uid)
    if session and time.time() - session.get("started_at", 0) > 600:
        del EX[uid]
        session = None
    if not session:
        try: await q.edit_message_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> No active battle! Use /explore")
        except: pass
        return
    # Refresh enemy photo from cache if it wasn't loaded when explore started
    if not session["enemy"].get("photo"):
        ep = PHOTO_CACHE.get(session["enemy"].get("name", ""))
        if ep:
            session["enemy"]["photo"] = ep
    cd = get_cdata(session["p_char"])
    if not cd: return
    is_photo = session.get("is_photo",False)
    user = await db_get(uid)

    if action=="fight":
        # User chose to fight — show full battle screen with move buttons
        # Compute bijuu availability on fight start (require caught or always-host char)
        cd_f = get_cdata(session["p_char"])
        tb_f = cd_f.get("tailed_beast") if cd_f else None
        ALWAYS_BIJUU_CHARS = {"Naruto (Baryon Mode)", "Naruto Uzumaki", "Minato Namikaze",
                              "Killer Bee", "Gaara", "Gaara (Fifth Kazekage)"}
        _caught_f = list(user.get("caught_beasts") or [])
        bijuu_av_f = (bool(tb_f and tb_f in BEASTS)
                      and session["p_battle_chakra"] >= 150
                      and not session.get("bijuu_active")
                      and (session["p_char"] in ALWAYS_BIJUU_CHARS or tb_f in _caught_f))
        session["bijuu_avail"] = bijuu_av_f
        txt = fmt_battle_text(session)
        transform_avail = session.get("transform_available", False)
        kb = move_btns_explore(
            get_char_moves(session["p_char"], session["p_level"]), uid,
            transform_avail, weapon=session.get("equipped_weapon"),
            weapon_used=session.get("weapon_used", False),
            bijuu_avail=bijuu_av_f)
        enemy_photo = session["enemy"].get("photo") or PHOTO_CACHE.get(session["enemy"].get("name",""))
        safe_txt = _safe_trunc_battle(txt)
        vs_photo = await make_vs_photo(session["p_char"], session["enemy"]["name"], enemy_photo)
        if vs_photo:
            try:
                if q.message.photo:
                    await q.message.edit_media(
                        media=InputMediaPhoto(media=vs_photo, caption=safe_txt, parse_mode="HTML"),
                        reply_markup=Kbd(kb))
                else:
                    sent = await q.message.reply_photo(photo=vs_photo, caption=safe_txt,
                                                       parse_mode="HTML", reply_markup=Kbd(kb))
                    try: await q.message.delete()
                    except: pass
                return
            except Exception:
                pass
        await safe_edit(q, safe_txt, kb, enemy_photo)
        return

    if action=="run":
        del EX[uid]
        kb = [[Btn("Explore Again",callback_data="menu:explore")]]
        await safe_edit(q,"<b>You fled safely.</b>\nNo rewards.",kb,is_photo); return

    # ── WEAPON USE ───────────────────────────────────────────────
    if action=="wpn":
        weapon = session.get("equipped_weapon")
        if not weapon:
            await q.answer("No weapon equipped!", show_alert=True); return
        if session.get("weapon_used"):
            await q.answer("Weapon already used this battle!", show_alert=True); return
        p_atk = session["p_atk"]
        raw_dmg = int(weapon["atk"] * p_atk / 100 * random.uniform(0.85, 1.15)) + weapon["atk"]
        raw_dmg = max(5, raw_dmg)
        session["e_hp"] = max(0, session["e_hp"] - raw_dmg)
        session["weapon_used"] = True
        buff = weapon.get("buff", {})
        buff_txt = ""
        if buff.get("type") and buff["type"] not in ("def_up","dodge_next"):
            buff_txt = f"\n{fmt_effect(buff['type'] + ':' + str(buff.get('val',0)))} applied!"
        log_txt = (f"<b>{session['p_char']}</b> uses weapon <b>{weapon['name']}</b>!\n"
                   f"<b>{weapon['ability']}</b> — -{raw_dmg} HP!{buff_txt}")
        # Enemy turn if not dead
        if session["e_hp"] > 0:
            e_move = random.choice(session["enemy"].get("moves", [{"name":"Strike","power":40,"acc":90,"type":"normal","effect":""}]))
            e_res = resolve_attack(e_move, session["enemy"].get("atk",100),
                                   session["p_def"], session["enemy"].get("nat","neutral"),
                                   session["p_nat"], "None", session["p_kg"],
                                   session["e_level"], session["p_level"])
            if e_res["hit"]:
                session["p_hp"] = max(0, session["p_hp"] - e_res["dmg"])
                log_txt += f"\n<b>{session['enemy']['name']}</b> counters: -{e_res['dmg']} HP!"
            else:
                log_txt += f"\n<b>{session['enemy']['name']}</b>'s attack missed!"
        wep_data = session.get("equipped_weapon")
        wep_used = session.get("weapon_used", False)
        txt = fmt_battle_text(session, log_txt)
        kb = move_btns_explore(get_char_moves(session["p_char"], session["p_level"]), uid,
                               session.get("transform_available", False),
                               weapon=wep_data, weapon_used=wep_used)
        if session["e_hp"] <= 0 or session["p_hp"] <= 0:
            kb = move_btns_explore(get_char_moves(session["p_char"], session["p_level"]), uid, False)
        await safe_edit(q, txt, kb, is_photo)
        return

    # TEAM SWITCH (called when current char is defeated)
    if action=="sw":
        new_char_id = int(parts[3])
        team_map = session.get("team_map",{})
        team_order = session.get("team_order",[])
        cr = team_map.get(new_char_id)
        if not cr:
            await q.answer("Character not found!",show_alert=True); return
        new_cd = get_cdata(cr["char_name"])
        if not new_cd:
            await q.answer("Character data missing!",show_alert=True); return
        # Find the new char's index in team_order
        try: new_idx = team_order.index(new_char_id)
        except ValueError: new_idx = session.get("team_idx",0)+1
        vi_i = VILLAGES.get(user["village"],{})
        new_plv = cr["level"]
        new_pkg = CLAN_KG.get(new_cd["clan"],"None")
        new_php = int(calc_stat(new_cd["base"]["hp"],cr["pp_hp"],new_plv)*(1+vi_i.get("hp",0)))
        new_form = new_cd.get("form")
        session["p_char"]     = cr["char_name"]
        session["p_char_id"]  = new_char_id
        session["p_level"]    = new_plv
        session["p_hp"]       = new_php
        session["p_max_hp"]   = new_php
        session["p_atk"]      = calc_stat(new_cd["base"]["atk"],cr["pp_atk"],new_plv)
        session["p_def"]      = calc_stat(new_cd["base"]["def"],cr["pp_def"],new_plv)
        session["p_spd"]      = int(calc_stat(new_cd["base"]["speed"],cr["pp_spd"],new_plv)*(1+vi_i.get("spd",0)))
        session["p_nat"]      = new_cd["nature"]
        session["p_kg"]       = new_pkg
        session["p_status"]   = ""
        session["p_dot"]      = None
        session["p_def_broken"]= False
        session["p_revived"]  = False
        session["p_battle_chakra"] = 0
        session["p_transformed"]   = False
        session["req_chakra"] = new_form["req_chakra"] if new_form else 999999
        session["transform_available"] = False
        session["team_idx"]   = new_idx
        session["awaiting_switch"] = False
        log_sw = f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>{cr['char_name']}</b> enters the battle! (Lv.{new_plv})"
        txt = fmt_battle_text(session, log_sw)
        kb  = move_btns_explore(get_char_moves(cr["char_name"], new_plv), uid, False)
        # Try to show new char photo
        sw_photo = PHOTO_CACHE.get(cr["char_name"])
        if sw_photo:
            try:
                await q.message.reply_photo(photo=sw_photo, caption=txt[:1020],
                    parse_mode="HTML", reply_markup=Kbd(kb))
                session["is_photo"] = True
                return
            except: pass
        await safe_edit(q, txt, kb, is_photo); return

    # TRANSFORM
    if action=="tf":
        form = cd.get("form")
        if not form or session.get("p_transformed"):
            await q.answer("Cannot transform!",show_alert=True); return
        if user.get("stones",0) < 1:
            await q.answer("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Need a Transform Stone!",show_alert=True); return
        await db_set(uid, stones=user.get("stones",0)-1)
        buff = form["buff"]
        session["p_hp"] = min(session["p_max_hp"] + buff.get("hp",0),
                              session["p_hp"] + buff.get("hp",0))
        session["p_max_hp"] += buff.get("hp",0)
        session["p_atk"] += buff.get("atk",0)
        session["p_def"] += buff.get("def",0)
        session["p_spd"] += buff.get("speed",0)
        session["p_transformed"] = True
        session["transform_available"] = False
        log = f"<tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji> <b>{session['p_char']}</b> → <b>{form['name']}</b>! <tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji> Stone consumed!\nAll stats buffed!"
        # Show the form-specific photo (e.g. Baryon Mode image for Naruto)
        _tf_photo = get_form_photo(cd["name"], form["name"])
        if _tf_photo:
            try:
                await q.message.reply_photo(
                    photo=_tf_photo,
                    caption=f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>TRANSFORMATION!</b>\n<b>{session['p_char']}</b> → <b>{form['name']}</b>!\n<tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji> Transform Stone consumed!",
                    parse_mode="HTML")
            except: pass
        txt = fmt_battle_text(session, log)
        kb  = move_btns_explore(get_char_moves(session["p_char"], session["p_level"]), uid, False,
                                weapon=session.get("equipped_weapon"), weapon_used=session.get("weapon_used",False))
        await safe_edit(q, txt, kb, is_photo); return

    # MANUAL SWITCH: show team roster to pick a different fighter mid-battle
    if action=="swlist":
        team_map   = session.get("team_map", {})
        team_order = session.get("team_order", [])
        cur_id     = session.get("p_char_id")
        others     = [team_map[cid] for cid in team_order
                      if cid != cur_id and team_map.get(cid) and team_map[cid].get("hp", 1) > 0]
        if not others:
            await q.answer("No other chars available!", show_alert=True)
            return
        sw_kb = [[Btn(f"{cr['char_name']} Lv.{cr['level']}{'  [Active]' if cr['char_name']==session['p_char'] else ''}",
                      callback_data=f"ex:sw:{uid}:{cr['id']}")]
                 for cr in others]
        sw_kb.append([Btn("Back", callback_data=f"ex:swback:{uid}")])
        await safe_edit(q,
            f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>Switch Fighter</b>\nChoose who replaces <b>{session['p_char']}</b>:",
            sw_kb, is_photo)
        return

    # BACK FROM SWITCH MENU
    if action=="swback":
        txt = fmt_battle_text(session)
        kb  = move_btns_explore(get_char_moves(session["p_char"], session["p_level"]), uid,
                                session.get("transform_available", False),
                                weapon=session.get("equipped_weapon"), weapon_used=session.get("weapon_used",False))
        await safe_edit(q, txt, kb, is_photo)
        return

    # ── WEAPONS PANEL ────────────────────────────────────────────
    if action == "weap":
        owned_wids   = list(user.get("weapons") or [])
        equipped_wid = user.get("equipped_weapon")
        if not owned_wids:
            await q.answer("No weapons yet! Explore to find them.", show_alert=True); return
        lines = []
        for wid in owned_wids[:6]:
            w = get_weapon_by_id(wid)
            if w:
                eq_tag = " [EQUIPPED]" if wid == equipped_wid else ""
                rar    = w.get("rarity","Common")
                lines.append(
                    f"  [{rar[:2]}]{eq_tag} <b>{hesc(w['name'])}</b>\n"
                    f"    ATK +{w['atk']} | {hesc(w['ability'][:40])}"
                )
        weap_txt = (
            f"{pe('sword')} <b>Your Weapons</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(lines) +
            f"\n━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Use /equip to change weapon.</i>"
        )
        back_kb = move_btns_explore(
            get_char_moves(session["p_char"], session["p_level"]), uid,
            session.get("transform_available", False),
            weapon=session.get("equipped_weapon"), weapon_used=session.get("weapon_used", False),
            bijuu_avail=session.get("bijuu_avail", False))
        await safe_edit(q, weap_txt, back_kb, is_photo); return

    # ── BIJUU MODE ───────────────────────────────────────────────
    if action == "bijuu":
        if session.get("bijuu_active"):
            await q.answer("Bijuu Mode already active!", show_alert=True); return
        cd_b = get_cdata(session["p_char"])
        tb_name = cd_b.get("tailed_beast") if cd_b else None
        if not tb_name or tb_name not in BEASTS:
            await q.answer("No Tailed Beast available!", show_alert=True); return
        bi = BEASTS[tb_name]
        if session["p_battle_chakra"] < 150:
            await q.answer(f"Need 150 battle chakra! (You have {session['p_battle_chakra']})", show_alert=True); return
        # Gate: must have caught this beast (except always-host chars)
        _ALWAYS_BIJUU_B = {"Naruto (Baryon Mode)", "Naruto Uzumaki", "Minato Namikaze",
                           "Killer Bee", "Gaara", "Gaara (Fifth Kazekage)"}
        _caught_b = list(user.get("caught_beasts") or [])
        if session["p_char"] not in _ALWAYS_BIJUU_B and tb_name not in _caught_b:
            await q.answer(
                f"❌ You haven't caught {tb_name} yet!\n"
                f"Explore {bi.get('village','your village')} and defeat it first!",
                show_alert=True); return
        # Apply Bijuu stat boosts
        atk_bonus = bi["power"] // 50
        hp_bonus  = bi["power"] // 10
        session["p_hp"]       = min(session["p_max_hp"] + hp_bonus, session["p_hp"] + hp_bonus)
        session["p_max_hp"]  += hp_bonus
        session["p_atk"]     += atk_bonus
        session["bijuu_active"]     = True
        session["bijuu_turns_left"] = 4
        session["bijuu_beast_name"] = tb_name
        session["bijuu_avail"]      = False
        # Bijuu initial blast
        beast_dmg = int(bi["power"] / 20 * random.uniform(0.9, 1.15))
        session["e_hp"] = max(0, session["e_hp"] - beast_dmg)
        bijuu_log = (
            f"<tg-emoji emoji-id='6003600664687546316'>🦊</tg-emoji> <b>BIJUU MODE ACTIVATED!</b>\n"
            f"{bi.get('emoji','🦊')} <b>{hesc(tb_name)}</b> ({bi['tails']} tails) takes over!\n"
            f"<b>{hesc(bi['ability'])}</b>\n"
            f"  HP +{hp_bonus} | ATK +{atk_bonus}\n"
            f"  Initial beast blast: <b>-{beast_dmg} HP</b> to {hesc(session['enemy']['name'])}!"
        )
        txt = fmt_battle_text(session, bijuu_log)
        kb  = move_btns_explore(get_char_moves(session["p_char"], session["p_level"]), uid,
                                session.get("transform_available", False),
                                weapon=session.get("equipped_weapon"), weapon_used=session.get("weapon_used", False),
                                bijuu_avail=False)
        # Show beast photo if available
        beast_photo = bi.get("photo") or PHOTO_CACHE.get(bi.get("host",""))
        if beast_photo:
            try:
                await q.message.reply_photo(photo=beast_photo,
                    caption=f"🦊 <b>{hesc(tb_name)} AWAKENS!</b>\n<i>{hesc(bi['ability'])}</i>",
                    parse_mode="HTML")
            except Exception:
                pass
        await safe_edit(q, txt, kb, is_photo); return

    if not action.startswith("m"): return
    mi = int(action[1:])
    p_moves = get_char_moves(session["p_char"], session["p_level"])
    if mi >= len(p_moves): return
    move = p_moves[mi]
    log  = ""

    # Gain battle chakra from move use
    session["p_battle_chakra"] += move.get("chakra",20)

    # ── PLAYER TURN ───────────────────────────────────────────
    if session.get("p_status")=="stun":
        session["p_status"]=""; log += "😵 You were stunned — turn skipped!\n"
    else:
        e_def = session["enemy"]["def"] * (0.7 if session.get("e_def_broken") else 1.0)
        res = resolve_attack(move,session["p_atk"],e_def,
                             session["p_nat"],session["enemy"]["nat"],
                             session["p_kg"],"None",
                             atk_lv=session["p_level"],def_lv=session["e_level"])
        if res["hit"]:
            session["e_hp"]=max(0,session["e_hp"]-res["dmg"])
            crit_pfx = "💥 <b>CRITICAL!</b> " if res.get("crit") else ""
            log += f"⚔️ <b>{hesc(session['p_char'])}</b> → <b>{hesc(move['name'])}</b>\n"
            log += f"  {crit_pfx}{res['eff_txt']} <b>-{res['dmg']} HP</b>\n"
            if res.get("kg_def"): log+=f"  {hesc(res['kg_def'])}\n"
            n=apply_effects_to_state(res["effects"],session,"e")
            if n: log+="  "+" ".join(n)+"\n"
            if res.get("reflect",0):
                session["p_hp"]=max(0,session["p_hp"]-res["reflect"])
                log+=f"  🔄 Reflect <b>-{res['reflect']} HP</b>!\n"
        else:
            log+=f"⚔️ <b>{hesc(move['name'])}</b> — <b>MISSED!</b>\n"

        # Attack photos are NOT sent as separate messages — doing so scrolls the
        # chat away from the battle message, making the HP bar invisible to the
        # user. Damage and crit info appear in the log text inside the battle card.

    # ── ENEMY DEFEATED? ──────────────────────────────────────
    if session["e_hp"]<=0:
        wild=session["enemy"]
        # NC coins: 10-20 per battle, daily cap of 100 NC from explore
        _today = datetime.utcnow().strftime("%Y-%m-%d")
        _daily_nc_key = user.get("daily_explore_date","")
        _daily_nc_earned = user.get("daily_explore_nc", 0) if _daily_nc_key == _today else 0
        _daily_nc_left = max(0, 100 - _daily_nc_earned)
        nc_r    = min(random.randint(10, 20), _daily_nc_left)
        chakra_r= random.randint(4, 5)
        exp_g   = random.randint(*wild.get("exp",(30,120)))*(2 if user.get("exp_boost") else 1)
        # Stone drop: 4% chance. Weapon drop: 5% chance (mutually exclusive with stone in same slot)
        stone_drop = random.random() < 0.04
        weapon_drop = None
        if not stone_drop and random.random() < 0.05:
            # Pick a weighted-random weapon (common most likely)
            rar_weights = {"Common":50,"Uncommon":25,"Rare":14,"Epic":8,"Legendary":2,"Mythic":1}
            roll = random.random() * 100
            cumulative = 0
            chosen_rar = "Common"
            for rar, w in rar_weights.items():
                cumulative += w
                if roll <= cumulative:
                    chosen_rar = rar
                    break
            pool = [w for w in WEAPONS if w["rarity"] == chosen_rar]
            if pool:
                weapon_drop = random.choice(pool)
        nc_n=user["coins"]+nc_r; nch=user["chakra"]+chakra_r
        ne=user["exp"]+exp_g; nl=user["level"]; lm=""
        while ne>=exp_for_lv(nl+1) and nl<100:
            ne-=exp_for_lv(nl+1); nl+=1
            lm+=f"\n<tg-emoji emoji-id='5426976939850080222'>🎉</tg-emoji> <b>Level Up!</b> Lv.{nl} — {rank_for_lv(nl)}"
        st=user.get("stones",0)+(1 if stone_drop else 0)
        _new_daily_nc = _daily_nc_earned + nc_r
        update_kw = dict(coins=nc_n,chakra=nch,exp=ne,level=nl,rank=rank_for_lv(nl),
                         wins=user["wins"]+1,stones=st,
                         daily_explore_nc=_new_daily_nc,
                         daily_explore_date=_today)
        if weapon_drop:
            cur_weapons = user.get("weapons") or []
            cur_weapons = list(cur_weapons)
            cur_weapons.append(weapon_drop["id"])
            update_kw["weapons"] = cur_weapons
        # Beast catch: if this was a beast encounter, add to caught_beasts
        caught_name = session["enemy"].get("beast_name") if session["enemy"].get("is_beast") else None
        beast_catch_txt = ""
        if caught_name and caught_name in BEASTS:
            cur_caught = list(user.get("caught_beasts") or [])
            if caught_name not in cur_caught:
                cur_caught.append(caught_name)
                update_kw["caught_beasts"] = cur_caught
                bi_c = BEASTS[caught_name]
                beast_catch_txt = (
                    f"\n\n{bi_c.get('emoji','🦊')} <b>TAILED BEAST CAUGHT!</b>\n"
                    f"  <b>{hesc(caught_name)}</b> has been sealed!\n"
                    f"  HP +{bi_c['catch_hp_boost']} | ATK +{bi_c['catch_atk_boost']}\n"
                    f"  <i>Now available for Bijuu Mode with compatible hosts!</i>"
                )
        await db_set(uid, **update_kw)
        # ── Give EXP to the active character + auto-level ──
        char_exp_gain = exp_g
        crow = _cdoc(await chars_col.find_one({"_id": session["p_char_id"]}, {"level": 1, "exp": 1}))
        if crow:
            clv=crow["level"]; cexp=crow["exp"]+char_exp_gain; clm=""
            char_lv_needed = int(80*(clv**1.4))
            new_move_pending = None
            while cexp >= char_lv_needed and clv < MAX_CHAR_LEVEL:
                cexp -= char_lv_needed; clv += 1
                char_lv_needed = int(80*(clv**1.4))
                clm += f"\n<tg-emoji emoji-id='5803416753031615097'>⬆️</tg-emoji> <b>{session['p_char']}</b> leveled up to Lv.{clv}!"
                # ── Check for a level-up move unlock ─────────────────
                unlocks = LEVEL_MOVE_UNLOCKS.get(session["p_char"], {})
                if clv in unlocks and new_move_pending is None:
                    mk = unlocks[clv]
                    if mk in M:
                        new_move_pending = {"move_key": mk, "move": dict(M[mk]), "at_level": clv}
            await chars_col.update_one({"_id": session["p_char_id"]}, {"$set": {"exp": cexp, "level": clv}})
            if clm: lm += clm
            # ── Store pending move swap so player can pick a slot ────
            if new_move_pending:
                PENDING_MOVE_SWAP[uid] = {
                    "char_id":   session["p_char_id"],
                    "char_name": session["p_char"],
                    "new_move_key": new_move_pending["move_key"],
                    "new_move":     new_move_pending["move"],
                }
                lm += (f"\n\n<tg-emoji emoji-id='5427397421443325675'>🆕</tg-emoji> <b>NEW MOVE UNLOCKED!</b>\n"
                       f"<b>{hesc(session['p_char'])}</b> learned "
                       f"<b>{hesc(new_move_pending['move']['name'])}</b> at Lv.{new_move_pending['at_level']}!\n"
                       f"<i>Use /newmove to choose which move to replace!</i>")
        del EX[uid]
        kb=[[Btn("Explore Again",callback_data="menu:explore"),
             Btn("Summon",callback_data=f"sm:s:{uid}")]]
        if uid in PENDING_MOVE_SWAP:
            kb.insert(0,[Btn("Pick Move to Replace",callback_data=f"mvswap:menu:{uid}")])
        stone_txt = f"\n{pe('stone')} <b>RARE DROP!</b> Transform Stone!" if stone_drop else ""
        weapon_txt = ""
        if weapon_drop:
            rar = weapon_drop['rarity']
            weapon_txt = (
                f"\n{pe('sword')} <b>WEAPON DROP!</b> [{hesc(rar)}] <b>{hesc(weapon_drop['name'])}</b>"
                f"\n  ATK +{weapon_drop['atk']} | {hesc(weapon_drop['ability'])}"
                f"\n  Added to your inventory. Use /equip {hesc(weapon_drop['id'])} to equip!"
            )
        # ── Calculate battle narrative stats ──────────────────────────
        turns = session.get("turn", 1)
        hp_pct = int((session["p_hp"] / session["p_max_hp"]) * 100) if session["p_max_hp"] else 100
        if turns <= 1:
            pace_txt = "One-shot! Absolute dominance."
        elif turns <= 3:
            pace_txt = "Lightning-fast takedown!"
        elif turns <= 5:
            pace_txt = "Swift and decisive!"
        elif turns <= 8:
            pace_txt = "A hard-fought victory!"
        else:
            pace_txt = "A grueling, legendary clash!"
        if hp_pct >= 85:
            hp_txt = "Not even scratched."
        elif hp_pct >= 60:
            hp_txt = "Took some hits but held strong."
        elif hp_pct >= 35:
            hp_txt = "A rough battle — HP running low."
        else:
            hp_txt = "Survived by sheer willpower!"
        txt = (
            f"{pe('trophy')} <b>VICTORY!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{pe('sword')} <b>{hesc(session['p_char'])}</b> defeated <b>{hesc(wild['name'])}</b>!\n"
            f"{pe('exp')} {pace_txt} Battle lasted <b>{turns}</b> turn{'s' if turns != 1 else ''}.\n"
            f"{pe('hp')} HP remaining: <b>{session['p_hp']}/{session['p_max_hp']}</b> — {hp_txt}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Battle Rewards:</b>\n"
            + (f"  {pe('coin')} +<b>{nc_r:,} NC</b>\n" if nc_r > 0 else f"  {pe('coin')} NC: <b>Daily cap reached (100/100)</b> — resets tomorrow!\n")
            + f"  {pe('chakra')} +<b>{chakra_r} Chakra</b>\n"
            f"  {pe('exp')} +<b>{exp_g} EXP</b> (player)\n"
            f"  {pe('star')} <b>{hesc(session['p_char'])}</b> gained +<b>{char_exp_gain}</b> char EXP"
            f"{stone_txt}{weapon_txt}{beast_catch_txt}{lm}"
        )
        try:
            await q.message.reply_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))
        except Exception:
            await safe_edit(q, txt[:4000], kb, is_photo, parse_mode="HTML")
        return

    # ── ENEMY TURN ───────────────────────────────────────────
    log+="\n"
    if session["e_dot"]:
        session["e_hp"],dn=apply_dot(session["e_dot"],session["e_hp"])
        session["e_dot"]=tick_dot(session["e_dot"]); log+=f"  {dn} (enemy)\n"
    if session["p_dot"]:
        session["p_hp"],dn=apply_dot(session["p_dot"],session["p_hp"])
        session["p_dot"]=tick_dot(session["p_dot"]); log+=f"  {dn} (you)\n"
    regen,rn=kg_turn_regen(session["p_kg"],session["p_hp"],session["p_max_hp"])
    if regen: session["p_hp"]=min(session["p_max_hp"],session["p_hp"]+regen); log+=f"  {rn}\n"

    if session.get("e_status")=="stun":
        session["e_status"]=""
        log+=f"  😵 <b>{session['enemy']['name']}</b> stunned — skips!\n"
    else:
        em=random.choice(session["enemy"]["moves"])
        p_def_v=session["p_def"]*(0.7 if session.get("p_def_broken") else 1.0)
        dodge=KG.get(session["p_kg"],{}).get("dodge_chance",0)
        if dodge and random.randint(1,100)<=dodge:
            log+=f"  <tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> You dodged <b>{em['name']}</b>!\n"
        else:
            res2=resolve_attack(em,session["enemy"]["atk"],p_def_v,
                                session["enemy"]["nat"],session["p_nat"],
                                "None",session["p_kg"],
                                atk_lv=session["e_level"],def_lv=session["p_level"])
            if res2["hit"]:
                session["p_hp"]=max(0,session["p_hp"]-res2["dmg"])
                log+=f"  <tg-emoji emoji-id='5798530836890390483'>🔴</tg-emoji> <b>{em['name']}</b> {res2['eff_txt']} <b>-{res2['dmg']} HP</b>\n"
                if res2.get("kg_def"): log+=f"  {res2['kg_def']}\n"
                n2=apply_effects_to_state(res2["effects"],session,"p")
                if n2: log+="  "+" ".join(n2)+"\n"
            else:
                log+=f"  <tg-emoji emoji-id='5798530836890390483'>🔴</tg-emoji> <b>{em['name']}</b> — missed!\n"

    # ── PLAYER DEFEATED? ────────────────────────────────────
    if session["p_hp"]<=0:
        if not session.get("p_revived") and KG.get(session["p_kg"],{}).get("revive"):
            session["p_hp"]=int(session["p_max_hp"]*0.25)
            session["p_revived"]=True
            log+=f"  💚 Medical NJ revived!\n"
        else:
            # Check if team has more members
            team_order=session.get("team_order",[])
            team_idx=session.get("team_idx",0)
            remaining=[cid for i,cid in enumerate(team_order) if i>team_idx]
            if remaining:
                log+=f"\n<tg-emoji emoji-id='5426953124256424318'>💀</tg-emoji> <b>{session['p_char']}</b> was defeated!\n<b>Send your next fighter!</b>"
                session["awaiting_switch"]=True
                team_map=session.get("team_map",{})
                sw_kb=[]
                for cid in remaining:
                    cr=team_map.get(cid)
                    if cr:
                        sw_kb.append([Btn(f"{cr['char_name']} Lv.{cr['level']}",
                                          callback_data=f"ex:sw:{uid}:{cid}")])
                sw_kb.append([Btn("Forfeit",callback_data=f"ex:run:{uid}")])
                await safe_edit(q,f"{log}",sw_kb,is_photo); return
            else:
                del EX[uid]
                await db_set(uid,losses=user["losses"]+1)
                kb=[[Btn("Heal",callback_data="menu:heal"),
                     Btn("Try Again",callback_data="menu:explore")]]
                enemy_name = session.get("enemy", {}).get("name", "the enemy")
                defeat_turns = session.get("turn", "?")
                await safe_edit(q,
                    f"{pe('skull')} <b>DEFEATED!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"<b>{hesc(enemy_name)}</b> was too powerful this time.\n"
                    f"Your entire team fell after <b>{defeat_turns}</b> turns of combat.\n\n"
                    f"<i>Every great shinobi has faced defeat.\n"
                    f"Heal up, train your team, and come back stronger!</i>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"{log}",
                    kb, is_photo); return

    session["turn"]+=1
    # Tick Bijuu Mode turns
    if session.get("bijuu_active"):
        session["bijuu_turns_left"] = session.get("bijuu_turns_left", 1) - 1
        if session["bijuu_turns_left"] <= 0:
            session["bijuu_active"] = False
            log += f"\n🦊 Bijuu Mode fades — {hesc(session.get('bijuu_beast_name','Beast'))} rests.\n"
    # Check transform availability
    user2=await db_get(uid)
    form=cd.get("form")
    req_c=form["req_chakra"] if form else 999999
    transform_avail=(session["p_battle_chakra"]>=req_c and
                     user2.get("stones",0)>=1 and form and not session.get("p_transformed"))
    session["transform_available"]=transform_avail
    # Check Bijuu availability (needs 150 battle chakra, must be caught or always-host)
    tb_check = get_cdata(session["p_char"])
    tb_check_name = tb_check.get("tailed_beast") if tb_check else None
    _ALWAYS_BIJUU = {"Naruto (Baryon Mode)", "Naruto Uzumaki", "Minato Namikaze",
                     "Killer Bee", "Gaara", "Gaara (Fifth Kazekage)"}
    _caught_now = list(user2.get("caught_beasts") or [])
    bijuu_avail_now = (bool(tb_check_name and tb_check_name in BEASTS)
                       and session["p_battle_chakra"] >= 150
                       and not session.get("bijuu_active")
                       and (session["p_char"] in _ALWAYS_BIJUU or tb_check_name in _caught_now))
    session["bijuu_avail"] = bijuu_avail_now
    txt=fmt_battle_text(session,log)
    is_photo = session.get("is_photo", False)
    kb=move_btns_explore(get_char_moves(session["p_char"], session["p_level"]),uid,transform_avail,
                         weapon=session.get("equipped_weapon"), weapon_used=session.get("weapon_used",False),
                         bijuu_avail=bijuu_avail_now)
    # Update the battle message — use safe_edit so there's always a response
    await safe_edit(q, txt, kb, is_photo)

# ─── /battle + /duel ────────────────────────────────────────────
async def cmd_battle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid   = str(update.effective_user.id)
    reply = update.message.reply_to_message
    if not reply:
        await update.message.reply_text(
            "<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> <b>How to Battle:</b>\nReply to another player's message with /battle",
            parse_mode="HTML"); return
    opp_id=str(reply.from_user.id)
    if uid==opp_id: await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Can't battle yourself!"); return
    opp=await db_get(opp_id)
    if not opp: await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Opponent has no account!"); return
    my_team=await db_team(uid)
    if not my_team: await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Set a team first! Use /team"); return
    CHAL[opp_id]={"challenger_id":uid}
    name=update.effective_user.first_name
    oname=reply.from_user.first_name
    kb=[[Btn("Accept!",callback_data=f"pv:ac:{uid}:{opp_id}"),
         Btn("Decline",callback_data=f"pv:dc:{uid}:{opp_id}")]]
    await update.message.reply_text(
        f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> <b>Battle Challenge!</b>\n\n<tg-emoji emoji-id='5798483635199807367'>🔵</tg-emoji> <b>{name}</b> <tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> vs <tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>{oname}</b>\n\n"
        f"_{oname}, do you accept?_",
        parse_mode="HTML",reply_markup=Kbd(kb))

# ─── /wiki — Character Encyclopedia ────────────────────────────
def wiki_kb(name: str, section: str, has_form: bool, has_eyes: bool = False) -> list:
    tabs = [("Overview","ov"),("Stats","st"),("Moves","mv"),("Weakness","wk")]
    if has_form:
        tabs.append(("Form/Beast","fm"))
    if has_eyes:
        tabs.append(("Eyes","ey"))
    rows = []
    row  = []
    for label, key in tabs:
        marker = f"▸{label}◂" if key == section else label
        row.append(Btn(marker, callback_data=f"wk:{key}:{name[:40]}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row: rows.append(row)
    return rows

def wiki_text(found: dict, section: str) -> str:
    kg   = CLAN_KG.get(found["clan"], "None")
    ki   = KG.get(kg, KG["None"])
    rr   = RAR.get(found["rarity"], "⚪")
    form = found.get("form")
    tb   = found.get("tailed_beast")
    tb_i = BEASTS.get(tb) if tb else None
    adv  = ADV.get(found["nature"], {"s": [], "w": []})
    header = f"📖 <b>{found['name']}</b> {rr} ⟨{found['rarity']}⟩\n━━━━━━━━━━━━━━━━━━━━\n"

    if section == "ov":
        txt = (
            header +
            f"<tg-emoji emoji-id='5426872512015244606'>🌿</tg-emoji> <b>Nature:</b> {found['nature']} {nat_icon(found['nature'])}\n"
            f"<tg-emoji emoji-id='5427342518876381603'>🏘️</tg-emoji> <b>Village:</b> {found['village']}\n"
            f"<tg-emoji emoji-id='5224388744156557558'>🧬</tg-emoji> <b>Clan:</b> {found['clan']}\n"
            f"<tg-emoji emoji-id='5424892463372312872'>⭐</tg-emoji> <b>Rarity:</b> {found['rarity']}\n"
            f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>KG:</b> {kg}\n"
            f"<i>{ki['desc'][:80]}</i>\n"
        )
        if tb_i:
            txt += f"\n<tg-emoji emoji-id='6003600664687546316'>🦊</tg-emoji> <b>Tailed Beast:</b> {tb} ({tb_i['tails']}<tg-emoji emoji-id='6003600664687546316'>🦊</tg-emoji>)\n<i>{tb_i['ability'][:60]}</i>\n"
        if form:
            txt += f"\n<tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji> <b>Form:</b> {form['name']} (needs {form['req_chakra']:,}<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji>)\n"
        return txt

    if section == "st":
        b = found["base"]
        bar = lambda v, mx=600: "█"*int(v/mx*10) + "░"*(10-int(v/mx*10))
        return (
            header +
            f"<tg-emoji emoji-id='5427095369278299187'>❤️</tg-emoji> <b>HP</b>  <code>{b['hp']:>4}</code>  {bar(b['hp'])}\n"
            f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> <b>ATK</b> <code>{b['atk']:>4}</code>  {bar(b['atk'])}\n"
            f"<tg-emoji emoji-id='6039727447090403055'>🛡️</tg-emoji> <b>DEF</b> <code>{b['def']:>4}</code>  {bar(b['def'])}\n"
            f"💨 <b>SPD</b> <code>{b['speed']:>4}</code>  {bar(b['speed'])}\n"
            f"<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> <b>CHK</b> <code>{b['chakra']:>4}</code>  {bar(b['chakra'],200)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Bonus:</b> {found.get('bonus','')}\n"
        )

    if section == "mv":
        txt = header + "<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> <b>Moves:</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        for m in found["moves"]:
            adv_m = ADV.get(m["type"], {"s": [], "w": []})
            strong = f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> {adv_m['s'][0]}" if adv_m.get("s") else ""
            txt += (
                f"<b>{m['name']}</b> {nat_icon(m['type'])}\n"
                f"  Pwr:{m['power']} | Acc:{m['acc']}% | Crit:{m.get('crit',8)}%"
                f" | Miss:{m.get('miss',10)}% {strong}\n"
            )
        return txt

    if section == "wk":
        strong_vs = ", ".join(adv["s"]) or "None"
        weak_vs   = ", ".join(adv["w"]) or "None"
        txt = (
            header +
            f"<b>Nature:</b> {found['nature']} {nat_icon(found['nature'])}\n\n"
            f"<tg-emoji emoji-id='5803416753031615097'>⬆️</tg-emoji> <b>Strong vs:</b> {strong_vs}\n"
            f"<tg-emoji emoji-id='5803204762035818905'>⬇️</tg-emoji> <b>Weak vs:</b>   {weak_vs}\n\n"
            f"<b>KG Bonus:</b> {kg}\n<i>{ki['desc'][:80]}</i>\n"
        )
        txt += "\n<b>Move type strengths:</b>\n"
        seen = set()
        for m in found["moves"]:
            if m["type"] in seen: continue
            seen.add(m["type"])
            ma = ADV.get(m["type"], {"s": [], "w": []})
            txt += f"  {nat_icon(m['type'])} {m['type']}: <tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji>{', '.join(ma['s']) or '—'}  <tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji>{', '.join(ma['w']) or '—'}\n"
        return txt

    if section == "fm":
        txt = header
        if form:
            bs = " | ".join(f"{k.upper()}+{v}" for k, v in form["buff"].items() if v > 0)
            txt += (
                f"<tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji> <b>Transformation: {form['name']}</b>\n"
                f"  ━━━━━━━━━━━━━━━━━━━━\n"
                f"  <b>Requires:</b> {form['req_chakra']:,} <tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> Battle Chakra\n"
                f"  + 1 Transform Stone <tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji>\n"
                f"  <b>Stat Buffs:</b> {bs}\n"
                f"  <b>How it works:</b> Build Battle Chakra by using moves in combat.\n"
                f"  When threshold is reached, tap Transform to enter this form.\n\n"
            )
        else:
            txt += "<i>This character has no transformation form.</i>\n\n"
        if tb_i:
            bi_bonus_txt = (f"  <b>Caught Bonus:</b> HP +{tb_i['catch_hp_boost']} | "
                            f"ATK +{tb_i['catch_atk_boost']}\n") if tb_i.get('catch_hp_boost') else ""
            host_chars = ", ".join(tb_i.get("host_chars", [tb_i.get("host","?")]))
            txt += (
                f"{tb_i.get('emoji','🦊')} <b>Tailed Beast: {tb}</b>\n"
                f"  ━━━━━━━━━━━━━━━━━━━━\n"
                f"  <b>Tails:</b> {tb_i['tails']} | <b>Power:</b> {tb_i.get('power',0):,}\n"
                f"  <b>Nature:</b> {tb_i.get('nat','?')} | <b>Location:</b> {tb_i.get('village','?')}\n"
                f"  <b>Hosts:</b> {hesc(host_chars)}\n"
                f"  <b>Ability:</b> <i>{hesc(tb_i['ability'])}</i>\n"
                f"  <b>Lore:</b> <i>{hesc(tb_i.get('desc',''))}</i>\n"
                f"{bi_bonus_txt}"
                f"  <b>Bijuu Mode:</b> Requires 150 Battle Chakra in combat.\n"
                f"  Grants 4 turns of boosted HP+ATK + initial beast blast.\n"
                f"  Beast must first be caught by defeating it in Explore!\n"
            )
        if not form and not tb_i:
            txt += "<i>No form or beast data for this character.</i>\n"
        return txt

    if section == "ey":
        eye_name = CHAR_EYE_POWER.get(found["name"])
        ep = EYE_POWERS.get(eye_name) if eye_name else None
        txt = header
        if not ep:
            txt += "<i>This character has no known Dojutsu (eye power).</i>"
            return txt
        clan_list = ", ".join(ep["clans"])
        ab_list = "\n".join(f"  • {hesc(a)}" for a in ep["abilities"])
        bonus_parts = []
        for k, v in ep.get("battle_bonus", {}).items():
            bonus_parts.append(f"{k.upper()} +{v}")
        bonus_str = " | ".join(bonus_parts) or "None"
        upgrade_str = f"\n  <b>Evolves to:</b> {hesc(ep['upgrade'])}" if ep.get("upgrade") else ""
        txt += (
            f"{ep['emoji']} <b>Dojutsu: {hesc(eye_name)}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Clans:</b> {hesc(clan_list)}\n"
            f"<b>Description:</b>\n  <i>{hesc(ep['desc'])}</i>\n\n"
            f"<b>Abilities:</b>\n{ab_list}\n\n"
            f"<b>How it Works:</b>\n  <i>{hesc(ep['how_works'])}</i>\n\n"
            f"<b>Battle Bonus:</b> {bonus_str}{upgrade_str}\n"
        )
        return txt

    return header + "<i>Unknown section.</i>"

async def cmd_wiki(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await update.message.reply_text(
            "📖 <b>Naruto Wiki</b> — No account needed!\n"
            "Usage: <code>/wiki &lt;character name&gt;</code>\n"
            "Example: <code>/wiki Naruto Uzumaki</code>\n\n"
            "<i>Search any of the 225 characters!</i>",
            parse_mode="HTML")
        return
    query = " ".join(args).lower()
    found = next((c for c in CHARACTERS if query in c["name"].lower()), None)
    if not found:
        close = [c["name"] for c in CHARACTERS
                 if any(w in c["name"].lower() for w in query.split())][:5]
        msg = f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> <b>{' '.join(args)}</b> not found!\n"
        if close: msg += "Did you mean: " + ", ".join(f"`{n}`" for n in close) + "?"
        await update.message.reply_text(msg, parse_mode="HTML")
        return
    has_form = bool(found.get("form") or found.get("tailed_beast"))
    has_eyes = found["name"] in CHAR_EYE_POWER
    txt   = wiki_text(found, "ov")
    kb    = wiki_kb(found["name"], "ov", has_form, has_eyes)
    photo = PHOTO_CACHE.get(found["name"])
    if photo:
        try:
            await update.message.reply_photo(photo=photo, caption=txt[:1020],
                                             parse_mode="HTML", reply_markup=Kbd(kb))
            return
        except: pass
    await update.message.reply_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))

async def cb_wiki(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts   = q.data.split(":", 2)
    section = parts[1]
    name    = parts[2] if len(parts) > 2 else ""
    found   = next((c for c in CHARACTERS if c["name"].lower().startswith(name.lower())), None)
    if not found:
        await q.answer("Character not found!", show_alert=True); return
    has_form = bool(found.get("form") or found.get("tailed_beast"))
    has_eyes = found["name"] in CHAR_EYE_POWER
    txt  = wiki_text(found, section)
    kb   = wiki_kb(found["name"], section, has_form, has_eyes)
    is_photo_msg = bool(q.message and q.message.photo)
    try:
        if is_photo_msg:
            await q.edit_message_caption(caption=txt[:1020], parse_mode="HTML",
                                         reply_markup=Kbd(kb))
        else:
            await q.edit_message_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))
    except Exception:
        pass

# ─── /exchange — Chakra ↔ NC Exchange ───────────────────────────
async def cmd_exchange(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid=str(update.effective_user.id); user=await db_get(uid)
    kb=[
        [Btn("100 Chakra → 200 NC",   callback_data=f"xc:c2n:100:{uid}"),
         Btn("500 Chakra → 1000 NC",  callback_data=f"xc:c2n:500:{uid}")],
        [Btn("200 NC → 100 Chakra",   callback_data=f"xc:n2c:200:{uid}"),
         Btn("1000 NC → 500 Chakra",  callback_data=f"xc:n2c:1000:{uid}")],
        [Btn("1000 Chakra → 2200 NC", callback_data=f"xc:c2n:1000:{uid}")],
    ]
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5769455402945090965'>🔄</tg-emoji> <b>Exchange</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> NC: <b>{user['coins']:,}</b> | <tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> Chakra: <b>{user['chakra']:,}</b>\n\n"
        f"Convert between NC and Chakra:\n"
        f"• 100 Chakra = 200 NC\n"
        f"• 200 NC = 100 Chakra\n"
        f"• 1000 Chakra = 2200 NC _(bonus rate!)_",
        parse_mode="HTML", reply_markup=Kbd(kb))

async def cb_exchange(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    parts=q.data.split(":"); mode=parts[1]; amt=int(parts[2]); uid=parts[3]
    if str(q.from_user.id)!=uid: await q.answer("Not yours!",show_alert=True); return
    user=await db_get(uid)
    if mode=="c2n":
        give_out = {100:200, 500:1000, 1000:2200}.get(amt, amt*2)
        if user["chakra"]<amt:
            await q.answer(f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Need {amt} Chakra!",show_alert=True); return
        await db_set(uid, chakra=user["chakra"]-amt, coins=user["coins"]+give_out)
        await q.answer(f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> -{amt}<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> +{give_out}<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji>",show_alert=True)
    elif mode=="n2c":
        give_out = {200:100, 1000:500}.get(amt, amt//2)
        if user["coins"]<amt:
            await q.answer(f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Need {amt} NC!",show_alert=True); return
        await db_set(uid, coins=user["coins"]-amt, chakra=user["chakra"]+give_out)
        await q.answer(f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> -{amt}<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> +{give_out}<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji>",show_alert=True)
    user2=await db_get(uid)
    try:
        await q.edit_message_text(
            f"<tg-emoji emoji-id='5769455402945090965'>🔄</tg-emoji> <b>Exchange</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> NC: <b>{user2['coins']:,}</b> | <tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> Chakra: <b>{user2['chakra']:,}</b>\n\n"
            f"_Transaction complete!_",
            parse_mode="HTML",
            reply_markup=q.message.reply_markup)
    except: pass

async def cmd_duel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid=str(update.effective_user.id)
    reply=update.message.reply_to_message
    if not reply:
        await update.message.reply_text(
            "<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> <b>Duel Challenge</b>\n\nReply to a player's message with /duel to challenge them!",
            parse_mode="HTML"); return
    opp_id=str(reply.from_user.id)
    if uid==opp_id: await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Can't duel yourself!"); return
    opp=await db_get(opp_id)
    if not opp: await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> That user has no account!"); return
    user=await db_get(uid)
    CHAL[opp_id]=uid
    kb=[[Btn("Accept Duel",callback_data=f"pv:ac:{uid}:{opp_id}"),
         Btn("Decline",callback_data=f"pv:dc:{uid}:{opp_id}")]]
    dn=display_name(user); odn=display_name(opp)
    await update.message.reply_text(
        f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> <b>Duel Challenge!</b>\n\n<b>{dn}</b> challenges <b>{odn}</b> to a duel!\n\n"
        f"_{odn}, accept or decline below:_",
        parse_mode="HTML",reply_markup=Kbd(kb))

async def cb_pvp_challenge(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    parts=q.data.split(":"); action=parts[1]; c_uid=parts[2]; t_uid=parts[3]
    caller=str(q.from_user.id)
    if action=="dc":
        if caller!=t_uid: await q.answer("Not yours!",show_alert=True); return
        CHAL.pop(t_uid,None)
        await q.edit_message_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Challenge declined."); return
    if action!="ac": return
    if caller!=t_uid: await q.answer("Not yours!",show_alert=True); return
    ct=await db_team(c_uid); tt=await db_team(t_uid)
    if not ct: await q.edit_message_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Challenger has no team!"); return
    if not tt: await q.edit_message_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> You need a team! Use /team"); return
    CHAL.pop(t_uid,None)
    cu=await db_get(c_uid); tu=await db_get(t_uid)

    def build_side(team, user):
        d={}; lv_d={}
        vi_i=VILLAGES.get(user.get("village","Konoha"),{})
        for row in team:
            cd=get_cdata(row["char_name"])
            if not cd: continue
            pkg=CLAN_KG.get(cd["clan"],"None"); kg_b=KG.get(pkg,{}).get("all_stats",0)
            lv=row["level"]
            hp  =int(calc_stat(cd["base"]["hp"],   row["pp_hp"],  lv)*(1+kg_b))
            atk =int(calc_stat(cd["base"]["atk"],  row["pp_atk"], lv)*(1+kg_b))
            dfc =int(calc_stat(cd["base"]["def"],   row["pp_def"],  lv)*(1+kg_b))
            spd =int(calc_stat(cd["base"]["speed"],row["pp_spd"], lv)*(1+kg_b))
            cha =cd["base"]["chakra"]+row["pp_cha"]*2
            d[row["char_name"]]={"hp":hp,"max_hp":hp,"atk":atk,"def":dfc,"spd":spd,"chakra":cha}
            lv_d[row["char_name"]]=lv
        return d,lv_d

    cs,clv=build_side(ct,cu); ts,tlv=build_side(tt,tu)
    fc=next((n for n,v in cs.items() if v["hp"]>0),None)
    ft=next((n for n,v in ts.items() if v["hp"]>0),None)
    if not fc or not ft: await q.edit_message_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Team error!"); return

    def get_nat(n): cd=get_cdata(n); return cd["nature"] if cd else "Wind"
    def get_kg(n):  cd=get_cdata(n); return CLAN_KG.get(cd["clan"],"None") if cd else "None"

    # Speed determines first turn
    cs_spd=cs[fc]["spd"]; ts_spd=ts[ft]["spd"]
    first_turn=c_uid if cs_spd>=ts_spd else t_uid

    bkey=f"{c_uid}_{t_uid}"
    state={
        "p1":c_uid,"p2":t_uid,
        "chars":{c_uid:cs,t_uid:ts},
        "cur":{c_uid:fc,t_uid:ft},
        "hp":{c_uid:cs[fc]["hp"],t_uid:ts[ft]["hp"]},
        "mhp":{c_uid:cs[fc]["max_hp"],t_uid:ts[ft]["max_hp"]},
        "nat":{c_uid:get_nat(fc),t_uid:get_nat(ft)},
        "kg":{c_uid:get_kg(fc),t_uid:get_kg(ft)},
        "lv":{c_uid:clv.get(fc,1),t_uid:tlv.get(ft,1)},
        "lv_data":{c_uid:clv,t_uid:tlv},
        "status":{c_uid:"",t_uid:""},
        "dot":{c_uid:None,t_uid:None},
        "def_broken":{c_uid:False,t_uid:False},
        "dodge_next":{c_uid:False,t_uid:False},
        "revived":{c_uid:False,t_uid:False},
        "battle_chakra":{c_uid:0,t_uid:0},
        "transform_avail":{c_uid:False,t_uid:False},
        "transformed":{c_uid:False,t_uid:False},
        "names":{c_uid:cu["name"],t_uid:tu["name"]},
        "stones":{c_uid:cu.get("stones",0),t_uid:tu.get("stones",0)},
        "turn":first_turn,
    }
    PVP[bkey]=state
    fc_cd=get_cdata(fc)
    txt=fmt_pvp_text(state)
    transform_avail=state["transform_avail"].get(first_turn,False)
    kb=move_btns_pvp(get_char_moves(fc,clv.get(fc,1)) if fc_cd else [],c_uid,t_uid,transform_avail)
    spd_note=(f"\n<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> {state['names'][first_turn]} goes first! (Higher SPD: {max(cs_spd,ts_spd)})")
    await q.edit_message_text(txt+spd_note,parse_mode="HTML",reply_markup=Kbd(kb))

async def cb_pvp_move(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    parts=q.data.split(":"); mi=int(parts[1]); c_uid=parts[2]; t_uid=parts[3]
    bkey=f"{c_uid}_{t_uid}"; uid=str(q.from_user.id)
    state=PVP.get(bkey)
    if not state: await q.edit_message_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Battle expired!"); return
    tid=state["turn"]
    if uid!=tid: await q.answer("Not your turn!",show_alert=True); return
    oid=state["p2"] if tid==state["p1"] else state["p1"]
    tc=state["cur"][tid]; oc=state["cur"][oid]
    tcd=get_cdata(tc); ocd=get_cdata(oc)
    if not tcd or not ocd: return
    if mi>=len(tcd["moves"]): return
    move=tcd["moves"][mi]; log=""

    # Gain battle chakra
    state["battle_chakra"][tid]=state["battle_chakra"].get(tid,0)+move.get("chakra",20)

    if state["status"][tid]=="stun":
        state["status"][tid]=""; log+=f"😵 <b>{tc}</b> stunned — skips!\n"
    else:
        o_def=state["chars"][oid][oc]["def"]*(0.7 if state["def_broken"].get(oid) else 1.0)
        if state["dodge_next"].get(oid):
            state["dodge_next"][oid]=False; log+=f"  <tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>{oc}</b> dodged!\n"
        else:
            res=resolve_attack(move,
                state["chars"][tid][tc]["atk"],o_def,
                state["nat"][tid],state["nat"][oid],
                state["kg"][tid],state["kg"][oid],
                atk_lv=state["lv"][tid],def_lv=state["lv"][oid])
            if res["hit"]:
                dmg=res["dmg"]
                state["chars"][oid][oc]["hp"]=max(0,state["chars"][oid][oc]["hp"]-dmg)
                state["hp"][oid]=state["chars"][oid][oc]["hp"]
                log+=f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> <b>{tc}</b> → <b>{move['name']}</b>\n  {res['eff_txt']} <b>-{dmg} HP</b>\n"
                if res.get("kg_def"): log+=f"  {res['kg_def']}\n"
                if res.get("reflect",0):
                    state["chars"][tid][tc]["hp"]=max(0,state["chars"][tid][tc]["hp"]-res["reflect"])
                    state["hp"][tid]=state["chars"][tid][tc]["hp"]
                    log+=f"  <tg-emoji emoji-id='5769455402945090965'>🔄</tg-emoji> Reflect <b>-{res['reflect']}</b> back!\n"
                en=apply_effects_pvp(res["effects"],state,oid)
                if en: log+="  "+" ".join(en)+"\n"
            else:
                log+=f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> <b>{tc}</b> → <b>{move['name']}</b> — <b>MISSED!</b>\n"

            # ── ATTACK PHOTO: always show normal portrait during attacks ─────────
            # get_alt NOT used — char shows normal form until TRANSFORM is pressed.
            j_img = (PHOTO_CACHE.get(tc)
                     or MOVE_IMAGE_CACHE.get(move["name"])
                     or JUTSU_CACHE.get(move["name"]))
            if j_img:
                try:
                    crit_tag = "💥 <b>CRITICAL HIT!</b> " if res.get("crit") else ""
                    miss_tag = "❌ <b>MISSED!</b> " if not res["hit"] else ""
                    nat_tag  = f"{res['eff_txt']} "  if res["hit"] else ""
                    dmg_tag  = f"<b>-{res['dmg']} HP</b>" if res["hit"] else ""
                    pname    = state["names"].get(tid, tc)
                    cap = (f"{crit_tag}{miss_tag}"
                           f"<b>{hesc(pname)}</b>'s <b>{hesc(tc)}</b> uses <b>{hesc(move['name'])}</b>!\n"
                           f"{nat_tag}{dmg_tag}").strip()
                    is_photo_msg = bool(q.message and q.message.photo)
                    if is_photo_msg:
                        # Edit the current photo in-place (same as explore)
                        nc_char = state["cur"][oid]
                        nc_cd   = get_cdata(nc_char)
                        ta      = state["transform_avail"].get(oid, False)
                        await q.message.edit_media(
                            media=InputMediaPhoto(media=j_img, caption=cap[:1020],
                                                  parse_mode="HTML"),
                            reply_markup=Kbd(move_btns_pvp(
                                get_char_moves(nc_char,state["lv"].get(oid,1)) if nc_cd else [], c_uid, t_uid, ta)))
                        state["is_photo"] = True
                    else:
                        await q.message.reply_photo(photo=j_img, caption=cap[:1020],
                                                    parse_mode="HTML")
                except Exception:
                    pass

    def check_ko(vid, ally_id):
        vc=state["cur"][vid]
        if state["chars"][vid][vc]["hp"]<=0:
            if not state["revived"].get(vid) and KG.get(state["kg"].get(vid,"None"),{}).get("revive"):
                rh=int(state["chars"][vid][vc]["max_hp"]*0.25)
                state["chars"][vid][vc]["hp"]=rh; state["hp"][vid]=rh; state["revived"][vid]=True
                return f"  💚 {vc} revived at 25%!\n",False
            nc2=next((n for n,d in state["chars"][vid].items() if d["hp"]>0 and n!=vc),None)
            if nc2:
                state["cur"][vid]=nc2; state["hp"][vid]=state["chars"][vid][nc2]["hp"]
                state["mhp"][vid]=state["chars"][vid][nc2]["max_hp"]
                cd2=get_cdata(nc2)
                state["nat"][vid]=cd2["nature"] if cd2 else "Wind"
                state["kg"][vid]=CLAN_KG.get(cd2["clan"],"None") if cd2 else "None"
                state["lv"][vid]=state["lv_data"][vid].get(nc2,1)
                state["dot"][vid]=None; state["status"][vid]=""
                state["transformed"][vid]=False
                return f"  <tg-emoji emoji-id='5426953124256424318'>💀</tg-emoji> <b>{vc}</b> fainted! → <b>{nc2}</b> enters!\n",False
            return "",True
        return "",False

    kn,all_dead=check_ko(oid,tid); log+=kn
    if all_dead:
        del PVP[bkey]
        wu=await db_get(tid); lu=await db_get(oid); rw=100
        await db_set(tid,wins=wu["wins"]+1,coins=wu["coins"]+rw)
        await db_set(oid,losses=lu["losses"]+1)
        win_char=state["cur"][tid]; win_photo=PHOTO_CACHE.get(win_char)
        pvp_turns = state.get("turn_count", len(log.split("\n")) if log else 1)
        pvp_hp_left = state["hp"].get(tid, 0)
        pvp_mhp = state["mhp"].get(tid, 1)
        pvp_hp_pct = int((pvp_hp_left / pvp_mhp) * 100) if pvp_mhp else 0
        if pvp_hp_pct >= 80:
            pvp_hp_txt = "Dominated the duel!"
        elif pvp_hp_pct >= 50:
            pvp_hp_txt = "Solid performance."
        elif pvp_hp_pct >= 20:
            pvp_hp_txt = "Hard-fought win — barely standing!"
        else:
            pvp_hp_txt = "Survived by a miracle!"
        pvp_loser_name = lu.get("nickname") or lu["name"]
        win_txt=(
                 f"{pe('trophy')} <b>PvP VICTORY!</b>\n"
                 f"━━━━━━━━━━━━━━━━━━━━\n"
                 f"{pe('sword')} <b>{wu.get('nickname') or wu['name']}</b> defeated <b>{pvp_loser_name}</b>!\n"
                 f"{pe('star')} Winning character: <b>{win_char}</b>\n"
                 f"{pe('hp')} HP remaining: <b>{pvp_hp_left}/{pvp_mhp}</b> — <i>{pvp_hp_txt}</i>\n"
                 f"━━━━━━━━━━━━━━━━━━━━\n"
                 f"<b>Rewards:</b>\n"
                 f"  {pe('coin')} +<b>{rw} NC</b> victory bonus\n"
                 f"  {pe('exp')} Record: <b>{wu['wins']+1}W / {wu['losses']}L</b>\n"
                 f"━━━━━━━━━━━━━━━━━━━━\n"
                 f"{log}")
        composite = await make_pvp_win_image(ctx.bot, tid, win_photo)
        if composite:
            try:
                await q.message.reply_photo(photo=composite, caption=win_txt[:1020], parse_mode="HTML")
                return
            except: pass
        await q.edit_message_text(win_txt, parse_mode="HTML"); return

    for pid in [tid,oid]:
        if state["dot"].get(pid):
            state["hp"][pid],dn=apply_dot(state["dot"][pid],state["hp"][pid])
            cv=state["cur"][pid]
            if cv in state["chars"][pid]: state["chars"][pid][cv]["hp"]=state["hp"][pid]
            state["dot"][pid]=tick_dot(state["dot"][pid]); log+=f"  {dn}\n"
        regen,rn=kg_turn_regen(state["kg"].get(pid,"None"),state["hp"][pid],state["mhp"][pid])
        if regen:
            state["hp"][pid]=min(state["mhp"][pid],state["hp"][pid]+regen)
            cv=state["cur"][pid]
            if cv in state["chars"][pid]: state["chars"][pid][cv]["hp"]=state["hp"][pid]
            log+=f"  {rn}\n"

    kn2,self_dead=check_ko(tid,oid); log+=kn2
    if self_dead:
        del PVP[bkey]
        wu=await db_get(oid); lu=await db_get(tid); rw=100
        await db_set(oid,wins=wu["wins"]+1,coins=wu["coins"]+rw)
        await db_set(tid,losses=lu["losses"]+1)
        win_char2=state["cur"][oid]; win_photo2=PHOTO_CACHE.get(win_char2)
        win_txt2=(f"<tg-emoji emoji-id='5426976939850080222'>🏆</tg-emoji> <b>VICTORY!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n{log}\n"
                  f"<tg-emoji emoji-id='5426976939850080222'>🥇</tg-emoji> <b>{wu.get('nickname') or wu['name']}</b> wins!\n"
                  f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> Winner's Char: <b>{win_char2}</b>\n"
                  f"<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> +<b>{rw} NC</b> reward!\n"
                  f"<tg-emoji emoji-id='5981204549132619885'>📊</tg-emoji> Record: {wu['wins']+1}W {wu['losses']}L")
        composite2 = await make_pvp_win_image(ctx.bot, oid, win_photo2)
        if composite2:
            try:
                await q.message.reply_photo(photo=composite2, caption=win_txt2[:1020], parse_mode="HTML")
                return
            except: pass
        await q.edit_message_text(win_txt2, parse_mode="HTML"); return

    state["turn"]=oid
    PVP[bkey]=state
    # Check transform for next player
    nc_char=state["cur"][oid]; nc_cd=get_cdata(nc_char)
    nc_form=nc_cd.get("form") if nc_cd else None
    req_c=nc_form["req_chakra"] if nc_form else 999999
    bc=state["battle_chakra"].get(oid,0)
    st=state["stones"].get(oid,0)
    ta=(bc>=req_c and st>=1 and nc_form and not state["transformed"].get(oid))
    state["transform_avail"][oid]=ta
    txt=fmt_pvp_text(state,log)
    kb=move_btns_pvp(get_char_moves(nc_char,state["lv"].get(oid,1)) if nc_cd else [],c_uid,t_uid,ta)
    await q.edit_message_text(txt,parse_mode="HTML",reply_markup=Kbd(kb))

async def cb_pvp_transform(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    parts=q.data.split(":"); c_uid=parts[1]; t_uid=parts[2]
    bkey=f"{c_uid}_{t_uid}"; uid=str(q.from_user.id)
    state=PVP.get(bkey)
    if not state: return
    tid=state["turn"]
    if uid!=tid: await q.answer("Not your turn!",show_alert=True); return
    if state["stones"].get(tid,0)<1:
        await q.answer("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> No Transform Stone!",show_alert=True); return
    tc=state["cur"][tid]; tcd=get_cdata(tc)
    form=tcd.get("form") if tcd else None
    if not form: return
    buff=form["buff"]
    state["chars"][tid][tc]["hp"]+=buff.get("hp",0)
    state["chars"][tid][tc]["max_hp"]+=buff.get("hp",0)
    state["chars"][tid][tc]["atk"]+=buff.get("atk",0)
    state["chars"][tid][tc]["def"]+=buff.get("def",0)
    state["chars"][tid][tc]["spd"]+=buff.get("speed",0)
    state["hp"][tid]=state["chars"][tid][tc]["hp"]
    state["mhp"][tid]=state["chars"][tid][tc]["max_hp"]
    state["transformed"][tid]=True; state["transform_avail"][tid]=False
    state["stones"][tid]-=1
    # Update DB stone count
    tu=await db_get(tid)
    await db_set(tid,stones=max(0,tu.get("stones",0)-1))
    # Show form-specific photo (e.g. Baryon Mode image, not normal Naruto portrait)
    _pvp_tf_photo = get_form_photo(tcd["name"], form["name"]) if tcd else None
    if _pvp_tf_photo:
        try:
            await q.message.reply_photo(
                photo=_pvp_tf_photo,
                caption=f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>TRANSFORMATION!</b>\n<b>{tc}</b> → <b>{form['name']}</b>!\n<tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji> Transform Stone consumed!",
                parse_mode="HTML")
        except: pass
    log=f"<tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji> <b>{tc}</b> → <b>{form['name']}</b>! Stats buffed!\n"
    txt=fmt_pvp_text(state,log)
    kb=move_btns_pvp(get_char_moves(tc,state["lv"].get(tid,1)),c_uid,t_uid,False)
    await q.edit_message_text(txt,parse_mode="HTML",reply_markup=Kbd(kb))

async def cb_pvp_forfeit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    _,c_uid,t_uid=q.data.split(":")
    bkey=f"{c_uid}_{t_uid}"; uid=str(q.from_user.id)
    if not PVP.get(bkey): await q.edit_message_text("Battle not found!"); return
    opp=t_uid if uid==c_uid else c_uid
    del PVP[bkey]
    wu=await db_get(opp); lu=await db_get(uid)
    await db_set(opp,wins=wu["wins"]+1,coins=wu["coins"]+500)
    await db_set(uid,losses=lu["losses"]+1)
    await q.edit_message_text(
        f"🏳️ <b>{lu['name']}</b> forfeited!\n<tg-emoji emoji-id='5426976939850080222'>🏆</tg-emoji> <b>{wu['name']}</b> wins +500 NC!",
        parse_mode="HTML")

# ─── /info ──────────────────────────────────────────────────────
async def cmd_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid = str(update.effective_user.id)
    if not ctx.args:
        await update.message.reply_text(
            "Usage: /info <character name>\nExample: /info Naruto\n\nOnly shows characters you own.")
        return
    query = " ".join(ctx.args).strip().lower()
    chars = await db_chars(uid)
    owned = next((c for c in chars if query in c["char_name"].lower()), None)
    if not owned:
        await update.message.reply_text(
            f"You don't own a character matching '{' '.join(ctx.args)}'.\nUse /summon to get more characters.")
        return
    cd = get_cdata(owned["char_name"])
    if not cd:
        await update.message.reply_text("Character data not found."); return
    lv   = owned["level"]
    cexp = owned.get("exp", 0)
    char_lv_needed = int(80 * (lv ** 1.4))
    kg   = CLAN_KG.get(cd["clan"], "None")
    ki   = KG.get(kg, KG["None"])
    if kg != "None":
        ability_txt = ki["desc"]
    else:
        ability_txt = (f"{owned['char_name']} is a {cd['nature']} nature shinobi from {cd['village']} "
                       f"with mastery in {cd['nature']} style jutsu and exceptional combat skills.")
    user = await db_get(uid)
    equipped_wid    = user.get("equipped_weapon")
    equipped_weapon = get_weapon_by_id(equipped_wid) if equipped_wid else None
    weapon_name     = equipped_weapon["name"] if equipped_weapon else "None"
    total_pp        = (owned.get("pp_hp",0)+owned.get("pp_atk",0)+owned.get("pp_def",0)
                       +owned.get("pp_spd",0)+owned.get("pp_cha",0))
    awakening_lv    = total_pp // 5
    txt = (
        f"Shinobi Info\n"
        f"Shinobi: {owned['char_name']}\n"
        f"Ability: {ability_txt}\n\n"
        f"Level: {lv}\n"
        f"Exp: {cexp} / {char_lv_needed}\n"
        f"Chakra: {user['chakra']:,} / 60000\n"
        f"Awakening Level: {awakening_lv}\n"
        f"Main Nature: {cd['nature']}\n"
        f"Equipped Weapon: {weapon_name}"
    )
    cid  = owned["id"]
    kb   = [[Btn("Moves", callback_data=f"info:moves:{cid}"),
             Btn("Advantage", callback_data=f"info:adv:{cid}")]]
    row2 = []
    if cd.get("form"):
        row2.append(Btn("Transform", callback_data=f"info:tf:{cid}"))
    if cd.get("tailed_beast"):
        row2.append(Btn("Beast", callback_data=f"info:beast:{cid}"))
    if row2:
        kb.append(row2)
    kb.append([Btn("More Info", callback_data=f"info:more:{cid}")])
    photo = best_char_photo(owned["char_name"])
    if photo:
        try:
            await update.message.reply_photo(photo=photo, caption=txt[:1020], reply_markup=Kbd(kb))
            return
        except Exception:
            pass
    await update.message.reply_text(txt, reply_markup=Kbd(kb))


async def cb_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts  = q.data.split(":")
    action = parts[1]; cid = int(parts[2])
    uid    = str(q.from_user.id)
    row    = _cdoc(await chars_col.find_one({"_id": cid, "uid": uid}))
    if not row:
        await q.answer("Character not found!", show_alert=True); return
    cd = get_cdata(row["char_name"])
    if not cd:
        await q.answer("Character data missing!", show_alert=True); return
    back_kb = [[Btn("Back", callback_data=f"info:back:{cid}")]]

    if action == "moves":
        lv       = row["level"]
        unlocked = get_char_moves(row["char_name"], lv)
        all_mvs  = cd["moves"]
        lines    = []
        for i, m in enumerate(all_mvs, 1):
            strong  = [n for n in ALL_NATURES if type_mult(m["type"], n) > 1.0]
            hint    = f" (Strong vs: {', '.join(strong[:2])})" if strong else ""
            eff_raw = m.get("effect","").replace(":"," +").replace("_"," ")
            eff_txt = f" | {eff_raw.title()}" if eff_raw else ""
            locked  = i > len(unlocked)
            if locked:
                ul = 10 if i==2 else (20 if i==3 else 30)
                lines.append(f"{i}. {m['name']} [{m['type']}] (Locked - Lv{ul})\n"
                             f"   Power: {m['power']} | Acc: {m['acc']}%{eff_txt}{hint}")
            else:
                lines.append(f"{i}. {m['name']} [{m['type']}]\n"
                             f"   Power: {m['power']} | Acc: {m['acc']}% | Chakra: {m['chakra']}{eff_txt}{hint}")
        txt = (f"{row['char_name']} - Moves\n"
               f"Unlocked: {len(unlocked)} / {len(all_mvs)}\n"
               f"{'='*22}\n\n" + "\n\n".join(lines))
        await _safe_edit(q, txt[:4000], back_kb)

    elif action == "adv":
        nat      = cd["nature"]
        adv_info = ADV.get(nat, {})
        strong   = adv_info.get("s", [])
        weak     = adv_info.get("w", [])
        txt = (f"{row['char_name']} - Nature Advantage\n"
               f"{'='*22}\n"
               f"Main Nature: {nat}\n\n"
               f"Strong against: {', '.join(strong) if strong else 'None'}\n"
               f"Weak against:   {', '.join(weak) if weak else 'None'}")
        await _safe_edit(q, txt, back_kb)

    elif action == "tf":
        form = cd.get("form")
        if not form:
            await q.answer("No transform available!", show_alert=True); return
        buffs = " | ".join(f"{k.upper()} +{v}" for k,v in form["buff"].items() if v > 0)
        txt = (f"{row['char_name']} - Transform\n"
               f"{'='*22}\n"
               f"Form: {form['name']}\n"
               f"Required Chakra: {form['req_chakra']:,}\n"
               f"Buffs: {buffs if buffs else 'Stat Boost'}\n\n"
               f"Cost: 1 Transform Stone")
        await _safe_edit(q, txt, back_kb)

    elif action == "beast":
        tb_name = cd.get("tailed_beast")
        if not tb_name or tb_name not in BEASTS:
            await q.answer("No tailed beast!", show_alert=True); return
        bi   = BEASTS[tb_name]
        user = await db_get(uid)
        caught = tb_name in list(user.get("caught_beasts") or [])
        txt = (f"{row['char_name']} - Tailed Beast\n"
               f"{'='*22}\n"
               f"Beast: {tb_name}\n"
               f"Tails: {bi['tails']}\n"
               f"Ability: {bi['ability']}\n"
               f"Status: {'Caught - Bijuu Mode Available' if caught else 'Not caught yet - defeat it in explore'}\n"
               f"Power Rating: {bi['power']}")
        await _safe_edit(q, txt, back_kb)

    elif action == "more":
        nat      = cd["nature"]
        adv_info = ADV.get(nat, {})
        weak     = adv_info.get("w", [])
        kg       = CLAN_KG.get(cd["clan"], "None")
        ki       = KG.get(kg, KG["None"])
        lv       = row["level"]
        hp = calc_stat(cd["base"]["hp"],   row["pp_hp"],  lv)
        at = calc_stat(cd["base"]["atk"],  row["pp_atk"], lv)
        df = calc_stat(cd["base"]["def"],  row["pp_def"],  lv)
        sp = calc_stat(cd["base"]["speed"],row["pp_spd"], lv)
        ch = cd["base"]["chakra"] + row["pp_cha"] * 2
        txt = (f"{row['char_name']} - Full Details\n"
               f"{'='*22}\n"
               f"Rarity: {cd['rarity']}\n"
               f"Village: {cd['village']}\n"
               f"Clan: {cd['clan'] or 'None'}\n"
               f"Kekkei Genkai: {kg}\n\n"
               f"Stats at Lv.{lv}:\n"
               f"  HP:  {hp}\n"
               f"  ATK: {at}\n"
               f"  DEF: {df}\n"
               f"  SPD: {sp}\n"
               f"  CHK: {ch}\n\n"
               f"Weakness: {', '.join(weak) if weak else 'None'}\n"
               f"KG Effect: {ki['desc']}")
        await _safe_edit(q, txt[:4000], back_kb)

    elif action == "back":
        lv             = row["level"]
        cexp           = row.get("exp", 0)
        char_lv_needed = int(80 * (lv ** 1.4))
        kg             = CLAN_KG.get(cd["clan"], "None")
        ki             = KG.get(kg, KG["None"])
        if kg != "None":
            ability_txt = ki["desc"]
        else:
            ability_txt = (f"{row['char_name']} is a {cd['nature']} nature shinobi from {cd['village']} "
                           f"with mastery in {cd['nature']} style jutsu and exceptional combat skills.")
        user        = await db_get(uid)
        ew          = get_weapon_by_id(user.get("equipped_weapon")) if user.get("equipped_weapon") else None
        weapon_name = ew["name"] if ew else "None"
        total_pp    = (row.get("pp_hp",0)+row.get("pp_atk",0)+row.get("pp_def",0)
                       +row.get("pp_spd",0)+row.get("pp_cha",0))
        awakening_lv = total_pp // 5
        txt = (f"Shinobi Info\n"
               f"Shinobi: {row['char_name']}\n"
               f"Ability: {ability_txt}\n\n"
               f"Level: {lv}\n"
               f"Exp: {cexp} / {char_lv_needed}\n"
               f"Chakra: {user['chakra']:,} / 60000\n"
               f"Awakening Level: {awakening_lv}\n"
               f"Main Nature: {cd['nature']}\n"
               f"Equipped Weapon: {weapon_name}")
        kb   = [[Btn("Moves", callback_data=f"info:moves:{cid}"),
                 Btn("Advantage", callback_data=f"info:adv:{cid}")]]
        row2 = []
        if cd.get("form"):
            row2.append(Btn("Transform", callback_data=f"info:tf:{cid}"))
        if cd.get("tailed_beast"):
            row2.append(Btn("Beast", callback_data=f"info:beast:{cid}"))
        if row2:
            kb.append(row2)
        kb.append([Btn("More Info", callback_data=f"info:more:{cid}")])
        await _safe_edit(q, txt, kb)


# ─── /stats ─────────────────────────────────────────────────────
async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid  = str(update.effective_user.id)
    args = ctx.args
    if args:
        # Search by character name
        query = " ".join(args).lower()
        found = next((c for c in CHARACTERS if query in c["name"].lower()), None)
        if not found:
            await update.message.reply_text(
                f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Character '{' '.join(args)}' not found!\nTry /stats Naruto"); return
        kg = CLAN_KG.get(found["clan"],"None"); ki = KG.get(kg,KG["None"])
        rr = RAR.get(found["rarity"],"⚪")
        form=found.get("form",{}); tb=found.get("tailed_beast")
        tb_i=BEASTS.get(tb) if tb else None
        txt=(
            f"{rr} <b>{found['name']}</b> ⟨{found['rarity']}⟩\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<tg-emoji emoji-id='5426872512015244606'>🌿</tg-emoji> {found['nature']} {nat_icon(found['nature'])} | <tg-emoji emoji-id='5427342518876381603'>🏘️</tg-emoji> {found['village']} | <tg-emoji emoji-id='5224388744156557558'>🧬</tg-emoji> {found['clan']}\n"
            f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>KG: {kg}</b>\n<i>{ki['desc']}</i>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<tg-emoji emoji-id='5427095369278299187'>❤️</tg-emoji> HP  {found['base']['hp']:>5}\n"
            f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> ATK {found['base']['atk']:>5}\n"
            f"<tg-emoji emoji-id='6039727447090403055'>🛡️</tg-emoji> DEF {found['base']['def']:>5}\n"
            f"💨 SPD {found['base']['speed']:>5}\n"
            f"<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> CHK {found['base']['chakra']:>5}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
        if form:
            bs=" | ".join(f"{k.upper()}+{v}" for k,v in form["buff"].items() if v>0)
            txt+=f"<tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji> <b>Form:</b> {form['name']}\n  Req: {form['req_chakra']:,} Chakra\n  Buffs: {bs}\n"
        if tb_i:
            txt+=f"\n<tg-emoji emoji-id='6003600664687546316'>🦊</tg-emoji> <b>{tb}</b> ({tb_i['tails']} tails)\n_{tb_i['ability']}_\n"
        # Move list
        txt+="\n<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> <b>Moveset:</b>\n"
        for m in found["moves"]:
            txt+=f"  • <b>{m['name']}</b> {nat_icon(m['type'])} <tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji>{m['power']} <tg-emoji emoji-id='5427397421443325675'>🎯</tg-emoji>{m['acc']}%\n"
        photo = PHOTO_CACHE.get(found["name"])
        if photo:
            try:
                await update.message.reply_photo(
                    photo=photo, caption=txt[:1020],
                    parse_mode="HTML"); return
            except: pass
        await update.message.reply_text(txt, parse_mode="HTML"); return

    # Show your own chars list with STATS_BANNER
    chars = await db_chars(uid)
    if not chars: await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> No characters!"); return
    kb=[[Btn(f"{c['char_name'][:26]} Lv.{c['level']}",
             callback_data=f"sv:{c['id']}")] for c in chars[:20]]
    stats_txt = "<tg-emoji emoji-id='5981204549132619885'>📊</tg-emoji> <b>Your Characters</b>\nSelect one to view stats &amp; level up:"
    banner = _get_banner(STATS_BANNER)
    print(f"🔍 cmd_stats: banner type={type(banner).__name__}")
    sent_photo = False
    for pm in ("HTML", None):
        try:
            if hasattr(banner, "seek"):
                banner.seek(0)
            await update.message.reply_photo(photo=banner, caption=stats_txt,
                parse_mode=pm, reply_markup=Kbd(kb))
            sent_photo = True
            break
        except Exception as e:
            pass
    if not sent_photo:
        await update.message.reply_text(stats_txt, parse_mode="HTML",
                                        reply_markup=Kbd(kb))

async def cb_stats_view(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    uid=str(q.from_user.id); cid=int(q.data.split(":")[1])
    row = _cdoc(await chars_col.find_one({"_id": cid, "uid": uid}))
    if not row: return
    cd=get_cdata(row["char_name"])
    if not cd: return
    kg=CLAN_KG.get(cd["clan"],"None"); uid_owner=row["uid"]
    lv=row["level"]
    hp=calc_stat(cd["base"]["hp"],   row["pp_hp"],  lv)
    at=calc_stat(cd["base"]["atk"],  row["pp_atk"], lv)
    df=calc_stat(cd["base"]["def"],   row["pp_def"],  lv)
    sp=calc_stat(cd["base"]["speed"],row["pp_spd"], lv)
    ch=cd["base"]["chakra"]+row["pp_cha"]*2
    tp=row["pp_hp"]+row["pp_atk"]+row["pp_def"]+row["pp_spd"]+row["pp_cha"]
    tb=cd.get("tailed_beast"); tb_i=BEASTS.get(tb) if tb else None
    form=cd.get("form",{})
    rr=RAR.get(cd["rarity"],"⚪")
    # NOTE: Telegram Markdown V1 uses *bold* (single asterisk), NOT **bold**.
    # Double asterisks cause "Can't parse entities" errors that silently break edits.
    def _stat_bar(val, max_val=1000, length=10):
        filled = min(length, int(val / max_val * length))
        return "█" * filled + "░" * (length - filled)
    hp_bar_s  = _stat_bar(hp,  1000)
    atk_bar_s = _stat_bar(at,  800)
    def_bar_s = _stat_bar(df,  800)
    spd_bar_s = _stat_bar(sp,  600)
    chk_bar_s = _stat_bar(ch,  600)
    txt=(f"<tg-emoji emoji-id='5981204549132619885'>📊</tg-emoji> {rr} <b>{row['char_name']}</b> Lv.{lv}/100\n━━━━━━━━━━━━━━━━━━━━\n"
         f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> KG: <b>{kg}</b>\n<i>{KG.get(kg,KG['None'])['desc'][:45]}</i>\n\n"
         f"<tg-emoji emoji-id='5427095369278299187'>❤️</tg-emoji> HP:  <b>{hp}</b>  <code>{hp_bar_s}</code> [PP:{row['pp_hp']:02d} {pp_grade(row['pp_hp'])}]\n"
         f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> ATK: <b>{at}</b>  <code>{atk_bar_s}</code> [PP:{row['pp_atk']:02d} {pp_grade(row['pp_atk'])}]\n"
         f"<tg-emoji emoji-id='6039727447090403055'>🛡️</tg-emoji> DEF: <b>{df}</b>  <code>{def_bar_s}</code> [PP:{row['pp_def']:02d} {pp_grade(row['pp_def'])}]\n"
         f"💨 SPD: <b>{sp}</b>  <code>{spd_bar_s}</code> [PP:{row['pp_spd']:02d} {pp_grade(row['pp_spd'])}]\n"
         f"<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> CHK: <b>{ch}</b>  <code>{chk_bar_s}</code> [PP:{row['pp_cha']:02d} {pp_grade(row['pp_cha'])}]\n"
         f"<tg-emoji emoji-id='5981204549132619885'>📊</tg-emoji> Total PP: {tp}/155 ({int(tp/155*100)}%)\n")
    if form:
        bs=" | ".join(f"{k.upper()}+{v}" for k,v in form["buff"].items() if v>0)
        txt+=f"\n<tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji> <b>Form:</b> {form['name']}\n  Req: {form['req_chakra']:,}<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> | {bs}\n"
    if tb_i:
        txt+=f"\n<tg-emoji emoji-id='6003600664687546316'>🦊</tg-emoji> <b>{tb}</b> ({tb_i['tails']}<tg-emoji emoji-id='6003600664687546316'>🦊</tg-emoji>)\n_{tb_i['ability']}_"
    kb=[
        [Btn("Level Up",callback_data=f"lv:{cid}:{uid}"),
         Btn("Moves",callback_data=f"mv:{cid}")],
        [Btn("Save Team",callback_data=f"tm:addch:{cid}"),
         Btn("Train",callback_data=f"tr:pick:{cid}")],
        [Btn("Relearn",callback_data=f"rl:menu:{cid}"),
         Btn("Release",callback_data=f"mc:{cid}:release")],
        [Btn("Back to List",callback_data="cmd:stats")]
    ]
    caption = txt[:1020]
    markup = Kbd(kb)
    # Always send a fresh reply so photo shows AND buttons always work
    photo_url = best_char_photo(row["char_name"])
    if photo_url:
        try:
            await q.message.reply_photo(photo=photo_url, caption=caption,
                                        parse_mode="HTML", reply_markup=markup)
            return
        except Exception:
            pass
    # Fallback: text reply
    try:
        await q.message.reply_text(caption, parse_mode="HTML", reply_markup=markup)
    except Exception:
        pass

# ─── WIN IMAGE HELPER ───────────────────────────────────────────
async def make_pvp_win_image(bot, winner_uid: str, char_photo_url):
    """Composite winner's Telegram DP + winning char photo side by side."""
    if not PIL_AVAILABLE:
        return None
    try:
        SIZE = (400, 220)
        HALF = (200, 220)
        base = Image.new("RGB", SIZE, (20, 20, 40))

        def load_img(data: bytes) -> Image.Image:
            return Image.open(io.BytesIO(data)).convert("RGB").resize(HALF, Image.LANCZOS)

        # Left: user profile photo
        try:
            photos = await bot.get_user_profile_photos(int(winner_uid), limit=1)
            if photos and photos.photos:
                file = await bot.get_file(photos.photos[0][-1].file_id)
                buf = io.BytesIO()
                await file.download_to_memory(buf)
                buf.seek(0)
                left = load_img(buf.read())
                base.paste(left, (0, 0))
        except Exception:
            pass

        # Right: character photo
        if char_photo_url:
            try:
                if char_photo_url.startswith("http"):
                    with urllib.request.urlopen(char_photo_url, timeout=5) as r:
                        right = load_img(r.read())
                else:
                    with open(char_photo_url, "rb") as f:
                        right = load_img(f.read())
                base.paste(right, (200, 0))
            except Exception:
                pass

        # Divider line + trophy text
        draw = ImageDraw.Draw(base)
        draw.line([(199, 0), (199, 220)], fill=(255, 215, 0), width=3)
        try:
            fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        except Exception:
            fnt = ImageFont.load_default()
        draw.text((130, 4), "<tg-emoji emoji-id='5426976939850080222'>🏆</tg-emoji> VS", fill=(255, 215, 0), font=fnt)

        out = io.BytesIO()
        base.save(out, format="JPEG", quality=85)
        out.seek(0)
        return out
    except Exception:
        return None

# ─── /nickname ──────────────────────────────────────────────────
async def cmd_nickname(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid  = str(update.effective_user.id)
    args = ctx.args
    if not args:
        await update.message.reply_text(
            "✏️ *Set Nickname:*\nUsage: `/nickname YourName`\n"
            "<i>Max 20 chars. Costs 0 NC (first time free!)</i>",
            parse_mode="HTML"); return
    nick = " ".join(args)[:20]
    if len(nick) < 2:
        await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Nickname too short (min 2 chars)!"); return
    await db_set(uid, nickname=nick)
    await update.message.reply_text(
        f"✏️ <b>Nickname set to:</b> <code>{nick}</code>\nShown in /start and profile!",
        parse_mode="HTML")

# ─── /shop ──────────────────────────────────────────────────────
def _shop_page_txt(user, page):
    total_pages = (len(SHOP) + SHOP_PAGE_SIZE - 1) // SHOP_PAGE_SIZE
    start = page * SHOP_PAGE_SIZE
    items = SHOP[start:start + SHOP_PAGE_SIZE]
    txt  = (f"🛒 <b>Ninja Shop</b> — Page {page+1}/{total_pages}\n"
            f"<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> Balance: <b>{user['coins']:,} NC</b> | <tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji> Stones: {user.get('stones',0)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n")
    for item in items:
        ok = "<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji>" if user["coins"] >= item["price"] else "<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji>"
        txt += f"{item['emoji']} <b>{item['name']}</b> — <b>{item['price']:,} NC</b> {ok}\n<i>{item['desc']}</i>\n\n"
    txt += "━━━━━━━━━━━━━━━━━━━━"
    return txt

def _shop_page_kb(page, uid):
    total_pages = (len(SHOP) + SHOP_PAGE_SIZE - 1) // SHOP_PAGE_SIZE
    start = page * SHOP_PAGE_SIZE
    items = SHOP[start:start + SHOP_PAGE_SIZE]
    kb = []
    for item in items:
        kb.append([Btn(f"Buy: {item['name']} ({item['price']:,} NC)", callback_data=f"sh:buy:{item['id']}:{uid}")])
    nav = []
    if page > 0:          nav.append(Btn("Back",   callback_data=f"sp:{page-1}:{uid}"))
    if page < total_pages-1: nav.append(Btn("Next",callback_data=f"sp:{page+1}:{uid}"))
    if nav: kb.append(nav)
    kb.append([Btn("Weapon Shop",callback_data=f"wp:page:0:{uid}"),
               Btn("Inventory",callback_data=f"inv:view:{uid}")])
    return kb

def _weapon_shop_txt(uid: str, user: dict) -> str:
    weapons = get_user_weapon_shop(uid)
    txt = (f"⚔️ <b>Weapon Shop</b> — Daily Selection\n"
           f"Balance: {pe('coin')} <b>{user['coins']:,} NC</b>\n"
           f"<i>Each user sees 5 different weapons daily.</i>\n"
           f"━━━━━━━━━━━━━━━━━━━━\n\n")
    for w in weapons:
        owned = w["id"] in (user.get("weapons") or [])
        equipped = user.get("equipped_weapon") == w["id"]
        status = " <b>[Equipped]</b>" if equipped else (" <i>[Owned]</i>" if owned else "")
        ok = "✅" if user["coins"] >= w["price"] else "❌"
        txt += (f"{ok} <b>{hesc(w['name'])}</b> [{hesc(w['rarity'])}]{status} — <b>{w['price']:,} NC</b>\n"
                f"  ATK +{w['atk']} | {hesc(w['ability'])}\n"
                f"  <i>{hesc(w['desc'])}</i>\n"
                f"\n")
    txt += "━━━━━━━━━━━━━━━━━━━━"
    return txt

def _weapon_shop_kb(uid: str, user: dict) -> list:
    weapons = get_user_weapon_shop(uid)
    kb = []
    for w in weapons:
        owned = w["id"] in (user.get("weapons") or [])
        label = f"{'Owned: ' if owned else 'Buy: '}{w['name']} {w['price']:,}NC"
        kb.append([Btn(label, callback_data=f"wp:buy:{w['id']}:{uid}")])
    kb.append([Btn("Back to Shop", callback_data=f"sp:0:{uid}"),
               Btn("My Weapons", callback_data=f"wp:myweapons:{uid}")])
    return kb

async def cmd_shop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid  = str(update.effective_user.id)
    user = await db_get(uid)
    page = 0
    txt  = _shop_page_txt(user, page)
    kb   = _shop_page_kb(page, uid)
    try:
        await update.message.reply_photo(
            photo=SHOP_BANNER, caption=txt[:1020],
            parse_mode="HTML", reply_markup=Kbd(kb))
    except:
        await update.message.reply_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))

async def cb_shop_page(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts = q.data.split(":"); page = int(parts[1]); uid = parts[2]
    if str(q.from_user.id) != uid: await q.answer("Not yours!", show_alert=True); return
    user = await db_get(uid)
    txt  = _shop_page_txt(user, page)
    kb   = _shop_page_kb(page, uid)
    is_photo = bool(q.message and q.message.photo)
    try:
        if is_photo: await q.edit_message_caption(caption=txt[:1020], parse_mode="HTML", reply_markup=Kbd(kb))
        else: await q.edit_message_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))
    except: pass

async def cb_weapon_shop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle wp: callbacks for weapon shop."""
    q = update.callback_query; await q.answer()
    parts = q.data.split(":")
    action = parts[1]; uid = parts[-1]
    if str(q.from_user.id) != uid:
        await q.answer("Not yours!", show_alert=True); return
    user = await db_get(uid)
    if not user: return
    if action == "page":
        txt = _weapon_shop_txt(uid, user)
        kb  = _weapon_shop_kb(uid, user)
        try:
            is_photo = bool(q.message and q.message.photo)
            if is_photo: await q.edit_message_caption(caption=txt[:1020], parse_mode="HTML", reply_markup=Kbd(kb))
            else: await q.edit_message_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))
        except: pass
    elif action == "buy":
        wid = parts[2]
        weapon = get_weapon_by_id(wid)
        if not weapon:
            await q.answer("Weapon not found!", show_alert=True); return
        cur_weapons = list(user.get("weapons") or [])
        if wid in cur_weapons:
            await q.answer("You already own this weapon!", show_alert=True); return
        if user["coins"] < weapon["price"]:
            await q.answer(f"Need {weapon['price']:,} NC!", show_alert=True); return
        cur_weapons.append(wid)
        await db_set(uid, coins=user["coins"]-weapon["price"], weapons=cur_weapons)
        await q.answer(f"Bought {weapon['name']}! Use /equip {wid}", show_alert=True)
        user = await db_get(uid)
        txt = _weapon_shop_txt(uid, user)
        kb  = _weapon_shop_kb(uid, user)
        try:
            is_photo = bool(q.message and q.message.photo)
            if is_photo: await q.edit_message_caption(caption=txt[:1020], parse_mode="HTML", reply_markup=Kbd(kb))
            else: await q.edit_message_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))
        except: pass
    elif action == "myweapons":
        cur_weapons = list(user.get("weapons") or [])
        if not cur_weapons:
            await q.answer("No weapons in inventory! Buy from the shop or find in explore.", show_alert=True); return
        equipped_id = user.get("equipped_weapon")
        lines = []
        for wid in cur_weapons:
            w = get_weapon_by_id(wid)
            if w:
                eq_tag = " <b>[Equipped]</b>" if wid == equipped_id else ""
                lines.append(f"⚔️ <b>{hesc(w['name'])}</b> [{hesc(w['rarity'])}]{eq_tag}\n  ATK +{w['atk']} | {hesc(w['ability'])}")
        txt = "⚔️ <b>My Weapons</b>\n━━━━━━━━━━━━━━━━━━━━\n\n" + "\n\n".join(lines)
        txt += "\n\n<i>Use <code>/equip &lt;weapon_id&gt;</code> to equip a weapon.</i>"
        kb = [[Btn("Back to Weapon Shop", callback_data=f"wp:page:0:{uid}")]]
        try:
            is_photo = bool(q.message and q.message.photo)
            if is_photo: await q.edit_message_caption(caption=txt[:1020], parse_mode="HTML", reply_markup=Kbd(kb))
            else: await q.edit_message_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))
        except: pass

async def cmd_buy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid  = str(update.effective_user.id)
    args = ctx.args
    if not args:
        await update.message.reply_text(
            "💡 Usage: `/buy <item_id>`\nCheck /shop for item IDs",
            parse_mode="HTML"); return
    item_id = args[0].lower()
    item = next((i for i in SHOP if i["id"]==item_id), None)
    if not item:
        await update.message.reply_text(
            f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Unknown item <code>{item_id}</code>\nCheck /shop for valid IDs",
            parse_mode="HTML"); return
    user = await db_get(uid)
    if user["coins"] < item["price"]:
        await update.message.reply_text(
            f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Need <b>{item['price']:,} NC</b> — you have <b>{user['coins']:,} NC</b>",
            parse_mode="HTML"); return
    await db_set(uid, coins=user["coins"]-item["price"])
    user = await db_get(uid)
    if item["type"]=="item":
        if item_id=="heal":
            await update.message.reply_text("<tg-emoji emoji-id='5427095369278299187'>💊</tg-emoji> <b>All characters healed!</b> Ready for battle!",
                                            parse_mode="HTML")
        elif item_id=="chakra_pill":
            await db_set(uid, chakra=user["chakra"]+300)
            await update.message.reply_text("<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> <b>+300 Chakra!</b>",parse_mode="HTML")
        elif item_id=="super_heal":
            await db_set(uid, chakra=user["chakra"]+500)
            await update.message.reply_text("<tg-emoji emoji-id='5426872512015244606'>🌿</tg-emoji> <b>All healed + 500 Chakra!</b>",parse_mode="HTML")
        elif item_id=="exp_boost":
            await db_set(uid, exp_boost=1)
            await update.message.reply_text("📜 *2x EXP Boost active for 5 battles!*",
                                            parse_mode="HTML")
        elif item_id=="stone":
            await db_set(uid, stones=user.get("stones",0)+1)
            await update.message.reply_text(
                f"<tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji> <b>Transform Stone acquired!</b>\n"
                f"Total Stones: {user.get('stones',0)+1}\n"
                f"Use in battle when chakra is full!",
                parse_mode="HTML")
        elif item_id=="chakra_crystal":
            await db_set(uid, chakra=user["chakra"]+1000)
            await update.message.reply_text("<tg-emoji emoji-id='5454122580564786042'>💎</tg-emoji> <b>+1000 Chakra!</b> Crystal absorbed!",parse_mode="HTML")
        elif item_id=="antidote":
            await db_set(uid, antidote=1)
            await update.message.reply_text("🧪 <b>Antidote ready!</b> All status effects will be cleared in next battle.",parse_mode="HTML")
        elif item_id=="battle_seal":
            await db_set(uid, battle_seal=1)
            await update.message.reply_text("🔖 <b>Battle Seal active!</b> +10% all stats for next battle.",parse_mode="HTML")
        elif item_id=="lucky_charm":
            await db_set(uid, lucky_charm=3)
            await update.message.reply_text("🍀 <b>Lucky Charm active!</b> Triple stone drop rate for 3 battles!",parse_mode="HTML")
        elif item_id=="double_nc":
            await db_set(uid, double_nc=3)
            await update.message.reply_text("<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> <b>NC Multiplier active!</b> Double NC from next 3 explore wins!",parse_mode="HTML")
        elif item_id=="mega_exp":
            await db_set(uid, mega_exp=1)
            await update.message.reply_text("📚 <b>Mega EXP Scroll active!</b> 5x EXP for next battle!",parse_mode="HTML")
        elif item_id=="rebirth_token":
            chars=await db_chars(uid)
            if not chars:
                await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> No characters to use token on!"); return
            kb=[[Btn(f"{c['char_name'][:25]} Lv.{c['level']}",callback_data=f"rbtk:{c['id']}")] for c in chars[:10]]
            await update.message.reply_text(
                "<tg-emoji emoji-id='5424892463372312872'>🌟</tg-emoji> <b>Rebirth Token!</b>\nSelect character to grant +10 levels:",
                parse_mode="HTML", reply_markup=Kbd(kb))
            return
        elif item_id=="rename":
            await update.message.reply_text(
                "✏️ *Rename token granted!*\nUse `/nickname <name>` to set your nickname!",
                parse_mode="HTML")
        elif item_id=="clan_reset":
            await db_set(uid, clan="")
            await update.message.reply_text(
                "<tg-emoji emoji-id='5224388744156557558'>🧬</tg-emoji> <b>Clan Reset!</b> Your clan has been cleared.\nUse <code>/clan</code> to pick a new one!",
                parse_mode="HTML")
        elif item_id=="village_vip":
            await update.message.reply_text("<tg-emoji emoji-id='5424767857781122187'>🏅</tg-emoji> <b>Village VIP Pass active!</b> +20% all village bonuses for 10 battles!",parse_mode="HTML")
        else:
            await update.message.reply_text(f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> {item['name']} purchased!",
                                            parse_mode="HTML")
    elif item["type"]=="summon":
        rm={"rare_scroll":"Rare","epic_scroll":"Epic","legendary_scroll":"Legendary","mythic_scroll":"Mythic"}
        tar=rm.get(item_id); pulled=gacha_guaranteed(tar) if tar else gacha_pull()
        await db_add_char(uid, pulled["name"])
        rr=RAR.get(pulled["rarity"],"⚪"); kg=CLAN_KG.get(pulled["clan"],"None")
        ki=KG.get(kg,KG["None"]); tb=pulled.get("tailed_beast","")
        txt=(f"<tg-emoji emoji-id='5424892463372312872'>🌟</tg-emoji> <b>Scroll Summon!</b>\n{rr} <b>{pulled['name']}</b> ⟨{pulled['rarity']}⟩\n"
             f"<tg-emoji emoji-id='5426872512015244606'>🌿</tg-emoji> {pulled['nature']} {nat_icon(pulled['nature'])} | <tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>{kg}</b>\n"
             f"<i>{hesc(ki['desc'][:50])}</i>"
             + (f"\n{pe('bijuu')} <b>{hesc(tb)}</b>" if tb else "")
             + "\n✅ Added to collection!")
        photo = PHOTO_CACHE.get(pulled["name"]) or pulled.get("photo")
        if photo:
            try:
                await update.message.reply_photo(photo=photo,caption=txt[:1020],
                    parse_mode="HTML"); return
            except: pass
        await update.message.reply_text(txt,parse_mode="HTML")

async def _do_shop_buy(uid: str, item_id: str, user: dict, reply_fn):
    """Shared buy logic for /buy command and inline shop buttons."""
    item = next((i for i in SHOP if i["id"] == item_id), None)
    if not item:
        await reply_fn(f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Unknown item <code>{item_id}</code>",
                       parse_mode="HTML")
        return False
    if user["coins"] < item["price"]:
        await reply_fn(
            f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Need <b>{item['price']:,} NC</b> — you have <b>{user['coins']:,} NC</b>",
            parse_mode="HTML")
        return False
    return True

async def cb_shop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    parts=q.data.split(":")
    uid=str(q.from_user.id); user=await db_get(uid)
    # sh:buy:item_id:uid — inline buy from shop page button
    if len(parts)==4 and parts[1]=="buy":
        item_id=parts[2]
        item=next((i for i in SHOP if i["id"]==item_id),None)
        if not item: await q.answer("Item not found!",show_alert=True); return
        if user["coins"]<item["price"]:
            await q.answer(f"Need {item['price']:,} NC! You have {user['coins']:,} NC.",show_alert=True); return
        await db_set(uid,coins=user["coins"]-item["price"])
        await q.answer(f"Bought {item['name']}! Check /inventory.",show_alert=True)
        try:
            await q.message.reply_text(
                f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> You bought <b>{hesc(item['name'])}</b>!\n"
                f"<i>Check /inventory to use it.</i>",
                parse_mode="HTML")
        except Exception: pass
        user=await db_get(uid); page=0
        txt=_shop_page_txt(user,page); kb=_shop_page_kb(page,uid)
        is_photo=bool(q.message and q.message.photo)
        try:
            if is_photo: await q.edit_message_caption(caption=txt[:1020],parse_mode="HTML",reply_markup=Kbd(kb))
            else: await q.edit_message_text(txt,parse_mode="HTML",reply_markup=Kbd(kb))
        except: pass
        return
    _,action,item_id=q.data.split(":")
    item=next((i for i in SHOP if i["id"]==item_id),None)
    if not item: return
    if user["coins"]<item["price"]:
        await q.answer(f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Need {item['price']:,} NC!",show_alert=True); return
    await q.answer(f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> Item info shown below!",show_alert=True)

# ─── /summon ────────────────────────────────────────────────────
async def cmd_summon(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid=str(update.effective_user.id); user=await db_get(uid)
    rates="\n".join(f"  {RAR.get(r,'⚪')} {r}: {int(p*100)}%" for r,p in RAR_RATES.items())
    kb=[[Btn("Single (500 NC)",callback_data=f"sm:s:{uid}"),
         Btn("10x (4500 NC)",callback_data=f"sm:m:{uid}")],
        [Btn("Epic (10000 NC)",callback_data=f"sm:e:{uid}"),
         Btn("Legendary (25000 NC)",callback_data=f"sm:l:{uid}")]]
    caption=(f"<tg-emoji emoji-id='5426957509418031897'>🌀</tg-emoji> <b>Ninja Scroll Summon</b>\n━━━━━━━━━━━━━━━━━━━━\n"
             f"<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> Balance: <b>{user['coins']:,} NC</b>\n\n"
             f"<tg-emoji emoji-id='5981204549132619885'>📊</tg-emoji> <b>Pull Rates:</b>\n{rates}\n\n"
             f"_Summon is the ONLY way to get characters!_")
    try:
        await update.message.reply_photo(photo=SUMMON_BANNER, caption=caption[:1020],
                                         parse_mode="HTML", reply_markup=Kbd(kb))
    except Exception:
        await update.message.reply_text(caption, parse_mode="HTML", reply_markup=Kbd(kb))

async def cb_summon(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    parts=q.data.split(":"); mode=parts[1]; uid=parts[2]
    if str(q.from_user.id)!=uid: await q.answer("Not yours!",show_alert=True); return
    user=await db_get(uid)
    costs={"s":500,"m":4500,"e":10000,"l":25000}
    cost=costs.get(mode,500)
    if user["coins"]<cost: await q.answer(f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Need {cost:,} NC!",show_alert=True); return
    await db_set(uid,coins=user["coins"]-cost)
    if mode=="s": pulled=[gacha_pull()]
    elif mode=="m": pulled=[gacha_pull() for _ in range(10)]
    elif mode=="e": pulled=[gacha_guaranteed("Epic")]
    elif mode=="l": pulled=[gacha_guaranteed("Legendary")]
    else: pulled=[gacha_pull()]
    for p in pulled: await db_add_char(uid,p["name"])

    is_photo_msg = bool(q.message and q.message.photo)

    if len(pulled)==1:
        p=pulled[0]; rr=RAR.get(p["rarity"],"⚪"); kg=CLAN_KG.get(p["clan"],"None")
        ki=KG.get(kg,KG["None"]); tb=p.get("tailed_beast","")

        # ── SUMMON ANIMATION ─────────────────────────────────────────
        frames = [
            "<tg-emoji emoji-id='5426957509418031897'>🌀</tg-emoji> <b>Channeling chakra...</b>",
            "<tg-emoji emoji-id='5426957509418031897'>🌀</tg-emoji><tg-emoji emoji-id='5426957509418031897'>🌀</tg-emoji> <b>The scroll begins to glow!</b>",
            "✨<tg-emoji emoji-id='5426957509418031897'>🌀</tg-emoji>✨ <b>A ninja appears from the seal!</b>",
            f"<tg-emoji emoji-id='5424892463372312872'>💫</tg-emoji> <b>Summoning complete!</b>\n\n_Revealing..._",
        ]
        for frame in frames:
            try:
                if is_photo_msg:
                    await q.edit_message_caption(caption=frame, parse_mode="HTML")
                else:
                    await q.edit_message_text(frame, parse_mode="HTML")
            except Exception: pass
            await asyncio.sleep(0.7)

        # ── REVEAL ───────────────────────────────────────────────────
        txt=(f"<tg-emoji emoji-id='5424892463372312872'>🌟</tg-emoji> <b>Summon Result!</b>\n━━━━━━━━━━━━━━━━━━━━\n"
             f"{rr} <b>{hesc(p['name'])}</b> ⟨{hesc(p['rarity'])}⟩\n"
             f"<tg-emoji emoji-id='5426872512015244606'>🌿</tg-emoji> {hesc(p['nature'])} {nat_icon(p['nature'])} | <tg-emoji emoji-id='5427342518876381603'>🏘️</tg-emoji> {hesc(p['village'])}\n"
             f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> KG: <b>{hesc(kg)}</b> — <i>{hesc(ki['desc'][:50])}</i>"
             + (f"\n{pe('bijuu')} <b>{hesc(tb)}</b>" if tb else "")
             + "\n\n✅ Added to your roster!")
        photo = PHOTO_CACHE.get(p["name"]) or p.get("photo")
        if photo:
            try:
                if is_photo_msg:
                    await q.edit_message_media(
                        media=InputMediaPhoto(media=photo, caption=txt[:1020], parse_mode="HTML"))
                else:
                    await q.message.reply_photo(photo=photo, caption=txt[:1020], parse_mode="HTML")
                    try: await q.message.delete()
                    except: pass
                return
            except Exception: pass
        try:
            if is_photo_msg:
                await q.edit_message_caption(caption=txt[:1020], parse_mode="HTML")
            else:
                await q.edit_message_text(txt, parse_mode="HTML")
        except Exception: pass
    else:
        # ── MULTI SUMMON ANIMATION ───────────────────────────────────
        multi_frames = [
            "<tg-emoji emoji-id='5426957509418031897'>🌀</tg-emoji> <b>Channeling chakra...</b>",
            "<tg-emoji emoji-id='5426957509418031897'>🌀</tg-emoji><tg-emoji emoji-id='5426957509418031897'>🌀</tg-emoji><tg-emoji emoji-id='5426957509418031897'>🌀</tg-emoji> <b>10 scrolls unroll!</b>",
            "✨<tg-emoji emoji-id='5424892463372312872'>💫</tg-emoji>✨ <b>Ninjas pour forth from the seals!</b>",
        ]
        for frame in multi_frames:
            try:
                if is_photo_msg:
                    await q.edit_message_caption(caption=frame, parse_mode="HTML")
                else:
                    await q.edit_message_text(frame, parse_mode="HTML")
            except Exception: pass
            await asyncio.sleep(0.7)

        lines=[f"{RAR.get(p['rarity'],'⚪')} <b>{p['name']}</b> ⟨{p['rarity']}⟩ {nat_icon(p['nature'])}" for p in pulled]
        result_txt = f"<tg-emoji emoji-id='5424892463372312872'>🌟</tg-emoji> <b>10x Summon!</b>\n━━━━━━━━━━━━━━━━━━━━\n"+"\n".join(lines)+"\n\n<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> All added!"
        try:
            if is_photo_msg:
                await q.edit_message_caption(caption=result_txt[:1020], parse_mode="HTML")
            else:
                await q.edit_message_text(result_txt, parse_mode="HTML")
        except Exception: pass

# ─── /daily ─────────────────────────────────────────────────────
async def cmd_daily(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid=str(update.effective_user.id); user=await db_get(uid)
    now=datetime.utcnow()
    if user.get("daily_last",""):
        try:
            diff=(now-datetime.fromisoformat(user["daily_last"])).total_seconds()
            if diff<86400:
                h,m=divmod(int(86400-diff)//60,60)
                await update.message.reply_text(f"<tg-emoji emoji-id='5803204762035818905'>⏳</tg-emoji> Come back in <b>{h}h {m}m</b>!",
                                                parse_mode="HTML"); return
        except: pass
    streak=user.get("streak",0)+1
    cr=100
    ck=5
    await db_set(uid,coins=user["coins"]+cr,chakra=user["chakra"]+ck,
                 daily_last=now.isoformat(),streak=streak)
    kb=[[Btn("Summon",callback_data=f"sm:s:{uid}"),
         Btn("Explore",callback_data="menu:explore")]]
    if streak == 1:
        streak_msg = "Welcome back! Your training resumes."
    elif streak < 7:
        streak_msg = "Keep it up — every day sharpens your blade."
    elif streak < 14:
        streak_msg = "One week strong! The village notices your dedication."
    elif streak < 30:
        streak_msg = "Half a month of training! True shinobi dedication."
    elif streak < 60:
        streak_msg = f"A whole month straight! Jonin-level commitment!"
    else:
        streak_msg = f"Legendary! {streak} days straight — Hokage material!"
    import random as _dr; _daily_tips = [
        "Tip: Use /summon to expand your character roster!",
        "Tip: Complete your /mission for bonus NC today!",
        "Tip: Try /explore — wild shinobi lurk in the forest!",
        "Tip: Visit /shop to upgrade your weapons and gear!",
        "Tip: Challenge rivals with /battle!",
        "Tip: Use /forge to craft powerful Transform Stones!",
    ]
    _tip = _dr.choice(_daily_tips)
    await update.message.reply_text(
        f"🎁 <b>Daily Reward!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>{streak_msg}</i>\n\n"
        f"  {pe('coin')} +<b>{cr:,} NC</b> (Leaf Coins)\n"
        f"  {pe('chakra')} +<b>{ck} Chakra</b>\n"
        f"  {pe('fire')} Streak bonus: +<b>{streak*50} NC</b> for {streak} day{'s' if streak != 1 else ''} in a row!\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{pe('fire')} <b>Streak: {streak} day{'s' if streak != 1 else ''}</b>\n"
        f"<i>{_tip}</i>",
        parse_mode="HTML", reply_markup=Kbd(kb))

# ─── /mission ───────────────────────────────────────────────────
MISSIONS_POOL=[
    {"type":"Win 3 Explore Battles","target":3,"coins":200,"chakra":6},
    {"type":"Win 5 Explore Battles","target":5,"coins":200,"chakra":6},
    {"type":"Win 2 PvP Battles","target":2,"coins":200,"chakra":6},
    {"type":"Summon 3 Characters","target":3,"coins":200,"chakra":6},
    {"type":"Find 1 Transform Stone","target":1,"coins":200,"chakra":6},
]

async def cmd_mission(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid=str(update.effective_user.id); now=datetime.utcnow()
    missions_col = _mongo_db["missions"]
    m = await missions_col.find_one({"_id": uid})
    if m:
        try:
            if(now-datetime.fromisoformat(m["last_reset"])).total_seconds()<86400:
                done=m["progress"]>=m["target"]
                bar=hp_bar(m["progress"],m["target"])
                kb=[[Btn("Claim!",callback_data=f"ms:{uid}")]] if done else []
                await update.message.reply_text(
                    f"{pe('scroll')} <b>Daily Mission</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🎯 <b>Objective:</b> {hesc(m['mtype'])}\n"
                    f"{'<b>✅ COMPLETE!</b> Press below to claim your reward!' if done else f'Progress: {bar}'}\n\n"
                    f"<b>Reward on completion:</b>\n"
                    f"  {pe('coin')} <b>{m['r_coins']:,} NC</b>\n"
                    f"  {pe('chakra')} <b>{m['r_chakra']} Chakra</b>\n"
                    f"<i>Missions reset daily — complete it before midnight!</i>",
                    parse_mode="HTML",
                    reply_markup=Kbd(kb) if kb else None); return
        except: pass
    mt=random.choice(MISSIONS_POOL)
    await missions_col.replace_one({"_id": uid}, {
        "_id": uid, "mtype": mt["type"], "target": mt["target"],
        "progress": 0, "r_coins": mt["coins"], "r_chakra": mt["chakra"],
        "last_reset": now.isoformat()
    }, upsert=True)
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5426895906702107044'>📋</tg-emoji> <b>New Mission Assigned!</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5427397421443325675'>🎯</tg-emoji> <b>{mt['type']}</b>\nProgress: 0/{mt['target']}\n"
        f"Reward: <b>{mt['coins']:,} NC</b> + <b>{mt['chakra']}</b> {pe('chakra')}",
        parse_mode="HTML")

async def cb_mission(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    uid=q.data.split(":")[1]
    if str(q.from_user.id)!=uid: await q.answer("Not yours!",show_alert=True); return
    missions_col = _mongo_db["missions"]
    m = await missions_col.find_one({"_id": uid})
    if not m or m["progress"]<m["target"]: await q.answer("Not done!",show_alert=True); return
    user=await db_get(uid)
    _mission_nc = 200
    _mission_ck = random.randint(5, 7)
    await db_set(uid,coins=user["coins"]+_mission_nc,chakra=user["chakra"]+_mission_ck)
    await missions_col.update_one({"_id": uid}, {"$set": {"last_reset": "1970-01-01"}})
    await q.edit_message_text(
        f"<tg-emoji emoji-id='5424830993800373710'>🎁</tg-emoji> <b>Claimed!</b>\n+<b>{_mission_nc:,} NC</b> | +<b>{_mission_ck}</b><tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji>",
        parse_mode="HTML")

# ─── /travel ────────────────────────────────────────────────────
async def cmd_travel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid  = str(update.effective_user.id)
    user = await db_get(uid)
    vn   = user.get("village", "Konoha")
    vi   = VILLAGES.get(vn, {})
    vinfo= VILLAGE_INFO.get(vn, {})
    areas= VILLAGE_AREAS.get(vn, VILLAGE_AREAS["Konoha"])
    rows = []
    for i in range(0, len(areas), 2):
        row = []
        for j in range(2):
            if i + j < len(areas):
                a = areas[i + j]
                row.append(Btn(f"{a['emoji']} {a['name']}", callback_data=f"trv:{i+j}"))
        rows.append(row)
    rows.append([Btn("Change Village", callback_data="menu:village")])
    txt = (f"<tg-emoji emoji-id='5425114616260731920'>🗺️</tg-emoji> <b>Explore {vinfo.get('full', vn)}</b>\n"
           f"━━━━━━━━━━━━━━━━━━━━\n"
           f"{vi.get('emoji', pe('village'))} <i>{vinfo.get('country','')} — {vi.get('desc','')}</i>\n\n"
           f"Choose an area to explore. Each location offers different\n"
           f"enemies, rewards, and bonus multipliers!\n\n"
           f"<tg-emoji emoji-id='5427342518876381603'>📍</tg-emoji> <b>Available Areas:</b> {len(areas)}")
    try:
        await update.message.reply_photo(
            photo=VILLAGE_BANNER, caption=txt[:1020],
            parse_mode="HTML", reply_markup=Kbd(rows))
    except:
        await update.message.reply_text(txt, parse_mode="HTML", reply_markup=Kbd(rows))

async def cb_travel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle tapping an area in /travel — show area info and offer to explore there."""
    q   = update.callback_query; await q.answer()
    uid = str(q.from_user.id)
    user = await db_get(uid)
    vn  = user.get("village","Konoha")
    areas = VILLAGE_AREAS.get(vn, VILLAGE_AREAS["Konoha"])
    idx = int(q.data.split(":")[1])
    if idx >= len(areas):
        await q.answer("Unknown area!", show_alert=True); return
    area = areas[idx]
    bonus_label = {
        "exp":    "<tg-emoji emoji-id='5803416753031615097'>⬆️</tg-emoji> +{:.0f}% EXP from battles".format(area['bonus_val']*100),
        "nc":     "<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> +{:.0f}% NC from battles".format(area['bonus_val']*100),
        "chakra": "<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> +{:.0f}% Chakra gain".format(area['bonus_val']*100),
        "heal":   "<tg-emoji emoji-id='5427095369278299187'>💊</tg-emoji> Free HP restore before battle",
    }.get(area["bonus"], f"+{area['bonus_val']*100:.0f}% bonus")
    vi   = VILLAGES.get(vn,{})
    vinfo= VILLAGE_INFO.get(vn,{})
    cap  = (f"{area['emoji']} <b>{hesc(area['name'])}</b>\n"
            f"<i>{hesc(vinfo.get('full',vn))} · {hesc(vinfo.get('country',''))}</i>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>{hesc(area['desc'])}</i>\n\n"
            f"✨ <b>Area Bonus:</b> {hesc(bonus_label)}\n\n"
            f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> Enemies drawn from {hesc(vinfo.get('full',vn))} shinobi.\n"
            f"<i>Tap below to begin battle in this area!</i>")
    kb = [
        [Btn("Explore This Area", callback_data=f"trv_ex:{idx}")],
        [Btn("◀ Back to Areas", callback_data="trv_back")],
    ]
    try:
        await q.edit_message_caption(caption=cap[:1020], parse_mode="HTML",
                                     reply_markup=Kbd(kb))
    except:
        try: await q.edit_message_text(cap[:1020], parse_mode="HTML",
                                       reply_markup=Kbd(kb))
        except: pass

async def cb_travel_explore(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Start an explore battle from a chosen travel area with area bonuses applied."""
    q   = update.callback_query; await q.answer()
    uid = str(q.from_user.id)
    user = await db_get(uid)
    vn  = user.get("village","Konoha")
    areas = VILLAGE_AREAS.get(vn, VILLAGE_AREAS["Konoha"])
    idx  = int(q.data.split(":")[1])
    area = areas[idx] if idx < len(areas) else areas[0]
    team = await db_team(uid)
    if not team:
        await q.answer("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> No team! Use /team to set one.", show_alert=True); return
    team_sorted = sorted(team, key=lambda c: c.get("slot",99))
    p_row = team_sorted[0]
    cd    = get_cdata(p_row["char_name"])
    if not cd:
        await q.answer("Character data error!", show_alert=True); return
    pkg   = CLAN_KG.get(cd["clan"],"None")
    vi_i  = VILLAGES.get(vn, {})
    hp_b  = vi_i.get("hp",0)
    plv   = p_row["level"]
    php   = int(calc_stat(cd["base"]["hp"], p_row["pp_hp"], plv) * (1 + hp_b))
    p_atk = calc_stat(cd["base"]["atk"], p_row["pp_atk"], plv)
    p_def = calc_stat(cd["base"]["def"], p_row["pp_def"], plv)
    p_spd = int(calc_stat(cd["base"]["speed"], p_row["pp_spd"], plv) * (1 + vi_i.get("spd",0)))
    # Apply area heal bonus
    if area["bonus"] == "heal":
        php = int(calc_stat(cd["base"]["hp"], p_row["pp_hp"], plv) * (1 + hp_b))  # full hp
    # Build enemy — always use village characters for travel areas
    village_chars = [c for c in CHARACTERS if c["village"] == vn] or CHARACTERS
    ecd  = random.choice(village_chars)
    elv  = max(1, plv + random.randint(-6, 10))
    ehp  = int(calc_stat(ecd["base"]["hp"], 15, elv) * 0.7)
    wild = {
        "name": ecd["name"], "nat": ecd["nature"],
        "hp": ehp,
        "atk": int(calc_stat(ecd["base"]["atk"], 15, elv) * 0.7),
        "def": int(calc_stat(ecd["base"]["def"], 15, elv) * 0.7),
        "spd": int(calc_stat(ecd["base"]["speed"], 15, elv) * 0.7),
        "photo": PHOTO_CACHE.get(ecd["name"]),
        "nc":    (max(200, elv*30), max(500, elv*80)),
        "chakra":(max(20, elv*3),  max(80,  elv*10)),
        "exp":   (max(30, elv*8),  max(100, elv*20)),
        "moves": ecd["moves"], "is_char": True,
        # Store area bonus so cb_explore can apply it
        "area_bonus": area["bonus"], "area_bonus_val": area["bonus_val"],
        "area_name": area["name"],
    }
    elv_s = elv
    e_spd = wild.get("spd", 150)
    p_goes_first = p_spd >= e_spd
    form = cd.get("form"); req_chakra = form["req_chakra"] if form else 999999
    session = {
        "p_char":p_row["char_name"],"p_char_id":p_row["id"],"p_level":plv,
        "p_hp":php,"p_max_hp":php,"p_atk":p_atk,"p_def":p_def,
        "p_spd":p_spd,"p_nat":cd["nature"],"p_kg":pkg,
        "p_status":"","p_dot":None,"p_def_broken":False,"p_revived":False,
        "p_battle_chakra":0,"p_transformed":False,"transform_available":False,
        "req_chakra":req_chakra,
        "enemy":wild,"e_hp":ehp,"e_max_hp":ehp,"e_level":elv_s,
        "e_status":"","e_dot":None,"e_def_broken":False,
        "is_photo":False,"turn":0,"uid":uid,"p_goes_first":p_goes_first,
        "team_order":[c["id"] for c in team_sorted],
        "team_idx":0,
        "team_map":{c["id"]:c for c in team_sorted},
        "area_name": area["name"], "area_bonus": area["bonus"],
        "area_bonus_val": area["bonus_val"],
        "started_at": time.time(),
    }
    EX[uid] = session
    transform_avail = (session["p_battle_chakra"] >= req_chakra and
                       user.get("stones",0) >= 1 and form and not session["p_transformed"])
    session["transform_available"] = transform_avail
    txt = fmt_battle_text(session)
    # Append area banner to battle text
    area_line = f"\n{pe('village')} <i>{area['emoji']} {hesc(area['name'])} — +{area['bonus_val']*100:.0f}% {hesc(area['bonus'].upper())} bonus!</i>"
    txt = txt + area_line
    kb  = move_btns_explore(get_char_moves(p_row["char_name"], plv), uid, transform_avail)
    battle_photo = PHOTO_CACHE.get(ecd["name"])
    if battle_photo:
        try:
            await q.edit_message_caption(caption=txt[:1020], parse_mode="HTML",
                                         reply_markup=Kbd(kb))
            session["is_photo"] = True
            return
        except: pass
    try:
        await q.edit_message_text(txt[:4096], parse_mode="HTML", reply_markup=Kbd(kb))
    except: pass

async def cb_travel_back(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Return to the areas list."""
    q   = update.callback_query; await q.answer()
    uid = str(q.from_user.id)
    user = await db_get(uid)
    vn   = user.get("village","Konoha")
    vi   = VILLAGES.get(vn, {})
    vinfo= VILLAGE_INFO.get(vn, {})
    areas= VILLAGE_AREAS.get(vn, VILLAGE_AREAS["Konoha"])
    rows = []
    for i in range(0, len(areas), 2):
        row = []
        for j in range(2):
            if i + j < len(areas):
                a = areas[i + j]
                row.append(Btn(f"{a['emoji']} {a['name']}", callback_data=f"trv:{i+j}"))
        rows.append(row)
    rows.append([Btn("Change Village", callback_data="menu:village")])
    txt = (f"<tg-emoji emoji-id='5425114616260731920'>🗺️</tg-emoji> <b>Explore {vinfo.get('full', vn)}</b>\n"
           f"━━━━━━━━━━━━━━━━━━━━\n"
           f"{vi.get('emoji', pe('village'))} <i>{vinfo.get('country','')} — {vi.get('desc','')}</i>\n\n"
           f"Choose an area to explore. Each location has unique\n"
           f"enemies and bonus multipliers!\n\n"
           f"<tg-emoji emoji-id='5427342518876381603'>📍</tg-emoji> <b>Available Areas:</b> {len(areas)}")
    try:
        await q.edit_message_caption(caption=txt[:1020], parse_mode="HTML",
                                     reply_markup=Kbd(rows))
    except:
        try: await q.edit_message_text(txt[:1020], parse_mode="HTML",
                                       reply_markup=Kbd(rows))
        except: pass

# ─── /village /clan ─────────────────────────────────────────────
def _village_list_kb(current_village: str):
    """Build 2-column keyboard showing full village names. Tap → preview."""
    vkeys = list(VILLAGES.keys())
    rows = []
    for i in range(0, len(vkeys), 2):
        row = []
        for j in range(2):
            if i + j < len(vkeys):
                vk = vkeys[i + j]
                vi  = VILLAGES[vk]
                vinfo = VILLAGE_INFO.get(vk, {})
                # Telegram button labels do NOT render HTML — use plain text only
                star  = "✅ " if vk == current_village else ""
                label = f"{star}{vinfo.get('full', vk)}"
                row.append(Btn(label, callback_data=f"vp:{vk}"))
        rows.append(row)
    return rows

async def cmd_village(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid  = str(update.effective_user.id)
    user = await db_get(uid)
    cur  = user["village"]
    vi   = VILLAGES.get(cur, {})
    vinfo = VILLAGE_INFO.get(cur, {})
    kb   = _village_list_kb(cur)
    txt  = (f"<tg-emoji emoji-id='5427342518876381603'>🏘️</tg-emoji> <b>Villages of the Ninja World</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Current: {vi.get('emoji', pe('village'))} <b>{vinfo.get('full', cur)}</b>\n"
            f"_{vinfo.get('country', '')} — {vinfo.get('kage','')}_\n\n"
            f"_Tap a village to see details and join!_")
    try:
        await update.message.reply_photo(photo=VILLAGE_BANNER, caption=txt[:1020],
            parse_mode="HTML", reply_markup=Kbd(kb))
    except:
        await update.message.reply_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))

async def cb_village_preview(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show village details + join button when user taps a village name."""
    q  = update.callback_query; await q.answer()
    vn = q.data.split(":")[1]
    if vn not in VILLAGES: return
    uid  = str(q.from_user.id)
    user = await db_get(uid)
    vi   = VILLAGES[vn]
    vinfo = VILLAGE_INFO.get(vn, {})
    bonuses = "\n".join(
        f"  • +{int(v*100)}% {k.upper()}"
        for k, v in vi.items() if isinstance(v, float) and v > 0
    )
    vc = [c["name"] for c in CHARACTERS if c["village"] == vn][:5]
    is_current = (user["village"] == vn)
    status_line = "✅ <b>Your current village</b>" if is_current else f"Tap below to join {vi['emoji']} {hesc(vinfo.get('full', vn))}!"
    cap = (f"{vi['emoji']} <b>{hesc(vinfo.get('full', vn))}</b>\n"
           f"<i>{hesc(vinfo.get('country',''))} · {hesc(vinfo.get('kage','Kage'))}</i>\n"
           f"━━━━━━━━━━━━━━━━━━━━\n"
           f"<i>{hesc(vi['desc'])}</i>\n\n"
           f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> <b>Battle Bonuses:</b>\n{bonuses or '  • +5% all stats'}\n\n"
           f"<tg-emoji emoji-id='5425113284820869526'>🥷</tg-emoji> <b>Notable Shinobi:</b>\n  {hesc(', '.join(vc) or 'Various')}\n\n"
           f"{status_line}")
    kb = []
    if not is_current:
        kb.append([Btn(f"✅ Join {vinfo.get('full', vn)}", callback_data=f"vj:{vn}")])
    kb.append([Btn("◀ Back to Villages", callback_data="vback")])
    try:
        await q.edit_message_caption(caption=cap[:1020], parse_mode="HTML",
                                     reply_markup=Kbd(kb))
    except:
        try: await q.edit_message_text(cap[:1020], parse_mode="HTML",
                                       reply_markup=Kbd(kb))
        except: pass

async def cb_village(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    vn = q.data.split(":")[1]
    if vn not in VILLAGES: return
    uid = str(q.from_user.id); await db_set(uid, village=vn)
    vi   = VILLAGES[vn]
    vinfo = VILLAGE_INFO.get(vn, {})
    bonuses = "\n".join(
        f"  • +{int(v*100)}% {k.upper()}"
        for k, v in vi.items() if isinstance(v, float) and v > 0
    )
    vc = [c["name"] for c in CHARACTERS if c["village"] == vn][:5]
    new_cap = (f"{vi['emoji']} <b>Joined {hesc(vinfo.get('full', vn))}!</b>\n"
               f"<i>{hesc(vinfo.get('country',''))} — {hesc(vinfo.get('kage','Kage'))}</i>\n"
               f"<i>{hesc(vi['desc'])}</i>\n\n"
               f"<b>Battle Bonuses:</b>\n{bonuses or '  • +5% all stats'}\n\n"
               f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> <b>Notable Shinobi:</b> {hesc(', '.join(vc) or 'Various')}\n\n"
               f"<i>In /explore you will now face {hesc(vinfo.get('full', vn))} characters!</i>")
    kb = [[Btn("◀ Back to Villages", callback_data="vback")]]
    try:
        await q.edit_message_caption(caption=new_cap[:1020], parse_mode="HTML",
                                     reply_markup=Kbd(kb))
    except:
        try: await q.edit_message_text(new_cap[:1020], parse_mode="HTML",
                                       reply_markup=Kbd(kb))
        except: pass

async def cb_village_back(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Go back to the village list."""
    q   = update.callback_query; await q.answer()
    uid = str(q.from_user.id)
    user = await db_get(uid)
    cur  = user["village"]
    vi   = VILLAGES.get(cur, {})
    vinfo = VILLAGE_INFO.get(cur, {})
    kb   = _village_list_kb(cur)
    txt  = (f"<tg-emoji emoji-id='5427342518876381603'>🏘️</tg-emoji> <b>Villages of the Ninja World</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Current: {vi.get('emoji', pe('village'))} <b>{hesc(vinfo.get('full', cur))}</b>\n"
            f"<i>{hesc(vinfo.get('country', ''))} — {hesc(vinfo.get('kage',''))}</i>\n\n"
            f"<i>Tap a village to see details and join!</i>")
    try:
        await q.edit_message_caption(caption=txt[:1020], parse_mode="HTML",
                                     reply_markup=Kbd(kb))
    except:
        try: await q.edit_message_text(txt[:1020], parse_mode="HTML",
                                       reply_markup=Kbd(kb))
        except: pass

async def cmd_clan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid=str(update.effective_user.id); user=await db_get(uid)
    if user.get("clan"):
        kg=CLAN_KG.get(user["clan"],"None"); ki=KG.get(kg,KG["None"])
        chars_w=[c["name"] for c in CHARACTERS if c["clan"]==user["clan"]][:4]
        txt=(f"<tg-emoji emoji-id='5224388744156557558'>🧬</tg-emoji> <b>{user['clan']} Clan</b> ⟨LOCKED⟩\n\n"
             f"_{CLANS.get(user['clan'],'')}_\n\n"
             f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>KG: {kg}</b>\n_{ki['desc']}_\n\n"
             f"<tg-emoji emoji-id='5425113284820869526'>🥷</tg-emoji> Clan users: {', '.join(chars_w) or 'Various'}\n\n"
             f"<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji> <i>Clan is a lifetime choice — it cannot be changed!</i>")
        try:
            await update.message.reply_photo(photo=CLAN_BANNER,caption=txt[:1020],parse_mode="HTML")
        except:
            await update.message.reply_text(txt,parse_mode="HTML")
        return
    cnames=SELECTABLE_CLANS; kb=[]
    for i in range(0,len(cnames),2):
        row=[]
        for j in range(2):
            if i+j<len(cnames):
                cn=cnames[i+j]
                row.append(Btn(f"Join {cn}",callback_data=f"cj:{i+j}"))
        kb.append(row)
    txt=(f"<tg-emoji emoji-id='5224388744156557558'>🧬</tg-emoji> <b>Choose Your Clan</b>\n\n"
         f"<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji> <b>WARNING: This is a LIFETIME choice!</b>\n"
         f"_You can NEVER change your clan once chosen._\n\n"
         f"Your clan gives you a Kekkei Genkai (KG) power that affects all battles!")
    try:
        await update.message.reply_photo(photo=CLAN_BANNER,caption=txt[:1020],
            parse_mode="HTML",reply_markup=Kbd(kb))
    except:
        await update.message.reply_text(txt,parse_mode="HTML",reply_markup=Kbd(kb))

async def cb_clan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    idx=int(q.data.split(":")[1]); cnames=SELECTABLE_CLANS
    if idx>=len(cnames): return
    cn=cnames[idx]; uid=str(q.from_user.id)
    user=await db_get(uid)
    if user.get("clan"):
        await q.answer(f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> You already belong to {user['clan']} Clan! This is permanent.",show_alert=True); return
    # Check if this clan has an admin (approval required)
    clan_doc = await clans_col.find_one({"_id": cn})
    if not clan_doc or not clan_doc.get("admin_uid"):
        # No admin registered — clan is locked until an admin is appointed
        await q.answer(
            "⛔ This clan has no active admin and is currently closed. "
            "An admin must be appointed before members can join.",
            show_alert=True)
        return
    admin_uid = clan_doc["admin_uid"]
    # Admin must have joined this clan themselves before it opens for join requests
    admin_user = await db_get(admin_uid)
    if not admin_user or admin_user.get("clan") != cn:
        await q.answer(
            "⛔ The clan admin has not yet joined this clan. "
            "Joining is unavailable until the admin becomes a member first.",
            show_alert=True)
        return
    # Admin is confirmed in clan — send approval request
    await clan_req_col.replace_one(
        {"uid": uid, "clan": cn},
        {"uid": uid, "clan": cn, "ts": datetime.utcnow().isoformat()},
        upsert=True)
    kb_admin = [[Btn("Approve", callback_data=f"clreq:approve:{uid}:{cn}"),
                 Btn("Deny",    callback_data=f"clreq:deny:{uid}:{cn}")]]
    req_name = update.effective_user.first_name or uid
    try:
        await ctx.bot.send_message(
            admin_uid,
            f"<tg-emoji emoji-id='5224388744156557558'>🧬</tg-emoji> <b>Clan Join Request</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"<tg-emoji emoji-id='5425113284820869526'>👤</tg-emoji> <b>{req_name}</b> (ID: <code>{uid}</code>) wants to join <b>{cn}</b> Clan!\n\n"
            f"Approve or deny their request:",
            parse_mode="HTML", reply_markup=Kbd(kb_admin))
    except Exception:
        pass
    await _safe_edit(q,
        f"<tg-emoji emoji-id='5803204762035818905'>⏳</tg-emoji> <b>Join Request Sent!</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"Your request to join <b>{cn}</b> Clan has been sent to the clan admin.\n\n"
        f"<i>You will be notified once it is approved or denied.</i>",
        [[Btn("◀ Back to Clans", callback_data="cj:0")]])
    kg=CLAN_KG.get(cn,"None"); ki=KG.get(kg,KG["None"])
    chars_w=[c["name"] for c in CHARACTERS if c["clan"]==cn][:4]
    txt=(f"<tg-emoji emoji-id='5224388744156557558'>🧬</tg-emoji> <b>{cn} Clan — JOINED!</b>\n\n_{CLANS[cn]}_\n\n"
         f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>KG: {kg}</b>\n_{ki['desc']}_\n\n"
         f"<tg-emoji emoji-id='5425113284820869526'>🥷</tg-emoji> Clan users: {', '.join(chars_w) or 'Various'}\n\n"
         f"<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji> <i>This clan is now permanent — it can never be changed!</i>")
    try:
        await q.edit_message_caption(caption=txt[:1020], parse_mode="HTML")
    except:
        await q.edit_message_text(txt, parse_mode="HTML")

# ─── CLAN JOIN REQUEST APPROVAL ─────────────────────────────────
async def cb_clan_request(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts = q.data.split(":", 3)
    if len(parts) < 4: return
    action, req_uid, clan = parts[1], parts[2], parts[3]
    admin_uid = str(q.from_user.id)
    # Verify caller is this clan's admin
    clan_doc = await clans_col.find_one({"_id": clan})
    if not clan_doc or clan_doc.get("admin_uid") != admin_uid:
        await q.answer("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> You are not this clan's admin!", show_alert=True); return
    if action == "approve":
        req_user = await db_get(req_uid)
        if not req_user:
            await q.edit_message_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> User not found."); return
        if req_user.get("clan"):
            await q.edit_message_text(f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> User already belongs to {req_user['clan']} clan."); return
        await db_set(req_uid, clan=clan)
        await clan_req_col.delete_one({"uid": req_uid, "clan": clan})
        kg = CLAN_KG.get(clan, "None"); ki = KG.get(kg, KG["None"])
        try:
            await ctx.bot.send_message(
                req_uid,
                f"<tg-emoji emoji-id='5224388744156557558'>🧬</tg-emoji> <b>{clan} Clan — JOIN APPROVED!</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                f"_{CLANS.get(clan, '')}_\n\n"
                f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>KG: {kg}</b>\n_{ki['desc']}_\n\n"
                f"<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji> <i>This clan choice is permanent — it can never be changed!</i>",
                parse_mode="HTML")
        except Exception:
            pass
        await q.edit_message_text(
            f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> <b>Approved!</b>\nUser <code>{req_uid}</code> has been added to <b>{clan}</b> Clan.",
            parse_mode="HTML")
    elif action == "deny":
        await clan_req_col.delete_one({"uid": req_uid, "clan": clan})
        try:
            await ctx.bot.send_message(
                req_uid,
                f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> <b>Clan Join Request Denied</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                f"Your request to join <b>{clan}</b> Clan was denied by the admin.\n\n"
                f"<i>Try /clan to choose a different clan!</i>",
                parse_mode="HTML")
        except Exception:
            pass
        await q.edit_message_text(
            f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Denied <code>{req_uid}</code>'s request to join <b>{clan}</b> Clan.",
            parse_mode="HTML")

# ─── /nature /kekkei /beast /ability ────────────────────────────
async def cmd_nature(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    nats=ALL_NATURES[:18]
    kb=[[Btn(f"{NAT_EMO.get(nats[i+j],'🌿')} {nats[i+j]}",callback_data=f"nat:{nats[i+j]}") for j in range(3) if i+j<len(nats)] for i in range(0,len(nats),3)]
    await update.message.reply_text("<tg-emoji emoji-id='5426872512015244606'>🌿</tg-emoji> <b>Nature Types</b> — Tap to see advantages:",
                                    parse_mode="HTML",reply_markup=Kbd(kb))

async def cb_nature(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    nat=q.data.split(":",1)[1]
    if nat=="__back":
        nats=ALL_NATURES[:18]
        kb=[[Btn(f"{NAT_EMO.get(nats[i+j],'🌿')} {nats[i+j]}",callback_data=f"nat:{nats[i+j]}") for j in range(3) if i+j<len(nats)] for i in range(0,len(nats),3)]
        await q.edit_message_text("<tg-emoji emoji-id='5426872512015244606'>🌿</tg-emoji> <b>Nature Types</b>",parse_mode="HTML",reply_markup=Kbd(kb)); return
    info=ADV.get(nat,{"s":[],"w":[]})
    strong=", ".join(info["s"]) or "None"; weak=", ".join(info["w"]) or "None"
    cw=[c["name"] for c in CHARACTERS if c["nature"]==nat][:4]
    await q.edit_message_text(
        f"{NAT_EMO.get(nat,'🌿')} <b>{hesc(nat)} Nature</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5803416753031615097'>⬆️</tg-emoji> <b>Strong vs:</b> {hesc(strong)}\n<tg-emoji emoji-id='5803204762035818905'>⬇️</tg-emoji> <b>Weak vs:</b> {hesc(weak)}\n\n"
        f"<tg-emoji emoji-id='5425113284820869526'>🥷</tg-emoji> Notable Users: {hesc(', '.join(cw) or 'Various')}",
        parse_mode="HTML",
        reply_markup=Kbd([[Btn("Back",callback_data="nat:__back")]]))

async def cmd_kekkei(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kgn=[k for k in KG if k!="None"]
    kb=[[Btn(kgn[i+j],callback_data=f"kk:{i+j}") for j in range(2) if i+j<len(kgn)] for i in range(0,len(kgn),2)]
    await update.message.reply_text("<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>Kekkei Genkai</b>",parse_mode="HTML",reply_markup=Kbd(kb))

async def cb_kekkei(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    idx=int(q.data.split(":")[1]); kgn=[k for k in KG if k!="None"]
    if idx==-1 or idx>=len(kgn):
        kb=[[Btn(kgn[i+j],callback_data=f"kk:{i+j}") for j in range(2) if i+j<len(kgn)] for i in range(0,len(kgn),2)]
        await q.edit_message_text("<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>Kekkei Genkai</b>",parse_mode="HTML",reply_markup=Kbd(kb)); return
    kn=kgn[idx]; info=KG[kn]; effs=[]
    if "crit" in info: effs.append(f"+{info['crit']}% crit")
    if "acc" in info:  effs.append(f"+{info['acc']}% acc")
    if "regen" in info:effs.append(f"Regen {int(info['regen']*100)}% HP/turn")
    if "reflect" in info:effs.append(f"Reflect {int(info['reflect']*100)}% dmg")
    if "shield" in info:effs.append(f"Shield {int(info['shield']*100)}% HP")
    clans_w=[c for c,k in CLAN_KG.items() if k==kn]
    chars_w=[c["name"] for c in CHARACTERS if CLAN_KG.get(c["clan"],"")==kn][:4]
    await q.edit_message_text(
        f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>{kn}</b>\n━━━━━━━━━━━━━━━━━━━━\n_{info['desc']}_\n\n"
        f"<b>Battle Effects:</b>\n"+"\n".join(f"  • {e}" for e in effs)+
        f"\n\n<b>Clans:</b> {', '.join(clans_w[:5]) or 'None'}\n<b>Users:</b> {', '.join(chars_w) or 'Various'}",
        parse_mode="HTML",
        reply_markup=Kbd([[Btn("Back",callback_data="kk:-1")]]))

async def cmd_beast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb=[[Btn(f"{n} ({v['tails']} tails)",callback_data=f"bs:{n}")] for n,v in BEASTS.items()]
    await update.message.reply_text("<tg-emoji emoji-id='6003600664687546316'>🦊</tg-emoji> <b>Tailed Beasts (Bijuu)</b>",parse_mode="HTML",reply_markup=Kbd(kb))

async def cb_beast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    bn=q.data.split(":")[1]
    if bn=="__back":
        kb=[[Btn(f"{n} ({v['tails']} tails)",callback_data=f"bs:{n}")] for n,v in BEASTS.items()]
        await q.edit_message_text("<tg-emoji emoji-id='6003600664687546316'>🦊</tg-emoji> <b>Tailed Beasts (Bijuu)</b>",parse_mode="HTML",reply_markup=Kbd(kb)); return
    info=BEASTS.get(bn,{})
    hc=get_cdata(info.get("host",""))
    await q.edit_message_text(
        f"{info.get('emoji', pe('wolf'))} <b>{bn}</b> ({info['tails']} Tails)\n━━━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5426872512015244606'>🌿</tg-emoji> Nature: <b>{info['nat']}</b> | <tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> Power: <b>{info['power']:,}</b>\n"
        f"<tg-emoji emoji-id='5425113284820869526'>🥷</tg-emoji> Host: <b>{info['host']}</b> ⟨{hc['rarity'] if hc else '?'}⟩\n\n"
        f"<tg-emoji emoji-id='5998841304052669228'>💥</tg-emoji> <b>Ability:</b>\n_{info['ability']}_",
        parse_mode="HTML",
        reply_markup=Kbd([[Btn("All Beasts",callback_data="bs:__back")]]))

async def cmd_ability(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid=str(update.effective_user.id); user=await db_get(uid)
    kg=CLAN_KG.get(user["clan"],"None"); ki=KG.get(kg,KG["None"])
    vi=VILLAGES.get(user["village"],{})
    effs=[]
    if ki.get("crit"): effs.append(f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> +{ki['crit']}% crit chance")
    if ki.get("acc"):  effs.append(f"<tg-emoji emoji-id='5427397421443325675'>🎯</tg-emoji> +{ki['acc']}% accuracy")
    if ki.get("regen"):effs.append(f"💚 Regen {int(ki['regen']*100)}% HP/turn")
    if ki.get("reflect"):effs.append(f"<tg-emoji emoji-id='5769455402945090965'>🔄</tg-emoji> Reflect {int(ki['reflect']*100)}% damage")
    if ki.get("shield"):effs.append(f"<tg-emoji emoji-id='6039727447090403055'>🛡️</tg-emoji> Auto-shield {int(ki['shield']*100)}% HP")
    if ki.get("dodge_chance"):effs.append(f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> {ki['dodge_chance']}% dodge")
    vb=[f"{k.upper()} +{int(v*100)}%" for k,v in vi.items() if isinstance(v,float) and v>0]
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>Your Active Abilities</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5224388744156557558'>🧬</tg-emoji> <b>Clan:</b> {user['clan'] or 'None'}\n"
        f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>KG:</b> {kg}\n_{ki['desc']}_\n\n"
        f"<b>Battle Bonuses:</b>\n"+("\n".join(f"  • {e}" for e in effs) or "  • +5% all stats")+
        f"\n\n{vi.get('emoji', '🏘️')} <b>Village:</b> {user['village']}\n"
        f"<b>Village Bonuses:</b> {', '.join(vb) or 'None'}",
        parse_mode="HTML")

# ─── /heal /inventory /chakra /team ─────────────────────────────
async def cmd_heal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid=str(update.effective_user.id); user=await db_get(uid)
    if user["coins"]<300:
        await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Need 300 NC to heal."); return
    await db_set(uid,coins=user["coins"]-300)
    await update.message.reply_text(
        "<tg-emoji emoji-id='5427095369278299187'>💊</tg-emoji> <b>All characters healed!</b> (-300 NC)\nReady for battle!",
        parse_mode="HTML",
        reply_markup=Kbd([[Btn("Explore!",callback_data="menu:explore")]]))

async def _show_inventory(target, uid, edit=False):
    user      = await db_get(uid)
    stones    = user.get("stones", 0)
    chakra    = user.get("chakra", 0)
    coins     = user.get("coins", 0)
    exp_boost = user.get("exp_boost", 0)
    level     = user.get("level", 1)
    rank      = user.get("rank", "Academy Student")
    chars     = await db_chars(uid)

    # ── Equipped weapon only ───────────────────────────────────────
    equipped_wid = user.get("equipped_weapon")
    owned_wids   = list(user.get("weapons") or [])
    ew = get_weapon_by_id(equipped_wid) if equipped_wid else None
    if ew:
        weapon_txt = f"  1. <b>{hesc(ew['name'])}</b> [Equipped] — ATK +{ew['atk']}"
    elif owned_wids:
        weapon_txt = f"  {len(owned_wids)} weapon(s) owned — none equipped"
    else:
        weapon_txt = "  No weapons yet — explore to find them!"

    # ── Items section ─────────────────────────────────────────────
    item_lines = []
    if exp_boost:
        item_lines.append(f"  {pe('exp')} 2× EXP Boost — Active")
    if stones:
        item_lines.append(f"  {pe('stone')} Transform Stones — ×{stones}")
    if not item_lines:
        item_lines.append("  Bag empty — head to the shop!")

    txt = (
        f"{pe('anbu')} <b>Inventory</b>\n\n"
        f"Lv.{level} {hesc(rank)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{pe('coin')} Coins      : <b>{coins:,} NC</b>\n"
        f"{pe('chakra')} Chakra    : <b>{chakra:,}</b>\n"
        f"{pe('stone')} Stones    : <b>{stones}</b>\n"
        f"{pe('team')} Characters : <b>{len(chars)}</b> owned\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{pe('sword')} <b>Weapons</b> (equipped):\n"
        f"{weapon_txt}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{pe('bag')} <b>Items:</b>\n"
        + "\n".join(item_lines) + "\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    kb = [
        [Btn("Active Team",  callback_data=f"inv:active_team:{uid}"),
         Btn("Weapons List", callback_data=f"inv:weapons:{uid}:0")],
        [Btn("Your Beast",   callback_data=f"inv:beast:{uid}"),
         Btn("Ranks",        callback_data=f"inv:ranks:{uid}")],
    ]
    if edit:
        is_photo = bool(getattr(target, 'message', None) and target.message.photo)
        try:
            if is_photo:
                await target.edit_message_caption(caption=txt[:1020], parse_mode="HTML", reply_markup=Kbd(kb))
            else:
                await target.edit_message_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))
        except: pass
    else:
        await target.reply_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))

async def cmd_inventory(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid = str(update.effective_user.id)
    await _show_inventory(update.message, uid, edit=False)

async def cb_inventory(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts = q.data.split(":"); action = parts[1]; uid = parts[2]
    if str(q.from_user.id) != uid: await q.answer("Not yours!", show_alert=True); return

    BACK_KB = [[Btn("Back", callback_data=f"inv:view:{uid}")]]

    if action == "view":
        await _show_inventory(q, uid, edit=True)

    elif action == "active_team":
        team = await db_team(uid)
        if not team:
            await _safe_edit(q,
                f"{pe('team')} <b>Active Team</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                f"No team set!\n<i>Use /team to add characters.</i>",
                BACK_KB); return
        lines = []
        for i in range(1, 7):
            sc = next((c for c in team if c["slot"] == i), None)
            if sc:
                cd = get_cdata(sc["char_name"])
                rar = RAR.get(cd["rarity"], "⚪") if cd else "⚪"
                nat = nat_icon(cd["nature"]) if cd else ""
                lines.append(f"Slot {i}: {rar} <b>{hesc(sc['char_name'])}</b> Lv.{sc['level']} {nat}")
            else:
                lines.append(f"Slot {i}: — (empty)")
        txt = (f"{pe('team')} <b>Active Team</b>\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               + "\n".join(lines) +
               f"\n━━━━━━━━━━━━━━━━━━━━\n<i>Use /team to manage slots.</i>")
        await _safe_edit(q, txt, BACK_KB)

    elif action == "weapons":
        page = int(parts[3]) if len(parts) > 3 else 0
        user = await db_get(uid)
        owned_wids   = list(user.get("weapons") or [])
        equipped_wid = user.get("equipped_weapon")
        if not owned_wids:
            await _safe_edit(q,
                f"{pe('sword')} <b>Your Weapons</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                f"No weapons yet!\n<i>Explore or buy from the weapon shop.</i>",
                BACK_KB); return
        PER_PAGE = 10
        total  = len(owned_wids)
        pages  = max(1, (total + PER_PAGE - 1) // PER_PAGE)
        page   = max(0, min(page, pages - 1))
        batch  = owned_wids[page * PER_PAGE:(page + 1) * PER_PAGE]
        lines  = []
        for i, wid in enumerate(batch, page * PER_PAGE + 1):
            w = get_weapon_by_id(wid)
            if w:
                eq = " ✓ <b>[Equipped]</b>" if wid == equipped_wid else ""
                lines.append(
                    f"{i}. [{w['rarity'][:2]}] <b>{hesc(w['name'])}</b> — ATK +{w['atk']}{eq}\n"
                    f"   <i>{hesc(w['ability'])}</i>"
                )
        txt = (f"{pe('sword')} <b>Your Weapons</b>\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"Total: <b>{total}</b> | Page <b>{page+1}/{pages}</b>\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               + "\n\n".join(lines))
        nav = []
        if page > 0:
            nav.append(Btn("◀ Prev", callback_data=f"inv:weapons:{uid}:{page-1}"))
        if page < pages - 1:
            nav.append(Btn("Next ▶", callback_data=f"inv:weapons:{uid}:{page+1}"))
        kb = []
        if nav: kb.append(nav)
        kb.extend(BACK_KB)
        await _safe_edit(q, txt[:4000], kb)

    elif action == "beast":
        user         = await db_get(uid)
        caught       = list(user.get("caught_beasts") or [])
        team         = await db_team(uid)
        team_beasts  = set()
        for c in team:
            cd = get_cdata(c["char_name"])
            if cd and cd.get("tailed_beast"):
                team_beasts.add(cd["tailed_beast"])
        all_beasts = set(caught) | team_beasts
        if not all_beasts:
            await _safe_edit(q,
                f"{pe('wolf')} <b>Your Beasts</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                f"No tailed beasts yet!\n<i>Defeat beast encounters while exploring to catch them.</i>",
                BACK_KB); return
        lines = []
        for bname in sorted(all_beasts, key=lambda b: BEASTS.get(b, {}).get("tails", 0)):
            bi     = BEASTS.get(bname, {})
            status = "✓ Caught" if bname in caught else "Via team"
            hosts  = bi.get("host_chars", [bi.get("host", "?")])
            lines.append(
                f"{bi.get('emoji','🦊')} <b>{hesc(bname)}</b> — {bi.get('tails','?')} Tails\n"
                f"   Host: <i>{hesc(', '.join(hosts[:2]))}</i>\n"
                f"   Power: {bi.get('power',0):,} | {status}"
            )
        txt = (f"{pe('wolf')} <b>Your Beasts</b>\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"Total: <b>{len(all_beasts)}</b> beast(s)\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               + "\n\n".join(lines))
        await _safe_edit(q, txt[:4000], BACK_KB)

    elif action == "ranks":
        user  = await db_get(uid)
        lv    = user.get("level", 1)
        wins  = user.get("wins", 0)
        losses = user.get("losses", 0)
        rank  = user.get("rank", "Academy Student")
        pos   = await users_col.count_documents({"wins": {"$gt": wins}}) + 1
        RANKS = ["Academy Student","Genin","Skilled Genin","Chunin","Elite Chunin",
                 "Jonin","Elite Jonin","ANBU","Kage Candidate","Kage"]
        cur_idx   = RANKS.index(rank) if rank in RANKS else 0
        next_rank = RANKS[cur_idx + 1] if cur_idx + 1 < len(RANKS) else None
        next_lv   = (cur_idx + 1) * 10 if next_rank else None
        total_b   = wins + losses
        win_rate  = int(wins / total_b * 100) if total_b > 0 else 0
        next_line = (f"Next: <b>{next_rank}</b> at Level <b>{next_lv}</b>"
                     if next_rank else "<i>Max rank reached!</i>")
        txt = (f"{pe('rank')} <b>Your Rankings</b>\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"Title: <b>{hesc(rank)}</b>\n"
               f"Level: <b>{lv}</b> / 100\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"Battle Rank: <b>#{pos}</b> (global)\n"
               f"Wins: <b>{wins}</b> | Losses: <b>{losses}</b>\n"
               f"Win Rate: <b>{win_rate}%</b>\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"{next_line}")
        await _safe_edit(q, txt, BACK_KB)

    elif action == "doequip":
        wid = parts[3] if len(parts) > 3 else None
        if not wid:
            await q.answer("Error.", show_alert=True); return
        user = await db_get(uid)
        owned_wids = list(user.get("weapons") or [])
        if wid not in owned_wids:
            await q.answer("You don't own this weapon!", show_alert=True); return
        await db_set(uid, equipped_weapon=wid)
        w = get_weapon_by_id(wid)
        await q.answer(f"Equipped {w['name']}!" if w else "Equipped!", show_alert=False)
        await _show_inventory(q, uid, edit=True)

async def cmd_chakra(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid=str(update.effective_user.id); user=await db_get(uid); team=await db_team(uid)
    lines=[]
    for c in (team or []):
        cd=get_cdata(c["char_name"])
        if cd:
            form=cd.get("form"); req=form["req_chakra"] if form else None
            status=f" (Transform needs {req:,}<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji>)" if req else ""
            lines.append(f"  <tg-emoji emoji-id='5425113284820869526'>🥷</tg-emoji> {c['char_name']}: <b>{cd['base']['chakra']+c['pp_cha']*2}</b> chakra{status}")
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> <b>Chakra</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"Total: <b>{user['chakra']:,}</b> | <tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji> Stones: <b>{user.get('stones',0)}</b>\n\n"
        f"<b>Team Chakra:</b>\n"+("\n".join(lines) or "  No team"),
        parse_mode="HTML")

async def cmd_team(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid=str(update.effective_user.id)
    await show_team_panel(update.message, uid, edit=False)

async def show_team_panel(target, uid, edit=False):
    team=await db_team(uid)
    all_chars=await db_chars(uid)
    lines=[]
    now_str=datetime.utcnow().strftime("%I:%M %p")
    for i in range(1,7):
        slot_char=next((c for c in team if c["slot"]==i),None)
        if slot_char:
            rr=RAR.get(get_cdata(slot_char["char_name"])["rarity"],"⚪") if get_cdata(slot_char["char_name"]) else "⚪"
            lines.append(f"{i}. {rr} {slot_char['char_name']} — Lv. {slot_char['level']}  {now_str}")
        else:
            lines.append(f"{i}. — (empty)")
    txt=(f"<tg-emoji emoji-id='5425113284820869526'>👥</tg-emoji> <b>Active Team [ TEAM 1 ]</b>\n\n"+"\n".join(lines))
    kb=[
        [Btn("Slot 1",callback_data="tm:slot:1"),Btn("Slot 2",callback_data="tm:slot:2")],
        [Btn("Slot 3",callback_data="tm:slot:3"),Btn("Slot 4",callback_data="tm:slot:4")],
        [Btn("Slot 5",callback_data="tm:slot:5"),Btn("Slot 6",callback_data="tm:slot:6")],
        [Btn("Add",callback_data=f"tm:add:{uid}"),Btn("Remove",callback_data=f"tm:rem:{uid}")],
        [Btn("Change Order",callback_data=f"tm:order:{uid}"),Btn("Randomize",callback_data=f"tm:rand:{uid}")],
    ]
    if edit:
        is_photo = bool(getattr(target, 'message', None) and target.message.photo)
        try:
            if is_photo:
                await target.edit_message_caption(caption=txt[:1020], parse_mode="HTML", reply_markup=Kbd(kb))
            else:
                await target.edit_message_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))
        except: pass
    else:
        await target.reply_text(txt,parse_mode="HTML",reply_markup=Kbd(kb))

async def cb_team(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    parts=q.data.split(":"); action=parts[1]; uid=str(q.from_user.id)
    if action in ("slot","add","rem","order","rand") and len(parts)>2 and parts[2]!=uid:
        if not parts[2].isdigit():
            await q.answer("Not yours!",show_alert=True); return
    if action=="rand":
        all_chars=await db_chars(uid)
        if len(all_chars)<1: await q.answer("No chars!",show_alert=True); return
        team_pick=random.sample(all_chars,min(6,len(all_chars)))
        await chars_col.update_many({"uid": uid}, {"$set": {"in_team": 0, "slot": 0}})
        for sl,c in enumerate(team_pick,1):
            await chars_col.update_one({"_id": c["id"]}, {"$set": {"in_team": 1, "slot": sl}})
        await show_team_panel(q,uid,edit=True); return
    if action=="add":
        all_chars=await db_chars(uid); team=await db_team(uid)
        if len(team)>=6: await q.answer("Team full (6/6)!",show_alert=True); return
        not_in=[ c for c in all_chars if not c["in_team"]][:12]
        if not not_in: await q.answer("All chars already in team!",show_alert=True); return
        kb=[[Btn(f"{c['char_name'][:22]} Lv.{c['level']}",
                 callback_data=f"tm:addch:{c['id']}")] for c in not_in]
        kb.append([Btn("Back",callback_data="tm:back:0")])
        await _safe_edit(q, "➕ *Select char to add to team:*", kb); return
    if action=="addch":
        cid=int(parts[2]); team=await db_team(uid)
        if len(team)>=6: await q.answer("Team full!",show_alert=True); return
        next_slot=max((c["slot"] for c in team),default=0)+1
        await chars_col.update_one({"_id": cid, "uid": uid}, {"$set": {"in_team": 1, "slot": next_slot}})
        await show_team_panel(q,uid,edit=True); return
    if action=="rem":
        team=await db_team(uid)
        if not team: await q.answer("Team is empty!",show_alert=True); return
        kb=[[Btn(f"{c['char_name'][:24]} Lv.{c['level']}",callback_data=f"tm:remch:{c['id']}")] for c in team]
        kb.append([Btn("Back",callback_data="tm:back:0")])
        await _safe_edit(q, "➖ *Select char to remove:*", kb); return
    if action=="remch":
        cid=int(parts[2])
        await chars_col.update_one({"_id": cid, "uid": uid}, {"$set": {"in_team": 0, "slot": 0}})
        await show_team_panel(q,uid,edit=True); return
    if action=="back":
        await show_team_panel(q,uid,edit=True); return
    await show_team_panel(q,uid,edit=True)

# ─── /leaderboard /rank /top ─────────────────────────────────────
async def cmd_leaderboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb=[[Btn("Wins",callback_data="lb:wins"),Btn("NC",callback_data="lb:coins")],
        [Btn("Chakra",callback_data="lb:chakra"),Btn("Level",callback_data="lb:level")]]
    await update.message.reply_text("<tg-emoji emoji-id='5426976939850080222'>🏆</tg-emoji> <b>Leaderboard</b>\nChoose ranking:",
                                    parse_mode="HTML",reply_markup=Kbd(kb))

async def cb_lb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    col=q.data.split(":")[1]
    proj = {"name": 1, "nickname": 1, "rank": 1, col: 1}
    rows = await users_col.find({}, proj).sort([(col, -1)]).limit(10).to_list(None)
    medals=["<tg-emoji emoji-id='5426976939850080222'>🥇</tg-emoji>","<tg-emoji emoji-id='5424892463372312872'>🥈</tg-emoji>","<tg-emoji emoji-id='5224388744156557558'>🥉</tg-emoji>","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","<tg-emoji emoji-id='5798483635199807367'>🔟</tg-emoji>"]
    col_name = "NC" if col=="coins" else col.title()
    lines=[]
    for i,r in enumerate(rows):
        dn = r["nickname"] if r["nickname"] else r["name"]
        val = r[col]
        lines.append(f"{medals[i]} <b>{dn}</b> ⟨{r['rank']}⟩ — {val:,}")
    await q.edit_message_text(
        f"<tg-emoji emoji-id='5426976939850080222'>🏆</tg-emoji> <b>Top 10 — {col_name}</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"+
        ("\n".join(lines) or "No players yet!"),
        parse_mode="HTML")

async def cmd_rank(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid=str(update.effective_user.id); user=await db_get(uid)
    pos = await users_col.count_documents({"wins": {"$gt": user["wins"]}}) + 1
    bar=hp_bar(user["exp"],exp_for_lv(user["level"]+1))
    dn=display_name(user)
    _rank_wins = user["wins"]; _rank_losses = user["losses"]
    _rank_total = _rank_wins + _rank_losses
    _rank_wr = int((_rank_wins / _rank_total) * 100) if _rank_total else 0
    if _rank_wr >= 80:
        _rank_flavor = "Unstoppable — a true shinobi legend!"
    elif _rank_wr >= 60:
        _rank_flavor = "Solid record — rising through the ranks."
    elif _rank_wr >= 40:
        _rank_flavor = "Balanced fighter — keep training!"
    elif _rank_total == 0:
        _rank_flavor = "No battles yet — time to prove yourself!"
    else:
        _rank_flavor = "Room to grow — every loss is a lesson."
    _rank_streak = user.get("streak", 0)
    _streak_bonus = f" {pe('fire')} {_rank_streak}-day streak!" if _rank_streak >= 3 else ""
    await update.message.reply_text(
        f"{pe('rank')} <b>{dn}'s Shinobi Profile</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{pe('star')} <b>Rank:</b> <b>{hesc(user['rank'])}</b> — Lv.<b>{user['level']}</b>/100\n"
        f"{pe('exp')} <b>EXP Progress:</b> {bar}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{pe('sword')} <b>Battle Record:</b>\n"
        f"  Wins: <b>{_rank_wins}</b>  |  Losses: <b>{_rank_losses}</b>  |  Win Rate: <b>{_rank_wr}%</b>\n"
        f"  <i>{_rank_flavor}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{pe('coin')} NC: <b>{user['coins']:,}</b>  {pe('stone')} Stones: <b>{user.get('stones', 0)}</b>\n"
        f"{pe('leaf')} Global Rank: <b>#{pos}</b>{_streak_bonus}",
        parse_mode="HTML")

async def cmd_top(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = await users_col.find({}, {"name": 1, "nickname": 1, "wins": 1, "losses": 1, "rank": 1, "level": 1}).sort([("wins", -1)]).limit(10).to_list(None)
    if not rows: await update.message.reply_text("<tg-emoji emoji-id='5426976939850080222'>🏆</tg-emoji> No players yet!"); return
    lines=[]
    medals=["<tg-emoji emoji-id='5426976939850080222'>🥇</tg-emoji>","<tg-emoji emoji-id='5424892463372312872'>🥈</tg-emoji>","<tg-emoji emoji-id='5224388744156557558'>🥉</tg-emoji>"]
    for i,u in enumerate(rows,1):
        dn=u["nickname"] if u["nickname"] else u["name"]
        medal=medals[i-1] if i<=3 else f"<b>{i}.</b>"
        lines.append(f"{medal} {dn} ⟨{u['rank']}⟩ Lv.{u['level']} — {u['wins']}W")
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5426976939850080222'>🏆</tg-emoji> <b>Top 10 Shinobi</b>\n━━━━━━━━━━━━━━━━━━━━\n"+"\n".join(lines),
        parse_mode="HTML")

async def cmd_tournament(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = await users_col.find({}, {"name": 1, "nickname": 1, "wins": 1, "losses": 1, "rank": 1, "level": 1}).sort([("wins", -1)]).limit(8).to_list(None)
    if not rows: await update.message.reply_text("<tg-emoji emoji-id='5426976939850080222'>🏟️</tg-emoji> No players yet!"); return
    lines=[]
    for i,u in enumerate(rows,1):
        dn=u["nickname"] if u["nickname"] else u["name"]
        wr=f"{u['wins']}/{u['wins']+u['losses']}"
        lines.append(f"<b>{i}.</b> {hesc(dn)} ⟨{hesc(u['rank'])}⟩ Lv.{u['level']} — {u['wins']}W ({wr})")
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5426976939850080222'>🏟️</tg-emoji> <b>Tournament Standings</b>\n━━━━━━━━━━━━━━━━━━━━\n"+"\n".join(lines)+
        "\n\n<i>Reply to a user's message then /battle to challenge!</i>",
        parse_mode="HTML")

async def cmd_gift(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    reply=update.message.reply_to_message; args=ctx.args
    if not reply or not args or not args[0].isdigit():
        await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Reply to user + <code>/gift &lt;amount&gt;</code>",
                                        parse_mode="HTML"); return
    if not reply.from_user:
        await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Cannot gift to this message!",
                                        parse_mode="HTML"); return
    amount=int(args[0]); uid=str(update.effective_user.id); opp_id=str(reply.from_user.id)
    if uid==opp_id: await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Can't gift yourself!"); return
    user=await db_get(uid)
    if user["coins"]<amount: await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Not enough NC!", parse_mode="HTML"); return
    opp=await db_get(opp_id)
    if not opp: await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Target has no account!", parse_mode="HTML"); return
    await db_set(uid,coins=user["coins"]-amount)
    await db_set(opp_id,coins=opp["coins"]+amount)
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5424830993800373710'>🎁</tg-emoji> Sent <b>{amount:,} NC</b> to <b>{reply.from_user.first_name}</b>!",
        parse_mode="HTML")

# ─── /transform ─────────────────────────────────────────────────
TF_PER_PAGE = 5

def _build_transform_entries(chars, user):
    """Return list of (char_name, form_name, req_chakra, can_tf, buffs_str) tuples."""
    entries = []
    for c in chars:
        cd = get_cdata(c["char_name"])
        if not cd or not cd.get("form"):
            continue
        f = cd["form"]
        r = f["req_chakra"]
        can_tf = user["chakra"] >= r
        bs = "  ".join(f"{k.upper()}:+{v}" for k, v in f["buff"].items() if v > 0)
        entries.append((c["char_name"], f["name"], r, can_tf, bs or "—"))
    return entries

def _transform_page_text(entries, user, page):
    """Build the formatted text for one page of /transform."""
    total   = len(entries)
    pages   = max(1, (total + TF_PER_PAGE - 1) // TF_PER_PAGE)
    page    = max(0, min(page, pages - 1))
    start   = page * TF_PER_PAGE
    batch   = entries[start:start + TF_PER_PAGE]
    chakra  = user["chakra"]
    stones  = user.get("stones", 0)
    stone_ok = stones > 0

    header = (
        f"{pe('round','🔄')} <b>Transformations</b>\n\n"
        f"{pe('chakra','💠')}: <b>{chakra:,}</b>    "
        f"{pe('stone','🪨')} Stones: <b>{stones}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Transform in battle: need Stone + Chakra!\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    card_lines = []
    for char_name, form_name, req, can_tf, buffs in batch:
        status = "✅" if (can_tf and stone_ok) else "❌"
        card_lines.append(
            f"{pe('round','🔄')} <b>{hesc(char_name)}</b> → <b>{hesc(form_name)}</b>\n\n"
            f"  Req: {req:,} {pe('round','🔄')}  {status}\n\n"
            f"  Buffs: <b>{hesc(buffs)}</b>"
        )
    sep = "\n─────────────────────────────\n"
    body = sep.join(card_lines) if card_lines else f"❌ No transformations available for your characters!"

    footer = f"\n\n<i>Page {page+1}/{pages}</i>" if pages > 1 else ""
    return header + body + footer, page, pages

async def cmd_transform(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid   = str(update.effective_user.id)
    user  = await db_get(uid)
    chars = await db_chars(uid)
    entries = _build_transform_entries(chars, user)
    text, page, pages = _transform_page_text(entries, user, 0)
    kb = []
    nav = []
    if pages > 1:
        nav.append(Btn("▶ Next", callback_data=f"tfpg:{uid}:1"))
        kb.append(nav)
    await update.message.reply_text(text, parse_mode="HTML",
                                    reply_markup=Kbd(kb) if kb else None)

async def cb_transform_page(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts = q.data.split(":")
    uid   = parts[1]; page = int(parts[2])
    if str(q.from_user.id) != uid:
        await q.answer("Not your menu!", show_alert=True); return
    user  = await db_get(uid)
    chars = await db_chars(uid)
    entries = _build_transform_entries(chars, user)
    text, page, pages = _transform_page_text(entries, user, page)
    kb = []
    nav = []
    if page > 0:
        nav.append(Btn("◀ Prev", callback_data=f"tfpg:{uid}:{page-1}"))
    if page < pages - 1:
        nav.append(Btn("▶ Next", callback_data=f"tfpg:{uid}:{page+1}"))
    if nav:
        kb.append(nav)
    await _safe_edit(q, text, kb if kb else None)

# ─── /moves /jutsu ───────────────────────────────────────────────
async def cmd_moves(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid=str(update.effective_user.id); chars=await db_chars(uid)
    if not chars: await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> No characters!"); return
    kb=[[Btn(f"{c['char_name'][:30]}",callback_data=f"mv:{c['id']}")] for c in chars[:20]]
    await update.message.reply_text("<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> <b>Select character for moveset:</b>",
                                    parse_mode="HTML",reply_markup=Kbd(kb))

async def cb_moves_view(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    uid=str(q.from_user.id); cid=int(q.data.split(":")[1])
    row = _cdoc(await chars_col.find_one({"_id": cid, "uid": uid}, {"char_name": 1, "level": 1}))
    if not row: return
    cd=get_cdata(row["char_name"])
    if not cd: return
    char_lv = row.get("level", 1)
    unlocked = get_char_moves(row["char_name"], char_lv)
    all_moves = cd["moves"]
    lines=[]
    for i,m in enumerate(all_moves,1):
        strong=[n for n in ALL_NATURES if type_mult(m["type"],n)>1.0]
        hint=f"vs {','.join(strong[:2])}" if strong else ""
        eff = fmt_effect(m.get("effect",""))
        eff_txt = f" | {eff}" if eff else ""
        locked = i > len(unlocked)
        if locked:
            unlock_lv = 10 if i==2 else (20 if i==3 else 30)
            lines.append(f"<b>{i}. {m['name']}</b> {nat_icon(m['type'])} <i>(locked — Lv{unlock_lv})</i>\n"
                         f"  Pwr:{m['power']} | Acc:{m['acc']}% | Chk:{m['chakra']}{eff_txt} {hint}")
        else:
            lines.append(f"<b>{i}. {m['name']}</b> {nat_icon(m['type'])}\n"
                         f"  Pwr:{m['power']} | Acc:{m['acc']}% | Chk:{m['chakra']}{eff_txt} {hint}\n"
                         f"  <i>{m.get('desc','')}</i>")
    await _safe_edit(q,
        f"<b>{row['char_name']} Lv.{char_lv} — Moves</b>\n"
        f"Unlocked: {len(unlocked)}/{len(all_moves)}\n━━━━━━━━━━━━\n\n"+"\n\n".join(lines),
        [[Btn("Back",callback_data=f"sv:{cid}")]])

async def cmd_jutsu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid = str(update.effective_user.id)
    # If user passed a jutsu name (e.g. /jutsu fire ball), search for it
    if ctx.args:
        query = " ".join(ctx.args).lower().strip()
        # Search in the move library M
        matched_key = None
        matched_move = None
        for k, mv_data in M.items():
            if query in mv_data["name"].lower() or query in k.lower():
                matched_key = k
                matched_move = mv_data
                break
        # Also search partial matches if no direct hit
        if not matched_move:
            for k, mv_data in M.items():
                move_lower = mv_data["name"].lower()
                if any(word in move_lower for word in query.split() if len(word) >= 3):
                    matched_key = k
                    matched_move = mv_data
                    break
        if matched_move:
            tp = matched_move.get("type","?")
            nat_icon_str = NAT_EMO.get(tp,"")
            eff = matched_move.get("effect","—").replace(":"," +").replace("_"," ")
            desc_txt = (
                f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>{matched_move['name']}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"<tg-emoji emoji-id='5426872512015244606'>🌿</tg-emoji> <b>Type:</b> {tp} {nat_icon_str}\n"
                f"<tg-emoji emoji-id='5998841304052669228'>💥</tg-emoji> <b>Power:</b> {matched_move['power']}\n"
                f"<tg-emoji emoji-id='5427397421443325675'>🎯</tg-emoji> <b>Accuracy:</b> {matched_move['acc']}%\n"
                f"<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> <b>Chakra Cost:</b> {matched_move['chakra']}\n"
                f"✨ <b>Effect:</b> {eff.title()}\n\n"
                f"📖 <i>{matched_move.get('desc','No description.')}</i>"
            )
            # Try to get a jutsu image
            jutsu_img = JUTSU_CACHE.get(matched_move["name"]) or MOVE_IMAGE_CACHE.get(matched_key or "")
            if jutsu_img:
                try:
                    await update.message.reply_photo(photo=jutsu_img, caption=desc_txt[:1020],
                                                     parse_mode="HTML")
                    return
                except: pass
            await update.message.reply_text(desc_txt, parse_mode="HTML")
        else:
            await update.message.reply_text(
                f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Jutsu <b>\"{' '.join(ctx.args)}\"</b> not found!\n\n"
                f"_Try: `/jutsu rasengan`, `/jutsu chidori`, `/jutsu fire ball`_",
                parse_mode="HTML")
        return
    # No args — show character selection menu (original behaviour)
    chars = await db_chars(uid)
    if not chars:
        await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> No characters! Use /summon first."); return
    kb = [[Btn(f"{c['char_name'][:30]}", callback_data=f"mv:{c['id']}")] for c in chars[:20]]
    await update.message.reply_text(
        "<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> <b>Jutsu Reference</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        "_Select a character to view their moveset, or use:_\n"
        "`/jutsu <name>` — look up any jutsu directly\n\n"
        "_Example: `/jutsu rasengan`, `/jutsu amaterasu`_",
        parse_mode="HTML", reply_markup=Kbd(kb))

# ─── /help ──────────────────────────────────────────────────────
HELP_TEXTS = {
    "account":(
        f"{pe('team')} <b>Account Commands</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        "/start — Main menu + banner\n"
        "/profile — Full profile &amp; stats\n"
        "/mychar — Browse character list\n"
        "/team — Manage active team (6 slots)\n"
        "/rank — Your global rank\n"
        "/nickname <code>&lt;name&gt;</code> — Set display name\n"
        "/daily — Daily NC + chakra reward\n"
        "/mission — Complete daily missions\n"
        "/gift — Gift NC to a teammate"
    ),
    "battle":(
        f"{pe('sword')} <b>Battle Commands</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        "/explore — Village-based wild battles\n"
        "  <i>EXP · NC · Chakra · Stone drops · Team battles!</i>\n"
        "/battle — Reply to a user to start PvP\n"
        "/transform — View your transform list\n"
        "/heal — Restore HP (300 NC)\n"
        "/tournament — Rankings &amp; standings\n\n"
        f"{pe('lightning')} <b>Battle Mechanics:</b>\n"
        "• Village choice controls enemy type (/village)\n"
        "• Speed decides who strikes first\n"
        "• Level bonus: +2% damage per level above enemy\n"
        "• Nature advantage: up to 2× damage multiplier\n"
        "• Character falls? Auto-switch to next team member!\n"
        "• 4% stone drop chance per explore battle\n"
        "• Transform when chakra is full + 1 Stone equipped\n"
        "• Tailed Beast hosts gain passive power bonuses"
    ),
    "economy":(
        f"{pe('coin')} <b>Economy</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        "/summon — Pull new characters!\n"
        "  Single <b>500 NC</b> | 10× <b>4500 NC</b>\n"
        "  Legendary <b>25,000 NC</b>\n"
        "/shop — Browse the item shop\n"
        "/buy <code>&lt;id&gt;</code> — Purchase an item\n"
        "/inventory — Your items &amp; stones\n"
        "/daily — 500–2000 NC + streak bonus\n"
        "/mission — Complete missions for NC\n\n"
        "💡 <b>Items:</b> <code>heal</code> | <code>chakra_pill</code> | <code>exp_boost</code> | <code>stone</code>\n"
        "💡 <b>Scrolls:</b> <code>rare_scroll</code> | <code>epic_scroll</code> | <code>legendary_scroll</code>"
    ),
    "train":(
        "🏋️ <b>Training &amp; Levels</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        "/train — Level up or stat-train your characters\n\n"
        f"  {pe('arrow_up')} <b>Level Up cost:</b>\n"
        "    1 level = <b>40 NC</b>\n"
        "    5 levels = <b>400 NC</b>\n"
        "    10 levels = <b>700 NC</b>\n"
        "    Max Level: <b>100!</b>\n\n"
        "  🏋️ <b>Stat Training</b> (30 min, free):\n"
        "    ATK | DEF | SPD | HP\n"
        "    Gain +1 to +3 PP per session\n\n"
        f"{pe('exp')} <b>PP Grades:</b> E → D → C → B → A → A+ → S (31)\n\n"
        "/relearn — Recover a forgotten move (Lv100 required)\n"
        "<i>Characters unlock moves at Lv10, Lv20, Lv30</i>"
    ),
    "systems":(
        f"{pe('leaf')} <b>Game Systems</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        "/nature — 20-type nature chart\n"
        "/kekkei — Bloodline (KG) abilities\n"
        "/ability — Your active bonuses\n"
        "/beast — Tailed Beast lore\n"
        "/jutsu — Full moveset reference\n"
        "/village — Join a village (stat bonuses)\n"
        "/clan — Join a clan (Kekkei Genkai)\n"
        "/chakra — Chakra &amp; stone status\n\n"
        f"{pe('stone')} <b>Stone System:</b>\n"
        "• 4% drop chance from explore battles\n"
        "• Also available in the /shop (2000 NC)\n"
        "• Required to TRANSFORM in battle\n"
        "• Transform = massive power boost for 1 battle!"
    ),
}

# ─── LEGENDARY BOSSES ────────────────────────────────────────────
# Ring emoji IDs for boss drop decoration (NarutoPack_Emoji 💍)
_BOSS_RING_EMOJI = [
    "5453859582537381825","5453936934898383623","5454042226021646604",
    "5451985645356465948","5454389753300401546","5451666744034737160",
    "5454296543920143326","5453983715682171125","5454122580564786042",
]
def _boss_ring(i: int = 0) -> str:
    eid = _BOSS_RING_EMOJI[i % len(_BOSS_RING_EMOJI)]
    return f'<tg-emoji emoji-id="{eid}">💍</tg-emoji>'

LEGENDARY_BOSSES = [
    {"name":"Kaguya Otsutsuki","emoji":"👁️","pe_id":"5771890962934534474","nat":"Yin-Yang","hp":8000,"atk":420,"def":300,"spd":280,
     "desc":"The Rabbit Goddess — mother of chakra itself. Infinite Tsukuyomi wielder.",
     "nc":(8000,15000),"chakra":(500,1200),"exp":(800,1500),"stone_chance":0.40,
     "moves":[M["tbb"],M["izanagi"],M["divine_palm"] if "divine_palm" in M else M["almighty_push"]]},
    {"name":"Madara Uchiha","emoji":"🌀","pe_id":"5900182374800428625","nat":"Fire","hp":6500,"atk":380,"def":280,"spd":260,
     "desc":"The legendary Uchiha who became the Ten-Tails Jinchuriki.",
     "nc":(6000,12000),"chakra":(400,1000),"exp":(600,1200),"stone_chance":0.35,
     "moves":[M["perfect_susanoo"],M["amaterasu"],M["tengai_shinsei"] if "tengai_shinsei" in M else M["kirin"]]},
    {"name":"Pain (Nagato)","emoji":"<tg-emoji emoji-id='5798483635199807367'>🔵</tg-emoji>","pe_id":"5897759424834965828","nat":"Yin","hp":5500,"atk":340,"def":260,"spd":250,
     "desc":"Leader of the Akatsuki — the Six Paths of Pain.",
     "nc":(5000,10000),"chakra":(350,900),"exp":(500,1000),"stone_chance":0.30,
     "moves":[M["almighty_push"],M["planetary_devastation"] if "planetary_devastation" in M else M["almighty_push"],M["shinra_tensei"] if "shinra_tensei" in M else M["almighty_push"]]},
    {"name":"Obito Uchiha","emoji":"🌑","pe_id":"5897719988445254285","nat":"Fire","hp":5000,"atk":320,"def":240,"spd":270,
     "desc":"The masked man who controlled the Nine-Tails attack on Konoha.",
     "nc":(4500,9000),"chakra":(300,800),"exp":(450,900),"stone_chance":0.28,
     "moves":[M["perfect_susanoo"],M["amaterasu"],M["izanami"] if "izanami" in M else M["chidori"]]},
    {"name":"Itachi Uchiha","emoji":"<tg-emoji emoji-id='5426872512015244606'>🌸</tg-emoji>","pe_id":"6043876132095266850","nat":"Fire","hp":4500,"atk":360,"def":220,"spd":300,
     "desc":"The legendary ANBU prodigy who carries the weight of his clan.",
     "nc":(4000,8000),"chakra":(280,700),"exp":(400,800),"stone_chance":0.25,
     "moves":[M["tsukuyomi"],M["amaterasu"],M["totsuka_blade"] if "totsuka_blade" in M else M["perfect_susanoo"]]},
    {"name":"Hashirama Senju","emoji":"🌲","pe_id":"5774001999490060567","nat":"Wood","hp":7000,"atk":360,"def":340,"spd":240,
     "desc":"The God of Shinobi — first Hokage and Wood Release master.",
     "nc":(6500,13000),"chakra":(450,1100),"exp":(700,1400),"stone_chance":0.38,
     "moves":[M["wood_dragon"],M["thousand_hands"] if "thousand_hands" in M else M["tbb"],M["sage_strike"] if "sage_strike" in M else M["rasengan"]]},
    {"name":"Sasuke Uchiha","emoji":"⚡","pe_id":"5901990444362895405","nat":"Fire","hp":4000,"atk":350,"def":200,"spd":320,
     "desc":"The last Uchiha — Indra's reincarnation and rival to Naruto.",
     "nc":(3500,7000),"chakra":(260,650),"exp":(380,750),"stone_chance":0.22,
     "moves":[M["kirin"],M["amaterasu"],M["perfect_susanoo"]]},
    {"name":"Naruto Uzumaki","emoji":"<tg-emoji emoji-id='5426872512015244606'>🍃</tg-emoji>","pe_id":"5773756533519160001","nat":"Wind","hp":4200,"atk":360,"def":210,"spd":310,
     "desc":"The Seventh Hokage — child of prophecy in Baryon Mode.",
     "nc":(3800,7500),"chakra":(270,680),"exp":(400,800),"stone_chance":0.22,
     "moves":[M["rasenshuriken"],M["tbb"],M["baryon_strike"]]},
]

# ─── /map ────────────────────────────────────────────────────────
async def cmd_map(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid   = str(update.effective_user.id)
    user  = await db_get(uid)
    cur   = user.get("village","Konoha")
    lines = []
    for vk, vi in VILLAGES.items():
        vinfo = VILLAGE_INFO.get(vk, {})
        n_chars = len([c for c in CHARACTERS if c["village"] == vk])
        areas   = VILLAGE_AREAS.get(vk, [])
        marker  = "<tg-emoji emoji-id='5427342518876381603'>📍</tg-emoji>" if vk == cur else "  "
        lines.append(
            f"{marker} {vi['emoji']} <b>{vinfo.get('full', vk)}</b>\n"
            f"     <i>{vinfo.get('country','')}</i> · {vinfo.get('kage','')} · {n_chars} shinobi · {len(areas)} areas"
        )
    kb = [
        [Btn("Travel to Area", callback_data="menu:village"),
         Btn("Explore Now", callback_data="menu:explore")],
        [Btn("Village Info", callback_data=f"vp:{cur}")],
    ]
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5425114616260731920'>🗺️</tg-emoji> <b>World Map — Ninja Nations</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5427342518876381603'>📍</tg-emoji> = Your current location\n\n"
        + "\n\n".join(lines) +
        f"\n\n_Use /travel to explore areas within your village\n"
        f"Use /village to move to a different village_",
        parse_mode="HTML", reply_markup=Kbd(kb))

# ─── /location ───────────────────────────────────────────────────
async def cmd_location(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid  = str(update.effective_user.id)
    user = await db_get(uid)
    vn   = user.get("village","Konoha")
    vi   = VILLAGES.get(vn, {})
    vinfo= VILLAGE_INFO.get(vn, {})
    areas= VILLAGE_AREAS.get(vn, [])
    n_chars = len([c for c in CHARACTERS if c["village"] == vn])
    bonuses = "\n".join(
        f"  • +{int(v*100)}% {k.upper()}"
        for k, v in vi.items() if isinstance(v, float) and v > 0
    )
    kb = [
        [Btn("Explore Areas", callback_data="menu:village"),
         Btn("Battle Here", callback_data="menu:explore")],
        [Btn("Boss Battle!", callback_data=f"boss:random:{uid}")],
    ]
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5427342518876381603'>📍</tg-emoji> <b>Current Location</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{vi.get('emoji', pe('village'))} <b>{vinfo.get('full', vn)}</b>\n"
        f"_{vinfo.get('country','')} · {vinfo.get('kage','Kage')}_\n\n"
        f"_{vi.get('desc','')}_\n\n"
        f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> <b>Battle Bonuses:</b>\n{bonuses or '  • +5% all stats'}\n\n"
        f"<tg-emoji emoji-id='5425113284820869526'>🥷</tg-emoji> <b>Shinobi here:</b> {n_chars} characters\n"
        f"<tg-emoji emoji-id='5427342518876381603'>📍</tg-emoji> <b>Explorable Areas:</b> {len(areas)}\n\n"
        f"_Use /travel to pick a specific area to fight in!_",
        parse_mode="HTML", reply_markup=Kbd(kb))

# ─── /hunt ───────────────────────────────────────────────────────
HUNT_COOLDOWN = 1800  # 30 minutes

async def cmd_hunt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid  = str(update.effective_user.id)
    user = await db_get(uid)
    now  = datetime.utcnow()
    hunt_last = user.get("hunt_last","")
    if hunt_last:
        try:
            diff = (now - datetime.fromisoformat(hunt_last)).total_seconds()
            if diff < HUNT_COOLDOWN:
                m = int((HUNT_COOLDOWN - diff) // 60)
                await update.message.reply_text(
                    f"<tg-emoji emoji-id='5426872512015244606'>🌿</tg-emoji> <b>Hunt Cooldown</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"<tg-emoji emoji-id='5803204762035818905'>⏳</tg-emoji> You need to rest! <b>{m} min</b> remaining.\n"
                    f"_Your senses need to sharpen before the next hunt._",
                    parse_mode="HTML"); return
        except: pass
    # Determine hunt outcome
    vn   = user.get("village","Konoha")
    vi   = VILLAGES.get(vn,{})
    roll = random.random()
    if roll < 0.08:  # 8% — stone find
        reward_type = "stone"
        await db_set(uid, stones=user.get("stones",0)+1, hunt_last=now.isoformat())
        txt = (f"<tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji> <b>RARE FIND!</b> Transform Stone discovered!\n\n"
               f"You searched the wild terrain near {VILLAGE_INFO.get(vn,{}).get('full',vn)}\n"
               f"and unearthed a <b>Transform Stone</b> hidden in the earth!\n\n"
               f"<tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji> Stones: <b>{user.get('stones',0)+1}</b>\n"
               f"<i>Use it in battle to transform!</i>")
    elif roll < 0.40:  # 32% — chakra crystals
        chakra_gain = random.randint(2, 10)
        await db_set(uid, chakra=user["chakra"]+chakra_gain, hunt_last=now.isoformat())
        txt = (f"<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> <b>Chakra Crystal Found!</b>\n\n"
               f"You hunted through the wilderness and found a chakra-infused crystal!\n\n"
               f"<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> +<b>{chakra_gain} Chakra</b> absorbed!\n"
               f"Total: <b>{user['chakra']+chakra_gain:,}</b>")
    elif roll < 0.70:  # 30% — NC loot
        nc_gain = random.randint(200, 800)
        nc_bonus = int(nc_gain * vi.get("exp", 0))
        nc_total = nc_gain + nc_bonus
        await db_set(uid, coins=user["coins"]+nc_total, hunt_last=now.isoformat())
        txt = (f"<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> <b>Loot Found!</b>\n\n"
               f"You tracked down a defeated enemy's hidden cache!\n\n"
               f"<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> +<b>{nc_total:,} NC</b> recovered!\n"
               f"_Village bonus included_")
    else:  # 30% — nothing
        await db_set(uid, hunt_last=now.isoformat())
        txt = (f"<tg-emoji emoji-id='5426872512015244606'>🌿</tg-emoji> <b>Nothing found...</b>\n\n"
               f"You searched the wilds near {VILLAGE_INFO.get(vn,{}).get('full',vn)}\n"
               f"but returned empty-handed.\n\n"
               f"_Try again in 30 minutes. Maybe your luck will change!_")
    kb = [[Btn("Explore", callback_data="menu:explore"),
           Btn("Boss Battle", callback_data=f"boss:random:{uid}")]]
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5426872512015244606'>🌿</tg-emoji> <b>Hunt Results</b>\n━━━━━━━━━━━━━━━━━━━━\n{txt}\n\n"
        f"_Next hunt available in 30 minutes_",
        parse_mode="HTML", reply_markup=Kbd(kb))

# ─── /dataweapon ─────────────────────────────────────────────────
async def cmd_dataweapon(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    args = ctx.args
    RAR_ORDER = ["Common","Uncommon","Rare","Epic","Legendary","Mythic"]
    RAR_ICON  = {"Common":"⚪","Uncommon":"🟢","Rare":"🔵","Epic":"🟣","Legendary":"🟡","Mythic":"🔴"}

    # /dataweapon <name> — search for a specific weapon
    if args:
        query = " ".join(args).lower().strip()
        matches = [w for w in WEAPONS if query in w["name"].lower() or query in w.get("ability","").lower()]
        if not matches:
            await update.message.reply_text(
                f"{pe('xmark','❌')} No weapon found for <b>{hesc(query)}</b>.\n"
                f"Use <code>/dataweapon</code> with no args to browse all weapons.",
                parse_mode="HTML"); return
        cards = []
        for w in matches[:8]:
            rar_icon  = RAR_ICON.get(w["rarity"], "⚪")
            buff_type = w.get("buff", {}).get("type", "—")
            buff_val  = w.get("buff", {}).get("val", 0)
            buff_str  = f"{buff_type}({buff_val})" if buff_val else buff_type
            raw_desc  = w.get("desc", "No description.")
            # Expand short descriptions with extra lore detail
            if len(raw_desc) < 40:
                raw_desc = raw_desc + " — a weapon forged with exceptional craftsmanship, infused with powerful chakra that amplifies the user's combat abilities in battle."
            cards.append(
                f"{rar_icon} <b>{hesc(w['name'])}</b> [{hesc(w['rarity'])}]\n\n"
                f"{pe('round','🔄')} ATK: <b>{w['atk']}</b> |\n"
                f" {pe('coin','🪙')}: <b>{w['price']:,} NC</b>\n\n"
                f"{pe('round','🔄')} Ability: <b>{hesc(w['ability'])}</b> — {hesc(buff_str)}.\n"
                f"───────\n"
                f"Details:\n\n"
                f"  <i>{hesc(raw_desc)}</i>"
            )
        await update.message.reply_text(
            f"{pe('round','🔄')}<b>Weapon Data — Search: {hesc(query)}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            + "\n\n".join(cards),
            parse_mode="HTML"); return

    # No args — show rarity summary
    by_rar: dict = {}
    for w in WEAPONS:
        by_rar.setdefault(w["rarity"], []).append(w)
    lines = []
    for rar in RAR_ORDER:
        ws = by_rar.get(rar, [])
        if not ws: continue
        icon = RAR_ICON.get(rar,"⚪")
        sample = ", ".join(w["name"] for w in ws[:3])
        atk_vals = [w["atk"] for w in ws]
        lines.append(
            f"{icon} <b>{rar}</b> ({len(ws)} weapons)\n"
            f"  ATK range: {min(atk_vals)}–{max(atk_vals)}\n"
            f"  Examples: <i>{hesc(sample)}...</i>"
        )
    await update.message.reply_text(
        f"{pe('kunai','🗡')} <b>Weapon Database</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Total weapons: {len(WEAPONS)}</i>\n\n"
        + "\n\n".join(lines)
        + f"\n\n<i>Use <code>/dataweapon &lt;name&gt;</code> to search by weapon or ability name.\n"
          f"Use <code>/shop</code> to buy weapons.</i>",
        parse_mode="HTML")

# ─── /boss ───────────────────────────────────────────────────────
async def cmd_boss(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid  = str(update.effective_user.id)
    user = await db_get(uid)
    now  = datetime.utcnow()
    boss_last = user.get("boss_last","")
    if boss_last:
        try:
            diff = (now - datetime.fromisoformat(boss_last)).total_seconds()
            if diff < 7200:  # 2hr cooldown
                h = int((7200 - diff) // 3600); m = int(((7200-diff)%3600)//60)
                await update.message.reply_text(
                    f"<tg-emoji emoji-id='5224388744156557558'>🏯</tg-emoji> <b>Boss Cooldown</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"<tg-emoji emoji-id='5803204762035818905'>⏳</tg-emoji> The boss is recovering! <b>{h}h {m}m</b> remaining.\n"
                    f"_Even Legendary shinobi need time to recover._",
                    parse_mode="HTML"); return
        except: pass
    # Show boss selection with custom emoji
    rows = []
    for i in range(0, len(LEGENDARY_BOSSES), 2):
        row = []
        for j in range(2):
            if i + j < len(LEGENDARY_BOSSES):
                b = LEGENDARY_BOSSES[i+j]
                row.append(Btn(f"{b['name']}", callback_data=f"boss:{i+j}:{uid}"))
        rows.append(row)
    # Build boss list with custom emoji using HTML
    boss_lines = []
    for i, b in enumerate(LEGENDARY_BOSSES):
        pe_id = b.get("pe_id","")
        ring  = _boss_ring(i)
        if pe_id:
            boss_icon = f'<tg-emoji emoji-id="{pe_id}">👹</tg-emoji>'
        else:
            boss_icon = b["emoji"]
        boss_lines.append(f"{ring} {boss_icon} <b>{hesc(b['name'])}</b> — {b['nat']} · HP {b['hp']:,}")
    boss_list = "\n".join(boss_lines)
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5224388744156557558'>🏯</tg-emoji> <b>Legendary Boss Battle</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji> These are the most powerful enemies!\n"
        f"Defeat them for <b>massive NC, Chakra, and Stones</b>!\n\n"
        f"{boss_list}\n\n"
        f"<tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji> Stone drop: <b>22–40%</b> chance\n"
        f"{pe('coin')} NC reward: up to <b>15,000 NC</b>!\n\n"
        f"<i>Choose your opponent:</i>",
        parse_mode="HTML", reply_markup=Kbd(rows))

async def cb_boss(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q   = update.callback_query; await q.answer()
    parts = q.data.split(":")
    idx = parts[1]; uid = parts[2]
    if str(q.from_user.id) != uid:
        await q.answer("Not your battle!", show_alert=True); return
    user = await db_get(uid)
    team = await db_team(uid)
    if not team:
        await q.answer("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Set a team first with /team!", show_alert=True); return
    if idx == "random":
        boss = random.choice(LEGENDARY_BOSSES)
    else:
        idx = int(idx)
        if idx >= len(LEGENDARY_BOSSES):
            await q.answer("Unknown boss!", show_alert=True); return
        boss = LEGENDARY_BOSSES[idx]
    team_sorted = sorted(team, key=lambda c: c.get("slot",99))
    p_row = team_sorted[0]
    cd    = get_cdata(p_row["char_name"])
    if not cd:
        await q.answer("Character error!", show_alert=True); return
    vi_i  = VILLAGES.get(user.get("village","Konoha"), {})
    plv   = p_row["level"]
    php   = int(calc_stat(cd["base"]["hp"], p_row["pp_hp"], plv) * (1 + vi_i.get("hp",0)))
    p_atk = calc_stat(cd["base"]["atk"], p_row["pp_atk"], plv)
    p_def = calc_stat(cd["base"]["def"], p_row["pp_def"], plv)
    p_spd = int(calc_stat(cd["base"]["speed"], p_row["pp_spd"], plv) * (1 + vi_i.get("spd",0)))
    pkg   = CLAN_KG.get(cd["clan"],"None")
    ehp   = boss["hp"]
    e_spd = boss["spd"]
    p_goes_first = p_spd >= e_spd
    form  = cd.get("form"); req_chakra = form["req_chakra"] if form else 999999
    wild  = {
        "name": boss["name"], "nat": boss["nat"],
        "hp": ehp, "atk": boss["atk"], "def": boss["def"], "spd": e_spd,
        "photo": PHOTO_CACHE.get(boss["name"]),
        "nc":    boss["nc"], "chakra": boss["chakra"], "exp": boss["exp"],
        "moves": boss.get("moves", [M["tbb"], M["amaterasu"], M["kirin"]]),
        "is_char": False, "is_boss": True,
        "stone_chance_override": boss.get("stone_chance", 0.30),
    }
    equipped_wid_b = user.get("equipped_weapon")
    equipped_weapon_b = get_weapon_by_id(equipped_wid_b) if equipped_wid_b else None
    # Bijuu availability for boss battle
    tb_name_b = cd.get("tailed_beast")
    bijuu_avail_b = bool(tb_name_b and tb_name_b in BEASTS)
    session = {
        "p_char":p_row["char_name"],"p_char_id":p_row["id"],"p_level":plv,
        "p_hp":php,"p_max_hp":php,"p_atk":p_atk,"p_def":p_def,
        "p_spd":p_spd,"p_nat":cd["nature"],"p_kg":pkg,
        "p_status":"","p_dot":None,"p_def_broken":False,"p_revived":False,
        "p_battle_chakra":0,"p_transformed":False,"transform_available":False,
        "req_chakra":req_chakra,
        "enemy":wild,"e_hp":ehp,"e_max_hp":ehp,"e_level":plv+15,
        "e_status":"","e_dot":None,"e_def_broken":False,
        "is_photo":False,"turn":0,"uid":uid,"p_goes_first":p_goes_first,
        "team_order":[c["id"] for c in team_sorted],
        "team_idx":0,
        "team_map":{c["id"]:c for c in team_sorted},
        "is_boss_battle": True,
        "equipped_weapon": equipped_weapon_b,
        "weapon_used": False,
        "bijuu_avail": bijuu_avail_b,
        "bijuu_active": False,
        "bijuu_turns_left": 0,
        "bijuu_beast_name": tb_name_b or "",
        "started_at": time.time(),
    }
    EX[uid] = session
    transform_avail = (session["p_battle_chakra"] >= req_chakra and
                       user.get("stones",0) >= 1 and form and not session["p_transformed"])
    session["transform_available"] = transform_avail
    await db_set(uid, boss_last=datetime.utcnow().isoformat())
    txt  = fmt_battle_text(session)
    pe_id = boss.get("pe_id","")
    boss_icon = f'<tg-emoji emoji-id="{pe_id}">👹</tg-emoji>' if pe_id else hesc(boss["emoji"])
    boss_banner = (f"\n<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji> <i>LEGENDARY BOSS: {boss_icon} <b>{hesc(boss['name'])}</b></i>"
                   f"\n<i>{hesc(boss['desc'])}</i>")
    txt  = txt + boss_banner
    kb   = move_btns_explore(get_char_moves(p_row["char_name"], plv), uid, transform_avail,
                             weapon=equipped_weapon_b, weapon_used=False,
                             bijuu_avail=bijuu_avail_b)
    boss_photo = PHOTO_CACHE.get(boss["name"])
    if boss_photo:
        try:
            await q.edit_message_caption(caption=txt[:1020], parse_mode="HTML",
                                         reply_markup=Kbd(kb))
            session["is_photo"] = True
            return
        except: pass
    try:
        await q.edit_message_text(txt[:4096], parse_mode="HTML", reply_markup=Kbd(kb))
    except: pass

# ─── /adminclan — Admin: set a user as clan admin ────────────────
async def cmd_adminclan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid != ADMIN_ID:
        await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Admin only."); return
    args = ctx.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "<tg-emoji emoji-id='5426895906702107044'>📋</tg-emoji> <b>Usage:</b> <code>/adminclan <clan_name> <user_id></code>\n\n"
            "_Example: `/adminclan Uchiha 123456789`_\n\n"
            f"Valid clans: {', '.join(list(CLANS.keys())[:8])}...",
            parse_mode="HTML"); return
    user_id   = args[-1]
    clan_name = " ".join(args[:-1])
    if clan_name not in CLANS:
        await update.message.reply_text(
            f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Clan <code>{clan_name}</code> not found!\n"
            f"Valid: {', '.join(list(CLANS.keys())[:12])}",
            parse_mode="HTML"); return
    target = await db_get(user_id)
    if not target:
        await update.message.reply_text(
            f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> User <code>{user_id}</code> not found in the bot.", parse_mode="HTML"); return
    await clans_col.replace_one(
        {"_id": clan_name},
        {"_id": clan_name, "admin_uid": user_id},
        upsert=True)
    kg = CLAN_KG.get(clan_name, "None")
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> <b>Clan Admin Set!</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5224388744156557558'>🧬</tg-emoji> Clan: <b>{clan_name}</b>\n"
        f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> KG: {kg}\n"
        f"<tg-emoji emoji-id='5425113284820869526'>👤</tg-emoji> Admin: <code>{user_id}</code> ({display_name(target)})\n\n"
        f"_New join requests for {clan_name} Clan will now require this admin's approval._",
        parse_mode="HTML")

# ─── /equip ─────────────────────────────────────────────────────
async def cmd_equip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid  = str(update.effective_user.id)
    user = await db_get(uid)
    args = ctx.args
    if not args:
        equipped_id = user.get("equipped_weapon")
        equipped = get_weapon_by_id(equipped_id) if equipped_id else None
        weapons = list(user.get("weapons") or [])
        if not weapons:
            await update.message.reply_text(
                "<b>Equip Weapon</b>\nYou have no weapons!\n"
                "Find weapons by exploring or buy from /shop (Weapon Shop tab).",
                parse_mode="HTML"); return
        lines = []
        for wid in weapons:
            w = get_weapon_by_id(wid)
            if w:
                eq_tag = " <b>[Equipped]</b>" if wid == equipped_id else ""
                lines.append(f"<code>{hesc(w['id'])}</code>{eq_tag} — <b>{hesc(w['name'])}</b> [{hesc(w['rarity'])}] ATK +{w['atk']}")
        cur_txt = f"Currently equipped: <b>{hesc(equipped['name'])}</b>" if equipped else "No weapon equipped."
        await update.message.reply_text(
            f"<b>Your Weapons</b>\n{cur_txt}\n━━━━━━━━━━━━━━━━━━━━\n" + "\n".join(lines) +
            "\n\nUse <code>/equip &lt;weapon_id&gt;</code> to equip a weapon.",
            parse_mode="HTML"); return
    wid = args[0].lower()
    weapons = list(user.get("weapons") or [])
    if wid not in weapons:
        await update.message.reply_text(
            f"You don't own `{wid}`!\nUse /equip to see your weapons.",
            parse_mode="HTML"); return
    weapon = get_weapon_by_id(wid)
    if not weapon:
        await update.message.reply_text("Weapon not found in database!"); return
    await db_set(uid, equipped_weapon=wid)
    await update.message.reply_text(
        f"<b>Weapon Equipped!</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>{weapon['name']}</b> [{weapon['rarity']}]\n"
        f"ATK Bonus: +{weapon['atk']}\n"
        f"Active Ability: {weapon['ability']}\n"
        f"<i>{weapon['desc']}</i>\n\n"
        f"Your weapon button will appear during explore battles!",
        parse_mode="HTML")

async def cmd_myweapons(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid  = str(update.effective_user.id)
    user = await db_get(uid)
    weapons = list(user.get("weapons") or [])
    if not weapons:
        await update.message.reply_text(
            "⚔️ <b>My Weapons</b>\nNo weapons yet!\n"
            "Find them by exploring, or buy from /shop.",
            parse_mode="HTML"); return
    equipped_id = user.get("equipped_weapon")
    lines = []
    for wid in weapons:
        w = get_weapon_by_id(wid)
        if w:
            eq_tag = " <b>[Equipped]</b>" if wid == equipped_id else ""
            lines.append(
                f"⚔️ <b>{hesc(w['name'])}</b>{eq_tag} [{hesc(w['rarity'])}]\n"
                f"  <code>{hesc(w['id'])}</code> | ATK +{w['atk']} | {hesc(w['ability'])}")
    kb = [[Btn("Weapon Shop", callback_data=f"wp:page:0:{uid}")]]
    await update.message.reply_text(
        f"⚔️ <b>My Weapons ({len(weapons)})</b>\n━━━━━━━━━━━━━━━━━━━━\n\n" + "\n\n".join(lines) +
        "\n\n<i>Use <code>/equip &lt;id&gt;</code> to equip.</i>",
        parse_mode="HTML", reply_markup=Kbd(kb))

async def cmd_buy_weapon(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid  = str(update.effective_user.id)
    user = await db_get(uid)
    args = ctx.args
    if not args:
        await update.message.reply_text(
            "Usage: <code>/buy_weapon &lt;weapon_id&gt;</code>\nOpen /shop and tap Weapon Shop to browse.",
            parse_mode="HTML"); return
    wid = args[0].lower()
    weapon = get_weapon_by_id(wid)
    if not weapon:
        await update.message.reply_text(
            f"Unknown weapon <code>{hesc(wid)}</code>. Open /shop and tap Weapon Shop.",
            parse_mode="HTML"); return
    cur_weapons = list(user.get("weapons") or [])
    if wid in cur_weapons:
        await update.message.reply_text(f"You already own <b>{hesc(weapon['name'])}</b>!", parse_mode="HTML"); return
    if user["coins"] < weapon["price"]:
        await update.message.reply_text(
            f"Need <b>{weapon['price']:,} NC</b> — you have <b>{user['coins']:,} NC</b>",
            parse_mode="HTML"); return
    cur_weapons.append(wid)
    await db_set(uid, coins=user["coins"]-weapon["price"], weapons=cur_weapons)
    await update.message.reply_text(
        f"✅ <b>Weapon Purchased!</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"⚔️ <b>{hesc(weapon['name'])}</b> [{hesc(weapon['rarity'])}]\n"
        f"ATK +{weapon['atk']} | {hesc(weapon['ability'])}\n"
        f"{pe('coin')} -{weapon['price']:,} NC\n\n"
        f"<i>Use <code>/equip {hesc(wid)}</code> to equip it!</i>",
        parse_mode="HTML")

# ─── /ban /unban /reset (Admin) ──────────────────────────────────
async def cmd_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid != ADMIN_ID:
        await update.message.reply_text("Admin only command."); return
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /ban <user_id>"); return
    target_id = args[0]
    target = await db_get(target_id)
    if not target:
        await update.message.reply_text(f"User {target_id} not found."); return
    await db_set(target_id, banned=True)
    await update.message.reply_text(
        f"🚫 <b>User Banned</b>\nID: <code>{target_id}</code>\nName: {hesc(target.get('name','Unknown'))}\n"
        f"They can no longer use the bot.",
        parse_mode="HTML")

async def cmd_unban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid != ADMIN_ID:
        await update.message.reply_text("Admin only command."); return
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /unban <user_id>"); return
    target_id = args[0]
    target = await db_get(target_id)
    if not target:
        await update.message.reply_text(f"User {target_id} not found."); return
    await db_set(target_id, banned=False)
    await update.message.reply_text(
        f"✅ <b>User Unbanned</b>\nID: <code>{target_id}</code>\nName: {hesc(target.get('name','Unknown'))}\n"
        f"They can use the bot again.",
        parse_mode="HTML")

async def cmd_resetuser(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid != ADMIN_ID:
        await update.message.reply_text("Admin only command."); return
    args = ctx.args
    if not args:
        await update.message.reply_text(
            "Usage: /resetuser &lt;user_id&gt;\n<b>Warning:</b> This permanently deletes all data for that user.",
            parse_mode="HTML"); return
    target_id = args[0]
    target = await db_get(target_id)
    if not target:
        await update.message.reply_text(f"User {target_id} not found."); return
    tname = target.get("name", "Unknown")
    char_count = await chars_col.count_documents({"uid": target_id})
    await chars_col.delete_many({"uid": target_id})
    await users_col.delete_one({"_id": target_id})
    await update.message.reply_text(
        f"✅ <b>User Reset Complete</b>\nID: <code>{target_id}</code>\nName: {hesc(tname)}\n"
        f"Deleted: {char_count} characters + account\n"
        f"They can /start again for a fresh account.",
        parse_mode="HTML")

# ─── /claninfo ──────────────────────────────────────────────────
CLAN_RANKS = ["Member", "Elite", "Elder", "Leader"]
CLAN_RANK_EMOJIS = {"Member":"", "Elite":"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji>", "Elder":"<tg-emoji emoji-id='5427302588565430059'>🔱</tg-emoji>", "Leader":"👑"}
# Only these 10 clans are shown in the /clan selection menu
SELECTABLE_CLANS = [
    "Uchiha","Hyuga","Uzumaki","Senju","Nara",
    "Akimichi","Yamanaka","Sarutobi","Hatake","Namikaze",
]

async def cmd_claninfo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid  = str(update.effective_user.id)
    user = await db_get(uid)
    clan = user.get("clan","")
    if not clan:
        await update.message.reply_text(
            "*Clan Info*\nYou are not in a clan! Use /clan to join one.",
            parse_mode="HTML"); return
    kg = CLAN_KG.get(clan,"None")
    ki = KG.get(kg, KG["None"])
    clan_doc = await clans_col.find_one({"_id": clan})
    admin_uid = clan_doc.get("admin_uid","") if clan_doc else ""
    clan_members_docs = await users_col.find({"clan": clan}).to_list(None)
    total = len(clan_members_docs)
    user_rank = user.get("clan_rank","Member")
    user_glory = user.get("clan_glory",0)
    leaders = [m for m in clan_members_docs if m.get("clan_rank") == "Leader"]
    elders  = [m for m in clan_members_docs if m.get("clan_rank") == "Elder"]
    elites  = [m for m in clan_members_docs if m.get("clan_rank") == "Elite"]
    members = [m for m in clan_members_docs if m.get("clan_rank","Member") == "Member"]
    def fmt_member(m):
        dn = m.get("nickname","") or m.get("name","Shinobi")
        return f"{dn} (Lv.{m.get('level',1)})"
    lines = [f"<b>{clan} Clan</b>"]
    lines.append(f"Kekkei Genkai: {kg} — _{ki['desc'][:50]}_")
    lines.append(f"Total Members: {total}")
    lines.append(f"Your Rank: <b>{user_rank}</b> | Glory: {user_glory}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("<b>Hierarchy</b>")
    lines.append(f"Leader ({len(leaders)}): " + (", ".join(fmt_member(m) for m in leaders[:3]) or "None"))
    lines.append(f"Elder ({len(elders)}): " + (", ".join(fmt_member(m) for m in elders[:5]) or "None"))
    lines.append(f"Elite ({len(elites)}): " + (", ".join(fmt_member(m) for m in elites[:5]) or "None"))
    lines.append(f"Member ({len(members)}): {len(members)} members")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("<b>Clan Ranks:</b>")
    lines.append("Member → Elite (50 glory) → Elder (200 glory) → Leader (1000 glory + approval)")
    lines.append("\nGain glory by winning explore battles and completing missions.")
    kb = [[Btn("Join Clan", callback_data="menu:clan"),
           Btn("My Profile", callback_data="menu:profile")]]
    await update.message.reply_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=Kbd(kb))

async def cmd_setclanrank(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid != ADMIN_ID:
        await update.message.reply_text("Admin only."); return
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /setclanrank <user_id> <rank>\n"
            "Ranks: Member, Elite, Elder, Leader"); return
    target_id = args[0]; rank = args[1].capitalize()
    if rank not in CLAN_RANKS:
        await update.message.reply_text(f"Invalid rank. Use: {', '.join(CLAN_RANKS)}"); return
    target = await db_get(target_id)
    if not target:
        await update.message.reply_text(f"User {target_id} not found."); return
    await db_set(target_id, clan_rank=rank)
    await update.message.reply_text(
        f"<b>Clan Rank Updated</b>\n<code>{target_id}</code> → {rank}", parse_mode="HTML")

# ─── /close ─────────────────────────────────────────────────────
async def cmd_close(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Remove the reply keyboard."""
    await update.message.reply_text(
        "<tg-emoji emoji-id='5426872512015244606'>🍃</tg-emoji> <i>Keyboard closed. Use any command to continue!</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove())

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb=[[Btn("Account",callback_data="hl:account"),Btn("Battle",callback_data="hl:battle")],
        [Btn("Economy",callback_data="hl:economy"),Btn("Training",callback_data="hl:train")],
        [Btn("Systems",callback_data="hl:systems")]]
    await update.message.reply_text("<tg-emoji emoji-id='5426895906702107044'>📋</tg-emoji> <b>Help Center</b>\nChoose a category:",
                                    parse_mode="HTML",reply_markup=Kbd(kb))

async def cmd_update(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    fi = pe('fire','🔥')
    sw = pe('sword','⚔️')
    st = pe('star','⭐')
    tr = pe('trophy','🏆')
    rd = pe('dot_red','🔴')
    ex = pe('nat_exp','💥')
    cn = pe('coin','🪙')
    lf = pe('leaf','🍃')
    tm = pe('team','👥')
    kn = pe('kunai','🗡️')
    mp = pe('map','🗺️')
    txt = (
        f"{fi}━━━━━━━━━━━━━━━━━━{fi}\n"
        f"<b>NARUTO RPG BOT</b>\n"
        f"✨ <i>The Ultimate Ninja Battle Experience!</i> ✨\n"
        f"{fi}━━━━━━━━━━━━━━━━━━{fi}\n\n"
        f"Hey Shinobi! 😀\n"
        f"Looking for a Naruto bot that takes your ninja adventure to the next level?\n"
        f"Then step into the world of @Narutoorg_bot 🎮\n"
        f"and join our amazing community at @narutoorgg 💕\n\n"
        f"Whether you're a casual collector or a hardcore competitive battler, this bot delivers the ultimate Naruto RPG experience right inside your Telegram chat! "
        f"Summon, train, level up, and battle your way to becoming the Hokage! {tr}\n\n"
        f"━━━━━━━━━━ {st} ━━━━━━━━━━\n"
        f"{rd} <b>Elite Shinobi Battle Mechanics</b>\n"
        f"Experience intense, turn-based speed battles with deep tactical features straight from the anime:\n\n"
        f"{sw} <b>Speed Battle &amp; Roster System</b>\n"
        f"Engage in fast-paced turn-based combat built around Health (HP), Attack, Defense, Speed, and Chakra! "
        f"Assemble your ultimate 6-slot ninja squad to dominate the battlefield.\n\n"
        f"{ex} <b>Legendary Transformations</b>\n"
        f"Awaken your character's true power! Collect Transform Stones to unleash legendary forms mid-battle—"
        f"from Naruto's Nine-Tails Chakra Mode to Sasuke's Rinnegan Awakening!\n\n"
        f"🌀 <b>Nature Transformations &amp; Dojutsu Modifiers</b>\n"
        f"Master the elemental matchups (Fire, Wind, Lightning, Earth, Water, Yin, Yang, and more) along with "
        f"specialized Dojutsu bonuses to deal devastating \"Super Effective\" damage.\n\n"
        f"🐾 <b>Tailed Beasts (Bijuu)</b>\n"
        f"Host or face off against powerful Tailed Beasts! Unlocking a Bijuu grants unique states, custom turn logs, "
        f"and massive stat boosts in combat.\n\n"
        f"━━━━━━━━━━ {tr} ━━━━━━━━━━\n"
        f"🎮 <b>Missions, Gear &amp; Epic Rewards</b>\n"
        f"Compete in grueling ninja missions, explore iconic villages, and gear up your roster:\n\n"
        f"{kn} <b>Mythic Weapon Shop</b> — Equip your shinobi with iconic weapons like the Totsuka Blade or "
        f"Hiraishin Kunai to add flat attack damage and inflict status effects like <i>burn, stun, or shield pierce</i>.\n\n"
        f"{mp} <b>Hidden Villages &amp; Travel</b> — Journey between Konoha, Kumo, Iwa, and more to discover "
        f"localized bonuses, extra EXP, and unique wild encounters.\n\n"
        f"{cn} <b>NC Coin Economy</b> — Earn NC coins through active victories, daily claims, or dangerous missions "
        f"to fund your training and shop purchases.\n\n"
        f"━━━━━━━━━━ 🎉 ━━━━━━━━━━\n"
        f"{rd} <b>Smooth Gameplay &amp; Clan Wars</b>\n\n"
        f"✨ <b>Beginner Friendly &amp; Competitive Ready</b>\n"
        f"Balanced gameplay designed seamlessly for both casual anime fans and veteran RPG strategists.\n\n"
        f"{tm} <b>Custom Ninja Clans</b>\n"
        f"Form or join powerful Shinobi Clans, track your group's victories, and fight alongside your clan members "
        f"to claim absolute supremacy.\n\n"
        f"🎁 <b>Daily Rewards &amp; Events</b>\n"
        f"Claim your daily bonuses, gather upgrade materials, and participate in community events for premium rewards.\n\n"
        f"━━━━━━━━━━ {rd} ━━━━━━━━━━\n"
        f"{fi} <b>Your Shinobi World journey starts NOW!</b> {fi}\n"
        f"Join today, gather your chakra, summon your first ninja, and prove you have what it takes to survive the arena. {lf}\n\n"
        f"✨ <i>We'll be waiting, Shinobi…</i> ✨\n\n"
        f"💕 Regards ~\n"
        f"<b>Naruto RPG Team</b>"
    )
    await update.message.reply_text(txt, parse_mode="HTML")

async def cb_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    cat=q.data.split(":")[1]
    if cat=="__back":
        kb=[[Btn("Account",callback_data="hl:account"),Btn("Battle",callback_data="hl:battle")],
            [Btn("Economy",callback_data="hl:economy"),Btn("Training",callback_data="hl:train")],
            [Btn("Systems",callback_data="hl:systems")]]
        await q.edit_message_text("<tg-emoji emoji-id='5426895906702107044'>📋</tg-emoji> <b>Help Center</b>",parse_mode="HTML",reply_markup=Kbd(kb)); return
    txt=HELP_TEXTS.get(cat,"Not found")
    await q.edit_message_text(txt,parse_mode="HTML",
                              reply_markup=Kbd([[Btn("◀ Back",callback_data="hl:__back")]]))

# ─── MENU CALLBACKS ─────────────────────────────────────────────
async def cb_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    uid=str(q.from_user.id); act=q.data.split(":")[1]
    if act=="home":
        user=await db_get(uid)
        if not user: return
        dn=display_name(user)
        kb=[[Btn("My Stats",callback_data="menu:profile"),Btn("My Chars",callback_data="menu:chars")],
            [Btn("Explore",callback_data="menu:explore"),Btn("Summon",callback_data="menu:summon")],
            [Btn("Shop",callback_data="menu:shop"),Btn("Help",callback_data="menu:help")]]
        await _safe_edit(q,
            f"{pe('anbu')} <b>{hesc(dn)}</b> — Lv.{user['level']} {hesc(user['rank'])}\n"
            f"{pe('coin')} <b>{user['coins']:,} NC</b>  {pe('stone')} <b>{user.get('stones',0)} Stones</b>", kb)
        return
    if act=="profile":
        user=await db_get(uid)
        if not user: return
        vi=VILLAGES.get(user["village"],{}); dn=display_name(user)
        await _safe_edit(q,
            f"<tg-emoji emoji-id='5425113284820869526'>👤</tg-emoji> <b>{dn}</b> Lv.{user['level']} {user['rank']}\n"
            f"<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> {user['coins']:,} NC | <tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> {user['chakra']:,} | <tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji> {user.get('stones',0)} Stones\n"
            f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> {user['wins']}W <tg-emoji emoji-id='5426953124256424318'>💀</tg-emoji>{user['losses']}L | {vi.get('emoji','')} {user['village']}")
    elif act=="inventory":
        await _show_inventory(q, uid, edit=True)
    elif act=="collection":
        chars=await db_chars(uid)
        if not chars:
            await _safe_edit(q,"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> No characters yet! Use /summon."); return
        rarity_order = ["Mythic","Legendary","Epic","Rare","Uncommon","Common"]
        rarity_counts = {r:0 for r in rarity_order}
        for c in chars:
            cd = get_cdata(c["char_name"])
            rar = cd["rarity"] if cd else "Common"
            if rar in rarity_counts:
                rarity_counts[rar] += 1
        lines = []
        for r in rarity_order:
            count = rarity_counts[r]
            if count > 0:
                emoji = RAR.get(r,"⚪")
                lines.append(f"{emoji} <b>{r}</b> — {count} character{'s' if count!=1 else ''}")
        total = len(chars)
        col_txt = (
            f"📚 <b>Your Collection</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Total: <b>{total}</b> characters\n\n"
            + "\n".join(lines)
        )
        await _safe_edit(q, col_txt, [[Btn("Back",callback_data="menu:profile")]]); return
    elif act=="chars":
        chars=await db_chars(uid)
        if not chars: await _safe_edit(q,"No characters! Use /summon."); return
        try: await q.message.delete()
        except: pass
        await send_char_card(q.message,ctx,uid,0,chars,edit=False)
    elif act=="explore":
        team=await db_team(uid)
        if not team: await q.edit_message_text("Set a team first! Use /team"); return
        user=await db_get(uid); p_row=sorted(team,key=lambda c:c.get("slot",99))[0]
        cd=get_cdata(p_row["char_name"])
        if not cd: return
        pkg=CLAN_KG.get(cd["clan"],"None"); vi_i=VILLAGES.get(user["village"],{})
        hp_b=vi_i.get("hp",0); plv=p_row["level"]
        php=int(calc_stat(cd["base"]["hp"],p_row["pp_hp"],plv)*(1+hp_b))
        p_atk=calc_stat(cd["base"]["atk"],p_row["pp_atk"],plv)
        p_def=calc_stat(cd["base"]["def"],p_row["pp_def"],plv)
        p_spd=int(calc_stat(cd["base"]["speed"],p_row["pp_spd"],plv)*(1+vi_i.get("spd",0)))
        equipped_wid_m=user.get("equipped_weapon"); equipped_weapon_m=get_weapon_by_id(equipped_wid_m) if equipped_wid_m else None
        if random.random()<0.55:
            ecd=random.choice(CHARACTERS); elv=max(1,plv+random.randint(-8,12))
            ehp=int(calc_stat(ecd["base"]["hp"],15,elv)*0.7)
            wild={"name":ecd["name"],"nat":ecd["nature"],"hp":ehp,
                  "atk":int(calc_stat(ecd["base"]["atk"],15,elv)*0.7),
                  "def":int(calc_stat(ecd["base"]["def"],15,elv)*0.7),
                  "spd":int(calc_stat(ecd["base"]["speed"],15,elv)*0.7),
                  "photo":ecd.get("photo") or PHOTO_CACHE.get(ecd["name"]),"nc":(max(200,elv*30),max(500,elv*80)),
                  "chakra":(max(20,elv*3),max(80,elv*10)),"exp":(max(30,elv*8),max(100,elv*20)),
                  "moves":ecd["moves"],"is_char":True}; elv_s=elv
        else:
            wild=random.choice(WILDS); elv_s=max(1,plv+random.randint(-5,8))
            wild=dict(wild); wild["hp"]=wild.get("hp",150)+random.randint(-20,60)
        ehp=wild["hp"]; e_spd=wild.get("spd",150); p_goes_first=p_spd>=e_spd
        form=cd.get("form"); req_chakra=form["req_chakra"] if form else 999999
        tb_name_m = cd.get("tailed_beast")
        _ALWAYS_BIJUU_M = {"Naruto (Baryon Mode)", "Naruto Uzumaki", "Minato Namikaze",
                           "Killer Bee", "Gaara", "Gaara (Fifth Kazekage)"}
        _caught_m = list(user.get("caught_beasts") or [])
        bijuu_av_m = (bool(tb_name_m and tb_name_m in BEASTS)
                      and (p_row["char_name"] in _ALWAYS_BIJUU_M or tb_name_m in _caught_m))
        session={"p_char":p_row["char_name"],"p_char_id":p_row["id"],"p_level":plv,
                 "p_hp":php,"p_max_hp":php,"p_atk":p_atk,"p_def":p_def,
                 "p_spd":p_spd,"p_nat":cd["nature"],"p_kg":pkg,
                 "p_status":"","p_dot":None,"p_def_broken":False,"p_revived":False,
                 "p_battle_chakra":0,"p_transformed":False,"transform_available":False,
                 "req_chakra":req_chakra,
                 "enemy":wild,"e_hp":ehp,"e_max_hp":ehp,"e_level":elv_s,
                 "e_status":"","e_dot":None,"e_def_broken":False,
                 "is_photo":False,"turn":0,"uid":uid,"p_goes_first":p_goes_first,
                 "equipped_weapon":equipped_weapon_m,"weapon_used":False,
                 "bijuu_avail":bijuu_av_m,"bijuu_active":False,
                 "bijuu_turns_left":0,"bijuu_beast_name":tb_name_m or "",
                 "started_at":time.time()}
        EX[uid]=session
        # Show encounter screen — Fight or Run
        encounter_txt=(
            f"<b>Wild Encounter!</b>\n\n"
            f"A wild <b>{hesc(wild['name'])}</b> appeared!\n"
            f"Lv.{elv_s}  {hesc(wild.get('nat','neutral'))} {nat_pe(wild.get('nat','neutral'))}\n\n"
            f"<i>What will you do?</i>"
        )
        enc_kb=[[Btn("Fight",callback_data=f"ex:fight:{uid}"),
                 Btn("Run",callback_data=f"ex:run:{uid}")]]
        await _safe_edit(q, encounter_txt, enc_kb)
    elif act=="summon":
        user=await db_get(uid)
        kb=[[Btn("Single (500 NC)",callback_data=f"sm:s:{uid}"),
             Btn("10x (4500 NC)",callback_data=f"sm:m:{uid}")],
            [Btn("Legendary (25000 NC)",callback_data=f"sm:l:{uid}")]]
        await _safe_edit(q,f"<tg-emoji emoji-id='5426957509418031897'>🌀</tg-emoji> <b>Summon</b> — {user['coins']:,} NC",kb)
    elif act=="shop":
        user=await db_get(uid)
        txt=f"🛒 <b>Ninja Shop</b> — {pe('coin')} {user['coins']:,} NC\n\nUse /buy <code>&lt;id&gt;</code> to purchase:\n\n"
        for item in SHOP:
            txt+=f"{item['emoji']} <code>{hesc(item['id'])}</code> — <b>{hesc(item['name'])}</b> {item['price']:,} NC\n<i>{hesc(item['desc'])}</i>\n\n"
        await _safe_edit(q, txt[:1020])
    elif act=="profile_view":
        user  = await db_get(uid)
        chars = await db_chars(uid)
        team  = await db_team(uid)
        en    = exp_for_lv(user["level"] + 1)
        bar   = hp_bar(user["exp"], en)
        kg    = CLAN_KG.get(user["clan"], "None")
        ki    = KG.get(kg, KG["None"])
        dn    = display_name(user)
        clan_rank     = user.get("clan_rank", "Member")
        clan_rank_tag = CLAN_RANK_EMOJIS.get(clan_rank, "")
        admin_tag     = f"   {pe('star')} <b>[ADMIN]</b>" if uid == ADMIN_ID else ""
        SEP = "──────────────────────"
        rank_line = (f"{hesc(user['rank'])} — Level {user['level']}/100"
                     + (f"  {clan_rank_tag} <b>{clan_rank}</b>" if clan_rank != "Member" else ""))
        ptxt = (
            f"{pe('anbu')} <b>User Profile:</b>\n{SEP}\n"
            f"<b>{hesc(dn)}</b>{admin_tag}\n{SEP}\n"
            f"{pe('rank')} <b>Stats:</b>\n{rank_line}\nEXP: {bar}\n{SEP}\n"
            f"{pe('coin')} <b>Collection:</b>\n"
            f"1) {pe('coin')} <b>{user['coins']:,} NC</b>\n"
            f"2) {pe('exp')} <b>{user['exp']}</b>\n"
            f"3) {pe('stone')} <b>{user.get('stones',0)} Stones</b>\n"
            f"4) {pe('sword')} <b>{user['wins']} W</b>\n"
            f"5) {pe('skull')} <b>{user['losses']} L</b>\n"
            f"{SEP}\n"
            f"{pe('lightning')} <b>KG:</b>\n<b>{hesc(kg)}</b>\n<i>{hesc(ki['desc'])}</i>\n\n"
            f"{pe('team')} <b>{len(chars)}</b> chars   {pe('anbu')} <b>{len(team)}/6</b> team"
        )
        ach = _get_achievements(user, chars)
        pkb = [[Btn("Village", callback_data="menu:village"),
                Btn("Clan",    callback_data="menu:clan")]]
        if ach:
            pkb.append([Btn(f"Achievements ({len(ach)})", callback_data="menu:achievements")])
        await _safe_edit(q, ptxt[:1020], pkb)
    elif act=="village":
        user  = await db_get(uid)
        cur   = user["village"]
        vi    = VILLAGES.get(cur, {}); vinfo = VILLAGE_INFO.get(cur, {})
        bonus_map = {"exp":"EXP","chakra":"Chakra","def":"DEF","spd":"SPD",
                     "hp":"HP","atk":"ATK","crit":"CRIT","all":"All Stats","lightning":"Lightning"}
        bonus_lines = [f"  • {label} +{int(vi[k]*100)}%"
                       for k, label in bonus_map.items() if vi.get(k)]
        bonus_txt = "\n".join(bonus_lines) if bonus_lines else "  • Balanced bonuses"
        txt = (f"{pe('village')} <b>Your Village</b>\n"
               f"──────────────────────\n"
               f"{vi.get('emoji','')} <b>{hesc(vinfo.get('full', cur))}</b>\n"
               f"<i>{hesc(vi.get('desc',''))}</i>\n"
               f"Country: {hesc(vinfo.get('country',''))}\n"
               f"Kage: <b>{hesc(vinfo.get('kage',''))}</b>\n\n"
               f"<b>Village Bonuses:</b>\n{bonus_txt}")
        kb = [[Btn("Switch Village", callback_data="menu:village_switch"),
               Btn("Back",          callback_data="menu:profile_view")]]
        await _safe_edit(q, txt, kb)
    elif act=="village_switch":
        user = await db_get(uid)
        kb   = _village_list_kb(user["village"])
        kb.append([Btn("Back", callback_data="menu:village")])
        txt  = (f"{pe('village')} <b>Switch Village</b>\n"
                f"Current: <b>{hesc(user['village'])}</b>\n\n"
                f"<i>Tap a village to view details and join!</i>")
        await _safe_edit(q, txt, kb)
    elif act=="clan":
        user=await db_get(uid)
        if user.get("clan"):
            clan=user["clan"]
            kg=CLAN_KG.get(clan,"None"); ki=KG.get(kg,KG["None"])
            clan_members_docs=await users_col.find({"clan":clan}).to_list(None)
            total=len(clan_members_docs)
            user_rank=user.get("clan_rank","Member")
            user_glory=user.get("clan_glory",0)
            rank_tag=CLAN_RANK_EMOJIS.get(user_rank,"")
            chars_w=[c["name"] for c in CHARACTERS if c["clan"]==clan][:5]
            leaders=[m for m in clan_members_docs if m.get("clan_rank")=="Leader"]
            elders=[m for m in clan_members_docs if m.get("clan_rank")=="Elder"]
            elites=[m for m in clan_members_docs if m.get("clan_rank")=="Elite"]
            def _fn(m): return m.get("nickname","") or m.get("name","Shinobi")
            txt=(
                f"{pe('anbu')} <b>{hesc(clan)} Clan</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"<b>Kekkei Genkai:</b> {hesc(kg)}\n"
                f"<i>{hesc(ki['desc'][:80])}</i>\n\n"
                f"<b>Members:</b> {total} | <b>Your Rank:</b> {rank_tag} {hesc(user_rank)}\n"
                f"<b>Glory:</b> {user_glory}\n\n"
                f"<b>Hierarchy</b>\n"
                f"Leader: {', '.join(_fn(m) for m in leaders[:2]) or 'None'}\n"
                f"Elder: {', '.join(_fn(m) for m in elders[:3]) or 'None'}\n"
                f"Elite: {len(elites)} members\n\n"
                f"<b>Clan Characters:</b> {hesc(', '.join(chars_w) or 'Various')}"
            )
            await _safe_edit(q, txt, [[Btn("Back", callback_data="menu:profile_view")]])
        else:
            await _safe_edit(q,
                f"{pe('clan')} <b>Clan</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                f"You have <b>not joined</b> a clan yet.\n\n"
                f"Use the button below or <code>/clan</code> to browse and join a clan!\n"
                f"<i>Clans grant Kekkei Genkai abilities in battle.</i>",
                [[Btn("Join a Clan", callback_data="menu:clan_join")],
                 [Btn("Back", callback_data="menu:profile_view")]])
    elif act=="clan_join":
        cnames=list(CLANS.keys()); kb=[]
        for i in range(0,len(cnames)-1,2):
            row=[]
            for j in range(2):
                if i+j<len(cnames): row.append(Btn(cnames[i+j],callback_data=f"cj:{i+j}"))
            kb.append(row)
        kb.append([Btn("Back", callback_data="menu:clan")])
        await _safe_edit(q,"<b>Choose Your Clan</b>\n<i>This is a lifetime choice. Choose wisely!</i>",kb)
    elif act=="achievements":
        user  = await db_get(uid)
        chars = await db_chars(uid)
        ach   = _get_achievements(user, chars)
        if not ach:
            await _safe_edit(q,
                f"{pe('star')} <b>Achievements</b>\n──────────────────────\n"
                f"No achievements yet!\n<i>Keep playing to earn titles.</i>",
                [[Btn("Back", callback_data="menu:profile_view")]])
            return
        SEP = "──────────────────────"
        lines = []
        for title, desc in ach:
            lines.append(f"{pe('trophy')} <b>{hesc(title)}</b>\n   <i>{hesc(desc)}</i>")
        txt = (
            f"{pe('star')} <b>Achievements</b>\n"
            f"{SEP}\n"
            f"{pe('rank')} Titles earned: <b>{len(ach)}</b>\n\n"
            + "\n\n".join(lines)
        )
        await _safe_edit(q, txt[:4000], [[Btn("Back", callback_data="menu:profile_view")]])
    elif act=="ability":
        user=await db_get(uid); kg=CLAN_KG.get(user["clan"],"None"); ki=KG.get(kg,KG["None"])
        await _safe_edit(q,
            f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> <b>Abilities</b>\nKG: <b>{kg}</b> — <i>{ki['desc'][:55]}</i>\nVillage: <b>{user['village']}</b>")
    elif act=="heal":
        user=await db_get(uid)
        if user["coins"]>=300:
            await db_set(uid,coins=user["coins"]-300)
            await _safe_edit(q,"<tg-emoji emoji-id='5427095369278299187'>💊</tg-emoji> <b>Healed!</b> -300 NC")
        else: await q.answer("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Need 300 NC!",show_alert=True)
    elif act=="help":
        kb=[[Btn("Account",callback_data="hl:account"),Btn("Battle",callback_data="hl:battle")],
            [Btn("Economy",callback_data="hl:economy"),Btn("Systems",callback_data="hl:systems")]]
        await _safe_edit(q,"<tg-emoji emoji-id='5426895906702107044'>📋</tg-emoji> <b>Help</b>",kb)

async def cb_misc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    d=q.data; uid=str(q.from_user.id)
    if d=="cmd:stats":
        chars=await db_chars(uid)
        if not chars: return
        kb=[[Btn(f"{c['char_name'][:26]} Lv.{c['level']}",
                 callback_data=f"sv:{c['id']}")] for c in chars[:20]]
        stats_txt = "<tg-emoji emoji-id='5981204549132619885'>📊</tg-emoji> <b>Your Characters</b>\nSelect one to view stats &amp; level up:"
        # Edit the current message in place — swap photo back to STATS_BANNER.
        # Never send new messages; always keep the same message position.
        is_photo_msg = bool(q.message and q.message.photo)
        banner_src = _get_banner(STATS_BANNER)   # use pre-cached bytes (fast, reliable)
        if banner_src and is_photo_msg:
            for pm in ("Markdown", None):
                if hasattr(banner_src, "seek"):
                    banner_src.seek(0)
                try:
                    await q.edit_message_media(
                        media=InputMediaPhoto(media=banner_src,
                                              caption=stats_txt, parse_mode=pm),
                        reply_markup=Kbd(kb))
                    return
                except Exception:
                    pass
            # edit_message_media failed — keep current photo, update caption+buttons
            for pm in ("Markdown", None):
                try:
                    await q.edit_message_caption(caption=stats_txt, parse_mode=pm,
                                                 reply_markup=Kbd(kb))
                    return
                except Exception:
                    pass
        # Text message fallback
        await _safe_edit(q, stats_txt, kb)
    elif d=="cmd:moves":
        chars=await db_chars(uid)
        if not chars: return
        kb=[[Btn(f"{c['char_name'][:26]} Lv.{c['level']}",
                 callback_data=f"mv:{c['id']}")] for c in chars[:20]]
        await _safe_edit(q, "<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> <b>Select character for moves:</b>", kb)

# ─── REBIRTH TOKEN CALLBACK ─────────────────────────────────────
async def cb_rebirth_token(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = str(q.from_user.id)
    cid = int(q.data.split(":")[1])
    row = _cdoc(await chars_col.find_one({"_id": cid, "uid": uid}))
    if not row: return
    new_lv = min(row["level"] + 10, MAX_CHAR_LEVEL)
    await chars_col.update_one({"_id": cid}, {"$set": {"level": new_lv}})
    await _safe_edit(q,
        f"<tg-emoji emoji-id='5424892463372312872'>🌟</tg-emoji> <b>Rebirth Token used!</b>\n"
        f"<b>{row['char_name']}</b> → Lv. <b>{new_lv}</b> (+10 levels)!")

# ─── 10 NEW COMMANDS ─────────────────────────────────────────────

# 1) /gamble — Gamble NC for chance to multiply
async def cmd_gamble(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid = str(update.effective_user.id); user = await db_get(uid)
    args = ctx.args
    if not args or not args[0].isdigit():
        kb = [[Btn("Bet 100 NC", callback_data=f"gb:100:{uid}"),
               Btn("Bet 500 NC", callback_data=f"gb:500:{uid}")],
              [Btn("Bet 1000 NC",callback_data=f"gb:1000:{uid}"),
               Btn("Bet 5000 NC",callback_data=f"gb:5000:{uid}")]]
        await update.message.reply_text(
            f"<tg-emoji emoji-id='5426953124256424318'>🎰</tg-emoji> <b>Casino — Gamble NC!</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> Balance: <b>{user['coins']:,} NC</b>\n\n"
            f"<tg-emoji emoji-id='5427397421443325675'>🎲</tg-emoji> Win: <b>×2</b> your bet (50/50 chance)\n"
            f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> Jackpot: <b>×5</b> (5% chance!)\n\n"
            f"_Or use `/gamble <amount>` to bet a custom amount_",
            parse_mode="HTML", reply_markup=Kbd(kb)); return
    amount = min(int(args[0]), user["coins"], 50000)
    if amount < 50:
        await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Minimum bet is 50 NC!"); return
    roll = random.random()
    if roll < 0.05:
        won = amount * 5; msg = f"<tg-emoji emoji-id='5426953124256424318'>🎰</tg-emoji> <b>JACKPOT!</b> ×5 — +<b>{won:,} NC</b>! <tg-emoji emoji-id='5426976939850080222'>🎉</tg-emoji>"
    elif roll < 0.50:
        won = amount; msg = f"<tg-emoji emoji-id='5427397421443325675'>🎲</tg-emoji> <b>You Win!</b> ×2 — +<b>{won:,} NC</b>!"
    else:
        won = -amount; msg = f"<tg-emoji emoji-id='5426953124256424318'>💀</tg-emoji> <b>You Lose!</b> —<b>{abs(won):,} NC</b> gone."
    new_coins = max(0, user["coins"] + won)
    await db_set(uid, coins=new_coins)
    await update.message.reply_text(
        f"{msg}\n<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> Balance: <b>{new_coins:,} NC</b>", parse_mode="HTML")

async def cb_gamble(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts = q.data.split(":"); amount = int(parts[1]); uid = parts[2]
    if str(q.from_user.id) != uid: await q.answer("Not yours!", show_alert=True); return
    user = await db_get(uid)
    if user["coins"] < amount:
        await q.answer(f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Need {amount:,} NC!", show_alert=True); return
    roll = random.random()
    if roll < 0.05:
        won = amount * 5; msg = f"<tg-emoji emoji-id='5426953124256424318'>🎰</tg-emoji> <b>JACKPOT!</b> ×5 — +<b>{won:,} NC</b>! <tg-emoji emoji-id='5426976939850080222'>🎉</tg-emoji>"
    elif roll < 0.50:
        won = amount; msg = f"<tg-emoji emoji-id='5427397421443325675'>🎲</tg-emoji> <b>You Win!</b> ×2 — +<b>{won:,} NC</b>!"
    else:
        won = -amount; msg = f"<tg-emoji emoji-id='5426953124256424318'>💀</tg-emoji> <b>You Lose!</b> —<b>{abs(won):,} NC</b> gone."
    new_coins = max(0, user["coins"] + won)
    await db_set(uid, coins=new_coins)
    kb = [[Btn("Bet Again", callback_data=f"gb:{amount}:{uid}"),
           Btn("Inventory", callback_data=f"inv:view:{uid}")]]
    await q.edit_message_text(
        f"<tg-emoji emoji-id='5426953124256424318'>🎰</tg-emoji> <b>Casino Result</b>\n━━━━━━━━━━━━━━━━━━━━\n{msg}\n"
        f"<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> Balance: <b>{new_coins:,} NC</b>",
        parse_mode="HTML", reply_markup=Kbd(kb))

# 2) /meditate — Free chakra regeneration on cooldown
async def cmd_meditate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid = str(update.effective_user.id); user = await db_get(uid)
    last = user.get("meditate_last", "")  # dedicated field — no conflict with mission_last
    now = datetime.utcnow()
    COOLDOWN = 4 * 3600
    if last:
        try:
            diff = (now - datetime.fromisoformat(last)).total_seconds()
            if diff < COOLDOWN:
                h, m = divmod(int(COOLDOWN - diff) // 60, 60)
                await update.message.reply_text(
                    f"<tg-emoji emoji-id='5425111072912713470'>🧘</tg-emoji> <b>Meditation in progress...</b>\n"
                    f"<tg-emoji emoji-id='5803204762035818905'>⏳</tg-emoji> Cooldown: <b>{h}h {m}m</b> remaining\n"
                    f"_Your chakra is still recovering._", parse_mode="HTML"); return
        except: pass
    gain = random.randint(1, 5)
    await db_set(uid, chakra=user["chakra"] + gain, meditate_last=now.isoformat())
    kb = [[Btn("Explore", callback_data="menu:explore"),
           Btn("Inventory", callback_data=f"inv:view:{uid}")]]
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5425111072912713470'>🧘</tg-emoji> <b>Deep Meditation Complete!</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> +<b>{gain} Chakra</b> restored!\n"
        f"<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> Total: <b>{user['chakra']+gain:,} Chakra</b>\n\n"
        f"_Come back in 4 hours to meditate again!_",
        parse_mode="HTML", reply_markup=Kbd(kb))

# 3) /bounty — Daily bounty system for bonus NC
async def cmd_bounty(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid = str(update.effective_user.id)
    chars = await db_chars(uid)
    if not chars:
        await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> No characters to hunt bounties!"); return
    _rng = random.Random(int(uid) + datetime.utcnow().toordinal())
    targets = _rng.sample(CHARACTERS, min(3, len(CHARACTERS)))
    reward = 120
    lines = "\n".join(f"  <tg-emoji emoji-id='5427397421443325675'>🎯</tg-emoji> <b>{t['name']}</b> ⟨{t['rarity']}⟩ {nat_icon(t['nature'])}" for t in targets)
    kb = [[Btn("Explore", callback_data="menu:explore"),
           Btn("Missions", callback_data="hl:account")]]
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5426953124256424318'>🏴‍☠️</tg-emoji> <b>Daily Bounty Board</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"Hunt these characters in /explore:\n\n{lines}\n\n"
        f"<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> Total Reward: <b>{reward:,} NC</b>\n"
        f"🕐 Resets at midnight UTC\n\n"
        f"_Defeat them in explore to claim rewards!_",
        parse_mode="HTML", reply_markup=Kbd(kb))

# 4) /forge — Convert chakra into a Transform Stone
async def cmd_forge(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid = str(update.effective_user.id); user = await db_get(uid)
    CHAKRA_COST = 800; NC_COST = 300
    kb = [[Btn(f"Forge (800 Chakra + 300 NC)", callback_data=f"fg:forge:{uid}"),
           Btn("Cancel", callback_data=f"fg:cancel:{uid}")]]
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5999047234849611002'>⚒️</tg-emoji> <b>Forge Workshop</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"Transform raw chakra energy into a battle stone!\n\n"
        f"<tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji> <b>Forge Transform Stone:</b>\n"
        f"  Cost: <b>{CHAKRA_COST} Chakra</b> + <b>{NC_COST} NC</b>\n"
        f"  Gain: <b>1 Transform Stone</b> <tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji>\n\n"
        f"<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> Your Chakra: <b>{user['chakra']:,}</b>\n"
        f"<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> Your NC: <b>{user['coins']:,}</b>\n"
        f"<tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji> Current Stones: <b>{user.get('stones',0)}</b>",
        parse_mode="HTML", reply_markup=Kbd(kb))

async def cb_forge(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts = q.data.split(":"); action = parts[1]; uid = parts[2]
    if str(q.from_user.id) != uid: await q.answer("Not yours!", show_alert=True); return
    if action == "cancel":
        await q.edit_message_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Forging cancelled.", parse_mode="HTML"); return
    CHAKRA_COST = 800; NC_COST = 300
    user = await db_get(uid)
    if user["chakra"] < CHAKRA_COST:
        await q.answer(f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Need {CHAKRA_COST} Chakra!", show_alert=True); return
    if user["coins"] < NC_COST:
        await q.answer(f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Need {NC_COST} NC!", show_alert=True); return
    await db_set(uid, chakra=user["chakra"]-CHAKRA_COST,
                 coins=user["coins"]-NC_COST, stones=user.get("stones",0)+1)
    kb = [[Btn("Forge Again", callback_data=f"fg:forge:{uid}"),
           Btn("Battle!", callback_data="menu:explore")]]
    await q.edit_message_text(
        f"<tg-emoji emoji-id='5999047234849611002'>⚒️</tg-emoji> <b>Forging Complete!</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji> <b>+1 Transform Stone!</b>\n"
        f"Total Stones: <b>{user.get('stones',0)+1}</b>\n\n"
        f"<i>Use it in battle when your chakra is full!</i>",
        parse_mode="HTML", reply_markup=Kbd(kb))

# 5) /sacrifice — Sacrifice a character for NC + chance of Stone
async def cmd_sacrifice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid = str(update.effective_user.id)
    chars = await db_chars(uid)
    team = await db_team(uid)
    team_ids = {c["id"] for c in team}
    eligible = [c for c in chars if c["id"] not in team_ids]
    if not eligible:
        await update.message.reply_text(
            "<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> No eligible characters!\nRemove a character from your team first."); return
    kb = [[Btn(f"{c['char_name'][:20]} Lv.{c['level']}",
               callback_data=f"sc:{c['id']}:{uid}")] for c in eligible[:10]]
    kb.append([Btn("Cancel", callback_data=f"sc:cancel:{uid}")])
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5426953124256424318'>⚰️</tg-emoji> <b>Character Sacrifice</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"Sacrifice a character not in your team for:\n"
        f"  <tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> NC based on rarity + level\n"
        f"  <tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji> 10% chance of a Transform Stone\n\n"
        f"<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji> <i>This is permanent — choose carefully!</i>\n\n"
        f"Select character to sacrifice:",
        parse_mode="HTML", reply_markup=Kbd(kb))

async def cb_sacrifice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts = q.data.split(":"); uid = parts[2]
    if str(q.from_user.id) != uid: await q.answer("Not yours!", show_alert=True); return
    if parts[1] == "cancel":
        await q.edit_message_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Sacrifice cancelled."); return
    cid = int(parts[1])
    row = _cdoc(await chars_col.find_one({"_id": cid, "uid": uid}))
    if not row or row["in_team"]:
        await q.answer("Cannot sacrifice a team member!", show_alert=True); return
    await chars_col.delete_one({"_id": cid})
    cd = get_cdata(row["char_name"])
    rar = cd["rarity"] if cd else "Common"
    rar_nc = {"Common":200,"Uncommon":400,"Rare":800,"Epic":2000,"Legendary":5000,"Mythic":12000}
    nc_gain = rar_nc.get(rar, 200) + row["level"] * 15
    stone_drop = random.random() < 0.10
    user = await db_get(uid)
    new_stones = user.get("stones", 0) + (1 if stone_drop else 0)
    await db_set(uid, coins=user["coins"]+nc_gain, stones=new_stones)
    stone_txt = "\n<tg-emoji emoji-id='5803134797018566405'>🪨</tg-emoji> <b>Bonus: Transform Stone dropped!</b>" if stone_drop else ""
    await q.edit_message_text(
        f"<tg-emoji emoji-id='5426953124256424318'>⚰️</tg-emoji> <b>Sacrifice Complete!</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>{row['char_name']}</b> has been sacrificed.\n\n"
        f"<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> +<b>{nc_gain:,} NC</b> received!{stone_txt}\n"
        f"<tg-emoji emoji-id='6032916496542339992'>💰</tg-emoji> Balance: <b>{user['coins']+nc_gain:,} NC</b>",
        parse_mode="HTML")

# 6) /arena — Quick auto-battle vs random top-10 player's team
# 7) /dojo — Train a specific character stat for free (with cooldown)
# /dojo and /powerup removed — use /train instead

# 9) /pity — Check your gacha pity counter
async def cmd_pity(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid = str(update.effective_user.id)
    chars = await db_chars(uid)
    total_summons = len(chars)
    epic_pity = 10 - (total_summons % 10)
    leg_pity = 50 - (total_summons % 50)
    kb = [[Btn("Summon Now!", callback_data=f"sm:s:{uid}"),
           Btn("10x Summon",    callback_data=f"sm:m:{uid}")]]
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5427397421443325675'>🎲</tg-emoji> <b>Pity Counter</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5981204549132619885'>📊</tg-emoji> Total Summons: <b>{total_summons}</b>\n\n"
        f"<tg-emoji emoji-id='5769297434047943583'>🟣</tg-emoji> Epic Pity: <b>{epic_pity}</b> pulls away\n"
        f"<tg-emoji emoji-id='5915696866120438280'>🟡</tg-emoji> Legendary Pity: <b>{leg_pity}</b> pulls away\n\n"
        f"_Every 10th pull guarantees Rare+_\n"
        f"_Every 50th pull guarantees Epic+_\n\n"
        f"Use /summon to keep pulling!",
        parse_mode="HTML", reply_markup=Kbd(kb))

# /powerup removed — was a quick power overview, replaced by /add (admin) and /train

# ─── /add — Admin: add resources/chars to any user ───────────────
async def cmd_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid != ADMIN_ID:
        await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Admin only."); return
    args = ctx.args  # /add <target_uid> <what> <value>
    usage = (
        "<tg-emoji emoji-id='5426895906702107044'>📋</tg-emoji> <b>Admin /add usage:</b>\n"
        "`/add <uid> coins <amount>`\n"
        "`/add <uid> chakra <amount>`\n"
        "`/add <uid> stones <amount>`\n"
        "`/add <uid> level <amount>`   _(player level)_\n"
        "`/add <uid> char <char_name>`\n"
        "`/add <uid> pp <stat> <char_id> <amount>`\n\n"
        "_stat = atk | def | spd | hp_"
    )
    if not args or len(args) < 3:
        await update.message.reply_text(usage, parse_mode="HTML"); return

    target_uid = args[0]; what = args[1].lower()

    # Verify target user exists
    tuser = await db_get(target_uid)
    if not tuser:
        await update.message.reply_text(f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> User <code>{target_uid}</code> not found.", parse_mode="HTML"); return

    # ── coins ─────────────────────────────────────────────────────
    if what == "coins":
        try: amount = int(args[2])
        except ValueError: await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Amount must be a number."); return
        new_val = tuser["coins"] + amount
        await db_set(target_uid, coins=new_val)
        await update.message.reply_text(
            f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> Added <b>{amount:,} NC</b> to <code>{target_uid}</code>\n"
            f"New balance: <b>{new_val:,} NC</b>", parse_mode="HTML")

    # ── chakra ────────────────────────────────────────────────────
    elif what == "chakra":
        try: amount = int(args[2])
        except ValueError: await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Amount must be a number."); return
        new_val = tuser["chakra"] + amount
        await db_set(target_uid, chakra=new_val)
        await update.message.reply_text(
            f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> Added <b>{amount:,} Chakra</b> to <code>{target_uid}</code>\n"
            f"New chakra: <b>{new_val:,}</b>", parse_mode="HTML")

    # ── stones ────────────────────────────────────────────────────
    elif what == "stones":
        try: amount = int(args[2])
        except ValueError: await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Amount must be a number."); return
        new_val = tuser.get("stones", 0) + amount
        await db_set(target_uid, stones=new_val)
        await update.message.reply_text(
            f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> Added <b>{amount}</b> Transform Stone(s) to <code>{target_uid}</code>\n"
            f"New stones: <b>{new_val}</b>", parse_mode="HTML")

    # ── player level ──────────────────────────────────────────────
    elif what == "level":
        try: amount = int(args[2])
        except ValueError: await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Amount must be a number."); return
        new_lv = min(100, tuser["level"] + amount)
        await db_set(target_uid, level=new_lv, rank=rank_for_lv(new_lv))
        await update.message.reply_text(
            f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> Player <code>{target_uid}</code> leveled up by <b>{amount}</b>\n"
            f"New player level: <b>{new_lv}</b>", parse_mode="HTML")

    # ── give a character ──────────────────────────────────────────
    elif what == "char":
        char_name = " ".join(args[2:])
        cd = get_cdata(char_name)
        if not cd:
            # Try case-insensitive match
            char_name = next((c["name"] for c in CHARACTERS
                              if c["name"].lower() == char_name.lower()), None)
            cd = get_cdata(char_name) if char_name else None
        if not cd:
            await update.message.reply_text(
                f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Character <code>{' '.join(args[2:])}</code> not found.\n"
                f"Check spelling — must match exactly.", parse_mode="HTML"); return
        move_keys = [m["name"] for m in cd["moves"]]
        new_cid = await _next_char_id()
        await chars_col.insert_one({"_id": new_cid, "uid": target_uid, "char_name": cd["name"],
            "level": 1, "exp": 0, "pp_hp": 0, "pp_atk": 0, "pp_def": 0,
            "pp_spd": 0, "pp_cha": 0, "in_team": 0, "slot": 0, "forgotten_moves": []})
        rr = RAR.get(cd["rarity"], "⚪")
        await update.message.reply_text(
            f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> Gave {rr} <b>{cd['name']}</b> ({cd['rarity']}) to <code>{target_uid}</code>",
            parse_mode="HTML")

    # ── PP stat boost for a specific char ─────────────────────────
    elif what == "pp":
        if len(args) < 5:
            await update.message.reply_text(
                "Usage: `/add <uid> pp <stat> <char_id> <amount>`\n"
                "stat = atk | def | spd | hp", parse_mode="HTML"); return
        stat = args[2].lower(); char_id_str = args[3]
        try: char_id = int(char_id_str); amount = int(args[4])
        except ValueError: await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> char_id and amount must be numbers."); return
        col = {"atk":"pp_atk","def":"pp_def","spd":"pp_spd","hp":"pp_hp"}.get(stat)
        if not col:
            await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> stat must be atk, def, spd, or hp."); return
        crow = _cdoc(await chars_col.find_one({"_id": char_id, "uid": target_uid}))
        if not crow:
            await update.message.reply_text(
                f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Char ID {char_id} not found for user <code>{target_uid}</code>.",
                parse_mode="HTML"); return
        cd2  = get_cdata(crow["char_name"])
        cap  = MAX_PP_BY_RARITY.get(cd2["rarity"] if cd2 else "Common", 22)
        nv   = min(cap, crow[col] + amount)
        await chars_col.update_one({"_id": char_id}, {"$set": {col: nv}})
        await update.message.reply_text(
            f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> Added <b>+{amount} PP</b> to {stat.upper()} for <b>{crow['char_name']}</b> "
            f"(ID:{char_id})\nNew PP: <b>{nv}/{cap}</b>", parse_mode="HTML")

    else:
        await update.message.reply_text(usage, parse_mode="HTML")


# ─── /newmove — Show pending move swap for current user ──────────
async def cmd_newmove(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid = str(update.effective_user.id)
    if uid not in PENDING_MOVE_SWAP:
        await update.message.reply_text(
            "<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> No pending move unlocks!\n"
            "_Move unlocks happen when your character levels up._",
            parse_mode="HTML"); return
    pnd = PENDING_MOVE_SWAP[uid]
    await _send_mvswap_menu(update.message, uid, pnd, edit=False)

async def _send_mvswap_menu(target, uid, pnd, edit=False):
    nm   = pnd["new_move"]
    cid  = pnd["char_id"]
    cname= pnd["char_name"]
    # Load current moves for this char from DB
    await chars_col.find_one({"_id": cid}, {"char_name": 1})
    cd = get_cdata(cname)
    if not cd:
        if edit: await target.edit_message_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Character data missing.")
        else:    await target.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Character data missing.")
        return
    moves = cd["moves"]
    txt = (f"<tg-emoji emoji-id='5427397421443325675'>🆕</tg-emoji> <b>NEW MOVE UNLOCKED for {cname}!</b>\n"
           f"━━━━━━━━━━━━━━━━━━━━\n"
           f"<b>{nm['name']}</b>\n"
           f"<tg-emoji emoji-id='5812074410667938253'>⚡</tg-emoji> Type: {nm['type']} | <tg-emoji emoji-id='5998841304052669228'>💥</tg-emoji> Power: {nm['power']} | <tg-emoji emoji-id='5427397421443325675'>🎯</tg-emoji> Acc: {nm['acc']}%\n"
           f"<tg-emoji emoji-id='5382228835234236951'>💠</tg-emoji> Chakra: {nm['chakra']} | Effect: {nm.get('effect','—')}\n"
           f"_{nm.get('desc','')}_\n\n"
           f"━━━━━━━━━━━━━━━━━━━━\n"
           f"<b>Pick which move to REPLACE:</b>\n")
    kb = []
    for i, mv_obj in enumerate(moves):
        txt += (f"  <b>Slot {i+1}:</b> {mv_obj['name']} "
                f"(Pw:{mv_obj['power']} Acc:{mv_obj['acc']}%)\n")
        kb.append([Btn(f"Replace Slot {i+1}: {mv_obj['name'][:22]}",
                       callback_data=f"mvswap:pick:{uid}:{cid}:{i}")])
    kb.append([Btn("Skip (keep current moves)", callback_data=f"mvswap:skip:{uid}")])
    if edit:
        try: await target.edit_message_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))
        except: pass
    else:
        await target.reply_text(txt, parse_mode="HTML", reply_markup=Kbd(kb))


# ─── Callback: move swap menu / pick slot ────────────────────────
async def cb_mvswap(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts = q.data.split(":")
    action = parts[1]; uid = parts[2]
    if str(q.from_user.id) != uid:
        await q.answer("Not your move swap!", show_alert=True); return

    if action == "menu":
        if uid not in PENDING_MOVE_SWAP:
            await q.edit_message_text("<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> No pending move unlocks."); return
        await _send_mvswap_menu(q, uid, PENDING_MOVE_SWAP[uid], edit=True)

    elif action == "skip":
        PENDING_MOVE_SWAP.pop(uid, None)
        await q.edit_message_text(
            "<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> Skipped — your moves were kept unchanged.\n"
            "_The new move unlock is dismissed._",
            parse_mode="HTML")

    elif action == "pick":
        cid   = int(parts[3])
        slot  = int(parts[4])
        if uid not in PENDING_MOVE_SWAP:
            await q.edit_message_text("<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> No pending swap found."); return
        pnd      = PENDING_MOVE_SWAP.pop(uid)
        new_mk   = pnd["new_move_key"]
        new_mv   = pnd["new_move"]
        cname    = pnd["char_name"]
        cd       = get_cdata(cname)
        if not cd:
            await q.edit_message_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Character data not found."); return
        # Replace the chosen slot in the in-memory CHARACTERS list
        # We patch the live CHARACTERS entry for this session.
        if 0 <= slot < len(cd["moves"]):
            old_mv = cd["moves"][slot].copy()
            cd["moves"][slot] = dict(new_mv)
            # ── Persist forgotten move ────────────────────────────
            old_mk = old_mv.get("key") or old_mv["name"].lower().replace(" ","_")
            row2 = _cdoc(await chars_col.find_one({"_id": cid, "uid": uid}, {"forgotten_moves": 1}))
            if row2:
                try:
                    flist_raw = row2.get("forgotten_moves", [])
                    flist = flist_raw if isinstance(flist_raw, list) else json.loads(flist_raw or "[]")
                except Exception:
                    flist = []
                if old_mk not in flist:
                    flist.append(old_mk)
                await chars_col.update_one({"_id": cid, "uid": uid},
                    {"$set": {"forgotten_moves": flist}})
            await q.edit_message_text(
                f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> <b>Move Swapped!</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                f"<b>{cname}</b> replaced:\n"
                f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> {old_mv['name']} (Slot {slot+1})\n"
                f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> <b>{new_mv['name']}</b> (Power: {new_mv['power']} | Acc: {new_mv['acc']}%)\n\n"
                f"_Your new move is active in battles!_",
                parse_mode="HTML")
        else:
            await q.edit_message_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Invalid slot."); return

# ─── /relearn ────────────────────────────────────────────────────
async def cmd_relearn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid = str(update.effective_user.id)
    chars = await db_chars(uid)
    lv100 = [c for c in chars if c["level"] >= 100]
    if not lv100:
        await update.message.reply_text(
            "Relearn requires a character at Level 100.\n"
            "Keep training to reach the max!"); return
    kb = [[Btn(f"{c['char_name']} Lv.{c['level']}", callback_data=f"rl:menu:{c['id']}")]
          for c in lv100[:20]]
    await update.message.reply_text(
        "*Relearn a Forgotten Move*\n"
        "Select a Lv100 character:",
        parse_mode="HTML", reply_markup=Kbd(kb))

# ─── RELEARN ─────────────────────────────────────────────────────
async def cb_relearn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle rl:menu:<cid>, rl:pick:<cid>:<fmk>, rl:slot:<cid>:<fmk>:<slot>."""
    q = update.callback_query; await q.answer()
    uid = str(q.from_user.id)
    parts = q.data.split(":")
    action = parts[1]; cid = int(parts[2])

    # Load char row
    row = _cdoc(await chars_col.find_one({"_id": cid, "uid": uid}))
    if not row:
        await _safe_edit(q, "<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Character not found."); return
    cd = get_cdata(row["char_name"])
    if not cd:
        await _safe_edit(q, "<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Character data not found."); return

    if action == "menu":
        if row["level"] < 100:
            await q.answer(f"Relearn requires Lv100 (you are Lv{row['level']}).", show_alert=True); return
        raw_fm = row.get("forgotten_moves", [])
        try:
            flist = raw_fm if isinstance(raw_fm, list) else json.loads(raw_fm or "[]")
        except Exception:
            flist = []
        if not flist:
            await q.answer("No forgotten moves to relearn.", show_alert=True); return
        # Show forgotten moves as buttons
        btns = []
        for fmk in flist:
            # find move data in cd["moves"] history or all_moves
            mv_data = next((m for m in cd.get("all_moves", cd["moves"]) if
                            (m.get("key") or m["name"].lower().replace(" ","_")) == fmk), None)
            label = mv_data["name"] if mv_data else fmk.replace("_"," ").title()
            btns.append([Btn(label, callback_data=f"rl:pick:{cid}:{fmk}")])
        btns.append([Btn("Cancel", callback_data=f"sv:{cid}")])
        await _safe_edit(q,
            f"<b>{row['char_name']}</b> — Relearn a Forgotten Move\n"
            f"Select the move you want to relearn:", btns)

    elif action == "pick":
        if row["level"] < 100:
            await q.answer("Relearn requires Lv100.", show_alert=True); return
        fmk = parts[3]
        cur_moves = get_char_moves(row["char_name"], row["level"])
        btns = []
        for i, mv in enumerate(cur_moves):
            btns.append([Btn(f"Replace: {mv['name']}", callback_data=f"rl:slot:{cid}:{fmk}:{i}")])
        btns.append([Btn("Cancel", callback_data=f"rl:menu:{cid}")])
        mv_data = next((m for m in cd.get("all_moves", cd["moves"]) if
                        (m.get("key") or m["name"].lower().replace(" ","_")) == fmk), None)
        mv_name = mv_data["name"] if mv_data else fmk.replace("_"," ").title()
        await _safe_edit(q,
            f"<b>Relearn {mv_name}</b>\nChoose which current move to replace:", btns)

    elif action == "slot":
        if row["level"] < 100:
            await q.answer("Relearn requires Lv100.", show_alert=True); return
        fmk = parts[3]; slot = int(parts[4])
        raw_fm = row.get("forgotten_moves", [])
        try:
            flist = raw_fm if isinstance(raw_fm, list) else json.loads(raw_fm or "[]")
        except Exception:
            flist = []
        if fmk not in flist:
            await _safe_edit(q, "<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Move not in forgotten list."); return
        mv_data = next((m for m in cd.get("all_moves", cd["moves"]) if
                        (m.get("key") or m["name"].lower().replace(" ","_")) == fmk), None)
        if not mv_data:
            await _safe_edit(q, "<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Move data not found."); return
        cur_moves = get_char_moves(row["char_name"], row["level"])
        if slot >= len(cur_moves):
            await _safe_edit(q, "<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Invalid slot."); return
        old_mv = cur_moves[slot].copy()
        # Swap in live data
        cd["moves"][slot] = dict(mv_data)
        # Store old move as forgotten, remove relearned from forgotten
        flist.remove(fmk)
        old_mk = old_mv.get("key") or old_mv["name"].lower().replace(" ","_")
        if old_mk not in flist:
            flist.append(old_mk)
        flist_to_save = flist if isinstance(flist, list) else json.loads(flist or "[]")
        await chars_col.update_one({"_id": cid, "uid": uid}, {"$set": {"forgotten_moves": flist_to_save}})
        await _safe_edit(q,
            f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> <b>Move Relearned!</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>{row['char_name']}</b> relearned:\n"
            f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> <b>{mv_data['name']}</b> (Slot {slot+1})\n"
            f"Replaced: {old_mv['name']} → moved to forgotten\n\n"
            f"<i>Active in battles now!</i>")

# ─── GROUP TRACKER ──────────────────────────────────────────────
async def track_group(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Record every group the bot is active in for broadcast."""
    chat = update.effective_chat
    if chat and chat.type in ("group", "supergroup", "channel"):
        try:
            await groups_col.insert_one({"_id": str(chat.id), "title": chat.title or "", "joined_at": datetime.utcnow().isoformat()})
        except Exception:
            pass

# ─── /trade ─────────────────────────────────────────────────────
async def cmd_trade(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await need_account(update): return
    uid_a = str(update.effective_user.id)
    msg   = update.message
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text(
            "<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> <b>How to trade:</b>\nReply to the user you want to trade with and send /trade",
            parse_mode="HTML"); return
    target_user = msg.reply_to_message.from_user
    uid_b = str(target_user.id)
    if uid_b == uid_a:
        await msg.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> You can't trade with yourself!"); return
    if await db_get(uid_b) is None:
        await msg.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> That user hasn't started the bot yet!"); return
    # Cancel any existing trade for this pair
    tkey = f"{uid_a}_{uid_b}"
    TRADE[tkey] = {"step": "wait_agree", "uid_a": uid_a, "uid_b": uid_b,
                   "pick_a": None, "pick_b": None,
                   "name_a": update.effective_user.first_name,
                   "name_b": target_user.first_name}
    kb = [[Btn("Agree",    callback_data=f"trd:agree:{uid_a}:{uid_b}"),
           Btn("Disagree", callback_data=f"trd:no:{uid_a}:{uid_b}")]]
    await msg.reply_text(
        f"<tg-emoji emoji-id='5769455402945090965'>🔄</tg-emoji> <b>Trade Request!</b>\n\n"
        f"<b>{hesc(update.effective_user.first_name)}</b> wants to trade characters with <b>{hesc(target_user.first_name)}</b>!\n\n"
        f"<b>{hesc(target_user.first_name)}</b>, do you accept?",
        parse_mode="HTML", reply_markup=Kbd(kb))

async def _trade_char_list(bot, uid, side, uid_a, uid_b, caption):
    """Send a char-pick list to a specific user."""
    chars = await db_chars(uid)
    if not chars:
        await bot.send_message(uid, "<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> You have no characters to trade!"); return False
    btns = []
    for i, c in enumerate(chars[:20]):    # show up to 20
        rr = RAR.get(get_cdata(c["char_name"])["rarity"] if get_cdata(c["char_name"]) else "Common", "⚪")
        btns.append([Btn(f"{rr} {c['char_name']} Lv.{c['level']}",
                         callback_data=f"trd:pick:{side}:{uid_a}:{uid_b}:{c['id']}")])
    await bot.send_message(uid, caption, parse_mode="HTML", reply_markup=Kbd(btns))
    return True

async def cb_trade(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q   = update.callback_query; await q.answer()
    uid = str(q.from_user.id)
    parts = q.data.split(":")   # trd:action:...

    action = parts[1]

    # ── Agree / Disagree ────────────────────────────────────────
    if action in ("agree", "no"):
        uid_a, uid_b = parts[2], parts[3]
        tkey = f"{uid_a}_{uid_b}"
        state = TRADE.get(tkey)
        if not state:
            await q.edit_message_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Trade expired!"); return
        if uid != uid_b:
            await q.answer("Only the invited player can respond!", show_alert=True); return
        if action == "no":
            del TRADE[tkey]
            await q.edit_message_text(f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> <b>{state['name_b']}</b> declined the trade.",
                                      parse_mode="HTML"); return
        # Agreed — show both users their char lists
        state["step"] = "picking"
        await q.edit_message_text(
            f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> <b>{state['name_b']}</b> agreed! Both players, pick a character to trade.\n"
            f"Check your DMs for your character list!", parse_mode="HTML")
        ok_a = await _trade_char_list(ctx.bot, uid_a, "a", uid_a, uid_b,
            f"<tg-emoji emoji-id='5769455402945090965'>🔄</tg-emoji> <b>Trade with {state['name_b']}</b>\nPick the character you want to offer:")
        ok_b = await _trade_char_list(ctx.bot, uid_b, "b", uid_a, uid_b,
            f"<tg-emoji emoji-id='5769455402945090965'>🔄</tg-emoji> <b>Trade with {state['name_a']}</b>\nPick the character you want to offer:")
        if not ok_a or not ok_b:
            TRADE.pop(tkey, None)

    # ── Character pick ──────────────────────────────────────────
    elif action == "pick":
        side, uid_a, uid_b = parts[2], parts[3], parts[4]
        char_id = int(parts[5])
        tkey = f"{uid_a}_{uid_b}"
        state = TRADE.get(tkey)
        if not state or state.get("step") != "picking":
            await q.answer("Trade expired!", show_alert=True); return
        expected_uid = uid_a if side == "a" else uid_b
        if uid != expected_uid:
            await q.answer("This isn't your pick!", show_alert=True); return
        # Record pick
        chars_of_picker = await db_chars(uid)
        picked = next((c for c in chars_of_picker if c["id"] == char_id), None)
        if not picked:
            await q.answer("Character not found!", show_alert=True); return
        state[f"pick_{side}"] = picked
        picker_name = state["name_a"] if side == "a" else state["name_b"]
        await q.edit_message_text(
            f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> <b>{picker_name}</b> selected <b>{picked['char_name']}</b> (Lv.{picked['level']})!\n"
            f"Waiting for the other player…", parse_mode="HTML")
        # Both picked? Show confirmation
        if state.get("pick_a") and state.get("pick_b"):
            pa, pb = state["pick_a"], state["pick_b"]
            conf_txt = (f"<tg-emoji emoji-id='5769455402945090965'>🔄</tg-emoji> <b>Final Trade Confirmation</b>\n\n"
                        f"<b>{hesc(state['name_a'])}</b> gives: <b>{hesc(pa['char_name'])}</b> Lv.{pa['level']}\n"
                        f"<b>{hesc(state['name_b'])}</b> gives: <b>{hesc(pb['char_name'])}</b> Lv.{pb['level']}\n\n"
                        f"Do BOTH players agree?")
            state["step"] = "confirm"
            state["conf_a"] = False; state["conf_b"] = False
            kb = [[Btn("Confirm Trade", callback_data=f"trd:conf:{uid_a}:{uid_b}"),
                   Btn("Cancel",        callback_data=f"trd:cancel:{uid_a}:{uid_b}")]]
            await ctx.bot.send_message(uid_a, conf_txt, parse_mode="HTML", reply_markup=Kbd(kb))
            await ctx.bot.send_message(uid_b, conf_txt, parse_mode="HTML", reply_markup=Kbd(kb))

    # ── Final confirm ────────────────────────────────────────────
    elif action == "conf":
        uid_a, uid_b = parts[2], parts[3]
        tkey = f"{uid_a}_{uid_b}"
        state = TRADE.get(tkey)
        if not state or state.get("step") != "confirm":
            await q.answer("Trade expired!", show_alert=True); return
        if uid == uid_a:   state["conf_a"] = True
        elif uid == uid_b: state["conf_b"] = True
        else:
            await q.answer("Not your trade!", show_alert=True); return
        await q.edit_message_text("<tg-emoji emoji-id='5803204762035818905'>⏳</tg-emoji> Waiting for the other player to confirm…")
        if state["conf_a"] and state["conf_b"]:
            # Execute trade
            pa, pb = state["pick_a"], state["pick_b"]
            await chars_col.update_one({"_id": pa["id"]}, {"$set": {"uid": uid_b, "in_team": 0, "slot": 0}})
            await chars_col.update_one({"_id": pb["id"]}, {"$set": {"uid": uid_a, "in_team": 0, "slot": 0}})
            del TRADE[tkey]
            done_txt = (f"<tg-emoji emoji-id='5426976939850080222'>🎉</tg-emoji> <b>Trade Complete!</b>\n\n"
                        f"<b>{hesc(state['name_a'])}</b> received: <b>{hesc(pb['char_name'])}</b>\n"
                        f"<b>{hesc(state['name_b'])}</b> received: <b>{hesc(pa['char_name'])}</b>")
            await ctx.bot.send_message(uid_a, done_txt, parse_mode="HTML")
            await ctx.bot.send_message(uid_b, done_txt, parse_mode="HTML")

    # ── Cancel ───────────────────────────────────────────────────
    elif action == "cancel":
        uid_a, uid_b = parts[2], parts[3]
        tkey = f"{uid_a}_{uid_b}"
        state = TRADE.pop(tkey, None)
        await q.edit_message_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Trade cancelled.")
        if state:
            other = uid_b if uid == uid_a else uid_a
            try: await ctx.bot.send_message(other, "<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> The trade was cancelled.")
            except: pass

# ─── /getemoji — extract custom emoji IDs (Admin) ────────────────
async def cmd_getemoji(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid != ADMIN_ID:
        await update.message.reply_text("Admin only."); return
    msg = update.message
    entities   = list(msg.entities or [])
    entities  += list(msg.caption_entities or [])
    text = msg.text or msg.caption or ""
    found = []
    seen = set()
    for e in entities:
        if e.type == "custom_emoji" and e.custom_emoji_id not in seen:
            seen.add(e.custom_emoji_id)
            char = text[e.offset : e.offset + e.length]
            found.append((e.custom_emoji_id, char))
    if not found:
        await msg.reply_text(
            "<b>No custom emoji found in this message.</b>\n\n"
            "<b>How to use:</b>\n"
            "1. Find a Naruto emoji pack on Telegram (search: <i>Naruto Emoji</i>, <i>Shinobi Pack</i>)\n"
            "2. Send a message containing those emoji to this chat (or forward one)\n"
            "3. Reply to that message with /getemoji\n\n"
            "<i>The bot will instantly reply with each emoji's ID so you can paste it into the PE dict.</i>",
            parse_mode="HTML"); return
    lines = ["<b>Custom Emoji IDs detected:</b>\n"]
    for eid, char in found:
        lines.append(f"{char}  →  <code>{eid}</code>")
    lines.append("\n<i>Copy the ID into the matching PE dict key in the bot file.</i>")
    await msg.reply_text("\n".join(lines), parse_mode="HTML")


async def track_admin_emoji(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Auto-detect custom emoji or stickers in any private message from the admin."""
    if not update.message: return
    uid = str(update.effective_user.id)
    if uid != ADMIN_ID: return

    # ── Case 1: message contains inline custom emoji ──────────────
    entities  = list(update.message.entities or [])
    entities += list(update.message.caption_entities or [])
    text = update.message.text or update.message.caption or ""
    found = []
    seen: set = set()
    for e in entities:
        if e.type == "custom_emoji" and e.custom_emoji_id not in seen:
            seen.add(e.custom_emoji_id)
            char = text[e.offset : e.offset + e.length]
            found.append((e.custom_emoji_id, char))
    if found:
        # Use the first emoji ID to look up the full pack automatically
        first_eid = found[0][0]
        loading_msg = await update.message.reply_text(
            "🔍 Detected custom emoji — fetching full pack…", parse_mode="HTML")
        try:
            emoji_stickers = await ctx.bot.get_custom_emoji_stickers([first_eid])
            set_name = (emoji_stickers[0].set_name if emoji_stickers else None)
        except Exception:
            set_name = None

        if set_name:
            # Fetch every emoji in the pack
            try:
                sticker_set = await ctx.bot.get_sticker_set(set_name)
                all_items = sticker_set.stickers
                real_emoji = [(s, getattr(s, "custom_emoji_id", None))
                              for s in all_items
                              if getattr(s, "custom_emoji_id", None)]
                plain_count = len(all_items) - len(real_emoji)
                lines = [
                    f"<b>Pack:</b> {hesc(sticker_set.title)}",
                    f"<b>Name:</b> <code>{hesc(set_name)}</code>",
                    f"<b>Total:</b> {len(all_items)}  |  "
                    f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> Custom emoji: <b>{len(real_emoji)}</b>  |  "
                    f"🖼 Plain stickers: <b>{plain_count}</b>\n",
                    "<b><tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> All custom emoji IDs (copy into PE dict):</b>",
                ]
                for s, eid in real_emoji:
                    icon = s.emoji or "?"
                    lines.append(f"  {hesc(icon)}  <code>{eid}</code>")
                lines.append("\n<i>Tell me which PE key each ID belongs to and I'll add it for you.</i>")
                full_text = "\n".join(lines)
                chunks = [full_text[i:i+4000] for i in range(0, len(full_text), 4000)]
                await loading_msg.edit_text(chunks[0], parse_mode="HTML")
                for chunk in chunks[1:]:
                    await update.message.reply_text(chunk, parse_mode="HTML")
                return
            except Exception as e:
                # Fall back to showing individual IDs
                await loading_msg.edit_text(
                    f"<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji> Found pack <code>{hesc(set_name)}</code> but couldn't fetch it: {hesc(str(e))}\n\n"
                    f"Run /findpack {hesc(set_name)} manually.",
                    parse_mode="HTML")
                return
        else:
            # No pack found — just show the individual IDs
            lines = ["<b><tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> Custom emoji IDs:</b>\n"]
            for eid, char in found:
                lines.append(f"{char}  →  <code>{eid}</code>")
            lines.append("\n<i>Paste each ID into the matching PE dict key in the bot file.</i>")
            await loading_msg.edit_text("\n".join(lines), parse_mode="HTML")
        return

    # ── Case 2: sticker forwarded — auto-fetch the whole pack ─────
    sticker = update.message.sticker
    if sticker:
        set_name = sticker.set_name or ""
        this_eid = getattr(sticker, "custom_emoji_id", None)
        this_icon = sticker.emoji or "?"

        if not set_name:
            # Single sticker with no pack — just show its own ID
            await update.message.reply_text(
                f"<b>Single sticker (no pack):</b>\n"
                f"{this_icon}  <code>{this_eid or sticker.file_unique_id}</code>",
                parse_mode="HTML")
            return

        # Fetch the full pack automatically
        loading_msg = await update.message.reply_text(
            f"🔍 Fetching pack <code>{hesc(set_name)}</code>…", parse_mode="HTML")
        try:
            sticker_set = await ctx.bot.get_sticker_set(set_name)
        except Exception as e:
            await loading_msg.edit_text(
                f"<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Could not fetch pack <code>{hesc(set_name)}</code>\nError: {hesc(str(e))}",
                parse_mode="HTML")
            return

        all_stickers = sticker_set.stickers
        real_emoji   = [(s, getattr(s, "custom_emoji_id", None))
                        for s in all_stickers
                        if getattr(s, "custom_emoji_id", None)]
        plain_count  = len(all_stickers) - len(real_emoji)

        lines = [
            f"<b>Pack:</b> {hesc(sticker_set.title)}",
            f"<b>Name:</b> <code>{hesc(set_name)}</code>",
            f"<b>Total:</b> {len(all_stickers)}  |  "
            f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> Custom emoji: <b>{len(real_emoji)}</b>  |  "
            f"🖼 Plain stickers: <b>{plain_count}</b>\n",
        ]

        if real_emoji:
            lines.append("<b><tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> Custom emoji IDs (paste into PE dict):</b>")
            for s, eid in real_emoji[:50]:
                icon = s.emoji or "?"
                lines.append(f"  {hesc(icon)}  <code>{eid}</code>")
            if len(real_emoji) > 50:
                lines.append(f"  <i>…and {len(real_emoji)-50} more. Run /findpack {hesc(set_name)} to see all.</i>")
            lines.append("\n<i>Copy any ID and tell me which PE key to assign it to.</i>")
        else:
            lines.append(
                "<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji> <b>This is a regular sticker pack — no custom emoji inside.</b>\n\n"
                "<b>Forward a sticker from an emoji pack instead.</b>\n"
                "To find emoji packs: search Telegram for\n"
                "<i>Naruto Emoji</i> · <i>Shinobi Emoji</i> · <i>Anime RPG Emoji</i>\n"
                "then forward any item from it here."
            )

        full_text = "\n".join(lines)
        # Edit the loading message with the first chunk; send further chunks as new messages
        chunks = [full_text[i:i+4000] for i in range(0, len(full_text), 4000)]
        await loading_msg.edit_text(chunks[0], parse_mode="HTML")
        for chunk in chunks[1:]:
            await update.message.reply_text(chunk, parse_mode="HTML")


# ─── /findpack — fetch all custom emoji IDs from a sticker pack ──
async def cmd_emoji(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Send the full list of emoji keys registered in the bot's PE dict."""
    uid = str(update.effective_user.id)
    if uid != ADMIN_ID:
        await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Admin only."); return

    # Group keys by section comment order in PE dict
    sections = {
        "<tg-emoji emoji-id='5999047234849611002'>⚙️</tg-emoji> UI Chrome": [
            "sword","shield","hp","chakra","star","coin","fire","lightning",
            "skull","trophy","scroll","village","clan","rank","diamond",
            "leaf","stone","exp","team","summon","shop","daily","map",
        ],
        "<tg-emoji emoji-id='5426872512015244606'>🍃</tg-emoji> Naruto-Specific": [
            "kunai","sharingan","rasengan","sage","bijuu","anbu",
            "akatsuki","curse","byakugan","susanoo","round",
        ],
        "<tg-emoji emoji-id='6001182426301209831'>🔥</tg-emoji> MostRandomPack — Core": [
            "flame","chain","blood","bolt","moon2","web","gem2",
        ],
        "<tg-emoji emoji-id='5798530836890390483'>🔴</tg-emoji> Colored Dots (HP / Status)": [
            "dot_red","dot_blue","dot_green","dot_purple",
            "dot_yellow","dot_white","dot_black",
        ],
        "<tg-emoji emoji-id='6003600664687546316'>🐺</tg-emoji> Extra Objects": [
            "wolf","wolf2","bat","spider","heart2","triangle","smirk",
            "cool","devil2","star3","diamond3","fire4","ghost","web2","hat","turtle",
        ],
    }

    CHUNK_LIMIT = 3600
    header = (
        f"<tg-emoji emoji-id='5426895906702107044'>📋</tg-emoji> <b>Bot Emoji List</b>  (<code>{len(PE)}</code> keys)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Use pe('key') in any HTML message to show the custom emoji.</i>\n\n"
    )

    lines: list[str] = [header]
    for section_title, keys in sections.items():
        lines.append(f"\n<b>{hesc(section_title)}</b>")
        for key in keys:
            if key not in PE:
                continue
            emoji_tag = pe(key)
            eid = PE[key]
            lines.append(f"  {emoji_tag} <code>{hesc(key)}</code>  <code>{eid}</code>")

    # Any keys not listed in sections (future additions)
    listed = {k for keys in sections.values() for k in keys}
    extra = [k for k in PE if k not in listed]
    if extra:
        lines.append(f"\n<b><tg-emoji emoji-id='5427397421443325675'>🆕</tg-emoji> Other</b>")
        for key in extra:
            emoji_tag = pe(key)
            eid = PE[key]
            lines.append(f"  {emoji_tag} <code>{hesc(key)}</code>  <code>{eid}</code>")

    # Send in safe line-based chunks
    current_chunk: list[str] = []
    current_len = 0
    for line in lines:
        line_len = len(line) + 1
        if current_chunk and current_len + line_len > CHUNK_LIMIT:
            await update.message.reply_text("\n".join(current_chunk), parse_mode="HTML")
            current_chunk = []
            current_len = 0
        current_chunk.append(line)
        current_len += line_len
    if current_chunk:
        await update.message.reply_text("\n".join(current_chunk), parse_mode="HTML")


async def cmd_findpack(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid != ADMIN_ID:
        await update.message.reply_text("Admin only."); return
    if not ctx.args:
        await update.message.reply_text(
            "<b>Usage:</b> /findpack &lt;pack_name&gt;\n\n"
            "<b>How to find a pack name (no Premium needed):</b>\n"
            "1. Google: <i>naruto telegram emoji pack site:t.me</i>\n"
            "2. You will find links like <code>t.me/addemoji/PackName</code>\n"
            "3. The pack name is the last part — e.g. <code>PackName</code>\n"
            "4. Run: /findpack PackName\n\n"
            "<b>Or:</b> forward any sticker from a pack to this chat and the bot will tell you the pack name automatically.",
            parse_mode="HTML"); return

    # Accept full URLs like https://t.me/addemoji/PackName or t.me/addemoji/PackName
    raw = " ".join(ctx.args).strip()
    if "/" in raw:
        pack_name = raw.rstrip("/").split("/")[-1]
    else:
        pack_name = raw
    await update.message.reply_text(f"🔍 Looking up pack <code>{hesc(pack_name)}</code>…", parse_mode="HTML")
    try:
        sticker_set = await ctx.bot.get_sticker_set(pack_name)
    except Exception as e:
        await update.message.reply_text(
            f"<b>Could not find pack:</b> <code>{hesc(pack_name)}</code>\n"
            f"Error: {hesc(str(e))}\n\n"
            f"<i>Make sure the pack name is exactly as it appears in the t.me/addemoji/... link.</i>",
            parse_mode="HTML"); return

    stickers = sticker_set.stickers
    if not stickers:
        await update.message.reply_text("Pack found but has no stickers."); return

    # Separate real custom emoji from regular stickers
    emoji_stickers = [(s, getattr(s, "custom_emoji_id", None)) for s in stickers]
    real_emoji  = [(s, eid) for s, eid in emoji_stickers if eid]
    plain_stickers = [s for s, eid in emoji_stickers if not eid]

    lines = [
        f"<b>Pack:</b> {hesc(sticker_set.title)}",
        f"<b>Name:</b> <code>{hesc(pack_name)}</code>",
        f"<b>Total items:</b> {len(stickers)}  |  "
        f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> Custom emoji: <b>{len(real_emoji)}</b>  |  "
        f"🖼 Regular stickers: <b>{len(plain_stickers)}</b>\n",
    ]

    if real_emoji:
        lines.append("<b><tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> CUSTOM EMOJI — paste these IDs into PE dict:</b>")
        for idx, (s, eid) in enumerate(real_emoji[:500], start=1):
            icon = s.emoji or "?"
            lines.append(f"  <code>{idx}.</code> {hesc(icon)}  <code>{eid}</code>")
        if len(real_emoji) > 500:
            lines.append(f"  <i>…and {len(real_emoji)-500} more (showing first 500)</i>")
    else:
        lines.append(
            "<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji> <b>No custom emoji found in this pack.</b>\n"
            "This is a regular sticker pack — its IDs cannot be used as inline emoji.\n\n"
            "<b>To find a pack that HAS custom emoji:</b>\n"
            "• Search Telegram for: <i>Naruto Emoji</i>, <i>Shinobi Emoji</i>, <i>Anime RPG Emoji</i>\n"
            "• Open the pack link (t.me/addemoji/PackName)\n"
            "• Copy the <b>PackName</b> from the URL and run: /findpack PackName\n\n"
            "<b>Known Naruto emoji packs to try:</b>\n"
            "  /findpack NarutoEmoji\n"
            "  /findpack NarutoRPGEmoji\n"
            "  /findpack ShinobiEmoji\n"
            "  /findpack AnimeRPGEmoji"
        )

    lines.append("\n<i>Paste each ID into the matching PE dict key in the bot file, then restart.</i>")

    # Send in safe chunks — split by LINE so HTML tags are never cut mid-way
    CHUNK_LIMIT = 3800
    current_chunk: list[str] = []
    current_len = 0
    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if current_chunk and current_len + line_len > CHUNK_LIMIT:
            await update.message.reply_text("\n".join(current_chunk), parse_mode="HTML")
            current_chunk = []
            current_len = 0
        current_chunk.append(line)
        current_len += line_len
    if current_chunk:
        await update.message.reply_text("\n".join(current_chunk), parse_mode="HTML")


# ─── /broadcast ──────────────────────────────────────────────────
async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid != ADMIN_ID:
        await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Admin only command!"); return
    text = " ".join(ctx.args) if ctx.args else ""
    if not text:
        await update.message.reply_text(
            "📢 <b>Usage:</b> /broadcast &lt;message&gt;\n\nThis will send to all users and groups.",
            parse_mode="HTML"); return
    broadcast_msg = f"📢 <b>Announcement</b>\n\n{hesc(text)}"
    users = [d["_id"] async for d in users_col.find({}, {"_id": 1})]
    groups = [d["_id"] async for d in groups_col.find({}, {"_id": 1})]
    sent = 0; failed = 0
    for target_id in users + groups:
        try:
            await ctx.bot.send_message(target_id, broadcast_msg, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)  # Telegram rate limit
        except Exception:
            failed += 1
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> <b>Broadcast done!</b>\n\n"
        f"📨 Sent: <b>{sent}</b>\n<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Failed: <b>{failed}</b>",
        parse_mode="HTML")

# ─── /botstats ───────────────────────────────────────────────────
async def cmd_botstats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid != ADMIN_ID:
        await update.message.reply_text("<tg-emoji emoji-id='5803134797018566405'>❌</tg-emoji> Admin only command!"); return
    user_count = await users_col.count_documents({})
    group_count = await groups_col.count_documents({})
    char_count = await chars_col.count_documents({})
    agg = await users_col.aggregate([{"$group": {"_id": None, "total_wins": {"$sum": "$wins"}}}]).to_list(1)
    total_wins = agg[0]["total_wins"] if agg else 0
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5981204549132619885'>📊</tg-emoji> <b>Bot Statistics</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5425113284820869526'>👥</tg-emoji> Total Users: <b>{user_count:,}</b>\n"
        f"<tg-emoji emoji-id='5427342518876381603'>🏘️</tg-emoji> Total Groups: <b>{group_count:,}</b>\n"
        f"🃏 Total Characters: <b>{char_count:,}</b>\n"
        f"<tg-emoji emoji-id='6035338995536238141'>⚔️</tg-emoji> Total Battles Won: <b>{total_wins:,}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 Characters in DB: <b>{len(CHARACTERS)}</b>\n"
        f"🏪 Shop Items: <b>{len(SHOP)}</b>",
        parse_mode="HTML")

# ─── STARTUP ────────────────────────────────────────────────────
async def _preload_banners():
    """Download all banner images to memory so they never fail due to CDN issues."""
    import httpx
    urls = [START_BANNER, SUMMON_BANNER, SHOP_BANNER, STATS_BANNER,
            VILLAGE_BANNER, CLAN_BANNER]
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        for url in urls:
            try:
                r = await client.get(url)
                if r.status_code == 200 and r.content:
                    _BANNER_CACHE[url] = r.content
                    print(f"<tg-emoji emoji-id='5224388744156557558'>✅</tg-emoji> Banner cached: {url[-30:]} ({len(r.content)} bytes)")
                else:
                    print(f"<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji> Banner fetch failed {r.status_code}: {url[-30:]}")
            except Exception as e:
                print(f"<tg-emoji emoji-id='5803297348645818019'>⚠️</tg-emoji> Banner fetch error {url[-30:]}: {e}")

def _get_banner(url: str):
    """Return io.BytesIO from cache.
    Falls back to START_BANNER bytes if the primary URL failed to pre-download
    (catbox.moe is unreachable from Replit — supabase URLs always work).
    This guarantees a photo message is always sent so edit_message_media works.
    """
    data = _BANNER_CACHE.get(url)
    if data:
        buf = io.BytesIO(data)
        buf.name = "banner.jpg"
        return buf
    # Primary URL not cached (e.g. catbox.moe blocked) — use START_BANNER fallback
    data = _BANNER_CACHE.get(START_BANNER)
    if data:
        buf = io.BytesIO(data)
        buf.name = "banner.jpg"
        return buf
    # Nothing cached yet — return URL string and let Telegram try to download it
    return url

async def post_init(app):
    await init_db()
    asyncio.create_task(PHOTO_CACHE.load())
    asyncio.create_task(JUTSU_CACHE.load())
    asyncio.create_task(MOVE_IMAGE_CACHE.load())
    asyncio.create_task(_preload_banners())
    cmds=[
        BotCommand("start","Main menu + banner"),
        BotCommand("profile","Full shinobi profile"),
        BotCommand("mychar","Browse char list (paginated)"),
        BotCommand("info","Character info — /info Naruto"),
        BotCommand("team","Active team"),
        BotCommand("explore","Battle wild enemies"),
        BotCommand("battle","PvP — reply to challenge"),
        BotCommand("train","Level up / stat train"),
        BotCommand("shop","Browse shop (paginated)"),
        BotCommand("nickname","Set display name"),
        BotCommand("summon","Pull characters"),
        BotCommand("daily","Daily NC reward"),
        BotCommand("mission","Daily mission"),
        BotCommand("heal","Restore HP 300 NC"),
        BotCommand("inventory","Items and resources"),
        BotCommand("transform","Transform list"),
        BotCommand("nature","Nature type chart"),
        BotCommand("kekkei","Kekkei Genkai list"),
        BotCommand("ability","Your active abilities"),
        BotCommand("village","Join a village"),
        BotCommand("clan","Join a clan"),
        BotCommand("beast","Tailed Beast lore"),
        BotCommand("jutsu","Jutsu reference"),
        BotCommand("leaderboard","Global leaderboard"),
        BotCommand("rank","Your rank"),
        BotCommand("top","Top players"),
        BotCommand("chakra","Chakra and stone status"),
        BotCommand("gift","Gift NC to someone"),
        BotCommand("help","Full help menu"),
        BotCommand("wiki","Character encyclopedia — /wiki Naruto"),
        BotCommand("dataweapon","Weapon database — /dataweapon [name]"),
        BotCommand("meditate","Free chakra regen — 4h cooldown"),
        BotCommand("bounty","Daily bounty board for bonus NC"),
        BotCommand("sacrifice","Sacrifice a char for NC + stone"),
        BotCommand("pity","Check gacha pity counter"),
        BotCommand("trade","Trade chars — reply to a user"),
        BotCommand("newmove","Pick which move to replace on level-up"),
        BotCommand("relearn","Relearn a forgotten move (requires Lv100)"),
        BotCommand("travel","Explore areas within your village"),
        BotCommand("map","World map — all villages and locations"),
        BotCommand("location","Your current village and area info"),
        BotCommand("hunt","Hunt for loot and stones — 30 min cooldown"),
        BotCommand("boss","Challenge a Legendary boss — big rewards"),
        BotCommand("adminclan","(Admin) Set a user as clan admin for approval"),
        BotCommand("close","Dismiss the reply keyboard"),
        BotCommand("add","(Admin) Add coins/chakra/chars/etc to user"),
        BotCommand("broadcast","(Admin) Broadcast to all users+groups"),
        BotCommand("botstats","(Admin) Total users, groups, chars"),
        BotCommand("equip","Equip a weapon — /equip <weapon_id>"),
        BotCommand("myweapons","View your weapon inventory"),
        BotCommand("buy_weapon","Buy a weapon — /buy_weapon <id>"),
        BotCommand("claninfo","View your clan hierarchy and glory"),
        BotCommand("ban","(Admin) Ban a user — /ban <user_id>"),
        BotCommand("unban","(Admin) Unban a user — /unban <user_id>"),
        BotCommand("resetuser","(Admin) Wipe a user's data — /resetuser <id>"),
        BotCommand("setclanrank","(Admin) Set clan rank — /setclanrank <id> <rank>"),
        BotCommand("getemoji","(Admin) Extract custom emoji IDs from a message"),
        BotCommand("findpack","(Admin) List all emoji IDs from a sticker pack — /findpack PackName"),
    ]
    await app.bot.set_my_commands(cmds)

def main():
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    for cmd,fn in [
        ("start",cmd_start),("profile",cmd_profile),
        ("mychar",cmd_mychar),
        ("info",cmd_info),("team",cmd_team),
        ("explore",cmd_explore),("battle",cmd_battle),
        ("train",cmd_train),("transform",cmd_transform),
        ("shop",cmd_shop),("nickname",cmd_nickname),
        ("summon",cmd_summon),("daily",cmd_daily),("mission",cmd_mission),
        ("heal",cmd_heal),("inventory",cmd_inventory),
        ("nature",cmd_nature),("kekkei",cmd_kekkei),("ability",cmd_ability),
        ("village",cmd_village),("clan",cmd_clan),("beast",cmd_beast),
        ("jutsu",cmd_jutsu),("moves",cmd_moves),
        ("leaderboard",cmd_leaderboard),("rank",cmd_rank),
        ("top",cmd_top),
        ("chakra",cmd_chakra),("gift",cmd_gift),("help",cmd_help),
        ("wiki",cmd_wiki),("exchange",cmd_exchange),
        ("duel",cmd_duel),
        # New commands
        ("dataweapon",cmd_dataweapon),
        ("meditate",cmd_meditate),
        ("bounty",cmd_bounty),
        ("sacrifice",cmd_sacrifice),
        ("pity",cmd_pity),
        ("trade",cmd_trade),
        ("add",cmd_add),("newmove",cmd_newmove),
        ("relearn",cmd_relearn),
        ("broadcast",cmd_broadcast),("botstats",cmd_botstats),
        # Travel + close
        ("travel",cmd_travel),("close",cmd_close),
        # New channel-inspired commands
        ("map",cmd_map),("location",cmd_location),
        ("hunt",cmd_hunt),("boss",cmd_boss),
        ("adminclan",cmd_adminclan),
        # Weapons
        ("equip",cmd_equip),("myweapons",cmd_myweapons),("buy_weapon",cmd_buy_weapon),
        # Clan
        ("claninfo",cmd_claninfo),("setclanrank",cmd_setclanrank),
        # Admin ban/reset
        ("ban",cmd_ban),("unban",cmd_unban),("resetuser",cmd_resetuser),
        # Premium emoji helper
        ("getemoji",cmd_getemoji),
        ("findpack",cmd_findpack),
        ("emoji",cmd_emoji),
        ("update",cmd_update),
    ]:
        app.add_handler(CommandHandler(cmd,fn))

    app.add_handler(CallbackQueryHandler(cb_starter,        pattern=r"^st:"))
    app.add_handler(CallbackQueryHandler(cb_mychars,         pattern=r"^mc:\d+:"))
    app.add_handler(CallbackQueryHandler(cb_mychar_list,     pattern=r"^ml:"))
    app.add_handler(CallbackQueryHandler(cb_mychar_list,     pattern=r"^mcd:"))
    app.add_handler(CallbackQueryHandler(cb_mychar_list,     pattern=r"^noop$"))
    app.add_handler(CallbackQueryHandler(cb_levelup,         pattern=r"^lv:"))
    app.add_handler(CallbackQueryHandler(cb_levelup_confirm, pattern=r"^lvc:"))
    app.add_handler(CallbackQueryHandler(cb_train,           pattern=r"^tr:"))
    app.add_handler(CallbackQueryHandler(cb_explore,         pattern=r"^ex:"))
    app.add_handler(CallbackQueryHandler(cb_pvp_challenge,   pattern=r"^pv:"))
    app.add_handler(CallbackQueryHandler(cb_pvp_move,        pattern=r"^pm:"))
    app.add_handler(CallbackQueryHandler(cb_pvp_forfeit,     pattern=r"^pf:"))
    app.add_handler(CallbackQueryHandler(cb_pvp_transform,   pattern=r"^pvtf:"))
    app.add_handler(CallbackQueryHandler(cb_shop,            pattern=r"^sh:"))
    app.add_handler(CallbackQueryHandler(cb_shop_page,       pattern=r"^sp:"))
    app.add_handler(CallbackQueryHandler(cb_inventory,       pattern=r"^inv:"))
    app.add_handler(CallbackQueryHandler(cb_summon,          pattern=r"^sm:"))
    app.add_handler(CallbackQueryHandler(cb_wiki,            pattern=r"^wk:"))
    app.add_handler(CallbackQueryHandler(cb_village_preview, pattern=r"^vp:"))
    app.add_handler(CallbackQueryHandler(cb_village,         pattern=r"^vj:"))
    app.add_handler(CallbackQueryHandler(cb_village_back,    pattern=r"^vback$"))
    app.add_handler(CallbackQueryHandler(cb_clan,            pattern=r"^cj:"))
    app.add_handler(CallbackQueryHandler(cb_nature,          pattern=r"^nat:"))
    app.add_handler(CallbackQueryHandler(cb_kekkei,          pattern=r"^kk:"))
    app.add_handler(CallbackQueryHandler(cb_beast,           pattern=r"^bs:"))
    app.add_handler(CallbackQueryHandler(cb_lb,              pattern=r"^lb:"))
    app.add_handler(CallbackQueryHandler(cb_stats_view,      pattern=r"^sv:"))
    app.add_handler(CallbackQueryHandler(cb_info,            pattern=r"^info:"))
    app.add_handler(CallbackQueryHandler(cb_moves_view,      pattern=r"^mv:"))
    app.add_handler(CallbackQueryHandler(cb_mission,         pattern=r"^ms:"))
    app.add_handler(CallbackQueryHandler(cb_help,            pattern=r"^hl:"))
    app.add_handler(CallbackQueryHandler(cb_team,            pattern=r"^tm:"))
    app.add_handler(CallbackQueryHandler(cb_train_page,      pattern=r"^tn:pg:"))
    app.add_handler(CallbackQueryHandler(cb_exchange,        pattern=r"^xc:"))
    app.add_handler(CallbackQueryHandler(cb_menu,            pattern=r"^menu:"))
    app.add_handler(CallbackQueryHandler(cb_misc,            pattern=r"^cmd:"))
    app.add_handler(CallbackQueryHandler(cb_transform_page,  pattern=r"^tfpg:"))
    # New callback handlers
    app.add_handler(CallbackQueryHandler(cb_rebirth_token,   pattern=r"^rbtk:"))
    app.add_handler(CallbackQueryHandler(cb_gamble,          pattern=r"^gb:"))
    app.add_handler(CallbackQueryHandler(cb_forge,           pattern=r"^fg:"))
    app.add_handler(CallbackQueryHandler(cb_sacrifice,       pattern=r"^sc:"))
    app.add_handler(CallbackQueryHandler(cb_mvswap,          pattern=r"^mvswap:"))
    app.add_handler(CallbackQueryHandler(cb_relearn,         pattern=r"^rl:"))
    app.add_handler(CallbackQueryHandler(cb_trade,           pattern=r"^trd:"))
    # Travel callbacks
    app.add_handler(CallbackQueryHandler(cb_travel,          pattern=r"^trv:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_travel_explore,  pattern=r"^trv_ex:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_travel_back,     pattern=r"^trv_back$"))
    # Boss callbacks
    app.add_handler(CallbackQueryHandler(cb_boss,            pattern=r"^boss:"))
    # Weapon shop callbacks
    app.add_handler(CallbackQueryHandler(cb_weapon_shop,      pattern=r"^wp:"))
    # Clan join request approval (admin approve/deny)
    app.add_handler(CallbackQueryHandler(cb_clan_request,    pattern=r"^clreq:"))
    # Admin private chat — auto-extract custom emoji IDs (group=1, runs before group tracker)
    from telegram.ext import MessageHandler, filters as tg_filters
    app.add_handler(MessageHandler(
        tg_filters.ChatType.PRIVATE & tg_filters.ALL,
        track_admin_emoji), group=1)
    # Group tracker — low priority, catches all messages in groups
    app.add_handler(MessageHandler(tg_filters.ChatType.GROUPS, track_group), group=99)

    print("<tg-emoji emoji-id='5426872512015244606'>🍃</tg-emoji> Naruto RPG Bot v3 — Enhanced Edition")
    print(f"<tg-emoji emoji-id='5981204549132619885'>📊</tg-emoji> Loaded {len(CHARACTERS)} characters | {len(WILDS)} wild types | {len(SHOP)} shop items")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
