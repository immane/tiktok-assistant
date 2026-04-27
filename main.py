import argparse
import asyncio
import signal
import sys
from pathlib import Path
from typing import Awaitable, Callable, Iterable, Optional

from TikTokLive import TikTokLiveClient
from TikTokLive.client.errors import UserNotFoundError, UserOfflineError

from event_handlers import GiftTask, register_event_handlers
from gift_queue import consume_gift_queue
from likes_trigger import create_likes_trigger_handler

# ANSI color codes for terminal output
GREEN = "\033[32m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Show TikTok live comments in the console and queue matching gifts with sound alerts."
	)
	parser.add_argument(
		"unique_id",
		help="TikTok live unique_id, for example: some_creator",
	)
	parser.add_argument(
		"--gift-names",
		nargs="*",
		default=[],
		metavar="GIFT",
		help="Optional gift names to watch. If omitted, every gift is queued.",
	)
	parser.add_argument(
		"--sound",
		default="",
		help="Optional path to a .wav file. Defaults to the system notification sound.",
	)
	parser.add_argument(
		"--no-comments",
		action="store_true",
		help="Disable comment output and only watch gifts.",
	)
	parser.add_argument(
		"--queue-timeout",
		type=float,
		default=0.0,
		help="Optional delay in seconds after each queued gift is processed.",
	)
	parser.add_argument(
		"--triggers",
		default="",
		metavar="JSON",
		help=(
			"Optional JSON array of trigger rules, e.g. "
			"'[{\"trigger\":\"[default]\",\"action-key\":\"x\"}]'. "
			"Each rule has 'trigger' (gift name or '[default]'), "
			"'action-key' (e.g. 'x' or 'ctrl-v'), "
			"and optional 'repeats' (int, defaults to diamonds count)."
		),
	)
	parser.add_argument(
		"--likes-threshold",
		type=int,
		default=500,
		help="Trigger likes hotkey every N likes (default: 500).",
	)
	parser.add_argument(
		"--likes-trigger-key",
		default="",
		help="Optional key/combo to trigger when likes reach each threshold, e.g. 'x' or 'ctrl-v'.",
	)
	return parser.parse_args()


def normalize_names(names: Iterable[str]) -> set[str]:
	return {name.strip().casefold() for name in names if name.strip()}



async def run_client_session(client: TikTokLiveClient) -> None:
	websocket_task = await client.start()
	await websocket_task


async def run() -> None:
	args = parse_args()
	watched_gifts = normalize_names(args.gift_names)
	sound_path = str(Path(args.sound).expanduser().resolve()) if args.sound else ""
	likes_threshold = max(args.likes_threshold, 1)
	likes_trigger_key = args.likes_trigger_key.strip()
	likes_trigger: Optional[Callable[[object], Awaitable[None]]] = None

	if likes_trigger_key:
		try:
			likes_trigger = create_likes_trigger_handler(
				trigger_key=likes_trigger_key,
				threshold=likes_threshold,
			)
			print(
				f"[system] Likes trigger enabled: {likes_trigger_key} (threshold={likes_threshold})",
				flush=True,
			)
		except ValueError as exc:
			print(f"[system] Invalid --likes-trigger-key: {exc}", flush=True)

	if sound_path and not Path(sound_path).exists():
		raise FileNotFoundError(f"Sound file not found: {sound_path}")

	queue: asyncio.Queue[GiftTask] = asyncio.Queue()
	client = TikTokLiveClient(unique_id=args.unique_id)
	print(f"[system] Connecting to @{args.unique_id}...", flush=True)
	register_event_handlers(
		client=client,
		unique_id=args.unique_id,
		queue=queue,
		watched_gifts=watched_gifts,
		show_comments=not args.no_comments,
		likes_trigger=likes_trigger,
	)

	consumer_task = asyncio.create_task(
		consume_gift_queue(
			queue,
			sound_path or None,
			args.queue_timeout,
			args.triggers.strip() or None,
		)
	)

	stop_event = asyncio.Event()

	def request_shutdown() -> None:
		if not stop_event.is_set():
			print("\n[system] Shutdown requested", flush=True)
			stop_event.set()

	loop = asyncio.get_running_loop()
	for sig in (signal.SIGINT, signal.SIGTERM):
		try:
			loop.add_signal_handler(sig, request_shutdown)
		except NotImplementedError:
			pass

	client_task = asyncio.create_task(run_client_session(client))
	shutdown_task = asyncio.create_task(stop_event.wait())

	done, pending = await asyncio.wait(
		{client_task, shutdown_task},
		return_when=asyncio.FIRST_COMPLETED,
	)

	if shutdown_task in done and not client_task.done():
		client.stop()
		await client.disconnect()
		await client_task
	elif client_task in done:
		try:
			client_task.result()
		except UserOfflineError:
			print(f"[system] @{args.unique_id} is not live right now", flush=True)
		except UserNotFoundError:
			print(f"[system] TikTok user @{args.unique_id} was not found", flush=True)
		except Exception as exc:
			print(f"[system] Connection failed: {exc}", flush=True)

	for pending_task in pending:
		pending_task.cancel()
		with contextlib.suppress(asyncio.CancelledError):
			await pending_task

	consumer_task.cancel()
	with contextlib.suppress(asyncio.CancelledError):
		await consumer_task


if sys.platform == "win32":
	import contextlib
else:
	import contextlib


if __name__ == "__main__":
	try:
		asyncio.run(run())
	except KeyboardInterrupt:
		print("\n[system] Stopped", flush=True)
