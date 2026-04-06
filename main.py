# -*- coding: utf-8 -*-

import logging
import os
from pathlib import Path
from colorama import Fore
from TwitchChannelPointsMiner import TwitchChannelPointsMiner
from TwitchChannelPointsMiner.logger import LoggerSettings, ColorPalette
from TwitchChannelPointsMiner.classes.Chat import ChatPresence
from TwitchChannelPointsMiner.classes.Discord import Discord
from TwitchChannelPointsMiner.classes.Settings import Priority, Events, FollowersOrder
from TwitchChannelPointsMiner.classes.entities.Bet import (
    Strategy,
    BetSettings,
    Condition,
    OutcomeKeys,
    FilterCondition,
    DelayMode,
)
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer, StreamerSettings


def load_dotenv(dotenv_path=".env"):
    path = Path(dotenv_path)
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if len(value) >= 2 and value[0] == value[-1] and value[0] in ['"', "'"]:
            value = value[1:-1]

        os.environ.setdefault(key, value)


load_dotenv()

TWITCH_USERNAME = os.getenv("TWITCH_USERNAME", "your-twitch-username")
TWITCH_PASSWORD = os.getenv("TWITCH_PASSWORD")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

twitch_miner = TwitchChannelPointsMiner(
    username=TWITCH_USERNAME,
    password=TWITCH_PASSWORD,
    claim_drops_startup=True,       # Claim any pending drops on startup
    priority=[
        Priority.STREAK,            # 1. Watch streaks are time-sensitive, catch first
        Priority.SUBSCRIBED,        # 2. Gifted/Prime subs count — get the points multiplier
        Priority.DROPS,             # 3. Drops campaigns (august, rainbow6)
        Priority.ORDER,             # 4. Fall back to array order below
    ],
    enable_analytics=False,
    disable_ssl_cert_verification=False,
    disable_at_in_nickname=False,
    logger_settings=LoggerSettings(
        save=True,
        console_level=logging.INFO,
        console_username=False,
        auto_clear=True,
        time_zone="",
        file_level=logging.DEBUG,
        emoji=True,
        less=False,
        colored=True,
        color_palette=ColorPalette(
            STREAMER_online="GREEN",
            streamer_offline="red",
            BET_wiN=Fore.MAGENTA,
        ),
        discord=Discord(
            webhook_api=DISCORD_WEBHOOK_URL,
            events=[
                Events.STREAMER_ONLINE,
                Events.STREAMER_OFFLINE,
                Events.BET_START,
                Events.BET_WIN,
                Events.BET_REFUND,
                Events.BET_LOSE,
                Events.BONUS_CLAIM,
                Events.DROP_CLAIM,
                Events.GAIN_FOR_RAID,
                Events.GAIN_FOR_CLAIM,
                Events.GAIN_FOR_WATCH,
                Events.GAIN_FOR_WATCH_STREAK,
            ],
        ) if DISCORD_WEBHOOK_URL else None,
    ),
    streamer_settings=StreamerSettings(
        make_predictions=False,     # Safe global default — each streamer opts in explicitly
        follow_raid=True,
        claim_drops=True,
        claim_moments=True,
        watch_streak=True,
        community_goals=False,
        chat=ChatPresence.ONLINE,
        bet=BetSettings(
            strategy=Strategy.PERCENTAGE,
            percentage=5,
            percentage_gap=25,
            max_points=50000,
            stealth_mode=True,
            delay_mode=DelayMode.FROM_END,
            delay=6,
            minimum_points=50000,
            filter_condition=FilterCondition(
                by=OutcomeKeys.TOTAL_USERS,
                where=Condition.GT,
                value=20,
            ),
        ),
    ),
)

twitch_miner.mine(
    [
        # ── august ───────────────────────────────────────────────────────────────
        # Main drops-only target (Overwatch).
        # No predictions, no raid-following (leaving a drops stream kills watch time).
        Streamer(
            "august",
            settings=StreamerSettings(
                make_predictions=False,
                follow_raid=False,
                claim_drops=True,
                watch_streak=True,
                community_goals=False,
                chat=ChatPresence.ONLINE,
            ),
        ),

        # ── rainbow6 ─────────────────────────────────────────────────────────────
        # Second drops-only target (R6 Siege). Same reasoning as august.
        # Official Twitch channel so drops are reliable and frequent during events.
        Streamer(
            "rainbow6",
            settings=StreamerSettings(
                make_predictions=False,
                follow_raid=False,
                claim_drops=True,
                watch_streak=True,
                community_goals=False,
                chat=ChatPresence.ONLINE,
            ),
        ),

        # ── boxyfresh ────────────────────────────────────────────────────────────
        # Favourite streamer, Prime sub here.
        # SoT predictions (steal item / W/L hourglass) are situational — keep
        # minimum_points high so we only bet when the bank is comfortable.
        Streamer(
            "boxyfresh",
            settings=StreamerSettings(
                make_predictions=True,
                follow_raid=True,
                claim_drops=True,
                watch_streak=True,
                community_goals=False,
                bet=BetSettings(
                    strategy=Strategy.PERCENTAGE,
                    percentage=5,
                    stealth_mode=True,
                    percentage_gap=25,
                    max_points=50000,
                    minimum_points=100000,
                    delay_mode=DelayMode.FROM_END,
                    delay=6,
                    filter_condition=FilterCondition(
                        by=OutcomeKeys.TOTAL_USERS,
                        where=Condition.GT,
                        value=20,
                    ),
                ),
            ),
        ),

        # ── caedrel ──────────────────────────────────────────────────────────────
        # LEC/LCK match predictions have some readability (team form,
        # standings), so SMART can find genuine edges. percentage_gap=25 skips
        # near-50/50 matches. minimum_points protects ~half the bank.
        Streamer(
            "caedrel",
            settings=StreamerSettings(
                make_predictions=True,
                follow_raid=True,
                claim_drops=True,
                watch_streak=True,
                community_goals=False,
                bet=BetSettings(
                    strategy=Strategy.PERCENTAGE,
                    percentage=5,
                    stealth_mode=True,
                    percentage_gap=25,
                    max_points=30000,
                    minimum_points=20000,
                    delay_mode=DelayMode.FROM_END,
                    delay=6,
                    filter_condition=FilterCondition(
                        by=OutcomeKeys.TOTAL_USERS,
                        where=Condition.GT,
                        value=20,
                    ),
                ),
            ),
        ),

        # ── insym ────────────────────────────────────────────────────────────────
        # Ghost gambling predictions are pure coin-flips (Will it be
        # Yuri? Yes/No) with no signal to exploit. Predictions OFF per Codex review —
        # the bank is too small to absorb variance on random 50/50s.
        # Re-enable and set minimum_points=8000 once bank exceeds ~30K.
        Streamer(
            "insym",
            settings=StreamerSettings(
                make_predictions=True,
                follow_raid=True,
                claim_drops=True,
                watch_streak=True,
                community_goals=False,
                bet=BetSettings(
                    strategy=Strategy.PERCENTAGE,
                    percentage=2,
                    max_points=5000,
                    minimum_points=30000,
                    stealth_mode=True,
                    delay_mode=DelayMode.FROM_END,
                    delay=6,
                    filter_condition=FilterCondition(
                        by=OutcomeKeys.TOTAL_USERS,
                        where=Condition.GT,
                        value=30,
                    ),
                ),
            ),
        ),

        # ── lauchgruen ───────────────────────────────────────────────────────────
        # IRL friend, small streamer. Predictions off: nobody bets
        # the other side so wins pay near-zero while losses are full stake.
        # Pure passive accumulation — watch, streak, claim.
        Streamer(
            "lauchgruen",
            settings=StreamerSettings(
                make_predictions=False,
                follow_raid=True,
                claim_drops=True,
                watch_streak=True,
                community_goals=False,
            ),
        ),
    ],
    followers=False,
    followers_order=FollowersOrder.ASC,
)
