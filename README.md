# AI-Powered Invoice Extraction Agent

A sophisticated document intelligence system that leverages a multi-agent **LangGraph** workflow and **Google Gemini Vision** to autonomously extract structured data from complex invoices with high precision.

**Live Demo:** [https://sxm-invoice-agent.vercel.app/](https://sxm-invoice-agent.vercel.app/)

## 🚀 Key Features
- **Multi-Agent Workflow:** Orchestrates specialized agents for OCR, layout analysis (Areas of Interest), and targeted data extraction using LangGraph.
- **Vision-Based OCR:** Employs Gemini's native vision capabilities for high-accuracy text and coordinate extraction, optimized for low-memory environments (Render's 512MB tier).
- **Interactive UI:** A React-based dashboard featuring **Konva.js** for real-time document annotation and data highlighting.
- **Real-time Progress Streaming:** Utilizes Server-Sent Events (SSE) to stream the agent's internal state and progress back to the user instantly.
- **Unified Schema:** Leverages Pydantic for strict data validation and shared type definitions between the Python backend and React frontend.

## 🛠️ Tech Stack
- **Backend:** FastAPI, LangGraph, LangChain, Pydantic, Google Gemini Pro Vision.
- **Frontend:** React (Vite), Konva.js (HTML5 Canvas), PDF.js, Axios.
- **Deployment:** Render (Backend), Vercel (Frontend).

## 🏗️ Technical Architecture
1. **OCR Stage:** Gemini Vision extracts raw tokens and maps them to a normalized 0-1000 coordinate system.
2. **Layout Analysis:** An analyst agent identifies functional "Areas of Interest" (Header, Line Items, Summary).
3. **Targeted Extraction:** Specialized extractors parse metadata, itemized tables, and financial totals from their respective regions.
4. **Aggregation:** A final node consolidates all agent outputs into a validated `CompleteInvoice` schema.

## 🔮 Future Work
- **Parallel Extraction:** Optimize the workflow by running the Header, Line Items, and Summary extraction nodes in parallel rather than sequentially, significantly reducing total latency.
- **Human-in-the-loop (HITL):** Implement a review stage where users can correct extracted data directly on the UI, feeding corrections back into the system.
- **Multi-page Support:** Expand the graph to handle complex, multi-page PDF documents and cross-page table reconstruction.

---

## 💻 Local Setup

### Backend
1. Navigate to `backend/`.
2. Create and activate a virtual environment.
3. Install dependencies: `pip install -r requirements.txt`.
4. Configure `GOOGLE_API_KEY` in `backend/.env`.
5. Run: `uvicorn app.main:app --reload`.

### Frontend
1. Navigate to `frontend/`.
2. Install dependencies: `npm install`.
3. Start development server: `npm run dev`.

### Quick Start
Use the root-level scripts: `./run_backend.sh` and `./run_frontend.sh`.