from PIL import Image
import win32gui, win32con, win32api, win32ui
import mss
import numpy as np
import cv2
import time
import skimage
from skimage.metrics import structural_similarity as ssim
from skimage.exposure import match_histograms

# List of image file paths for the set of six images
# MAX HUD SCALE
# ONE BOX [660, 960], [750, 1050]
# TOP LEFT CORNER OF FAR LEFT [660, 960]
# TOP RIGHT CORNER OF FAR RIGHT [1230, 960]

# MIN HUD SCALE
# ONE BOX [810, 1020], [854, 1064]
# TOP LEFT CORNER OF FAR LEFT [810, 1020] TOP LEFT CORNER OF FAR RIGHT [1050]
# TOP RIGHT CORNER OF FAR RIGHT [1095, 1020]
# List of image file paths for the set of nine images to compare to

# OFFSET 4
# FAR LEFT  screenshot(660, 962, 92, 92)  SCALE 1   OFFSET 4
# FAR RIGHT screenshot(1140, 962, 92, 92) SCALE 1

#"WEAPON_LR.jpg", WEAPON_THOMPSON
compare_image_paths = ["WEAPON_AK.jpg","WEAPON_LR.jpg", "WEAPON_THOMPSON.jpg" ,"WEAPON_CUSTOM.jpg","WEAPON_M249.jpg","WEAPON_MP5.jpg","WEAPON_PYTHON.jpg","WEAPON_SEMI.jpg"]

def screenshot(left, top, width, height):
    with mss.mss() as sct:
        # The screen part to capture
        monitor = {'top': top, 'left': left, 'width': width, 'height': height}
        # Get raw pixels from the screen, save it to a Numpy array
        img = np.array(sct.grab(monitor))
        return img


def get_hotbar(UI_SCALE):
    images = [cv2.imread(f'./images_n/{compare_image_paths[i]}') for i in range(len(compare_image_paths))]

    pos = int(660 + ((572 - (572 * UI_SCALE)) / 2))
    size = int(92 * UI_SCALE)
    offset = int(4 * UI_SCALE)


    bluest_image = None
    max_green_value = 0
    max_green_index = 0
    total_blue = 0
    blue_index = 0

    for i in range(6):
        total_similarity = 0
        index = 0
        total_similarity_m = 0

        image = (screenshot(660 + (i * (size + offset)), 962, size, size))
        frame = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if(i == 0):
            bluest_image = image
        curr_blue = 0
        for j in range (size):
            for k in range (size):
                colorsB = image[j,k,0]
                colorsG = image[j,k,1]
                colorsR = image[j,k,2]
                if(colorsB > colorsG and colorsB > colorsR):
                    curr_blue += colorsB

        # img_sc = cv2.resize(image, (int(92 * UI_SCALE), int(92 * UI_SCALE)))
        # for k in range(len(images)):
        #     img_reference = images[k]
        #     img_reference = cv2.resize(img_reference, (int(92 * UI_SCALE), int(92 * UI_SCALE)))

        #     matched = match_histograms(img_sc, img_reference, channel_axis=-1)

        #     gray_reference = cv2.cvtColor(img_reference, cv2.COLOR_RGB2GRAY)
        #     gray_sc = cv2.cvtColor(img_sc, cv2.COLOR_RGB2GRAY)

        #     grayB_m = cv2.cvtColor(matched, cv2.COLOR_RGB2GRAY)

        #     s_m = ssim(grayB_m, gray_reference)
        #     s = ssim(gray_sc, gray_reference)
        #     if(s > total_similarity):
        #         index = k
        #         total_similarity = s
        #         total_similarity_m = s_m
        # print(i, "most similiar to", compare_image_paths[index], "score:",total_similarity,total_similarity_m )

        if (curr_blue > total_blue):
            total_blue = curr_blue
            blue_index = i
            bluest_image = image
    print(blue_index, total_blue)
    # Return image of current selecton, and index
    return bluest_image


def get_weapon_equipped(UI_SCALE):
    images = [cv2.imread(f'./images_n/{compare_image_paths[i]}') for i in range(len(compare_image_paths))]
    error_t = 0.0
    index = 0
    imgB = get_hotbar(UI_SCALE)
    imgB = cv2.resize(imgB, (int(92 * UI_SCALE), int(92 * UI_SCALE)))
    for i in range(len(images)):
        imgA = images[i]
        imgA = cv2.resize(imgA, (int(92 * UI_SCALE), int(92 * UI_SCALE)))

        matched = match_histograms(imgB, imgA, channel_axis=-1)

        grayA = cv2.cvtColor(imgA, cv2.COLOR_BGRA2GRAY)
        grayB = cv2.cvtColor(imgB, cv2.COLOR_RGB2GRAY)

        grayB_m = cv2.cvtColor(matched, cv2.COLOR_RGB2GRAY)

        np_subtr  = np.subtract(grayA, grayB)
        np_mean = np.mean(np_subtr)
        s_m = ssim(grayB_m, grayA)
        s = ssim(grayB, grayA)
        #print(s, s_m,compare_image_paths[i])
        if(s > error_t):
            index = i
            error_t = s
    #print(compare_image_paths[index])
    #return compare_image_paths[index]
    return "WEAPON_SEMI"

# def get_weapon_equipped(UI_SCALE):
#     # Get images
#     images = [skimage.io.imread(f'./images_n/{compare_image_paths[i]}') for i in range(len(compare_image_paths))]
#     # Get Bluest Image
#     current_equip = get_hotbar(UI_SCALE)
#     # Hacky, but save to disk
#     cv2.imwrite('./images_n/WP_CURRENT.jpg', current_equip)
#     # Read in current weapon
#     current_equip = skimage.io.imread('./images_n/WP_CURRENT.jpg')
#     # Convert to greyscale
#     #current_equip = cv2.cvtColor(current_equip, cv2.COLOR_BGR2GRAY)
#     # resize the image to 92 by 92
#     current_equip = skimage.transform.resize(current_equip,(92,92))
    
#     # initialize a dictionary to store the similarity scores
#     similarity_scores = {}
#     # loop through the images and compute the structural similarity index (SSIM)
#     for img in images:
#         # Convert to greyscale
#         #img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
#         # Resize the image to 92 by 92
#         img = skimage.transform.resize(img, (92, 92))
#         print(img.shape)
#         print(current_equip.shape)
#         # compute the SSIM score and store it in the dictionary
#         similarity_scores[img] = structural_similarity(current_equip, img)
    
#     # sort the dictionary by values in descending order
#     sorted_similarity_scores = {k: v for k, v in sorted(similarity_scores.items(), key=lambda item: item[1], reverse=True)}
    
#     # return the most similar image
#     print(list(sorted_similarity_scores.keys())[0])
#     return "WEAPON_AK"
#     #return list(sorted_similarity_scores.keys())[0]
