const mongoose = require('mongoose');

const JobSchema = new mongoose.Schema({
  userId: {
    type: String,
    default: 'anonymous',
  },
  originalFilename: {
    type: String,
    required: true,
  },
  videoPath: {
    type: String,
    required: true,
  },
  durationOption: {
    type: Number,
    required: true,
  },
  aspectRatio: {
    type: String,
    enum: ['9:16', '16:9', '1:1'],
    default: '9:16',
  },
  fastMode: {
    type: Boolean,
    default: false,
  },
  status: {
    type: String,
    enum: [
      'pending',
      'downloading',
      'processing',
      'extracting_audio',
      'transcribing',
      'analyzing',
      'cutting',
      'generating_thumbnails',
      'done',
      'failed',
    ],
    default: 'pending',
  },
  progress: {
    type: Number,
    default: 0,
    min: 0,
    max: 100,
  },
  error: {
    type: String,
  },
  transcript: {
    type: mongoose.Schema.Types.Mixed,
  },
  totalClips: {
    type: Number,
    default: 0,
  },
  createdAt: {
    type: Date,
    default: Date.now,
  },
  completedAt: {
    type: Date,
  },
});

module.exports = mongoose.model('Job', JobSchema);
