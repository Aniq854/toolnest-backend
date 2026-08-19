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

// ---------------------------------------------------------------------------
// Chunked upload: POST /api/upload/chunk
//
// The browser sends 3 MB pieces of one video, in order, all tagged with the
// same uploadId. Each piece is appended to <uploadId>.part; the final piece
// renames that file into storage/uploads and starts the job. Without this the
// page 404s on every video over 3 MB.
// ---------------------------------------------------------------------------
const chunkTmpPath = path.resolve(__dirname, '../../storage/chunks');
if (!fs.existsSync(chunkTmpPath)) {
  fs.mkdirSync(chunkTmpPath, { recursive: true });
}

const chunkUpload = multer({
  storage: multer.diskStorage({
    destination: (req, file, cb) => cb(null, chunkTmpPath),
    filename: (req, file, cb) => cb(null, 'part-' + Date.now() + '-' + Math.round(Math.random() * 1e9)),
  }),
  limits: { fileSize: 16 * 1024 * 1024 },   // one 3 MB piece, with headroom
}).single('chunk');

// uploadId comes from the browser, so it must never be trusted as a path
const safeId = (id) => (typeof id === 'string' && /^[A-Za-z0-9_-]{6,64}$/.test(id)) ? id : null;

const safeExt = (name) => {
  const allowed = ['.mp4', '.mov', '.mkv', '.avi', '.webm', '.flv', '.wmv', '.m4v'];
  const ext = path.extname(String(name || '')).toLowerCase();
  return allowed.includes(ext) ? ext : '.mp4';
};

router.post('/chunk', (req, res) => {
  chunkUpload(req, res, async (err) => {
    if (err) {
      console.error('Chunk upload error:', err);
      return res.status(400).json({ error: `Upload error: ${err.message}` });
    }
    if (!req.file) {
      return res.status(400).json({ error: 'No chunk received.' });
    }

    const uploadId = safeId(req.body.uploadId);
    const index = parseInt(req.body.chunkIndex, 10);
    const total = parseInt(req.body.totalChunks, 10);

    if (!uploadId || isNaN(index) || isNaN(total) || total < 1 || index < 0 || index >= total) {
      fs.unlink(req.file.path, () => {});
      return res.status(400).json({ error: 'Malformed chunk request.' });
    }

    const partPath = path.join(chunkTmpPath, uploadId + '.part');

    try {
      if (index === 0 && fs.existsSync(partPath)) {
        fs.unlinkSync(partPath);           // a retried upload starts clean
      }
      fs.appendFileSync(partPath, fs.readFileSync(req.file.path));
      fs.unlinkSync(req.file.path);
    } catch (e) {
      console.error('Chunk append failed:', e);
      try { fs.unlinkSync(req.file.path); } catch (e2) {}
      try { fs.unlinkSync(partPath); } catch (e2) {}
      return res.status(500).json({ error: 'Could not store this part of the upload.' });
    }

    if (index + 1 < total) {
      return res.json({ received: index, of: total });
    }

    // last chunk - assemble, register the job, start processing
    try {
      const originalName = String(req.body.filename || 'upload.mp4');
      const finalName = Date.now() + '-' + Math.round(Math.random() * 1e9) + safeExt(originalName);
      const finalPath = path.join(storagePath, finalName);
      fs.renameSync(partPath, finalPath);

      const { duration, aspectRatio, fast, fastMode } = req.body;
      const job = new Job({
        originalFilename: originalName,
        videoPath: finalPath,
        durationOption: parseInt(duration) || 30,
        aspectRatio: ['9:16', '16:9', '1:1'].includes(aspectRatio) ? aspectRatio : '9:16',
        status: 'pending',
        fastMode: !![true, 'true', 1, '1'].find(v => v === fast || v === fastMode),
      });
      await job.save();

      console.log(`✅ Chunked upload complete (${total} parts) for job ${job._id}. Starting processing...`);
      processJobDirectly(job._id.toString());

      return res.status(202).json({ jobId: job._id, status: job.status });
    } catch (error) {
      console.error('Chunk finalise error:', error);
      try { fs.unlinkSync(partPath); } catch (e) {}
      return res.status(500).json({ error: 'Internal server error.', message: error.message });
    }
  });
});

module.exports = router;
