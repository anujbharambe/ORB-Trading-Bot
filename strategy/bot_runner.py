"""
Bot Runner Module
Runs the ORB strategy in a daemon background thread, decoupled from Streamlit's UI lifecycle.
Provides thread-safe access to strategy state.
"""

import threading
import logging
from typing import Dict, Any, List

from broker.angel_client import AngelOneClient
from strategy.orb_strategy import ORBStrategy
from utils.time_utils import TimeManager
from utils.config import TICK_INTERVAL, HEALTH_CHECK_INTERVAL
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Derive the tick-count threshold from the two config values
HEALTH_CHECK_EVERY_N_TICKS = max(1, HEALTH_CHECK_INTERVAL // TICK_INTERVAL)


class BotRunner:
    """
    Manages the ORB strategy in a background daemon thread.
    Thread-safe: all reads/writes to shared state go through a Lock.
    """

    def __init__(self, paper_trading: bool = True):
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        self.broker = AngelOneClient(paper_trading=paper_trading)
        self.strategy = ORBStrategy(self.broker)
        self._tick_count = 0
        self._consecutive_failures = 0

    # ── public controls ────────────────────────────────────────────

    def start(self) -> bool:
        """
        Start the bot. Connects to broker and launches the background thread.

        Returns:
            bool: True if started successfully
        """
        with self._lock:
            if self.strategy.is_running:
                logger.warning("Bot is already running.")
                return False

            if not self.broker.is_connected:
                if not self.broker.connect():
                    self.strategy.state.error_message = "Failed to connect to broker"
                    logger.error("Failed to connect to broker")
                    return False

            self.strategy.is_running = True
            self.strategy.state.last_trade_date = TimeManager.get_today_date()
            self._stop_event.clear()

            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            logger.info("BotRunner: strategy thread started.")
            return True

    def stop(self) -> None:
        """Stop the bot gracefully."""
        with self._lock:
            self.strategy.is_running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        logger.info("BotRunner: strategy thread stopped.")

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self.strategy.is_running

    def set_paper_trading(self, enabled: bool) -> None:
        with self._lock:
            self.broker.paper_trading = enabled

    @property
    def paper_trading(self) -> bool:
        return self.broker.paper_trading

    # ── thread-safe state access ───────────────────────────────────

    def get_state(self) -> Dict[str, Any]:
        """Return a snapshot of the current strategy state (thread-safe)."""
        with self._lock:
            return self.strategy.get_state_summary()

    def get_trade_history(self) -> List[Dict]:
        with self._lock:
            return self.strategy.get_trade_history()

    @property
    def connection_status(self) -> str:
        return self.broker.connection_status

    # ── internal loop ──────────────────────────────────────────────

    def _run_loop(self) -> None:
        """Background loop: tick strategy every TICK_INTERVAL seconds."""
        logger.info("BotRunner: entering main loop.")
        while not self._stop_event.is_set():
            try:
                with self._lock:
                    if not self.strategy.is_running:
                        break
                    self.strategy.tick()

                self._consecutive_failures = 0
                self._tick_count += 1

                # Periodic health check
                if self._tick_count % HEALTH_CHECK_EVERY_N_TICKS == 0:
                    self._health_check()

            except Exception as e:
                logger.error(f"BotRunner: tick error: {e}", exc_info=True)
                self._consecutive_failures += 1
                if self._consecutive_failures >= 3:
                    logger.warning("BotRunner: 3 consecutive failures, attempting reconnect.")
                    self.broker.reconnect()
                    self._consecutive_failures = 0

            # Wait for next tick (interruptible via _stop_event)
            self._stop_event.wait(timeout=TICK_INTERVAL)

        logger.info("BotRunner: exited main loop.")

    def _health_check(self) -> None:
        """Verify the broker session is still alive."""
        ltp = self.broker.get_ltp()
        if ltp is None:
            logger.warning("BotRunner health-check: LTP returned None. Triggering reconnect.")
            self.broker.reconnect()
