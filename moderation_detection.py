import boto3
import cv2
import numpy as np
import io
import math
from PIL import Image
import random



def moderation(bucket, img_path):
    # amazon rekognition connection
    boto3.setup_default_session(profile_name='default')
    client = boto3.client('rekognition')

    # Load image from S3 bucket
    s3_connection = boto3.resource('s3')

    s3_object = s3_connection.Object(bucket,img_path)
    s3_response = s3_object.get()

    #read file directly from s3 bucket
    stream = io.BytesIO(s3_response['Body'].read())
    img = Image.open(stream)

    #image dimensions
    imgWidth, imgHeight = img.size


    gridCols = 8 #total columns in the grid
    gridRows = 4 #total rows in thegrid

    userH = int(imgHeight / gridRows)  # user image height
    userW = int(imgWidth / gridCols)  # user image width


    results = []

    def cropImage(fromCols, toCols, fromRows, toRows, image):
        fromR = int(fromRows * userH) #crop starting point for rows
        toR = int(toRows * userH) #crop ending point for rows
        fromC = int(fromCols * userW) #crop starting point for columns
        toC = int(toCols * userW) #crop ending point for columns
        
        # Load the image into a NumPy array
        np_image = np.array(image)
        
        # Check if np_image has at least 2 dimensions
        if np_image.ndim >= 2:
            cropped_image = np_image[fromR:toR, fromC:toC] #halved image
        else:
            raise ValueError("np_image must have at least 2 dimensions, but it has {}".format(np_image.ndim))

        hashV = random.getrandbits(16) #unique id generated for each halved image
        
        # Save the cropped image to a buffer
        file_stream = io.BytesIO()
        Image.fromarray(cropped_image).save(file_stream, format='PNG')

        s3 = boto3.client("s3")

        s3.put_object(Bucket=bucket, Key="temp/{}.png".format(hashV), Body=file_stream.getvalue())


        return ("temp/{}.png".format(hashV))




        # function to detect the grid position of detected inappropriate image
    def userPosition(cols, rows, naughtyImage, image):

        # Fetch image from S3 bucket
        s3 = boto3.client('s3')
        image = s3.get_object(Bucket=bucket, Key=img_path)
        img_bytes = image['Body'].read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED) #grid image


        img2 = img.copy() #copy of the grid image
        template = naughtyImage #inappropriate user image
        h = template.shape[0] #user image height
        w = template.shape[1] #user image width


        heightTotal = img.shape[0]  # total grid image height
        widthTotal = img.shape[1]  # total grid image width
        cols = 8 #total grid image columns
        rows = 4 #total grid image rows
        personWidth = widthTotal / cols #user image width
        personHeight = heightTotal / rows #user image height


    # All possible methods for comparison in a list:
    # 'cv.TM_CCOEFF_NORMED', 'cv.TM_CCORR',  'cv.TM_CCORR_NORMED', 
    # 'cv.TM_SQDIFF', 'cv.TM_SQDIFF_NORMED', 'cv.TM_CCOEFF'

        methods = ['cv2.TM_CCOEFF'] #pick the method of image comparison


    # evaluate the copied image with the chosen method   
        for meth in methods:
            img = img2.copy()
            method = eval(meth)

            # Apply template Matching
            res = cv2.matchTemplate(img,template,method)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res) #coordinates from the copied image


    #         If the method is TM_SQDIFF or TM_SQDIFF_NORMED, take minimum
    #         if method in [cv.TM_SQDIFF, cv.TM_SQDIFF_NORMED]:
    #             top_left = min_loc
    #         else:
            top_left = max_loc #Top Left coordinates of the matched image
            bottom_right = (top_left[0] + w, top_left[1] + h) #Bottom right coordinates of the matched image 


            topLeftX = top_left[0] #width of the matched image
            topLeftY = top_left[1] #height of the matched image
            
            a = topLeftX + (personWidth/2) #centre point a of the matched image
            b = topLeftY + (personHeight/2) #centre point b of the matched image

            
            # work out the grid position
            gridPositionArray = []
            gridCount = 0
            y = 0
            while (y < rows):
                x = 0 
                while (x < cols):
                    startX = x * personWidth
                    startY = y * personHeight
                    endX = (x + 1) * personWidth
                    endY = (y + 1) * personHeight

                    if (a >= startX and a < endX):
                        if (b >= startY and b < endY):

                            gridPositionArray.append({'gridPosition': gridCount})

                    gridCount = gridCount + 1
                    x = x + 1
                y = y + 1

        return gridPositionArray

    # function that iterates over the halved images with any number of rows and columns(odd or even)
    # if moderation label detected
    # until the last user images with moderation label are cropped out
    def iterate(cols, rows, image, response):
        newCols1 = None
        newRows1 = None
        newCols2 = None
        newRows2 = None
        

        # once the user image with moderation label (1 row and 1 column) is cropped out  
        # save the user image with name "NAUGHTY + unique ID" in jpg and return the user grid position
        if (cols == 1 and rows == 1):
            # Generate unique id for each halved image
            hashV = random.getrandbits(16)
            naughtyImageFileName = "temp/NAUGHTY{}.png".format(hashV)

            # Save the cropped image to S3
            s3 = boto3.client("s3")
            ret, buf = cv2.imencode(".png", image)
            s3.put_object(Bucket=bucket, Key=naughtyImageFileName, Body=buf.tobytes())


            gridPosArray = userPosition(cols, rows, image, img)
            gridPos = gridPosArray[0]['gridPosition']

            results.append({
                "GridPos": gridPos,
                "Labels": response['ModerationLabels'],
            })

            try:
                s3.head_object(Bucket=bucket, Key=naughtyImageFileName)
                s3.delete_object(Bucket=bucket, Key=naughtyImageFileName)
            except:
                pass

            return
            
        # crop the image by columns
        # math.floor is used to halve the images with odd number of columns
        elif (cols > 1):
            image1 = cropImage(0, math.floor(cols/2), 0, rows, image)
            image2 = cropImage(math.floor(cols/2), cols, 0, rows, image)
            newCols1 = math.floor(cols/2)
            newRows1 = rows
            newCols2 = cols - math.floor(cols/2)
            newRows2 = rows

        # crop the image by rows
        # math.floor is used to halve the images with odd number of rows
        elif (rows > 1):
            image1 = cropImage(0, cols, 0, math.floor(rows/2), image)
            image2 = cropImage(0, cols, math.floor(rows/2), rows, image)
            newCols1 = cols
            newRows1 = math.floor(rows/2)
            newCols2 = cols
            newRows2 = rows - math.floor(rows/2)

        response1 = None
        response2 = None
            
        # halved images (image1 and image2)
        # are processed through aws moderation API to check for any moderation labels


    # halved images (image1 and image2)
    # are processed through aws moderation API to check for any moderation labels         
        response1 = client.detect_moderation_labels(Image={'S3Object': {'Bucket': bucket, 'Name': image1}})


        response2 = client.detect_moderation_labels(Image={'S3Object': {'Bucket': bucket, 'Name': image2}})

            
    # if moderation label detected on the halved image, load the image, remove the image
        if (len(response1['ModerationLabels']) > 0 ):
            s3 = boto3.client("s3")
            s3_object = s3.get_object(Bucket=bucket, Key=image1)
            s3_response = s3_object['Body'].read()
            imgNew = np.array(Image.open(io.BytesIO(s3_response)))
            
            iterate(newCols1, newRows1, imgNew, response1)

            s3.delete_object(Bucket=bucket, Key=image1) 
        
        if (len(response2['ModerationLabels']) > 0 ):
            s3 = boto3.client("s3")
            s3_object = s3.get_object(Bucket=bucket, Key=image2)
            s3_response = s3_object['Body'].read()
            imgNew = np.array(Image.open(io.BytesIO(s3_response)))

            
            iterate(newCols2, newRows2, imgNew, response2)
        
            s3.delete_object(Bucket=bucket, Key=image2)

        # Check if image1 or image2 still exists in the S3 bucket and delete it if so
        s3 = boto3.client("s3")
        try:
            s3.head_object(Bucket=bucket, Key=image1)
            s3.delete_object(Bucket=bucket, Key=image1)
        except:
            pass

        try:
            s3.head_object(Bucket=bucket, Key=image2)
            s3.delete_object(Bucket=bucket, Key=image2)
        except:
            pass




    # call the function
    iterate(gridCols, gridRows, img, None)



    return results

# moderation("rekognition.bucket.crowd", "temp/merged_image.png")
