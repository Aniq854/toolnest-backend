const express = require('express');
const router = express.Router();
const path = require('path');
const fs = require('fs');
const archiver = require('archiver');
const Clip = require('../models/Clip');
const Job = require('../models/Job');

// GET /api/download/thumbnail/:clipId - Serve thumbnail image
router.get('/thumbnail/:clipId', async (req, res) => {
  try {
    const clip = await Clip.findById(req.params.clipId);
    if (!clip || !clip.thumbnailPath || !fs.existsSync(clip.thumbnailPath)) {
      return res.status(404).send('Thumbnail not found');
    }

    res.sendFile(path.resolve(clip.thumbnailPath));
  } catch (error) {
    console.error('Thumbnail serve error:', error);
    res.status(500).send('Error serving thumbnail');
  }
});

// Make titles safe for filenames (strip emojis / special characters)
const safeFilename = (title, fallback) => {
  const cleaned = (title || '')
    .replace(/[^a-zA-Z0-9 _-]/g, '')
    .trim()
    .replace(/\s+/g, '_');
  return cleaned || fallback;
};

// GET /api/download/:clipId - Single clip download
router.get('/:clipId', async (req, res) => {
  try {
    const clip = await Clip.findById(req.params.clipId);
    if (!clip) return res.status(404).json({ error: 'Clip not found' });

    if (!clip.clipPath || !fs.existsSync(clip.clipPath)) {
      return res.status(404).json({ error: 'Clip file not found on server' });
    }

    res.download(clip.clipPath, `${safeFilename(clip.title, 'clip')}.mp4`);
  } catch (error) {
    console.error('Download error:', error);
    res.status(500).json({ error: 'Internal server error', message: error.message });
  }
});

// GET /api/download/:jobId/all - Download all clips as ZIP
router.get('/:jobId/all', async (req, res) => {
  try {
    const clips = await Clip.find({ jobId: req.params.jobId });
    if (!clips || clips.length === 0) {
      return res.status(404).json({ error: 'No clips found for this job' });
    }

    res.attachment(`clips_${req.params.jobId}.zip`);
    const archive = archiver('zip', { zlib: { level: 9 } });

    archive.on('error', function(err) {
      throw err;
    });

    archive.pipe(res);

    clips.forEach((clip, index) => {
      if (fs.existsSync(clip.clipPath)) {
        archive.file(clip.clipPath, { name: `${safeFilename(clip.title, `clip_${index + 1}`)}.mp4` });
      }
    });

    archive.finalize();
  } catch (error) {
    console.error('Download all error:', error);
    res.status(500).json({ error: 'Internal server error', message: error.message });
  }
});

module.exports = router;
