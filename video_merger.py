import os
import glob
import datetime
import subprocess
import time
import logging
import shutil
import re
import json
import concurrent.futures
from pathlib import Path
import argparse
import configparser
import threading
import signal
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('video_merger.log'),
        logging.StreamHandler()
    ]
)

# 添加看门狗定时器类
class WatchdogTimer:
    def __init__(self, timeout, handler=None):
        self.timeout = timeout
        self.handler = handler or self._default_handler
        self.timer = None
        self.is_running = False

    def _default_handler(self):
        logging.critical("看门狗超时! 脚本执行时间过长，可能已卡死，强制退出...")
        sys.exit(1)

    def start(self):
        self.reset()

    def stop(self):
        if self.timer:
            self.timer.cancel()
        self.is_running = False

    def reset(self):
        if self.timer:
            self.timer.cancel()
        self.is_running = True
        self.timer = threading.Timer(self.timeout, self.handler)
        self.timer.daemon = True  # 设置为守护线程，主线程退出时自动终止
        self.timer.start()

# 默认配置
DEFAULT_CONFIG = {
    "video_root": r"C:\Users\Public\Videos",
    "merged_dir": "merged_videos",
    "max_timeout": 1800,  # 合并超时时间(秒)，实际执行时会先用600秒，超时后再用剩余时间 
    "max_retries": 3,    # 合并失败最大重试次数
    "retry_delay": 5,    # 重试间隔(秒)
    "scan_interval": 600,  # 扫描间隔(秒)，每10分钟扫描一次
    "min_valid_size": 1024,   # 有效文件最小大小(KB)
    "max_workers": 1,    # 并行处理摄像头数量
    "save_hourly": False,  # 是否保留小时视频(不删除)
    "use_hw_accel": True,  # 是否使用硬件加速
    "cleanup_temp_files": True,  # 是否清理临时文件
    "verify_merged_files": True,  # 是否验证合并后的文件
    "deep_check": False,   # 是否进行深度检查(验证文件可播放性)
    "delete_original_after_days": 1,  # 合并完成后多少天删除原始视频
    "delete_merged_after_days": 1  # 合并完成后多少天删除已合并的视频文件
}

CONFIG_FILE = "video_merger.ini"
PROCESSED_FILE = "processed.json"

def load_config():
    """加载配置文件，如果不存在则创建默认配置"""
    config = DEFAULT_CONFIG.copy()
    
    if os.path.exists(CONFIG_FILE):
        try:
            parser = configparser.ConfigParser()
            parser.read(CONFIG_FILE)
            
            if 'Settings' in parser:
                settings = parser['Settings']
                config["video_root"] = settings.get('video_root', config["video_root"])
                config["merged_dir"] = settings.get('merged_dir', config["merged_dir"])
                config["max_timeout"] = settings.getint('max_timeout', config["max_timeout"])
                config["max_retries"] = settings.getint('max_retries', config["max_retries"])
                config["retry_delay"] = settings.getint('retry_delay', config["retry_delay"])
                config["scan_interval"] = settings.getint('scan_interval', config["scan_interval"])
                config["min_valid_size"] = settings.getint('min_valid_size', config["min_valid_size"])
                config["max_workers"] = settings.getint('max_workers', config["max_workers"])
                config["save_hourly"] = settings.getboolean('save_hourly', config["save_hourly"])
                config["use_hw_accel"] = settings.getboolean('use_hw_accel', config["use_hw_accel"])
                config["cleanup_temp_files"] = settings.getboolean('cleanup_temp_files', config["cleanup_temp_files"])
                config["verify_merged_files"] = settings.getboolean('verify_merged_files', config["verify_merged_files"])
                config["deep_check"] = settings.getboolean('deep_check', config["deep_check"])
                config["delete_original_after_days"] = settings.getint('delete_original_after_days', config["delete_original_after_days"])
                config["delete_merged_after_days"] = settings.getint('delete_merged_after_days', config["delete_merged_after_days"])
            
            logging.info(f"已加载配置文件: {CONFIG_FILE}")
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}，将使用默认配置")
    else:
        # 创建默认配置文件
        try:
            parser = configparser.ConfigParser()
            parser['Settings'] = {
                'video_root': config["video_root"],
                'merged_dir': config["merged_dir"],
                'max_timeout': str(config["max_timeout"]),
                'max_retries': str(config["max_retries"]),
                'retry_delay': str(config["retry_delay"]),
                'scan_interval': str(config["scan_interval"]),
                'min_valid_size': str(config["min_valid_size"]),
                'max_workers': str(config["max_workers"]),
                'save_hourly': str(config["save_hourly"]),
                'use_hw_accel': str(config["use_hw_accel"]),
                'cleanup_temp_files': str(config["cleanup_temp_files"]),
                'verify_merged_files': str(config["verify_merged_files"]),
                'deep_check': str(config["deep_check"]),
                'delete_original_after_days': str(config["delete_original_after_days"]),
                'delete_merged_after_days': str(config["delete_merged_after_days"])
            }
            
            with open(CONFIG_FILE, 'w') as f:
                parser.write(f)
                
            logging.info(f"已创建默认配置文件: {CONFIG_FILE}")
        except Exception as e:
            logging.error(f"创建默认配置文件失败: {e}")
    
    return config

def load_processed_files():
    """加载已处理文件记录"""
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, 'r') as f:
                data = json.load(f)
                # 确保没有重复记录
                if "hours" in data:
                    data["hours"] = list(set(data["hours"]))
                if "days" in data:
                    data["days"] = list(set(data["days"]))
                # 确保有合并时间记录
                if "merge_timestamps" not in data:
                    data["merge_timestamps"] = {}
                return data
        except Exception as e:
            logging.error(f"加载已处理文件记录失败: {e}")
    return {"hours": [], "days": [], "merge_timestamps": {}}

def save_processed_files(processed):
    """保存已处理文件记录"""
    try:
        # 确保没有重复记录
        if "hours" in processed:
            processed["hours"] = list(set(processed["hours"]))
        if "days" in processed:
            processed["days"] = list(set(processed["days"]))
        # 确保有合并时间记录
        if "merge_timestamps" not in processed:
            processed["merge_timestamps"] = {}
            
        with open(PROCESSED_FILE, 'w') as f:
            json.dump(processed, f)
        logging.info(f"已保存处理记录: {len(processed['hours'])} 小时视频, {len(processed['days'])} 天视频")
    except Exception as e:
        logging.error(f"保存已处理文件记录失败: {e}")

def run_with_timeout(cmd, timeout):
    """运行命令，设置超时
    
    实际执行时，命令首先会使用最多10分钟(600秒)运行，如果在这个时间内完成，则返回成功。
    如果在10分钟内未完成，且设置的超时时间大于10分钟，则会重新启动命令，使用剩余的超时时间。
    
    Args:
        cmd: 要执行的命令列表
        timeout: 总超时时间(秒)
    
    Returns:
        bool: 命令执行成功返回True，否则返回False
    """
    
    # 最大执行时间为10分钟 (600秒)
    max_execution_time = 600
    
    # 检查设置的超时时间是否超过最大执行时间
    effective_timeout = min(timeout, max_execution_time)
    
    try:
        logging.info(f"运行命令，设置初始超时时间: {effective_timeout} 秒")
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=effective_timeout)
        if process.returncode != 0:
            logging.error(f"命令执行失败: {process.stderr.decode('utf-8', errors='ignore')}")
            return False
        return True
    except subprocess.TimeoutExpired:
        logging.warning(f"命令执行到达 {effective_timeout} 秒超时限制，但未完成")
        
        # 如果初始超时时间小于实际配置的超时时间，进行重试
        if effective_timeout < timeout:
            remaining_timeout = timeout - effective_timeout
            logging.info(f"尝试重新启动命令，设置剩余超时时间: {remaining_timeout} 秒")
            
            try:
                # 终止之前的进程并重新启动一个新的进程
                logging.info(f"重新启动命令: {' '.join(cmd)}")
                process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=remaining_timeout)
                if process.returncode != 0:
                    logging.error(f"重试后命令执行失败: {process.stderr.decode('utf-8', errors='ignore')}")
                    return False
                logging.info("重试后命令执行成功")
                return True
            except subprocess.TimeoutExpired:
                logging.error(f"重试后命令仍然超时: {' '.join(cmd)}")
                return False
            except Exception as e:
                logging.error(f"重试命令执行异常: {e}")
                return False
        else:
            logging.error(f"命令执行超时且无法重试 (配置的超时时间={timeout}秒，已使用={effective_timeout}秒): {' '.join(cmd)}")
            return False
    except Exception as e:
        logging.error(f"命令执行异常: {e}")
        return False

def get_date_from_folder(folder_name):
    """从文件夹名称获取日期时间信息"""
    match = re.match(r'(\d{4})(\d{2})(\d{2})(\d{2})?', folder_name)
    if match:
        groups = match.groups()
        if len(groups) == 4 and groups[3]:  # 有小时
            return datetime.datetime(int(groups[0]), int(groups[1]), int(groups[2]), int(groups[3]))
        else:  # 只有日期
            return datetime.datetime(int(groups[0]), int(groups[1]), int(groups[2]))
    return None

def check_file_valid(file_path, min_size_kb, deep_check=False):
    """检查文件是否有效（存在且大于最小大小，可选深度检查）"""
    if not os.path.exists(file_path):
        return False
        
    file_size_kb = os.path.getsize(file_path) / 1024
    if file_size_kb < min_size_kb:
        logging.warning(f"文件大小异常 ({file_size_kb:.2f}KB < {min_size_kb}KB): {file_path}")
        return False
    
    # 如果需要深度检查，验证文件是否可以播放
    if deep_check and not verify_video_file(file_path):
        logging.warning(f"文件无法正常播放: {file_path}")
        return False
        
    return True

def verify_video_file(file_path):
    """验证视频文件是否完整可播放"""
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', file_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        return result.returncode == 0
    except Exception:
        return False

def direct_copy_first_hour(input_files, output_file):
    """直接复制第一个小时视频作为天视频（应急方案）"""
    if not input_files:
        return False
    try:
        logging.info(f"使用应急方案：直接复制第一个小时视频作为天视频: {input_files[0]} -> {output_file}")
        shutil.copy2(input_files[0], output_file)
        return check_file_valid(output_file, 1024)  # 检查复制后的文件是否有效
    except Exception as e:
        logging.error(f"复制文件失败: {e}")
        return False

def merge_videos(input_files, output_file, config, is_daily_merge=False):
    """合并视频文件
    
    Args:
        input_files: 输入文件列表
        output_file: 输出文件路径
        config: 配置信息
        is_daily_merge: 是否是合并天视频(True)还是合并小时视频(False)
    """
    if not input_files:
        logging.warning(f"没有找到需要合并的视频文件: {output_file}")
        return False
    
    # 创建输出目录
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 创建合并列表文件
    list_file = f"{output_file}.txt"
    try:
        with open(list_file, 'w', encoding='utf-8') as f:
            for video_file in input_files:
                f.write(f"file '{video_file}'\n")
    except Exception as e:
        logging.error(f"创建合并列表文件失败: {e}")
        return False
    
    for attempt in range(config["max_retries"]):
        try:
            # 天视频合并使用更简单直接的方法
            if is_daily_merge:
                # 对于天视频，如果只有一个小时，直接复制替代合并
                if len(input_files) == 1:
                    logging.info(f"只有一个小时视频，直接复制: {input_files[0]} -> {output_file}")
                    shutil.copy2(input_files[0], output_file)
                    if check_file_valid(output_file, config["min_valid_size"]):
                        logging.info(f"天视频创建成功(直接复制): {output_file}")
                        if os.path.exists(list_file):
                            os.unlink(list_file)
                        return True
                    else:
                        logging.error(f"天视频创建失败(直接复制): {output_file}")
                        continue

                # 尝试方法1：直接使用简化的concat方法
                logging.info(f"合并天视频 (第{attempt + 1}次): {output_file} (共{len(input_files)}个文件)")
                cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', list_file,
                    '-c:v', 'copy',      # 视频直接拷贝
                    '-c:a', 'copy',      # 音频直接拷贝
                    '-y',
                    output_file
                ]
                
                # 天视频合并超时时间是配置的2倍
                daily_timeout = config["max_timeout"] * 2
                logging.info(f"天视频合并设置超时时间: {daily_timeout}秒 (普通超时的2倍)")
                success = run_with_timeout(cmd, daily_timeout)
                
                if success and check_file_valid(output_file, config["min_valid_size"]):
                    logging.info(f"天视频合并成功: {output_file}")
                    if os.path.exists(list_file):
                        os.unlink(list_file)
                    return True
                else:
                    logging.error(f"天视频合并失败(方法1): {output_file}")
                    
                    # 如果失败，尝试方法2：使用aac音频编码
                    if attempt < 1:  # 只在第一次失败后尝试
                        logging.info(f"尝试方法2(aac音频): 合并天视频 (第{attempt + 1}次): {output_file}")
                        cmd = [
                            'ffmpeg',
                            '-f', 'concat',
                            '-safe', '0',
                            '-i', list_file,
                            '-c:v', 'copy',      # 视频直接拷贝
                            '-c:a', 'aac',       # 音频转换为aac格式
                            '-strict', 'experimental',  # 允许实验性编码器
                            '-y',
                            output_file
                        ]
                        
                        success = run_with_timeout(cmd, daily_timeout)
                        
                        if success and check_file_valid(output_file, config["min_valid_size"]):
                            logging.info(f"天视频合并成功(方法2): {output_file}")
                            if os.path.exists(list_file):
                                os.unlink(list_file)
                            return True
                        else:
                            logging.error(f"天视频合并失败(方法2): {output_file}")
                            
                            # 方法3：尝试应急方案，直接复制第一个小时文件作为天视频
                            if direct_copy_first_hour(input_files, output_file):
                                logging.info(f"天视频创建成功(应急方案): {output_file}")
                                if os.path.exists(list_file):
                                    os.unlink(list_file)
                                return True
                            else:
                                logging.error(f"天视频创建失败(应急方案): {output_file}")
            else:
                # 小时视频合并，使用常规方法
                cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', list_file,
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-y',
                    output_file
                ]
                
                logging.info(f"尝试合并小时视频 (第{attempt + 1}次): {output_file} (共{len(input_files)}个文件, 超时时间: {config['max_timeout']}秒)")
                success = run_with_timeout(cmd, config["max_timeout"])
                
                if success:
                    # 检查合并后的文件是否有效
                    if check_file_valid(output_file, config["min_valid_size"]):
                        logging.info(f"小时视频合并成功: {output_file}")
                        # 清理列表文件
                        if os.path.exists(list_file):
                            os.unlink(list_file)
                        return True
                    else:
                        logging.error(f"合并后的视频文件无效或过小: {output_file}")
            
            # 如果失败，并且还有重试机会
            if attempt < config["max_retries"] - 1:
                if os.path.exists(output_file):
                    try:
                        os.unlink(output_file)  # 删除无效文件
                    except:
                        logging.error(f"删除无效文件失败: {output_file}")
                logging.info(f"合并失败，等待{config['retry_delay']}秒后进行第{attempt + 2}次重试...")
                time.sleep(config["retry_delay"])
                    
        except Exception as e:
            logging.error(f"合并视频异常 (第{attempt + 1}次): {e}")
            if attempt < config["max_retries"] - 1:
                logging.info(f"等待{config['retry_delay']}秒后重试...")
                time.sleep(config["retry_delay"])
    
    # 所有重试都失败了
    logging.error(f"视频合并最终失败 (已重试{config['max_retries']}次): {output_file}")
    if os.path.exists(list_file):
        os.unlink(list_file)
    
    # 最后的应急方案：直接使用第一个文件
    if is_daily_merge and len(input_files) > 0:
        if direct_copy_first_hour(input_files, output_file):
            logging.info(f"天视频创建成功(最终应急方案): {output_file}")
            return True
    
    return False

def is_nvidia_available():
    """检测NVIDIA GPU是否可用于FFmpeg加速"""
    try:
        # 尝试运行ffmpeg -encoders检查是否支持NVIDIA编码器
        process = subprocess.run(['ffmpeg', '-encoders'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = process.stdout.decode('utf-8', errors='ignore')
        return 'h264_nvenc' in output
    except Exception:
        return False

def scan_camera_folders(config):
    """扫描摄像头文件夹"""
    camera_folders = []
    video_root = config["video_root"]
    
    try:
        # 确保合并输出目录存在
        merged_dir = os.path.join(video_root, config["merged_dir"])
        os.makedirs(merged_dir, exist_ok=True)
        logging.info(f"确保合并输出目录存在: {merged_dir}")
    
        # 扫描各个位置
        for location in os.listdir(video_root):
            location_path = os.path.join(video_root, location)
            if os.path.isdir(location_path) and location != config["merged_dir"]:
                # 查找xiaomi_camera_videos文件夹
                xiaomi_path = os.path.join(location_path, "xiaomi_camera_videos")
                if os.path.isdir(xiaomi_path):
                    # 查找摄像头ID文件夹
                    for camera_id in os.listdir(xiaomi_path):
                        camera_path = os.path.join(xiaomi_path, camera_id)
                        if os.path.isdir(camera_path):
                            camera_folders.append({
                                "location": location,
                                "camera_id": camera_id,
                                "path": camera_path
                            })
                    
        logging.info(f"找到 {len(camera_folders)} 个摄像头目录")
        return camera_folders
    except Exception as e:
        logging.error(f"扫描摄像头文件夹失败: {e}")
        return []

def process_camera(camera_info, config, processed):
    """处理单个摄像头的视频"""
    location = camera_info["location"]
    camera_id = camera_info["camera_id"]
    camera_path = camera_info["path"]
    
    logging.info(f"开始处理摄像头: {location}/{camera_id}")
    
    # 获取当前日期
    current_date = datetime.datetime.now()
    current_day = current_date.strftime("%Y%m%d")
    
    try:
        # 使用Path对象和通配符更高效地查找日期文件夹
        date_pattern = re.compile(r'\d{10}')
        date_folders = [
            folder.name for folder in Path(camera_path).iterdir() 
            if folder.is_dir() and date_pattern.match(folder.name)
        ]
        
        # 按日期排序
        date_folders.sort()
        
        # 先按天分组小时文件夹
        day_to_hours = {}
        for folder in date_folders:
            folder_date = get_date_from_folder(folder)
            if not folder_date:
                continue
            folder_day = folder_date.strftime("%Y%m%d")
            # 跳过当天的视频
            if folder_day == current_day:
                continue
            day_to_hours.setdefault(folder_day, []).append(folder)
        
        # 如果没有需要处理的日期，直接返回
        if not day_to_hours:
            logging.info(f"摄像头 {location}/{camera_id} 没有需要处理的历史视频")
            return True
            
        # 统计总工作量
        total_folders = sum(len(hours) for hours in day_to_hours.values())
        processed_count = 0
        
        # 记录处理开始时间
        start_time = time.time()
        days_processed = 0
        
        for day, hour_folders in sorted(day_to_hours.items()):
            days_processed += 1
            logging.info(f"处理日期: {day} ({len(hour_folders)} 个小时文件夹) [{days_processed}/{len(day_to_hours)}]")
            
            # 合并后存放到 merged_videos/日期/ 目录下，所有位置共享同一个日期文件夹
            merged_day_path = os.path.join(config["video_root"], config["merged_dir"], day)
            os.makedirs(merged_day_path, exist_ok=True)

            # 如果天视频已合并且有效，则跳过该天所有小时的合并
            day_output = os.path.join(merged_day_path, f"{day}_{location}.mp4")
            day_key = f"{location}_{day}"
            if day_key in processed["days"]:
                if os.path.exists(day_output) and check_file_valid(day_output, config["min_valid_size"], config["deep_check"]):
                    logging.info(f"天视频已处理且文件有效: {day}，跳过该天所有小时的合并")
                    continue  # 跳过该天所有小时

            # 1. 改为顺序处理每小时视频
            hour_video_paths = []
            hour_folder_paths = []  # 记录原始小时文件夹路径，用于后续清理
            
            for hour_folder in sorted(hour_folders):
                hour = hour_folder[-2:]
                folder_path = os.path.join(camera_path, hour_folder)
                hour_folder_paths.append(folder_path)
                
                # 输出到 merged_videos/日期/ 目录
                hour_output = os.path.join(merged_day_path, f"{day}_{location}_{hour}.mp4")
                
                # 处理记录中仍使用完整的键名以确保唯一性
                hour_key = f"{os.path.basename(os.path.dirname(camera_path))}_{os.path.basename(camera_path)}_{hour_folder}"
                
                # 检查是否已处理且文件有效
                if hour_key in processed["hours"]:
                    if os.path.exists(hour_output) and check_file_valid(hour_output, config["min_valid_size"], config["deep_check"]):
                        logging.info(f"小时视频已处理且文件有效: {hour_folder}")
                        hour_video_paths.append(hour_output)
                        processed_count += 1
                        continue
                    else:
                        logging.warning(f"小时视频已处理但文件无效或不存在，将重新处理: {hour_folder}")
                        # 从记录中移除，以便重新处理
                        processed["hours"].remove(hour_key)
                
                # 获取该小时内所有视频文件，包括.mp4和.mp4.old后缀的文件
                videos = []
                videos.extend(glob.glob(os.path.join(folder_path, "*.mp4")))
                videos.extend(glob.glob(os.path.join(folder_path, "*.mp4.old")))
                if not videos:
                    processed_count += 1
                    continue
                
                # 根据文件名排序，确保时间顺序正确
                videos.sort()
                
                # 合并小时视频
                logging.info(f"合并小时视频 ({len(videos)} 个文件，包含.mp4和.mp4.old): {hour_folder} → {os.path.basename(hour_output)}")
                if merge_videos(videos, hour_output, config):
                    processed["hours"].append(hour_key)
                    # 记录合并时间戳
                    processed["merge_timestamps"][hour_key] = time.time()
                    save_processed_files(processed)
                    hour_video_paths.append(hour_output)
                
                processed_count += 1
                
                # 显示每个小时视频的处理进度
                progress = (processed_count / total_folders) * 100
                elapsed = time.time() - start_time
                logging.info(f"处理进度: {progress:.1f}% ({processed_count}/{total_folders}), 已用时间: {int(elapsed/60)}分钟")
            
            # 2. 合并成天视频
            if hour_video_paths:
                # 天视频输出路径包含位置信息
                day_output = os.path.join(merged_day_path, f"{day}_{location}.mp4")
                # 修改键名逻辑，使其更简单且唯一
                day_key = f"{location}_{day}"
                
                # 移除可能存在的临时文件
                temp_file = f"{day_output}.temp.mp4"
                if os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                        logging.info(f"删除旧的临时文件: {temp_file}")
                    except Exception as e:
                        logging.warning(f"删除临时文件失败: {e}")
                
                if day_key in processed["days"]:
                    if os.path.exists(day_output) and check_file_valid(day_output, config["min_valid_size"], config["deep_check"]):
                        logging.info(f"天视频已处理且文件有效: {day}")
                        continue  # 已处理且文件有效，跳过
                    else:
                        logging.warning(f"天视频已处理但文件无效或不存在，将重新处理: {day}")
                        # 从记录中移除，以便重新处理
                        processed["days"].remove(day_key)
                
                # 需要处理天视频
                if len(hour_video_paths) >= 2:  # 至少需要两个小时视频才合并
                    hour_video_paths.sort()
                    logging.info(f"合并天视频 ({len(hour_video_paths)} 个小时): {day}")
                    if merge_videos(hour_video_paths, day_output, config, is_daily_merge=True):
                        processed["days"].append(day_key)
                        # 记录天视频合并时间戳
                        processed["merge_timestamps"][day_key] = time.time()
                        
                        # 记录该天所有小时文件夹的合并时间戳（用于后续清理原始文件）
                        for folder_path in hour_folder_paths:
                            folder_key = f"original_{location}_{camera_id}_{os.path.basename(folder_path)}"
                            processed["merge_timestamps"][folder_key] = time.time()
                            
                        save_processed_files(processed)
                        # 3. 合并后删除小时视频（除非配置指定保留）
                        if not config["save_hourly"]:
                            for hv in hour_video_paths:
                                try:
                                    os.unlink(hv)
                                    logging.info(f"删除小时视频: {os.path.basename(hv)}")
                                except Exception as e:
                                    logging.error(f"删除小时视频失败: {e}")
                else:
                    logging.info(f"小时视频数量不足 ({len(hour_video_paths)}个)，跳过天合并: {day}")
            
        logging.info(f"摄像头处理完成: {location}/{camera_id}, 总用时: {int((time.time()-start_time)/60)}分钟")
        return True
        
    except Exception as e:
        logging.error(f"处理摄像头出错 {location}/{camera_id}: {e}")
        return False

def verify_processed_records(config, processed, deep_check=False):
    """验证已处理记录的文件是否存在且有效"""
    invalid_hours = []
    invalid_days = []
    
    logging.info(f"开始验证 {len(processed['hours'])} 个小时视频记录和 {len(processed['days'])} 个天视频记录...")
    
    # 验证小时视频
    for hour_key in processed["hours"]:
        # 解析小时键，格式为：xiaomi_camera_videos_相机ID_年月日时
        parts = hour_key.split('_')
        if len(parts) < 4:
            logging.warning(f"无效的小时记录键: {hour_key}")
            invalid_hours.append(hour_key)
            continue
            
        camera_id = parts[-2]
        hour_folder = parts[-1]
        
        if len(hour_folder) >= 10:
            day = hour_folder[:8]  # 年月日
            hour = hour_folder[8:10]  # 小时
            
            # 查找摄像头位置
            location = None
            video_root = config["video_root"]
            for loc in os.listdir(video_root):
                loc_path = os.path.join(video_root, loc)
                if os.path.isdir(loc_path) and loc != config["merged_dir"]:
                    camera_path = os.path.join(loc_path, "xiaomi_camera_videos", camera_id)
                    if os.path.exists(camera_path):
                        location = loc
                        break
            
            if location:
                # 判断当天与否，决定输出路径
                current_day = datetime.datetime.now().strftime("%Y%m%d")
                if day == current_day:
                    # 当天：输出到 video_root 根目录
                    hour_output = os.path.join(config["video_root"], f"{day}_{location}_{hour}.mp4")
                else:
                    # 非当天：输出到 merged_videos/日期/
                    merged_day_path = os.path.join(config["video_root"], config["merged_dir"], day)
                    hour_output = os.path.join(merged_day_path, f"{day}_{location}_{hour}.mp4")
                
                # 检查文件是否存在且有效
                if not os.path.exists(hour_output) or not check_file_valid(hour_output, config["min_valid_size"], deep_check):
                    logging.warning(f"小时视频文件无效或不存在: {hour_output}")
                    invalid_hours.append(hour_key)
            else:
                logging.warning(f"找不到摄像头位置: {camera_id}")
                invalid_hours.append(hour_key)
        else:
            logging.warning(f"无效的小时文件夹格式: {hour_folder}")
            invalid_hours.append(hour_key)
    
    # 验证天视频
    for day_key in processed["days"]:
        # 解析天键，格式为：位置_年月日
        parts = day_key.split('_')
        if len(parts) != 2:
            logging.warning(f"无效的天记录键: {day_key}")
            invalid_days.append(day_key)
            continue
            
        location = parts[0]
        day = parts[1]
        
        # 构建文件路径
        merged_day_path = os.path.join(config["video_root"], config["merged_dir"], day)
        day_output = os.path.join(merged_day_path, f"{day}_{location}.mp4")
        
        # 检查文件是否存在且有效
        if not os.path.exists(day_output) or not check_file_valid(day_output, config["min_valid_size"], deep_check):
            logging.warning(f"天视频文件无效或不存在: {day_output}")
            invalid_days.append(day_key)
    
    return invalid_hours, invalid_days

def clean_processed_records(processed, invalid_hours, invalid_days):
    """清理无效的处理记录"""
    # 移除无效小时记录
    for hour_key in invalid_hours:
        if hour_key in processed["hours"]:
            processed["hours"].remove(hour_key)
    
    # 移除无效天记录
    for day_key in invalid_days:
        if day_key in processed["days"]:
            processed["days"].remove(day_key)
    
    # 保存清理后的记录
    save_processed_files(processed)
    
    logging.info(f"已清理 {len(invalid_hours)} 个无效的小时记录和 {len(invalid_days)} 个无效的天记录")
    return processed

def cleanup_original_videos(config, processed):
    """清理已合并且超过指定天数的原始视频文件"""
    if config["delete_original_after_days"] <= 0:
        logging.info("未启用原始视频清理功能")
        return
    
    logging.info("开始检查是否有需要清理的原始视频...")
    current_time = time.time()
    delete_after_seconds = config["delete_original_after_days"] * 86400  # 天数转换为秒
    
    # 获取所有原始文件夹的记录
    original_folders = {}
    for key, timestamp in processed["merge_timestamps"].items():
        if key.startswith("original_"):
            # 检查是否已经过了指定的天数
            if current_time - timestamp > delete_after_seconds:
                parts = key.split('_')
                if len(parts) >= 4:
                    location = parts[1]
                    camera_id = parts[2]
                    hour_folder = parts[3]
                    
                    # 构建原始文件夹路径
                    video_root = config["video_root"]
                    folder_path = os.path.join(video_root, location, "xiaomi_camera_videos", camera_id, hour_folder)
                    
                    if os.path.exists(folder_path):
                        logging.info(f"准备清理原始视频文件夹: {folder_path}")
                        try:
                            # 删除文件夹中的所有文件
                            file_count = 0
                            for file in os.listdir(folder_path):
                                file_path = os.path.join(folder_path, file)
                                if os.path.isfile(file_path):
                                    os.unlink(file_path)
                                    file_count += 1
                            
                            # 尝试删除文件夹（如果为空）
                            if len(os.listdir(folder_path)) == 0:
                                os.rmdir(folder_path)
                                logging.info(f"已清理原始视频文件夹: {folder_path} (删除了 {file_count} 个文件)")
                            else:
                                logging.warning(f"文件夹不为空，无法删除: {folder_path}")
                            
                            # 从记录中移除，避免重复处理
                            original_folders[key] = True
                            
                        except Exception as e:
                            logging.error(f"清理原始视频文件夹失败 {folder_path}: {e}")
    
    # 从记录中移除已处理的文件夹
    for key in original_folders.keys():
        if key in processed["merge_timestamps"]:
            del processed["merge_timestamps"][key]
    
    # 保存更新后的记录
    save_processed_files(processed)
    logging.info(f"原始视频清理完成，共处理 {len(original_folders)} 个文件夹")

def cleanup_merged_videos(config, processed):
    """清理已合并且超过指定天数的视频文件"""
    if config["delete_merged_after_days"] <= 0:
        logging.info("未启用合并视频清理功能")
        return
    
    logging.info(f"开始检查是否有需要清理的已合并视频 (超过{config['delete_merged_after_days']}天的视频将被删除)...")
    current_time = time.time()
    delete_after_seconds = config["delete_merged_after_days"] * 86400  # 天数转换为秒
    videos_deleted = 0
    
    # 处理小时视频记录
    for hour_key in list(processed["hours"]):  # 使用list创建副本避免遍历时修改
        # 检查合并时间戳
        if hour_key in processed["merge_timestamps"]:
            timestamp = processed["merge_timestamps"][hour_key]
            if current_time - timestamp > delete_after_seconds:
                # 解析小时键，格式为：xiaomi_camera_videos_相机ID_年月日时
                parts = hour_key.split('_')
                if len(parts) < 4:
                    continue
                    
                camera_id = parts[-2]
                hour_folder = parts[-1]
                
                if len(hour_folder) >= 10:
                    day = hour_folder[:8]  # 年月日
                    hour = hour_folder[8:10]  # 小时
                    
                    # 查找摄像头位置
                    location = None
                    video_root = config["video_root"]
                    for loc in os.listdir(video_root):
                        loc_path = os.path.join(video_root, loc)
                        if os.path.isdir(loc_path) and loc != config["merged_dir"]:
                            camera_path = os.path.join(loc_path, "xiaomi_camera_videos", camera_id)
                            if os.path.exists(camera_path):
                                location = loc
                                break
                    
                    if location:
                        # 构建小时视频文件路径
                        merged_day_path = os.path.join(config["video_root"], config["merged_dir"], day)
                        hour_output = os.path.join(merged_day_path, f"{day}_{location}_{hour}.mp4")
                        
                        # 删除小时视频文件
                        if os.path.exists(hour_output):
                            try:
                                os.unlink(hour_output)
                                logging.info(f"已删除超过{config['delete_merged_after_days']}天的小时视频: {hour_output}")
                                videos_deleted += 1
                                
                                # 从处理记录中移除
                                processed["hours"].remove(hour_key)
                                if hour_key in processed["merge_timestamps"]:
                                    del processed["merge_timestamps"][hour_key]
                            except Exception as e:
                                logging.error(f"删除小时视频失败 {hour_output}: {e}")
    
    # 处理天视频记录
    for day_key in list(processed["days"]):  # 同样使用list创建副本
        if day_key in processed["merge_timestamps"]:
            timestamp = processed["merge_timestamps"][day_key]
            if current_time - timestamp > delete_after_seconds:
                # 解析天键，格式为：位置_年月日
                parts = day_key.split('_')
                if len(parts) != 2:
                    continue
                    
                location = parts[0]
                day = parts[1]
                
                # 构建天视频文件路径
                merged_day_path = os.path.join(config["video_root"], config["merged_dir"], day)
                day_output = os.path.join(merged_day_path, f"{day}_{location}.mp4")
                
                # 删除天视频文件
                if os.path.exists(day_output):
                    try:
                        os.unlink(day_output)
                        logging.info(f"已删除超过{config['delete_merged_after_days']}天的天视频: {day_output}")
                        videos_deleted += 1
                        
                        # 从处理记录中移除
                        processed["days"].remove(day_key)
                        if day_key in processed["merge_timestamps"]:
                            del processed["merge_timestamps"][day_key]
                    except Exception as e:
                        logging.error(f"删除天视频失败 {day_output}: {e}")
    
    # 保存更新后的处理记录
    if videos_deleted > 0:
        save_processed_files(processed)
        logging.info(f"已清理 {videos_deleted} 个超过{config['delete_merged_after_days']}天的已合并视频文件")
    else:
        logging.info(f"未找到需要清理的已合并视频文件")
    
    # 尝试清理可能的空文件夹
    try:
        merged_dir = os.path.join(config["video_root"], config["merged_dir"])
        for day_dir in os.listdir(merged_dir):
            day_path = os.path.join(merged_dir, day_dir)
            if os.path.isdir(day_path) and len(os.listdir(day_path)) == 0:
                os.rmdir(day_path)
                logging.info(f"已删除空的日期文件夹: {day_path}")
    except Exception as e:
        logging.warning(f"清理空文件夹时出错: {e}")

def get_latest_date_folders_by_camera(cameras):
    """获取每个摄像头当前日期的文件夹"""
    camera_latest_dates = {}
    required_cameras = set(['收银台', '熨烫机', '转角', '门口'])
    current_date = datetime.datetime.now().strftime("%Y%m%d")
    
    # 按摄像头位置分组
    cameras_by_location = {}
    for camera in cameras:
        location = camera["location"]
        if location in required_cameras:
            if location not in cameras_by_location:
                cameras_by_location[location] = []
            cameras_by_location[location].append(camera)
    
    # 检查是否所有必需的摄像头都被找到
    for required_loc in required_cameras:
        if required_loc not in cameras_by_location:
            logging.warning(f"缺少必需的摄像头位置: {required_loc}")
    
    # 处理每个位置的摄像头
    for location, location_cameras in cameras_by_location.items():
        logging.info(f"检查位置 {location} 的 {len(location_cameras)} 个摄像头是否有当前日期 {current_date} 的视频")
        
        # 检查该位置是否有当前日期的视频
        has_current_date = False
        
        for camera in location_cameras:
            camera_id = camera["camera_id"]
            camera_path = camera["path"]
        
            logging.info(f"检查摄像头 {location}({camera_id}) 是否有当前日期 {current_date} 的视频")
        
            # 使用Path对象查找当前日期的文件夹
            try:
                # 构建日期文件夹名称（前8位是日期，后2位是小时）
                current_date_pattern = current_date + r'\d{2}'  # 例如：2025070200, 2025070201 等
                date_pattern = re.compile(current_date_pattern)
            
                # 确保路径存在
                camera_path_obj = Path(camera_path)
                if not camera_path_obj.exists():
                    logging.warning(f"摄像头路径不存在: {camera_path}")
                    continue
                
                # 获取当前日期的文件夹
                current_date_folders = [
                    folder.name for folder in camera_path_obj.iterdir() 
                    if folder.is_dir() and date_pattern.match(folder.name)
                ]
            
                if current_date_folders:
                    # 验证文件夹中有足够的视频文件
                    valid_folders = 0
                    for folder in current_date_folders:
                        hour_folder_path = os.path.join(camera_path, folder)
                        if os.path.isdir(hour_folder_path) and len(os.listdir(hour_folder_path)) >= 5:  # 至少有5个文件
                            valid_folders += 1
                    
                    if valid_folders > 0:
                        logging.info(f"摄像头 {location}({camera_id}) 找到当前日期 {current_date} 的有效视频目录: {valid_folders} 个")
                        has_current_date = True
                        break  # 一个摄像头有当前日期的视频就足够了
                    else:
                        logging.warning(f"摄像头 {location}({camera_id}) 找到日期 {current_date} 的文件夹但没有足够的视频文件")
                else:
                    logging.warning(f"摄像头 {location}({camera_id}) 未找到当前日期 {current_date} 的文件夹")
            except Exception as e:
                logging.error(f"处理摄像头 {location}({camera_id}) 时出错: {e}")
                import traceback
                logging.error(traceback.format_exc())
        
        # 如果找到了当前日期的视频，记录到结果中
        if has_current_date:
            camera_latest_dates[location] = current_date
            logging.info(f"位置 {location} 有当前日期 {current_date} 的视频")
    
    # 记录找到的当前日期视频的摄像头
    if camera_latest_dates:
        found_locations = list(camera_latest_dates.keys())
        logging.info(f"有当前日期 {current_date} 视频的摄像头位置: {found_locations}")
        
        # 检查是否所有必需的摄像头都有当前日期的视频
        if all(camera in camera_latest_dates for camera in required_cameras):
            logging.info(f"所有必需的摄像头 {required_cameras} 都有当前日期 {current_date} 的视频，可以开始合并")
        else:
            missing = required_cameras - set(found_locations)
            logging.warning(f"有 {len(missing)} 个必需的摄像头位置没有当前日期 {current_date} 的视频: {missing}")
    else:
        logging.warning(f"没有任何摄像头有当前日期 {current_date} 的视频")
    
    return camera_latest_dates

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="小米摄像头视频合并工具")
    parser.add_argument("--config", help="指定配置文件路径")
    parser.add_argument("--single-run", action="store_true", help="单次运行模式（运行完成后退出）")
    parser.add_argument("--ignore-processed", action="store_true", help="忽略已处理记录，强制重新处理")
    parser.add_argument("--deep-check", action="store_true", help="进行深度检查，验证视频文件可播放性")
    parser.add_argument("--verify-only", action="store_true", help="仅验证已处理记录，不执行合并")
    parser.add_argument("--clean-records", action="store_true", help="清理无效的处理记录")
    parser.add_argument("--auto-clean", action="store_true", help="自动清理无效记录（默认启用）", default=True)
    parser.add_argument("--cleanup-original", action="store_true", help="仅清理原始视频文件，不执行合并")
    parser.add_argument("--cleanup-merged", action="store_true", help="仅清理已合并的视频文件，不执行合并")
    parser.add_argument("--watchdog-timeout", type=int, default=3600, help="看门狗超时时间(秒)，默认1小时")
    args = parser.parse_args()
    
    if args.config:
        global CONFIG_FILE
        CONFIG_FILE = args.config
    
    # 加载配置
    config = load_config()
    
    # 如果命令行指定了深度检查，覆盖配置
    if args.deep_check:
        config["deep_check"] = True
        logging.info("已启用深度检查模式")
    
    # 启动看门狗定时器，防止脚本卡死
    watchdog = WatchdogTimer(args.watchdog_timeout)
    watchdog.start()
    logging.info(f"已启动看门狗定时器，超时时间: {args.watchdog_timeout} 秒")
    
    logging.info("="*50)
    logging.info("开始视频合并处理")
    logging.info(f"配置: {json.dumps(config, ensure_ascii=False, indent=2)}")
    
    # 检查ffmpeg是否可用
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception:
        logging.error("ffmpeg未安装或不可用，请先安装ffmpeg并确保可以在命令行中使用")
        watchdog.stop()
        return
    
    # 加载已处理记录
    processed = load_processed_files()
    
    # 如果指定了忽略已处理记录，则清空记录
    if args.ignore_processed:
        logging.info("已指定--ignore-processed参数，将忽略已处理记录")
        # 保留合并时间戳记录，只清空处理记录
        merge_timestamps = processed.get("merge_timestamps", {})
        processed = {"hours": [], "days": [], "merge_timestamps": merge_timestamps}
    
    # 如果只需要清理原始视频，则执行清理后退出
    if args.cleanup_original:
        logging.info("仅执行原始视频清理...")
        cleanup_original_videos(config, processed)
        watchdog.stop()
        return
        
    # 如果只需要清理已合并视频，则执行清理后退出
    if args.cleanup_merged:
        logging.info("仅执行已合并视频清理...")
        cleanup_merged_videos(config, processed)
        watchdog.stop()
        return
    
    # 每次执行前都验证已处理记录
    logging.info("开始验证已处理记录...")
    invalid_hours, invalid_days = verify_processed_records(config, processed, config["deep_check"])
    logging.info(f"验证结果: 发现 {len(invalid_hours)} 个无效的小时记录和 {len(invalid_days)} 个无效的天记录")
    
    # 如果启用了自动清理或指定了清理参数，则清理无效记录
    if args.auto_clean or args.clean_records:
        if invalid_hours or invalid_days:
            logging.info("清理无效的处理记录...")
            processed = clean_processed_records(processed, invalid_hours, invalid_days)

    # === 新增：列出所有已合并且有效的视频文件 ===
    print("\n[已合并且有效的小时视频:]")
    for hour_key in processed["hours"]:
        # 解析 hour_key 得到实际路径
        parts = hour_key.split('_')
        if len(parts) < 4:
            continue
        camera_id = parts[-2]
        hour_folder = parts[-1]
        if len(hour_folder) >= 10:
            day = hour_folder[:8]
            hour = hour_folder[8:10]
            # 查找摄像头位置
            location = None
            video_root = config["video_root"]
            for loc in os.listdir(video_root):
                loc_path = os.path.join(video_root, loc)
                if os.path.isdir(loc_path) and loc != config["merged_dir"]:
                    camera_path = os.path.join(loc_path, "xiaomi_camera_videos", camera_id)
                    if os.path.exists(camera_path):
                        location = loc
                        break
            if location:
                current_day = datetime.datetime.now().strftime("%Y%m%d")
                if day == current_day:
                    hour_output = os.path.join(config["video_root"], f"{day}_{location}_{hour}.mp4")
                else:
                    merged_day_path = os.path.join(config["video_root"], config["merged_dir"], day)
                    hour_output = os.path.join(merged_day_path, f"{day}_{location}_{hour}.mp4")
                if os.path.exists(hour_output):
                    print(hour_output)
    print("\n[已合并且有效的天视频:]")
    for day_key in processed["days"]:
        parts = day_key.split('_')
        if len(parts) != 2:
            continue
        location = parts[0]
        day = parts[1]
        merged_day_path = os.path.join(config["video_root"], config["merged_dir"], day)
        day_output = os.path.join(merged_day_path, f"{day}_{location}.mp4")
        if os.path.exists(day_output):
            print(day_output)
    # === 新增结束 ===

    # 如果只是验证记录，则退出
    if args.verify_only:
        logging.info("验证完成，退出")
        watchdog.stop()
        return
    
    # 执行原始视频清理
    cleanup_original_videos(config, processed)
    
    # 执行合并后的视频清理
    cleanup_merged_videos(config, processed)
    
    run_forever = not args.single_run
    required_cameras = set(['收银台', '熨烫机', '转角', '门口'])
    is_processing = False
    
    while True:
        try:
            # 重置看门狗定时器
            watchdog.reset()
            
            # 如果当前没有正在处理的任务，则检查是否有新的日期需要处理
            if not is_processing:
                # 扫描摄像头文件夹
                cameras = scan_camera_folders(config)
                
                if not cameras:
                    logging.warning("未找到摄像头文件夹")
                    if not run_forever:
                        break
                    time.sleep(config["scan_interval"])
                    continue
                
                # 打印找到的摄像头信息
                found_cameras = [f"{c['location']}({c['camera_id']})" for c in cameras]
                logging.info(f"找到摄像头: {found_cameras}")
                
                # 获取每个摄像头当天的日期文件夹
                camera_dates = get_latest_date_folders_by_camera(cameras)
                
                # 检查是否所有必需的摄像头都有当前日期的视频
                logging.info(f"当前必需的摄像头: {sorted(list(required_cameras))}")
                logging.info(f"找到的摄像头当前日期视频: {camera_dates}")
                
                # 确认所有必需的摄像头都有当天视频
                all_cameras_present = all(camera in camera_dates for camera in required_cameras)
                if not all_cameras_present:
                    missing_cameras = required_cameras - set(camera_dates.keys())
                    logging.warning(f"有 {len(missing_cameras)} 个摄像头没有当前日期的视频: {missing_cameras}")
                    if not run_forever:
                        break
                    time.sleep(config["scan_interval"])
                    continue
                    
                # 所有摄像头都有当前日期的视频，开始处理
                logging.info(f"所有必需的摄像头都有当前日期的视频，开始处理")
                current_date = datetime.datetime.now().strftime("%Y%m%d")
                
                # 开始处理
                is_processing = True
                start_time = time.time()
                
                # 强制串行处理每个摄像头
                for camera in cameras:
                    # 重置看门狗定时器，防止长时间处理导致超时
                    watchdog.reset()
                    
                    location = camera["location"]
                    if location in required_cameras:
                        process_camera(camera, config, processed)
                
                elapsed_time = time.time() - start_time
                logging.info(f"本轮处理完成，耗时: {elapsed_time:.1f} 秒")
                
                # 每轮处理完成后，执行原始视频和合并视频清理
                cleanup_original_videos(config, processed)
                cleanup_merged_videos(config, processed)
                
                is_processing = False
            
            if not run_forever:
                break
                
            # 等待下一次扫描
            logging.info(f"等待 {config['scan_interval']} 秒后再次扫描...")
            
            # 分段休眠，每30秒重置一次看门狗定时器，防止长时间休眠导致程序被误判为卡死
            remaining_sleep = config["scan_interval"]
            while remaining_sleep > 0:
                sleep_time = min(30, remaining_sleep)
                time.sleep(sleep_time)
                remaining_sleep -= sleep_time
                watchdog.reset()
            
        except KeyboardInterrupt:
            logging.info("接收到中断信号，程序退出...")
            watchdog.stop()
            return
        except Exception as e:
            logging.error(f"处理发生错误: {e}")
            import traceback
            logging.error(f"错误详情: {traceback.format_exc()}")
            is_processing = False  # 发生错误时重置处理状态
            time.sleep(60)  # 发生错误后，等待1分钟再重试
            if not run_forever:
                break
            continue
    
    # 程序正常退出，停止看门狗定时器
    watchdog.stop()
    logging.info("程序正常退出")

if __name__ == "__main__":
    main() 
