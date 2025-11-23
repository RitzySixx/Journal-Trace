# Journal Trace

![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Forensics](https://img.shields.io/badge/Forensics-Tool-green?style=for-the-badge)
![Version](https://img.shields.io/badge/Version-1.0.0-blue?style=for-the-badge)

A modern Windows USN Journal analyzer that provides comprehensive file system activity tracking with an advanced glass-morphism interface.

## What's New in v1.0.0

### Premium Glass-Morphism UI
- **Advanced Visual Design** - Complete glass-morphism interface with backdrop filters
- **Expanded Grid Layout** - Comprehensive view with USN numbers, filenames, actions, paths, and timestamps
- **Smooth Animations** - Enhanced transitions and hover effects throughout
- **Virtual Scrolling** - Optimized performance for large datasets with thousands of entries

### Technical Innovations
- **Ultra-Fast Scanning** - Multi-drive parallel processing with optimized buffers
- **Advanced Path Resolution** - MFT-based path caching for accurate file tracking
- **Virtual Scrolling Engine** - Handles millions of entries with smooth performance
- **Smart Memory Management** - Optimized caching and garbage collection

### Enhanced Analysis Capabilities
- **Comprehensive USN Parsing** - Full USN Journal extraction from all NTFS drives
- **File Activity Tracking** - Complete timeline of file creations, deletions, renames, and modifications
- **Download Sequence Detection** - Intelligent tracking of file download and completion patterns
- **Rename Group Analysis** - Advanced detection and grouping of file rename operations

## Activity Matrix

| Activity Type | Description |
|---------------|-------------|
| **File Create** | New file creation events |
| **File Delete** | File deletion operations |
| **Rename Operations** | File rename tracking with old/new names |
| **Data Extend** | File size extension activities |
| **Data Overwrite** | File content overwrite operations |
| **Security Changes** | Security descriptor modifications |
| **Download Tracking** | Browser download sequence detection |

## Installation

### Option 1: Using Pre-built Executable (Recommended)
1. Download the latest `JournalTrace.exe` from Releases
2. Run `JournalTrace.exe` directly - no installation required!

### Option 2: Build from Source
1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/JournalTrace.git
   cd JournalTrace
   ```

2. **Install Python dependencies**
   ```bash
   pip install pywebview
   ```

3. **Run the application**
   ```bash
   python JournalTrace.py
   ```

### Option 3: Build Executable
```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --hidden-import="webview" --hidden-import="webview.platforms.win32" JournalTrace.py
```

## Usage

### Quick Start
1. **Launch**: Run JournalTrace.exe (Administrator rights recommended)
2. **Scan**: Click "Scan All Drives" to parse USN Journal from all NTFS drives
3. **Review**: Examine results with color-coded activity types
4. **Filter**: Use search and toggle filters to focus on specific activities

### Interface Controls
- **Scan All Drives** - Comprehensive USN Journal parsing from all available NTFS drives
- **Stop Scan** - Cancel ongoing scan operation
- **Clear Results** - Reset the results grid
- **Export Results** - Save analysis to CSV format
- **Search Bar** - Real-time filtering by filename, path, or USN number
- **Toggle Filters** - Filter by: File Create, File Delete, Rename, Data Extend, Data Overwrite, Data Truncation, Security Change, Basic Info Change, Stream Change, Close

### Advanced Features
- **File Information Modal** - Detailed view of file activity sequences
- **Context Menu Actions** - Right-click for copy USN, copy path, and file info
- **Drag Window** - Click and drag title bar to move the frameless window
- **Real-time Progress** - Live progress tracking during multi-drive scanning
- **Virtual Scrolling** - Smooth navigation through thousands of entries

## Interface Preview

The v1.0.0 interface features:
- **Expanded Grid View** - 5-column layout showing comprehensive file activity details
- **Visual Indicators** - Color-coded activity types for quick identification
- **Download Tracking** - Special highlighting for browser download sequences
- **Premium Styling** - Advanced glass effects with backdrop filters
- **Responsive Design** - Optimized for various screen sizes

## Technical Details

### Backend Architecture
- **Python Core** - Robust USN Journal parsing engine with Windows API integration
- **Direct Drive Access** - Low-level drive access for comprehensive journal extraction
- **Multi-threading** - Concurrent drive processing for optimal performance
- **MFT Path Resolution** - Advanced path reconstruction from Master File Table

### Analysis Engine
- **USN Journal Parsing** - Complete extraction of Update Sequence Number records
- **File Reference Tracking** - Advanced file and directory reference correlation
- **Rename Detection** - Intelligent grouping of rename operations
- **Download Sequence Analysis** - Pattern recognition for browser download activities

### Performance Optimizations
- **Virtual Scrolling** - Efficient rendering of large datasets
- **Smart Caching** - Optimized memory usage with intelligent cache management
- **Parallel Processing** - Simultaneous multi-drive scanning
- **Buffer Optimization** - 8MB buffers for ultra-fast journal reading

## System Requirements

- **OS**: Windows 7 or newer (Windows 10/11 recommended)
- **File System**: NTFS drives only
- **Architecture**: x64 or x86
- **RAM**: 4GB minimum (8GB recommended for large journals)
- **Storage**: 100MB free space
- **Permissions**: Administrator rights required for full drive access

## Reporting Issues

Found a bug or have a feature request? Please open an issue with:
- Detailed description of the problem
- Steps to reproduce
- Screenshots (if applicable)
- Your system specifications

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is designed for legitimate digital forensics, system administration, and security analysis purposes. Users are responsible for complying with local laws and regulations regarding system analysis. Use only on systems you own or have explicit permission to analyze.
