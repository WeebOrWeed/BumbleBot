import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import os
import numpy as np
import pandas as pd
import re
from model import fairfaceWrapper as FF
from model import obeseTrainer as OT
from torch.utils.data import DataLoader 
from tqdm import tqdm  # For a nice progress bar
from torch.utils.data import Dataset, random_split, DataLoader
from PIL import Image, ImageTk
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
from torchvision import transforms
import ast  # For safely evaluating the string representation of the list
import dlib

def construct_dataset(data_index_path, data_path, img_size, batch_size, train_test_split):
    try:
        transform = transforms.Compose([
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        full_dataset = ProfileImageDatasetWithMetadata(
            csv_file=data_index_path,
            root_dir=data_path,
            transform=transform
        )

        train_size = int(train_test_split * len(full_dataset))
        test_size = len(full_dataset) - train_size
        train_dataset, test_dataset = random_split(full_dataset, [train_size, test_size])

        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=4)

        return train_loader, test_loader

    except FileNotFoundError:
        print(f"Error: Data index file not found at {data_index_path} or data path {data_path} is incorrect.")
        return None, None
    except Exception as e:
        print(f"An error occurred during dataset construction: {e}")
        return None, None

def parse_score_string(score_str):
    clean_str = score_str.strip("[]")
    clean_str = re.sub(r"[,\s]+", ",", clean_str.strip())
    final_str = "[" + clean_str + "]"
    return ast.literal_eval(final_str)

class ProfileImageDatasetWithMetadata(Dataset):
    def __init__(self, csv_file, root_dir, transform=None, num_race_classes=7, num_obesity_classes=3):
        self.df = pd.read_csv(csv_file)
        self.root_dir = root_dir
        self.transform = transform
        self.num_race_classes = num_race_classes
        self.num_obesity_classes = num_obesity_classes

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        image_name = row['image']
        label = float(row['outcome'])
        race_scores = parse_score_string(row['race_scores'])
        obesity_scores = parse_score_string(row['obese_scores'])

        image_path = os.path.join(self.root_dir, image_name)
        try:
            image = Image.open(image_path).convert('RGB')
        except:
            image = Image.new("RGB", (224, 224))

        if self.transform:
            image = self.transform(image)

        race_tensor = torch.tensor(race_scores, dtype=torch.float32)
        obesity_tensor = torch.tensor(obesity_scores, dtype=torch.float32)
        label_tensor = torch.tensor(label, dtype=torch.float32)

        return image, race_tensor, obesity_tensor, label_tensor

class InterestRegressorWithMetadata(nn.Module):
    def __init__(self, img_size, num_race_classes=7, num_obesity_classes=3, pretrained=True, freeze_features=False):
        super().__init__()
        self.efficientnet = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None)
        if freeze_features and pretrained:
            for param in self.efficientnet.features.parameters():
                param.requires_grad = False

        in_features = self.efficientnet.classifier[1].in_features
        self.fc = nn.Sequential(
            nn.Linear(in_features + num_race_classes + num_obesity_classes, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Tanh()
        )

    def forward(self, image, race_tensor, obesity_tensor):
        x = self.efficientnet.features(image)
        x = self.efficientnet.avgpool(x)
        x = torch.flatten(x, 1)
        combined = torch.cat((x, race_tensor, obesity_tensor), dim=1)
        return self.fc(combined)

def train_classifier_with_metadata(train_loader, num_epochs, image_size, model_path, num_race_classes=7, num_obesity_classes=3, cancel_flag=None, progress_callback=None):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = InterestRegressorWithMetadata(img_size=image_size, num_race_classes=num_race_classes, num_obesity_classes=num_obesity_classes)

    if os.path.exists(model_path) and os.path.getsize(model_path) > 0:
        try:
            model.load_state_dict(torch.load(model_path, map_location=device))
            print("Loaded model from", model_path)
        except Exception as e:
            print(f"Failed to load model from {model_path}: {e}")

    model.to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-4)

    for epoch in range(num_epochs):
        if cancel_flag and cancel_flag():
            print("Training cancelled.")
            break
        if progress_callback:
            progress_callback(epoch + 1)
        model.train()
        running_loss = 0.0
        train_loader_iter = tqdm(train_loader, desc=f"Epoch {epoch+1}/{num_epochs}", leave=False)

        for images, race_tensor, obesity_tensor, labels in train_loader_iter:
            if cancel_flag and cancel_flag():
                print("Training cancelled.")
                break
            images = images.to(device)
            race_tensor = race_tensor.to(device)
            obesity_tensor = obesity_tensor.to(device)
            labels = labels.to(device).unsqueeze(1)

            optimizer.zero_grad()
            outputs = model(images, race_tensor, obesity_tensor)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)

        epoch_loss = running_loss / len(train_loader.dataset)
        print(f"Epoch {epoch+1}, Loss: {epoch_loss:.4f}")
        if cancel_flag and cancel_flag():
            return model
        torch.save(model.state_dict(), model_path)
        print(f"Model saved to {model_path}")
        
    if cancel_flag and cancel_flag():
        return model
    torch.save(model.state_dict(), model_path)
    print(f"Model saved to {model_path}")
    return model

def predict(model, data_loader):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.eval()
    all_predictions = []
    with torch.no_grad():
        for images, race_onehot, obesity_onehot, _ in data_loader:
            images = images.to(device)
            race_onehot = race_onehot.to(device)
            obesity_onehot = obesity_onehot.to(device)
            outputs = model(images, race_onehot, obesity_onehot)
            predictions = outputs.cpu().numpy().flatten().tolist()
            all_predictions.extend(predictions)
    return all_predictions

class SingleImageDataset(Dataset):
    def __init__(self, image_paths, race_vectors, obesity_vectors, img_size, transform=None):
        self.image_paths = image_paths
        self.race_vectors = race_vectors
        self.obesity_vectors = obesity_vectors
        self.img_size = img_size
        self.transform = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        try:
            image = Image.open(img_path).convert('RGB')
            if self.transform:
                image = self.transform(image)

            race_onehot = torch.tensor(self.race_vectors[idx], dtype=torch.float32)
            obesity_onehot = torch.tensor(self.obesity_vectors[idx], dtype=torch.float32)
            dummy_label = torch.tensor(0.0, dtype=torch.float32)

            return image, race_onehot, obesity_onehot, dummy_label
        except Exception as e:
            print(f"Error loading image at {img_path}: {e}")
            placeholder = torch.zeros((3, self.img_size, self.img_size))
            return placeholder, torch.zeros(7), torch.zeros(3), torch.tensor(0.0)

def init_models():
    FF.init_models()
    OT.init_models()

def load_images_for_prediction_dataloader(data_path, img_size, profile, batch_size=1):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    picture_dir = os.path.join(os.getcwd(), data_path, profile)
    image_paths = [os.path.join(picture_dir, f) for f in sorted(os.listdir(picture_dir)) if os.path.isfile(os.path.join(picture_dir, f))]

    transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    race_scores = []
    obesity_scores = []

    for img_path in image_paths:
        try:
            image = Image.open(img_path).convert('RGB')
            tensor = transform(image).unsqueeze(0).to(device)
            race_out = FF.predict(image)
            obesity_out = OT.predict_obesity_class(image)
            race_scores.append(race_out)
            obesity_scores.append(obesity_out)
        except Exception as e:
            print(f"[WARN] Skipping {img_path} due to error: {e}")
            race_scores.append([0.0]*7)
            obesity_scores.append([0.0]*3)

    dataset = SingleImageDataset(
        image_paths=image_paths,
        race_vectors=race_scores,
        obesity_vectors=obesity_scores,
        img_size=img_size,
        transform=transform
    )
    return DataLoader(dataset, batch_size=batch_size, shuffle=False)
