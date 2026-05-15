"""OCR evaluation harness package.

This file exists so `ocr_eval` is importable from outside (e.g. the
`open_src` pipeline using `--from-ocr`). Runners inside `runners/<name>/`
continue to work by inserting `ocr_eval/` itself onto sys.path and
importing bare modules like `schema` / `runner_utils`.
"""
