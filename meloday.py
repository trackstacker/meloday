import os
import re
import random
import openai
from datetime import datetime, timedelta
from plexapi.server import PlexServer

# Plex server details
PLEX_URL = '<PLEX_SERVER_URL>'
PLEX_TOKEN = '<PLEX_AUTH_TOKEN>'
plex = PlexServer(PLEX_URL, PLEX_TOKEN)

# OpenAI API Key
openai.api_key = "<OPENAI_API_KEY>"

# Playlist and configuration constants
BASE_PLAYLIST_NAME = "Meloday"
HISTORY_LOOKBACK_DAYS = 30
MAX_TRACKS = 50
HISTORICAL_RATIO = 0.5  # 50% historical tracks
SONIC_SIMILAR_LIMIT = 5
COVER_IMAGE_DIR = r"<COVER_IMAGE_DIRECTORY_PATH>"

# Time periods and metadata
time_periods = {
    "Early Morning": {"hours": range(4, 8), "desc": "Start your day bright and early.", "cover": "meloday-02.webp"},
    "Morning": {"hours": range(8, 12), "desc": "Good vibes for your morning.", "cover": "meloday-03.webp"},
    "Afternoon": {"hours": range(12, 17), "desc": "Keep the energy going through the afternoon.", "cover": "meloday-04.webp"},
    "Evening": {"hours": range(17, 21), "desc": "Relax and unwind as the evening begins.", "cover": "meloday-05.webp"},
    "Night": {"hours": range(21, 24), "desc": "Tunes for a cozy night.", "cover": "meloday-06.webp"},
    "Late Night": {"hours": range(0, 4), "desc": "Late-night jams for night owls.", "cover": "meloday-01.webp"},
}

def get_current_day():
    """Returns the full name of the current weekday (e.g., 'Tuesday')."""
    return datetime.now().strftime("%A")

def clean_title(title):
    """Normalize track titles for deduplication."""
    return re.sub(r"\(.*?\)|\[.*?\]", "", title).strip().lower()

def categorize_tracks_by_time(history):
    """Organize tracks by time period."""
    tracks_by_period = {period: [] for period in time_periods}
    for entry in history:
        if hasattr(entry, 'viewedAt') and entry.viewedAt:
            hour = entry.viewedAt.hour
            for period, details in time_periods.items():
                if hour in details["hours"]:
                    tracks_by_period[period].append(entry)
    return tracks_by_period

def deduplicate_tracks(tracks):
    """Deduplicate tracks based on title + artist (ignoring album versions)."""
    unique_tracks = {}
    for track in tracks:
        try:
            key = (clean_title(track.title), track.artist().title.lower() if track.artist() else "unknown")
            if key not in unique_tracks:
                unique_tracks[key] = track
        except Exception as e:
            print(f"Error deduplicating track '{track.title}': {e}")
    return list(unique_tracks.values())

def find_similar_tracks(tracks, limit=SONIC_SIMILAR_LIMIT):
    """Find sonically similar tracks while avoiding duplicates."""
    similar_tracks = []
    seen_tracks = set()

    for track in tracks:
        try:
            for similar in track.sonicallySimilar(limit=limit):
                key = (clean_title(similar.title), similar.artist().title.lower() if similar.artist() else "unknown")
                if key not in seen_tracks:
                    seen_tracks.add(key)
                    similar_tracks.append(similar)
        except Exception:
            pass  # Ignore errors and continue
    return deduplicate_tracks(similar_tracks)

def generate_dynamic_title_and_description(time_period, tracks):
    """Use AI to generate a properly formatted playlist title and description."""
    track_titles = [f"{track.title} by {track.artist().title}" for track in tracks[:5]]
    current_day = get_current_day()

    messages = [
        {"role": "system", "content": "You're a DJ curating playlists for specific days and dayparts. Ensure the title follows the correct format and the description reflects past listening habits."},
        {"role": "user", "content": f"""
        - Create a unique, fun playlist title that follows this format: 'Meloday for [Fun Daypart Title]'. Example: 'Meloday for Electropop Tuesday Afternoons'.
        - The title must always begin with "Meloday for", but do NOT repeat "Meloday for" if it’s already there.
        - The [Fun Daypart Title] should be creative and reflect listening habits, including the current day ({current_day}) and a mood or genre.
        - Example: 'Meloday for Chillwave Thursday Nights' or 'Meloday for Funky Tuesday Afternoons'.
        
        - The description must be formatted like:
          'You listened to [genres] on {current_day} in the {time_period}! Here's some [related genres].'
        
        - The playlist contains these tracks: {', '.join(track_titles)}.
        - Do NOT include "Title:", "Description:", or any unnecessary labels in the response. Just return the title and description.
        """}
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150,
            temperature=0.8
        )
        content = response.choices[0].message['content'].strip()

        # Split AI output into title + description
        lines = content.split("\n", 1)
        raw_title = lines[0].strip()
        raw_description = lines[1].strip() if len(lines) > 1 else "You listened to various genres. Here's a mix to match your vibe."

        # Ensure correct title formatting
        if raw_title.startswith("Meloday for "):
            playlist_title = raw_title  # Use as-is if AI correctly formatted it
        else:
            playlist_title = f"Meloday for {raw_title}"

        # Ensure "Description:" is removed from the output
        description = raw_description.replace("Description:", "").strip()

        return playlist_title, description

    except Exception as e:
        print(f"Error generating title/description: {e}")
        return f"Meloday for {current_day} {time_period}", f"You listened to music on {current_day} in the {time_period}. Here's a mix to match your vibe."

def create_or_update_playlist(name, tracks, description, cover_file):
    """Find an existing 'Meloday for' playlist and update it, or create one if it doesn't exist."""
    try:
        # Search for an existing playlist that starts with "Meloday for "
        existing_playlist = next((p for p in plex.playlists() if p.title.startswith("Meloday for ")), None)

        if existing_playlist:
            print(f"Updating existing playlist: {existing_playlist.title}")
            existing_playlist.removeItems(existing_playlist.items())  # Clear old tracks
            existing_playlist.addItems(tracks)  # Add new tracks
            existing_playlist.editTitle(name)  # Update the playlist title
            existing_playlist.editSummary(description)  # Update description
            playlist = existing_playlist  # Use the existing playlist
        else:
            print(f"Creating new playlist: {name}")
            playlist = plex.createPlaylist(name, items=tracks)
            playlist.editSummary(description)

        # Update the playlist cover
        cover_path = os.path.join(COVER_IMAGE_DIR, cover_file)
        if os.path.exists(cover_path):
            playlist.uploadPoster(filepath=cover_path)

        print(f"Playlist '{playlist.title}' updated with {len(tracks)} tracks.")

    except Exception as e:
        print(f"Error creating/updating playlist: {e}")

def main():
    print("Fetching listening history...")
    music_section = plex.library.section('Music')
    history = music_section.history(mindate=datetime.now() - timedelta(days=HISTORY_LOOKBACK_DAYS))

    print("Categorizing tracks by time period...")
    tracks_by_period = categorize_tracks_by_time(history)

    current_hour = datetime.now().hour
    current_period = next((period for period, details in time_periods.items() if current_hour in details["hours"]), "Late Night")

    selected_tracks = deduplicate_tracks(tracks_by_period.get(current_period, []))
    historical_tracks = random.sample(selected_tracks, min(len(selected_tracks), int(MAX_TRACKS * HISTORICAL_RATIO)))
    similar_tracks = find_similar_tracks(historical_tracks)

    all_tracks = deduplicate_tracks(historical_tracks + similar_tracks)[:MAX_TRACKS]
    title, description = generate_dynamic_title_and_description(current_period, all_tracks)

    create_or_update_playlist(title, all_tracks, description, time_periods[current_period]['cover'])

if __name__ == "__main__":
    main()
