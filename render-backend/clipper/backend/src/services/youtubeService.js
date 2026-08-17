const { execFile } = require('child_process');
const os = require('os');
const path = require('path');
const fs = require('fs');

// Locate a yt-dlp binary. Prefer the one bundled in ../../../clipserver/bin,
// otherwise fall back to a system-installed `yt-dlp` on PATH.
const isWin = os.platform() === 'win32';
const bundledBin = path.resolve(
  __dirname,
  '../../../clipserver/bin',
  isWin ? 'yt-dlp.exe' : 'yt-dlp'
);
const ytdlpPath = fs.existsSync(bundledBin) ? bundledBin : 'yt-dlp';

const extractYoutubeId = (url) => {
  if (!url) return null;
  const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
  const match = url.match(regExp);
  return match && match[2].length === 11 ? match[2] : null;
};

// Download a full YouTube video to `outputPath` (best mp4 up to 1080p, merged).
const downloadVideo = (youtubeUrl, outputPath) => {
  return new Promise((resolve, reject) => {
    const ffmpegInstaller = require('@ffmpeg-installer/ffmpeg');

    const args = [
      '--force-ipv4',
      '--no-check-certificates',
      '--no-playlist',
      '--extractor-args', 'youtube:player_client=android,tv_embedded',
      '--ffmpeg-location', path.dirname(ffmpegInstaller.path),
      '-f', 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=480]/best',
      '-o', outputPath,
      youtubeUrl,
    ];

    execFile(ytdlpPath, args, { timeout: 15 * 60 * 1000, maxBuffer: 1024 * 1024 * 20 }, (error, stdout, stderr) => {
      if (error) {
        console.error('yt-dlp download error:', stderr || error.message);
        return reject(new Error(`yt-dlp failed: ${stderr || error.message}`));
      }
      if (!fs.existsSync(outputPath)) {
        return reject(new Error('yt-dlp finished but output file not found.'));
      }
      resolve(outputPath);
    });
  });
};

module.exports = {
  extractYoutubeId,
  downloadVideo,
  ytdlpPath,
};
