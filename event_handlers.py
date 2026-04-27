import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from deep_translator import GoogleTranslator
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent, GiftEvent, LiveEndEvent


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
) -> None:
	# Import colors here to avoid circular import
	from main import GREEN, RESET

	@client.on(ConnectEvent)
	async def on_connect(_: ConnectEvent) -> None:
		print(f"[system] Connected to @{unique_id}", flush=True)

	@client.on(CommentEvent)
	async def on_comment(event: CommentEvent) -> None:
		if not show_comments:
			return

		comment_text = getattr(event, "comment", "")
		translation = await translate_to_chinese(comment_text)
		suffix = f"（{translation}）" if translation else ""
		print(
			f"[{format_timestamp(datetime.now())}] [comment] {event_user_name(event)}: {comment_text}{suffix}",
			flush=True,
		)

	@client.on(GiftEvent)
	async def on_gift(event: GiftEvent) -> None:
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

	@client.on(LiveEndEvent)
	async def on_live_end(_: LiveEndEvent) -> None:
		print("[system] Live ended", flush=True)

	@client.on(DisconnectEvent)
	async def on_disconnect(_: DisconnectEvent) -> None:
		print("[system] Disconnected", flush=True)
