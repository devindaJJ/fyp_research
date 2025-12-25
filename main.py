import argparse
import cv2
from typing import Optional

from src.core.config import config
from src.speed.detector import VehicleSpeedDetector
from src.anpr.detector import NumberPlateDetector


class TrafficApp:
    """
    Class-based orchestrator for speed detection, ANPR, or both.
    Keeps main.py small, clear, and extensible.
    """

    def __init__(
        self,
        mode: str,
        video_path: Optional[str] = None,
        image_path: Optional[str] = None,
        anpr_model: Optional[str] = None,
    ):
        self.mode = mode
        self.video_path = video_path
        self.image_path = image_path
        self.anpr_model = anpr_model

        self.speed_detector: Optional[VehicleSpeedDetector] = None
        self.anpr_detector: Optional[NumberPlateDetector] = None

    @staticmethod
    def parse_args():
        parser = argparse.ArgumentParser(description="Urban Traffic System Runner")
        parser.add_argument("--mode", choices=["speed", "anpr", "both"], default="speed",
                            help="Which pipeline to run")
        parser.add_argument("--video", type=str, default=None, help="Path to video file")
        parser.add_argument("--image", type=str, default=None, help="Path to image (ANPR only)")
        parser.add_argument("--anpr-model", type=str, default=None, help="Path to ANPR YOLO model")
        return parser.parse_args()

    def create_anpr_detector(self) -> NumberPlateDetector:
        model_path = (
            self.anpr_model
            or (getattr(config, "anpr").model_path if hasattr(config, "anpr") else None)
            or "models/number_plate_yolo.pt"
        )
        languages = (getattr(config, "anpr").languages if hasattr(config, "anpr") else ["en"])
        conf = (getattr(config, "anpr").confidence_threshold if hasattr(config, "anpr") else 0.25)
        img_size = (getattr(config, "anpr").image_size if hasattr(config, "anpr") else 640)
        return NumberPlateDetector(model_path=model_path, languages=languages,
                                   confidence_threshold=conf, image_size=img_size)

    def run(self):
        if self.mode == "speed":
            self.run_speed()
        elif self.mode == "anpr":
            self.run_anpr()
        else:
            self.run_both()

    def run_speed(self):
        """Run speed detection using the detector’s own loop."""
        self.speed_detector = VehicleSpeedDetector(video_path=self.video_path)
        self.speed_detector.run()

    def run_anpr(self):
        """Run ANPR on either an image or a video."""
        self.anpr_detector = self.create_anpr_detector()

        # Image mode
        if self.image_path:
            img = cv2.imread(self.image_path)
            if img is None:
                print(f"Error: could not load image: {self.image_path}")
                return
            plates = self.anpr_detector.detect_and_read(img, draw_results=True)
            if isinstance(plates, tuple):
                plates_data, annotated = plates
            else:
                plates_data, annotated = plates, img
            print(f"Detected {len(plates_data)} plate(s)")
            for p in plates_data:
                print(f"- {p['text']} (valid={p['valid']}) bbox={p['bbox']}")
            cv2.imshow("ANPR", annotated)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            return

        # Video mode
        path = self.video_path or config.video.path
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            print(f"Error: could not open video: {path}")
            return

        window_name = "ANPR"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                plates = self.anpr_detector.detect_and_read(frame, draw_results=True)
                if isinstance(plates, tuple):
                    _, annotated = plates
                else:
                    annotated = frame

                cv2.imshow(window_name, annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

    def draw_anpr_overlays_on_frame(self, frame):
        """Run ANPR on a frame and draw overlays onto the same frame."""
        if self.anpr_detector is None:
            self.anpr_detector = self.create_anpr_detector()

        plates_data = self.anpr_detector.detect_and_read(frame, draw_results=False)
        for p in plates_data:
            (x1, y1, x2, y2) = p["bbox"]
            color = (0, 255, 0) if p["text"] else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            if p["text"]:
                cv2.putText(frame, p["text"], (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        return frame

    def run_both(self):
        """Run speed detection and ANPR in a single loop with a single window."""
        # Instantiate speed detector but release its internal capture; we’ll reuse one shared cap.
        self.speed_detector = VehicleSpeedDetector(video_path=self.video_path)
        if self.speed_detector.cap and self.speed_detector.cap.isOpened():
            self.speed_detector.cap.release()

        # ANPR detector
        self.anpr_detector = self.create_anpr_detector()

        # Shared capture
        path = self.video_path or config.video.path
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            print(f"Error: could not open video: {path}")
            return

        window_name = self.speed_detector.window_name
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, config.display.window_width, config.display.window_height)

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Speed per-frame
                detections = self.speed_detector.detect_vehicles(frame)
                tracks = self.speed_detector.tracker.update_tracks(detections, frame=frame)
                active_ids = self.speed_detector.process_tracks(tracks, frame)
                self.speed_detector.draw_virtual_lines(frame)
                self.speed_detector.clean_old_tracks(active_ids)

                # ANPR overlays on same frame
                frame = self.draw_anpr_overlays_on_frame(frame)

                cv2.imshow(window_name, frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()


def main():
    args = TrafficApp.parse_args()
    app = TrafficApp(
        mode=args.mode,
        video_path=args.video,
        image_path=args.image,
        anpr_model=args.anpr_model,
    )
    app.run()


if __name__ == "__main__":
    main()