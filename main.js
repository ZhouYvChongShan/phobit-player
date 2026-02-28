const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');

// 禁用GPU加速以避免某些Windows问题
app.disableHardwareAcceleration();

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    frame: true,
    backgroundColor: '#F2F2F7',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    show: false
  });

  mainWindow.loadFile('index.html');

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    console.log('[GlassFlow] Application started successfully');
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// 处理文件选择对话框
ipcMain.handle('open-file-dialog', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: '选择音乐文件',
    buttonLabel: '添加歌曲',
    filters: [
      { name: '音频文件', extensions: ['wav', 'mp3', 'flac', 'm4a'] }
    ],
    properties: ['openFile', 'multiSelections']
  });

  if (result.canceled) {
    return { canceled: true, filePaths: [] };
  }

  return { canceled: false, filePaths: result.filePaths };
});

// 读取文件为Buffer (用于元数据解析)
ipcMain.handle('read-file', async (event, filePath) => {
  try {
    const buffer = fs.readFileSync(filePath);
    return { success: true, data: buffer.toString('base64'), path: filePath };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

// 获取文件信息
ipcMain.handle('get-file-info', async (event, filePath) => {
  try {
    const stats = fs.statSync(filePath);
    return {
      success: true,
      name: path.basename(filePath),
      path: filePath,
      ext: path.extname(filePath).toLowerCase()
    };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

// 应用启动
app.whenReady().then(() => {
  console.log('[GlassFlow] Creating main window...');
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// 错误处理
process.on('uncaughtException', (error) => {
  console.error('[GlassFlow] Uncaught Exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('[GlassFlow] Unhandled Rejection at:', promise, 'reason:', reason);
});
