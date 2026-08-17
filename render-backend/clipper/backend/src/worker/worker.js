require('dotenv').config({ path: require('path').resolve(__dirname, '../../.env') });
const { Worker } = require('bullmq');
const path = require('path');
const fs = require('fs');
const mongoose = require('mongoose');
const { connection } = require('../queue/queueConfig');
const Job = require('../models/Job');
const Clip = require('../models/Clip');
const videoService = require('../services/videoService');
const transcriptionService = require('../services/transcriptionService');
const aiAnalysisService = require('../services/aiAnalysisService');
const connectDB = require('../config/db');

// Connect to MongoDB
connectDB();

const getStoragePath = (subDir) => {
  const p = path.resolve(__dirname, '../../', process.env.STORAGE_PATH || '../storage', subDir);
  if (!fs.existsSync(p)) {
    fs.mkdirSync(p, { recursive: true });
  }
  return p;
};

const worker = new Worker('video-processing', async (bullJob) => {
  const { jobId } = bullJob.data;
  let jobRecord = await Job.findById(jobId);
  if (!jobRecord) {
    throw new Error('Job not found in database');
  }

  try {
    const updateJob = async (status, progress) => {
      jobRecord.status = status;
      jobRecord.progress = progress;
      await jobRecord.save();
      await bullJob.updateProgress(progress);
      console.log(`Job ${jobId} status: ${status} [${progress}%]`);
    };

    // 1. [0-10%] Validate video exists
    await updateJob('processing', 0);
    const videoPath = jobRecord.videoPath;
    if (!fs.existsSync(videoPath)) {
      throw new Error(`Video file not found at ${videoPath}`);
    }
    const videoDuration = await videoService.getVideoDuration(videoPath);
    await updateJob('processing', 10);

    // 2. [10-20%] Extract audio
    await updateJob('extracting_audio', 10);
    const audioDir = getStoragePath('audio');
    const audioPath = path.join(audioDir, `${jobId}.wav`);
    await videoService.extractAudio(videoPath, audioPath);
    await updateJob('extracting_audio', 20);

    // 3. [20-45%] Transcribe
    await updateJob('transcribing', 20);
    const transcript = await transcriptionService.transcribeAudio(audioPath);
    jobRecord.transcript = transcript;
    await updateJob('transcribing', 45);

    // 4. [45-60%] AI Analysis
    await updateJob('analyzing', 45);
    const moments = await aiAnalysisService.findBestMoments(transcript, jobRecord.durationOption, videoDuration);
    await updateJob('analyzing', 60);

    // 5. [60-85%] Cut clips
    await updateJob('cutting', 60);
    const clipsDir = getStoragePath('clips');
    const cutClips = [];
    const cutProgressStep = 25 / moments.length;

    for (let i = 0; i < moments.length; i++) {
      const moment = moments[i];
      const clipFilename = `${jobId}_clip_${i}.mp4`;
      const clipPath = path.join(clipsDir, clipFilename);
      
      await videoService.cutClip(videoPath, moment.start_time, moment.end_time, clipPath);
      cutClips.push({ ...moment, clipPath, index: i });
      
      const currentProgress = 60 + Math.round(cutProgressStep * (i + 1));
      await updateJob('cutting', currentProgress);
    }
    await updateJob('cutting', 85);

    // 6. [85-95%] Generate thumbnails
    await updateJob('generating_thumbnails', 85);
    const thumbnailsDir = getStoragePath('thumbnails');
    const thumbProgressStep = 10 / cutClips.length;

    for (let i = 0; i < cutClips.length; i++) {
      const clip = cutClips[i];
      const thumbnailFilename = `${jobId}_clip_${clip.index}.jpg`;
      const thumbnailPath = path.join(thumbnailsDir, thumbnailFilename);
      
      // Thumbnail at 10% into the clip or start time + 1 second
      const thumbTime = clip.start_time + 1;
      await videoService.generateThumbnail(videoPath, thumbnailPath, thumbTime);
      clip.thumbnailPath = thumbnailPath;

      const currentProgress = 85 + Math.round(thumbProgressStep * (i + 1));
      await updateJob('generating_thumbnails', currentProgress);
    }
    await updateJob('generating_thumbnails', 95);

    // 7. [95-100%] Save clips to DB
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
        viralityScore: clip.virality_score
      });
    }

    jobRecord.totalClips = cutClips.length;
    jobRecord.completedAt = new Date();
    await updateJob('done', 100);

    // Cleanup audio
    if (fs.existsSync(audioPath)) {
      fs.unlinkSync(audioPath);
    }

  } catch (error) {
    console.error(`Worker error for job ${jobId}:`, error);
    jobRecord.status = 'failed';
    jobRecord.error = error.message;
    await jobRecord.save();
    throw error;
  }
}, {
  connection,
  concurrency: 1
});

worker.on('failed', (job, err) => {
  console.error(`${job.id} has failed with ${err.message}`);
});

process.on('SIGTERM', async () => {
  console.log('Shutting down worker...');
  await worker.close();
  process.exit(0);
});

process.on('SIGINT', async () => {
  console.log('Shutting down worker...');
  await worker.close();
  process.exit(0);
});
