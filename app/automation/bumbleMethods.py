from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import uuid
import os
import urllib.request

# this downloads all pictures into a folder labelled by the profiles name age and a uuid
def find_download_all_pictures(driver, data_folder):
    # first make the folder name
    idnum = str(uuid.uuid4())
    string = idnum
    # make the directory
    savePath = os.path.join(data_folder, string)
    pictures = driver.find_elements(By.CLASS_NAME, "media-box__picture-image")
    if len(pictures) > 0:
        os.mkdir(savePath)
        for i in range(len(pictures)):
            pic = pictures[i]
            src = pic.get_attribute("src")
            urllib.request.urlretrieve(src, os.path.join(savePath, f"image_{i}.png"))
        return string
    else:
        return "invalid"


# like this profile that we are working on
def like_profile(driver):
    driver.find_element(By.CSS_SELECTOR, "body").send_keys(Keys.RIGHT)


# dislike the profile we are workig on
def dislike_profile(driver):
    driver.find_element(By.CSS_SELECTOR, "body").send_keys(Keys.LEFT)
