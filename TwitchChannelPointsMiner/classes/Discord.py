import re

import requests

from TwitchChannelPointsMiner.classes.Settings import Events


class Discord(object):
    __slots__ = ["webhook_api", "events"]

    STREAMER_RE = re.compile(
        r"Streamer\(username=(?P<username>[^,]+), channel_points=(?P<points>[^)]+)\)"
    )
    GAIN_RE = re.compile(
        r"\+(?P<amount>[\d.]+).*?Streamer\(username=(?P<username>[^,]+), channel_points=(?P<points>[^)]+)\)\s*-\s*Reason:\s*(?P<reason>[A-Z_]+)\.?"
    )
    BONUS_RE = re.compile(
        r"Claiming the bonus for Streamer\(username=(?P<username>[^,]+), channel_points=(?P<points>[^)]+)\)!"
    )
    MOMENT_RE = re.compile(
        r"Claiming the moment for Streamer\(username=(?P<username>[^,]+), channel_points=(?P<points>[^)]+)\)!"
    )
    BET_DELAY_RE = re.compile(
        r"Place the bet after:\s*(?P<delay>[\d.]+)s for:\s*EventPrediction\(event_id=.*?streamer=Streamer\(username=(?P<username>[^,]+), channel_points=(?P<points>[^)]+)\), title=(?P<title>.+?)\)"
    )
    BET_PLACE_RE = re.compile(
        r"Place\s+(?P<amount>[\w.]+)\s+channel points on:\s*(?P<choice>.+)"
    )
    BET_RESULT_RE = re.compile(
        r"EventPrediction\(event_id=.*?streamer=Streamer\(username=(?P<username>[^,]+), channel_points=(?P<points>[^)]+)\), title=(?P<title>.+?)\)\s*-\s*Decision:\s*(?P<choice>\d+):\s*(?P<decision>.+?)\s*-\s*Result:\s*(?P<result>.+)"
    )

    REASON_LABELS = {
        "WATCH": "watch time",
        "WATCH_STREAK": "watch streak",
        "CLAIM": "bonus claim",
        "RAID": "raid",
    }

    TITLES = {
        "STREAMER_ONLINE": "Streamer Online",
        "STREAMER_OFFLINE": "Streamer Offline",
        "GAIN_FOR_RAID": "Points Earned",
        "GAIN_FOR_CLAIM": "Points Earned",
        "GAIN_FOR_WATCH": "Points Earned",
        "GAIN_FOR_WATCH_STREAK": "Points Earned",
        "BONUS_CLAIM": "Bonus Claimed",
        "MOMENT_CLAIM": "Moment Claimed",
        "DROP_CLAIM": "Drop Claimed",
        "BET_START": "Prediction Opening",
        "BET_GENERAL": "Prediction Update",
        "BET_WIN": "Prediction Won",
        "BET_LOSE": "Prediction Lost",
        "BET_REFUND": "Prediction Refunded",
        "BET_FILTERS": "Prediction Skipped",
        "BET_FAILED": "Prediction Error",
        "CHAT_MENTION": "Chat Mention",
        "JOIN_RAID": "Joined Raid",
    }

    COLORS = {
        "STREAMER_ONLINE": 0x57F287,
        "STREAMER_OFFLINE": 0x747F8D,
        "GAIN_FOR_RAID": 0x5865F2,
        "GAIN_FOR_CLAIM": 0xFEE75C,
        "GAIN_FOR_WATCH": 0x5865F2,
        "GAIN_FOR_WATCH_STREAK": 0x57F287,
        "BONUS_CLAIM": 0xFEE75C,
        "MOMENT_CLAIM": 0x5865F2,
        "DROP_CLAIM": 0xEB459E,
        "BET_START": 0x5865F2,
        "BET_GENERAL": 0x5865F2,
        "BET_WIN": 0x57F287,
        "BET_LOSE": 0xED4245,
        "BET_REFUND": 0xFEE75C,
        "BET_FILTERS": 0x747F8D,
        "BET_FAILED": 0xED4245,
        "CHAT_MENTION": 0x5865F2,
        "JOIN_RAID": 0xEB459E,
    }

    def __init__(self, webhook_api: str, events: list):
        self.webhook_api = webhook_api
        self.events = [str(e) for e in events]

    def send(self, message: str, event: Events) -> None:
        if str(event) not in self.events:
            return

        payload = self._build_payload(message, event)
        requests.post(url=self.webhook_api, json=payload)

    def _build_payload(self, message: str, event: Events) -> dict:
        event_name = str(event)
        title = self.TITLES.get(event_name, event_name.replace("_", " ").title())
        color = self.COLORS.get(event_name, 0x5865F2)
        description, fields = self._format_message(message, event_name)

        embed = {
            "title": title,
            "description": description,
            "color": color,
        }

        if fields:
            embed["fields"] = fields

        return {
            "username": "Jett",
            "avatar_url": "https://i.ibb.co/20dmQ2N7/Profilepicture22.jpg",
            "allowed_mentions": {"parse": []},
            "embeds": [embed],
        }

    def _format_message(self, message: str, event_name: str):
        message = self._strip_leading_emoji(message)

        if event_name in ["STREAMER_ONLINE", "STREAMER_OFFLINE"]:
            streamer = self._extract_streamer(message)
            if streamer is not None:
                status = "online" if event_name == "STREAMER_ONLINE" else "offline"
                return (
                    f"**{streamer['username']}** is now {status}.",
                    [self._field("Balance", streamer["points"])],
                )

        if event_name.startswith("GAIN_FOR_"):
            match = self.GAIN_RE.search(message)
            if match:
                reason = self.REASON_LABELS.get(match.group("reason"), match.group("reason").lower())
                return (
                    f"**{match.group('username')}** earned **+{match.group('amount')}** points from {reason}.",
                    [self._field("Balance", match.group("points"))],
                )

        if event_name == "BONUS_CLAIM":
            match = self.BONUS_RE.search(message)
            if match:
                return (
                    f"Claimed the bonus chest on **{match.group('username')}**.",
                    [self._field("Balance", match.group("points"))],
                )

        if event_name == "MOMENT_CLAIM":
            match = self.MOMENT_RE.search(message)
            if match:
                return (
                    f"Claimed the community moment on **{match.group('username')}**.",
                    [self._field("Balance", match.group("points"))],
                )

        if event_name == "DROP_CLAIM":
            drop_name = message.removeprefix("Claim ").strip()
            return (drop_name if drop_name else message, [])

        if event_name == "BET_START":
            match = self.BET_DELAY_RE.search(message)
            if match:
                return (
                    f"**{match.group('username')}** has a prediction coming up in **{match.group('delay')}s**.",
                    [
                        self._field("Title", match.group("title")),
                        self._field("Balance", match.group("points")),
                    ],
                )

        if event_name == "BET_GENERAL":
            match = self.BET_PLACE_RE.search(message)
            if match:
                return (
                    f"Placing **{match.group('amount')}** channel points.",
                    [self._field("Choice", self._cleanup_text(match.group("choice")))],
                )

        if event_name in ["BET_WIN", "BET_LOSE", "BET_REFUND"]:
            match = self.BET_RESULT_RE.search(message)
            if match:
                return (
                    f"**{match.group('username')}** prediction result: **{match.group('result')}**",
                    [
                        self._field("Title", match.group("title")),
                        self._field("Decision", self._cleanup_text(match.group("decision"))),
                        self._field("Balance", match.group("points")),
                    ],
                )

        cleaned = self._cleanup_text(self._replace_streamers(message))
        return (cleaned, [])

    def _extract_streamer(self, message: str):
        match = self.STREAMER_RE.search(message)
        if match is None:
            return None

        return {
            "username": match.group("username"),
            "points": match.group("points"),
        }

    def _replace_streamers(self, message: str) -> str:
        def repl(match):
            return f"{match.group('username')} ({match.group('points')})"

        return self.STREAMER_RE.sub(repl, message)

    def _strip_leading_emoji(self, message: str) -> str:
        parts = message.strip().split("  ", 1)
        if len(parts) == 2 and len(parts[0]) <= 4:
            return parts[1].strip()
        return message.strip()

    def _cleanup_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _field(self, name: str, value: str) -> dict:
        return {
            "name": name,
            "value": value,
            "inline": True,
        }
