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

function buildTimeBasedMoments(videoDuration, clipLen){
  clipLen = clipLen || 30;
  let count;
  if(videoDuration<=clipLen) count=1;
  else if(videoDuration<=90) count=2;
  else if(videoDuration<=300) count=3;
  else if(videoDuration<=900) count=5;
  else count=Math.min(8, Math.max(1, Math.floor(videoDuration/clipLen)));
  const gap = videoDuration/count;
  const out=[];
  for(let i=0;i<count;i++){
    const start = Math.floor(i*gap);
    const end = Math.min(start+clipLen, Math.floor(videoDuration));
    if(end-start < 3) continue;
    out.push({start_time:start, end_time:end, title:'Clip '+(i+1), reason:'Fast time-based clip', virality_score:5});
  }
  return out.length ? out : [{start_time:0, end_time:Math.min(clipLen, Math.floor(videoDuration)), title:'Clip 1', reason:'Fast clip', virality_score:5}];
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
