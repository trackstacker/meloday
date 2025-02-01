# Meloday - Dynamic Plex Playlist Generator

Meloday is a Python script that dynamically generates and updates playlists on your Plex server based on your listening history and time of day. Inspired by Spotify’s Daylist, it creates personalized playlists using Plex metadata.

## Features
- Automatically generates time-of-day themed playlists (e.g., "Meloday for Chillwave Friday Night")
- Uses Plex listening history to suggest music
- Filters out 1-star rated tracks for a refined experience
- Sonic similarity-based recommendations for better playlist flow
- Toggleable AI support for enhanced playlist titles and descriptions
- AI-assisted track selection for context-appropriate songs (optional)
- Automatically updates playlists in Plex
- Beautiful covers for each time-of-day

## What's New in v2.0
- Toggleable OpenAI support: AI-enhanced playlist titles and descriptions can be turned on or off.
- AI-generated playlist descriptions are more detailed and varied.
- AI may prioritize tracks that fit the time of day (e.g., a song called "Coffee" for early mornings).
- Formatting changes to remove special characters and markup language from titles and descriptions.
- Meloday covers have been updated and renamed to make them easier to identify.
- Versions of covers without text have been added for users who want to customize them.

### Example Playlist Titles & Descriptions

Without AI  
Title: Meloday for Romantic Downtempo Bass Saturday Afternoon  
Description: You listened to Downtempo Bass and Romantic in the Afternoon. Here's some Escape Room, Indie Soul, Confident, and Sensual tracks as well.

With AI  
Title: Meloday for Dreamy Lounge Grooves Saturday Afternoon  
Description: You’ve been drifting through Downtempo Bass and Romantic vibes this afternoon. Let’s add some smooth Indie Soul, confident Escape Room beats, and a touch of Sensual energy. Start with "Neon Dreams" by The Midnight, then ease into "Stay Awhile" by Rhye before closing with the hypnotic pulse of "After Dark" by Mr. Kitty.

## Requirements
- Python 3.7 or later
- Plex Media Server with a Music library
- OpenAI API Key (optional, for AI-generated playlist titles and descriptions) – [Get yours here](https://platform.openai.com/)
- Plex API Token (for authentication and interaction with Plex) – [How to find it](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)
- PlexAPI Python library

## Installation

### 1. Install dependencies:
pip install plexapi  
pip install openai  

If you do not want AI enhancements, you can skip installing OpenAI.

### 2. Configure environment:
Edit the script to set your Plex server details:

PLEX_URL = 'http://127.0.0.1:32400'  # Replace with your Plex URL  
PLEX_TOKEN = 'YOUR_PLEX_TOKEN'  # Replace with your Plex authentication token  
openai.api_key = "YOUR_OPENAI_API_KEY"  # Optional, replace if using AI features  
USE_AI_ENHANCEMENTS = False  # Set to True if you want AI-enhanced playlist titles and descriptions  

### 3. Run the script:
python meloday.py  

Your playlist should now be updated in Plex.

## Automating with Windows Task Scheduler
To schedule the script to run automatically at different times of the day, follow these steps:

1. Open Task Scheduler:  
   - Press Win + R, type taskschd.msc, and press Enter.  

2. Create a New Task:  
   - Click Action > Create Task.  
   - Under the General tab:  
     - Name the task (e.g., Meloday Morning Playlist).  
     - Check Run with highest privileges.  

3. Set Triggers for Different Time Periods:  
   - Go to the Triggers tab and click New.  
   - Set the time you want the script to run.  
   - Choose Daily and repeat this step for other time periods.  

4. Set the Action to Run the Script:  
   - Go to the Actions tab and click New.  
   - Choose Start a Program.  
   - In the Program/script field, enter the path to Python:  

     C:\Path\To\Python\python.exe  

   - In the Add arguments field, enter:  

     "C:\Path\To\meloday.py"  

   Replace "C:\Path\To\meloday.py" with the full path of your script.  

5. Finalize and Enable the Task:  
   - Click OK and enter your Windows password if prompted.  
   - Right-click the task and choose Run to test it.  

Your playlists should update automatically at the configured times.

## Support This Project
If you find Meloday useful and want to support its development, consider donating:  
[Buy Me a Coffee](https://buymeacoffee.com/trackstack)
