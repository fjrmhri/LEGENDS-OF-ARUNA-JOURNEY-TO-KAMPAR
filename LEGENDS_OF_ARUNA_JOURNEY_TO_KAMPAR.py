"""
LEGENDS OF ARUNA: JOURNEY TO KAMPAR
Telegram Turn-Based Text RPG
================================

- Satu file Python.
- Menggunakan python-telegram-bot v20+ (async).
- Fokus: sistem state user, scene story, kota, hutan, battle sederhana, stats & skill dasar.
- Banyak konten dari GDD sudah disusun sebagai data, tapi kamu bebas menambah/merapikan.

Cara pakai (singkat):
1. pip install python-telegram-bot==20.7
2. Isi TOKEN_BOT di bawah.
3. Jalankan: python legends_of_aruna_bot.py
4. Chat bot di Telegram, pakai /start

NB: Untuk produksi, sebaiknya simpan state di database, bukan di memory seperti contoh ini.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import random

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ==========================
# KONFIGURASI
# ==========================

TOKEN_BOT = "ISI_TOKEN_BOT_KAMU_DI_SINI"  # <--- Ganti dengan token bot dari BotFather

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================
# DATA DASAR DARI GDD
# ==========================

# Lokasi utama
LOCATIONS = {
    "SELATPANJANG": {"name": "Selatpanjang", "min_level": 1, "type": "CITY"},
    "SIAK": {"name": "Siak", "min_level": 2, "type": "CITY"},
    "RENGAT": {"name": "Rengat", "min_level": 5, "type": "CITY"},
    "PEKANBARU": {"name": "Pekanbaru", "min_level": 8, "type": "CITY"},
    "KAMPAR": {"name": "Kampar", "min_level": 12, "type": "CITY"},  # final area
}

# Area hutan/dungeon terdekat per kota
NEAREST_DUNGEON = {
    "SELATPANJANG": "HUTAN_SELATPANJANG",
    "SIAK": "HUTAN_SIAK",
    "RENGAT": "HUTAN_RENGAT",
    "PEKANBARU": "HUTAN_PEKANBARU",
    "KAMPAR": "KAMPAR_LUAR",
}

# Monster definitions sederhana (subset dari GDD, bisa kamu tambah)
MONSTERS = {
    "SHADOW_SLIME": {
        "name": "Shadow Slime",
        "area": "HUTAN_SELATPANJANG",
        "level": 1,
        "hp": 20,
        "mp": 5,
        "atk": 4,
        "defense": 2,
        "mag": 1,
        "spd": 3,
        "luck": 1,
        "xp": 5,
        "gold": 3,
        "element": "GELAP",
    },
    "MIST_WOLF": {
        "name": "Mist Wolf",
        "area": "HUTAN_SELATPANJANG",
        "level": 2,
        "hp": 28,
        "mp": 5,
        "atk": 6,
        "defense": 3,
        "mag": 1,
        "spd": 5,
        "luck": 2,
        "xp": 8,
        "gold": 5,
        "element": "GELAP",
    },
    "SHADOW_BANDIT": {
        "name": "Shadow Bandit",
        "area": "HUTAN_SIAK",
        "level": 3,
        "hp": 35,
        "mp": 10,
        "atk": 8,
        "defense": 4,
        "mag": 2,
        "spd": 6,
        "luck": 2,
        "xp": 12,
        "gold": 10,
        "element": "GELAP",
    },
    "GATE_SPIRIT": {
        "name": "Gate Spirit",
        "area": "HUTAN_SIAK",
        "level": 4,
        "hp": 40,
        "mp": 20,
        "atk": 5,
        "defense": 5,
        "mag": 8,
        "spd": 4,
        "luck": 3,
        "xp": 16,
        "gold": 12,
        "element": "GELAP",
    },
    # Kamu bisa lanjutkan monster lainnya dari GDD...
}

# Skill dasar (subset, bisa kamu tambah)
SKILLS = {
    "SLASH": {
        "name": "Slash",
        "mp_cost": 0,
        "type": "PHYS",
        "power": 1.0,
        "target": "ENEMY_SINGLE",
        "description": "Serangan fisik standar Aruna.",
    },
    "LIGHT_BURST": {
        "name": "Light Burst",
        "mp_cost": 5,
        "type": "MAG",
        "power": 1.3,
        "element": "CAHAYA",
        "target": "ENEMY_SINGLE",
        "description": "Serangan cahaya ke satu musuh.",
    },
    "HEAL": {
        "name": "Heal",
        "mp_cost": 4,
        "type": "HEAL",
        "power": 0.3,
        "target": "ALLY_SINGLE",
        "description": "Memulihkan HP 30% dari MAG Umar ke 1 ally.",
    },
    "FIRE_BOLT": {
        "name": "Fire Bolt",
        "mp_cost": 4,
        "type": "MAG",
        "power": 1.2,
        "element": "API",
        "target": "ENEMY_SINGLE",
        "description": "Serangan api standar Reza.",
    },
}

# Base stats karakter sesuai GDD (disederhanakan)
CHAR_BASE = {
    "ARUNA": {
        "name": "Aruna",
        "level": 1,
        "hp": 40,
        "mp": 15,
        "atk": 8,
        "defense": 6,
        "mag": 5,
        "spd": 7,
        "luck": 5,
        "skills": ["SLASH"],
    },
    "UMAR": {
        "name": "Umar",
        "level": 1,
        "hp": 32,
        "mp": 25,
        "atk": 4,
        "defense": 4,
        "mag": 8,
        "spd": 6,
        "luck": 6,
        "skills": ["HEAL"],
    },
    "REZA": {
        "name": "Reza",
        "level": 1,
        "hp": 30,
        "mp": 30,
        "atk": 3,
        "defense": 4,
        "mag": 10,
        "spd": 5,
        "luck": 5,
        "skills": ["FIRE_BOLT"],
    },
}

# Scene/story ID:
# Kita fokus prolog & Chapter 1/awal Rengat.
# Kamu bisa menambah scene lain mengikuti format ini.
SCENE_DATA = {
    # PROLOG SELATPANJANG
    "CH0_S1": {
        "text": (
            "Selatpanjang, kota pelabuhan kecil di selatan.\n"
            "Di sebuah rumah kayu sederhana, seorang pemuda bernama Aruna "
            "memandang laut yang memerah oleh senja.\n\n"
            "Paman: \"Aruna, sudah waktunya makan. Jangan bengong terus di depan jendela.\"\n"
            "Aruna: \"Iya, Paman. Entah kenapa... hari ini terasa berbeda.\"\n"
        ),
        "choices": [("Lanjut", "CH0_S2")],
    },
    "CH0_S2": {
        "text": (
            "Malam turun. Aruna duduk di ranjang, memegang kalung bercahaya lembut.\n"
            "Paman: \"Suatu hari, kau akan mengerti kenapa kalung itu begitu penting. "
            "Tapi belum sekarang.\"\n"
            "Kalung berpendar lemah...\n"
        ),
        "choices": [("Ada apa dengan kalung ini?", "CH0_S3")],
    },
    "CH0_S3": {
        "text": (
            "Jeritan memecah malam. Tanah bergetar, udara penuh bau asap.\n"
            "Penduduk: \"MONSTER!! LARI!!\"\n"
            "Paman: \"Aruna! Ada monster menyerang desa!\"\n\n"
            "Kamu berlari keluar dan melihat bayangan besar di kejauhan: Shadow Fiend.\n\n"
            "Paman: \"Mulailah dari yang kecil, habisi minion-nya!\"\n\n"
            ">> Kamu akan menjalani battle tutorial melawan Shadow Slime.\n"
        ),
        "choices": [("Hadapi Shadow Slime", "BATTLE_TUTORIAL_1")],
    },
    "CH0_S4_POST_BATTLE": {
        "text": (
            "Setelah mengalahkan Shadow Slime, kamu kembali ke rumah.\n"
            "Rumah retak, dinding runtuh. Paman tergeletak, napasnya tersengal.\n"
            "Paman: \"Dengarkan aku... Pergilah ke barat, ke SIAK. "
            "Di sana, kebenaranmu menunggu... Kau keturunan Penjaga Cahaya...\"\n"
            "Kalung menyala terang.\n\n"
            "Paman: \"Teruslah berjalan... sampai Kampar... di sanalah takdirmu...\"\n"
            "Tangan Paman perlahan terkulai...\n"
        ),
        "choices": [("Pergi dari Selatpanjang...", "CH0_S5")],
    },
    "CH0_S5": {
        "text": (
            "Fajar menyingsing.\n"
            "Dengan tas kecil dan kalung bercahaya di dada, Aruna berdiri di tepi pelabuhan.\n"
            "Aruna: \"Paman... aku janji. Aku akan ke Siak. "
            "Aku akan cari kebenaran. Dan aku akan mengakhiri kegelapan ini.\"\n\n"
            ">> MAIN QUEST TERBUKA: Pergi ke SIAK.\n"
        ),
        "choices": [("Mulai perjalanan ke SIAK", "GO_TO_WORLD_MAP")],
    },

    # Contoh scene awal Siak: Umar
    "CH1_SIAK_ENTRY": {
        "text": (
            "Kamu tiba di gerbang Siak.\n"
            "Penjaga: \"Selamat datang di Kota Siak. Kau terlihat lelah, Anak Muda.\"\n"
            "Kota ini aman dari monster. Di sini kamu bisa istirahat, belanja, dan bekerja.\n"
        ),
        "choices": [("Masuk kota", "SIAK_CITY_MENU")],
    },
    "CH1_UMAR_CLINIC": {
        "text": (
            "Kamu memasuki klinik kecil.\n"
            "Seorang pemuda dengan pakaian healer menyambutmu.\n\n"
            "Umar: \"Selamat datang di klinik sederhana kami. Kau tampak babak belur. "
            "Monster di jalan, ya?\"\n"
            "Kalungmu tiba-tiba berpendar.\n"
            "Umar: \"Kalung itu... simbol Aruna Core. Ibuku sering bercerita tentang itu.\"\n"
        ),
        "choices": [
            ("Tanya lebih jauh tentang Aruna Core", "CH1_UMAR_CORE"),
            ("Diam saja dan mengangguk", "CH1_UMAR_CORE"),
        ],
    },
    "CH1_UMAR_CORE": {
        "text": (
            "Umar: \"Ibuku bilang, suatu hari akan datang seseorang membawa kalung itu, "
            "yang akan menentukan nasib Kampar.\"\n"
            "Aruna: \"Kampar... lagi-lagi nama itu.\"\n"
            "Umar: \"Kalau begitu, biarkan aku ikut. Ibu meninggalkan pesan: "
            "'Jika kau menemukannya, bantu dia apa pun yang terjadi.'\"\n\n"
            ">> Umar bergabung denganmu sebagai healer!\n"
        ),
        "choices": [("Lanjut", "SIAK_CITY_MENU_AFTER_UMAR")],
    },
    # dsb. Kamu dapat menambahkan semua scene dari GDD mengikuti pola ini.
}

WORLD_MAP_ASCII = """
              [ HUTAN KAMPAR ]
                    ||
        +-----------||-----------+
        |                       |
    [KAMPAR] - - - - - - - - [KASTIL FEBRI]

              ^
              |
        [PEKANBARU]
              ^
              |
       [HUTAN PEKANBARU]
              ^
              |
           [RENGAT]
              ^
              |
       [HUTAN RENGAT]
              ^
              |
            [SIAK]
              ^
              |
    [HUTAN SELATPANJANG]
              ^
              |
        [SELATPANJANG]
"""

# ==========================
# STRUKTUR STATE GAME
# ==========================

@dataclass
class CharacterState:
    id: str
    name: str
    level: int
    hp: int
    max_hp: int
    mp: int
    max_mp: int
    atk: int
    defense: int
    mag: int
    spd: int
    luck: int
    skills: List[str] = field(default_factory=list)


@dataclass
class GameState:
    user_id: int
    scene_id: str = "CH0_S1"
    location: str = "SELATPANJANG"
    in_battle: bool = False
    battle_enemies: List[Dict[str, Any]] = field(default_factory=list)
    battle_turn: str = "PLAYER"
    gold: int = 0
    main_progress: str = "PROLOG"
    party: Dict[str, CharacterState] = field(default_factory=dict)
    party_order: List[str] = field(default_factory=list)
    inventory: Dict[str, int] = field(default_factory=dict)
    xp_pool: Dict[str, int] = field(default_factory=dict)
    flags: Dict[str, Any] = field(default_factory=dict)

    def ensure_aruna(self):
        if "ARUNA" not in self.party:
            base = CHAR_BASE["ARUNA"]
            self.party["ARUNA"] = CharacterState(
                id="ARUNA",
                name=base["name"],
                level=base["level"],
                hp=base["hp"],
                max_hp=base["hp"],
                mp=base["mp"],
                max_mp=base["mp"],
                atk=base["atk"],
                defense=base["defense"],
                mag=base["mag"],
                spd=base["spd"],
                luck=base["luck"],
                skills=list(base["skills"]),
            )
            self.party_order.append("ARUNA")
            self.xp_pool["ARUNA"] = 0

    def add_umar(self):
        if "UMAR" not in self.party:
            base = CHAR_BASE["UMAR"]
            self.party["UMAR"] = CharacterState(
                id="UMAR",
                name=base["name"],
                level=base["level"],
                hp=base["hp"],
                max_hp=base["hp"],
                mp=base["mp"],
                max_mp=base["mp"],
                atk=base["atk"],
                defense=base["defense"],
                mag=base["mag"],
                spd=base["spd"],
                luck=base["luck"],
                skills=list(base["skills"]),
            )
            self.party_order.append("UMAR")
            self.xp_pool["UMAR"] = 0
            self.flags["HAS_UMAR"] = True

    def add_reza(self):
        if "REZA" not in self.party:
            base = CHAR_BASE["REZA"]
            self.party["REZA"] = CharacterState(
                id="REZA",
                name=base["name"],
                level=base["level"],
                hp=base["hp"],
                max_hp=base["hp"],
                mp=base["mp"],
                max_mp=base["mp"],
                atk=base["atk"],
                defense=base["defense"],
                mag=base["mag"],
                spd=base["spd"],
                luck=base["luck"],
                skills=list(base["skills"]),
            )
            self.party_order.append("REZA")
            self.xp_pool["REZA"] = 0
            self.flags["HAS_REZA"] = True


# Storage in-memory
USER_STATES: Dict[int, GameState] = {}


def get_game_state(user_id: int) -> GameState:
    state = USER_STATES.get(user_id)
    if not state:
        state = GameState(user_id=user_id)
        state.ensure_aruna()
        USER_STATES[user_id] = state
    return state


# ==========================
# HELPER UI
# ==========================

def make_keyboard(choices: List[tuple]) -> InlineKeyboardMarkup:
    """
    choices: list of (label, callback_data)
    """
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=data)] for (label, data) in choices
    ]
    return InlineKeyboardMarkup(buttons)


# ==========================
# BATTLE LOGIC SEDERHANA
# ==========================

def pick_random_monster_for_area(area: str) -> Dict[str, Any]:
    pool = [m for m in MONSTERS.values() if m["area"] == area]
    if not pool:
        pool = [MONSTERS["SHADOW_SLIME"]]  # fallback
    base = random.choice(pool)
    # copy agar tidak mengubah base
    return {
        "name": base["name"],
        "hp": base["hp"],
        "max_hp": base["hp"],
        "mp": base["mp"],
        "atk": base["atk"],
        "defense": base["defense"],
        "mag": base["mag"],
        "spd": base["spd"],
        "luck": base["luck"],
        "xp": base["xp"],
        "gold": base["gold"],
        "element": base.get("element", "NETRAL"),
        "id": base["name"].upper().replace(" ", "_"),
    }


def calc_physical_damage(attacker: CharacterState, target_def: int) -> int:
    base = attacker.atk - target_def // 2
    if base < 1:
        base = 1
    # variasi kecil
    base = int(base * random.uniform(0.9, 1.1))
    return max(1, base)


def calc_magic_damage(attacker: CharacterState, target_def: int, power: float) -> int:
    base = int((attacker.mag - target_def / 3) * power)
    if base < 1:
        base = 1
    base = int(base * random.uniform(0.9, 1.1))
    return max(1, base)


def calc_heal_amount(caster: CharacterState, power: float) -> int:
    base = int(caster.mag * power)
    if base < 1:
        base = 1
    return base


async def start_random_battle(update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState):
    """
    Mulai battle random di area dungeon berdasarkan lokasi sekarang.
    """
    area = NEAREST_DUNGEON.get(state.location, "HUTAN_SELATPANJANG")
    enemy = pick_random_monster_for_area(area)
    state.in_battle = True
    state.battle_enemies = [enemy]
    state.battle_turn = "PLAYER"
    await send_battle_state(update, context, state, intro=True)


def battle_status_text(state: GameState) -> str:
    lines = ["=== BATTLE ==="]
    lines.append("Party:")
    for cid in state.party_order:
        c = state.party[cid]
        lines.append(f"- {c.name} Lv{c.level} HP {c.hp}/{c.max_hp} MP {c.mp}/{c.max_mp}")
    lines.append("")
    lines.append("Musuh:")
    for e in state.battle_enemies:
        lines.append(f"- {e['name']} HP {e['hp']}/{e['max_hp']}")
    return "\n".join(lines)


async def send_battle_state(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: GameState,
    intro: bool = False,
    extra_text: str = "",
):
    text = ""
    if intro:
        text += f"Kamu bertemu dengan {state.battle_enemies[0]['name']}!\n\n"
    text += battle_status_text(state)
    if extra_text:
        text = extra_text + "\n\n" + text

    keyboard = make_keyboard(
        [
            ("⚔ Serang", "BATTLE_ATTACK"),
            ("✨ Skill", "BATTLE_SKILL_MENU"),
            ("🎒 Item", "BATTLE_ITEM"),
            ("🛡 Bertahan", "BATTLE_DEFEND"),
            ("🏃 Kabur", "BATTLE_RUN"),
        ]
    )

    query = update.callback_query
    if query:
        await query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text=text, reply_markup=keyboard)


async def process_battle_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState, action: str
):
    """
    action: BATTLE_ATTACK, BATTLE_DEFEND, BATTLE_RUN, etc.
    Untuk sekarang: serangan simple Aruna saja (bisa dikembangkan untuk semua party).
    """
    aruna = state.party["ARUNA"]
    enemy = state.battle_enemies[0]

    log = []

    if action == "BATTLE_ATTACK":
        dmg = calc_physical_damage(aruna, enemy["defense"])
        enemy["hp"] -= dmg
        log.append(f"Aruna menyerang {enemy['name']} dan memberikan {dmg} damage!")

    elif action == "BATTLE_DEFEND":
        # defensif sederhana: kurang damage musuh nantinya
        state.flags["LAST_DEFEND"] = True
        log.append("Aruna bersiap bertahan, mengurangi damage yang diterima di ronde ini.")

    elif action == "BATTLE_RUN":
        chance = 0.5 + aruna.luck * 0.01
        if random.random() < chance:
            log.append("Kamu berhasil kabur dari pertarungan.")
            state.in_battle = False
            state.battle_enemies = []
            state.battle_turn = "PLAYER"
            await end_battle_and_return(update, context, state, log_text="\n".join(log))
            return
        else:
            log.append("Kamu gagal kabur!")

    elif action == "BATTLE_ITEM":
        log.append("Sistem item belum diimplementasikan penuh. (TODO)")

    elif action == "BATTLE_SKILL_MENU":
        # Tampilkan skill Aruna saja dulu
        skills = state.party["ARUNA"].skills
        choices = [(SKILLS[s]["name"], f"USE_SKILL|ARUNA|{s}") for s in skills]
        keyboard = make_keyboard(choices + [("Kembali", "BATTLE_BACK")])
        text = battle_status_text(state) + "\n\nPilih skill Aruna:"
        query = update.callback_query
        if query:
            await query.edit_message_text(text=text, reply_markup=keyboard)
        return

    # Cek jika musuh mati
    if enemy["hp"] <= 0:
        log.append(f"{enemy['name']} kalah!")
        xp = enemy["xp"]
        gold = enemy["gold"]
        state.gold += gold
        for cid in state.party_order:
            state.xp_pool[cid] += xp
        state.in_battle = False
        state.battle_enemies = []
        await end_battle_and_return(
            update,
            context,
            state,
            log_text="\n".join(log)
            + f"\n\nKamu mendapatkan {xp} XP dan {gold} Gold.",
        )
        return

    # GILIRAN MUSUH
    dmg_to_player = max(1, int(enemy["atk"] * random.uniform(0.8, 1.1)))
    if state.flags.get("LAST_DEFEND"):
        dmg_to_player = max(1, dmg_to_player // 2)
        state.flags["LAST_DEFEND"] = False

    aruna.hp -= dmg_to_player
    log.append(f"{enemy['name']} menyerang Aruna dan memberikan {dmg_to_player} damage!")

    if aruna.hp <= 0:
        # GAME OVER lokal (untuk sekarang, tidak langsung BAD END global)
        aruna.hp = 0
        log.append("Aruna tumbang! Kamu kalah dalam pertarungan ini...")
        state.in_battle = False
        state.battle_enemies = []
        # Kembalikan Aruna dengan sedikit HP untuk tidak mem-softlock
        aruna.hp = max(1, aruna.max_hp // 3)
        await end_battle_and_return(update, context, state, log_text="\n".join(log))
        return

    # Kirim status again
    await send_battle_state(update, context, state, intro=False, extra_text="\n".join(log))


async def process_use_skill(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState, user: str, skill_id: str
):
    c = state.party[user]
    skill = SKILLS.get(skill_id)
    if not skill:
        return

    log = []

    if c.mp < skill["mp_cost"]:
        log.append(f"{c.name} tidak punya MP yang cukup untuk menggunakan {skill['name']}!")
        await send_battle_state(update, context, state, intro=False, extra_text="\n".join(log))
        return

    c.mp -= skill["mp_cost"]
    enemy = state.battle_enemies[0]

    if skill["type"] == "PHYS":
        dmg = calc_physical_damage(c, enemy["defense"])
        enemy["hp"] -= dmg
        log.append(f"{c.name} menggunakan {skill['name']}! {enemy['name']} menerima {dmg} damage.")
    elif skill["type"] == "MAG":
        dmg = calc_magic_damage(c, enemy["defense"], skill["power"])
        enemy["hp"] -= dmg
        log.append(f"{c.name} melempar {skill['name']}! {enemy['name']} menerima {dmg} damage.")
    elif skill["type"] == "HEAL":
        heal_amount = calc_heal_amount(c, skill["power"])
        target = state.party["ARUNA"]  # untuk sekarang heal Aruna
        before = target.hp
        target.hp = min(target.max_hp, target.hp + heal_amount)
        healed = target.hp - before
        log.append(
            f"{c.name} menggunakan {skill['name']} dan menyembuhkan {target.name} sebanyak {healed} HP."
        )

    # cek musuh mati
    enemy = state.battle_enemies[0]
    if enemy["hp"] <= 0:
        log.append(f"{enemy['name']} kalah!")
        xp = enemy["xp"]
        gold = enemy["gold"]
        state.gold += gold
        for cid in state.party_order:
            state.xp_pool[cid] += xp
        state.in_battle = False
        state.battle_enemies = []
        await end_battle_and_return(
            update,
            context,
            state,
            log_text="\n".join(log)
            + f"\n\nKamu mendapatkan {xp} XP dan {gold} Gold.",
        )
        return

    # giliran musuh
    enemy_attack = max(1, int(enemy["atk"] * random.uniform(0.8, 1.1)))
    target = state.party["ARUNA"]
    target.hp -= enemy_attack
    log.append(f"{enemy['name']} menyerang {target.name} dan memberikan {enemy_attack} damage!")

    if target.hp <= 0:
        log.append(f"{target.name} tumbang! Kamu kalah dalam pertarungan ini...")
        target.hp = max(1, target.max_hp // 3)
        state.in_battle = False
        state.battle_enemies = []
        await end_battle_and_return(update, context, state, log_text="\n".join(log))
        return

    await send_battle_state(update, context, state, intro=False, extra_text="\n".join(log))


async def end_battle_and_return(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: GameState,
    log_text: str = "",
):
    """
    Setelah battle selesai, balik ke menu yang sesuai dengan lokasi (hutan/kota).
    Untuk sekarang: jika battle random, balik ke 'DUNGEON_MENU', kalau battle story, balik ke scene.
    """
    # Deteksi: kalau scene main prolog battle tutorial
    if state.scene_id == "CH0_S3" or state.scene_id.startswith("BATTLE_TUTORIAL"):
        state.scene_id = "CH0_S4_POST_BATTLE"
        await send_scene(update, context, state, extra_text=log_text)
        return

    # Battle random biasa
    text = log_text + "\n\nKamu kembali ke area hutan."
    keyboard = make_keyboard(
        [
            ("Cari monster lagi", "DUNGEON_BATTLE_AGAIN"),
            ("Kembali ke kota", "RETURN_TO_CITY"),
        ]
    )
    query = update.callback_query
    if query:
        await query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text=text, reply_markup=keyboard)


# ==========================
# STORY / SCENE HANDLER
# ==========================

async def send_scene(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: GameState,
    extra_text: str = "",
):
    data = SCENE_DATA.get(state.scene_id)
    if not data:
        # fallback
        text = "Scene belum diimplementasikan. (TODO) \nID: " + state.scene_id
        keyboard = make_keyboard([("Kembali ke map", "GO_TO_WORLD_MAP")])
        query = update.callback_query
        if query:
            await query.edit_message_text(text=text, reply_markup=keyboard)
        else:
            await update.message.reply_text(text=text, reply_markup=keyboard)
        return

    text = data["text"]
    if extra_text:
        text = extra_text + "\n\n" + text

    keyboard = make_keyboard(data["choices"])
    query = update.callback_query
    if query:
        await query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text=text, reply_markup=keyboard)


async def handle_scene_choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: GameState,
    choice_data: str,
):
    # beberapa keyword khusus
    if choice_data == "BATTLE_TUTORIAL_1":
        state.scene_id = "CH0_S3"
        await start_random_battle(update, context, state)
        return

    if choice_data == "GO_TO_WORLD_MAP":
        state.main_progress = "WORLD"
        await send_world_map(update, context, state)
        return

    if choice_data == "SIAK_CITY_MENU":
        state.location = "SIAK"
        await send_city_menu(update, context, state)
        return

    if choice_data == "SIAK_CITY_MENU_AFTER_UMAR":
        state.location = "SIAK"
        state.add_umar()
        await send_city_menu(update, context, state, extra_text="Umar kini menjadi anggota party.")
        return

    # Default: ganti scene_id dan tampilkan scene
    state.scene_id = choice_data
    await send_scene(update, context, state)


# ==========================
# WORLD MAP & CITY MENU
# ==========================

async def send_world_map(update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState):
    text = "WORLD MAP\n" + WORLD_MAP_ASCII + "\n\n"
    text += "Lokasi kamu sekarang: " + LOCATIONS[state.location]["name"] + "\n"
    text += "Pilih tujuan:"

    # buat tombol kota + dungeon
    choices = []
    for loc_id, info in LOCATIONS.items():
        if loc_id == state.location:
            continue
        label = f"{info['name']} (Lv {info['min_level']}+)"
        choices.append((label, f"GOTO_CITY|{loc_id}"))

    # dungeon terdekat dari lokasi sekarang
    choices.append(("Pergi ke hutan terdekat (grinding)", "ENTER_DUNGEON"))

    keyboard = make_keyboard(choices)
    query = update.callback_query
    if query:
        await query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text=text, reply_markup=keyboard)


async def send_city_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: GameState,
    extra_text: str = "",
):
    loc = LOCATIONS[state.location]
    text = f"KOTA: {loc['name']}\n"
    if extra_text:
        text += extra_text + "\n\n"
    text += "Apa yang ingin kamu lakukan?"

    choices = [
        ("Lihat status party", "MENU_STATUS"),
        ("Pergi ke toko (shop)", "MENU_SHOP"),
        ("Bekerja (job)", "MENU_JOB"),
        ("Ke penginapan (heal)", "MENU_INN"),
        ("Pergi ke klinik (Siak saja)", "MENU_CLINIC"),
        ("Kembali ke world map", "GO_TO_WORLD_MAP"),
    ]

    # klinik hanya untuk Siak
    if state.location != "SIAK":
        # hapus klinik
        choices = [c for c in choices if c[1] != "MENU_CLINIC"]

    keyboard = make_keyboard(choices)
    query = update.callback_query
    if query:
        await query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text=text, reply_markup=keyboard)


# ==========================
# HANDLER KOMANDO
# ==========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = get_game_state(user_id)
    state.scene_id = "CH0_S1"
    state.location = "SELATPANJANG"
    state.main_progress = "PROLOG"
    state.ensure_aruna()
    await send_scene(update, context, state)


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = get_game_state(user_id)
    lines = ["=== STATUS PARTY ==="]
    for cid in state.party_order:
        c = state.party[cid]
        lines.append(
            f"{c.name} Lv {c.level} | HP {c.hp}/{c.max_hp} | MP {c.mp}/{c.max_mp} | ATK {c.atk} DEF {c.defense} MAG {c.mag}"
        )
    lines.append(f"\nGold: {state.gold}")
    lines.append(f"Lokasi: {LOCATIONS[state.location]['name']}")
    await update.message.reply_text("\n".join(lines))


async def map_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = get_game_state(user_id)
    await send_world_map(update, context, state)


# ==========================
# CALLBACK QUERY HANDLER
# ==========================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = get_game_state(user_id)
    data = query.data

    # BATTLE-related
    if data.startswith("BATTLE_"):
        if not state.in_battle:
            await query.edit_message_text("Kamu tidak sedang dalam battle.")
            return
        if data == "BATTLE_BACK":
            await send_battle_state(update, context, state)
            return
        await process_battle_action(update, context, state, data)
        return

    if data.startswith("USE_SKILL|"):
        # format: USE_SKILL|CHAR_ID|SKILL_ID
        _, char_id, skill_id = data.split("|")
        if not state.in_battle:
            await query.edit_message_text("Kamu tidak sedang dalam battle.")
            return
        await process_use_skill(update, context, state, char_id, skill_id)
        return

    if data == "DUNGEON_BATTLE_AGAIN":
        await start_random_battle(update, context, state)
        return

    if data == "RETURN_TO_CITY":
        await send_city_menu(update, context, state)
        return

    # WORLD MAP / TRAVEL
    if data.startswith("GOTO_CITY|"):
        _, loc_id = data.split("|")
        loc_info = LOCATIONS[loc_id]
        # cek level Aruna
        aruna = state.party["ARUNA"]
        if aruna.level < loc_info["min_level"]:
            text = (
                f"Level kamu ({aruna.level}) belum cukup untuk masuk ke {loc_info['name']} "
                f"(butuh Lv {loc_info['min_level']})."
            )
            keyboard = make_keyboard([("Kembali ke map", "GO_TO_WORLD_MAP")])
            await query.edit_message_text(text=text, reply_markup=keyboard)
            return
        # kalau cukup
        state.location = loc_id
        if loc_id == "SIAK" and not state.flags.get("VISITED_SIAK"):
            state.flags["VISITED_SIAK"] = True
            state.scene_id = "CH1_SIAK_ENTRY"
            await send_scene(update, context, state)
        else:
            await send_city_menu(update, context, state)
        return

    if data == "ENTER_DUNGEON":
        # masuk hutan terdekat
        area = NEAREST_DUNGEON.get(state.location, "HUTAN_SELATPANJANG")
        text = f"Kamu memasuki {area}. Monster berkeliaran di sini."
        keyboard = make_keyboard(
            [("Cari monster", "DUNGEON_BATTLE_AGAIN"), ("Kembali ke kota", "RETURN_TO_CITY")]
        )
        await query.edit_message_text(text=text, reply_markup=keyboard)
        return

    # MENU KOTA
    if data == "MENU_STATUS":
        # tampilkan status via edit message
        lines = ["=== STATUS PARTY ==="]
        for cid in state.party_order:
            c = state.party[cid]
            lines.append(
                f"{c.name} Lv {c.level} | HP {c.hp}/{c.max_hp} | MP {c.mp}/{c.max_mp}"
            )
        lines.append(f"\nGold: {state.gold}")
        lines.append(f"Lokasi: {LOCATIONS[state.location]['name']}")
        text = "\n".join(lines)
        keyboard = make_keyboard(
            [
                ("Kembali ke kota", "BACK_CITY_MENU"),
            ]
        )
        await query.edit_message_text(text=text, reply_markup=keyboard)
        return

    if data == "BACK_CITY_MENU":
        await send_city_menu(update, context, state)
        return

    if data == "MENU_SHOP":
        text = (
            "SHOP (sederhana) - Contoh:\n"
            "Saat ini sistem shop full belum diimplementasikan.\n"
            "Kamu bisa tambahkan logika beli/jual item di sini.\n"
        )
        keyboard = make_keyboard([("Kembali ke kota", "BACK_CITY_MENU")])
        await query.edit_message_text(text=text, reply_markup=keyboard)
        return

    if data == "MENU_JOB":
        text = (
            "SISTEM KERJA (JOB)\n"
            "Kamu bekerja sehari dan mendapatkan sejumlah Gold.\n"
        )
        gained = random.randint(10, 30)
        state.gold += gained
        text += f"Kamu bekerja keras dan mendapatkan {gained} Gold.\n"
        keyboard = make_keyboard([("Kembali ke kota", "BACK_CITY_MENU")])
        await query.edit_message_text(text=text, reply_markup=keyboard)
        return

    if data == "MENU_INN":
        # heal full party
        for cid in state.party_order:
            c = state.party[cid]
            c.hp = c.max_hp
            c.mp = c.max_mp
        text = "Kamu beristirahat di penginapan. HP & MP seluruh party pulih."
        keyboard = make_keyboard([("Kembali ke kota", "BACK_CITY_MENU")])
        await query.edit_message_text(text=text, reply_markup=keyboard)
        return

    if data == "MENU_CLINIC":
        # trigger klinik Umar di Siak
        if state.location != "SIAK":
            await query.edit_message_text(
                "Klinik hanya ada di Siak.", reply_markup=make_keyboard([("Kembali", "BACK_CITY_MENU")])
            )
            return
        # jika Umar belum join, jalankan scene Umar
        if not state.flags.get("HAS_UMAR"):
            state.scene_id = "CH1_UMAR_CLINIC"
            await send_scene(update, context, state)
        else:
            text = "Umar: \"Jaga dirimu baik-baik, Aruna. Aku di sini kalau kau butuh bantuan.\"\n"
            keyboard = make_keyboard([("Kembali ke kota", "BACK_CITY_MENU")])
            await query.edit_message_text(text=text, reply_markup=keyboard)
        return

    if data == "GO_TO_WORLD_MAP":
        await send_world_map(update, context, state)
        return

    # SCENE / STORY CHOICE
    await handle_scene_choice(update, context, state, data)


# ==========================
# MAIN
# ==========================

def main():
    application = ApplicationBuilder().token(TOKEN_BOT).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(CommandHandler("map", map_cmd))

    application.add_handler(CallbackQueryHandler(button))

    logger.info("Bot Legends of Aruna berjalan...")
    application.run_polling()


if __name__ == "__main__":
    main()
