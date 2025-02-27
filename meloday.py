import yaml
import os
import re
import random
import json
from datetime import datetime, timedelta
from collections import Counter
from plexapi.server import PlexServer
from plexapi.audio import Track
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Get the base directory of the script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_config(filepath="config.yml"):
    with open(os.path.join(BASE_DIR, filepath), "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

config = load_config()

PLEX_URL = config["plex"]["url"]
PLEX_TOKEN = config["plex"]["token"]
MUSIC_LIBRARY = config["plex"]["music_library"]

EXCLUDE_PLAYED_DAYS = config["playlist"]["exclude_played_days"]
HISTORY_LOOKBACK_DAYS = config["playlist"]["history_lookback_days"]
MAX_TRACKS = config["playlist"]["max_tracks"]
SONIC_SIMILAR_LIMIT = config["playlist"]["sonic_similar_limit"]

PERIOD_PHRASES = config["period_phrases"]
def get_period_phrase(period):
    return PERIOD_PHRASES.get(period, f"in the {period}")

# Convert paths to be relative to BASE_DIR
COVER_IMAGE_DIR = os.path.join(BASE_DIR, config["directories"]["cover_images"])
MOOD_MAP_PATH = os.path.join(BASE_DIR, config["files"]["mood_map"])
FONTS_DIR = os.path.join(BASE_DIR, config["directories"]["fonts"])

FONT_MAIN_PATH = os.path.join(FONTS_DIR, config["fonts"]["main"])
FONT_MELODAY_PATH = os.path.join(FONTS_DIR, config["fonts"]["meloday"])

time_periods = config["time_periods"]

plex = PlexServer(PLEX_URL, PLEX_TOKEN, timeout=60)


# ---------------------------------------------------------------------
# HELPER: Print a simple progress bar (0-100%) with a message
def print_status(percent, message):
    """
    Print a progress bar with the given percentage and a status message.
    """
    bar_length = 30
    filled_length = int(bar_length * percent // 100)
    bar = '=' * filled_length + '-' * (bar_length - filled_length)
    print(f"[{bar}] {percent:3d}%  {message}")

# ---------------------------------------------------------------------
def get_current_time_period():
    """
    Determine which daypart the current hour belongs to.
    We do NOT sort. We rely on time_periods[period]["hours"]
    being the exact hours for that daypart, possibly wrapping midnight.
    """
    current_hour = datetime.now().hour

    for period, details in time_periods.items():
        period_hours = details["hours"]  # no sorting
        if current_hour in period_hours:
            return period

    # Fallback if not found
    return "Late Night"

def load_descriptor_map(filepath="moodmap.json"):
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading descriptor dictionary: {e}")
        return {}

def wrap_text(text, font, draw, max_width):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

# ---------------------------------------------------------------------
# Removed most debugging prints from these functions,
# except for warnings or errors.
def fetch_historical_tracks(period):
    """
    Fetch tracks from Plex history that match the current daypart,
    while excluding recently played tracks.
    """
    music_section = plex.library.section(MUSIC_LIBRARY)
    now = datetime.now()
    period_hours = set(time_periods[period]["hours"])

    history_start = now - timedelta(days=HISTORY_LOOKBACK_DAYS)
    exclude_start = now - timedelta(days=EXCLUDE_PLAYED_DAYS)

    history_entries = [
        entry for entry in music_section.history(mindate=history_start)
        if entry.viewedAt and entry.viewedAt.hour in period_hours
    ]
    excluded_entries = [
        entry for entry in music_section.history(mindate=exclude_start)
        if entry.viewedAt
    ]

    excluded_keys = {entry.ratingKey for entry in excluded_entries}
    filtered_tracks = [
        entry for entry in history_entries
        if entry.ratingKey not in excluded_keys
    ]

    # If no historical tracks found, fallback
    if not filtered_tracks:
        fallback_entries = [
            entry for entry in music_section.history(mindate=history_start)
            if entry.viewedAt and entry.viewedAt.hour in period_hours
               and entry.ratingKey not in excluded_keys
        ]
        if fallback_entries:
            filtered_tracks = fallback_entries

    # Genre balancing
    track_play_counts = Counter()
    genre_count = Counter()
    for track in filtered_tracks:
        track_play_counts[track] += 1
        for genre in track.grandparentTitle or []:
            genre_count[genre] += 1

    sorted_tracks = sorted(filtered_tracks, key=lambda t: track_play_counts[t], reverse=True)
    split_index = max(1, len(sorted_tracks) // 4)
    popular_tracks = sorted_tracks[:split_index]
    rare_tracks = sorted_tracks[split_index:]

    balanced_selection = (
        random.sample(rare_tracks, min(len(rare_tracks), int(MAX_TRACKS * 0.75)))
        + random.sample(popular_tracks, min(len(popular_tracks), int(MAX_TRACKS * 0.25)))
    )

    if genre_count:
        most_common_genre, most_common_count = genre_count.most_common(1)[0]
        max_genre_limit = int(MAX_TRACKS * 0.25)
        if most_common_count > max_genre_limit:
            balanced_selection = (
                [t for t in balanced_selection if most_common_genre not in t.genres][:max_genre_limit]
                + [t for t in balanced_selection if most_common_genre in t.genres][:max_genre_limit]
            )

    return balanced_selection, excluded_keys

def filter_low_rated_tracks(tracks):
    """
    Filter out tracks, albums, or artists with a 1-star rating (rating <=2),
    skipping ephemeral tracks that lack ratingKey or parentRatingKey.
    """
    filtered = []
    for track in tracks:
        try:
            if not getattr(track, "ratingKey", None) or not getattr(track, "parentRatingKey", None):
                continue
            artist = track.artist() if callable(getattr(track, "artist", None)) else None
            artist_rating = getattr(artist, "userRating", None) if artist else None
            album = plex.fetchItem(track.parentRatingKey)
            album_rating = getattr(album, "userRating", None) if album else None
            track_rating = getattr(track, "userRating", None)

            if artist_rating is not None and artist_rating <= 2:
                continue
            if album_rating is not None and album_rating <= 2:
                continue
            if track_rating is not None and track_rating <= 2:
                continue

            filtered.append(track)
        except Exception:
            # Just skip if something goes wrong
            pass
    return filtered

def clean_title(title):
    version_keywords = [
        "extended", "deluxe", "remaster", "remastered", "live", "acoustic", "edit",
        "version", "anniversary", "special edition", "radio edit", "album version",
        "original mix", "remix", "mix", "dub", "instrumental", "karaoke", "cover",
        "rework", "re-edit", "bootleg", "vip", "session", "alternate", "take",
        "mix cut", "cut", "dj mix"
    ]

    featuring_patterns = [
        r"\(feat\.?.*?\)", r"\[feat\.?.*?\]", r"\(ft\.?.*?\)", r"\[ft\.?.*?\]",
        r"\bfeat\.?\s+\w+", r"\bfeaturing\s+\w+", r"\bft\.?\s+\w+",
        r" - .*mix$", r" - .*dub$", r" - .*remix$", r" - .*edit$", r" - .*version$"
    ]

    title_clean = title.lower().strip()

    for pattern in featuring_patterns:
        title_clean = re.sub(pattern, '', title_clean, flags=re.IGNORECASE).strip()

    for keyword in version_keywords:
        title_clean = re.sub(rf"\b{keyword}\b", "", title_clean, flags=re.IGNORECASE).strip()

    title_clean = re.sub(r"[\s-]+$", "", title_clean)  # Trim trailing spaces or hyphens
    return title_clean


def process_tracks(tracks):
    """
    Process tracks to remove duplicates and balance artist/genre representation.
    """
    filtered_tracks = filter_low_rated_tracks(tracks)
    seen_titles = set()
    unique_tracks = []
    artist_count = Counter()
    genre_count = Counter()
    artist_limit = round(MAX_TRACKS * 0.05)

    for track in filtered_tracks:
        try:
            if not hasattr(track, "ratingKey") or not hasattr(track, "title") or not hasattr(track, "artist"):
                continue

            # Normalize title & artist for comparison
            title_clean = clean_title(track.title)
            artist_obj = track.artist() if callable(getattr(track, "artist", None)) else track.artist
            artist_name = artist_obj.title.lower().strip() if artist_obj else "unknown"
            track_key = (title_clean, artist_name)

            # Deduplicate strictly by title + artist (ignoring ratingKey)
            if track_key in seen_titles:
                continue

            seen_titles.add(track_key)

            # Ensure artist balance
            if artist_count[artist_name] >= artist_limit:
                continue

            # Ensure genre balance
            track_genre = track.genres[0] if track.genres else "Unknown"
            if genre_count[track_genre] >= int(MAX_TRACKS * 0.15):
                continue

            # Store track as unique
            artist_count[artist_name] += 1
            genre_count[track_genre] += 1
            unique_tracks.append(track)

        except Exception:
            pass

    return unique_tracks




def fetch_sonically_similar_tracks(reference_tracks, excluded_keys=None):
    """
    Fetch sonically similar tracks while ensuring excluded tracks (played in the last X days) are removed.
    """
    similar_tracks = []
    now = datetime.now()
    exclude_start = now - timedelta(days=EXCLUDE_PLAYED_DAYS)

    for track in reference_tracks:
        try:
            similars = track.sonicallySimilar(limit=SONIC_SIMILAR_LIMIT)

            # Ensure we're filtering by last play date
            filtered_similars = []
            for s in similars:
                last_played = getattr(s, "lastViewedAt", None)

                # Exclude if it was played recently
                if last_played and last_played >= exclude_start:
                    print(f"EXCLUDED (sonicallySimilar): {s.title} - Last played {last_played}")
                    continue

                # Exclude if it's already in the excluded keys
                if excluded_keys and s.ratingKey in excluded_keys:
                    print(f"EXCLUDED (recent play): {s.title} - In excluded keys")
                    continue

                filtered_similars.append(s)

            # Run deduplication **before** adding similar tracks
            final_similars = process_tracks(filter_low_rated_tracks(filtered_similars))
            similar_tracks.extend(final_similars)

        except Exception as e:
            print(f"Error fetching sonically similar tracks: {e}")
            pass

    return similar_tracks




def similarity_score(current, candidate, limit=20, max_distance=1.0):
    try:
        similars = current.sonicallySimilar(limit=limit, maxDistance=max_distance)
    except Exception:
        return 100
    for index, track in enumerate(similars):
        if track.ratingKey == candidate.ratingKey:
            return index
    return 100

def sort_by_sonic_similarity_greedy(tracks, limit=20, max_distance=1.0):
    if len(tracks) < 2:
        return tracks
    remaining = list(tracks)
    sorted_list = []
    start_index = random.randrange(len(remaining))
    current = remaining.pop(start_index)
    sorted_list.append(current)
    while remaining:
        next_track = min(
            remaining,
            key=lambda candidate: similarity_score(current, candidate, limit, max_distance)
        )
        sorted_list.append(next_track)
        remaining.remove(next_track)
        current = next_track
    return sorted_list

def generate_playlist_title_and_description(period, tracks):
    descriptor_map = load_descriptor_map("moodmap.json")
    day_name = datetime.now().strftime("%A")

    top_genres = [str(g) for t in tracks for g in (t.genres or [])]
    top_moods = [str(m) for t in tracks for m in (t.moods or [])]
    genre_counts = Counter(top_genres)
    mood_counts = Counter(top_moods)

    sorted_genres = [g for g, _ in genre_counts.most_common()]
    sorted_moods = [m for m, _ in mood_counts.most_common()]

    most_common_genre = sorted_genres[0] if sorted_genres else "Eclectic"
    most_common_mood = sorted_moods[0] if sorted_moods else "Vibes"
    second_common_mood = sorted_moods[1] if len(sorted_moods) > 1 else None

    descriptor = random.choice(descriptor_map.get(second_common_mood, ["Vibrant"]))
    period_phrase = get_period_phrase(period)

    title = f"Meloday for {most_common_mood} {descriptor} {most_common_genre} {day_name} {period}"

    max_styles = 6
    highlight_styles = sorted_genres[:3] + sorted_moods[:3]
    highlight_styles = [s for s in highlight_styles if s not in {most_common_genre, most_common_mood}]
    highlight_styles = list(dict.fromkeys(highlight_styles))[:max_styles]
    while len(highlight_styles) < max_styles:
        additional = sorted_genres + sorted_moods
        for s in additional:
            if s not in highlight_styles:
                highlight_styles.append(s)
            if len(highlight_styles) == max_styles:
                break

    if second_common_mood:
        description = (
            f"You listened to {most_common_mood} and {most_common_genre} tracks on {day_name} {period_phrase}. "
            f"Here's some {', '.join(highlight_styles[:-1])}, and {highlight_styles[-1]} tracks as well."
        )
    else:
        description = (
            f"You listened to {most_common_genre} and {most_common_mood} tracks on {day_name} {period_phrase}. "
            f"Here's some {', '.join(highlight_styles[:-1])}, and {highlight_styles[-1]} tracks as well."
        )

    try:
        plex_account = plex.myPlexAccount()
        plex_user = plex_account.title.split()[0] if plex_account.title else plex_account.username
    except Exception:
        plex_user = "you"

    now = datetime.now()
    period_hours = time_periods[period]["hours"]
    last_hour = period_hours[-1]
    next_update_hour = (last_hour + 1) % 24

    next_update = now.replace(hour=next_update_hour, minute=0, second=0)
    if next_update_hour < now.hour:
        next_update += timedelta(days=1)

    next_update_time = next_update.strftime("%I:%M %p").lstrip("0")
    description += f"\n\nMade for {plex_user} • Next update at {next_update_time}."
    return title, description

def apply_text_to_cover(image_path, text):
    try:
        prefix = "Meloday for "
        if text.startswith(prefix):
            text = text[len(prefix):]

        image = Image.open(image_path).convert("RGBA")
        shadow_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        text_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        text_draw = ImageDraw.Draw(text_layer)

        try:
            font_main = ImageFont.truetype(FONT_MAIN_PATH, size=67)
            font_meloday = ImageFont.truetype(FONT_MELODAY_PATH, size=87)
        except IOError:
            font_main = ImageFont.load_default()
            font_meloday = ImageFont.load_default()

        text_box_width = 630
        text_box_right = image.width - 110
        text_box_left = text_box_right - text_box_width
        y = 100

        shadow_offset = 0
        shadow_blur = 40

        lines = wrap_text(text, font_main, text_draw, text_box_width)
        for line in lines:
            bbox = text_draw.textbbox((0, 0), line, font=font_main)
            line_width = bbox[2] - bbox[0]
            x = text_box_left + (text_box_width - line_width)

            shadow_draw.text((x + shadow_offset, y + shadow_offset), line, font=font_main, fill=(0, 0, 0, 120))
            text_draw.text((x, y), line, font=font_main, fill=(255, 255, 255, 255))
            y += bbox[3] - bbox[1] + 10

        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
        meloday_x = 110
        meloday_y = image.height - 200
        shadow_draw.text((meloday_x + shadow_offset, meloday_y + shadow_offset), "Meloday", font=font_meloday, fill=(0, 0, 0, 120))
        text_draw.text((meloday_x, meloday_y), "Meloday", font=font_meloday, fill=(255, 255, 255, 255))

        combined = Image.alpha_composite(image, shadow_layer)
        combined = Image.alpha_composite(combined, text_layer)

        new_image_path = image_path.replace(".webp", "_texted.webp")
        combined.convert("RGB").save(new_image_path)
        return new_image_path
    except Exception:
        return image_path

def create_or_update_playlist(name, tracks, description, cover_file):
    try:
        existing_playlist = None
        for playlist in plex.playlists():
            if playlist.title.startswith("Meloday for "):
                existing_playlist = playlist
                break

        valid_tracks = [t for t in tracks if hasattr(t, "ratingKey")]
        if existing_playlist:
            existing_playlist.removeItems(existing_playlist.items())
            existing_playlist.addItems(valid_tracks)
            existing_playlist.editTitle(name)
            existing_playlist.editSummary(description)
        else:
            existing_playlist = plex.createPlaylist(name, items=valid_tracks)
            existing_playlist.editSummary(description)

        cover_path = os.path.join(COVER_IMAGE_DIR, cover_file)
        if os.path.exists(cover_path):
            new_cover = apply_text_to_cover(cover_path, name)
            existing_playlist.uploadPoster(filepath=new_cover)
    except Exception:
        pass

def find_first_and_last_tracks(tracks, period):
    if not tracks:
        return None, None
    valid_hours = set(time_periods[period]["hours"])
    sorted_tracks = sorted(
        tracks,
        key=lambda t: t.lastViewedAt if hasattr(t, "lastViewedAt") and t.lastViewedAt else datetime.max
    )
    first_track = next((t for t in sorted_tracks if t.lastViewedAt and t.lastViewedAt.hour in valid_hours), None)
    last_track = next((t for t in reversed(sorted_tracks) if t.lastViewedAt and t.lastViewedAt.hour in valid_hours), None)
    if not first_track and sorted_tracks:
        first_track = sorted_tracks[0]
    if not last_track and sorted_tracks:
        last_track = sorted_tracks[-1]
    return first_track, last_track

# ---------------------------------------------------------------------
def main():
    # Step 0% - Start
    print_status(0, "Starting track selection...")

    period = get_current_time_period()
    print_status(10, f"Current time period: {period}")

    # Step 1: Fetch historical
    print_status(20, "Fetching historical tracks...")
    historical, excluded_keys = fetch_historical_tracks(period)

    # Guarantee ~30% historical
    guaranteed_count = int(MAX_TRACKS * 0.3)
    guaranteed_historical = random.sample(historical, min(guaranteed_count, len(historical)))

    # Step 2: Fetch similar
    print_status(30, "Fetching sonically similar tracks...")
    similar = fetch_sonically_similar_tracks(guaranteed_historical, excluded_keys=excluded_keys)

    # Combine
    print_status(40, "Combining & processing tracks...")
    all_tracks = guaranteed_historical + similar
    final_tracks = process_tracks(all_tracks)

    # Step 3: Ensure we reach MAX_TRACKS
    progress_step = 40
    while len(final_tracks) < MAX_TRACKS:
        progress_step += 5
        print_status(progress_step, f"Attempting to add more tracks...")

        more_historical, more_excluded = fetch_historical_tracks(period)
        excluded_keys |= more_excluded
        leftover_count = MAX_TRACKS - len(final_tracks)
        leftover_historical = random.sample(more_historical, min(leftover_count, len(more_historical)))

        more_similar = fetch_sonically_similar_tracks(final_tracks, excluded_keys=excluded_keys)
        additional_tracks = process_tracks(leftover_historical + more_similar)
        final_tracks.extend(additional_tracks[:leftover_count])

        if not additional_tracks:
            break

    print_status(70, "Finding first & last historical tracks...")
    first_track, last_track = find_first_and_last_tracks(final_tracks[:MAX_TRACKS], period)
    middle_tracks = [t for t in final_tracks[:MAX_TRACKS] if t not in {first_track, last_track}]

    # Step 4: Sonic sort (GREEDY)
    if middle_tracks:
        print_status(80, "Performing GREEDY sonic sort...")
        middle_tracks = sort_by_sonic_similarity_greedy(middle_tracks)

    final_ordered_tracks = (
        [first_track] + middle_tracks + [last_track]
        if first_track and last_track else final_tracks[:MAX_TRACKS]
    )

    print_status(90, "Creating/Updating playlist...")
    title, description = generate_playlist_title_and_description(period, final_ordered_tracks)
    create_or_update_playlist(title, final_ordered_tracks, description, time_periods[period]['cover'])

    # Step 5: Done
    print_status(100, "Playlist creation/update complete!")


if __name__ == "__main__":
    main()
