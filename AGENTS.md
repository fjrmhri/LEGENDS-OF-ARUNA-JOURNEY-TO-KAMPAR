# AGENTS.md  
# Legends of Aruna: Journey to Kampar – Agent Design (Implementasi Saat Ini)

Dokumen ini menjelaskan pembagian *agent logis* (modul mental) di dalam  
kode `LEGENDS_OF_ARUNA_JOURNEY_TO_KAMPAR.py`.

Secara fisik semuanya masih berada di **satu file Python**, tapi secara konsep  
sudah terbagi menjadi beberapa “agent” agar mudah dikembangkan, di-refactor ke banyak file, dan di-maintain.

---

## 0. Gambaran Besar

Alur umum:

1. Player kirim command (`/start`, `/status`, `/map`, `/inventory`, `/save`, `/load`)  
   atau menekan inline button.
2. Handler Telegram (`start`, `status_cmd`, `map_cmd`, `inventory_cmd`, `save_cmd`, `load_cmd`, `button`) menangani update.
3. Berdasarkan `text` atau `callback_data`, handler memanggil logika yang secara mental kita bagi jadi:

- **GameMasterAgent** – router/orkestrator input → agent lain, plus locking per user.
- **StoryAgent** – scene & dialog cerita utama + side quest + ending.
- **WorldAgent** – world map, perpindahan kota, level gate, akses dungeon/hutan.
- **CityAgent** – menu kota, job, inn, klinik, shop, event kota.
- **BattleAgent** – sistem pertarungan turn-based full party + skill + buff/debuff.
- **ProgressionAgent** – XP, level up, growth stat, unlock skill.
- **Inventory/ItemAgent** – item, inventory, equipment, drop, shop beli/jual.
- **PersistenceAgent** – save/load game ke file JSON per user.

Semua state pemain tersimpan dalam `GameState` per `user_id` dan disimpan di  
`USER_STATES[user_id]`, dengan `asyncio.Lock` per user untuk menghindari race condition.

---

## 1. GameMasterAgent

**Lokasi kode utama:**

- `main()` – setup `Application`, register semua command & callback handler.
- `get_game_state(user_id)` – inisialisasi & ambil `GameState` per user.
- `get_user_lock(user_id)` – kunci per user (async lock).
- Handler:
  - `start(update, context)`
  - `status_cmd(update, context)`
  - `map_cmd(update, context)`
  - `inventory_cmd(update, context)`
  - `save_cmd(update, context)`
  - `load_cmd(update, context)`
  - `button(update, context)` – handler utama semua tombol.

**Tanggung jawab:**

- Menjadi **router** utama:
  - Prefix callback:
    - `BATTLE_`, `USE_SKILL|...`, `USE_ITEM|...` → BattleAgent.
    - `GOTO_CITY|...`, `ENTER_DUNGEON` → WorldAgent.
    - `MENU_*`, `EVENT_*`, `QUEST_*`, `DO_JOB|...` → CityAgent / StoryAgent.
    - `INV_*`, `EQUIP_*`, `UNEQUIP|...` → Inventory/ItemAgent.
  - Kalau `callback_data` cocok dengan `scene_id` di `SCENE_DATA` → StoryAgent.
- Menjamin hanya satu operasi per user yang berjalan sekaligus:
  - Semua handler async dibungkus `async with get_user_lock(user_id)`.
- Memastikan `GameState` selalu punya Aruna melalui `state.ensure_aruna()` ketika perlu.

---

## 2. StoryAgent

**Lokasi kode utama:**

- `SCENE_DATA` – kamus semua scene naratif (prolog, chapter, side quest, ending).
- Fungsi:
  - `send_scene(update, context, state, extra_text="")`
  - `handle_scene_choice(update, context, state, choice_data)`

**Tanggung jawab:**

- Menyimpan dan menampilkan **seluruh cerita**:

  - **Prolog – Selatpanjang (CH0)**  
    Kehidupan Aruna & paman, serangan Shadow Fiend, wasiat untuk pergi ke Siak.

  - **Chapter 1 – Siak (CH1)**  
    - Kedatangan di Siak.  
    - Klinik Umar & pengenalan Ibunya (Safiya).  
    - Serangan monster di gerbang Siak (battle story).  
    - Umar bergabung ke party.  

  - **Chapter 2 – Rengat (CH2)**  
    - Gerbang kota magis Rengat.  
    - Menara Reza, pengenalan Harsan (ayah Aruna, Penjaga Cahaya terakhir).  
    - Cerita tentang Febri dan Kampar.  
    - Serangan Corrupted Forest Golem (boss story) dan Reza join party.

  - **Chapter 3 – Pekanbaru (CH3)**  
    - Kota muram, NPC yang takut Kampar.  
    - Kafe remang, orang tua misterius yang bercerita tentang Febri dulu manusia.  
    - Mimpi Aruna tentang Harsan vs Febri dan segel Kampar.  
    - Pointer ke Kampar sebagai main quest berikutnya.

  - **Chapter 4 – Kampar (CH4)**  
    - Masuk kota terkutuk Kampar; tidak ada NPC atau toko.  
    - Flashback besar Harsan & Rusmini memisahkan Aruna Core dan bayi Aruna.  
    - Pendekatan ke kastil Febri.

  - **Chapter 5 – Kastil Febri (CH5)**  
    - Lantai 1: Koridor Bayangan.  
    - Lantai 2: Hound of Void (mini boss) – Aruna Core melindungi Umar.  
    - Lantai 3: Ruang Segel Lama – jubah guru Reza, janji Reza melindungi Aruna.  
    - Lantai 4: Void Sentinel (mini boss).  
    - Lantai 5: Singgasana Febri – dialog final dan final battle trigger.

  - **Side Quest Umar – Warisan Safiya (SQ_UMAR_*)**  
    - Keluarga yang menyalahkan Safiya di Siak.  
    - Mencari herb di hutan Siak.  
    - Umar menyembuhkan anak mereka dan menerima warisan Safiya.  

  - **Side Quest Reza – Suara dari Segel (SQ_REZA_*)**  
    - Suara guru Reza dari hutan Rengat.  
    - Mini-dungeon & echo sang guru.  
    - Reza diminta meninggalkan balas dendam, fokus lindungi Aruna.

  - **Quest Pedang Warisan Harsan (SQ_HARSAN_BLADE_*)**  
    - Rumor tentang simbol kalung pada relief pedang di Pekanbaru.  
    - Shrine rahasia (kuil cahaya), penjaga luminescent.  
    - Vision Harsan & Rusmini memisah pedang + kalung.  
    - Aruna menyatukan pedang + kalung → mendapat **Pedang Warisan Harsan**.

  - **Ending:**
    - `ENDING_BAD` – kalah vs Febri, Kampar menelan dunia.  
    - `ENDING_GOOD` – menang tanpa semua side quest selesai.  
    - `ENDING_TRUE` – menang + `UMAR_QUEST_DONE` & `REZA_QUEST_DONE` → Febri sempat sadar dan disegel tanpa kebencian.

- Mengatur **flag cerita** di `state.flags`, misalnya:
  - `HAS_UMAR`, `HAS_REZA`.
  - `VISITED_SIAK`, `VISITED_RENGAT`, `VISITED_PEKANBARU`, `VISITED_KAMPAR`.
  - `UMAR_QUEST_DONE`, `REZA_QUEST_DONE`.
  - `QUEST_WEAPON_STARTED`, `QUEST_WEAPON_DONE`.
- Menghubungkan scene dengan BattleAgent:
  - `BATTLE_TUTORIAL_1`, `BATTLE_SIAK_GATE`, `BATTLE_RENGAT_GOLEM`,  
    `BATTLE_HOUND_OF_VOID`, `BATTLE_VOID_SENTINEL`, `BATTLE_FEBRI`,  
    battle penjaga shrine Harsan.

**Contoh jalur penting:**

- Dari Siak:
  - `CH1_UMAR_CLINIC` → Umar join → `SIAK_CITY_MENU_AFTER_UMAR`.
- Dari Rengat:
  - `CH2_GOLEM_ALERT` → `BATTLE_RENGAT_GOLEM` → `CH2_GOLEM_AFTER` → `ADD_REZA_PARTY`.
- Menuju ending:
  - Setelah final battle Febri: scene `CH5_FINAL_RESOLVE` → pilihan `RESOLVE_ENDING` →  
    cek flag `UMAR_QUEST_DONE` & `REZA_QUEST_DONE` → `ENDING_TRUE` atau `ENDING_GOOD`.

---

## 3. WorldAgent

**Lokasi kode utama:**

- Data:
  - `LOCATIONS` – definisi kota: nama, tipe (TOWN/CURSED), `min_level`, fitur (`has_shop`, `has_job`, dll).
  - `NEAREST_DUNGEON` – map kota → area hutan/dungeon.
  - `WORLD_MAP_ASCII` – desain map dunia dalam ASCII.
- Fungsi:
  - `send_world_map(update, context, state)`
  - Bagian dalam `button()` untuk:
    - `GOTO_CITY|...`
    - `ENTER_DUNGEON`

**Tanggung jawab:**

- Menampilkan world map lengkap + status main quest, misalnya:
  - "Menuju Rengat (Lv 5+)", "Menuju Pekanbaru (Lv 8+)", "Menuju Kampar (Lv 12+)".
- Mengatur **perpindahan kota**:
  - `GOTO_CITY|SIAK`, `GOTO_CITY|RENGAT`, `GOTO_CITY|PEKANBARU`, `GOTO_CITY|KAMPAR`.
  - Cek `min_level` berdasarkan level Aruna:
    - Jika belum cukup: tampilkan pesan penolakan masuk.
    - Jika cukup:
      - Jika belum pernah `VISITED_*`: trigger scene entry chapter terkait.
      - Jika sudah: langsung ke `send_city_menu()`.

- Mengatur akses **hutan/dungeon**:
  - `ENTER_DUNGEON` dari menu kota → pilih area sekitar (mis. Hutan Siak, Hutan Rengat).
  - Dari sana player bisa:
    - Mulai battle random (`start_random_battle`).
    - Kembali ke kota.

- Untuk Kampar:
  - `LOCATIONS["KAMPAR"]` bertipe `CURSED`, `has_shop = False`, `has_inn = False`, `has_job = False`.
  - Hanya menyediakan akses:
    - Ke area monster Kampar luar.
    - Ke event masuk kastil (`EVENT_KASTIL_ENTRY` → scene `CH4_CASTLE_APPROACH`).

---

## 4. CityAgent

**Lokasi kode utama:**

- Data:
  - `CITY_FEATURES` – detail per kota:
    - `shop_items`: list item yang dijual.
    - `inn_price`: harga penginapan.
    - `jobs`: daftar kerja (nama, deskripsi, reward, fail_chance).
- Fungsi:
  - `send_city_menu(update, context, state)`
  - `send_job_menu(...)`, `resolve_job(...)`
  - `send_shop_menu(...)`, `send_shop_buy_menu(...)`, `send_shop_sell_menu(...)`
  - `handle_buy_item(...)`, `handle_sell_item(...)`
  - `send_inn_menu(...)`
  - Event kota / quest trigger:
    - `EVENT_SIAK_GATE`
    - `EVENT_PEKANBARU_CAFE`
    - `QUEST_UMAR`, `QUEST_REZA`, `QUEST_HARSAN_BLADE`

**Tanggung jawab:**

- Menjadi **hub aktivitas** di setiap kota:
  - Menu status singkat kota, Gold, main quest hint.
  - Pilihan:
    - `MENU_STATUS` – cek detail party.
    - `MENU_EQUIPMENT` – menu equipment per karakter.
    - `MENU_INVENTORY` – cek inventori + pakai consumable di luar battle.
    - `MENU_SHOP` – beli/jual item.
    - `MENU_JOB` – bekerja untuk Gold.
    - `MENU_INN` – tidur untuk full heal.
    - `MENU_CLINIC` – klinik khusus (mis. trigger Umar di Siak).

- **Sistem kerja (job):**
  - Pilihan job beda per kota, dengan:
    - reward Gold berbeda.
    - kemungkinan gagal.
  - `resolve_job(...)`:
    - pakai random untuk menentukan sukses/gagal.
    - update Gold dan kirim pesan hasil.

- **Penginapan (inn):**
  - Cek Gold cukup atau tidak.
  - Jika cukup:
    - kurangi Gold.
    - set HP/MP seluruh party ke max.
  - Pesan konfirmasi dalam bahasa Indonesia.

- **Shop:**
  - `MENU_SHOP` → submenu:
    - `SHOP_BUY`: daftar barang yang dijual + harga buy.
    - `SHOP_SELL`: daftar item di inventory + harga sell, dengan warning kalau item sedang dipakai.
  - Beli:
    - cek Gold.
    - pakai `adjust_inventory`.
  - Jual:
    - cek qty > 0 dan tidak sedang ter-equip (kalau mau lebih aman).
    - tambah Gold.

- **Quest & event kota:**
  - Siak:
    - gate event (monster menyerang).
    - rumour untuk quest Umar.
  - Rengat:
    - trigger side quest Reza dari NPC tua.
  - Pekanbaru:
    - kafe remang (CH3).
    - NPC library/relief yang memicu quest pedang Harsan.
  - Kampar:
    - event masuk kastil.

---

## 5. BattleAgent

**Lokasi kode utama:**

- Data:
  - `MONSTERS` – data monster lengkap (stat, area, element, weakness, resist, XP, Gold).
  - `DROP_TABLES` – tabel drop per area (HUTAN_SELATPANJANG, HUTAN_SIAK, HUTAN_RENGAT, HUTAN_PEKANBARU, KAMPAR_LUAR, HARSAN_SHRINE).
  - `SKILLS` – definisi skill karakter (type, power, MP cost, element, dll).

- Struct:
  - `BattleTurnState`:
    - `turn_order: List[str]` – urutan token `"CHAR:ARUNA"`, `"CHAR:UMAR"`, `"CHAR:REZA"`, `"ENEMY:0"`, dst.
    - `current_index: int`
    - `awaiting_player_input: bool`
    - `active_token: Optional[str]`
  - `GameState` fields terkait:
    - `in_battle`
    - `battle_enemies`
    - `battle_turn`
    - `battle_state`
    - `return_scene_after_battle`
    - `loss_scene_after_battle`

- Fungsi utama:
  - Setup:
    - `pick_random_monster_for_area(area_id)`
    - `create_enemy_from_key(monster_key)`
    - `start_random_battle(...)`
    - `start_story_battle(...)`
    - `init_battle_turn_order(state)` – bikin `turn_order` berdasarkan party & musuh.
  - UI:
    - `battle_status_text(state)` – teks status HP/MP party & musuh.
    - `send_battle_state(...)`
  - Aksi player:
    - `process_battle_action(...)` – routing ke ATTACK, DEFEND, SKILL, ITEM, RUN.
    - `process_use_skill(...)` – eksekusi skill berdasarkan `skill['type']`.
    - `show_battle_skill_menu(...)`
    - `show_battle_item_menu(...)`
  - Aksi musuh:
    - `process_enemy_turn(...)` – pilih target party random dari yang masih hidup.
  - Turn flow:
    - `advance_to_next_player_turn(...)`
    - `conclude_player_turn(...)`
    - `resolve_battle_outcome(...)`
    - `end_battle_and_return(...)`
  - Buff/debuff:
    - `apply_temporary_modifier(...)`, `tick_buffs(...)`,  
      `make_char_buff_key(...)`, `make_enemy_buff_key(...)`,
      `clear_active_buffs(...)`, `cleanse_character(...)`.

**Tanggung jawab:**

- Menjalankan **full party turn-based battle**:
  - Tiap karakter (Aruna, Umar, Reza) mendapat giliran, lalu musuh.
  - `active_token` menentukan siapa yang bergerak.
  - Player memilih aksi per karakter:
    - Serang biasa.
    - Skill (sesuai skill list di `CharacterState.skills`).
    - Item (gunakan consumable dari inventory).
    - Bertahan (DEFEND).
    - Lari (RUN, logikanya sederhana).

- Menghitung **damage & efek skill**:
  - Tipe skill yang sudah di-handle:
    - `PHYS`, `MAG` – serangan fisik/magis.
    - `HEAL_SINGLE`, `HEAL_ALL`.
    - `BUFF_DEF_SELF`, `BUFF_SELF`, `BUFF_TEAM`.
    - `DEBUFF_ENEMY`.
    - `LIMIT_HEAL` (Aruna Core Awakening).
    - `CLEANSE`.
    - Dan bisa ditambah lainnya jika dibutuhkan.
  - Ada sistem elemen:
    - Element: `CAHAYA`, `GELAP`, `ALAM`, `NETRAL`.
    - Monster punya `weakness` dan `resist`.
    - Buff seperti `LIGHT_BUFF_TURNS` meningkatkan damage element cahaya.

- Drop & hadiah:
  - Setelah battle menang:
    - Distribusi XP ke `state.xp_pool[char_id]`.
    - Tambah Gold.
    - Panggil ProgressionAgent → `check_level_up(...)`.
    - Gunakan `DROP_TABLES` untuk random drop item (potion, equipment, dsb.) → `adjust_inventory`.
    - Kirim teks log lengkap “Kamu mendapatkan XP/GOLD/Item”.

- Kekalahan:
  - Untuk battle biasa, Aruna tidak langsung "Game Over" – ada mekanisme pemulihan minimal.
  - Untuk battle final Febri:
    - Jika kalah dan ada `loss_scene_after_battle="ENDING_BAD"` → langsung ke BAD END.

---

## 6. ProgressionAgent

**Lokasi kode utama:**

- Data:
  - `CHAR_BASE` – stat dasar per karakter (ARUNA, UMAR, REZA).
  - `CHAR_GROWTH` – pertumbuhan per level (HP, MP, ATK, DEF, MAG, SPD, LUCK).
  - `CHAR_SKILL_UNLOCKS` – mapping level → skill baru.
- Fungsi:
  - `xp_required_for_next_level(current_level)`
  - `grant_skill_to_character(character, skill_id, logs=None)`
  - `apply_growth(character)`
  - `check_level_up(state, logs=None)`

**Tanggung jawab:**

- Menyimpan XP per karakter di `state.xp_pool[char_id]`.
- Menentukan **XP yang dibutuhkan** untuk naik level dengan kurva eksponensial sederhana (`20 * 2^(level-1)`).
- Saat selesai battle:
  - XP ditambahkan ke pool.
  - `check_level_up`:
    - Jika XP cukup:
      - `level += 1`.
      - Terapkan `apply_growth` → naikkan HP/MP/ATK/DEF/MAG/SPD/LUCK.
      - Tambah log "X naik ke Level Y!" + ringkasan stat.
      - Cek `CHAR_SKILL_UNLOCKS` dan panggil `grant_skill_to_character`.
- Memberi skill spesial dari story:
  - `ARUNA_CORE_AWAKENING` saat main quest menuju Kampar (pointer).
  - `SAFIYAS_GRACE` saat `UMAR_QUEST_DONE`.
  - `MASTERS_LEGACY` saat `REZA_QUEST_DONE`.

---

## 7. Inventory/ItemAgent

**Status:** Sudah **diimplementasikan** dan aktif.

**Lokasi kode utama:**

- Data:
  - `ITEMS` – definisi semua item (consumable, weapon, armor, pedang warisan).
  - `EQUIP_BONUS_MAP` – mapping efek equipment ke atribut stat.
- Fungsi:
  - Inventory & drop:
    - `adjust_inventory(state, item_id, delta)`
    - `apply_item_effects_in_battle(...)`
    - `apply_consumable_outside_battle(...)`
  - Equipment:
    - `apply_equipment_stat_changes(character, item, direction)`
    - `equip_item(state, char_id, item_id)`
    - `unequip_item(state, char_id, slot)`
    - `get_equipped_owners(state, item_id)`
    - `get_character_passive_effects(character)`
    - `get_character_weapon_element(character)`
  - UI:
    - `send_inventory_menu(...)`
    - `prompt_inventory_target_selection(...)`
    - `apply_inventory_item_to_target(...)`
    - `send_equipment_menu(...)`
    - `send_character_equipment_menu(...)`
    - `handle_equip_item_selection(...)`
    - `handle_unequip_selection(...)`
  - Shop (lihat juga CityAgent):
    - `send_shop_menu(...)`
    - `send_shop_buy_menu(...)`
    - `send_shop_sell_menu(...)`
    - `handle_buy_item(...)`
    - `handle_sell_item(...)`

**Tanggung jawab:**

- **ITEMS dictionary**:
  - Contoh:
    - Potion kecil/sedang/besar (HP/MP).
    - Senjata awal (Pedang Kayu, Pedang Baja).
    - Armor dasar (Leather Armor, Light Robe, Mystic Cloak).
    - **Pedang Warisan Harsan** – senjata unik (tidak dijual di shop, hanya dari quest).
- Mengelola **inventory & drop**:
  - Drop random dari `DROP_TABLES` setelah battle.
  - Konsumsi item di battle (`BATTLE_ITEM` + `USE_ITEM|...`).
  - Konsumsi item di luar battle via `/inventory` → `MENU_INVENTORY`.
- **Equipment system**:
  - Weapon & armor terikat ke `CharacterState.weapon_id` dan `.armor_id`.
  - Saat equip:
    - Inventory berkurang.
    - Stat diubah sesuai `effects` (atk_bonus, def_bonus, hp_bonus, mp_bonus, dll).
  - Saat unequip:
    - Stat kembali normal; item kembali ke inventory.
- UI untuk player:
  - `/inventory` menampilkan:
    - daftar item + jumlah.
    - deskripsi.
    - equipment yang sedang terpasang di setiap karakter.
  - Di kota:
    - `MENU_EQUIPMENT` → pilih karakter → pilih equip/unequip.

---

## 8. PersistenceAgent (Save/Load)

**Status:** Sudah **diimplementasikan**.

**Lokasi kode utama:**

- Konstanta:
  - `SAVE_DIR` – direktori save.
- Fungsi:
  - `serialize_game_state(state) -> dict`
  - `deserialize_game_state(data, user_id) -> GameState`
  - `save_game_state(state)`
  - `load_game_state(user_id) -> Optional[GameState]`
- Command handler:
  - `save_cmd(update, context)`
  - `load_cmd(update, context)`

**Tanggung jawab:**

- Menyimpan **progress** pemain ke file JSON per user:
  - File: `saves/{user_id}.json`.
  - Menggunakan file `.tmp` lalu `os.replace` agar penulisan atomic (tidak corrupt).
- Data yang diserialisasi:
  - `scene_id`
  - `location`
  - `in_battle` (battle biasanya tidak disimpan; on load dianggap di luar battle).
  - `party` + semua `CharacterState` (level, stat, HP/MP, skills, weapon_id, armor_id).
  - `inventory`
  - `gold`
  - `xp_pool`
  - `flags`
  - `main_progress`
- `/save`:
  - Mengambil `GameState` current.
  - Memanggil `save_game_state`.
  - Balasan (Indonesia): `"Progress berhasil disimpan."`
- `/load`:
  - Membaca file JSON user.
  - Jika ada:
    - Buat `GameState` baru lewat `deserialize_game_state`.
    - `state.ensure_aruna()`.
    - Assign ke `USER_STATES[user_id]`.
    - Balasan: lokasi saat ini + saran `/status`.
  - Jika tidak ada:
    - Balasan: `"Belum ada file save untuk akun ini."`

---

## 9. Roadmap Lanjutan Berdasarkan Agent

Walaupun core RPG sudah berjalan cukup lengkap, masih ada ruang polish dan pengembangan:

1. **StoryAgent v2 (data-driven)**  
   - Pisahkan `SCENE_DATA` ke file JSON/YAML eksternal (mis. `data/scenes_main.json`, `data/scenes_sidequests.json`).  
   - Buat “story engine” generik agar pengubahan dialog & branching cukup edit file, bukan Python.

2. **BattleAgent v3**  
   - Manual target selection:
     - Pilih musuh/ally tertentu saat cast skill/item.
   - Tambah variasi AI musuh:
     - Skill musuh.
     - Prioritas target (misalnya fokus ke healer).

3. **Inventory/ItemAgent v2**  
   - Tambah lebih banyak equipment khusus (drop rare dari boss, reward quest).  
   - Tambah efek pasif yang lebih kompleks (lifesteal, reflect, resist element, dsb).

4. **ProgressionAgent v2**  
   - Fine-tuning XP curve & growth berdasarkan playtest.  
   - Tambah sistem job class atau talent pasif jika ingin.

5. **PersistenceAgent v2**  
   - Opsi multi-slot save.  
   - Opsi backup otomatis berkala.  
   - Migrasi ke storage lain (database) kalau user publik sudah banyak.

6. **Tooling untuk Admin / Live Ops**  
   - Command admin untuk:
     - melihat state player tertentu,
     - memberikan item/XP,
     - mengubah flag untuk debugging story.

---

Dengan struktur agent seperti ini, walaupun kode masih dalam satu file, kamu sudah punya desain modular yang jelas. Nanti kalau mau dipecah jadi:

- `agents/story.py`
- `agents/battle.py`
- `agents/world.py`
- `agents/city.py`
- `agents/progression.py`
- `agents/inventory.py`
- `agents/persistence.py`

…logika yang ada sekarang sudah siap dipindah tanpa banyak ubahan besar.
