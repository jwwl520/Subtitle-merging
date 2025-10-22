import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import os
import re
import subprocess
import sys
import hashlib

# 尝试导入 pysrt，如果没有则提示安装
try:
    import pysrt
except ImportError:
    print("警告: 未找到 pysrt 库，字幕检查功能将不可用")
    print("请运行: pip install pysrt")
    pysrt = None

class VideoCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("短剧审片检查工具 - 专业版")
        self.root.geometry("1400x900")
        
        # 数据存储
        self.video_data = []  # 存储视频文件信息
        self.srt_data = []    # 存储字幕文件信息

        # 创建主界面布局
        self.create_ui()
        
    def create_ui(self):
        """创建用户界面"""
        # ========== 顶部：文件夹选择区域 ==========
        top_frame = tk.Frame(self.root, padx=10, pady=10)
        top_frame.pack(fill=tk.X)

        tk.Label(top_frame, text="选择文件夹:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))

        self.folder_path_var = tk.StringVar()
        folder_entry = tk.Entry(top_frame, textvariable=self.folder_path_var, width=70)
        folder_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        tk.Button(top_frame, text="浏览...", command=self.browse_folder, width=10).pack(side=tk.LEFT, padx=(5, 0))

        # ========== 中上部：统计信息 ==========
        stats_frame = tk.Frame(self.root, padx=10, pady=5)
        stats_frame.pack(fill=tk.X)

        tk.Label(stats_frame, text="原片视频:").pack(side=tk.LEFT)
        self.original_video_count_var = tk.StringVar(value="0")
        tk.Entry(stats_frame, textvariable=self.original_video_count_var, width=8, state='readonly').pack(side=tk.LEFT, padx=(0, 20))

        tk.Label(stats_frame, text="无字幕视频:").pack(side=tk.LEFT)
        self.no_subtitle_count_var = tk.StringVar(value="0")
        tk.Label(stats_frame, textvariable=self.no_subtitle_count_var, width=8, relief=tk.SUNKEN).pack(side=tk.LEFT, padx=(0, 20))

        tk.Label(stats_frame, text="SRT文件:").pack(side=tk.LEFT)
        self.srt_count_var = tk.StringVar(value="0")
        tk.Label(stats_frame, textvariable=self.srt_count_var, width=8, relief=tk.SUNKEN).pack(side=tk.LEFT, padx=(0, 20))

        # ========== 中部：双列表区域 ==========
        tables_frame = tk.Frame(self.root, padx=10, pady=5)
        tables_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：视频文件列表
        video_frame = tk.LabelFrame(tables_frame, text="📹 无字幕视频文件", font=("Arial", 10, "bold"))
        video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 视频表格
        video_columns = ("序号", "文件名", "状态", "问题详情")
        self.video_tree = ttk.Treeview(video_frame, columns=video_columns, show="headings", height=15)
        
        self.video_tree.heading("序号", text="序号")
        self.video_tree.heading("文件名", text="文件名")
        self.video_tree.heading("状态", text="检查状态")
        self.video_tree.heading("问题详情", text="问题详情")
        
        self.video_tree.column("序号", width=50, anchor="center")
        self.video_tree.column("文件名", width=250, anchor="w")
        self.video_tree.column("状态", width=100, anchor="center")
        self.video_tree.column("问题详情", width=200, anchor="w")
        
        # 滚动条
        video_scrollbar = ttk.Scrollbar(video_frame, orient="vertical", command=self.video_tree.yview)
        self.video_tree.configure(yscrollcommand=video_scrollbar.set)
        
        self.video_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        video_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 右侧：字幕文件列表
        srt_frame = tk.LabelFrame(tables_frame, text="📝 字幕文件列表", font=("Arial", 10, "bold"))
        srt_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 字幕表格
        srt_columns = ("序号", "文件名", "状态", "问题")
        self.srt_tree = ttk.Treeview(srt_frame, columns=srt_columns, show="headings", height=15)
        
        self.srt_tree.heading("序号", text="序号")
        self.srt_tree.heading("文件名", text="文件名")
        self.srt_tree.heading("状态", text="检查状态")
        self.srt_tree.heading("问题", text="问题详情")
        
        self.srt_tree.column("序号", width=50, anchor="center")
        self.srt_tree.column("文件名", width=250, anchor="w")
        self.srt_tree.column("状态", width=100, anchor="center")
        self.srt_tree.column("问题", width=200, anchor="w")
        
        # 滚动条
        srt_scrollbar = ttk.Scrollbar(srt_frame, orient="vertical", command=self.srt_tree.yview)
        self.srt_tree.configure(yscrollcommand=srt_scrollbar.set)
        
        self.srt_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        srt_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 配置标签颜色
        self.video_tree.tag_configure('pass', background='#c8e6c9')  # 浅绿色
        self.video_tree.tag_configure('fail', background='#ffcdd2')  # 浅红色
        self.video_tree.tag_configure('warning', background='#fff9c4')  # 浅黄色
        self.video_tree.tag_configure('pending', background='#e0e0e0')  # 灰色
        
        self.srt_tree.tag_configure('pass', background='#c8e6c9')
        self.srt_tree.tag_configure('fail', background='#ffcdd2')
        self.srt_tree.tag_configure('warning', background='#fff9c4')
        self.srt_tree.tag_configure('pending', background='#e0e0e0')

        # ========== 底部：操作按钮 ==========
        action_frame = tk.Frame(self.root, padx=10, pady=10)
        action_frame.pack(fill=tk.X)

        tk.Button(action_frame, text="🔍 基础检查", command=self.start_check, 
                 bg="#2196F3", fg="white", width=15, height=2, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        
        tk.Button(action_frame, text="🎯 字幕深度检查", command=self.start_subtitle_deep_check,
                 bg="#4CAF50", fg="white", width=15, height=2, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        
        tk.Button(action_frame, text="📊 导出报告", command=self.export_report,
                 bg="#FF9800", fg="white", width=15, height=2, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        
        tk.Button(action_frame, text="🔄 刷新", command=self.refresh_all,
                 bg="#607D8B", fg="white", width=12, height=2, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

        # ========== 最底部：日志区域（可折叠）==========
        log_frame = tk.LabelFrame(self.root, text="📋 详细日志（点击展开/收起）", padx=10, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 初始化数据
        self.original_folder = None
        self.no_subtitle_folder = None
        self.srt_folder = None

    def log(self, message):
        """添加日志"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def refresh_all(self):
        """刷新所有数据"""
        self.log("🔄 刷新数据...")
        self.video_tree.delete(*self.video_tree.get_children())
        self.srt_tree.delete(*self.srt_tree.get_children())
        self.video_data.clear()
        self.srt_data.clear()
        
        if self.folder_path_var.get():
            self.scan_folders()
        else:
            self.log("请先选择文件夹")
    
    def export_report(self):
        """导出检查报告"""
        if not self.video_data and not self.srt_data:
            messagebox.showwarning("警告", "没有可导出的数据")
            return
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"审片报告_{timestamp}.txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("="*60 + "\n")
                    f.write("短剧审片检查报告\n")
                    f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("="*60 + "\n\n")
                    
                    f.write(f"项目路径: {self.folder_path_var.get()}\n")
                    f.write(f"原片视频数量: {self.original_video_count_var.get()}\n")
                    f.write(f"无字幕视频数量: {self.no_subtitle_count_var.get()}\n")
                    f.write(f"SRT文件数量: {self.srt_count_var.get()}\n\n")
                    
                    f.write("-"*60 + "\n")
                    f.write("视频文件检查结果:\n")
                    f.write("-"*60 + "\n")
                    for item in self.video_tree.get_children():
                        values = self.video_tree.item(item)['values']
                        f.write(f"[{values[0]}] {values[1]}: {values[2]}\n")
                    
                    f.write("\n" + "-"*60 + "\n")
                    f.write("字幕文件检查结果:\n")
                    f.write("-"*60 + "\n")
                    for item in self.srt_tree.get_children():
                        values = self.srt_tree.item(item)['values']
                        problem = values[3] if len(values) > 3 else ""
                        f.write(f"[{values[0]}] {values[1]}: {values[2]} {problem}\n")
                
                self.log(f"✓ 报告已导出: {filename}")
                messagebox.showinfo("成功", f"报告已导出到:\n{filename}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")
                self.log(f"✗ 导出失败: {e}")

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path_var.set(folder_selected)
            self.log(f"已选择文件夹: {folder_selected}")
            # Reset fields
            self.original_video_count_var.set("0")
            self.no_subtitle_count_var.set("0")
            self.srt_count_var.set("0")
            self.original_folder = None
            self.no_subtitle_folder = None
            self.srt_folder = None
            self.scan_folders()

    def scan_folders(self):
        base_path = self.folder_path_var.get()
        if not base_path:
            self.log("错误: 请先选择一个文件夹。")
            return

        self.log("🔍 开始扫描子文件夹...")
        try:
            for item in os.listdir(base_path):
                full_path = os.path.join(base_path, item)
                if os.path.isdir(full_path):
                    if "原片" in item:
                        self.original_folder = full_path
                        self.log(f"✓ 找到原片文件夹: {item}")
                    elif "无字幕" in item:
                        self.no_subtitle_folder = full_path
                        self.log(f"✓ 找到无字幕视频文件夹: {item}")
                    elif "英语SRT终版" in item or "SRT" in item:
                        self.srt_folder = full_path
                        self.log(f"✓ 找到SRT文件夹: {item}")
            
            if not self.original_folder or not self.srt_folder:
                messagebox.showerror("错误", "未能找到必需的文件夹（原片、SRT）。请检查文件夹名称。")
                self.log("✗ 错误: 未能找到所有必需的文件夹。")
                return
            
            # 扫描并加载视频文件到表格
            self.load_video_files()
            
            # 扫描并加载字幕文件到表格
            self.load_srt_files()
            
            self.log("✓ 文件夹扫描完成\n")

        except Exception as e:
            messagebox.showerror("扫描错误", f"扫描文件夹时发生错误: {e}")
            self.log(f"✗ 错误: {e}")
    
    def load_video_files(self):
        """加载无字幕文件夹的视频到表格"""
        if not self.no_subtitle_folder:
            return
        
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv']
        self.video_data.clear()
        self.video_tree.delete(*self.video_tree.get_children())
        
        try:
            files = []
            for filename in os.listdir(self.no_subtitle_folder):
                full_path = os.path.join(self.no_subtitle_folder, filename)
                if os.path.isfile(full_path) and any(filename.lower().endswith(ext) for ext in video_extensions):
                    files.append((filename, full_path))
            
            # 按EP编号排序
            files.sort(key=lambda x: self.extract_ep_number(x[0]))
            
            for idx, (filename, full_path) in enumerate(files, 1):
                self.video_data.append({
                    'index': idx,
                    'name': filename,
                    'path': full_path,
                    'base_name': os.path.splitext(filename)[0],
                    'status': '待检查',
                    'has_subtitle': None,
                    'problems': []
                })
                
                # 插入到表格
                self.video_tree.insert("", tk.END, values=(idx, filename, "待检查", ""), tags=('pending',))
            
            self.no_subtitle_count_var.set(str(len(files)))
            self.log(f"  📹 加载了 {len(files)} 个无字幕视频文件")
            
        except Exception as e:
            self.log(f"✗ 加载视频文件失败: {e}")
    
    def load_srt_files(self):
        """加载字幕文件到表格"""
        if not self.srt_folder:
            return
        
        self.srt_data.clear()
        self.srt_tree.delete(*self.srt_tree.get_children())
        
        try:
            files = []
            for filename in os.listdir(self.srt_folder):
                full_path = os.path.join(self.srt_folder, filename)
                if os.path.isfile(full_path) and filename.lower().endswith('.srt'):
                    files.append((filename, full_path))
            
            # 按EP编号排序
            files.sort(key=lambda x: self.extract_ep_number(x[0]))
            
            for idx, (filename, full_path) in enumerate(files, 1):
                self.srt_data.append({
                    'index': idx,
                    'name': filename,
                    'path': full_path,
                    'base_name': os.path.splitext(filename)[0],
                    'status': '待检查',
                    'matched_video': None,
                    'problems': []
                })
                
                # 插入到表格
                self.srt_tree.insert("", tk.END, values=(idx, filename, "待检查", ""), tags=('pending',))
            
            self.srt_count_var.set(str(len(files)))
            self.log(f"  📝 加载了 {len(files)} 个字幕文件")
            
        except Exception as e:
            self.log(f"✗ 加载字幕文件失败: {e}")
    
    def extract_ep_number(self, filename):
        """提取EP编号用于排序"""
        match = re.search(r'EP\s*(\d+)', filename, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 999999  # 没有EP编号的放最后

    def count_original_videos(self):
        if not self.original_folder:
            return
        
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv']
        count = 0
        video_files = []
        other_files = []
        
        try:
            self.log("\n开始扫描原片文件夹...")
            all_files = os.listdir(self.original_folder)
            self.log(f"原片文件夹中共有 {len(all_files)} 个项目")
            
            for filename in all_files:
                full_path = os.path.join(self.original_folder, filename)
                if os.path.isfile(full_path):
                    if any(filename.lower().endswith(ext) for ext in video_extensions):
                        count += 1
                        video_files.append(filename)
                        self.log(f"  [视频 {count}] {filename}")
                    else:
                        other_files.append(filename)
            
            if other_files:
                self.log(f"\n忽略的非视频文件 ({len(other_files)} 个):")
                for f in other_files:
                    self.log(f"  - {f}")
            
            self.original_video_count_var.set(str(count))
            self.log(f"\n✓ 原片文件夹扫描完成: 共找到 {count} 个视频文件。")
        except Exception as e:
            messagebox.showerror("错误", f"读取原片文件夹时出错: {e}")
            self.log(f"错误: 读取原片文件夹时出错: {e}")

    def start_check(self):
        """基础检查：命名规范、数量、序列完整性"""
        self.log("\n" + "="*50)
        self.log("🔍 开始基础检查")
        self.log("="*50 + "\n")
        
        # 统计原片数量
        original_count = 0
        if self.original_folder and os.path.exists(self.original_folder):
            video_extensions = ('.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.m4v', '.rmvb')
            original_count = sum(1 for f in os.listdir(self.original_folder) 
                                if f.lower().endswith(video_extensions))
            self.original_video_count_var.set(str(original_count))
        
        self.log(f"📊 原片数量: {original_count} 个")
        
        # 加载文件到表格
        self.load_video_files()
        self.load_srt_files()
        
        if not self.video_data:
            messagebox.showwarning("警告", "未找到无字幕视频文件")
            return
        
        if not self.srt_data:
            messagebox.showwarning("警告", "未找到字幕文件")
            return
        
        # 检查视频文件
        self.log("\n📹 检查无字幕视频文件...")
        video_problems = self.check_video_naming_and_sequence()
        
        # 检查视频内容重复
        self.log("\n🔍 检查视频内容重复...")
        duplicate_problems = self.check_video_content_duplicates()
        video_problems.extend(duplicate_problems)
        
        # 检查字幕文件
        self.log("\n📝 检查字幕文件...")
        srt_problems = self.check_srt_naming_and_sequence()
        
        # 更新表格显示
        self.update_video_table_status()
        self.update_srt_table_status()
        
        # 显示汇总
        self.log("\n" + "="*50)
        self.log("📊 检查完成")
        self.log("="*50)
        
        total_problems = len(video_problems) + len(srt_problems)
        if total_problems == 0:
            self.log("✓ 所有基础检查通过！")
            messagebox.showinfo("检查完成", "✓ 所有基础检查通过！")
        else:
            self.log(f"⚠️ 发现 {total_problems} 个问题")
            messagebox.showwarning("发现问题", f"发现 {total_problems} 个问题\n请查看表格和日志")
    
    def check_video_naming_and_sequence(self):
        """检查无字幕视频命名和序列"""
        problems = []
        expected_count = len(self.video_data)
        ep_numbers = {}
        invalid_count = 0
        duplicate_count = 0
        
        self.log(f"  开始检查 {expected_count} 个视频文件的命名规范...")
        
        for video in self.video_data:
            base_name = video['base_name']  # 不含扩展名的文件名
            
            # 严格检查命名规范：必须是 EP + 纯数字（大小写EP都可以）
            # ^EP\d+$ 表示：开头EP，然后是一个或多个数字，然后结束
            match = re.match(r'^EP(\d+)$', base_name, re.IGNORECASE)
            
            if not match:
                invalid_count += 1
                video['status'] = '✗ 命名错误'
                video['problems'].append('文件名必须是 EP+数字 格式（如 EP1、EP2）')
                problems.append(f"{video['name']}: 命名不规范")
                
                # 详细说明错误原因
                if re.match(r'^ep\d+', base_name):  # 小写ep
                    self.log(f"  ✗ {video['name']}: 错误 - EP必须大写")
                elif re.match(r'^EP\d+.+', base_name):  # EP1后面有其他字符
                    self.log(f"  ✗ {video['name']}: 错误 - EP数字后不能有其他字符（如括号、下划线等）")
                elif 'EP' in base_name.upper():
                    self.log(f"  ✗ {video['name']}: 错误 - EP和数字之间不能有空格或其他字符")
                else:
                    self.log(f"  ✗ {video['name']}: 错误 - 文件名不符合 EP+数字 格式")
            else:
                ep_num = int(match.group(1))
                
                # 检查是否重复
                if ep_num in ep_numbers:
                    duplicate_count += 1
                    ep_numbers[ep_num].append(video['name'])
                    video['status'] = '✗ 重复编号'
                    video['problems'].append(f'EP{ep_num} 编号重复')
                    problems.append(f"{video['name']}: EP{ep_num}重复")
                    self.log(f"  ✗ {video['name']}: EP{ep_num} 编号重复")
                else:
                    ep_numbers[ep_num] = [video['name']]
                    if video['status'] == '待检查':
                        video['status'] = '✓ 通过'
                    self.log(f"  ✓ {video['name']}: 命名正确 (EP{ep_num})")
        
        # 检查序列完整性（缺少的集数）
        if ep_numbers:
            min_ep = min(ep_numbers.keys())
            max_ep = max(ep_numbers.keys())
            expected_eps = set(range(min_ep, max_ep + 1))
            actual_eps = set(ep_numbers.keys())
            missing = sorted(expected_eps - actual_eps)
            
            if missing:
                msg = f"缺少集数: EP{', EP'.join(map(str, missing))}"
                problems.append(msg)
                self.log(f"\n  ⚠️ {msg}")
        
        # 统计汇总
        valid_count = expected_count - invalid_count - duplicate_count
        self.log(f"\n  命名检查结果:")
        self.log(f"    ✓ 命名正确: {valid_count} 个")
        if invalid_count > 0:
            self.log(f"    ✗ 命名错误: {invalid_count} 个")
        if duplicate_count > 0:
            self.log(f"    ✗ 编号重复: {duplicate_count} 个")
        
        if not problems:
            self.log(f"  ✓ 所有视频文件命名规范检查通过")
        
        return problems
    
    def check_video_content_duplicates(self):
        """检查视频内容是否重复（通过MD5哈希值）"""
        problems = []
        
        if len(self.video_data) < 2:
            self.log("  ℹ️ 视频数量少于2个，跳过重复检查")
            return problems
        
        self.log(f"  🔄 正在计算 {len(self.video_data)} 个视频的MD5哈希值...")
        hash_dict = {}  # {hash: [video1, video2, ...]}
        
        for idx, video in enumerate(self.video_data, 1):
            try:
                # 计算MD5哈希值
                file_hash = self.calculate_file_md5(video['path'])
                video['md5'] = file_hash
                
                # 记录哈希值
                if file_hash in hash_dict:
                    hash_dict[file_hash].append(video)
                else:
                    hash_dict[file_hash] = [video]
                
                # 显示进度
                if idx % 5 == 0 or idx == len(self.video_data):
                    self.log(f"    进度: {idx}/{len(self.video_data)}")
                    
            except Exception as e:
                self.log(f"  ⚠️ 无法计算 {video['name']} 的哈希值: {e}")
        
        # 查找MD5完全相同的视频（内容100%一样）
        duplicate_groups = {h: vids for h, vids in hash_dict.items() if len(vids) > 1}
        
        if duplicate_groups:
            self.log(f"\n  ✗ 发现 {len(duplicate_groups)} 组内容完全相同的视频:")
            for hash_val, videos in duplicate_groups.items():
                self.log(f"\n    【内容重复组】以下 {len(videos)} 个视频内容完全相同:")
                
                # 获取所有视频名称，用于交叉引用
                video_names = [v['name'] for v in videos]
                
                for video in videos:
                    # 找出除了自己之外的其他视频
                    other_videos = [name for name in video_names if name != video['name']]
                    other_videos_str = ', '.join(other_videos)
                    
                    video['status'] = '✗ 内容重复'
                    video['problems'].append(f'内容与 {other_videos_str} 完全相同')
                    self.log(f"      • {video['name']} (与 {other_videos_str} 内容相同)")
                    problems.append(f"{video['name']}: 内容完全重复")
        else:
            self.log("  ✓ 未发现内容完全重复的视频")
        
        return problems
    
    def calculate_file_md5(self, filepath, chunk_size=8192):
        """计算文件的MD5哈希值"""
        md5_hash = hashlib.md5()
        
        with open(filepath, "rb") as f:
            # 分块读取，避免大文件占用过多内存
            while chunk := f.read(chunk_size):
                md5_hash.update(chunk)
        
        return md5_hash.hexdigest()
    
    def check_srt_naming_and_sequence(self):
        """检查字幕命名和序列"""
        problems = []
        expected_count = len(self.srt_data)
        ep_numbers = {}
        invalid_count = 0
        duplicate_count = 0
        
        self.log(f"  开始检查 {expected_count} 个字幕文件的命名规范...")
        
        for srt in self.srt_data:
            base_name = srt['base_name']  # 不含扩展名的文件名
            
            # 严格检查命名规范：必须是 EP + 纯数字（大小写EP都可以）
            match = re.match(r'^EP(\d+)$', base_name, re.IGNORECASE)
            
            if not match:
                invalid_count += 1
                srt['status'] = '✗ 命名错误'
                srt['problems'].append('文件名必须是 EP+数字 格式（如 EP1、EP2）')
                problems.append(f"{srt['name']}: 命名不规范")
                
                # 详细说明错误原因
                if re.match(r'^ep\d+', base_name):  # 小写ep
                    self.log(f"  ✗ {srt['name']}: 错误 - EP必须大写")
                elif re.match(r'^EP\d+.+', base_name):  # EP1后面有其他字符
                    self.log(f"  ✗ {srt['name']}: 错误 - EP数字后不能有其他字符（如括号、下划线等）")
                elif 'EP' in base_name.upper():
                    self.log(f"  ✗ {srt['name']}: 错误 - EP和数字之间不能有空格或其他字符")
                else:
                    self.log(f"  ✗ {srt['name']}: 错误 - 文件名不符合 EP+数字 格式")
            else:
                ep_num = int(match.group(1))
                
                # 检查是否重复
                if ep_num in ep_numbers:
                    duplicate_count += 1
                    ep_numbers[ep_num].append(srt['name'])
                    srt['status'] = '✗ 重复编号'
                    srt['problems'].append(f'EP{ep_num} 编号重复')
                    problems.append(f"{srt['name']}: EP{ep_num}重复")
                    self.log(f"  ✗ {srt['name']}: EP{ep_num} 编号重复")
                else:
                    ep_numbers[ep_num] = [srt['name']]
                    if srt['status'] == '待检查':
                        srt['status'] = '✓ 通过'
                    self.log(f"  ✓ {srt['name']}: 命名正确 (EP{ep_num})")
        
        # 检查序列完整性（缺少的集数）
        if ep_numbers:
            min_ep = min(ep_numbers.keys())
            max_ep = max(ep_numbers.keys())
            expected_eps = set(range(min_ep, max_ep + 1))
            actual_eps = set(ep_numbers.keys())
            missing = sorted(expected_eps - actual_eps)
            
            if missing:
                msg = f"缺少集数: EP{', EP'.join(map(str, missing))}"
                problems.append(msg)
                self.log(f"\n  ⚠️ {msg}")
        
        # 统计汇总
        valid_count = expected_count - invalid_count - duplicate_count
        self.log(f"\n  命名检查结果:")
        self.log(f"    ✓ 命名正确: {valid_count} 个")
        if invalid_count > 0:
            self.log(f"    ✗ 命名错误: {invalid_count} 个")
        if duplicate_count > 0:
            self.log(f"    ✗ 编号重复: {duplicate_count} 个")
        
        if not problems:
            self.log(f"  ✓ 所有字幕文件命名规范检查通过")
        
        return problems
    
    def update_video_table_status(self):
        """更新视频表格状态"""
        self.video_tree.delete(*self.video_tree.get_children())
        
        for video in self.video_data:
            status = video['status']
            problems_str = '; '.join(video['problems']) if video['problems'] else ''
            
            if '✓' in status or status == '通过':
                tag = 'pass'
            elif '命名错误' in status or '重复' in status:
                tag = 'fail'
            else:
                tag = 'warning'
            
            self.video_tree.insert("", tk.END, 
                                  values=(video['index'], video['name'], status, problems_str),
                                  tags=(tag,))
    
    def update_srt_table_status(self):
        """更新字幕表格状态"""
        self.srt_tree.delete(*self.srt_tree.get_children())
        
        for srt in self.srt_data:
            status = srt['status']
            problems = "; ".join(srt['problems']) if srt['problems'] else ""
            
            if '✓' in status or status == '通过':
                tag = 'pass'
            elif '命名错误' in status or '重复' in status or '找不到' in status:
                tag = 'fail'
            elif '乱序' in status or '超出' in status:
                tag = 'warning'
            else:
                tag = 'pending'
            
            self.srt_tree.insert("", tk.END,
                                values=(srt['index'], srt['name'], status, problems),
                                tags=(tag,))


    def check_files_in_folder(self, folder_path, expected_count, count_var, file_ext_filter=None):
        errors = []
        try:
            all_items = os.listdir(folder_path)
            files = [f for f in all_items if os.path.isfile(os.path.join(folder_path, f))]
            
            if file_ext_filter:
                filtered_files = [f for f in files if any(f.lower().endswith(ext) for ext in file_ext_filter)]
                ignored_files = [f for f in files if f not in filtered_files]
                files = filtered_files
                
                if ignored_files:
                    self.log(f"  忽略 {len(ignored_files)} 个非目标格式文件")
            
            count_var.set(str(len(files)))
            self.log(f"  文件夹中共有 {len(files)} 个文件")

            # 数量检查
            if len(files) != expected_count:
                errors.append(f"文件数量不匹配。应为 {expected_count}, 实际为 {len(files)}。")
                self.log(f"  ✗ 数量检查失败: 应为 {expected_count}, 实际为 {len(files)}")
            else:
                self.log(f"  ✓ 数量检查通过: {len(files)} 个文件")

            # 命名规范检查
            self.log(f"\n  开始检查文件命名规范...")
            ep_numbers = {}  # 改为字典，记录EP编号对应的文件名
            malformed_files = []

            for f in files:
                match = re.match(r'^EP(\d+)', f, re.IGNORECASE)
                if match:
                    ep_num = int(match.group(1))
                    if ep_num in ep_numbers:
                        ep_numbers[ep_num].append(f)
                    else:
                        ep_numbers[ep_num] = [f]
                    self.log(f"    [EP{ep_num}] {f}")
                else:
                    malformed_files.append(f)
                    self.log(f"    [命名错误] {f}")
            
            if malformed_files:
                errors.append(f"以下 {len(malformed_files)} 个文件命名不规范 (非'EP'开头): {', '.join(malformed_files)}")
                self.log(f"  ✗ 发现 {len(malformed_files)} 个命名不规范的文件")
            else:
                self.log(f"  ✓ 所有文件命名规范符合要求")

            # 序列完整性检查
            self.log(f"\n  开始检查EP序列完整性...")
            expected_set = set(range(1, expected_count + 1))
            actual_set = set(ep_numbers.keys())
            
            missing = sorted(list(expected_set - actual_set))
            if missing:
                errors.append(f"缺少以下集数: EP{', EP'.join(map(str, missing))}")
                self.log(f"  ✗ 缺少集数: EP{', EP'.join(map(str, missing))}")

            extra = sorted(list(actual_set - expected_set))
            if extra:
                errors.append(f"发现规定范围外的多余集数: EP{', EP'.join(map(str, extra))}")
                self.log(f"  ✗ 多余集数: EP{', EP'.join(map(str, extra))}")
            
            # 检查重复
            duplicates = {ep: files for ep, files in ep_numbers.items() if len(files) > 1}
            if duplicates:
                errors.append(f"发现重复的集数编号")
                self.log(f"  ✗ 发现重复的集数编号:")
                for ep, file_list in duplicates.items():
                    self.log(f"    EP{ep}: {', '.join(file_list)}")
            
            if not missing and not extra and not duplicates and not malformed_files:
                self.log(f"  ✓ EP序列完整且连续 (EP1 - EP{expected_count})")

        except Exception as e:
            errors.append(f"处理文件夹时发生错误: {e}")
            self.log(f"  ✗ 错误: {e}")
        
        return errors


    # ==================== 字幕深度检查功能 ====================
    
    def start_subtitle_deep_check(self):
        """开始字幕深度检查"""
        if pysrt is None:
            messagebox.showerror("错误", "未安装 pysrt 库，无法进行字幕检查。\n请运行: pip install pysrt")
            self.log("✗ 错误: 未安装 pysrt 库")
            return
        
        self.log("\n" + "="*50)
        self.log("🎯 开始字幕深度检查")
        self.log("="*50 + "\n")
        
        if not self.video_data or not self.srt_data:
            messagebox.showerror("错误", "请先选择文件夹并完成扫描")
            self.log("✗ 错误: 未找到视频或字幕文件")
            return
        
        # 1. 视频与字幕匹配检查
        self.log("【1/3】检查视频与字幕匹配...")
        self.check_matching_in_depth()
        
        # 2. 时间轴乱序检查
        self.log("\n【2/3】检查字幕时间轴乱序...")
        self.check_time_disorder_in_depth()
        
        # 3. 字幕超出视频时长检查
        self.log("\n【3/3】检查字幕超出视频时长...")
        self.check_duration_exceed_in_depth()
        
        # 更新表格
        self.update_video_table_status()
        self.update_srt_table_status()
        
        # 统计问题
        video_problems = sum(1 for v in self.video_data if v['problems'])
        srt_problems = sum(1 for s in self.srt_data if s['problems'])
        total_problems = video_problems + srt_problems
        
        # 汇总报告
        self.log("\n" + "="*50)
        self.log("📊 字幕深度检查完成")
        self.log("="*50)
        
        if total_problems == 0:
            self.log("🎉 所有检查项均通过！")
            messagebox.showinfo("检查完成", "字幕深度检查完成！\n\n✓ 所有检查项均通过！")
        else:
            self.log(f"⚠️ 共发现 {total_problems} 个问题")
            summary = f"字幕深度检查完成！\n\n发现问题：\n• 视频问题: {video_problems} 个\n• 字幕问题: {srt_problems} 个\n\n详情请查看表格"
            messagebox.showwarning("发现问题", summary)
    
    def check_matching_in_depth(self):
        """深度检查视频字幕匹配"""
        matched_count = 0
        unmatched_count = 0
        
        for video in self.video_data:
            matched_srt = self.find_matching_subtitle_data(video)
            
            if matched_srt:
                video['has_subtitle'] = True
                matched_srt['matched_video'] = video['name']
                matched_count += 1
                self.log(f"  ✓ {video['name']} ↔ {matched_srt['name']}")
            else:
                video['has_subtitle'] = False
                video['status'] = '✗ 缺少字幕'
                video['problems'].append('找不到对应的字幕文件')
                unmatched_count += 1
                self.log(f"  ✗ {video['name']}: 找不到对应字幕")
        
        # 统计
        self.log(f"\n  匹配结果: {matched_count} 个成功, {unmatched_count} 个失败")
        if unmatched_count == 0:
            self.log("  ✓ 所有视频都找到了对应的字幕")
        else:
            self.log(f"  ✗ {unmatched_count} 个视频找不到对应字幕")
    
    def check_time_disorder_in_depth(self):
        """深度检查时间轴乱序"""
        disorder_count = 0
        normal_count = 0
        error_count = 0
        
        for srt in self.srt_data:
            try:
                # 读取字幕文件
                try:
                    subs = pysrt.open(srt['path'], encoding='utf-8')
                except UnicodeDecodeError:
                    subs = pysrt.open(srt['path'], encoding='gbk')
                
                # 检查时间轴
                is_disorder, detail = self.check_time_order(subs)
                
                if is_disorder:
                    disorder_count += 1
                    srt['status'] = '⚠️ 时间轴乱序'
                    srt['problems'].append(f'时间轴乱序: {detail}')
                    self.log(f"  ✗ {srt['name']}: {detail}")
                else:
                    normal_count += 1
                    if not srt['problems']:  # 如果没有其他问题
                        srt['status'] = '✓ 通过'
                    self.log(f"  ✓ {srt['name']}: 时间轴正常")
                
            except Exception as e:
                error_count += 1
                srt['status'] = '✗ 读取失败'
                srt['problems'].append(f'无法读取: {str(e)}')
                self.log(f"  ⚠️ {srt['name']}: 无法读取文件")
        
        # 统计
        self.log(f"\n  检查结果: {normal_count} 个正常, {disorder_count} 个乱序, {error_count} 个错误")
        if disorder_count == 0 and error_count == 0:
            self.log("  ✓ 所有字幕时间轴正常")
        elif disorder_count > 0:
            self.log(f"  ✗ {disorder_count} 个字幕文件时间轴乱序")
    
    def check_duration_exceed_in_depth(self):
        """深度检查字幕时长（字幕不能比视频长）"""
        exceed_count = 0
        normal_count = 0
        skip_count = 0
        no_ffprobe = False
        
        for video in self.video_data:
            if not video.get('has_subtitle'):
                skip_count += 1
                continue
            
            # 找到对应的字幕
            matched_srt = self.find_matching_subtitle_data(video)
            if not matched_srt:
                skip_count += 1
                continue
            
            # 获取视频时长
            video_duration = self.get_video_duration_ffprobe(video['path'])
            if video_duration is None:
                no_ffprobe = True
                skip_count += 1
                self.log(f"  ⚠️ {video['name']}: 无法获取视频时长")
                continue
            
            try:
                # 读取字幕
                try:
                    subs = pysrt.open(matched_srt['path'], encoding='utf-8')
                except UnicodeDecodeError:
                    subs = pysrt.open(matched_srt['path'], encoding='gbk')
                
                # 检查最大结束时间
                if len(subs) > 0:
                    max_end_ms = max(
                        sub.end.hours * 3600000 + 
                        sub.end.minutes * 60000 + 
                        sub.end.seconds * 1000 + 
                        sub.end.milliseconds
                        for sub in subs
                    )
                    
                    srt_end_seconds = max_end_ms / 1000.0
                    time_diff = srt_end_seconds - video_duration
                    
                    if time_diff > 3.0:
                        exceed_count += 1
                        matched_srt['status'] = '⚠️ 超出时长'
                        matched_srt['problems'].append(f'超出视频时长 {time_diff:.2f}秒')
                        self.log(f"  ✗ {matched_srt['name']}: 字幕 {srt_end_seconds:.1f}秒 > 视频 {video_duration:.1f}秒 (超出 {time_diff:.2f}秒)")
                    else:
                        normal_count += 1
                        self.log(f"  ✓ {matched_srt['name']}: 时长正常 (字幕 {srt_end_seconds:.1f}秒 <= 视频 {video_duration:.1f}秒)")
            
            except Exception as e:
                skip_count += 1
                self.log(f"  ⚠️ {matched_srt['name']}: 检查失败 - {str(e)}")
        
        # 统计
        self.log(f"\n  检查结果: {normal_count} 个正常, {exceed_count} 个超出, {skip_count} 个跳过")
        
        if no_ffprobe:
            self.log("  ⚠️ 部分视频无法获取时长（需要安装ffprobe）")
        
        if exceed_count == 0 and skip_count == 0:
            self.log("  ✓ 所有字幕时长正常")
        elif exceed_count > 0:
            self.log(f"  ✗ {exceed_count} 个字幕文件超出对应视频时长")
    
    def find_matching_subtitle_data(self, video):
        """在srt_data中查找匹配的字幕"""
        video_base = video['base_name']
        
        # 1. 精确匹配
        for srt in self.srt_data:
            if srt['base_name'].lower() == video_base.lower():
                return srt
        
        # 2. EP模式匹配
        video_ep = re.search(r'EP\s*(\d+)', video_base, re.IGNORECASE)
        if video_ep:
            video_ep_num = int(video_ep.group(1))
            
            for srt in self.srt_data:
                srt_ep = re.search(r'EP\s*(\d+)', srt['base_name'], re.IGNORECASE)
                if srt_ep and int(srt_ep.group(1)) == video_ep_num:
                    return srt
        
        return None
    
    def check_time_order(self, subs):
        """检查字幕时间轴顺序"""
        if len(subs) <= 1:
            return False, ""
        
        for idx in range(1, len(subs)):
            prev_ms = (subs[idx-1].start.hours * 3600000 + 
                      subs[idx-1].start.minutes * 60000 + 
                      subs[idx-1].start.seconds * 1000 + 
                      subs[idx-1].start.milliseconds)
            
            curr_ms = (subs[idx].start.hours * 3600000 + 
                      subs[idx].start.minutes * 60000 + 
                      subs[idx].start.seconds * 1000 + 
                      subs[idx].start.milliseconds)
            
            if curr_ms < prev_ms:
                return True, f"第{idx}条早于第{idx+1}条"
        
        return False, ""
    
    def get_video_files_list(self):
        """获取视频文件列表"""
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv']
        videos = []
        
        try:
            for filename in os.listdir(self.original_folder):
                full_path = os.path.join(self.original_folder, filename)
                if os.path.isfile(full_path) and any(filename.lower().endswith(ext) for ext in video_extensions):
                    videos.append({
                        'name': filename,
                        'path': full_path,
                        'base_name': os.path.splitext(filename)[0]
                    })
        except Exception as e:
            self.log(f"错误: 读取视频文件列表失败: {e}")
        
        return videos
    
    def get_srt_files_list(self):
        """获取字幕文件列表"""
        srts = []
        
        try:
            for filename in os.listdir(self.srt_folder):
                full_path = os.path.join(self.srt_folder, filename)
                if os.path.isfile(full_path) and filename.lower().endswith('.srt'):
                    srts.append({
                        'name': filename,
                        'path': full_path,
                        'base_name': os.path.splitext(filename)[0]
                    })
        except Exception as e:
            self.log(f"错误: 读取字幕文件列表失败: {e}")
        
        return srts
    
    def find_matching_subtitle(self, video_info, srt_list):
        """查找匹配的字幕文件"""
        video_base = video_info['base_name']
        
        # 1. 精确匹配（文件名完全相同，忽略大小写）
        for srt in srt_list:
            if srt['base_name'].lower() == video_base.lower():
                return srt
        
        # 2. EP模式匹配（EP集数相同）
        video_ep_match = re.search(r'EP\s*(\d+)', video_base, re.IGNORECASE)
        if video_ep_match:
            video_ep_num = int(video_ep_match.group(1))
            
            for srt in srt_list:
                srt_ep_match = re.search(r'EP\s*(\d+)', srt['base_name'], re.IGNORECASE)
                if srt_ep_match and int(srt_ep_match.group(1)) == video_ep_num:
                    return srt
        
        return None
    
    def check_video_subtitle_matching(self):
        """检查视频与字幕匹配"""
        videos = self.get_video_files_list()
        srts = self.get_srt_files_list()
        
        unmatched = []
        
        for video in videos:
            matched_srt = self.find_matching_subtitle(video, srts)
            if not matched_srt:
                unmatched.append(video['name'])
                self.log(f"  ✗ 未找到字幕: {video['name']}")
        
        return unmatched
    
    def check_subtitle_time_disorder(self):
        """检查字幕时间轴乱序"""
        videos = self.get_video_files_list()
        srts = self.get_srt_files_list()
        
        problems = []
        
        for video in videos:
            matched_srt = self.find_matching_subtitle(video, srts)
            if not matched_srt:
                continue
            
            try:
                # 尝试用UTF-8打开
                try:
                    subs = pysrt.open(matched_srt['path'], encoding='utf-8')
                except UnicodeDecodeError:
                    # 失败则尝试GBK
                    subs = pysrt.open(matched_srt['path'], encoding='gbk')
                
                # 检查时间轴顺序
                if len(subs) > 1:
                    for idx in range(1, len(subs)):
                        prev_sub = subs[idx - 1]
                        curr_sub = subs[idx]
                        
                        prev_time_ms = (prev_sub.start.hours * 3600000 + 
                                       prev_sub.start.minutes * 60000 + 
                                       prev_sub.start.seconds * 1000 + 
                                       prev_sub.start.milliseconds)
                        curr_time_ms = (curr_sub.start.hours * 3600000 + 
                                       curr_sub.start.minutes * 60000 + 
                                       curr_sub.start.seconds * 1000 + 
                                       curr_sub.start.milliseconds)
                        
                        if curr_time_ms < prev_time_ms:
                            problems.append({
                                'file': matched_srt['name'],
                                'detail': f"第{idx}条字幕时间早于第{idx+1}条"
                            })
                            break
            
            except Exception as e:
                self.log(f"  ⚠️ 无法读取字幕: {matched_srt['name']} - {e}")
        
        return problems
    
    def get_video_duration_ffprobe(self, video_path):
        """使用ffprobe获取视频时长"""
        try:
            # 尝试使用ffprobe
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            process = subprocess.Popen(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                 '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                text=True, startupinfo=startupinfo)
            
            stdout, stderr = process.communicate(timeout=30)
            
            if process.returncode == 0 and stdout.strip():
                return float(stdout.strip())
        except:
            pass
        
        return None
    
    def check_subtitle_duration_exceed(self):
        """检查字幕超出视频时长"""
        videos = self.get_video_files_list()
        srts = self.get_srt_files_list()
        
        problems = []
        
        for video in videos:
            matched_srt = self.find_matching_subtitle(video, srts)
            if not matched_srt:
                continue
            
            # 获取视频时长
            video_duration = self.get_video_duration_ffprobe(video['path'])
            if video_duration is None:
                self.log(f"  ⚠️ 无法获取视频时长: {video['name']} (需要ffprobe)")
                continue
            
            try:
                # 读取字幕
                try:
                    subs = pysrt.open(matched_srt['path'], encoding='utf-8')
                except UnicodeDecodeError:
                    subs = pysrt.open(matched_srt['path'], encoding='gbk')
                
                # 找到最大结束时间
                if len(subs) > 0:
                    max_end_time_ms = 0
                    for sub in subs:
                        end_time_ms = (sub.end.hours * 3600000 + 
                                      sub.end.minutes * 60000 + 
                                      sub.end.seconds * 1000 + 
                                      sub.end.milliseconds)
                        if end_time_ms > max_end_time_ms:
                            max_end_time_ms = end_time_ms
                    
                    srt_end_time_seconds = max_end_time_ms / 1000.0
                    time_diff = srt_end_time_seconds - video_duration
                    
                    # 超出3秒才记录为问题
                    if time_diff > 3.0:
                        problems.append({
                            'file': matched_srt['name'],
                            'exceed': time_diff,
                            'video_duration': video_duration,
                            'srt_end': srt_end_time_seconds
                        })
            
            except Exception as e:
                self.log(f"  ⚠️ 无法检查字幕时长: {matched_srt['name']} - {e}")
        
        return problems


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoCheckerApp(root)
    root.mainloop()
