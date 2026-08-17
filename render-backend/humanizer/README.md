# AI Text Humanizer

AI (ChatGPT / Claude / Gemini) ka likha hua robotic draft le kar usay natural,
readable, insaani writing mein badalta hai — tone, reading level aur rewrite
strength ke controls ke saath, plus ek **before/after quality report**.

**Cost: 0 rupees.** Poora stack open-source hai aur LLM ke liye free-tier
providers (Groq / Gemini / OpenRouter) ya bilkul local Ollama use hota hai.

---

## 1. Scope ki ek zaroori baat

Yeh tool **writing quality** behtar banane ke liye hai — draft polish karna,
awkward jumle theek karna, non-native English ko natural banana, SEO content
ko readable banana.

Yeh **"plagiarism detector bypass" ya assignment cheating** ke liye nahi hai,
aur us maqsad se features add karna is project ka hissa nahi. Wajah sirf
akhlaqi nahi — business wajah bhi hai:

- "Detector bypass" wale tools par universities, Turnitin aur Google
  lagatar crackdown karte hain — product ki umar chhoti hoti hai.
- Payment gateways (Stripe/PayPal) aise products ke accounts band kar dete hain.
- "Writing assistant" positioning par market bara hai (Grammarly, QuillBot,
  Wordtune sab isi jagah hain) aur SEO agencies + non-native writers paisay
  dete hain.

Yani wahi core technology, magar tikne wali packaging.

---

## 2. Tech Stack (sab free)

| Layer | Kya use ho raha hai | Kyun |
|---|---|---|
| Backend | **Python + FastAPI** | Fast, auto API docs (`/docs`), async support |
| LLM | **Groq / Gemini / OpenRouter / Ollama** | Chaaron ke free tiers hain; Ollama 100% offline |
| HTTP client | **httpx** | Async, koi bhaari SDK nahi |
| Frontend | **Vanilla HTML + CSS + JS** | Koi npm, koi build step, koi node_modules — seedha chalta hai |
| Config | **pydantic-settings + .env** | Keys code mein nahi jaatin |
| Tests | **pytest** | Core logic verify hoti hai |
| Hosting | Local, ya Render / Hugging Face Spaces free tier | Bilkul free |

**LangChain jaan boojh kar use nahi kiya** — is use-case mein woh sirf ek
prompt bhejta hai aur jawab wapas leta hai. 200 lines ka apna provider layer
zyada tez, samajhne mein aasan aur debug karne mein behtar hai.

---

## 3. Folder Structure

```
ai-humanizer/
│
├── run.py                      # Yahan se app chalti hai: python run.py
├── requirements.txt            # Python packages
├── .env.example                # Config ka template (copy -> .env)
├── .gitignore                  # .env ko GitHub par jaane se rokta hai
├── README.md                   # Yeh file
│
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app banata hai, routes jorta hai
│   ├── config.py               # .env parh kar settings object banata hai
│   ├── schemas.py              # Request/response ke shapes (validation)
│   │
│   ├── providers/              # === LLM se baat karne wali layer ===
│   │   ├── __init__.py         # Factory: naam do, provider milega
│   │   ├── base.py             # Common interface (naya provider add karna aasan)
│   │   ├── openai_compatible.py# Groq + OpenRouter + OpenAI + Ollama (ek hi format)
│   │   └── gemini_provider.py  # Google Gemini (format alag hai)
│   │
│   ├── core/                   # === Asli dimagh — product ki value yahan hai ===
│   │   ├── __init__.py
│   │   ├── prompts.py          # ⭐ SABSE AHEM FILE: system prompt + tone + style block
│   │   ├── humanizer.py        # Orchestrator: chunk -> LLM -> clean -> metrics
│   │   ├── fingerprint.py      # ⭐ MOAT: writing habits maths se naapta hai (free)
│   │   ├── style_profile.py    # ⭐ "Meri awaaz" profile banata + save karta hai
│   │   ├── chunker.py          # Lamba text paragraph boundaries par torta hai
│   │   ├── postprocess.py      # Preamble hatana, typography theek karna
│   │   └── readability.py      # Metrics + naturalness score (koi API call nahi)
│   │
│   ├── routes/                 # === HTTP endpoints ===
│   │   ├── __init__.py
│   │   ├── humanize.py         # POST /api/humanize , /api/rewrite-sentence
│   │   ├── analyze.py          # POST /api/analyze (free, bina LLM)
│   │   └── profiles.py         # Voice profiles ka CRUD
│   │
│   └── static/                 # === Frontend (no build step) ===
│       ├── index.html          # UI ka structure
│       ├── style.css           # Dark theme styling
│       └── app.js              # Fetch calls + metrics rendering
│
├── data/
│   └── profiles/               # Voice profiles JSON mein (gitignored)
│
└── tests/
    ├── test_readability.py     # Metrics aur score ke tests
    ├── test_chunker.py         # Chunking aur postprocess ke tests
    └── test_style_profile.py   # Fingerprint, match score, storage ke tests
```

### Har file ka kaam — ek line mein

| File | Kaam |
|---|---|
| `run.py` | Server start karta hai port 8000 par |
| `app/main.py` | FastAPI app, CORS, static files, `/health`, `/` |
| `app/config.py` | Saari settings ek jagah, `.env` se |
| `app/schemas.py` | Input validate karta hai (galat data pehle hi rok deta hai) |
| `app/providers/base.py` | Abstract class — har provider `complete()` deta hai |
| `app/providers/openai_compatible.py` | 4 providers ek hi class se (kyunki API format same hai) |
| `app/providers/gemini_provider.py` | Gemini ka apna REST format |
| `app/providers/__init__.py` | `get_provider("groq")` -> object |
| `app/core/prompts.py` | System prompt, 6 tone presets, 3 levels, 3 strengths, **style block builder** |
| `app/core/fingerprint.py` | 10 measurable writing habits + voice-match score (koi LLM nahi) |
| `app/core/style_profile.py` | Samples se profile banata hai, JSON files mein save karta hai |
| `app/core/chunker.py` | 2500 chars ke chunks, jumla beech se nahi katta |
| `app/core/postprocess.py` | "Here's the rewritten text:" hatata hai, em-dash/smart quotes fix |
| `app/core/readability.py` | Flesch score, sentence variety, cliche count, passive voice |
| `app/core/humanizer.py` | Sab kuch jorta hai, chunks parallel chalata hai (max 3) |
| `app/routes/humanize.py` | Main endpoint + per-sentence rewrite |
| `app/routes/analyze.py` | Sirf metrics — bilkul muft, foran |
| `app/routes/profiles.py` | Voice profiles banana / list / delete |
| `app/static/*` | UI (voice card, diff view, voice-match meter) |

---

## 4. Setup (5 minute)

### Step 1 — Project kholein aur virtual environment banayein

```bash
cd ai-humanizer
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Mac / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### Step 2 — Free API key lein (kisi ek se)

| Provider | Link | Free tier |
|---|---|---|
| **Groq** (recommended) | https://console.groq.com/keys | Bara free tier, sabse tez |
| **Google Gemini** | https://aistudio.google.com/apikey | Bara free tier |
| **OpenRouter** | https://openrouter.ai/keys | Kuch models `:free` hain |
| **Ollama** | https://ollama.com | 100% free, offline, key nahi chahiye |

Groq sabse aasan hai: sign up karein, key copy karein, bas.

### Step 3 — `.env` banayein

```bash
cp .env.example .env      # Windows par: copy .env.example .env
```

Phir `.env` kholein aur do line bharein:

```
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_yahan_apni_key_paste_karein
```

### Step 4 — Chalayein

```bash
python run.py
```

Browser mein kholein: **http://127.0.0.1:8000**
API docs: **http://127.0.0.1:8000/docs**

### Step 5 — Tests

```bash
pytest -q        # 39 tests pass hone chahiye
```

---

## 5. ⭐ "Meri awaaz mein likho" — Voice Profile

Yeh is project ka **differentiator** hai. Har doosra humanizer ek generic
"natural English" deta hai jo kisi ki bhi awaaz nahi hoti. Yeh tool user ki
**apni** awaaz seekhta hai.

### Kaise kaam karta hai

```
User apne 2-3 samples deta hai  (kam az kam 150 lafz, uske KHUD ke likhe hue)
        |
        +--> fingerprint.py   -->  10 measurable habits   (maths, 0 cost)
        |                          avg jumla lambai, variety, contraction rate,
        |                          "you" rate, "I" rate, comma rate, sawaal %,
        |                          paragraph lambai, bhaari lafz %, flesch
        |
        +--> LLM (SIRF EK DAFA) -->  qualitative traits    (JSON)
                                     voice_summary, tone_labels,
                                     signature_phrases, common_openers,
                                     avoid_words, punctuation_habits
        |
        v
   data/profiles/mera-style.json     <-- save. Aage LLM cost NAHI aati.
        |
        v
   Har rewrite mein prompt ke andar inject hota hai (build_style_block)
        |
        v
   Rewrite ke baad: output ka fingerprint vs profile ka fingerprint
        |
        v
   ⭐ VOICE MATCH SCORE (0-100%) + kaun sa signal off hai
```

### Do design faislay jo ahem hain

**1. LLM ko sirf sifaat nahi, NUMBERS bhi diye jaate hain.** Sirf "casual
likho" kehna kaam nahi karta. `build_style_block()` prompt mein aisa daalta
hai: *"average jumla ~14 lafz; contractions freely use karo; reader ko seedha
'you' keh kar address karo; paragraph ~3 jumlon ke rakho."* Yeh concrete
targets output ko waqai match karate hain.

**2. Voice match score objective hai, LLM ki raaye nahi.** Output ka
fingerprint dobara naapa jata hai aur profile se compare hota hai
(`fingerprint.match_score`). Yani user ko **saboot** milta hai, sirf daawa
nahi. Aur agar match kam ho to tool bataata hai kyun — misal:
*"contractions: aapke style se kam hai (5.0 vs 11.3)"*.

Yeh doosra point aapka trust-builder hai. Competitors black box dete hain;
aap numbers dete hain.

### Business ke lehaz se yeh kyun jeetta hai

| | Detector bypass | Voice profile |
|---|---|---|
| Muqabla | Turnitin/GPTZero ke against arms race | Kisi ke against nahi |
| Har update par | product toot jata hai | koi asar nahi |
| Switching cost | zero — user kahin bhi chala jaye | uska profile yahan hai |
| Payment risk | Stripe account band ho sakta hai | normal SaaS |
| Team plan | nahi bech sakte | "agency brand voice" — asli paisa |

### API

```bash
# Profile banayein (ek LLM call)
curl -X POST localhost:8000/api/profiles \
  -H 'Content-Type: application/json' \
  -d '{"name":"Mera blog style","samples":["...apni purani writing...","...doosra sample..."]}'

# Profile use kar ke rewrite
curl -X POST localhost:8000/api/humanize \
  -H 'Content-Type: application/json' \
  -d '{"text":"AI ka draft...","profile_id":"mera-blog-style","strength":2}'

# Response mein: voice_match: 84.6, voice_gaps: [...], profile_used: "..."
```

Baaqi endpoints: `GET /api/profiles`, `GET /api/profiles/{id}`,
`DELETE /api/profiles/{id}`, aur `POST /api/rewrite-sentence`
(ek jumla dobara likhne ke liye — "Regenerate" button).

### UI mein kya mila

- Sab se upar **Voice Profile card** — profile banayein, choose karein, delete karein
- Profile active ho to tone/level dropdowns khud disable ho jate hain
  (kyunki user ki apni awaaz preset ko override karti hai)
- Rewrite ke baad **voice match meter** (green/yellow/red) + gap explanations
- **Diff dikhayein** button — jumla ba jumla kya badla, aur har jumle par
  "Regenerate"

### Zaroori warning user ko dikhayein

Samples **user ke apne likhe hue** hone chahiye. Agar woh AI ka output paste
karega to tool AI ki hi awaaz seekh lega — poora faida khatam. UI mein yeh
warning placeholder text mein already maujood hai.

---

## 6. Ollama se bilkul offline chalana (koi key nahi)

```bash
# 1. Ollama install karein: https://ollama.com
ollama pull llama3.1

# 2. .env mein:
LLM_PROVIDER=ollama
```

Bas. Na key, na internet, na bill.

---

## 7. API

### `POST /api/humanize`

```json
{
  "text": "Aapka draft yahan...",
  "tone": "blog",
  "reading_level": "medium",
  "strength": 2,
  "keep_length": true,
  "provider": null
}
```

Response mein `output`, `provider_used`, aur `before`/`after` metrics aate hain.

- `tone`: `casual` | `professional` | `academic` | `blog` | `simple` | `storytelling`
- `reading_level`: `easy` | `medium` | `advanced`
- `strength`: `1` (halki edit) | `2` (mutawazin) | `3` (gehra rewrite)

### `POST /api/analyze`

Sirf `{"text": "..."}` bhejein. Koi LLM call nahi hoti, is liye
**bilkul free aur instant** — metrics + suggestions milte hain.

### `GET /api/providers` , `GET /health`

Utility endpoints.

---

## 8. Naturalness score kya hai?

Yeh **AI detector nahi hai** — aur jaan boojh kar nahi hai. Yeh writing quality
ke 4 objective signals naapta hai:

1. **Sentence variety** (standard deviation) — insaan jumlon ki lambai zyada
   badalta hai, AI ek jaisi lambai rakhta hai
2. **Cliche density** — "in today's fast-paced world", "delve into" wagera
3. **Passive voice density**
4. **Flesch reading ease**

Iska faida: aap dekh sakte hain ke rewrite se text **waqai** behtar hua ya
nahi, kisi third-party detector par bharosa kiye baghair.

---

## 9. Free hosting

| Platform | Kaise |
|---|---|
| **Hugging Face Spaces** | Naya Space (Docker/Python), repo push karein, `HF Secrets` mein API key |
| **Render** free tier | Web Service, build: `pip install -r requirements.txt`, start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Railway / Fly.io** | Free credits, wahi start command |

**Zaroori:** kabhi `.env` GitHub par push na karein — `.gitignore` mein
already shamil hai. Hosting par key hamesha "Environment Variables" /
"Secrets" mein daalein.

---

## 10. Aage kya add kar sakte hain (roadmap)

**Ho gaya**
- [x] Voice profile ("meri awaaz mein likho") + voice-match score
- [x] Side-by-side diff view (kaun sa jumla badla)
- [x] Sentence-by-sentence "Regenerate" button
- [x] Before/after quality report

**Phase 1 — abhi karein (sab se ahem)**
- [ ] `prompts.py` par 20-30 real drafts se experiment — yahi product ki jaan hai
- [ ] 8 free micro-tools ke alag pages (SEO) — readability checker, passive
      voice detector, cliche finder wagera. `/api/analyze` pehle se maujood
      hai aur us ki serving cost **zero** hai, is liye traffic ka bill nahi aata.

**Phase 2 — utility**
- [ ] File upload (.docx / .txt / .pdf se text nikalna)
- [ ] Multi-language (Urdu, Roman Urdu output)
- [ ] Rate limiting (`slowapi`) taake aapka free tier na jale
- [ ] Profile ko time ke saath behtar karna (user ke edits se seekhna)

**Phase 3 — product**
- [ ] Chrome extension (Google Docs / WordPress mein hi kaam kare)
- [ ] History + user accounts (SQLite se shuru karein)
- [ ] Team / agency brand-voice profiles — **yahan asli paying customers hain**

---

## 11. Debugging tips

| Masla | Hal |
|---|---|
| `GROQ_API_KEY .env mein set nahi hai` | `.env` file project root mein honi chahiye, `app/` ke andar nahi |
| `502` error | Key ghalat hai ya free-tier limit khatam — `.env` mein doosra provider try karein |
| Output mein "Here's the rewritten..." | `postprocess.py` ke `PREAMBLES` list mein woh pattern add karein |
| Output ka matlab badal jata hai | `strength` 3 se 2 ya 1 par le aayein |
| Bohat dheema | `chunk_size` barha dein, ya `humanizer.py` mein `Semaphore(3)` ko `5` karein |
| Rewrite "AI jaisa" hi lagta hai | `prompts.py` ka `SYSTEM` prompt edit karein — 90% control wahin hai |
| Voice match hamesha kam aata hai | Profile mein zyada samples (300+ lafz) daalein, aur `strength` 3 karein |
| Voice match theek magar output ajeeb | `fingerprint.py` ke `WEIGHTS` mein tolerance barha dein |
| Profile save nahi hota | `data/profiles/` folder ki write permission check karein |

---

## License

MIT — jo chahein karein.
