import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import shutil
import time
import win32api
import win32con
import winreg
import threading
from queue import Queue
import psutil
import win32file
import win32security
import ntsecuritycon as con
import sys
import ctypes
import signal
import stat
import urllib
import zipfile
import win32com.client  # 新增导入，用于访问回收站

class DiskCleaner:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("快捷磁盘清理器")
        # 获取屏幕宽度和高度
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        # 设置窗口大小为屏幕分辨率
        self.root.geometry(f"{screen_width}x{screen_height}")
        # 计算窗口居中时的坐标
        x = (screen_width - screen_width) // 2
        y = (screen_height - screen_height) // 2
        # 设置窗口位置
        self.root.geometry(f"+{x}+{y}")
        
        # 创建磁盘选择下拉框
        disk_frame = ttk.LabelFrame(self.root, text="选择要清理的磁盘")
        disk_frame.pack(padx=10, pady=10, fill="x")
        
        self.disk_var = tk.StringVar()
        disks = [d for d in "CDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:")]
        self.disk_combo = ttk.Combobox(disk_frame, textvariable=self.disk_var, values=disks)
        self.disk_combo.pack(padx=5, pady=5)
        
        # 创建按钮
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(padx=10, pady=10)
        
        ttk.Button(btn_frame, text="系统磁盘清理", command=self.clean_disk).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="清理临时文件", command=self.clean_temp).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="扫描闲置程序", command=self.scan_unused_exe).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="一键清理", command=self.quick_clean).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="扫描大文件夹", command=self.scan_large_folders).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="万能删除", command=self.force_delete).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="显示文件夹/文件大小排序", command=self.show_folder_file_sizes).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="自动清理回收站", command=self.auto_clean_recycle_bin).pack(side="left", padx=5)  # 修改按钮文本和命令
        
        # 创建进度条
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress.pack(padx=10, pady=5, fill="x")
        
        # 创建日志文本框
        log_frame = ttk.LabelFrame(self.root, text="清理日志")
        log_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.log_text = tk.Text(log_frame, height=10)
        self.log_text.pack(padx=5, pady=5, fill="both", expand=True)

        # 创建程序详情列表
        self.details_frame = ttk.LabelFrame(self.root, text="程序详细信息")
        self.details_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        # 创建Treeview用于显示程序列表
        self.tree = ttk.Treeview(self.details_frame, columns=("路径", "未使用天数", "大小", "影响"), show="headings")
        self.tree.heading("路径", text="程序路径")
        self.tree.heading("未使用天数", text="未使用天数")
        self.tree.heading("大小", text="占用空间")
        self.tree.heading("影响", text="删除影响")
        self.tree.pack(padx=5, pady=5, fill="both", expand=True)
        
        # 绑定双击事件
        self.tree.bind("<Double-1>", self.open_file_location)
        
        # 创建消息队列用于线程间通信
        self.msg_queue = Queue()
        self.root.after(100, self.check_msg_queue)

    def force_delete(self):
        """万能删除器"""
        # 以所有者权限运行
        if not ctypes.windll.shell32.IsUserAnAdmin():
            # 获取当前用户的SID
            user_sid = win32security.GetTokenInformation(
                win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY),
                win32security.TokenUser)[0]
                
            # 获取当前用户的所有者权限
            sd = win32security.SECURITY_DESCRIPTOR()
            sd.SetSecurityDescriptorOwner(user_sid, True)
            
            # 以所有者权限重新启动程序
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas", 
                sys.executable,
                " ".join(sys.argv),
                None,
                1
            )
            return
            
        path = filedialog.askdirectory(title="选择要删除的文件夹") or filedialog.askopenfilename(title="选择要删除的文件")
        if not path:
            return
        # 检查路径是否存在
        if not os.path.exists(path):
            self.log_text.insert("end", f"路径不存在: {path}\n")
            self.log_text.see("end")
            return
            
        try:
            # 获取文件/文件夹的所有权
            sd = win32security.GetFileSecurity(path, win32security.OWNER_SECURITY_INFORMATION | 
                                                   win32security.DACL_SECURITY_INFORMATION)
            
            # 获取TrustedInstaller SID
            ti_sid = win32security.ConvertStringSidToSid("S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464")
            
            # 获取当前用户的SID
            user_sid = win32security.GetTokenInformation(
                win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY),
                win32security.TokenUser)[0]
                
            # 修改所有者为当前用户
            sd.SetSecurityDescriptorOwner(user_sid, True)
            win32security.SetFileSecurity(path, win32security.OWNER_SECURITY_INFORMATION, sd)
            
            # 修改DACL权限
            dacl = win32security.ACL()
            dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.FILE_ALL_ACCESS, user_sid)
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION, sd)
            
            # 强制删除文件/文件夹
            if os.path.isfile(path):
                os.chmod(path, stat.S_IWRITE)  # 移除只读属性
                os.unlink(path)
            else:
                for root, dirs, files in os.walk(path):
                    for d in dirs:
                        os.chmod(os.path.join(root, d), stat.S_IWRITE)
                    for f in files:
                        os.chmod(os.path.join(root, f), stat.S_IWRITE)
                shutil.rmtree(path, ignore_errors=True)
                
            self.log_text.insert("end", f"成功删除: {path}\n")
            
        except Exception as e:
            self.log_text.insert("end", f"删除失败: {str(e)}\n")
            if "拒绝访问" in str(e):
                self.log_text.insert("end", "提示:请以管理员身份运行程序\n")
            
        self.log_text.see("end")

    def check_msg_queue(self):
        """检查消息队列并更新UI"""
        while not self.msg_queue.empty():
            msg = self.msg_queue.get()
            if isinstance(msg, tuple):
                msg_type, content = msg
                if msg_type == "progress":
                    self.progress_var.set(content)
                elif msg_type == "log":
                    self.log_text.insert("end", content)
                    self.log_text.see("end")
            else:
                self.log_text.insert("end", msg)
                self.log_text.see("end")
        self.root.after(100, self.check_msg_queue)

    def get_file_size(self, path):
        """获取文件或文件夹的总大小"""
        total_size = 0
        if os.path.isfile(path):
            return os.path.getsize(path)
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total_size += os.path.getsize(fp)
        return total_size

    def is_system_file(self, path):
        """检查是否是系统重要文件"""
        system_paths = [
            os.environ.get('SystemRoot'),
            os.environ.get('ProgramFiles'),
            os.environ.get('ProgramFiles(x86)'),
            os.environ.get('windir')
        ]
        return any(path.lower().startswith(sys_path.lower()) for sys_path in system_paths if sys_path)

    def analyze_program_impact(self, exe_path):
        """分析删除程序的影响"""
        impact = []
        
        # 检查是否有自启动项
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ) as key:
                for i in range(winreg.QueryInfoKey(key)[1]):
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        if exe_path.lower() in value.lower():
                            impact.append("开机自启动程序")
                    except:
                        continue
        except:
            pass

        # 检查是否为常用文件类型的默认程序
        try:
            assoc_path = os.path.dirname(exe_path)
            if any(f.endswith('.dll') for f in os.listdir(assoc_path)):
                impact.append("可能是文件关联程序")
        except:
            pass

        # 检查是否有服务依赖
        try:
            output = subprocess.check_output(['sc', 'query', 'type=', 'service']).decode()
            if exe_path.lower() in output.lower():
                impact.append("系统服务依赖")
        except:
            pass

        if not impact:
            return "影响较小"
        return "、".join(impact)

    def open_file_location(self, event):
        """双击打开文件所在位置"""
        selected_item = self.tree.selection()
        if selected_item:
            file_path = self.tree.item(selected_item[0])['values'][0]
            subprocess.run(['explorer', '/select,', file_path])

    def scan_large_folders(self):
        """扫描占用空间较大的文件夹"""
        disk = self.disk_var.get()
        if not disk:
            messagebox.showwarning("警告", "请先选择要扫描的磁盘!")
            return

        self.log_text.insert("end", f"开始扫描磁盘 {disk}: 上的大文件夹...\n")
        self.root.update()

        # 清空现有列表
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 获取所有文件夹大小
        folder_sizes = []
        for root, dirs, files in os.walk(f"{disk}:\\"):
            try:
                folder_size = self.get_file_size(root)
                if folder_size > 1024 * 1024 * 100:  # 大于100MB的文件夹
                    folder_sizes.append((root, folder_size))
            except:
                continue

        # 按大小排序
        folder_sizes.sort(key=lambda x: x[1], reverse=True)

        # 显示前50个最大的文件夹
        for folder_path, size in folder_sizes[:50]:
            size_mb = size / (1024 * 1024)
            size_gb = size_mb / 1024
            
            # 获取文件夹最后修改时间
            try:
                last_modified = os.path.getmtime(folder_path)
                days_ago = (time.time() - last_modified) / (24 * 3600)
            except:
                days_ago = 0

            # 添加到Treeview
            if size_gb >= 1:
                size_str = f"{size_gb:.2f}GB"
            else:
                size_str = f"{size_mb:.2f}MB"

            self.tree.insert("", "end", values=(
                folder_path,
                f"{int(days_ago)}天",
                size_str,
                "双击打开目录"
            ))

        self.log_text.insert("end", "扫描完成!\n")
        self.log_text.see("end")

    def scan_unused_exe(self):
        disk = self.disk_var.get()
        if not disk:
            messagebox.showwarning("警告", "请先选择要扫描的磁盘!")
            return

        self.log_text.insert("end", f"开始扫描磁盘 {disk}: 上的闲置程序...\n")
        self.root.update()

        # 清空现有列表
        for item in self.tree.get_children():
            self.tree.delete(item)

        current_time = time.time()
        unused_exes = []

        for root, dirs, files in os.walk(f"{disk}:\\"):
            for file in files:
                if file.lower().endswith('.exe'):
                    file_path = os.path.join(root, file)
                    try:
                        if self.is_system_file(file_path):
                            continue
                            
                        # 获取最后访问时间
                        last_access = os.path.getatime(file_path)
                        days_unused = (current_time - last_access) / (24 * 3600)
                        
                        if days_unused > 90:  # 超过90天未使用
                            # 计算程序及关联文件总大小
                            program_dir = os.path.dirname(file_path)
                            total_size = self.get_file_size(program_dir)
                            
                            if total_size > 100 * 1024 * 1024:  # 大于100MB
                                impact = self.analyze_program_impact(file_path)
                                unused_exes.append((file_path, days_unused, total_size, impact))
                    except:
                        continue

        if unused_exes:
            self.log_text.insert("end", "\n发现以下长期未使用的程序:\n")
            for exe_path, days, size, impact in unused_exes:
                size_mb = size / (1024 * 1024)
                # 添加到Treeview
                self.tree.insert("", "end", values=(
                    exe_path,
                    f"{int(days)}天",
                    f"{size_mb:.2f}MB",
                    impact
                ))
                # 同时在日志中显示
                self.log_text.insert("end", f"\n程序: {exe_path}\n")
                self.log_text.insert("end", f"未使用天数: {int(days)}天\n")
                self.log_text.insert("end", f"占用空间: {size_mb:.2f}MB\n")
                self.log_text.insert("end", f"删除影响: {impact}\n")
        else:
            self.log_text.insert("end", "\n未发现长期未使用的大型程序\n")

        self.log_text.see("end")
        
    def clean_disk(self):
        disk = self.disk_var.get()
        if not disk:
            messagebox.showwarning("警告", "请先选择要清理的磁盘!")
            return
            
        self.log_text.insert("end", f"开始清理磁盘 {disk}:\n")
        self.root.update()
        
        # 运行cleanmgr
        subprocess.run(f"cleanmgr /d {disk}:", shell=True)
        
        self.log_text.insert("end", "磁盘清理完成!\n")
        self.log_text.see("end")
        
    def clean_temp(self):
        self.log_text.insert("end", "开始清理临时文件...\n")
        self.root.update()
        
        temp_path = os.environ.get("TEMP")
        try:
            for item in os.listdir(temp_path):
                item_path = os.path.join(temp_path, item)
                try:
                    if os.path.isfile(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except:
                    pass
            self.log_text.insert("end", "临时文件清理完成!\n")
        except Exception as e:
            self.log_text.insert("end", f"清理出错: {str(e)}\n")
        
        self.log_text.see("end")

    def quick_clean_worker(self):
        """后台清理线程"""
        total_cleaned = 0
        total_files = 0
        processed_files = 0
        
        # 先统计总文件数
        for disk in [d for d in "CDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:")]:
            for root, dirs, files in os.walk(f"{disk}:\\"):
                total_files += len([f for f in files if f.lower().endswith('.exe')])
        
        # 开始清理
        for disk in [d for d in "CDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:")]:
            self.msg_queue.put(f"\n扫描磁盘 {disk}:...\n")
            
            for root, dirs, files in os.walk(f"{disk}:\\"):
                exe_files = [f for f in files if f.lower().endswith('.exe')]
                for file in exe_files:
                    processed_files += 1
                    progress = (processed_files / total_files) * 100
                    self.msg_queue.put(("progress", progress))
                    
                    file_path = os.path.join(root, file)
                    try:
                        if self.is_system_file(file_path):
                            continue
                            
                        last_access = os.path.getatime(file_path)
                        days_unused = (time.time() - last_access) / (24 * 3600)
                        
                        if days_unused > 90:
                            program_dir = os.path.dirname(file_path)
                            total_size = self.get_file_size(program_dir)
                            
                            if total_size > 100 * 1024 * 1024:
                                impact = self.analyze_program_impact(file_path)
                                if impact == "影响较小":
                                    try:
                                        shutil.rmtree(program_dir)
                                        self.msg_queue.put(f"已删除: {program_dir}\n")
                                        total_cleaned += total_size
                                    except:
                                        self.msg_queue.put(f"删除失败: {program_dir}\n")
                    except:
                        continue
        
        total_cleaned_mb = total_cleaned / (1024 * 1024)
        if total_cleaned_mb >= 1024:
            total_cleaned_gb = total_cleaned_mb / 1024
            self.msg_queue.put(f"\n一键清理完成! 共释放空间: {total_cleaned_gb:.2f}GB\n")
        else:
            self.msg_queue.put(f"\n一键清理完成! 共释放空间: {total_cleaned_mb:.2f}MB\n")
        self.msg_queue.put(("progress", 100))

    def quick_clean(self):
        """一键清理所有影响较小的程序"""
        self.msg_queue.put("开始一键清理...\n")
        self.progress_var.set(0)
        
        # 在新线程中运行清理任务
        threading.Thread(target=self.quick_clean_worker, daemon=True).start()

    def show_folder_file_sizes(self):
        """选择一个文件夹/磁盘，显示从大到小从上到下排序的文件夹/文件"""
        path = filedialog.askdirectory(title="选择要扫描的文件夹/磁盘")
        if not path:
            return

        self.log_text.insert("end", f"开始扫描 {path} 中的文件夹/文件...\n")
        self.root.update()

        # 清空现有列表
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 获取所有文件夹和文件的大小
        sizes = []
        for root, dirs, files in os.walk(path):
            for d in dirs:
                dir_path = os.path.join(root, d)
                try:
                    size = self.get_file_size(dir_path)
                    sizes.append((dir_path, size))
                except:
                    continue
            for f in files:
                file_path = os.path.join(root, f)
                try:
                    size = os.path.getsize(file_path)
                    sizes.append((file_path, size))
                except:
                    continue

        # 按大小排序
        sizes.sort(key=lambda x: x[1], reverse=True)

        # 显示所有文件夹和文件
        for item_path, size in sizes:
            size_mb = size / (1024 * 1024)
            size_gb = size_mb / 1024

            if size_gb >= 1:
                size_str = f"{size_gb:.2f}GB"
            else:
                size_str = f"{size_mb:.2f}MB"

            self.tree.insert("", "end", values=(
                item_path,
                "",
                size_str,
                "双击打开目录"
            ))

        self.log_text.insert("end", "扫描完成!\n")
        self.log_text.see("end")

    def auto_clean_recycle_bin(self):
        """自动清理回收站中的文件和文件夹"""
        self.log_text.insert("end", "开始自动清理回收站...\n")
        self.root.update()

        shell = win32com.client.Dispatch("Shell.Application")
        recycle_bin = shell.NameSpace(0x0A)
        for item in recycle_bin.Items():
            item_path = item.Path
            try:
                if os.path.isfile(item_path):
                    os.chmod(item_path, stat.S_IWRITE)  # 移除只读属性
                    os.unlink(item_path)
                else:
                    for root, dirs, files in os.walk(item_path):
                        for d in dirs:
                            os.chmod(os.path.join(root, d), stat.S_IWRITE)
                        for f in files:
                            os.chmod(os.path.join(root, f), stat.S_IWRITE)
                    shutil.rmtree(item_path, ignore_errors=True)

                self.log_text.insert("end", f"已彻底删除: {item_path}\n")
            except Exception as e:
                continue

        self.log_text.insert("end", "回收站清理完成!\n")
        self.log_text.see("end")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    print(os.path.join(os.path.dirname(sys.executable), "handle.exe"))
    app = DiskCleaner()
    app.run()
