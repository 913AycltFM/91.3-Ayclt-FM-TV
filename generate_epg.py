import json
from datetime import datetime, timedelta
from pathlib import Path
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

AZURACAST_BASE_URL = "https://radio.913aycltfm.com"
TIMEZONE = ZoneInfo("America/Chicago")
DAYS_AHEAD = 7
XML_OUTPUT = "91.3_Ayclt_FM_radio_guide.xml"
JSON_OUTPUT = "epg.json"

STATIONS = {
    "913AycltFM": "91.3_ayclt_fm",
    "913AycltFMHD2": "91.3_ayclt_fm_hd2",
    "913AycltFMHD3": "91.3_ayclt_fm_hd3",
}

CHANNELS = [
    {"id": "913AycltFM", "display": "1", "name": "91.3 Ayclt FM", "description": "Dickinson's Texas #1 Hit Music Station", "icon": "https://radio.913aycltfm.com/static/uploads/91.3_ayclt_fm/background.1779890712.png"},
    {"id": "913AycltFMHD2", "display": "1.2", "name": "91.3 Ayclt FM HD2", "description": "Dickinson's Texas #1 Hit Music Station", "icon": "https://radio.913aycltfm.com/static/uploads/91.3_ayclt_fm_hd2/background.1779890739.png"},
    {"id": "913AycltFMHD3", "display": "1.3", "name": "91.3 Ayclt FM HD3", "description": "Dickinson's Texas #1 Hit Music Station", "icon": "https://radio.913aycltfm.com/static/uploads/91.3_ayclt_fm_hd3/background.1779890763.png"},
    {"id": "913AycltFMLiveStudioCam", "display": "1.4", "name": "91.3 Ayclt FM Live Studio Cam", "description": "91.3 Ayclt FM Live Studio Cam", "icon": "https://radio.913aycltfm.com/static/uploads/91.3_ayclt_fm/background.1779890712.png"},
    {"id": "913AycltFMMobileStudioCam", "display": "1.5", "name": "91.3 Ayclt FM Mobile Studio Cam", "description": "91.3 Ayclt FM Mobile Studio Cam", "icon": "https://radio.913aycltfm.com/static/uploads/91.3_ayclt_fm/background.1779890712.png"},
]


def fetch_json(url):
    refresh_url = f"{url}{'&' if '?' in url else '?'}epg_refresh={int(time.time())}"
    request = Request(refresh_url, headers={
        "User-Agent": "91.3-Ayclt-FM-EPG/1.3",
        "Cache-Control": "no-cache, no-store, max-age=0",
        "Pragma": "no-cache",
        "Accept": "application/json",
        "Connection": "close",
    })
    timeout_seconds = 90
    last_error = None

    for attempt in range(1, 4):
        try:
            print(f"Fetching AzuraCast API (attempt {attempt}/3): {url}")
            with urlopen(request, timeout=timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8-sig"))
        except (HTTPError, URLError, TimeoutError, ConnectionError, OSError) as error:
            last_error = error
            if attempt == 3:
                break
            delay = 5 * attempt
            print(f"AzuraCast request failed: {type(error).__name__}: {error}. Retrying in {delay}s...")
            time.sleep(delay)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"AzuraCast API returned invalid JSON: {url}") from error

    raise RuntimeError(f"AzuraCast API request failed after 3 attempts: {url}") from last_error


def find_schedule_list(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []

    keys = ["schedule", "schedules", "data", "items", "results"]
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            for nested_key in keys:
                nested = value.get(nested_key)
                if isinstance(nested, list):
                    return nested
    return []


def get_field(item, names):
    if not isinstance(item, dict):
        return None
    for name in names:
        if name in item and item[name] is not None:
            return item[name]
    return None


def parse_datetime(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=ZoneInfo("UTC")).astimezone(TIMEZONE)
        except Exception:
            return None

    value = str(value).strip()
    if not value:
        return None

    if value.isdigit():
        try:
            timestamp = int(value)
            if timestamp > 100000000000:
                timestamp /= 1000
            return datetime.fromtimestamp(timestamp, tz=ZoneInfo("UTC")).astimezone(TIMEZONE)
        except Exception:
            pass

    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TIMEZONE)
        return dt.astimezone(TIMEZONE)
    except Exception:
        pass

    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"]:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=TIMEZONE)
        except Exception:
            continue

    return None


def xmltv_datetime(dt):
    dt = dt.astimezone(TIMEZONE)
    offset = dt.utcoffset() or timedelta(0)
    minutes = int(offset.total_seconds() / 60)
    sign = "+" if minutes >= 0 else "-"
    minutes = abs(minutes)
    return f"{dt:%Y%m%d%H%M%S} {sign}{minutes // 60:02d}{minutes % 60:02d}"


def get_program_title(item, channel_name):
    value = get_field(item, ["name", "title", "program_name", "show_name", "playlist_name", "streamer_name", "dj_name"])
    if isinstance(value, dict):
        value = get_field(value, ["name", "title"])
    return str(value).strip() if value else channel_name


def get_streamer_info(item):
    if not isinstance(item, dict):
        return "", ""

    # Pull the streamer/DJ directly from the AzuraCast schedule API item.
    streamer = get_field(
        item,
        ["streamer", "streamer_name", "dj", "dj_name", "presenter", "presenter_name"],
    )
    streamer_id = get_field(
        item,
        ["streamer_id", "dj_id", "presenter_id", "streamerId", "djId", "presenterId"],
    )

    name = None

    if isinstance(streamer, dict):
        if streamer_id is None:
            streamer_id = get_field(
                streamer,
                ["id", "streamer_id", "dj_id", "presenter_id", "streamerId", "djId", "presenterId"],
            )
        name = get_field(
            streamer,
            ["name", "display_name", "username", "title", "streamer_name", "dj_name"],
        )
    elif streamer:
        name = streamer

    # AzuraCast can nest schedule/presenter data inside the schedule response.
    for key in ("schedule", "data", "user", "presenter", "dj", "streamer"):
        nested = item.get(key)
        if isinstance(nested, dict):
            if streamer_id is None:
                streamer_id = get_field(
                    nested,
                    ["id", "streamer_id", "dj_id", "presenter_id", "streamerId", "djId", "presenterId"],
                )
            if not name:
                name = get_field(
                    nested,
                    ["name", "display_name", "username", "title", "streamer_name", "dj_name"],
                )

    return (
        str(name).strip() if name else "",
        str(streamer_id).strip() if streamer_id is not None else "",
    )


def streamer_art_url(station_slug, streamer_id):
    if not streamer_id:
        return None
    return f"{AZURACAST_BASE_URL}/api/station/{station_slug}/streamer/{streamer_id}/art"


def get_streamer_art(item, station_slug):
    # The schedule API supplies the DJ/streamer ID. Use that ID directly.
    _name, streamer_id = get_streamer_info(item)
    if streamer_id:
        return streamer_art_url(station_slug, streamer_id)
    return None


def is_live_program(item):
    for name in ("is_live", "live", "is_live_dj", "live_dj"):
        value = get_field(item, [name])
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().lower() in {"true", "yes", "1"}:
            return True
        if isinstance(value, str) and value.strip().lower() in {"false", "no", "0"}:
            return False

    streamer = get_field(item, ["streamer_name", "streamer", "dj_name", "dj", "presenter_name", "presenter"])
    if isinstance(streamer, dict):
        streamer = get_field(streamer, ["name", "title", "display_name"])
    if streamer and str(streamer).strip():
        return True

    description = get_field(item, ["description", "desc"])
    if description:
        description = str(description).strip()
        if description.lower().startswith(("streamer:", "live dj:")):
            return bool(description.split(":", 1)[1].strip())

    return False


def set_live_metadata(programme, is_live):
    if not is_live:
        return
    ET.SubElement(programme, "live")
    ET.SubElement(programme, "category", {"lang": "en"}).text = "LIVE"
    ET.SubElement(programme, "sub-title", {"lang": "en"}).text = "LIVE"
    ET.SubElement(programme, "new")


def get_description(item, channel_description):
    value = get_field(item, ["description", "desc"])
    if value:
        text = str(value).strip()
        if text.lower().startswith("streamer:"):
            return "Live DJ:" + text.split(":", 1)[1]
        return text
    return channel_description


def fetch_station_schedule(station_slug, start_date, end_date):
    schedules = []
    current_date = start_date

    while current_date <= end_date:
        chunk_end = min(current_date + timedelta(days=6), end_date)
        query = urlencode({"start": current_date.isoformat(), "end": chunk_end.isoformat()})
        data = fetch_json(f"{AZURACAST_BASE_URL}/api/station/{station_slug}/schedule?{query}")
        schedules.extend(find_schedule_list(data))
        current_date = chunk_end + timedelta(days=1)

    return schedules


def convert_schedule(channel, schedules, minimum, maximum, station_slug):
    events = []

    for item in schedules:
        if not isinstance(item, dict):
            continue

        start = parse_datetime(get_field(item, ["start", "start_time", "start_datetime", "startDateTime", "starts_at", "start_at"]))
        end = parse_datetime(get_field(item, ["end", "end_time", "end_datetime", "endDateTime", "ends_at", "end_at"]))

        if start is None or end is None or end <= start or end < minimum or start > maximum:
            continue

        live_program = is_live_program(item)
        icon = get_streamer_art(item, station_slug) if live_program else None

        events.append({
            "channel_id": channel["id"],
            "channel_name": channel["name"],
            "title": get_program_title(item, channel["name"]),
            "description": get_description(item, channel["description"]),
            "start": max(start, minimum),
            "end": min(end, maximum),
            "icon": icon or channel["icon"],
            "fallback": False,
            "live_program": live_program,
        })

    return events


def add_filler_blocks(result, channel, start_time, end_time):
    current = start_time

    while current < end_time:
        end = min(current + timedelta(hours=1), end_time)
        result.append({
            "channel_id": channel["id"],
            "channel_name": channel["name"],
            "title": channel["name"],
            "description": channel["description"],
            "start": current,
            "end": end,
            "icon": channel["icon"],
            "fallback": True,
            "live_program": False,
            "live": False,
        })
        current = end


def fill_schedule_gaps(channel, events, start_time, end_time):
    scheduled = sorted(
        events,
        key=lambda x: (x["start"], -(x["end"] - x["start"]).total_seconds(), x["title"]),
    )

    real_events = []

    for event in scheduled:
        event = dict(event)

        if real_events and event["start"] < real_events[-1]["end"]:
            if event["start"] == real_events[-1]["start"]:
                if event["end"] <= real_events[-1]["end"]:
                    continue
                real_events[-1] = event
                continue

            event["start"] = real_events[-1]["end"]

            if event["end"] <= event["start"]:
                continue

        real_events.append(event)

    result = []
    current = start_time

    for event in real_events:
        if event["start"] > current:
            add_filler_blocks(result, channel, current, event["start"])

        if event["end"] > current:
            event["start"] = max(event["start"], current)
            result.append(event)
            current = event["end"]

    if current < end_time:
        add_filler_blocks(result, channel, current, end_time)

    return result


def create_no_schedule_channel(channel, start_time, end_time):
    return [{
        "channel_id": channel["id"],
        "channel_name": channel["name"],
        "title": channel["name"],
        "description": channel["description"],
        "start": start_time,
        "end": end_time,
        "icon": channel["icon"],
        "fallback": True,
        "live_program": False,
        "live": False,
    }]


def clean_events(events):
    # Remove malformed/zero-duration entries before timeline validation.
    # Valid future DJs are preserved; only events with end <= start are dropped.
    events = [
        event for event in events
        if event.get("start") is not None
        and event.get("end") is not None
        and event["end"] > event["start"]
    ]

    events.sort(key=lambda x: (x["channel_id"], x["start"], x["end"], x["title"]))
    seen = set()
    result = []

    for event in events:
        key = (
            event["channel_id"],
            event["start"].isoformat(),
            event["end"].isoformat(),
            event["title"],
        )

        if key not in seen:
            seen.add(key)
            result.append(event)

    return result


def validate_timelines(events):
    grouped = {}

    for event in events:
        grouped.setdefault(event["channel_id"], []).append(event)

    valid = True

    for channel_id, channel_events in grouped.items():
        channel_events.sort(key=lambda x: (x["start"], x["end"]))
        previous = None

        for event in channel_events:
            if event["end"] <= event["start"]:
                print(
                    f"Invalid timeline: {channel_id}: "
                    f"{event['title']} {event['start'].isoformat()} -> {event['end'].isoformat()}"
                )
                valid = False
                continue

            if previous and event["start"] < previous["end"]:
                print(
                    f"Overlap: {channel_id}: "
                    f"'{previous['title']}' {previous['start'].isoformat()} -> {previous['end'].isoformat()} "
                    f"overlaps '{event['title']}' {event['start'].isoformat()} -> {event['end'].isoformat()}"
                )
                valid = False

            previous = event

    return valid


def generate_xml(events):
    root = ET.Element("tv", {"generator-info-name": "RadioEPG"})

    for channel in CHANNELS:
        channel_element = ET.SubElement(root, "channel", {"id": channel["id"]})
        ET.SubElement(channel_element, "display-name").text = channel["display"]
        ET.SubElement(channel_element, "display-name").text = channel["name"]

    for event in events:
        programme = ET.SubElement(root, "programme", {
            "start": xmltv_datetime(event["start"]),
            "stop": xmltv_datetime(event["end"]),
            "channel": event["channel_id"],
        })

        is_live = event.get("live_program", False)

        ET.SubElement(programme, "title", {"lang": "en"}).text = event["title"]
        ET.SubElement(programme, "desc", {"lang": "en"}).text = event["description"]

        if event.get("icon"):
            ET.SubElement(programme, "icon", {"src": event["icon"]})

        set_live_metadata(programme, is_live)

    try:
        ET.indent(root, space="  ")
    except AttributeError:
        pass

    path = Path(XML_OUTPUT)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    xml = path.read_text(encoding="utf-8")
    xml = xml.replace("<?xml version='1.0' encoding='utf-8'?>", '<?xml version="1.0" encoding="utf-8"?>', 1)

    if "<!DOCTYPE tv SYSTEM" not in xml:
        xml = xml.replace(
            '<?xml version="1.0" encoding="utf-8"?>',
            '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">',
            1,
        )

    xml = xml.replace("<live />", "<live/>").replace("<new />", "<new/>")
    path.write_text(xml, encoding="utf-8")


def generate_json(events):
    output = []

    for event in events:
        output.append({
            "channel_id": event["channel_id"],
            "station_name": event["channel_name"],
            "title": event["title"],
            "description": event["description"],
            "start": event["start"].isoformat(),
            "end": event["end"].isoformat(),
            "icon": event["icon"],
            "fallback": event["fallback"],
            "live": event.get("live_program", False),
            "live_badge": "LIVE" if event.get("live_program", False) else "",
            "display_title": event["title"],
        })

    Path(JSON_OUTPUT).write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def validate_xml():
    try:
        ET.parse(XML_OUTPUT)
        return True
    except Exception as error:
        print(f"XML validation FAILED: {error}")
        return False


def main():
    now = datetime.now(TIMEZONE)
    start_time = now.replace(minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(days=DAYS_AHEAD)
    schedule_start_date = start_time.date() - timedelta(days=1)

    all_events = []
    schedule_cache = {}

    for channel in CHANNELS:
        channel_id = channel["id"]

        if channel_id not in STATIONS:
            all_events.extend(create_no_schedule_channel(channel, start_time, end_time))
            continue

        station_slug = STATIONS[channel_id]

        if station_slug not in schedule_cache:
            schedule_cache[station_slug] = fetch_station_schedule(
                station_slug,
                schedule_start_date,
                end_time.date(),
            )

        actual_events = convert_schedule(
            channel,
            schedule_cache[station_slug],
            start_time,
            end_time,
            station_slug,
        )

        all_events.extend(fill_schedule_gaps(channel, actual_events, start_time, end_time))

    # Live Studio Cam and Mobile Studio Cam mirror the FM schedule exactly.
    live_cam = next(channel for channel in CHANNELS if channel["id"] == "913AycltFMLiveStudioCam")
    mobile_cam = next(channel for channel in CHANNELS if channel["id"] == "913AycltFMMobileStudioCam")
    fm_channel = next(channel for channel in CHANNELS if channel["id"] == "913AycltFM")

    all_events = [
        event for event in all_events
        if event["channel_id"] not in {live_cam["id"], mobile_cam["id"]}
    ]

    fm_station_slug = STATIONS["913AycltFM"]
    fm_events = convert_schedule(
        fm_channel,
        schedule_cache[fm_station_slug],
        start_time,
        end_time,
        fm_station_slug,
    )

    live_cam_events = []

    for event in fm_events:
        cam_event = dict(event)
        cam_event["channel_id"] = live_cam["id"]
        cam_event["channel_name"] = live_cam["name"]

        if not cam_event.get("live_program"):
            cam_event["icon"] = live_cam["icon"]

        live_cam_events.append(cam_event)

    all_events.extend(fill_schedule_gaps(live_cam, live_cam_events, start_time, end_time))

    mobile_cam_events = []
    for event in fm_events:
        cam_event = dict(event)
        cam_event["channel_id"] = mobile_cam["id"]
        cam_event["channel_name"] = mobile_cam["name"]
        if not cam_event.get("live_program"):
            cam_event["icon"] = mobile_cam["icon"]
        mobile_cam_events.append(cam_event)

    all_events.extend(fill_schedule_gaps(mobile_cam, mobile_cam_events, start_time, end_time))
    all_events = clean_events(all_events)

    if not validate_timelines(all_events):
        raise RuntimeError("EPG timeline validation failed")

    generate_xml(all_events)
    generate_json(all_events)

    if not validate_xml():
        raise RuntimeError("Generated XML validation failed")

    print(f"Generated {len(all_events)} EPG programmes.")


if __name__ == "__main__":
    main()
