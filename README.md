# 小米摄像头视频合并工具

一个用于自动合并小米摄像头录制的小时视频为天视频的Python工具。支持多摄像头并行处理、自动清理、看门狗保护等功能。

## 功能特性

### 核心功能
- **自动视频合并**: 将小米摄像头按小时录制的视频自动合并为天视频
- **多摄像头支持**: 支持多个摄像头位置（收银台、熨烫机、转角、门口）
- **智能文件管理**: 自动检测和处理.mp4和.mp4.old文件
- **进度跟踪**: 实时显示处理进度和状态信息

### 高级功能
- **看门狗保护**: 防止程序卡死，自动重启长时间运行的任务
- **自动清理**: 支持清理原始视频文件和已合并视频文件
- **文件验证**: 支持深度检查视频文件的可播放性
- **错误恢复**: 自动重试失败的合并操作
- **配置管理**: 支持INI配置文件，可自定义各种参数

## 系统要求

- Python 3.6+
- FFmpeg (必须安装并添加到系统PATH)
- Windows/Linux/macOS

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

### 1. 基本使用

```bash
# 单次运行模式
python video_merger.py --single-run

# 持续运行模式（默认）
python video_merger.py

# 使用自定义配置文件
python video_merger.py --config my_config.ini
```

### 2. 高级选项

```bash
# 忽略已处理记录，强制重新处理
python video_merger.py --ignore-processed

# 深度检查模式（验证视频可播放性）
python video_merger.py --deep-check

# 仅验证已处理记录
python video_merger.py --verify-only

# 清理无效的处理记录
python video_merger.py --clean-records

# 仅清理原始视频文件
python video_merger.py --cleanup-original

# 仅清理已合并的视频文件
python video_merger.py --cleanup-merged
```

## 配置说明

程序会自动创建 `video_merger.ini` 配置文件，您可以根据需要修改以下参数：

### 基本配置
```ini
[Settings]
# 视频根目录路径
video_root = C:\Users\Public\Videos

# 合并视频输出目录名
merged_dir = merged_videos

# 合并超时时间(秒)
max_timeout = 1800

# 合并失败最大重试次数
max_retries = 3

# 重试间隔(秒)
retry_delay = 5

# 扫描间隔(秒)
scan_interval = 600

# 有效文件最小大小(KB)
min_valid_size = 1024

# 并行处理摄像头数量
max_workers = 1
```

### 高级配置
```ini
[Settings]
# 是否保留小时视频(不删除)
save_hourly = False

# 是否使用硬件加速
use_hw_accel = True

# 是否清理临时文件
cleanup_temp_files = True

# 是否验证合并后的文件
verify_merged_files = True

# 是否进行深度检查(验证文件可播放性)
deep_check = False

# 合并完成后多少天删除原始视频
delete_original_after_days = 1

# 合并完成后多少天删除已合并的视频文件
delete_merged_after_days = 1
```

## 目录结构

程序期望的目录结构：
```
video_root/
├── 收银台/
│   └── xiaomi_camera_videos/
│       └── 607ea446e5b2/
│           ├── 2025062923/
│           ├── 2025063000/
│           └── ...
├── 熨烫机/
│   └── xiaomi_camera_videos/
│       └── 607ea44f1e3e/
│           ├── 2025062923/
│           └── ...
├── 转角/
│   └── xiaomi_camera_videos/
│       └── 607ea4468dc7/
│           └── ...
├── 门口/
│   └── xiaomi_camera_videos/
│       └── 607ea44713e6/
│           └── ...
└── merged_videos/
    ├── 20250629/
    │   ├── 20250629_收银台_23.mp4
    │   └── 20250629_熨烫机_23.mp4
    ├── 20250630/
    │   ├── 20250630_收银台.mp4
    │   ├── 20250630_熨烫机.mp4
    │   ├── 20250630_转角.mp4
    │   └── 20250630_门口.mp4
    └── ...
```

## 工作流程

1. **扫描摄像头**: 自动扫描指定目录下的所有摄像头
2. **检测日期**: 检查每个摄像头是否有需要处理的历史视频
3. **合并小时视频**: 将每个小时文件夹中的视频合并为小时视频
4. **合并天视频**: 将24个小时视频合并为天视频
5. **清理文件**: 根据配置自动清理原始文件和已合并文件
6. **记录管理**: 维护处理记录，避免重复处理

## 文件命名规则

### 输入文件
- 小时文件夹: `YYYYMMDDHH` (如: `2025063000`)
- 视频文件: `*.mp4` 和 `*.mp4.old`

### 输出文件
- 小时视频: `YYYYMMDD_位置_HH.mp4` (如: `20250630_收银台_00.mp4`)
- 天视频: `YYYYMMDD_位置.mp4` (如: `20250630_收银台.mp4`)

## 日志和监控

程序会生成详细的日志文件 `video_merger.log`，包含：
- 处理进度和状态
- 错误信息和异常处理
- 文件操作记录
- 性能统计信息

### 日志级别
- INFO: 正常操作信息
- WARNING: 警告信息
- ERROR: 错误信息
- CRITICAL: 严重错误

## 故障排除

### 常见问题

1. **FFmpeg未找到**
   ```
   错误: ffmpeg未安装或不可用
   解决: 安装FFmpeg并确保在PATH中可用
   ```

2. **视频合并失败**
   ```
   错误: 命令执行失败
   解决: 检查视频文件完整性，尝试使用--deep-check参数
   ```

3. **程序卡死**
   ```
   错误: 看门狗超时
   解决: 检查磁盘空间，调整max_timeout参数
   ```

4. **文件权限问题**
   ```
   错误: 无法访问文件
   解决: 检查文件和目录权限
   ```

### 调试模式

使用以下参数进行调试：
```bash
# 启用深度检查
python video_merger.py --deep-check

# 仅验证记录
python video_merger.py --verify-only

# 忽略已处理记录
python video_merger.py --ignore-processed
```

## 性能优化

### 硬件加速
如果您的系统支持NVIDIA GPU，可以启用硬件加速：
```ini
use_hw_accel = True
```

### 并行处理
调整并行处理数量（注意：当前版本限制为1）：
```ini
max_workers = 1
```

### 超时设置
根据系统性能调整超时时间：
```ini
max_timeout = 1800  # 30分钟
```

## 安全注意事项

1. **备份重要数据**: 在运行程序前备份重要视频文件
2. **测试环境**: 建议先在测试环境中验证配置
3. **磁盘空间**: 确保有足够的磁盘空间存储合并后的视频
4. **权限管理**: 确保程序有足够的文件读写权限

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。

## 更新日志

### v1.0.0
- 初始版本发布
- 支持多摄像头视频合并
- 自动清理和文件管理
- 看门狗保护机制
- 配置文件支持
