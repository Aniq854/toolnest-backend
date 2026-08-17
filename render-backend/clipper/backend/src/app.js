process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const connectDB = require('./config/db');

// Connect to MongoDB
connectDB();

const app = express();

// Middleware
app.use(cors({ origin: true, credentials: true }));
app.use(express.json());

// Health Check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'Backend AI Clipper running' });
});

// Routes
app.use('/api/upload', require('./routes/upload'));
app.use('/api/youtube', require('./routes/youtube'));
app.use('/api/jobs', require('./routes/jobs'));
app.use('/api/download', require('./routes/download'));
app.use('/api/preview', require('./routes/preview'));

// Serve Frontend Static Build if available (Single Platform Deployment)
const frontendOutDir = path.resolve(__dirname, '../../frontend/out');
if (fs.existsSync(frontendOutDir)) {
  console.log(`🌐 Serving Frontend static files from ${frontendOutDir}`);
  app.use(express.static(frontendOutDir));
  app.get('*', (req, res, next) => {
    if (req.path.startsWith('/api')) {
      return next();
    }
    const htmlFile = path.join(frontendOutDir, 'index.html');
    if (fs.existsSync(htmlFile)) {
      return res.sendFile(htmlFile);
    }
    next();
  });
}

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!', message: err.message });
});

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

module.exports = app;
