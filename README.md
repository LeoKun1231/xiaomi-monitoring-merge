# 视频合并工具 (Video Merger)

这个工具用于自动合并小米摄像头录制的视频文件。

[English README](README_EN.md) | 中文说明

## 功能特性

- 自动监控摄像头录像，每分钟扫描一次
- 当四个摄像头(收银台、熨烫机、转角、门口)都出现相同的新日期时，自动合并视频
- 按天合并小时视频
- 自动重试失败的合并操作
- 支持超时处理和自动重试
- 配置文件支持自定义设置
- 自动处理原始视频文件的保留和删除

## 最近更新

- **视频合并更新**：成功合并了2025年6月29日的四个摄像头(收银台、熨烫机、转角、门口)的视频。
- **监控模式更新**：改为持续监控模式，每分钟扫描一次，当所有摄像头都有新日期时自动合并。
- **超时处理增强**：增加了10分钟超时自动重试机制，避免长时间卡住的问题。当命令执行超过10分钟时，
  程序会自动中断当前执行，然后使用剩余的超时时间重新尝试该命令。
- **自动清理功能**：根据配置可自动删除已处理的原始视频和合并视频，节省存储空间。

## 安装说明

### 前置需求

- Python 3.6+
- FFmpeg (需要安装并添加到系统PATH)

### 安装步骤

1. 克隆或下载本仓库到本地
   ```bash
   git clone https://github.com/your-username/video-merger.git
   cd video-merger
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 修改配置文件 `video_merger.ini` 以适应您的环境

## 配置说明

配置文件: `video_merger.ini`

主要配置项:
- `video_root`: 视频根目录
- `merged_dir`: 合并后视频存放目录
- `max_timeout`: 最大超时时间(秒)，默认1200秒(20分钟)
  - 注：实际执行时会应用10分钟(600秒)的自动重试机制
- `max_retries`: 合并失败最大重试次数，默认3次
- `retry_delay`: 重试间隔(秒)，默认5秒
- `scan_interval`: 扫描间隔(秒)，默认60秒
- `delete_original_after_days`: 处理后原始视频保留天数，默认1天
- `delete_merged_after_days`: 合并视频保留天数，默认1天
- `use_hw_accel`: 是否使用硬件加速，默认启用

### 配置样例

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

## 使用方法

### Windows

双击运行 `daily_merge.bat` 批处理文件即可启动视频监控与自动合并服务。

### Linux/MacOS

```bash
python video_merger.py
```

### 停止服务

使用 `Ctrl+C` 来停止运行中的服务。

## 工作原理

1. 程序启动后会每分钟扫描一次各个摄像头的视频文件夹
2. 当检测到所有四个摄像头(收银台、熨烫机、转角、门口)都有相同的新日期视频时，自动开始合并处理
3. 合并完成后，继续监控等待新的日期出现
4. 如果发生错误，会重置状态并在设定的时间后重试
5. 根据配置的保留时间，自动清理已处理的视频文件

## 项目结构

```
video-merger/
├── video_merger.py     # 主程序文件
├── video_merger.ini    # 配置文件
├── daily_merge.bat     # Windows启动脚本
├── requirements.txt    # Python依赖
├── processed.json      # 处理记录文件
└── videos/             # 视频目录
    ├── 收银台/         # 收银台摄像头视频
    ├── 熨烫机/         # 熨烫机摄像头视频
    ├── 转角/           # 转角摄像头视频
    ├── 门口/           # 门口摄像头视频
    └── merged_videos/  # 合并后的视频存放目录
```

## 常见问题

1. **问题**: FFmpeg未找到
   **解决**: 请确保FFmpeg已安装并添加到系统PATH

2. **问题**: 视频未被合并
   **解决**: 检查是否所有四个摄像头都有相同日期的视频文件

3. **问题**: 程序占用过多系统资源
   **解决**: 调整配置文件中的`max_workers`参数减少并行处理数

## 贡献指南

欢迎贡献代码或提出建议！请按以下步骤操作：

1. Fork本项目
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开一个Pull Request

## 系统要求

- Python 3.6+
- FFmpeg (需要安装并添加到系统PATH)
- 足够的存储空间用于视频处理

## 许可证

该项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。

## 联系方式

如有任何问题或建议，请通过以下方式联系：

- GitHub Issue: [创建Issue](https://github.com/your-username/video-merger/issues)
- 电子邮件: your-email@example.com

## 致谢

- 感谢所有贡献者和使用者
- 感谢FFmpeg提供强大的视频处理能力
