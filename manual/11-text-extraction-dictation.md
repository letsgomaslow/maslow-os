# Text Extraction & Dictation

### Text Extraction

Hit `Super + Ctrl + PrtScr` to select a region on the screen for text extraction. The tesseract open source OCR model will then quickly convert that selection into text and place it on the clipboard. Then you just hit `Super + V` to paste.

This is very helpful for grabbing addresses out of image footers or phone numbers embedded in website headlines.

 ![text-extraction](images/text-extraction.webp)

### Dictation

Maslow OS offers optional AI dictation through [Voxtype](https://voxtype.io/). Install it through _Install > AI > Dictation_ in the Maslow OS menu. By default, it loads a base English model that takes about 150MB. Choose a different model with `voxtype setup model`, and edit advanced settings in `~/.config/voxtype/config.toml`.

Once installed, you dictate by holding down `F9` or by toggling with `Super + Ctrl + X`, and the dictated text will appear in the focused input area.
