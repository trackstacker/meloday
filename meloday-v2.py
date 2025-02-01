import os
import re
import random
from datetime import datetime, timedelta
from plexapi.server import PlexServer

# --- PLEX SERVER CONFIGURATION ---
PLEX_URL = 'http://127.0.0.1:32400'  
PLEX_TOKEN = 'YOUR_PLEX_TOKEN'  
plex = PlexServer(PLEX_URL, PLEX_TOKEN, timeout=60)
MUSIC_LIBRARY = 'Music'
COVER_IMAGE_DIR = r"YOUR_COVER_DIR" 

# --- AI ENHANCEMENT TOGGLE ---
USE_AI_ENHANCEMENTS = False  # Set to False to disable AI

# --- CONDITIONAL OPENAI IMPORT ---
try:
    if USE_AI_ENHANCEMENTS:
        import openai
except ImportError:
    USE_AI_ENHANCEMENTS = False 

# --- OPENAI API CONFIGURATION ---
if USE_AI_ENHANCEMENTS:
    openai.api_key = ""  # Replace with your OpenAI API Key, leave blank if not using AI

# --- PLAYLIST CONFIGURATION ---
BASE_PLAYLIST_NAME = "Meloday"
HISTORY_LOOKBACK_DAYS = 30
MAX_TRACKS = 50
HISTORICAL_RATIO = 0.4  # 40%
SONIC_SIMILAR_LIMIT = 5

# --- DAY PARTS CONFIGURATION ---
time_periods = {
    "Early Morning": {"hours": range(4, 8), "cover": "early-morning.webp"},
    "Morning": {"hours": range(8, 12), "cover": "morning.webp"},
    "Afternoon": {"hours": range(12, 17), "cover": "afternoon.webp"},
    "Evening": {"hours": range(17, 21), "cover": "evening.webp"},
    "Night": {"hours": range(21, 24), "cover": "night.webp"},
    "Late Night": {"hours": range(0, 4), "cover": "late-night.webp"},
}

# --- UTILITY FUNCTIONS ---
def get_current_day():
    return datetime.now().strftime("%A")

def clean_title(title):
    return re.sub(r"\(.*?\)|\[.*?\]", "", title).strip().lower()

def get_current_time_period():
    current_hour = datetime.now().hour
    for period, details in time_periods.items():
        if current_hour in details["hours"]:
            return period
    return "Late Night" 

# --- AI ENHANCEMENT FUNCTION ---
def enhance_with_ai(title, description, added_styles, selected_genre, selected_mood, tracks, previous_genres, previous_moods):
    if not USE_AI_ENHANCEMENTS:
        return title, description  
    
    styles_text = ", ".join(added_styles) if added_styles else ""
    previous_genres_text = ", ".join(previous_genres) if previous_genres else selected_genre
    previous_moods_text = ", ".join(previous_moods) if previous_moods else selected_mood

    track_data = [(t.title, t.artist().title if t.artist() else "Unknown Artist") for t in tracks if hasattr(t, "title")]

    if len(track_data) < 3:
        return title, description  # Not enough data, fallback to original

    (first_track, first_artist) = track_data[0]
    (middle_track, middle_artist) = track_data[len(track_data) // 2]
    (last_track, last_artist) = track_data[-1]

    track_snippet = f'"{first_track}" by {first_artist}, "{middle_track}" by {middle_artist}, and "{last_track}" by {last_artist}'

    fact_track, fact_artist = random.choice([track_data[0], track_data[len(track_data) // 2], track_data[-1]])

    prompt = f"""
    You are a music journalist and radio DJ curating a playlist intro with personality and flow.

    **Title Guidelines:**
    - The title should follow this format: "Meloday for [fitting clever adjective] [genre] [day] [time period]".
    - The adjective should match the **mood** and **energy** of the playlist. Example adjectives: "Brat", "Dreamy", "Electric", "Hazy", "Slick", "Vibrant".
    - The genre should be **clear but fun**. If multiple genres, combine them in a natural way.
    - **Keep it short** (~5 words max after "Meloday for").
    - Always prefix the playlist with "Meloday for" if it's not present, but do not repeat it more than once.
    - Do not include any markup language or special characters (##, !, ", -, :, etc).
    - Do not add the word Title: to the title itself

    **Description Guidelines:**
    - Write in the tone of an engaging **music journalist or DJ**.
    - Start by mentioning **the previous genres and moods** the listener was into.
    - Then, introduce the **new additions (added styles)** to the mix.
    - Mention the **first, middle, and last tracks** with their **artist names**.
    - **Pick one** of those three artists and add an interesting fact, insight, or note about why they fit the playlist.
    - Example:
      - "You've been deep into Chillhop and Aggressive this morning—now ride the wave with Pop, Kinetic, and Hypnotic grooves. We're starting with ‘Neon Skyline’ by Andy Shauf, an indie groove perfect for lazy mornings. Then, ‘Afterglow’ by CHVRCHES layers shimmering synth textures, before closing with ‘Electric Sunset’ by Washed Out."
      - "You've been grooving to British Soul and Funk this afternoon. Now let's bring in some Future Bass and Cosmic Disco. We’re easing in with ‘Pink + White’ by Frank Ocean, then drifting into ‘Tame Impala’ with ‘Borderline,’ and closing with ‘Spotless Mind’ by Jhene Aiko. Jhene’s dreamy storytelling is the perfect way to wrap up this mix."
    - Do not include any markup language or special characters (##, !, ", -, :, etc).
    - Do not add thr word Description: to the description itself

    **Data for this playlist:**
    - Current Title: {title}
    - Current Description: {description}
    - Previous Genres: {previous_genres_text}
    - Previous Moods: {previous_moods_text}
    - Added Styles: {styles_text}
    - Featured Tracks: {track_snippet}
    - Fun Fact Focus: "{fact_track}" by {fact_artist}

    **Return exactly two lines without any labels, prefixes, or formatting:**
    Line 1 = Improved title (no extra words)
    Line 2 = Improved description (short, engaging, DJ-style, retaining all details)
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=180,
            temperature=0.9 
        )
        ai_text = response['choices'][0]['message']['content'].strip().split("\n")
        ai_title = ai_text[0].strip() if len(ai_text) > 0 else title
        ai_description = ai_text[1].strip() if len(ai_text) > 1 else description
        return ai_title, ai_description
    except Exception as e:
        print(f"AI Enhancement failed: {e}")
        return title, description  


# --- STEP 1: FETCH LISTENING HISTORY ---
def fetch_recent_tracks():
    """Fetch the user's historical listening data from Plex."""
    music_section = plex.library.section('Music')
    history_entries = music_section.history(mindate=datetime.now() - timedelta(days=HISTORY_LOOKBACK_DAYS))

    tracks_by_period = {period: [] for period in time_periods}

    for entry in history_entries:
        try:
            track = plex.library.fetchItem(entry.ratingKey)

            if not hasattr(track, "title"):  
                continue

            hour = entry.viewedAt.hour if hasattr(entry, 'viewedAt') and entry.viewedAt else None
            if hour is not None:
                for period, details in time_periods.items():
                    if hour in details["hours"]:
                        tracks_by_period[period].append(track)
        except Exception as e:
            print(f"Error retrieving track metadata: {e}")
            continue

    return tracks_by_period

# --- STEP 2: DEDUPLICATE & FILTER TRACKS ---
def filter_excluded_tracks(tracks):
    """Removes tracks where the song, album, or artist has a 1-star rating."""
    filtered_tracks = []
    
    for track in tracks:
        try:
            if hasattr(track, "userRating") and track.userRating == 1:
                continue  
            
            album = track.album() if hasattr(track, "album") else None
            if album and hasattr(album, "userRating") and album.userRating == 1:
                continue  

            artist = track.artist() if hasattr(track, "artist") else None
            if artist and hasattr(artist, "userRating") and artist.userRating == 1:
                continue  

            filtered_tracks.append(track)

        except Exception as e:
            print(f"Error filtering track: {e}")
            continue 

    return filtered_tracks

# --- STEP 3: DEDUPLICATE TRACKS ---
def deduplicate_tracks(tracks):
    """Removes duplicate tracks based on title and artist, while filtering out excluded tracks."""
    unique_tracks = {}
    
    filtered_tracks = filter_excluded_tracks(tracks)

    for track in filtered_tracks:
        try:
            key = (clean_title(track.title), track.artist().title.lower() if track.artist() else "unknown")
            if key not in unique_tracks:
                unique_tracks[key] = track
        except Exception:
            pass  
    
    return list(unique_tracks.values())


# --- STEP 4: GENERATE PLAYLIST TITLE & DESCRIPTION ---
def generate_playlist_title_and_description(time_period, tracks):
    """Generate a structured playlist title and description, optionally enhanced with AI."""
    top_genres = list(set(str(g) for t in tracks for g in (t.genres or [])))
    top_moods = list(set(str(m) for t in tracks for m in (t.moods or [])))

    selected_genre = random.choice(top_genres) if top_genres else "Eclectic"
    selected_mood = random.choice(top_moods) if top_moods else "Vibes"
    current_day = get_current_day()

    added_genres = list(set(top_genres) - {selected_genre})
    added_moods = list(set(top_moods) - {selected_mood})

    previous_genres = top_genres[:]
    previous_moods = top_moods[:]

    sampled_genres = random.sample(added_genres, min(2, len(added_genres))) if added_genres else []
    sampled_moods = random.sample(added_moods, min(2, len(added_moods))) if added_moods else []

    added_styles = sampled_genres + sampled_moods

    if added_styles:
        if len(added_styles) == 1:
            added_text = f"Here's some {added_styles[0]} tracks as well."
        elif len(added_styles) == 2:
            added_text = f"Here's some {added_styles[0]} and {added_styles[1]} tracks as well."
        else:
            added_text = f"Here's some {', '.join(added_styles[:-1])}, and {added_styles[-1]} tracks as well."
    else:
        added_text = ""

    title = f"Meloday for {selected_mood} {selected_genre} {current_day} {time_period}"
    description = f"You listened to {selected_genre} and {selected_mood} in the {time_period}. {added_text}"

    if USE_AI_ENHANCEMENTS:
        title, description = enhance_with_ai(title, description, added_styles, selected_genre, selected_mood, tracks, previous_genres, previous_moods)

    return title, description
    
def prioritize_tracks_with_ai(tracks, time_period):
    """Uses AI to prioritize songs that fit the daypart context based on their title or artist name."""
    
    track_data = [(t.title, t.artist().title if t.artist() else "Unknown Artist") for t in tracks if hasattr(t, "title")]
    
    if not track_data:
        return tracks 
    
    track_list_text = "\n".join([f"{title} by {artist}" for title, artist in track_data])

    prompt = f"""
    You are a music curator refining a playlist for the {time_period}.
    
    **Objective:**
    - Prioritize tracks that naturally fit the {time_period}.
    - Consider song **titles** and **artist names** when making decisions.
    - Do NOT add new songs—only reorder what is already provided.

    **Examples:**
    - Morning: Prioritize tracks related to waking up, coffee, morning light, sunshine.
    - Afternoon: Prioritize upbeat songs related to energy, motion, productivity.
    - Evening: Prioritize chill, relaxed songs, sunset-related.
    - Late Night: Prioritize dreamy, atmospheric, nocturnal-themed music.

    **Tracklist:**
    {track_list_text}

    **Instructions:**
    - Reorder the list, **placing the most relevant tracks first** based on the {time_period}.
    - The final list should retain ALL original tracks, but with **better flow**.
    - Do NOT include explanations—just return the reordered list in this format:
      - Line 1: "New Order:"
      - Line 2 and onward: The reordered tracks, one per line.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.7
        )

        ai_text = response['choices'][0]['message']['content'].strip().split("\n")

        if not ai_text[0].startswith("New Order:"):
            print("AI response not formatted correctly. Using original order.")
            return tracks

        reordered_titles = [line.strip() for line in ai_text[1:]]

        reordered_tracks = []
        for title in reordered_titles:
            for track in tracks:
                if track.title == title:
                    reordered_tracks.append(track)
                    break 

        remaining_tracks = [t for t in tracks if t not in reordered_tracks]
        return reordered_tracks + remaining_tracks  

    except Exception as e:
        print(f"AI Prioritization failed: {e}")
        return tracks  
    


# --- STEP 5: CREATE OR UPDATE PLAYLIST ---
def create_or_update_playlist(name, tracks, description, cover_file):
    """Finds and updates an existing 'Meloday for' playlist or creates a new one."""
    try:
        existing_playlist = None
        for playlist in plex.playlists():
            if playlist.title.startswith("Meloday for "):  
                existing_playlist = playlist
                break  
        valid_tracks = [track for track in tracks if hasattr(track, "ratingKey")]

        if existing_playlist:
            print(f"Updating existing playlist: {existing_playlist.title}")

            existing_playlist.removeItems(existing_playlist.items())
            existing_playlist.addItems(valid_tracks)
            existing_playlist.editTitle(name) 
            existing_playlist.editSummary(description)

        else:
            print(f"Creating new playlist: {name}")
            existing_playlist = plex.createPlaylist(name, items=valid_tracks)
            existing_playlist.editSummary(description)

        cover_path = os.path.join(COVER_IMAGE_DIR, cover_file)
        if os.path.exists(cover_path):
            print(f"Uploading cover image: {cover_path}")
            existing_playlist.uploadPoster(filepath=cover_path)
        else:
            print(f"Cover image not found: {cover_path}")

        print(f"Playlist '{existing_playlist.title}' updated with {len(valid_tracks)} tracks.")

    except Exception as e:
        print(f"Error creating/updating playlist: {e}")



# --- MAIN EXECUTION ---
def main():
    history = fetch_recent_tracks()
    period = get_current_time_period()
    all_tracks = deduplicate_tracks(history[period])[:MAX_TRACKS]

    if USE_AI_ENHANCEMENTS:
        all_tracks = prioritize_tracks_with_ai(all_tracks, period)

    title, description = generate_playlist_title_and_description(period, all_tracks)
    create_or_update_playlist(title, all_tracks, description, time_periods[period]['cover'])

if __name__ == "__main__":
    main()

