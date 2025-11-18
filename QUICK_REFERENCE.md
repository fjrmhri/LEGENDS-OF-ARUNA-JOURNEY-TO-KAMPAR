# Quick Reference: Code Changes

## Line Numbers & Changes

### New Functions

**Line ~2036:** `get_living_enemies(state: GameState)`
- Helper function to get list of living enemies
- Returns `List[Dict[str, Any]]`
- Used by both attack and skill targeting logic

**Line ~2617:** `start_fixed_battle(update, context, state, monster_key)`
- Starts battle with specific monster (not random)
- Used for tutorial and special story battles
- Similar to `start_story_battle()` but simpler

### Modified Functions

**Line ~3319:** `process_battle_action()` - BATTLE_ATTACK section
- **Before:** Always showed target selection menu
- **After:** 
  - 1 enemy: Direct attack (no menu)
  - 2+ enemies: Shows target selection menu
- Direct attack includes full damage calculation and log

**Line ~3460:** `process_use_skill()` - Target handling
- **Before:** Always showed menu for single-target skills
- **After:**
  - Enemy skill + 1 living enemy: Direct execution
  - Enemy skill + 2+ enemies: Shows menu
  - Ally skills: Unchanged (always show menu)

**Line ~3882:** `handle_story_battle_trigger()` - Random battle type
- **Before:** All "random" type battles used `start_random_battle()`
- **After:** `BATTLE_TUTORIAL_1` uses `start_fixed_battle()` with "SHADOW_SLIME"
- Other random battles unchanged

## Key Behaviors

### Tutorial Battle Flow
1. User clicks "Hadapi Shadow Slime" in CH0_S3
2. Callback triggers `BATTLE_TUTORIAL_1`
3. `handle_story_battle_trigger()` detects special case
4. Calls `start_fixed_battle(update, context, state, "SHADOW_SLIME")`
5. Battle state initialized with Shadow Slime
6. After victory, `end_battle_and_return()` transitions to CH0_S4_POST_BATTLE

### Single Enemy Attack Flow
1. User clicks "Serang" (BATTLE_ATTACK)
2. `process_battle_action()` checks living enemies
3. If 1 enemy: Calculate damage → Apply damage → Log → `conclude_player_turn()`
4. If 2+ enemies: Store pending_action → `show_pending_target_prompt()`

### Single Enemy Skill Flow
1. User selects skill from menu
2. `process_use_skill()` checks skill target type
3. If ENEMY target + 1 living enemy: Execute skill directly → `conclude_player_turn()`
4. If ENEMY target + 2+ enemies: Store pending_action → `show_pending_target_prompt()`
5. If ALLY target: Always show menu (unchanged)

## Testing Commands

```bash
# Syntax check
python3 -m py_compile LEGENDS_OF_ARUNA_JOURNEY_TO_KAMPAR.py

# Run bot (requires valid token)
python3 LEGENDS_OF_ARUNA_JOURNEY_TO_KAMPAR.py
```

## Integration Points

The changes integrate cleanly with existing systems:
- ✅ Battle state management
- ✅ Turn order system  
- ✅ Damage calculation
- ✅ Buff/debuff system
- ✅ Scene transitions
- ✅ Save/load system
- ✅ Logging system

No breaking changes to any existing functionality.
