
# Meloday: A daylist for Plex  
### *Docker support coming soon*

## Overview of v2.2
Meloday is a script that **automatically creates playlists throughout the day**, evolving with your listening habits. Inspired by Spotify’s **daylist**, it pulls tracks from your **Plex listening history**, finds **patterns in what you like at different times**, and builds a mix that feels both **familiar and fresh**—without getting repetitive.  

Each playlist update brings a **new cover, a new name, and a fresh mix of tracks** that fit the current moment. It also reaches into a **custom-built mood map** filled with different ways to describe the playlist’s vibe, so the names always stay interesting.  

## What It Does  
- **Creates playlists based on your past listening habits** – It looks at what you’ve played before at the same time of day.  
- **Avoids repeats** – Tracks you’ve played too recently won’t be included.  
- **Finds sonically similar tracks** – It expands your playlist with music that fits the vibe.  
- **Uses Plex metadata, not AI** – Everything is based on your existing library and Plex’s own data.  
- **Automatically updates itself** – No manual curation needed.  
- **Applies custom covers and descriptions** – The playlist gets a new look each time it updates.  
- **Gets creative with playlist names** – It pulls words from a mood map for extra variety.  



## What It *Doesn’t* Do  
- **It doesn’t add songs from outside your Plex library** – Everything comes from what you already have.  
- **It doesn’t use AI recommendations** – There’s no external algorithm picking tracks, just your own listening history.  
- **It doesn’t force specific genres or moods** – Your past listening shapes each playlist organically. 
- **It doesn’t replace your other playlists** – This just runs alongside whatever else you have in Plex.  



## How It Works  

### 1. Identifies the Current Time Period  
- Meloday divides the day into **morning, afternoon, evening, night, etc.**  
- The script figures out the current time and selects the right time period.  

### 2. Pulls Tracks from Your Listening History  
- It looks at **what you’ve played at this time of day in the past**.  
- If a track was **played too recently**, it’s skipped to keep things fresh.  

### 3. Finds Sonically Similar Tracks  
- It uses Plex’s **sonicallySimilar()** function to find related songs.  
- This helps the playlist feel cohesive instead of just being a random shuffle.  

### 4. Filters & Organizes Tracks  
- **Duplicates** (live versions, remixes, etc.) are removed if they’re too similar.  
- **Low-rated tracks** (anything with 1 or 2 stars) are skipped.  
- **A mix of popular and rare tracks** is used so the playlist doesn’t feel repetitive.  

### 5. Sorts the Playlist for a Natural Flow  
- The **first track** is the earliest one you’ve played in that time period.  
- The **last track** is the most recent one you’ve played in that time period.  
- Everything in between is sorted by **sonic similarity** for smooth transitions.  

### 6. Creates a Playlist Title & Description  
Every playlist gets a **unique, descriptive name** based on what you’ve been listening to. Meloday doesn’t just pull from a basic list of moods—it taps into a **custom-built mood map** that expands common moods into more creative variations.  

For example, if the playlist has a **cheerful vibe**, it won’t just call it "Cheerful." Instead, it might use words like:  Joyous, Sunny, Happy, Upbeat, or Jovial. Or, if it leans a bit more **quirky**, it might get a title with words like: Eccentric, Unconventional, Odd, or Whimsical.

This means **every playlist name feels different**, even if the mood stays similar, so maybe a *Brash Vibrant Lo-Fi Study Wednesday Evening* is in your future.

### 7. Applies a Cover & Updates the Playlist in Plex  
- The cover image changes depending on the time of day.  
- The script applies a **text overlay** to customize the cover.  
- The playlist is updated with the new tracks, title, and description.  

## Best Mileage  

Meloday works best with **larger music libraries**. Since it pulls from **your own past listening**, the more variety you have, the better the playlists will be.  

- If your **library is small**, Meloday might start repeating songs more often, creating a **feedback loop** where the same tracks show up frequently.  
- If you **haven't rated your tracks**, it will still work, but if you take the time to rate songs (1-5 stars), Meloday will be able to **avoid low-rated content** and refine selections over time.  
- Playlist generation *should* work for just about any size you make it, but a larger size will no doubt take longer to generate.  
- Meloday was **tested on a library of only about 25,000 tracks**, so your mileage may vary on significantly smaller or larger collections.  

## What’s Changed Since v2  

- **No more OpenAI** – Focused on **core functionality first** before expanding into AI recommendations in the future.  
- **Mood map integration** – More **random and creative titles/descriptions** based on expanded word choices.  
- **Plex username support** – The playlist description now **includes your Plex username** for a more personal touch.  
- **Next update time in the description** – Now tells you **exactly when the playlist will refresh**.  
- **More fallback methods** – If not enough historical data is available, Meloday will **use additional logic to fill the playlist** instead of leaving gaps.  
- **Now strictly maintains a single playlist** – Meloday is designed to provide one evolving playlist that updates throughout the day. The logic has been improved to ensure it no longer creates multiple playlists unintentionally. If you experienced this issue before, it should now be resolved.

## Who Made This?  
Just me, and a bit of help from ChatGPT! I’m learning as I go, and this seemed like a fun project to try out. It started as a small project for myself, but as I continued to use it, I found it really enjoyable and exciting to look forward to listening to every day! I figured I'd share it with the community, get more feedback, share the idea and see what happened! If you’re enjoying Meloday and feel like saying thanks, [a coffee is always appreciated](https://buymeacoffee.com/trackstack). No pressure at all though, I just want people to enjoy it!  



## Installation

### 1. Install dependencies:
pip install -r requirements.txt  

This will install:
- `plexapi` (for communicating with Plex)
- `Pillow` (for handling playlist cover images)
- `pyyaml` (for reading the config file)

### 2. Configure environment:
Edit the `config.yml` file to set your Plex server details:

plex:  
  url: "http://localhost:32400"  # Replace with your Plex URL  
  token: "YOUR_PLEX_TOKEN"  # Replace with your Plex authentication token - [How to find it](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)
  music_library: "Music"  # Replace with the name of your Plex music library  

Modify playlist settings if needed (*recommended to try it initially with these settings*):

playlist:  
  exclude_played_days: 4  # Ignore tracks played in the last X days  
  history_lookback_days: 30  # How many days of listening history to analyze  
  max_tracks: 50  # Maximum number of tracks in each playlist  

### 3. Run the script:
python meloday.py  

Your playlist should now be updated in Plex.

## Automating with Windows Task Scheduler
To schedule the script to run automatically at different times of the day, follow these steps:

1. Open Task Scheduler:  
   - Press Win + R, type `taskschd.msc`, and press Enter.  

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

     `C:\Path\To\Python\python.exe`  

   - In the Add arguments field, enter:  

     `"C:\Path\To\meloday.py"`  

   Replace `"C:\Path\To\meloday.py"` with the full path of your script.  

5. Finalize and Enable the Task:  
   - Click OK and enter your Windows password if prompted.  
   - Right-click the task and choose Run to test it.  

Your playlists should update automatically at the configured times.


