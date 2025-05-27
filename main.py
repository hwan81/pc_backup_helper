import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import shutil
import threading

APP_NAME = "PC 백업 도우미 (pc_backup_helper)"
DEFAULT_BACKUP_SUBDIR = "PC_Backup_Data"

USER_PROFILE = os.path.expanduser('~')

BACKUP_ITEMS_CONFIG = {
    "바탕화면": os.path.join(USER_PROFILE, 'Desktop'),
    "문서": os.path.join(USER_PROFILE, 'Documents'),
    "다운로드": os.path.join(USER_PROFILE, 'Downloads'),
    "사진": os.path.join(USER_PROFILE, 'Pictures'),
    "음악": os.path.join(USER_PROFILE, 'Music'),
    "동영상": os.path.join(USER_PROFILE, 'Videos'),
    "Edge 즐겨찾기 파일": os.path.join(USER_PROFILE, 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data', 'Default', 'Bookmarks'),
    "Chrome 즐겨찾기 파일": os.path.join(USER_PROFILE, 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default', 'Bookmarks'),
    "GPKI (교육기관용 인증서)": "C:\\GPKI",
    "카카오톡 파일 백업": os.path.join(USER_PROFILE, 'Documents', '카카오톡 받은 파일'),
}

# --- 유틸리티 함수 ---
def get_item_size(item_path):
    if not os.path.exists(item_path):
        return 0
    if os.path.isfile(item_path):
        return os.path.getsize(item_path)
    total_size = 0
    try:
        for dirpath, _, filenames in os.walk(item_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    try:
                        total_size += os.path.getsize(fp)
                    except OSError:
                        pass
    except OSError:
        return 0
    return total_size

def format_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"

class BackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("720x800")
        self.root.configure(bg="#F7F7FA")

        # 스타일 및 폰트 설정
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Custom.TFrame", background="#F7F7FA")
        self.style.configure("Custom.TLabelframe", background="#F7F7FA")
        self.style.configure("Custom.TLabelframe.Label", background="#F7F7FA")
        self.style.configure("Custom.TCheckbutton", background="#F7F7FA")
        self.style.configure("Custom.TRadiobutton", background="#F7F7FA")
        self.style.configure("TLabel", font=("Malgun Gothic", 10), background="#F7F7FA")
        self.style.configure("Header.TLabel", font=("Malgun Gothic", 12), foreground="#000", background="#F7F7FA")
        self.style.configure("SubHeader.TLabel", font=("Malgun Gothic", 10), foreground="#000", background="#F7F7FA")
        self.style.configure("TButton", font=("Malgun Gothic", 13), padding=8)
        self.style.map("TButton",
                       foreground=[('active', '#F7F7FA'), ('!active', '#F7F7FA')],
                       background=[('active', '#2A9D8F'), ('!active', '#3A86FF')])

        self.mode = tk.StringVar(value="backup")
        self.backup_vars = {}
        self.backup_path_labels = {}

        self._create_widgets()
        self._update_all_path_labels_threaded()

    def _create_widgets(self):
        # 상단 타이틀
        ttk.Label(self.root, text=APP_NAME, style="Header.TLabel").pack(pady=(18, 8))
        ttk.Label(self.root, text="성일중학교 이정환 hwan@esungil.ms.kr", style="SubHeader.TLabel").pack(pady=(0, 18))

        # 모드 선택
        mode_frame = ttk.LabelFrame(self.root, text="모드 선택", padding=(10, 10) , style="Custom.TLabelframe")
        mode_frame.pack(padx=18, pady=8, fill="both" , )

        ttk.Radiobutton(mode_frame, text="백업 모드", variable=self.mode, value="backup", style="Custom.TRadiobutton",
                        command=self._update_action_button_text).pack(side="left", padx=8, pady=2 )
        ttk.Radiobutton(mode_frame, text="복구 모드", variable=self.mode, value="restore", style="Custom.TRadiobutton",
                        command=self._update_action_button_text).pack(side="left", padx=8, pady=2)

        # 백업/복구 대상 선택
        items_frame = ttk.LabelFrame(self.root, text="백업/복구 대상 선택", padding=(14, 10) , style="Custom.TLabelframe")
        items_frame.pack(padx=18, pady=8, fill="both", expand=True)



        canvas = tk.Canvas(items_frame, bg="#F7F7FA", highlightthickness=0)
        scrollbar = ttk.Scrollbar(items_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="Custom.TFrame")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw" )
        canvas.configure(yscrollcommand=scrollbar.set )
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for name, path in BACKUP_ITEMS_CONFIG.items():
            item_row = ttk.Frame(scrollable_frame)
            item_row.pack(fill="x", pady=4, padx=0)
            var = tk.BooleanVar()
            self.backup_vars[name] = var
            cb = ttk.Checkbutton(item_row, text=name, variable=var ,style="Custom.TCheckbutton")
            cb.pack(side="left", padx=0)
            path_label_text = f"경로: {path} (크기 계산 중...)" if os.path.exists(path) else f"경로: {path} (경로 없음)"
            path_label = ttk.Label(item_row, text=path_label_text,  justify="left", foreground="#888", background="#F7F7FA")
            path_label.pack(side="left", padx=6, fill="x", expand=True)
            self.backup_path_labels[name] = path_label



        # 실행 버튼 및 로그
        action_frame = ttk.Frame(self.root, padding=(14, 10), style="Custom.TFrame")
        action_frame.pack(padx=18, pady=8, fill="x")
        self.action_button = ttk.Button(action_frame, text="백업 시작", command=self._start_action_threaded, style="Custom.TButton")
        self.action_button.pack(pady=6, fill="x")

        log_frame = ttk.LabelFrame(self.root, text="로그", padding=(14, 10) ,style="Custom.TLabelframe")
        log_frame.pack(padx=18, pady=8, fill="both", expand=True)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, state="disabled", font=("Malgun Gothic", 10))
        self.log_text.pack(fill="both", expand=True)

    def _log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        self.root.update_idletasks()

    def _update_path_label(self, name, path):
        label = self.backup_path_labels.get(name)
        if label:
            if not os.path.exists(path):
                label.config(text=f"경로: {path} (경로 없음)", foreground="#D62828")
                return
            try:
                size_bytes = get_item_size(path)
                formatted_size = format_size(size_bytes)
                label.config(text=f"경로: {path} ({formatted_size})", foreground="#222" if size_bytes > 0 else "#888")
            except Exception as e:
                label.config(text=f"경로: {path} (크기 계산 오류)", foreground="#FFB703")
                self._log(f"오류: {name} 크기 계산 중 오류 발생 - {e}")

    def _update_all_path_labels_threaded(self):
        self._log("경로 정보 업데이트 시작...")
        threading.Thread(target=self._update_all_path_labels_task, daemon=True).start()

    def _update_all_path_labels_task(self):
        for name, path in BACKUP_ITEMS_CONFIG.items():
            self._update_path_label(name, path)
            self.root.update_idletasks()
        self._log("경로 정보 업데이트 완료.")

    def _update_action_button_text(self):
        self.action_button.config(text="백업 시작" if self.mode.get() == "backup" else "복구 시작")

    def _start_action_threaded(self):
        self.action_button.config(state="disabled")
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")

        selected_items = {name: BACKUP_ITEMS_CONFIG[name] for name, var in self.backup_vars.items() if var.get()}
        if not selected_items:
            messagebox.showwarning("선택 필요", "백업 또는 복구할 항목을 하나 이상 선택해주세요.")
            self.action_button.config(state="normal")
            return

        if self.mode.get() == "backup":
            target_dir = filedialog.askdirectory(title="백업 파일을 저장할 폴더 선택")
            if not target_dir:
                self.action_button.config(state="normal")
                return
            backup_root_dir = os.path.join(target_dir, DEFAULT_BACKUP_SUBDIR)
            os.makedirs(backup_root_dir, exist_ok=True)
            threading.Thread(target=self._execute_backup, args=(selected_items, backup_root_dir), daemon=True).start()
        else:
            source_dir = filedialog.askdirectory(title="백업 데이터가 있는 폴더 선택 (예: .../PC_Backup_Data)")
            if not source_dir:
                self.action_button.config(state="normal")
                return
            if not os.path.basename(source_dir) == DEFAULT_BACKUP_SUBDIR:
                potential_backup_root = os.path.join(source_dir, DEFAULT_BACKUP_SUBDIR)
                if os.path.isdir(potential_backup_root):
                    source_dir = potential_backup_root
            self._log(f"복구 시작... 원본 폴더: {source_dir}")
            threading.Thread(target=self._execute_restore, args=(selected_items, source_dir), daemon=True).start()

    def _execute_backup(self, items_to_backup, backup_root_dir):
        total_items = len(items_to_backup)
        for idx, (name, source_path) in enumerate(items_to_backup.items(), 1):
            self._log(f"[{idx}/{total_items}] '{name}' 백업 중... ({source_path})")
            if not os.path.exists(source_path):
                self._log(f"경고: '{name}'의 경로({source_path})가 존재하지 않아 건너뜁니다.")
                continue

            # [수정] 항목별 폴더 생성
            item_folder = os.path.join(backup_root_dir, name.replace(" ", "_"))
            os.makedirs(item_folder, exist_ok=True)
            base_name = os.path.basename(source_path)
            destination_path = os.path.join(item_folder, base_name)

            try:
                if os.path.isfile(source_path):
                    shutil.copy2(source_path, destination_path)
                    self._log(f"파일 백업 완료: '{name}' -> {destination_path}")
                elif os.path.isdir(source_path):
                    # 폴더 내부 전체 복사 (항목 폴더 내에 복사)
                    dest_dir = os.path.join(item_folder, base_name)
                    if os.path.exists(dest_dir):
                        shutil.rmtree(dest_dir)
                    shutil.copytree(source_path, dest_dir)
                    self._log(f"폴더 백업 완료: '{name}' -> {dest_dir}")
            except Exception as e:
                self._log(f"오류: '{name}' 백업 중 오류 발생 - {e}")
        self._log("모든 선택 항목 백업 완료.")
        messagebox.showinfo("백업 완료", f"선택한 항목의 백업이 완료되었습니다.\n저장 위치: {backup_root_dir}")
        self.root.after(0, lambda: self.action_button.config(state="normal"))

    def _execute_restore(self, items_to_restore, backup_source_dir):
        total_items = len(items_to_restore)
        for idx, (name, original_target_path) in enumerate(items_to_restore.items(), 1):
            self._log(f"[{idx}/{total_items}] '{name}' 복구 중... -> {original_target_path}")

            # [수정] 항목별 폴더에서 복원
            item_folder = os.path.join(backup_source_dir, name.replace(" ", "_"))
            base_name = os.path.basename(original_target_path)
            source_path_in_backup = os.path.join(item_folder, base_name)

            if not os.path.exists(source_path_in_backup):
                self._log(f"경고: 백업 데이터 폴더에서 '{name}'의 항목({source_path_in_backup})을 찾을 수 없어 건너뜁니다.")
                continue
            try:
                target_parent_dir = os.path.dirname(original_target_path)
                if target_parent_dir and not os.path.exists(target_parent_dir):
                    os.makedirs(target_parent_dir, exist_ok=True)
                    self._log(f"복구 대상 폴더 생성: {target_parent_dir}")
                if os.path.isfile(source_path_in_backup):
                    shutil.copy2(source_path_in_backup, original_target_path)
                    self._log(f"파일 복구 완료: '{name}' ({source_path_in_backup} -> {original_target_path})")
                elif os.path.isdir(source_path_in_backup):
                    if os.path.exists(original_target_path):
                        if os.path.isdir(original_target_path):
                            shutil.rmtree(original_target_path)
                        else:
                            os.remove(original_target_path)
                        self._log(f"기존 항목 삭제: {original_target_path}")
                    shutil.copytree(source_path_in_backup, original_target_path)
                    self._log(f"폴더 복구 완료: '{name}' ({source_path_in_backup} -> {original_target_path})")
            except Exception as e:
                self._log(f"오류: '{name}' 복구 중 오류 발생 - {e}")
        self._log("모든 선택 항목 복구 완료.")
        messagebox.showinfo("복구 완료", "선택한 항목의 복구가 완료되었습니다.")
        self.root.after(0, lambda: self.action_button.config(state="normal"))


if __name__ == "__main__":
    root = tk.Tk()
    BackupApp(root)
    root.mainloop()
