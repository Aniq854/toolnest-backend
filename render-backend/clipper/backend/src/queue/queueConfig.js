const { Queue } = require('bullmq');
const connection = require('../config/redis');

const videoQueue = new Queue('video-processing', {
  connection,
  defaultJobOptions: {
    attempts: 3,
    backoff: {
      type: 'exponential',
      delay: 5000,
    },
    removeOnComplete: {
      age: 86400, // 24 hours
    },
    removeOnFail: {
      age: 604800, // 7 days
    },
  },
});

module.exports = {
  videoQueue,
  connection,
};
