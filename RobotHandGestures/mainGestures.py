import cv2
import mediapipe as mp
import numpy as np
import serial  # Uncomment if using serial communication
import time

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Initialize MediaPipe Hands ONCE outside the loop
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.8,
    min_tracking_confidence=0.8
)

# --- Serial Setup (uncomment if needed) ---
ser = serial.Serial('COM3', 9600, timeout=1)
time.sleep(2)  # Wait for serial to initialize

cap = cv2.VideoCapture(0)
# Store last packet sent
last_packet = ""

def get_finger_status(landmarks, hand_label):
    """
    Returns list of 5 values: 1=open, 0=closed for each finger.
    Order: [Thumb, Index, Middle, Ring, Pinky]

    FIX 1: Thumb now uses handedness-aware comparison (left vs right hand).
    FIX 2: Uses wrist as reference for thumb, not just landmark[3].
    """
    fingers = []

    # --- THUMB (FIX: handedness-aware) ---
    # For RIGHT hand: thumb tip (4) should be to the RIGHT of thumb IP (3)
    # For LEFT hand:  thumb tip (4) should be to the LEFT  of thumb IP (3)
    if hand_label == "Right":
        fingers.append(1 if landmarks[4].x > landmarks[3].x else 0)
    else:  # Left hand
        fingers.append(1 if landmarks[4].x < landmarks[3].x else 0)

    # --- OTHER 4 FINGERS (Index, Middle, Ring, Pinky) ---
    # Tip landmark IDs: 8, 12, 16, 20
    # PIP landmark IDs: 6, 10, 14, 18  (two joints below tip)
    tip_ids = [8, 12, 16, 20]
    for tip in tip_ids:
        # Finger is open if tip is ABOVE the PIP joint (lower Y value = higher on screen)
        fingers.append(1 if landmarks[tip].y < landmarks[tip - 2].y else 0)

    return fingers


def count_fingers(finger_status):
    """Returns the total number of open fingers."""
    return sum(finger_status)


def get_gesture_name(finger_status):
    """
    Maps finger status to common gesture names.
    Extend this dict for your own gestures.
    """
    gestures = {
        (0, 0, 0, 0, 0): "Fist",
        (1, 1, 1, 1, 1): "Open Hand",
        (0, 1, 0, 0, 0): "Pointing",
        (0, 1, 1, 0, 0): "Peace / V",
        (1, 1, 0, 0, 0): "Gun",
        (1, 0, 0, 0, 1): "Rock On",
        (0, 0, 0, 0, 1): "Pinky",
        (1, 0, 0, 0, 0): "Thumbs Up",
    }
    return gestures.get(tuple(finger_status), "Unknown")


# --- Main Loop ---
prev_time = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Mirror the frame for natural interaction
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape

    # Convert BGR to RGB for MediaPipe
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb.flags.writeable = False          # Performance: lock buffer
    result = hands.process(rgb)
    rgb.flags.writeable = True

    # --- FPS Calculation ---
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0
    prev_time = curr_time
    cv2.putText(frame, f"FPS: {int(fps)}", (w - 120, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    # --- Hand Detection ---
    if result.multi_hand_landmarks and result.multi_handedness:

        for hand_landmarks, handedness in zip(result.multi_hand_landmarks,
                                              result.multi_handedness):

            # FIX 2: Get handedness label ("Left" or "Right")
            hand_label = handedness.classification[0].label
            hand_label = "Right" if hand_label == "Left" else "Left"
            # Draw landmarks with default styles
            mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style()
            )

            # Get finger status with correct handedness
            finger_status = get_finger_status(hand_landmarks.landmark, hand_label)
            total_open   = count_fingers(finger_status)
            gesture      = get_gesture_name(finger_status)

            # --- Display Info ---
            labels = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
            for i, (label, state) in enumerate(zip(labels, finger_status)):
                color = (0, 255, 0) if state else (0, 0, 255)
                cv2.putText(frame, f"{label}: {'Open' if state else 'Closed'}",
                            (10, 50 + i * 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

            cv2.putText(frame, f"Hand: {hand_label}",    (10, 220),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 0), 2)
            cv2.putText(frame, f"Open: {total_open}/5",  (10, 250),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 165, 0), 2)
            cv2.putText(frame, f"Gesture: {gesture}",    (10, 280),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

            # --- Serial Output (FIX 3: properly formatted) ---
            thumb = finger_status[0]
            index = finger_status[1]
            middle = finger_status[2]
            ring = finger_status[3]
            pinky = finger_status[4]

            packet = f"${pinky}{ring}{middle}{index}{thumb}"

            # Send only if gesture changed
            if packet != last_packet:
                ser.write(packet.encode())
                print("Sent:", packet)  # Debug
                last_packet = packet

    else:
        cv2.putText(frame, "No Hand Detected", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow("Hand Tracking", frame)

    # Press ESC to quit
    if cv2.waitKey(1) == 27:
        break

# --- Cleanup ---
cap.release()
hands.close()
cv2.destroyAllWindows()
ser.close()  # Uncomment if using serial