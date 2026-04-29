import asyncio
from datetime import datetime
from typing import Awaitable, Callable, Optional

from gift_queue import fire_hot_key, parse_trigger_hot_key

YELLOW = "\033[33m"
RESET = "\033[0m"


def _format_timestamp(value: datetime) -> str:
	return value.strftime("%H:%M:%S")


def _as_int(value: object) -> Optional[int]:
	if isinstance(value, int):
		return value
	if isinstance(value, str):
		try:
			return int(value)
		except ValueError:
			return None
	return None


def _nested(source: object, attr: str) -> object:
	try:
		return getattr(source, attr)
	except Exception:
		return None


def _extract_total_likes(event: object) -> Optional[int]:
	# Try common total-like fields used by TikTokLive events.
	for attr in ("total", "total_likes", "like_count", "likes"):
		value = _as_int(_nested(event, attr))
		if value is not None and value > 0:
			return value

	stats = _nested(event, "room_stats")
	if stats is not None:
		for attr in ("total_user", "total_like", "like_count", "likes"):
			value = _as_int(_nested(stats, attr))
			if value is not None and value > 0:
				return value

	return None


def _extract_like_increment(event: object) -> int:
	for attr in ("count", "like_count", "likes"):
		value = _as_int(_nested(event, attr))
		if value is not None and value > 0:
			return value
	return 1


class LikesThresholdTrigger:
	def __init__(self, trigger_key: str, threshold: int) -> None:
		self._parsed_key = parse_trigger_hot_key(trigger_key)
		self._trigger_key = trigger_key
		self._threshold = max(threshold, 1)
		self._next_threshold = self._threshold
		self._running_likes = 0

	async def on_like(self, event: object) -> None:
		total_likes = _extract_total_likes(event)
		should_trigger = False

		if total_likes is not None:
			while total_likes >= self._next_threshold:
				should_trigger = True
				self._next_threshold += self._threshold
			self._running_likes = max(self._running_likes, total_likes)
			current_likes = total_likes
		else:
			self._running_likes += _extract_like_increment(event)
			while self._running_likes >= self._next_threshold:
				should_trigger = True
				self._next_threshold += self._threshold
			current_likes = self._running_likes

		if not should_trigger:
			return

		try:
			await asyncio.to_thread(fire_hot_key, self._parsed_key, 1)
			print(
				f"[{_format_timestamp(datetime.now())}] {YELLOW}[likes-trigger]{RESET} "
				f"fired '{self._trigger_key}' x1 (likes={current_likes}, threshold={self._threshold})",
				flush=True,
			)
		except Exception as exc:
			print(f"[system] Likes trigger failed ({self._trigger_key}): {exc}", flush=True)


def create_likes_trigger_handler(
	trigger_key: str,
	threshold: int,
) -> Callable[[object], Awaitable[None]]:
	trigger = LikesThresholdTrigger(trigger_key=trigger_key, threshold=threshold)
	return trigger.on_like
