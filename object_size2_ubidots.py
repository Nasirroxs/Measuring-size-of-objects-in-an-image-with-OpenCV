# import the necessary packages
from scipy.spatial import distance as dist
from imutils import perspective
from imutils import contours
import numpy as np
import argparse
import imutils
import cv2
import requests
import time


#global result
#result = 2
#URL_EDUCATIONAL = "https://things.ubidots.com/api/v1.6/variables?token=A1E-IYDQdB0bAN6hGszR2t5rCXtM5tKvmFhttp://things.ubidots.com"
INDUSTRIAL_USER = False  # Set this to False if you are an educational user
TOKEN = "A1E-T9BqJqlx1iyBWdjAU9ybdIwepMztdq"  # Put here your Ubidots TOKEN
DEVICE_LABEL = "Raspberry_PI"  # Device where will be stored the result
VARIABLE_LABEL_1 = "Height"
VARIABLE_LABEL_2 = "Width"


def midpoint(ptA, ptB):
        return ((ptA[0] + ptB[0]) * 0.5, (ptA[1] + ptB[1]) * 0.5)
 
# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", required=True,
     help="path to the input image")
ap.add_argument("-w", "--width", type=float, required=True,
     help="width of the left-most object in the image (in inches)")
args = vars(ap.parse_args())
# load the image, convert it to grayscale, and blur it slightly
image = cv2.imread(args["image"])
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
gray = cv2.GaussianBlur(gray, (7, 7), 0)
 
# perform edge detection, then perform a dilation + erosion to
# close gaps in between object edges
edged = cv2.Canny(gray, 50, 100)
edged = cv2.dilate(edged, None, iterations=1)
edged = cv2.erode(edged, None, iterations=1)
 
# find contours in the edge map
cnts = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL,
     cv2.CHAIN_APPROX_SIMPLE)
cnts = imutils.grab_contours(cnts)
 
# sort the contours from left-to-right and initialize the
# 'pixels per metric' calibration variable
(cnts, _) = contours.sort_contours(cnts)
pixelsPerMetric = None

# loop over the contours individually
for c in cnts:
     # if the contour is not sufficiently large, ignore it
     if cv2.contourArea(c) < 100:
          continue
 
     # compute the rotated bounding box of the contour
     orig = image.copy()
     box = cv2.minAreaRect(c)
     box = cv2.cv.BoxPoints(box) if imutils.is_cv2() else cv2.boxPoints(box)
     box = np.array(box, dtype="int")
 
     # order the points in the contour such that they appear
     # in top-left, top-right, bottom-right, and bottom-left
     # order, then draw the outline of the rotated bounding
     # box
     box = perspective.order_points(box)
     cv2.drawContours(orig, [box.astype("int")], -1, (0, 255, 0), 2)
 
     # loop over the original points and draw them
     for (x, y) in box:
          cv2.circle(orig, (int(x), int(y)), 5, (0, 0, 255), -1)

# unpack the ordered bounding box, then compute the midpoint
     # between the top-left and top-right coordinates, followed by
     # the midpoint between bottom-left and bottom-right coordinates
     (tl, tr, br, bl) = box
     (tltrX, tltrY) = midpoint(tl, tr)
     (blbrX, blbrY) = midpoint(bl, br)
 
     # compute the midpoint between the top-left and top-right points,
     # followed by the midpoint between the top-righ and bottom-right
     (tlblX, tlblY) = midpoint(tl, bl)
     (trbrX, trbrY) = midpoint(tr, br)
 
     # draw the midpoints on the image
     cv2.circle(orig, (int(tltrX), int(tltrY)), 5, (255, 0, 0), -1)
     cv2.circle(orig, (int(blbrX), int(blbrY)), 5, (255, 0, 0), -1)
     cv2.circle(orig, (int(tlblX), int(tlblY)), 5, (255, 0, 0), -1)
     cv2.circle(orig, (int(trbrX), int(trbrY)), 5, (255, 0, 0), -1)
 
     # draw lines between the midpoints
     cv2.line(orig, (int(tltrX), int(tltrY)), (int(blbrX), int(blbrY)),
          (255, 0, 255), 2)
     cv2.line(orig, (int(tlblX), int(tlblY)), (int(trbrX), int(trbrY)),
          (255, 0, 255), 2)

# compute the Euclidean distance between the midpoints
     dA = dist.euclidean((tltrX, tltrY), (blbrX, blbrY))
     dB = dist.euclidean((tlblX, tlblY), (trbrX, trbrY))
 
     # if the pixels per metric has not been initialized, then
     # compute it as the ratio of pixels to supplied metric
     # (in this case, inches)
     if pixelsPerMetric is None:
          pixelsPerMetric = dB / args["width"]

# compute the size of the object
     dimA = dA / pixelsPerMetric
     dimB = dB / pixelsPerMetric
 
     # draw the object sizes on the image
     cv2.putText(orig, "{:.1f}in".format(dimA),
          (int(tltrX - 15), int(tltrY - 10)), cv2.FONT_HERSHEY_SIMPLEX,
          0.65, (255, 255, 255), 2)
     cv2.putText(orig, "{:.1f}in".format(dimB),
          (int(trbrX + 10), int(trbrY)), cv2.FONT_HERSHEY_SIMPLEX,
          0.65, (255, 255, 255), 2)
 
     # show the output image
     cv2.imshow("Image", orig)
     cv2.waitKey(0)

def build_payload(variable_1, variable_2):
    payload = {variable_1: dimA,variable_2: dimB}

    return payload
     #post_request(payload)
    

def post_request(payload):
    # Creates the headers for the HTTP requests
    url = "https://things.ubidots.com"
    url = "{}/api/v1.6/devices/{}".format(url, DEVICE_LABEL)
    headers = {"X-Auth-Token":TOKEN, "Content-Type": "application/json"}
    #x-ubidots-apikey
    # Makes the HTTP requests
    status = 400
    attempts = 0
    while status >= 400 and attempts <= 5:
        req = requests.post(url=url, headers=headers, json=payload)
        status = req.status_code
        attempts += 1
        time.sleep(1)

    # Processes results
    if status >= 400:
        print("[ERROR] Could not send data after 5 attempts, please check \
            your token credentials and internet connection")
        return False
        

    print("[INFO] request made properly, your device is updated")
    return True
    return req
    

def main():
    payload = build_payload(VARIABLE_LABEL_1, VARIABLE_LABEL_2)

    print("[INFO] Attempting to send data")
    post_request(payload)
    print("[INFO] finished")

if __name__== "__main__":
    while (True):
        main()
        time.sleep(1)
        break
