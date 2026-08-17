const mongoose = require('mongoose');

const connectDB = async () => {
  try {
    const options = {
      serverSelectionTimeoutMS: 5000,
    };

    const conn = await mongoose.connect(process.env.MONGODB_URI, options);
    console.log(`✅ MongoDB Connected: ${conn.connection.host}`);
    return conn;
  } catch (error) {
    console.warn(`⚠️ Primary MongoDB Atlas connection failed (${error.message}). Retrying with direct fallback options...`);
    try {
      // Try fallback connection without srv or with tls options
      const conn = await mongoose.connect(process.env.MONGODB_URI, {
        serverSelectionTimeoutMS: 10000,
        tls: true,
        tlsAllowInvalidCertificates: true
      });
      console.log(`✅ MongoDB Connected via Fallback TLS: ${conn.connection.host}`);
      return conn;
    } catch (fallbackError) {
      console.error(`❌ MongoDB Connection Error: ${fallbackError.message}`);
    }
  }
};

module.exports = connectDB;
