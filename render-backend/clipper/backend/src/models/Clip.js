const mongoose = require('mongoose');

const ClipSchema = new mongoose.Schema({
  jobId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Job',
    required: true,
    index: true,
  },
  title: {
    type: String,
  },
  clipPath: {
    type: String,
  },
  thumbnailPath: {
    type: String,
  },
  startTime: {
    type: Number,
  },
  endTime: {
    type: Number,
  },
  duration: {
    type: Number,
  },
  reason: {
    type: String,
  },
  viralityScore: {
    type: Number,
    min: 0,
    max: 10,
    default: 5,
  },
  createdAt: {
    type: Date,
    default: Date.now,
  },
});

module.exports = mongoose.model('Clip', ClipSchema);
