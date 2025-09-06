# FactDari

A lightweight desktop widget application for displaying and managing facts, designed to help you learn and review information throughout your day. FactDari sits on your desktop and provides quick access to categorized facts with built-in analytics tracking.

## Features

- **Desktop Widget Interface**: Minimal, always-accessible widget that stays on your desktop
- **Category Management**: Organize facts into categories for better organization
- **Favorites System**: Mark important facts as favorites for quick access
- **Knowledge Tracking**: Mark facts as "Known" or "Not Known" to track your learning progress
- **Review Tracking**: Automatically tracks when and how often you review each fact
- **Text-to-Speech**: Listen to facts with built-in TTS support
- **Analytics Dashboard**: Web-based analytics to visualize your learning patterns
- **Navigation Controls**: Easy navigation through facts with previous/next buttons
- **Search & Filter**: Filter facts by category, favorites, or knowledge status
- **Dark Theme**: Eye-friendly dark interface with customizable transparency

## Key Functionality

### Main Application
- View random facts or navigate sequentially through your collection
- Add, edit, and delete facts directly from the widget
- Mark facts as favorites or known/unknown
- Category-based filtering
- Speech synthesis for audio learning
- Automatic review logging

### Analytics Dashboard
- Category distribution charts
- Daily review activity tracking
- Most and least reviewed facts
- Review patterns over time
- Favorite facts statistics
- Knowledge progress tracking
- Interactive charts with Chart.js

## Installation

1. Clone this repository
2. Install required Python packages:
   ```
   pip install -r util/requirements_factdari.txt
   ```
3. Set up the SQL Server database using the script in `database_setup/factdari_setup.sql`
4. Configure your database connection in `config.py`
5. Run the application:
   ```
   python factdari.py
   ```

## Usage

### Main Widget
- **Home Page**: Shows statistics and quick actions
- **View Facts**: Click "Show Random Fact" or use navigation arrows
- **Add Facts**: Click the "+" button to add new facts
- **Edit/Delete**: Use the edit and delete buttons when viewing a fact
- **Mark Favorite**: Toggle the star icon to mark/unmark favorites
- **Mark Known**: Use the checkmark to track your knowledge progress
- **Filter**: Use the category dropdown to filter facts
- **Listen**: Click the speaker icon for text-to-speech

### Analytics
- Run the analytics server:
  ```
  python analytics_factdari.py
  ```
- Open your browser to `http://localhost:5000`
- View comprehensive statistics about your fact review patterns

### Startup Configuration
For Windows users, use the VBS script to configure automatic startup:
```
util/RunFactDari.vbs
```

## Technical Details

- **Frontend**: Python tkinter for the desktop widget
- **Backend**: SQL Server database for fact storage
- **Analytics**: Flask web server with Chart.js visualizations
- **Speech**: pyttsx3 for text-to-speech functionality
- **Configuration**: Centralized config.py for all settings

## Database Schema

- **Facts**: Stores fact content, category, review count, and metadata
- **Categories**: Manages fact categories
- **ReviewLogs**: Tracks all fact review events
- **Preferences**: Stores user preferences and settings

## Configuration

Edit `config.py` to customize:
- Database connection settings
- Window dimensions and positioning
- Color schemes
- Font settings
- UI element sizes
- Inactivity timeout behavior

### Inactivity Timeout
- `FACTDARI_IDLE_TIMEOUT_SECONDS` (default: `300`): seconds of no input before the app considers you idle.
- `FACTDARI_IDLE_END_SESSION` (default: `true`): when idle, end the active session as timed out. If set to `false`, only the current fact view is finalized as timed out and the session remains open.

## Making This Repo Public

Before making the repository public:

- Hide local environment folders:
  - A `.gitignore` has been added to exclude `.venv/`, `__pycache__/`, editor folders, etc. If `.venv/` was already committed, untrack it with:
    - `git rm -r --cached .venv`
    - `git commit -m "chore: stop tracking .venv"`
- Database host defaults:
  - Default DB server changed to `localhost\SQLEXPRESS`. Set environment variables to point to your own SQL Server if different.
- Email privacy:
  - Your past commits may include your email in Git metadata. Consider enabling GitHub email privacy and using your noreply address for future commits.
- Assets and licenses:
  - Ensure all images in `Resources/` are yours or properly licensed.
- Debug mode:
  - `analytics_factdari.py` runs the Flask app in debug for local use. Do not expose this publicly.

## Requirements

- Python 3.7+
- SQL Server (or SQL Server Express)
- Windows OS (for desktop widget functionality)
- Required Python packages (see requirements_factdari.txt)

## License

[MIT License](LICENSE)

---

*FactDari - Your daily companion for fact-based learning*
