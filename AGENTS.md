# AGENTS.md
# Legends of Aruna: Journey to Kampar – Agent Design (Implementasi Saat Ini)

Dokumen ini menjelaskan pembagian *agent logis* (modul logika) di dalam
kode `LEGENDS_OF_ARUNA_JOURNEY_TO_KAMPAR.py`.  
Semuanya masih berada di satu file Python, tetapi secara konsep
dibagi menjadi beberapa agent agar pengembangan dan refactor ke depan
lebih mudah.

---

## 0. Gambaran Besar

Alur utama:

1. User mengirim perintah (`/start`, `/status`, `/map`) atau menekan inline button.
2. Handler Telegram (`start`, `status_cmd`, `map_cmd`, `button`) memanggil fungsi-fungsi logika.
3. Logika dipisah secara mental menjadi beberapa agent:

   - **GameMasterAgent** – orkestrator; pusat routing input → agent lain.
   - **StoryAgent** – mengurus scene & dialog cerita.
   - **WorldAgent** – mengurus world map dan perpindahan kota/hutan.
   - **CityAgent** – mengurus menu kota, job, penginapan, klinik, shop.
   - **BattleAgent** – mengurus encounter, perhitungan damage, skill.
   - **ProgressionAgent** – mengurus XP, level up, growth stat, unlock skill.
   - **(Planned) Inventory/ItemAgent** – sistem item & equipment.
   - **(Planned) PersistenceAgent** – save/load state ke storage permanen.

Semua state pemain berada di struktur `GameState` per `user_id`.

---

## 1. GameMasterAgent

**Lokasi kode utama:**

- `main()` – setup `Application`, register handler.
- `button()` – handler utama untuk semua `callback_data`.
- `get_game_state()` – inisialisasi dan akses `GameState` per user.

**Tanggung jawab:**

- Menerima input dari Telegram dan memutuskan akan diarahkan ke logika apa:
  - Prefix `BATTLE_` → BattleAgent.
  - `USE_SKILL|...` → BattleAgent.
  - `GOTO_CITY|...`, `ENTER_DUNGEON` → WorldAgent.
  - `MENU_*`, `QUEST_*`, `EVENT_*`, `DO_JOB|...` → CityAgent / StoryAgent.
  - Lainnya (scene id) → StoryAgent.
- Menjaga satu sumber kebenaran state: `USER_STATES[user_id]`.

**Catatan:**

Saat refactor ke banyak file, agent ini bisa jadi modul `router` yang memanggil fungsi dari modul lain.


---

## 2. StoryAgent

**Lokasi kode utama:**

- `SCENE_DATA` – kamus semua scene & ending.
- `send_scene()` – render teks dan tombol dari `SCENE_DATA`.
- `handle_scene_choice()` – menangani transisi antar scene, termasuk trigger battle & event.  

**Tanggung jawab:**

- Menyimpan dan menampilkan seluruh narasi & dialog:
  - Prolog Selatpanjang (CH0).
  - Chapter Siak (Umar).
  - Chapter Rengat (Reza).
  - Chapter Pekanbaru (rumor & mimpi).
  - Chapter Kampar & Kastil (floors & Febri).
  - Side quest Umar & Reza.
  - Ending GOOD / TRUE / BAD.
- Menggerakkan story dengan `scene_id` di `GameState`.
- Men-set flag terkait story:
  - `HAS_UMAR`, `HAS_REZA`.
  - `UMAR_QUEST_DONE`, `REZA_QUEST_DONE`.
  - `VISITED_SIAK`, `VISITED_RENGAT`, `VISITED_PEKANBARU`, `VISITED_KAMPAR`.
- Memanggil BattleAgent untuk battle skenario:
  - `BATTLE_TUTORIAL_1`.
  - `BATTLE_SIAK_GATE`, `BATTLE_RENGAT_GOLEM`.
  - `BATTLE_HOUND_OF_VOID`, `BATTLE_VOID_SENTINEL`, `BATTLE_FEBRI`.

**Contoh alur:**

- Dari scene `CH1_UMAR_CLINIC` → player pilih → `CH1_UMAR_CORE` → Umar join (lewat `SIAK_CITY_MENU_AFTER_UMAR`).
- Di scene `CH5_FLOOR5` → pilihan `"BATTLE_FEBRI"` → `start_story_battle(..., "FEBRI_LORD", "CH5_FINAL_WIN", loss_scene="ENDING_BAD")`.

---

## 3. WorldAgent

**Lokasi kode utama:**

- `LOCATIONS` – definisi kota + `min_level` dan fitur.
- `NEAREST_DUNGEON` – map lokasi → area hutan/dungeon.
- `WORLD_MAP_ASCII` – layout world map.
- `send_world_map()` – kirim ASCII map + tombol tujuan.
- Bagian `button()` yang menangani:
  - `GOTO_CITY|...`
  - `ENTER_DUNGEON`.

**Tanggung jawab:**

- Menampilkan world map lengkap + status Main Quest.
- Mengatur perpindahan antar kota:
  - Cek `min_level` sebelum boleh masuk.
  - Jika baru pertama kali, trigger scene entry (Siak/Rengat/Pekanbaru/Kampar).
  - Jika sudah pernah, langsung `send_city_menu()`.
- Mengatur akses ke area hutan:
  - `ENTER_DUNGEON` → info area + tombol “Cari monster” (battle) atau “Kembali ke kota”.

**Perilaku penting:**

- Level gating:
  - Jika Aruna level < `LOCATIONS[loc_id]["min_level"]`, user ditolak masuk dengan pesan khusus.
- Di Kampar:
  - Tidak ada toko/job/inn (type CURSED, `has_* = False`).
  - Hanya bisa ke hutan Kampar dan Kastil Febri.

---

## 4. CityAgent

**Lokasi kode utama:**

- `CITY_FEATURES` – deskripsi kota, shop item, biaya inn, job.
- `send_city_menu()` – menu utama kota.
- Bagian `button()` untuk:
  - `MENU_STATUS`
  - `MENU_SHOP`
  - `MENU_JOB`
  - `MENU_INN`
  - `MENU_CLINIC`
  - `BACK_CITY_MENU`
  - Event kota & side quest:
    - `EVENT_SIAK_GATE`, `EVENT_PEKANBARU_CAFE`, `EVENT_KASTIL_ENTRY`.
    - `QUEST_UMAR`, `QUEST_REZA`.
- `send_job_menu()` dan `resolve_job()` – sistem kerja.

**Tanggung jawab:**

- Menyajikan aktivitas kota:
  - Lihat status party.
  - Pergi ke shop (sementara hanya tampilan list).
  - Bekerja (job) untuk mendapatkan Gold.
  - Menginap di penginapan (heal full dengan biaya).
  - Ke klinik (Siak → trigger Umar).
- Menjadi “hub” untuk event lokal:
  - Side quest Umar di Siak.
  - Side quest Reza di Rengat.
  - Event rumor kafe di Pekanbaru.
  - Masuk ke Kastil dari Kampar.

**Status implementasi:**

- **Job**: sudah penuh (payout, fail chance, hadiah Gold).
- **Penginapan**: sudah penuh (cek biaya, kurangi Gold, restore HP/MP).
- **Klinik**: trigger Umar join dan dialog setelah join.
- **Shop**: masih tampilan list item, belum ada sistem beli/jual & inventory.

---

## 5. BattleAgent

**Lokasi kode utama:**

- Data:
  - `MONSTERS` – stat & drop musuh.
- Fungsi:
  - `pick_random_monster_for_area()`
  - `create_enemy_from_key()`
  - `start_random_battle()`
  - `start_story_battle()`
  - `battle_status_text()`
  - `send_battle_state()`
  - `process_battle_action()`
  - `process_use_skill()`
  - `end_battle_and_return()`
  - Buff helper: `reset_battle_flags()`, `tick_buffs()`.

**Tanggung jawab:**

- Membuat encounter:
  - Random di hutan (berdasarkan `NEAREST_DUNGEON`).
  - Spesifik untuk story (musuh by key: GOLEM, HOUND, SENTINEL, FEBRI).
- Mengelola state battle:
  - `state.in_battle`
  - `state.battle_enemies`
  - `state.return_scene_after_battle` (untuk story)
  - `state.loss_scene_after_battle` (contoh: BAD END vs Febri).
- Menghitung damage & efek:
  - Serangan fisik & magic (power, sedikit randomizer).
  - Skill heal single & heal all.
  - Buff defense Aruna.
  - Limit break Aruna Core (heal party + buff cahaya).
- Menentukan hasil:
  - Jika musuh mati:
    - Bagi XP & Gold ke semua anggota `party_order`.
    - Panggil ProgressionAgent (check_level_up).
    - Kembali ke scene (kalau battle story) atau ke menu hutan.
  - Jika Aruna kalah:
    - Set HP Aruna ke sebagian kecil untuk mencegah softlock.
    - Di battle final Febri, bisa trigger BAD END lewat `loss_scene_after_battle`.

**Status implementasi:**

- **Saat ini**:
  - Hanya Aruna yang di-handle di menu skill & serangan.
  - Musuh hanya menyerang Aruna.
- **Sudah siap untuk diperluas**:
  - `process_use_skill()` sudah support `char_id` (Aruna/Umar/Reza).
  - Tinggal kembangkan menu skill agar bisa memilih skill Umar/Reza dan, nanti, sistem turn multi-anggota.

---

## 6. ProgressionAgent

**Lokasi kode utama:**

- Data:
  - `CHAR_BASE`, `CHAR_GROWTH`, `CHAR_SKILL_UNLOCKS`.
- Fungsi:
  - `xp_required_for_next_level()`
  - `grant_skill_to_character()`
  - `apply_growth()`
  - `check_level_up()`
- Logika tambahan di StoryAgent:
  - Memberi skill khusus:
    - `ARUNA_CORE_AWAKENING` saat Kampar pointer.
    - `SAFIYAS_GRACE` saat Umar quest selesai.
    - `MASTERS_LEGACY` saat Reza quest selesai.

**Tanggung jawab:**

- Menyimpan XP di `state.xp_pool[char_id]`.
- Menentukan kapan karakter naik level:
  - XP requirement eksponensial (20 * 2^(level-1)).
  - Growth stat per karakter (ARUNA/UMAR/REZA).
- Meng-unlock skill baru di level tertentu:
  - Meng-update `character.skills`.
- Memberi log level up:
  - `"Aruna naik ke Level X!"`
  - Tampilkan stat baru singkat.

---

## 7. (Planned) Inventory/ItemAgent

**Status:** Belum diimplementasikan penuh, tapi rencana ke depan:

**Tanggung jawab:**

- Menyimpan jumlah item di `state.inventory`.
- Mengurus:
  - Beli item di shop (kurangi Gold, tambah inventory).
  - Pakai item di battle (`BATTLE_ITEM` → pilih item → efek).
  - Equip senjata/armor dan pengaruhnya ke stat.
- Menentukan data item:
  - `ITEMS` dictionary dengan:
    - nama, tipe (consumable/equipment), harga, efek (HP/MP, ATK/DEF, dsb).

---

## 8. (Planned) PersistenceAgent (Save/Load)

**Status:** Belum ada di kode; saat ini state hanya di memory.

**Tugas yang direncanakan:**

- `/save` – menyimpan `GameState` user ke storage permanen (JSON file / DB).
- `/load` – memuat kembali `GameState`.
- Auto-save di momen penting:
  - Setelah boss.
  - Setelah menyelesaikan chapter atau side quest.

**Target:**

- Format serialisasi aman:
  - scene_id, location, party, inventory, gold, xp_pool, flags, dsb.

---

## 9. Roadmap Lanjutan Berdasarkan Agent

1. **BattleAgent v2**
   - Menu skill multi-anggota (Aruna/Umar/Reza).
   - Musuh bisa target selain Aruna.
   - Nanti bisa kembangkan sistem turn order berbasis SPD.

2. **Inventory/ItemAgent v1**
   - Sistem beli di shop (harga, Gold).
   - System item battle (Potion, Ether, dsb).

3. **PersistenceAgent v1**
   - Save/load sederhana (JSON per user).

4. **Skill System v2**
   - Implement tipe skill lain:
     - BUFF_TEAM, DEBUFF_ENEMY, CLEANSE, REVIVE, dsb.

5. **Polish & Balancing**
   - Tuning XP requirement.
   - Tuning stat monster.
   - Penyesuaian job payout vs harga item.

---

Dengan arsitektur agent seperti ini, meskipun sekarang masih 1 file,
kamu sudah punya kerangka yang rapi untuk nanti di-split menjadi
beberapa modul (`story.py`, `battle.py`, `world.py`, dll) tanpa
mengubah logika besar.
