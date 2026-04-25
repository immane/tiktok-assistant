import asyncio
from typing import Optional

from event_handlers import GiftTask, format_timestamp

try:
	import winsound
except ImportError:
	winsound = None


async def play_alert(sound_path: Optional[str]) -> None:
	if winsound is None:
		print("[alert] winsound unavailable, skipping sound", flush=True)
		return

	if sound_path:
		winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
		return

	winsound.MessageBeep(winsound.MB_ICONASTERISK)


async def consume_gift_queue(queue: asyncio.Queue[GiftTask], sound_path: Optional[str], cooldown: float) -> None:
	while True:
		task = await queue.get()
		try:
			print(
				f"[{format_timestamp(task.created_at)}] [gift-queue] {task.description}",
				flush=True,
			)
			await play_alert(sound_path)
			if cooldown > 0:
				await asyncio.sleep(cooldown)
		finally:
			queue.task_done()
