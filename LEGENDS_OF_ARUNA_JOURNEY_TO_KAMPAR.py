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

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
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
        "shop_items": ["WOODEN_SWORD", "LEATHER_ARMOR", "POTION_SMALL", "ETHER_SMALL"],
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
            "LIGHT_ROBE",
            "POTION_SMALL",
            "POTION_MEDIUM",
            "ETHER_SMALL",
            "ETHER_MEDIUM",
            "HERBAL_TEA",
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
            "BRONZE_SWORD",
            "CHAIN_ARMOR",
            "MYSTIC_CLOAK",
            "POTION_MEDIUM",
            "ETHER_MEDIUM",
            "HERBAL_TEA",
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

# =====================================
# ITEM DEFINITIONS
# =====================================

ITEMS = {
    "POTION_SMALL": {
        "id": "POTION_SMALL",
        "name": "Potion Kecil",
        "description": "Memulihkan 50 HP satu karakter.",
        "type": "consumable",
        "buy_price": 20,
        "sell_price": 10,
        "effects": {"hp_restore": 50, "target": "single"},
    },
    "POTION_MEDIUM": {
        "id": "POTION_MEDIUM",
        "name": "Potion Sedang",
        "description": "Memulihkan 120 HP satu karakter.",
        "type": "consumable",
        "buy_price": 60,
        "sell_price": 30,
        "effects": {"hp_restore": 120, "target": "single"},
    },
    "ETHER_SMALL": {
        "id": "ETHER_SMALL",
        "name": "Ether Kecil",
        "description": "Memulihkan 15 MP satu karakter.",
        "type": "consumable",
        "buy_price": 40,
        "sell_price": 20,
        "effects": {"mp_restore": 15, "target": "single"},
    },
    "ETHER_MEDIUM": {
        "id": "ETHER_MEDIUM",
        "name": "Ether Sedang",
        "description": "Memulihkan 30 MP satu karakter.",
        "type": "consumable",
        "buy_price": 90,
        "sell_price": 45,
        "effects": {"mp_restore": 30, "target": "single"},
    },
    "HERBAL_TEA": {
        "id": "HERBAL_TEA",
        "name": "Teh Herbal Hangat",
        "description": "Ramuan ringan yang menyembuhkan seluruh party sedikit.",
        "type": "consumable",
        "buy_price": 120,
        "sell_price": 60,
        "effects": {"hp_restore": 40, "target": "party"},
    },
    "WOODEN_SWORD": {
        "id": "WOODEN_SWORD",
        "name": "Pedang Kayu",
        "description": "Pedang sederhana untuk pemula.",
        "type": "weapon",
        "buy_price": 50,
        "sell_price": 25,
        "allowed_users": ["ARUNA"],
        "effects": {"atk_bonus": 3},
    },
    "BRONZE_SWORD": {
        "id": "BRONZE_SWORD",
        "name": "Pedang Perunggu",
        "description": "Pedang logam ringan yang menambah daya serang Aruna.",
        "type": "weapon",
        "buy_price": 140,
        "sell_price": 70,
        "allowed_users": ["ARUNA"],
        "effects": {"atk_bonus": 7},
    },
    "LEATHER_ARMOR": {
        "id": "LEATHER_ARMOR",
        "name": "Baju Kulit",
        "description": "Pelindung ringan yang meningkatkan ketahanan Aruna.",
        "type": "armor",
        "buy_price": 65,
        "sell_price": 30,
        "allowed_users": ["ARUNA"],
        "effects": {"def_bonus": 3, "hp_bonus": 12},
    },
    "CHAIN_ARMOR": {
        "id": "CHAIN_ARMOR",
        "name": "Zirah Rantai",
        "description": "Armor rantai sederhana yang menambah pertahanan fisik.",
        "type": "armor",
        "buy_price": 150,
        "sell_price": 75,
        "allowed_users": ["ARUNA"],
        "effects": {"def_bonus": 6, "hp_bonus": 18},
    },
    "LIGHT_ROBE": {
        "id": "LIGHT_ROBE",
        "name": "Jubah Cahaya",
        "description": "Jubah tipis untuk Umar atau Reza yang menambah MAG.",
        "type": "armor",
        "buy_price": 110,
        "sell_price": 55,
        "allowed_users": ["UMAR", "REZA"],
        "effects": {"def_bonus": 2, "mag_bonus": 3, "hp_bonus": 8},
    },
    "MYSTIC_CLOAK": {
        "id": "MYSTIC_CLOAK",
        "name": "Jubah Mistik",
        "description": "Cloak langka yang melindungi penyihir dari serangan gelap.",
        "type": "armor",
        "buy_price": 200,
        "sell_price": 100,
        "allowed_users": ["ARUNA", "UMAR", "REZA"],
        "effects": {
            "def_bonus": 4,
            "mag_bonus": 4,
            "mp_bonus": 12,
            "passives": {"element_boost": {"CAHAYA": 0.05}},
        },
    },
    "HARSAN_LEGACY_BLADE": {
        "id": "HARSAN_LEGACY_BLADE",
        "name": "Pedang Warisan Harsan",
        "description": "Pedang warisan keluarga Harsan yang bangkit kembali saat bersatu dengan Aruna Core; dulu dipisahkan dari kalung untuk menahan Abyss.",
        "type": "weapon",
        "buy_price": 0,
        "sell_price": 0,
        "allowed_users": ["ARUNA"],
        "effects": {
            "atk_bonus": 16,
            "passives": {
                "element_boost": {"CAHAYA": 0.35},
                "bonus_vs_element": {"GELAP": 0.3, "ABYSS": 0.3},
                "light_skill_amp": 0.15,
            },
        },
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
        "weakness": ["CAHAYA"],
        "resist": ["GELAP"],
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
        "weakness": ["CAHAYA"],
        "resist": ["GELAP"],
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
        "weakness": ["CAHAYA"],
        "resist": ["GELAP"],
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
        "weakness": ["CAHAYA"],
        "resist": ["GELAP"],
    },
    "HERB_GUARDIAN": {
        "name": "Herb Guardian",
        "area": "HUTAN_SIAK",
        "level": 6,
        "hp": 85,
        "mp": 15,
        "atk": 12,
        "defense": 9,
        "mag": 6,
        "spd": 6,
        "luck": 4,
        "xp": 36,
        "gold": 24,
        "element": "ALAM",
        "weakness": ["API"],
        "resist": ["ALAM"],
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
        "weakness": ["API"],
        "resist": ["ALAM"],
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
        "weakness": ["GELAP"],
        "resist": ["CAHAYA"],
    },
    "SEAL_WARDEN": {
        "name": "Penjaga Segel Retak",
        "area": "HUTAN_RENGAT",
        "level": 9,
        "hp": 120,
        "mp": 28,
        "atk": 16,
        "defense": 12,
        "mag": 14,
        "spd": 7,
        "luck": 4,
        "xp": 55,
        "gold": 32,
        "element": "GELAP",
        "weakness": ["CAHAYA"],
        "resist": ["GELAP"],
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
        "weakness": ["API"],
        "resist": ["ALAM"],
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
        "weakness": ["CAHAYA"],
        "resist": ["GELAP"],
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
        "weakness": ["CAHAYA"],
        "resist": ["GELAP"],
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
        "weakness": ["CAHAYA"],
        "resist": ["GELAP"],
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
        "weakness": ["CAHAYA"],
        "resist": ["GELAP"],
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
        "weakness": ["CAHAYA"],
        "resist": ["GELAP"],
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
        "weakness": ["CAHAYA"],
        "resist": ["GELAP"],
    },
    "LUMINAR_SENTINEL": {
        "name": "Luminar Sentinel",
        "area": "HARSAN_SHRINE",
        "level": 11,
        "hp": 160,
        "mp": 40,
        "atk": 18,
        "defense": 14,
        "mag": 18,
        "spd": 10,
        "luck": 5,
        "xp": 90,
        "gold": 80,
        "element": "CAHAYA",
        "weakness": ["GELAP"],
        "resist": ["CAHAYA"],
    },
    "ABYSS_SHADE": {
        "name": "Abyss Shade",
        "area": "HARSAN_SHRINE",
        "level": 10,
        "hp": 130,
        "mp": 30,
        "atk": 17,
        "defense": 12,
        "mag": 16,
        "spd": 12,
        "luck": 6,
        "xp": 70,
        "gold": 70,
        "element": "GELAP",
        "weakness": ["CAHAYA"],
        "resist": ["GELAP"],
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
        "weakness": ["CAHAYA"],
        "resist": ["GELAP"],
    },
}

# Drop tables per area
DROP_TABLES = {
    "HUTAN_SELATPANJANG": [
        {"item_id": "POTION_SMALL", "chance": 0.35, "min_qty": 1, "max_qty": 2},
        {"item_id": "WOODEN_SWORD", "chance": 0.08, "min_qty": 1, "max_qty": 1},
    ],
    "HUTAN_SIAK": [
        {"item_id": "POTION_SMALL", "chance": 0.3, "min_qty": 1, "max_qty": 2},
        {"item_id": "LEATHER_ARMOR", "chance": 0.06, "min_qty": 1, "max_qty": 1},
        {"item_id": "ETHER_SMALL", "chance": 0.1, "min_qty": 1, "max_qty": 1},
    ],
    "HUTAN_RENGAT": [
        {"item_id": "POTION_MEDIUM", "chance": 0.25, "min_qty": 1, "max_qty": 1},
        {"item_id": "LIGHT_ROBE", "chance": 0.08, "min_qty": 1, "max_qty": 1},
        {"item_id": "HERBAL_TEA", "chance": 0.12, "min_qty": 1, "max_qty": 1},
    ],
    "HUTAN_PEKANBARU": [
        {"item_id": "ETHER_SMALL", "chance": 0.25, "min_qty": 1, "max_qty": 1},
        {"item_id": "MYSTIC_CLOAK", "chance": 0.05, "min_qty": 1, "max_qty": 1},
        {"item_id": "ETHER_MEDIUM", "chance": 0.16, "min_qty": 1, "max_qty": 1},
    ],
    "KAMPAR_LUAR": [
        {"item_id": "POTION_MEDIUM", "chance": 0.35, "min_qty": 1, "max_qty": 2},
        {"item_id": "BRONZE_SWORD", "chance": 0.07, "min_qty": 1, "max_qty": 1},
    ],
    "HARSAN_SHRINE": [
        {"item_id": "ETHER_SMALL", "chance": 0.4, "min_qty": 1, "max_qty": 2},
    ],
}


def generate_loot_for_area(area_id: str) -> List[Tuple[str, int]]:
    loot: List[Tuple[str, int]] = []
    for entry in DROP_TABLES.get(area_id, []):
        chance = entry.get("chance", 0)
        if random.random() > chance:
            continue
        qty = random.randint(entry.get("min_qty", 1), entry.get("max_qty", 1))
        loot.append((entry["item_id"], qty))
    return loot


def grant_battle_drops(state: GameState) -> List[str]:
    area = state.flags.get("CURRENT_BATTLE_AREA")
    if not area:
        return []
    drops = []
    for item_id, qty in generate_loot_for_area(area):
        adjust_inventory(state, item_id, qty)
        item = ITEMS.get(item_id)
        name = item["name"] if item else item_id
        drops.append(f"{name} x{qty}")
    return drops

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
        "buffs": {"defense": 5},
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
        "duration": 3,
        "buffs": {"defense": 4},
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
        "target": "party",
        "description": "Menghilangkan 1 debuff dari ally.",
    },
    "REVIVE": {
        "name": "Revive",
        "mp_cost": 18,
        "type": "REVIVE",
        "revive_ratio": 0.4,
        "description": "Menghidupkan ally yang tumbang.",
    },
    "SAFIYA_GRACE": {
        "name": "Grace Safiya",
        "mp_cost": 20,
        "type": "HEAL_ALL",
        "power": 0.5,
        "description": "Ultimate Umar: heal besar seluruh tim dan membersihkan luka batin.",
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
        "duration": 3,
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
        "duration": 3,
        "buffs": {"mag": 5},
        "penalties": {"spd": -2},
        "description": "Meningkatkan MAG Reza namun menurunkan SPD sementara.",
    },
    "LEGACY_RADIANCE": {
        "name": "Legacy Radiance",
        "mp_cost": 12,
        "type": "PHYS",
        "power": 1.6,
        "element": "CAHAYA",
        "description": "Tebasan cahaya dari pedang warisan Harsan yang membakar kegelapan.",
    },
    "ABYSS_SEAL": {
        "name": "Abyss Seal",
        "mp_cost": 15,
        "type": "DEBUFF_ENEMY",
        "debuffs": {"mag": -4, "spd": -3},
        "duration": 3,
        "description": "Menurunkan MAG dan SPD musuh.",
    },
    "MASTER_LEGACY": {
        "name": "Warisan Sang Guru",
        "mp_cost": 20,
        "type": "BUFF_TEAM",
        "buffs": {"atk": 3, "mag": 3, "defense": 3},
        "duration": 3,
        "description": "Ultimate Reza: buff ATK/MAG/DEF dan tekad melindungi dari kegelapan.",
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

LEVEL_XP = {
    1: 30,
    2: 70,
    3: 120,
    4: 180,
    5: 250,
    6: 330,
    7: 420,
    8: 520,
    9: 630,
    10: 750,
}

CHAR_GROWTH = {
    "ARUNA": {"hp": 9, "mp": 3, "atk": 3, "defense": 2, "mag": 2, "spd": 2, "luck": 1},
    "UMAR": {"hp": 8, "mp": 5, "atk": 2, "defense": 2, "mag": 3, "spd": 1, "luck": 2},
    "REZA": {"hp": 8, "mp": 5, "atk": 2, "defense": 2, "mag": 4, "spd": 1, "luck": 1},
}

CHAR_SKILL_UNLOCKS = {
    "ARUNA": [
        (3, "LIGHT_BURST"),
        (6, "RADIANT_SLASH"),
        (9, "GUARDIAN_OATH"),
        (12, "LIGHT_WAVE"),
    ],
    "UMAR": [
        (2, "HEAL"),
        (5, "SMALL_BARRIER"),
        (7, "GROUP_HEAL"),
        (10, "PURIFY"),
        (13, "REVIVE"),
    ],
    "REZA": [
        (2, "FIRE_BOLT"),
        (5, "CHAIN_LIGHTNING"),
        (7, "MANA_SHIELD"),
        (10, "ARCANE_FOCUS"),
        (14, "ABYSS_SEAL"),
    ],
}

# STORY DATA LOADER
# Story/story data diambil dari file eksternal
SCENE_FILES = [os.path.join("data", "scenes_main.json")]
SCENES: Dict[str, Dict[str, Any]] = {}


def _normalize_flags(flag_data: Any) -> Dict[str, List[str]]:
    set_flags: List[str] = []
    unset_flags: List[str] = []
    if isinstance(flag_data, dict):
        set_raw = flag_data.get("set") or flag_data.get("set_flags") or []
        unset_raw = flag_data.get("unset") or flag_data.get("unset_flags") or []
        if isinstance(set_raw, list):
            set_flags = [f for f in set_raw if isinstance(f, str)]
        if isinstance(unset_raw, list):
            unset_flags = [f for f in unset_raw if isinstance(f, str)]
    elif isinstance(flag_data, list):
        set_flags = [f for f in flag_data if isinstance(f, str)]
    return {"set": set_flags, "unset": unset_flags}


def _normalize_requirements(req_data: Any) -> Dict[str, Any]:
    req_flags: List[str] = []
    min_level: Optional[int] = None
    if isinstance(req_data, dict):
        flags_raw = req_data.get("flags", [])
        if isinstance(flags_raw, list):
            req_flags = [f for f in flags_raw if isinstance(f, str)]
        level_raw = req_data.get("min_level")
        if isinstance(level_raw, int):
            min_level = level_raw
    return {"flags": req_flags, "min_level": min_level}


def _normalize_choice(choice: Any, scene_id: str, index: int) -> Optional[Dict[str, Any]]:
    if not isinstance(choice, dict):
        return None
    label = choice.get("label")
    next_scene = choice.get("next_scene") or choice.get("next")
    battle_key = choice.get("battle")
    command = choice.get("command")
    callback_data = (
        choice.get("callback_data")
        or command
        or next_scene
        or battle_key
        or f"SCENECHOICE|{scene_id}|{index}"
    )
    return {
        "label": label or "Lanjut",
        "next_scene": next_scene,
        "battle": battle_key,
        "command": command,
        "flags": _normalize_flags(choice.get("flags")),
        "requirements": _normalize_requirements(choice.get("requirements")),
        "callback_data": str(callback_data),
    }


def _normalize_text(text_data: Any) -> List[str]:
    if isinstance(text_data, list):
        return [str(line) for line in text_data]
    if isinstance(text_data, str):
        return text_data.split("\n")
    return []


def load_scenes(paths: Optional[List[str]] = None) -> None:
    """Muat semua file scene eksternal ke dalam kamus global SCENES."""

    global SCENES
    paths = paths or SCENE_FILES
    loaded: Dict[str, Dict[str, Any]] = {}
    for path in paths:
        if not os.path.exists(path):
            logger.warning("Scene file tidak ditemukan: %s", path)
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Gagal memuat scene file %s: %s", path, exc)
            continue
        if not isinstance(data, dict):
            logger.warning("Format scene file tidak valid (harus dict): %s", path)
            continue
        for scene_id, scene_data in data.items():
            text_lines = _normalize_text(scene_data.get("text", []))
            flags = _normalize_flags(scene_data.get("flags"))
            requirements = _normalize_requirements(scene_data.get("requirements"))
            choices_raw = scene_data.get("choices", [])
            choices: List[Dict[str, Any]] = []
            if isinstance(choices_raw, list):
                for idx, choice in enumerate(choices_raw):
                    normalized = _normalize_choice(choice, scene_id, idx)
                    if normalized:
                        choices.append(normalized)
            loaded[scene_id] = {
                "text": text_lines,
                "choices": choices,
                "flags": flags,
                "requirements": requirements,
            }
    SCENES = loaded


def get_scene(scene_id: str) -> Optional[Dict[str, Any]]:
    return SCENES.get(scene_id)


# Muat scene utama saat startup
load_scenes()

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
    weapon_id: Optional[str] = None
    armor_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "mp": self.mp,
            "max_mp": self.max_mp,
            "atk": self.atk,
            "defense": self.defense,
            "mag": self.mag,
            "spd": self.spd,
            "luck": self.luck,
            "skills": list(self.skills),
            "weapon_id": self.weapon_id,
            "armor_id": self.armor_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CharacterState":
        return cls(
            id=data.get("id", "UNKNOWN"),
            name=data.get("name", ""),
            level=data.get("level", 1),
            hp=data.get("hp", 1),
            max_hp=data.get("max_hp", 1),
            mp=data.get("mp", 0),
            max_mp=data.get("max_mp", 0),
            atk=data.get("atk", 1),
            defense=data.get("defense", 1),
            mag=data.get("mag", 1),
            spd=data.get("spd", 1),
            luck=data.get("luck", 1),
            skills=list(data.get("skills", [])),
            weapon_id=data.get("weapon_id"),
            armor_id=data.get("armor_id"),
        )


@dataclass
class BattleTurnState:
    turn_order: List[str] = field(default_factory=list)
    current_turn_index: int = -1
    enemies: List[Dict[str, Any]] = field(default_factory=list)
    awaiting_player_input: bool = False
    active_token: Optional[str] = None


@dataclass
class GameState:
    user_id: int
    scene_id: str = "CH0_S1"
    location: str = "SELATPANJANG"
    in_battle: bool = False
    battle_enemies: List[Dict[str, Any]] = field(default_factory=list)
    battle_turn: str = "PLAYER"
    battle_state: BattleTurnState = field(default_factory=BattleTurnState)
    gold: int = 0
    main_progress: str = "PROLOG"
    party: Dict[str, CharacterState] = field(default_factory=dict)
    party_order: List[str] = field(default_factory=list)
    inventory: Dict[str, int] = field(default_factory=dict)
    xp_pool: Dict[str, int] = field(default_factory=dict)
    flags: Dict[str, Any] = field(default_factory=dict)
    return_scene_after_battle: Optional[str] = None
    loss_scene_after_battle: Optional[str] = None

    def __post_init__(self):
        self.ensure_flag_defaults()

    def ensure_flag_defaults(self):
        default_flags = {
            "HAS_UMAR": False,
            "HAS_REZA": False,
            "UMAR_QUEST_DONE": False,
            "REZA_QUEST_DONE": False,
            "QUEST_WEAPON_STARTED": False,
            "QUEST_WEAPON_DONE": False,
            "WEAPON_QUEST_STARTED": False,
            "WEAPON_QUEST_DONE": False,
        }
        for key, value in default_flags.items():
            self.flags.setdefault(key, value)

    def to_dict(self) -> Dict[str, Any]:
        safe_flags = {
            k: v
            for k, v in self.flags.items()
            if k
            not in {
                "ACTIVE_BUFFS",
                "DEFENDING",
                "LIGHT_BUFF_TURNS",
                "ARUNA_LIMIT_USED",
                "CURRENT_BATTLE_AREA",
                "MANA_SHIELD",
            }
        }
        return {
            "scene_id": self.scene_id,
            "location": self.location,
            "main_progress": self.main_progress,
            "gold": self.gold,
            "party_order": list(self.party_order),
            "party": {cid: ch.to_dict() for cid, ch in self.party.items()},
            "inventory": dict(self.inventory),
            "xp_pool": dict(self.xp_pool),
            "flags": safe_flags,
        }

    @classmethod
    def from_dict(cls, user_id: int, data: Dict[str, Any]) -> "GameState":
        state = cls(user_id=user_id)
        state.scene_id = data.get("scene_id", state.scene_id)
        state.location = data.get("location", state.location)
        state.main_progress = data.get("main_progress", state.main_progress)
        state.gold = data.get("gold", 0)
        party_data = data.get("party", {})
        state.party = {cid: CharacterState.from_dict(ch) for cid, ch in party_data.items()}
        saved_order = data.get("party_order", [])
        state.party_order = [cid for cid in saved_order if cid in state.party]
        for cid in state.party:
            if cid not in state.party_order:
                state.party_order.append(cid)
        if not state.party:
            state.ensure_aruna()
        state.inventory = data.get("inventory", {})
        state.xp_pool = data.get("xp_pool", {})
        for cid in state.party_order:
            state.xp_pool.setdefault(cid, 0)
        state.flags = data.get("flags", {})
        state.ensure_flag_defaults()
        state.in_battle = False
        state.battle_enemies = []
        state.battle_state = BattleTurnState()
        state.return_scene_after_battle = None
        state.loss_scene_after_battle = None
        return state

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


EQUIP_BONUS_MAP = {
    "atk_bonus": "atk",
    "def_bonus": "defense",
    "mag_bonus": "mag",
    "hp_bonus": "max_hp",
    "mp_bonus": "max_mp",
    "spd_bonus": "spd",
    "luck_bonus": "luck",
}


def get_equipment_stat_bonuses(character: CharacterState) -> Dict[str, int]:
    bonuses: Dict[str, int] = {attr: 0 for attr in EQUIP_BONUS_MAP.values()}
    for slot in [character.weapon_id, character.armor_id]:
        if not slot:
            continue
        item = ITEMS.get(slot)
        if not item:
            continue
        effects = item.get("effects", {})
        for effect_key, attr in EQUIP_BONUS_MAP.items():
            bonus = effects.get(effect_key, 0)
            if bonus:
                bonuses[attr] = bonuses.get(attr, 0) + bonus
    return bonuses


def get_effective_stat(character: CharacterState, attr: str) -> int:
    bonuses = get_equipment_stat_bonuses(character)
    return getattr(character, attr, 0) + bonuses.get(attr, 0)


def get_effective_max_hp(character: CharacterState) -> int:
    return get_effective_stat(character, "max_hp")


def get_effective_max_mp(character: CharacterState) -> int:
    return get_effective_stat(character, "max_mp")


def get_effective_combat_stats(character: CharacterState) -> Dict[str, int]:
    bonuses = get_equipment_stat_bonuses(character)
    stats: Dict[str, int] = {}
    for attr in ["atk", "defense", "mag", "spd", "luck", "max_hp", "max_mp"]:
        stats[attr] = getattr(character, attr, 0) + bonuses.get(attr, 0)
    return stats


def clamp_resource_to_effective_cap(character: CharacterState):
    effective_max_hp = get_effective_max_hp(character)
    effective_max_mp = get_effective_max_mp(character)
    if character.hp > effective_max_hp:
        character.hp = effective_max_hp
    if character.mp > effective_max_mp:
        character.mp = effective_max_mp


def format_effective_stat_summary(character: CharacterState) -> str:
    stats = get_effective_combat_stats(character)
    return (
        f"{character.name} Lv {character.level} | HP {character.hp}/{stats['max_hp']} | "
        f"MP {character.mp}/{stats['max_mp']} | ATK {stats['atk']} DEF {stats['defense']} MAG {stats['mag']}"
    )


def adjust_inventory(state: GameState, item_id: str, delta: int) -> int:
    if delta == 0:
        return state.inventory.get(item_id, 0)
    new_value = state.inventory.get(item_id, 0) + delta
    if new_value <= 0:
        state.inventory.pop(item_id, None)
        return 0
    state.inventory[item_id] = new_value
    return new_value


def unequip_item(state: GameState, char_id: str, slot: str) -> Tuple[bool, str]:
    character = state.party.get(char_id)
    if not character:
        return False, "Karakter tidak ditemukan."
    slot_attr = "weapon_id" if slot == "weapon" else "armor_id"
    equipped_id = getattr(character, slot_attr)
    if not equipped_id:
        return False, "Tidak ada equipment yang terpasang."
    item = ITEMS.get(equipped_id)
    adjust_inventory(state, equipped_id, 1)
    setattr(character, slot_attr, None)
    clamp_resource_to_effective_cap(character)
    message = f"{character.name} melepas {item['name']}." if item else "Equipment dilepas."
    return True, message


def equip_item(
    state: GameState, char_id: str, item_id: str, expected_type: Optional[str] = None
) -> Tuple[bool, str]:
    character = state.party.get(char_id)
    if not character:
        return False, "Karakter tidak ditemukan."
    item = ITEMS.get(item_id)
    if not item:
        return False, "Item tidak dikenal."
    if item.get("type") not in {"weapon", "armor"}:
        return False, "Item itu bukan equipment."
    if expected_type and item.get("type") != expected_type:
        return False, "Item tidak cocok dengan slot."
    allowed = item.get("allowed_users")
    if allowed and char_id not in allowed:
        return False, f"{item['name']} tidak cocok untuk {character.name}."
    qty = state.inventory.get(item_id, 0)
    if qty <= 0:
        return False, "Kamu tidak memiliki item tersebut."
    slot_attr = "weapon_id" if item["type"] == "weapon" else "armor_id"
    currently_equipped = getattr(character, slot_attr)
    if currently_equipped:
        unequip_item(state, char_id, item["type"])
    adjust_inventory(state, item_id, -1)
    setattr(character, slot_attr, item_id)
    clamp_resource_to_effective_cap(character)
    return True, f"{character.name} memasang {item['name']}."


def get_equipped_owners(state: GameState, item_id: str) -> List[str]:
    owners = []
    for cid in state.party_order:
        character = state.party[cid]
        if character.weapon_id == item_id or character.armor_id == item_id:
            owners.append(character.name)
    return owners


def get_character_passive_effects(character: CharacterState) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for slot in [character.weapon_id, character.armor_id]:
        if not slot:
            continue
        item = ITEMS.get(slot)
        if not item:
            continue
        passives = item.get("effects", {}).get("passives", {})
        for key, value in passives.items():
            if key == "element_boost" and isinstance(value, dict):
                dest = result.setdefault("element_boost", {})
                for elem, bonus in value.items():
                    dest[elem] = dest.get(elem, 0.0) + bonus
            else:
                result[key] = result.get(key, 0) + value
    return result


def get_character_weapon_element(character: CharacterState) -> str:
    weapon = ITEMS.get(character.weapon_id) if character.weapon_id else None
    if not weapon:
        return "NETRAL"
    return weapon.get("effects", {}).get("element", "NETRAL")


def list_equippable_items(state: GameState, char_id: str, slot_type: str) -> List[Tuple[str, Dict[str, Any], int]]:
    results: List[Tuple[str, Dict[str, Any], int]] = []
    for item_id, qty in state.inventory.items():
        if qty <= 0:
            continue
        item = ITEMS.get(item_id)
        if not item or item.get("type") != slot_type:
            continue
        allowed = item.get("allowed_users")
        if allowed and char_id not in allowed:
            continue
        results.append((item_id, item, qty))
    return results


def manual_targeting_enabled(state: GameState) -> bool:
    """Placeholder to toggle manual target selection in the future."""
    return bool(state.flags.get("MANUAL_TARGETING"))


def clear_manual_target_request(state: GameState):
    state.flags.pop("PENDING_TARGET", None)


def make_char_buff_key(char_id: str) -> str:
    return f"CHAR:{char_id}"


def make_enemy_buff_key(index: int) -> str:
    return f"ENEMY:{index}"


def get_buff_target(state: GameState, key: str):
    if not key:
        return None
    if key.startswith("CHAR:"):
        cid = key.split(":", 1)[1]
        return state.party.get(cid)
    if key.startswith("ENEMY:"):
        try:
            idx = int(key.split(":", 1)[1])
        except ValueError:
            return None
        if 0 <= idx < len(state.battle_enemies):
            return state.battle_enemies[idx]
    return None


def adjust_stat_value(target: Any, stat: str, amount: int):
    if target is None or amount == 0:
        return
    if isinstance(target, CharacterState):
        current = getattr(target, stat, None)
        if current is not None:
            setattr(target, stat, current + amount)
    elif isinstance(target, dict):
        target[stat] = target.get(stat, 0) + amount


def apply_temporary_modifier(
    state: GameState, target_key: str, stat: str, amount: int, duration: int
):
    if amount == 0 or duration <= 0:
        return
    target = get_buff_target(state, target_key)
    if target is None:
        return
    adjust_stat_value(target, stat, amount)
    buffs = state.flags.setdefault("ACTIVE_BUFFS", {})
    buffs.setdefault(target_key, []).append({
        "stat": stat,
        "amount": amount,
        "turns": duration,
    })


def cleanse_character(state: GameState, char_id: str) -> int:
    key = make_char_buff_key(char_id)
    buffs = state.flags.get("ACTIVE_BUFFS", {}).get(key, [])
    if not buffs:
        return 0
    target = state.party.get(char_id)
    kept = []
    removed = 0
    for buff in buffs:
        if buff["amount"] < 0:
            adjust_stat_value(target, buff["stat"], -buff["amount"])
            removed += 1
        else:
            kept.append(buff)
    active = state.flags.get("ACTIVE_BUFFS", {})
    if kept:
        active[key] = kept
    else:
        active.pop(key, None)
    return removed


def clear_active_buffs(state: GameState):
    active = state.flags.pop("ACTIVE_BUFFS", None)
    if not active:
        return
    for key, buffs in active.items():
        target = get_buff_target(state, key)
        if target is None:
            continue
        for buff in buffs:
            adjust_stat_value(target, buff["stat"], -buff["amount"])


# Storage in-memory
USER_STATES: Dict[int, GameState] = {}
USER_LOCKS: Dict[int, asyncio.Lock] = {}

SAVE_DIR = "saves"  # Untuk VPS, pastikan folder ini ada & bisa ditulis (chmod/chown sesuai user bot)


def get_save_path(user_id: int) -> str:
    return os.path.join(SAVE_DIR, f"{user_id}.json")


def serialize_game_state(state: GameState) -> Dict[str, Any]:
    return state.to_dict()


def save_game_state(user_id: int, state: GameState) -> bool:
    try:
        os.makedirs(SAVE_DIR, exist_ok=True)
    except Exception:
        logger.exception("Gagal membuat folder save saat menyimpan user %s", user_id)
        return False

    path = get_save_path(user_id)
    tmp_path = f"{path}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(serialize_game_state(state), f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        return True
    except Exception as exc:
        logger.exception("Gagal menyimpan progress user %s: %s", user_id, exc)
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            logger.exception("Gagal menghapus file temporary save untuk user %s", user_id)
        return False


def load_game_state(user_id: int) -> Optional[GameState]:
    path = get_save_path(user_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    except Exception as exc:
        logger.exception("Gagal memuat progress user %s: %s", user_id, exc)
        return None
    try:
        return GameState.from_dict(user_id=user_id, data=data)
    except Exception as exc:
        logger.exception("Gagal deserialisasi save user %s: %s", user_id, exc)
        return None


def get_game_state(user_id: int) -> GameState:
    state = USER_STATES.get(user_id)
    if not state:
        state = GameState(user_id=user_id)
        state.ensure_aruna()
        USER_STATES[user_id] = state
    return state


def get_user_lock(user_id: int) -> asyncio.Lock:
    lock = USER_LOCKS.get(user_id)
    if not lock:
        lock = asyncio.Lock()
        USER_LOCKS[user_id] = lock
    return lock


def xp_required_for_next_level(current_level: int) -> int:
    current_level = max(1, current_level)
    if current_level in LEVEL_XP:
        return LEVEL_XP[current_level]
    max_defined_level = max(LEVEL_XP)
    base_requirement = LEVEL_XP[max_defined_level]
    growth_step = LEVEL_XP[max_defined_level] - LEVEL_XP.get(max_defined_level - 1, 0)
    return base_requirement + growth_step * (current_level - max_defined_level)


def grant_skill_to_character(character: CharacterState, skill_id: str, logs: Optional[List[str]] = None):
    if skill_id not in SKILLS:
        return
    if skill_id in character.skills:
        return
    character.skills.append(skill_id)
    if logs is not None:
        logs.append(f"{character.name} mempelajari skill baru: {SKILLS[skill_id]['name']}!")


def apply_growth(character: CharacterState) -> Optional[Dict[str, int]]:
    growth = CHAR_GROWTH.get(character.id)
    if not growth:
        return None
    character.level += 1
    increments = {
        "hp": growth["hp"],
        "mp": growth["mp"],
        "atk": growth["atk"],
        "defense": growth["defense"],
        "mag": growth["mag"],
        "spd": growth["spd"],
        "luck": growth["luck"],
    }
    character.max_hp += increments["hp"]
    character.max_mp += increments["mp"]
    character.atk += increments["atk"]
    character.defense += increments["defense"]
    character.mag += increments["mag"]
    character.spd += increments["spd"]
    character.luck += increments["luck"]
    character.hp = get_effective_max_hp(character)
    character.mp = get_effective_max_mp(character)
    return increments


def check_level_up(state: GameState) -> List[str]:
    messages: List[str] = []
    for cid in state.party_order:
        character = state.party[cid]
        pool = state.xp_pool.get(cid, 0)
        leveled = False
        while pool >= xp_required_for_next_level(character.level):
            requirement = xp_required_for_next_level(character.level)
            pool -= requirement
            increments = apply_growth(character) or {}
            leveled = True
            inc_parts = []
            for key, label in [
                ("hp", "HP"),
                ("mp", "MP"),
                ("atk", "ATK"),
                ("defense", "DEF"),
                ("mag", "MAG"),
                ("spd", "SPD"),
            ]:
                if increments.get(key):
                    inc_parts.append(f"{label} +{increments[key]}")
            inc_text = ", ".join(inc_parts) if inc_parts else "Stat meningkat."
            messages.append(f"{character.name} naik ke Level {character.level}! {inc_text}.")
            for req_level, skill in CHAR_SKILL_UNLOCKS.get(cid, []):
                if character.level >= req_level:
                    grant_skill_to_character(character, skill, messages)
        state.xp_pool[cid] = pool
        if leveled:
            effective = get_effective_combat_stats(character)
            messages.append(
                f"Stat baru {character.name}: HP {effective['max_hp']} | MP {effective['max_mp']} | ATK {effective['atk']} | DEF {effective['defense']} | MAG {effective['mag']}"
            )
    return messages


def handle_after_battle_xp_and_level_up(state: GameState, total_xp: int, total_gold: int) -> List[str]:
    logs: List[str] = []
    for cid in state.party_order:
        state.xp_pool[cid] += total_xp
    state.gold += total_gold
    logs.append(f"Kamu mendapatkan {total_xp} XP dan {total_gold} Gold.")
    level_logs = check_level_up(state)
    if level_logs:
        logs.extend(level_logs)
    return logs


def reset_battle_flags(state: GameState):
    clear_active_buffs(state)
    for key in [
        "LIGHT_BUFF_TURNS",
        "ARUNA_LIMIT_USED",
        "CURRENT_BATTLE_AREA",
    ]:
        state.flags.pop(key, None)
    state.flags.pop("DEFENDING", None)
    state.flags.pop("MANA_SHIELD", None)
    state.battle_state = BattleTurnState()


def tick_buffs(state: GameState) -> List[str]:
    logs: List[str] = []
    active = state.flags.get("ACTIVE_BUFFS")
    if active:
        to_remove = []
        for key, buffs in active.items():
            target = get_buff_target(state, key)
            remaining = []
            for buff in buffs:
                buff["turns"] -= 1
                if buff["turns"] <= 0:
                    adjust_stat_value(target, buff["stat"], -buff["amount"])
                    if target and isinstance(target, CharacterState):
                        logs.append(
                            f"Buff {buff['stat']} pada {target.name} menghilang."
                        )
                else:
                    remaining.append(buff)
            if remaining:
                active[key] = remaining
            else:
                to_remove.append(key)
        for key in to_remove:
            active.pop(key, None)
        if not active:
            state.flags.pop("ACTIVE_BUFFS", None)
    shields = state.flags.get("MANA_SHIELD")
    if shields:
        expired: List[str] = []
        for cid in list(shields.keys()):
            shields[cid] -= 1
            if shields[cid] <= 0:
                expired.append(cid)
        for cid in expired:
            shields.pop(cid, None)
            target = state.party.get(cid)
            if target:
                logs.append(f"Mana Shield di sekitar {target.name} menghilang.")
        if not shields:
            state.flags.pop("MANA_SHIELD", None)
    if state.flags.get("LIGHT_BUFF_TURNS"):
        state.flags["LIGHT_BUFF_TURNS"] -= 1
        if state.flags["LIGHT_BUFF_TURNS"] <= 0:
            state.flags.pop("LIGHT_BUFF_TURNS", None)
            logs.append("Aura cahaya dari Aruna Core memudar.")
    return logs


def living_party_members(state: GameState) -> List[str]:
    return [cid for cid in state.party_order if state.party[cid].hp > 0]


def living_enemies(state: GameState) -> List[tuple]:
    enemies = state.battle_state.enemies or state.battle_enemies
    return [
        (idx, enemy)
        for idx, enemy in enumerate(enemies)
        if enemy.get("hp", 0) > 0
    ]


def get_first_alive_enemy(state: GameState) -> Optional[tuple]:
    alive = living_enemies(state)
    return alive[0] if alive else None


def choose_random_party_target(state: GameState) -> Optional[str]:
    alive = living_party_members(state)
    if not alive:
        return None
    return random.choice(alive)


def pick_lowest_hp_ally(state: GameState) -> Optional[CharacterState]:
    candidates = [state.party[cid] for cid in state.party_order if state.party[cid].hp > 0]
    if not candidates:
        return None
    return min(candidates, key=lambda c: c.hp / max(1, get_effective_max_hp(c)))


def find_revive_target(state: GameState) -> Optional[CharacterState]:
    for cid in state.party_order:
        member = state.party[cid]
        if member.hp <= 0:
            return member
    return None


def initialize_battle_turn_state(state: GameState):
    order = [f"CHAR:{cid}" for cid in state.party_order]
    order += [f"ENEMY:{idx}" for idx in range(len(state.battle_enemies))]
    state.battle_state = BattleTurnState(
        turn_order=order, current_turn_index=-1, enemies=state.battle_enemies
    )
    advance_to_next_actor(state)


def advance_to_next_actor(state: GameState) -> Optional[str]:
    order = state.battle_state.turn_order
    if not order:
        return None
    total = len(order)
    for _ in range(total):
        state.battle_state.current_turn_index = (
            state.battle_state.current_turn_index + 1
        ) % total
        token = order[state.battle_state.current_turn_index]
        if token.startswith("CHAR:"):
            cid = token.split(":", 1)[1]
            character = state.party.get(cid)
            if character and character.hp > 0:
                state.battle_state.active_token = token
                state.battle_state.awaiting_player_input = True
                defending = state.flags.get("DEFENDING", {})
                defending.pop(cid, None)
                if not defending:
                    state.flags.pop("DEFENDING", None)
                return token
        elif token.startswith("ENEMY:"):
            try:
                idx = int(token.split(":", 1)[1])
            except ValueError:
                continue
            if 0 <= idx < len(state.battle_enemies) and state.battle_enemies[idx]["hp"] > 0:
                state.battle_state.active_token = token
                state.battle_state.awaiting_player_input = False
                return token
    return None


def check_battle_outcome(state: GameState) -> Optional[str]:
    if not living_enemies(state):
        return "WIN"
    if not living_party_members(state):
        return "LOSE"
    return None


async def resolve_battle_outcome(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState, log: List[str]
) -> bool:
    outcome = check_battle_outcome(state)
    if not outcome:
        return False
    if outcome == "WIN":
        total_xp = sum(enemy.get("xp", 0) for enemy in state.battle_enemies)
        total_gold = sum(enemy.get("gold", 0) for enemy in state.battle_enemies)
        state.in_battle = False
        state.battle_enemies = []
        state.flags["LAST_BATTLE_RESULT"] = "WIN"
        reward_logs = handle_after_battle_xp_and_level_up(state, total_xp, total_gold)
        if reward_logs:
            log.extend(reward_logs)
        drop_logs = grant_battle_drops(state)
        if drop_logs:
            log.append("Kamu mendapatkan:")
            for entry in drop_logs:
                log.append(f"- {entry}")
        else:
            log.append("Kamu tidak menemukan apa-apa.")
        await end_battle_and_return(
            update,
            context,
            state,
            log_text="\n".join(log),
        )
        return True
    # LOSE
    for cid in state.party_order:
        member = state.party[cid]
        member.hp = max(1, get_effective_max_hp(member) // 3)
    state.in_battle = False
    state.battle_enemies = []
    log.append("Seluruh party tumbang! Kamu kalah dalam pertarungan ini...")
    state.flags["LAST_BATTLE_RESULT"] = "LOSE"
    await end_battle_and_return(update, context, state, log_text="\n".join(log))
    return True


def enemy_take_turn(state: GameState, enemy_index: int) -> List[str]:
    log: List[str] = []
    enemies = state.battle_state.enemies or state.battle_enemies
    if enemy_index < 0 or enemy_index >= len(enemies):
        return log
    enemy = enemies[enemy_index]
    if enemy.get("hp", 0) <= 0:
        return log
    target_id = choose_random_party_target(state)
    if not target_id:
        return log
    target = state.party[target_id]
    target_def = get_effective_stat(target, "defense")
    base = enemy["atk"] - target_def // 2
    if base < 1:
        base = 1
    dmg = max(1, int(base * random.uniform(0.8, 1.1)))
    defending = state.flags.get("DEFENDING", {})
    if defending.get(target_id):
        dmg = max(1, dmg // 2)
        defending.pop(target_id, None)
        if not defending:
            state.flags.pop("DEFENDING", None)
    dmg = apply_mana_shield_absorption(state, target_id, dmg, log)
    if dmg <= 0:
        return log
    target.hp -= dmg
    log.append(f"{enemy['name']} menyerang {target.name} dan memberikan {dmg} damage!")
    if target.hp <= 0:
        target.hp = 0
        log.append(f"{target.name} tumbang!")
    return log


async def conclude_player_turn(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState, log: List[str]
):
    if await resolve_battle_outcome(update, context, state, log):
        return
    next_token = advance_to_next_actor(state)
    if not next_token:
        await send_battle_state(update, context, state, intro=False, extra_text="\n".join(log))
        return
    enemy_phase = False
    while next_token and next_token.startswith("ENEMY:"):
        enemy_phase = True
        try:
            enemy_index = int(next_token.split(":", 1)[1])
        except ValueError:
            enemy_index = -1
        log.extend(enemy_take_turn(state, enemy_index))
        if await resolve_battle_outcome(update, context, state, log):
            return
        next_token = advance_to_next_actor(state)
    if enemy_phase:
        buff_logs = tick_buffs(state)
        if buff_logs:
            log.extend(buff_logs)
    await send_battle_state(update, context, state, intro=False, extra_text="\n".join(log))


async def send_skill_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState, character: CharacterState
):
    skills = character.skills
    if not skills:
        await send_battle_state(
            update,
            context,
            state,
            intro=False,
            extra_text=f"{character.name} belum mempelajari skill apa pun.",
        )
        return
    choices = [(SKILLS[s]["name"], f"USE_SKILL|{character.id}|{s}") for s in skills]
    choices.append(("Kembali", f"BATTLE_MENU|{character.id}"))
    keyboard = make_keyboard(choices)
    text = battle_status_text(state) + f"\n\nPilih skill {character.name}:"
    query = update.callback_query
    if query:
        await query.edit_message_text(text=text, reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(text=text, reply_markup=keyboard)


async def send_battle_item_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState, char_id: Optional[str] = None
):
    if not char_id:
        token = state.battle_state.active_token
        if token and token.startswith("CHAR:"):
            char_id = token.split(":", 1)[1]
    consumables = [
        (item_id, qty)
        for item_id, qty in state.inventory.items()
        if qty > 0 and ITEMS.get(item_id, {}).get("type") == "consumable"
    ]
    if not consumables:
        await send_battle_state(
            update,
            context,
            state,
            intro=False,
            extra_text="Kamu tidak punya item yang bisa dipakai.",
        )
        return
    buttons = []
    lines = ["Pilih item yang akan dipakai:"]
    for item_id, qty in consumables:
        item = ITEMS[item_id]
        lines.append(f"- {item['name']} x{qty}")
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{item['name']} (x{qty})", callback_data=f"USE_ITEM|{item_id}"
                )
            ]
        )
    back_target = f"BATTLE_MENU|{char_id}" if char_id else "BATTLE_BACK"
    buttons.append([InlineKeyboardButton("⬅ Kembali", callback_data=back_target)])
    query = update.callback_query
    if query:
        await query.edit_message_text(
            text="\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif update.message:
        await update.message.reply_text(
            text="\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons)
        )


def apply_item_effects_in_battle(
    state: GameState, user_char_id: str, item_id: str
) -> Tuple[bool, List[str]]:
    item = ITEMS.get(item_id)
    if not item:
        return False, ["Item tidak dikenal."]
    effects = item.get("effects", {})
    target_mode = effects.get("target", "single")
    targets: List[CharacterState] = []
    if target_mode == "party":
        targets = [state.party[cid] for cid in state.party_order if state.party[cid].hp > 0]
    else:
        actor = state.party.get(user_char_id)
        if actor:
            targets = [actor]
    if not targets:
        return False, ["Tidak ada target yang bisa menerima efek item."]
    logs: List[str] = []
    hp_restore = effects.get("hp_restore", 0)
    mp_restore = effects.get("mp_restore", 0)
    for target in targets:
        if hp_restore:
            before = target.hp
            target.hp = min(get_effective_max_hp(target), target.hp + hp_restore)
            logs.append(f"{target.name} memulihkan {target.hp - before} HP.")
        if mp_restore:
            before_mp = target.mp
            target.mp = min(get_effective_max_mp(target), target.mp + mp_restore)
            logs.append(f"{target.name} memulihkan {target.mp - before_mp} MP.")
    if not logs:
        logs.append("Tidak ada efek yang terlihat.")
    return True, logs


async def process_use_item(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState, item_id: str
):
    token = state.battle_state.active_token
    if not token or not token.startswith("CHAR:"):
        await send_battle_state(update, context, state)
        return
    char_id = token.split(":", 1)[1]
    item = ITEMS.get(item_id)
    if not item or item.get("type") != "consumable":
        await send_battle_state(
            update, context, state, intro=False, extra_text="Item itu tidak bisa dipakai sekarang."
        )
        return
    qty = state.inventory.get(item_id, 0)
    if qty <= 0:
        await send_battle_state(
            update, context, state, intro=False, extra_text="Kamu tidak memiliki item itu."
        )
        return
    success, effect_logs = apply_item_effects_in_battle(state, char_id, item_id)
    if not success:
        await send_battle_state(update, context, state, intro=False, extra_text="\n".join(effect_logs))
        return
    adjust_inventory(state, item_id, -1)
    log = [f"{state.party[char_id].name} menggunakan {item['name']}."] + effect_logs
    await conclude_player_turn(update, context, state, log)


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
        "weakness": list(base.get("weakness", [])),
        "resist": list(base.get("resist", [])),
        "area": base.get("area", "UNKNOWN"),
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
    state.flags["CURRENT_BATTLE_AREA"] = enemy.get("area")
    initialize_battle_turn_state(state)
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
        "weakness": list(base.get("weakness", [])),
        "resist": list(base.get("resist", [])),
        "area": base.get("area", area),
        "id": base["name"].upper().replace(" ", "_"),
    }


def compute_elemental_multiplier(
    element: str,
    target_weakness: Optional[List[str]],
    target_resist: Optional[List[str]],
    passives: Optional[Dict[str, Any]] = None,
) -> Tuple[float, bool, bool]:
    multiplier = 1.0
    hit_weakness = bool(element and target_weakness and element in target_weakness)
    hit_resist = bool(element and target_resist and element in target_resist)
    if hit_weakness:
        multiplier *= 1.5
    if hit_resist:
        multiplier *= 0.75
    if passives:
        boost = passives.get("element_boost", {})
        if element in boost:
            multiplier *= 1 + boost[element]
    return multiplier, hit_weakness, hit_resist


def compute_passive_damage_bonus(
    passives: Dict[str, Any], target_element: Optional[str], used_element: str
) -> float:
    multiplier = 1.0
    if not passives:
        return multiplier
    bonus_vs = passives.get("bonus_vs_element", {})
    if target_element and target_element in bonus_vs:
        multiplier *= 1 + bonus_vs[target_element]
    if used_element == "CAHAYA":
        multiplier *= 1 + passives.get("light_skill_amp", 0)
    return multiplier


def calc_physical_damage(
    attacker: CharacterState,
    target_def: int,
    power: float = 1.0,
    element: str = "NETRAL",
    target_weakness: Optional[List[str]] = None,
    target_resist: Optional[List[str]] = None,
    target_element: Optional[str] = None,
) -> Tuple[int, bool, bool]:
    attacker_atk = get_effective_stat(attacker, "atk")
    base = attacker_atk - target_def // 2
    if base < 1:
        base = 1
    # variasi kecil
    base = int(base * random.uniform(0.9, 1.1))
    passives = get_character_passive_effects(attacker)
    element_multiplier, hit_weakness, hit_resist = compute_elemental_multiplier(
        element, target_weakness, target_resist, passives
    )
    passive_bonus = compute_passive_damage_bonus(passives, target_element, element)
    base = int(base * power * element_multiplier * passive_bonus)
    return max(1, base), hit_weakness, hit_resist


def calc_magic_damage(
    attacker: CharacterState,
    target_def: int,
    power: float,
    element: str = "NETRAL",
    target_weakness: Optional[List[str]] = None,
    target_resist: Optional[List[str]] = None,
    target_element: Optional[str] = None,
) -> Tuple[int, bool, bool]:
    attacker_mag = get_effective_stat(attacker, "mag")
    base = int((attacker_mag - target_def / 3) * power)
    if base < 1:
        base = 1
    base = int(base * random.uniform(0.9, 1.1))
    passives = get_character_passive_effects(attacker)
    element_multiplier, hit_weakness, hit_resist = compute_elemental_multiplier(
        element, target_weakness, target_resist, passives
    )
    passive_bonus = compute_passive_damage_bonus(passives, target_element, element)
    base = int(base * element_multiplier * passive_bonus)
    return max(1, base), hit_weakness, hit_resist


def calc_heal_amount(caster: CharacterState, power: float) -> int:
    base = int(get_effective_stat(caster, "mag") * power)
    if base < 1:
        base = 1
    return base


def apply_mana_shield_absorption(
    state: GameState, target_id: str, damage: int, log: List[str]
) -> int:
    if damage <= 0:
        return 0
    shields = state.flags.get("MANA_SHIELD")
    if not shields or target_id not in shields:
        return damage
    target = state.party.get(target_id)
    if not target:
        return damage
    absorb = min(target.mp, damage)
    if absorb > 0:
        target.mp -= absorb
        damage -= absorb
        log.append(f"Mana Shield menyerap {absorb} damage dari {target.name}.")
    if damage <= 0:
        log.append(f"{target.name} terlindungi sepenuhnya oleh Mana Shield!")
        return 0
    return damage


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
    state.flags["CURRENT_BATTLE_AREA"] = area
    initialize_battle_turn_state(state)
    await send_battle_state(update, context, state, intro=True)


def battle_status_text(state: GameState) -> str:
    lines = ["=== BATTLE ==="]
    lines.append("Party:")
    for cid in state.party_order:
        c = state.party[cid]
        effective_hp = get_effective_max_hp(c)
        effective_mp = get_effective_max_mp(c)
        lines.append(f"- {c.name} Lv{c.level} HP {c.hp}/{effective_hp} MP {c.mp}/{effective_mp}")
    token = state.battle_state.active_token
    if token:
        if token.startswith("CHAR:"):
            cid = token.split(":", 1)[1]
            actor = state.party.get(cid)
            if actor:
                lines.append(f"\nGiliran saat ini: {actor.name}")
        elif token.startswith("ENEMY:"):
            try:
                idx = int(token.split(":", 1)[1])
            except ValueError:
                idx = -1
            if 0 <= idx < len(state.battle_enemies):
                enemy = state.battle_enemies[idx]
                lines.append(f"\nGiliran saat ini: {enemy['name']}")
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

    keyboard = None
    token = state.battle_state.active_token
    if token and token.startswith("CHAR:"):
        cid = token.split(":", 1)[1]
        keyboard = make_keyboard(
            [
                ("⚔ Serang", f"BATTLE_ATTACK|{cid}"),
                ("✨ Skill", f"BATTLE_SKILL_MENU|{cid}"),
                ("🎒 Item", f"BATTLE_ITEM|{cid}"),
                ("🛡 Bertahan", f"BATTLE_DEFEND|{cid}"),
                ("🏃 Kabur", f"BATTLE_RUN|{cid}"),
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
    action_parts = action.split("|")
    action_key = action_parts[0]
    requested_char = action_parts[1] if len(action_parts) > 1 else None

    token = state.battle_state.active_token
    if not token or not token.startswith("CHAR:"):
        token = advance_to_next_actor(state)
    if not token or not token.startswith("CHAR:"):
        await send_battle_state(update, context, state)
        return

    active_char_id = token.split(":", 1)[1]
    if requested_char and requested_char != active_char_id:
        await send_battle_state(update, context, state)
        return

    character = state.party[active_char_id]

    if action_key in {"BATTLE_MENU", "BATTLE_BACK"}:
        await send_battle_state(update, context, state)
        return

    if action_key == "BATTLE_SKILL_MENU":
        await send_skill_menu(update, context, state, character)
        return
    if action_key == "BATTLE_ITEM":
        await send_battle_item_menu(update, context, state, active_char_id)
        return

    log: List[str] = []

    if action_key == "BATTLE_ATTACK":
        target_info = get_first_alive_enemy(state)
        if not target_info:
            if await resolve_battle_outcome(update, context, state, log):
                return
        else:
            idx, enemy = target_info
            weapon_element = get_character_weapon_element(character)
            dmg, hit_weakness, hit_resist = calc_physical_damage(
                character,
                enemy["defense"],
                element=weapon_element,
                target_weakness=enemy.get("weakness"),
                target_resist=enemy.get("resist"),
                target_element=enemy.get("element"),
            )
            enemy["hp"] -= dmg
            log.append(
                f"{character.name} menyerang {enemy['name']} dan memberikan {dmg} damage!"
            )
            if hit_weakness:
                log.append("Itu serangan yang sangat efektif!")
            if hit_resist:
                log.append("Musuh tampaknya menahan serangan itu.")

    elif action_key == "BATTLE_DEFEND":
        defend_flags = state.flags.setdefault("DEFENDING", {})
        defend_flags[active_char_id] = True
        log.append(
            f"{character.name} mengambil posisi bertahan untuk mengurangi damage sementara."
        )

    elif action_key == "BATTLE_RUN":
        if active_char_id != "ARUNA":
            await send_battle_state(
                update,
                context,
                state,
                intro=False,
                extra_text="Hanya Aruna yang bisa memutuskan untuk kabur!",
            )
            return
        chance = 0.5 + character.luck * 0.01
        if random.random() < chance:
            log.append("Kamu berhasil kabur dari pertarungan.")
            state.in_battle = False
            state.battle_enemies = []
            state.flags["LAST_BATTLE_RESULT"] = "ESCAPE"
            await end_battle_and_return(update, context, state, log_text="\n".join(log))
            return
        log.append("Kamu gagal kabur!")

    else:
        log.append("Aksi belum dikenal dalam sistem battle ini.")
        await send_battle_state(update, context, state, intro=False, extra_text="\n".join(log))
        return

    await conclude_player_turn(update, context, state, log)


async def process_use_skill(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState, user: str, skill_id: str
):
    token = state.battle_state.active_token
    if not token or not token.startswith("CHAR:") or token.split(":", 1)[1] != user:
        await send_battle_state(update, context, state)
        return
    character = state.party[user]
    skill = SKILLS.get(skill_id)
    if not skill:
        await send_battle_state(update, context, state)
        return

    if skill_id == "ARUNA_CORE_AWAKENING" and state.flags.get("ARUNA_LIMIT_USED"):
        await send_battle_state(
            update,
            context,
            state,
            intro=False,
            extra_text="Aruna Core sudah bangkit sekali di pertarungan ini!",
        )
        return

    if character.mp < skill.get("mp_cost", 0):
        await send_battle_state(
            update,
            context,
            state,
            intro=False,
            extra_text=f"{character.name} tidak punya MP yang cukup untuk menggunakan {skill['name']}!",
        )
        return

    character.mp -= skill.get("mp_cost", 0)
    log: List[str] = []
    skill_type = skill.get("type")
    element = skill.get("element", "NETRAL")

    if skill_type in ("PHYS", "MAG"):
        target_info = get_first_alive_enemy(state)
        if not target_info:
            character.mp += skill.get("mp_cost", 0)
            if await resolve_battle_outcome(update, context, state, log):
                return
        else:
            idx, enemy = target_info
            if skill_type == "PHYS":
                dmg, hit_weakness, hit_resist = calc_physical_damage(
                    character,
                    enemy["defense"],
                    skill.get("power", 1.0),
                    element,
                    enemy.get("weakness"),
                    enemy.get("resist"),
                    enemy.get("element"),
                )
            else:
                dmg, hit_weakness, hit_resist = calc_magic_damage(
                    character,
                    enemy["defense"],
                    skill.get("power", 1.0),
                    element,
                    enemy.get("weakness"),
                    enemy.get("resist"),
                    enemy.get("element"),
                )
            if element == "CAHAYA" and state.flags.get("LIGHT_BUFF_TURNS"):
                dmg = int(dmg * 1.2)
            enemy["hp"] -= dmg
            log.append(f"{character.name} menggunakan {skill['name']}! {enemy['name']} menerima {dmg} damage.")
            if hit_weakness:
                log.append("Itu serangan yang sangat efektif!")
            if hit_resist:
                log.append("Musuh tampaknya menahan serangan itu.")
    elif skill_type == "HEAL_SINGLE":
        target = pick_lowest_hp_ally(state)
        if not target:
            character.mp += skill.get("mp_cost", 0)
            log.append("Tidak ada target untuk disembuhkan.")
            await send_battle_state(update, context, state, extra_text="\n".join(log))
            return
        heal_amount = calc_heal_amount(character, skill.get("power", 0.3))
        before = target.hp
        target.hp = min(get_effective_max_hp(target), target.hp + heal_amount)
        log.append(
            f"{character.name} menyembuhkan {target.name} sebanyak {target.hp - before} HP dengan {skill['name']}!"
        )
    elif skill_type == "HEAL_ALL":
        total = []
        for cid in state.party_order:
            member = state.party[cid]
            if member.hp <= 0:
                continue
            heal_amount = calc_heal_amount(character, skill.get("power", 0.25))
            before = member.hp
            member.hp = min(get_effective_max_hp(member), member.hp + heal_amount)
            total.append(f"{member.name}+{member.hp - before}HP")
        log.append(f"{character.name} menyalurkan {skill['name']}! ({', '.join(total)})")
    elif skill_type == "BUFF_DEF_SELF":
        buffs = skill.get("buffs", {"defense": 3})
        duration = skill.get("duration", 3)
        for stat, amount in buffs.items():
            apply_temporary_modifier(state, make_char_buff_key(user), stat, amount, duration)
        log.append(
            f"{character.name} memperkuat pertahanan dengan {skill['name']}! DEF meningkat selama {duration} turn."
        )
    elif skill_type == "BUFF_DEF_SINGLE":
        target = pick_lowest_hp_ally(state) or character
        buffs = skill.get("buffs", {"defense": 3})
        duration = skill.get("duration", 3)
        for stat, amount in buffs.items():
            apply_temporary_modifier(
                state, make_char_buff_key(target.id), stat, amount, duration
            )
        log.append(
            f"{character.name} menyalurkan {skill['name']} pada {target.name}! Pertahanan meningkat selama {duration} turn."
        )
    elif skill_type == "LIMIT_HEAL":
        state.flags["ARUNA_LIMIT_USED"] = True
        state.flags["LIGHT_BUFF_TURNS"] = 3
        total = []
        for cid in state.party_order:
            member = state.party[cid]
            heal_amount = max(1, int(get_effective_max_hp(member) * 0.4))
            before = member.hp
            member.hp = min(get_effective_max_hp(member), member.hp + heal_amount)
            total.append(f"{member.name}+{member.hp - before}HP")
        log.append(
            "Aruna Core Awakening memulihkan party dan meningkatkan serangan cahaya! ("
            + ", ".join(total)
            + ")"
        )
    elif skill_type == "BUFF_TEAM":
        buffs = skill.get("buffs", {})
        duration = skill.get("duration", 3)
        affected = []
        for cid in state.party_order:
            member = state.party[cid]
            if member.hp <= 0:
                continue
            for stat, amount in buffs.items():
                apply_temporary_modifier(state, make_char_buff_key(cid), stat, amount, duration)
            affected.append(member.name)
        log.append(
            f"{character.name} menyalurkan {skill['name']}! Buff menyelimuti {', '.join(affected)} selama {duration} turn."
        )
    elif skill_type == "DEBUFF_ENEMY":
        target_info = get_first_alive_enemy(state)
        if not target_info:
            character.mp += skill.get("mp_cost", 0)
            log.append("Tidak ada musuh untuk didebuff.")
            await send_battle_state(update, context, state, extra_text="\n".join(log))
            return
        idx, enemy = target_info
        duration = skill.get("duration", 3)
        for stat, amount in skill.get("debuffs", {}).items():
            apply_temporary_modifier(state, make_enemy_buff_key(idx), stat, amount, duration)
        log.append(
            f"{character.name} melempar {skill['name']}! Statistik {enemy['name']} melemah selama {duration} turn."
        )
    elif skill_type == "CLEANSE":
        target_mode = skill.get("target", "party")
        total_removed = 0
        if target_mode == "party":
            for cid in state.party_order:
                total_removed += cleanse_character(state, cid)
        else:
            total_removed = cleanse_character(state, user)
        if total_removed:
            log.append(f"{character.name} membersihkan {total_removed} debuff dengan {skill['name']}!")
        else:
            log.append(f"{character.name} menggunakan {skill['name']}, tetapi tidak ada debuff yang perlu dibersihkan.")
    elif skill_type == "BUFF_SELF":
        duration = skill.get("duration", 3)
        for stat, amount in skill.get("buffs", {}).items():
            apply_temporary_modifier(state, make_char_buff_key(user), stat, amount, duration)
        for stat, amount in skill.get("penalties", {}).items():
            apply_temporary_modifier(state, make_char_buff_key(user), stat, amount, duration)
        log.append(
            f"{character.name} memfokuskan energi melalui {skill['name']} untuk {duration} turn."
        )
    elif skill_type == "BUFF_SPECIAL":
        duration = skill.get("duration", 3)
        shields = state.flags.setdefault("MANA_SHIELD", {})
        shields[user] = duration
        log.append(
            f"{character.name} menciptakan {skill['name']}! Damage akan menguras MP lebih dulu selama {duration} turn."
        )
    elif skill_type == "REVIVE":
        target = find_revive_target(state)
        if not target:
            character.mp += skill.get("mp_cost", 0)
            log.append("Tidak ada ally yang butuh dihidupkan.")
            await send_battle_state(update, context, state, extra_text="\n".join(log))
            return
        ratio = skill.get("revive_ratio", 0.4)
        target.hp = max(1, int(get_effective_max_hp(target) * ratio))
        log.append(f"{character.name} menghidupkan {target.name} dengan {skill['name']}! HP pulih {target.hp}.")
    else:
        log.append(f"{skill['name']} belum bisa digunakan di sistem battle sederhana ini.")
        await send_battle_state(update, context, state, intro=False, extra_text="\n".join(log))
        return

    await conclude_player_turn(update, context, state, log)


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

STORY_BATTLE_ROUTES = {
    "BATTLE_TUTORIAL_1": {
        "type": "random",
        "set_scene": "CH0_S3",
    },
    "BATTLE_SIAK_GATE": {
        "type": "story",
        "set_scene": "CH1_GATE_ALERT",
        "enemy": "GATE_SPIRIT",
        "return_scene": "CH1_GATE_AFTER",
    },
    "BATTLE_UMAR_HERB": {
        "type": "story",
        "set_scene": "SQ_UMAR_MINIDUNGEON",
        "enemy": "HERB_GUARDIAN",
        "return_scene": "SQ_UMAR_HEAL",
    },
    "BATTLE_RENGAT_GOLEM": {
        "type": "story",
        "set_scene": "CH2_GOLEM_ALERT",
        "enemy": "CORRUPTED_FOREST_GOLEM",
        "return_scene": "CH2_GOLEM_AFTER",
    },
    "BATTLE_REZA_SEAL": {
        "type": "story",
        "set_scene": "SQ_REZA_MASTER",
        "enemy": "SEAL_WARDEN",
        "return_scene": "SQ_REZA_RESOLVE",
    },
    "BATTLE_HOUND_OF_VOID": {
        "type": "story",
        "set_scene": "CH5_FLOOR2",
        "enemy": "HOUND_OF_VOID",
        "return_scene": "CH5_FLOOR2_AFTER",
    },
    "BATTLE_VOID_SENTINEL": {
        "type": "story",
        "set_scene": "CH5_FLOOR4",
        "enemy": "VOID_SENTINEL",
        "return_scene": "CH5_FLOOR4_AFTER",
    },
    "BATTLE_FEBRI": {
        "type": "story",
        "set_scene": "CH5_FLOOR5",
        "enemy": "FEBRI_LORD",
        "return_scene": "CH5_FINAL_WIN",
        "loss_scene": "BAD_ENDING",
    },
    "BATTLE_HARSAN_SENTINEL": {
        "type": "story",
        "set_scene": "SQ_HARSAN_SHRINE_CORE",
        "enemy": "LUMINAR_SENTINEL",
        "return_scene": "SQ_HARSAN_BLADE_VISION",
    },
    "BATTLE_ABYSS_SHADE": {
        "type": "story",
        "set_scene": "SQ_HARSAN_SHRINE_PILLARS",
        "enemy": "ABYSS_SHADE",
        "return_scene": "SQ_HARSAN_SHRINE_CORE",
    },
}


def apply_flags_from_data(state: GameState, flags: Optional[Dict[str, List[str]]]) -> None:
    if not flags:
        return
    for flag in flags.get("set", []):
        state.flags[flag] = True
    for flag in flags.get("unset", []):
        state.flags[flag] = False


def highest_party_level(state: GameState) -> int:
    return max((c.level for c in state.party.values()), default=1)


def requirements_met(requirements: Optional[Dict[str, Any]], state: GameState) -> bool:
    if not requirements:
        return True
    req_flags = requirements.get("flags") or []
    for flag in req_flags:
        if not state.flags.get(flag):
            return False
    min_level = requirements.get("min_level")
    if isinstance(min_level, int) and highest_party_level(state) < min_level:
        return False
    return True


def find_choice_by_callback(scene_data: Optional[Dict[str, Any]], callback_data: str) -> Optional[Dict[str, Any]]:
    if not scene_data:
        return None
    for choice in scene_data.get("choices", []):
        possible = {
            choice.get("callback_data"),
            choice.get("next_scene"),
            choice.get("next"),
            choice.get("command"),
            choice.get("battle"),
        }
        if callback_data in possible:
            return choice
    return None


def build_default_choice() -> Dict[str, Any]:
    return {
        "label": "Lanjut",
        "next_scene": "GO_TO_WORLD_MAP",
        "battle": None,
        "command": "GO_TO_WORLD_MAP",
        "flags": {"set": [], "unset": []},
        "requirements": {"flags": [], "min_level": None},
        "callback_data": "GO_TO_WORLD_MAP",
    }


async def send_scene_not_found(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState
) -> None:
    text = "Maaf, terjadi kesalahan pada cerita. Scene tidak ditemukan."
    keyboard = make_keyboard([("Kembali ke map", "GO_TO_WORLD_MAP")])
    query = update.callback_query
    if query:
        await query.edit_message_text(text=text, reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(text=text, reply_markup=keyboard)
    await send_world_map(update, context, state)


async def execute_story_command(
    command: Optional[str],
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: GameState,
    extra_text: str = "",
) -> bool:
    if not command:
        return False
    if command in {"GO_TO_WORLD_MAP", "WORLD_MAP"}:
        state.main_progress = "WORLD"
        await send_world_map(update, context, state)
        return True
    if command == "SIAK_CITY_MENU":
        state.location = "SIAK"
        await send_city_menu(update, context, state)
        return True
    if command == "SIAK_CITY_MENU_AFTER_UMAR":
        state.location = "SIAK"
        state.add_umar()
        await send_city_menu(
            update, context, state, extra_text="Umar kini menjadi anggota party."
        )
        return True
    if command == "SET_MAIN_RENGAT":
        state.main_progress = "Menuju Rengat (Lv 5+)"
        state.flags["SIAK_GATE_EVENT_DONE"] = True
        await send_world_map(update, context, state)
        return True
    if command == "SET_MAIN_PEKANBARU":
        state.main_progress = "Menuju Pekanbaru (Lv 8+)"
        await send_world_map(update, context, state)
        return True
    if command == "SET_MAIN_KAMPAR":
        state.main_progress = "Menuju Kampar (Lv 12+)"
        state.flags["PEKANBARU_RUMOR_DONE"] = True
        aruna = state.party.get("ARUNA")
        if aruna:
            grant_skill_to_character(aruna, "ARUNA_CORE_AWAKENING")
        await send_world_map(update, context, state)
        return True
    if command == "SQ_HARSAN_SHRINE":
        state.scene_id = "SQ_HARSAN_BLADE_SHRINE"
        await send_scene(update, context, state)
        return True
    if command == "ADD_REZA_PARTY":
        state.add_reza()
        state.scene_id = "CH2_REZA_JOINS"
        await send_scene(update, context, state)
        return True
    if command == "COMPLETE_UMAR_QUEST":
        state.flags["UMAR_QUEST_DONE"] = True
        umar = state.party.get("UMAR")
        if umar:
            grant_skill_to_character(umar, "SAFIYA_GRACE")
        state.scene_id = "SQ_UMAR_REWARD"
        await send_scene(
            update,
            context,
            state,
            extra_text=extra_text or "Umar mempelajari skill baru: Grace Safiya!",
        )
        return True
    if command == "COMPLETE_REZA_QUEST":
        state.flags["REZA_QUEST_DONE"] = True
        reza = state.party.get("REZA")
        if reza:
            grant_skill_to_character(reza, "MASTER_LEGACY")
        state.scene_id = "SQ_REZA_REWARD"
        await send_scene(
            update,
            context,
            state,
            extra_text=extra_text or "Reza mempelajari skill baru: Warisan Sang Guru!",
        )
        return True
    return False


async def handle_story_battle_trigger(
    battle_key: Optional[str],
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: GameState,
    next_scene: Optional[str] = None,
) -> bool:
    if not battle_key:
        return False
    route = STORY_BATTLE_ROUTES.get(battle_key)
    if not route:
        return False
    set_scene = route.get("set_scene")
    if set_scene:
        state.scene_id = set_scene
    if route.get("type") == "random":
        await start_random_battle(update, context, state)
        return True
    enemy = route.get("enemy")
    return_scene = next_scene or route.get("return_scene")
    if not enemy or not return_scene:
        return False
    await start_story_battle(
        update,
        context,
        state,
        enemy,
        return_scene,
        loss_scene=route.get("loss_scene"),
    )
    return True

def handle_scene_side_effects(state: GameState) -> str:
    extras: List[str] = []
    if state.scene_id == "SQ_HARSAN_BLADE_VISION" and not state.flags.get("WEAPON_QUEST_DONE"):
        state.flags["QUEST_WEAPON_DONE"] = True
        state.flags["WEAPON_QUEST_DONE"] = True
        state.flags["QUEST_WEAPON_STARTED"] = True
        state.flags["WEAPON_QUEST_STARTED"] = True
        adjust_inventory(state, "HARSAN_LEGACY_BLADE", 1)
        success, equip_msg = equip_item(state, "ARUNA", "HARSAN_LEGACY_BLADE")
        if not success:
            equip_msg = "Pedang baru tersimpan di tas."
        aruna = state.party.get("ARUNA")
        if aruna:
            grant_skill_to_character(aruna, "LEGACY_RADIANCE")
        extras.append(
            "Pedang warisan keluarga Harsan bangkit kembali saat bersatu dengan Aruna Core!\n"
            + equip_msg
            + "\nSkill baru diperoleh: Legacy Radiance."
        )
    if state.scene_id == "CH5_FLOOR5" and (
        state.flags.get("WEAPON_QUEST_DONE") or state.flags.get("QUEST_WEAPON_DONE")
    ):
        aruna = state.party.get("ARUNA")
        wielding = aruna and aruna.weapon_id == "HARSAN_LEGACY_BLADE"
        if wielding:
            extras.append(
                "Febri menatap pedangmu: \"Itu bilah Harsan... cahaya yang pernah mengkhianatiku.\" Aura Abyss-nya bergolak."
            )
        else:
            extras.append(
                "Aura pedang warisan dalam tasmu membuat Febri gelisah, seolah ia merasakan tatapan Harsan dari kejauhan."
            )
    if state.scene_id == "CH5_FINAL_WIN":
        if state.flags.get("UMAR_QUEST_DONE") and state.flags.get("REZA_QUEST_DONE"):
            extras.append(
                "Cahaya Aruna Core beresonansi dengan niat Umar dan Reza yang sudah pulih. Jalan menuju TRUE ENDING terbuka."
            )
        else:
            extras.append(
                "Ada gema yang belum tuntas. Selesaikan Warisan Safiya dan Suara dari Segel untuk menemukan akhir sejati."
            )
    return "\n\n".join(extras)


async def send_scene(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: GameState,
    extra_text: str = "",
):
    reward_text = handle_scene_side_effects(state)
    data = get_scene(state.scene_id)
    if not data:
        await send_scene_not_found(update, context, state)
        return

    apply_flags_from_data(state, data.get("flags"))

    if not requirements_met(data.get("requirements"), state):
        text = "Maaf, terjadi kesalahan pada cerita. Syarat scene belum terpenuhi."
        keyboard = make_keyboard([("Kembali ke map", "GO_TO_WORLD_MAP")])
        query = update.callback_query
        if query:
            await query.edit_message_text(text=text, reply_markup=keyboard)
        elif update.message:
            await update.message.reply_text(text=text, reply_markup=keyboard)
        await send_world_map(update, context, state)
        return

    text_lines = data.get("text", []) or []
    if isinstance(text_lines, str):
        text_lines = text_lines.split("\n")
    if not text_lines:
        text_lines = ["Maaf, terjadi kesalahan pada cerita. Teks scene kosong."]
    text = "\n".join(text_lines)
    if reward_text:
        extra_text = reward_text + ("\n\n" + extra_text if extra_text else "")
    if extra_text:
        text = extra_text + "\n\n" + text

    choices_raw = data.get("choices", []) or []
    visible_choices: List[Tuple[str, str]] = []
    for choice in choices_raw:
        if not requirements_met(choice.get("requirements"), state):
            continue
        callback_data = choice.get("callback_data")
        label = choice.get("label") or "Lanjut"
        if callback_data:
            visible_choices.append((label, callback_data))
    if not visible_choices:
        default_choice = build_default_choice()
        visible_choices.append((default_choice["label"], default_choice["callback_data"]))
    keyboard = make_keyboard(visible_choices)
    query = update.callback_query
    if query:
        await query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text=text, reply_markup=keyboard)


async def render_scene(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: GameState,
    scene_id: str,
    extra_text: str = "",
):
    state.scene_id = scene_id
    await send_scene(update, context, state, extra_text=extra_text)


async def handle_scene_choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: GameState,
    choice_data: str,
):
    scene_data = get_scene(state.scene_id)
    selected_choice = find_choice_by_callback(scene_data, choice_data)

    if selected_choice:
        if not requirements_met(selected_choice.get("requirements"), state):
            await send_scene(
                update,
                context,
                state,
                extra_text="Pilihan ini belum bisa dipilih. Syarat belum terpenuhi.",
            )
            return
        apply_flags_from_data(state, selected_choice.get("flags"))
        battle_key = selected_choice.get("battle") or (
            choice_data if choice_data.startswith("BATTLE_") else None
        )
        next_scene = selected_choice.get("next_scene")
        command = selected_choice.get("command")

        handled_battle = await handle_story_battle_trigger(
            battle_key, update, context, state, next_scene=next_scene
        )
        if handled_battle:
            return

        handled_command = await execute_story_command(
            command or next_scene or choice_data, update, context, state
        )
        if handled_command:
            return

        target_scene = next_scene or choice_data
        if target_scene in SCENES:
            await render_scene(update, context, state, target_scene)
            return

        await send_scene_not_found(update, context, state)
        return

    battle_key = choice_data if choice_data.startswith("BATTLE_") else None
    if await handle_story_battle_trigger(battle_key, update, context, state):
        return

    if await execute_story_command(choice_data, update, context, state):
        return

    if choice_data == "TRUE_ENDING_TRIGGER":
        has_true = state.flags.get("UMAR_QUEST_DONE") and state.flags.get("REZA_QUEST_DONE")
        state.scene_id = "TRUE_ENDING" if has_true else "GOOD_ENDING"
        state.main_progress = "Epilog"
        await send_scene(update, context, state)
        return

    if choice_data in SCENES:
        await render_scene(update, context, state, choice_data)
        return

    await send_scene_not_found(update, context, state)

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

    choices = [("Lihat status party", "MENU_STATUS"), ("Kelola Equipment", "MENU_EQUIPMENT"), ("Inventory", "MENU_INVENTORY")]
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
    if (
        state.location == "PEKANBARU"
        and state.flags.get("VISITED_PEKANBARU")
        and not (state.flags.get("WEAPON_QUEST_DONE") or state.flags.get("QUEST_WEAPON_DONE"))
    ):
        started = state.flags.get("QUEST_WEAPON_STARTED") or state.flags.get("WEAPON_QUEST_STARTED")
        label = "Lanjutkan pencarian pedang Harsan" if started else "Jejak pedang warisan Harsan"
        choices.append((label, "QUEST_HARSAN_BLADE"))
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


async def send_shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState):
    query = update.callback_query
    loc_info = LOCATIONS.get(state.location)
    if not loc_info or not loc_info.get("has_shop"):
        if query:
            await query.edit_message_text(
                "Tidak ada toko di lokasi ini.",
                reply_markup=make_keyboard([("Kembali ke kota", "BACK_CITY_MENU")]),
            )
        elif update.message:
            await update.message.reply_text("Tidak ada toko di lokasi ini.")
        return
    features = CITY_FEATURES.get(state.location, {})
    shop_items = features.get("shop_items", [])
    lines = [f"🏪 Toko di {loc_info['name']}", f"Gold-mu saat ini: {state.gold}"]
    buttons = [
        [InlineKeyboardButton("🛒 Beli barang", callback_data="SHOP_BUY")],
        [InlineKeyboardButton("💰 Jual barang", callback_data="SHOP_SELL")],
        [InlineKeyboardButton("⬅ Kembali", callback_data="BACK_CITY_MENU")],
    ]
    text = "\n".join(lines)
    markup = InlineKeyboardMarkup(buttons)
    if query:
        await query.edit_message_text(text=text, reply_markup=markup)
    elif update.message:
        await update.message.reply_text(text=text, reply_markup=markup)


async def send_shop_buy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState):
    query = update.callback_query
    features = CITY_FEATURES.get(state.location, {})
    shop_items = features.get("shop_items", [])
    lines = ["Daftar barang yang dijual:", f"Gold: {state.gold}"]
    buttons: List[List[InlineKeyboardButton]] = []
    if not shop_items:
        lines.append("Toko ini sedang kosong.")
    else:
        for item_id in shop_items:
            item = ITEMS.get(item_id)
            if not item:
                continue
            lines.append(f"- {item['name']} ({item['buy_price']} Gold)")
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"Beli {item['name']}", callback_data=f"BUY_ITEM|{item_id}"
                    )
                ]
            )
    buttons.append([InlineKeyboardButton("⬅ Kembali", callback_data="MENU_SHOP")])
    markup = InlineKeyboardMarkup(buttons)
    if query:
        await query.edit_message_text("\n".join(lines), reply_markup=markup)
    else:
        await update.message.reply_text("\n".join(lines), reply_markup=markup)


async def send_shop_sell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState):
    query = update.callback_query
    lines = ["Pilih item yang ingin dijual:", f"Gold: {state.gold}"]
    buttons: List[List[InlineKeyboardButton]] = []
    any_item = False
    for item_id, qty in sorted(state.inventory.items()):
        if qty <= 0:
            continue
        item = ITEMS.get(item_id)
        if not item:
            continue
        sell_price = item.get("sell_price", 0)
        if sell_price <= 0:
            continue
        any_item = True
        lines.append(f"- {item['name']} x{qty} (jual {sell_price} Gold)")
        buttons.append(
            [InlineKeyboardButton(f"Jual {item['name']}", callback_data=f"SELL_ITEM|{item_id}")]
        )
    if not any_item:
        lines.append("Tidak ada item yang bisa dijual.")
    buttons.append([InlineKeyboardButton("⬅ Kembali", callback_data="MENU_SHOP")])
    markup = InlineKeyboardMarkup(buttons)
    if query:
        await query.edit_message_text("\n".join(lines), reply_markup=markup)
    else:
        await update.message.reply_text("\n".join(lines), reply_markup=markup)


async def handle_buy_item(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState, item_id: str
):
    item = ITEMS.get(item_id)
    if not item:
        await update.callback_query.answer("Item tidak dikenal.", show_alert=True)
        return
    price = item.get("buy_price", 0)
    if state.gold < price:
        await update.callback_query.answer("Gold-mu tidak cukup.", show_alert=True)
        return
    state.gold -= price
    adjust_inventory(state, item_id, 1)
    await update.callback_query.answer(f"Kamu membeli {item['name']}!", show_alert=False)
    await send_shop_buy_menu(update, context, state)


async def handle_sell_item(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState, item_id: str
):
    item = ITEMS.get(item_id)
    if not item:
        await update.callback_query.answer("Item tidak dikenal.", show_alert=True)
        return
    sell_price = item.get("sell_price", 0)
    if sell_price <= 0:
        await update.callback_query.answer("Item itu tidak bisa dijual.", show_alert=True)
        return
    qty = state.inventory.get(item_id, 0)
    if qty <= 0:
        await update.callback_query.answer("Kamu tidak memiliki item tersebut.", show_alert=True)
        return
    adjust_inventory(state, item_id, -1)
    state.gold += sell_price
    await update.callback_query.answer(
        f"Kamu menjual {item['name']} seharga {sell_price} Gold.", show_alert=False
    )
    await send_shop_sell_menu(update, context, state)


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


async def send_equipment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState):
    lines = ["Kelola equipment party:"]
    buttons = []
    for cid in state.party_order:
        c = state.party[cid]
        weapon = ITEMS.get(c.weapon_id, {}).get("name") if c.weapon_id else "(Kosong)"
        armor = ITEMS.get(c.armor_id, {}).get("name") if c.armor_id else "(Kosong)"
        lines.append(f"- {c.name}: Senjata {weapon} | Armor {armor}")
        lines.append(f"  {format_effective_stat_summary(c)}")
        buttons.append([InlineKeyboardButton(c.name, callback_data=f"EQUIP_CHAR|{cid}")])
    buttons.append([InlineKeyboardButton("⬅ Kembali", callback_data="BACK_CITY_MENU")])
    markup = InlineKeyboardMarkup(buttons)
    query = update.callback_query
    text = "\n".join(lines)
    if query:
        await query.edit_message_text(text=text, reply_markup=markup)
    else:
        await update.message.reply_text(text=text, reply_markup=markup)


async def send_character_equipment_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: GameState,
    char_id: str,
    extra_text: str = "",
):
    character = state.party.get(char_id)
    if not character:
        await send_equipment_menu(update, context, state)
        return
    weapon = ITEMS.get(character.weapon_id, {}).get("name") if character.weapon_id else "(Kosong)"
    armor = ITEMS.get(character.armor_id, {}).get("name") if character.armor_id else "(Kosong)"
    lines = [
        f"Kelola gear untuk {character.name}:",
        f"Senjata saat ini: {weapon}",
        f"Armor saat ini: {armor}",
        f"Stat efektif: {format_effective_stat_summary(character)}",
    ]
    if extra_text:
        lines.append("")
        lines.append(extra_text)
    buttons: List[List[InlineKeyboardButton]] = []
    weapon_choices = list_equippable_items(state, char_id, "weapon")
    if weapon_choices:
        lines.append("\nSenjata di tas:")
        for item_id, item, qty in weapon_choices:
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"Pasang {item['name']} (x{qty})",
                        callback_data=f"EQUIP_WEAPON|{char_id}|{item_id}",
                    )
                ]
            )
    if character.weapon_id:
        buttons.append(
            [InlineKeyboardButton("Lepas senjata", callback_data=f"UNEQUIP|{char_id}|weapon")]
        )
    armor_choices = list_equippable_items(state, char_id, "armor")
    if armor_choices:
        lines.append("\nArmor di tas:")
        for item_id, item, qty in armor_choices:
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"Pasang {item['name']} (x{qty})",
                        callback_data=f"EQUIP_ARMOR|{char_id}|{item_id}",
                    )
                ]
            )
    if character.armor_id:
        buttons.append(
            [InlineKeyboardButton("Lepas armor", callback_data=f"UNEQUIP|{char_id}|armor")]
        )
    buttons.append([InlineKeyboardButton("⬅ Kembali", callback_data="MENU_EQUIPMENT")])
    markup = InlineKeyboardMarkup(buttons)
    query = update.callback_query
    text = "\n".join(lines)
    if query:
        await query.edit_message_text(text=text, reply_markup=markup)
    else:
        await update.message.reply_text(text=text, reply_markup=markup)


async def handle_equip_item_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: GameState,
    char_id: str,
    item_id: str,
    slot_type: str,
):
    success, message = equip_item(state, char_id, item_id, expected_type=slot_type)
    await update.callback_query.answer(message, show_alert=not success)
    extra = message
    character = state.party.get(char_id)
    if character:
        extra += "\n" + format_effective_stat_summary(character)
    await send_character_equipment_menu(update, context, state, char_id, extra_text=extra)


async def handle_unequip_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState, char_id: str, slot: str
):
    success, message = unequip_item(state, char_id, slot)
    await update.callback_query.answer(message, show_alert=not success)
    extra = message
    character = state.party.get(char_id)
    if character:
        extra += "\n" + format_effective_stat_summary(character)
    await send_character_equipment_menu(update, context, state, char_id, extra_text=extra)


def apply_consumable_outside_battle(state: GameState, item_id: str) -> Tuple[bool, List[str]]:
    item = ITEMS.get(item_id)
    if not item or item.get("type") != "consumable":
        return False, ["Item itu tidak bisa dipakai di luar battle."]
    if state.inventory.get(item_id, 0) <= 0:
        return False, ["Persediaan item itu sudah habis."]
    effects = item.get("effects", {})
    hp_restore = effects.get("hp_restore", 0)
    mp_restore = effects.get("mp_restore", 0)
    if not hp_restore and not mp_restore:
        return False, ["Hanya item pemulih yang bisa dipakai di luar battle."]

    target_mode = effects.get("target", "single")
    targets: List[CharacterState] = []
    if target_mode == "party":
        targets = [state.party[cid] for cid in state.party_order if state.party[cid].hp > 0]
    else:
        aruna = state.party.get("ARUNA")
        if aruna and aruna.hp > 0:
            targets = [aruna]
    if not targets:
        return False, ["Tidak ada target yang bisa menerima efek item."]

    logs: List[str] = [f"Kamu menggunakan {item['name']}."]
    effect_logs: List[str] = []
    hp_targets: List[str] = []
    mp_targets: List[str] = []

    for target in targets:
        if hp_restore:
            before_hp = target.hp
            target.hp = min(get_effective_max_hp(target), target.hp + hp_restore)
            restored = target.hp - before_hp
            if restored > 0:
                hp_targets.append(target.name)
                effect_logs.append(f"HP {target.name} pulih {restored}.")
        if mp_restore:
            before_mp = target.mp
            target.mp = min(get_effective_max_mp(target), target.mp + mp_restore)
            restored_mp = target.mp - before_mp
            if restored_mp > 0:
                mp_targets.append(target.name)
                effect_logs.append(f"MP {target.name} pulih {restored_mp}.")

    def _format_names(names: List[str]) -> str:
        if len(names) <= 1:
            return names[0] if names else ""
        if len(names) == 2:
            return f"{names[0]} dan {names[1]}"
        return ", ".join(names[:-1]) + f", dan {names[-1]}"

    if len(hp_targets) > 1:
        effect_logs.append(f"HP {_format_names(hp_targets)} pulih sebagian.")
    if len(mp_targets) > 1:
        effect_logs.append(f"MP {_format_names(mp_targets)} pulih sebagian.")

    if not effect_logs:
        effect_logs.append("Tidak ada efek berarti.")

    adjust_inventory(state, item_id, -1)
    logs.extend(effect_logs)
    return True, logs


async def send_inventory_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: GameState,
    extra_text: str = "",
):
    lines = ["=== INVENTORY ==="]
    if extra_text:
        lines.append(extra_text)
        lines.append("")
    if not state.inventory:
        lines.append("Tas kamu kosong.")
    else:
        for item_id, qty in sorted(state.inventory.items()):
            if qty <= 0:
                continue
            item = ITEMS.get(item_id)
            if not item:
                continue
            owners = get_equipped_owners(state, item_id)
            owner_text = f" | Dipakai: {', '.join(owners)}" if owners else ""
            lines.append(f"- {item['name']} x{qty}{owner_text}")
            lines.append(f"  {item['description']}")
    lines.append("\nPerlengkapan terpasang:")
    for cid in state.party_order:
        c = state.party[cid]
        weapon = ITEMS.get(c.weapon_id, {}).get("name") if c.weapon_id else "(Kosong)"
        armor = ITEMS.get(c.armor_id, {}).get("name") if c.armor_id else "(Kosong)"
        lines.append(f"- {c.name}: Senjata {weapon} | Armor {armor}")
    buttons: List[List[InlineKeyboardButton]] = []
    for item_id, qty in sorted(state.inventory.items()):
        if qty <= 0:
            continue
        item = ITEMS.get(item_id)
        if not item or item.get("type") != "consumable":
            continue
        effects = item.get("effects", {})
        if not effects.get("hp_restore") and not effects.get("mp_restore"):
            continue
        buttons.append(
            [InlineKeyboardButton(f"Gunakan {item['name']}", callback_data=f"USE_ITEM_OUTSIDE|{item_id}")]
        )
    buttons.append([InlineKeyboardButton("⬅ Kembali", callback_data="BACK_CITY_MENU")])
    markup = InlineKeyboardMarkup(buttons)
    query = update.callback_query
    text = "\n".join(lines)
    if query:
        await query.edit_message_text(text=text, reply_markup=markup)
    elif update.message:
        await update.message.reply_text(text=text, reply_markup=markup)


async def handle_use_item_outside(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: GameState, item_id: str
):
    success, logs = apply_consumable_outside_battle(state, item_id)
    if not success:
        await update.callback_query.answer(" ".join(logs), show_alert=True)
        await send_inventory_menu(update, context, state)
        return
    await update.callback_query.answer("Berhasil menggunakan item.", show_alert=False)
    await send_inventory_menu(update, context, state, extra_text="\n".join(logs))


# ==========================
# HANDLER KOMANDO
# ==========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with get_user_lock(user_id):
        state = get_game_state(user_id)
        state.scene_id = "CH0_S1"
        state.location = "SELATPANJANG"
        state.main_progress = "PROLOG"
        state.ensure_aruna()
    await send_scene(update, context, state)


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with get_user_lock(user_id):
        state = get_game_state(user_id)
    lines = ["=== STATUS PARTY ==="]
    for cid in state.party_order:
        c = state.party[cid]
        lines.append(format_effective_stat_summary(c))
    lines.append(f"\nGold: {state.gold}")
    lines.append(f"Lokasi: {LOCATIONS[state.location]['name']}")
    lines.append(f"Main Quest: {state.main_progress}")
    await update.message.reply_text("\n".join(lines))


async def map_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with get_user_lock(user_id):
        state = get_game_state(user_id)
    await send_world_map(update, context, state)


async def save_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with get_user_lock(user_id):
        state = get_game_state(user_id)
        success = save_game_state(user_id, state)
    if update.message:
        if success:
            await update.message.reply_text("Progress permainanmu telah disimpan.")
        else:
            await update.message.reply_text(
                "Gagal menyimpan progress. Silakan coba lagi atau cek izin folder saves."
            )


async def load_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with get_user_lock(user_id):
        save_exists = os.path.exists(get_save_path(user_id))
        loaded = load_game_state(user_id)
        if not loaded:
            if update.message:
                if save_exists:
                    await update.message.reply_text(
                        "Gagal memuat save. Coba lagi nanti atau periksa file di folder saves."
                    )
                else:
                    await update.message.reply_text(
                        "Tidak ada data save yang ditemukan untuk akunmu."
                    )
            return
        loaded.ensure_aruna()
        USER_STATES[user_id] = loaded
    if update.message:
        loc_name = LOCATIONS.get(loaded.location, {}).get("name", loaded.location)
        aruna = loaded.party.get("ARUNA")
        aruna_level = aruna.level if aruna else "-"
        await update.message.reply_text(
            (
                "Progress berhasil dimuat!\n"
                f"Lokasi: {loc_name}\n"
                f"Level Aruna: {aruna_level}\n"
                "Gunakan /status untuk melihat detail party."
            )
        )


async def inventory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with get_user_lock(user_id):
        state = get_game_state(user_id)
    await send_inventory_menu(update, context, state)


# ==========================
# CALLBACK QUERY HANDLER
# ==========================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    async with get_user_lock(user_id):
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

        if data.startswith("USE_ITEM|"):
            _, item_id = data.split("|", 1)
            if not state.in_battle:
                await query.edit_message_text("Kamu tidak sedang dalam battle.")
                return
            await process_use_item(update, context, state, item_id)
            return

        if data == "DUNGEON_BATTLE_AGAIN":
            await start_random_battle(update, context, state)
            return

        if data == "RETURN_TO_CITY":
            await send_city_menu(update, context, state)
            return

        current_scene = get_scene(state.scene_id)
        if current_scene and find_choice_by_callback(current_scene, data):
            await handle_scene_choice(update, context, state, data)
            return

        # WORLD MAP / TRAVEL
        if data.startswith("GOTO_CITY|"):
            _, loc_id = data.split("|")
            loc_info = LOCATIONS[loc_id]
            aruna = state.party["ARUNA"]
            if aruna.level < loc_info["min_level"]:
                text = (
                    f"Level kamu ({aruna.level}) belum cukup untuk masuk ke {loc_info['name']} "
                    f"(butuh Lv {loc_info['min_level']})."
                )
                keyboard = make_keyboard([("Kembali ke map", "GO_TO_WORLD_MAP")])
                await query.edit_message_text(text=text, reply_markup=keyboard)
                return
            state.location = loc_id
            if loc_id == "SIAK" and not state.flags.get("VISITED_SIAK"):
                state.flags["VISITED_SIAK"] = True
                await render_scene(update, context, state, "CH1_SIAK_ENTRY")
            elif loc_id == "RENGAT" and not state.flags.get("VISITED_RENGAT"):
                state.flags["VISITED_RENGAT"] = True
                await render_scene(update, context, state, "CH2_RENGAT_GATE")
            elif loc_id == "PEKANBARU" and not state.flags.get("VISITED_PEKANBARU"):
                state.flags["VISITED_PEKANBARU"] = True
                await render_scene(update, context, state, "CH3_PEKANBARU_ENTRY")
            elif loc_id == "KAMPAR" and not state.flags.get("VISITED_KAMPAR"):
                state.flags["VISITED_KAMPAR"] = True
                await render_scene(update, context, state, "CH4_KAMPAR_ENTRY")
            else:
                await send_city_menu(update, context, state)
            return

        if data == "ENTER_DUNGEON":
            area = NEAREST_DUNGEON.get(state.location, "HUTAN_SELATPANJANG")
            text = f"Kamu memasuki {area}. Monster berkeliaran di sini."
            keyboard = make_keyboard(
                [("Cari monster", "DUNGEON_BATTLE_AGAIN"), ("Kembali ke kota", "RETURN_TO_CITY")]
            )
            await query.edit_message_text(text=text, reply_markup=keyboard)
            return

        # MENU KOTA
        if data == "MENU_STATUS":
            lines = ["=== STATUS PARTY ==="]
            for cid in state.party_order:
                c = state.party[cid]
                lines.append(format_effective_stat_summary(c))
            lines.append(f"\nGold: {state.gold}")
            lines.append(f"Lokasi: {LOCATIONS[state.location]['name']}")
            lines.append(f"Main Quest: {state.main_progress}")
            text = "\n".join(lines)
            keyboard = make_keyboard([("Kembali ke kota", "BACK_CITY_MENU")])
            await query.edit_message_text(text=text, reply_markup=keyboard)
            return

        if data == "BACK_CITY_MENU":
            await send_city_menu(update, context, state)
            return

        if data == "MENU_SHOP":
            await send_shop_menu(update, context, state)
            return
        if data == "SHOP_BUY":
            await send_shop_buy_menu(update, context, state)
            return
        if data == "SHOP_SELL":
            await send_shop_sell_menu(update, context, state)
            return
        if data.startswith("BUY_ITEM|"):
            _, item_id = data.split("|", 1)
            await handle_buy_item(update, context, state, item_id)
            return
        if data.startswith("SELL_ITEM|"):
            _, item_id = data.split("|", 1)
            await handle_sell_item(update, context, state, item_id)
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
                    c.hp = get_effective_max_hp(c)
                    c.mp = get_effective_max_mp(c)
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
            if state.location != "SIAK":
                await query.edit_message_text(
                    "Klinik hanya ada di Siak.",
                    reply_markup=make_keyboard([("Kembali", "BACK_CITY_MENU")]),
                )
                return
            if not state.flags.get("HAS_UMAR"):
                await render_scene(update, context, state, "CH1_UMAR_CLINIC")
            else:
                text = "Umar: \"Jaga dirimu baik-baik, Aruna. Aku di sini kalau kau butuh bantuan.\"\n"
                keyboard = make_keyboard([("Kembali ke kota", "BACK_CITY_MENU")])
                await query.edit_message_text(text=text, reply_markup=keyboard)
            return

        if data == "MENU_EQUIPMENT":
            await send_equipment_menu(update, context, state)
            return
        if data.startswith("EQUIP_CHAR|"):
            _, char_id = data.split("|", 1)
            await send_character_equipment_menu(update, context, state, char_id)
            return
        if data.startswith("EQUIP_WEAPON|"):
            _, char_id, item_id = data.split("|", 2)
            await handle_equip_item_selection(
                update, context, state, char_id, item_id, slot_type="weapon"
            )
            return
        if data.startswith("EQUIP_ARMOR|"):
            _, char_id, item_id = data.split("|", 2)
            await handle_equip_item_selection(
                update, context, state, char_id, item_id, slot_type="armor"
            )
            return
        if data.startswith("EQUIP_ITEM|"):
            _, char_id, item_id = data.split("|", 2)
            item = ITEMS.get(item_id)
            slot_type = item.get("type") if item else "weapon"
            await handle_equip_item_selection(
                update, context, state, char_id, item_id, slot_type=slot_type
            )
            return
        if data.startswith("UNEQUIP|"):
            _, char_id, slot = data.split("|", 2)
            await handle_unequip_selection(update, context, state, char_id, slot)
            return

        if data == "MENU_INVENTORY":
            await send_inventory_menu(update, context, state)
            return
        if data.startswith("USE_ITEM_OUTSIDE|"):
            _, item_id = data.split("|", 1)
            await handle_use_item_outside(update, context, state, item_id)
            return

        if data == "EVENT_SIAK_GATE":
            await render_scene(update, context, state, "CH1_GATE_ALERT")
            return

        if data == "EVENT_PEKANBARU_CAFE":
            state.flags["PEKANBARU_RUMOR_DONE"] = True
            await render_scene(update, context, state, "CH3_PEKANBARU_ENTRY")
            return

        if data == "EVENT_KASTIL_ENTRY":
            await render_scene(update, context, state, "CH4_CASTLE_APPROACH")
            return

        if data == "QUEST_UMAR":
            await render_scene(update, context, state, "SQ_UMAR_INTRO")
            return

        if data == "QUEST_REZA":
            await render_scene(update, context, state, "SQ_REZA_INTRO")
            return
        if data == "QUEST_HARSAN_BLADE":
            state.flags["QUEST_WEAPON_STARTED"] = True
            state.flags["WEAPON_QUEST_STARTED"] = True
            await render_scene(update, context, state, "SQ_HARSAN_BLADE_INTRO")
            return

        if data.startswith("DO_JOB|"):
            _, job_id = data.split("|")
            await resolve_job(update, context, state, job_id)
            return

        if data == "GO_TO_WORLD_MAP":
            await send_world_map(update, context, state)
            return

        if data in SCENES:
            await render_scene(update, context, state, data)
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
    application.add_handler(CommandHandler("save", save_cmd))
    application.add_handler(CommandHandler("load", load_cmd))
    application.add_handler(CommandHandler("inventory", inventory_cmd))

    application.add_handler(CallbackQueryHandler(button))

    logger.info("Bot Legends of Aruna berjalan...")
    application.run_polling()


if __name__ == "__main__":
    main()
