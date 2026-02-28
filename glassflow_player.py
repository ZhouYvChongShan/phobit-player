# -*- coding: utf-8 -*-
"""
Phobit Player
具有iOS风格毛玻璃效果的本地音乐播放器
开发者: ZhouYvChongShan
"""

import sys
import os
import base64
import json
import time
import random
from datetime import datetime

# 初始化pygame混合器
import pygame
pygame.mixer.init()

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QSlider,
    QFrame, QStyle, QScrollArea, QFileDialog, QMenu, QAction, QDialog,
    QButtonGroup, QRadioButton, QLineEdit, QMessageBox, QStackedWidget,
    QSplitter
)
from PyQt5.QtCore import Qt, QTimer, QUrl, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, QRect
from PyQt5.QtGui import (
    QPixmap, QPalette, QBrush, QColor, QPainter, 
    QLinearGradient, QRadialGradient, QFont, QFontDatabase,
    QIcon, QKeyEvent, QImage
)
from PyQt5.QtWidgets import QGraphicsBlurEffect, QGraphicsOpacityEffect

# 导入OpenCV
import cv2
import numpy as np

# 导入歌词解析器
try:
    from lyrics_parser import LyricsParser, MetadataParserAlternative
except ImportError:
    # 如果导入失败，可能是循环导入，重新组织导入
    import lyrics_parser
    LyricsParser = lyrics_parser.LyricsParser
    MetadataParserAlternative = lyrics_parser.MetadataParserAlternative


class PlayMode:
    """播放模式枚举"""
    SEQUENTIAL = 0  # 顺序播放
    SINGLE_CYCLE = 1  # 单曲循环
    SHUFFLE = 2  # 随机播放


class Song:
    """歌曲数据结构"""
    def __init__(self, song_id, file_path, title=None, artist=None, album=None, 
                 duration=0, cover_data=None, cover_type=None, lyrics=None, 
                 play_count=0, last_played=None):
        self.song_id = song_id
        self.file_path = file_path
        self.title = title or os.path.splitext(os.path.basename(file_path))[0]
        self.artist = artist or "未知艺术家"
        self.album = album or "未知专辑"
        self.duration = duration
        self.cover_data = cover_data
        self.cover_type = cover_type
        self.lyrics = lyrics or []
        self.play_count = play_count  # 播放次数
        self.last_played = last_played  # 最后播放时间
        self.primary_color = None  # 封面主色调
        
    def to_dict(self):
        return {
            'song_id': self.song_id,
            'file_path': self.file_path,
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'duration': self.duration,
            'cover_data': self.cover_data,
            'cover_type': self.cover_type,
            'lyrics': self.lyrics,
            'play_count': self.play_count,
            'last_played': self.last_played
        }
    
    @staticmethod
    def from_dict(data):
        return Song(
            song_id=data.get('song_id', 0),
            file_path=data.get('file_path', ''),
            title=data.get('title'),
            artist=data.get('artist'),
            album=data.get('album'),
            duration=data.get('duration', 0),
            cover_data=data.get('cover_data'),
            cover_type=data.get('cover_type'),
            lyrics=data.get('lyrics', []),
            play_count=data.get('play_count', 0),
            last_played=data.get('last_played')
        )


class Playlist:
    """歌单数据结构"""
    def __init__(self, playlist_id, name, description="", cover_data=None, songs=None):
        self.playlist_id = playlist_id
        self.name = name
        self.description = description
        self.cover_data = cover_data
        self.songs = songs or []  # 存储歌曲ID列表
        self.created_at = datetime.now().isoformat()
        
    def to_dict(self):
        return {
            'playlist_id': self.playlist_id,
            'name': self.name,
            'description': self.description,
            'cover_data': self.cover_data,
            'songs': self.songs,
            'created_at': self.created_at
        }
    
    @staticmethod
    def from_dict(data):
        playlist = Playlist(
            playlist_id=data.get('playlist_id', 0),
            name=data.get('name', '新建歌单'),
            description=data.get('description', ''),
            cover_data=data.get('cover_data'),
            songs=data.get('songs', [])
        )
        playlist.created_at = data.get('created_at', datetime.now().isoformat())
        return playlist


class BuiltInMetadataParser:
    """内置元数据解析器"""
    
    SUPPORTED_FORMATS = ['.mp3', '.flac', '.m4a', '.wav']
    
    def __init__(self):
        self.audio_data = None
        
    def is_supported(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.SUPPORTED_FORMATS
    
    def parse(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        
        result = {
            'title': os.path.splitext(os.path.basename(file_path))[0],
            'artist': '未知艺术家',
            'album': '未知专辑',
            'duration': 0,
            'cover_data': None,
            'cover_type': None,
            'lyrics': [],
        }
        
        try:
            with open(file_path, 'rb') as f:
                self.audio_data = f.read()
            
            if ext == '.mp3':
                return self._parse_mp3(result)
            elif ext == '.flac':
                return self._parse_flac(result)
            elif ext == '.m4a':
                return self._parse_m4a(result)
            elif ext == '.wav':
                return self._parse_wav(result)
        except Exception as e:
            print(f"[BuiltIn Parser] Error: {e}")
        
        return result
    
    def _decode_text(self, data, encoding='utf-8'):
        if not data:
            return None
        for enc in [encoding, 'utf-8', 'gbk', 'gb2312', 'latin-1']:
            try:
                return data.decode(enc).strip('\x00').strip()
            except:
                continue
        return data.decode('utf-8', errors='ignore').strip('\x00').strip()
    
    def _syncsafe_int(self, data):
        return (data[0] << 21) | (data[1] << 14) | (data[2] << 7) | data[3]
    
    def _parse_mp3(self, result):
        data = self.audio_data
        if len(data) < 10 or data[:3] != b'ID3':
            return result
            
        version = data[3]
        flags = data[5]
        size = self._syncsafe_int(data[6:10])
        
        offset = 10
        end_offset = offset + size
        
        if flags & 0x40:
            ext_size = (data[offset] << 24) | (data[offset+1] << 16) | (data[offset+2] << 8) | data[offset+3]
            offset += ext_size
        
        while offset < end_offset - 10:
            if version >= 3:
                frame_id = data[offset:offset+4].decode('latin-1', errors='ignore')
                frame_size = (data[offset+4] << 24) | (data[offset+5] << 16) | (data[offset+6] << 8) | data[offset+7]
            else:
                frame_id = data[offset:offset+4].decode('latin-1', errors='ignore')
                frame_size = self._syncsafe_int(data[offset+4:offset+8])
            
            if frame_size <= 0 or offset + frame_size > end_offset:
                break
                
            frame_data_offset = offset + (10 if version >= 3 else 6)
            
            if frame_id == 'TIT2':
                text = self._read_text_frame(data, frame_data_offset, frame_size)
                if text: result['title'] = text
            elif frame_id == 'TPE1':
                text = self._read_text_frame(data, frame_data_offset, frame_size)
                if text: result['artist'] = text
            elif frame_id == 'TALB':
                text = self._read_text_frame(data, frame_data_offset, frame_size)
                if text: result['album'] = text
            elif frame_id == 'APIC':
                cover = self._read_apic_frame(data, frame_data_offset, frame_size)
                if cover:
                    result['cover_data'] = cover['data']
                    result['cover_type'] = cover['mime']
            elif frame_id == 'USLT':
                text = self._read_text_frame(data, frame_data_offset, frame_size)
                if text and '[00:' in text:
                    result['lyrics'] = LyricsParser.parse_lrc(text)
            
            offset += (10 if version >= 3 else 6) + frame_size
        
        return result
    
    def _read_text_frame(self, data, offset, size):
        if size <= 1:
            return None
        try:
            return data[offset+1:offset+size].decode('utf-8', errors='ignore').strip('\x00').strip()
        except:
            return None
    
    def _read_apic_frame(self, data, offset, size):
        if size <= 4:
            return None
        try:
            pos = offset + 1
            mime_end = pos
            while mime_end < offset + size - 1 and data[mime_end] != 0:
                mime_end += 1
            mime = data[pos:mime_end].decode('latin-1', errors='ignore')
            pos = mime_end + 1 + 1
            while pos < offset + size - 1 and data[pos] != 0:
                pos += 1
            pos += 1
            image_data = data[pos:offset+size]
            return {'data': base64.b64encode(image_data).decode(), 'mime': mime or 'image/jpeg'}
        except:
            return None
    
    def _parse_flac(self, result):
        return result
    
    def _parse_m4a(self, result):
        return result
    
    def _parse_wav(self, result):
        return result


class GlassPanel(QFrame):
    """毛玻璃效果面板 - 现代圆角风格"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            GlassPanel {
                background-color: rgba(255, 255, 255, 0.8);
                border-radius: 16px;
            }
        """)


class BlurBackgroundWidget(QWidget):
    """OpenCV模糊背景容器 - 最大模糊"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.current_pixmap = None
        self.blur_radius = 40
        self.setAutoFillBackground(True)  # 确保背景自动填充
        
    def set_blur_background(self, cover_data):
        """使用OpenCV设置最大模糊背景"""
        if not cover_data:
            return
            
        try:
            # 解码base64图片数据
            image_data = base64.b64decode(cover_data)
            
            # 转换为numpy数组供OpenCV使用
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return
                
            # 调整图片大小以匹配窗口
            h, w = img.shape[:2]
            window_size = self.size()
            
            # 如果窗口大小为0，等待下一次调用
            if window_size.width() <= 0 or window_size.height() <= 0:
                return
                
            # 计算缩放比例 - 放大1.5倍确保完全覆盖
            scale = max(window_size.width() / w, window_size.height() / h) * 1.5
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            # 缩放图片
            resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            
            # 应用最大高斯模糊 - 使用最大核 (99x99) 实现极限模糊效果
            # 核大小必须是奇数，99是允许的最大值
            blurred = cv2.GaussianBlur(resized, (99, 99), 0)
            
            # 再次应用模糊以增强效果（双重模糊）
            blurred = cv2.GaussianBlur(blurred, (99, 99), 0)
            
            # 添加半透明黑色蒙版，使歌词更易读
            overlay = np.full(blurred.shape, (0, 0, 0), dtype=np.uint8)
            alpha = 0.35  # 稍微增加透明度使歌词更突出
            blended = cv2.addWeighted(blurred, 1 - alpha, overlay, alpha, 0)
            
            # 转换为RGB格式（OpenCV默认BGR）
            blended_rgb = cv2.cvtColor(blended, cv2.COLOR_BGR2RGB)
            
            # 转换为QPixmap
            height, width, channel = blended_rgb.shape
            bytes_per_line = 3 * width
            q_image = QImage(blended_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
            self.current_pixmap = QPixmap.fromImage(q_image)
            
            # 更新显示
            self.update()
            
        except Exception as e:
            print(f"[OpenCV] Blur error: {e}")
            
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        
        # 绘制背景颜色（作为fallback）
        painter.fillRect(self.rect(), QColor(20, 20, 20, 200))
        
        # 如果有模糊图片，绘制图片
        if self.current_pixmap and not self.current_pixmap.isNull():
            # 计算居中位置
            x = (self.width() - self.current_pixmap.width()) // 2
            y = (self.height() - self.current_pixmap.height()) // 2
            painter.drawPixmap(x, y, self.current_pixmap)
        
        super().paintEvent(event)


class CreatePlaylistDialog(QDialog):
    """创建歌单对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("创建新歌单")
        self.setModal(True)
        self.resize(400, 250)
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
                border-radius: 16px;
            }
            QLabel {
                color: #333333;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QLineEdit {
                border: none;
                border-radius: 8px;
                background-color: #FFFFFF;
                padding: 10px 12px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QLineEdit:focus {
                background-color: #FFFFFF;
                outline: none;
            }
            QTextEdit {
                border: none;
                border-radius: 8px;
                background-color: #FFFFFF;
                padding: 10px 12px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QPushButton {
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton#createBtn {
                background-color: #007AFF;
                color: white;
            }
            QPushButton#createBtn:hover {
                background-color: #0066DD;
            }
            QPushButton#cancelBtn {
                background-color: #E5E5EA;
                color: #000000;
            }
            QPushButton#cancelBtn:hover {
                background-color: #D5D5DA;
            }
        """)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # 歌单名称
        name_label = QLabel("歌单名称")
        name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(name_label)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入歌单名称")
        layout.addWidget(self.name_edit)
        
        # 歌单描述
        desc_label = QLabel("描述 (可选)")
        desc_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        layout.addWidget(desc_label)
        
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("输入歌单描述")
        layout.addWidget(self.desc_edit)
        
        layout.addStretch()
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        
        create_btn = QPushButton("创建")
        create_btn.setObjectName("createBtn")
        create_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(create_btn)
        layout.addLayout(btn_layout)
    
    def get_playlist_info(self):
        return {
            'name': self.name_edit.text().strip(),
            'description': self.desc_edit.text().strip()
        }


class AddToPlaylistDialog(QDialog):
    """添加到歌单对话框"""
    def __init__(self, playlists, song_title, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加到歌单")
        self.setModal(True)
        self.resize(400, 350)
        self.playlists = playlists
        self.song_title = song_title
        self.selected_playlist = None
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
                border-radius: 16px;
            }
            QLabel {
                color: #333333;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                padding: 4px 0;
            }
            QListWidget {
                background-color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-radius: 8px;
            }
            QListWidget::item:hover {
                background-color: rgba(0, 122, 255, 0.1);
            }
            QListWidget::item:selected {
                background-color: #007AFF;
                color: white;
            }
            QPushButton {
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton#addBtn {
                background-color: #007AFF;
                color: white;
            }
            QPushButton#addBtn:hover {
                background-color: #0066DD;
            }
            QPushButton#addBtn:disabled {
                background-color: #CCCCCC;
                color: #888888;
            }
            QPushButton#cancelBtn {
                background-color: #E5E5EA;
                color: #000000;
            }
            QPushButton#cancelBtn:hover {
                background-color: #D5D5DA;
            }
        """)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # 提示信息
        info_label = QLabel(f"选择要将《{self.song_title}》添加到的歌单：")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 歌单列表
        self.playlist_list = QListWidget()
        for playlist in self.playlists:
            item = QListWidgetItem(f"{playlist.name} ({len(playlist.songs)}首)")
            item.setData(Qt.UserRole, playlist)
            self.playlist_list.addItem(item)
        
        self.playlist_list.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.playlist_list)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.add_btn = QPushButton("添加")
        self.add_btn.setObjectName("addBtn")
        self.add_btn.setEnabled(False)
        self.add_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.add_btn)
        layout.addLayout(btn_layout)
        
    def on_selection_changed(self):
        """选择变化时"""
        selected_items = self.playlist_list.selectedItems()
        self.add_btn.setEnabled(len(selected_items) > 0)
        if selected_items:
            self.selected_playlist = selected_items[0].data(Qt.UserRole)
            
    def get_selected_playlist(self):
        return self.selected_playlist


class PlaylistItem(QListWidgetItem):
    """歌单列表项"""
    def __init__(self, playlist, song_count=0):
        super().__init__()
        self.playlist = playlist
        self.song_count = song_count
        self.setText(f"{playlist.name} ({song_count}首)")
        self.setSizeHint(QSize(0, 60))
        self.setFont(QFont("Segoe UI", 12))
        self.setTextAlignment(Qt.AlignVCenter)


class SongItem(QListWidgetItem):
    """歌曲列表项"""
    def __init__(self, song, index):
        super().__init__()
        self.song = song
        self.index = index
        self.setText(f"{index+1}. {song.title} - {song.artist}")
        self.setSizeHint(QSize(0, 50))
        self.setFont(QFont("Segoe UI", 11))
        self.setTextAlignment(Qt.AlignVCenter)


class LyricsView(QWidget):
    """歌词显示界面 - 使用窗口高度/歌词行数计算行高，点击容器返回单句模式"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lyrics = []
        self.current_time = 0
        self.show_single = True  # 单句显示模式
        self.is_seeking = False  # 是否正在拖拽进度
        self.current_lyric_index = -1
        
        # 歌词标签列表
        self.lyric_labels = []
        
        # 加载自定义字体
        self.custom_font = self.load_custom_font()
        
        self.setup_ui()
        
    def load_custom_font(self):
        """加载自定义字体文件"""
        font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "XIANGCUIJIXUESONG Regular.ttf")
        
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                if font_families:
                    custom_font = QFont(font_families[0], 48)
                    custom_font.setBold(True)
                    print(f"[Font] Loaded font: {font_families[0]}")
                    return custom_font
        
        print("[Font] Custom font not found, using SimSun")
        default_font = QFont("SimSun", 48)
        default_font.setBold(True)
        return default_font
        
    def setup_ui(self):
        self.setStyleSheet("background: transparent;")
        
        # OpenCV模糊背景层
        self.blur_layer = BlurBackgroundWidget(self)
        self.blur_layer.lower()
        
        # 主布局 - 使用单一容器
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 顶部弹性空间
        main_layout.addStretch(1)
        
        # ========== 歌词内容容器 - 扩大宽度，设置点击事件 ==========
        self.lyrics_container = QWidget()
        self.lyrics_container.setStyleSheet("background: transparent;")
        self.lyrics_container.setCursor(Qt.PointingHandCursor)  # 设置鼠标指针为手型
        self.lyrics_container.mousePressEvent = self.on_container_clicked  # 绑定点击事件
        
        # 使用 QVBoxLayout 管理所有歌词
        self.container_layout = QVBoxLayout(self.lyrics_container)
        self.container_layout.setContentsMargins(80, 10, 80, 10)  # 扩大左右边距到80px
        self.container_layout.setSpacing(0)  # 间距为0，由固定高度控制
        self.container_layout.setAlignment(Qt.AlignCenter)
        
        # 单句显示标签
        self.single_label = QLabel()
        self.single_label.setAlignment(Qt.AlignCenter)
        self.single_label.setWordWrap(True)
        self.single_label.setFont(self.custom_font)
        self.single_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 48px;
            font-weight: bold;
            background: transparent;
            padding: 20px;
        """)
        self.single_label.mousePressEvent = self.on_single_clicked
        self.single_label.setCursor(Qt.PointingHandCursor)
        self.container_layout.addWidget(self.single_label)
        
        # 多句歌词容器（初始隐藏）
        self.multi_line_container = QWidget()
        self.multi_line_container.setStyleSheet("background: transparent;")
        self.multi_line_container.setCursor(Qt.PointingHandCursor)  # 设置鼠标指针为手型
        self.multi_line_container.mousePressEvent = self.on_container_clicked  # 绑定点击事件
        
        self.multi_line_layout = QVBoxLayout(self.multi_line_container)
        self.multi_line_layout.setContentsMargins(0, 0, 0, 0)
        self.multi_line_layout.setSpacing(0)  # 间距为0，由固定高度控制
        self.multi_line_layout.setAlignment(Qt.AlignCenter)
        self.multi_line_container.hide()
        
        self.container_layout.addWidget(self.multi_line_container)
        
        main_layout.addWidget(self.lyrics_container, 0, Qt.AlignCenter)
        
        # 底部弹性空间
        main_layout.addStretch(1)
        
    def on_container_clicked(self, event):
        """点击容器返回单句歌词界面"""
        if not self.show_single:
            self.show_single = True
            self.single_label.setVisible(True)
            self.multi_line_container.hide()
            self.update_display()
        
    def calculate_line_height(self):
        """根据窗口高度和歌词行数计算每行高度"""
        if not self.lyrics or len(self.lyrics) == 0:
            return 40, 48
            
        # 获取窗口可用高度（减去上下边距）
        available_height = self.height() - 100  # 减去上下留白
        
        # 歌词数量
        lyric_count = len(self.lyrics)
        
        if lyric_count == 0:
            return 40, 48
            
        # 计算每行高度
        # 当前歌词高度 = 其他歌词高度 * 1.2 (大20%)
        # 总高度 = (lyric_count - 1) * base_height + current_height
        # 其中 current_height = base_height * 1.2
        
        # 解方程: available_height = (lyric_count - 1) * base_height + base_height * 1.2
        # available_height = base_height * (lyric_count - 1 + 1.2)
        # available_height = base_height * (lyric_count + 0.2)
        
        base_height = available_height / (lyric_count + 0.2)
        current_height = base_height * 1.2
        
        # 限制最小高度
        base_height = max(20, int(base_height))
        current_height = max(24, int(current_height))
        
        return base_height, current_height
        
    def set_blur_background(self, cover_data):
        """设置OpenCV模糊背景"""
        self.blur_layer.set_blur_background(cover_data)
        
    def set_lyrics(self, lyrics):
        self.lyrics = lyrics
        self.show_single = True
        self.single_label.setVisible(True)
        self.multi_line_container.hide()
        self.current_lyric_index = -1
        self.update_display()
        
    def on_single_clicked(self, event):
        """点击单句显示，切换到多句模式"""
        self.show_single = False
        self.single_label.setVisible(False)
        self.multi_line_container.show()
        self.update_display()
        
    def update_time(self, current_time):
        if not self.is_seeking:
            self.current_time = current_time
            self.update_display()
        
    def update_display(self):
        if not self.lyrics:
            self.single_label.setText("暂无歌词")
            return
        
        if self.show_single:
            # 单句模式
            current_idx = -1
            for i, (t, _) in enumerate(self.lyrics):
                if t <= self.current_time:
                    current_idx = i
                else:
                    break
            
            if current_idx >= 0 and current_idx < len(self.lyrics):
                self.single_label.setText(self.lyrics[current_idx][1])
                self.current_lyric_index = current_idx
            else:
                self.single_label.setText("")
                self.current_lyric_index = -1
        else:
            # 多句模式 - 使用固定行高
            current_idx = -1
            for i, (t, _) in enumerate(self.lyrics):
                if t <= self.current_time:
                    current_idx = i
                else:
                    break
            
            self.current_lyric_index = current_idx
            
            # 计算每行高度
            base_height, current_height = self.calculate_line_height()
            
            # 清除旧的歌词标签
            self.clear_lyric_labels()
            
            # 创建新的歌词标签
            for i, (t, text) in enumerate(self.lyrics):
                label = QLabel(text)
                label.setAlignment(Qt.AlignCenter)
                label.setWordWrap(True)
                label.setStyleSheet("background: transparent; color: #FFFFFF;")
                label.setCursor(Qt.PointingHandCursor)  # 设置鼠标指针为手型
                
                if i == current_idx:
                    # 当前歌词 - 使用当前行高
                    font = QFont()
                    font.setPointSize(int(current_height * 0.7))  # 字体大小约为行高的70%
                    font.setBold(True)
                    label.setFont(font)
                    label.setFixedHeight(current_height)
                    label.setStyleSheet(f"""
                        color: #FFFFFF;
                        background: transparent;
                        font-size: {int(current_height * 0.7)}px;
                        font-weight: bold;
                    """)
                else:
                    # 其他歌词 - 使用基础行高
                    font = QFont()
                    font.setPointSize(int(base_height * 0.7))
                    label.setFont(font)
                    label.setFixedHeight(base_height)
                    label.setStyleSheet(f"""
                        color: #CCCCCC;
                        background: transparent;
                        font-size: {int(base_height * 0.7)}px;
                    """)
                
                self.lyric_labels.append(label)
                self.multi_line_layout.addWidget(label)
    
    def clear_lyric_labels(self):
        """清除所有歌词标签"""
        for label in self.lyric_labels:
            self.multi_line_layout.removeWidget(label)
            label.deleteLater()
        self.lyric_labels.clear()
    
    def resizeEvent(self, event):
        """窗口大小改变时重新计算行高"""
        super().resizeEvent(event)
        if not self.show_single and self.lyrics:
            self.update_display()


class SettingsDialog(QDialog):
    """设置对话框 - 现代圆角风格，显示快捷键说明"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(450, 450)
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
                border-radius: 16px;
            }
            QLabel {
                color: #333333;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                padding: 4px 0;
            }
            QRadioButton {
                color: #333333;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #999999;
                background-color: #FFFFFF;
            }
            QRadioButton::indicator:checked {
                background-color: #007AFF;
                border: 2px solid #007AFF;
            }
            QPushButton {
                border: none;
                border-radius: 8px;
                padding: 8px 24px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#okButton {
                background-color: #007AFF;
                color: white;
            }
            QPushButton#okButton:hover {
                background-color: #0066DD;
            }
            QPushButton#cancelButton {
                background-color: #E5E5EA;
                color: #000000;
            }
            QPushButton#cancelButton:hover {
                background-color: #D5D5DA;
            }
        """)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # 解析器选择
        parser_label = QLabel("元数据解析引擎:")
        parser_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(parser_label)
        
        self.parser_group = QButtonGroup(self)
        
        self.radio_mutagen = QRadioButton("Mutagen解析器 (推荐)")
        self.radio_mutagen.setChecked(True)
        self.parser_group.addButton(self.radio_mutagen, 1)
        
        self.radio_builtin = QRadioButton("内置解析器")
        self.parser_group.addButton(self.radio_builtin, 0)
        
        layout.addWidget(self.radio_mutagen)
        layout.addWidget(self.radio_builtin)
        
        layout.addSpacing(20)
        
        # 快捷键说明
        shortcut_label = QLabel("键盘快捷键")
        shortcut_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(shortcut_label)
        
        # 创建快捷键表格
        shortcut_frame = QFrame()
        shortcut_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 12px;
                padding: 12px;
            }
        """)
        shortcut_layout = QVBoxLayout(shortcut_frame)
        
        shortcuts = [
            ("Ctrl + Space", "播放/暂停"),
            ("Ctrl + ←", "上一首"),
            ("Ctrl + →", "下一首"),
            ("Esc", "退出歌词界面"),
        ]
        
        for key, desc in shortcuts:
            row = QHBoxLayout()
            key_label = QLabel(key)
            key_label.setStyleSheet("""
                font-family: 'Courier New', monospace;
                font-weight: bold;
                color: #007AFF;
                background-color: #F0F0F5;
                padding: 4px 8px;
                border-radius: 4px;
                min-width: 120px;
            """)
            key_label.setAlignment(Qt.AlignCenter)
            
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #333333;")
            
            row.addWidget(key_label)
            row.addWidget(desc_label)
            row.addStretch()
            shortcut_layout.addLayout(row)
        
        layout.addWidget(shortcut_frame)
        
        layout.addStretch()
        
        # 更多功能开发中提示
        dev_label = QLabel("更多功能开发中...")
        dev_label.setAlignment(Qt.AlignCenter)
        dev_label.setStyleSheet("""
            color: #888888;
            background-color: #EEEEEE;
            border-radius: 12px;
            padding: 16px;
            font-size: 14px;
            font-weight: bold;
        """)
        layout.addWidget(dev_label)
        
        # 开发者信息
        author_label = QLabel("开发者: ZhouYvChongShan")
        author_label.setAlignment(Qt.AlignRight)
        author_label.setStyleSheet("color: #999999; font-size: 11px;")
        layout.addWidget(author_label)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.setObjectName("okButton")
        ok_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancelButton")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
    
    def get_parser_type(self):
        return self.parser_group.checkedId()


class AudioPlayer:
    def __init__(self):
        self.current_file = None
        self.is_playing = False
        self.paused = False
        
    def load(self, file_path):
        try:
            pygame.mixer.music.load(file_path)
            self.current_file = file_path
            self.is_playing = False
            self.paused = False
            return True
        except Exception as e:
            print(f"[AudioPlayer] Load error: {e}")
            return False
    
    def play(self):
        try:
            pygame.mixer.music.play()
            self.is_playing = True
            self.paused = False
            return True
        except Exception as e:
            print(f"[AudioPlayer] Play error: {e}")
            return False
    
    def pause(self):
        try:
            pygame.mixer.music.pause()
            self.paused = True
            self.is_playing = False
            return True
        except:
            return False
    
    def unpause(self):
        try:
            pygame.mixer.music.unpause()
            self.paused = False
            self.is_playing = True
            return True
        except:
            return False
    
    def set_volume(self, volume):
        pygame.mixer.music.set_volume(volume)
    
    def is_playing_state(self):
        return pygame.mixer.music.get_busy()


class ProgressBarWidget(QWidget):
    """自定义进度条组件 - 贴底显示，颜色匹配封面"""
    
    progressChanged = pyqtSignal(int)
    sliderPressed = pyqtSignal()
    sliderReleased = pyqtSignal()
    sliderMoved = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(4)  # 固定高度4px
        self.setMinimumWidth(100)
        
        self._value = 0
        self._maximum = 100
        self._minimum = 0
        self._progress_color = QColor(0, 122, 255)  # 默认蓝色
        self._background_color = QColor(229, 229, 234)  # 默认灰色
        
        self._is_pressed = False
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        
    def setRange(self, minimum, maximum):
        """设置范围"""
        self._minimum = minimum
        self._maximum = maximum
        self.update()
        
    def setValue(self, value):
        """设置当前值"""
        self._value = max(self._minimum, min(value, self._maximum))
        self.update()
        
    def value(self):
        return self._value
        
    def maximum(self):
        return self._maximum
        
    def setProgressColor(self, color):
        """设置进度条颜色"""
        self._progress_color = color
        self.update()
        
    def setProgressColorFromImage(self, cover_data):
        """从封面图片提取主色调"""
        if not cover_data:
            return
            
        try:
            # 解码base64图片数据
            image_data = base64.b64decode(cover_data)
            
            # 转换为numpy数组供OpenCV使用
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return
                
            # 调整图片大小以加快处理
            small_img = cv2.resize(img, (100, 100), interpolation=cv2.INTER_AREA)
            
            # 转换为RGB
            rgb_img = cv2.cvtColor(small_img, cv2.COLOR_BGR2RGB)
            
            # 使用更简单的平均色作为主色调
            avg_color = np.mean(rgb_img.reshape(-1, 3), axis=0).astype(int)
            
            # 创建QColor
            color = QColor(avg_color[0], avg_color[1], avg_color[2])
            
            # 提高饱和度，使其更鲜艳
            h, s, v, a = color.getHsv()
            s = min(255, int(s * 1.2))  # 提高饱和度
            v = min(255, int(v * 1.1))  # 稍微提高亮度
            
            self._progress_color = QColor.fromHsv(h, s, v, a)
            
        except Exception as e:
            print(f"[ProgressBar] Color extraction error: {e}")
            self._progress_color = QColor(0, 122, 255)  # 保持默认蓝色
            
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self._is_pressed = True
            self.sliderPressed.emit()
            self.setValueFromPos(event.pos().x())
            
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self._is_pressed:
            self._is_pressed = False
            self.sliderReleased.emit()
            
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self._is_pressed:
            self.setValueFromPos(event.pos().x())
            self.sliderMoved.emit(self._value)
            
    def setValueFromPos(self, x):
        """根据鼠标位置设置值"""
        if self.width() <= 0:
            return
            
        ratio = x / self.width()
        new_value = self._minimum + ratio * (self._maximum - self._minimum)
        new_value = max(self._minimum, min(new_value, self._maximum))
        
        if int(new_value) != self._value:
            self._value = int(new_value)
            self.progressChanged.emit(self._value)
            self.update()
        
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 计算进度宽度
        if self._maximum > self._minimum:
            ratio = (self._value - self._minimum) / (self._maximum - self._minimum)
            progress_width = int(self.width() * ratio)
        else:
            progress_width = 0
            
        # 绘制背景
        painter.fillRect(0, 0, self.width(), self.height(), self._background_color)
        
        # 绘制已播放部分
        if progress_width > 0:
            painter.fillRect(0, 0, progress_width, self.height(), self._progress_color)
            
        # 绘制滑块（悬停或拖拽时显示）
        if self._is_pressed or self.underMouse():
            painter.setBrush(self._progress_color)
            painter.setPen(Qt.NoPen)
            handle_size = 12
            handle_x = max(0, min(progress_width - handle_size // 2, self.width() - handle_size))
            painter.drawEllipse(handle_x, self.height() // 2 - handle_size // 2, handle_size, handle_size)
        
        painter.end()


class GlassFlowPlayer(QMainWindow):
    """主播放器窗口"""
    
    def __init__(self):
        super().__init__()
        self.songs = []
        self.playlists = []  # 歌单列表
        self.current_index = -1
        self.is_playing = False
        self.current_view = "list"
        self.play_start_time = 0
        self.use_mutagen = True  # 默认使用mutagen解析器
        self.current_playlist = None  # 当前选中的歌单
        self.sidebar_visible = True  # 侧边栏可见状态
        self.is_seeking = False  # 是否正在拖拽进度
        self.play_mode = PlayMode.SEQUENTIAL  # 默认顺序播放
        self.shuffle_history = []  # 随机播放历史
        self.current_playlist_songs = []  # 当前播放列表的歌曲索引
        
        # 解析器
        self.builtIn_parser = BuiltInMetadataParser()
        self.mutagen_parser = MetadataParserAlternative()
        
        # 音频播放器
        self.audio_player = AudioPlayer()
        
        # 数据文件路径
        self.data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'songs.json')
        self.playlist_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'playlists.json')
        
        # 加载设置和数据
        self.load_data()
        self.load_playlists()
        
        # 初始化UI
        self.init_ui()
        
        # 定时器
        self.timer = QTimer()
        self.timer.start(100)
        self.timer.timeout.connect(self.update_progress)
        
        # 设置焦点策略，使窗口能够接收键盘事件
        self.setFocusPolicy(Qt.StrongFocus)
        
    def keyPressEvent(self, event: QKeyEvent):
        """键盘事件处理 - 添加快捷键"""
        # Ctrl + Space: 播放/暂停
        if event.key() == Qt.Key_Space and event.modifiers() & Qt.ControlModifier:
            self.toggle_play()
            event.accept()
            return
        
        # Ctrl + Left: 上一首
        if event.key() == Qt.Key_Left and event.modifiers() & Qt.ControlModifier:
            self.play_previous()
            event.accept()
            return
        
        # Ctrl + Right: 下一首
        if event.key() == Qt.Key_Right and event.modifiers() & Qt.ControlModifier:
            self.play_next()
            event.accept()
            return
        
        # Esc: 退出歌词界面
        if event.key() == Qt.Key_Escape and self.current_view == "lyrics":
            self.exit_lyrics_view()
            event.accept()
            return
        
        super().keyPressEvent(event)
        
    def load_playlists(self):
        """加载歌单数据"""
        if os.path.exists(self.playlist_file):
            try:
                with open(self.playlist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for pd in data:
                        self.playlists.append(Playlist.from_dict(pd))
            except Exception as e:
                print(f"[Playlist] Load error: {e}")
        
        # 如果没有歌单，创建默认歌单
        if not self.playlists:
            default_playlist = Playlist(
                playlist_id=1,
                name="默认歌单",
                description="默认播放列表"
            )
            self.playlists.append(default_playlist)
            self.save_playlists()
    
    def save_playlists(self):
        """保存歌单到JSON"""
        try:
            data = [p.to_dict() for p in self.playlists]
            with open(self.playlist_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Playlist] Save error: {e}")
    
    def load_data(self):
        """加载保存的数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.use_mutagen = data.get('use_mutagen', True)
                    songs_data = data.get('songs', [])
                    for sd in songs_data:
                        if os.path.exists(sd.get('file_path', '')):
                            self.songs.append(Song.from_dict(sd))
            except Exception as e:
                print(f"[Data] Load error: {e}")
    
    def save_data(self):
        """保存数据到JSON"""
        try:
            data = {
                'use_mutagen': self.use_mutagen,
                'songs': [s.to_dict() for s in self.songs]
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Data] Save error: {e}")
        
    def parse_metadata(self, file_path):
        """解析元数据"""
        if self.use_mutagen:
            return self.mutagen_parser.parse(file_path)
        else:
            return self.builtIn_parser.parse(file_path)
        
    def init_ui(self):
        self.setWindowTitle("Phobit Player")
        self.setGeometry(100, 100, 1200, 700)
        self.setMinimumSize(900, 600)
        
        # 使用Windows默认框架
        self.setWindowFlags(Qt.Window)
        
        # 主容器 - 使用垂直布局，确保进度条在底部
        self.main_container = QWidget()
        self.main_container.setObjectName("mainContainer")
        self.main_container.setStyleSheet("""
            #mainContainer {
                background-color: #F5F5F5;
            }
        """)
        self.setCentralWidget(self.main_container)
        
        # 主布局 - 垂直布局，从上到下：内容区域、进度条
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== 顶部内容区域（包含侧边栏和右侧内容）==========
        self.top_content = QWidget()
        top_layout = QHBoxLayout(self.top_content)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)
        
        # ========== 左侧侧边栏 ==========
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(250)
        self.sidebar.setStyleSheet("""
            QWidget {
                background-color: #F0F0F0;
                border-right: 1px solid #E0E0E0;
            }
        """)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(16, 24, 16, 24)
        sidebar_layout.setSpacing(16)
        
        # 侧边栏标题
        sidebar_title = QLabel("Phobit")
        sidebar_title_font = QFont("Segoe UI", 20)
        sidebar_title_font.setBold(True)
        sidebar_title.setFont(sidebar_title_font)
        sidebar_title.setStyleSheet("color: #000000; margin-bottom: 8px;")
        sidebar_layout.addWidget(sidebar_title)
        
        # 主菜单 - 只保留音乐库
        self.library_btn = self.create_sidebar_button("🎵 音乐库", True)
        self.library_btn.clicked.connect(self.show_library_view)
        sidebar_layout.addWidget(self.library_btn)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #E0E0E0; max-height: 1px; margin: 16px 0;")
        sidebar_layout.addWidget(separator)
        
        # 歌单标题区域
        playlist_header = QHBoxLayout()
        playlist_title = QLabel("我的歌单")
        playlist_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #666666;")
        
        self.add_playlist_btn = QPushButton("+")
        self.add_playlist_btn.setFixedSize(24, 24)
        self.add_playlist_btn.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0066DD;
            }
        """)
        self.add_playlist_btn.clicked.connect(self.create_playlist)
        
        playlist_header.addWidget(playlist_title)
        playlist_header.addStretch()
        playlist_header.addWidget(self.add_playlist_btn)
        sidebar_layout.addLayout(playlist_header)
        
        # 歌单列表
        self.playlist_list = QListWidget()
        self.playlist_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-radius: 8px;
                margin: 2px 0;
            }
            QListWidget::item:hover {
                background: rgba(0, 0, 0, 0.05);
            }
            QListWidget::item:selected {
                background: rgba(0, 122, 255, 0.1);
                color: #007AFF;
            }
        """)
        self.playlist_list.itemClicked.connect(self.on_playlist_selected)
        self.refresh_playlist_list()
        sidebar_layout.addWidget(self.playlist_list)
        
        sidebar_layout.addStretch()
        
        # 开发者信息
        dev_info = QLabel("ZhouYvChongShan")
        dev_info.setAlignment(Qt.AlignCenter)
        dev_info.setStyleSheet("color: #999999; font-size: 11px; padding: 16px 0;")
        sidebar_layout.addWidget(dev_info)
        
        top_layout.addWidget(self.sidebar)
        
        # ========== 右侧内容区域 ==========
        self.content_area = QWidget()
        self.content_area_layout = QVBoxLayout(self.content_area)
        self.content_area_layout.setContentsMargins(24, 24, 24, 24)
        self.content_area_layout.setSpacing(16)
        
        # ========== 标题栏 ==========
        self.header_layout = QHBoxLayout()
        
        # 主标题 - 默认为"音乐库"，当进入歌单时会显示具体歌单名称
        self.title_label = QLabel("音乐库")
        title_font = QFont("Segoe UI", 28)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #000000;")
        
        # 设置按钮
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #E5E5EA;
                border: none;
                border-radius: 20px;
                font-size: 18px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #D5D5DA;
            }
            QPushButton:pressed {
                background-color: #C5C5CA;
            }
        """)
        self.settings_btn.clicked.connect(self.show_settings)
        
        self.add_btn = QPushButton("+ 添加歌曲")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 8px 24px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0066DD;
            }
            QPushButton:pressed {
                background-color: #0055BB;
            }
        """)
        self.add_btn.clicked.connect(self.add_songs)
        
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.settings_btn)
        self.header_layout.addWidget(self.add_btn)
        
        self.content_area_layout.addLayout(self.header_layout)
        
        # ========== 内容堆叠区域 ==========
        self.content_stack = QStackedWidget()
        
        # 1. 音乐库视图
        self.library_view = self.create_library_view()
        self.content_stack.addWidget(self.library_view)
        
        # 2. 歌单详情视图
        self.playlist_view = self.create_playlist_view()
        self.content_stack.addWidget(self.playlist_view)
        
        # 3. 歌词视图 - 这个会覆盖整个窗口
        self.lyrics_view = LyricsView()
        self.lyrics_view.hide()
        
        self.content_area_layout.addWidget(self.content_stack, 1)
        
        # ========== 播放控制栏 ==========
        self.player_bar = GlassPanel()
        self.player_bar.setFixedHeight(80)
        player_layout = QHBoxLayout(self.player_bar)
        player_layout.setContentsMargins(20, 12, 20, 12)
        player_layout.setSpacing(16)
        
        # 当前播放信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self.current_title_label = QLabel("未选择歌曲")
        self.current_title_label.setStyleSheet("color: #000000; font-size: 14px; font-weight: 600; font-family: 'Segoe UI', sans-serif;")
        self.current_title_label.setMaximumWidth(200)
        
        self.current_artist_label = QLabel("-")
        self.current_artist_label.setStyleSheet("color: #8E8E93; font-size: 12px; font-family: 'Segoe UI', sans-serif;")
        self.current_artist_label.setMaximumWidth(200)
        
        info_layout.addWidget(self.current_title_label)
        info_layout.addWidget(self.current_artist_label)
        
        # 封面 - 只在底部播放栏显示
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(56, 56)
        self.cover_label.setStyleSheet("""
            QLabel {
                border-radius: 12px;
                background-color: #E5E5EA;
            }
        """)
        self.cover_label.mousePressEvent = self.on_cover_clicked
        
        player_layout.addWidget(self.cover_label)
        player_layout.addLayout(info_layout)
        
        # 添加到歌单按钮（加号）
        self.add_to_playlist_btn = QPushButton("+")
        self.add_to_playlist_btn.setFixedSize(36, 36)
        self.add_to_playlist_btn.setStyleSheet("""
            QPushButton {
                background: #007AFF;
                border: none;
                border-radius: 18px;
                font-size: 24px;
                font-weight: bold;
                color: white;
            }
            QPushButton:hover {
                background: #0066DD;
            }
            QPushButton:pressed {
                background: #0055BB;
            }
        """)
        self.add_to_playlist_btn.clicked.connect(self.show_add_to_playlist_dialog)
        player_layout.addWidget(self.add_to_playlist_btn)
        
        # 播放模式按钮
        self.play_mode_btn = QPushButton("🔁 顺序")
        self.play_mode_btn.setFixedSize(80, 36)
        self.play_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 122, 255, 0.1);
                border: 1px solid #007AFF;
                border-radius: 18px;
                font-size: 13px;
                color: #007AFF;
            }
            QPushButton:hover {
                background-color: rgba(0, 122, 255, 0.2);
            }
            QPushButton:pressed {
                background-color: rgba(0, 122, 255, 0.3);
            }
        """)
        self.play_mode_btn.setCursor(Qt.PointingHandCursor)
        self.play_mode_btn.clicked.connect(self.toggle_play_mode)
        player_layout.addWidget(self.play_mode_btn)
        
        # 控制按钮
        controls_layout = QVBoxLayout()
        controls_layout.setAlignment(Qt.AlignCenter)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(16)
        
        prev_btn = QPushButton()
        prev_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        prev_btn.setIconSize(QSize(24, 24))
        prev_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 20px;
                padding: 8px;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 0.05);
            }
        """)
        prev_btn.clicked.connect(self.play_previous)
        
        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_btn.setIconSize(QSize(32, 32))
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                border: none;
                border-radius: 22px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #0066DD;
            }
            QPushButton:pressed {
                background-color: #0055BB;
            }
        """)
        self.play_btn.clicked.connect(self.toggle_play)
        
        next_btn = QPushButton()
        next_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        next_btn.setIconSize(QSize(24, 24))
        next_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 20px;
                padding: 8px;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 0.05);
            }
        """)
        next_btn.clicked.connect(self.play_next)
        
        buttons_layout.addWidget(prev_btn)
        buttons_layout.addWidget(self.play_btn)
        buttons_layout.addWidget(next_btn)
        
        controls_layout.addLayout(buttons_layout)
        player_layout.addLayout(controls_layout, 1)
        
        # 时间显示
        time_layout = QHBoxLayout()
        
        self.current_time_label = QLabel("0:00")
        self.current_time_label.setStyleSheet("color: #8E8E93; font-size: 11px; font-family: 'Segoe UI', sans-serif;")
        
        self.total_time_label = QLabel("0:00")
        self.total_time_label.setStyleSheet("color: #8E8E93; font-size: 11px; font-family: 'Segoe UI', sans-serif;")
        
        time_layout.addWidget(self.current_time_label)
        time_layout.addStretch()
        time_layout.addWidget(self.total_time_label)
        
        # 音量控制
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(8)
        
        volume_icon = QLabel()
        volume_icon.setPixmap(self.style().standardIcon(QStyle.SP_MediaVolume).pixmap(16, 16))
        volume_icon.setStyleSheet("border: none;")
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #E5E5EA;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                height: 14px;
                margin: -5px 0;
                background: #333333;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #000000;
                transform: scale(1.1);
            }
        """)
        self.volume_slider.valueChanged.connect(self.set_volume)
        
        volume_layout.addWidget(volume_icon)
        volume_layout.addWidget(self.volume_slider)
        
        # 将时间显示和音量控制添加到播放栏
        player_layout.addLayout(time_layout)
        player_layout.addLayout(volume_layout)
        
        # 将播放栏添加到内容区域布局
        self.content_area_layout.addWidget(self.player_bar)
        
        top_layout.addWidget(self.content_area, 1)
        
        # 将顶部内容区域添加到主布局
        main_layout.addWidget(self.top_content, 1)
        
        # ========== 底部进度条（贴底，贯穿整个窗口）==========
        self.bottom_progress = ProgressBarWidget()
        self.bottom_progress.setRange(0, 100)
        self.bottom_progress.setValue(0)
        self.bottom_progress.progressChanged.connect(self.on_progress_slider_changed)
        self.bottom_progress.sliderPressed.connect(self.on_progress_slider_pressed)
        self.bottom_progress.sliderReleased.connect(self.on_progress_slider_released)
        self.bottom_progress.sliderMoved.connect(self.on_progress_slider_moved)
        
        # 将进度条添加到主布局的底部
        main_layout.addWidget(self.bottom_progress)
        
        # 加载歌曲列表
        self.refresh_song_list()
        
        # 初始音量
        self.audio_player.set_volume(0.8)
        
        # 歌词视图覆盖整个窗口
        self.setup_lyrics_overlay()
        
    def on_progress_slider_pressed(self):
        """进度条按下事件"""
        self.is_seeking = True
        self.lyrics_view.is_seeking = True
        
    def on_progress_slider_released(self):
        """进度条释放事件"""
        self.is_seeking = False
        self.lyrics_view.is_seeking = False
        
        # 跳转到指定位置
        if self.current_index >= 0:
            value = self.bottom_progress.value()
            song = self.songs[self.current_index]
            seek_time = value / 1000.0  # 转换为秒
            self.play_start_time = time.time() - seek_time
            
            # 使用pygame跳转（需要重新加载）
            self.audio_player.load(song.file_path)
            self.audio_player.play()
            
    def on_progress_slider_moved(self, value):
        """进度条拖拽移动事件"""
        # 更新时间显示
        seek_time = value / 1000.0
        self.current_time_label.setText(self._format_time(seek_time))
        
    def on_progress_slider_changed(self, value):
        """进度条值改变事件"""
        if not self.is_seeking:
            return
        # 更新时间显示
        seek_time = value / 1000.0
        self.current_time_label.setText(self._format_time(seek_time))
        
    def setup_lyrics_overlay(self):
        """设置歌词视图覆盖整个窗口"""
        self.lyrics_overlay = QWidget(self)
        self.lyrics_overlay.setAttribute(Qt.WA_TranslucentBackground)
        self.lyrics_overlay_layout = QVBoxLayout(self.lyrics_overlay)
        self.lyrics_overlay_layout.setContentsMargins(0, 0, 0, 0)
        self.lyrics_overlay_layout.addWidget(self.lyrics_view)
        self.lyrics_overlay.hide()
        self.lyrics_overlay.setGeometry(self.rect())
        
    def resizeEvent(self, event):
        """窗口大小改变时更新歌词覆盖层"""
        super().resizeEvent(event)
        if hasattr(self, 'lyrics_overlay'):
            self.lyrics_overlay.setGeometry(self.rect())
        
    def create_sidebar_button(self, text, active=False):
        """创建侧边栏按钮"""
        btn = QPushButton(text)
        btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px 16px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                color: #333333;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
            QPushButton:checked {
                background-color: rgba(0, 122, 255, 0.1);
                color: #007AFF;
            }
        """)
        btn.setCheckable(True)
        btn.setChecked(active)
        return btn
        
    def create_library_view(self):
        """创建音乐库视图"""
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 歌曲列表容器
        self.list_container = GlassPanel()
        list_inner_layout = QVBoxLayout(self.list_container)
        list_inner_layout.setContentsMargins(12, 12, 12, 12)
        
        self.song_list = QListWidget()
        self.song_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                font-family: 'Segoe UI', sans-serif;
            }
            QListWidget::item {
                background: transparent;
                padding: 8px;
                border-radius: 12px;
            }
            QListWidget::item:hover {
                background: rgba(0, 0, 0, 0.05);
            }
            QListWidget::item:selected {
                background: rgba(0, 122, 255, 0.1);
            }
        """)
        self.song_list.itemClicked.connect(self.on_song_clicked)
        self.song_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.song_list.customContextMenuRequested.connect(self.show_song_context_menu)
        
        list_inner_layout.addWidget(self.song_list)
        
        self.empty_label = QLabel("还没有歌曲\n点击上方\"添加歌曲\"按钮导入音乐")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #8E8E93; font-size: 16px; font-family: 'Segoe UI', sans-serif;")
        list_inner_layout.addWidget(self.empty_label)
        
        layout.addWidget(self.list_container, 1)
        
        return view
        
    def create_playlist_view(self):
        """创建歌单详情视图"""
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 歌单标题 - 显示具体歌单名称
        self.playlist_title_label = QLabel()
        self.playlist_title_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.playlist_title_label.setStyleSheet("color: #000000; margin-bottom: 8px;")
        layout.addWidget(self.playlist_title_label)
        
        # 歌单描述
        self.playlist_desc_label = QLabel()
        self.playlist_desc_label.setStyleSheet("color: #8E8E93; font-size: 13px; margin-bottom: 16px;")
        layout.addWidget(self.playlist_desc_label)
        
        # 歌曲列表容器
        container = GlassPanel()
        inner_layout = QVBoxLayout(container)
        inner_layout.setContentsMargins(12, 12, 12, 12)
        
        self.playlist_song_list = QListWidget()
        self.playlist_song_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                font-family: 'Segoe UI', sans-serif;
            }
            QListWidget::item {
                background: transparent;
                padding: 8px;
                border-radius: 12px;
            }
            QListWidget::item:hover {
                background: rgba(0, 0, 0, 0.05);
            }
            QListWidget::item:selected {
                background: rgba(0, 122, 255, 0.1);
            }
        """)
        self.playlist_song_list.itemClicked.connect(self.on_playlist_song_clicked)
        self.playlist_song_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.playlist_song_list.customContextMenuRequested.connect(self.show_playlist_song_context_menu)
        
        inner_layout.addWidget(self.playlist_song_list)
        
        self.empty_playlist_label = QLabel("歌单暂无歌曲\n右键点击歌曲可添加到歌单")
        self.empty_playlist_label.setAlignment(Qt.AlignCenter)
        self.empty_playlist_label.setStyleSheet("color: #8E8E93; font-size: 16px; font-family: 'Segoe UI', sans-serif;")
        inner_layout.addWidget(self.empty_playlist_label)
        
        layout.addWidget(container, 1)
        
        return view
        
    def refresh_playlist_list(self):
        """刷新歌单列表"""
        self.playlist_list.clear()
        for playlist in self.playlists:
            # 计算歌单歌曲数量
            song_count = len(playlist.songs)
            item = PlaylistItem(playlist, song_count)
            self.playlist_list.addItem(item)
            
    def refresh_playlist_content(self):
        """刷新当前歌单内容"""
        if not self.current_playlist:
            return
            
        self.playlist_song_list.clear()
        self.playlist_title_label.setText(self.current_playlist.name)
        self.playlist_desc_label.setText(self.current_playlist.description or "暂无描述")
        
        # 获取歌单中的歌曲
        playlist_songs = [s for s in self.songs if s.song_id in self.current_playlist.songs]
        
        if playlist_songs:
            self.empty_playlist_label.hide()
            for i, song in enumerate(playlist_songs):
                item = SongItem(song, i)
                self.playlist_song_list.addItem(item)
        else:
            self.empty_playlist_label.show()
            
    def create_playlist(self):
        """创建新歌单"""
        dialog = CreatePlaylistDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            info = dialog.get_playlist_info()
            if info['name']:
                new_id = len(self.playlists) + 1
                playlist = Playlist(
                    playlist_id=new_id,
                    name=info['name'],
                    description=info['description']
                )
                self.playlists.append(playlist)
                self.save_playlists()
                self.refresh_playlist_list()
                
    def on_playlist_selected(self, item):
        """选择歌单"""
        self.current_playlist = item.playlist
        # 更新主标题为歌单名称
        self.title_label.setText(item.playlist.name)
        self.content_stack.setCurrentWidget(self.playlist_view)
        self.refresh_playlist_content()
        
    def show_library_view(self):
        """显示音乐库视图"""
        self.library_btn.setChecked(True)
        self.title_label.setText("音乐库")  # 恢复为"音乐库"
        self.content_stack.setCurrentWidget(self.library_view)
        
    def show_add_to_playlist_dialog(self):
        """显示添加到歌单对话框"""
        if self.current_index < 0:
            QMessageBox.information(self, "提示", "请先选择一首歌曲")
            return
            
        song = self.songs[self.current_index]
        
        dialog = AddToPlaylistDialog(self.playlists, song.title, self)
        if dialog.exec_() == QDialog.Accepted:
            selected_playlist = dialog.get_selected_playlist()
            if selected_playlist:
                # 检查是否已存在
                if song.song_id in selected_playlist.songs:
                    QMessageBox.information(self, "提示", f"《{song.title}》已经在歌单《{selected_playlist.name}》中了")
                else:
                    selected_playlist.songs.append(song.song_id)
                    self.save_playlists()
                    QMessageBox.information(self, "成功", f"《{song.title}》已添加到歌单《{selected_playlist.name}》")
                    
                    # 如果当前正在查看该歌单，刷新显示
                    if self.current_playlist and self.current_playlist.playlist_id == selected_playlist.playlist_id:
                        self.refresh_playlist_content()
        
    def add_song_to_playlist(self, song, playlist):
        """添加歌曲到歌单"""
        if song.song_id not in playlist.songs:
            playlist.songs.append(song.song_id)
            self.save_playlists()
            if self.current_playlist and self.current_playlist.playlist_id == playlist.playlist_id:
                self.refresh_playlist_content()
            return True
        return False
        
    def remove_song_from_playlist(self, song, playlist):
        """从歌单移除歌曲"""
        if song.song_id in playlist.songs:
            playlist.songs.remove(song.song_id)
            self.save_playlists()
            if self.current_playlist and self.current_playlist.playlist_id == playlist.playlist_id:
                self.refresh_playlist_content()
            return True
        return False
            
    def show_song_context_menu(self, position):
        """显示歌曲右键菜单"""
        item = self.song_list.itemAt(position)
        if not item:
            return
            
        # 获取对应的歌曲
        index = self.song_list.row(item)
        song = self.songs[index]
        
        self.show_song_menu(song, index, position, self.song_list.mapToGlobal(position))
            
    def show_playlist_song_context_menu(self, position):
        """显示歌单歌曲右键菜单"""
        item = self.playlist_song_list.itemAt(position)
        if not item or not self.current_playlist:
            return
            
        # 获取对应的歌曲
        index = self.playlist_song_list.row(item)
        playlist_songs = [s for s in self.songs if s.song_id in self.current_playlist.songs]
        if index < len(playlist_songs):
            song = playlist_songs[index]
            song_index = self.songs.index(song)
            self.show_song_menu(song, song_index, position, self.playlist_song_list.mapToGlobal(position), in_playlist=True)
            
    def show_song_menu(self, song, index, position, global_pos, in_playlist=False):
        """显示歌曲右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 8px;
                font-family: 'Segoe UI', sans-serif;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 8px;
            }
            QMenu::item:selected {
                background-color: #007AFF;
                color: white;
            }
        """)
        
        # 播放
        play_action = QAction("播放", self)
        play_action.triggered.connect(lambda: self.play_song(index))
        menu.addAction(play_action)
        
        menu.addSeparator()
        
        # 添加到歌单子菜单
        add_to_playlist_menu = menu.addMenu("添加到歌单")
        for playlist in self.playlists:
            playlist_action = QAction(playlist.name, self)
            playlist_action.triggered.connect(lambda checked, p=playlist: self.add_song_to_playlist(song, p))
            add_to_playlist_menu.addAction(playlist_action)
        
        if in_playlist:
            # 从歌单移除
            remove_action = QAction("从歌单移除", self)
            remove_action.triggered.connect(lambda: self.remove_song_from_playlist(song, self.current_playlist))
            menu.addAction(remove_action)
        
        menu.addSeparator()
        
        # 删除歌曲
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.delete_song(index))
        menu.addAction(delete_action)
        
        menu.exec_(global_pos)
        
    def delete_song(self, index):
        """删除歌曲"""
        if 0 <= index < len(self.songs):
            song = self.songs.pop(index)
            # 从所有歌单中移除
            for playlist in self.playlists:
                if song.song_id in playlist.songs:
                    playlist.songs.remove(song.song_id)
            self.save_data()
            self.save_playlists()
            self.refresh_song_list()
            if self.current_playlist:
                self.refresh_playlist_content()
        
    def set_auto_background(self):
        """设置默认背景"""
        if hasattr(self, 'main_container'):
            self.main_container.setStyleSheet("""
                #mainContainer {
                    background-color: #F5F5F5;
                }
            """)
        
    def set_blur_background(self, cover_data):
        """设置OpenCV模糊背景"""
        if not cover_data:
            self.set_auto_background()
            return
        try:
            # 使用OpenCV处理背景
            self.lyrics_view.set_blur_background(cover_data)
            
            # 解码base64图片数据
            image_data = base64.b64decode(cover_data)
            
            # 转换为numpy数组供OpenCV使用
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                self.set_auto_background()
                return
                
            # 调整图片大小以匹配窗口
            h, w = img.shape[:2]
            window_size = self.size()
            
            # 计算缩放比例
            scale = max(window_size.width() / w, window_size.height() / h) * 1.5
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            # 缩放图片
            resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            
            # 应用最大高斯模糊
            blurred = cv2.GaussianBlur(resized, (99, 99), 0)
            blurred = cv2.GaussianBlur(blurred, (99, 99), 0)  # 双重模糊
            
            # 添加半透明黑色蒙版
            overlay = np.full(blurred.shape, (0, 0, 0), dtype=np.uint8)
            alpha = 0.35
            blended = cv2.addWeighted(blurred, 1 - alpha, overlay, alpha, 0)
            
            # 转换为RGB格式
            blended_rgb = cv2.cvtColor(blended, cv2.COLOR_BGR2RGB)
            
            # 转换为QPixmap
            height, width, channel = blended_rgb.shape
            bytes_per_line = 3 * width
            q_image = QImage(blended_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            
            # 设置背景
            palette = QPalette()
            palette.setBrush(QPalette.Window, QBrush(pixmap))
            self.setPalette(palette)
            self.setAutoFillBackground(True)
            
            if hasattr(self, 'main_container'):
                self.main_container.setStyleSheet("""
                    #mainContainer {
                        background-color: transparent;
                    }
                """)
                    
        except Exception as e:
            print(f"[OpenCV] Background error: {e}")
            self.set_auto_background()
    
    def update_background(self, cover_data):
        """更新背景"""
        if self.current_view == "lyrics":
            self.set_blur_background(cover_data)
        else:
            self.set_auto_background()
    
    def exit_lyrics_view(self):
        """退出歌词视图"""
        self.current_view = "list"
        self.lyrics_view.hide()
        self.lyrics_overlay.hide()
        
        # 显示侧边栏和内容区域
        self.sidebar.show()
        self.content_area.show()
        
        # 根据当前选中的视图显示对应的内容
        if self.library_btn.isChecked():
            self.title_label.setText("音乐库")
            self.content_stack.setCurrentWidget(self.library_view)
        else:
            # 如果当前有选中的歌单，显示歌单标题
            if self.current_playlist:
                self.title_label.setText(self.current_playlist.name)
            self.content_stack.setCurrentWidget(self.playlist_view)
        
        if self.current_index >= 0:
            song = self.songs[self.current_index]
            self.set_auto_background()
    
    def on_cover_clicked(self, event):
        if self.current_view == "list":
            # 切换到歌词视图 - 覆盖整个窗口
            self.current_view = "lyrics"
            self.lyrics_view.show()
            
            # 设置模糊背景
            if self.current_index >= 0:
                song = self.songs[self.current_index]
                self.lyrics_view.set_blur_background(song.cover_data)
                self.set_blur_background(song.cover_data)
            
            # 隐藏侧边栏和内容区域
            self.sidebar.hide()
            self.content_area.hide()
            
            # 显示歌词覆盖层
            self.lyrics_overlay.show()
            self.lyrics_overlay.raise_()
            
            # 设置焦点到窗口，以便接收键盘事件
            self.setFocus()
            
        else:
            self.exit_lyrics_view()
    
    def on_lyrics_view_clicked(self, event):
        """点击歌词界面返回"""
        if self.current_view == "lyrics":
            self.exit_lyrics_view()
    
    def add_songs(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择音乐文件",
            "",
            "音频文件 (*.wav *.mp3 *.flac *.m4a);;所有文件 (*.*)"
        )
        
        if not files:
            return
            
        for file_path in files:
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in ['.wav', '.mp3', '.flac', '.m4a']:
                continue
            
            meta = self.parse_metadata(file_path)
            
            song = Song(
                song_id=len(self.songs) + 1,
                file_path=file_path,
                title=meta.get('title'),
                artist=meta.get('artist'),
                album=meta.get('album'),
                duration=meta.get('duration', 0),
                cover_data=meta.get('cover_data'),
                cover_type=meta.get('cover_type'),
                lyrics=meta.get('lyrics', [])
            )
            
            self.songs.append(song)
        
        self.refresh_song_list()
        self.save_data()
    
    def refresh_song_list(self):
        self.song_list.clear()
        
        if len(self.songs) == 0:
            self.empty_label.show()
            return
        
        self.empty_label.hide()
        
        for i, song in enumerate(self.songs):
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 72))
            
            widget = QWidget()
            widget.setStyleSheet("border: none;")
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(12, 8, 12, 8)
            layout.setSpacing(12)
            
            # 封面
            cover_label = QLabel()
            cover_label.setFixedSize(56, 56)
            
            if song.cover_data:
                try:
                    image_data = base64.b64decode(song.cover_data)
                    pixmap = QPixmap()
                    pixmap.loadFromData(image_data)
                    pixmap = pixmap.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    cover_label.setPixmap(pixmap)
                    cover_label.setStyleSheet("border-radius: 12px;")
                except:
                    cover_label.setStyleSheet("border-radius: 12px; background: linear-gradient(135deg, #667eea, #764ba2);")
            else:
                cover_label.setStyleSheet("border-radius: 12px; background: linear-gradient(135deg, #667eea, #764ba2);")
            
            layout.addWidget(cover_label)
            
            # 信息
            info_layout = QVBoxLayout()
            info_layout.setSpacing(4)
            
            title_label = QLabel(f"{i+1}. {song.title}")
            title_label.setStyleSheet("color: #000000; font-size: 15px; font-weight: 600; font-family: 'Segoe UI', sans-serif;")
            title_label.setMaximumWidth(300)
            
            artist_label = QLabel(song.artist)
            artist_label.setStyleSheet("color: #8E8E93; font-size: 13px; font-family: 'Segoe UI', sans-serif;")
            artist_label.setMaximumWidth(300)
            
            info_layout.addWidget(title_label)
            info_layout.addWidget(artist_label)
            layout.addLayout(info_layout)
            
            layout.addStretch()
            
            self.song_list.addItem(item)
            self.song_list.setItemWidget(item, widget)
    
    def on_song_clicked(self, item):
        index = self.song_list.row(item)
        # 从音乐库点击，设置当前播放列表为所有歌曲
        self.current_playlist_songs = list(range(len(self.songs)))
        self.play_song(index)
            
    def on_playlist_song_clicked(self, item):
        if not self.current_playlist:
            return
        index = self.playlist_song_list.row(item)
        playlist_songs = [s for s in self.songs if s.song_id in self.current_playlist.songs]
        if index < len(playlist_songs):
            song = playlist_songs[index]
            song_index = self.songs.index(song)
            # 设置当前播放列表为歌单中的歌曲
            self.current_playlist_songs = [self.songs.index(s) for s in playlist_songs]
            self.play_song(song_index)
        
    def play_song(self, index):
        if index < 0 or index >= len(self.songs):
            return
        
        self.current_index = index
        song = self.songs[index]
        
        # 更新播放次数
        song.play_count += 1
        song.last_played = datetime.now().isoformat()
        
        if self.audio_player.load(song.file_path):
            self.audio_player.play()
            self.is_playing = True
            self.play_start_time = time.time()
            
            self.current_title_label.setText(song.title)
            self.current_artist_label.setText(song.artist)
            
            self.update_current_cover(song)
            self.update_background(song.cover_data)
            
            self.lyrics_view.set_lyrics(song.lyrics)
            
            self.total_time_label.setText(self._format_time(song.duration))
            
            # 设置进度条范围
            self.bottom_progress.setRange(0, int(song.duration * 1000))
            self.bottom_progress.setValue(0)
            
            # 从封面提取颜色设置进度条
            self.bottom_progress.setProgressColorFromImage(song.cover_data)
            
            self.update_play_button()
            
            self.save_data()
    
    def update_current_cover(self, song):
        if song.cover_data:
            try:
                image_data = base64.b64decode(song.cover_data)
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                pixmap = pixmap.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.cover_label.setPixmap(pixmap)
                self.cover_label.setStyleSheet("border-radius: 12px;")
            except:
                self.cover_label.setStyleSheet("border-radius: 12px; background: linear-gradient(135deg, #667eea, #764ba2);")
        else:
            self.cover_label.setStyleSheet("border-radius: 12px; background: linear-gradient(135deg, #667eea, #764ba2);")
    
    def toggle_play(self):
        if self.current_index < 0 and len(self.songs) > 0:
            self.play_song(0)
            return
        
        if self.is_playing:
            self.audio_player.pause()
            self.is_playing = False
        else:
            if self.audio_player.paused:
                self.audio_player.unpause()
                self.is_playing = True
            elif self.current_index >= 0:
                self.audio_player.play()
                self.is_playing = True
        self.update_play_button()
        
    def play_previous(self):
        if len(self.songs) == 0 or not self.current_playlist_songs:
            return
            
        current_pos = -1
        for i, idx in enumerate(self.current_playlist_songs):
            if idx == self.current_index:
                current_pos = i
                break
                
        if current_pos >= 0:
            if self.play_mode == PlayMode.SHUFFLE:
                # 随机模式：从历史中获取上一首
                if len(self.shuffle_history) > 1:
                    self.shuffle_history.pop()  # 移除当前
                    prev_index = self.shuffle_history[-1]
                    self.play_song(prev_index)
            else:
                # 顺序或单曲循环模式
                new_pos = current_pos - 1
                if new_pos < 0:
                    new_pos = len(self.current_playlist_songs) - 1
                self.play_song(self.current_playlist_songs[new_pos])
        
    def play_next(self):
        if len(self.songs) == 0 or not self.current_playlist_songs:
            return
            
        current_pos = -1
        for i, idx in enumerate(self.current_playlist_songs):
            if idx == self.current_index:
                current_pos = i
                break
                
        if current_pos >= 0:
            if self.play_mode == PlayMode.SHUFFLE:
                # 随机模式：随机选择下一首
                available = [idx for idx in self.current_playlist_songs if idx != self.current_index]
                if available:
                    next_index = random.choice(available)
                    self.shuffle_history.append(next_index)
                    self.play_song(next_index)
            elif self.play_mode == PlayMode.SINGLE_CYCLE:
                # 单曲循环：重新播放当前歌曲
                self.play_song(self.current_index)
            else:
                # 顺序模式
                new_pos = current_pos + 1
                if new_pos >= len(self.current_playlist_songs):
                    new_pos = 0
                self.play_song(self.current_playlist_songs[new_pos])
        
    def update_progress(self):
        if self.is_playing and self.current_index >= 0:
            song = self.songs[self.current_index]
            elapsed = time.time() - self.play_start_time
            position_ms = int(elapsed * 1000)
            
            if not self.is_seeking:  # 如果不是在拖拽进度，才更新时间显示
                self.current_time_label.setText(self._format_time(elapsed))
                self.bottom_progress.setValue(min(position_ms, int(song.duration * 1000)))
            
            self.lyrics_view.update_time(elapsed)
            
            if not self.audio_player.is_playing_state() and not self.audio_player.paused:
                self.is_playing = False
                self.update_play_button()
                self.play_next()
            
    def update_play_button(self):
        if self.is_playing:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            
    def set_volume(self, value):
        self.audio_player.set_volume(value / 100.0)
        
    def _format_time(self, seconds):
        if not seconds or seconds < 0:
            return "0:00"
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"
        
    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        if self.use_mutagen:
            dialog.radio_mutagen.setChecked(True)
        else:
            dialog.radio_builtin.setChecked(True)
            
        if dialog.exec_() == QDialog.Accepted:
            self.use_mutagen = (dialog.get_parser_type() == 1)
            self.save_data()
    
    def toggle_play_mode(self):
        """切换播放模式"""
        self.play_mode = (self.play_mode + 1) % 3
        if self.play_mode == PlayMode.SEQUENTIAL:
            self.play_mode_btn.setText("🔁 顺序")
            self.play_mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 122, 255, 0.1);
                    border: 1px solid #007AFF;
                    border-radius: 18px;
                    font-size: 13px;
                    color: #007AFF;
                }
                QPushButton:hover {
                    background-color: rgba(0, 122, 255, 0.2);
                }
                QPushButton:pressed {
                    background-color: rgba(0, 122, 255, 0.3);
                }
            """)
            self.shuffle_history = []  # 清空随机历史
        elif self.play_mode == PlayMode.SINGLE_CYCLE:
            self.play_mode_btn.setText("🔂 单曲循环")
            self.play_mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: #007AFF;
                    border: 1px solid #007AFF;
                    border-radius: 18px;
                    font-size: 13px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #0066DD;
                }
                QPushButton:pressed {
                    background-color: #0055BB;
                }
            """)
        elif self.play_mode == PlayMode.SHUFFLE:
            self.play_mode_btn.setText("🔀 随机")
            self.play_mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 122, 255, 0.1);
                    border: 1px solid #007AFF;
                    border-radius: 18px;
                    font-size: 13px;
                    color: #007AFF;
                }
                QPushButton:hover {
                    background-color: rgba(0, 122, 255, 0.2);
                }
                QPushButton:pressed {
                    background-color: rgba(0, 122, 255, 0.3);
                }
            """)


def main():
    pygame.init()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Phobit Player")
    player = GlassFlowPlayer()
    player.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()