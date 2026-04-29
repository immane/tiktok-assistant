import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable, Iterable, Optional

from deep_translator import GoogleTranslator
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent, GiftEvent, LiveEndEvent

try:
	from TikTokLive.events import LikeEvent
except Exception:
	LikeEvent = None


@dataclass(slots=True)
class GiftTask:
	created_at: datetime
	user_name: str
	gift_name: str
	repeat_count: int
	diamonds: Optional[int]
	description: str


def safe_getattr(obj: object, name: str) -> object:
	try:
		return getattr(obj, name)
	except Exception:
		return None


def value_from_source(source: object, attr_names: Iterable[str]) -> Optional[str]:
	if source is None:
		return None

	if isinstance(source, dict):
		for attr in attr_names:
			value = source.get(attr)
			if value:
				return str(value)
		return None

	for attr in attr_names:
		value = safe_getattr(source, attr)
		if value:
			return str(value)
	return None


def event_user_name(event: object) -> str:
	attr_candidates = (
		"nickname",
		"nick_name",
		"display_id",
		"unique_id",
		"sec_uid",
	)

	for source in (
		safe_getattr(event, "user_info"),
		safe_getattr(event, "user"),
	):
		value = value_from_source(source, attr_candidates)
		if value:
			return value

	return "unknown-user"


def event_gift_name(event: GiftEvent) -> str:
	gift = getattr(event, "gift", None)
	for attr in ("name", "describe"):
		value = getattr(gift, attr, None)
		if value:
			return str(value)
	return "unknown-gift"


def event_gift_diamonds(event: GiftEvent) -> Optional[int]:
	gift = getattr(event, "gift", None)
	for attr in ("diamond_count", "diamonds"):
		value = getattr(gift, attr, None)
		if isinstance(value, int):
			return value
	return None


def event_repeat_count(event: GiftEvent) -> int:
	repeat_count = getattr(event, "repeat_count", None)
	if isinstance(repeat_count, int) and repeat_count > 0:
		return repeat_count
	return 1


def is_final_gift_event(event: GiftEvent) -> bool:
	if not getattr(event, "streaking", False):
		return True

	gift = getattr(event, "gift", None)
	gift_info = getattr(gift, "info", None)
	gift_type = getattr(gift_info, "type", None)
	return gift_type != 1


def format_timestamp(value: datetime) -> str:
	return value.strftime("%H:%M:%S")


def _likes_as_int(value: object) -> Optional[int]:
	if isinstance(value, int):
		return value
	if isinstance(value, str):
		try:
			return int(value)
		except ValueError:
			return None
	return None


def event_total_likes(event: object) -> Optional[int]:
	for attr in ("total", "total_likes", "like_count", "likes"):
		value = _likes_as_int(safe_getattr(event, attr))
		if value is not None and value > 0:
			return value

	stats = safe_getattr(event, "room_stats")
	if stats is not None:
		for attr in ("total_like", "like_count", "likes"):
			value = _likes_as_int(safe_getattr(stats, attr))
			if value is not None and value > 0:
				return value

	return None


def event_like_increment(event: object) -> int:
	for attr in ("count", "like_count", "likes"):
		value = _likes_as_int(safe_getattr(event, attr))
		if value is not None and value > 0:
			return value
	return 1


class LikesProgressReporter:
	def __init__(self, interval_seconds: float = 30.0) -> None:
		self._interval_seconds = interval_seconds
		self._running_likes = 0
		self._report_task: Optional[asyncio.Task[None]] = None
		self._active = False

	def start(self) -> None:
		if self._report_task is not None:
			return
		self._active = True
		self._report_task = asyncio.create_task(self._run())

	async def stop(self) -> None:
		self._active = False
		if self._report_task is None:
			return
		self._report_task.cancel()
		try:
			await self._report_task
		except asyncio.CancelledError:
			pass
		self._report_task = None

	async def _run(self) -> None:
		from main import BLUE, RESET

		try:
			while self._active:
				await asyncio.sleep(self._interval_seconds)
				print(
					f"[{format_timestamp(datetime.now())}] {BLUE}[likes]{RESET} total={self._running_likes}",
					flush=True,
				)
		except asyncio.CancelledError:
			pass

	async def on_like(self, event: object) -> None:
		total_likes = event_total_likes(event)
		if total_likes is not None:
			self._running_likes = max(self._running_likes, total_likes)
		else:
			self._running_likes += event_like_increment(event)


async def translate_to_chinese(text: str) -> Optional[str]:
	if not text or not text.strip():
		return None
	try:
		result = await asyncio.to_thread(
			GoogleTranslator(source="auto", target="zh-CN").translate, text
		)
		if result and result.strip() and result.strip() != text.strip():
			return result.strip()
	except Exception:
		pass
	return None


def register_event_handlers(
	client: TikTokLiveClient,
	unique_id: str,
	queue: asyncio.Queue[GiftTask],
	watched_gifts: set[str],
	show_comments: bool,
	likes_trigger: Optional[Callable[[object], Awaitable[None]]] = None,
) -> None:
	# Import colors here to avoid circular import
	from main import GREEN, RESET
	likes_reporter = LikesProgressReporter()

	@client.on(ConnectEvent)
	async def on_connect(_: ConnectEvent) -> None:
		likes_reporter.start()
		print(f"[system] Connected to @{unique_id}", flush=True)

	@client.on(CommentEvent)
	async def on_comment(event: CommentEvent) -> None:
		try:
			if not show_comments:
				return

			comment_text = getattr(event, "comment", "")
			translation = await translate_to_chinese(comment_text)
			suffix = f"（{translation}）" if translation else ""
			print(
				f"[{format_timestamp(datetime.now())}] [comment] {event_user_name(event)}: {comment_text}{suffix}",
				flush=True,
			)
		except Exception as exc:
			print(f"[system] Comment handler error: {exc}", flush=True)

	@client.on(GiftEvent)
	async def on_gift(event: GiftEvent) -> None:
		try:
			if not is_final_gift_event(event):
				return

			gift_name = event_gift_name(event)
			if watched_gifts and gift_name.casefold() not in watched_gifts:
				return

			repeat_count = event_repeat_count(event)
			diamonds = event_gift_diamonds(event)
			user_name = event_user_name(event)
			description = f"{user_name} sent <{gift_name}> x{repeat_count}"
			if diamonds is not None:
				description = f"{description} ({diamonds} diamonds each)"

			await queue.put(
				GiftTask(
					created_at=datetime.now(),
					user_name=user_name,
					gift_name=gift_name,
					repeat_count=repeat_count,
					diamonds=diamonds,
					description=description,
				)
			)
			print(
				f"[{format_timestamp(datetime.now())}] {GREEN}[gift-detected]{RESET} queued -> {description}",
				flush=True,
			)
		except Exception as exc:
			print(f"[system] Gift handler error: {exc}", flush=True)

	if LikeEvent is not None:
		@client.on(LikeEvent)
		async def on_like(event: object) -> None:
			try:
				await likes_reporter.on_like(event)
				if likes_trigger:
					await likes_trigger(event)
			except Exception as exc:
				print(f"[system] Like handler error: {exc}", flush=True)
	elif likes_trigger and LikeEvent is None:
		print("[system] Likes trigger unavailable: LikeEvent is not supported by this TikTokLive version", flush=True)

	@client.on(LiveEndEvent)
	async def on_live_end(_: LiveEndEvent) -> None:
		await likes_reporter.stop()
		print("[system] Live ended", flush=True)

	@client.on(DisconnectEvent)
	async def on_disconnect(_: DisconnectEvent) -> None:
		await likes_reporter.stop()
		print("[system] Disconnected", flush=True)
