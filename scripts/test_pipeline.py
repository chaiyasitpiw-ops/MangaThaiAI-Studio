import sys
from pathlib import Path
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from control_center.pipeline.pipeline import ZeroTrainingMangaPipeline
import cv2

def run_test():
    pipeline = ZeroTrainingMangaPipeline()
    input_file = Path("data/inputs/sample_manga.png")
    output_dir = Path("data/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    res = pipeline.process_page(input_file)
    print(f"Detected {len(res['bboxes'])} bubbles:")
    for b in res['bubbles']:
        print(f"  Bubble #{b['id']} Bbox={b['bbox']}")
        print(f"    JP: {repr(b['jp_text'])}")
        print(f"    TH: {repr(b['th_text'])}")

    cleaned_path = output_dir / "sample_cleaned.png"
    result_path = output_dir / "sample_translated_thai.png"

    cv2.imwrite(str(cleaned_path), res['cleaned_bgr'])
    res['result_pil'].save(str(result_path))
    print(f"Saved cleaned image to: {cleaned_path}")
    print(f"Saved translated Thai image to: {result_path}")
    print("SUCCESS: Pipeline executed cleanly!")

if __name__ == "__main__":
    run_test()
