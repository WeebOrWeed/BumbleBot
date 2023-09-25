# BumbleBot
A autoswiper for bumble that learns your preferences
![Bumble Bot Logo](/BumbleBotImage.png?raw=true)

## Introduction

Welcome to the BumbleBot Readme! This document will provide you with an overview of the Bumble AutoSwipe bot, its features, installation instructions, and usage guidelines. The Bumble AutoSwipe bot is designed to automate the swiping process on Bumble. Also note that this for educational purposes only. Apart from being quite unethical its also illegal to use bumble as a bot. For the whole article that delves into the details of why it was done please check here : [Shenanigans Article](https://www.shenanigans.blog/shenan/?shenan=bumblebot)

Also here is a demo of the bot in action:
[![Demo of Bumble Bot](https://img.youtube.com/vi/TggSPKmyDUY/0.jpg)](https://www.youtube.com/watch?v=TggSPKmyDUY)

## Features

- **Automated Swiping**: The Bumble AutoSwipe bot is programmed to automatically swipe left or right on profiles based on predefined criteria. This eliminates the need for manual swiping, allowing you to browse through profiles more efficiently.

- **Customizable Settings**: The bot comes with customizable settings that allow you to define your preferences for swiping. You can set parameters such as age range, location, and gender to tailor the swiping behavior according to your preferences.

## Installation

Follow these steps to install the Bumble AutoSwipe bot:

1. **Clone the Repository**: Clone this repository to your local machine using the following command:

   ```
   git clone https://github.com/range-et/BumbleBot
   ```

2. **Navigate to the Directory**: Move into the project directory:

   ```
   cd BumbleBot
   ```

3. **Install Dependencies**: Install the required dependencies using:

   ```
   pip install -r requirements.txt
   ```
   Note this installs from the requirements.txt file I highly recommend using VEnv as a virtual environment. I personally used conda and installed all the packages into an anaconda environment.

4. **Configuration**: Open the `settings.json` file and customize the settings such as the model file - where the trained model will be stored, the data folder, where the data is stored (Like the pictures etc). Number of epochs to train the model for. TTS - which is the Test Training split, where a number like 0.75 means 75% of the data is used for training and 0.25 is used for validation/testing. And lastly thresh, the ML model outputs a number between 0-1 so as to how confident it is about a profile, the threshold defines at what point you would want the model to swipe. A number like 0.65 worked well for me.


## Usage

To start using the Bumble AutoSwipe bot, follow these steps:

1. **Run the Bot**: In the project directory, run the bot using the following command:

   ```
   python main.py HELP
   ```
   This prints out all the possible commands.

1. **Collecting Data**: To collect data for training, Start the bot with the command:
    ```
    python main.py SCRAPE
    ```
    This launches a browser window where you can log into bumble and start swiping. By typing yes or no in the command terminal. (Also there are instructions in the terminal)

1. **Train the Model**: To train the model type:
    ```
    python main.py TRAIN
    ```

1. **To start auto swiping**: Type the command:
    ```
    python main.py SWIPE
    ```

1. **Interrupting the Bot**: If you want to stop the bot, simply press `Ctrl + C` in the terminal where the bot is running.

## Disclaimer

Please note that the use of automated bots on platforms like Bumble may violate their terms of service. Use this bot at your own risk. The creators of this bot are not responsible for any consequences that may arise from its usage. This was made for educational purposes only. 

## Contributing

If you'd like to contribute to the development of the Bumble AutoSwipe bot, feel free to submit pull requests or raise issues in the [GitHub repository](https://github.com/range-et/BumbleBot).

## License

The Bumble AutoSwipe bot is released under the [MIT License](LICENSE).

---

Happy swiping! If you encounter any issues or have suggestions for improvements, don't hesitate to reach out or contribute. Your feedback is greatly appreciated.
