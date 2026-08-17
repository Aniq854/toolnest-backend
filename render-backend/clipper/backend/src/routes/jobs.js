const express = require('express');
const router = express.Router();
const Job = require('../models/Job');
const Clip = require('../models/Clip');

router.get('/:id/status', async (req, res) => {
  try {
    const job = await Job.findById(req.params.id);
    if (!job) {
      return res.status(404).json({ error: 'Job not found' });
    }
    res.json({
      status: job.status,
      progress: job.progress,
      error: job.error,
      totalClips: job.totalClips
    });
  } catch (error) {
    console.error('Get status error:', error);
    res.status(500).json({ error: 'Internal server error.', message: error.message });
  }
});

router.get('/:id/clips', async (req, res) => {
  try {
    const job = await Job.findById(req.params.id);
    if (!job) {
      return res.status(404).json({ error: 'Job not found' });
    }
    
    const clips = await Clip.find({ jobId: job._id }).sort({ createdAt: 1 });
    
    // In a real app we might attach complete URLs, but here we can just send the relative paths or build URLs.
    const clipsWithUrls = clips.map(clip => {
      const clipObj = clip.toObject();
      clipObj.previewUrl = `/api/preview/${clip._id}`;
      clipObj.downloadUrl = `/api/download/${clip._id}`;
      clipObj.thumbnailUrl = `/api/download/thumbnail/${clip._id}`;
      return clipObj;
    });

    res.json(clipsWithUrls);
  } catch (error) {
    console.error('Get clips error:', error);
    res.status(500).json({ error: 'Internal server error.', message: error.message });
  }
});

module.exports = router;
