const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const Job = require('../models/Job');
const { processJobDirectly } = require('../services/jobProcessor');

const storagePath = path.resolve(__dirname, '../../storage/uploads');

if (!fs.existsSync(storagePath)) {
  fs.mkdirSync(storagePath, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, storagePath);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, uniqueSuffix + path.extname(file.originalname));
  }
});

const fileFilter = (req, file, cb) => {
  const allowedExtensions = ['.mp4', '.mov', '.mkv', '.avi', '.webm', '.flv', '.wmv', '.m4v'];
  const ext = path.extname(file.originalname).toLowerCase();
  
  if (allowedExtensions.includes(ext) || file.mimetype.startsWith('video/')) {
    cb(null, true);
  } else {
    cb(new Error('Invalid file type. Only video files are allowed.'), false);
  }
};

const upload = multer({
  storage: storage,
  fileFilter: fileFilter,
  limits: { fileSize: 2 * 1024 * 1024 * 1024 } // 2GB limit
}).single('video');

router.post('/', (req, res) => {
  upload(req, res, async (err) => {
    if (err instanceof multer.MulterError) {
      console.error('Multer error:', err);
      return res.status(400).json({ error: `Upload error: ${err.message}` });
    } else if (err) {
      console.error('File filter error:', err);
      return res.status(400).json({ error: err.message });
    }

    if (!req.file) {
      return res.status(400).json({ error: 'No video file provided.' });
    }

    try {
      const { duration, aspectRatio, fast, fastMode } = req.body;
      const durationOption = parseInt(duration) || 30;
      const selectedAspectRatio = ['9:16', '16:9', '1:1'].includes(aspectRatio) ? aspectRatio : '9:16';

      const job = new Job({
        originalFilename: req.file.originalname,
        videoPath: req.file.path,
        durationOption: durationOption,
        aspectRatio: selectedAspectRatio,
        status: 'pending',
        fastMode: !![true,'true',1,'1'].find(v => v === fast || v === fastMode),
      });
      await job.save();

      console.log(`✅ Upload received for job ${job._id}. Starting instant processing...`);

      // Trigger instant processing immediately in background
      processJobDirectly(job._id.toString());

      res.status(202).json({ jobId: job._id, status: job.status });
    } catch (error) {
      console.error('Upload processing error:', error);
      res.status(500).json({ error: 'Internal server error.', message: error.message });
    }
  });
});

module.exports = router;
