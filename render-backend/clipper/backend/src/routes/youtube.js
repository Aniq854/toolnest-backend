const express = require('express');
const router = express.Router();
const path = require('path');
const fs = require('fs');
const Job = require('../models/Job');
const { extractYoutubeId, downloadVideo } = require('../services/youtubeService');
const { processJobDirectly } = require('../services/jobProcessor');

const uploadsDir = path.resolve(__dirname, '../../storage/uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

// POST /api/youtube  { youtubeUrl, duration, aspectRatio }
router.post('/', async (req, res) => {
  try {
    const { youtubeUrl, duration, aspectRatio, fast, fastMode } = req.body;

    if (!youtubeUrl) {
      return res.status(400).json({ error: 'youtubeUrl is required' });
    }

    const youtubeId = extractYoutubeId(youtubeUrl);
    if (!youtubeId) {
      return res.status(400).json({ error: 'Invalid YouTube URL' });
    }

    const durationOption = parseInt(duration) || 30;
    const selectedAspectRatio = ['9:16', '16:9', '1:1'].includes(aspectRatio) ? aspectRatio : '9:16';

    const videoFilename = `yt_${youtubeId}_${Date.now()}.mp4`;
    const videoPath = path.join(uploadsDir, videoFilename);

    // Create the job first so the frontend can poll immediately.
    const job = new Job({
      originalFilename: `YouTube Video (${youtubeId})`,
      videoPath,
      durationOption,
      aspectRatio: selectedAspectRatio,
      status: 'downloading',
      progress: 0,
      fastMode: !![true,'true',1,'1'].find(v => v === fast || v === fastMode),
    });
    await job.save();

    res.status(202).json({ jobId: job._id, status: job.status });

    // Download in the background, then run the normal AI pipeline.
    (async () => {
      try {
        console.log(`⬇️  [Job ${job._id}] Downloading YouTube video ${youtubeId}...`);
        await downloadVideo(youtubeUrl, videoPath);
        console.log(`✅ [Job ${job._id}] Download complete. Starting AI processing...`);
        await processJobDirectly(job._id.toString());
      } catch (err) {
        console.error(`❌ [Job ${job._id}] YouTube download failed:`, err.message);
        const failed = await Job.findById(job._id);
        if (failed) {
          failed.status = 'failed';
          failed.error = `YouTube download failed: ${err.message}`;
          await failed.save();
        }
      }
    })();
  } catch (error) {
    console.error('YouTube route error:', error);
    if (!res.headersSent) {
      res.status(500).json({ error: 'Internal server error', message: error.message });
    }
  }
});

module.exports = router;
