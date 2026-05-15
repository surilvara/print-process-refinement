# Google Vision Outputs

Drop Google Vision OCR JSON files here. These act as the baseline / ground
truth for the OCR evaluation harness (`ocr_eval/`).

## Expected naming

Use the same stem as the source image so the comparator can pair them
automatically:

```
inputs/vogue_uk_2026-04-01_v2/00000001.jpg
googlevision_outputs/00000001.json
```

Subfolders mirroring the publication folder are fine, e.g.
`googlevision_outputs/vogue_uk_2026-04-01_v2/00000001.json`.
