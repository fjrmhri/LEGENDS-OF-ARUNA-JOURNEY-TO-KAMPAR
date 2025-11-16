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

# Lokasi utama dan fitur kotanya
LOCATIONS = {
    "SELATPANJANG": {
        "name": "Selatpanjang",
        "min_level": 1,
        "type": "CITY",
        "has_shop": False,
        "has_job": False,
        "has_inn": False,
        "has_clinic": False,
    },
    "SIAK": {
        "name": "Siak",
        "min_level": 2,
        "type": "CITY",
        "has_shop": True,
        "has_job": True,
        "has_inn": True,
        "has_clinic": True,
    },
    "RENGAT": {
        "name": "Rengat",
        "min_level": 5,
        "type": "CITY",
        "has_shop": True,
        "has_job": True,
        "has_inn": True,
        "has_clinic": False,
    },
    "PEKANBARU": {
        "name": "Pekanbaru",
        "min_level": 8,
        "type": "CITY",
        "has_shop": True,
        "has_job": True,
        "has_inn": True,
        "has_clinic": False,
    },
    "KAMPAR": {
        "name": "Kampar",
        "min_level": 12,
        "type": "CURSED",
        "has_shop": False,
        "has_job": False,
        "has_inn": False,
        "has_clinic": False,
    },
}

CITY_FEATURES = {
    "SELATPANJANG": {
        "description": "Kota pelabuhan kecil dan tenang. Di sinilah petualangan Aruna dimulai.",
        "shop_items": [],
        "inn_cost": 0,
        "jobs": {},
    },
    "SIAK": {
        "description": "Kota sungai damai dengan klinik Safiya dan tempat kerja sederhana.",
        "shop_items": [
            "Pisau Sungai (+ATK kecil)",
            "Jubah Healer (+DEF, bonus pada Umar)",
            "Potion Kecil (heal 50 HP)",
        ],
        "inn_cost": 20,
        "jobs": {
            "KURIR_OBAT": {
                "name": "Kurir Obat",
                "description": "Mengantar ramuan ke dermaga.",
                "payout": (15, 30),
                "fail_chance": 0.05,
            },
            "PENJAGA_GUDANG": {
                "name": "Penjaga Gudang",
                "description": "Menjaga gudang bahan medis sepanjang malam.",
                "payout": (25, 45),
                "fail_chance": 0.15,
            },
        },
    },
    "RENGAT": {
        "description": "Kota para penyihir dengan menara-menara riset dan hutan magis.",
        "shop_items": [
            "Staf Rimba (+MAG)",
            "Jubah Rune (+DEF/MAG)",
            "Ether Kecil (restore 15 MP)",
        ],
        "inn_cost": 30,
        "jobs": {
            "ASISTEN_RISET": {
                "name": "Asisten Riset",
                "description": "Membantu laboratorium Reza mengumpulkan bahan sihir.",
                "payout": (35, 60),
                "fail_chance": 0.1,
            },
            "EKSPEDISI_HUTAN": {
                "name": "Ekspedisi Hutan",
                "description": "Mengawal murid muda memasuki hutan magis.",
                "payout": (50, 80),
                "fail_chance": 0.2,
            },
        },
    },
    "PEKANBARU": {
        "description": "Metropolis suram, tempat terakhir untuk melengkapi persiapan sebelum Kampar.",
        "shop_items": [
            "Pedang Kota Besar (+ATK menengah)",
            "Armor Baja Riau (+DEF tinggi)",
            "Light Charm (resist Gelap +10%)",
            "Potion Sedang (heal 120 HP)",
        ],
        "inn_cost": 45,
        "jobs": {
            "PENGAWAL_KARAVAN": {
                "name": "Pengawal Karavan",
                "description": "Mengawal saudagar melewati jalanan berkabut.",
                "payout": (70, 110),
                "fail_chance": 0.2,
            },
            "PEMBURU_RUMOR": {
                "name": "Pemburu Rumor",
                "description": "Menyelidiki rumor Abyss di gang-gang gelap.",
                "payout": (60, 90),
                "fail_chance": 0.25,
            },
        },
    },
    "KAMPAR": {
        "description": "Kota terkutuk tanpa NPC. Semua jalan menuju kastil Febri.",
        "shop_items": [],
        "inn_cost": 0,
        "jobs": {},
    },
}

# Area hutan/dungeon terdekat per kota
NEAREST_DUNGEON = {
    "SELATPANJANG": "HUTAN_SELATPANJANG",
    "SIAK": "HUTAN_SIAK",
    "RENGAT": "HUTAN_RENGAT",
    "PEKANBARU": "HUTAN_PEKANBARU",
    "KAMPAR": "KAMPAR_LUAR",
}

# Monster definitions lengkap sesuai GDD
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
    "CORRUPTED_TREANT": {
        "name": "Corrupted Treant",
        "area": "HUTAN_RENGAT",
        "level": 5,
        "hp": 60,
        "mp": 10,
        "atk": 9,
        "defense": 8,
        "mag": 4,
        "spd": 3,
        "luck": 2,
        "xp": 20,
        "gold": 15,
        "element": "ALAM",
    },
    "FOREST_WISP": {
        "name": "Forest Wisp",
        "area": "HUTAN_RENGAT",
        "level": 6,
        "hp": 40,
        "mp": 30,
        "atk": 4,
        "defense": 3,
        "mag": 10,
        "spd": 7,
        "luck": 4,
        "xp": 22,
        "gold": 18,
        "element": "CAHAYA",
    },
    "CORRUPTED_FOREST_GOLEM": {
        "name": "Corrupted Forest Golem",
        "area": "HUTAN_RENGAT",
        "level": 8,
        "hp": 150,
        "mp": 30,
        "atk": 18,
        "defense": 15,
        "mag": 8,
        "spd": 4,
        "luck": 3,
        "xp": 80,
        "gold": 50,
        "element": "ALAM",
    },
    "PHANTOM_MERCHANT": {
        "name": "Phantom Merchant",
        "area": "HUTAN_PEKANBARU",
        "level": 9,
        "hp": 70,
        "mp": 25,
        "atk": 10,
        "defense": 8,
        "mag": 10,
        "spd": 6,
        "luck": 5,
        "xp": 30,
        "gold": 25,
        "element": "GELAP",
    },
    "CURSED_MILITIA": {
        "name": "Cursed Militia",
        "area": "HUTAN_PEKANBARU",
        "level": 10,
        "hp": 80,
        "mp": 10,
        "atk": 14,
        "defense": 12,
        "mag": 4,
        "spd": 5,
        "luck": 3,
        "xp": 35,
        "gold": 28,
        "element": "GELAP",
    },
    "ABYSS_HOUND": {
        "name": "Abyss Hound",
        "area": "KAMPAR_LUAR",
        "level": 13,
        "hp": 95,
        "mp": 20,
        "atk": 18,
        "defense": 10,
        "mag": 6,
        "spd": 12,
        "luck": 4,
        "xp": 45,
        "gold": 40,
        "element": "GELAP",
    },
    "VOID_KNIGHT": {
        "name": "Void Knight",
        "area": "KAMPAR_LUAR",
        "level": 15,
        "hp": 120,
        "mp": 30,
        "atk": 20,
        "defense": 16,
        "mag": 10,
        "spd": 8,
        "luck": 5,
        "xp": 60,
        "gold": 50,
        "element": "GELAP",
    },
    "HOUND_OF_VOID": {
        "name": "Hound of Void",
        "area": "KASTIL_FEBRI",
        "level": 17,
        "hp": 220,
        "mp": 50,
        "atk": 26,
        "defense": 16,
        "mag": 16,
        "spd": 14,
        "luck": 5,
        "xp": 120,
        "gold": 0,
        "element": "GELAP",
    },
    "VOID_SENTINEL": {
        "name": "Void Sentinel",
        "area": "KASTIL_FEBRI",
        "level": 18,
        "hp": 260,
        "mp": 40,
        "atk": 28,
        "defense": 20,
        "mag": 18,
        "spd": 10,
        "luck": 6,
        "xp": 150,
        "gold": 0,
        "element": "GELAP",
    },
    "FEBRI_LORD": {
        "name": "Febri, Lord of Abyss",
        "area": "KASTIL_FEBRI",
        "level": 20,
        "hp": 400,
        "mp": 120,
        "atk": 32,
        "defense": 22,
        "mag": 32,
        "spd": 16,
        "luck": 8,
        "xp": 999,
        "gold": 0,
        "element": "GELAP",
    },
}

# Skill dasar lengkap
SKILLS = {
    "SLASH": {
        "name": "Slash",
        "mp_cost": 0,
        "type": "PHYS",
        "power": 1.0,
        "element": "NETRAL",
        "description": "Serangan fisik standar Aruna.",
    },
    "LIGHT_BURST": {
        "name": "Light Burst",
        "mp_cost": 5,
        "type": "MAG",
        "power": 1.3,
        "element": "CAHAYA",
        "description": "Serangan cahaya fokus ke satu musuh.",
    },
    "RADIANT_SLASH": {
        "name": "Radiant Slash",
        "mp_cost": 8,
        "type": "PHYS",
        "power": 1.3,
        "element": "CAHAYA",
        "description": "Tebasan fisik bercahaya yang melemahkan musuh.",
    },
    "GUARDIAN_OATH": {
        "name": "Guardian's Oath",
        "mp_cost": 10,
        "type": "BUFF_DEF_SELF",
        "duration": 3,
        "description": "Aruna memperkuat pertahanan dan resistensi kegelapan sementara.",
    },
    "LIGHT_WAVE": {
        "name": "Light Wave",
        "mp_cost": 14,
        "type": "MAG",
        "power": 0.9,
        "element": "CAHAYA",
        "description": "Gelombang cahaya yang menghantam semua musuh.",
    },
    "ARUNA_CORE_AWAKENING": {
        "name": "Aruna Core Awakening",
        "mp_cost": 0,
        "type": "LIMIT_HEAL",
        "description": "Skill cerita: menyembuhkan dan memberkati seluruh party sekali per battle.",
    },
    "HEAL": {
        "name": "Heal",
        "mp_cost": 4,
        "type": "HEAL_SINGLE",
        "power": 0.3,
        "description": "Memulihkan HP seorang ally.",
    },
    "SMALL_BARRIER": {
        "name": "Small Barrier",
        "mp_cost": 5,
        "type": "BUFF_DEF_SINGLE",
        "description": "Meningkatkan DEF satu ally untuk beberapa turn.",
    },
    "GROUP_HEAL": {
        "name": "Group Heal",
        "mp_cost": 10,
        "type": "HEAL_ALL",
        "power": 0.25,
        "description": "Heal kecil ke seluruh party.",
    },
    "PURIFY": {
        "name": "Purify",
        "mp_cost": 8,
        "type": "CLEANSE",
        "description": "Menghilangkan 1 debuff dari ally.",
    },
    "REVIVE": {
        "name": "Revive",
        "mp_cost": 18,
        "type": "REVIVE",
        "description": "Menghidupkan ally yang tumbang.",
    },
    "SAFIYAS_GRACE": {
        "name": "Safiya's Grace",
        "mp_cost": 20,
        "type": "HEAL_ALL",
        "power": 0.5,
        "description": "Ultimate Umar: heal besar + hilangkan debuff utama.",
    },
    "FIRE_BOLT": {
        "name": "Fire Bolt",
        "mp_cost": 4,
        "type": "MAG",
        "power": 1.2,
        "element": "API",
        "description": "Serangan api standar Reza.",
    },
    "MANA_SHIELD": {
        "name": "Mana Shield",
        "mp_cost": 6,
        "type": "BUFF_SPECIAL",
        "description": "Mengubah damage fisik menjadi konsumsi MP sementara.",
    },
    "CHAIN_LIGHTNING": {
        "name": "Chain Lightning",
        "mp_cost": 10,
        "type": "MAG",
        "power": 0.8,
        "element": "PETIR",
        "description": "Serangan AoE petir dengan peluang stun.",
    },
    "ARCANE_FOCUS": {
        "name": "Arcane Focus",
        "mp_cost": 8,
        "type": "BUFF_SELF",
        "description": "Meningkatkan MAG Reza namun menurunkan SPD sementara.",
    },
    "ABYSS_SEAL": {
        "name": "Abyss Seal",
        "mp_cost": 15,
        "type": "DEBUFF_ENEMY",
        "description": "Menurunkan MAG dan SPD musuh.",
    },
    "MASTERS_LEGACY": {
        "name": "Master's Legacy",
        "mp_cost": 20,
        "type": "BUFF_TEAM",
        "description": "Ultimate Reza: buff ATK/MAG/DEF dan resist gelap party.",
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

CHAR_GROWTH = {
    "ARUNA": {"hp": 8, "mp": 3, "atk": 3, "defense": 2, "mag": 2, "spd": 2, "luck": 1},
    "UMAR": {"hp": 6, "mp": 6, "atk": 1, "defense": 2, "mag": 3, "spd": 2, "luck": 2},
    "REZA": {"hp": 5, "mp": 7, "atk": 1, "defense": 2, "mag": 4, "spd": 2, "luck": 1},
}

CHAR_SKILL_UNLOCKS = {
    "ARUNA": {
        3: ["LIGHT_BURST"],
        5: ["RADIANT_SLASH"],
        7: ["GUARDIAN_OATH"],
        10: ["LIGHT_WAVE"],
    },
    "UMAR": {
        3: ["SMALL_BARRIER"],
        6: ["GROUP_HEAL"],
        8: ["PURIFY"],
        11: ["REVIVE"],
    },
    "REZA": {
        3: ["MANA_SHIELD"],
        6: ["CHAIN_LIGHTNING"],
        8: ["ARCANE_FOCUS"],
        11: ["ABYSS_SEAL"],
    },
}

# Scene/story ID sesuai GDD
SCENE_DATA = {
    # PROLOG SELATPANJANG
    "CH0_S1": {
        "text": (
            "Selatpanjang, kota pelabuhan kecil di selatan.\n"
            "Di sebuah rumah kayu sederhana, seorang pemuda bernama Aruna memandang laut yang memerah oleh senja.\n\n"
            "Paman: \"Aruna, sudah waktunya makan. Jangan bengong terus di depan jendela.\"\n"
            "Aruna: \"Iya, Paman. Entah kenapa... hari ini terasa berbeda.\"\n"
            "Paman: \"Kalau berbeda, berarti sesuatu akan berubah. Nikmati saja makan malammu.\""
        ),
        "choices": [("Lanjut", "CH0_S2")],
    },
    "CH0_S2": {
        "text": (
            "Malam turun. Aruna duduk di ranjang, memegang kalung bercahaya lembut yang selalu menggantung di lehernya.\n"
            "Paman: \"Suatu hari, kau akan mengerti kenapa kalung itu penting. Tapi belum sekarang.\"\n"
            "Kalung berpendar lemah.\n"
            "Aruna: \"Kalung ini... satu-satunya peninggalan orang tuaku. Siapa kalian sebenarnya?\"\n"
            "Paman hanya tersenyum getir.\n"
        ),
        "choices": [("Kalung itu menyala...", "CH0_S3")],
    },
    "CH0_S3": {
        "text": (
            "Jeritan memecah malam. Tanah bergetar dan udara dipenuhi bau belerang.\n"
            "Penduduk: \"MONSTER!! LARI!!\"\n"
            "Aruna berlari keluar dan melihat bayangan besar di kejauhan: Shadow Fiend.\n"
            "Paman: \"Aruna! Mundur! Itu bukan monster biasa!\"\n"
            "Aruna: \"Aku tidak bisa diam saja! Mereka butuh bantuan!\"\n"
            "Paman: \"Mulai dari minion-nya! Habisi Shadow Slime itu!\"\n\n"
            ">> Battle tutorial melawan Shadow Slime."
        ),
        "choices": [("Hadapi Shadow Slime", "BATTLE_TUTORIAL_1")],
    },
    "CH0_S4_POST_BATTLE": {
        "text": (
            "Setelah mengalahkan Shadow Slime, kamu kembali ke rumah. Dinding runtuh dan paman tergeletak, napasnya tersengal.\n"
            "Paman: \"Dengarkan aku... pergilah ke barat, ke Siak. Di sana kebenaranmu menunggu. Kau keturunan Penjaga Cahaya...\"\n"
            "Kalung menyala terang.\n"
            "Paman: \"Teruslah berjalan sampai Kampar... di sanalah takdirmu...\"\n"
            "Tangannya terkulai. Di luar, suara monster memudar."
        ),
        "choices": [("Pegang janji terakhirnya", "CH0_S5")],
    },
    "CH0_S5": {
        "text": (
            "Fajar menyingsing. Dengan tas kecil dan kalung bercahaya di dada, Aruna berdiri di tepi pelabuhan.\n"
            "Aruna: \"Paman... aku janji. Aku akan ke Siak. Aku akan cari kebenaran, dan aku akan mengakhiri kegelapan ini.\"\n\n"
            ">> MAIN QUEST: Pergi ke Siak (Lv 2)."
        ),
        "choices": [("Buka world map", "GO_TO_WORLD_MAP")],
    },

    # SIAK & UMAR
    "CH1_SIAK_ENTRY": {
        "text": (
            "Kamu tiba di gerbang Siak. Sungai tenang membelah kota panggung kayu.\n"
            "Penjaga: \"Selamat datang di Kota Siak. Di dalam kota tidak ada monster, jadi manfaatkan untuk istirahat dan bekerja.\""
        ),
        "choices": [("Masuk kota", "SIAK_CITY_MENU")],
    },
    "CH1_UMAR_CLINIC": {
        "text": (
            "Klinik sederhana itu dipenuhi aroma herbal. Seorang pemuda healer menyambutmu.\n"
            "Umar: \"Selamat datang di klinik Safiya. Kau tampak babak belur. Monster di jalan, ya?\"\n"
            "Kalungmu tiba-tiba berpendar dan Umar menatap serius."
        ),
        "choices": [
            ("Tanya tentang simbol itu", "CH1_UMAR_CORE"),
            ("Tetap diam", "CH1_UMAR_CORE"),
        ],
    },
    "CH1_UMAR_CORE": {
        "text": (
            "Umar: \"Kalung itu simbol Aruna Core. Ibuku, Safiya, pernah menolong Penjaga Cahaya yang membawa simbol yang sama.\"\n"
            "Aruna: \"Kampar... lagi-lagi nama itu.\"\n"
            "Umar: \"Ibu meninggalkan pesan: 'Jika pembawa cahaya datang, bantu dia apapun yang terjadi.' Aku yakin orang itu adalah kamu.\"\n\n"
            ">> Umar bergabung sebagai healer party."
        ),
        "choices": [("Lanjut", "SIAK_CITY_MENU_AFTER_UMAR")],
    },
    "CH1_GATE_ALERT": {
        "text": (
            "Alarm kota meraung. Para penjaga berlari menuju gerbang kayu.\n"
            "Penjaga: \"Monster bayangan menyerang gerbang! Siapapun yang bisa bertarung, ikut kami!\"\n"
            "Umar: \"Aruna! Ini kesempatan membuktikan kenapa aku harus ikut kamu.\""
        ),
        "choices": [("Bantu penjaga Siak", "BATTLE_SIAK_GATE")],
    },
    "CH1_GATE_AFTER": {
        "text": (
            "Shadow Bandit terakhir jatuh. Para penjaga bersorak lega.\n"
            "Penjaga: \"Kalian menyelamatkan kami. Terima kasih!\"\n"
            "Umar: \"Keputusan sudah jelas. Aku akan ikutmu sampai Kampar.\"\n"
            "Aruna: \"Kenapa sejauh itu?\"\n"
            "Umar: \"Ibu meninggal dengan penyesalan. Aku tidak akan membiarkan warisan Safiya hilang.\""
        ),
        "choices": [("Bicara dengan Umar", "CH1_POINTER_RENGAT")],
    },
    "CH1_POINTER_RENGAT": {
        "text": (
            "Umar: \"Kalau soal Kampar dan Penjaga Cahaya, hanya ada satu nama di kepalaku: Reza, penyihir agung dari Rengat.\"\n"
            "Aruna: \"Penyihir?\"\n"
            "Umar: \"Katanya ia punya hubungan langsung dengan Kampar. Jika ada yang tahu masa lalumu, itu dia.\"\n\n"
            ">> MAIN QUEST diperbarui: Pergi ke Rengat (Lv 5)."
        ),
        "choices": [("Buka world map", "SET_MAIN_RENGAT")],
    },

    # RENGAT & REZA
    "CH2_RENGAT_GATE": {
        "text": (
            "Aura magis menyelimuti gerbang Rengat. Rune bercahaya mengambang di udara.\n"
            "Penjaga: \"Selamat datang di kota para penyihir. Banyak yang mencari ilmu di sini... banyak juga yang hilang saat pergi ke Kampar.\""
        ),
        "choices": [("Masuki kota magis", "CH2_REZA_TOWER")],
    },
    "CH2_REZA_TOWER": {
        "text": (
            "Menara batu sunyi menjulang. Reza menatapmu dari balik buku tebal.\n"
            "Reza: \"Aku tidak menerima murid baru. Pergi.\"\n"
            "Kalungmu kembali berpendar terang."
        ),
        "choices": [("Tunjukkan kalung Aruna Core", "CH2_REZA_REVEAL")],
    },
    "CH2_REZA_REVEAL": {
        "text": (
            "Reza: \"Kalung itu... milik guruku. Ia memberikannya pada Penjaga Cahaya terakhir, Ashalon.\"\n"
            "Aruna: \"Ashalon?\"\n"
            "Reza: \"Ayahmu. Ia mengejar muridnya yang berkhianat, Febri, ke Kampar lima belas tahun lalu.\""
        ),
        "choices": [("Dengar cerita lebih jauh", "CH2_REZA_PAST")],
    },
    "CH2_REZA_PAST": {
        "text": (
            "Reza mengungkap rahasia: Febri haus akan sihir terlarang dan ingin membalikkan waktu.\n"
            "Umar: \"Kenapa seseorang ingin memutar waktu dengan harga segila itu?\"\n"
            "Reza: \"Karena rasa kehilangan. Tapi Kampar hancur karenanya.\"\n"
            "Tiba-tiba tanah bergetar.\n"
        ),
        "choices": [("Apa itu?!", "CH2_GOLEM_ALERT")],
    },
    "CH2_GOLEM_ALERT": {
        "text": (
            "NPC: \"Golem Hutan datang lagi!\"\n"
            "Reza: \"Dia dulu penjaga hutan. Aura Kampar membuatnya gila.\"\n"
            "Umar: \"Kalau begitu kita bebaskan dia.\""
        ),
        "choices": [("Lindungi Rengat", "BATTLE_RENGAT_GOLEM")],
    },
    "CH2_GOLEM_AFTER": {
        "text": (
            "Corrupted Forest Golem runtuh dan kembali tenang. Reza menatapmu.\n"
            "Reza: \"Kalian lebih kuat dari yang kuduga. Tanpa Aruna Core, segel itu tidak akan bertahan.\"\n"
            "Umar: \"Jadi kau akan ikut?\"\n"
            "Reza: \"Guruku mungkin masih terjerat di Kampar. Aku tidak akan membiarkan pengorbanannya sia-sia.\""
        ),
        "choices": [("Biarkan Reza bergabung", "ADD_REZA_PARTY")],
    },
    "CH2_REZA_JOINS": {
        "text": (
            "Reza resmi bergabung dalam party. Cahaya Aruna Core terasa lebih stabil.\n"
            "Reza: \"Sebelum Kampar, kita perlu menguatkan diri di Pekanbaru. Itu kota besar terakhir sebelum neraka.\""
        ),
        "choices": [("Rencanakan perjalanan", "CH2_PEKANBARU_POINTER")],
    },
    "CH2_PEKANBARU_POINTER": {
        "text": (
            "Reza: \"Kumpulkan gear terbaik di Pekanbaru. Dengarkan rumor tentang Febri di sana.\"\n\n"
            ">> MAIN QUEST: Pergi ke Pekanbaru (Lv 8)."
        ),
        "choices": [("Buka world map", "SET_MAIN_PEKANBARU")],
    },

    # PEKANBARU
    "CH3_PEKANBARU_ENTRY": {
        "text": (
            "Pekanbaru terlihat muram. Toko-toko tutup lebih awal dan orang-orang berbisik tentang Kampar.\n"
            "NPC: \"Kau lihat kastil hitam di horizon? Katanya dipanggil dari tanah oleh iblis.\""
        ),
        "choices": [("Cari informasi di kafe gelap", "CH3_PEKANBARU_CAFE")],
    },
    "CH3_PEKANBARU_CAFE": {
        "text": (
            "Kafe remang penuh asap. Seorang orang tua menatap kalungmu.\n"
            "Orang Tua: \"Kalung itu segel cahaya. Aku melihat Febri sebelum ia berubah. Ia dulu manusia... murid jenius yang ingin membalikkan waktu.\"\n"
            "Reza: \"Guruku punya murid lain?\"\n"
            "Orang Tua: \"Sihir terlarang selalu menuntut harga.\""
        ),
        "choices": [("Biarkan cerita mengalir", "CH3_DREAM")],
    },
    "CH3_DREAM": {
        "text": (
            "Malam itu Aruna bermimpi. Ashalon berdiri di hadapan Febri muda.\n"
            "Ashalon: \"Berhentilah, Febri! Kekuatan itu bukan milik manusia!\"\n"
            "Febri: \"Dengan ini aku bisa membalikkan waktu! Aku bisa menyelamatkannya!\"\n"
            "Cahaya dan kegelapan bertubrukan. Ashalon menghilang bersama segel Kampar."
        ),
        "choices": [("Bangun dari mimpi", "CH3_WAKE")],
    },
    "CH3_WAKE": {
        "text": (
            "Aruna terbangun berkeringat.\n"
            "Aruna: \"Aku melihat ayahku. Dia menyegel Febri... lalu lenyap.\"\n"
            "Reza: \"Kalungmu bereaksi makin kuat. Kampar memanggilmu.\""
        ),
        "choices": [("Terima panggilan Kampar", "CH3_KAMPAR_POINTER")],
    },
    "CH3_KAMPAR_POINTER": {
        "text": (
            ">> MAIN QUEST: Pergi ke Kampar – Kota Terkutuk (Lv 12).\n"
            "Umar: \"Apapun yang menunggu di sana, kita hadapi bersama.\""
        ),
        "choices": [("Buka world map", "SET_MAIN_KAMPAR")],
    },

    # KAMPAR
    "CH4_KAMPAR_ENTRY": {
        "text": (
            "Begitu melewati perbatasan Kampar, langit kehilangan warnanya. Rumah-rumah hancur, jalan retak, tak ada suara manusia.\n"
            "Umar: \"Aku tidak merasakan satu pun kehidupan... hanya kegelapan.\"\n"
            "Reza: \"Aura Abyss menutup semuanya.\""
        ),
        "choices": [("Biarkan kalung memandu", "CH4_FLASHBACK")],
    },
    "CH4_FLASHBACK": {
        "text": (
            "Kalung Aruna menyala menyilaukan. Kilasan masa lalu muncul.\n"
            "Ashalon menyerahkan bayi Aruna kepada seorang paman di Selatpanjang.\n"
            "Ashalon: \"Suatu hari... kau yang harus memilih. Selamatkan dunia atau biarkan kegelapan menang.\""
        ),
        "choices": [("Menuju kastil Febri", "CH4_CASTLE_APPROACH")],
    },
    "CH4_CASTLE_APPROACH": {
        "text": (
            "Kastil hitam menjulang di tengah Kampar, seolah mencakar langit. Pintu gerbangnya terbuka seperti undangan.\n"
            "Umar: \"Di sanalah semuanya akan berakhir.\"\n"
            "Reza: \"Atau dimulai lagi dari awal.\""
        ),
        "choices": [("Masuk ke Kastil Febri", "CH5_CASTLE_ENTRY")],
    },

    # KASTIL FEBRI
    "CH5_CASTLE_ENTRY": {
        "text": (
            "Lantai 1 – Koridor Bayangan. Dinding hidup dan bayangan merayap.\n"
            "Umar: \"Monster di sini jauh lebih kuat dari luar.\"\n"
            "Reza: \"Ini baru pintu depan. Jangan lengah.\""
        ),
        "choices": [("Terus ke Balai Kekosongan", "CH5_FLOOR2")],
    },
    "CH5_FLOOR2": {
        "text": (
            "Lantai 2 – Balai Kekosongan. Hound of Void menatap dengan mata ungu menyala.\n"
            "Umar: \"Aura kegelapannya membuat napasku sesak!\"\n"
            "Reza: \"Ini penjaga pertama Abyss.\""
        ),
        "choices": [("Hadapi Hound of Void", "BATTLE_HOUND_OF_VOID")],
    },
    "CH5_FLOOR2_AFTER": {
        "text": (
            "Hound of Void runtuh. Cakar terakhirnya hampir merobek Umar, tapi Aruna Core memancarkan cahaya dan menyembuhkannya.\n"
            "Sistem: \"Aruna Core bereaksi! Umar dipulihkan oleh Cahaya Aruna.\""
        ),
        "choices": [("Naik ke Ruang Segel Lama", "CH5_FLOOR3")],
    },
    "CH5_FLOOR3": {
        "text": (
            "Ruang segel lama dipenuhi rune retak. Di tengahnya hanya tersisa jubah tua.\n"
            "Reza: \"Ini jubah guruku... Febri memakan jiwanya. Yang tersisa hanya kenangan.\"\n"
            "Reza menatap Aruna: \"Mulai sekarang, aku bersumpah melindungimu.\""
        ),
        "choices": [("Buka Gerbang Takdir", "CH5_FLOOR4")],
    },
    "CH5_FLOOR4": {
        "text": (
            "Void Sentinel, armor besar tanpa tubuh, melayang di depan gerbang terakhir.\n"
            "Suara Febri bergema: \"Jika ingin menemuiku, buktikan bahwa kau pantas mati di tanganku.\""
        ),
        "choices": [("Hancurkan Void Sentinel", "BATTLE_VOID_SENTINEL")],
    },
    "CH5_FLOOR4_AFTER": {
        "text": (
            "Sentinel runtuh. Energi gelap berputar membuka jalan menuju tahta.\n"
            "Umar: \"Itu dia... akhir segala mimpi buruk.\""
        ),
        "choices": [("Masuki Tahta Kegelapan", "CH5_FLOOR5")],
    },
    "CH5_FLOOR5": {
        "text": (
            "Tahta Kegelapan – Febri berdiri dengan tubuh setengah manusia setengah iblis.\n"
            "Febri: \"Ashalon... aku sudah lama menunggu.\"\n"
            "Aruna: \"Aku bukan ayahku. Aku Aruna, anak yang kau tinggalkan di dalam kegelapanmu.\"\n"
            "Febri tertawa: \"Ashalon mengorbankan segalanya demi kamu. Seharusnya kaulah yang mati hari itu.\""
        ),
        "choices": [("Pertarungan terakhir", "BATTLE_FEBRI")],
    },
    "CH5_FINAL_WIN": {
        "text": (
            "Febri jatuh berlutut. Aura Abyss goyah.\n"
            "Febri: \"Ashalon... maafkan aku...\"\n"
            "Aruna memegang Aruna Core yang menyala hebat. Saatnya menentukan akhir perang ini."
        ),
        "choices": [("Gunakan cahaya untuk menentukan akhir", "RESOLVE_ENDING")],
    },

    # ENDINGS
    "ENDING_GOOD": {
        "text": (
            "Kau menghancurkan Febri dan memutus paktanya. Kampar perlahan pulih, meski luka masih tertinggal.\n"
            "Aruna kembali ke Selatpanjang sebagai Penjaga Cahaya baru. Umar membuka klinik besar di Siak, Reza memimpin akademi sihir Rengat.\n"
            "Namun jauh di dalam hati, kau tahu ada cara yang lebih damai... jika saja luka lama bisa disembuhkan."
        ),
        "choices": [("Kembali menjelajah", "GO_TO_WORLD_MAP")],
    },
    "ENDING_TRUE": {
        "text": (
            "Cahaya Aruna Core menyegel Febri tanpa menghancurkan jiwanya. Sisa kemanusiaan Febri menangis menyesal sebelum lenyap dalam cahaya.\n"
            "Aura Abyss hilang. Kampar bersih dari kegelapan dan menjadi simbol harapan baru.\n"
            "Umar dan Reza menyelesaikan penyesalan keluarga mereka, sementara Aruna menjaga dunia sebagai Penjaga Cahaya yang matang."
        ),
        "choices": [("Nikmati kedamaian", "GO_TO_WORLD_MAP")],
    },
    "ENDING_BAD": {
        "text": (
            "Teriakan Aruna tenggelam dalam tawa Febri. Kampar tidak lagi sekadar kota terkutuk—ia menjadi pusat kegelapan yang menelan dunia.\n"
            "Aruna Core hancur, Umar dan Reza gugur. Hanya kenangan tentang cahaya yang tersisa di dunia yang runtuh."
        ),
        "choices": [("Bangkit dari kegagalan", "GO_TO_WORLD_MAP")],
    },

    # SIDE QUEST UMAR
    "SQ_UMAR_INTRO": {
        "text": (
            "Seorang warga Siak memanggil Umar.\n"
            "NPC: \"Kau anak Safiya, kan? Di ujung kota ada keluarga yang masih menyimpan dendam pada ibumu.\"\n"
            "Umar menggenggam tongkatnya, ragu-ragu."
        ),
        "choices": [("Temui keluarga tersebut", "SQ_UMAR_FAMILY")],
    },
    "SQ_UMAR_FAMILY": {
        "text": (
            "Keluarga itu menatap Umar dengan mata merah.\n"
            "Keluarga: \"Anak kami mati karena kutukan Kampar. Safiya datang terlambat. Kami tak pernah bisa memaafkannya.\"\n"
            "Umar: \"Ibu tidak pernah berhenti mencoba... bahkan hingga napas terakhirnya.\""
        ),
        "choices": [("Tawarkan bantuan", "SQ_UMAR_FETCH")],
    },
    "SQ_UMAR_FETCH": {
        "text": (
            "Anak kedua keluarga itu kini sakit karena kutukan kecil dari aura Kampar.\n"
            "Umar: \"Biarkan aku mencoba menyembuhkannya. Kalau gagal, bencilah aku, bukan ibuku.\"\n"
            "Untuk membuat ramuan, kalian mencari herb suci di hutan sekitar Siak."
        ),
        "choices": [("Bawa herb itu kembali", "SQ_UMAR_RETURN")],
    },
    "SQ_UMAR_RETURN": {
        "text": (
            "Umar meracik ramuan warisan Safiya. Cahaya lembut menyelimuti anak itu.\n"
            "Keluarga meneteskan air mata: \"Kalau ini warisan Safiya... kami salah membenci.\""
        ),
        "choices": [("Wariskan berkah Safiya", "COMPLETE_UMAR_QUEST")],
    },
    "SQ_UMAR_REWARD": {
        "text": (
            "Umar meraih tongkat ibunya.\n"
            "Umar: \"Aku akan membawa Safiya's Grace ke mana pun aku pergi. Terima kasih sudah mempercayaiku.\"\n"
            "(Umar mempelajari ultimate: Safiya's Grace.)"
        ),
        "choices": [("Kembali ke kota", "BACK_CITY_MENU")],
    },

    # SIDE QUEST REZA
    "SQ_REZA_INTRO": {
        "text": (
            "Seorang tetua Rengat berbisik pada Reza.\n"
            "Tetua: \"Kadang aku mendengar suara dari hutan, memanggil namamu. Suara itu terdengar seperti gurumu.\"\n"
            "Reza menatapmu dan mengangguk."
        ),
        "choices": [("Ikuti suara hutan", "SQ_REZA_FOREST")],
    },
    "SQ_REZA_FOREST": {
        "text": (
            "Di hutan khusus, fragment segel bercahaya berdenyut.\n"
            "Suara Guru: \"Reza... jangan biarkan balas dendam memandumu.\"\n"
            "Reza: \"Guru...? Febri menghancurkanmu. Aku tidak bisa memaafkannya.\""
        ),
        "choices": [("Sentuh fragmen segel", "SQ_REZA_FRAGMENT")],
    },
    "SQ_REZA_FRAGMENT": {
        "text": (
            "Suara Guru: \"Balas dendam melahirkan tragedi baru. Lindungi cahaya, lindungi Aruna.\"\n"
            "Reza menunduk, menyadari luka batinnya sendiri.\n"
            "Reza: \"Aku mengerti sekarang. Aku tidak akan melawan kegelapan dengan kegelapan.\""
        ),
        "choices": [("Terima warisan guru", "COMPLETE_REZA_QUEST")],
    },
    "SQ_REZA_REWARD": {
        "text": (
            "Energi arcane melingkupi party.\n"
            "Reza: \"Master's Legacy akan melindungi kita. Aku tidak sendiri lagi.\"\n"
            "(Reza mempelajari ultimate: Master's Legacy.)"
        ),
        "choices": [("Kembali ke kota", "BACK_CITY_MENU")],
    },
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
    return_scene_after_battle: Optional[str] = None
    loss_scene_after_battle: Optional[str] = None

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


def xp_required_for_next_level(current_level: int) -> int:
    current_level = max(1, current_level)
    return 20 * (2 ** (current_level - 1))


def grant_skill_to_character(character: CharacterState, skill_id: str, logs: Optional[List[str]] = None):
    if skill_id not in SKILLS:
        return
    if skill_id in character.skills:
        return
    character.skills.append(skill_id)
    if logs is not None:
        logs.append(f"{character.name} mempelajari skill baru: {SKILLS[skill_id]['name']}!")


def apply_growth(character: CharacterState):
    growth = CHAR_GROWTH.get(character.id)
    if not growth:
        return
    character.level += 1
    character.max_hp += growth["hp"]
    character.max_mp += growth["mp"]
    character.atk += growth["atk"]
    character.defense += growth["defense"]
    character.mag += growth["mag"]
    character.spd += growth["spd"]
    character.luck += growth["luck"]
    character.hp = character.max_hp
    character.mp = character.max_mp


def check_level_up(state: GameState) -> List[str]:
    messages: List[str] = []
    for cid in state.party_order:
        character = state.party[cid]
        pool = state.xp_pool.get(cid, 0)
        leveled = False
        while pool >= xp_required_for_next_level(character.level):
            requirement = xp_required_for_next_level(character.level)
            pool -= requirement
            apply_growth(character)
            leveled = True
            messages.append(f"{character.name} naik ke Level {character.level}!")
            unlocks = CHAR_SKILL_UNLOCKS.get(cid, {}).get(character.level, [])
            for skill in unlocks:
                grant_skill_to_character(character, skill, messages)
        state.xp_pool[cid] = pool
        if leveled:
            messages.append(
                f"Stat baru {character.name}: HP {character.max_hp} | MP {character.max_mp} | ATK {character.atk} | DEF {character.defense} | MAG {character.mag}"
            )
    return messages


def reset_battle_flags(state: GameState):
    for key in [
        "LAST_DEFEND",
        "ARUNA_DEF_BUFF_TURNS",
        "LIGHT_BUFF_TURNS",
        "ARUNA_LIMIT_USED",
    ]:
        if key in state.flags:
            state.flags.pop(key)


def tick_buffs(state: GameState):
    if state.flags.get("ARUNA_DEF_BUFF_TURNS"):
        state.flags["ARUNA_DEF_BUFF_TURNS"] -= 1
        if state.flags["ARUNA_DEF_BUFF_TURNS"] <= 0:
            state.flags.pop("ARUNA_DEF_BUFF_TURNS", None)
    if state.flags.get("LIGHT_BUFF_TURNS"):
        state.flags["LIGHT_BUFF_TURNS"] -= 1
        if state.flags["LIGHT_BUFF_TURNS"] <= 0:
            state.flags.pop("LIGHT_BUFF_TURNS", None)


def create_enemy_from_key(monster_key: str) -> Dict[str, Any]:
    base = MONSTERS.get(monster_key)
    if not base:
        return pick_random_monster_for_area("HUTAN_SELATPANJANG")
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
        "id": monster_key,
    }


async def start_story_battle(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: GameState,
    enemy_key: str,
    return_scene: str,
    loss_scene: Optional[str] = None,
):
    enemy = create_enemy_from_key(enemy_key)
    state.in_battle = True
    state.battle_enemies = [enemy]
    state.battle_turn = "PLAYER"
    state.return_scene_after_battle = return_scene
    state.loss_scene_after_battle = loss_scene
    reset_battle_flags(state)
    await send_battle_state(update, context, state, intro=True)


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


def calc_physical_damage(attacker: CharacterState, target_def: int, power: float = 1.0) -> int:
    base = attacker.atk - target_def // 2
    if base < 1:
        base = 1
    # variasi kecil
    base = int(base * random.uniform(0.9, 1.1))
    base = int(base * power)
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
    state.return_scene_after_battle = None
    state.loss_scene_after_battle = None
    reset_battle_flags(state)
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
        state.flags["LAST_BATTLE_RESULT"] = "WIN"
        level_msgs = check_level_up(state)
        if level_msgs:
            log.extend(level_msgs)
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
    if state.flags.get("ARUNA_DEF_BUFF_TURNS"):
        dmg_to_player = max(1, int(dmg_to_player * 0.7))

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
        state.flags["LAST_BATTLE_RESULT"] = "LOSE"
        await end_battle_and_return(update, context, state, log_text="\n".join(log))
        return

    tick_buffs(state)
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

    if skill_id == "ARUNA_CORE_AWAKENING" and state.flags.get("ARUNA_LIMIT_USED"):
        log.append("Aruna Core sudah bangkit sekali di pertarungan ini!")
        await send_battle_state(update, context, state, intro=False, extra_text="\n".join(log))
        return

    if c.mp < skill["mp_cost"]:
        log.append(f"{c.name} tidak punya MP yang cukup untuk menggunakan {skill['name']}!")
        await send_battle_state(update, context, state, intro=False, extra_text="\n".join(log))
        return

    c.mp -= skill["mp_cost"]
    enemy = state.battle_enemies[0]

    skill_type = skill.get("type")
    element = skill.get("element", "NETRAL")

    if skill_type == "PHYS":
        dmg = calc_physical_damage(c, enemy["defense"], skill.get("power", 1.0))
        if element == "CAHAYA" and state.flags.get("LIGHT_BUFF_TURNS"):
            dmg = int(dmg * 1.2)
        enemy["hp"] -= dmg
        log.append(f"{c.name} menggunakan {skill['name']}! {enemy['name']} menerima {dmg} damage.")
        if skill_id == "RADIANT_SLASH" and random.random() < 0.2:
            enemy["atk"] = max(1, enemy["atk"] - 2)
            log.append(f"{enemy['name']} goyah! ATK-nya melemah sementara.")
    elif skill_type == "MAG":
        dmg = calc_magic_damage(c, enemy["defense"], skill.get("power", 1.0))
        if element == "CAHAYA" and state.flags.get("LIGHT_BUFF_TURNS"):
            dmg = int(dmg * 1.2)
        enemy["hp"] -= dmg
        log.append(f"{c.name} melempar {skill['name']}! {enemy['name']} menerima {dmg} damage.")
    elif skill_type == "HEAL_SINGLE":
        heal_amount = calc_heal_amount(c, skill.get("power", 0.3))
        target = state.party["ARUNA"]
        before = target.hp
        target.hp = min(target.max_hp, target.hp + heal_amount)
        healed = target.hp - before
        log.append(f"{c.name} menyembuhkan {target.name} sebanyak {healed} HP dengan {skill['name']}.")
    elif skill_type == "HEAL_ALL":
        total = []
        for cid in state.party_order:
            member = state.party[cid]
            heal_amount = calc_heal_amount(c, skill.get("power", 0.25))
            before = member.hp
            member.hp = min(member.max_hp, member.hp + heal_amount)
            total.append(f"{member.name}+{member.hp - before}HP")
        log.append(f"{c.name} menyalurkan {skill['name']}! ({', '.join(total)})")
    elif skill_type == "BUFF_DEF_SELF":
        state.flags["ARUNA_DEF_BUFF_TURNS"] = skill.get("duration", 3)
        log.append(f"{c.name} memperkuat pertahanan dengan {skill['name']}! DEF naik sementara.")
    elif skill_type == "LIMIT_HEAL":
        state.flags["ARUNA_LIMIT_USED"] = True
        state.flags["LIGHT_BUFF_TURNS"] = 3
        total = []
        for cid in state.party_order:
            member = state.party[cid]
            heal_amount = max(1, int(member.max_hp * 0.4))
            before = member.hp
            member.hp = min(member.max_hp, member.hp + heal_amount)
            total.append(f"{member.name}+{member.hp - before}HP")
        log.append(
            "Aruna Core Awakening memulihkan party dan meningkatkan serangan cahaya! ("
            + ", ".join(total)
            + ")"
        )
    else:
        log.append(f"{skill['name']} belum bisa digunakan di sistem battle sederhana ini.")

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
        state.flags["LAST_BATTLE_RESULT"] = "WIN"
        level_msgs = check_level_up(state)
        if level_msgs:
            log.extend(level_msgs)
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
    if state.flags.get("ARUNA_DEF_BUFF_TURNS"):
        enemy_attack = max(1, int(enemy_attack * 0.7))
    target.hp -= enemy_attack
    log.append(f"{enemy['name']} menyerang {target.name} dan memberikan {enemy_attack} damage!")

    if target.hp <= 0:
        log.append(f"{target.name} tumbang! Kamu kalah dalam pertarungan ini...")
        target.hp = max(1, target.max_hp // 3)
        state.in_battle = False
        state.battle_enemies = []
        state.flags["LAST_BATTLE_RESULT"] = "LOSE"
        await end_battle_and_return(update, context, state, log_text="\n".join(log))
        return

    tick_buffs(state)
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
    last_result = state.flags.pop("LAST_BATTLE_RESULT", None)
    reset_battle_flags(state)

    # Deteksi: kalau scene main prolog battle tutorial
    if state.scene_id == "CH0_S3" or state.scene_id.startswith("BATTLE_TUTORIAL"):
        state.scene_id = "CH0_S4_POST_BATTLE"
        await send_scene(update, context, state, extra_text=log_text)
        return

    if state.return_scene_after_battle:
        next_scene = state.return_scene_after_battle
        if last_result == "LOSE" and state.loss_scene_after_battle:
            next_scene = state.loss_scene_after_battle
        state.return_scene_after_battle = None
        state.loss_scene_after_battle = None
        if next_scene:
            state.scene_id = next_scene
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

    if choice_data == "BATTLE_SIAK_GATE":
        state.scene_id = "CH1_GATE_ALERT"
        await start_story_battle(update, context, state, "GATE_SPIRIT", "CH1_GATE_AFTER")
        return

    if choice_data == "BATTLE_RENGAT_GOLEM":
        state.scene_id = "CH2_GOLEM_ALERT"
        await start_story_battle(update, context, state, "CORRUPTED_FOREST_GOLEM", "CH2_GOLEM_AFTER")
        return

    if choice_data == "BATTLE_HOUND_OF_VOID":
        state.scene_id = "CH5_FLOOR2"
        await start_story_battle(update, context, state, "HOUND_OF_VOID", "CH5_FLOOR2_AFTER")
        return

    if choice_data == "BATTLE_VOID_SENTINEL":
        state.scene_id = "CH5_FLOOR4"
        await start_story_battle(update, context, state, "VOID_SENTINEL", "CH5_FLOOR4_AFTER")
        return

    if choice_data == "BATTLE_FEBRI":
        state.scene_id = "CH5_FLOOR5"
        await start_story_battle(update, context, state, "FEBRI_LORD", "CH5_FINAL_WIN", loss_scene="ENDING_BAD")
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

    if choice_data == "SET_MAIN_RENGAT":
        state.main_progress = "Menuju Rengat (Lv 5+)"
        state.flags["SIAK_GATE_EVENT_DONE"] = True
        await send_world_map(update, context, state)
        return

    if choice_data == "SET_MAIN_PEKANBARU":
        state.main_progress = "Menuju Pekanbaru (Lv 8+)"
        await send_world_map(update, context, state)
        return

    if choice_data == "SET_MAIN_KAMPAR":
        state.main_progress = "Menuju Kampar (Lv 12+)"
        state.flags["PEKANBARU_RUMOR_DONE"] = True
        aruna = state.party.get("ARUNA")
        if aruna:
            grant_skill_to_character(aruna, "ARUNA_CORE_AWAKENING")
        await send_world_map(update, context, state)
        return

    if choice_data == "ADD_REZA_PARTY":
        state.add_reza()
        state.scene_id = "CH2_REZA_JOINS"
        await send_scene(update, context, state)
        return

    if choice_data == "COMPLETE_UMAR_QUEST":
        state.flags["UMAR_QUEST_DONE"] = True
        umar = state.party.get("UMAR")
        if umar:
            grant_skill_to_character(umar, "SAFIYAS_GRACE")
        state.scene_id = "SQ_UMAR_REWARD"
        await send_scene(update, context, state)
        return

    if choice_data == "COMPLETE_REZA_QUEST":
        state.flags["REZA_QUEST_DONE"] = True
        reza = state.party.get("REZA")
        if reza:
            grant_skill_to_character(reza, "MASTERS_LEGACY")
        state.scene_id = "SQ_REZA_REWARD"
        await send_scene(update, context, state)
        return

    if choice_data == "RESOLVE_ENDING":
        has_true = state.flags.get("UMAR_QUEST_DONE") and state.flags.get("REZA_QUEST_DONE")
        state.scene_id = "ENDING_TRUE" if has_true else "ENDING_GOOD"
        state.main_progress = "Epilog"
        await send_scene(update, context, state)
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
    text += f"Main Quest: {state.main_progress}\n"
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
    features = CITY_FEATURES.get(state.location, {})
    text = f"KOTA: {loc['name']} (Lv {loc['min_level']}+)\n"
    if features.get("description"):
        text += features["description"] + "\n"
    text += f"Gold: {state.gold}\n"
    if extra_text:
        text += extra_text + "\n"
    text += "Apa yang ingin kamu lakukan?"

    choices = [("Lihat status party", "MENU_STATUS")]
    if loc.get("has_shop"):
        choices.append(("Pergi ke toko", "MENU_SHOP"))
    if loc.get("has_job") and features.get("jobs"):
        choices.append(("Bekerja (job)", "MENU_JOB"))
    if loc.get("has_inn"):
        choices.append(("Ke penginapan (heal)", "MENU_INN"))
    if loc.get("has_clinic"):
        choices.append(("Pergi ke klinik", "MENU_CLINIC"))

    # Event / side quest per kota
    if state.location == "SIAK":
        if state.flags.get("HAS_UMAR") and not state.flags.get("UMAR_QUEST_DONE"):
            choices.append(("Side Quest Umar: Warisan Safiya", "QUEST_UMAR"))
        if state.flags.get("HAS_UMAR") and not state.flags.get("SIAK_GATE_EVENT_DONE"):
            choices.append(("Periksa gerbang kota", "EVENT_SIAK_GATE"))
    if state.location == "RENGAT" and state.flags.get("HAS_REZA") and not state.flags.get("REZA_QUEST_DONE"):
        choices.append(("Side Quest Reza: Suara dari Segel", "QUEST_REZA"))
    if state.location == "PEKANBARU" and not state.flags.get("PEKANBARU_RUMOR_DONE"):
        choices.append(("Cari rumor di kafe remang", "EVENT_PEKANBARU_CAFE"))
    if state.location == "KAMPAR":
        choices.append(("Menuju Kastil Febri", "EVENT_KASTIL_ENTRY"))

    choices.append(("Kembali ke world map", "GO_TO_WORLD_MAP"))

    keyboard = make_keyboard(choices)
    query = update.callback_query
    if query:
        await query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text=text, reply_markup=keyboard)


async def send_job_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState):
    features = CITY_FEATURES.get(state.location, {})
    jobs = features.get("jobs", {})
    if not jobs:
        text = "Tidak ada pekerjaan yang tersedia di kota ini."
        keyboard = make_keyboard([("Kembali ke kota", "BACK_CITY_MENU")])
        query = update.callback_query
        if query:
            await query.edit_message_text(text=text, reply_markup=keyboard)
        else:
            await update.message.reply_text(text=text, reply_markup=keyboard)
        return

    lines = ["Pilih pekerjaan di kota ini:"]
    keyboard_choices = []
    for job_id, info in jobs.items():
        lines.append(f"- {info['name']}: {info['description']} (Bayaran {info['payout'][0]}-{info['payout'][1]} Gold)")
        keyboard_choices.append((info["name"], f"DO_JOB|{job_id}"))
    keyboard_choices.append(("Batal", "BACK_CITY_MENU"))
    keyboard = make_keyboard(keyboard_choices)
    query = update.callback_query
    if query:
        await query.edit_message_text(text="\n".join(lines), reply_markup=keyboard)
    else:
        await update.message.reply_text(text="\n".join(lines), reply_markup=keyboard)


async def resolve_job(update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState, job_id: str):
    features = CITY_FEATURES.get(state.location, {})
    job = features.get("jobs", {}).get(job_id)
    if not job:
        text = "Pekerjaan tidak tersedia."
    else:
        fail = random.random() < job.get("fail_chance", 0)
        if fail:
            text = f"Kamu gagal menyelesaikan {job['name']}. Kamu tidak dibayar."
        else:
            payout = random.randint(job["payout"][0], job["payout"][1])
            state.gold += payout
            text = f"Kamu menyelesaikan {job['name']} dan mendapatkan {payout} Gold!"
    keyboard = make_keyboard([("Kembali ke kota", "BACK_CITY_MENU")])
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
    lines.append(f"Main Quest: {state.main_progress}")
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
        elif loc_id == "RENGAT" and not state.flags.get("VISITED_RENGAT"):
            state.flags["VISITED_RENGAT"] = True
            state.scene_id = "CH2_RENGAT_GATE"
            await send_scene(update, context, state)
        elif loc_id == "PEKANBARU" and not state.flags.get("VISITED_PEKANBARU"):
            state.flags["VISITED_PEKANBARU"] = True
            state.scene_id = "CH3_PEKANBARU_ENTRY"
            await send_scene(update, context, state)
        elif loc_id == "KAMPAR" and not state.flags.get("VISITED_KAMPAR"):
            state.flags["VISITED_KAMPAR"] = True
            state.scene_id = "CH4_KAMPAR_ENTRY"
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
        lines.append(f"Main Quest: {state.main_progress}")
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
        features = CITY_FEATURES.get(state.location, {})
        items = features.get("shop_items", [])
        if not items:
            text = "Tidak ada toko yang beroperasi di kota terkutuk ini."
        else:
            text = "SHOP – Barang yang tersedia:\n" + "\n".join(f"- {item}" for item in items)
            text += "\n\n(Belum bisa membeli secara langsung di versi demo.)"
        keyboard = make_keyboard([("Kembali ke kota", "BACK_CITY_MENU")])
        await query.edit_message_text(text=text, reply_markup=keyboard)
        return

    if data == "MENU_JOB":
        await send_job_menu(update, context, state)
        return

    if data == "MENU_INN":
        cost = CITY_FEATURES.get(state.location, {}).get("inn_cost", 0)
        if cost > state.gold:
            text = f"Biaya penginapan {cost} Gold, tapi Gold-mu tidak cukup."
        else:
            state.gold -= cost
            for cid in state.party_order:
                c = state.party[cid]
                c.hp = c.max_hp
                c.mp = c.max_mp
            if cost == 0:
                text = "Kamu beristirahat gratis. HP & MP seluruh party pulih."
            else:
                text = (
                    f"Kamu membayar {cost} Gold dan beristirahat di penginapan. "
                    "HP & MP seluruh party pulih."
                )
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

    if data == "EVENT_SIAK_GATE":
        state.scene_id = "CH1_GATE_ALERT"
        await send_scene(update, context, state)
        return

    if data == "EVENT_PEKANBARU_CAFE":
        state.flags["PEKANBARU_RUMOR_DONE"] = True
        state.scene_id = "CH3_PEKANBARU_ENTRY"
        await send_scene(update, context, state)
        return

    if data == "EVENT_KASTIL_ENTRY":
        state.scene_id = "CH4_CASTLE_APPROACH"
        await send_scene(update, context, state)
        return

    if data == "QUEST_UMAR":
        state.scene_id = "SQ_UMAR_INTRO"
        await send_scene(update, context, state)
        return

    if data == "QUEST_REZA":
        state.scene_id = "SQ_REZA_INTRO"
        await send_scene(update, context, state)
        return

    if data.startswith("DO_JOB|"):
        _, job_id = data.split("|")
        await resolve_job(update, context, state, job_id)
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
