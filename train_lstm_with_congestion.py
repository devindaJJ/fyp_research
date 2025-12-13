import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, accuracy_score, classification_report
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input

# -------------------------
# Settings
# -------------------------
WINDOW_SIZE = 16
THRESHOLD_CONGESTION = 120       # Based on heavy congestion examples
RESAMPLE_RULE = "1min"

# -------------------------
# Load & Clean Dataset
# -------------------------
def load_and_clean(path):
    df = pd.read_csv(path)

    numeric_cols = ["CarCount", "BikeCount", "BusCount", "TruckCount", "Total"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Date"] = df["Date"].astype(str).str.zfill(2)

    df["DateTime"] = pd.to_datetime(
        "2025-01-" + df["Date"] + " " + df["Time"],
        format="%Y-%m-%d %I:%M:%S %p",
        errors="coerce",
    )

    df = df.dropna(subset=["DateTime"])
    df = df.dropna().sort_values("DateTime")

    return df


# -------------------------
# Resample & Normalize
# -------------------------
def preprocess(df):
    df = df.set_index("DateTime")

    features = ["CarCount", "BikeCount", "BusCount", "TruckCount", "Total"]

    df = df[features].resample(RESAMPLE_RULE).mean().ffill()

    scaler = StandardScaler()

    df_scaled = scaler.fit_transform(df.ffill().fillna(0))
    df_scaled = pd.DataFrame(df_scaled, index=df.index, columns=features)

    return df_scaled, df, scaler


# -------------------------
# Create Sequences (✅ FIXED)
# -------------------------
def make_sequences(df_scaled, df_raw):
    X, y_reg, y_clf = [], [], []

    values_scaled = df_scaled.values
    values_raw = df_raw["Total"].values   # ✅ RAW total
    total_idx = df_scaled.columns.get_loc("Total")

    for i in range(len(values_scaled) - WINDOW_SIZE):
        window = values_scaled[i : i + WINDOW_SIZE]

        if np.isnan(window).any():
            continue

        X.append(window)

        # ✅ Regression uses SCALED
        next_total_scaled = values_scaled[i + WINDOW_SIZE, total_idx]
        y_reg.append(next_total_scaled)

        # ✅ Classification uses RAW
        next_total_raw = values_raw[i + WINDOW_SIZE]
        y_clf.append(1 if next_total_raw > THRESHOLD_CONGESTION else 0)

    return np.array(X), np.array(y_reg), np.array(y_clf)


# -------------------------
# Build LSTM Model
# -------------------------
def build_model(input_shape):
    model = Sequential([
        Input(shape=input_shape),
        LSTM(64),
        Dropout(0.2),
        Dense(32, activation="relu"),
        Dense(1)
    ])

    model.compile(loss="mse", optimizer="adam", metrics=["mae"])
    return model


# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":

    df = load_and_clean("data/traffic_dataset.csv")
    df_scaled, df_raw, scaler = preprocess(df)

    # ✅ FIXED CALL
    X, y_reg, y_clf = make_sequences(df_scaled, df_raw)

    print("Shapes:", X.shape, y_reg.shape, y_clf.shape)

    # -------------------------
    # ✅ CHECK LABEL DISTRIBUTION
    # -------------------------
    print("\n================ THE LABEL DISTRIBUTION ================")

    unique, counts = np.unique(y_clf, return_counts=True)
    label_dist = dict(zip(unique, counts))

    print("Label counts:", label_dist)

    for k, v in label_dist.items():
        print(f"Class {k}: {(v/len(y_clf))*100:.2f}%")

    majority_class = max(label_dist, key=label_dist.get)
    baseline_acc = label_dist[majority_class] / len(y_clf)

    print(f"\nBaseline accuracy: {baseline_acc:.4f}")

    if baseline_acc > 0.90:
        print("⚠ WARNING: Dataset is highly imbalanced!\n")

    # -------------------------
    # Train/Test Split
    # -------------------------
    X_train, X_test, y_reg_train, y_reg_test, y_clf_train, y_clf_test = train_test_split(
        X, y_reg, y_clf, test_size=0.2, shuffle=False
    )

    model = build_model((WINDOW_SIZE, X.shape[2]))

    model.fit(
        X_train,
        y_reg_train,
        epochs=10,
        batch_size=32,
        validation_split=0.1,
        verbose=1
    )

    # -------------------------
    # Predict
    # -------------------------
    preds_scaled = model.predict(X_test).flatten()

    # ✅ Convert scaled predictions back to RAW values
    total_idx = df_scaled.columns.get_loc("Total")
    temp = np.zeros((len(preds_scaled), df_scaled.shape[1]))
    temp[:, total_idx] = preds_scaled
    preds_raw = scaler.inverse_transform(temp)[:, total_idx]

    preds_clf = (preds_raw > THRESHOLD_CONGESTION).astype(int)

    # -------------------------
    # Sample Output
    # -------------------------
    print("\nSample predictions:")
    print(pd.DataFrame({
        "pred_total": preds_raw[:10],
        "true_total": df_raw["Total"].values[-len(preds_raw):][:10],
        "pred_congest": preds_clf[:10],
        "true_congest": y_clf_test[:10]
    }))

    # -------------------------
    # Final Evaluation
    # -------------------------
    mse = mean_squared_error(y_reg_test, preds_scaled)
    acc = accuracy_score(y_clf_test, preds_clf)

    print("\nFinal Evaluation:")
    print("MSE:", mse)
    print("Congestion Accuracy:", acc)

    print("\nClassification Report:")
    print(classification_report(y_clf_test, preds_clf))
