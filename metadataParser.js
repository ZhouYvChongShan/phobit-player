/**
 * GlassFlow Music Player - 元数据解析引擎
 * 基于 SongMetadataParsingEngine 思想改造
 * 支持: MP3, FLAC, M4A, WAV
 */

class MusicMetadataExtractor {
  constructor() {
    this.supportedFormats = ['.mp3', '.flac', '.m4a', '.wav'];
  }

  /**
   * 检查文件格式是否支持
   */
  isFormatSupported(filePath) {
    const ext = this.getFileExtension(filePath).toLowerCase();
    return this.supportedFormats.includes(ext);
  }

  /**
   * 获取文件扩展名
   */
  getFileExtension(filePath) {
    const match = filePath.match(/\.[^.]+$/);
    return match ? match[0] : '';
  }

  /**
   * 从文件路径提取默认标题（当无元数据时使用）
   */
  getDefaultTitle(filePath) {
    const fileName = filePath.split(/[\\/]/).pop();
    const withoutExt = fileName.replace(/\.[^.]+$/, '');
    return withoutExt || '未知歌曲';
  }

  /**
   * 解析音乐文件元数据
   * @param {ArrayBuffer} audioData - 音频文件的ArrayBuffer数据
   * @param {string} filePath - 文件路径
   * @returns {Promise<Object>} - 解析后的元数据对象
   */
  async parseMetadata(audioData, filePath) {
    const ext = this.getFileExtension(filePath).toLowerCase();
    
    const defaultMetadata = {
      title: this.getDefaultTitle(filePath),
      artist: '未知艺术家',
      album: '未知专辑',
      duration: 0,
      cover: null,
      coverType: null,
      format: ext.replace('.', '').toUpperCase(),
      filePath: filePath
    };

    try {
      switch (ext) {
        case '.mp3':
          return await this.parseMP3(audioData, defaultMetadata);
        case '.flac':
          return await this.parseFLAC(audioData, defaultMetadata);
        case '.m4a':
          return await this.parseM4A(audioData, defaultMetadata);
        case '.wav':
          return await this.parseWAV(audioData, defaultMetadata);
        default:
          return defaultMetadata;
      }
    } catch (error) {
      console.error('[MetadataParser] Parse error:', error);
      return defaultMetadata;
    }
  }

  /**
   * 解析ID3v2标签 (MP3)
   * 参考 SongMetadataParsingEngine 的 MP3 解析逻辑
   */
  async parseMP3(audioData, defaultMetadata) {
    const view = new DataView(audioData);
    const metadata = { ...defaultMetadata };

    // 检查ID3v2标签
    if (view.getUint8(0) === 0x49 && view.getUint8(1) === 0x44 && view.getUint8(2) === 0x33) {
      // ID3v2
      const version = view.getUint8(3);
      const flags = view.getUint8(5);
      const size = this.readSyncsafeInt(view, 6);
      
      let offset = 10;
      const endOffset = offset + size;

      // 扩展头部 (如果存在)
      if (flags & 0x40) {
        const extSize = view.getUint32(offset);
        offset += extSize;
      }

      while (offset < endOffset - 10) {
        const frameId = String.fromCharCode(
          view.getUint8(offset),
          view.getUint8(offset + 1),
          view.getUint8(offset + 2),
          view.getUint8(offset + 3)
        );
        
        const frameSize = version >= 3 
          ? view.getUint32(offset + 4)
          : this.readSyncsafeInt(view, offset + 4);
        
        if (frameSize <= 0 || offset + frameSize > endOffset) break;

        const frameDataOffset = offset + (version >= 3 ? 10 : 6);
        
        switch (frameId) {
          case 'TIT2': // 标题
            metadata.title = this.readTextFrame(view, frameDataOffset, frameSize - 1) || metadata.title;
            break;
          case 'TPE1': // 艺术家
            metadata.artist = this.readTextFrame(view, frameDataOffset, frameSize - 1) || metadata.artist;
            break;
          case 'TALB': // 专辑
            metadata.album = this.readTextFrame(view, frameDataOffset, frameSize - 1) || metadata.album;
            break;
          case 'APIC': // 封面图片
            const coverData = this.readAPICFrame(view, frameDataOffset, frameSize);
            if (coverData) {
              metadata.cover = coverData.data;
              metadata.coverType = coverData.mime;
            }
            break;
        }

        offset += (version >= 3 ? 10 : 6) + frameSize;
      }

      // 尝试从文件名获取时长（ID3标签后第一个MPEG帧）
      metadata.duration = this.estimateMP3Duration(audioData, endOffset);
    }

    return metadata;
  }

  /**
   * 解析FLAC元数据
   */
  async parseFLAC(audioData, defaultMetadata) {
    const view = new DataView(audioData);
    const metadata = { ...defaultMetadata };

    // 检查FLAC签名
    const signature = String.fromCharCode(
      view.getUint8(0), view.getUint8(1), view.getUint8(2), view.getUint8(3)
    );
    
    if (signature !== 'fLaC') {
      return metadata;
    }

    let offset = 4;
    
    while (offset < audioData.byteLength) {
      const blockHeader = view.getUint8(offset);
      const isLast = (blockHeader & 0x80) !== 0;
      const blockType = blockHeader & 0x7F;
      const blockSize = (view.getUint8(offset + 1) << 16) | 
                        (view.getUint8(offset + 2) << 8) | 
                        view.getUint8(offset + 3);
      
      const blockDataOffset = offset + 4;
      
      if (blockType === 0) {
        // STREAMINFO
        const sampleRate = (view.getUint32(blockDataOffset + 10) >> 12) & 0xFFFFF;
        const totalSamples = ((view.getUint32(blockDataOffset + 13) & 0xF) << 32) | 
                             view.getUint32(blockDataOffset + 10) >> 12;
        metadata.duration = sampleRate > 0 ? totalSamples / sampleRate : 0;
      } else if (blockType === 4) {
        // VORBIS_COMMENT
        const vorbisData = this.parseVorbisComments(audioData, blockDataOffset, blockSize);
        metadata.title = vorbisData.title || metadata.title;
        metadata.artist = vorbisData.artist || metadata.artist;
        metadata.album = vorbisData.album || metadata.album;
      } else if (blockType=== 6) {
        // PICTURE
        const pictureData = this.parseFLACPicture(audioData, blockDataOffset, blockSize);
        if (pictureData) {
          metadata.cover = pictureData.data;
          metadata.coverType = pictureData.mime;
        }
      }

      offset += 4 + blockSize;
      if (isLast) break;
    }

    return metadata;
  }

  /**
   * 解析M4A/MP4元数据
   */
  async parseM4A(audioData, defaultMetadata) {
    const metadata = { ...defaultMetadata };
    
    try {
      const parser = new M4AParser(audioData);
      const tags = parser.parse();
      
      metadata.title = tags.title || metadata.title;
      metadata.artist = tags.artist || metadata.artist;
      metadata.album = tags.album || metadata.album;
      metadata.duration = tags.duration || 0;
      metadata.cover = tags.cover;
      metadata.coverType = tags.coverType;
    } catch (e) {
      console.error('[MetadataParser] M4A parse error:', e);
    }

    return metadata;
  }

  /**
   * 解析WAV元数据
   */
  async parseWAV(audioData, defaultMetadata) {
    const view = new DataView(audioData);
    const metadata = { ...defaultMetadata };

    // 检查RIFF签名
    const riff = String.fromCharCode(view.getUint8(0), view.getUint8(1), view.getUint8(2));
    if (riff !== 'RIF') return metadata;

    // 检查WAVE格式
    const wave = String.fromCharCode(view.getUint8(8), view.getUint8(9), view.getUint8(10), view.getUint8(11));
    if (wave !== 'WAVE') return metadata;

    let offset = 12;
    
    while (offset < audioData.byteLength - 8) {
      const chunkId = String.fromCharCode(
        view.getUint8(offset), view.getUint8(offset + 1),
        view.getUint8(offset + 2), view.getUint8(offset + 3)
      );
      const chunkSize = view.getUint32(offset + 4);
      
      if (chunkId === 'fmt ') {
        // 读取音频格式信息
        const numChannels = view.getUint16(offset + 10);
        const sampleRate = view.getUint32(offset + 12);
        const byteRate = view.getUint32(offset + 16);
        const bitsPerSample = view.getUint16(offset + 22);
        
        // 计算时长
        const dataChunkSize = this.findWAVDataSize(view, offset + 8 + chunkSize, audioData.byteLength);
        if (dataChunkSize > 0 && byteRate > 0) {
          metadata.duration = dataChunkSize / byteRate;
        }
      } else if (chunkId === 'LIST') {
        // INFO块
        const listType = String.fromCharCode(
          view.getUint8(offset + 8), view.getUint8(offset + 9),
          view.getUint8(offset + 10), view.getUint8(offset + 11)
        );
        
        if (listType === 'INFO') {
          const infoData = this.parseWAVInfo(audioData, offset + 12, chunkSize - 4);
          metadata.title = infoData.INAM || metadata.title;
          metadata.artist = infoData.IART || metadata.artist;
          metadata.album = infoData.IPRD || metadata.album;
        }
      }

      offset += 8 + chunkSize;
      // 对齐到偶数
      if (chunkSize % 2 !== 0) offset++;
    }

    return metadata;
  }

  /**
   * 查找WAV数据块大小
   */
  findWAVDataSize(view, startOffset, fileSize) {
    let offset = startOffset;
    while (offset < fileSize - 8) {
      const chunkId = String.fromCharCode(
        view.getUint8(offset), view.getUint8(offset + 1),
        view.getUint8(offset + 2), view.getUint8(offset + 3)
      );
      const chunkSize = view.getUint32(offset + 4);
      
      if (chunkId === 'data') {
        return chunkSize;
      }
      
      offset += 8 + chunkSize;
      if (chunkSize % 2 !== 0) offset++;
    }
    return 0;
  }

  /**
   * 解析WAV INFO块
   */
  parseWAVInfo(audioData, offset, size) {
    const info = {};
    const view = new DataView(audioData);
    const endOffset = offset + size;
    let pos = offset;

    while (pos < endOffset - 8) {
      const id = String.fromCharCode(
        view.getUint8(pos), view.getUint8(pos + 1),
        view.getUint8(pos + 2), view.getUint8(pos + 3)
      );
      const dataSize = view.getUint32(pos + 4);
      
      if (dataSize <= 0 || pos + 8 + dataSize > endOffset) break;

      if (['INAM', 'IART', 'IPRD', 'ICRD', 'IGNR'].includes(id)) {
        const str = this.readString(view, pos + 8, Math.min(dataSize - 1, 256));
        info[id] = str;
      }

      pos += 8 + dataSize;
      if (dataSize % 2 !== 0) pos++;
    }

    return info;
  }

  /**
   * 读取文本帧 (ID3v2)
   */
  readTextFrame(view, offset, size) {
    if (size <= 1) return null;
    
    const encoding = view.getUint8(offset);
    const text = this.readString(view, offset + 1, size - 1);
    
    // 尝试正确的编码
    try {
      const decoder = new TextDecoder(encoding === 1 ? 'utf-16be' : 'utf-8');
      return decoder.decode(new Uint8Array(audioData.slice(offset + 1, offset + size)));
    } catch {
      return text;
    }
  }

  /**
   * 读取APIC帧 (封面)
   */
  readAPICFrame(view, offset, size) {
    if (size <= 4) return null;
    
    try {
      // 跳过编码
      let pos = offset + 1;
      
      // 读取MIME类型
      let mimeEnd = pos;
      while (mimeEnd < offset + size - 1 && view.getUint8(mimeEnd) !== 0) mimeEnd++;
      const mime = this.readString(view, pos, mimeEnd - pos);
      pos = mimeEnd + 1;
      
      // 跳过图片类型
      pos++;
      
      // 跳过描述
      while (pos < offset + size - 1 && view.getUint8(pos) !== 0) pos++;
      pos++;
      
      const imageSize = offset + size - pos;
      const imageData = new Uint8Array(audioData.slice(pos, pos + imageSize));
      
      return {
        data: this.arrayBufferToBase64(imageData.buffer),
        mime: mime || 'image/jpeg'
      };
    } catch (e) {
      console.error('[MetadataParser] APIC parse error:', e);
      return null;
    }
  }

  /**
   * 解析Vorbis注释
   */
  parseVorbisComments(audioData, offset, size) {
    const view = new DataView(audioData);
    const result = { title: null, artist: null, album: null };
    
    try {
      // 跳过供应商字符串
      let pos = offset;
      const vendorLength = view.getUint32(pos);
      pos += 4 + vendorLength;
      
      // 读取评论数量
      const commentCount = view.getUint32(pos);
      pos += 4;
      
      for (let i = 0; i < commentCount && pos < offset + size - 4; i++) {
        const commentLength = view.getUint32(pos);
        pos += 4;
        
        const commentData = new Uint8Array(audioData.slice(pos, pos + commentLength));
        const comment = new TextDecoder().decode(commentData);
        
        const [key, value] = comment.split('=');
        if (key && value) {
          const upperKey = key.toUpperCase();
          if (upperKey === 'TITLE') result.title = value;
          else if (upperKey === 'ARTIST') result.artist = value;
          else if (upperKey === 'ALBUM') result.album = value;
        }
        
        pos += commentLength;
      }
    } catch (e) {
      console.error('[MetadataParser] Vorbis parse error:', e);
    }
    
    return result;
  }

  /**
   * 解析FLAC图片
   */
  parseFLACPicture(audioData, offset, size) {
    const view = new DataView(audioData);
    
    try {
      let pos = offset;
      
      // 图片类型
      pos += 4;
      
      // MIME长度
      const mimeLength = view.getUint32(pos);
      pos += 4;
      
      // MIME类型
      const mime = this.readString(view, pos, mimeLength);
      pos += mimeLength;
      
      // 描述
      const descLength = view.getUint32(pos);
      pos += 4 + descLength;
      
      // 宽度/高度/颜色深度/颜色数
      pos += 16;
      
      // 图片数据大小
      const imageSize = view.getUint32(pos);
      pos += 4;
      
      const imageData = new Uint8Array(audioData.slice(pos, pos + imageSize));
      
      return {
        data: this.arrayBufferToBase64(imageData.buffer),
        mime: mime || 'image/jpeg'
};
    } catch (e) {
      console.error('[MetadataParser] FLAC picture parse error:', e);
      return null;
    }
  }

  /**
   * 估算MP3时长
   */
  estimateMP3Duration(audioData, dataOffset) {
    // 简化的MPEG帧时长估算
    // 假设128kbps average
    const dataLength = audioData.byteLength - dataOffset;
    const bitrate = 128000; // 128 kbps
    return dataLength / (bitrate / 8);
  }

  /**
   * 读取同步安全整数
   */
  readSyncsafeInt(view, offset) {
    return (view.getUint8(offset) << 21) |
           (view.getUint8(offset + 1) << 14) |
           (view.getUint8(offset + 2) << 7) |
           view.getUint8(offset + 3);
  }

  /**
   * 读取字符串
   */
  readString(view, offset, length) {
    if (length <= 0) return '';
    try {
      const bytes = new Uint8Array(audioData.slice(offset, offset + length));
      // 尝试UTF-8
      let result = new TextDecoder('utf-8', { fatal: false }).decode(bytes);
      // 清理null字符
      result = result.replace(/\0/g, '');
      return result.trim();
    } catch {
      // 回退到Latin-1
      let result = '';
      for (let i = 0; i < length; i++) {
        const char = view.getUint8(offset + i);
        if (char === 0) break;
        result += String.fromCharCode(char);
      }
      return result.trim();
    }
  }

  /**
   * ArrayBuffer转Base64
   */
  arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }
}

/**
 * M4A/MP4解析器
 */
class M4AParser {
  constructor(audioData) {
    this.view = new DataView(audioData);
    this.offset = 0;
  }

  parse() {
    const result = {
      title: null,
      artist: null,
      album: null,
      duration: 0,
      cover: null,
      coverType: null
    };

    while (this.offset < this.view.byteLength - 8) {
      const size = this.view.getUint32(this.offset);
      const type = String.fromCharCode(
        this.view.getUint8(this.offset + 4),
        this.view.getUint8(this.offset + 5),
        this.view.getUint8(this.offset + 6),
        this.view.getUint8(this.offset + 7)
      );

      if (type === 'moov') {
        // 递归解析moov容器
        const subParser = new M4AParser(this.view.buffer);
        subParser.offset = this.offset + 8;
        const moovData = subParser.parse();
        Object.assign(result, moovData);
      } else if (type === 'trak') {
        this.parseTrack(result);
      } else if (type === 'ilst') {
        this.parseMetadata(result);
      } else if (type === 'mdia') {
        // 媒体信息
        this.parseMedia(result);
      }

      if (size === 0) break;
      this.offset += size;
    }

    return result;
  }

  parseTrack(result) {
    const endOffset = this.offset + this.view.getUint32(this.offset);
    this.offset += 8;
    
    while (this.offset < endOffset - 8) {
      const size = this.view.getUint32(this.offset);
      const type = String.fromCharCode(
        this.view.getUint8(this.offset + 4),
        this.view.getUint8(this.offset + 5),
        this.view.getUint8(this.offset + 6),
        this.view.getUint8(this.offset + 7)
      );
      
      if (type === 'mdia') {
        const subParser = new M4AParser(this.view.buffer);
        subParser.offset = this.offset + 8;
        subParser.parseMedia(result);
      }
      
      if (size === 0) break;
      this.offset += size;
    }
  }

  parseMedia(result) {
    const endOffset = this.offset + this.view.getUint32(this.offset);
    this.offset += 8;
    
    while (this.offset < endOffset - 8) {
      const size = this.view.getUint32(this.offset);
      const type = String.fromCharCode(
        this.view.getUint8(this.offset + 4),
        this.view.getUint8(this.offset + 5),
        this.view.getUint8(this.offset + 6),
        this.view.getUint8(this.offset + 7)
      );
      
      if (type === 'hdlr') {
        // 跳过处理程序
      } else if (type === 'minf') {
        const subParser = new M4AParser(this.view.buffer);
        subParser.offset = this.offset + 8;
        subParser.parseMediaInfo(result);
      }
      
      if (size === 0) break;
      this.offset += size;
    }
  }

  parseMediaInfo(result) {
    const endOffset = this.offset + this.view.getUint32(this.offset);
    this.offset += 8;
    
    while (this.offset < endOffset - 8) {
      const size = this.view.getUint32(this.offset);
      const type = String.fromCharCode(
        this.view.getUint8(this.offset + 4),
        this.view.getUint8(this.offset + 5),
        this.view.getUint8(this.offset + 6),
        this.view.getUint8(this.offset + 7)
      );
      
      if (type === 'stsd') {
        // 样本描述 - 获取时长信息
        this.offset += size;
      } else if (type === 'stts') {
        // 时间到样本映射
        const entries = this.view.getUint32(this.offset + 12);
        if (entries > 0) {
          const sampleCount = this.view.getUint32(this.offset + 16);
          const sampleDuration = this.view.getUint32(this.offset + 20);
          result.duration = sampleCount * sampleDuration / 10000000; // 转换为秒
        }
      }
      
      if (size === 0) break;
      this.offset += size;
    }
  }

  parseMetadata(result) {
    const endOffset = this.offset + this.view.getUint32(this.offset);
    this.offset += 8;
    
    while (this.offset < endOffset - 8) {
      const size = this.view.getUint32(this.offset);
      const type = String.fromCharCode(
        this.view.getUint8(this.offset + 4),
        this.view.getUint8(this.offset + 5),
        this.view.getUint8(this.offset + 6),
        this.view.getUint8(this.offset + 7)
      );
      
      if (type === 'covr') {
        const dataSize = size - 8;
        const dataOffset = this.offset + 8;
        
        // 检测MIME类型
        let mimeType = 'image/jpeg';
        if (this.view.getUint8(dataOffset) === 0x89) {
          mimeType = 'image/png';
        }
        
        const imageData = new Uint8Array(this.view.buffer.slice(dataOffset, dataOffset + dataSize));
        result.cover = this.arrayBufferToBase64(imageData.buffer);
        result.coverType = mimeType;
      } else if (type === 'data') {
        // 文本数据
        const dataOffset = this.offset + 8 + 4; // 跳过flag
        const dataSize = size - 12;
        const text = this.readString(dataOffset, Math.min(dataSize, 256));
        
        // 根据上下文设置
        // 需要记录当前在哪个key下
      }
      
      if (size === 0) break;
      this.offset += size;
    }
  }

  readString(offset, length) {
    if (length <= 0) return '';
    try {
      const bytes = new Uint8Array(this.view.buffer.slice(offset, offset + length));
      const result = new TextDecoder('utf-8', { fatal: false }).decode(bytes);
      return result.replace(/\0/g, '').trim();
    } catch {
      return '';
    }
  }

  arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }
}

// 导出
window.MusicMetadataExtractor = MusicMetadataExtractor;
