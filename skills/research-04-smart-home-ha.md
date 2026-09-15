# Ei Adapted Skill — Smart-Home Control Knowledge (Home Assistant)

- **Source skill:** `home-assistant` — mezzle/ai-skills
  (`https://github.com/mezzle/ai-skills/blob/main/home-assistant/SKILL.md`)
  via web search (top SkillsMP-adjacent HA skill). Also cross-checked against the
  SkillsMP `smart-home` result: "Control the user's smart-home devices through Home
  Assistant — lights, switches, fans, covers/blinds, and scenes on their local
  network. Use WHENEVER the user wants to check or change something physical."
- **License:** MIT (declared in source SKILL.md frontmatter).
- **Original trigger:** "Use when the user asks about smart home, Home Assistant,
  lights, switches, sensors, thermostats, automation, or home control."
  (Original drives HA via Node.js scripts + `HOME_ASSISTANT_URL`/`HOME_ASSISTANT_TOKEN`.)
- **Why picked:** Only HA skill with a full domain×service matrix + state/history/event
  checklist, MIT-licensed. Ei already has `ha_control` (HA REST + `HA_URL`/`HA_TOKEN`);
  this file maps the source knowledge onto it and proposes exactly ONE read-only tool
  to close the "is the X on?" gap.

## Ei tool mapping

- Existing: `ha_control(entity_id, action, brightness)` in `tools/home_assistant.py`
  (POST `{HA_URL}/api/services/<domain>/<action>`, `requires_confirmation` per registry).
  - light/switch/scene/script → `turn_on | turn_off | toggle` (+ `brightness` 1–100 for lights)
  - cover → `open_cover | close_cover | stop_cover` (pass through `action` as-is)
  - climate → `set_temperature` (+ temperature via brightness-equivalent param — see proposal)
  - media_player → `volume_set`, automation → `trigger`
- Voice intent → tool call examples:
  - "allume le salon" → `ha_control("light.salon", "turn_on")`
  - "éteins tout" → one call per known light/switch entity (or scene: `scene.tout_eteindre`)
  - "tamis la chambre à 30%" → `ha_control("light.chambre", "turn_on", brightness=30)`
  - "ferme les volets" → `ha_control("cover.salon", "close_cover")`
  - "mets 21 degrés" → `ha_control("climate.thermostat", "set_temperature")` (needs payload fix — see proposal)
- If `HA_URL`/`HA_TOKEN` unset → reply "Home Assistant n'est pas configuré" (existing behavior).

## Safety rules for Ei (voice-first, French home)

1. Voice commands map to `ha_control` ONLY; never expose tokens or raw URLs in speech.
2. `toggle` when the current state is unknown (no state tool yet) to avoid wrong-way actions.
3. Scenes (`scene.*`) preferred for multi-device orders ("mode ciné", "bonne nuit").
4. Confirm before: locks, covers (blinds), thermostat setpoints, anything outside
   light/switch domains.

## Precise NEW Tool() proposal (ONE tool, closes the read gap)

The source skill's "Getting Entity States" has no Ei equivalent — Ei cannot answer
"la lumière du salon est-elle allumée ?" or read sensors/thermostats today.

```python
# tools/home_assistant.py (new, beside ha_control)
@tool_registry.register(
    name="ha_get_state",
    description="Lit l'état actuel d'une entité Home Assistant (lumière, capteur, thermostat)",
    parameters={"entity_id": "str (ex: light.salon, sensor.temperature, climate.thermostat)"}
)
def ha_get_state(entity_id: str) -> Dict[str, Any]:
    # GET {HA_URL}/api/states/<entity_id> with Bearer HA_TOKEN, timeout 5
    # return {"speech": ..., "data": {"state": ..., "attributes": {...}}}
```

- `category="home"`, read-only → `requires_confirmation=False`.
- Second (optional, later): extend `ha_control` payload with a generic
  `service_data: dict` so climate `temperature`, light `rgb_color`, cover `position`
  work without new tools. Not required for v1.
