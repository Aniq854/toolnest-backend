const Redis = require('ioredis');

const redisConfig = {
  host: process.env.REDIS_HOST || '127.0.0.1',
  port: parseInt(process.env.REDIS_PORT) || 6379,
  maxRetriesPerRequest: null,
};

// Cloud Redis needs password
if (process.env.REDIS_PASSWORD) {
  redisConfig.password = process.env.REDIS_PASSWORD;
  redisConfig.username = 'default';
}

// Upstash requires TLS
if (process.env.REDIS_TLS === 'true') {
  redisConfig.tls = { rejectUnauthorized: false };
}

const connection = new Redis(redisConfig);

connection.on('error', (err) => {
  console.error('Redis connection error:', err);
});

module.exports = connection;
