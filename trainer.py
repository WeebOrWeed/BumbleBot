import machineLearning as ML
import utilities as UM


def main_trainning_app():
    # load up the JSON file that holds the settings
    settings = UM.load_settings()
    # first construct the training data example
    [x_train, y_train, x_test, y_test] = ML.construct_dataset(
        settings["DATA_INDEX"], settings["DATA_PATH"], int(settings["IMG_SIZE"]), float(settings["TTS"])
    )
    # the model just keeps reajusting old weights that its seen
    # try loading the model if that exists
    model = ML.build_model(int(settings["IMG_SIZE"]))
    try:
        model.load_weights(settings["MODELPATH"])
    except Exception as e:
        print("Couldn't load existing model")
    # now start training
    model = ML.train_model(
        x_train, y_train, int(settings["IMG_SIZE"]), int(settings["BATCH_SIZE"]), int(settings["EPOCHS"])
    )
    # make some test predictions to see how the model did 
    y_preads = model.predict(x_test)
    accuracy = ML.return_accuracy(y_test, y_preads)
    print(f"The model is {accuracy*100}% accurate")
    # save the accuracy
    model.save_weights(settings["MODELPATH"])


if __name__ == "__main__":
    main_trainning_app()
