const ffmpeg = require('fluent-ffmpeg');
const ffmpegInstaller = require('@ffmpeg-installer/ffmpeg');
const ffprobeInstaller = require('@ffprobe-installer/ffprobe');
const path = require('path');

// Set static paths for FFmpeg and FFprobe
ffmpeg.setFfmpegPath(ffmpegInstaller.path);
ffmpeg.setFfprobePath(ffprobeInstaller.path);

const extractAudio = (videoPath, outputPath) => {
  return new Promise((resolve, reject) => {
    ffmpeg(videoPath)
      .noVideo()
      .audioCodec('pcm_s16le')
      .audioFrequency(16000)
      .audioChannels(1)
      .save(outputPath)
      .on('end', () => resolve(outputPath))
      .on('error', (err) => {
        console.error('FFmpeg extractAudio error:', err);
        reject(err);
      });
  });
};

const cutClip = (videoPath, startTime, endTime, outputPath, aspectRatio = '9:16') => {
  return new Promise((resolve, reject) => {
    const duration = Math.max(1, endTime - startTime);

    // Build video filter chain: PTS timestamp reset + optional aspect ratio crop
    let vfChain = 'setpts=PTS-STARTPTS';
    if (aspectRatio === '9:16') {
      vfChain += ",crop='min(iw,ih*9/16)':'min(ih,iw*16/9)'";
    } else if (aspectRatio === '1:1') {
      vfChain += ",crop='min(iw,ih)':'min(iw,ih)'";
    }

    ffmpeg(videoPath)
      .inputOptions([`-ss ${startTime}`])
      .outputOptions([
        `-t ${duration}`,
        '-c:v libx264',
        '-preset ultrafast',
        '-crf 23',
        '-pix_fmt yuv420p',
        '-vsync cfr',
        '-r 30',
        '-g 30',
        '-keyint_min 30',
        '-sc_threshold 0',
        '-af asetpts=PTS-STARTPTS',
        '-vf', vfChain,
        '-c:a aac',
        '-ac 2',
        '-ar 44100',
        '-shortest',
        '-avoid_negative_ts make_zero',
        '-max_muxing_queue_size 1024',
        '-movflags +faststart'
      ])
      .save(outputPath)
      .on('end', () => resolve(outputPath))
      .on('error', (err) => {
        console.error('FFmpeg cutClip error:', err);
        reject(err);
      });
  });
};

const generateThumbnail = (videoPath, outputPath, timestamp) => {
  return new Promise((resolve) => {
    ffmpeg(videoPath)
      .screenshots({
        timestamps: [Math.max(0, timestamp)],
        filename: path.basename(outputPath),
        folder: path.dirname(outputPath),
        size: '1280x720'
      })
      .on('end', () => resolve(outputPath))
      .on('error', (err) => {
        console.error('FFmpeg generateThumbnail error:', err);
        resolve(outputPath);
      });
  });
};

const getVideoDuration = (videoPath) => {
  return new Promise((resolve) => {
    ffmpeg.ffprobe(videoPath, (err, metadata) => {
      if (err) {
        console.error('ffprobe error:', err);
        return resolve(60);
      }
      const duration = metadata?.format?.duration || 60;
      resolve(duration);
    });
  });
};

module.exports = {
  extractAudio,
  cutClip,
  generateThumbnail,
  getVideoDuration
};
