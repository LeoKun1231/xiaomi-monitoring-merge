# Xiaomi Camera Video Merger Tool

A Python tool for automatically merging hourly videos recorded by Xiaomi cameras into daily videos. Supports multi-camera parallel processing, automatic cleanup, watchdog protection, and more.

## Features

### Core Features
- **Automatic Video Merging**: Automatically merges hourly videos recorded by Xiaomi cameras into daily videos
- **Multi-Camera Support**: Supports multiple camera locations (Cashier, Ironing Machine, Corner, Entrance)
- **Smart File Management**: Automatically detects and processes .mp4 and .mp4.old files
- **Progress Tracking**: Real-time display of processing progress and status information

### Advanced Features
- **Watchdog Protection**: Prevents program deadlock, automatically restarts long-running tasks
- **Automatic Cleanup**: Supports cleaning up original video files and merged video files
- **File Verification**: Supports deep checking of video file playability
- **Error Recovery**: Automatically retries failed merge operations
- **Configuration Management**: Supports INI configuration files with customizable parameters

## System Requirements

- Python 3.6+
- FFmpeg (must be installed and added to system PATH)
- Windows/Linux/macOS

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Basic Usage

```bash
# Single run mode
python video_merger.py --single-run

# Continuous run mode (default)
python video_merger.py

# Use custom configuration file
python video_merger.py --config my_config.ini
```

### 2. Advanced Options

```bash
# Ignore processed records, force reprocessing
python video_merger.py --ignore-processed

# Deep check mode (verify video playability)
python video_merger.py --deep-check

# Only verify processed records
python video_merger.py --verify-only

# Clean invalid processed records
python video_merger.py --clean-records

# Only clean original video files
python video_merger.py --cleanup-original

# Only clean merged video files
python video_merger.py --cleanup-merged
```

## Configuration

The program automatically creates a `video_merger.ini` configuration file. You can modify the following parameters as needed:

### Basic Configuration
```ini
[Settings]
# Video root directory path
video_root = C:\Users\Public\Videos

# Merged video output directory name
merged_dir = merged_videos

# Merge timeout (seconds)
max_timeout = 1800

# Maximum retry attempts for failed merges
max_retries = 3

# Retry interval (seconds)
retry_delay = 5

# Scan interval (seconds)
scan_interval = 600

# Minimum valid file size (KB)
min_valid_size = 1024

# Number of parallel camera processing
max_workers = 1
```

### Advanced Configuration
```ini
[Settings]
# Whether to keep hourly videos (not delete)
save_hourly = False

# Whether to use hardware acceleration
use_hw_accel = True

# Whether to clean up temporary files
cleanup_temp_files = True

# Whether to verify merged files
verify_merged_files = True

# Whether to perform deep check (verify file playability)
deep_check = False

# Days to keep original videos after merging
delete_original_after_days = 1

# Days to keep merged videos after merging
delete_merged_after_days = 1
```

## Directory Structure

The expected directory structure for the program:
```
video_root/
├── Cashier/
│   └── xiaomi_camera_videos/
│       └── 607ea446e5b2/
│           ├── 2025062923/
│           ├── 2025063000/
│           └── ...
├── IroningMachine/
│   └── xiaomi_camera_videos/
│       └── 607ea44f1e3e/
│           ├── 2025062923/
│           └── ...
├── Corner/
│   └── xiaomi_camera_videos/
│       └── 607ea4468dc7/
│           └── ...
├── Entrance/
│   └── xiaomi_camera_videos/
│       └── 607ea44713e6/
│           └── ...
└── merged_videos/
    ├── 20250629/
    │   ├── 20250629_Cashier_23.mp4
    │   └── 20250629_IroningMachine_23.mp4
    ├── 20250630/
    │   ├── 20250630_Cashier.mp4
    │   ├── 20250630_IroningMachine.mp4
    │   ├── 20250630_Corner.mp4
    │   └── 20250630_Entrance.mp4
    └── ...
```

## Workflow

1. **Scan Cameras**: Automatically scans all cameras in the specified directory
2. **Detect Dates**: Checks if each camera has historical videos that need processing
3. **Merge Hourly Videos**: Merges videos in each hourly folder into hourly videos
4. **Merge Daily Videos**: Merges 24 hourly videos into daily videos
5. **Clean Files**: Automatically cleans up original files and merged files according to configuration
6. **Record Management**: Maintains processing records to avoid duplicate processing

## File Naming Rules

### Input Files
- Hourly folders: `YYYYMMDDHH` (e.g., `2025063000`)
- Video files: `*.mp4` and `*.mp4.old`

### Output Files
- Hourly videos: `YYYYMMDD_Location_HH.mp4` (e.g., `20250630_Cashier_00.mp4`)
- Daily videos: `YYYYMMDD_Location.mp4` (e.g., `20250630_Cashier.mp4`)

## Logging and Monitoring

The program generates detailed log files `video_merger.log` containing:
- Processing progress and status
- Error messages and exception handling
- File operation records
- Performance statistics

### Log Levels
- INFO: Normal operation information
- WARNING: Warning messages
- ERROR: Error messages
- CRITICAL: Critical errors

## Troubleshooting

### Common Issues

1. **FFmpeg Not Found**
   ```
   Error: ffmpeg not installed or not available
   Solution: Install FFmpeg and ensure it's available in PATH
   ```

2. **Video Merge Failed**
   ```
   Error: Command execution failed
   Solution: Check video file integrity, try using --deep-check parameter
   ```

3. **Program Deadlock**
   ```
   Error: Watchdog timeout
   Solution: Check disk space, adjust max_timeout parameter
   ```

4. **File Permission Issues**
   ```
   Error: Cannot access file
   Solution: Check file and directory permissions
   ```

### Debug Mode

Use the following parameters for debugging:
```bash
# Enable deep check
python video_merger.py --deep-check

# Only verify records
python video_merger.py --verify-only

# Ignore processed records
python video_merger.py --ignore-processed
```

## Performance Optimization

### Hardware Acceleration
If your system supports NVIDIA GPU, you can enable hardware acceleration:
```ini
use_hw_accel = True
```

### Parallel Processing
Adjust the number of parallel processing (Note: current version is limited to 1):
```ini
max_workers = 1
```

### Timeout Settings
Adjust timeout based on system performance:
```ini
max_timeout = 1800  # 30 minutes
```

## Security Considerations

1. **Backup Important Data**: Backup important video files before running the program
2. **Test Environment**: It's recommended to verify configuration in a test environment first
3. **Disk Space**: Ensure sufficient disk space for storing merged videos
4. **Permission Management**: Ensure the program has sufficient file read/write permissions

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Welcome to submit Issues and Pull Requests to improve this project.

## Changelog

### v1.0.0
- Initial version release
- Support for multi-camera video merging
- Automatic cleanup and file management
- Watchdog protection mechanism
- Configuration file support 