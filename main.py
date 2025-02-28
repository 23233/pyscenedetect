import os
import sys
import argparse
import logging
from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector
from scenedetect.video_splitter import split_video_ffmpeg
from datetime import datetime


# 设置日志
def setup_logging():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    # 今天的日期
    log_file = os.path.join(log_dir, f'scene_detect_{datetime.now().strftime("%Y-%m-%d")}.log')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def split_video_into_scenes(video_path, threshold=27.0):
    """
    Split a video into scenes based on content detection
    
    Returns:
        dict: 包含处理结果的字典
    """
    result = {
        'status': 'success',
        'video_path': video_path,
        'output_path': '',
        'scenes_count': 0
    }

    try:
        # Create output directory in the same folder as the video
        video_dir = os.path.dirname(video_path)
        base_filename = os.path.splitext(os.path.basename(video_path))[0]
        save_path = os.path.join(video_dir, f"{base_filename}_分镜镜头")
        
        # 如果目录已存在，先删除
        if os.path.exists(save_path):
            import shutil
            shutil.rmtree(save_path)
            logging.info(f"已清理已存在的输出目录: {save_path}")
            
        os.makedirs(save_path)
        result['output_path'] = save_path

        output_file_template = os.path.join(save_path, 'Scene-$SCENE_NUMBER.mp4')

        # Perform scene detection
        video = open_video(video_path)
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=threshold))
        
        scene_manager.detect_scenes(video)
        scene_list = scene_manager.get_scene_list()
        result['scenes_count'] = len(scene_list)

        # Split the video
        split_video_ffmpeg(
            video_path,
            scene_list,
            output_file_template=output_file_template,
            show_progress=False,
            show_output=False
        )
        
        logging.info(f"处理完成: {video_path}")
        logging.info(f"输出目录: {save_path}")
        logging.info(f"场景数量: {len(scene_list)}")
        
        return result

    except Exception as e:
        error_msg = f"处理视频时出错: {str(e)}"
        logging.error(error_msg)
        result['status'] = 'error'
        result['error'] = error_msg
        return result

def process_folder(folder_path, threshold):
    """
    Process all MP4 files in the given folder
    
    Returns:
        list: 包含每个视频处理结果的列表
    """
    results = []
    video_files = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith('.mp4')
    ]

    if not video_files:
        logging.warning(f"在目录 {folder_path} 中未找到MP4文件")
        return results

    for video_file in video_files:
        try:
            result = split_video_into_scenes(video_file, threshold)
            results.append(result)
        except Exception as e:
            results.append({
                'status': 'error',
                'video_path': video_file,
                'error': str(e)
            })
    
    return results

def main():
    setup_logging()

    parser = argparse.ArgumentParser(description='视频场景分割工具')
    parser.add_argument('path', help='视频文件或包含视频的文件夹的路径')
    parser.add_argument('--threshold', type=float, default=27.0,
                        help='场景检测阈值 (默认: 27.0)')
    parser.add_argument('--json-output', action='store_true',default=True,
                        help='以JSON格式输出结果')

    args = parser.parse_args()
    path = args.path    
    threshold = args.threshold

    try:
        results = []
        if os.path.isfile(path):
            if path.lower().endswith('.mp4'):
                results = [split_video_into_scenes(path, threshold)]
            else:
                logging.error("请提供有效的MP4文件")
        elif os.path.isdir(path):
            results = process_folder(path, threshold)
        else:
            logging.error("请提供有效的文件或文件夹路径")

        if args.json_output:
            import json
            print(json.dumps(results, ensure_ascii=False, indent=2))
        
        # 返回退出码
        if any(r.get('status') == 'error' for r in results):
            sys.exit(1)
        sys.exit(0)

    except Exception as e:
        logging.error(f"程序执行出错: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        if not args.json_output:
            input("按回车键退出...")

if __name__ == "__main__":
    main()
