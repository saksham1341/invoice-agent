# Invoice Extraction Agent

An AI-powered agent that extracts structured data from invoices using LangGraph and Gemini.

**Live Demo:** [https://sxm-invoice-agent.vercel.app/](https://sxm-invoice-agent.vercel.app/)

## Features
- **Real-time Streaming**: Watch the agent process the invoice in real-time.
- **Visual Feedback**: Bounding boxes highlight extracted data on the document.
- **Structured Data**: Extracts vendor details, line items, and totals into a structured format.
- **Pure Pydantic Schema**: Unified data models between backend and frontend.

## Setup

### Backend
1. Navigate to `backend/`.
2. Create a virtual environment: `python -m venv venv`.
3. Activate it: `source venv/bin/activate`.
4. Install dependencies: `pip install -r requirements.txt`.
5. Set your `GOOGLE_API_KEY` and `GEMINI_MODEL_NAME` (e.g., `gemini-2.5-flash` or `gemini-1.5-pro`) in `backend/.env`.

### Frontend
1. Navigate to `frontend/`.
2. Install dependencies: `npm install`.
3. Start the dev server: `npm run dev`.

## Running the Application
You can use the helper scripts in the root directory:
- `./run_backend.sh`
- `./run_frontend.sh`
