# -*- coding: utf-8 -*-
import os
from PIL import Image, ExifTags
from collections import defaultdict
import pandas as pd
import matplotlib.pyplot as plt
import sys
import matplotlib as mpl
import numpy as np

# 设置matplotlib后端为Agg（非交互式），避免某些系统问题
mpl.use('Agg')

def get_focal_length(img_path):
    """从图像文件EXIF中提取焦距信息（单位：毫米）"""
    try:
        with Image.open(img_path) as img:
            exif = img._getexif()
            if not exif:
                print(f"警告: {img_path} 缺少EXIF数据")
                return None
                
            # 查找焦距标签ID（0x920A）
            focal_length = None
            for tag_id, value in exif.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                if tag == 'FocalLength':
                    focal_length = value
                elif tag == 'FocalLengthIn35mmFilm':
                    return float(value)  # 优先使用35mm等效焦距

            if focal_length is not None:
                # 处理有理数格式（分子/分母）
                if isinstance(focal_length, tuple):
                    return round(focal_length[0] / focal_length[1], 1)
                return float(focal_length)
    except (IOError, AttributeError, KeyError, IndexError, TypeError) as e:
        print(f"处理 {img_path} 时出错: {e}")
    return None

def analyze_focal_lengths(directories):
    """主分析函数，接受一个目录列表"""
    focal_counter = defaultdict(int)
    total_files = 0
    missing_exif = 0
    
    for directory in directories:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    total_files += 1
                    img_path = os.path.join(root, file)
                    focal = get_focal_length(img_path)
                    
                    if focal is not None:
                        focal_counter[focal] += 1
                    else:
                        missing_exif += 1
    
    # 生成结果
    return {
        "total_images": total_files,
        "images_with_focal": total_files - missing_exif,
        "focal_counts": dict(focal_counter),
        "missing_exif": missing_exif
    }

def generate_report(results, output_dir):
    """生成统计报告和图表"""
    if not results['focal_counts']:
        print(f"警告: 在 {output_dir} 中未找到任何包含焦距信息的图片")
        return None, None

    # 创建数据表格
    df = pd.DataFrame(
        [(focal, count) for focal, count in results['focal_counts'].items()],
        columns=['Focal Length (mm)', 'Count']
    ).sort_values('Focal Length (mm)')
    
    # 保存CSV
    csv_path = os.path.join(output_dir, 'focal_length_stats.csv')
    try:
        df.to_csv(csv_path, index=False)
    except IOError as e:
        print(f"保存CSV文件时出错: {e}")
        return None, None
    
    # 生成图表
    plt.figure(figsize=(14, 7))  # 增加图表尺寸
    
    # 优化坐标轴显示
    x_values = df['Focal Length (mm)'].astype(str)
    y_values = df['Count']
    
    plt.bar(x_values, y_values, color='skyblue')
    plt.title('Focal Length Distribution', fontsize=14)
    plt.xlabel('Focal Length (mm)', fontsize=12)
    plt.ylabel('Image Count', fontsize=12)
    
    # 优化x轴标签显示
    num_labels = len(x_values)
    
    # 根据数据点数量动态调整标签显示频率
    if num_labels > 30:
        # 如果焦距值太多，只显示部分标签
        step = max(1, num_labels // 20)  # 大约显示20个标签
        plt.xticks(
            ticks=np.arange(len(x_values)), 
            labels=[label if i % step == 0 else '' for i, label in enumerate(x_values)],
            rotation=45, 
            ha='right',
            fontsize=10
        )
    else:
        # 如果数据点不多，显示所有标签但旋转45度
        plt.xticks(rotation=45, ha='right', fontsize=10)
    
    plt.tight_layout()
    
    # 保存图表
    chart_path = os.path.join(output_dir, 'focal_length_chart.png')
    try:
        plt.savefig(chart_path, bbox_inches='tight', dpi=150)
    except IOError as e:
        print(f"保存图表文件时出错: {e}")
        return csv_path, None
    
    # 清除图形释放内存
    plt.close()
    
    return csv_path, chart_path

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='批量分析照片焦距信息')
    parser.add_argument('input_dirs', nargs='+', help='包含JPEG或PNG文件的目录列表')
    parser.add_argument('output_dir', help='结果输出目录')
    
    parser.epilog = "示例用法: python focal_analyzer.py /照片目录1 /照片目录2 /输出目录"
    
    args = parser.parse_args()
    
    # 验证输入目录列表中的每个目录
    for directory in args.input_dirs:
        if not os.path.isdir(directory) or not os.access(directory, os.R_OK):
            print(f"错误: 输入目录 {directory} 不存在或不可读")
            sys.exit(1)
    
    # 确保输出目录存在且可写
    os.makedirs(args.output_dir, exist_ok=True)
    if not os.access(args.output_dir, os.W_OK):
        print(f"错误: 输出目录 {args.output_dir} 不可写")
        sys.exit(1)
    
    # 分析照片
    print(f"正在分析目录: {args.input_dirs}...")
    results = analyze_focal_lengths(args.input_dirs)
    
    # 生成报告
    csv_path, chart_path = generate_report(results, args.output_dir)
    
    # 打印摘要
    print("\n===== 分析结果 =====")
    print(f"扫描图片总数: {results['total_images']}")
    print(f"包含焦距信息的图片: {results['images_with_focal']}")
    print(f"缺少EXIF数据的图片: {results['missing_exif']}")
    
    if csv_path:
        print(f"\n焦距统计已保存至: {csv_path}")
    if chart_path:
        print(f"分布图表已保存至: {chart_path}")
    
    # 显示最常见的焦距
    if results['focal_counts']:
        top_focal = max(results['focal_counts'].items(), key=lambda x: x[1])
        print(f"\n最常见的焦距: {top_focal[0]}mm (共 {top_focal[1]} 张)")
