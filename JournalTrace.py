import webview
import os
import sys
import time
import ctypes
from ctypes import wintypes, POINTER, byref, create_unicode_buffer, Structure, sizeof
import json
import threading
from datetime import datetime, timedelta
import csv
import string
import struct

# Check for admin privileges
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()

# Constants
GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

FSCTL_QUERY_USN_JOURNAL = 0x000900f4
FSCTL_READ_USN_JOURNAL = 0x000900bb
FSCTL_ENUM_USN_DATA = 0x000900b3

# USN Reason flags
USN_REASONS = {
    0x00000001: "DATA_OVERWRITE",
    0x00000002: "DATA_EXTEND",
    0x00000004: "DATA_TRUNCATION",
    0x00000010: "NAMED_DATA_OVERWRITE",
    0x00000020: "NAMED_DATA_EXTEND",
    0x00000040: "NAMED_DATA_TRUNCATION",
    0x00000100: "FILE_CREATE",
    0x00000200: "FILE_DELETE",
    0x00000400: "EA_CHANGE",
    0x00000800: "SECURITY_CHANGE",
    0x00001000: "RENAME_OLD_NAME",
    0x00002000: "RENAME_NEW_NAME",
    0x00004000: "INDEXABLE_CHANGE",
    0x00008000: "BASIC_INFO_CHANGE",
    0x00010000: "HARD_LINK_CHANGE",
    0x00020000: "COMPRESSION_CHANGE",
    0x00040000: "ENCRYPTION_CHANGE",
    0x00080000: "OBJECT_ID_CHANGE",
    0x00100000: "REPARSE_POINT_CHANGE",
    0x00200000: "STREAM_CHANGE",
    0x00400000: "TRANSACTED_CHANGE",
    0x00800000: "INTEGRITY_CHANGE",
    0x80000000: "CLOSE"
}

FILE_ATTRIBUTES = {
    0x00000001: "READONLY",
    0x00000002: "HIDDEN",
    0x00000004: "SYSTEM",
    0x00000010: "DIRECTORY",
    0x00000020: "ARCHIVE",
    0x00000080: "NORMAL",
    0x00000100: "TEMPORARY",
    0x00000200: "SPARSE_FILE",
    0x00000400: "REPARSE_POINT",
    0x00000800: "COMPRESSED",
    0x00001000: "OFFLINE",
    0x00002000: "NOT_CONTENT_INDEXED",
    0x00004000: "ENCRYPTED"
}

class JournalScanner:
    def __init__(self):
        self.results = []
        self.is_scanning = False
        self.drive_handles = {}
        self.file_ref_to_path = {}  # Cache for path resolution
        
    def get_reason_string(self, reason_mask):
        reasons = [name for flag, name in USN_REASONS.items() if reason_mask & flag]
        return " | ".join(reasons) if reasons else "UNKNOWN"
    
    def get_file_attributes_string(self, attributes):
        attrs = [name for flag, name in FILE_ATTRIBUTES.items() if attributes & flag]
        return ", ".join(attrs) if attrs else "NORMAL"
    
    def filetime_to_datetime(self, filetime):
        if filetime == 0:
            return None
        try:
            return datetime(1601, 1, 1) + timedelta(microseconds=filetime // 10)
        except:
            return None
    
    def get_drive_handle(self, drive_letter):
        if drive_letter in self.drive_handles:
            return self.drive_handles[drive_letter]
            
        handle = ctypes.windll.kernel32.CreateFileW(
            f"\\\\.\\{drive_letter}:",
            GENERIC_READ,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            None,
            OPEN_EXISTING,
            0,
            None
        )
        
        if handle == INVALID_HANDLE_VALUE:
            error = ctypes.windll.kernel32.GetLastError()
            raise Exception(f"Could not open drive {drive_letter}: Error {error}")
            
        self.drive_handles[drive_letter] = handle
        return handle
    
    def query_usn_journal(self, drive_letter):
        handle = self.get_drive_handle(drive_letter)
        output_buffer = ctypes.create_string_buffer(56)
        bytes_returned = wintypes.DWORD()
        
        success = ctypes.windll.kernel32.DeviceIoControl(
            handle, FSCTL_QUERY_USN_JOURNAL, None, 0,
            output_buffer, 56, ctypes.byref(bytes_returned), None
        )
        
        if not success:
            error = ctypes.windll.kernel32.GetLastError()
            if error == 5:
                raise Exception("Access Denied - Run as Administrator!")
            elif error == 1179:
                raise Exception("USN Journal not active on this drive")
            raise Exception(f"Failed to query USN Journal (Error {error})")
        
        data = output_buffer.raw
        return {
            'journal_id': struct.unpack('<Q', data[0:8])[0],
            'first_usn': struct.unpack('<q', data[8:16])[0],
            'next_usn': struct.unpack('<q', data[16:24])[0],
            'lowest_valid_usn': struct.unpack('<q', data[24:32])[0],
            'max_usn': struct.unpack('<q', data[32:40])[0],
            'max_size': struct.unpack('<Q', data[40:48])[0],
            'allocation_delta': struct.unpack('<Q', data[48:56])[0]
        }
    
    def build_mft_path_cache(self, drive_letter, window=None):
        """Build a cache of file reference numbers to paths using MFT enumeration"""
        handle = self.get_drive_handle(drive_letter)
        journal_info = self.query_usn_journal(drive_letter)
        
        # MFT_ENUM_DATA_V0 structure
        enum_data = struct.pack('<QqQ', 0, 0, journal_info['next_usn'])
        
        buffer_size = 4 * 1024 * 1024  # 4MB buffer for faster scanning
        output_buffer = ctypes.create_string_buffer(buffer_size)
        bytes_returned = wintypes.DWORD()
        
        # Pre-allocate dictionaries
        parent_cache = {}
        path_cache = {5: f"{drive_letter}:\\"}  # Root directory
        
        while self.is_scanning:
            success = ctypes.windll.kernel32.DeviceIoControl(
                handle, FSCTL_ENUM_USN_DATA, enum_data, len(enum_data),
                output_buffer, buffer_size, ctypes.byref(bytes_returned), None
            )
            
            if not success:
                error = ctypes.windll.kernel32.GetLastError()
                if error == 38:  # No more data
                    break
                break
            
            if bytes_returned.value <= 8:
                break
            
            data = output_buffer.raw[:bytes_returned.value]
            next_ref = struct.unpack('<Q', data[0:8])[0]
            
            offset = 8
            while offset + 60 <= len(data):
                record_length = struct.unpack('<I', data[offset:offset+4])[0]
                if record_length == 0 or record_length > buffer_size or offset + record_length > len(data):
                    break
                
                file_ref = struct.unpack('<Q', data[offset+8:offset+16])[0] & 0xFFFFFFFFFFFF
                parent_ref = struct.unpack('<Q', data[offset+16:offset+24])[0] & 0xFFFFFFFFFFFF
                filename_length = struct.unpack('<H', data[offset+56:offset+58])[0]
                filename_offset = struct.unpack('<H', data[offset+58:offset+60])[0]
                
                fn_start = offset + filename_offset
                fn_end = fn_start + filename_length
                
                if fn_end <= len(data):
                    try:
                        filename = data[fn_start:fn_end].decode('utf-16-le', errors='ignore')
                        parent_cache[file_ref] = (parent_ref, filename)
                    except:
                        pass
                
                offset += record_length
            
            enum_data = struct.pack('<QqQ', next_ref, 0, journal_info['next_usn'])
            if next_ref == 0:
                break
        
        # Build full paths - optimized recursive resolution
        def resolve_path(ref, depth=0):
            if depth > 100:  # Prevent infinite recursion
                return f"{drive_letter}:\\"
            if ref in path_cache:
                return path_cache[ref]
            if ref not in parent_cache:
                return f"{drive_letter}:\\"
            
            parent_ref, filename = parent_cache[ref]
            parent_path = resolve_path(parent_ref, depth + 1)
            full_path = os.path.join(parent_path, filename)
            path_cache[ref] = full_path
            return full_path
        
        # Resolve all paths
        for ref in list(parent_cache.keys()):
            if ref not in path_cache:
                try:
                    resolve_path(ref)
                except:
                    pass
        
        return path_cache
    
    def read_usn_journal_fast(self, drive_letter, path_cache, window=None, fast_mode=True):
        """Fast USN Journal reading with optimized processing"""
        handle = self.get_drive_handle(drive_letter)
        journal_info = self.query_usn_journal(drive_letter)
        
        start_usn = 0
        journal_id = journal_info['journal_id']
        
        buffer_size = 8 * 1024 * 1024  # 8MB buffer for ultra-fast scanning
        output_buffer = ctypes.create_string_buffer(buffer_size)
        bytes_returned = wintypes.DWORD()
        
        entries = []
        unique_files = set()
        unique_dirs = set()
        
        while self.is_scanning:
            input_buffer = struct.pack('<qIIQQQ', start_usn, 0xFFFFFFFF, 0, 0, 0, journal_id)
            
            success = ctypes.windll.kernel32.DeviceIoControl(
                handle, FSCTL_READ_USN_JOURNAL, input_buffer, len(input_buffer),
                output_buffer, buffer_size, ctypes.byref(bytes_returned), None
            )
            
            if not success:
                error = ctypes.windll.kernel32.GetLastError()
                if error == 38:  # No more data
                    break
                break
            
            if bytes_returned.value <= 8:
                break
            
            data = output_buffer.raw[:bytes_returned.value]
            new_start_usn = struct.unpack('<q', data[0:8])[0]
            
            offset = 8
            while offset + 60 <= len(data):
                record_length = struct.unpack('<I', data[offset:offset+4])[0]
                if record_length == 0 or record_length > buffer_size or offset + record_length > len(data):
                    break
                
                major_version = struct.unpack('<H', data[offset+4:offset+6])[0]
                if major_version != 2:
                    offset += record_length
                    continue
                
                try:
                    file_ref = struct.unpack('<Q', data[offset+8:offset+16])[0]
                    parent_ref = struct.unpack('<Q', data[offset+16:offset+24])[0]
                    usn = struct.unpack('<q', data[offset+24:offset+32])[0]
                    timestamp = struct.unpack('<Q', data[offset+32:offset+40])[0]
                    reason = struct.unpack('<I', data[offset+40:offset+44])[0]
                    file_attributes = struct.unpack('<I', data[offset+52:offset+56])[0]
                    filename_length = struct.unpack('<H', data[offset+56:offset+58])[0]
                    filename_offset = struct.unpack('<H', data[offset+58:offset+60])[0]
                    
                    fn_start = offset + filename_offset
                    fn_end = fn_start + filename_length
                    
                    if fn_end <= len(data):
                        filename = data[fn_start:fn_end].decode('utf-16-le', errors='ignore')
                        
                        # Fast mode: Skip path resolution for speed
                        if fast_mode:
                            # Use minimal path information for speed
                            parent_ref_index = parent_ref & 0xFFFFFFFFFFFF
                            parent_path = f"{drive_letter}:\\"  # Simplified path
                            full_path = parent_path + filename  # Faster than os.path.join
                        else:
                            # Full path resolution
                            parent_ref_index = parent_ref & 0xFFFFFFFFFFFF
                            parent_path = path_cache.get(parent_ref_index, f"{drive_letter}:\\")
                            full_path = os.path.join(parent_path, filename)
                        
                        is_dir = bool(file_attributes & 0x10)
                        
                        # Track unique files/directories (simplified for speed)
                        if is_dir:
                            unique_dirs.add(filename)
                        else:
                            unique_files.add(filename)
                        
                        ts = self.filetime_to_datetime(timestamp)
                        
                        # Optimized entry creation
                        entry = {
                            'usn': str(usn),
                            'name': filename,
                            'path': full_path,
                            'timestamp': ts.isoformat() if ts else None,
                            'reason': self.get_reason_string(reason),
                            'fileSize': 0,
                            'isDirectory': is_dir,
                            'attributes': self.get_file_attributes_string(file_attributes) if not fast_mode else '',
                            'fileReference': file_ref,
                            'parentFileReference': parent_ref,
                            'originalName': filename,
                            'isRename': bool(reason & 0x30000),
                            'renameType': 'old' if (reason & 0x10000) else ('new' if (reason & 0x20000) else 'none')
                        }
                            
                        entries.append(entry)
                        
                except Exception:
                    # Skip invalid entries quickly
                    pass
                
                offset += record_length
            
            if new_start_usn == 0 or new_start_usn == start_usn:
                break
            
            start_usn = new_start_usn
        
        return entries, len(unique_files), len(unique_dirs)
    
    def get_available_drives(self):
        drives = []
        drive_bits = ctypes.windll.kernel32.GetLogicalDrives()
        
        for letter in string.ascii_uppercase:
            if drive_bits & 1:
                drive_path = f"{letter}:\\"
                try:
                    if os.path.exists(drive_path):
                        fs_buffer = create_unicode_buffer(32)
                        vol_buffer = create_unicode_buffer(256)
                        serial = wintypes.DWORD()
                        max_len = wintypes.DWORD()
                        flags = wintypes.DWORD()
                        
                        if ctypes.windll.kernel32.GetVolumeInformationW(
                            drive_path, vol_buffer, sizeof(vol_buffer),
                            byref(serial), byref(max_len), byref(flags),
                            fs_buffer, sizeof(fs_buffer)
                        ):
                            if fs_buffer.value.upper() == "NTFS":
                                total = ctypes.c_ulonglong()
                                free = ctypes.c_ulonglong()
                                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                                    drive_path, None, byref(total), byref(free)
                                )
                                
                                drives.append({
                                    'letter': letter,
                                    'name': drive_path,
                                    'label': vol_buffer.value or 'Local Disk',
                                    'format': 'NTFS',
                                    'root': drive_path,
                                    'totalFree': f"{free.value / (1024**3):.1f}GB",
                                    'totalSize': f"{total.value / (1024**3):.1f}GB",
                                    'type': 'Fixed',
                                    'isReady': True
                                })
                except:
                    pass
            drive_bits >>= 1
        
        return drives
    
    def scan_all_drives(self, window):
        self.is_scanning = True
        self.results = []
        
        try:
            window.evaluate_js("clearAllResults();")
            
            drives = self.get_available_drives()
            if not drives:
                window.evaluate_js("showError('No NTFS drives found!');")
                return
            
            total_files = 0
            total_dirs = 0
            all_entries = []
            
            # Scan drives in parallel for faster performance
            import concurrent.futures
            drive_results = []
            
            for i, drive_info in enumerate(drives):
                if not self.is_scanning:
                    break
                    
                drive_letter = drive_info['letter']
                
                try:
                    # Update progress for current drive
                    progress = int((i / len(drives)) * 40) + 10  # 10-50% for indexing
                    window.evaluate_js(f"updateStatus('Indexing {drive_letter}:...', {progress}, 0, 'Indexing...', '0/0');")
                    
                    # Phase 1: Build path cache (silent)
                    path_cache = self.build_mft_path_cache(drive_letter, window)
                    
                    # Update progress for reading phase
                    progress = int(((i + 0.5) / len(drives)) * 40) + 50  # 50-90% for reading
                    window.evaluate_js(f"updateStatus('Reading {drive_letter}:...', {progress}, 0, 'Reading...', '0/0');")
                    
                    # Phase 2: Read USN Journal (full mode for better paths)
                    entries, unique_files, unique_dirs = self.read_usn_journal_fast(drive_letter, path_cache, window, fast_mode=False)
                    
                    drive_results.append({
                        'drive': drive_letter,
                        'entries': entries,
                        'unique_files': unique_files,
                        'unique_dirs': unique_dirs,
                        'journal_info': self.query_usn_journal(drive_letter)
                    })
                    
                except Exception as e:
                    error_msg = str(e).replace("'", "\\'")
                    window.evaluate_js(f"showError('Drive {drive_letter}: {error_msg}');")
                    continue
            
            # Combine results from all drives
            journal_info_summary = []
            for result in drive_results:
                total_files += result['unique_files']
                total_dirs += result['unique_dirs']
                all_entries.extend(result['entries'])
                self.results.extend(result['entries'])
                
                # Track journal state for each drive
                info = result['journal_info']
                journal_info_summary.append({
                    'drive': result['drive'],
                    'first_usn': info['first_usn'],
                    'next_usn': info['next_usn'],
                    'max_usn': info['max_usn'],
                    'journal_size': f"{info['max_size'] / (1024**3):.1f}GB",
                    'entries_found': len(result['entries'])
                })  
            
            # Phase 3: Send optimized data to UI at once
            if all_entries:
                # Show journal state information to explain varying results
                journal_summary = f"Journal States: " + ", ".join([f"{j['drive']}:{j['entries_found']} entries" for j in journal_info_summary])
                
                window.evaluate_js(f"updateStatus('Loading {len(all_entries)} entries...', 90, {len(all_entries)}, 'Processing...', '{total_files}/{total_dirs}');")
                
                # Optimize data before sending - keep rename tracking fields for file info feature
                optimized_entries = []
                for entry in all_entries:
                    # Keep essential fields AND rename tracking fields for file info functionality
                    optimized_entry = {
                        'usn': entry['usn'],
                        'name': entry['name'],
                        'path': entry['path'],
                        'timestamp': entry['timestamp'],
                        'reason': entry['reason'],
                        'isDirectory': entry['isDirectory'],
                        'attributes': entry['attributes'],
                        # Keep rename tracking fields for file info feature
                        'originalName': entry.get('originalName', entry['name']),
                        'isRename': entry.get('isRename', False),
                        'renameType': entry.get('renameType', 'none'),
                        'fileReference': entry.get('fileReference', 0),
                        'parentFileReference': entry.get('parentFileReference', 0),
                        'details': entry.get('details', '')
                    }
                    optimized_entries.append(optimized_entry)
                
                # Send all optimized data at once as JSON
                all_json = json.dumps(optimized_entries)
                window.evaluate_js(f"loadAllEntries({all_json});")
                
                timestamps = [e['timestamp'] for e in all_entries if e['timestamp']]
                oldest = min(timestamps)[:10] if timestamps else 'N/A'
                
                # Enhanced status with journal information and optimization notice
                status_msg = f"⚡ Complete - {len(all_entries)} entries from {len(drives)} drives (Optimized Scan)"
                window.evaluate_js(f"updateStatus('{status_msg}', 100, {len(all_entries)}, '{oldest}', '{total_files}/{total_dirs}');")
                
                # Log journal state for user reference
                print(f"=== Journal State Summary ===")
                for info in journal_info_summary:
                    print(f"Drive {info['drive']}: {info['entries_found']} entries, Journal size: {info['journal_size']}")
                print(f"Total: {len(all_entries)} entries across {len(drives)} drives")
                print("Note: USN journal is a circular buffer - results vary as old entries are overwritten")
                
            else:
                window.evaluate_js("updateStatus('No entries found', 100, 0, 'N/A', '0/0');")
                    
        except Exception as e:
            window.evaluate_js(f"showError('Scan failed: {str(e)}');")
        finally:
            self.is_scanning = False
            window.evaluate_js("scanComplete();")
    
    def get_results(self):
        return self.results
    
    def stop_scan(self):
        self.is_scanning = False
    
    def export_results(self, filename=None):
        if not filename:
            filename = f"journal_trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            # Include rename tracking fields in export
            fieldnames = ['USN', 'Name', 'Path', 'Timestamp', 'Reason', 'IsDirectory', 'Attributes', 
                         'OriginalName', 'IsRename', 'RenameType', 'FileReference', 'ParentFileReference', 'Details']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for entry in self.results:
                writer.writerow({
                    'USN': entry['usn'],
                    'Name': entry['name'],
                    'Path': entry['path'],
                    'Timestamp': entry['timestamp'],
                    'Reason': entry['reason'],
                    'IsDirectory': entry['isDirectory'],
                    'Attributes': entry['attributes'],
                    'OriginalName': entry.get('originalName', ''),
                    'IsRename': entry.get('isRename', False),
                    'RenameType': entry.get('renameType', 'none'),
                    'FileReference': entry.get('fileReference', 0),
                    'ParentFileReference': entry.get('parentFileReference', 0),
                    'Details': entry.get('details', '')
                })
        return filename

class Api:
    def __init__(self):
        self.scanner = JournalScanner()
    
    def get_available_drives(self):
        return self.scanner.get_available_drives()
    
    def start_scan(self):
        if self.scanner.is_scanning or not webview.windows:
            return False
        thread = threading.Thread(target=self.scanner.scan_all_drives, args=(webview.windows[0],))
        thread.daemon = True
        thread.start()
        return True
    
    def stop_scan(self):
        self.scanner.stop_scan()
        return True
    
    def get_results(self):
        return self.scanner.get_results()
    
    def clear_results(self):
        self.scanner.results = []
        return True
    
    def export_results(self):
        try:
            return {'success': True, 'filename': self.scanner.export_results()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def window_minimize(self):
        if webview.windows:
            webview.windows[0].minimize()
        return True
    
    def window_maximize(self):
        if webview.windows:
            webview.windows[0].toggle_fullscreen()
        return True
    
    def window_close(self):
        if webview.windows:
            webview.windows[0].destroy()
        return True
    
    def window_move(self, x, y):
        if webview.windows:
            webview.windows[0].move(x, y)
        return True

def get_web_files_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'web')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')

def create_fallback_html():
    return """<!DOCTYPE html><html><head><title>Journal Trace - Error</title>
<style>body{background:#0f172a;color:white;font-family:Arial;padding:20px;}
.error{color:#ef4444;background:rgba(239,68,68,0.1);padding:20px;border-radius:8px;}</style>
</head><body><h1>Journal Trace</h1><div class="error">Web files not found.</div></body></html>"""

if __name__ == '__main__':
    if not is_admin():
        run_as_admin()
    
    if getattr(sys, 'frozen', False) and sys.platform == 'win32':
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    
    api = Api()
    web_path = get_web_files_path()
    ui_path = os.path.join(web_path, 'UI.html')
    
    url = ui_path if os.path.exists(ui_path) else None
    html = create_fallback_html() if not url else None
    
    window = webview.create_window(
        'Journal Trace - USN Journal Analysis',
        url=url, html=html,
        width=1400, height=900, resizable=True,
        frameless=True, easy_drag=False, min_size=(1000, 700),
        js_api=api
    )
    
    webview.start(debug=False)
