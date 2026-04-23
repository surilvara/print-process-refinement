# Print Document Intelligence Pipeline

## Quick Start

### 1. Install dependencies

```bash
uv venv && uv pip install -e "."
uv run python -m spacy download en_core_web_trf
```

### 2. Run on a single file

```bash
uv run python main.py --input path/to/scan.jpg
```

### 3. Run on a folder of scans

```bash
uv run python main.py --input path/to/scans/
```

Supported formats: `.jpg`, `.jpeg`, `.png`, `.pdf`

## CLI Options

```
uv run python main.py --input <file_or_folder> [options]

Required:
  --input, -i        Path to an image file, PDF, or folder of scans

Optional:
  --output, -o       Output directory (default: output/)
  --config, -c       Path to config file (default: config.yaml)
  --log-level        DEBUG | INFO | WARNING | ERROR
  --ocr-model        Override OCR backend
  --layout-model     Override layout model
  --ner-model        Override NER model
  --image-model      Override image analysis model
```

## Examples

```bash
# Process a single JPEG with debug logging
uv run python main.py -i magazine_cover.jpg --log-level DEBUG

# Process a multi-page PDF
uv run python main.py -i newspaper.pdf

# Process a folder, output to a custom directory
uv run python main.py -i ./scans/ -o ./results/

# Use a custom config file
uv run python main.py -i scan.png -c my_config.yaml
```

## Output

Results are written as JSON files to the `output/` folder (or the directory specified with `--output`).

Filenames follow the pattern:
```
<input_name>_<timestamp>_<models>.json
```

Example: `magazine_cover_2026-04-23T14-30-00_doctr_layoutlmv3_spacy_owlv2.json`

## Configuration

Edit `config.yaml` to change models, detection prompts, or output settings. CLI arguments override config file values.
