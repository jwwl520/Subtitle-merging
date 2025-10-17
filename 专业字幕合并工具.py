import os
import pysrt # type: ignore
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import threading
import time
from pathlib import Path
import re # 引入正则表达式库用于自然排序
import sys
import tempfile

class SubtitleMerger:
    def __init__(self, root):
        self.root = root
        self.root.title("字幕合并工具 - v2.2 (优化文件夹数字排序) - by 不是绅士")
        self.root.geometry("1000x1100")  # 增加高度给日志更多空间
        self.root.resizable(True, True)
        self.root.configure()  # 使用默认背景

        # 初始化ffprobe路径
        self.ffprobe_path = self._get_ffprobe_path()

        self.style = ttk.Style()
        # 使用默认主题，不进行自定义样式配置

        self.main_frame = ttk.Frame(self.root, padding="15")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.create_path_section()
        self.create_info_section()
        self.create_options_section()
        self.create_file_list_and_log_section()  # 合并文件列表和日志区域
        self.create_action_section()
        self.create_status_bar()

        # 在启动时显示欢迎信息
        self.log_message("字幕合并工具启动成功！")
        
        # 检查并显示ffprobe状态
        if self.ffprobe_path:
            if getattr(sys, 'frozen', False) and self.ffprobe_path.endswith('ffprobe.exe'):
                self.log_message("✓ 使用内置的ffprobe.exe")
            elif self.ffprobe_path == 'ffprobe':
                self.log_message("✓ 使用系统PATH中的ffprobe")
            else:
                self.log_message(f"✓ 使用本地ffprobe.exe: {self.ffprobe_path}")
        else:
            self.log_message("⚠ 警告：未找到ffprobe.exe，视频时长功能将不可用")
        
        self.log_message("请按以下步骤操作：")
        self.log_message("1. 选择视频文件夹")
        self.log_message("2. 选择字幕文件夹") 
        self.log_message("3. 选择输出文件路径")
        self.log_message("4. 等待自动扫描完成后选择合并方式：")
        self.log_message("   • 使用预设的1-20集或后5集合并")
        self.log_message("   • 或使用自定义范围合并功能指定任意集数范围")

        # (filename, full_path, relative_subfolder, base_name_for_matching)
        self.video_files_data = [] 
        self.srt_files_data = []   
        self.folder_durations = {}
        self.total_duration_seconds = 0.0
        self.processing = False
        self.auto_scan_scheduled = False  # 防止重复自动扫描的标志

    def get_base_filename(self, filename_with_ext):
        """获取不带后缀的文件主名，用于匹配"""
        return os.path.splitext(filename_with_ext)[0]

    def natural_sort_key_for_filename(self, filename_str):
        """针对纯文件名的自然排序键函数"""
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split('([0-9]+)', filename_str)]
    
    def smart_folder_sort_key(self, folder_name):
        """智能文件夹排序键函数，专门处理包含数字范围的文件夹名称"""
        # 寻找文件夹名中的数字范围模式，如 "1-30", "31-61" 等
        range_pattern = r'(\d+)-(\d+)'
        range_matches = re.findall(range_pattern, folder_name)
        
        if range_matches:
            # 如果找到数字范围，使用第一个数字作为主要排序键
            first_number = int(range_matches[0][0])
            # 为了处理重叠范围，也考虑结束数字
            last_number = int(range_matches[0][1])
            # 使用起始数字作为主排序键，结束数字作为次排序键
            return (first_number, last_number, folder_name.lower())
        else:
            # 如果没有找到范围，寻找单独的数字
            numbers = re.findall(r'\d+', folder_name)
            if numbers:
                # 使用第一个找到的数字作为排序键
                first_number = int(numbers[0])
                return (first_number, 0, folder_name.lower())
            else:
                # 如果没有数字，使用字母排序，但排在有数字的后面
                return (float('inf'), 0, folder_name.lower())

    def create_path_section(self):
        path_frame = ttk.LabelFrame(self.main_frame, text="路径设置", padding="15")
        path_frame.pack(fill=tk.X, pady=(0,10))
        ttk.Label(path_frame, text="视频文件夹:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.video_folder_entry = ttk.Entry(path_frame, width=70)
        self.video_folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(path_frame, text="选择", command=self.select_video_folder).grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(path_frame, text="字幕文件夹:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.srt_folder_entry = ttk.Entry(path_frame, width=70)
        self.srt_folder_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(path_frame, text="选择", command=self.select_srt_folder).grid(row=1, column=2, padx=5, pady=5)
        ttk.Label(path_frame, text="输出字幕文件:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.output_file_entry = ttk.Entry(path_frame, width=70)
        self.output_file_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(path_frame, text="选择", command=self.select_output_file).grid(row=2, column=2, padx=5, pady=5)
        path_frame.columnconfigure(1, weight=1)

    def create_info_section(self):
        info_outer_frame = ttk.LabelFrame(self.main_frame, text="文件信息", padding="15")
        info_outer_frame.pack(fill=tk.X, pady=(0,10))
        info_outer_frame.columnconfigure(0, weight=1)
        # 将所有统计信息放在一行
        stats_frame = ttk.Frame(info_outer_frame)
        stats_frame.grid(row=0, column=0, sticky=tk.EW, pady=(0,10))
        stats_frame.columnconfigure(6, weight=1)
        self.video_count_label = ttk.Label(stats_frame, text="视频文件总数: 0"); self.video_count_label.grid(row=0, column=0, sticky=tk.W, padx=(0,20))
        self.srt_count_label = ttk.Label(stats_frame, text="字幕文件总数: 0"); self.srt_count_label.grid(row=0, column=1, sticky=tk.W, padx=(0,20))
        self.total_duration_label = ttk.Label(stats_frame, text="视频总时长: 00:00:00"); self.total_duration_label.grid(row=0, column=2, sticky=tk.W, padx=(0,20))
        folder_duration_frame = ttk.Frame(info_outer_frame); folder_duration_frame.grid(row=1, column=0, sticky=tk.EW, pady=(5,0)); folder_duration_frame.columnconfigure(0, weight=1)
        ttk.Label(folder_duration_frame, text="各文件夹视频时长:").pack(anchor=tk.W, pady=(0,2))
        columns = ("文件夹名", "总时长"); self.folder_duration_tree = ttk.Treeview(folder_duration_frame, columns=columns, show="headings", height=3)
        self.folder_duration_tree.heading("文件夹名", text="子文件夹"); self.folder_duration_tree.heading("总时长", text="总时长")
        self.folder_duration_tree.column("文件夹名", width=450, anchor="w"); self.folder_duration_tree.column("总时长", width=120, anchor="center")
        folder_scrollbar_y = ttk.Scrollbar(folder_duration_frame, orient="vertical", command=self.folder_duration_tree.yview)
        self.folder_duration_tree.configure(yscrollcommand=folder_scrollbar_y.set)
        folder_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y); self.folder_duration_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def create_options_section(self):
        options_frame = ttk.LabelFrame(self.main_frame, text="合并选项", padding="15")
        options_frame.pack(fill=tk.X, pady=(0,10))
        
        # 第一行：字幕合并选项
        merge_frame = ttk.Frame(options_frame)
        merge_frame.pack(fill=tk.X, pady=(0,10))
        
        # 合并全部按钮
        self.merge_all_button = ttk.Button(merge_frame, text="🚀 合并全部字幕", 
                                          command=self.start_merge_all, 
                                          width=18, state=tk.DISABLED,
                                          style='Accent.TButton')
        self.merge_all_button.grid(row=0, column=0, padx=15, pady=10, sticky=tk.W)
        
        # 自定义合并范围
        ttk.Label(merge_frame, text="自定义合并:", 
                 font=('Microsoft YaHei UI', 10, 'bold')).grid(row=0, column=1, padx=15, pady=10, sticky=tk.W)
        
        ttk.Label(merge_frame, text="起始:").grid(row=0, column=2, padx=(5,2), pady=10, sticky=tk.W)
        self.custom_start_entry = ttk.Entry(merge_frame, width=6)
        self.custom_start_entry.grid(row=0, column=3, padx=2, pady=10)
        self.custom_start_entry.insert(0, "1")  # 默认起始为1
        
        ttk.Label(merge_frame, text="结束:").grid(row=0, column=4, padx=(5,2), pady=10, sticky=tk.W)
        self.custom_end_entry = ttk.Entry(merge_frame, width=6)
        self.custom_end_entry.grid(row=0, column=5, padx=2, pady=10)
        self.custom_end_entry.insert(0, "0")  # 0表示自动使用全部
        
        # 自定义合并按钮
        self.custom_merge_button = ttk.Button(merge_frame, text="开始自定义合并",
                                             command=self.start_custom_merge,
                                             width=15, state=tk.DISABLED)
        self.custom_merge_button.grid(row=0, column=6, padx=10, pady=10, sticky=tk.W)
        
        # 视频总数显示标签
        self.total_videos_label = ttk.Label(merge_frame, text="(共0个视频)")
        self.total_videos_label.grid(row=0, column=7, padx=5, pady=10, sticky=tk.W)
        
        # 配置网格权重
        merge_frame.columnconfigure(8, weight=1)
        
        # 第二行：其他选项
        options_frame2 = ttk.Frame(options_frame); options_frame2.pack(fill=tk.X, pady=(10,0))
        self.auto_sort_var = tk.BooleanVar(value=True) # 默认启用智能排序
        ttk.Checkbutton(options_frame2, text="智能数字排序文件", variable=self.auto_sort_var).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame2, text="合并前备份原文件", variable=self.backup_var).grid(row=0, column=1, padx=(20,5), pady=5, sticky=tk.W)
        self.auto_suffix_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame2, text="自动添加集数后缀", variable=self.auto_suffix_var).grid(row=0, column=2, padx=(20,5), pady=5, sticky=tk.W)
        options_frame2.columnconfigure(3, weight=1)

    def _get_ffprobe_path(self):
        """获取ffprobe.exe的路径"""
        # 1. 首先尝试从打包的资源中获取
        if getattr(sys, 'frozen', False):
            # 运行在PyInstaller打包的exe中
            bundle_dir = sys._MEIPASS
            ffprobe_path = os.path.join(bundle_dir, 'ffprobe.exe')
            if os.path.exists(ffprobe_path):
                return ffprobe_path
        
        # 2. 尝试在当前目录查找
        current_dir_ffprobe = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffprobe.exe')
        if os.path.exists(current_dir_ffprobe):
            return current_dir_ffprobe
        
        # 3. 检查系统PATH中是否有ffprobe
        try:
            subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
            return 'ffprobe'
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # 4. 如果都没有找到，返回None
        return None


    def create_file_list_and_log_section(self):
        # 创建水平布局的容器
        horizontal_frame = ttk.Frame(self.main_frame)
        horizontal_frame.pack(fill=tk.BOTH, expand=True, pady=(0,10))
        
        # 左侧：文件列表
        files_frame = ttk.LabelFrame(horizontal_frame, text="文件列表 (按全局智能数字顺序)", padding="15")
        files_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0,5))
        files_frame.configure(width=400)  # 设置固定宽度
        
        self.tab_control = ttk.Notebook(files_frame)
        
        # 视频文件标签页（第一个标签页）
        video_tab = ttk.Frame(self.tab_control)
        video_frame_inner = ttk.Frame(video_tab)
        video_frame_inner.pack(fill=tk.BOTH, expand=True)
        columns_video = ("序号", "文件名", "帧数", "时长") # 增加帧数列
        self.video_tree = ttk.Treeview(video_frame_inner, columns=columns_video, show="headings", height=8)
        self.video_tree.heading("序号", text="全局序"); self.video_tree.heading("文件名", text="文件名")
        self.video_tree.heading("帧数", text="帧数"); self.video_tree.heading("时长", text="时长")
        self.video_tree.column("序号", width=60, anchor="center", stretch=tk.NO); self.video_tree.column("文件名", width=200, anchor="w")  # 减小文件名宽度
        self.video_tree.column("帧数", width=80, anchor="center", stretch=tk.NO); self.video_tree.column("时长", width=100, anchor="center", stretch=tk.NO)
        video_scrollbar_y = ttk.Scrollbar(video_frame_inner, orient="vertical", command=self.video_tree.yview)
        self.video_tree.configure(yscrollcommand=video_scrollbar_y.set)
        video_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y); self.video_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # 添加视频文件标签页为第一个
        self.tab_control.add(video_tab, text="视频文件")

        # 字幕文件标签页（第二个标签页）
        srt_tab = ttk.Frame(self.tab_control)
        srt_frame_inner = ttk.Frame(srt_tab)
        srt_frame_inner.pack(fill=tk.BOTH, expand=True)
        columns_srt = ("序号", "文件名") # 删除"所在完整路径"列
        self.srt_tree = ttk.Treeview(srt_frame_inner, columns=columns_srt, show="headings", height=8)
        self.srt_tree.heading("序号", text="全局序"); self.srt_tree.heading("文件名", text="文件名")
        self.srt_tree.column("序号", width=60, anchor="center", stretch=tk.NO); self.srt_tree.column("文件名", width=380, anchor="w")
        srt_scrollbar_y = ttk.Scrollbar(srt_frame_inner, orient="vertical", command=self.srt_tree.yview)
        self.srt_tree.configure(yscrollcommand=srt_scrollbar_y.set)
        srt_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y); self.srt_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # 添加字幕文件标签页为第二个
        self.tab_control.add(srt_tab, text="字幕文件")
        
        # 显示Notebook并默认选中第一个标签页（视频文件）
        self.tab_control.pack(fill=tk.BOTH, expand=True, pady=5)
        self.tab_control.select(0)  # 确保默认选中第一个标签页（视频文件）
        
        # 右侧：日志区域
        log_frame = ttk.LabelFrame(horizontal_frame, text="处理日志", padding="15")
        log_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5,0))
        
        # 确保日志文本框有足够的最小高度
        self.log_text = ScrolledText(log_frame, width=50, height=20, wrap=tk.WORD, 
                                   font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)


    def create_action_section(self):
        action_frame = ttk.Frame(self.main_frame, padding=(0, 5, 0, 0)); action_frame.pack(fill=tk.X, pady=(5,0))
        self.progress = ttk.Progressbar(action_frame, orient="horizontal", length=500, mode="determinate"); self.progress.pack(side=tk.LEFT, padx=(0,10), fill=tk.X, expand=True)
        self.clear_button = ttk.Button(action_frame, text="清空日志", command=self.clear_log); self.clear_button.pack(side=tk.RIGHT, padx=5)
        self.reset_button = ttk.Button(action_frame, text="🔄 重置", command=self.reset_all); self.reset_button.pack(side=tk.RIGHT, padx=5)

    def create_status_bar(self):
        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.FLAT, anchor=tk.W, padding=(10,5))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def start_merge_all(self):
        """合并全部字幕"""
        if self.processing: 
            messagebox.showinfo("提示", "处理中..."); 
            return
        output_path = self.output_file_entry.get().strip()
        if not output_path: 
            messagebox.showwarning("警告", "请选择输出路径."); 
            return
        if not self.video_files_data: 
            messagebox.showwarning("警告", "无视频文件."); 
            return
        
        total_videos = len(self.video_files_data)
        
        # 确认合并全部
        result = messagebox.askyesno("确认合并全部", 
            f"确定要合并全部字幕吗？\n\n详细信息：\n• 共{total_videos}个视频文件\n• 起始集数：第1集\n• 结束集数：第{total_videos}集")
        
        if result:
            self.log_message(f"开始合并全部字幕（第1-{total_videos}集）...")
            self.merge_all_button.config(state=tk.DISABLED)
            self.custom_merge_button.config(state=tk.DISABLED)
            threading.Thread(target=self._merge_srt_files_thread, args=(output_path, 1, total_videos, True), daemon=True).start()

    def start_custom_merge(self):
        """自定义范围合并"""
        if self.processing: 
            messagebox.showinfo("提示", "处理中..."); 
            return
        output_path = self.output_file_entry.get().strip()
        if not output_path: 
            messagebox.showwarning("警告", "请选择输出路径."); 
            return
        if not self.video_files_data: 
            messagebox.showwarning("警告", "无视频文件."); 
            return
        
        # 获取自定义范围
        try:
            custom_start_text = self.custom_start_entry.get().strip()
            custom_end_text = self.custom_end_entry.get().strip()
            
            custom_start = int(custom_start_text) if custom_start_text else 1
            custom_end = int(custom_end_text) if custom_end_text and custom_end_text != "0" else len(self.video_files_data)
            
            # 验证自定义范围
            total_videos = len(self.video_files_data)
            if custom_start <= 0:
                messagebox.showwarning("警告", "起始集数必须大于0！")
                return
            
            if custom_end > total_videos:
                messagebox.showwarning("警告", f"结束集数不能超过视频总数！当前共有{total_videos}个视频文件。")
                return
            
            if custom_start > custom_end:
                messagebox.showwarning("警告", "起始集数不能大于结束集数！")
                return
            
            # 确认自定义合并
            result = messagebox.askyesno("确认自定义合并", 
                f"确定要合并第{custom_start}-{custom_end}集吗？\n\n详细信息：\n• 共{custom_end-custom_start+1}个文件\n• 起始集数：第{custom_start}集\n• 结束集数：第{custom_end}集\n• 视频总数：{total_videos}个")
            
            if result:
                # 执行自定义合并
                self.log_message(f"开始自定义合并第{custom_start}-{custom_end}集...")
                self.merge_all_button.config(state=tk.DISABLED)
                self.custom_merge_button.config(state=tk.DISABLED)
                threading.Thread(target=self._merge_srt_files_thread, args=(output_path, custom_start, custom_end, True), daemon=True).start()
                
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的数字！")


    def update_button_states(self):
        """更新按钮状态"""
        total_videos = len(self.video_files_data)
        
        # 更新视频总数显示
        self.total_videos_label.config(text=f"(共{total_videos}个视频)")
        
        # 启用或禁用按钮
        if total_videos > 0:
            self.merge_all_button.config(state=tk.NORMAL)
            self.custom_merge_button.config(state=tk.NORMAL)
        else:
            self.merge_all_button.config(state=tk.DISABLED)
            self.custom_merge_button.config(state=tk.DISABLED)

    def generate_output_filename_with_suffix(self, original_path, start_episode, end_episode):
        """生成带集数后缀的输出文件名"""
        if not self.auto_suffix_var.get():
            return original_path
            
        path_obj = Path(original_path)
        name_without_ext = path_obj.stem
        extension = path_obj.suffix
        directory = path_obj.parent
        
        # 生成集数后缀
        suffix = f"{start_episode}-{end_episode}"
        new_name = f"{name_without_ext}{suffix}{extension}"
        
        return str(directory / new_name)

    def select_video_folder(self):
        video_folder = filedialog.askdirectory(title="选择视频文件夹")
        if video_folder: self.video_folder_entry.delete(0, tk.END); self.video_folder_entry.insert(0, video_folder); self.update_file_lists()

    def select_srt_folder(self):
        srt_folder = filedialog.askdirectory(title="选择字幕文件夹")
        if srt_folder: self.srt_folder_entry.delete(0, tk.END); self.srt_folder_entry.insert(0, srt_folder); self.update_file_lists()

    def select_output_file(self):
        output_file = filedialog.asksaveasfilename(defaultextension=".srt", filetypes=[("SRT 文件", "*.srt")], title="保存合并后的字幕文件")
        if output_file: self.output_file_entry.delete(0, tk.END); self.output_file_entry.insert(0, output_file)

    def update_file_lists(self):
        self.log_message("正在扫描文件...")
        # 重置自动扫描标志，允许新的扫描
        self.auto_scan_scheduled = False
        for tree in [self.video_tree, self.srt_tree, self.folder_duration_tree]: tree.delete(*tree.get_children())
        self.video_files_data, self.srt_files_data, self.folder_durations = [], [], {}
        self.total_duration_seconds = 0.0
        self.total_duration_label.config(text="视频总时长: 00:00:00")
        self.video_count_label.config(text="视频文件总数: 0"); self.srt_count_label.config(text="字幕文件总数: 0")

        video_root_dir, srt_root_dir = self.video_folder_entry.get().strip(), self.srt_folder_entry.get().strip()
        
        # --- 扫描和初步收集文件 ---
        raw_video_files, raw_srt_files = [], []
        if os.path.isdir(video_root_dir):
            for dirpath, _, filenames in os.walk(video_root_dir):
                for f in filenames:
                    if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv')):
                        # 使用列表，包含：[文件名, 完整路径, 基础名, 时长(秒), 帧数, 帧率]
                        raw_video_files.append([f, os.path.join(dirpath, f), self.get_base_filename(f), 0.0, 0, 0.0])
        
        if os.path.isdir(srt_root_dir):
            for dirpath, _, filenames in os.walk(srt_root_dir):
                for f in filenames:
                    if f.lower().endswith('.srt'):
                        raw_srt_files.append((f, os.path.join(dirpath, f), self.get_base_filename(f)))

        # --- 全局自然排序 ---
        if self.auto_sort_var.get():
            raw_video_files.sort(key=lambda x: self.natural_sort_key_for_filename(x[0]))
            raw_srt_files.sort(key=lambda x: self.natural_sort_key_for_filename(x[0]))
        else: # 传统字典序 (如果用户取消勾选)
            raw_video_files.sort(key=lambda x: x[0].lower())
            raw_srt_files.sort(key=lambda x: x[0].lower())
            
        self.video_files_data = raw_video_files
        self.srt_files_data = raw_srt_files

        # --- 更新UI列表 ---
        self.video_count_label.config(text=f"视频文件总数: {len(self.video_files_data)}")
        for i, video_item in enumerate(self.video_files_data):
            name = video_item[0]
            self.video_tree.insert("", tk.END, values=(i+1, name, "待扫描", "待扫描"))  # 添加帧数列
            
        self.srt_count_label.config(text=f"字幕文件总数: {len(self.srt_files_data)}")
        for i, (name, full_path, _) in enumerate(self.srt_files_data):
            self.srt_tree.insert("", tk.END, values=(i+1, name))

        if not self.video_files_data and os.path.isdir(video_root_dir): self.log_message("未在视频目录找到支持的视频文件。")
        if not self.srt_files_data and os.path.isdir(srt_root_dir): self.log_message("未在字幕目录找到SRT文件。")
        if self.video_files_data or self.srt_files_data: self.log_message("文件扫描完成。")
        
        # 更新按钮状态
        self.update_button_states()
        
        # 检查是否应该进行自动扫描（仅在两个目录都有内容时进行）
        self.check_and_start_auto_scan()

    def check_and_start_auto_scan(self):
        """检查条件并启动自动扫描"""
        video_folder = self.video_folder_entry.get().strip()
        srt_folder = self.srt_folder_entry.get().strip()
        
        # 条件：有视频文件 且 (有字幕文件 或 至少设置了字幕文件夹路径)
        should_scan = (
            self.video_files_data and  # 有视频文件
            (self.srt_files_data or srt_folder) and  # 有字幕文件或至少设置了字幕文件夹
            not self.auto_scan_scheduled  # 未安排过自动扫描
        )
        
        if should_scan:
            self.auto_scan_scheduled = True
            self.log_message("检测到视频和字幕文件夹都已设置，开始自动扫描时长...")
            threading.Thread(target=self._scan_video_duration_thread, daemon=True).start()
        else:
            self.status_bar.config(text="文件列表已更新。")

    def _scan_video_duration_thread(self):
        self.log_message("开始扫描视频时长...")
        self.status_bar.config(text="正在扫描视频时长..."); self.root.update_idletasks()
        self.total_duration_seconds = 0.0; self.folder_durations.clear(); self.folder_duration_tree.delete(*self.folder_duration_tree.get_children())
        total_files_to_scan = len(self.video_files_data); self.progress["maximum"] = total_files_to_scan; self.progress["value"] = 0
        
        video_tree_items = self.video_tree.get_children() # 获取treeview中的item ID列表

        for i, video_data_item in enumerate(self.video_files_data): # 遍历已排序的数据列表
            video_name = video_data_item[0]
            video_full_path = video_data_item[1]
            # 假设 self.video_files_data 和 video_tree_items 顺序一致
            tree_item_id = video_tree_items[i] if i < len(video_tree_items) else None

            video_root_dir = Path(self.video_folder_entry.get().strip())
            try:
                relative_folder = str(Path(os.path.dirname(video_full_path)).relative_to(video_root_dir))
                if relative_folder == ".": relative_folder = "根目录"
            except ValueError:
                relative_folder = Path(os.path.dirname(video_full_path)).name # Fallback

            try:
                # 获取基于帧的精确信息
                total_frames, fps_decimal, duration = self.get_video_frame_info_ffprobe(video_full_path)
                
                if total_frames is not None and fps_decimal is not None and duration is not None:
                    # 存储完整信息：[文件名, 路径, 基础名, 时长, 帧数, 帧率]
                    video_data_item[3] = duration
                    video_data_item[4] = total_frames
                    video_data_item[5] = fps_decimal
                    
                    self.total_duration_seconds += duration
                    self.folder_durations[relative_folder] = self.folder_durations.get(relative_folder, 0.0) + duration
                    
                    formatted_duration = self.format_duration(duration)
                    framerate_display = f"{total_frames}f@{fps_decimal:.2f}fps"
                    
                    if tree_item_id:
                        current_values = list(self.video_tree.item(tree_item_id, 'values'))
                        current_values[2] = framerate_display  # 帧数和帧率
                        current_values[3] = formatted_duration  # 时长
                        self.video_tree.item(tree_item_id, values=tuple(current_values))
                    
                    self.log_message(f"[{i+1}/{total_files_to_scan}] {relative_folder}/{video_name}: {formatted_duration} ({framerate_display})")
                else:
                    # 回退到旧方法
                    duration = self.get_video_duration_ffprobe(video_full_path)
                    framerate = self.get_video_framerate_ffprobe(video_full_path)
                    video_data_item[3] = duration
                    self.total_duration_seconds += duration
                    self.folder_durations[relative_folder] = self.folder_durations.get(relative_folder, 0.0) + duration
                    formatted_duration = self.format_duration(duration)
                    if tree_item_id:
                        current_values = list(self.video_tree.item(tree_item_id, 'values'))
                        current_values[2] = framerate
                        current_values[3] = formatted_duration
                        self.video_tree.item(tree_item_id, values=tuple(current_values))
                    self.log_message(f"[{i+1}/{total_files_to_scan}] {relative_folder}/{video_name}: {formatted_duration} ({framerate})")
            except Exception as e:
                self.log_message(f"扫描 {video_name} 出错: {str(e)}")
                if tree_item_id:
                    current_values = list(self.video_tree.item(tree_item_id, 'values'))
                    current_values[2] = "错误"  # 帧数列
                    current_values[3] = "错误"  # 时长列
                    self.video_tree.item(tree_item_id, values=tuple(current_values))
            finally:
                self.progress["value"] = i + 1
                self.root.after(0, self.root.update_idletasks)
        
        self.total_duration_label.config(text=f"视频总时长: {self.format_duration(self.total_duration_seconds)}")
        # 使用智能排序来显示文件夹时长，按数字大小排序
        sorted_folders = sorted(self.folder_durations.items(), key=lambda x: self.smart_folder_sort_key(x[0]))
        for folder, dur_sec in sorted_folders: 
            self.folder_duration_tree.insert("", tk.END, values=(folder, self.format_duration(dur_sec)))
        self.log_message(f"扫描完成！视频总时长: {self.format_duration(self.total_duration_seconds)}")
        if self.folder_durations: self.log_message("各文件夹时长已更新。")
        
        # 扫描完成后，如果启用了"自动识别后5个"，重新计算集数范围
        # if hasattr(self, 'auto_last5_var') and self.auto_last5_var.get():
        #     self.root.after(0, self.on_auto_last5_changed)
        
        # 扫描完成后，更新按钮状态
        self.root.after(0, self.update_button_states)
        
        # 重置自动扫描标志，允许下次重新选择文件夹时再次自动扫描
        self.auto_scan_scheduled = False
        
        # 扫描完成后立即检查字幕文件问题
        self.root.after(0, self.check_subtitle_problems_after_scan)
            
        self.status_bar.config(text="视频时长扫描完成。"); self.progress["value"] = 0; self.root.after(0, self.root.update_idletasks)

    def check_subtitle_problems_after_scan(self):
        """扫描完成后检查字幕文件问题并弹窗提醒"""
        if not self.video_files_data or not self.srt_files_data:
            return
        
        self.log_message("开始检查字幕文件问题...")
        
        time_disorder_subtitles = []
        large_time_diff_subtitles = []
        
        # 遍历所有字幕文件进行检查
        for srt_idx, (srt_name, srt_full_path, srt_base_name) in enumerate(self.srt_files_data):
            # 尝试匹配对应的视频
            matched_video_data = None
            video_idx = -1
            
            # 精确匹配
            for v_idx, video_data_item in enumerate(self.video_files_data):
                video_base_name = video_data_item[2]
                if srt_base_name.lower() == video_base_name.lower():
                    matched_video_data = video_data_item
                    video_idx = v_idx
                    break
            
            # EP模式匹配
            if not matched_video_data:
                srt_ep_match = re.search(r'EP\s*(\d+)', srt_base_name, re.IGNORECASE)
                if srt_ep_match:
                    srt_ep_num = int(srt_ep_match.group(1))
                    for v_idx, video_data_item in enumerate(self.video_files_data):
                        video_name = video_data_item[0]
                        video_ep_match = re.search(r'EP\s*(\d+)', video_name, re.IGNORECASE)
                        if video_ep_match and int(video_ep_match.group(1)) == srt_ep_num:
                            matched_video_data = video_data_item
                            video_idx = v_idx
                            break
            
            if not matched_video_data:
                continue
            
            video_name = matched_video_data[0]
            video_duration_seconds = matched_video_data[3]
            
            # 检查字幕文件
            try:
                subs = pysrt.open(srt_full_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    subs = pysrt.open(srt_full_path, encoding='gbk')
                except:
                    continue
            except:
                continue
            
            # 检查时间轴乱序
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
                        regression_details = f"第{idx}条 ({self.format_duration(curr_time_ms/1000)}) < 第{idx+1}条 ({self.format_duration(prev_time_ms/1000)})"
                        disorder_info = {
                            'video_name': video_name,
                            'srt_name': srt_name,
                            'episode_num': video_idx + 1,  # 序号
                            'episode_display': srt_name,  # 显示文件名
                            'details': regression_details
                        }
                        time_disorder_subtitles.append(disorder_info)
                        break
            
            # 检查字幕超出视频时长
            if len(subs) > 0 and video_duration_seconds > 0:
                max_end_time_ms = 0
                for sub in subs:
                    end_time_ms = (sub.end.hours * 3600000 + 
                                  sub.end.minutes * 60000 + 
                                  sub.end.seconds * 1000 + 
                                  sub.end.milliseconds)
                    if end_time_ms > max_end_time_ms:
                        max_end_time_ms = end_time_ms
                
                srt_end_time_seconds = max_end_time_ms / 1000.0
                time_diff = srt_end_time_seconds - video_duration_seconds
                
                if time_diff > 3.0:
                    large_diff_info = {
                        'video_name': video_name,
                        'srt_name': srt_name,
                        'episode_num': video_idx + 1,  # 序号
                        'episode_display': srt_name,  # 显示文件名
                        'time_diff': time_diff,
                        'srt_end': self.format_duration(srt_end_time_seconds),
                        'video_duration': self.format_duration(video_duration_seconds)
                    }
                    large_time_diff_subtitles.append(large_diff_info)
        
        # 显示检查结果
        has_problems = large_time_diff_subtitles or time_disorder_subtitles
        
        if has_problems:
            self.show_subtitle_problems_dialog(time_disorder_subtitles, large_time_diff_subtitles)
        else:
            self.log_message("✓ 字幕文件检查完成，未发现问题！")

    def show_subtitle_problems_dialog(self, time_disorder_subtitles, large_time_diff_subtitles):
        """显示字幕问题弹窗"""
        self.log_message("")
        self.log_message("="*70)
        self.log_message("🚨 检测到字幕文件存在问题！")
        self.log_message("="*70)
        
        warning_details = []
        
        # 处理时间轴乱序
        if time_disorder_subtitles:
            self.log_message(f"\n【时间轴乱序】检测到 {len(time_disorder_subtitles)} 个字幕文件：")
            for info in time_disorder_subtitles:
                # 使用文件名显示，而不是序号
                file_display = os.path.splitext(info['srt_name'])[0]  # 去掉扩展名
                self.log_message(f"🔀 {file_display}: {info['srt_name']}")
                self.log_message(f"   问题: {info['details']}")
                warning_details.append(f"{file_display}: 时间轴乱序")
        
        # 处理超出3秒
        if large_time_diff_subtitles:
            self.log_message(f"\n【超出时长】检测到 {len(large_time_diff_subtitles)} 个字幕文件：")
            for info in large_time_diff_subtitles:
                # 使用文件名显示，而不是序号
                file_display = os.path.splitext(info['srt_name'])[0]  # 去掉扩展名
                self.log_message(f"⏰ {file_display}: {info['srt_name']}")
                self.log_message(f"   超出: {info['time_diff']:.3f}秒")
                warning_details.append(f"{file_display}: 超出 {info['time_diff']:.1f}秒")
        
        self.log_message("="*70)
        
        # 弹窗提醒
        warning_message = "⚠️ 检测到字幕文件存在问题，建议修复后再合并！\n\n"
        
        if time_disorder_subtitles:
            warning_message += f"🔀 时间轴乱序：{len(time_disorder_subtitles)} 个文件\n"
            warning_message += "   • 字幕时间轴前后顺序混乱\n"
            warning_message += "   • 拖入视频软件会显示很长\n\n"
        
        if large_time_diff_subtitles:
            warning_message += f"⏰ 超出时长：{len(large_time_diff_subtitles)} 个文件\n"
            warning_message += "   • 字幕比视频长超过3秒\n"
            warning_message += "   • 可能版本不匹配\n\n"
        
        warning_message += "问题文件详情：\n"
        display_items = warning_details[:8]
        warning_message += "\n".join(display_items)
        
        if len(warning_details) > 8:
            warning_message += f"\n... 还有 {len(warning_details) - 8} 个文件"
        
        warning_message += "\n\n⚠️ 建议先修复这些问题，再进行字幕合并！"
        
        messagebox.showwarning("字幕文件问题警告", warning_message)

    def format_duration(self, seconds_float):
        if not isinstance(seconds_float, (int, float)) or seconds_float < 0: return "00:00:00,000"
        milliseconds = int((seconds_float % 1) * 1000)
        seconds_int = int(seconds_float)
        hours = seconds_int // 3600
        minutes = (seconds_int % 3600) // 60
        seconds = seconds_int % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    def get_video_duration_ffprobe(self, video_path):
        try:
            if not self.ffprobe_path:
                self.log_message(f"警告: ffprobe不可用，跳过 '{os.path.basename(video_path)}' 时长获取")
                return 0.0
                
            video_path_str = str(video_path); startupinfo = None
            if os.name == 'nt': startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startupinfo.wShowWindow = subprocess.SW_HIDE
            process = subprocess.Popen(
                [self.ffprobe_path, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path_str],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=startupinfo)
            stdout, stderr = process.communicate(timeout=30)
            if process.returncode != 0 or stderr: self.log_message(f"警告: ffprobe未能获取 '{os.path.basename(video_path_str)}' 时长. 错误: {stderr.strip() if stderr else '未知'}"); return 0.0
            output = stdout.strip()
            if not output: self.log_message(f"警告: ffprobe未能获取 '{os.path.basename(video_path_str)}' 时长 (无输出)."); return 0.0
            # 使用Decimal来保持高精度
            from decimal import Decimal, ROUND_HALF_UP
            duration_decimal = Decimal(output).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
            return float(duration_decimal)
        except subprocess.TimeoutExpired: self.log_message(f"获取 '{os.path.basename(video_path_str)}' 时长超时。"); return 0.0
        except FileNotFoundError: self.log_message("错误: ffprobe 命令未找到。"); self.root.after(0, lambda: messagebox.showerror("ffprobe错误", "ffprobe 未找到")); return 0.0
        except ValueError: self.log_message(f"无法转换ffprobe输出为时长: {output if 'output' in locals() else ''}"); return 0.0
        except Exception as e: self.log_message(f"ffprobe获取 '{os.path.basename(video_path_str)}' 时长未知错误: {e}"); return 0.0

    def get_video_framerate_ffprobe(self, video_path):
        """获取视频帧率"""
        try:
            if not self.ffprobe_path:
                return "未知"
                
            video_path_str = str(video_path); startupinfo = None
            if os.name == 'nt': 
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            # 使用ffprobe获取帧率信息
            process = subprocess.Popen(
                [self.ffprobe_path, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', '-of', 'default=noprint_wrappers=1:nokey=1', video_path_str],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=startupinfo)
            stdout, stderr = process.communicate(timeout=15)
            
            if process.returncode != 0 or stderr: 
                return "错误"
            
            output = stdout.strip()
            if not output: 
                return "未知"
            
            # 解析帧率，通常格式为 "30/1" 或 "29970/1000"
            if '/' in output:
                numerator, denominator = output.split('/')
                framerate = float(numerator) / float(denominator)
                # 格式化为常见的帧率显示
                if framerate.is_integer():
                    return f"{int(framerate)}fps"
                else:
                    # 对于常见的帧率进行特殊处理
                    if abs(framerate - 23.976) < 0.1:
                        return "23.98fps"
                    elif abs(framerate - 29.97) < 0.1:
                        return "29.97fps"
                    elif abs(framerate - 59.94) < 0.1:
                        return "59.94fps"
                    else:
                        return f"{framerate:.2f}fps"
            else:
                framerate = float(output)
                return f"{framerate:.2f}fps" if not framerate.is_integer() else f"{int(framerate)}fps"
                
        except subprocess.TimeoutExpired: 
            return "超时"
        except (FileNotFoundError, ValueError, ZeroDivisionError): 
            return "错误"
        except Exception: 
            return "未知"

    def get_video_frame_info_ffprobe(self, video_path):
        """获取视频的帧数和精确帧率（用于精确时间计算）"""
        try:
            if not self.ffprobe_path:
                return None, None, None
                
            video_path_str = str(video_path)
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            # 获取帧率（分数形式）
            process_fps = subprocess.Popen(
                [self.ffprobe_path, '-v', 'error', '-select_streams', 'v:0', 
                 '-show_entries', 'stream=r_frame_rate', 
                 '-of', 'default=noprint_wrappers=1:nokey=1', video_path_str],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=startupinfo)
            stdout_fps, _ = process_fps.communicate(timeout=15)
            
            # 获取总帧数（使用 nb_frames 而不是 nb_read_packets）
            # nb_read_packets 是数据包数，对于B帧视频会不准确
            # nb_frames 才是真正的帧数
            process_frames = subprocess.Popen(
                [self.ffprobe_path, '-v', 'error', '-select_streams', 'v:0',
                 '-show_entries', 'stream=nb_frames',
                 '-of', 'default=noprint_wrappers=1:nokey=1', video_path_str],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=startupinfo)
            stdout_frames, stderr_frames = process_frames.communicate(timeout=30)
            
            # 如果 nb_frames 不可用（某些容器格式），尝试count_frames
            if not stdout_frames.strip() or stdout_frames.strip() == 'N/A':
                self.log_message(f"  警告：nb_frames不可用，使用count_frames方法（较慢）")
                process_frames = subprocess.Popen(
                    [self.ffprobe_path, '-v', 'error', '-select_streams', 'v:0',
                     '-count_frames', '-show_entries', 'stream=nb_read_frames',
                     '-of', 'default=noprint_wrappers=1:nokey=1', video_path_str],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=startupinfo)
                stdout_frames, _ = process_frames.communicate(timeout=60)
            
            # 解析帧率（保持分数形式以获得最高精度）
            fps_str = stdout_fps.strip()
            if '/' in fps_str:
                fps_num, fps_den = fps_str.split('/')
                fps_numerator = int(fps_num)
                fps_denominator = int(fps_den)
                fps_decimal = fps_numerator / fps_denominator
            else:
                fps_decimal = float(fps_str)
                fps_numerator = int(fps_decimal)
                fps_denominator = 1
            
            # 解析总帧数
            total_frames = int(stdout_frames.strip())
            
            # 使用帧数和帧率计算精确时长（秒）
            from fractions import Fraction
            frame_duration = Fraction(fps_denominator, fps_numerator)  # 每帧的时长（秒）
            total_duration = float(frame_duration * total_frames)  # 总时长（秒）
            
            return total_frames, fps_decimal, total_duration
            
        except Exception as e:
            self.log_message(f"获取视频帧信息失败: {str(e)}")
            return None, None, None

    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S", time.localtime()); self.root.after(0, lambda: self._append_log_message(f"[{timestamp}] {message}\n"))
    def _append_log_message(self, formatted_message):
        self.log_text.insert(tk.END, formatted_message); self.log_text.see(tk.END)
    def clear_log(self): self.log_text.delete(1.0, tk.END)
    
    def reset_all(self):
        """重置所有内容，清空路径和文件列表"""
        if self.processing:
            messagebox.showinfo("提示", "正在处理中，无法重置。")
            return
        
        # 确认重置
        result = messagebox.askyesno("确认重置", 
            "确定要重置所有内容吗？\n\n将清空：\n• 视频文件夹路径\n• 字幕文件夹路径\n• 输出文件路径\n• 所有文件列表\n• 扫描数据")
        
        if not result:
            return
        
        # 清空路径输入框
        self.video_folder_entry.delete(0, tk.END)
        self.srt_folder_entry.delete(0, tk.END)
        self.output_file_entry.delete(0, tk.END)
        
        # 清空自定义范围
        self.custom_start_entry.delete(0, tk.END)
        self.custom_start_entry.insert(0, "1")
        self.custom_end_entry.delete(0, tk.END)
        self.custom_end_entry.insert(0, "0")
        
        # 清空文件列表
        self.video_tree.delete(*self.video_tree.get_children())
        self.srt_tree.delete(*self.srt_tree.get_children())
        self.folder_duration_tree.delete(*self.folder_duration_tree.get_children())
        
        # 重置数据
        self.video_files_data = []
        self.srt_files_data = []
        self.folder_durations = {}
        self.total_duration_seconds = 0.0
        self.auto_scan_scheduled = False
        
        # 更新标签
        self.video_count_label.config(text="视频文件总数: 0")
        self.srt_count_label.config(text="字幕文件总数: 0")
        self.total_duration_label.config(text="视频总时长: 00:00:00")
        self.total_videos_label.config(text="(共0个视频)")
        
        # 禁用合并按钮
        self.merge_all_button.config(state=tk.DISABLED)
        self.custom_merge_button.config(state=tk.DISABLED)
        
        # 重置进度条
        self.progress["value"] = 0
        
        # 清空日志
        self.log_text.delete(1.0, tk.END)
        
        # 更新状态栏
        self.status_bar.config(text="已重置")
        
        self.log_message("✓ 所有内容已重置，可以开始新的任务！")



    def _merge_srt_files_thread(self, output_path, start_episode_num, end_episode_num, show_completion_dialog=True):
        self.processing = True; self.status_bar.config(text="正在合并字幕..."); self.root.update_idletasks()
        
        # 生成带后缀的输出文件名
        final_output_path = self.generate_output_filename_with_suffix(output_path, start_episode_num, end_episode_num)
        self.log_message(f"字幕合并开始: {final_output_path}")
        
        try:
            start_idx = start_episode_num - 1
            end_idx = end_episode_num # Python slice `end_idx` is exclusive

            # 1. 从全局排序的视频列表中选取指定范围的视频
            selected_videos_data = self.video_files_data[start_idx:end_idx]
            if not selected_videos_data:
                self.log_message("错误：按所选集数范围，未找到视频文件。"); self.root.after(0, lambda: messagebox.showerror("错误", "未找到视频。")); return

            self.log_message(f"准备合并 {len(selected_videos_data)} 个视频对应的字幕...")
            all_subs_combined = pysrt.SubRipFile()
            current_total_offset_seconds = 0.0
            self.progress["maximum"] = len(selected_videos_data); self.progress["value"] = 0; self.root.after(0, self.root.update_idletasks)

            if self.backup_var.get() and os.path.exists(final_output_path): # Backup logic
                # ... (backup logic from previous version) ...
                backup_idx = 0; backup_path_base = final_output_path + ".bak"; backup_path = backup_path_base
                while os.path.exists(backup_path): backup_idx += 1; backup_path = f"{backup_path_base}{backup_idx}"
                try: os.rename(final_output_path, backup_path); self.log_message(f"已创建备份: {backup_path}")
                except Exception as e: self.log_message(f"备份失败: {str(e)}")


            # 使用基于帧的精确时间计算
            from fractions import Fraction
            cumulative_frames = 0  # 累积帧数（整数，完全精确）
            reference_fps = None  # 参考帧率
            
            # 记录所有需要修正的字幕
            corrected_subtitles = []  # 存储需要修正的字幕信息
            large_time_diff_subtitles = []  # 存储时间差异过大的字幕（超过3秒）
            time_disorder_subtitles = []  # 存储时间轴乱序的字幕
            
            processed_count = 0
            for i, video_data_item in enumerate(selected_videos_data):
                video_name = video_data_item[0]
                video_full_path = video_data_item[1]
                video_base_name = video_data_item[2]
                video_duration_seconds = video_data_item[3]
                video_frames = video_data_item[4] if len(video_data_item) > 4 else 0
                video_fps = video_data_item[5] if len(video_data_item) > 5 else 0.0

                # 如果帧信息未扫描，实时获取
                if video_frames == 0 or video_fps == 0.0:
                    self.log_message(f"警告：视频 '{video_name}' 帧信息缺失，尝试实时获取...")
                    frames, fps, duration = self.get_video_frame_info_ffprobe(video_full_path)
                    if frames and fps and duration:
                        video_frames = frames
                        video_fps = fps
                        video_duration_seconds = duration
                        # 更新数据
                        if len(video_data_item) > 5:
                            video_data_item[3] = duration
                            video_data_item[4] = frames
                            video_data_item[5] = fps
                    else:
                        # 如果还是失败，回退到旧方法
                        video_duration_seconds = self.get_video_duration_ffprobe(video_full_path)
                        video_data_item[3] = video_duration_seconds
                
                # 设置参考帧率（使用第一个视频的帧率）
                if reference_fps is None and video_fps > 0:
                    reference_fps = video_fps
                    self.log_message(f"使用参考帧率: {reference_fps:.6f} fps (来自第一个视频)")

                # 增强匹配逻辑
                matched_srt_data = None
                
                # 1. 首先尝试精确匹配
                for srt_data_item in self.srt_files_data:
                    srt_fn, srt_fp, srt_bn = srt_data_item
                    if srt_bn.lower() == video_base_name.lower():  # 忽略大小写
                        matched_srt_data = srt_data_item
                        break
                        
                # 2. 如果没有精确匹配，尝试EP模式匹配
                if not matched_srt_data:
                    # 提取EP后的数字
                    video_ep_match = re.search(r'EP\s*(\d+)', video_base_name, re.IGNORECASE)
                    if video_ep_match:
                        video_ep_num = int(video_ep_match.group(1))
                        
                        for srt_data_item in self.srt_files_data:
                            srt_fn, srt_fp, srt_bn = srt_data_item
                            srt_ep_match = re.search(r'EP\s*(\d+)', srt_bn, re.IGNORECASE)
                            
                            if srt_ep_match and int(srt_ep_match.group(1)) == video_ep_num:
                                matched_srt_data = srt_data_item
                                self.log_message(f"通过EP集数匹配: 视频'{video_name}'与字幕'{srt_fn}'")
                                break
                
                if not matched_srt_data:
                    self.log_message(f"警告：视频 '{video_name}' 未找到同基本名的SRT文件，已跳过。")
                    # 即使跳过字幕，也必须累加该视频的帧数作为偏移量
                    if video_frames > 0:
                         cumulative_frames += video_frames
                         self.log_message(f"  累积帧数: +{video_frames} = {cumulative_frames}")
                    else:
                         self.log_message(f"警告：跳过的视频 '{video_name}' 帧数为0，偏移量未增加。")
                    self.progress["value"] = i + 1; self.root.after(0, self.root.update_idletasks)
                    continue # 跳过这个视频的字幕处理

                srt_name, srt_full_path, _ = matched_srt_data

                if video_duration_seconds == 0.0 and i < len(selected_videos_data) - 1:
                    self.log_message(f"警告：视频 '{video_name}' 时长为0或获取失败。后续字幕偏移可能不准确。")

                # 计算基于帧的精确偏移量
                if reference_fps and reference_fps > 0:
                    # 使用整数帧数计算，避免浮点误差
                    # 偏移秒数 = 累积帧数 / 帧率（精确到帧）
                    offset_total_frames = cumulative_frames
                    offset_hours = offset_total_frames // int(reference_fps * 3600)
                    remaining_frames = offset_total_frames % int(reference_fps * 3600)
                    offset_minutes = remaining_frames // int(reference_fps * 60)
                    remaining_frames = remaining_frames % int(reference_fps * 60)
                    offset_seconds = remaining_frames // int(reference_fps)
                    offset_frames = remaining_frames % int(reference_fps)
                    
                    # 转换为秒（用于pysrt的shift）
                    current_offset_seconds = cumulative_frames / reference_fps
                else:
                    # 如果没有帧率信息，回退到简单计算
                    current_offset_seconds = cumulative_frames / reference_fps if reference_fps else 0.0
                    offset_hours = offset_minutes = offset_seconds = offset_frames = 0
                
                formatted_vid_dur = self.format_duration(video_duration_seconds)
                formatted_offset = self.format_duration(current_offset_seconds)
                # 显示剪辑软件格式的时间（时:分:秒:帧）
                editor_format_offset = f"{offset_hours:02d}:{offset_minutes:02d}:{offset_seconds:02d}:{offset_frames:02d}"
                
                frame_info = f"{video_frames}帧@{video_fps:.3f}fps" if video_frames > 0 else "帧信息缺失"
                self.log_message(f"处理字幕 [{processed_count+1}/{len(selected_videos_data)}]: '{srt_name}'")
                self.log_message(f"  视频: '{video_name}' ({frame_info}, 时长: {formatted_vid_dur})")
                self.log_message(f"  偏移: {formatted_offset} | 剪辑格式: {editor_format_offset} (累积: {cumulative_frames}帧)")
                
                try:
                    subs_for_current_file = pysrt.open(srt_full_path, encoding='utf-8')
                except UnicodeDecodeError:
                    try: self.log_message(f"'{srt_name}' UTF-8解码失败，尝试GBK..."); subs_for_current_file = pysrt.open(srt_full_path, encoding='gbk')
                    except Exception as enc_e: self.log_message(f"错误: 无法解码字幕 '{srt_name}': {enc_e}"); continue
                except Exception as e: self.log_message(f"错误: 打开字幕 '{srt_name}' 失败: {e}"); continue
                
                # ===== 检测字幕时间轴顺序（不自动修复，记录待提醒）=====
                if len(subs_for_current_file) > 1:
                    # 检查时间轴是否有倒退
                    time_regression_detected = False
                    regression_details = ""
                    for idx in range(1, len(subs_for_current_file)):
                        prev_sub = subs_for_current_file[idx - 1]
                        curr_sub = subs_for_current_file[idx]
                        
                        prev_time_ms = (prev_sub.start.hours * 3600000 + 
                                       prev_sub.start.minutes * 60000 + 
                                       prev_sub.start.seconds * 1000 + 
                                       prev_sub.start.milliseconds)
                        curr_time_ms = (curr_sub.start.hours * 3600000 + 
                                       curr_sub.start.minutes * 60000 + 
                                       curr_sub.start.seconds * 1000 + 
                                       curr_sub.start.milliseconds)
                        
                        if curr_time_ms < prev_time_ms:
                            time_regression_detected = True
                            regression_details = f"第{idx}条 ({self.format_duration(curr_time_ms/1000)}) < 第{idx+1}条 ({self.format_duration(prev_time_ms/1000)})"
                            self.log_message(f"  ⚠️ 检测到时间轴倒退: {regression_details}")
                            break
                    
                    if time_regression_detected:
                        # 记录到问题列表，稍后统一弹窗提醒
                        disorder_info = {
                            'video_name': video_name,
                            'srt_name': srt_name,
                            'episode_num': processed_count + 1,  # 序号
                            'episode_display': srt_name,  # 显示文件名
                            'details': regression_details
                        }
                        time_disorder_subtitles.append(disorder_info)
                        self.log_message(f"  ⚠️ 此字幕文件时间轴混乱，建议手动检查修复")
                # ===== 时间轴检测结束 =====
                
                # ===== 检测字幕时长（严格模式：0.01秒容差）=====
                # 注意：字幕时长检测不影响偏移计算，偏移始终基于视频的实际帧数
                if len(subs_for_current_file) > 0:
                    # 使用所有字幕中的最大结束时间，而不是最后一条
                    # 这样可以避免时间轴乱序导致的误判
                    max_end_time_ms = 0
                    max_end_sub = None
                    for sub in subs_for_current_file:
                        end_time_ms = (sub.end.hours * 3600000 + 
                                      sub.end.minutes * 60000 + 
                                      sub.end.seconds * 1000 + 
                                      sub.end.milliseconds)
                        if end_time_ms > max_end_time_ms:
                            max_end_time_ms = end_time_ms
                            max_end_sub = sub
                    
                    srt_end_time_ms = max_end_time_ms
                    srt_end_time_seconds = srt_end_time_ms / 1000.0
                    
                    time_diff = srt_end_time_seconds - video_duration_seconds
                    
                    if abs(time_diff) > 0.01:
                        if time_diff > 0:
                            # 字幕超出视频时长的情况
                            self.log_message(f"  ⚠️ 警告：字幕结束时间超出视频时长 {time_diff:.3f}秒")
                            self.log_message(f"     字幕最大结束: {self.format_duration(srt_end_time_seconds)}")
                            self.log_message(f"     视频时长: {formatted_vid_dur}")
                            
                            # 只检查字幕超出视频时长的情况（time_diff > 3秒）
                            # 字幕提前结束不需要弹窗提醒（因为视频结尾可能没有对话）
                            if time_diff > 3.0:
                                # 超过3秒，记录到问题列表，不自动修正
                                large_diff_info = {
                                    'video_name': video_name,
                                    'srt_name': srt_name,
                                    'episode_num': processed_count + 1,  # 序号
                                    'episode_display': srt_name,  # 显示文件名
                                    'time_diff': time_diff,
                                    'srt_end': self.format_duration(srt_end_time_seconds),
                                    'video_duration': formatted_vid_dur
                                }
                                large_time_diff_subtitles.append(large_diff_info)
                                self.log_message(f"     ⚠️ 超出时间过长（>{time_diff:.3f}秒），建议检查字幕和视频是否匹配")
                            else:
                                # 小于3秒的差异，自动修正
                                correction_info = {
                                    'video_name': video_name,
                                    'srt_name': srt_name,
                                    'episode_num': processed_count + 1,  # 序号
                                    'episode_display': srt_name,  # 显示文件名
                                    'time_diff': time_diff,
                                    'srt_end': self.format_duration(srt_end_time_seconds),
                                    'video_duration': formatted_vid_dur
                                }
                                corrected_subtitles.append(correction_info)
                                
                                # 修正最大结束时间的字幕
                                if max_end_sub:
                                    video_duration_ms = int(video_duration_seconds * 1000)
                                    max_end_sub.end.hours = video_duration_ms // 3600000
                                    max_end_sub.end.minutes = (video_duration_ms % 3600000) // 60000
                                    max_end_sub.end.seconds = (video_duration_ms % 60000) // 1000
                                    max_end_sub.end.milliseconds = video_duration_ms % 1000
                                    
                                    self.log_message(f"     ✓ 已自动修正为: {formatted_vid_dur}")
                        elif time_diff < -0.01:
                            # 字幕提前结束是正常的，不需要特殊处理和弹窗提醒
                            self.log_message(f"  ℹ️ 字幕提前结束 {abs(time_diff):.3f}秒（正常）")
                        else:
                            self.log_message(f"  ✓ 字幕时长完美（差异 {time_diff:.3f}秒）")
                    else:
                        self.log_message(f"  ✓ 字幕时长完美（差异 {time_diff:.3f}秒）")
                # ===== 检测结束 =====
                
                # 使用基于帧的精确偏移
                if cumulative_frames > 0 and reference_fps > 0:
                    # 计算精确的偏移时间（避免浮点累积误差）
                    # 方法：逐条字幕手动调整时间，而不是使用shift
                    offset_ms = int((cumulative_frames * 1000.0) / reference_fps)
                    
                    for sub in subs_for_current_file:
                        # 转换开始时间
                        start_ms = (sub.start.hours * 3600000 + 
                                   sub.start.minutes * 60000 + 
                                   sub.start.seconds * 1000 + 
                                   sub.start.milliseconds)
                        new_start_ms = start_ms + offset_ms
                        
                        sub.start.hours = new_start_ms // 3600000
                        sub.start.minutes = (new_start_ms % 3600000) // 60000
                        sub.start.seconds = (new_start_ms % 60000) // 1000
                        sub.start.milliseconds = new_start_ms % 1000
                        
                        # 转换结束时间
                        end_ms = (sub.end.hours * 3600000 + 
                                 sub.end.minutes * 60000 + 
                                 sub.end.seconds * 1000 + 
                                 sub.end.milliseconds)
                        new_end_ms = end_ms + offset_ms
                        
                        sub.end.hours = new_end_ms // 3600000
                        sub.end.minutes = (new_end_ms % 3600000) // 60000
                        sub.end.seconds = (new_end_ms % 60000) // 1000
                        sub.end.milliseconds = new_end_ms % 1000
                
                all_subs_combined.extend(subs_for_current_file)
                
                # 累加帧数（整数运算，完全精确）
                if video_frames > 0:
                    cumulative_frames += video_frames
                
                processed_count +=1
                self.progress["value"] = i + 1; self.root.after(0, self.root.update_idletasks)
            
            self.log_message(f"共成功匹配并处理了 {processed_count} 对影音文件。")
            
            # ===== 显示所有需要人工检查的字幕问题汇总 =====
            # 统一弹窗提醒：时间轴乱序 + 超出3秒的情况
            has_problems = large_time_diff_subtitles or time_disorder_subtitles
            
            if has_problems:
                self.log_message("")
                self.log_message("="*70)
                self.log_message("🚨🚨🚨 字幕文件问题汇总 🚨🚨🚨")
                self.log_message("="*70)
                
                warning_details = []
                
                # 处理时间轴乱序的情况
                if time_disorder_subtitles:
                    self.log_message(f"\n【时间轴乱序】检测到 {len(time_disorder_subtitles)} 个字幕文件时间轴混乱：")
                    self.log_message("")
                    for info in time_disorder_subtitles:
                        file_display = os.path.splitext(info['srt_name'])[0]  # 去掉扩展名
                        self.log_message(f"🔀 {file_display}: {info['srt_name']}")
                        self.log_message(f"   视频: {info['video_name']}")
                        self.log_message(f"   问题: {info['details']}")
                        self.log_message("")
                        warning_details.append(f"{file_display}: 时间轴乱序")
                
                # 处理超出3秒的情况
                if large_time_diff_subtitles:
                    self.log_message(f"\n【超出时长】检测到 {len(large_time_diff_subtitles)} 个字幕文件超出视频时长超过3秒：")
                    self.log_message("")
                    for info in large_time_diff_subtitles:
                        file_display = os.path.splitext(info['srt_name'])[0]  # 去掉扩展名
                        self.log_message(f"⏰ {file_display}: {info['srt_name']}")
                        self.log_message(f"   视频: {info['video_name']}")
                        self.log_message(f"   超出: {info['time_diff']:.3f}秒")
                        self.log_message(f"   字幕结束: {info['srt_end']}")
                        self.log_message(f"   视频时长: {info['video_duration']}")
                        self.log_message("")
                        warning_details.append(f"{file_display}: 超出 {info['time_diff']:.1f}秒")
                
                self.log_message("="*70)
                self.log_message("⚠️ 以上字幕文件未自动修正，建议手动检查！")
                self.log_message("="*70)
                self.log_message("")
                
                # 统一弹窗提醒用户
                warning_message = "检测到字幕文件存在以下问题：\n\n"
                
                if time_disorder_subtitles:
                    warning_message += f"🔀 时间轴乱序：{len(time_disorder_subtitles)} 个文件\n"
                    warning_message += "   • 字幕时间轴前后顺序混乱\n"
                    warning_message += "   • 拖入视频软件会显示很长\n\n"
                
                if large_time_diff_subtitles:
                    warning_message += f"⏰ 超出时长：{len(large_time_diff_subtitles)} 个文件\n"
                    warning_message += "   • 字幕比视频长超过3秒\n"
                    warning_message += "   • 可能版本不匹配\n\n"
                
                warning_message += "可能的原因：\n"
                warning_message += "• 字幕和视频版本不匹配\n"
                warning_message += "• 字幕文件本身有问题\n"
                warning_message += "• 视频帧率与字幕制作时不一致\n\n"
                warning_message += "问题文件详情：\n"
                
                # 限制弹窗显示的条目数量，避免过长
                display_items = warning_details[:8]  # 最多显示8个
                warning_message += "\n".join(display_items)
                
                if len(warning_details) > 8:
                    warning_message += f"\n... 还有 {len(warning_details) - 8} 个文件"
                
                warning_message += "\n\n⚠️ 这些文件未自动修正，建议手动检查后重新处理！"
                
                if show_completion_dialog:
                    self.root.after(0, lambda: messagebox.showwarning("字幕文件问题警告", warning_message))
            
            if corrected_subtitles:
                self.log_message("")
                self.log_message("="*70)
                self.log_message("⚠️⚠️⚠️ 字幕时长修正汇总报告 ⚠️⚠️⚠️")
                self.log_message("="*70)
                self.log_message(f"检测到 {len(corrected_subtitles)} 个字幕文件的结束时间超出视频时长，已自动修正：")
                self.log_message("")
                for info in corrected_subtitles:
                    self.log_message(f"❌ 第{info['episode']}集: {info['srt_name']}")
                    self.log_message(f"   视频: {info['video_name']}")
                    self.log_message(f"   超出: {info['time_diff']:.3f}秒")
                    self.log_message(f"   原字幕结束时间: {info['srt_end']}")
                    self.log_message(f"   修正为视频时长: {info['video_duration']}")
                    self.log_message("")
                self.log_message("="*70)
                self.log_message("✓ 所有超出的字幕已自动修正，确保后续集数字幕偏移准确！")
                self.log_message("="*70)
                self.log_message("")
            else:
                self.log_message("")
                self.log_message("="*70)
                self.log_message("✓✓✓ 所有字幕时长检查通过！✓✓✓")
                self.log_message("="*70)
                self.log_message("所有字幕文件的结束时间都与视频时长完美匹配（误差<0.01秒）")
                self.log_message("="*70)
                self.log_message("")
            # ===== 汇总结束 =====
            
            if len(all_subs_combined) > 0:
                all_subs_combined.save(final_output_path, encoding='utf-8')
                msg_s = f"字幕合并成功！共 {len(all_subs_combined)} 条字幕 ({processed_count}个文件)."; self.log_message(msg_s)
                if show_completion_dialog:
                    self.root.after(0, lambda m=msg_s: messagebox.showinfo("成功", m))
            else:
                warn_m = "合并结束，未找到有效字幕内容或未成功配对文件。"; self.log_message(warn_m)
                if show_completion_dialog:
                    self.root.after(0, lambda m=warn_m: messagebox.showwarning("无内容", m))

        except Exception as e:
            import traceback; error_details = f"合并过程严重错误: {e}\n{traceback.format_exc()}"
            self.log_message(error_details)
            if show_completion_dialog:
                self.root.after(0, lambda m=error_details: messagebox.showerror("严重错误", m))
        finally:
            self.processing = False
            # 恢复按钮状态
            has_videos = len(self.video_files_data) > 0
            self.root.after(0, lambda: self.merge_all_button.config(state=tk.NORMAL if has_videos else tk.DISABLED))
            self.root.after(0, lambda: self.custom_merge_button.config(state=tk.NORMAL if has_videos else tk.DISABLED))
            self.root.after(0, lambda: self.status_bar.config(text="就绪"))
            self.root.after(0, lambda: self.progress.config(value=0)); self.root.after(0, self.root.update_idletasks)

    def get_video_duration_from_tree_or_probe(self, video_full_path, video_name, original_list_idx):
        """辅助函数: 尝试从Treeview获取时长，否则调用ffprobe"""
        video_duration_seconds = 0.0
        if original_list_idx != -1 and original_list_idx < len(self.video_tree.get_children()):
            video_item_id = self.video_tree.get_children()[original_list_idx]
            duration_str = self.video_tree.item(video_item_id, 'values')[3]  # 时长列现在是索引3
            if duration_str not in ["待扫描", "错误"]:
                try:
                    # 处理包含毫秒的时间格式 "00:00:00,000" 或 "00:00:00.000"
                    parts = duration_str.split(':')
                    if len(parts) == 3:
                        h, m = int(parts[0]), int(parts[1])
                        # 处理秒部分，可能包含小数
                        s_part = parts[2].replace(',', '.')  # 统一替换逗号为点号
                        s = float(s_part)
                        video_duration_seconds = float(h * 3600 + m * 60 + s)
                    else:
                        # 原始处理方式作为后备
                        h, m, s = map(int, duration_str.split(':'))
                        video_duration_seconds = float(h * 3600 + m * 60 + s)
                except ValueError:
                    self.log_message(f"警告：列表解析视频 '{video_name}' 时长 ('{duration_str}')失败。重新获取。")
                    video_duration_seconds = self.get_video_duration_ffprobe(video_full_path)
        else:
            self.log_message(f"警告：视频 '{video_name}' 未在列表找到，直接获取时长。")
            video_duration_seconds = self.get_video_duration_ffprobe(video_full_path)
        return video_duration_seconds

if __name__ == "__main__":
    root = tk.Tk()
    app = SubtitleMerger(root)
    root.mainloop()
