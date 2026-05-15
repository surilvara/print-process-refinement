# Runners

One folder per OCR model. Each runner is a standalone script with its own
virtualenv — this avoids dependency conflicts between models (e.g. different
`transformers` pins).

## Adding a new runner

1. Copy `_template/` to `<model_name>/`.
2. Edit `requirements.txt` with the model's deps.
3. Implement `run.py` so that:
   - `python run.py --input <path> --output <path>` produces a JSON file
     matching `ocr_eval/schema.OcrOutput`.
4. Set up its venv:
   ```bash
   cd ocr_eval/runners/<model_name>
   uv venv && uv pip install -r requirements.txt
   ```
5. Run over the corpus:
   ```bash
   for img in ../../../inputs/<publication>/*.jpg; do
     stem=$(basename "$img" .jpg)
     .venv/bin/python run.py \
       --input "$img" \
       --output "../../outputs/<model_name>/${stem}.json"
   done
   ```
6. Compare against the Google Vision baseline:
   ```bash
   cd ../..
   python compare.py --runner <model_name>
   ```

## Contract

Every runner must:
- Read one image at a time (path argument).
- Emit a single JSON file conforming to `schema.OcrOutput`.
- Set `runner` to the folder name.
- Normalise all bboxes to `[0, 1]`.
- Never crash the harness — catch and log errors, write an empty result if
  needed.

The runner script is the *only* place that imports the model. The comparator
never touches model code.
