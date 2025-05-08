from __future__ import print_function, division
import warnings
warnings.filterwarnings("ignore")
import os.path
import pandas as pd
import torch
import torch.nn as nn
import numpy as np
import torchvision
from torchvision import datasets, models, transforms
import dlib
import csv
import os
from PIL import Image
import argparse
import ast

model_fair_7 = None
model_fair_4 = None
trans = None
device = None
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_path_multi_7 = os.path.join(BASE_DIR, 'fair_face_models', 'res34_fair_align_multi_7_20190809.pt')
model_path_multi_4 = os.path.join(BASE_DIR, 'fair_face_models', 'res34_fair_align_multi_4_20190809.pt')

# Returns all the faces in iamge
def detect_faces_of_image(image, default_max_size=800, size = 300, padding = 0.25):
    cnn_face_detector = dlib.cnn_face_detection_model_v1('dlib_models/mmod_human_face_detector.dat')
    sp = dlib.shape_predictor('dlib_models/shape_predictor_5_face_landmarks.dat')
    img = np.array(image)

    old_height, old_width, _ = img.shape
    if old_width > old_height:
        new_width = default_max_size
        new_height = int(default_max_size * old_height / old_width)
    else:
        new_height = default_max_size
        new_width = int(default_max_size * old_width / old_height)

    img = dlib.resize_image(img, rows=new_height, cols=new_width)
    
    dets = cnn_face_detector(img, 1)
    num_faces = len(dets)
    if num_faces == 0:
        print("Sorry, there were no faces found")
        return np.empty(0)
    # Find the 5 face landmarks we need to do the alignment.
    faces = dlib.full_object_detections()
    for detection in dets:
        rect = detection.rect
        faces.append(sp(img, rect))
    return dlib.get_face_chips(img, faces, size=size, padding = padding)

def predidct_races_of_image(face_chips):
    # list within a list. Each sublist contains scores for all races. Take max for predicted race
    race_scores_fair = []
    # gender_scores_fair = []
    # age_scores_fair = []
    race_preds_fair = []
    # gender_preds_fair = []
    # age_preds_fair = []
    # race_scores_fair_4 = []
    # race_preds_fair_4 = []

    # We take average if there're multiple faces
    
    for face_chip in face_chips:
        pil_image = Image.fromarray(face_chip)
        image = trans(pil_image)
        image = image.view(1, 3, 224, 224)  # reshape image to match model dimensions (1 batch size)
        image = image.to(device)

        # fair
        outputs = model_fair_7(image)
        outputs = outputs.cpu().detach().numpy()
        outputs = np.squeeze(outputs)

        race_outputs = outputs[:7]
        # gender_outputs = outputs[7:9]
        # age_outputs = outputs[9:18]

        race_score = np.exp(race_outputs) / np.sum(np.exp(race_outputs))
        # gender_score = np.exp(gender_outputs) / np.sum(np.exp(gender_outputs))
        # age_score = np.exp(age_outputs) / np.sum(np.exp(age_outputs))

        race_pred = np.argmax(race_score)
        # gender_pred = np.argmax(gender_score)
        # age_pred = np.argmax(age_score)

        race_scores_fair.append(race_score)
        # gender_scores_fair.append(gender_score)
        # age_scores_fair.append(age_score)

        race_preds_fair.append(race_pred)
        # gender_preds_fair.append(gender_pred)
        # age_preds_fair.append(age_pred)
        # if race_pred == 0:
        #     print('White')
        # elif race_pred == 1:
        #     print("Black")
        # elif race_pred == 2:
        #     print("Latino_Hispanic")
        # elif race_pred == 3:
        #     print("East Asian")
        # elif race_pred == 4:
        #     print("Southeast Asian")
        # elif race_pred == 5:
        #     print("Indian")
        # elif race_pred == 6:
        #     print("Middle Eastern")    
        # else:
        #     print("Impossible Race")
    if len(race_scores_fair) == 0:
        return np.array([1/7,1/7,1/7,1/7,1/7,1/7,1/7])
    return np.mean(np.stack(race_scores_fair), axis=0)

def init_models():
    global model_fair_7, model_fair_4, trans, device  
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model_fair_7 = torchvision.models.resnet34(pretrained=True)
    model_fair_7.fc = nn.Linear(model_fair_7.fc.in_features, 18)
    model_fair_7.load_state_dict(torch.load(model_path_multi_7, map_location=device))
    model_fair_7 = model_fair_7.to(device)
    model_fair_7.eval()

    model_fair_4 = torchvision.models.resnet34(pretrained=True)
    model_fair_4.fc = nn.Linear(model_fair_4.fc.in_features, 18)
    model_fair_4.load_state_dict(torch.load(model_path_multi_4, map_location=device))
    model_fair_4 = model_fair_4.to(device)
    model_fair_4.eval()

    trans = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

def convert_old_csv(csv_file, new_csv_file):
    image_root = "C:/Users/Redux/autolike/BumbleBot/DATA/e4fa3127d2b1b7137b65ed697015d407"
    df = pd.read_csv(csv_file)
    if not os.path.exists(new_csv_file):
        csvsessdata = open(new_csv_file, "w")
        csvsessdata.write("profile,image,outcome,race_scores\n")
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
            print(profile)
            outcome = ast.literal_eval(row["outcome"])

            if profile in existing_profiles:
                continue
            profile_dir = image_root + "/" + profile

            if not os.path.isdir(profile_dir):
                # writer.writerow([profile,outcome,np.empty(7)])
                # csvsessdata.flush()
                continue

            idx = 0
            for img_file in sorted(os.listdir(profile_dir)):
                img_path = os.path.join(profile_dir, img_file)
                csvsessdata.flush()
                if not os.path.isfile(img_path):
                    continue

                image = Image.open(img_path).convert("RGB")
                face_chips = detect_faces_of_image(image)
                race_scores = predidct_races_of_image(face_chips)
                writer.writerow([profile, img_file, outcome[idx], race_scores])  # add other fields if needed
                idx += 1
                csvsessdata.flush()

def predict(image):
    face_chips = detect_faces_of_image(image)
    return predidct_races_of_image(face_chips)

if __name__ == "__main__":
    init_models()
    # convert_old_csv("C:/Users/Redux/autolike/BumbleBot/DATA/e4fa3127d2b1b7137b65ed697015d407/e4fa3127d2b1b7137b65ed697015d407.csv", "C:/Users/Redux/autolike/BumbleBot/DATA/e4fa3127d2b1b7137b65ed697015d407/e4fa3127d2b1b7137b65ed697015d407_2.csv")
    # init_models()
    # image = Image.open("C:/Users/Redux/autolike/BumbleBot/a6f2069065035938704f79e3bcf9f3f3-PREDICTION/1a15bcb3-3743-4dc1-b459-b430e7af58a4/image_0.png").convert('RGB')
    # face_chips = detect_faces_of_image(image)
    # print(predidct_races_of_image(face_chips))
