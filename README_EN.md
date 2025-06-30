# Video Merger

A tool for automatically merging videos recorded by Xiaomi cameras.

[English](README_EN.md) | [中文说明](README.md)

## Features

- Automatically monitors camera recordings, scanning every minute
- Automatically merges videos when all four cameras (Cashier, Ironing Machine, Corner, Entrance) have videos from the same date
- Merges hourly videos into daily videos
- Automatically retries failed merge operations
- Supports timeout handling and automatic retry
- Customizable settings via configuration file
- Automatic management of original video files and retention policies

## Recent Updates

- **Video Merger Update**: Successfully merged videos from four cameras (Cashier, Ironing Machine, Corner, Entrance) for June 29, 2025.
- **Monitoring Mode Update**: Changed to continuous monitoring mode, scanning every minute and automatically merging when all cameras have videos from a new date.
- **Timeout Enhancement**: Added a 10-minute timeout auto-retry mechanism to prevent long-term blockage. When command execution exceeds 10 minutes, the program automatically interrupts the current execution and retries the command with the remaining timeout.
- **Auto-cleanup Feature**: Automatically deletes processed original and merged videos according to configuration, saving storage space.

## Installation

### Prerequisites

- Python 3.6+
- FFmpeg (must be installed and added to system PATH)

### Setup Steps

1. Clone or download this repository
   ```bash
   git clone https://github.com/your-username/video-merger.git
   cd video-merger
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Modify the `video_merger.ini` configuration file to suit your environment

## Configuration

Configuration file: `video_merger.ini`

Main configuration items:
- `video_root`: Root directory for videos
- `merged_dir`: Directory for storing merged videos
- `max_timeout`: Maximum timeout in seconds, default is 1200 seconds (20 minutes)
  - Note: A 10-minute (600 seconds) auto-retry mechanism is applied during execution
- `max_retries`: Maximum number of retries for failed merges, default is 3
- `retry_delay`: Retry interval in seconds, default is 5 seconds
- `scan_interval`: Scan interval in seconds, default is 60 seconds
- `delete_original_after_days`: Number of days to keep original videos after processing, default is 1 day
- `delete_merged_after_days`: Number of days to keep merged videos, default is 1 day
- `use_hw_accel`: Whether to use hardware acceleration, enabled by default

### Configuration Example

```ini
[Settings]
video_root = /path/to/videos
merged_dir = merged_videos
max_timeout = 1200
max_retries = 3
retry_delay = 5
scan_interval = 60
delete_original_after_days = 1
delete_merged_after_days = 1
use_hw_accel = True
```

## Usage

### Windows

Double-click the `daily_merge.bat` batch file to start the video monitoring and automatic merging service.

### Linux/MacOS

```bash
python video_merger.py
```

### Stopping the Service

Use `Ctrl+C` to stop the running service.

## How It Works

1. After startup, the program scans each camera's video folders every minute
2. When all four cameras (Cashier, Ironing Machine, Corner, Entrance) have videos from the same new date, it automatically begins merging
3. After merging is complete, it continues monitoring for new dates
4. If an error occurs, it resets the state and retries after the configured time
5. Based on the configured retention period, it automatically cleans up processed video files

## Project Structure

```
video-merger/
├── video_merger.py     # Main program file
├── video_merger.ini    # Configuration file
├── daily_merge.bat     # Windows startup script
├── requirements.txt    # Python dependencies
├── processed.json      # Processing records file
└── videos/             # Videos directory
    ├── 收银台/         # Cashier camera videos
    ├── 熨烫机/         # Ironing Machine camera videos
    ├── 转角/           # Corner camera videos
    ├── 门口/           # Entrance camera videos
    └── merged_videos/  # Directory for merged videos
```

## Frequently Asked Questions

1. **Issue**: FFmpeg not found
   **Solution**: Ensure FFmpeg is installed and added to the system PATH

2. **Issue**: Videos not being merged
   **Solution**: Check if all four cameras have video files from the same date

3. **Issue**: Program using too many system resources
   **Solution**: Adjust the `max_workers` parameter in the configuration file to reduce parallel processing

## Contribution Guidelines

Contributions and suggestions are welcome! Please follow these steps:

1. Fork this project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## System Requirements

- Python 3.6+
- FFmpeg (must be installed and added to system PATH)
- Sufficient storage space for video processing

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

If you have any questions or suggestions, please contact:

- GitHub Issue: [Create Issue](https://github.com/your-username/video-merger/issues)
- Email: your-email@example.com

## Acknowledgements

- Thanks to all contributors and users
- Thanks to FFmpeg for providing powerful video processing capabilities 