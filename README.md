# MemoDari

A feature-rich application for learning through flashcards, powered by the Free Spaced Repetition System (FSRS) algorithm.

## Features

- **Smart Flashcard Learning**: Implements FSRS algorithm for optimized learning schedules
- **Rich Analytics Dashboard**: Track your learning progress with detailed visualizations
- **Category & Tag Management**: Organize your cards for better recall
- **Customizable Interface**: Dark theme with persistent window positioning
- **Text-to-Speech**: Audio support for better learning retention
- **Difficulty Tracking**: Monitor stability and difficulty for each card

## Screenshots

*Insert screenshots here - recommended sections:*
1. Main flashcard interface
2. Analytics dashboard
3. Card management screen
4. Settings panel

## Installation

1. Clone this repository
2. Install requirements:
   ```
   pip install -r util/requirements.txt
   ```
3. Configure your database settings in `config.py`
4. Run the application:
   ```
   python memodari.py
   ```

## Usage

- **Add Flashcards**: Click the '+' button to create new cards
- **Review Cards**: The application will present cards due for review based on FSRS algorithm
- **Rate Difficulty**: After reviewing a card, rate how difficult it was to recall
- **Track Progress**: Use the analytics tab to monitor your learning journey
wh
## Technical Details

- Built with Python and tkinter for the UI
- SQL Server database backend
- Implements the FSRS algorithm for spaced repetition learning
- Modern UI with responsive design elements

## Future Enhancements

- Cloud synchronization
- Mobile companion app
- Import/export functionality
- User accounts for multi-user support

## License

[MIT License](LICENSE)

---

*Note: MemoDari is a mini-project created for educational purposes.*