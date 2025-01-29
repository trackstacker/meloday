import os
import re
import random
import logging
import sys
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import openai
from datetime import datetime, timedelta
from plexapi.server import PlexServer
from plexapi.audio import Track
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
    handlers=[
        logging.StreamHandler(sys.stdout)  # Write logs to stdout for Docker
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TimePeriod:
    """Data class for time period configuration"""
    hours: range
    desc: str
    cover: str

@dataclass
class Config:
    """Configuration settings for the application"""
    plex_url: str
    plex_token: str
    openai_api_key: str
    base_playlist_name: str = "Meloday"
    history_lookback_days: int = 30
    max_tracks: int = 50
    historical_ratio: float = 0.5
    sonic_similar_limit: int = 5
    cover_image_dir: str = "covers"

class MelodayApp:
    """Main application class for Meloday"""

    time_periods: Dict[str, TimePeriod] = {
        "Early Morning": TimePeriod(range(4, 8), "Start your day bright and early.", "meloday-02.webp"),
        "Morning": TimePeriod(range(8, 12), "Good vibes for your morning.", "meloday-03.webp"),
        "Afternoon": TimePeriod(range(12, 17), "Keep the energy going through the afternoon.", "meloday-04.webp"),
        "Evening": TimePeriod(range(17, 21), "Relax and unwind as the evening begins.", "meloday-05.webp"),
        "Night": TimePeriod(range(21, 24), "Tunes for a cozy night.", "meloday-06.webp"),
        "Late Night": TimePeriod(range(0, 4), "Late-night jams for night owls.", "meloday-01.webp"),
    }

    def __init__(self):
        """Initialize the Meloday application"""
        self.config = self._load_config()
        self.plex = PlexServer(self.config.plex_url, self.config.plex_token)
        openai.api_key = self.config.openai_api_key
        self.scheduler = BlockingScheduler()

    def _load_config(self) -> Config:
        """Load configuration from environment variables"""
        required_vars = {
            'PLEX_SERVER_URL': os.getenv('PLEX_SERVER_URL'),
            'PLEX_AUTH_TOKEN': os.getenv('PLEX_AUTH_TOKEN'),
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY')
        }

        missing_vars = [k for k, v in required_vars.items() if not v]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        return Config(
            plex_url=required_vars['PLEX_SERVER_URL'],
            plex_token=required_vars['PLEX_AUTH_TOKEN'],
            openai_api_key=required_vars['OPENAI_API_KEY']
        )

    @staticmethod
    def clean_title(title: str) -> str:
        """Normalize track titles for deduplication"""
        return re.sub(r"$.*?$|$.*?$", "", title).strip().lower()

    def categorize_tracks_by_time(self, history: List[Track]) -> Dict[str, List[Track]]:
        """Organize tracks by time period"""
        tracks_by_period = {period: [] for period in self.time_periods}
        for entry in history:
            if hasattr(entry, 'viewedAt') and entry.viewedAt:
                hour = entry.viewedAt.hour
                for period, details in self.time_periods.items():
                    if hour in details.hours:
                        tracks_by_period[period].append(entry)
        return tracks_by_period

    def deduplicate_tracks(self, tracks: List[Track]) -> List[Track]:
        """Deduplicate tracks based on title + artist"""
        unique_tracks = {}
        for track in tracks:
            try:
                key = (self.clean_title(track.title),
                      track.artist().title.lower() if track.artist() else "unknown")
                if key not in unique_tracks:
                    unique_tracks[key] = track
            except Exception as e:
                logger.error(f"Error deduplicating track '{track.title}': {e}")
        return list(unique_tracks.values())

    def find_similar_tracks(self, tracks: List[Track]) -> List[Track]:
        """Find sonically similar tracks while avoiding duplicates"""
        similar_tracks = []
        seen_tracks = set()

        for track in tracks:
            try:
                for similar in track.sonicallySimilar(limit=self.config.sonic_similar_limit):
                    key = (self.clean_title(similar.title),
                          similar.artist().title.lower() if similar.artist() else "unknown")
                    if key not in seen_tracks:
                        seen_tracks.add(key)
                        similar_tracks.append(similar)
            except Exception as e:
                logger.warning(f"Error finding similar tracks for '{track.title}': {e}")

        return self.deduplicate_tracks(similar_tracks)

    def generate_playlist_metadata(self, time_period: str, tracks: List[Track]) -> Tuple[str, str]:
        """Generate AI-powered playlist title and description"""
        track_titles = [f"{track.title} by {track.artist().title}" for track in tracks[:5]]
        current_day = datetime.now().strftime("%A")

        messages = [
            {"role": "system", "content": "You're a DJ curating playlists for specific days and dayparts."},
            {"role": "user", "content": f"""
            Create a playlist title and description for:
            - Day: {current_day}
            - Time: {time_period}
            - Sample tracks: {', '.join(track_titles)}

            Format:
            Title: "Meloday for [Creative Name]"
            Description: Brief, engaging description of the music style and mood.
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
            title, description = content.split("\n", 1)
            return title.strip(), description.strip()
        except Exception as e:
            logger.error(f"Error generating title/description: {e}")
            return (f"Meloday for {current_day} {time_period}",
                   f"Your {time_period} playlist for {current_day}")

    def update_playlist(self) -> None:
        """Main function to update the playlist"""
        try:
            logger.info("Starting playlist update")

            # Get current time period
            current_hour = datetime.now().hour
            current_period = next((period for period, details in self.time_periods.items()
                                 if current_hour in details.hours), "Late Night")

            # Fetch and process tracks
            music_section = self.plex.library.section('Music')
            history = music_section.history(
                mindate=datetime.now() - timedelta(days=self.config.history_lookback_days)
            )

            tracks_by_period = self.categorize_tracks_by_time(history)
            selected_tracks = self.deduplicate_tracks(tracks_by_period.get(current_period, []))

            # Create playlist
            historical_count = int(self.config.max_tracks * self.config.historical_ratio)
            historical_tracks = random.sample(selected_tracks, min(len(selected_tracks), historical_count))
            similar_tracks = self.find_similar_tracks(historical_tracks)

            all_tracks = self.deduplicate_tracks(historical_tracks + similar_tracks)[:self.config.max_tracks]

            if not all_tracks:
                logger.warning("No tracks found for playlist")
                return

            # Generate metadata and update playlist
            title, description = self.generate_playlist_metadata(current_period, all_tracks)

            # Update or create playlist
            existing_playlist = next((p for p in self.plex.playlists()
                                   if p.title.startswith("Meloday for ")), None)

            if existing_playlist:
                existing_playlist.removeItems(existing_playlist.items())
                existing_playlist.addItems(all_tracks)
                existing_playlist.editTitle(title)
                existing_playlist.editSummary(description)
                playlist = existing_playlist
            else:
                playlist = self.plex.createPlaylist(title, items=all_tracks)
                playlist.editSummary(description)

            # Update cover image
            cover_path = os.path.join(
                self.config.cover_image_dir,
                self.time_periods[current_period].cover
            )
            if os.path.exists(cover_path):
                playlist.uploadPoster(filepath=cover_path)

            logger.info(f"Successfully updated playlist '{title}' with {len(all_tracks)} tracks")

        except Exception as e:
            logger.error(f"Error updating playlist: {e}")

    def schedule_updates(self) -> None:
        """Configure and start the scheduler"""
        # Schedule updates for each time period transition
        for period in self.time_periods:
            start_hour = self.time_periods[period].hours[0]
            self.scheduler.add_job(
                self.update_playlist,
                CronTrigger(hour=start_hour, minute=0)
            )

        # Add an immediate update when starting
        self.scheduler.add_job(self.update_playlist)

        logger.info("Scheduler started - playlist will update at the start of each time period")
        self.scheduler.start()

def main():
    """Main entry point"""
    try:
        app = MelodayApp()
        app.schedule_updates()
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}")

if __name__ == "__main__":
    main()