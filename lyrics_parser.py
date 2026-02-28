# -*- coding: utf-8 -*-
"""
歌词解析模块
支持LRC、TTML格式
"""

import re
import base64


class LyricsParser:
    """歌词解析器"""
    
    @staticmethod
    def parse_lrc(lrc_text):
        """解析LRC格式歌词"""
        lyrics = []
        if not lrc_text:
            return lyrics
            
        # LRC格式: [mm:ss.xx]歌词内容
        pattern = r'\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)'
        
        for line in lrc_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            matches = re.findall(pattern, line)
            for match in matches:
                minutes = int(match[0])
                seconds = int(match[1])
                ms_str = match[2]
                if len(ms_str) == 2:
                    ms = int(ms_str) * 10
                else:
                    ms = int(ms_str)
                
                time_seconds = minutes * 60 + seconds + ms / 1000.0
                text = match[3].strip()
                
                if text:
                    lyrics.append((time_seconds, text))
        
        lyrics.sort(key=lambda x: x[0])
        return lyrics
    
    @staticmethod
    def parse_ttml(ttml_text):
        """解析TTML格式歌词"""
        lyrics = []
        if not ttml_text:
            return lyrics
        
        # 简单TTML解析
        pattern = r'<p[^>]*begin="(\d{2}):(\d{2}):(\d{2})\.(\d{2})"[^>]*>([^<]*)</p>'
        
        for match in re.finditer(pattern, ttml_text):
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            ms = int(match.group(4)) * 10
            
            time_seconds = hours * 3600 + minutes * 60 + seconds + ms / 1000.0
            text = match.group(5).strip()
            
            if text:
                text = re.sub(r'<[^>]+>', '', text)
                lyrics.append((time_seconds, text))
        
        if not lyrics:
            # 尝试简单格式
            pattern = r'<p[^>]*begin="(\d{2}):(\d{2})\.(\d{2})"[^>]*>([^<]*)</p>'
            for match in re.finditer(pattern, ttml_text):
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                ms = int(match.group(3)) * 10
                
                time_seconds = minutes * 60 + seconds + ms / 1000.0
                text = match.group(4).strip()
                
                if text:
                    text = re.sub(r'<[^>]+>', '', text)
                    lyrics.append((time_seconds, text))
        
        lyrics.sort(key=lambda x: x[0])
        return lyrics
    
    @staticmethod
    def parse_sylt(sylt_data):
        """解析SYLT同步歌词帧"""
        lyrics = []
        
        if not sylt_data:
            return lyrics
            
        try:
            # sylt_data 格式: [(time_ms, text), ...]
            for time_ms, text in sylt_data:
                time_seconds = time_ms / 1000.0
                if text:
                    lyrics.append((time_seconds, text))
        except:
            pass
        
        return lyrics


class MetadataParserAlternative:
    """
    替代元数据解析器 - 使用mutagen库
    """
    
    def __init__(self):
        self.metadata = None
        
    def parse(self, file_path):
        """解析音乐文件元数据"""
        from pathlib import Path
        from mutagen import File
        from mutagen.id3 import ID3, USLT, SYLT, ID3NoHeaderError
        from mutagen.mp4 import MP4
        from mutagen.flac import FLAC
        
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        result = {
            'title': file_path.stem,
            'artist': '未知艺术家',
            'album': '未知专辑',
            'duration': 0,
            'cover_data': None,
            'cover_type': None,
            'lyrics': [],
        }
        
        if not file_path.exists():
            return result
        
        try:
            if extension == '.mp3':
                result = self._parse_mp3(file_path, result)
            elif extension == '.flac':
                result = self._parse_flac(file_path, result)
            elif extension in ['.m4a', '.mp4']:
                result = self._parse_m4a(file_path, result)
            elif extension == '.wav':
                result = self._parse_wav(file_path, result)
            else:
                result = self._parse_generic(file_path, result)
        except Exception as e:
            print(f"[MetadataParser] Error: {e}")
        
        return result
    
    def _parse_mp3(self, file_path, result):
        """解析MP3元数据"""
        from mutagen import File
        from mutagen.id3 import ID3, USLT, SYLT, ID3NoHeaderError
        
        try:
            id3 = ID3(file_path)
            
            # 提取基本元数据
            if id3.get('TIT2'):
                result['title'] = str(id3.get('TIT2'))
            if id3.get('TPE1'):
                result['artist'] = str(id3.get('TPE1'))
            if id3.get('TALB'):
                result['album'] = str(id3.get('TALB'))
            
            # 提取封面
            for key in id3.keys():
                if 'APIC' in key:
                    frame = id3[key]
                    if hasattr(frame, 'data'):
                        result['cover_data'] = base64.b64encode(frame.data).decode()
                        result['cover_type'] = getattr(frame, 'mime', 'image/jpeg') or 'image/jpeg'
                    break
            
            # 提取歌词 - USLT
            lyrics_found = False
            for key in id3.keys():
                if 'USLT' in key:
                    frame = id3[key]
                    if hasattr(frame, 'text'):
                        text = frame.text
                        if isinstance(text, bytes):
                            text = self._decode_bytes(text)
                        if text:
                            result['lyrics'] = LyricsParser.parse_lrc(text)
                            lyrics_found = True
                            break
            
            # 提取歌词 - SYLT (如果没找到USLT)
            if not lyrics_found:
                for key in id3.keys():
                    if 'SYLT' in key:
                        frame = id3[key]
                        if hasattr(frame, 'lyrics') and frame.lyrics:
                            result['lyrics'] = LyricsParser.parse_sylt(frame.lyrics)
                            break
            
            # 获取时长
            audio = File(file_path)
            if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                result['duration'] = audio.info.length
                
        except Exception as e:
            print(f"[MP3 Parser] Error: {e}")
        
        return result
    
    def _parse_flac(self, file_path, result):
        """解析FLAC元数据"""
        from mutagen.flac import FLAC
        
        try:
            audio = FLAC(file_path)
            
            if audio.get('TITLE'):
                result['title'] = audio.get('TITLE')[0]
            if audio.get('ARTIST'):
                result['artist'] = audio.get('ARTIST')[0]
            if audio.get('ALBUM'):
                result['album'] = audio.get('ALBUM')[0]
            
            # 封面
            if audio.pictures:
                picture = audio.pictures[0]
                result['cover_data'] = base64.b64encode(picture.data).decode()
                result['cover_type'] = picture.mime or 'image/jpeg'
            
            # 歌词
            lyrics_data = audio.get('LYRICS')
            if lyrics_data and lyrics_data[0]:
                result['lyrics'] = LyricsParser.parse_lrc(lyrics_data[0])
            
            # 时长
            if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                result['duration'] = audio.info.length
                
        except Exception as e:
            print(f"[FLAC Parser] Error: {e}")
        
        return result
    
    def _parse_m4a(self, file_path, result):
        """解析M4A元数据"""
        from mutagen.mp4 import MP4
        
        try:
            audio = MP4(file_path)
            
            if audio.get('\xa9nam'):
                result['title'] = audio.get('\xa9nam')[0]
            if audio.get('\xa9ART'):
                result['artist'] = audio.get('\xa9ART')[0]
            if audio.get('\xa9alb'):
                result['album'] = audio.get('\xa9alb')[0]
            
            # 封面
            if audio.get('covr'):
                cover_data = audio.get('covr')[0]
                if isinstance(cover_data, bytes):
                    result['cover_data'] = base64.b64encode(cover_data).decode()
                    result['cover_type'] = 'image/png'
            
            # 歌词
            if audio.get('\xa9lyr'):
                result['lyrics'] = LyricsParser.parse_lrc(audio.get('\xa9lyr')[0])
            
            # 时长
            if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                result['duration'] = audio.info.length
                
        except Exception as e:
            print(f"[M4A Parser] Error: {e}")
        
        return result
    
    def _parse_wav(self, file_path, result):
        """解析WAV元数据"""
        # WAV通常没有标准元数据
        import wave
        try:
            with wave.open(str(file_path), 'rb') as w:
                frames = w.getnframes()
                rate = w.getframerate()
                result['duration'] = frames / rate if rate > 0 else 0
        except:
            pass
        return result
    
    def _parse_generic(self, file_path, result):
        """通用解析"""
        from mutagen import File
        try:
            audio = File(file_path)
            if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                result['duration'] = audio.info.length
        except:
            pass
        return result
    
    def _decode_bytes(self, data):
        """解码字节数据"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'latin-1']
        for enc in encodings:
            try:
                return data.decode(enc)
            except:
                continue
        return data.decode('utf-8', errors='ignore')