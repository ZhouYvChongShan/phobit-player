const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的API给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 打开文件选择对话框
  openFileDialog: () => ipcRenderer.invoke('open-file-dialog'),
  
  // 读取文件
  readFile: (filePath) => ipcRenderer.invoke('read-file', filePath),
  
  // 获取文件信息
  getFileInfo: (filePath) => ipcRenderer.invoke('get-file-info', filePath),
  
  // 平台信息
  platform: process.platform
});

console.log('[GlassFlow] Preload script loaded');
