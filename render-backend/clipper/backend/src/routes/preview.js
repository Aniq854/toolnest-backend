const express = require('express');
const router = express.Router();
const fs = require('fs');
const Clip = require('../models/Clip');

// GET /api/preview/:clipId
router.get('/:clipId', async (req, res) => {
  try {
    const clip = await Clip.findById(req.params.clipId);
    if (!clip) {
      return res.status(404).json({ error: 'Clip not found' });
    }

    const videoPath = clip.clipPath;
    if (!fs.existsSync(videoPath)) {
      return res.status(404).json({ error: 'Video file not found on server' });
    }

    const stat = fs.statSync(videoPath);
    const fileSize = stat.size;
    const range = req.headers.range;

    if (range) {
      const parts = range.replace(/bytes=/, '').split('-');
      const start = parseInt(parts[0], 10);
      const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;

      const chunksize = (end - start) + 1;
      const file = fs.createReadStream(videoPath, { start, end });
      const head = {
        'Content-Range': `bytes ${start}-${end}/${fileSize}`,
        'Accept-Ranges': 'bytes',
        'Content-Length': chunksize,
        'Content-Type': 'video/mp4',
      };

      res.writeHead(206, head);
      file.pipe(res);
    } else {
      const head = {
        'Content-Length': fileSize,
        'Content-Type': 'video/mp4',
      };
      res.writeHead(200, head);
      fs.createReadStream(videoPath).pipe(res);
    }
  } catch (error) {
    console.error('Preview error:', error);
    res.status(500).json({ error: 'Internal server error', message: error.message });
  }
});

module.exports = router;
