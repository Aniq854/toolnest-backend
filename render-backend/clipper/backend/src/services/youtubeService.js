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

// --- Cookies -------------------------------------------------------------
// Render mounts Secret Files at /etc/secrets/... on a READ-ONLY filesystem.
// yt-dlp writes the cookie jar back after each request (YouTube rotates
// session cookies), which crashed with:
//   OSError: [Errno 30] Read-only file system: '/etc/secrets/cookies.txt'
// Fix: copy the secret once into a writable temp path and point yt-dlp there,
// so rotated cookies persist for the life of the container instead of dying.
const COOKIE_SECRET = '/etc/secrets/cookies.txt';
const COOKIE_WRITABLE = path.join(os.tmpdir(), 'yt-cookies.txt');

const getCookieFile = () => {
  try {
    if (fs.existsSync(COOKIE_WRITABLE)) return COOKIE_WRITABLE;
    if (!fs.existsSync(COOKIE_SECRET)) return null;
    fs.copyFileSync(COOKIE_SECRET, COOKIE_WRITABLE);
    fs.chmodSync(COOKIE_WRITABLE, 0o600);
    console.log('Cookies copied to writable path:', COOKIE_WRITABLE);
    return COOKIE_WRITABLE;
  } catch (e) {
    console.error('Could not prepare cookie file:', e.message);
    return null;
  }
};

const extractYoutubeId = (url) => {
  if (!url) return null;
  const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
  const match = url.match(regExp);
  return match && match[2].length === 11 ? match[2] : null;
};

// Download a full YouTube video to `outputPath` (best mp4 up to 720p, merged).
const downloadVideo = (youtubeUrl, outputPath) => {
  return new Promise((resolve, reject) => {
    const ffmpegInstaller = require('@ffmpeg-installer/ffmpeg');
    const cookieFile = getCookieFile();

    const args = [
      '--force-ipv4',
      '--no-check-certificates',
      '--no-playlist',
      ...(cookieFile ? ['--cookies', cookieFile] : []),
      '--extractor-args', 'youtube:player_client=web_safari,mweb,ios,tv',
      '--retries', '5',
      '--sleep-requests', '1',
      '--user-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
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
  getCookieFile,
};
