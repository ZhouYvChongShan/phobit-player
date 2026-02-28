```markdown




# ?? Phobit Player

**具有iOS风格毛玻璃效果的本地音乐播放器**

[![GitHub release](
https://img.shields.io/github/v/release/ZhouYvChongShan/phobit-player?include_prereleases&style=flat-square)](https://github.com/ZhouYvChongShan/phobit-player/releases)
[![GitHub license](
https://img.shields.io/github/license/ZhouYvChongShan/phobit-player?style=flat-square)](https://github.com/ZhouYvChongShan/phobit-player/blob/main/LICENSE)
[![GitHub stars](
https://img.shields.io/github/stars/ZhouYvChongShan/phobit-player?style=flat-square)](https://github.com/ZhouYvChongShan/phobit-player/stargazers)
[![GitHub downloads](
https://img.shields.io/github/downloads/ZhouYvChongShan/phobit-player/total?style=flat-square)](https://github.com/ZhouYvChongShan/phobit-player/releases)
[![GitHub issues](
https://img.shields.io/github/issues/ZhouYvChongShan/phobit-player?style=flat-square)](https://github.com/ZhouYvChongShan/phobit-player/issues)
[![Build status](
https://img.shields.io/github/actions/workflow/status/ZhouYvChongShan/phobit-player/build.yml?branch=main&style=flat-square)](https://github.com/ZhouYvChongShan/phobit-player/actions)

[![Python](
https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![PyQt5](
https://img.shields.io/badge/PyQt5-5.15-41CD52?style=flat-square&logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![OpenCV](
https://img.shields.io/badge/OpenCV-4.8-5C3EE8?style=flat-square&logo=opencv&logoColor=white)](https://opencv.org)
[![Pygame](
https://img.shields.io/badge/Pygame-2.5-9B59B6?style=flat-square&logo=python&logoColor=white)](https://pygame.org)
[![Mutagen](
https://img.shields.io/badge/Mutagen-1.47-FF6B6B?style=flat-square)](https://mutagen.readthedocs.io)
[![NumPy](
https://img.shields.io/badge/NumPy-1.24-013243?style=flat-square&logo=numpy&logoColor=white)](https://numpy.org)
[![PyInstaller](
https://img.shields.io/badge/PyInstaller-6.3-FFD43B?style=flat-square)](https://pyinstaller.org)

[![Windows](
https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white)](https://microsoft.com/windows)
[![GitHub Actions](
https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?style=flat-square&logo=github-actions&logoColor=white)](https://github.com/features/actions)

[![GitHub watchers](
https://img.shields.io/github/watchers/ZhouYvChongShan/phobit-player?style=social)](https://github.com/ZhouYvChongShan/phobit-player/watchers)
[![GitHub forks](
https://img.shields.io/github/forks/ZhouYvChongShan/phobit-player?style=social)](https://github.com/ZhouYvChongShan/phobit-player/network/members)
[![GitHub repo size](
https://img.shields.io/github/repo-size/ZhouYvChongShan/phobit-player?style=flat-square)](https://github.com/ZhouYvChongShan/phobit-player)
[![GitHub last commit](
https://img.shields.io/github/last-commit/ZhouYvChongShan/phobit-player?style=flat-square)](https://github.com/ZhouYvChongShan/phobit-player/commits/main)



---

## ?? 目录

- [? 功能特性](#-功能特性)
- [?? 快速开始](#-快速开始)
- [?? 安装说明](#-安装说明)
- [?? 使用指南](#-使用指南)
- [?? 快捷键](#?-快捷键)
- [??? 技术栈](#?-技术栈)
- [?? 许可证](#-许可证)

## ? 功能特性

### ?? 音乐播放
- 支持 MP3、FLAC、M4A、WAV 格式
- 智能元数据解析（标题、艺术家、专辑、封面）
- 播放进度条拖拽
- 音量控制

### ?? 歌单管理
- 创建自定义歌单
- 添加/移除歌曲
- 歌单内播放（只播放当前歌单歌曲）
- 右键菜单快捷操作

### ?? 歌词显示
- **单句模式**：大字体显示当前歌词
- **多句模式**：完整显示所有歌词，自动计算行高
- 当前歌词高亮放大
- 点击歌词区域切换模式
- OpenCV 双重模糊背景

### ?? 播放模式
| 模式 | 图标 | 说明 |
|------|------|------|
| 顺序播放 | ?? | 列表顺序循环 |
| 单曲循环 | ?? | 重复播放当前歌曲 |
| 随机播放 | ?? | 随机选择下一首 |

### ?? 界面特性
- iOS风格毛玻璃效果
- 现代圆角设计
- 黑白灰配色
- 自适应窗口大小
- 自定义字体支持

## ?? 快速开始

### 下载预编译版本（推荐）

从 [Releases](
https://github.com/ZhouYvChongShan/phobit-player/releases)
 页面下载最新版本的 `PhobitPlayer-版本号.zip`

**系统要求：**
- Windows 10/11 (64位)
- 无需安装其他依赖

**安装步骤：**
```bash
# 1. 下载 ZIP 文件
# 2. 解压到任意目录
# 3. 运行 PhobitPlayer.exe
```

### 从源码运行

```bash
# 克隆仓库
git clone 
https://github.com/ZhouYvChongShan/phobit-player.git
cd phobit-player

# 安装依赖
pip install -r requirements.txt

# 运行
python glassflow_player.py
```

## ?? 安装说明

### 方法一：GitHub Releases（推荐）

1. 访问 [Releases 页面](
https://github.com/ZhouYvChongShan/phobit-player/releases)
2. 下载最新版本的 `PhobitPlayer-版本号.zip`
3. 解压到任意目录
4. 双击运行 `PhobitPlayer.exe`

### 方法二：从源码构建

```bash
# 安装依赖
pip install -r requirements.txt

# 使用 PyInstaller 打包
pyinstaller --noconsole --onefile --name "PhobitPlayer" --add-data "lyrics_parser.py;." --add-data "XIANGCUIJIXUESONG Regular.ttf;." glassflow_player.py
```

### 方法三：GitHub Actions 自动构建

项目使用 GitHub Actions 自动构建 Windows 可执行文件。每次推送到 main 分支都会自动触发构建。

[![Build status](
https://img.shields.io/github/actions/workflow/status/ZhouYvChongShan/phobit-player/build.yml?branch=main&style=flat-square)](https://github.com/ZhouYvChongShan/phobit-player/actions)

## ?? 使用指南

### 添加歌曲
1. 点击顶部工具栏的 `+ 添加歌曲` 按钮
2. 选择本地音乐文件（支持多选）
3. 程序会自动解析元数据并显示在列表中

### 创建歌单
1. 在左侧边栏点击 `+` 按钮
2. 输入歌单名称和描述
3. 点击 `创建` 完成

### 管理歌单
- **添加歌曲到歌单**：右键点击歌曲 → `添加到歌单` → 选择目标歌单
- **从歌单移除**：在歌单视图中右键点击歌曲 → `从歌单移除`
- **删除歌曲**：右键点击歌曲 → `删除`

### 播放控制
- 点击列表中的歌曲开始播放
- 底部播放栏控制播放/暂停、上一首/下一首
- 拖拽进度条跳转
- 点击封面切换到歌词界面

### 歌词界面
- **单句模式**：点击单句歌词进入多句模式
- **多句模式**：点击空白区域返回单句模式
- **自动滚动**：当前歌词自动居中显示
- **字体自适应**：根据窗口大小自动调整字体

### 播放模式切换
点击播放栏的播放模式按钮可在三种模式间切换：
- ?? 顺序播放
- ?? 单曲循环
- ?? 随机播放

## ?? 快捷键

| 快捷键 | 功能 | 图标 |
|--------|------|------|
| `Ctrl + Space` | 播放/暂停 | ?? |
| `Ctrl + ←` | 上一首 | ?? |
| `Ctrl + →` | 下一首 | ?? |
| `Esc` | 退出歌词界面 | ? |

## ??? 技术栈

### 核心框架
| 技术 | 版本 | 用途 |
|------|------|------|
| [Python](
https://python.org)
 | 3.10+ | 主编程语言 |
| [PyQt5](
https://riverbankcomputing.com/software/pyqt/)
 | 5.15 | GUI框架 |
| [OpenCV](
https://opencv.org)
 | 4.8 | 图像处理/模糊背景 |
| [Pygame](
https://pygame.org)
 | 2.5 | 音频播放 |









|------|------|









|------|----------|













```





















```

---










```
