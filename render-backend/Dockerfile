FROM nikolaik/python-nodejs:python3.12-nodejs20

# Install FFmpeg for Video Clipper
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

WORKDIR /app

# Copy Python Backend (Humanizer / Proxy)
COPY humanizer/ /app/humanizer/
RUN pip install --no-cache-dir -r /app/humanizer/requirements.txt

# Copy Node.js Backend (Clipper)
COPY clipper/backend/ /app/clipper/backend/
RUN cd /app/clipper/backend && npm install

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# The $PORT environment variable will be provided by Render.
# Our start.sh script handles starting all services.
CMD ["/app/start.sh"]
