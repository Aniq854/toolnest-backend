const path = require('path');
const fs = require('fs');
const Job = require('../models/Job');
const Clip = require('../models/Clip');
const videoService = require('./videoService');
const transcriptionService = require('./transcriptionService');
const aiAnalysisService = require('./aiAnalysisService');

const getStoragePath = (subDir) => {
  const p = path.resolve(__dirname, '../../storage', subDir);
  if (!fs.existsSync(p)) {
    fs.mkdirSync(p, { recursive: true });
  }
  return p;
};

// Cut the WHOLE video into back-to-back clips of the length the user picked,
// instead of picking 2-5 spread-out samples. A 10 minute video at 1 min gives
// 10 clips, at 30s gives 20.
//
// Two ceilings keep a single job from monopolising the free Render box, since
// every clip is a real ffmpeg re-encode: at most MAX_CLIPS clips, and at most
// MAX_OUTPUT_SECONDS of footage in total. Whatever is skipped is logged rather
// than silently dropped.
const MAX_CLIPS = 24;
const MAX_OUTPUT_SECONDS = 45 * 60;

function buildTimeBasedMoments(videoDuration, clipLen){
  clipLen = Math.max(5, Math.floor(clipLen || 30));
  const total = Math.floor(videoDuration || 0);

  if (total < 5) {
    return [{ start_time: 0, end_time: Math.max(3, total), title: 'Clip 1',
              reason: 'Whole video', virality_score: 5 }];
  }

  const out = [];
  let seconds = 0;
  for (let start = 0; start < total; start += clipLen) {
    const end = Math.min(start + clipLen, total);
    if (end - start < 3) break;                       // ignore a sliver at the end
    if (out.length >= MAX_CLIPS) break;
    if (seconds + (end - start) > MAX_OUTPUT_SECONDS) break;
    seconds += end - start;
    out.push({
      start_time: start,
      end_time: end,
      title: 'Clip ' + (out.length + 1),
      reason: 'Part ' + (out.length + 1) + ' of the video',
      virality_score: 5
    });
  }

  const covered = out.length ? out[out.length - 1].end_time : 0;
  if (covered < total - 3) {
    console.log(`\u2702\ufe0f  Cut ${out.length} clips covering ${covered}s of ${total}s ` +
                `(limit: ${MAX_CLIPS} clips / ${MAX_OUTPUT_SECONDS}s per job).`);
  } else {
    console.log(`\u2702\ufe0f  Cut ${out.length} clips covering the full ${total}s.`);
  }

  return out.length ? out : [{ start_time: 0, end_time: Math.min(clipLen, total),
                               title: 'Clip 1', reason: 'Whole video', virality_score: 5 }];
}

const processJobDirectly = async (jobId) => {
  let jobRecord = await Job.findById(jobId);
  if (!jobRecord) {
    console.error(`Job ${jobId} not found`);
    return;
  }

  try {
    const updateJob = async (status, progress) => {
      jobRecord.status = status;
      jobRecord.progress = progress;
      await jobRecord.save();
      console.log(`🚀 [Job ${jobId}] Status: ${status} [${progress}%]`);
    };

    // 1. [0-10%] Validate video
    await updateJob('processing', 0);
    const videoPath = jobRecord.videoPath;
    if (!fs.existsSync(videoPath)) {
      throw new Error(`Video file not found at ${videoPath}`);
    }
    const videoDuration = await videoService.getVideoDuration(videoPath);
    await updateJob('processing', 10);

    // 2-4. Build moments (FAST MODE skips audio/transcription/AI)
    let moments;
    let audioPath = null;
    if (jobRecord.fastMode) {
      await updateJob('cutting', 40);
      moments = buildTimeBasedMoments(videoDuration, jobRecord.durationOption);
    } else {
      await updateJob('extracting_audio', 10);
      const audioDir = getStoragePath('audio');
      audioPath = path.join(audioDir, `${jobId}.wav`);
      await videoService.extractAudio(videoPath, audioPath);
      await updateJob('extracting_audio', 20);

      await updateJob('transcribing', 20);
      const transcript = await transcriptionService.transcribeAudio(audioPath);
      jobRecord.transcript = transcript;
      await updateJob('transcribing', 45);

      await updateJob('analyzing', 45);
      moments = await aiAnalysisService.findBestMoments(transcript, jobRecord.durationOption, videoDuration);
      await updateJob('analyzing', 60);
    }

    // 5. [60-85%] Cut clips with FFmpeg
    await updateJob('cutting', 60);
    const clipsDir = getStoragePath('clips');
    const cutClips = [];
    const cutProgressStep = 25 / (moments.length || 1);

    for (let i = 0; i < moments.length; i++) {
      const moment = moments[i];
      const clipFilename = `${jobId}_clip_${i}.mp4`;
      const clipPath = path.join(clipsDir, clipFilename);
      
      await videoService.cutClip(videoPath, moment.start_time, moment.end_time, clipPath, jobRecord.aspectRatio || '9:16');
      cutClips.push({ ...moment, clipPath, index: i });
      
      const currentProgress = 60 + Math.round(cutProgressStep * (i + 1));
      await updateJob('cutting', currentProgress);
    }
    await updateJob('cutting', 85);

    // 6. [85-95%] Generate thumbnails
    await updateJob('generating_thumbnails', 85);
    const thumbnailsDir = getStoragePath('thumbnails');
    const thumbProgressStep = 10 / (cutClips.length || 1);

    for (let i = 0; i < cutClips.length; i++) {
      const clip = cutClips[i];
      const thumbnailFilename = `${jobId}_clip_${clip.index}.jpg`;
      const thumbnailPath = path.join(thumbnailsDir, thumbnailFilename);
      
      const thumbTime = clip.start_time + 1;
      await videoService.generateThumbnail(videoPath, thumbnailPath, thumbTime);
      clip.thumbnailPath = thumbnailPath;

      const currentProgress = 85 + Math.round(thumbProgressStep * (i + 1));
      await updateJob('generating_thumbnails', currentProgress);
    }
    await updateJob('generating_thumbnails', 95);

    // 7. [95-100%] Save clips to MongoDB
    for (const clip of cutClips) {
      await Clip.create({
        jobId: jobRecord._id,
        title: clip.title,
        clipPath: clip.clipPath,
        thumbnailPath: clip.thumbnailPath,
        startTime: clip.start_time,
        endTime: clip.end_time,
        duration: clip.end_time - clip.start_time,
        reason: clip.reason,
        viralityScore: Math.max(1, clip.virality_score || 5)
      });
    }

    jobRecord.totalClips = cutClips.length;
    jobRecord.completedAt = new Date();
    await updateJob('done', 100);

    // Cleanup temporary audio
    if (audioPath && fs.existsSync(audioPath)) {
      try { fs.unlinkSync(audioPath); } catch (e) {}
    }
    console.log(`✅ [Job ${jobId}] COMPLETED SUCCESSFULLY! ${cutClips.length} clips created.`);

  } catch (error) {
    console.error(`❌ Processing error for job ${jobId}:`, error);
    jobRecord.status = 'failed';
    jobRecord.error = error.message;
    await jobRecord.save();
  }
};

module.exports = {
  processJobDirectly
};
