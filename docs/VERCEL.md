# Vercel publication

Deploy from `frontend/`: `vercel deploy --prod`. Project: forte-vision.
The deployment publishes the React interface only. The local GPU engine and local database remain on the workstation.
The static `/api/health` reports offline; all other `/api/*` requests return HTTP 503 until a public analysis service is configured.
The explicitly labelled demonstration mode works without the backend. Real model conclusions are never synthesized as a fallback.

To connect production analysis, deploy the integrated Python backend (`frontend.backend.main:app`) on a persistent host with the model weights, appropriate CPU/GPU and persistent database. Keep its credentials server-side. Replace the offline API routes in `frontend/vercel.json` with routing to that HTTPS service, using a protected gateway for credentials and access controls. Keep large video uploads out of serverless function payloads. Do not upload `.env`, local data, videos or model weights to Vercel.

Local run from repository root: `python scripts/start_app.py --port 5174 --api-port 8000`.
Install web dependencies from `frontend/` with `npm ci`. Backend dependencies and model weights are separate; frontend builds do not prove model quality or availability.
