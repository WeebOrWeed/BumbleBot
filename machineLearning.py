import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import os
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader
from tqdm import tqdm  # For a nice progress bar
from torch.utils.data import Dataset, random_split, DataLoader
from PIL import Image
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
from torchvision import transforms
import ast  # For safely evaluating the string representation of the list

def construct_dataset(data_index_path, data_path, img_size, batch_size, train_test_split):
    """
    Constructs training and testing datasets for image classification
    based on a data index CSV and a root data path.

    Args:
        data_index_path (str): Path to the CSV file containing profile-outcome mapping
                                (e.g., "profile,outcome\n...").
        data_path (str): Root directory containing the profile folders.
        img_size (int): Desired size (both width and height) to resize images.
        train_test_split (float): Proportion of the dataset to use for training (e.g., 0.8 for 80%).

    Returns:
        tuple: A tuple containing the training DataLoader and the testing DataLoader.
               Returns (None, None) if an error occurs during dataset creation.
    """
    try:
        # Define image transformations
        transform = transforms.Compose([
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        # Create the custom dataset
        full_dataset = ProfileImageDataset(
            csv_file=data_index_path,
            root_dir=data_path,
            transform=transform
        )

        # Calculate the sizes of the training and testing sets
        train_size = int(train_test_split * len(full_dataset))
        test_size = len(full_dataset) - train_size

        # Split the dataset
        train_dataset, test_dataset = random_split(full_dataset, [train_size, test_size])

        # Create DataLoaders
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=4)

        return train_loader, test_loader

    except FileNotFoundError:
        print(f"Error: Data index file not found at {data_index_path} or data path {data_path} is incorrect.")
        return None, None
    except Exception as e:
        print(f"An error occurred during dataset construction: {e}")
        return None, None

class ProfileImageDataset(Dataset):
    def __init__(self, csv_file, root_dir, transform=None):
        """
        Custom dataset to load images and their corresponding continuous interest labels
        based on the profile-outcome mapping in the CSV file.

        Args:
            csv_file (str): Path to the CSV file containing 'profile' and 'outcome' columns.
                            The 'outcome' column contains a string representation of a list
                            of interest labels (e.g., '[-1, 0, 1, 0, 0]').
            root_dir (str): Root directory where the profile image folders are located.
            transform (callable, optional): Optional transform to be applied to the images.
        """
        self.df = pd.read_csv(csv_file)
        self.root_dir = root_dir
        self.transform = transform
        self.image_paths = []
        self.labels = []
        self._load_data()

    def _load_data(self):
        for index, row in self.df.iterrows():
            profile_id = row['profile']
            outcome_str = row['outcome']
            profile_dir = os.path.join(self.root_dir, profile_id)
            try:
                outcome_list = ast.literal_eval(outcome_str)
                if not isinstance(outcome_list, list):
                    print(f"Warning: Outcome for profile '{profile_id}' is not a list: {outcome_str}. Skipping profile.")
                    continue
                float_labels = [float(label) for label in outcome_list]
            except (SyntaxError, ValueError) as e:
                print(f"Warning: Could not parse outcome for profile '{profile_id}': {outcome_str}. Skipping profile. Error: {e}")
                continue

            if os.path.isdir(profile_dir):
                image_files = sorted([f for f in os.listdir(profile_dir) if os.path.isfile(os.path.join(profile_dir, f))])

                if len(image_files) == len(outcome_list):
                    for img_file, label in zip(image_files, float_labels):
                        img_path = os.path.join(profile_dir, img_file)
                        self.image_paths.append(img_path)
                        self.labels.append(label)
                else:
                    print(f"Warning: Number of images ({len(image_files)}) does not match the number of outcomes ({len(outcome_list)}) for profile '{profile_id}'. Skipping profile.")
            else:
                print(f"Warning: Profile directory not found: {profile_dir}")

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        label = self.labels[idx]
        try:
            image = Image.open(img_path).convert('RGB')
            if self.transform:
                image = self.transform(image)
            return image, torch.tensor(label, dtype=torch.float32) # Label shape will be [] (scalar)
        except Exception as e:
            print(f"Error loading image at {img_path}: {e}")
            # Return a placeholder or handle the error as needed
            if self.transform and hasattr(self.transform.transforms[0], 'size'):
                placeholder = torch.zeros((3, self.transform.transforms[0].size[0], self.transform.transforms[0].size[1]))
            else:
                placeholder = torch.zeros((3, 224, 224)) # Default placeholder size
            return placeholder, torch.tensor(0.0, dtype=torch.float32)

class InterestRegressor(nn.Module):
    def __init__(self, img_size, pretrained=True, freeze_features=False):
        super().__init__()
        self.img_size = img_size
        self.efficientnet = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None)

        # Freeze features if requested
        if freeze_features and pretrained:
            for param in self.efficientnet.features.parameters():
                param.requires_grad = False

        # Replace the classifier with a single output unit for regression
        in_features = self.efficientnet.classifier[1].in_features
        self.fc1 = nn.Linear(in_features, 1)
        self.tanh = nn.Tanh() # Optional: Squash output to [-1, 1]

    def forward(self, x):
        x = self.efficientnet.features(x)
        x = self.efficientnet.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc1(x)
        # Optional: Apply tanh to constrain the output to the desired range
        x = self.tanh(x)
        return x

def train_model(train_loader, num_epochs, image_size):
    """
    Initializes and trains a PyTorch model for regression on image data
    to predict a continuous interest level.

    Args:
        train_loader (DataLoader): DataLoader for the training dataset.
        num_epochs (int): The number of training epochs.
        image_size (int): The size of the input images.

    Returns:
        nn.Module: The trained PyTorch model.
    """
    # Define loss function, optimizer parameters, number of epochs, and device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    criterion = nn.MSELoss()  # Use Mean Squared Error for regression
    optimizer_name = 'Adam'
    learning_rate = 0.0001

    model = InterestRegressor(image_size)  # Initialize the regression model
    model.to(device)  # Move the model to the specified device

    # Initialize the optimizer based on the provided name
    if optimizer_name.lower() == 'adam':
        optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    elif optimizer_name.lower() == 'sgd':
        optimizer = optim.SGD(model.parameters(), lr=learning_rate)
    else:
        raise ValueError(f"Unsupported optimizer: {optimizer_name}. Choose 'Adam' or 'SGD'.")

    for epoch in range(num_epochs):
        model.train()     # Set the model to training mode each epoch
        running_loss = 0.0

        for inputs, labels in tqdm(train_loader, desc=f'Epoch {epoch+1}/{num_epochs}'):
            inputs = inputs.to(device)
            labels = labels.to(device).float().unsqueeze(1) # Ensure labels are float and [batch_size, 1] - ONLY ONCE!

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * inputs.size(0)

        epoch_loss = running_loss / len(train_loader.dataset)
        print(f'Epoch {epoch+1}/{num_epochs}, Training Loss: {epoch_loss:.4f}')

    print('Finished Training')
    return model

def predict(model, data_loader):
    """
    Makes predictions using a PyTorch regression model.

    Args:
        model (torch.nn.Module): The trained PyTorch regression model.
        data_loader (torch.utils.data.DataLoader): DataLoader for the input data.
        device (torch.device): The device to perform predictions on ('cuda' or 'cpu').

    Returns:
        list: A list of continuous prediction values.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.eval()  # Set the model to evaluation mode
    all_predictions = []
    with torch.no_grad():  # Disable gradient calculations during inference
        for inputs, _ in data_loader:  # Assuming your test DataLoader returns (inputs, labels) or just inputs
            inputs = inputs.to(device)
            outputs = model(inputs)
            # The output is a single continuous value for each image
            predictions = outputs.cpu().numpy().flatten().tolist()
            all_predictions.extend(predictions)
    return all_predictions

def calculate_loss(model, data_loader):
    """
    Calculates the Mean Squared Error loss on a given dataset.

    Args:
        model (torch.nn.Module): The trained PyTorch regression model.
        data_loader (torch.utils.data.DataLoader): DataLoader for the evaluation dataset.
        device (torch.device): The device to perform calculations on ('cuda' or 'cpu').

    Returns:
        float: The average Mean Squared Error loss.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.eval()  # Set the model to evaluation mode
    criterion = nn.MSELoss()
    total_loss = 0.0
    num_samples = 0
    with torch.no_grad():
        for inputs, labels in data_loader:
            inputs = inputs.to(device)
            labels = labels.to(device).float().unsqueeze(1)
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            total_loss += loss.item() * inputs.size(0)
            num_samples += inputs.size(0)
    avg_loss = total_loss / num_samples if num_samples > 0 else 0.0
    print(f"Mean Squared Error Loss: {avg_loss:.4f}")
    return avg_loss

class SingleImageDataset(Dataset):
    def __init__(self, image_paths, img_size, transform=None):
        self.image_paths = image_paths
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
            return image, torch.tensor(0.0, dtype=torch.float32).unsqueeze(0)  # Dummy label
        except Exception as e:
            print(f"Error loading image at {img_path}: {e}")
            placeholder_size = (self.transform.transforms[0].size[0] if self.transform and hasattr(self.transform.transforms[0], 'size') else self.img_size)
            return torch.zeros((3, placeholder_size, placeholder_size)), torch.tensor(0.0, dtype=torch.float32).unsqueeze(0)

def load_images_for_prediction_dataloader(data_path, img_size, profile, batch_size=1):
    """Loads images for a profile and returns a DataLoader for regression prediction."""
    picture_dir = os.path.join(os.getcwd(), data_path, profile)
    image_paths = []
    if os.path.isdir(picture_dir):
        for file in sorted(os.listdir(picture_dir)): # Ensure consistent order
            fp = os.path.join(picture_dir, file)
            if os.path.isfile(fp):
                image_paths.append(fp)

    transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    dataset = SingleImageDataset(image_paths, img_size, transform=transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    return dataloader

# Using the special variable 
# __name__
if __name__=="__main__":
    main()