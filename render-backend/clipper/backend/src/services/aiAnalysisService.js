const { GoogleGenerativeAI } = require('@google/generative-ai');

const MODEL_NAME = process.env.GEMINI_MODEL || 'gemini-1.5-flash';

// Robustly parse a JSON array out of a model response that may be wrapped
// in ```json ... ``` fences or contain surrounding prose.
const parseJsonArray = (text) => {
  if (!text) throw new Error('Empty model response');
  let cleaned = text.trim();
  // Strip markdown code fences if present
  cleaned = cleaned.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '').trim();
  try {
    return JSON.parse(cleaned);
  } catch (e) {
    // Fall back to extracting the first [...] block
    const start = cleaned.indexOf('[');
    const end = cleaned.lastIndexOf(']');
    if (start !== -1 && end !== -1 && end > start) {
      return JSON.parse(cleaned.slice(start, end + 1));
    }
    throw e;
  }
};

const findBestMoments = async (transcript, clipDuration, videoDuration) => {
  const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
  const model = genAI.getGenerativeModel({
    model: MODEL_NAME,
    generationConfig: {
      temperature: 0.2,
    },
  });

  const durationSec = videoDuration || 60;
  const targetClipDuration = clipDuration || 30;

  // Dynamic clip count formula for movies & long videos:
  // - Short video (<5 min): 3-5 clips
  // - Medium video (10-20 min): 6-10 clips
  // - Full movie (1-3 hours): 15 to 25 clips!
  let targetClipCount;
  if (durationSec > 3600) {
    // Movies / >1 hour video
    targetClipCount = Math.min(25, Math.max(15, Math.floor(durationSec / 240)));
  } else if (durationSec > 300) {
    // 5-60 minute video
    targetClipCount = Math.min(15, Math.max(5, Math.floor(durationSec / 120)));
  } else {
    // Short video
    targetClipCount = 3;
  }

  console.log(`🎬 Video duration: ${Math.round(durationSec / 60)} mins. Targeting ${targetClipCount} clips...`);

  const prompt = `You are an expert short-form video editor and content analyst. Your task is to identify the most engaging, viral-worthy moments from a video transcript.

VIDEO INFO:
- Total duration: ${Math.round(durationSec / 60)} minutes (${durationSec} seconds)
- Required clips: exactly ${targetClipCount}
- Each clip length: approximately ${targetClipDuration} seconds
- Time boundaries: start_time >= 0, end_time <= ${durationSec}

SELECTION CRITERIA (prioritize in order):
1. Strong Hooks — Moments that immediately grab attention (shocking statements, bold claims, questions)
2. Emotional Peaks — High-intensity emotions (laughter, surprise, anger, inspiration, tension, drama)
3. Key Insights — Memorable quotes, surprising facts, valuable takeaways, punchlines
4. Visual/Audio Energy — Fast-paced dialogue, dramatic pauses followed by reveals, tonal shifts
5. Completeness — Each clip MUST contain complete thoughts/sentences. NEVER cut mid-sentence.
6. Variety — Spread clips across the ENTIRE video timeline. Do NOT cluster them in one section.

TIMING RULES:
- Align start_time to the nearest transcript segment boundary (within 2 seconds of a segment start)
- Clips must NOT overlap with each other
- Leave at least 5 seconds gap between consecutive clips
- Each clip duration should be between ${Math.max(10, targetClipDuration - 10)} and ${targetClipDuration + 10} seconds

SCORING GUIDE (be honest, do NOT default to high scores):
- 9-10: Universally compelling — would go viral on any platform
- 7-8: Very engaging — strong hook or emotional moment
- 5-6: Good content — informative but not exceptional
- 3-4: Average — filler content with some value
- 1-2: Weak — low engagement potential

OUTPUT FORMAT:
Return ONLY a raw JSON array. No markdown fences. No explanation text. No prose before or after.
Each element must be: { "title": string, "start_time": number, "end_time": number, "reason": string, "virality_score": number }
- title: Short, specific, descriptive title for the clip content (max 60 chars, describe what actually happens)
- start_time / end_time: numbers in seconds
- reason: 1-2 sentences explaining WHY this moment is engaging (reference actual transcript content)
- virality_score: honest 1-10 score based on the criteria above

TRANSCRIPT TEXT:
${transcript.text || ''}

TIMED SEGMENTS:
${JSON.stringify((transcript.segments || []).slice(0, 200))}
`;

  try {
    const result = await model.generateContent(prompt);
    const response = await result.response;
    const text = response.text();
    const moments = parseJsonArray(text);

    return moments.map(m => {
      const start = Math.max(0, Math.min(m.start_time, durationSec - 5));
      const end = Math.min(durationSec, Math.max(start + 5, m.end_time));
      return {
        ...m,
        start_time: start,
        end_time: end
      };
    });
  } catch (err) {
    console.error('Gemini AI Analysis Error:', err);
    // Dynamic fallback for movies: generate evenly spaced clips across duration
    const moments = [];
    const step = Math.floor(durationSec / targetClipCount);
    let curStart = 10;
    while (curStart + targetClipDuration <= durationSec && moments.length < targetClipCount) {
      moments.push({
        title: `Movie Scene Highlight ${moments.length + 1}`,
        start_time: curStart,
        end_time: curStart + targetClipDuration,
        reason: 'High emotion / key scene extracted from movie',
        virality_score: 9
      });
      curStart += step;
    }
    return moments;
  }
};

module.exports = {
  findBestMoments
};
