# LICENSES — models and libraries used by the engine

All components are open source with commercially permissive licenses (Apache-2.0 / MIT / BSD / PSF / LGPL for
dynamically linked media libraries). No cloud AI API is used at any point; nothing with a non-commercial or
copyleft-only (GPL/AGPL) license is linked into the engine. Checked on 2026-10-17 (Hugging Face model cards
via the Hub API and package metadata).

## Models (weights downloaded once by `scripts/download_weights.py`)

| component | id / source | license | role |
|---|---|---|---|
| Grounding DINO tiny | `IDEA-Research/grounding-dino-tiny` (HF) | Apache-2.0 | open-vocabulary object detection (person, cash, bag, document, id card, phone, storage unit, counting machine, laptop) |
| Grounding DINO base | `IDEA-Research/grounding-dino-base` (HF) | Apache-2.0 | optional, `gpu-large` profile |
| RTMPose-s (body7) + YOLOX-tiny (unused detector) | `rtmlib` model zoo (OpenMMLab, ONNX) | Apache-2.0 (rtmlib, MMPose) | 2-D body keypoints (wrists/elbows); the 5 facial keypoints are never used for identification |
| Qwen3-VL-4B-Instruct | `Qwen/Qwen3-VL-4B-Instruct` (HF) | Apache-2.0 | default `gpu-small` contrastive verifier, NF4 quantization |
| Qwen3-VL-2B-Instruct | `Qwen/Qwen3-VL-2B-Instruct` (HF) | Apache-2.0 | local verifier / describer / catch-all (`gpu-small`) |
| Qwen3-VL-8B-Instruct | `Qwen/Qwen3-VL-8B-Instruct` (HF) | Apache-2.0 | optional, `gpu-large` profile |

Explicitly **not** used: Ultralytics YOLO (AGPL-3.0), YOLO-World (GPL), `boxmot` (AGPL), VideoMAE v2 weights
(CC-BY-NC), Qwen2.5-VL-3B (research license), any face recognition model, any cloud API.

## Libraries (pinned in `requirements.txt`)

| package | license | use |
|---|---|---|
| torch / torchvision | BSD-3 | inference runtime |
| transformers, accelerate, huggingface_hub, tokenizers, safetensors | Apache-2.0 | model loading / inference |
| bitsandbytes | MIT | optional 4-bit loading of the VLM |
| onnxruntime-gpu | MIT | RTMPose inference |
| rtmlib | Apache-2.0 | RTMPose wrapper + model zoo |
| opencv-python-headless (+ opencv-python / opencv-contrib-python pulled by rtmlib) | Apache-2.0 | image ops, JPEG encoding, drawing |
| av (PyAV) | BSD-3 (bundles FFmpeg libraries under LGPL-2.1+, dynamically linked) | video decoding |
| imageio-ffmpeg | BSD-2 (ships an FFmpeg binary; the binary is LGPL/GPL — used only as an external process by the development/robustness scripts, never linked) | re-encoding of augmented videos |
| numpy, scipy, scikit-learn, pandas, pyarrow | BSD-3 / Apache-2.0 | numerics, Hungarian matching (scipy), tables |
| supervision | MIT | installed; the engine ships its own compact ByteTrack implementation (`forte_ai/perception/bytetrack.py`, algorithm from Zhang et al. 2022, original code MIT) |
| pyyaml | MIT | config |
| jsonschema | MIT | result-contract validation |
| pydantic, fastapi, starlette, uvicorn, python-multipart | MIT / BSD-3 | reference server |
| requests | Apache-2.0 | api-test client only |
| openpyxl | MIT | reading the labels workbook |
| pillow | MIT-CMU (HPND) | image conversion |
| qwen-vl-utils | Apache-2.0 | optional helper for Qwen-VL inputs |
| timm | Apache-2.0 | transformers backbone dependency |
| pytest, matplotlib, beautifulsoup4, lxml, python-docx | MIT / PSF / MIT / BSD | development only |

## Data

Training videos and the labels workbook belong to ForteBank / the Datathon organisers and are used only inside
this project (never uploaded, never committed). Legal texts are public normative acts of the Republic of
Kazakhstan (adilet.zan.kz), stored verbatim in `kb/laws/` for citation.
