# Real-Time English to Italian Translation UI

A beautiful, Apple Music-style web interface for real-time speech translation from English to Italian using Whisper ML.

## Features

- 🎙️ Real-time speech recognition
- 🔄 Instant English to Italian translation
- 💫 Beautiful Apple Music-inspired animations
- 🎨 Dynamic background gradients
- 📱 Responsive design for all devices
- ⚙️ Adjustable font sizes
- 🎯 Multiple microphone support

## Requirements

- Python 3.8+
- FFmpeg
- MLX (for Apple Silicon) or CUDA (for NVIDIA GPUs)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/whisper-streaming-translation
cd whisper-streaming-translation
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install FFmpeg:
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt install ffmpeg`
- Windows: Download from [FFmpeg website](https://ffmpeg.org/download.html)

## Usage

1. Start the translation server:
```bash
python simple.py
```

2. Open your web browser and navigate to:
```
http://localhost:7878
```

3. Allow microphone access when prompted

4. Start speaking in English - you'll see the Italian translations appear in real-time with beautiful animations!

## Configuration

- Click the gear icon (⚙️) to adjust font sizes for both English and Italian text
- Use the microphone selector to choose between different audio input devices
- The UI automatically adjusts for different screen sizes

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](LICENSE)

