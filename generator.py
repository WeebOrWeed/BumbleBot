import os
import shutil
import random
import pandas as pd
import csv

root_dir = "C:/Users/Redux/autolike/BumbleBot/DATA/e4fa3127d2b1b7137b65ed697015d407"
source_csv = f"{root_dir}/e4fa3127d2b1b7137b65ed697015d407_3.csv"
destination_folder = "C:/Users/Redux/autolike/BumbleBot/InitialData"

os.makedirs(destination_folder, exist_ok=True)

df = pd.read_csv(source_csv)
new_csv_file = destination_folder + "/init_data.csv"
tianlin_csv_file = "C:/Users/Redux/autolike/BumbleBot/Weights/tianlin.csv"
if not os.path.exists(new_csv_file):
    csvsessdata = open(new_csv_file, "w")
    csvsessdata.write("image,race_scores,obese_scores\n")
    csvsessdata.close()
if not os.path.exists(tianlin_csv_file):
    tianlindata = open(tianlin_csv_file, "w")
    tianlindata.write("image,outcome,race_scores,obese_scores\n")
    tianlindata.close()
with open(new_csv_file, "a+", newline="") as csvsessdata, open(tianlin_csv_file, "a+", newline="") as tianlindata:
    counter = 0
    writercsv = csv.writer(csvsessdata)
    writertianlin = csv.writer(tianlindata)
    # shuffle the rows
    for index, row in df.sample(frac=1).iterrows():
        profile = row["profile"]
        image_path = row["image"]
        tianlin_outcome = row["outcome"]
        race_scores = row["race_scores"]
        obese_scores = row["obese_scores"]
        shutil.copy2(f"{root_dir}/{profile}/{image_path}",f"{destination_folder}/{counter}.png")
        writercsv.writerow([f"{counter}.png", race_scores, obese_scores])
        writertianlin.writerow([f"{counter}.png", tianlin_outcome, race_scores, obese_scores])
        counter+=1