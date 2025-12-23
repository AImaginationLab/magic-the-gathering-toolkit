#!/usr/bin/env python
"""Quick test to verify Ctrl+C exit works properly."""

import asyncio
import threading
from mtg_spellbook.context import DatabaseContext


async def main():
    print("Starting app simulation...")
    print(f"Initial threads: {threading.active_count()}")

    ctx = DatabaseContext()
    db = await ctx.get_db()

    print(f"After DB init: {threading.active_count()} threads")
    for t in threading.enumerate():
        print(f"  {t.name}: daemon={t.daemon}")

    print("\nDatabase initialized. Press Ctrl+C to test exit...")
    print("(Should exit cleanly on first Ctrl+C)")

    try:
        # Keep running until Ctrl+C
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nReceived Ctrl+C, cleaning up...")
        await ctx.close()
        print(f"After cleanup: {threading.active_count()} threads")
        for t in threading.enumerate():
            print(f"  {t.name}: daemon={t.daemon}, alive={t.is_alive()}")
        print("Cleanup complete, exiting...")


if __name__ == "__main__":
    asyncio.run(main())
    print("Exit successful!")
