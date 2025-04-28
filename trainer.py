import machineLearning as ML
import utilities as UM
import numpy as np
import torch
import os

def main_trainning_app():
    # Load settings
    settings = UM.load_settings()

    # Load dataset
    train_data, test_data = ML.construct_dataset(
        settings["DATA_INDEX"], settings["DATA_PATH"],
        int(settings["IMG_SIZE"]), int(settings["BATCH_SIZE"]), float(settings["TTS"])
    )

    # Train the model using the modified train_model function
    model = ML.train_model(
        train_loader=train_data,
        num_epochs=int(settings["EPOCHS"]),
        image_size=int(settings["IMG_SIZE"])
    )

    print("Training complete")
    # Save PyTorch model manually
    if settings.get("MODELPATH"):
        torch.save(model.state_dict(), settings["MODELPATH"])

    # Predict
    y_preds_raw = ML.predict(model, test_data)

    y_preds = ML.raw_to_binary(y_preds_raw, settings.get("THRESH", 0.5))
    print("Unique predicted labels:", np.unique(y_preds, return_counts=True))

    # Evaluation
    print("Predicted Positives:", y_preds.count(1), "Out of", len(y_preds))

    accuracy = ML.calculate_accuracy(test_data, y_preds)
    print(f"The model is {accuracy * 100:.2f}% accurate")

    torch.save(model.state_dict(), settings["MODELPATH"])
    print(f"Model saved to: {settings["MODELPATH"]}")

if __name__ == "__main__":
    main_trainning_app()
