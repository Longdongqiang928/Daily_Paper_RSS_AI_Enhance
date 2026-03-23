import json
import io
import os
import glob
import argparse

def cleanup_files(prefixes, data_dir, exclude_sources=['arxiv', 'nature'], remove_fields=['score', 'collection']):
    """
    删除指定日期前缀的 JSONL 文件中指定的字段，排除特定的源。
    """
    all_target_files = []
    for prefix in prefixes:
        # 匹配前缀的文件
        pattern = os.path.join(data_dir, f'{prefix}*.jsonl')
        files = glob.glob(pattern)
        
        # 过滤掉排除的源
        filtered = []
        for f in files:
            filename = os.path.basename(f).lower()
            should_exclude = any(src in filename for src in exclude_sources)
            if not should_exclude:
                filtered.append(f)
        
        all_target_files.extend(filtered)

    if not all_target_files:
        print("未找到符合条件的待处理文件。")
        return

    print(f"找到 {len(all_target_files)} 个待处理文件。")

    for file_path in all_target_files:
        try:
            filename = os.path.basename(file_path)
            # 如果是 AI 增强的文件，直接删除
            if '_AI_enhanced_' in filename:
                os.remove(file_path)
                print(f"已删除 AI 增强文件: {file_path}")
                continue

            # 对于原始文件，读取并清理指定字段
            with io.open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 写回修改后的内容
            with io.open(file_path, 'w', encoding='utf-8') as f:
                for line in lines:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        # 删除指定字段
                        for field in remove_fields:
                            data.pop(field, None)
                        f.write(json.dumps(data, ensure_ascii=False) + '\n')
                    except json.JSONDecodeError as e:
                        print(f"文件 {file_path} 中的 JSON 解析错误: {e}")
            print(f"已处理: {file_path}")
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量清理 JSONL 文件中的字段（排除 arxiv 和 nature 源）")
    parser.add_argument("prefixes", nargs="+", help="日期前缀，例如 2026-03-04")
    parser.add_argument("--dir", default=r"e:\yuxuan\interest\Daily_Paper_RSS_AI_Enhance\data", help="数据目录路径")
    parser.add_argument("--fields", nargs="+", default=["score", "collection"], help="要删除的字段列表")
    
    args = parser.parse_args()
    
    cleanup_files(args.prefixes, args.dir, remove_fields=args.fields)
