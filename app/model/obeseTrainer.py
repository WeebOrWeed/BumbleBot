import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import os
import numpy as np
import pandas as pd
from tqdm import tqdm
from torch.utils.data import Dataset, random_split, DataLoader
from torchvision.datasets import ImageFolder
from PIL import Image
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
from torchvision import transforms
import dlib
import csv
from pathlib import Path

model = None
device = None
BASE_DIR = Path(__file__).resolve().parent
class RemappedImageFolder(ImageFolder):
    def __init__(self, root, transform=None):
        super().__init__(root, transform=transform)
        self.label_map = {
            self.class_to_idx['Obese']: 0,    # map -1 to class index 0
            self.class_to_idx['Neutral']: 1,  # 0 to 1
            self.class_to_idx['Thin']: 2      # 1 to 2
        }

    def __getitem__(self, index):
        image, class_index = super().__getitem__(index)
        mapped_label = self.label_map[class_index]
        return image, mapped_label

def construct_obese_dataset(train_test_split=0.75, batch_size=5):
    root_dir = "C:/Users/Redux/autolike/BumbleBot/ObeseTrain"

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.Grayscale(num_output_channels=1),
        transforms.ToTensor(),
        transforms.Normalize([0.5], [0.5])
    ])

    full_dataset = RemappedImageFolder(root=root_dir, transform=transform)
    train_size = int(train_test_split * len(full_dataset))
    test_size = len(full_dataset) - train_size
    train_dataset, test_dataset = random_split(full_dataset, [train_size, test_size])

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=4)

    return train_loader, test_loader

class BodyTypeClassifier(nn.Module):
    def __init__(self, pretrained=True, freeze_features=False):
        super().__init__()
        self.base = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None)

        self.base.features[0][0] = nn.Conv2d(
            in_channels=1,
            out_channels=self.base.features[0][0].out_channels,
            kernel_size=self.base.features[0][0].kernel_size,
            stride=self.base.features[0][0].stride,
            padding=self.base.features[0][0].padding,
            bias=False
        )

        if freeze_features and pretrained:
            for param in self.base.features.parameters():
                param.requires_grad = False

        in_features = self.base.classifier[1].in_features
        self.classifier = nn.Linear(in_features, 3)  # 3-class output

    def forward(self, x):
        x = self.base.features(x)
        x = self.base.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x  # logits

def train_model(train_loader, epoch_num=100):
    global device, model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model = BodyTypeClassifier(pretrained=True)
    model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-4)

    for epoch in range(epoch_num):
        model.train()
        running_loss = 0.0

        for inputs, labels in tqdm(train_loader, desc=f"Epoch {epoch+1}/{epoch_num}"):
            inputs = inputs.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * inputs.size(0)

        epoch_loss = running_loss / len(train_loader.dataset)
        print(f"Epoch {epoch+1}/{epoch_num}, Loss: {epoch_loss:.4f}")

    print("Finished Training")

def predict_obesity_class(image):
    """
    Predicts obesity classification probabilities from an input PIL image.

    Args:
        image (PIL.Image): RGB image to evaluate.
        model (nn.Module): Trained BodyTypeClassifier model.

    Returns:
        list: Softmax-normalized probabilities for [Obese, Neutral, Thin] classes.
              Example: [0.1, 0.2, 0.7]
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.eval()

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.Grayscale(num_output_channels=1),
        transforms.ToTensor(),
        transforms.Normalize([0.5], [0.5])
    ])

    try:
        input_tensor = transform(image).unsqueeze(0).to(device)

        with torch.no_grad():
            logits = model(input_tensor)
            probs = torch.softmax(logits, dim=1).squeeze().cpu().tolist()  # 3-class prob vector

        return probs

    except Exception as e:
        print(f"Error processing image: {e}")
        return [0.0, 0.0, 0.0]  # fallback in case of error

def convert_old_csv(csv_file, new_csv_file):
    global model, device
    image_root = "C:/Users/Redux/autolike/BumbleBot/DATA/e4fa3127d2b1b7137b65ed697015d407"
    model = BodyTypeClassifier() 
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    loaded_state_dict = torch.load("C:/Users/Redux/autolike/BumbleBot/obese_model_multiclass.h5", map_location=device)
    model.load_state_dict(loaded_state_dict)
    model.to(device)
    model.eval()
    df = pd.read_csv(csv_file)
    if not os.path.exists(new_csv_file):
        csvsessdata = open(new_csv_file, "w")
        csvsessdata.write("profile,image,outcome,race_scores,obese_scores\n")
        csvsessdata.close()
    with open(new_csv_file, "a+", newline="") as csvsessdata:
        csvsessdata.seek(0)
        existing_profiles = set()
        reader = csv.reader(csvsessdata)
        for row in reader:
            if row:
                existing_profiles.add(row[0])  # assumes profile is the first column

        writer = csv.writer(csvsessdata)

        for index, row in df.iterrows():
            profile = row["profile"]
            image_id = row["image"]
            outcome = row["outcome"]
            race_scores = row["race_scores"]

            img_path = image_root + "/" + profile + "/" + image_id

            csvsessdata.flush()
            if not os.path.isfile(img_path):
                print(f"Error: {img_path} not exist")
                continue

            # try:
            image = Image.open(img_path).convert("RGB")
            obese_score = predict_obesity_class(image)
            writer.writerow([profile, image_id, outcome, race_scores, obese_score])  # add other fields if needed
            csvsessdata.flush()

def init_models():
    global model, device
    model = BodyTypeClassifier() 
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    loaded_state_dict = torch.load(Path(BASE_DIR / "obesetrain" / "obese_model_multiclass.h5").resolve(), map_location=device)
    model.load_state_dict(loaded_state_dict)
    model.to(device)
    model.eval()

if __name__ == "__main__":
    convert_old_csv("C:/Users/Redux/autolike/BumbleBot/DATA/e4fa3127d2b1b7137b65ed697015d407/e4fa3127d2b1b7137b65ed697015d407_2.csv", "C:/Users/Redux/autolike/BumbleBot/DATA/e4fa3127d2b1b7137b65ed697015d407/e4fa3127d2b1b7137b65ed697015d407_3.csv")
    # train_loader, test_loader = construct_obese_dataset()
    # train_model(train_loader=train_loader, epoch_num=250)
    # torch.save(model.state_dict(), "C:/Users/Redux/autolike/BumbleBot/obese_model_multiclass.h5")
    # print("Model saved to C:/Users/Redux/autolike/BumbleBot/obese_model_multiclass.h5")
    # # # model = BodyTypeClassifier() 
    # # # device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    # # # loaded_state_dict = torch.load("C:/Users/Redux/autolike/BumbleBot/obese_model_multiclass.h5", map_location=device)
    # # # model.load_state_dict(loaded_state_dict)
    # # # model.to(device)
    # # # model.eval()
    # # init_models()

    # score1 = predict_obesity_class(Image.open("C:/Users/Redux/autolike/BumbleBot/DATA/e4fa3127d2b1b7137b65ed697015d407/d5aa01cf-459a-4c39-a77c-c0c31c8fe537/image_0.png").convert("RGB")) # 1
    # score2 = predict_obesity_class(Image.open("C:/Users/Redux/autolike/BumbleBot/DATA/e4fa3127d2b1b7137b65ed697015d407/d8686402-f8ed-40c9-bb44-9f8517ea7e28/image_1.png").convert("RGB")) # -1
    # score3 = predict_obesity_class(Image.open("C:/Users/Redux/autolike/BumbleBot/DATA/e4fa3127d2b1b7137b65ed697015d407/a5acd1d1-3f3f-4dd9-9104-825410f48c80/image_4.png").convert("RGB")) # 1
    # score4 = predict_obesity_class(Image.open("C:/Users/Redux/autolike/BumbleBot/DATA/e4fa3127d2b1b7137b65ed697015d407/0f840689-c827-4d29-8225-bf44e6398c9c/image_4.png").convert("RGB")) # -1
    # score5 = predict_obesity_class(Image.open("C:/Users/Redux/autolike/BumbleBot/DATA/e4fa3127d2b1b7137b65ed697015d407/80d7345f-f184-44e5-a4a7-7406b3a2137c/image_0.png").convert("RGB")) # 1
    # print(f"{score1} \n {score2} \n {score3} \n {score4} \n {score5}")
