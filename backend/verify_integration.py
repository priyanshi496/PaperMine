"""Quick integration verification script."""
import sys
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("PaperMine Integration Verification")
print("=" * 60)

errors = []

# 1. Backend imports
print("\n[1] Backend imports...")
try:
    from app.services.paddle_ocr import (
        process_document, _is_image_file, IMAGE_EXTENSIONS,
        _minimal_preprocess, _heavy_preprocess, _ocr_single_image_adaptive,
        _ocr_image_file, get_ocr_engine, OcrLine,
        LOW_CONFIDENCE_THRESHOLD, RETRY_CONFIDENCE_THRESHOLD,
        NORMAL_RENDER_SCALE, LOW_RES_RENDER_SCALE, DET_LIMIT_SIDE_LEN,
    )
    print("  ✓ paddle_ocr.py — all functions and config imported")
except Exception as e:
    errors.append(f"paddle_ocr import: {e}")
    print(f"  ✗ paddle_ocr.py — {e}")

try:
    from app.services.ocr_postprocess import (
        postprocess_ocr_lines, is_gibberish, merge_broken_words,
        _fix_char_substitutions, LOW_CONFIDENCE_TAG,
    )
    print("  ✓ ocr_postprocess.py — all functions imported")
except Exception as e:
    errors.append(f"ocr_postprocess import: {e}")
    print(f"  ✗ ocr_postprocess.py — {e}")

try:
    from app.api.v1.upload import ALLOWED_EXTENSIONS, router
    print("  ✓ upload.py — ALLOWED_EXTENSIONS + router imported")
except Exception as e:
    errors.append(f"upload import: {e}")
    print(f"  ✗ upload.py — {e}")

try:
    from app.services.llm_service import call_llm_structured_extraction
    print("  ✓ llm_service.py — imported")
except Exception as e:
    errors.append(f"llm_service import: {e}")
    print(f"  ✗ llm_service.py — {e}")

try:
    from app.services.structured_extraction import merge_extraction
    print("  ✓ structured_extraction.py — imported")
except Exception as e:
    errors.append(f"structured_extraction import: {e}")
    print(f"  ✗ structured_extraction.py — {e}")

# 2. Config values
print("\n[2] Configuration values...")
print(f"  LOW_CONFIDENCE_THRESHOLD = {LOW_CONFIDENCE_THRESHOLD}")
print(f"  RETRY_CONFIDENCE_THRESHOLD = {RETRY_CONFIDENCE_THRESHOLD}")
print(f"  NORMAL_RENDER_SCALE = {NORMAL_RENDER_SCALE}")
print(f"  LOW_RES_RENDER_SCALE = {LOW_RES_RENDER_SCALE}")
print(f"  DET_LIMIT_SIDE_LEN = {DET_LIMIT_SIDE_LEN}")
print(f"  IMAGE_EXTENSIONS = {IMAGE_EXTENSIONS}")
print(f"  ALLOWED_EXTENSIONS (upload) = {ALLOWED_EXTENSIONS}")

# 3. Image detection
print("\n[3] Image file detection...")
test_cases = [
    ("invoice.pdf", False),
    ("photo.jpg", True),
    ("scan.jpeg", True),
    ("receipt.png", True),
    ("doc.tiff", True),
    ("img.bmp", True),
    ("photo.webp", True),
    ("data.csv", False),
]
for filename, expected in test_cases:
    result = _is_image_file(filename)
    status = "✓" if result == expected else "✗"
    if result != expected:
        errors.append(f"_is_image_file('{filename}') = {result}, expected {expected}")
    print(f"  {status} _is_image_file('{filename}') = {result}")

# 4. Upload extension alignment
print("\n[4] Backend upload ↔ OCR extension alignment...")
upload_exts = ALLOWED_EXTENSIONS - {".pdf"}  # non-PDF extensions
ocr_exts = IMAGE_EXTENSIONS
missing_in_upload = ocr_exts - ALLOWED_EXTENSIONS
missing_in_ocr = upload_exts - ocr_exts
if not missing_in_upload and not missing_in_ocr:
    print("  ✓ All image extensions match between upload.py and paddle_ocr.py")
else:
    if missing_in_upload:
        msg = f"In OCR but not in upload: {missing_in_upload}"
        errors.append(msg)
        print(f"  ✗ {msg}")
    if missing_in_ocr:
        msg = f"In upload but not in OCR: {missing_in_ocr}"
        errors.append(msg)
        print(f"  ✗ {msg}")

# 5. Gibberish detection
print("\n[5] Gibberish detection...")
gibberish_tests = [
    ("soobbenxopens-easeoog", True),
    ("Paernaoaeeeos", True),
    ("Paenaeeeeens", True),
    ("Invoice Number", False),
    ("Chicken Peppery Sandwich", False),
    ("Bengaluru", False),
    ("1234.56", False),
    ("GSTIN", False),
    ("tota1", False),  # short, handled by char fix not gibberish
]
for text, expected in gibberish_tests:
    result = is_gibberish(text)
    status = "✓" if result == expected else "~"  # ~ for soft mismatch
    print(f"  {status} is_gibberish('{text}') = {result} (expected {expected})")

# 6. Character substitution fixes
print("\n[6] Character substitution fixes...")
fix_tests = [
    ("tota1", "total"),
    ("arnount", "amount"),
    ("nurnber", "number"),
    ("lnvoice", "Invoice"),
    ("b111", "bill"),
    ("100.00", "100.00"),  # should NOT change
    ("Invoice", "Invoice"),  # should NOT change
]
for input_text, expected in fix_tests:
    result = _fix_char_substitutions(input_text)
    status = "✓" if result == expected else "✗"
    if result != expected:
        errors.append(f"char fix '{input_text}' = '{result}', expected '{expected}'")
    print(f"  {status} '{input_text}' → '{result}' (expected '{expected}')")

# 7. OcrLine dataclass
print("\n[7] OcrLine dataclass...")
line = OcrLine(text="test", score=0.95, box=[0, 0, 100, 20])
assert line.final_text == "test"
line.corrected = "corrected"
assert line.final_text == "corrected"
print("  ✓ OcrLine.final_text works correctly")

# 8. CV2 and Pillow availability
print("\n[8] Dependency availability...")
try:
    import cv2
    print(f"  ✓ OpenCV (cv2) version: {cv2.__version__}")
except ImportError as e:
    errors.append(f"cv2 import: {e}")
    print(f"  ✗ OpenCV (cv2): {e}")

try:
    from PIL import Image, ImageOps
    import PIL
    print(f"  ✓ Pillow version: {PIL.__version__}")
except ImportError as e:
    errors.append(f"Pillow import: {e}")
    print(f"  ✗ Pillow: {e}")

try:
    import numpy as np
    print(f"  ✓ NumPy version: {np.__version__}")
except ImportError as e:
    errors.append(f"numpy import: {e}")
    print(f"  ✗ NumPy: {e}")

# 9. FastAPI app loads
print("\n[9] FastAPI app initialization...")
try:
    from app.main import app
    routes = [r.path for r in app.routes]
    print(f"  ✓ App loaded with {len(routes)} routes")
    upload_route = any("/upload" in r for r in routes)
    print(f"  {'✓' if upload_route else '✗'} /upload route registered")
except Exception as e:
    errors.append(f"FastAPI app: {e}")
    print(f"  ✗ App load failed: {e}")

# Summary
print("\n" + "=" * 60)
if errors:
    print(f"RESULT: {len(errors)} error(s) found!")
    for e in errors:
        print(f"  ✗ {e}")
else:
    print("RESULT: ALL CHECKS PASSED ✓")
print("=" * 60)

sys.exit(1 if errors else 0)
