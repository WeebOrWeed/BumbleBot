import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras import layers
from tensorflow.keras.applications import EfficientNetB0
from sklearn.metrics import accuracy_score
import pandas as pd
import os
from skimage import io
from skimage.transform import resize
import random
import numpy as np


def return_test_train(split_value):
    rval = random.random()
    if rval >= split_value:
        return 1  # 1 means its validation data
    else:
        return 0  # zero means its training data


def encode_one_hot(label):
    if label == "positive":
        return 1
    elif label == "negetive":
        return 0


def construct_dataset(DATA_INDEX, DATA_PATH, IMG_SIZE, test_train_split):
    data_index = pd.read_csv(DATA_INDEX)
    data_index.head()
    x_train = []
    y_train = []
    x_test = []
    y_test = []
    counter = 0
    for index, row in data_index.iterrows():
        # construct the image path
        image_path_folder = os.path.join(DATA_PATH, row["profile"])
        for file in os.listdir(image_path_folder):
            fp = os.path.join(image_path_folder, file)
            image = io.imread(fp)
            img = resize(image, (IMG_SIZE, IMG_SIZE))
            label = encode_one_hot(row["outcome"])
            if return_test_train(test_train_split) == 0:  # zero means its training data
                # reshape the image using tensorflow's image automator
                x_train.append(img)
                y_train.append(label)
            else:
                x_test.append(img)
                y_test.append(label)
            counter += 1

    print(f"A total of {counter} images were processed")

    return [np.asarray(x_train), np.asarray(y_train), np.asarray(x_test), np.asarray(y_test)]


def build_model(IMG_SIZE):
    inputs = layers.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    img_augmentation = Sequential(
        [
            layers.RandomRotation(factor=0.10),
            layers.RandomTranslation(height_factor=0.1, width_factor=0.1),
        ],
        name="img_augmentation",
    )
    x = img_augmentation(inputs)
    model = EfficientNetB0(include_top=False, input_tensor=x, weights="imagenet")

    # Freeze the pretrained weights
    model.trainable = False

    # Rebuild top
    x = layers.GlobalAveragePooling2D(name="avg_pool")(model.output)
    x = layers.BatchNormalization()(x)

    top_dropout_rate = 0.2
    x = layers.Dropout(top_dropout_rate, name="top_dropout")(x)
    outputs = layers.Dense(1, activation="sigmoid", name="pred")(x)  # the otput layers are hardcoded
    # cause you cant sorta like a person on bumble

    # Compile
    model = tf.keras.Model(inputs, outputs, name="EfficientNet")
    optimizer = tf.keras.optimizers.Adam(learning_rate=1e-3)
    model.compile(optimizer=optimizer, loss="binary_crossentropy", metrics=["accuracy"])
    return model


def train_model(x_train, y_train, IMG_SIZE, BATCH_SIZE, epochs):
    strategy = tf.distribute.MirroredStrategy()
    with strategy.scope():
        model = build_model(IMG_SIZE)
    model.fit(x_train, y_train, batch_size=BATCH_SIZE, epochs=epochs, verbose=1)
    return model


def make_prediction(pictures, model):
    prediction = model.predict(np.asarray(pictures))
    avg = np.mean(prediction)
    print(f"Average weight of prediction {avg}")
    return avg

def make_decision(pred_avg, thresh):
    print(f"Making a decision, accuracy of {pred_avg}, threshold set at {thresh}")
    if pred_avg > thresh:
        return 1
    else:
        return 0

def load_images_for_prediction(DATA_PATH, IMG_SIZE, profile):
    pictureDir = os.path.join(os.getcwd(), DATA_PATH, profile)
    # load all the pictures into an array
    pictures = []
    for file in os.listdir(pictureDir):
        fp = os.path.join(pictureDir, file)
        # then load them using sk image
        image = io.imread(fp)
        img = resize(image, (IMG_SIZE, IMG_SIZE))
        pictures.append(img)
    return pictures


def return_accuracy(ytrue, ypreads):
    return accuracy_score(ytrue, ypreads)
