# Meloday - Dynamic Plex Playlist Generator

Meloday is a Python script that dynamically generates and updates playlists on your Plex server based on your listening history and time of day.

## Requirements

- **Python**: Ensure you have Python 3.7 or later installed.
- **Plex Media Server**: A running Plex server with a Music library.
- **OpenAI API Key**: For generating playlist titles and descriptions.
- **Plex API Token**: To authenticate and interact with your Plex server.
- **PlexAPI**: A Python library for accessing the Plex API.

## How to Run

1. **Install the required dependencies:**
   ```bash
   pip install plexapi
   pip install openai
   ```

2. **Configure your environment:**
   - Update the placeholders in the script (`<PLEX_SERVER_URL>`, `<PLEX_AUTH_TOKEN>`, `<OPENAI_API_KEY>`) with your own values:
     - `<PLEX_SERVER_URL>`: Your Plex server's base URL (e.g., `http://127.0.0.1:32400`).
     - `<PLEX_AUTH_TOKEN>`: Your Plex API token. Visit [this guide](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/) for details on obtaining it.
     - `<OPENAI_API_KEY>`: Your OpenAI API key from [OpenAI](https://platform.openai.com/).

3. **Run the script:**
   ```bash
   python meloday.py
   ```

4. **View your playlist on Plex!**

## Automating with Windows Task Scheduler

To run the script automatically at different times of the day, follow these steps:

1. **Open Task Scheduler**  
   Press `Win + R`, type `taskschd.msc`, and hit `Enter`.

2. **Create a New Task**  
   - Click **Action > Create Task**.
   - Under the **General** tab:
     - Name the task (e.g., `Meloday Morning Playlist`).
     - Check **Run with highest privileges**.

3. **Set Triggers for Different Dayparts**  
   - Go to the **Triggers** tab and click **New**.
   - Set the time you want the script to run.
   - Choose **Daily** and repeat this step for other dayparts.

4. **Set the Action to Run the Script**  
   - Go to the **Actions** tab and click **New**.
   - Choose **Start a Program**.
   - In the **Program/script** field, enter the path to Python:
     ```
     C:\Path\To\Python\python.exe
     ```
   - In the **Add arguments** field, enter:
     ```
     "C:\Path\To\meloday.py"
     ```
   - Replace `"C:\Path\To\meloday.py"` with the full path of your script.

5. **Finalize and Enable the Task**  
   - Click **OK** and enter your Windows password if prompted.
   - Right-click the task and choose **Run** to test it.

Your playlists will now update automatically at the configured times.

## Transparency

This project was created with the collaboration of AI (OpenAI's GPT) and human efforts to ensure accuracy and usability. Use at your own discretion.