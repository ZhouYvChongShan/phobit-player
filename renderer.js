/**
 * GlassFlow Music Player - 前端逻辑
 */

class GlassFlowPlayer {
  constructor() {
    // 状态
    this.songs = [];
    this.currentSongIndex = -1;
    this.isPlaying = false;
    this.volume = 0.8;
    
    // DOM元素
    this.elements = {
      // 按钮
      addSongsBtn: document.getElementById('add-songs-btn'),
      playBtn: document.getElementById('play-btn'),
      prevBtn: document.getElementById('prev-btn'),
      nextBtn: document.getElementById('next-btn'),
      
      // 图标
      playIcon: document.getElementById('play-icon'),
      pauseIcon: document.getElementById('pause-icon'),
      
      // 列表
      songList: document.getElementById('song-list'),
      emptyState: document.getElementById('empty-state'),
      
      // 播放器
      audioPlayer: document.getElementById('audio-player'),
      
      // 当前播放信息
      currentCover: document.getElementById('current-cover'),
      currentTitle: document.getElementById('current-title'),
      currentArtist: document.getElementById('current-artist'),
      
      // 进度
      progressBar: document.getElementById('progress-bar'),
      progressFill: document.getElementById('progress-fill'),
      progressHandle: document.getElementById('progress-handle'),
      currentTime: document.getElementById('current-time'),
      totalTime: document.getElementById('total-time'),
      
      // 音量
      volumeSlider: document.getElementById('volume-slider'),
      
      // 背景
      dynamicBackground: document.getElementById('dynamic-background')
    };
    
    // 元数据解析器
    this.metadataExtractor = new MusicMetadataExtractor();
    
    // 初始化
    this.init();
  }
  
  init() {
    console.log('[GlassFlow] Initializing player...');
    
    // 绑定事件
    this.bindEvents();
    
    // 设置音量
    this.elements.audioPlayer.volume = this.volume;
    this.elements.volumeSlider.value = this.volume * 100;
    
    console.log('[GlassFlow] Player initialized');
  }
  
  bindEvents() {
    // 添加歌曲按钮
    this.elements.addSongsBtn.addEventListener('click', () => this.addSongs());
    
    // 播放控制
    this.elements.playBtn.addEventListener('click', () => this.togglePlay());
    this.elements.prevBtn.addEventListener('click', () => this.playPrevious());
    this.elements.nextBtn.addEventListener('click', () => this.playNext());
    
    // 进度条
    this.elements.progressBar.addEventListener('click', (e) => this.seek(e));
    this.elements.audioPlayer.addEventListener('timeupdate', () => this.updateProgress());
    this.elements.audioPlayer.addEventListener('loadedmetadata', () => this.onMetadataLoaded());
    this.elements.audioPlayer.addEventListener('ended', () => this.onSongEnded());
    
    // 音量控制
    this.elements.volumeSlider.addEventListener('input', (e) => this.setVolume(e));
    
    // 键盘快捷键
    document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    
    // 拖放支持
    document.body.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.stopPropagation();
    });
    document.body.addEventListener('drop', (e) => this.handleDrop(e));
  }
  
  /**
   * 添加歌曲
   */
  async addSongs() {
    try {
      const result = await window.electronAPI.openFileDialog();
      
      if (result.canceled || result.filePaths.length === 0) {
        return;
      }
      
      console.log('[GlassFlow] Files selected:', result.filePaths.length);
      
      // 过滤支持的格式
      const validFiles = result.filePaths.filter(filePath => {
        const ext = filePath.toLowerCase().split('.').pop();
        return ['wav', 'mp3', 'flac', 'm4a'].includes(ext);
      });
      
      if (validFiles.length === 0) {
        console.log('[GlassFlow] No valid audio files found');
        return;
      }
      
      // 解析并添加歌曲
      for (const filePath of validFiles) {
        await this.addSong(filePath);
      }
      
    } catch (error) {
      console.error('[GlassFlow] Add songs error:', error);
    }
  }
  
  /**
   * 添加单个歌曲
   */
  async addSong(filePath) {
    try {
      console.log('[GlassFlow] Adding song:', filePath);
      
      // 获取文件信息
      const fileInfo = await window.electronAPI.getFileInfo(filePath);
      
      // 读取文件数据
      const fileResult = await window.electronAPI.readFile(filePath);
      
      if (!fileResult.success) {
        console.error('[GlassFlow] Failed to read file:', fileResult.error);
        return;
      }
      
      // 转换为ArrayBuffer
      const binaryString = atob(fileResult.data);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const audioData = bytes.buffer;
      
      // 解析元数据
      const metadata = await this.metadataExtractor.parseMetadata(audioData, filePath);
      
      // 创建歌曲对象
      const song = {
        id: Date.now() + Math.random(),
        filePath: filePath,
        title: metadata.title,
        artist: metadata.artist,
        album: metadata.album,
        duration: metadata.duration,
        cover: metadata.cover,
        coverType: metadata.coverType,
        format: metadata.format
      };
      
      this.songs.push(song);
      
      // 更新UI
      this.renderSongList();
      
      console.log('[GlassFlow] Song added:', song.title);
      
    } catch (error) {
      console.error('[GlassFlow] Add song error:', error);
    }
  }
  
  /**
   * 渲染歌曲列表
   */
  renderSongList() {
    // 清空列表
    this.elements.songList.innerHTML = '';
    
    // 显示/隐藏空状态
    if (this.songs.length === 0) {
      this.elements.emptyState.style.display = 'flex';
      return;
    }
    
    this.elements.emptyState.style.display = 'none';
    
    // 渲染每个歌曲
    this.songs.forEach((song, index) => {
      const li = document.createElement('li');
      li.className = 'song-item';
      if (index === this.currentSongIndex) {
        li.classList.add('playing');
      }
      
      li.innerHTML = `
        ${song.cover 
          ? `<img class="song-cover" src="data:${song.coverType || 'image/jpeg'};base64,${song.cover}" alt="${song.title}">`
          : `<div class="song-cover-placeholder">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 19V6l12-3v13"></path>
                <circle cx="6" cy="18" r="3"></circle>
                <circle cx="18" cy="16" r="3"></circle>
              </svg>
            </div>`
        }
        <div class="song-info">
          <span class="song-title">${this.escapeHtml(song.title)}</span>
          <span class="song-artist">${this.escapeHtml(song.artist)}</span>
          ${song.album ? `<span class="song-album">${this.escapeHtml(song.album)}</span>` : ''}
        </div>
        <span class="song-duration">${this.formatTime(song.duration)}</span>
      `;
      
      li.addEventListener('click', () => this.playSong(index));
      this.elements.songList.appendChild(li);
    });
  }
  
  /**
   * 播放歌曲
   */
  playSong(index) {
    if (index < 0 || index >= this.songs.length) return;
    
    this.currentSongIndex = index;
    const song = this.songs[index];
    
    console.log('[GlassFlow] Playing:', song.title);
    
    // 设置音频源
    // 使用file://协议播放本地文件
    const filePath = song.filePath.replace(/\\/g, '/');
    this.elements.audioPlayer.src = `file:///${filePath}`;
    
    // 更新UI
    this.updateCurrentTrackInfo(song);
    this.updateDynamicBackground(song);
    this.renderSongList();
    
    // 播放
    this.elements.audioPlayer.play()
      .then(() => {
        this.isPlaying = true;
        this.updatePlayButton();
      })
      .catch(error => {
        console.error('[GlassFlow] Play error:', error);
      });
  }
  
  /**
   * 切换播放/暂停
   */
  togglePlay() {
    if (this.currentSongIndex < 0 && this.songs.length > 0) {
      this.playSong(0);
      return;
    }
    
    if (this.isPlaying) {
      this.elements.audioPlayer.pause();
      this.isPlaying = false;
    } else {
      this.elements.audioPlayer.play();
      this.isPlaying = true;
    }
    
    this.updatePlayButton();
  }
  
  /**
   * 更新播放按钮
   */
  updatePlayButton() {
    if (this.isPlaying) {
      this.elements.playIcon.style.display = 'none';
      this.elements.pauseIcon.style.display = 'block';
    } else {
      this.elements.playIcon.style.display = 'block';
      this.elements.pauseIcon.style.display = 'none';
    }
  }
  
  /**
   * 播放上一首
   */
  playPrevious() {
    if (this.songs.length === 0) return;
    
    let newIndex = this.currentSongIndex - 1;
    if (newIndex < 0) {
      newIndex = this.songs.length - 1;
    }
    
    this.playSong(newIndex);
  }
  
  /**
   * 播放下一首
   */
  playNext() {
    if (this.songs.length === 0) return;
    
    let newIndex = this.currentSongIndex + 1;
    if (newIndex >= this.songs.length) {
      newIndex = 0;
    }
    
    this.playSong(newIndex);
  }
  
  /**
   * 歌曲结束
   */
  onSongEnded() {
    this.playNext();
  }
  
  /**
   * 更新当前曲目信息
   */
  updateCurrentTrackInfo(song) {
    this.elements.currentTitle.textContent = song.title || '未知歌曲';
    this.elements.currentArtist.textContent = song.artist || '未知艺术家';
    
    // 更新封面
    if (song.cover) {
      this.elements.currentCover.innerHTML = `
        <img src="data:${song.coverType || 'image/jpeg'};base64,${song.cover}" alt="${song.title}">
      `;
    } else {
      this.elements.currentCover.innerHTML = `
        <svg class="default-cover" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          <circle cx="8.5" cy="8.5" r="1.5"></circle>
          <polyline points="21 15 16 10 5 21"></polyline>
        </svg>
      `;
    }
  }
  
  /**
   * 更新动态模糊背景
   */
  updateDynamicBackground(song) {
    const background = this.elements.dynamicBackground;
    
    if (song && song.cover) {
      // 使用歌曲封面
      background.style.backgroundImage = `url(data:${song.coverType || 'image/jpeg'};base64,${song.cover})`;
    } else {
      // 默认渐变背景
      background.style.background = 'linear-gradient(135deg, #E8E8ED 0%, #F2F2F7 50%, #E5E5EA 100%)';
    }
  }
  
  /**
   * 更新进度条
   */
  updateProgress() {
    const current = this.elements.audioPlayer.currentTime;
    const duration = this.elements.audioPlayer.duration || 0;
    
    if (duration > 0) {
      const percent = (current / duration) * 100;
      this.elements.progressFill.style.width = `${percent}%`;
    }
    
    this.elements.currentTime.textContent = this.formatTime(current);
  }
  
  /**
   * 加载元数据后
   */
  onMetadataLoaded() {
    const duration = this.elements.audioPlayer.duration;
    this.elements.totalTime.textContent = this.formatTime(duration);
    
    // 更新当前歌曲的时长
    if (this.currentSongIndex >= 0 && this.songs[this.currentSongIndex]) {
      this.songs[this.currentSongIndex].duration = duration;
      this.renderSongList();
    }
  }
  
  /**
   * 跳转到指定位置
   */
  seek(e) {
    const progressBar = this.elements.progressBar;
    const rect = progressBar.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    const duration = this.elements.audioPlayer.duration;
    
    if (duration > 0) {
      this.elements.audioPlayer.currentTime = percent * duration;
    }
  }
  
  /**
   * 设置音量
   */
  setVolume(e) {
    const value = e.target.value / 100;
    this.volume = value;
    this.elements.audioPlayer.volume = value;
  }
  
  /**
   * 处理键盘快捷键
   */
  handleKeyboard(e) {
    // 空格键 - 播放/暂停
    if (e.code === 'Space' && e.target.tagName !== 'INPUT') {
      e.preventDefault();
      this.togglePlay();
    }
    // 左箭头 - 上一首
    else if (e.code === 'ArrowLeft' && e.target.tagName !== 'INPUT') {
      this.playPrevious();
    }
    // 右箭头 - 下一首
    else if (e.code === 'ArrowRight' && e.target.tagName !== 'INPUT') {
      this.playNext();
    }
  }
  
  /**
   * 处理拖放
   */
  handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    
    const files = Array.from(e.dataTransfer.files);
    const validFiles = files.filter(file => {
      const ext = file.name.toLowerCase().split('.').pop();
      return ['wav', 'mp3', 'flac', 'm4a'].includes(ext);
    });
    
    validFiles.forEach(file => {
      this.addSong(file.path);
    });
  }
  
  /**
   * 格式化时间
   */
  formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }
  
  /**
   * 转义HTML
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// 全局引用，便于调试
window.player = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
  window.player = new GlassFlowPlayer();
});
