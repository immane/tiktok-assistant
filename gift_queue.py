import asyncio
import json
from dataclasses import dataclass
from typing import Optional

from event_handlers import GiftTask, format_timestamp
from pynput.keyboard import Controller, Key

try:
	import winsound
except ImportError:
	winsound = None


SPECIAL_KEYS = {
	"ctrl": Key.ctrl,
	"control": Key.ctrl,
	"alt": Key.alt,
	"shift": Key.shift,
	"cmd": Key.cmd,
	"win": Key.cmd,
	"meta": Key.cmd,
	"enter": Key.enter,
	"return": Key.enter,
	"tab": Key.tab,
	"space": Key.space,
	"esc": Key.esc,
	"escape": Key.esc,
	"up": Key.up,
	"down": Key.down,
	"left": Key.left,
	"right": Key.right,
	"backspace": Key.backspace,
	"delete": Key.delete,
	"home": Key.home,
	"end": Key.end,
	"pageup": Key.page_up,
	"pagedown": Key.page_down,
	"insert": Key.insert,
}

for i in range(1, 13):
	SPECIAL_KEYS[f"f{i}"] = getattr(Key, f"f{i}")


def parse_trigger_hot_key(spec: str) -> list[Key | str]:
	normalized = spec.strip().replace("+", "-")
	if not normalized:
		raise ValueError("Hot key cannot be empty")

	parts = [p.strip().lower() for p in normalized.split("-") if p.strip()]
	if not parts:
		raise ValueError("Hot key cannot be empty")

	parsed: list[Key | str] = []
	for part in parts:
		if part in SPECIAL_KEYS:
			parsed.append(SPECIAL_KEYS[part])
		elif len(part) == 1:
			parsed.append(part)
		else:
			raise ValueError(
				f"Unsupported hot key token '{part}'. Use single key like 'x' or combo like 'ctrl-v'."
			)

	return parsed


def fire_hot_key(keys: list[Key | str], times: int) -> None:
	if times <= 0:
		return

	controller = Controller()

	for _ in range(times):
		if len(keys) == 1:
			key = keys[0]
			controller.press(key)
			controller.release(key)
			continue

		modifiers = keys[:-1]
		main_key = keys[-1]

		for key in modifiers:
			controller.press(key)

		controller.press(main_key)
		controller.release(main_key)

		for key in reversed(modifiers):
			controller.release(key)


async def play_alert(sound_path: Optional[str]) -> None:
	if winsound is None:
		print("[alert] winsound unavailable, skipping sound", flush=True)
		return

	if sound_path:
		winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
		return

	winsound.MessageBeep(winsound.MB_ICONASTERISK)


@dataclass(slots=True)
class TriggerRule:
	trigger: str          # gift name (casefolded) or "[default]"
	keys: list[Key | str]
	repeats: Optional[int]  # None means use task.diamonds
	raw_action_key: str


def parse_triggers_json(json_str: str) -> list[TriggerRule]:
	"""Parse --triggers JSON array into a list of TriggerRule."""
	try:
		items = json.loads(json_str)
		if not isinstance(items, list):
			raise ValueError("--triggers must be a JSON array")
	except json.JSONDecodeError as exc:
		raise ValueError(f"--triggers is not valid JSON: {exc}") from exc

	rules: list[TriggerRule] = []
	for i, item in enumerate(items):
		if not isinstance(item, dict):
			raise ValueError(f"--triggers item {i} must be an object")
		trigger = item.get("trigger", "")
		action_key = item.get("action-key", "")
		if not trigger:
			raise ValueError(f"--triggers item {i} missing 'trigger'")
		if not action_key:
			raise ValueError(f"--triggers item {i} missing 'action-key'")
		raw_repeats = item.get("repeats")
		repeats: Optional[int] = None
		if raw_repeats is not None:
			if not isinstance(raw_repeats, int) or raw_repeats < 0:
				raise ValueError(f"--triggers item {i} 'repeats' must be a non-negative int")
			repeats = raw_repeats
		keys = parse_trigger_hot_key(action_key)
		normalized_trigger = trigger if trigger == "[default]" else trigger.strip().casefold()
		rules.append(TriggerRule(trigger=normalized_trigger, keys=keys, repeats=repeats, raw_action_key=action_key))
	return rules


async def _fire_rule(rule: TriggerRule, diamonds: int, created_at: object) -> None:
	# Import colors here to avoid circular import
	from main import YELLOW, RESET
	
	times = rule.repeats if rule.repeats is not None else diamonds
	if times <= 0:
		return
	try:
		await asyncio.to_thread(fire_hot_key, rule.keys, times)
		print(
			f"[{format_timestamp(created_at)}] {YELLOW}[hotkey-trigger]{RESET} fired '{rule.raw_action_key}' x{times}",
			flush=True,
		)
	except Exception as exc:
		print(f"[system] Hotkey trigger failed ({rule.raw_action_key}): {exc}", flush=True)


async def consume_gift_queue(
	queue: asyncio.Queue[GiftTask],
	sound_path: Optional[str],
	cooldown: float,
	triggers_json: Optional[str],
) -> None:
	rules: list[TriggerRule] = []
	if triggers_json:
		try:
			rules = parse_triggers_json(triggers_json)
			print(f"[system] Loaded {len(rules)} trigger rule(s)", flush=True)
		except ValueError as exc:
			print(f"[system] Invalid --triggers: {exc}", flush=True)

	default_rules = [r for r in rules if r.trigger == "[default]"]
	named_rules = [r for r in rules if r.trigger != "[default]"]

	while True:
		task = await queue.get()
		try:
			"""
			print(
				f"[{format_timestamp(task.created_at)}] [gift-queue] {task.description}",
				flush=True,
			)
			"""
			try:
				await play_alert(sound_path)
			except Exception as exc:
				print(f"[system] Alert playback failed: {exc}", flush=True)

			total_diamonds = task.diamonds or 0
			norm_gift = task.gift_name.strip().casefold()

			# Find matching named rules for this gift
			matched = [r for r in named_rules if r.trigger == norm_gift]

			# [default] fires only when no named rule matched
			active_rules = matched if matched else default_rules

			if active_rules and total_diamonds >= 0:
				# Fire all active rules concurrently
				await asyncio.gather(
					*[_fire_rule(r, total_diamonds, task.created_at) for r in active_rules]
				)

			if cooldown > 0:
				await asyncio.sleep(cooldown)
		except Exception as exc:
			print(f"[system] Gift queue processing error: {exc}", flush=True)
		finally:
			queue.task_done()
