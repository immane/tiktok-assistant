import asyncio
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


async def consume_gift_queue(
	queue: asyncio.Queue[GiftTask],
	sound_path: Optional[str],
	cooldown: float,
	trigger_hot_key: Optional[str],
) -> None:
	parsed_hot_key: Optional[list[Key | str]] = None
	if trigger_hot_key:
		try:
			parsed_hot_key = parse_trigger_hot_key(trigger_hot_key)
			print(f"[system] Hot key trigger enabled: {trigger_hot_key}", flush=True)
		except ValueError as exc:
			print(f"[system] Invalid --trigger-hot-key: {exc}", flush=True)
			parsed_hot_key = None

	while True:
		task = await queue.get()
		try:
			print(
				f"[{format_timestamp(task.created_at)}] [gift-queue] {task.description}",
				flush=True,
			)
			await play_alert(sound_path)

			# Calculate total diamonds for the gift task, treating missing diamond info as 0
			total_diamonds = (task.diamonds or 0) * max(task.repeat_count, 1)

			if parsed_hot_key and total_diamonds > 0:
				await asyncio.to_thread(fire_hot_key, parsed_hot_key, total_diamonds)
				print(
					f"[{format_timestamp(task.created_at)}] [hotkey-trigger] fired '{trigger_hot_key}' x{total_diamonds}",
					flush=True,
				)

			if cooldown > 0:
				await asyncio.sleep(cooldown)
		finally:
			queue.task_done()
