import numpy as np
import boto3
import io
from PIL import Image, ImageDraw, ImageColor, ImageFont, ExifTags




def display_image(bucket,photo,response):
    # Load image from S3 bucket
    s3_connection = boto3.resource('s3')

    s3_object = s3_connection.Object(bucket,photo)
    s3_response = s3_object.get()


    #read file directly from s3 bucket
    stream = io.BytesIO(s3_response['Body'].read())
    image=Image.open(stream)

    #image dimensions
    imgWidth, imgHeight = image.size

    # draw bounding boxes on the grid
    draw = ImageDraw.Draw(image)

    resultArray = []
    if isinstance(response, dict) and 'CustomLabels' in response:
        gridPositionArray = []
        cols = 8
        rows = 4
        x = 0
        y = 0
        gridPositionCount = 0
        gridWidth = imgWidth / cols
        gridHeight = imgHeight / rows

        while x < rows:
            y = 0 
            while y < cols:
                gridLeft = y * gridWidth
                gridTop = x * gridHeight
                gridRight = (y + 1) * gridWidth
                gridBottom = (x + 1) * gridHeight
                leftTop = [y * gridWidth, x * gridHeight]
                leftBottom = [y * gridWidth, (x + 1) * gridHeight]
                rightTop = [(y + 1) * gridWidth, x * gridHeight]
                rightBottom = [(y + 1) * gridWidth, (x + 1) * gridHeight]
                gridPositionArray.append({'row': x, 'col': y, 'Left': gridLeft, 'Right': gridRight, 'Top': gridTop, 'Bottom': gridBottom, 
                                        'leftTop': leftTop, 'rightTop': rightTop, 'rightBottom': rightBottom,
                                        'leftBottom': leftBottom, 'gridPos': gridPositionCount})
                gridPositionCount += 1
                y += 1
                continue
            x += 1
            
        for customLabel in response['CustomLabels']:
            # Bounding box coordinates with detected custom label
            if 'Geometry' in customLabel:
                box = customLabel['Geometry']['BoundingBox']
                left = imgWidth * box['Left']
                top = imgHeight * box['Top']
                width = imgWidth * box['Width']
                height = imgHeight * box['Height']

                points = (
                    (left,top),
                    (left + width, top),
                    (left + width, top + height),
                    (left , top + height),
                    (left, top))
                draw.line(points, fill='#00d400', width=5) # draw bounding box


                resultPoints = [
                    {
                        "Label" : customLabel['Name'],
                        "Confidence": customLabel['Confidence'],
                        "left": left,
                        "right": left + width,
                        "top": top,
                        "bottom": top + height
                    }]


            # append grid position and custom label into result array
                for box in gridPositionArray:
                    for point in resultPoints:
                        itemLeft = point['left']
                        itemRight = point['right']
                        itemTop = point['top']
                        itemBottom =  point['bottom']
                        
                        if itemLeft >= box['leftTop'][0] and itemRight < box['rightTop'][0]:
                            if itemTop >= box['leftTop'][1] and itemBottom < box['leftBottom'][1]:
                                resultArray.append({"gridPos":box['gridPos'], "label": point['Label']})
                         
    return resultArray


def show_custom_labels(bucket,photo, min_confidence,model):
    client=boto3.client('rekognition')

    #Call DetectCustomLabels
    response = client.detect_custom_labels(Image={'S3Object': {'Bucket': bucket, 'Name': photo}},
        MinConfidence = min_confidence,
        ProjectVersionArn = model)



    return response

# # For object detection use case, code to display image.
# display_image(bucket,photo,response)


# def main():

#     bucket='rekognition.bucket.crowd'
#     photo='32_grid_moderation_test.jpg'
#     model='arn:aws:rekognition:****'
#     min_confidence=7

#     label_count=show_custom_labels(model,bucket,photo, min_confidence)
#     # print("Custom labels detected: " + str(label_count))


# if __name__ == "__main__":
#     main()
